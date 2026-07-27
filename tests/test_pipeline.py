from datetime import UTC, datetime

from intern_engine.models import Fetch
from intern_engine.pipeline import _detection_latency, _parse_iso


class TestParseIso:
    def test_z_suffix_is_utc_aware(self):
        dt = _parse_iso("2026-07-15T21:00:00Z")
        assert dt.tzinfo is not None
        assert dt.utcoffset().total_seconds() == 0

    def test_naive_and_date_only_assumed_utc(self):
        # Some ATS feeds ship timestamps with no offset (or a bare date);
        # they must come back aware or datetime arithmetic explodes.
        for raw in ("2026-07-15T18:00:00", "2026-07-15"):
            dt = _parse_iso(raw)
            assert dt.tzinfo is UTC

    def test_offset_normalized_to_utc(self):
        dt = _parse_iso("2026-07-15T14:00:00-04:00")
        assert dt.hour == 18
        assert dt.tzinfo is not None

    def test_garbage_is_none(self):
        assert _parse_iso("not a date") is None
        assert _parse_iso(None) is None


class TestDetectionLatency:
    # A fixed "now" so the window is measured against the fixtures, not the
    # day the suite happens to run.
    NOW = datetime(2026, 7, 16, tzinfo=UTC)

    def test_mixed_naive_and_aware_does_not_crash(self):
        # Regression: a single offset-less posted_at next to a Z-suffixed
        # first_seen_at crashed every run with TypeError (2026-07-15 outage).
        existing = {
            "a": {"posted_at": "2026-07-15T18:00:00",   # naive from the ATS
                  "first_seen_at": "2026-07-15T21:00:00Z"},
            "b": {"posted_at": "2026-07-15T10:00:00Z",
                  "first_seen_at": "2026-07-15T11:00:00Z"},
        }
        out = _detection_latency(existing, now=self.NOW)
        assert out["sample_size"] == 2
        assert out["median_minutes"] == 120.0  # median of 180 and 60

    def test_empty_store(self):
        out = _detection_latency({})
        assert out["median_minutes"] is None
        assert out["p95_minutes"] is None
        assert out["sample_size"] == 0
        assert out["window_days"] == 7

    def test_old_postings_outside_window_excluded(self):
        # The window bounds when the role was PUBLISHED. It used to bound the
        # detection delay instead, so a role published in January and first
        # seen in July counted as a 6-day "detection".
        existing = {
            "old": {"posted_at": "2026-01-01T09:30:00Z",
                    "first_seen_at": "2026-01-07T09:30:00Z"},
        }
        assert _detection_latency(existing, now=self.NOW)["sample_size"] == 0

    def test_date_only_timestamps_are_excluded(self):
        # A bare date is assumed midnight; measuring minutes against it invents
        # up to 24h of latency. These roles are out of the metric entirely.
        existing = {
            "dateonly": {"posted_at": "2026-07-15",
                         "first_seen_at": "2026-07-15T18:00:00Z"},
            "midnight": {"posted_at": "2026-07-15T00:00:00Z",
                         "first_seen_at": "2026-07-15T18:00:00Z"},
            "exact": {"posted_at": "2026-07-15T10:00:00Z",
                      "first_seen_at": "2026-07-15T11:00:00Z"},
        }
        out = _detection_latency(existing, now=self.NOW)
        assert out["sample_size"] == 1
        assert out["median_minutes"] == 60.0

    def test_reports_p95_alongside_median(self):
        existing = {
            str(i): {"posted_at": "2026-07-15T10:00:00Z",
                     "first_seen_at": f"2026-07-15T10:{i:02d}:00Z"}
            for i in range(1, 21)
        }
        out = _detection_latency(existing, now=self.NOW)
        assert out["sample_size"] == 20
        assert out["p95_minutes"] >= out["median_minutes"]


