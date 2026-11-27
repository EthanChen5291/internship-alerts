"""Apple and Atlassian connectors, and plural "Internships" titles."""

from __future__ import annotations

import json

from intern_engine import filters
from intern_engine.connectors import apple, atlassian


def test_plural_internships_titles_count_as_internships():
    assert filters.is_internship("Software Undergrad Engineering Internships")
    assert not filters.is_internship("Internal Tools Engineer")


def test_apple_parses_hydration_payload():
    payload = {"loaderData": {"search": {"totalRecords": 1, "searchResults": [{
        "positionId": "200612345", "postingTitle": "Software Engineering Internship",
        "transformedPostingTitle": "software-engineering-internship",
        "postDateInGMT": "2026-11-26T10:00:00.123Z", "jobSummary": "Build things.",
        "locations": [{"city": "Cupertino", "stateProvince": "California",
                       "countryName": "United States of America"}]}]}}}
    html = ("<script>window.__staticRouterHydrationData = JSON.parse("
            + json.dumps(json.dumps(payload)) + ");</script>")
    jobs, total, ok = apple.parse(html, {"slug": "apple"})
    assert ok and total == 1
    job = jobs[0]
    assert job.id == "apple:apple:200612345"
    assert job.location == "Cupertino, California, United States of America"
    assert job.url == "https://jobs.apple.com/en-us/details/200612345/software-engineering-internship"
    assert job.posted_at == "2026-11-26T10:00:00Z"


def test_apple_changed_shape_is_malformed():
    assert apple.parse("<html></html>", {"slug": "apple"})[2] is False


def test_atlassian_parses_listing():
    jobs = atlassian.parse([{
        "id": "26001", "title": "Software Engineer Intern, 2027 Summer U.S.",
        "locations": ["Seattle - United States -   Seattle, WA 98101 United States"],
        "overview": "<p>Hi</p>", "applyUrl": "https://careers.atlassian.com/jobs/26001",
    }], {"slug": "atlassian"})
    assert jobs[0].location == "Seattle, United States"
    assert jobs[0].url == "https://careers.atlassian.com/jobs/26001"
    assert atlassian.parse({"error": 1}, {"slug": "atlassian"}) is None
