"""The watcher + spotter.

One async pass per run: quarantine-check every tracked company (circuit
breaker), fetch the healthy ones concurrently (global + per-host concurrency
caps), normalize into one shape, keep the roles that match the configured
scope, de-duplicate across sources, enrich the keepers with posting text
(sponsorship classification + date backfill), merge into the store (detecting
what's new and what closed), and record run metrics + a history line.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import statistics
import time
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import httpx

from . import (
    config,
    enrich,
    filters,
    health,
    models,
    names,
    observe,
    paths,
    quality,
    sponsorship,
    store,
    trends,
)
from .connectors import (
    amazon,
    ashby,
    breezy,
    eightfold,
    greenhouse,
    lever,
    oracle,
    recruitee,
    rippling,
    smartrecruiters,
    workable,
    workday,
)
from .net import HostLimiter, Net

CONNECTORS = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workday": workday.fetch,
    "amazon": amazon.fetch,
    "oracle": oracle.fetch,
    "rippling": rippling.fetch,
    "workable": workable.fetch,
    "breezy": breezy.fetch,
    "recruitee": recruitee.fetch,
    "eightfold": eightfold.fetch,
}

GLOBAL_CONCURRENCY = 32
PER_HOST_CONCURRENCY = 8
USER_AGENT = f"intern-engine/3.0 (+https://github.com/{config.repo_slug()})"


def _load_companies() -> list[dict]:
    with open(paths.COMPANIES_PATH, encoding="utf-8") as f:
        return json.load(f)


async def _fetch_one(company: dict, net: Net):
    """Return (company, Fetch, error); never raises (failures are isolated).

    A connector may return a bare list (a whole-board read, always complete) or
    a `models.Fetch` carrying its own completeness verdict — `Fetch.of` unifies
    them. On error the result is an EMPTY, INCOMPLETE fetch, which is what stops
    a failed request from reading as "this company has no roles any more".
    """
    fetch = CONNECTORS.get(company.get("ats"))
    if fetch is None:
        return company, models.Fetch(complete=False), f"no connector for {company.get('ats')}"
    try:
        return company, models.Fetch.of(await fetch(company, net)), None
    except Exception as exc:  # noqa: BLE001 — one bad endpoint must not stop the run
        return company, models.Fetch(complete=False), f"{type(exc).__name__}: {exc}"


async def _fetch_all(companies: list[dict], enrich_after):
    """Fetch every company, then run `enrich_after(results, net)` on the same
    client session so enrichment reuses connections instead of reopening them."""
    limiter = HostLimiter(PER_HOST_CONCURRENCY)
    gate = asyncio.Semaphore(GLOBAL_CONCURRENCY)
    proxy = os.environ.get("WORKDAY_PROXY") or None

    common = dict(
        limits=httpx.Limits(max_connections=64, max_keepalive_connections=32),
        timeout=httpx.Timeout(20.0, connect=10.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )

    async with httpx.AsyncClient(**common) as client:
        default_net = Net(client, limiter)
        workday_client = httpx.AsyncClient(proxy=proxy, **common) if proxy else None
        workday_net = Net(workday_client, limiter) if workday_client else default_net

        async def worker(company: dict):
            net = workday_net if company.get("ats") in ("workday", "oracle") else default_net
            async with gate:
                return await _fetch_one(company, net)

        try:
            results = await asyncio.gather(*(worker(c) for c in companies))
            enrich_result = await enrich_after(results, default_net, workday_net)
            return results, enrich_result
        finally:
            if workday_client is not None:
                await workday_client.aclose()


def _norm_location(location: str) -> str:
    """A location reduced to its comparable core, for dedup only.

    Punctuation and casing are noise. Work mode is NOT: an employer that posts
    "Austin, TX" and "Austin, TX (Remote)" is offering two different jobs, and
    stripping the remote/hybrid marker merged them. Keeping the mode in the key
    means two postings only match when they really describe the same place on
    the same terms.
    """
    low = (location or "").lower()
    mode = ""
    if re.search(r"\bremote\b", low):
        mode = " remote"
    elif re.search(r"\bhybrid\b", low):
        mode = " hybrid"
    low = re.sub(r"\(remote\)|\bremote\b|\bhybrid\b|\bon[\s-]?site\b", " ", low)
    return re.sub(r"[^a-z0-9]+", " ", low).strip() + mode


def _dedup(jobs: list) -> list:
    """Collapse the same role seen more than once, across DIFFERENT sources.

    The only duplicate we can actually prove is one posting syndicated to two
    ATS: same company, same title, same place, two boards. That collapses, and
    the copy carrying a real posted date wins.

    Two requisitions on the SAME board are never merged, even when title and
    location match. Copart really did open JR109672 and JR109673 — "Software
    Engineering Intern, Dallas" twice — and an employer that opens two reqs is
    offering two jobs. The board already told us they're distinct by giving
    them distinct ids; second-guessing that deletes a real opening.
    """
    def key_of(job):
        return (
            job.company.lower().strip(),
            re.sub(r"[^a-z0-9]+", "", job.title.lower()),
            _norm_location(job.location),
        )

    # Group first, then decide. Only ONE pattern is provably a duplicate:
    # every source holds exactly one requisition for the key — the classic
    # single posting syndicated across boards. That collapses to the best copy
    # (a real posting date wins). The moment ANY source lists two or more reqs
    # under the key, identity is ambiguous — we can't tell which copy on the
    # other board mirrors which req — and deleting a real opening is worse
    # than showing a possible duplicate, so everything is kept.
    groups: dict[tuple[str, str, str], dict[str, list]] = {}
    for job in jobs:
        groups.setdefault(key_of(job), {}).setdefault(job.source, []).append(job)

    unique = []
    for by_source in groups.values():
        if len(by_source) > 1 and all(len(g) == 1 for g in by_source.values()):
            best = max(by_source.values(),
                       key=lambda g: any(j.posted_at for j in g))
            unique.extend(best)
        else:
            for group in by_source.values():
                unique.extend(group)
    return unique


def _keep_matching(results, cfg, blocklist, existing=None) -> tuple[list, set[str], int, Counter]:
    """Apply every scope filter; return (kept jobs, succeeded keys, complete
    keys, errors, errors by ats, dropped-no-year count, dropped-off-cycle count).

    `succeeded` is every company we got a usable response from (the fetch-health
    stat). `complete` is the subset whose response was provably the WHOLE list —
    only those may close roles. See `models.Fetch`.

    `existing` (the store) makes cycle assignment sticky for yearless titles: a
    season already on record — set by an earlier inference or verified from the
    posting's own text — is adopted as-is, never re-derived. Without this, a
    text-verified season would be re-guessed every run, and a role would flip
    "closed" the day its posting outgrew the inference recency window.
    """
    cycles = config.cycles(cfg)
    tech_only = cfg.get("role_scope", "tech") == "tech"
    restrict = config.restrict_region(cfg)
    wants_us = config.want_us(cfg)
    wants_canada = config.want_canada(cfg)
    include_intl = config.include_international(cfg)
    allowlist_only = config.allowlist_only(cfg)
    infer = config.infer_undated(cfg)
    infer_age = config.infer_max_age_days(cfg)
    max_age = config.max_age_days(cfg)
    cutoff = (
        (datetime.now(UTC) - timedelta(days=max_age)).strftime("%Y-%m-%d")
        if max_age else None
    )

    existing = existing or {}
    kept = []
    succeeded: set[str] = set()
    complete: set[str] = set()
    # Every job id a successful fetch returned, in scope or not. A role we saw
    # and REJECTED (wrong country, wrong cycle, not tech) must leave the list
    # even when the snapshot was capped: "we shouldn't have listed this" is a
    # verdict we can reach on our own, unlike "the employer took it down".
    seen_ids: set[str] = set()
    errors = 0
    errors_by_ats: Counter = Counter()
    dropped_no_year = 0  # tech internships we skip only because the title has no year
    dropped_offcycle = 0  # roles whose recorded season is a verified off-cycle label
    for company, result, error in results:
        jobs = result.jobs
        if error is not None:
            errors += 1
            errors_by_ats[company.get("ats", "?")] += 1
            continue
        key = f"{company['ats']}:{company['slug']}"
        succeeded.add(key)
        if result.complete:
            complete.add(key)
        if quality.is_blocked(company["name"], blocklist):
            continue
        if allowlist_only and not quality.is_recognized(company["name"]):
            continue
        for job in jobs:
            seen_ids.add(job.id)
            if not filters.is_internship(job.title):
                continue
            if tech_only and not filters.is_tech(job.title):
                continue
            season = filters.detect_season(job.title, cycles)
            inferred = False
            if season is None:
                if filters.states_explicit_year(job.title):
                    # The title names a year we don't track ("Summer 2026
                    # Intern"): a hard verdict. Neither a stored season nor a
                    # posting-date inference may rescue it.
                    dropped_offcycle += 1
                    continue
                prior = existing.get(job.id) or {}
                prior_season = prior.get("season")
                if prior_season in cycles:
                    season = prior_season  # sticky (see docstring)
                    inferred = bool(prior.get("season_inferred"))
                elif filters.is_cycle_label(prior_season):
                    # A recorded off-cycle label ("Summer 2026") is a settled
                    # text-verified verdict: the role stays off the list, and
                    # is never re-inferred or re-enriched.
                    dropped_offcycle += 1
                    continue
                elif infer and filters.cycle_unstated_ok(
                        job.title, job.posted_at, infer_age):
                    # Nobody stated a cycle. We used to guess one from the
                    # posting month; that guess was measured wrong (see
                    # filters.cycle_unstated_ok). The role is recent and real,
                    # so it stays — under a label that claims nothing. If its
                    # posting text names a cycle, enrichment promotes it.
                    season = filters.NOT_STATED
                    inferred = True
            if season is None:
                dropped_no_year += 1
                continue
            in_region = filters.region_ok(job.location, wants_us, wants_canada)
            if restrict and not in_region and not include_intl:
                continue
            loc = (job.location or "").strip()
            if not in_region and (not loc or loc == "—"):
                continue  # out-of-region roles need a real location
            posted_day = (job.posted_at or "")[:10]
            # The age cutoff exists to drop stale evergreen listings whose
            # recency was the ONLY evidence for their cycle. When the employer
            # stated the cycle themselves, age proves nothing — Amazon's
            # "Software Development Engineer Internship - Fall 2026 (US)" was
            # posted early and is still open and still for Fall 2026. Closing it
            # for being old was us overriding what the company wrote.
            if cutoff and posted_day and posted_day < cutoff and inferred:
                continue
            job.season = season
            job.season_inferred = inferred
            if not inferred:
                # A title can state MORE than one tracked cycle ("Fall 2026/
                # Summer 2027"); keep the full set so neither cycle loses it.
                stated_all = filters.detect_seasons(job.title, cycles)
                if len(stated_all) > 1:
                    job.seasons = stated_all
            job.category = filters.categorize(job.title)
            job.company = names.display(job.company, job.company_slug)
            if job.posted_at and not job.posted_at_source:
                job.posted_at_source = models.date_source(job.posted_at)
            kept.append(job)
    return (kept, succeeded, complete, seen_ids, errors, errors_by_ats,
            dropped_no_year, dropped_offcycle)


def _migrate_date_sources(existing: dict) -> None:
    """Stamp legacy records' date precision from the value's shape.

    Records written before posted_at_source existed rank as precision 0, so ANY
    labeled incoming date would "upgrade" over them and shift a frozen Posted
    date. Deriving the label once from the stored value gives real timestamps
    exact rank and date-only ones their own — after which the normal
    only-upgrade rule protects them.
    """
    for r in existing.values():
        if r.get("posted_at") and not r.get("posted_at_source"):
            r["posted_at_source"] = models.date_source(r["posted_at"])


def _retire_guessed_cycles(existing: dict, cfg: dict) -> int:
    """Strip cycle labels that came from the retired posting-date guess.

    Records written before `cycle_unstated_ok` carry a real cycle label with
    `season_inferred=True` — e.g. "Summer 2027" derived from nothing but the
    month the role was posted. The sticky-season path in `_keep_matching`
    treats any stored label that's in `cycles` as authoritative, so without
    this sweep those fabricated labels would survive forever and the fix would
    only apply to roles discovered afterwards.

    `season_inferred=True` is precisely the marker for "no employer said this"
    — enrichment clears the flag the moment a posting's text confirms a cycle
    — so every record still carrying it is reset to NOT_STATED and re-enriched.
    """
    cycles = set(config.cycles(cfg))
    n = 0
    for r in existing.values():
        if r.get("season_inferred") and r.get("season") in cycles:
            r["season"] = filters.NOT_STATED
            r.pop("seasons", None)
            # Force one re-read: the posting may well state a cycle that the
            # old (tag-blind) text reader missed.
            r.pop("enriched_at", None)
            r.pop("classifier_v", None)
            n += 1
    return n


def _close_out_of_scope(existing: dict, cfg: dict) -> int:
    """Close OPEN records whose stored location fails the region filter.

    Scope is our own verdict — it needs no fetch evidence. Without this sweep,
    a foreign role admitted under an older filter could hide forever on a
    capped board: never re-fetched (beyond the result cap), so never in
    seen_ids, so never closable. Medtronic's Lausanne role did exactly that.
    Region only, deliberately: it's the one check that's deterministic from
    the record alone.
    """
    if not config.restrict_region(cfg) or config.include_international(cfg):
        return 0
    ts = store.now_iso()
    wants_us, wants_canada = config.want_us(cfg), config.want_canada(cfg)
    n = 0
    for r in existing.values():
        if not r.get("is_open"):
            continue
        loc = (r.get("location") or "").strip()
        if loc and loc != "—" and not filters.region_ok(loc, wants_us, wants_canada):
            r.update(is_open=False, closed_at=ts, closed_reason="out-of-scope")
            r.pop("missing_streak", None)
            n += 1
    return n


def run_update() -> tuple[dict, dict, list[str]]:
    cfg = config.load_config()
    blocklist = quality.load_blocklist()
    companies = _load_companies()
    existing = store.load(paths.JOBS_PATH)
    _migrate_date_sources(existing)
    _retire_guessed_cycles(existing, cfg)
    _close_out_of_scope(existing, cfg)

    health_data = health.load()
    active, benched = health.partition(companies, health_data)

    started = time.monotonic()
    kept: list = []
    enriched_ids: set[str] = set()
    detail_fetches = 0

    async def _enrich_stage(results, net, workday_net):
        """Filter first (cheap, sync), then enrich only the keepers."""
        nonlocal kept
        (kept, succeeded, complete, seen_ids, errors, errors_by_ats, no_year,
         offcycle_sticky) = _keep_matching(results, cfg, blocklist, existing)
        kept = _dedup(kept)
        # Workday/Oracle enrichment goes through the same proxied client as fetch.
        wd_jobs = [j for j in kept if j.source in ("workday", "oracle")]
        other = [j for j in kept if j.source not in ("workday", "oracle")]
        ids_a, n_a = await enrich.enrich_jobs(other, existing, net)
        ids_b, n_b = await enrich.enrich_jobs(wd_jobs, existing, workday_net)
        # Enrichment may have replaced an inferred cycle with the one the
        # posting text states; anything now off-cycle leaves the list — and the
        # verdict is written into the store so the role never re-enters (or
        # pays another detail fetch) on later runs.
        cycles = config.cycles(cfg)
        ts = store.now_iso()
        offcycle = offcycle_sticky
        still = []
        for job in kept:
            # NOT_STATED survives alongside the tracked cycles: it isn't a
            # cycle claim, it's the absence of one, and those roles have their
            # own section. Only a real OFF-cycle label ("Summer 2026") drops.
            if job.season in cycles or job.season == filters.NOT_STATED:
                still.append(job)
                continue
            offcycle += 1
            record = existing.get(job.id)
            if record is None:
                record = {
                    k: v for k, v in asdict(job).items()
                    if k not in models.TRANSIENT_FIELDS
                }
                record.update(first_seen_at=ts, last_seen_at=ts,
                              is_open=False, closed_at=ts)
                existing[job.id] = record
            else:
                record["season"] = job.season
                record["season_inferred"] = False
            record["enriched_at"] = ts  # settled: never fetch this posting again
        kept = still
        return (succeeded, complete, seen_ids, errors, errors_by_ats,
                ids_a | ids_b, n_a + n_b, no_year, offcycle)

    results, (succeeded, complete_keys, seen_ids, errors, errors_by_ats,
              enriched_ids, detail_fetches, no_year, offcycle) = asyncio.run(
        _fetch_all(active, _enrich_stage)
    )

    for company, _result, error in results:
        health.record(health_data, company, error)
    health.save(health_data)

    rows = []
    for job in kept:
        row = asdict(job)
        for field in models.TRANSIENT_FIELDS:
            row.pop(field, None)
        rows.append(row)

    # Closure uses `complete_keys`, not `succeeded`: a capped or truncated
    # response is a successful fetch that still doesn't prove a role is gone.
    new_ids = store.upsert(existing, rows, complete_keys, enriched_ids,
                           seen_ids=seen_ids,
                           classifier_version=sponsorship.VERSION)
    purged = store.purge(existing)
    store.save(paths.JOBS_PATH, existing)

    # Record the real posted dates we saw straight from the ATS. This is the
    # engine's own ground truth for the Drop Radar — it accrues every run and
    # eventually replaces the outside reference dataset entirely.
    observe.record_run(existing)

    stats = _build_stats(
        companies, benched, succeeded, complete_keys, errors, errors_by_ats, kept,
        existing, new_ids, len(enriched_ids), detail_fetches, purged,
        round(time.monotonic() - started, 1), no_year, offcycle,
    )
    _write_stats(stats)
    _append_history(stats)
    return stats, existing, new_ids


def _parse_iso(value: str) -> datetime | None:
    """Always returns a UTC-aware datetime: ATS feeds mix offset-less strings
    and date-only strings with full `Z`/`±HH:MM` timestamps, and one naive
    value next to an aware one makes the subtraction below raise TypeError."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _is_exact_timestamp(value: str) -> bool:
    """True when a posted_at carries a real clock time, not just a date.

    Most ATS feeds give a bare date (or a relative "3 days ago" we resolve to
    midnight). Measuring pickup speed in MINUTES against an assumed midnight
    invents up to 24 hours of latency that never happened, so those roles are
    excluded from the metric rather than silently inflating it.
    """
    dt = _parse_iso(value)
    if dt is None:
        return False
    if len(value) <= 10:  # "2026-07-15" — a date, no time at all
        return False
    return not (dt.hour == 0 and dt.minute == 0 and dt.second == 0)