class TestStickySeasons:
    """A season already on record wins over re-inference (see _keep_matching)."""

    CFG = {"cycles": ["Summer 2027", "Fall 2026"], "regions": ["US"],
           "role_scope": "tech", "infer_undated": True, "infer_max_age_days": 45}

    def _results(self, posted_days_ago):
        from datetime import UTC, datetime, timedelta

        from intern_engine.models import Job
        posted = (datetime.now(UTC) - timedelta(days=posted_days_ago)).strftime("%Y-%m-%d")
        job = Job(id="greenhouse:acme:1", source="greenhouse", company="Acme",
                  company_slug="acme", title="Software Engineer Intern",
                  location="New York, NY", url="https://x",
                  posted_at=f"{posted}T00:00:00Z")
        return [({"ats": "greenhouse", "slug": "acme", "name": "Acme"},
                 Fetch([job]), None)]

    def _keep(self, results, existing):
        from intern_engine.pipeline import _keep_matching
        kept, *_ = _keep_matching(results, self.CFG, {}, existing)
        return kept

    def test_fresh_undated_role_is_date_inferred(self):
        kept = self._keep(self._results(3), {})
        assert [(j.season, j.season_inferred) for j in kept] == [("Summer 2027", True)]

    def test_text_verified_season_on_record_beats_reinference(self):
        existing = {"greenhouse:acme:1": {"season": "Fall 2026", "season_inferred": False}}
        kept = self._keep(self._results(3), existing)
        assert [(j.season, j.season_inferred) for j in kept] == [("Fall 2026", False)]

    def test_sticky_season_outlives_inference_recency_window(self):
        # 60 days old: a fresh inference would refuse, but the role is already
        # on record — it must stay open instead of flipping closed.
        existing = {"greenhouse:acme:1": {"season": "Summer 2027", "season_inferred": True}}
        kept = self._keep(self._results(60), existing)
        assert [(j.season, j.season_inferred) for j in kept] == [("Summer 2027", True)]

    def test_stale_undated_role_without_record_still_dropped(self):
        assert self._keep(self._results(60), {}) == []

    def test_verified_offcycle_season_is_sticky_dropped(self):
        # Text verification recorded "Summer 2026": the role must stay off the
        # list — never re-inferred back in from its posting date.
        existing = {"greenhouse:acme:1": {"season": "Summer 2026", "season_inferred": False}}
        assert self._keep(self._results(3), existing) == []

    def test_explicit_offcycle_title_beats_stale_sticky_season(self):
        # A store written by older code may hold "Summer 2027" for a title
        # that literally says "Summer 2026" — the title's own year wins.
        from datetime import UTC, datetime, timedelta

        from intern_engine.models import Job
        posted = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%d")
        job = Job(id="workday:stevens:1", source="workday", company="Stevens",
                  company_slug="stevens", title="Summer 2026 Intern: Cyber Security",
                  location="Hoboken, NJ", url="https://x",
                  posted_at=f"{posted}T00:00:00Z")
        results = [({"ats": "workday", "slug": "stevens", "name": "Stevens"},
                    Fetch([job]), None)]
        existing = {"workday:stevens:1": {"season": "Summer 2027", "season_inferred": True}}
        assert self._keep(results, existing) == []

    def test_legacy_unspecified_season_still_reinferred(self):
        # Only a real "<Term> <Year>" label is a verdict; junk labels fall
        # through to inference as before.
        existing = {"greenhouse:acme:1": {"season": "Unspecified"}}
        kept = self._keep(self._results(3), existing)
        assert [(j.season, j.season_inferred) for j in kept] == [("Summer 2027", True)]


