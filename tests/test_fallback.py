"""Owner-only Workday fallback via SimplifyJobs (fallback.py)."""

from __future__ import annotations

import json
import time

from intern_engine import fallback

CFG = {"cycles": ["Summer 2027"], "regions": ["US"], "excluded_categories": ["Hardware"]}
NOW = time.time()


def _item(i, title="Software Engineer Intern", url=None, posted=NOW, **kw):
    return {
        "id": str(i), "company_name": f"Co{i}", "title": title, "active": True,
        "is_visible": True, "terms": ["Summer 2027"], "locations": ["Austin, TX"],
        "url": url or f"https://co{i}.wd5.myworkdayjobs.com/x/job/Austin/SWE_{i}",
        "date_posted": posted, **kw,
    }


def test_select_keeps_only_blocked_ats_in_scope_roles_not_in_store():
    listings = [
        _item(1),
        _item(2, url="https://job-boards.greenhouse.io/co2/jobs/1"),  # not Workday
        _item(3, terms=["Summer 2026"]),                              # wrong cycle
        _item(4, active=False),                                       # closed
        _item(5, title="Marketing Intern"),                           # not tech
        _item(6, locations=["London, UK"]),                           # region
        _item(7),                                                     # already in store
    ]
    store = {"workday:co7:1": {"company": "Co7", "title": "Software Engineer Intern",
                               "url": "https://elsewhere"}}
    got = [r["id"] for r in fallback.select(listings, CFG, {"workday"}, store)]
    assert got == ["simplify:1"]


def test_no_outage_means_nothing_selected():
    assert fallback.select([_item(1)], CFG, set(), {}) == []


def _wire(monkeypatch, tmp_path, listings, sent_mail):
    monkeypatch.setenv("KNOWN_OUTAGE_SOURCES", "workday")
    monkeypatch.setattr(fallback, "STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(fallback.personal_alerts, "email_configured", lambda: True)
    monkeypatch.setattr(fallback.config, "load_config", lambda: CFG)
    monkeypatch.setattr(fallback, "_fetch", lambda url: listings)
    monkeypatch.setattr(fallback.personal_alerts, "build_email", lambda recs: ("s", "NEW INTERNSHIP ALERT"))
    monkeypatch.setattr(fallback.personal_alerts, "_post_email",
                        lambda subject, html: sent_mail.append(subject))


def test_first_run_mails_only_roles_since_the_outage_then_nothing_twice(monkeypatch, tmp_path):
    old = fallback._FIRST_RUN_SINCE.timestamp() - 86400
    listings = [_item(1), _item(2, posted=old)]
    mail: list[str] = []
    _wire(monkeypatch, tmp_path, listings, mail)
    (tmp_path / "state.json").write_text(json.dumps({"seeded": False, "sent_ids": []}))
    assert "emailed 1" in fallback.run({})
    assert mail and mail[0].startswith("[Workday via Simplify]")
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["seeded"] and set(state["sent_ids"]) == {"simplify:1", "simplify:2"}
    assert "emailed" not in fallback.run({})
    assert len(mail) == 1


def test_failed_send_is_retried_next_run(monkeypatch, tmp_path):
    mail: list[str] = []
    _wire(monkeypatch, tmp_path, [_item(1)], mail)

    def boom(subject, html):
        raise RuntimeError("brevo down")

    monkeypatch.setattr(fallback.personal_alerts, "_post_email", boom)
    assert "email failed" in fallback.run({})
    monkeypatch.setattr(fallback.personal_alerts, "_post_email",
                        lambda subject, html: mail.append(subject))
    assert "emailed 1" in fallback.run({})
