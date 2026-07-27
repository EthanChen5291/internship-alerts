"""Oracle Recruiting Cloud (enterprise + bank tenants).

Per-tenant like Workday: each company has its own oraclecloud.com host and a
site number (CX_1, CX_2001, ... — captured by discovery, not assumed). Public
REST endpoint, browser-like headers, paginated by offset.
"""

from __future__ import annotations

from ..models import Fetch, Job, clean_listing
from ..net import Net

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
}

_PAGE_SIZE = 50
_MAX_JOBS = 200  # per keyword
# Like Workday, the keyword search is literal — "intern" alone drops co-ops.
_KEYWORDS = ("intern", "co-op")


def _posted(value) -> str | None:
    # Keep only real ISO-ish dates (YYYY-MM-...), ignore anything else.
    if isinstance(value, str) and len(value) >= 7 and value[:4].isdigit() and value[4] == "-":
        return value
    return None


async def fetch(company: dict, net: Net) -> Fetch:
    host = company["host"]
    site = company.get("site", "CX_1")
    tenant = company["slug"]
    url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    base = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job"

    jobs: dict[str, Job] = {}  # keyed by job id: the two keywords overlap
    complete = True
    for keyword in _KEYWORDS:
        exhausted = False
        for offset in range(0, _MAX_JOBS, _PAGE_SIZE):
            params = {
                "onlyData": "true",
                "expand": "requisitionList.secondaryLocations",
                "finder": f"findReqs;siteNumber={site},keyword={keyword},"
                          f"sortBy=POSTING_DATES_DESC,offset={offset}",
                "limit": str(_PAGE_SIZE),
            }
            data = await net.get_json(url, params=params, headers=HEADERS)
            items = clean_listing(data, "items")
            if items is None:
                break  # malformed 200 / error envelope: not an empty board
            requisitions = clean_listing(items[0], "requisitionList") if items else []
            if requisitions is None:
                break
            for r in requisitions:
                rid = r.get("Id")
                job = Job(
                    id=f"oracle:{tenant}:{rid}",
                    source="oracle",
                    company=company["name"],
                    company_slug=tenant,
                    title=(r.get("Title") or "").strip(),
                    location=(r.get("PrimaryLocation") or "—").strip() or "—",
                    url=f"{base}/{rid}",
                    posted_at=_posted(r.get("PostedDate")),
                )
                jobs.setdefault(job.id, job)
            if len(requisitions) < _PAGE_SIZE:
                exhausted = True
                break
            total = items[0].get("TotalJobsCount") if items else None
            if isinstance(total, int) and offset + len(requisitions) >= total:
                exhausted = True
                break
        if not exhausted:
            complete = False  # stopped at the cap with results still pending
    return Fetch(list(jobs.values()), complete=complete)
