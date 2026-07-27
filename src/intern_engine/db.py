"""Optional Postgres (Supabase) sink for jobs, companies, and run metrics.

Best-effort by design: if SUPABASE_URL / SUPABASE_SERVICE_KEY aren't set (or the
client can't be built), every function no-ops and the engine runs exactly as
before. When configured, each run mirrors the data into Postgres - the source of
truth + analytics layer - while the README/CSV/dashboard remain exported views.
"""

from __future__ import annotations

import json
import os

from . import filters, paths

_JOB_BATCH = 500


def _client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
    except ImportError:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def enabled() -> bool:
    return _client() is not None


def _company_rows() -> list[dict]:
    try:
        with open(paths.COMPANIES_PATH, encoding="utf-8") as f:
            companies = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return [
        {"key": f"{c['ats']}:{c['slug']}", "ats": c["ats"], "slug": c["slug"], "name": c["name"]}
        for c in companies
        if c.get("ats") and c.get("slug")
    ]


def _job_rows(store_data: dict) -> list[dict]:
    rows = []
    for r in store_data.values():
        location = r.get("location") or ""
        rows.append({
            "id": r["id"],
            "company_key": f"{r.get('source')}:{r.get('company_slug')}",
            "source": r.get("source"),
            "company": r.get("company"),
            "title": r.get("title"),
            "location": location,
            "url": r.get("url"),
            "category": r.get("category"),
            "season": r.get("season"),
            "seasons": r.get("seasons") or None,
            # The evidence columns. Without these the mirror can't tell a
            # stated cycle from a guess, or a real date from a derived one —
            # which is most of what makes this dataset worth querying.
            "season_inferred": bool(r.get("season_inferred")),
            "region": "US" if filters.is_united_states(location) else "International",
            "sponsorship": r.get("sponsorship", "unknown"),
            "salary": r.get("salary"),
            "skills": r.get("skills") or None,
            "posted_at": r.get("posted_at"),
            "posted_at_source": r.get("posted_at_source"),
            "first_seen_at": r.get("first_seen_at"),
            "last_seen_at": r.get("last_seen_at"),
            "closed_at": r.get("closed_at"),
            "closed_reason": r.get("closed_reason"),
            "is_open": bool(r.get("is_open")),
        })
    return rows


def _run_row(stats: dict) -> dict:
    keep = (
        "duration_seconds", "companies_total", "fetched_ok", "fetch_errors",
        "fetch_success_rate", "roles_matched", "new_this_run", "open_total",
        "roles_by_source", "roles_by_cycle", "roles_by_region", "detection_latency",
    )
    return {k: stats.get(k) for k in keep}


def sync(store_data: dict, stats: dict) -> bool:
    """Mirror companies + all jobs + this run's metrics into Postgres."""
    client = _client()
    if client is None:
        return False
    try:
        companies = _company_rows()
        if companies:
            for i in range(0, len(companies), _JOB_BATCH):
                client.table("companies").upsert(
                    companies[i:i + _JOB_BATCH], on_conflict="key"
                ).execute()

        jobs = _job_rows(store_data)
        for i in range(0, len(jobs), _JOB_BATCH):
            client.table("jobs").upsert(jobs[i:i + _JOB_BATCH], on_conflict="id").execute()

        client.table("scrape_runs").insert(_run_row(stats)).execute()
        return True
    except Exception as exc:  # noqa: BLE001 - DB is a mirror; never break the run
        # Loud on purpose. The usual cause is a schema older than the writer
        # (db/schema.sql has `alter table ... add column if not exists` for
        # exactly this) — and a silently-skipped mirror looks identical to a
        # working one from the outside.
        print(f"  (Postgres sync FAILED: {type(exc).__name__}: {exc})")
        print("   If this mentions an unknown column, re-run db/schema.sql —"
              " it migrates existing tables.")
        return False
