"""Google Careers connector: parse the ds:1 block embedded in the results page."""

from __future__ import annotations

import json

from intern_engine.connectors import google

ROW = ["1192", "Software Engineering Intern, BS, Summer 2027", "https://signin", [None, "<p>Build</p>"],
       [None, "<li>Pursuing a BS</li>"], "projects/x", None, "Google", "en-US",
       [["Mountain View, CA, USA", ["addr"], "", "", "", "US"], ["New York, NY, USA"]],
       [None, "<p>10-12 week internship</p>"], [4], [1795505814, 0]]


def _page(rows, total):
    return ("<script>AF_initDataCallback({key: 'ds:0', hash: '1', data:[[]]});"
            "AF_initDataCallback({key: 'ds:1', hash: '2', data:"
            + json.dumps([rows, None, total, 20]) + ", sideChannel: {}});</script>")


def test_parse_reads_jobs_and_total():
    jobs, total, ok = google.parse(_page([ROW], 1), {"name": "Google", "slug": "google", "ats": "google"})
    assert ok and total == 1 and len(jobs) == 1
    job = jobs[0]
    assert job.id == "google:google:1192"
    assert job.title == "Software Engineering Intern, BS, Summer 2027"
    assert job.location == "Mountain View, CA, USA; New York, NY, USA"
    assert job.url.endswith("/1192-software-engineering-intern-bs-summer-2027")
    assert job.posted_at.startswith("2026-")
    assert "Pursuing a BS" in job.description


def test_a_changed_page_shape_is_malformed_not_empty():
    jobs, total, ok = google.parse("<html>no data block</html>", {"slug": "google"})
    assert not ok and jobs == []
