import os

import pytest

from intern_engine import store
from intern_engine.models import Job
from intern_engine.pipeline import _dedup


def _job_dict(jid, title="Software Engineer Intern"):
    return {
        "id": jid, "source": "greenhouse", "company_slug": "stripe",
        "company": "Stripe", "title": title, "location": "San Francisco, CA",
        "url": "https://example.com", "posted_at": None,
        "season": "Summer 2027", "category": "Software",
    }


class TestUpsert:
    def test_new_seen_closed_lifecycle(self):
        existing: dict = {}
        keys = {"greenhouse:stripe"}

        new_ids = store.upsert(existing, [_job_dict("a")], keys)
        assert new_ids == ["a"]
        assert existing["a"]["is_open"] is True
        first_seen = existing["a"]["first_seen_at"]

        # Same job again -> not "new", first_seen frozen.
        assert store.upsert(existing, [_job_dict("a")], keys) == []
        assert existing["a"]["first_seen_at"] == first_seen

        # Job disappears from a company we DID reach: the FIRST complete miss
        # only arms the closure (ATS indexes have transient gaps)…
        store.upsert(existing, [], keys)
        assert existing["a"]["is_open"] is True
        assert existing["a"]["missing_streak"] == 1
        # …the second consecutive miss fires it.
        store.upsert(existing, [], keys)
        assert existing["a"]["is_open"] is False
        assert "missing_streak" not in existing["a"]

    def test_unreached_company_is_not_closed(self):
        existing: dict = {}
        store.upsert(existing, [_job_dict("a")], {"greenhouse:stripe"})
        # This run did NOT successfully reach stripe -> must not close its jobs.
        store.upsert(existing, [], complete_keys=set())
        assert existing["a"]["is_open"] is True

    def test_rejected_role_closes_even_from_a_partial_snapshot(self):
        # The Medtronic case: a foreign role we should never have listed came
        # back from a CAPPED Workday response. "This is out of scope" is our
        # own verdict, so it must not wait on snapshot completeness the way
        # "the employer removed it" does.
        existing: dict = {}
        store.upsert(existing, [_job_dict("a")], {"greenhouse:stripe"})
        store.upsert(existing, [], complete_keys=set(), seen_ids={"a"})
        assert existing["a"]["is_open"] is False
        assert existing["a"]["closed_reason"] == "out-of-scope"

    def test_closed_reason_distinguishes_gone_from_out_of_scope(self):
        existing: dict = {}
        keys = {"greenhouse:stripe"}
        store.upsert(existing, [_job_dict("a")], keys)
        store.upsert(existing, [], keys, seen_ids=set())
        store.upsert(existing, [], keys, seen_ids=set())
        assert existing["a"]["closed_reason"] == "gone-from-feed"

    def test_out_of_scope_closes_immediately_without_a_second_miss(self):
        # Our own verdict is deterministic — it needs no confirmation run.
        existing: dict = {}
        store.upsert(existing, [_job_dict("a")], {"greenhouse:stripe"})
        store.upsert(existing, [], complete_keys=set(), seen_ids={"a"})
        assert existing["a"]["is_open"] is False
        assert existing["a"]["closed_reason"] == "out-of-scope"

    def test_reopening_clears_the_closed_reason(self):
        existing: dict = {}
        keys = {"greenhouse:stripe"}
        store.upsert(existing, [_job_dict("a")], keys)
        store.upsert(existing, [], keys)
        store.upsert(existing, [], keys)
        assert existing["a"]["closed_reason"]
        store.upsert(existing, [_job_dict("a")], keys)
        assert "closed_reason" not in existing["a"]

    def test_partial_snapshot_cannot_close_a_role(self):
        # The dangerous case: the fetch SUCCEEDED but the ATS capped its
        # results, so the role is missing from a response that only looks
        # complete. Capped sources are absent from complete_keys, and a role
        # they didn't return must survive rather than read as "taken down".
        existing: dict = {}
        store.upsert(existing, [_job_dict("page101")], {"greenhouse:stripe"})
        store.upsert(existing, [_job_dict("page1")], complete_keys=set())
        assert existing["page101"]["is_open"] is True
        assert "closed_at" not in existing["page101"]

    def test_closed_gets_timestamp_and_reopening_clears_it(self):
        existing: dict = {}
        keys = {"greenhouse:stripe"}
        store.upsert(existing, [_job_dict("a")], keys)
        store.upsert(existing, [], keys)  # arm
        store.upsert(existing, [], keys)  # fire
        assert existing["a"]["is_open"] is False
        assert existing["a"]["closed_at"]
        # The role comes back -> open again, closed_at wiped.
        store.upsert(existing, [_job_dict("a")], keys)
        assert existing["a"]["is_open"] is True
        assert "closed_at" not in existing["a"]

    def test_reappearing_between_misses_disarms_the_closure(self):
        # miss -> seen -> miss must NOT close: the streak resets on sight,
        # so only two CONSECUTIVE complete misses ever fire.
        existing: dict = {}
        keys = {"greenhouse:stripe"}
        store.upsert(existing, [_job_dict("a")], keys)
        store.upsert(existing, [], keys)                 # miss 1: armed
        store.upsert(existing, [_job_dict("a")], keys)   # seen: disarmed
        assert "missing_streak" not in existing["a"]
        store.upsert(existing, [], keys)                 # miss 1 again
        assert existing["a"]["is_open"] is True

    def test_posted_at_backfills_blanks_but_never_shifts(self):
        existing: dict = {}
        keys = {"greenhouse:stripe"}
        store.upsert(existing, [_job_dict("a")], keys)
        assert existing["a"]["posted_at"] is None

        dated = _job_dict("a") | {"posted_at": "2026-06-01T00:00:00Z"}
        store.upsert(existing, [dated], keys)
        assert existing["a"]["posted_at"] == "2026-06-01T00:00:00Z"  # blank filled

        shifted = _job_dict("a") | {"posted_at": "2026-06-20T00:00:00Z"}
        store.upsert(existing, [shifted], keys)
        assert existing["a"]["posted_at"] == "2026-06-01T00:00:00Z"  # frozen

    def test_sponsorship_verdict_never_clobbered_by_unknown(self):
        existing: dict = {}
        keys = {"greenhouse:stripe"}
        flagged = _job_dict("a") | {"sponsorship": "no-sponsorship"}
        store.upsert(existing, [flagged], keys, enriched_ids={"a"})
        assert existing["a"]["sponsorship"] == "no-sponsorship"
        assert existing["a"]["enriched_at"]

        # Next run didn't re-enrich (verdict already stored) -> stays flagged.
        unknown = _job_dict("a") | {"sponsorship": "unknown"}
        store.upsert(existing, [unknown], keys)
        assert existing["a"]["sponsorship"] == "no-sponsorship"


