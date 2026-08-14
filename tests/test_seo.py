"""Crawlable role pages: honest markup, stable files, live set only."""

import json
import os
import re
import xml.etree.ElementTree as ET

from intern_engine import paths, seo

BASE = "https://example.github.io/repo"


def _rec(**over):
    record = {
        "id": "greenhouse:stripe:1", "company": "Stripe", "company_slug": "stripe",
        "title": "Software Engineering Intern", "season": "Summer 2027",
        "location": "San Francisco, CA", "url": "https://stripe.com/jobs/1",
        "posted_at": "2026-08-03T00:00:00Z", "first_seen_at": "2026-08-03T01:00:00Z",
        "sponsorship": "unknown", "source": "greenhouse", "is_open": True,
    }
    record.update(over)
    return record


class TestSlugs:
    def test_slug_is_readable(self):
        assert seo.role_slug(_rec()).startswith("stripe-software-engineering-intern")

    def test_same_record_always_gets_the_same_slug(self):
        # The URL must survive a re-render, or every run would 404 the last one.
        assert seo.role_slug(_rec()) == seo.role_slug(_rec())

    def test_identical_titles_at_one_employer_do_not_collide(self):
        # Copart really does run eight "Software Engineering Intern, Dallas"
        # reqs. Colliding slugs would silently publish one and drop seven.
        slugs = {seo.role_slug(_rec(id=f"workday:copart:{n}", company="Copart"))
                 for n in range(8)}
        assert len(slugs) == 8

    def test_slug_survives_a_title_edit(self):
        before = seo.role_slug(_rec())
        after = seo.role_slug(_rec(title="Software Engineering Intern (Summer)"))
        assert before != after  # the readable half moves...
        assert before.split("-")[-1] == after.split("-")[-1]  # ...the id half does not


class TestJobPostingMarkup:
    def test_never_invents_an_expiry_date(self):
        # We do not know when an employer closes a req. A guessed validThrough
        # either hides a live role or advertises a dead one.
        assert "validThrough" not in seo.job_posting_ld(_rec(), BASE)

    def test_omits_dateposted_when_unknown(self):
        assert "datePosted" not in seo.job_posting_ld(_rec(posted_at=None), BASE)

    def test_carries_the_employer_date_when_known(self):
        assert seo.job_posting_ld(_rec(), BASE)["datePosted"] == "2026-08-03"

    def test_marks_an_inferred_cycle_as_inferred(self):
        ld = seo.job_posting_ld(_rec(season_inferred=True), BASE)
        assert "inferred" in ld["description"]

    def test_states_a_stated_cycle_plainly(self):
        ld = seo.job_posting_ld(_rec(), BASE)
        assert "as stated in the posting" in ld["description"]

    def test_unknown_sponsorship_is_not_read_as_refusal(self):
        ld = seo.job_posting_ld(_rec(sponsorship="unknown"), BASE)
        assert "unstated, not unavailable" in ld["description"]

    def test_remote_roles_are_flagged_for_search(self):
        ld = seo.job_posting_ld(_rec(location="Remote, USA"), BASE)
        assert ld["jobLocationType"] == "TELECOMMUTE"

    def test_onsite_roles_are_not(self):
        assert "jobLocationType" not in seo.job_posting_ld(_rec(), BASE)

    def test_splits_locality_and_region(self):
        addr = seo.job_posting_ld(_rec(), BASE)["jobLocation"]["address"]
        assert addr["addressLocality"] == "San Francisco"
        assert addr["addressRegion"] == "CA"
        assert addr["addressCountry"] == "US"

    def test_strips_the_site_name_employers_append_to_the_state(self):
        # Copart writes "Dallas, TX - Headquarters". "TX - Headquarters" is not
        # a place, and shipping it as addressRegion is a wrong answer, not a
        # partial one.
        addr = seo.job_posting_ld(
            _rec(location="Dallas, TX - Headquarters"), BASE,
        )["jobLocation"]["address"]
        assert addr["addressLocality"] == "Dallas"
        assert addr["addressRegion"] == "TX"

    def test_accepts_a_spelled_out_state(self):
        addr = seo.job_posting_ld(
            _rec(location="Austin, Texas"), BASE,
        )["jobLocation"]["address"]
        assert addr["addressRegion"] == "Texas"

    def test_drops_a_fragment_that_is_not_a_state(self):
        addr = seo.job_posting_ld(
            _rec(location="Palo Alto, Building 4"), BASE,
        )["jobLocation"]["address"]
        assert addr["addressLocality"] == "Palo Alto"
        assert "addressRegion" not in addr

    def test_country_token_is_not_mistaken_for_a_state(self):
        addr = seo.job_posting_ld(
            _rec(location="Chicago, USA"), BASE,
        )["jobLocation"]["address"]
        assert "addressRegion" not in addr

    def test_page_embeds_parseable_json_ld(self):
        html = seo.render_role_page(_rec(), BASE)
        blob = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        assert json.loads(blob.group(1))["@type"] == "JobPosting"

    def test_page_links_to_the_employer_not_to_us(self):
        assert "https://stripe.com/jobs/1" in seo.render_role_page(_rec(), BASE)


