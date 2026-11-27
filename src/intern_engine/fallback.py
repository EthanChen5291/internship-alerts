"""Personal-email fallback for an ATS that is blocking the engine (best-effort).

While a source is listed in KNOWN_OUTAGE_SOURCES (today: Workday, whose
Cloudflare has rejected the engine's client since 2026-11-16), the engine can't
see new roles on those boards. This module fills that gap for the fork owner's
own alert email only: it reads SimplifyJobs' public listings.json, keeps
roles hosted on the blocked ATS that pass this fork's own filters, and emails
the ones not already sent.

Nothing here touches the store, the README, the dashboard or the public list,
which stay employer-sourced as METHODOLOGY.md promises. Each email says the
roles came via SimplifyJobs.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime

import httpx

from . import config, filters, paths, personal_alerts

STATE_PATH = os.path.join(paths.DATA_DIR, "fallback_state.json")
_TIMEOUT = 30
_MAX_PER_EMAIL = 40
# The first run must not mail the whole backlog: only roles Simplify dated
# since the outage began go out; older ones are recorded as already seen.
_FIRST_RUN_SINCE = datetime(2026, 11, 16, tzinfo=UTC)
# Hosts that identify a role as living on each blocked ATS.
_HOSTS = {"workday": ("myworkdayjobs.com", "myworkdaysite.com")}


def outage_sources() -> set[str]:
    raw = os.environ.get("KNOWN_OUTAGE_SOURCES") or ""
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def _listing_urls(cycles: list[str]) -> list[str]:
    urls = []
    for cycle in cycles:
        m = re.fullmatch(r"Summer (\d{4})", cycle.strip())
        if m:
            urls.append(
                "https://raw.githubusercontent.com/SimplifyJobs/"
                f"Summer{m.group(1)}-Internships/dev/.github/scripts/listings.json"
            )
    return urls


def _norm_url(url: str) -> str:
    return re.sub(r"[?#].*$", "", (url or "").strip().lower()).rstrip("/")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("sent_ids"), list):
            return data
    except (OSError, ValueError):
        pass
    return {}


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True)
        f.write("\n")


def select(listings: list[dict], cfg: dict, outage: set[str], store_data: dict) -> list[dict]:
    """Roles on a blocked ATS that pass this fork's filters and aren't in the store."""
    hosts = tuple(h for src in outage for h in _HOSTS.get(src, ()))
    if not hosts:
        return []
    cycles = set(config.cycles(cfg))
    known_urls = {_norm_url(r.get("url") or "") for r in store_data.values()}
    known_pairs = {(_norm(r.get("company") or ""), _norm(r.get("title") or ""))
                   for r in store_data.values()}
    us, canada = config.want_us(cfg), config.want_canada(cfg)
    out = []
    for item in listings:
        url = item.get("url") or ""
        title = item.get("title") or ""
        company = item.get("company_name") or ""
        if not (item.get("active") and item.get("is_visible", True)):
            continue
        if not any(h in url.lower() for h in hosts):
            continue
        terms = [t for t in item.get("terms") or [] if t in cycles]
        if not terms:
            continue
        category = filters.categorize(title)
        if not filters.is_tech(title) or config.role_excluded(cfg, title, category):
            continue
        locations = [str(x) for x in item.get("locations") or []]
        if config.restrict_region(cfg) and locations and not any(
            filters.region_ok(loc, us, canada) for loc in locations
        ):
            continue
        if _norm_url(url) in known_urls or (_norm(company), _norm(title)) in known_pairs:
            continue
        posted = item.get("date_posted")
        out.append({
            "id": f"simplify:{item.get('id')}",
            "company": company,
            "title": title,
            "url": url,
            "season": terms[0],
            "location": "; ".join(locations[:3]) + (" +more" if len(locations) > 3 else ""),
            "category": category,
            "posted_at": (datetime.fromtimestamp(posted, UTC).strftime("%Y-%m-%d")
                          if isinstance(posted, (int, float)) else ""),
            "_posted_ts": posted if isinstance(posted, (int, float)) else 0,
        })
    out.sort(key=lambda r: -r["_posted_ts"])
    return out


def _fetch(url: str) -> list[dict]:
    response = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def run(store_data: dict) -> str:
    """Email new blocked-ATS roles found via SimplifyJobs. Returns a status line."""
    outage = outage_sources()
    if not outage & set(_HOSTS):
        return "no known outage"
    if not personal_alerts.email_configured():
        return "email not configured"
    cfg = config.load_config()
    listings: list[dict] = []
    for url in _listing_urls(config.cycles(cfg)):
        try:
            listings += _fetch(url)
        except Exception as exc:  # noqa: BLE001 - side channel, never fatal
            return f"Simplify fetch failed ({type(exc).__name__})"
    candidates = select(listings, cfg, outage, store_data)

    state = load_state()
    first_run = not state.get("seeded")
    sent = set(state.get("sent_ids") or [])
    fresh = [r for r in candidates if r["id"] not in sent]
    if first_run:
        cutoff = _FIRST_RUN_SINCE.timestamp()
        sent |= {r["id"] for r in fresh if r["_posted_ts"] < cutoff}
        fresh = [r for r in fresh if r["_posted_ts"] >= cutoff]

    shown = fresh[:_MAX_PER_EMAIL]
    status = f"{len(candidates)} matching, {len(fresh)} new"
    if shown:
        records = [{k: v for k, v in r.items() if not k.startswith("_")} for r in shown]
        subject, html = personal_alerts.build_email(records)
        src = ", ".join(sorted(s.title() for s in outage & set(_HOSTS)))
        html = html.replace(
            "NEW INTERNSHIP ALERT",
            f"NEW {src.upper()} ROLES · VIA SIMPLIFYJOBS (WHILE {src.upper()} BLOCKS THE SCRAPER)",
            1,
        )
        try:
            personal_alerts._post_email(f"[{src} via Simplify] {subject}", html)
        except Exception as exc:  # noqa: BLE001 - stays unsent, retried next run
            save_state({**state, "sent_ids": sorted(sent), "seeded": True})
            return status + f", email failed ({type(exc).__name__})"
        sent |= {r["id"] for r in shown}
        status += f", emailed {len(shown)}"
    # Forget ids that left the listings so the file doesn't grow forever.
    live = {f"simplify:{i.get('id')}" for i in listings}
    save_state({"sent_ids": sorted(sent & live) if listings else sorted(sent),
                "seeded": True,
                "updated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")})
    return status
