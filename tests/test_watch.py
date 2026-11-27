"""Big-company fast lane (watch.py) and its dedupe with the personal email."""

from __future__ import annotations

import json

from intern_engine import personal_alerts, watch


def test_watched_companies_match_names_and_skip_outage_boards():
    reg = [
        {"name": "Capital One", "ats": "workday", "slug": "capitalone"},
        {"name": "Stripe", "ats": "greenhouse", "slug": "stripe"},
        {"name": "Visa", "ats": "workday", "slug": "visa"},
        {"name": "Visa", "ats": "smartrecruiters", "slug": "Visa"},
        {"name": "Acme", "ats": "greenhouse", "slug": "acme"},
    ]
    got = watch.watched_companies(reg, ["capital one", "STRIPE", "Visa"], {"workday"})
    assert [(c["name"], c["ats"]) for c in got] == [("Stripe", "greenhouse"),
                                                    ("Visa", "smartrecruiters")]


def test_personal_email_skips_roles_the_watch_already_sent(monkeypatch, tmp_path):
    state = tmp_path / "watch_state.json"
    state.write_text(json.dumps({"seeded": True, "sent_ids": ["gh:stripe:1"]}))
    monkeypatch.setattr(watch, "STATE_PATH", str(state))
    monkeypatch.setattr(personal_alerts, "email_configured", lambda: True)
    sent: list[list[str]] = []
    monkeypatch.setattr(personal_alerts, "build_email",
                        lambda recs: ("s", ",".join(r["id"] for r in recs)))
    monkeypatch.setattr(personal_alerts, "_post_email",
                        lambda subject, html: sent.append(html.split(",")))
    store = {
        "gh:stripe:1": {"company": "Stripe", "title": "SWE Intern", "is_open": True},
        "gh:acme:2": {"company": "Acme", "title": "SWE Intern", "is_open": True},
    }
    done = personal_alerts.send_email(store, ["gh:stripe:1", "gh:acme:2"])
    assert set(done) == {"gh:stripe:1", "gh:acme:2"}
    assert sent == [["gh:acme:2"]]


class _Job:
    def __init__(self, jid, board):
        self.id, self.board_key = jid, board


def _wire(monkeypatch, tmp_path, reads, state=None):
    """reads: {board: [job ids]} returned by one fake sweep."""
    path = tmp_path / "watch_state.json"
    if state is not None:
        path.write_text(json.dumps(state))
    monkeypatch.setattr(watch, "STATE_PATH", str(path))
    wl = tmp_path / "watchlist.json"
    wl.write_text(json.dumps({"companies": list(reads)}))
    monkeypatch.setattr(watch, "WATCHLIST_PATH", str(wl))
    companies = [{"name": b, "ats": "greenhouse", "slug": b} for b in reads]
    monkeypatch.setattr(watch.registry, "load", lambda: companies)
    monkeypatch.setattr(watch.config, "load_config", lambda: {})
    monkeypatch.setattr(watch.store, "load", lambda p: {})
    monkeypatch.setattr(watch.quality, "load_blocklist", lambda: [])

    async def fake_fetch(cs, after):
        return [(c, None, None) for c in cs], None

    monkeypatch.setattr(watch.pipeline, "_fetch_all", fake_fetch)
    jobs = [_Job(j, f"greenhouse:{b}") for b, ids in reads.items() for j in ids]
    monkeypatch.setattr(watch.pipeline, "_keep_matching",
                        lambda *a: (jobs, {f"greenhouse:{b}" for b in reads}))
    mail: list[str] = []
    monkeypatch.setattr(watch.personal_alerts, "email_configured", lambda: True)
    monkeypatch.setattr(watch.personal_alerts, "build_email", lambda recs: ("s", "h"))
    monkeypatch.setattr(watch.personal_alerts, "_post_email", lambda s, h: mail.append(s))
    monkeypatch.setattr(watch, "_record", lambda j: {"id": j.id})
    return mail, path


def test_first_run_and_new_boards_are_learned_silently(monkeypatch, tmp_path):
    mail, path = _wire(monkeypatch, tmp_path, {"stripe": ["s1"]})
    assert "learned 1" in watch.run() and mail == []
    mail, path = _wire(monkeypatch, tmp_path, {"stripe": ["s1", "s2"], "google": ["g1", "g2"]},
                       state=json.loads(path.read_text()))
    out = watch.run()
    assert "learned 2" in out and "emailed 1" in out
    assert len(mail) == 1
    assert set(json.loads(path.read_text())["sent_ids"]) == {"s1", "s2", "g1", "g2"}


def test_legacy_state_learns_only_companies_added_since(monkeypatch, tmp_path):
    mail, _ = _wire(monkeypatch, tmp_path, {"stripe": ["s1", "s2"], "google": ["g1"]},
                    state={"seeded": True, "sent_ids": ["s1"]})
    out = watch.run()
    assert "learned 1" in out and "emailed 1" in out  # g1 learned, s2 emailed
