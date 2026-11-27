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
