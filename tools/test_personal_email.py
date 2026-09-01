"""Send one setup-test message using the personal Brevo configuration."""

from __future__ import annotations

import os
import re
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from intern_engine.personal_alerts import send_test_email  # noqa: E402


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


if __name__ == "__main__":
    try:
        send_test_email()
    except httpx.HTTPStatusError as exc:
        raise SystemExit(_safe_error(exc)) from None
    print("Brevo accepted the test email.")