def _detection_latency(existing: dict, window_days: int = 7,
                       now: datetime | None = None) -> dict:
    """How fast we pick up newly published roles, in minutes.

    Two things this deliberately does NOT do, because the earlier version did
    both and reported a ~997-minute median off an hourly schedule:

      - `window_days` bounds how recently the role was PUBLISHED, not how big
        a delay we're willing to count. Bounding the delay instead meant every
        historical backfill under the ceiling counted as a live detection.
      - Date-only timestamps are excluded entirely (see _is_exact_timestamp);
        against an assumed midnight they contribute fake hours.

    The result is a smaller sample measuring one honest thing. p95 ships next to
    p50 because a median alone hides the tail that actually costs applicants.
    """
    now = now or datetime.now(UTC)
    published_after = now - timedelta(days=window_days)
    deltas = []
    for record in existing.values():
        posted, seen = record.get("posted_at"), record.get("first_seen_at")
        if not posted or not seen or not _is_exact_timestamp(posted):
            continue
        posted_dt, seen_dt = _parse_iso(posted), _parse_iso(seen)
        if not posted_dt or not seen_dt or posted_dt < published_after:
            continue
        minutes = (seen_dt - posted_dt).total_seconds() / 60
        if minutes >= 0:
            deltas.append(minutes)
    deltas.sort()
    return {
        "median_minutes": round(statistics.median(deltas), 1) if deltas else None,
        "p95_minutes": (
            round(deltas[min(int(len(deltas) * 0.95), len(deltas) - 1)], 1)
            if deltas else None
        ),
        "sample_size": len(deltas),
        "window_days": window_days,
        "basis": "roles published in the window with an exact source timestamp",
    }


