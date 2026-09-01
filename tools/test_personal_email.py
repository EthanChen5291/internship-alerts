"""Send one setup-test message using the personal Brevo configuration."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from intern_engine.personal_alerts import send_preview_email  # noqa: E402

_EVENTS_URL = "https://api.brevo.com/v3/smtp/statistics/events"
_EMAILS_URL = "https://api.brevo.com/v3/smtp/emails"
_ACCOUNT_URL = "https://api.brevo.com/v3/account"
_FAILURE_EVENTS = {
    "blocked",
    "complaint",
    "error",
    "hardbounce",
    "invalid",
    "softbounce",
    "unsubscribed",
}


def _safe_error(exc: httpx.HTTPStatusError) -> str:
    """Return Brevo's useful response without leaking addresses or tokens."""
    try:
        payload = exc.response.json()
    except ValueError:
        payload = {}
    code = str(payload.get("code") or "unknown")
    message = str(payload.get("message") or "No diagnostic message returned")
    message = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted email]", message)
    message = re.sub(r"(?:xkeysib-|eyJ)[A-Za-z0-9._-]+", "[redacted key]", message)
    return f"Brevo HTTP {exc.response.status_code} ({code}): {message}"


def _safe_text(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted email]", text)
    return re.sub(r"(?:xkeysib-|eyJ)[A-Za-z0-9._-]+", "[redacted key]", text)


def _headers() -> dict[str, str]:
    return {"api-key": os.environ["BREVO_API_KEY"]}


def _account_summary() -> str:
    response = httpx.get(_ACCOUNT_URL, headers=_headers(), timeout=12)
    response.raise_for_status()
    account = response.json()
    enabled = bool((account.get("relay") or {}).get("enabled"))
    credits = [
        str(item.get("credits"))
        for item in account.get("plan") or []
        if item.get("creditsType") == "sendLimit" and item.get("credits") is not None
    ]
    remaining = ", ".join(credits) if credits else "not reported"
    return f"transactional relay enabled={enabled}; send credits={remaining}"


def _recent_activity() -> str:
    recipient = os.environ["ALERT_EMAIL_TO"].strip()
    emails_response = httpx.get(
        _EMAILS_URL,
        headers=_headers(),
        params={"email": recipient, "limit": 20, "sort": "desc"},
        timeout=12,
    )
    emails_response.raise_for_status()
    messages = emails_response.json().get("transactionalEmails") or []
    test_messages = sum(str(item.get("subject") or "").startswith("[PREVIEW]") for item in messages)

    events_response = httpx.get(
        _EVENTS_URL,
        headers=_headers(),
        params={"email": recipient, "days": 1, "limit": 50, "sort": "desc"},
        timeout=12,
    )
    events_response.raise_for_status()
    events = events_response.json().get("events") or []
    statuses = sorted({str(item.get("event") or "unknown") for item in events})
    reasons = sorted({_safe_text(item.get("reason")) for item in events if item.get("reason")})
    event_text = ", ".join(statuses) if statuses else "none"
    reason_text = f"; reasons={'; '.join(reasons)}" if reasons else ""
    return f"test messages recorded={test_messages}; recent events={event_text}{reason_text}"


def _preview_record() -> dict:
    store = json.loads((Path(__file__).resolve().parents[1] / "data" / "jobs.json").read_text())
    records = store.values() if isinstance(store, dict) else store
    try:
        return next(record for record in records if record.get("is_open"))
    except StopIteration:
        raise SystemExit("No open role is available for the email preview.") from None


def _wait_for_delivery(message_id: str) -> str:
    if not message_id:
        raise SystemExit("Brevo accepted the message but returned no tracking id.")
    deadline = time.monotonic() + 45
    observed: list[str] = []
    while time.monotonic() < deadline:
        response = httpx.get(
            _EVENTS_URL,
            headers={"api-key": os.environ["BREVO_API_KEY"]},
            params={"messageId": message_id, "limit": 20, "sort": "desc"},
            timeout=12,
        )
        response.raise_for_status()
        events = response.json().get("events") or []
        observed = [str(item.get("event") or "").strip() for item in events]
        normalized = {event.lower().replace(" ", "") for event in observed}
        if "delivered" in normalized:
            return "delivered"
        failed = normalized & _FAILURE_EVENTS
        if failed:
            reasons = "; ".join(
                _safe_text(item.get("reason")) for item in events if item.get("reason")
            )
            suffix = f" — {reasons}" if reasons else ""
            raise SystemExit(f"Brevo reports {sorted(failed)[0]}{suffix}")
        time.sleep(5)
    status = ", ".join(observed) if observed else "no events returned"
    raise SystemExit(
        f"Brevo did not report delivery within 45 seconds ({status}); {_recent_activity()}."
    )


if __name__ == "__main__":
    try:
        print(f"Brevo account: {_account_summary()}")
        tracking_id = send_preview_email(_preview_record())
        delivery = _wait_for_delivery(tracking_id)
    except httpx.HTTPStatusError as exc:
        raise SystemExit(_safe_error(exc)) from None
    print(f"Brevo accepted the test email and reports: {delivery}.")
