"""Recruitee offers API ({slug}.recruitee.com/api/offers/): public, no auth.

Offers include their full description HTML, so sponsorship classification is
free for this source.
"""

from __future__ import annotations

from ..models import Fetch, Job, clean_listing
from ..net import Net

URL = "https://{slug}.recruitee.com/api/offers/"


def _location(offer: dict) -> str:
    text = (offer.get("location") or "").strip()
    if text:
        return text
    parts = [p for p in (offer.get("city"), offer.get("country")) if p]
    return ", ".join(parts) or "—"


async def fetch(company: dict, net: Net) -> Fetch:
    slug = company["slug"]
    data = await net.get_json(URL.format(slug=slug))
    listing = clean_listing(data, "offers")

    jobs = []
    for offer in (listing or []):
        jobs.append(
            Job(
                id=f"recruitee:{slug}:{offer.get('id')}",
                source="recruitee",
                company=company["name"],
                company_slug=slug,
                title=(offer.get("title") or "").strip(),
                location=_location(offer),
                url=offer.get("careers_url") or "",
                posted_at=offer.get("created_at"),
                description=offer.get("description"),
            )
        )
    return Fetch.board(jobs, isinstance(listing, list))