def _build_stats(companies, benched, succeeded, complete_keys, errors, errors_by_ats,
                 kept, existing, new_ids, enriched, detail_fetches, purged, duration,
                 dropped_no_year=0, dropped_offcycle=0) -> dict:
    open_records = [r for r in existing.values() if r.get("is_open")]
    attempted = len(companies) - len(benched)
    dated = sum(1 for r in open_records if r.get("posted_at"))
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": duration,
        "companies_total": len(companies),
        "companies_by_source": dict(Counter(c["ats"] for c in companies)),
        "quarantined": len(benched),
        "fetched_ok": len(succeeded),
        "fetch_errors": errors,
        "errors_by_source": dict(errors_by_ats),
        # Two rates, because they answer different questions and only quoting
        # the first one overstates coverage: "of the boards we attempted this
        # run" vs "of every board on the registry" (quarantined ones included).
        "fetch_success_rate": round(len(succeeded) / max(attempted, 1), 3),
        "fetch_success_rate_registry": round(len(succeeded) / max(len(companies), 1), 3),
        # Boards whose response was provably the complete list. Only these are
        # allowed to close a role; the rest may have been truncated.
        "snapshots_complete": len(complete_keys),
        "snapshots_partial": len(succeeded) - len(complete_keys),
        # `roles_matched` is a FETCH number: what this run's responses yielded.
        # Everything below it describes the STORE — the roles actually open and
        # published. The two differ whenever a capped snapshot kept a role we
        # didn't re-see, so they must not be mixed: breaking down `open_total`
        # by a fetch-time count made Summer read 77 against a published 78.
        "roles_matched": len(kept),
        "dropped_no_year_in_title": dropped_no_year,
        "dropped_offcycle_by_text": dropped_offcycle,
        "roles_cycle_inferred": sum(1 for r in open_records if r.get("season_inferred")),
        "roles_by_source": dict(Counter(r.get("source") for r in open_records)),
        # Multi-cycle postings count once per cycle they state, matching how
        # they render — the primary-season-only count under-reported them.
        "roles_by_cycle": dict(Counter(
            cyc for r in open_records
            for cyc in (r.get("seasons") or [r.get("season")]) if cyc
        )),
        "roles_by_region": dict(Counter(
            "US" if filters.is_united_states(r.get("location") or "") else "International"
            for r in open_records
        )),
        "sponsorship_counts": dict(Counter(
            r.get("sponsorship", "unknown") for r in open_records
        )),
        "posted_date_coverage": round(dated / max(len(open_records), 1), 3),
        "enriched_this_run": enriched,
        "enrichment_detail_fetches": detail_fetches,
        "purged_this_run": purged,
        "new_this_run": len(new_ids),
        "open_total": len(open_records),
        "detection_latency": _detection_latency(existing),
        "posting_lifetime": dict(zip(
            ("median_days", "sample_size"), trends.median_days_open(existing),
            strict=True,
        )),
    }


