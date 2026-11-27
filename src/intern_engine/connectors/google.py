"""Google Careers: the public results page, which embeds its job list as data.

google.com/about/careers/applications/jobs/results renders server-side and
carries the page's results in an `AF_initDataCallback({key: 'ds:1', ...})`
block: `[[job, ...], null, total, page_size]`. Each job is a positional array:
0 id, 1 title, 3/4/10/19 description and qualification HTML, 7 company name
(Google, DeepMind, Waymo...), 9 locations, 12 [created epoch seconds, nanos].

One fixed endpoint (not per-tenant), filtered server-side to the "Intern &
Apprentice" level and sorted newest first.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from ..models import (
    INCOMPLETE_CAPPED,
    INCOMPLETE_MALFORMED,
    Fetch,
    Job,
    source_board_key,
)
from ..net import Net

URL = "https://www.google.com/about/careers/applications/jobs/results"
JOB_URL = "https://www.google.com/about/careers/applications/jobs/results/{id}-{slug}"
_MAX_PAGES = 30  # 20 per page; Google's intern+apprentice list runs ~50-400
_BLOCK = re.compile(r"AF_initDataCallback\(\{key: 'ds:1',[^\[]*?data:")


def _results(html: str):
    """The ds:1 payload, or None if the page no longer has that shape."""
    m = _BLOCK.search(html)
    if not m:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(html[m.end():])
    except ValueError:
        return None
    if not isinstance(data, list) or not data or not isinstance(data[0], list | type(None)):
        return None
    return data


def _text(value) -> str:
    if isinstance(value, list) and len(value) > 1 and isinstance(value[1], str):
        return re.sub(r"<[^>]+>", " ", value[1])
    return ""


def _location(raw) -> str:
    names = [loc[0] for loc in raw or [] if isinstance(loc, list) and loc and loc[0]]
    return "; ".join(names) or "—"


def _posted(raw) -> str | None:
    if isinstance(raw, list) and raw and isinstance(raw[0], int | float):
        return datetime.fromtimestamp(raw[0], UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def parse(html: str, company: dict) -> tuple[list[Job], int | None, bool]:
    """(jobs on this page, server total, ok)."""
    data = _results(html)
    if data is None:
        return [], None, False
    jobs = []
    for row in data[0] or []:
        if not (isinstance(row, list) and len(row) > 12 and row[0] and row[1]):
            continue
        title = str(row[1]).strip()
        employer = str(row[7] or "Google").strip()
        description = " ".join(_text(row[i]) for i in (3, 4, 10, 19) if i < len(row))
        jobs.append(Job(
            id=f"google:google:{row[0]}",
            source="google",
            company=employer,
            company_slug="google",
            title=title,
            location=_location(row[9]),
            url=JOB_URL.format(id=row[0], slug=_slug(title)),
            posted_at=_posted(row[12]),
            description=re.sub(r"\s+", " ", description).strip() or None,
            board_key=source_board_key(company, "google", "google"),
        ))
    total = data[2] if len(data) > 2 and isinstance(data[2], int) else None
    return jobs, total, True


async def fetch(company: dict, net: Net) -> Fetch:
    jobs: list[Job] = []
    seen: set[str] = set()
    for page in range(1, _MAX_PAGES + 1):
        html = await net.get_text(URL, params={
            "target_level": "INTERN_AND_APPRENTICE", "sort_by": "date", "page": page,
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
