"""Static dashboard contracts for freshness, saves, and double opt-in."""

from intern_engine import dashboard, paths


def test_dashboard_uses_fetch_time_and_prunes_ghost_saves():
    store = {
        "a": {
            "id": "a", "company": "Acme", "title": "SWE Intern",
            "season": "Summer 2027", "seasons": ["Summer 2027"],
            "season_inferred": False, "category": "Software",
            "location": "Austin, TX", "url": "https://x/1", "is_open": True,
            "posted_at": "2026-08-05T00:00:00Z",
            "first_seen_at": "2026-08-05T01:00:00Z",
            "sponsorship": "unknown", "skills": [], "source": "greenhouse",
        }
    }
    stats = {
        "generated_at": "2026-08-06T14:08:27Z", "companies_total": 1,
        "companies_by_source": {"greenhouse": 1}, "open_total": 1,
    }
    dashboard.generate(store, stats)
    html = open(paths.DASHBOARD_PATH, encoding="utf-8").read()
    assert "Data as of Aug 06, 2026 at 14:08 UTC" in html
    assert "if (!currentIds[id]) delete saved[id]" in html
    assert "/rest/v1/rpc/request_email_subscription" in html
    confirm = open(f"{paths.DOCS_DIR}/confirm.html", encoding="utf-8").read()
    assert "/rest/v1/rpc/confirm_email_subscription" in confirm
    assert "go.addEventListener('click'" in confirm
