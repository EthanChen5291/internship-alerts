"""Conservative, deterministic resume tailoring.

Tailoring is intentionally limited to ordering existing skills and bullets by
their relevance to a job. It never rewrites a sentence or invents a keyword,
claim, employer, metric, or technology.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

_WORD = re.compile(r"[a-z0-9+#.]{2,}")
_GENERIC = {
    "and", "the", "for", "with", "intern", "internship", "engineering",
    "engineer", "software", "summer", "fall", "role", "technology",
}


def keywords(job: dict) -> list[str]:
    explicit = [str(value).strip() for value in (job.get("skills") or []) if value]
    words = _WORD.findall(
        " ".join(str(job.get(key) or "") for key in ("title", "category")).lower()
    )
    seen: set[str] = set()
    result = []
    for value in [*explicit, *words]:
        normalized = value.casefold()
        if normalized not in seen and normalized not in _GENERIC:
            seen.add(normalized)
            result.append(value)
    return result


def _score(text: str, terms: list[str]) -> int:
    haystack = _WORD.findall(text.casefold())

    def contains(term: str) -> bool:
        needle = _WORD.findall(term.casefold())
        if not needle:
            return False
        width = len(needle)
        return any(haystack[index:index + width] == needle
                   for index in range(len(haystack) - width + 1))

    return sum(3 if contains(term) else 0 for term in terms)


def _stable_reorder(values: list, score) -> list:
    return [value for _index, value in sorted(
        enumerate(values), key=lambda item: (-score(item[1]), item[0])
    )]


def tailor(resume: dict, job: dict) -> dict:
    """Move relevant bullets/skills without changing section or entry order."""
    result = copy.deepcopy(resume)
    terms = keywords(job)
    for group in result.get("skills") or []:
        items = list(group.get("items") or [])
        group["items"] = _stable_reorder(items, lambda value: _score(str(value), terms))
    for section in ("experience", "projects", "honors"):
        for item in result.get(section) or []:
            bullets = list(item.get("bullets") or [])
            item["bullets"] = _stable_reorder(
                bullets,
                lambda value: _score(
                    str(value.get("text") if isinstance(value, dict) else value), terms
                ),
            )
    result["target"] = {
        "job_id": job.get("id"),
        "company": job.get("company"),
        "title": job.get("title"),
        "keywords": terms,
    }
    return result


def _safe(value: object) -> str:
    return (str(value or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def write_pdf(resume: dict, output: str | Path) -> None:
    """Write a clean ATS-readable PDF from an already-tailored resume."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "Name", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18,
        leading=20, alignment=TA_CENTER, spaceAfter=3,
    )
    contact_style = ParagraphStyle(
        "Contact", parent=styles["Normal"], fontSize=8.7, leading=11,
        alignment=TA_CENTER, textColor=colors.HexColor("#333333"), spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5,
        leading=12, textColor=colors.HexColor("#17365D"), spaceBefore=5, spaceAfter=2,
        borderWidth=0, borderPadding=0,
    )
    item_style = ParagraphStyle(
        "Item", parent=styles["Normal"], fontSize=9.2, leading=11.2, spaceAfter=1,
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=item_style, leftIndent=12, firstLineIndent=0, bulletIndent=2,
        spaceAfter=0.5,
    )
    doc = SimpleDocTemplate(
        str(output), pagesize=LETTER, rightMargin=0.55 * inch, leftMargin=0.55 * inch,
        topMargin=0.42 * inch, bottomMargin=0.42 * inch,
        title=str(resume.get("name") or "Resume"), author=str(resume.get("name") or ""),
    )
    story = [Paragraph(_safe(resume.get("name")), name_style)]
    contact = resume.get("contact") or {}
    contact_line = " | ".join(
        _safe(contact.get(key))
        for key in ("email", "phone", "location", "linkedin", "github", "website")
        if contact.get(key)
    )
    if contact_line:
        story.append(Paragraph(contact_line, contact_style))
    if resume.get("summary"):
        story.extend([
            Paragraph("SUMMARY", section_style),
            Paragraph(_safe(resume["summary"]), item_style),
        ])

    def heading(title: str):
        story.append(Paragraph(title, section_style))

    if resume.get("education"):
        heading("EDUCATION")
        for item in resume["education"]:
            left = " - ".join(filter(None, [_safe(item.get("school")), _safe(item.get("degree"))]))
            right = " - ".join(filter(None, [_safe(item.get("start")), _safe(item.get("end"))]))
            line = f"<b>{left}</b>" + (f"<br/><font size='8'>{right}</font>" if right else "")
            story.append(Paragraph(line, item_style))
            for detail in item.get("details") or []:
                story.append(Paragraph(_safe(detail), bullet_style, bulletText="-"))

    if resume.get("skills"):
        heading("SKILLS")
        for group in resume["skills"]:
            story.append(Paragraph(
                f"<b>{_safe(group.get('category'))}:</b> "
                + ", ".join(_safe(value) for value in (group.get("items") or [])),
                item_style,
            ))

    def entries(title: str, key: str):
        if not resume.get(key):
            return
        heading(title)
        for item in resume[key]:
            primary = item.get("role") or item.get("name") or ""
            secondary = item.get("company") or ""
            dates = " - ".join(filter(None, [_safe(item.get("start")), _safe(item.get("end"))]))
            title_line = " - ".join(filter(None, [_safe(primary), _safe(secondary)]))
            body = [Paragraph(
                f"<b>{title_line}</b>" + (f"<br/><font size='8'>{dates}</font>" if dates else ""),
                item_style,
            )]
            bullets = [
                ListItem(Paragraph(_safe(value), bullet_style), leftIndent=10)
                for value in (item.get("bullets") or [])
            ]
            if bullets:
                body.append(ListFlowable(bullets, bulletType="bullet", bulletFontSize=5, leftIndent=12))
            story.extend([KeepTogether(body), Spacer(1, 2)])

    entries("EXPERIENCE", "experience")
    entries("PROJECTS", "projects")
    doc.build(story)