class TestAgeCutoff:
    """The age filter backs an INFERENCE; it can't overrule a stated cycle."""

    CFG = {"cycles": ["Summer 2027", "Fall 2026"], "regions": ["US"],
           "role_scope": "tech", "infer_undated": True, "infer_max_age_days": 45,
           "max_age_days": 270}

    def _keep(self, title, days_ago):
        from datetime import datetime, timedelta

        from intern_engine.models import Job
        from intern_engine.pipeline import _keep_matching
        posted = (datetime.now(UTC) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        job = Job(id="amazon:amazon:1", source="amazon", company="Amazon",
                  company_slug="amazon", title=title, location="Seattle, WA",
                  url="https://x", posted_at=f"{posted}T00:00:00Z")
        results = [({"ats": "amazon", "slug": "amazon", "name": "Amazon"},
                    Fetch([job]), None)]
        kept, *_ = _keep_matching(results, self.CFG, {}, {})
        return kept

    def test_old_but_employer_stated_cycle_is_kept(self):
        # Amazon's "Fall 2026 (US)" internship was posted early and is still
        # open and still for Fall 2026. Closing it for age was us overriding
        # what the company wrote.
        kept = self._keep("Software Development Engineer Internship - Fall 2026 (US)", 300)
        assert [j.season for j in kept] == ["Fall 2026"]

    def test_old_and_only_inferred_is_dropped(self):
        # No stated cycle: recency was the ONLY evidence, and it's gone.
        assert self._keep("Software Engineer Intern", 300) == []

    def test_recent_inferred_is_kept(self):
        kept = self._keep("Software Engineer Intern", 3)
        assert [(j.season, j.season_inferred) for j in kept] == [("Summer 2027", True)]


class TestRegionConfig:
    """regions config must be honored end-to-end (Canada was silently dropped)."""

    def _results(self, location):
        from datetime import UTC, datetime, timedelta

        from intern_engine.models import Job
        posted = (datetime.now(UTC) - timedelta(days=3)).strftime("%Y-%m-%d")
        job = Job(id="greenhouse:acme:1", source="greenhouse", company="Acme",
                  company_slug="acme", title="Software Engineer Intern, Summer 2027",
                  location=location, url="https://x",
                  posted_at=f"{posted}T00:00:00Z")
        return [({"ats": "greenhouse", "slug": "acme", "name": "Acme"},
                 Fetch([job]), None)]

    def _keep(self, results, regions):
        from intern_engine.pipeline import _keep_matching
        cfg = {"cycles": ["Summer 2027", "Fall 2026"], "regions": regions,
               "role_scope": "tech"}
        kept, *_ = _keep_matching(results, cfg, {}, {})
        return kept

    def test_us_only_drops_canada(self):
        assert self._keep(self._results("Toronto, Ontario, Canada"), ["US"]) == []

    def test_us_and_canada_keeps_canada(self):
        kept = self._keep(self._results("Toronto, Ontario, Canada"), ["US", "Canada"])
        assert len(kept) == 1

    def test_us_and_canada_still_keeps_us(self):
        kept = self._keep(self._results("New York, NY"), ["US", "Canada"])
        assert len(kept) == 1


class TestDateSourceMigration:
    def test_legacy_records_get_a_shape_derived_label(self):
        from intern_engine.pipeline import _migrate_date_sources
        existing = {
            "a": {"posted_at": "2026-06-01T08:00:00-04:00"},          # real time
            "b": {"posted_at": "2026-06-01T00:00:00Z"},               # a day
            "c": {"posted_at": None},
            "d": {"posted_at": "2026-06-02T10:00:00Z",
                  "posted_at_source": "relative_derived"},            # labeled: kept
        }
        _migrate_date_sources(existing)
        assert existing["a"]["posted_at_source"] == "exact"
        assert existing["b"]["posted_at_source"] == "date_only"
        assert "posted_at_source" not in existing["c"]
        assert existing["d"]["posted_at_source"] == "relative_derived"


class TestOutOfScopeSweep:
    def test_foreign_open_record_is_closed_from_the_store_alone(self):
        # The Lausanne case: admitted under an older filter, then unreachable
        # by fetch-based closure because Medtronic's board is capped. Scope is
        # our own verdict — no fetch evidence required.
        from intern_engine.pipeline import _close_out_of_scope
        cfg = {"regions": ["US"]}
        existing = {
            "a": {"is_open": True, "location": "Lausanne, Vaud, Switzerland"},
            "b": {"is_open": True, "location": "Austin, TX"},
            "c": {"is_open": False, "location": "Paris, France"},   # already closed
            "d": {"is_open": True, "location": "—"},                # no location: leave
        }
        assert _close_out_of_scope(existing, cfg) == 1
        assert existing["a"]["is_open"] is False
        assert existing["a"]["closed_reason"] == "out-of-scope"
        assert existing["b"]["is_open"] is True
        assert existing["d"]["is_open"] is True

    def test_sweep_is_off_when_international_is_included(self):
        from intern_engine.pipeline import _close_out_of_scope
        cfg = {"regions": ["US"], "include_international": True}
        existing = {"a": {"is_open": True, "location": "Paris, France"}}
        assert _close_out_of_scope(existing, cfg) == 0
        assert existing["a"]["is_open"] is True
