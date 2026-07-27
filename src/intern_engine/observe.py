"""The engine's own memory of when companies really posted.

The Drop Radar used to lean entirely on an outside reference dataset (Simplify),
whose file only starts mid-November — so any company that actually drops in
August–October gets crushed to a November date, and the projection is wrong.

This module fixes that at the root: every run, we record the *real* posted date
the engine observed straight from each company's ATS (`posted_at`), keyed by
company and cycle. That record (`data/observed.json`) is authoritative ground
truth, owned by us, dependent on no third-party repo. It only grows, so once we
have watched a full cycle the radar can project from what companies actually did
last year instead of from a backfilled guess.

Structure:
    {
      "updated_at": "2026-07-07T12:00:00Z",
      "companies": {
        "<normalized name>": {
          "name": "NVIDIA",
          "cycles": {
            "Summer 2027": {"first_posted": "2026-09-03", "count": 4,
                            "role_ids": ["greenhouse:nvidia:1", ...]},
            "Fall 2026":   {"first_posted": "2026-03-25", "count": 2,
                            "role_ids": [...]}
          }
        }
      }
    }
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from . import config, h1b, paths


def load() -> dict:
    try:
        with open(paths.OBSERVED_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"companies": {}}


def _posted_day(record: dict) -> str | None:
    """The role's real published date as YYYY-MM-DD, or None if we never got one."""
    raw = record.get("posted_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return None


def update_from_store(store_data: dict, observed: dict | None = None,
                      cycles: list[str] | None = None) -> dict:
    """Fold the store's real posted dates into the observed record.

    Keeps, per company and cycle, the EARLIEST posted date we have ever seen and
    the set of distinct role ids behind it. Monotonic: a role closing and being
    purged from the store never erases the date (or the id) we learned from it.

    The ids are what make `count` mean something. It used to be a counter bumped
    once per role per RUN, so an hourly schedule inflated it without limit —
    Amazon showed 1,197 "roles" for a cycle it had posted a few dozen times.
    Recording the ids makes the number both correct and auditable: anyone can
    count the list themselves.

    Two guards keep the radar honest — a record is recorded only when BOTH hold:

      1. The cycle was STATED (title or verified text), not inferred from a
         posting date. The radar renders observations as "🎯 verified — the
         engine saw the drop itself"; a date-inferred guess would project
         fiction forward a year.
      2. The cycle is one we actually TRACK. Off-cycle tombstones (e.g. a lone
         "Summer 2026" role we dropped) are real but incomplete — we never swept
         that cycle in full, so projecting it forward would invent a cadence the
         company doesn't have. Cross-cycle projection is a next-cycle feature: we
         record this cycle's real drops now, and project them forward once THIS
         cycle becomes "last cycle".
    """
    observed = observed if observed is not None else load()
    companies = observed.setdefault("companies", {})
    tracked = set(cycles if cycles is not None else config.cycles(config.load_config()))

    for role_id, record in store_data.items():
        if record.get("season_inferred"):
            continue  # a guessed cycle is not a real observation (see docstring)
        day = _posted_day(record)
        if not day:
            continue
        name = (record.get("company") or "").strip()
        key = h1b.normalize(name)
        if not key:
            continue

        # A multi-cycle posting is a real drop in EVERY cycle it states —
        # reading only the primary season lost Deepgram's Fall history.
        for cycle in (record.get("seasons") or [record.get("season")]):
            if not cycle or cycle not in tracked:
                continue  # only real, tracked-cycle drops become observations
            entry = companies.setdefault(key, {"name": name, "cycles": {}})
            if name and (entry.get("name") in (None, "", key)):
                entry["name"] = name
            cyc = entry["cycles"].get(cycle)
            if cyc is None:
                cyc = entry["cycles"][cycle] = {"first_posted": day, "role_ids": []}
            # Files written before ids were tracked carry an inflated `count`
            # and no list; seeding from what we can see now replaces the bad
            # number with a real one, and it grows correctly from here.
            ids = set(cyc.get("role_ids") or ())
            ids.add(str(role_id))
            cyc["role_ids"] = sorted(ids)
            cyc["count"] = len(ids)
            if day < cyc["first_posted"]:
                cyc["first_posted"] = day

    # Every count is derived, never accumulated. This also retires any inflated
    # legacy number whose roles have since been purged from the store: those
    # cycles keep their (still valid) first_posted date and drop to a count we
    # can actually back with ids.
    for entry in companies.values():
        for cyc in (entry.get("cycles") or {}).values():
            cyc["count"] = len(cyc.get("role_ids") or ())

    observed["updated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    observed["companies"] = dict(sorted(companies.items()))
    return observed


def save(observed: dict) -> None:
    with open(paths.OBSERVED_PATH, "w", encoding="utf-8") as f:
        json.dump(observed, f, ensure_ascii=False, indent=1, sort_keys=False)


def record_run(store_data: dict) -> int:
    """Convenience for the pipeline: load, fold in the store, persist.

    Returns the number of companies we now hold at least one real date for.
    """
    observed = update_from_store(store_data)
    save(observed)
    return len(observed.get("companies", {}))
