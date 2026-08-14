"""Crawlable per-role pages, plus the sitemap and robots.txt that expose them.

Why this exists. The dashboard is one URL listing ~180 roles, so the only
queries it can win are ones about the list itself ("summer 2027 internship
list"). The queries applicants actually type are about a *role* — "Copart
software engineering intern Dallas" — and there was no page to rank for those.
This gives every open requisition its own address.

It also makes the data legible to search engines rather than only to humans:
each page carries schema.org ``JobPosting`` markup, which is the vocabulary
Google's job surfaces read. Being *eligible* is not the same as being
*included* — Google decides that, and it has requirements we cannot satisfy
from a list feed (see the description note below). Valid markup is still worth
emitting: it is how a crawler learns that "Fall 2026", "Dallas, TX" and
"posted Aug 3" are a term, a place and a date rather than three strings.

Two rules this module follows, both of which are really the same rule:

**Never invent a field.** ``validThrough`` is omitted rather than guessed —
we do not know when an employer closes a req, and a wrong expiry date either
hides a live role or advertises a dead one. ``description`` is composed only
from facts already on the record. We do not store the employer's own posting
text (enrichment reads it to classify sponsorship, then discards it), so the
honest move is a summary that says what we know and links to the source.

**Nothing on a role page may change unless the role changed.** These files are
committed every run, roughly every 30 minutes. A rendered-at timestamp in the
template would rewrite all ~180 pages on every run forever, which would bury
the repo's history in noise. So no run clock appears here; ``lastmod`` comes
from the posting's own date.

Closed roles get their pages deleted, not tombstoned. An expired posting that
keeps returning 200 is exactly what Google asks you not to do, and it wastes
crawl budget that should go to live roles.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from xml.sax.saxutils import escape, quoteattr

from . import config, filters, h1b, names, paths, sponsorship

# Slug budget. Long enough to stay readable in a search result, short enough
# to survive path limits once the docs/jobs/ prefix is added.
_MAX_SLUG = 70

_SPONSORSHIP_COPY = {
    "offers": "The posting states that visa sponsorship is available.",
    "no-sponsorship": "The posting states that visa sponsorship is not available.",
    "citizens-only": (
        "The posting states a citizenship or security-clearance requirement."
    ),
    "unknown": (
        "The posting does not say whether visa sponsorship is available. "
        "Unknown means unstated, not unavailable."
    ),
}


def slugify(text: str, limit: int = _MAX_SLUG) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (text or "").casefold()).strip("-")
    return cleaned[:limit].strip("-")


def role_slug(record: dict) -> str:
    """A stable, readable, unique filename stem for one requisition.

    The hash is taken from the store id, so the URL survives a title edit and
    two identical titles at one employer still get separate pages. Without it,
    Copart's eight "Software Engineering Intern, Dallas" reqs would collide on
    a single file and seven of them would vanish.
    """
    company = slugify(names.display(record.get("company") or "",
                                    record.get("company_slug")), 28)
    title = slugify(record.get("title") or "", 34)
    digest = hashlib.sha1(
        (record.get("id") or "").encode("utf-8"),
    ).hexdigest()[:8]
    stem = "-".join(part for part in (company, title) if part)
    return f"{stem}-{digest}" if stem else digest


def role_url(record: dict, base: str | None = None) -> str:
    base = (base or config.pages_base()).rstrip("/")
    return f"{base}/jobs/{role_slug(record)}.html"


def _posted_date(record: dict) -> str:
    return (record.get("posted_at") or "")[:10]


def _region(text: str) -> str:
    """The state out of a location fragment, or "" if it isn't one.

    Employers pad this field with site names: Copart writes "Dallas, TX -
    Headquarters", and passing that through whole put "TX - Headquarters" in
    ``addressRegion``, which is not a place. Only a real state code or state
    name is accepted; anything else yields nothing rather than a wrong value.
    """
    candidate = text.strip()
    head = re.split(r"[^A-Za-z.]+", candidate, maxsplit=1)[0].strip(".")
    if head.upper() in filters._US_CODES and head.upper() not in {"US", "USA"}:
        return head.upper()
    lowered = candidate.casefold()
    for name in filters._US_STATES:
        if lowered == name or lowered.startswith(f"{name} "):
            return name.title()
    return ""


def _location_parts(location: str) -> tuple[str, str]:
    """(locality, region) from our free-text location, best effort.

    Deliberately conservative: a fragment we cannot confidently read as a state
    is dropped rather than guessed into the wrong schema field.
    """
    text = (location or "").split(";")[0].strip()
    bits = [b.strip() for b in text.split(",") if b.strip()]
    if not bits:
        return "", ""
    if len(bits) >= 2:
        return bits[0], _region(bits[1])
    return bits[0], ""


def _summary(record: dict) -> str:
    """A description built only from what the record actually asserts."""
    company = names.display(record.get("company") or "",
                            record.get("company_slug"))
    title = record.get("title") or "Internship"
    location = record.get("location") or ""
    lines = [f"{title} at {company}."]
    if location:
        lines.append(f"Location: {location}.")

    season = record.get("season")
    if season and season != "Not stated":
        if record.get("season_inferred"):
            lines.append(
                f"Cycle: {season} — inferred from the posting date, not stated "
                f"by the employer."
            )
        else:
            lines.append(f"Cycle: {season}, as stated in the posting.")
    else:
        lines.append("The posting does not state a hiring cycle.")

    posted = _posted_date(record)
    if posted:
        lines.append(f"Posted {posted}.")
    if record.get("salary"):
        lines.append(f"Listed pay: {record['salary']}.")
    skills = record.get("skills") or []
    if skills:
        lines.append("Skills mentioned: " + ", ".join(str(s) for s in skills[:8]) + ".")
    lines.append(_SPONSORSHIP_COPY.get(record.get("sponsorship") or "unknown",
                                       _SPONSORSHIP_COPY["unknown"]))
    approvals = h1b.approvals_for(record.get("company") or "")
    if approvals:
        lines.append(
            f"{company} filed {h1b.pretty_count(approvals)} approved H-1B "
            f"petitions in the most recent USCIS data."
        )
    return " ".join(lines)


def job_posting_ld(record: dict, base: str | None = None) -> dict:
    """schema.org JobPosting for one requisition — known fields only."""
    company = names.display(record.get("company") or "",
                            record.get("company_slug"))
    location = record.get("location") or ""
    locality, region = _location_parts(location)
    address: dict = {"@type": "PostalAddress", "addressCountry": "US"}
    if locality:
        address["addressLocality"] = locality
    if region:
        address["addressRegion"] = region

    data: dict = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": record.get("title") or "Internship",
        "description": _summary(record),
        "employmentType": "INTERN",
        "hiringOrganization": {"@type": "Organization", "name": company},
        "jobLocation": {"@type": "Place", "address": address},
        "url": role_url(record, base),
    }
    posted = _posted_date(record)
    if posted:
        data["datePosted"] = posted
    identifier = record.get("requisition_id") or record.get("id")
    if identifier:
        data["identifier"] = {
            "@type": "PropertyValue", "name": company, "value": str(identifier),
        }
    if filters.is_remote(location, record.get("title") or ""):
        data["jobLocationType"] = "TELECOMMUTE"
        data["applicantLocationRequirements"] = {
            "@type": "Country", "name": "USA",
        }
    # validThrough is deliberately absent: we do not know the closing date.
    return data


def _page_head(title: str, description: str, canonical: str,
               extra: str = "") -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title>"
        f'<meta name="description" content={quoteattr(description[:300])}>'
        f'<link rel="canonical" href={quoteattr(canonical)}>'
        f'<meta property="og:title" content={quoteattr(title)}>'
        f'<meta property="og:description" content={quoteattr(description[:300])}>'
        '<meta property="og:type" content="website">'
        f'<meta property="og:url" content={quoteattr(canonical)}>'
        '<meta name="twitter:card" content="summary">'
        f"{extra}"
        "<style>"
        "body{margin:0;background:#0b0e14;color:#e8eef6;"
        "font:16px/1.65 ui-sans-serif,-apple-system,'Segoe UI',Roboto,Arial,sans-serif}"
        ".w{max-width:760px;margin:0 auto;padding:40px 20px 72px}"
        "a{color:#4d9dff}h1{font-size:28px;line-height:1.2;margin:0 0 6px}"
        ".sub{color:#8b96a8;margin:0 0 22px}"
        ".card{background:#141922;border:1px solid #2a313d;border-radius:14px;"
        "padding:20px;margin:0 0 18px}"
        "dl{display:grid;grid-template-columns:auto 1fr;gap:8px 18px;margin:0}"
        "dt{color:#8b96a8}dd{margin:0}"
        ".apply{display:inline-block;background:#2f81f7;color:#fff;font-weight:600;"
        "padding:11px 20px;border-radius:9px;text-decoration:none}"
        ".chip{display:inline-block;background:#1b212c;border:1px solid #2a313d;"
        "border-radius:999px;padding:3px 10px;margin:0 6px 6px 0;font-size:13px}"
        "ul{padding-left:20px}li{margin:4px 0}"
        "</style></head><body><div class=\"w\">"
    )


def render_role_page(record: dict, base: str | None = None) -> str:
    base = (base or config.pages_base()).rstrip("/")
    company = names.display(record.get("company") or "",
                            record.get("company_slug"))
    title = record.get("title") or "Internship"
    location = record.get("location") or "—"
    page_title = f"{title} — {company}"
    summary = _summary(record)
    ld = json.dumps(job_posting_ld(record, base), ensure_ascii=False)
    head = _page_head(
        page_title, summary, role_url(record, base),
        extra=f'<script type="application/ld+json">{ld}</script>',
    )

    rows = [("Employer", escape(company)), ("Location", escape(location))]
    season = record.get("season")
    if season and season != "Not stated":
        label = escape(season)
        if record.get("season_inferred"):
            label += ' <span class="chip">inferred from posting date</span>'
        rows.append(("Cycle", label))
    else:
        rows.append(("Cycle", "Not stated by the employer"))
    posted = _posted_date(record)
    if posted:
        rows.append(("Posted", escape(posted)))
    if record.get("salary"):
        rows.append(("Listed pay", escape(str(record["salary"]))))
    program = filters.program_type(title)
    if program:
        rows.append(("Program", escape(program)))
    if filters.is_remote(location, title):
        rows.append(("Work mode", "Remote"))

    flag = sponsorship.flag(record.get("sponsorship"))
    verdict = _SPONSORSHIP_COPY.get(record.get("sponsorship") or "unknown",
                                    _SPONSORSHIP_COPY["unknown"])
    rows.append(("Sponsorship", f"{escape(flag)} {escape(verdict)}".strip()))
    approvals = h1b.approvals_for(record.get("company") or "")
    if approvals:
        rows.append((
            "H-1B record",
            f"{escape(h1b.pretty_count(approvals))} approved petitions "
            f"({escape(h1b.window_label() or 'USCIS data')})",
        ))

    skills = record.get("skills") or []
    chips = "".join(f'<span class="chip">{escape(str(s))}</span>' for s in skills[:12])
    apply_url = record.get("url") or ""

    body = [
        f"<h1>{escape(title)}</h1>",
        f'<p class="sub">{escape(company)} · {escape(location)}</p>',
        '<div class="card"><dl>',
    ]
    for key, value in rows:
        body.append(f"<dt>{escape(key)}</dt><dd>{value}</dd>")
    body.append("</dl></div>")
    if chips:
        body.append(f'<div class="card"><strong>Skills mentioned</strong><br>{chips}</div>')
    if apply_url:
        body.append(
            f'<p><a class="apply" href={quoteattr(apply_url)} '
            f'rel="nofollow noopener">Apply on {escape(company)}’s site</a></p>'
        )
    body.append(
        '<div class="card"><strong>How this listing was produced</strong>'
        "<ul>"
        "<li>Read directly from the employer’s own applicant-tracking system, "
        "not a third-party aggregator.</li>"
        "<li>The posted date is the employer’s, not the date we found it.</li>"
        "<li>Sponsorship wording is classified from the posting text; "
        "“unknown” means the posting is silent on it.</li>"
        "<li>Listings are re-checked every 30 minutes and removed once the "
        "employer takes them down.</li>"
        "</ul></div>"
    )
    body.append(
        f'<p><a href="{escape(base)}/">← All open internships</a> · '
        f'<a href="{escape(base)}/jobs/">Browse every role</a></p>'
    )
    return head + "".join(body) + "</div></body></html>"


def render_index(records: list[dict], base: str | None = None) -> str:
    """A plain crawlable index, so role pages are reachable by link.

    A sitemap tells a crawler a URL exists; a link tells it the URL matters.
    Pages reachable only from a sitemap are treated as orphans.
    """
    base = (base or config.pages_base()).rstrip("/")
    head = _page_head(
        "Every open tech internship",
        "Direct links to every open software engineering internship the engine "
        "is currently tracking, one page per requisition.",
        f"{base}/jobs/",
    )
    items = []
    for record in sorted(
        records,
        key=lambda r: ((r.get("company") or "").casefold(), r.get("title") or ""),
    ):
        company = names.display(record.get("company") or "",
                                record.get("company_slug"))
        label = f"{record.get('title') or 'Internship'} — {company}"
        where = record.get("location") or ""
        items.append(
            f'<li><a href="{escape(role_slug(record))}.html">{escape(label)}</a>'
            + (f' <span class="chip">{escape(where)}</span>' if where else "")
            + "</li>"
        )
    return (
        head
        + "<h1>Every open tech internship</h1>"
        + f'<p class="sub">{len(items)} open requisitions, one page each.</p>'
        + f'<div class="card"><ul>{"".join(items)}</ul></div>'
        + f'<p><a href="{escape(base)}/">← Back to the dashboard</a></p>'
        + "</div></body></html>"
    )


def render_sitemap(records: list[dict], base: str | None = None) -> str:
    base = (base or config.pages_base()).rstrip("/")
    entries = [(f"{base}/", "1.0", ""), (f"{base}/jobs/", "0.8", "")]
    for record in records:
        entries.append((role_url(record, base), "0.6", _posted_date(record)))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, priority, lastmod in entries:
        parts.append("<url>")
        parts.append(f"<loc>{escape(loc)}</loc>")
        if lastmod:
            parts.append(f"<lastmod>{escape(lastmod)}</lastmod>")
        parts.append(f"<priority>{priority}</priority>")
        parts.append("</url>")
    parts.append("</urlset>")
    return "".join(parts)


def render_robots(base: str | None = None) -> str:
    base = (base or config.pages_base()).rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        # Ledger files are for the engine, not for readers or crawlers.
        "Disallow: /api/\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


def write(store_data: dict, base: str | None = None) -> int:
    """Write role pages, their index, the sitemap and robots.txt.

    Returns the number of role pages written. Pages for roles that are no
    longer open are removed, so the crawlable set always matches the live list.
    """
    base = (base or config.pages_base()).rstrip("/")
    open_records = [r for r in store_data.values() if r.get("is_open")]
    jobs_dir = os.path.join(paths.DOCS_DIR, "jobs")
    os.makedirs(jobs_dir, exist_ok=True)

    keep = set()
    for record in open_records:
        name = f"{role_slug(record)}.html"
        keep.add(name)
        page = render_role_page(record, base)
        target = os.path.join(jobs_dir, name)
        # Only rewrite when the content actually differs: these files are
        # committed every run and identical rewrites would churn git for nothing.
        if _read(target) != page:
            _write_text(target, page)

    keep.add("index.html")
    index = render_index(open_records, base)
    index_path = os.path.join(jobs_dir, "index.html")
    if _read(index_path) != index:
        _write_text(index_path, index)

    for stale in os.listdir(jobs_dir):
        if stale.endswith(".html") and stale not in keep:
            os.remove(os.path.join(jobs_dir, stale))

    _write_text(os.path.join(paths.DOCS_DIR, "sitemap.xml"),
                render_sitemap(open_records, base))
    _write_text(os.path.join(paths.DOCS_DIR, "robots.txt"), render_robots(base))
    return len(open_records)


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)
