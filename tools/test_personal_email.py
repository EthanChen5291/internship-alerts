"""Send one setup-test message using the personal Brevo configuration."""

from __future__ import annotations

import os
import re
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from intern_engine.personal_alerts import send_test_email  # noqa: E402

_EVENTS_URL = "https://api.brevo.com/v3/smtp/statistics/events"
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
    raise SystemExit(f"Brevo did not report delivery within 45 seconds ({status}).")


if __name__ == "__main__":
    try:
        tracking_id = send_test_email()
        delivery = _wait_for_delivery(tracking_id)
    except httpx.HTTPStatusError as exc:
        raise SystemExit(_safe_error(exc)) from None
    print(f"Brevo accepted the test email and reports: {delivery}.")
