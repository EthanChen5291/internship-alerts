"""Atlassian Careers: one public JSON list of every open posting.

www.atlassian.com/endpoint/careers/listings returns the whole board (~200
roles) as a list of {id, title, locations[], category, overview,
responsibilities, qualifications, applyUrl}. No posting dates are exposed.
"""

from __future__ import annotations

import re

from ..models import INCOMPLETE_MALFORMED, Fetch, Job, source_board_key
from ..net import Net

URL = "https://www.atlassian.com/endpoint/careers/listings"


def _location(raw) -> str:
    # "Seattle - United States -   Seattle, WA 98101 United States" -> "Seattle, United States"
    out = []
    for loc in raw or []:
        parts = [p.strip() for p in str(loc).split(" - ") if p.strip()]
        out.append(", ".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else ""))
    return "; ".join(p for p in out if p) or "—"


def parse(data, company: dict) -> list[Job] | None:
    if not isinstance(data, list):
        return None
    jobs = []
    for r in data:
        if not isinstance(r, dict) or not r.get("id") or not r.get("title"):
            continue
        text = " ".join(str(r.get(k) or "") for k in ("overview", "responsibilities", "qualifications"))
        jobs.append(Job(
            id=f"atlassian:atlassian:{r['id']}",
            source="atlassian",
            company="Atlassian",
            company_slug="atlassian",
            title=str(r["title"]).strip(),
            location=_location(r.get("locations")),
            url=str(r.get("applyUrl") or f"https://www.atlassian.com/company/careers/details/{r['id']}"),
            description=re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip() or None,
            board_key=source_board_key(company, "atlassian", "atlassian"),
        ))
    return jobs


async def fetch(company: dict, net: Net) -> Fetch:
    jobs = parse(await net.get_json(URL), company)
    if jobs is None:
        return Fetch([], complete=False, incomplete_reason=INCOMPLETE_MALFORMED)
    return Fetch(jobs, complete=True)
