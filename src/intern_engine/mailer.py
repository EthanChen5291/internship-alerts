"""Daily email digests to our own subscriber list (optional, best-effort).

The dashboard signup form inserts emails into Supabase (`email_subscribers`,
RLS: the public can sign up but never read the list). Each engine run calls
`send_digest`; it actually sends at most once a day, and only when there is
something new to say. Every email carries that subscriber's one-click
unsubscribe link (a per-subscriber secret token).

Sending goes through Brevo's transactional API (free tier: 300 emails/day,
no domain required — a verified sender address is enough). Like every
integration here: missing env vars = silent no-op, failures never break a run.

Env: BREVO_API_KEY, MAIL_FROM (verified sender, "Name <addr>" or bare),
     SUPABASE_URL, SUPABASE_SERVICE_KEY.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import UTC, datetime, timedelta
from html import escape

import httpx

from . import config, h1b, paths, sponsorship

_MIN_HOURS_BETWEEN = 22          # "daily", tolerant of cron jitter
# Backstop only — NOT the definition of "new". `sent_role_ids` decides that.
# This bound exists for one situation: if mail state is ever lost or reset, the
# next digest must not mail the entire back catalogue. Under normal operation
# every role is sent within a day, so this never binds.
_MAX_LOOKBACK_DAYS = 14
# A first-ever digest (no send history at all) stays tight, so standing up the
# mailer doesn't blast every open role at the whole list.
_COLD_START_HOURS = 48
_MAX_ROLES = 30                  # cap the digest body
_MAX_SENDS = 250                 # stay under Brevo's free 300/day
_BREVO_URL = "https://api.brevo.com/v3/smtp/email"


# --- state (committed, so CI runs share it) -----------------------------------

def _load_state() -> dict:
    try:
        with open(paths.MAIL_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    with open(paths.MAIL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _parse_ts(value: str | None) -> datetime | None:
    try:
        return datetime.strptime((value or "")[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None


_SENT_MEMORY = 2000  # ids we remember; ~2 months of digests at current volume


def new_roles(store_data: dict, now: datetime | None = None,
              already_sent: set[str] | None = None,
              has_history: bool | None = None) -> list[dict]:
    """Every open role the list hasn't been told about yet, newest first.

    "New" means *not yet sent* — full stop. It used to mean "first seen in the
    last N hours", which was wrong in both directions: a role could sit inside
    two consecutive windows and go out twice (2026-07-17: 26 of 30 roles were
    repeats), and a role that missed its window during a failed run could never
    be sent at all. `sent_role_ids` is now the only thing that decides, so
    nothing repeats and nothing is skipped.

    The clock survives only as a backstop. If mail state is lost,
    `_MAX_LOOKBACK_DAYS` stops the next digest mailing the back catalogue; on a
    first-ever digest `_COLD_START_HOURS` keeps it tighter still. Neither
    bound binds during normal operation.

    No cap here — the subject line reports the true count; the HTML body caps
    what it lists (and says "+N more") at composition time.
    """
    now = now or datetime.now(UTC)
    already_sent = already_sent or set()
    if has_history is None:
        has_history = bool(already_sent)
    span = timedelta(days=_MAX_LOOKBACK_DAYS) if has_history \
        else timedelta(hours=_COLD_START_HOURS)
    cutoff = now - span
    fresh = [
        r for r in store_data.values()
        if r.get("is_open")
        and (_parse_ts(r.get("first_seen_at")) or cutoff) > cutoff
        and r.get("id") not in already_sent
    ]
    fresh.sort(key=lambda r: r.get("first_seen_at") or "", reverse=True)
    return fresh


def should_send(state: dict, fresh_count: int, now: datetime | None = None) -> bool:
    """At most one digest a day, and never an empty one."""
    if fresh_count == 0:
        return False
    now = now or datetime.now(UTC)
    last = _parse_ts(state.get("last_digest_at"))
    return last is None or (now - last) >= timedelta(hours=_MIN_HOURS_BETWEEN)


# --- composition ---------------------------------------------------------------

def _role_row(r: dict) -> str:
    flag = sponsorship.flag(r.get("sponsorship"))
    approvals = h1b.approvals_for(r.get("company") or "")
    check = " ✓" if h1b.badge(approvals) else ""
    bits = [b for b in (r.get("season"), r.get("location"), r.get("salary")) if b]
    return (
        '<tr><td style="padding:10px 0;border-bottom:1px solid #eee">'
        f'<strong>{escape(r.get("company") or "")}{check}</strong> — '
        f'<a href="{escape(r.get("url") or "")}">{escape(r.get("title") or "")}</a> {flag}'
        f'<br><span style="color:#666;font-size:13px">{escape(" · ".join(bits))}</span>'
        "</td></tr>"
    )


def build_digest_html(fresh: list[dict]) -> str:
    """The digest body; {{UNSUB_URL}} is replaced per recipient at send time.

    Lists the newest _MAX_ROLES; a bigger day gets a "+N more" pointer instead
    of a 60-row email.
    """
    repo = config.repo_slug()
    rows = "".join(_role_row(r) for r in fresh[:_MAX_ROLES])
    extra = len(fresh) - _MAX_ROLES
    if extra > 0:
        rows += (
            '<tr><td style="padding:10px 0;color:#666">'
            f'…plus {extra} more new role{"s" if extra != 1 else ""} on '
            f'<a href="{config.pages_base()}/">the live dashboard</a>.'
            "</td></tr>"
        )
    return (
        '<div style="font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;'
        'max-width:640px;margin:0 auto;color:#1a1a1a">'
        f"<h2 style=\"font-size:18px\">{len(fresh)} new internship"
        f"{'s' if len(fresh) != 1 else ''} spotted</h2>"
        '<p style="color:#666;font-size:13px">✓ = the employer has a real H-1B '
        "track record (USCIS data) · 🇺🇸 = citizens only · 🛂 = no visa "
        "sponsorship — auto-detected, verify on the posting.</p>"
        f'<table style="width:100%;border-collapse:collapse">{rows}</table>'
        f'<p style="margin-top:18px"><a href="https://github.com/{escape(repo)}">'
        "Full list & tracker on GitHub</a> · "
        f'<a href="{config.pages_base()}/">live dashboard</a></p>'
        '<p style="color:#999;font-size:12px;margin-top:24px">You get this because '
        "you subscribed to new-internship alerts. "
        '<a href="{{UNSUB_URL}}" style="color:#999">Unsubscribe</a> anytime.</p>'
        "</div>"
    )


def _sender() -> dict | None:
    raw = (os.environ.get("MAIL_FROM") or "").strip()
    if not raw:
        return None
    m = re.match(r"^(.*?)\s*<([^<>@\s]+@[^<>\s]+)>$", raw)
    if m:
        return {"name": m.group(1).strip() or "Intern Engine", "email": m.group(2)}
    if "@" in raw:
        return {"name": "Intern Engine", "email": raw}
    return None


def _subscribers(base_url: str, service_key: str) -> list[dict]:
    resp = httpx.get(
        f"{base_url}/rest/v1/email_subscribers",
        params={"select": "email,unsub_token"},
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _recipients(subscribers: list[dict], cursor: int) -> tuple[list[dict], int]:
    """Today's slice of the list, and where the next digest should resume.

    The daily quota (_MAX_SENDS) is smaller than the list will eventually be.
    Always mailing `subscribers[:250]` meant everyone past that point silently
    never received a digest — and they'd have no way to tell. Rotating the
    start point instead means a list of any size gets served in turn, so the
    failure mode degrades from "starved forever" to "hears from us less often".
    """
    total = len(subscribers)
    if total <= _MAX_SENDS:
        return subscribers, 0
    start = cursor % total
    ordered = subscribers[start:] + subscribers[:start]
    return ordered[:_MAX_SENDS], (start + _MAX_SENDS) % total


def _addr_hash(address: str) -> str:
    """A short stable fingerprint of an email address.

    mail_state.json is COMMITTED to a public repo, so the retry list must never
    contain the addresses themselves — only enough to recognize them next run.
    """
    return hashlib.sha256(address.strip().lower().encode()).hexdigest()[:16]


def _order_with_retries(recipients: list[dict], retry: set[str]) -> list[dict]:
    """Yesterday's failed recipients go first, so a transient provider error
    costs them one day, not their place in line."""
    if not retry:
        return recipients
    front = [s for s in recipients if _addr_hash(s.get("email") or "") in retry]
    rest = [s for s in recipients if _addr_hash(s.get("email") or "") not in retry]
    return front + rest


# --- sending -------------------------------------------------------------------

def send_digest(store_data: dict) -> int:
    """Send today's digest if due. Returns how many emails went out."""
    api_key = os.environ.get("BREVO_API_KEY")
    base_url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    sender = _sender()
    if not api_key or not base_url or not service_key or not sender:
        return 0

    state = _load_state()
    already_sent = set(state.get("sent_role_ids") or ())
    # Any prior digest counts as history, even one that predates sent_role_ids
    # — otherwise an upgraded install looks "cold" and re-tightens the window.
    has_history = bool(already_sent or state.get("last_digest_at"))
    fresh = new_roles(store_data, already_sent=already_sent, has_history=has_history)
    if not should_send(state, len(fresh)):
        return 0

    try:
        subscribers = _subscribers(base_url, service_key)
    except Exception:  # noqa: BLE001 — alerting is a side channel, never fatal
        return 0
    if not subscribers:
        return 0

    today = datetime.now(UTC).strftime("%b %d")
    subject = f"{len(fresh)} new internship{'s' if len(fresh) != 1 else ''} · {today}"
    body = build_digest_html(fresh)
    unsub_base = f"{config.pages_base()}/unsubscribe.html"
    recipients, cursor = _recipients(subscribers, int(state.get("send_cursor") or 0))
    recipients = _order_with_retries(
        recipients, {str(a) for a in state.get("retry_emails") or ()}
    )

    sent = 0
    failed_addrs: list[str] = []
    with httpx.Client(timeout=20) as client:
        for sub in recipients:
            address = (sub.get("email") or "").strip()
            token = sub.get("unsub_token") or ""
            if not address or not token:
                continue  # never send without a working unsubscribe link
            unsub_url = f"{unsub_base}?t={token}"
            html = body.replace("{{UNSUB_URL}}", unsub_url)
            try:
                client.post(
                    _BREVO_URL,
                    headers={"api-key": api_key, "Content-Type": "application/json"},
                    json={
                        "sender": sender,
                        "to": [{"email": address}],
                        "subject": subject,
                        "htmlContent": html,
                        # List-Unsubscribe gives every mail client its native
                        # "unsubscribe" button, pointing at our confirmation
                        # page. List-Unsubscribe-Post is deliberately NOT sent:
                        # RFC 8058 one-click requires an endpoint that handles
                        # a POST, and a static Pages file can't. Advertising it
                        # would make providers POST into a 405 and count the
                        # unsubscribe as failed.
                        "headers": {
                            "List-Unsubscribe": f"<{unsub_url}>",
                        },
                    },
                ).raise_for_status()
                sent += 1
            except Exception:  # noqa: BLE001 — skip the bad address, keep going
                failed_addrs.append(_addr_hash(address))
                continue
            time.sleep(0.12)  # stay well under Brevo's request rate

    if sent:
        state["last_digest_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        state["last_digest_roles"] = len(fresh)
        state["last_digest_sent"] = sent
        # Surfaced in state so a quietly failing provider is visible in the
        # committed diff instead of only in a swallowed exception; the
        # addresses themselves jump the queue on the next digest.
        state["last_digest_failed"] = len(failed_addrs)
        state["retry_emails"] = failed_addrs[:100]
        state["subscribers_total"] = len(subscribers)
        state["send_cursor"] = cursor
        # Only the roles the body actually LISTED count as sent. Anything past
        # the cap was a "+N more" pointer, so it stays eligible and gets its own
        # line in the next digest instead of being silently swallowed.
        listed = [r["id"] for r in fresh[:_MAX_ROLES] if r.get("id")]
        remembered = list(state.get("sent_role_ids") or ()) + listed
        state["sent_role_ids"] = remembered[-_SENT_MEMORY:]  # oldest drop off
        _save_state(state)
    return sent
