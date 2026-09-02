"""Instant alerts for a personal fork (optional, best-effort).

The upstream project has a public, double-opt-in daily digest. A personal fork
does not need a subscriber database: one configured destination can receive the
same newly-published roles immediately. Email uses Brevo.

Each sender follows the outbox contract: return only role ids that were sent or
can never be sent. Transient failures remain queued for the next workflow run.
"""

from __future__ import annotations

import json
import os
import re
from html import escape
from urllib.parse import quote

import httpx

from . import competitiveness, config, grouping

_BREVO_URL = "https://api.brevo.com/v3/smtp/email"
_TIMEOUT = 12
_MAX_EMAIL_GROUPS = 50
_SKILL_ALIASES = {
    "c++": "cpp",
    "c#": "csharp",
    "js": "javascript",
    "ts": "typescript",
    "amazonwebservices": "aws",
    "restapis": "restapi",
}


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


def _short(value: object, limit: int) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _subject(records: list[dict], profile: dict | None = None) -> str:
    first = records[0]
    company = _short(first.get("company") or "New opening", 55)
    priority_match = next(
        (record for record in records if _priority_match(record, profile or {})),
        None,
    )
    if priority_match is not None:
        company = _short(priority_match.get("company") or company, 55)
        company = f"{company} · PRIORITY"
    count = sum(len(_ids(record)) for record in records)
    if len(records) == 1:
        title = _short(first.get("title") or "Tech internship", 80)
        season = _short(first.get("season") or "", 30)
        suffix = f" — {season}" if season else ""
        return f"[{company}] {title}{suffix}"
    companies = {str(record.get("company") or "").strip() for record in records}
    more = max(0, len(companies) - 1)
    company_label = f"{company} + {more} more" if more else company
    return f"[{company_label}] {count} new internships"


def _canonical(value: object) -> str:
    raw = str(value or "").strip().lower()
    compact = re.sub(r"[^a-z0-9+#]+", "", raw)
    return _SKILL_ALIASES.get(compact, compact)


