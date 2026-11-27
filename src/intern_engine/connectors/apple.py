"""Apple Jobs: the public search page filtered to the Internships team.

jobs.apple.com renders server-side and embeds its results as
`window.__staticRouterHydrationData = JSON.parse("...")`; the payload's
`loaderData.search` holds `searchResults` (20 per page) and `totalRecords`.
One fixed endpoint, newest first, worldwide (the region filter decides).
"""

from __future__ import annotations

import json

from ..models import INCOMPLETE_CAPPED, INCOMPLETE_MALFORMED, Fetch, Job, source_board_key
from ..net import Net

URL = "https://jobs.apple.com/en-us/search"
JOB_URL = "https://jobs.apple.com/en-us/details/{pid}/{slug}"
_KEY = "__staticRouterHydrationData = JSON.parse("
_MAX_PAGES = 25


def _search(html: str):
    i = html.find(_KEY)
    if i < 0:
        return None
    try:
        raw, _ = json.JSONDecoder().raw_decode(html[i + len(_KEY):])
        search = json.loads(raw)["loaderData"]["search"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(search, dict) or not isinstance(search.get("searchResults"), list):
        return None
    return search


def _location(locations) -> str:
    out = []
    for loc in locations or []:
        if not isinstance(loc, dict):
            continue
        parts = [loc.get("city"), loc.get("stateProvince"), loc.get("countryName")]
        text = ", ".join(p for p in parts if p) or loc.get("name") or ""
        if text:
            out.append(text)
    return "; ".join(out) or "—"


def parse(html: str, company: dict) -> tuple[list[Job], int | None, bool]:
    search = _search(html)
    if search is None:
        return [], None, False
    jobs = []
    for r in search["searchResults"]:
        pid = str(r.get("positionId") or r.get("id") or "").strip()
        title = str(r.get("postingTitle") or "").strip()
        if not pid or not title:
            continue
        jobs.append(Job(
            id=f"apple:apple:{pid}",
            source="apple",
            company="Apple",
            company_slug="apple",
            title=title,
            location=_location(r.get("locations")),
            url=JOB_URL.format(pid=pid, slug=r.get("transformedPostingTitle") or "role"),
            posted_at=(str(r["postDateInGMT"])[:19] + "Z") if r.get("postDateInGMT") else None,
            description=(r.get("jobSummary") or "").strip() or None,
            board_key=source_board_key(company, "apple", "apple"),
        ))
    total = search.get("totalRecords")
    return jobs, total if isinstance(total, int) else None, True


async def fetch(company: dict, net: Net) -> Fetch:
    jobs: list[Job] = []
    seen: set[str] = set()
    for page in range(1, _MAX_PAGES + 1):
        html = await net.get_text(URL, params={
            "team": "internships-STDNT-INTRN", "sort": "newest", "page": page,
        })
        page_jobs, total, ok = parse(html, company)
        if not ok:
            return Fetch(jobs, complete=False, incomplete_reason=INCOMPLETE_MALFORMED)
        fresh = [j for j in page_jobs if j.id not in seen]
        seen.update(j.id for j in fresh)
        jobs += fresh
        if not fresh or (total is not None and len(jobs) >= total):
            return Fetch(jobs, complete=True)
    return Fetch(jobs, complete=False, incomplete_reason=INCOMPLETE_CAPPED)
