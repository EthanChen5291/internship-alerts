"""Employer-verified, non-finance programs aimed specifically at underclassmen."""

from __future__ import annotations

import re

# Kept deliberately small. A program belongs here only while a current official
# employer page both names the program and states its underclassman audience.
PROGRAMS = (
    {
        "key": "microsoft-explore",
        "name": "Microsoft Explore",
        "company": "microsoft",
        "audience": "First- and second-year students",
        "official_url": "https://careers.microsoft.com/v2/global/en/exploremicrosoft",
        "verified_at": "2026-09-02",
        "title_re": r"\b(?:explore microsoft|microsoft explore|explore program)\b",
    },
    {
        "key": "nvidia-ignite",
        "name": "NVIDIA Ignite",
        "company": "nvidia",
        "audience": "Current freshmen and sophomores",
        "official_url": "https://www.nvidia.com/en-us/about-nvidia/careers/university-recruiting/",
        "verified_at": "2026-09-02",
        "title_re": r"\bignite\b",
    },
    {
        "key": "duolingo-thrive",
        "name": "Duolingo Thrive",
        "company": "duolingo",
        "audience": "Rising juniors",
        "official_url": "https://careers.duolingo.com/?type=Thrive%20Program",
        "verified_at": "2026-09-02",
        "title_re": r"\bthrive\b",
    },
)


def match(company: str | None, title: str | None) -> dict | None:
    company_key = re.sub(r"[^a-z0-9]+", " ", (company or "").casefold()).strip()
    title_text = title or ""
    for program in PROGRAMS:
        if company_key == program["company"] and re.search(
            program["title_re"], title_text, re.IGNORECASE,
        ):
            return program
    return None


def open_programs(store_data: dict) -> dict[str, dict]:
    """One representative live posting per watched program."""
    found: dict[str, dict] = {}
    for record in store_data.values():
        key = record.get("underclass_program_key")
        if record.get("is_open") and key and key not in found:
            found[key] = record
    return found