class TestDatePrecision:
    """A better date may replace a worse one; never the other way round."""

    KEYS = {"greenhouse:stripe"}

    def _seen(self, existing, posted, source):
        job = _job_dict("a") | {"posted_at": posted, "posted_at_source": source}
        store.upsert(existing, [job], self.KEYS)

    def test_exact_detail_date_supersedes_a_relative_guess(self):
        # Workday's list API only says "Posted 6 Days Ago". The detail page's
        # real date must be able to correct it — the old backfill-only rule
        # meant the guess, once stored, blocked the truth forever.
        existing: dict = {}
        self._seen(existing, "2026-06-01T00:00:00Z", "relative_derived")
        self._seen(existing, "2026-06-03T00:00:00Z", "date_only")
        assert existing["a"]["posted_at"] == "2026-06-03T00:00:00Z"
        assert existing["a"]["posted_at_source"] == "date_only"

    def test_a_guess_never_overwrites_a_real_date(self):
        existing: dict = {}
        self._seen(existing, "2026-06-03T14:22:00Z", "exact")
        self._seen(existing, "2026-06-01T00:00:00Z", "relative_derived")
        assert existing["a"]["posted_at"] == "2026-06-03T14:22:00Z"
        assert existing["a"]["posted_at_source"] == "exact"

    def test_equal_precision_does_not_shift_the_date(self):
        # The ladder property: same-quality data must not reorder the list.
        existing: dict = {}
        self._seen(existing, "2026-06-01T00:00:00Z", "date_only")
        self._seen(existing, "2026-06-20T00:00:00Z", "date_only")
        assert existing["a"]["posted_at"] == "2026-06-01T00:00:00Z"

    def test_classifier_version_is_stamped_on_enrichment(self):
        existing: dict = {}
        store.upsert(existing, [_job_dict("a")], self.KEYS,
                     enriched_ids={"a"}, classifier_version=7)
        assert existing["a"]["classifier_v"] == 7

    def test_reenrichment_may_retract_a_verdict_to_unknown(self):
        # A re-versioned classifier must be able to withdraw a false positive.
        existing: dict = {}
        flagged = _job_dict("a") | {"sponsorship": "no-sponsorship"}
        store.upsert(existing, [flagged], self.KEYS, enriched_ids={"a"},
                     classifier_version=1)
        retracted = _job_dict("a") | {"sponsorship": "unknown"}
        store.upsert(existing, [retracted], self.KEYS, enriched_ids={"a"},
                     classifier_version=2)
        assert existing["a"]["sponsorship"] == "unknown"

    def test_a_run_that_did_not_reenrich_still_cannot_clobber(self):
        existing: dict = {}
        flagged = _job_dict("a") | {"sponsorship": "no-sponsorship"}
        store.upsert(existing, [flagged], self.KEYS, enriched_ids={"a"})
        store.upsert(existing, [_job_dict("a")], self.KEYS)  # not re-enriched
        assert existing["a"]["sponsorship"] == "no-sponsorship"


