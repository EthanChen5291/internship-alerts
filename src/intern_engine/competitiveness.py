"""Transparent relative competition estimates for application prioritization.

No public source provides reliable applicant counts or internship acceptance
rates across employers.  These labels therefore stay explicitly estimated and
use only two stable signals already curated by the project: how sought-after
the employer is in the priority list and whether the role family is typically
especially crowded (quant or data/ML/AI).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import priority

_VERY_SOUGHT_AFTER_CUTOFF = 65
_HIGH_DEMAND_CATEGORIES = {"quant", "data & ml/ai"}


@dataclass(frozen=True)
class Estimate:
    label: str
    key: str
    explanation: str


def estimate(record: dict) -> Estimate:
    """Return a conservative relative label, never an acceptance-rate claim."""
    company = str(record.get("company") or "")
    rank = priority.rank(company)
    reasons: list[str] = []

    if rank < _VERY_SOUGHT_AFTER_CUTOFF:
        score = 3
        reasons.append("a highly sought-after employer")
    elif rank < priority.UNRANKED:
        score = 2
        reasons.append("a sought-after employer")
    else:
        score = 1
        reasons.append("limited employer-specific signal")

    category = str(record.get("category") or "").strip().casefold()
    if category in _HIGH_DEMAND_CATEGORIES:
        score += 1
        reasons.append("a typically crowded role family")

    if score >= 3:
        label, key = "Very high", "very-high"
    elif score == 2:
        label, key = "High", "high"
    else:
        label, key = "Moderate", "moderate"

    explanation = (
        f"Estimated {label.lower()} competition based on "
        f"{' and '.join(reasons)}. This is a relative planning signal, not an "
        "applicant count or acceptance rate."
    )
    return Estimate(label, key, explanation)
