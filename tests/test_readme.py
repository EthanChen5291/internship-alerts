"""README/CSV generation: honest counts and a CSV that can't execute."""

import csv
from datetime import UTC, datetime

import pytest

from intern_engine import paths, readme


def _rec(jid, **extra):
    rec = {
        "id": jid, "company": "Acme", "title": "Software Engineer Intern",
        "season": "Summer 2027", "season_inferred": False, "category": "Software",
        "location": "Austin, TX", "url": f"https://x/{jid}", "is_open": True,
        "posted_at": "2026-07-01T00:00:00Z", "first_seen_at": "2026-07-01T00:00:00Z",
        "sponsorship": "unknown", "skills": [],
    }
    rec.update(extra)
    return rec


@pytest.fixture
def outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "README_PATH", str(tmp_path / "README.md"))
    monkeypatch.setattr(paths, "CSV_PATH", str(tmp_path / "internships.csv"))
    return tmp_path


class TestEvidenceSplit:
    """A cycle heading is a claim; only employer-stated roles may sit under it."""

    def test_inferred_roles_get_their_own_section(self, outputs):
        store = {
            "a": _rec("a"),
            "b": _rec("b", season_inferred=True, title="Backend Intern"),
        }
        readme.generate(store)
        text = (outputs / "README.md").read_text(encoding="utf-8")
        assert "## Summer 2027  (1 employer-stated)" in text
        assert "Recently posted — cycle not stated  (1 roles)" in text
        # The guess is marked in its own column, not silently in the heading.
        assert "~Summer 2027" in text

    def test_hero_reports_the_split(self, outputs):
        store = {
            "a": _rec("a"),
            "b": _rec("b", season_inferred=True),
            "c": _rec("c", season_inferred=True),
        }
        readme.generate(store)
        text = (outputs / "README.md").read_text(encoding="utf-8")
        assert "1 have a cycle the employer stated" in text
        assert "2 are recent postings whose cycle isn't stated" in text

    def test_no_rolling_section_when_everything_is_stated(self, outputs):
        readme.generate({"a": _rec("a")})
        text = (outputs / "README.md").read_text(encoding="utf-8")
        assert "## Recently posted" not in text


class TestMultiCycleRendering:
    def test_role_appears_under_every_cycle_it_states(self, outputs):
        store = {"a": _rec("a", title="SWE Internship (Fall 2026/Summer 2027)",
                           season="Summer 2027",
                           seasons=["Summer 2027", "Fall 2026"])}
        readme.generate(store)
        text = (outputs / "README.md").read_text(encoding="utf-8")
        assert "## Summer 2027  (1 employer-stated)" in text
        assert "## Fall 2026  (1 employer-stated)" in text

    def test_it_is_counted_once_not_twice(self, outputs):
        store = {"a": _rec("a", seasons=["Summer 2027", "Fall 2026"])}
        out = readme.generate(store)
        assert out["open"] == 1

    def test_the_cross_reference_names_only_the_other_cycle(self, outputs):
        store = {"a": _rec("a", seasons=["Summer 2027", "Fall 2026"])}
        readme.generate(store)
        text = (outputs / "README.md").read_text(encoding="utf-8")
        # Under Summer 2027 it should point at Fall 2026, and vice versa —
        # repeating the section's own cycle back at the reader is noise.
        assert "_(also open for Fall 2026)_" in text
        assert "_(also open for Summer 2027)_" in text
        assert "also open for Summer 2027, Fall 2026" not in text


class TestCsvCompleteness:
    def test_csv_holds_every_open_role_even_when_readme_caps(self, outputs):
        # The README caps rows per company for readability; the CSV is the
        # machine-readable export and must never silently drop roles.
        store = {str(i): _rec(str(i), title=f"SWE Intern {i}") for i in range(9)}
        readme.generate(store)
        rows = list(csv.DictReader((outputs / "internships.csv").open(encoding="utf-8")))
        assert len(rows) == 9

    def test_csv_carries_the_new_fields(self, outputs):
        store = {"a": _rec("a", title="Data Co-op", location="Remote - US")}
        readme.generate(store)
        row = next(csv.DictReader((outputs / "internships.csv").open(encoding="utf-8")))
        assert row["program"] == "Co-op"
        assert row["remote"] == "yes"

    def test_closed_roles_are_excluded(self, outputs):
        store = {"a": _rec("a"), "b": _rec("b", is_open=False)}
        readme.generate(store)
        rows = list(csv.DictReader((outputs / "internships.csv").open(encoding="utf-8")))
        assert len(rows) == 1


class TestCsvInjection:
    """Job titles are third-party text and land in a file people open in Excel."""

    def test_formula_prefixes_are_neutralized(self):
        for raw in ("=HYPERLINK(\"http://evil\",\"click\")",
                    "+1+1", "-2+3", "@SUM(A1:A9)"):
            out = readme._csv_safe(raw)
            assert out.startswith("'"), raw
            assert out[1:] == raw  # the value itself is preserved, just inert

    def test_ordinary_values_are_untouched(self):
        for raw in ("Software Engineer Intern", "Stripe", "$45/hr",
                    "2026-06-01T00:00:00Z", "New York, NY", ""):
            assert readme._csv_safe(raw) == raw

    def test_non_strings_pass_through(self):
        assert readme._csv_safe(None) is None
        assert readme._csv_safe(42) == 42


class TestHeaderCounts:
    """The README and the API must not report different totals as the same thing."""

    CFG = {"cycles": ["Summer 2027"], "regions": ["US"]}

    def test_capped_listing_reports_both_numbers(self):
        lines = readme._header(self.CFG, total_open=107, companies=3900,
                               new_week=11, shown=104)
        line = next(x for x in lines if "open roles" in x)
        assert "107 open roles" in line
        assert "104 listed below" in line

    def test_no_parenthetical_when_nothing_was_cut(self):
        lines = readme._header(self.CFG, total_open=104, companies=3900,
                               new_week=11, shown=104)
        line = next(x for x in lines if "open roles" in x)
        assert "104 open roles" in line
        assert "listed below" not in line


class TestClosedRecordCells:
    """A closed record must never render as applyable (PR #3, @meshhi13)."""

    def _rec(self, **extra):
        r = {"id": "x", "company": "Acme", "title": "SWE Intern",
             "category": "Software", "location": "Austin, TX",
             "url": "https://acme.example/job/1", "season": "Summer 2027",
             "first_seen_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
        r.update(extra)
        return r

    def test_open_record_gets_an_apply_link(self):
        assert readme._cells(self._rec(is_open=True))[5].startswith("[Apply](")

    def test_closed_record_says_closed_not_a_link(self):
        cell = readme._cells(self._rec(is_open=False))[5]
        assert cell == "Closed"
        assert "http" not in cell

    def test_closed_record_never_shows_the_new_badge(self):
        # first_seen_at is "now", so _is_new() is True — but it's closed.
        assert "🆕" not in readme._cells(self._rec(is_open=False))[1]
        assert "🆕" in readme._cells(self._rec(is_open=True))[1]

    def test_missing_is_open_defaults_to_open(self):
        assert readme._cells(self._rec())[5].startswith("[Apply](")
