"""Telegram push alerts for newly spotted roles (optional, best-effort).

Why Telegram and not SMS: real SMS costs money per message, and the free
workaround — carrier email-to-SMS gateways like number@vtext.com — is actively
being switched off (AT&T ended theirs in 2025). Telegram's Bot API is free,
unlimited, delivers a real lock-screen push, and is not going to be
deprecated out from under us.

Setup is two minutes:
  1. Message @BotFather on Telegram, send /newbot, follow the prompts.
  2. Put the token it gives you in the TELEGRAM_BOT_TOKEN secret.
  3. Put the destination chat id in TELEGRAM_CHAT_ID (your own user id for a
     private feed, or a channel id like -1001234567890 to broadcast).

Unset = silent no-op, exactly like the Discord and email integrations.
Failures never break the pipeline: alerting is a side channel.
"""

from __future__ import annotations

import os
from html import escape

import httpx

from . import config, filters, h1b, sponsorship

_API = "https://api.telegram.org/bot{token}/sendMessage"
# Telegram hard-caps a message at 4096 characters. We chunk well under it so a
# long role list never gets truncated mid-link.
_MAX_CHARS = 3500
_MAX_ROLES = 40      # beyond this a run is a backfill, not an announcement
_TIMEOUT = 10


def configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def _role_line(record: dict) -> str:
    """One role, as Telegram-flavoured HTML.

    Telegram's HTML parse mode supports a small tag set (<b>, <i>, <a>, <code>)
    and nothing else — no tables, no styling. So the shape carries the meaning:
    bold employer, linked title, dim detail line.
    """
    company = escape(record.get("company") or "")
    if h1b.badge(h1b.approvals_for(record.get("company") or "")):
        company += " ✓"
    if filters.is_remote(record.get("location") or "", record.get("title") or ""):
        company += " 🆁"

    title = escape(record.get("title") or "")
    url = record.get("url") or ""
    head = f'<b>{company}</b>\n<a href="{escape(url)}">{title}</a>' if url \
        else f"<b>{company}</b>\n{title}"

    bits = []
    season = record.get("season")
    if season and season != "Not stated":
        bits.append(season)
    if record.get("location"):
        bits.append(record["location"][:40])
    if record.get("salary"):
        bits.append(record["salary"])
    flag = sponsorship.flag(record.get("sponsorship"))
    if flag:
        bits.append(flag)
    detail = escape(" · ".join(b for b in bits if b))

    skills = record.get("skills") or []
    if skills:
        detail += "\n" + escape(" · ".join(skills[:4]))
    return f"{head}\n<i>{detail}</i>" if detail else head


def build_chunks(records: list[tuple[str, dict]]) -> list[tuple[str, list[str]]]:
    """Split roles into (message text, ids in that message) pairs.

    Carrying the ids alongside each message is what makes partial delivery
    safe. An earlier version returned bare strings and only marked ids
    delivered once EVERY message had landed — so a run where message 1
    succeeded and message 2 timed out reported nothing delivered, left all of
    it queued, and re-sent message 1's roles on the next run. Each chunk now
    settles on its own POST.
    """
    if not records:
        return []
    header = (f"<b>{len(records)} new internship"
              f"{'s' if len(records) != 1 else ''}</b>")
    footer = f'\n<a href="{config.pages_base()}/">Open the dashboard</a>'

    chunks: list[tuple[list[str], list[str]]] = []   # (lines, ids)
    lines: list[str] = []
    ids: list[str] = []
    first = True
    for jid, record in records:
        line = _role_line(record)
        prefix = header + "\n\n" if first else ""
        if lines and len(prefix + "\n\n".join([*lines, line])) > _MAX_CHARS:
            chunks.append((lines, ids))
            lines, ids, first = [line], [jid], False
        else:
            lines.append(line)
            ids.append(jid)
    if lines:
        chunks.append((lines, ids))

    out = []
    for i, (body, chunk_ids) in enumerate(chunks):
        text = (header + "\n\n" if i == 0 else "") + "\n\n".join(body)
        if i == len(chunks) - 1:
            text += footer
        out.append((text, chunk_ids))
    return out


def build_messages(records: list[dict]) -> list[str]:
    """Just the message text — used by tests and previews."""
    return [text for text, _ids in build_chunks([("", r) for r in records])]


def send_new_roles(store_data: dict, new_ids: list[str]) -> list[str]:
    """Push new roles to Telegram. Returns the ids that no longer need announcing.

    Same contract as notify.send_new_roles, because the outbox drains on it:
    the return value must be exact. Ids that can never be announced (gone from
    the store, or since closed) count as settled so the queue doesn't grow
    forever; roles we meant to send but didn't stay queued for the next run.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return list(new_ids)  # nothing to deliver to; don't accumulate
    if not new_ids:
        return []

    live = [(jid, store_data[jid]) for jid in new_ids if jid in store_data]
    settled = [jid for jid in new_ids if jid not in store_data]
    settled += [jid for jid, r in live if not r.get("is_open")]
    records = [(jid, r) for jid, r in live if r.get("is_open")]
    if not records:
        return settled

    shown = records[:_MAX_ROLES]
    announced: list[str] = []
    url = _API.format(token=token)
    # Settle each chunk on its OWN successful POST. Waiting for every message
    # meant one failed chunk re-sent the ones that had already arrived.
    for text, chunk_ids in build_chunks(shown):
        try:
            httpx.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    # Link previews would turn a 10-role message into a wall of
                    # thumbnails for the same careers page.
                    "disable_web_page_preview": True,
                },
                timeout=_TIMEOUT,
            ).raise_for_status()
        except Exception:  # noqa: BLE001 — alerting is a side channel, never fatal
            break  # stop here; unsent chunks stay queued for the next run
        announced += chunk_ids
    return settled + announced
