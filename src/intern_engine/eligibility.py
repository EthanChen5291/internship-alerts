"""High-precision class-year requirements stated by the employer.

Only explicit student-standing language earns a label.  A job title such as
"Junior Software Developer" or prose about mentoring junior engineers must
never be interpreted as an applicant class-year requirement.
"""

from __future__ import annotations

import re

JUNIORS_PLUS = "Juniors+"

_JUNIORS_PLUS_RE = re.compile(
    r"("
    r"\b(?:rising|current)\s+junior(?:s)?(?:\s+(?:or|and|/)\s+seniors?)?\b"
    r"|\b(?:college\s+)?juniors?\s+(?:and|or)\s+(?:above|seniors?)\b"
    r"|\bjuniors?\s*(?:/|,|and|or)\s*seniors?\b"
    r"|\bjunior(?:\s+class)?\s+standing\s+(?:is\s+)?(?:required|or\s+(?:above|higher))\b"
    r"|\b(?:at\s+least|minimum(?:\s+of)?)\s+(?:a\s+)?junior"
    r"(?:\s+class)?\s+standing\b"
    r"|\b(?:junior|senior)\s+(?:year\s+)?(?:college|university|undergraduate)"
    r"\s+students?\b"
    r")",
    re.IGNORECASE,
)


def classify(text: str | None) -> str | None:
    """Return ``Juniors+`` only for explicit student-standing evidence."""
    return JUNIORS_PLUS if _JUNIORS_PLUS_RE.search(text or "") else None
