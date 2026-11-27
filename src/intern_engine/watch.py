"""Fast lane: check a short list of big companies and email new roles at once.

The full `update` sweep reads ~5,500 boards and GitHub only schedules it a few
times a day, so a new role at a big company could take days to reach the
owner. `run.py watch` reads only data/watchlist.json's boards (well under a
minute), applies the same scope filters as the main pipeline, and emails the
owner any role it has not emailed before. It never writes the store or the
public list; the next `update` publishes those roles as usual, and the
personal-email channel skips ids this module already sent (see
`already_sent`), so nothing is emailed twice.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import asdict
from datetime import UTC, datetime

from . import config, fallback, paths, personal_alerts, pipeline, quality, registry, store

WATCHLIST_PATH = os.path.join(paths.DATA_DIR, "watchlist.json")
STATE_PATH = os.path.join(paths.DATA_DIR, "watch_state.json")
_MAX_PER_EMAIL = 25
# Added to the watchlist after the first seed (2026-11-27), before per-board
# learning existed: learned silently once.
_ADDED_AFTER_FIRST_SEED = {"google"}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def watched_companies(reg: list[dict], names: list[str], outage: set[str]) -> list[dict]:
    wanted = {_norm(n) for n in names}
    return [c for c in reg
            if _norm(c.get("name") or "") in wanted and c.get("ats") not in outage]


def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("sent_ids"), list):
            return data
    except (OSError, ValueError):
        pass
    return {"seeded": False, "sent_ids": []}


def already_sent() -> set[str]:
    return set(load_state().get("sent_ids") or [])


def _save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True)
        f.write("\n")


def _record(job) -> dict:
    data = asdict(job)
    data["id"] = job.id
    return data


def run() -> str:
    with open(WATCHLIST_PATH, encoding="utf-8") as f:
        names = json.load(f).get("companies") or []
    cfg = config.load_config()
    companies = watched_companies(registry.load(), names, fallback.outage_sources())
    if not companies:
        return "watchlist matched no boards"
    existing = store.load(paths.JOBS_PATH)

    async def no_enrich(results, net, workday_net):
        return None

    results, _ = asyncio.run(pipeline._fetch_all(companies, no_enrich))
    kept, succeeded, *_ = pipeline._keep_matching(
        results, cfg, quality.load_blocklist(), existing)
    status = f"{len(succeeded)}/{len(companies)} boards read, {len(kept)} in scope"

    state = load_state()
    sent = set(state.get("sent_ids") or [])
    read_now = {registry.board_key(c) for c, _result, err in results if err is None}
    if not state.get("seeded"):
        known: set[str] = set()  # first run: learn every board
    elif "boards" in state:
        known = set(state["boards"])
    else:
        # State from before per-board learning: every board then watched was
        # seeded; only companies added since must be learned.
        known = {registry.board_key(c) for c in companies
                 if _norm(c.get("name") or "") not in _ADDED_AFTER_FIRST_SEED}
    # A board read for the first time (first run, or a company just added to
    # the watchlist) is learned silently: its open roles aren't "just posted".
    new_boards = read_now - known
    learned = [j for j in kept if j.board_key in new_boards]
    sent |= {j.id for j in learned}
    boards = known | read_now
    if learned:
        status += f", learned {len(learned)} from {len(new_boards)} new board(s)"

    # Anything already published (and so already emailed by `notify`) is old news.
    fresh = [j for j in kept if j.id not in sent and j.id not in existing]
    shown = fresh[:_MAX_PER_EMAIL]
    if shown and personal_alerts.email_configured():
        records = [_record(j) for j in shown]
        subject, html = personal_alerts.build_email(records)
        html = html.replace("NEW INTERNSHIP ALERT", "JUST POSTED · BIG-COMPANY WATCH", 1)
        try:
            personal_alerts._post_email(f"[Just posted] {subject}", html)
            sent |= {j.id for j in shown}
            status += f", emailed {len(shown)}"
        except Exception as exc:  # noqa: BLE001 - not marked sent, retried next run
            status += f", email failed ({type(exc).__name__})"
    elif shown:
        status += f", {len(shown)} new but email not configured"
    _save_state({"seeded": True, "sent_ids": sorted(sent), "boards": sorted(boards),
                 "updated_at": _now()})
    return status


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
