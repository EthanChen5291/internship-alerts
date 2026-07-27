"""Roles that have been found but not yet announced.

The ordering bug this exists to fix: `run.py update` used to fetch, write every
artifact, and fire the Discord/email alerts — and only THEN did the workflow
commit and push. So a run whose push failed had already told subscribers about
roles that were nowhere on the site, and the next run, seeing them as new all
over again, told them a second time.

Splitting it in two fixes both halves at once:

    update  -> writes the data AND queues the new role ids here
    (commit & push — the alerts' precondition)
    notify  -> drains the queue and actually sends

Because the queue is a committed file, a failed push leaves it un-drained: the
roles stay pending and go out with the next successful publish, exactly once.
The queue is what makes the alert idempotent, so `notify` can be re-run safely.
"""

from __future__ import annotations

import json
import os

from . import paths

_MAX_PENDING = 200  # a backlog past this is a bug, not an announcement


def load() -> list[str]:
    """The role ids waiting to be announced."""
    try:
        with open(paths.OUTBOX_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    pending = data.get("pending") if isinstance(data, dict) else None
    return [str(x) for x in pending] if isinstance(pending, list) else []


def save(pending: list[str]) -> None:
    os.makedirs(os.path.dirname(paths.OUTBOX_PATH), exist_ok=True)
    tmp = f"{paths.OUTBOX_PATH}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"pending": pending}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, paths.OUTBOX_PATH)


def queue(new_ids: list[str]) -> list[str]:
    """Add this run's new roles to the queue; returns everything pending.

    Duplicate-safe: a role already waiting is not queued twice, so re-running
    `update` before a successful publish doesn't multiply the announcement.
    """
    pending = load()
    known = set(pending)
    for jid in new_ids:
        if jid not in known:
            known.add(jid)
            pending.append(jid)
    pending = pending[-_MAX_PENDING:]
    save(pending)
    return pending


def drain(done: list[str] | None = None) -> list[str]:
    """Remove `done` from the queue; returns what's still pending.

    Partial on purpose. A run that announced 50 of 60 roles, or whose second
    Discord chunk failed, must keep the rest queued — clearing the whole queue
    on any success is how the unannounced ones would vanish for good. Passing
    nothing clears everything (used only when there is nothing left to deliver).
    """
    if done is None:
        save([])
        return []
    finished = set(done)
    remaining = [jid for jid in load() if jid not in finished]
    save(remaining)
    return remaining
