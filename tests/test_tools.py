"""Guards for tools/ — the scripts CI runs but unit tests never imported.

The Thursday audit workflow broke in production because connectors started
returning a `Fetch` and `tools/audit_seasons.py` still did `for j in fetched`.
Nothing caught it: the tools directory had zero tests, so a green suite meant
nothing about the code CI actually executes on a schedule.
"""

from __future__ import annotations

import asyncio
import importlib
import pkgutil

import pytest

from intern_engine import connectors, models
from intern_engine.models import Fetch, Job


def _job(jid: str = "greenhouse:acme:1") -> Job:
    return Job(id=jid, source="greenhouse", company="Acme", company_slug="acme",
               title="Software Engineer Intern", location="Austin, TX",
               url="https://x/1", description="Summer 2027 internship.")


class TestConnectorReturnContract:
    """Every connector must return something Fetch.of understands."""

    def test_every_connector_module_is_importable(self):
        names = [m.name for m in pkgutil.iter_modules(connectors.__path__)]
        assert names, "no connector modules discovered"
        for name in names:
            importlib.import_module(f"intern_engine.connectors.{name}")

    def test_fetch_of_normalizes_both_shapes(self):
        # Connectors may return a bare list (whole-board reads) or a Fetch
        # (paginated reads). Callers must never have to care which.
        assert Fetch.of([_job()]).jobs[0].id == "greenhouse:acme:1"
        assert Fetch.of(Fetch([_job()], complete=False)).complete is False

    def test_fetch_result_is_not_iterable_by_accident(self):
        # The exact production bug: iterating a Fetch raised TypeError at
        # runtime. Keep that explicit so callers use `.jobs`.
        with pytest.raises(TypeError):
            list(Fetch([_job()]))


class TestAuditSeasonsListPath:
    """The list-sourced branch that actually failed on Thursday."""

    def test_list_sourced_descriptions_are_read_from_a_fetch(self, monkeypatch):
        import tools.audit_seasons as audit

        # 'lever' ships descriptions in its list payload, so it takes the
        # list-sourced branch rather than the per-role detail fetch. The
        # connector's job must carry the SAME id the store holds — that id is
        # what the branch joins on.
        listed = Job(**{**_job().__dict__, "id": "lever:acme:1", "source": "lever"})

        async def fake_connector(company, net):
            return Fetch([listed], complete=True)  # shape connectors return today

        monkeypatch.setitem(audit.CONNECTORS, "lever", fake_connector)

        async def fake_fetch_all(jobs, companies):
            return await audit._texts_for(jobs, companies)

        texts = asyncio.run(fake_fetch_all(
            [listed],
            [{"ats": "lever", "slug": "acme", "name": "Acme"}],
        ))
        assert texts["lever:acme:1"] == "Summer 2027 internship."


class TestVerifyAccuracyImportable:
    def test_module_imports_and_exposes_a_main(self):
        mod = importlib.import_module("tools.verify_accuracy")
        assert callable(getattr(mod, "main", None))


class TestDatePrecisionContract:
    """models.date_source underpins the never-downgrade rule in the store."""

    def test_ranking_is_ordered_worst_to_best(self):
        p = models.DATE_PRECISION
        assert p[None] < p["relative_derived"] < p["date_only"] < p["exact"]

    def test_shape_classification(self):
        assert models.date_source("2026-07-01") == "date_only"
        assert models.date_source("2026-07-01T00:00:00Z") == "date_only"
        assert models.date_source("2026-07-01T09:31:00Z") == "exact"
        assert models.date_source(None) is None