def restat(existing: dict, stats: dict) -> dict:
    """Recompute the store-derived counts in `stats` from the current store.

    Two things produce numbers here: this run's FETCH (roles matched, per-source
    hit counts, error rates) and the resulting STORE (what's open, by cycle, by
    sponsorship). Only the store half can be recalculated later, and it has to
    be — after `run.py render` rewrites cycles, the published stats otherwise
    still describe the dataset from before the audit.

    Fetch metrics are deliberately left alone; inventing them would be worse
    than showing the last real run's.
    """
    stats = dict(stats)
    open_records = [r for r in existing.values() if r.get("is_open")]
    dated = sum(1 for r in open_records if r.get("posted_at"))
    stats.update({
        "open_total": len(open_records),
        "roles_by_cycle": dict(Counter(
            cyc for r in open_records
            for cyc in (r.get("seasons") or [r.get("season")]) if cyc
        )),
        "roles_cycle_inferred": sum(1 for r in open_records if r.get("season_inferred")),
        "roles_by_source": dict(Counter(r.get("source") for r in open_records)),
        "roles_by_region": dict(Counter(
            "US" if filters.is_united_states(r.get("location") or "") else "International"
            for r in open_records
        )),
        "sponsorship_counts": dict(Counter(
            r.get("sponsorship", "unknown") for r in open_records
        )),
        "posted_date_coverage": round(dated / max(len(open_records), 1), 3),
        "detection_latency": _detection_latency(existing),
        "posting_lifetime": dict(zip(
            ("median_days", "sample_size"), trends.median_days_open(existing),
            strict=True,
        )),
        "stats_basis": "counts recomputed from the store; fetch metrics from the last run",
    })
    _write_stats(stats)
    return stats


def _write_stats(stats: dict) -> None:
    with open(paths.STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


_HISTORY_KEEP = 2000  # ~6 weeks at the 30-minute cadence


def _append_history(stats: dict) -> None:
    """One compact line per run — the time series behind the dashboard chart."""
    line = json.dumps({
        "ts": stats["generated_at"],
        "open": stats["open_total"],
        "new": stats["new_this_run"],
        "companies": stats["companies_total"],
        "ok_rate": stats["fetch_success_rate"],
        "quarantined": stats["quarantined"],
        "secs": stats["duration_seconds"],
    }, ensure_ascii=False)
    lines = []
    try:
        with open(paths.HISTORY_PATH, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        pass
    lines.append(line)
    with open(paths.HISTORY_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines[-_HISTORY_KEEP:]) + "\n")
