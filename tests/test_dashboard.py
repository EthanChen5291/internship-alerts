"""Static dashboard contracts for freshness, saves, and resume actions."""

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
            "class_year": "Juniors+",
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
    assert "/rest/v1/rpc/request_email_subscription" not in html
    assert "resume.html?job=a" in html
    assert "Competition: " in html
    assert "not an applicant count or acceptance rate" in html
    assert "Employer-stated applicant class year" in html
    assert ">Juniors+</span>" in html
    resume = open(f"{paths.DOCS_DIR}/resume.html", encoding="utf-8").read()
    assert "visual structure stay unchanged" in resume
    assert "saved automatically on this browser" in resume
    assert 'id="remember"' not in resume
    assert "Highlighted on screen" in resume
    assert "Compensation: " in resume
    assert "document.title=outputTitle()" in resume
    assert ">Download PDF</button>" in resume
    assert "TECHNICAL SKILLS" in resume
    assert "entries('HONORS','honors','honor')" in resume
    assert "out[section]=ordered" not in resume
    assert "window.print()" in resume


def _opening(jid, **extra):
    rec = {
        "id": jid, "company": "Copart", "title": "Software Engineering Intern",
        "season": "Summer 2027", "seasons": ["Summer 2027"],
        "season_inferred": False, "category": "Software",
        "location": "Dallas, TX - Headquarters", "url": f"https://x/{jid}",
        "is_open": True, "posted_at": "2026-08-05T00:00:00Z",
        "first_seen_at": "2026-08-05T01:00:00Z",
        "sponsorship": "unknown", "skills": [], "source": "workday",
    }
    rec.update(extra)
    return rec


def _render(store):
    dashboard.generate(store, {
        "generated_at": "2026-08-07T21:35:57Z", "companies_total": 1,
        "companies_by_source": {"workday": 1}, "open_total": len(store),
    })
    return open(paths.DASHBOARD_PATH, encoding="utf-8").read()


def test_identical_requisitions_render_as_one_row():
    html = _render({str(i): _opening(str(i)) for i in range(8)})
    assert html.count("<tr data-id=") == 1
    assert "8 openings" in html


def test_a_grouped_row_still_links_every_requisition():
    html = _render({str(i): _opening(str(i)) for i in range(3)})
    for jid in ("0", "1", "2"):
        assert f"https://x/{jid}" in html


def test_a_grouped_row_carries_its_opening_count_for_the_filter_maths():
    # The visible count is a count of JOBS, so the filter script sums this
    # attribute rather than counting rows.
    html = _render({str(i): _opening(str(i)) for i in range(3)})
    assert 'data-openings="3"' in html
    assert "parseInt(tr.dataset.openings || '1', 10)" in html


def test_distinct_roles_are_not_folded_together():
    html = _render({
        "a": _opening("a"),
        "b": _opening("b", title="Database Engineering Intern"),
    })
    assert html.count("<tr data-id=") == 2
    assert "openings<" not in html


def test_a_star_on_an_absorbed_requisition_moves_to_the_surviving_row():
    # Folding three rows into one must not delete a reader's saved role. The
    # pruning step ("remove ids no longer in the artifact") would have done
    # exactly that to any sibling id, silently.
    html = _render({str(i): _opening(str(i)) for i in range(3)})
    assert 'data-ids="0|1|2"' in html
    assert "if (saved[ids[i]]) { saved[tr.dataset.id] = saved[ids[i]]; break; }" in html
    # And every one of those ids still counts as present.
    assert "ids.forEach(function (id) { currentIds[id] = true; });" in html
