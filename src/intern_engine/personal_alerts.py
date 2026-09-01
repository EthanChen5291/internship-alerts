"""Instant alerts for a personal fork (optional, best-effort).

The upstream project has a public, double-opt-in daily digest. A personal fork
does not need a subscriber database: one configured destination can receive the
same newly-published roles immediately. Email uses Brevo.

Each sender follows the outbox contract: return only role ids that were sent or
can never be sent. Transient failures remain queued for the next workflow run.
"""

from __future__ import annotations

import os
import re
from html import escape

import httpx

from . import config, grouping

_BREVO_URL = "https://api.brevo.com/v3/smtp/email"
_TIMEOUT = 12
_MAX_EMAIL_GROUPS = 50


def email_configured() -> bool:
    return bool(
        os.environ.get("BREVO_API_KEY")
        and os.environ.get("MAIL_FROM")
        and os.environ.get("ALERT_EMAIL_TO")
    )


def _sender(raw: str) -> dict[str, str]:
    match = re.fullmatch(r"\s*(.*?)\s*<\s*([^<>\s]+@[^<>\s]+)\s*>\s*", raw)
    if match:
        return {"name": match.group(1).strip() or "Internship Alerts", "email": match.group(2)}
    return {"name": "Internship Alerts", "email": raw.strip()}


def _records(store_data: dict, new_ids: list[str]) -> tuple[list[str], list[dict]]:
    live = [(jid, store_data[jid]) for jid in new_ids if jid in store_data]
    settled = [jid for jid in new_ids if jid not in store_data]
    settled += [jid for jid, record in live if not record.get("is_open")]
    grouped = grouping.group(
        [{**record, "id": jid} for jid, record in live if record.get("is_open")]
    )
    return settled, grouped


def _ids(record: dict) -> list[str]:
    return [value for value in (record.get("opening_ids") or [record.get("id")]) if value]


def build_email(records: list[dict]) -> tuple[str, str]:
    count = sum(len(_ids(record)) for record in records)
    subject = f"{count} new tech internship{'s' if count != 1 else ''}"
    rows = []
    for record in records:
        company = escape(str(record.get("company") or "")[:180])
        title = escape(str(record.get("title") or "")[:400])
        url = escape(str(record.get("url") or "")[:1500], quote=True)
        role = f'<a href="{url}">{title}</a>' if url else title
        details = " · ".join(
            str(value)[:180]
            for value in (
                record.get("season"),
                record.get("location"),
                record.get("salary"),
                ", ".join(record.get("skills") or []),
            )
            if value and value != "Not stated"
        )
        openings = len(_ids(record))
        if openings > 1:
            details = f"{openings} openings" + (f" · {details}" if details else "")
        rows.append(
            "<tr>"
            f'<td style="padding:12px;border-bottom:1px solid #ddd"><b>{company}</b><br>{role}'
            f'<div style="color:#666;margin-top:4px">{escape(details)}</div></td>'
            "</tr>"
        )
    dashboard = escape(config.pages_base() + "/", quote=True)
    html = (
        '<div style="font:15px system-ui,sans-serif;max-width:720px;margin:auto">'
        f"<h2>{escape(subject)}</h2><table style=\"border-collapse:collapse;width:100%\">"
        + "".join(rows)
        + f'</table><p><a href="{dashboard}">Open the internship dashboard</a></p></div>'
    )
    return subject, html


def _post_email(subject: str, html: str) -> None:
    """Post one transactional email, raising when Brevo rejects it."""
    httpx.post(
        _BREVO_URL,
        headers={"api-key": os.environ["BREVO_API_KEY"], "Content-Type": "application/json"},
        json={
            "sender": _sender(os.environ["MAIL_FROM"]),
            "to": [{"email": os.environ["ALERT_EMAIL_TO"].strip()}],
            "subject": subject,
            "htmlContent": html,
        },
        timeout=_TIMEOUT,
    ).raise_for_status()


def send_test_email() -> None:
    """Send a harmless configuration test without touching alert state."""
    if not email_configured():
        raise RuntimeError("BREVO_API_KEY, MAIL_FROM, and ALERT_EMAIL_TO are required")
    dashboard = escape(config.pages_base() + "/", quote=True)
    _post_email(
        "Internship Alerts email test",
        (
            '<div style="font:15px system-ui,sans-serif;max-width:640px;margin:auto">'
            "<h2>Your internship email alerts are working</h2>"
            "<p>This is a one-time setup test. Future messages will only be sent when "
            "new internship openings are published.</p>"
            f'<p><a href="{dashboard}">Open the internship dashboard</a></p></div>'
        ),
    )


def send_email(store_data: dict, new_ids: list[str]) -> list[str]:
    if not email_configured():
        return list(new_ids)
    settled, records = _records(store_data, new_ids)
    shown = records[:_MAX_EMAIL_GROUPS]
    if not shown:
        return settled
    subject, html = build_email(shown)
    try:
        _post_email(subject, html)
    except Exception:  # noqa: BLE001 - notification failures retry through the outbox
        return settled
    return settled + [jid for record in shown for jid in _ids(record)]