class TestPurge:
    def test_drops_long_closed_keeps_recent_and_open(self):
        existing = {
            "old": {"id": "old", "is_open": False, "closed_at": "2026-01-01T00:00:00Z"},
            "recent": {"id": "recent", "is_open": False, "closed_at": store.now_iso()},
            "open": {"id": "open", "is_open": True},
        }
        assert store.purge(existing, keep_closed_days=60) == 1
        assert set(existing) == {"recent", "open"}


class TestDedup:
    def test_collapses_same_role_and_prefers_dated(self):
        undated = Job(id="1", source="greenhouse", company="Stripe",
                      company_slug="stripe", title="Software Engineer Intern",
                      location="SF", url="a", posted_at=None)
        dated = Job(id="2", source="lever", company="Stripe",
                    company_slug="stripe", title="Software Engineer  Intern!",
                    location="SF", url="b", posted_at="2026-06-01T00:00:00Z")
        out = _dedup([undated, dated])
        assert len(out) == 1
        assert out[0].posted_at == "2026-06-01T00:00:00Z"

    def test_keeps_distinct_titles(self):
        a = Job(id="1", source="ashby", company="Verkada", company_slug="verkada",
                title="Backend SWE Intern", location="CA", url="a", posted_at=None)
        b = Job(id="2", source="ashby", company="Verkada", company_slug="verkada",
                title="Frontend SWE Intern", location="CA", url="b", posted_at=None)
        assert len(_dedup([a, b])) == 2

    def test_keeps_same_title_in_different_cities(self):
        # Employers open one requisition per site. Austin and New York are two
        # jobs a student applies to separately — keying on title alone deleted
        # one of them.
        austin = Job(id="gh:acme:1", source="greenhouse", company="Acme",
                     company_slug="acme", title="Software Engineer Intern",
                     location="Austin, TX", url="a", posted_at=None)
        newyork = Job(id="gh:acme:2", source="greenhouse", company="Acme",
                      company_slug="acme", title="Software Engineer Intern",
                      location="New York, NY", url="b", posted_at=None)
        out = _dedup([austin, newyork])
        assert len(out) == 2
        assert {j.location for j in out} == {"Austin, TX", "New York, NY"}

    def test_two_requisitions_on_one_board_both_survive(self):
        # Copart really opened JR109672 AND JR109673 — "Software Engineering
        # Intern, Dallas" twice. Collapsing them deleted a real opening; the
        # board already told us they're distinct by giving them distinct ids.
        a = Job(id="workday:copart:JR109672", source="workday", company="Copart",
                company_slug="copart", title="Software Engineering Intern",
                location="Dallas, TX - Headquarters", url="a", posted_at=None)
        b = Job(id="workday:copart:JR109673", source="workday", company="Copart",
                company_slug="copart", title="Software Engineering Intern",
                location="Dallas, TX - Headquarters", url="b", posted_at=None)
        out = _dedup([a, b])
        assert len(out) == 2
        assert {j.id for j in out} == {a.id, b.id}

    def test_same_role_same_city_still_collapses_across_sources(self):
        # One posting syndicated to two ATS: different external ids, same place,
        # same work mode. That IS a duplicate and must still collapse.
        a = Job(id="greenhouse:acme:1", source="greenhouse", company="Acme",
                company_slug="acme", title="Software Engineer Intern",
                location="Austin, TX", url="a", posted_at=None)
        b = Job(id="lever:acme:zz", source="lever", company="Acme",
                company_slug="acme", title="Software Engineer Intern",
                location="Austin TX", url="b", posted_at="2026-06-01T00:00:00Z")
        out = _dedup([a, b])
        assert len(out) == 1
        assert out[0].posted_at == "2026-06-01T00:00:00Z"  # the dated copy wins

    def test_remote_and_onsite_are_different_jobs(self):
        # "Austin, TX" and "Austin, TX (Remote)" are two things a student picks
        # between. Stripping the work mode for comparison merged them.
        onsite = Job(id="greenhouse:acme:1", source="greenhouse", company="Acme",
                     company_slug="acme", title="Software Engineer Intern",
                     location="Austin, TX", url="a", posted_at=None)
        remote = Job(id="lever:acme:zz", source="lever", company="Acme",
                     company_slug="acme", title="Software Engineer Intern",
                     location="Austin, TX (Remote)", url="b",
                     posted_at="2026-06-01T00:00:00Z")
        assert len(_dedup([onsite, remote])) == 2

    def test_ambiguous_cross_source_identity_keeps_everything(self):
        # Greenhouse lists TWO distinct requisitions; Lever carries one copy.
        # There's no way to prove which req the Lever posting mirrors — no
        # shared requisition id, no canonical URL — and deleting a real opening
        # is worse than showing a possible duplicate. Everything survives;
        # cross-source collapse only fires on the provable 1-per-source case.
        reqs = [
            Job(id=f"greenhouse:acme:{n}", source="greenhouse", company="Acme",
                company_slug="acme", title="Software Engineer Intern",
                location="Austin, TX", url=f"gh{n}", posted_at=None)
            for n in (1, 2)
        ]
        copy = Job(id="lever:acme:zz", source="lever", company="Acme",
                   company_slug="acme", title="Software Engineer Intern",
                   location="Austin, TX", url="lv",
                   posted_at="2026-06-01T00:00:00Z")
        out = _dedup([copy, *reqs])
        assert len(out) == 3
        assert {j.id for j in out} == {"greenhouse:acme:1", "greenhouse:acme:2",
                                       "lever:acme:zz"}


class TestCorruptState:
    """A corrupt store must stop the run, never silently reset it."""

    def test_missing_file_is_an_empty_store(self, tmp_path):
        assert store.load(str(tmp_path / "nope.json")) == {}

    def test_truncated_json_raises(self, tmp_path):
        path = tmp_path / "jobs.json"
        path.write_text('{"a": {"id": "a", "is_o', encoding="utf-8")
        with pytest.raises(store.StateCorrupt):
            store.load(str(path))

    def test_wrong_toplevel_type_raises(self, tmp_path):
        path = tmp_path / "jobs.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(store.StateCorrupt):
            store.load(str(path))

    def test_non_object_record_raises(self, tmp_path):
        path = tmp_path / "jobs.json"
        path.write_text('{"a": "not a record"}', encoding="utf-8")
        with pytest.raises(store.StateCorrupt):
            store.load(str(path))

    def test_save_is_atomic_and_round_trips(self, tmp_path):
        path = str(tmp_path / "sub" / "jobs.json")
        store.save(path, {"a": {"id": "a"}})
        assert store.load(path) == {"a": {"id": "a"}}
        # The temp file must not survive the swap.
        assert not os.path.exists(f"{path}.tmp")