class TestWrite:
    def _write(self, tmp_path, monkeypatch, store):
        monkeypatch.setattr(paths, "DOCS_DIR", str(tmp_path))
        return seo.write(store, BASE)

    def test_writes_a_page_per_open_role(self, tmp_path, monkeypatch):
        store = {"a": _rec(), "b": _rec(id="x", company="Ramp", title="Data Intern")}
        assert self._write(tmp_path, monkeypatch, store) == 2
        assert len(os.listdir(tmp_path / "jobs")) == 3  # two roles + index

    def test_closed_roles_get_no_page(self, tmp_path, monkeypatch):
        store = {"a": _rec(), "b": _rec(id="x", is_open=False)}
        assert self._write(tmp_path, monkeypatch, store) == 1

    def test_a_role_that_closes_has_its_page_removed(self, tmp_path, monkeypatch):
        # An expired posting that keeps returning 200 is what Google asks you
        # not to do, and it wastes crawl budget on dead roles.
        store = {"a": _rec()}
        self._write(tmp_path, monkeypatch, store)
        page = tmp_path / "jobs" / f"{seo.role_slug(_rec())}.html"
        assert page.exists()
        store["a"]["is_open"] = False
        self._write(tmp_path, monkeypatch, store)
        assert not page.exists()

    def test_rendering_twice_changes_nothing(self, tmp_path, monkeypatch):
        # These files are committed every 30 minutes. A run clock in the
        # template would rewrite every page forever and bury the git history.
        store = {"a": _rec()}
        self._write(tmp_path, monkeypatch, store)
        page = tmp_path / "jobs" / f"{seo.role_slug(_rec())}.html"
        first = page.read_text(encoding="utf-8")
        mtime = page.stat().st_mtime_ns
        self._write(tmp_path, monkeypatch, store)
        assert page.read_text(encoding="utf-8") == first
        assert page.stat().st_mtime_ns == mtime  # not even rewritten

    def test_index_links_every_role(self, tmp_path, monkeypatch):
        store = {"a": _rec(), "b": _rec(id="x", company="Ramp")}
        self._write(tmp_path, monkeypatch, store)
        index = (tmp_path / "jobs" / "index.html").read_text(encoding="utf-8")
        for record in store.values():
            assert f"{seo.role_slug(record)}.html" in index


class TestSitemapAndRobots:
    def test_sitemap_is_valid_xml_and_lists_every_open_role(self, tmp_path, monkeypatch):
        monkeypatch.setattr(paths, "DOCS_DIR", str(tmp_path))
        store = {"a": _rec(), "b": _rec(id="x", company="Ramp"),
                 "c": _rec(id="y", is_open=False)}
        seo.write(store, BASE)
        root = ET.parse(tmp_path / "sitemap.xml").getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = {u.findtext("s:loc", namespaces=ns) for u in root.findall("s:url", ns)}
        assert f"{BASE}/" in locs and f"{BASE}/jobs/" in locs
        assert seo.role_url(store["a"], BASE) in locs
        assert seo.role_url(store["c"], BASE) not in locs  # closed

    def test_sitemap_lastmod_is_the_posting_date_not_now(self, tmp_path, monkeypatch):
        monkeypatch.setattr(paths, "DOCS_DIR", str(tmp_path))
        seo.write({"a": _rec()}, BASE)
        assert "<lastmod>2026-08-03</lastmod>" in (
            tmp_path / "sitemap.xml").read_text(encoding="utf-8")

    def test_robots_points_at_the_sitemap_and_hides_the_ledgers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(paths, "DOCS_DIR", str(tmp_path))
        seo.write({"a": _rec()}, BASE)
        robots = (tmp_path / "robots.txt").read_text(encoding="utf-8")
        assert f"Sitemap: {BASE}/sitemap.xml" in robots
        assert "Disallow: /api/" in robots


class TestCanonical:
    def test_every_page_declares_a_canonical_url(self):
        page = seo.render_role_page(_rec(), BASE)
        assert f'<link rel="canonical" href="{seo.role_url(_rec(), BASE)}">' in page