def _applicant_profile() -> dict:
    raw = (os.environ.get("APPLICANT_PROFILE_JSON") or "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _matching_skills(record: dict, profile: dict) -> list[str]:
    profile_skills = {
        _canonical(value)
        for value in profile.get("skills") or []
        if str(value).strip()
    }
    return [
        str(value).strip()
        for value in record.get("skills") or []
        if str(value).strip() and _canonical(value) in profile_skills
    ]


def _priority_match(record: dict, profile: dict) -> bool:
    """True only for a very competitive employer and a strong resume match."""
    job_skills = [value for value in record.get("skills") or [] if str(value).strip()]
    matches = _matching_skills(record, profile)
    return (
        competitiveness.estimate(record).key == "very-high"
        and len(matches) >= 2
        and len(matches) / max(1, len(job_skills)) >= 0.6
    )


def _urgency_callout(record: dict, profile: dict) -> str:
    if not _priority_match(record, profile):
        return ""
    company = _short(record.get("company") or "this company", 80)
    matches = ", ".join(_matching_skills(record, profile)[:4])
    return (
        f"Priority match for {company}: your resume directly matches {matches}. "
        "This is a highly competitive employer, so tailor and apply promptly if the "
        "role fits your goals."
    )


def _profile_advice(record: dict, profile: dict) -> str:
    job_skills = [str(value).strip() for value in record.get("skills") or [] if str(value).strip()]
    profile_skills = {
        _canonical(value)
        for value in profile.get("skills") or []
        if str(value).strip()
    }
    matches = [value for value in job_skills if _canonical(value) in profile_skills]
    gaps = [value for value in job_skills if _canonical(value) not in profile_skills]
    query = {_canonical(value) for value in job_skills}

    evidence = []
    for item in profile.get("evidence") or []:
        item_skills = {_canonical(value) for value in item.get("skills") or []}
        evidence.append((len(query & item_skills), item))
    evidence.sort(key=lambda pair: pair[0], reverse=True)

    parts = []
    if evidence and evidence[0][0] > 0:
        item = evidence[0][1]
        name = _short(item.get("name") or "Relevant project", 60)
        proof = _short(item.get("proof") or "", 180)
        parts.append(f"Best resume proof: {name}{f' — {proof}' if proof else ''}.")
    if matches:
        parts.append(f"Direct matches: {', '.join(matches[:4])}.")
    if gaps:
        parts.append(
            f"Do not force unmatched terms such as {', '.join(gaps[:2])}; add them only if you "
            "have real supporting work."
        )
    graduation = str(profile.get("graduation") or "").strip()
    season = str(record.get("season") or "").strip()
    if graduation or season:
        details = " and ".join(
            value
            for value in (
                f"your {graduation} graduation" if graduation else "",
                f"{season} availability" if season else "",
            )
            if value
        )
        parts.append(f"Keep {details} easy to spot.")
    return " ".join(parts)


def _application_advice(record: dict, profile: dict | None = None) -> str:
    profile = profile if profile is not None else _applicant_profile()
    if profile:
        tailored = _profile_advice(record, profile)
        if tailored:
            return tailored
    skills = [str(value).strip() for value in record.get("skills") or [] if str(value).strip()]
    keywords = ", ".join(skills[:4])
    category = str(record.get("category") or "").lower()
    if any(term in category for term in ("data", "ml", "ai")):
        proof = "Put your strongest data or ML project first"
    elif any(term in category for term in ("hardware", "embedded", "robotics")):
        proof = "Lead with the project that best shows hands-on systems or hardware work"
    elif any(term in category for term in ("security", "cyber")):
        proof = "Lead with the project that best demonstrates secure engineering judgment"
    else:
        proof = "Put your strongest relevant software project first"
    keyword_note = f" Emphasize truthful evidence of {keywords}." if keywords else ""
    season = str(record.get("season") or "").strip()
    availability = f" Make your {season} availability obvious." if season else ""
    return (
        f"{proof}; quantify what you built and the result.{keyword_note}{availability} "
        "Use the listed wording only where it accurately describes your experience."
    )


def _fact(label: str, value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "unknown" or text == "Not stated":
        return ""
    return (
        '<div style="margin:3px 0">'
        f'<span style="color:#64748b">{escape(label)}:</span> {escape(_short(text, 260))}'
        "</div>"
    )


def build_email(records: list[dict]) -> tuple[str, str]:
    count = sum(len(_ids(record)) for record in records)
    profile = _applicant_profile()
    subject = _subject(records, profile)
    rows = []
    for record in records:
        company = escape(str(record.get("company") or "")[:180])
        title = escape(str(record.get("title") or "")[:400])
        url = escape(str(record.get("url") or "")[:1500], quote=True)
        resume_url = escape(
            f"{config.pages_base()}/resume.html?job={quote(str(record.get('id') or ''), safe='')}",
            quote=True,
        )
        skills = ", ".join(str(value) for value in (record.get("skills") or [])[:6])
        posted = str(record.get("posted_at") or "").split("T", 1)[0]
        facts = "".join(
            (
                _fact("Cycle", record.get("season")),
                _fact("Location", record.get("location")),
                _fact("Compensation", record.get("salary")),
                _fact(
                    "Class year",
                    f"{record.get('class_year')} (employer-stated)"
                    if record.get("class_year") else "",
                ),
                _fact("Role focus", record.get("category")),
                _fact(
                    "Competition estimate",
                    f"{competitiveness.estimate(record).label} (relative estimate)",
                ),
                _fact("Key terms", skills),
                _fact("Sponsorship", record.get("sponsorship")),
                _fact("Posted", posted),
            )
        )
        openings = len(_ids(record))
        opening_note = f" · {openings} openings" if openings > 1 else ""
        advice = escape(_application_advice(record, profile))
        urgency = _urgency_callout(record, profile)
        urgency_html = (
            '<div style="background:#fff7ed;border:1px solid #fb923c;color:#9a3412;'
            'padding:10px 12px;border-radius:8px;margin:0 0 13px;font-size:14px;'
            'line-height:1.45"><b>Apply promptly</b><br>'
            f'{escape(urgency)}</div>'
            if urgency else ""
        )
        apply_button = (
            f'<a href="{url}" style="display:inline-block;background:#111827;color:#fff;'
            'text-decoration:none;padding:10px 15px;border-radius:7px;font-weight:700">'
            "Apply now</a>"
            if url
            else ""
        )
        rows.append(
            '<section style="border:1px solid #e2e8f0;border-radius:12px;padding:18px;'
            'margin:0 0 14px;background:#fff">'
            f'<div style="color:#2563eb;font-weight:700;font-size:13px">{company}{opening_note}</div>'
            f'<h2 style="font-size:20px;line-height:1.25;margin:5px 0 12px">{title}</h2>'
            f'{urgency_html}'
            f'<div style="font-size:14px;line-height:1.45">{facts}</div>'
            '<div style="background:#f8fafc;border-left:3px solid #2563eb;padding:10px 12px;'
            'margin:14px 0;font-size:14px;line-height:1.45">'
            f'<b>Your application angle</b><br>{advice}</div>'
            f'<div style="display:flex;gap:9px;flex-wrap:wrap">{apply_button}'
            f'<a href="{resume_url}" style="display:inline-block;border:1px solid #94a3b8;'
            'color:#0f172a;text-decoration:none;padding:9px 14px;border-radius:7px;font-weight:700">'
            "Tailor resume</a></div></section>"
        )
    dashboard = escape(config.pages_base() + "/", quote=True)
    first_company = escape(_short(records[0].get("company") or "New internships", 80))
    heading = first_company if len(records) == 1 else f"{first_company} and more"
    intro = f"{count} newly published opening{'s' if count != 1 else ''}"
    html = (
        '<div style="font:15px system-ui,sans-serif;max-width:680px;margin:auto;color:#0f172a">'
        '<div style="color:#2563eb;font-size:12px;font-weight:800;letter-spacing:.08em">'
        "NEW INTERNSHIP ALERT</div>"
        f'<h1 style="font-size:26px;margin:5px 0">{heading}</h1>'
        f'<p style="color:#64748b;margin:0 0 18px">{intro}</p>'
        + "".join(rows)
        + f'<p style="font-size:13px"><a href="{dashboard}">View every open internship</a></p>'
        '<p style="color:#94a3b8;font-size:12px">Advice is based on listing keywords. '
        "Only claim skills and experience you actually have.</p></div>"
    )
    return subject, html


def _post_email(subject: str, html: str) -> str:
    """Post one transactional email and return Brevo's delivery-tracking id."""
    response = httpx.post(
        _BREVO_URL,
        headers={"api-key": os.environ["BREVO_API_KEY"], "Content-Type": "application/json"},
        json={
            "sender": _sender(os.environ["MAIL_FROM"]),
            "to": [{"email": os.environ["ALERT_EMAIL_TO"].strip()}],
            "subject": subject,
            "htmlContent": html,
        },
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return str(response.json().get("messageId") or "")


def send_test_email() -> str:
    """Send a harmless configuration test without touching alert state."""
    if not email_configured():
        raise RuntimeError("BREVO_API_KEY, MAIL_FROM, and ALERT_EMAIL_TO are required")
    dashboard = escape(config.pages_base() + "/", quote=True)
    return _post_email(
        "Internship Alerts email test",
        (
            '<div style="font:15px system-ui,sans-serif;max-width:640px;margin:auto">'
            "<h2>Your internship email alerts are working</h2>"
            "<p>This is a one-time setup test. Future messages will only be sent when "
            "new internship openings are published.</p>"
            f'<p><a href="{dashboard}">Open the internship dashboard</a></p></div>'
        ),
    )


def send_preview_email(record: dict) -> str:
    """Send the production layout for one real role without advancing alert state."""
    if not email_configured():
        raise RuntimeError("BREVO_API_KEY, MAIL_FROM, and ALERT_EMAIL_TO are required")
    subject, html = build_email([record])
    html = html.replace("NEW INTERNSHIP ALERT", "EMAIL FORMAT PREVIEW", 1)
    return _post_email(f"[PREVIEW] {subject}", html)


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
