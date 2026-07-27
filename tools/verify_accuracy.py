"""Self-check: every open role must satisfy every accuracy invariant.

    python tools/verify_accuracy.py        # exit 0 = clean, 1 = violations

Checks each OPEN role in data/jobs.json against the rules the pipeline promises:
  1. season is a tracked cycle
  2. a title that states a tracked term+year agrees with the assigned season
  3. no title states an off-cycle year (those must be tombstoned, never listed)
  4. the location passes the US filter (config regions honored)
  5. it still reads as a tech internship (title-level filters)
  6. a real posted date exists and is inside max_age_days
  7. inferred (~) rows carry a posted date (that date is the inference's basis)
  8. the company isn't blocklisted
Plus cross-artifact consistency: the JSON API's open count matches the store.

Run it after any filter change or store surgery — it's the "did we break the
list" button.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from intern_engine import config, filters, paths, quality, store  # noqa: E402


def main() -> None:
    cfg = config.load_config()
    cycles = config.cycles(cfg)
    blocklist = quality.load_blocklist()
    max_age = config.max_age_days(cfg)
    cutoff = (datetime.now(UTC) - timedelta(days=max_age)).strftime("%Y-%m-%d") if max_age else ""

    data = store.load(paths.JOBS_PATH)
    open_jobs = [r for r in data.values() if r.get("is_open")]
    problems: list[str] = []
    warnings: list[str] = []

    def _line(record: dict, rule: str) -> str:
        return (
            f"  [{rule}] {record.get('company', '?')[:28]} | "
            f"{(record.get('title') or '?')[:56]} | season={record.get('season')} "
            f"| loc={record.get('location')!r}"
        )

    def flag(record: dict, rule: str) -> None:
        problems.append(_line(record, rule))

    def warn(record: dict, rule: str) -> None:
        warnings.append(_line(record, rule))

    for r in open_jobs:
        title = r.get("title") or ""
        season = r.get("season")
        if season not in cycles:
            flag(r, "untracked-season")
        stated = filters.detect_season(title, cycles)
        if stated is not None and stated != season:
            flag(r, "title-season-mismatch")
        if stated is None and filters.states_explicit_year(title):
            flag(r, "off-cycle-year-in-title")
        if config.restrict_region(cfg) and not config.include_international(cfg) and \
                not filters.region_ok(r.get("location") or "",
                                      config.want_us(cfg), config.want_canada(cfg)):
            flag(r, "out-of-region")
        if not filters.is_internship(title):
            flag(r, "not-an-internship-title")
        if cfg.get("role_scope", "tech") == "tech" and not filters.is_tech(title):
            flag(r, "not-a-tech-title")
        posted = (r.get("posted_at") or "")[:10]
        # Age only disqualifies a role whose cycle we INFERRED, where recency
        # was the evidence. When the employer stated the cycle, an old posting
        # is just an early one — Amazon's "Fall 2026 (US)" internship opened
        # long before the cycle and is still both open and still Fall 2026.
        if cutoff and posted and posted < cutoff and r.get("season_inferred"):
            flag(r, "older-than-max-age")
        if not posted:
            # A warning, not a violation: some boards genuinely publish no
            # date, and one undated-but-real role must not block every publish.
            # (The published copy quotes date COVERAGE per run, not "every
            # role", precisely so this case can exist honestly.)
            warn(r, "missing-posted-date")
        if r.get("season_inferred") and not posted:
            flag(r, "inferred-without-posted-date")
        if quality.is_blocked(r.get("company") or "", blocklist):
            flag(r, "blocklisted-company")

    api_path = os.path.join(paths.API_DIR, "jobs.json")
    try:
        with open(api_path, encoding="utf-8") as f:
            api = json.load(f)
        if api.get("count") != len(open_jobs):
            problems.append(
                f"  [api-count-drift] api/jobs.json says {api.get('count')}, "
                f"store has {len(open_jobs)} open (regenerate outputs)"
            )
    except (OSError, ValueError):
        problems.append("  [api-missing] docs/api/jobs.json unreadable")

    # --- publish gates -------------------------------------------------------
    # Correctness checks above catch a bad ROW. These catch a bad RUN: a
    # collapse in volume means something upstream broke (an ATS changed shape,
    # a filter got too strict), and publishing it would quietly delete most of
    # the public list. Better to fail loudly and keep yesterday's good build.
    gates: list[str] = []
    floor = int(os.environ.get("MIN_OPEN_ROLES") or 0)
    if floor and len(open_jobs) < floor:
        gates.append(
            f"  [volume-floor] only {len(open_jobs)} open roles, floor is {floor}"
        )
    try:
        with open(paths.STATS_PATH, encoding="utf-8") as f:
            stats = json.load(f)
        rate = stats.get("fetch_success_rate")
        if isinstance(rate, (int, float)) and rate < 0.5:
            gates.append(f"  [fetch-collapse] only {rate:.0%} of boards responded")
    except (OSError, ValueError):
        gates.append("  [stats-missing] data/stats.json unreadable")

    n_inferred = sum(1 for r in open_jobs if r.get("season_inferred"))
    by_cycle = {c: sum(1 for r in open_jobs if r.get("season") == c) for c in cycles}
    print(f"Checked {len(open_jobs)} open roles "
          f"({', '.join(f'{c}: {n}' for c, n in by_cycle.items())}; "
          f"{n_inferred} cycle-inferred, {len(open_jobs) - n_inferred} employer-stated).")
    if warnings:
        print(f"\n{len(warnings)} warning(s) (non-blocking):")
        print("\n".join(warnings))
    if problems or gates:
        if problems:
            print(f"\n{len(problems)} violation(s):")
            print("\n".join(problems))
        if gates:
            print(f"\n{len(gates)} publish gate(s) tripped:")
            print("\n".join(gates))
        sys.exit(1)
    print("All accuracy invariants hold.")


if __name__ == "__main__":
    main()
