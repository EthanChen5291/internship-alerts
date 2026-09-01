"""Send one setup-test message using the personal Brevo configuration."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from intern_engine.personal_alerts import send_test_email  # noqa: E402

if __name__ == "__main__":
    send_test_email()
    print("Brevo accepted the test email.")
