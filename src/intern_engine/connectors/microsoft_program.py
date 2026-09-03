"""Microsoft Explore postings embedded on Microsoft's official program page."""

from __future__ import annotations

import html
import re

from .. import programs
from ..models import INCOMPLETE_MALFORMED, Fetch, Job, source_board_key
from ..net import Net

_CARD = re.compile(
    r'<div class="careers-joblistResponsive-columnList[^>]*>(.*?)(?='
    r'<div class="careers-joblistResponsive-columnList|$)',
    re.IGNORECASE | re.DOTALL,
)


def _field(card: str, class_name: str, tag: str = r"(?:div|h3)") -> str:
    found = re.search(
        rf'<{tag}[^>]*class="[^"]*{class_name}[^"]*"[^>]*>(.*?)</{tag}>',
        card,
        re.IGNORECASE | re.DOTALL,
    )
    if not found:
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", found.group(1)))).strip()


async def fetch(company: dict, net: Net) -> Fetch:
    url = company["url"]
    page = await net.get_text(url, headers={"User-Agent": "Mozilla/5.0"})
    if "careers-joblistResponsive-main" not in page:
        return Fetch([], complete=False, incomplete_reason=INCOMPLETE_MALFORMED)

    jobs: list[Job] = []
    for card_match in _CARD.finditer(page):
        card = card_match.group(1)
        title = _field(card, "careers-joblistResponsive-subheading", "h3")
        if not programs.match(company["name"], title):
            continue
        link = re.search(
            r'<a[^>]+href="([^"]+)"[^>]+class="[^"]*careers-joblistResponsive-button',
            card,
            re.IGNORECASE,
        )
        job_url = html.unescape(link.group(1)) if link else ""
        external = re.search(r"/job/(\d+)", job_url)
        if not job_url or not external:
            continue
        jobs.append(Job(
            id=f"microsoft_program:{company['slug']}:{external.group(1)}",
            source="microsoft_program",
            company=company["name"],
            company_slug=company["slug"],
            title=title,
            location=_field(card, "careers-joblistResponsive-primarylocation") or "—",
            url=job_url,
            posted_at=_field(card, "careers-joblistResponsive-postdate") or None,
            board_key=source_board_key(company, "microsoft_program"),
        ))
    return Fetch(jobs, complete=True)
