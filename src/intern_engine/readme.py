"""Render the public-facing README.md (the product) + a CSV tracker.

Plain, professional, human voice. No decorative emojis. Sections are exactly the
configured cycles, in order. Roles are sorted by their PUBLISHED date (newest on
top), and that date is frozen per role so the page behaves like a ladder.
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from . import config, filters, h1b, paths, priority, radar, sponsorship


def _engine_metrics() -> str:
    """One-line observability summary from the last run, if available."""
    try:
        with open(paths.STATS_PATH, encoding="utf-8") as f:
            stats = json.load(f)
    except (OSError, ValueError):
        return ""
    sources = len(stats.get("companies_by_source", {}))
    total = stats.get("companies_total", 0)
    ok = stats.get("fetched_ok", 0)
    # Both denominators, because quoting only the attempted-boards rate reads as
    # "we polled everything" when quarantined endpoints were never tried.
    line = (
        f"_Engine (last run): {ok:,} of {total:,} registered boards returned "
        f"successfully across {sources} ATS platforms "
        f"({int(stats.get('fetch_success_rate', 0) * 100)}% of boards attempted, "
        f"{int(stats.get('fetch_success_rate_registry', 0) * 100)}% of the full "
        f"registry) · completed in {stats.get('duration_seconds', 0)}s"
    )
    partial = stats.get("snapshots_partial")
    if partial:
        line += (
            f" · {partial} board(s) returned a capped result set, so their roles "
            "were not eligible to be closed this run"
        )
    coverage = stats.get("posted_date_coverage")
    if coverage is not None:
        line += f" · employer or source-derived date on {int(coverage * 100)}% of open roles"
    return line + "._"


def _now_str() -> str:
    return datetime.now(UTC).strftime("%b %d, %Y at %H:%M UTC")


def _md_cell(text: str) -> str:
    return (text or "—").replace("|", "/").replace("\n", " ").strip() or "—"


def _short_location(loc: str, limit: int = 40) -> str:
    loc = _md_cell(loc)
    if len(loc) <= limit:
        return loc
    parts = [p.strip() for p in loc.replace(";", ",").split(",") if p.strip()]
    if len(parts) > 1:
        return f"{parts[0]} +{len(parts) - 1} more"
    return loc[: limit - 1].rstrip() + "…"


def _date_str(record: dict) -> str:
    """The published date string we sort/display by (frozen per role)."""
    # Display only a REAL published date (no first_seen fallback) — undated -> dash.
    return record.get("posted_at") or ""


def _sort_key(record: dict):
    # Dated roles first (newest), undated sink to the bottom; first_seen breaks
    # ties so undated roles still have a stable, newest-first order.
    return ((record.get("posted_at") or "")[:10], (record.get("first_seen_at") or "")[:19])


def _pretty_date(record: dict) -> str:
    iso = _date_str(record)
    if not iso:
        return "—"
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %d, %Y")
    except ValueError:
        return iso[:10]


def _is_new(record: dict, hours: int = 48) -> bool:
    seen = (record.get("first_seen_at") or "")[:19]
    if not seen:
        return False
    try:
        seen_dt = datetime.strptime(seen, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return False
    return datetime.now(UTC) - seen_dt <= timedelta(hours=hours)


def _cells(record: dict) -> tuple[str, str, str, str, str, str]:
    company = _md_cell(record.get("company"))
    if h1b.badge(h1b.approvals_for(record.get("company") or "")):
        company += " ✓"
    title = _md_cell(record.get("title"))
    is_open = record.get("is_open", True)
    badges = " ".join(
        b for b in (sponsorship.flag(record.get("sponsorship")),
                    "🏠" if filters.is_remote(record.get("location") or "",
                                              record.get("title") or "") else "",
                    "🆕" if _is_new(record) and is_open else "")
        if b
    )
    if badges:
        title = f"{title} {badges}"
    url = record.get("url") or ""
    apply = "Closed" if not is_open else (f"[Apply]({url})" if url else "—")
    return (
        company, title,
        _md_cell(record.get("category")),
        _short_location(record.get("location")),
        _pretty_date(record),
        apply,
    )


def _row(record: dict, cycle: str | None = None) -> str:
    company, title, category, location, posted, apply = _cells(record)
    # A multi-cycle posting appears under each cycle it names. Naming the OTHER
    # cycles here explains why the same title shows up twice — repeating this
    # section's own cycle would just be noise.
    others = [s for s in (record.get("seasons") or []) if s != cycle]
    if len(record.get("seasons") or []) > 1 and others:
        title += f" _(also open for {', '.join(others)})_"
    return f"| {company} | {title} | {category} | {location} | {posted} | {apply} |"


def _rolling_row(record: dict) -> str:
    """A row in the cycle-not-stated lane: the guess gets its own column."""
    company, title, category, location, posted, apply = _cells(record)
    likely = f"~{_md_cell(record.get('season'))}"
    return (f"| {company} | {title} | {likely} | {category} | {location} | "
            f"{posted} | {apply} |")


def _region_label(cfg: dict) -> str:
    if not config.restrict_region(cfg):
        return "Worldwide"
    parts = []
    if config.want_us(cfg):
        parts.append("United States")
    if config.want_canada(cfg):
        parts.append("Canada")
    return " & ".join(parts) if parts else "United States"


def _company_count() -> tuple[int, int]:
    """(board endpoints, unique employers).

    They differ — a company with two ATS accounts is two endpoints — and
    calling the endpoint count "companies" overstated the employer reach by
    ~85. Both numbers are real; they just answer different questions.
    """
    try:
        with open(paths.COMPANIES_PATH, encoding="utf-8") as f:
            companies = json.load(f)
    except (OSError, ValueError):
        return 0, 0
    return len(companies), len({(c.get("name") or "").strip().lower() for c in companies})


def _raw_feed_url() -> str:
    """The feed served straight from the repo (no Pages dependency)."""
    return f"https://raw.githubusercontent.com/{config.repo_slug()}/main/docs/feed.xml"


def _email_subscribe_url() -> str:
    """One-click feed-to-email signup, prefilled with our feed."""
    return f"https://feedrabbit.com/subscriptions/new?url={quote(_raw_feed_url(), safe='')}"


def _header(cfg: dict, total_open: int, companies: int, new_week: int,
            employers: int | None = None,
            shown: int | None = None, stated: int | None = None,
            inferred: int | None = None) -> list[str]:
    """The README's opening block.

    `total_open` is every open role (what the API and dashboard report); `shown`
    is how many survived the per-company cap in these tables. They differ, and
    the page used to print only the smaller one under the same wording as the
    API's larger one — so the two disagreed with no way to tell which was real.

    `stated` / `inferred` split the total by cycle EVIDENCE. Leading with that
    split is the whole pitch: a smaller number you can trust beats a bigger one
    that quietly includes 46% guesses.
    """
    count_phrase = f"{total_open} open roles"
    if shown is not None and shown != total_open:
        count_phrase = f"{total_open} open roles ({shown} listed below)"
    region = _region_label(cfg)
    cycles = config.cycles(cfg)
    cycles_phrase = " and ".join(cycles)
    pages = config.pages_base()

    repo = config.repo_slug()
    stats_url = quote(f"{pages}/api/stats.json", safe="")
    return [
        "# Summer 2027 Tech Internships",
        "",
        f"[![CI](https://github.com/{repo}/actions/workflows/ci.yml/badge.svg)]"
        f"(https://github.com/{repo}/actions/workflows/ci.yml) "
        f"![Open roles](https://img.shields.io/badge/dynamic/json?label=open%20roles"
        f"&query=open_total&url={stats_url}&color=2f81f7) "
        "![Updates](https://img.shields.io/badge/updates-every%20hour-3fb950) "
        f"[![RSS](https://img.shields.io/badge/RSS-subscribe-e67e22)]({pages}/feed.xml)",
        "",
        "A self-updating engine that tracks tech internships so you don't have to. "
        "Instead of refreshing a dozen career pages by hand, it reads company hiring "
        "feeds directly and keeps one live list, newest roles on top, refreshed "
        "automatically throughout the day.",
        "",
        f"**{count_phrase} · {new_week} new this week · "
        f"{(employers or companies):,} employers tracked · updated {_now_str()}**",
        "",
        (f"_{stated} have a cycle the employer stated · {inferred} are recent "
         "postings whose cycle isn't stated (listed separately, never mixed in)._"
         if stated is not None and inferred else ""),
        "",
        "**⭐Star this repo⭐** to save it and get updates when new roles are added.",
        "",
        f"**Live:** [dashboard]({pages}/) · [RSS feed]({pages}/feed.xml) "
        f"(instant alerts in any RSS app) · [JSON API]({pages}/api/jobs.json)",
        "",
        # Native signup posts into our own Supabase list (RLS: insert-only).
        # The Feedrabbit link is the zero-account fallback via the raw feed URL,
        # which works even when GitHub Pages is off.
        f"**🔔 New roles in your inbox:** [subscribe by email]({pages}/#subscribe) "
        "- one email a day, only when new internships actually appeared, "
        f"unsubscribe from any email in two clicks. (Prefer RSS-to-email? "
        "[Feedrabbit works too]"
        f"({_email_subscribe_url()}).)",
        "",
        "## What this is",
        "",
        "This is an engine, not a hand-kept list. It polls company career feeds several "
        "times a day, finds the internships, removes duplicates, and rebuilds this page "
        "on its own. Every link comes straight from the source, so it's real and "
        "current, not a stale list someone forgot to update (speed matters).",
        "",
        "## What makes this different",
        "",
        "- **📅 [Drop Radar](#drop-radar)** - "
        "a forecast of **what's coming**: each marquee company's typical opening "
        "window, replaced by the real drop date the moment the engine catches it "
        "live. Windows are estimates and labelled as such; only dates the engine "
        "observed itself are marked verified.",
        "- **Visa intel, computed** - 🇺🇸 / 🛂 flags detected automatically from every "
        "job description, plus ✓ for employers with a real H-1B track record "
        "(official USCIS data, FY2022-23 - a history, not a promise). The big "
        "lists crowdsource this by hand; here it's code. Most postings say nothing "
        "either way, and those are shown as unknown rather than guessed.",
        "- **A date on nearly every role** - taken from the job portal itself where "
        "the portal states one, so newest-first actually means newest. The exact "
        "coverage figure is printed at the bottom of this page every run.",
        "- **Skill tags + pay, extracted** - every posting's text is scanned for the "
        "stack it wants (Python, C++, PyTorch, ...) and the pay it states - "
        f"searchable on the [dashboard]({pages}/), included in the CSV and API.",
        f"- **Alerts your way** - [email digests]({pages}/#subscribe) or "
        f"[RSS]({pages}/feed.xml) (point any reader, or a Slack/Discord RSS "
        f"integration, at it) - plus a [live dashboard]({pages}/) with search, "
        "filters, and a saved-roles list that never leaves your browser.",
        f"- **An engine, not a spreadsheet** - {companies:,} job-board endpoints "
        f"({(employers or companies):,} distinct employers; some run more than one "
        "board) polled every hour across 12 ATS platforms, full source and tests "
        "in this repo.",
        "",
        "## Scope",
        "",
        "- **Roles:** Software Engineering, Data Science & Machine Learning "
        "(and closely related technical internships)",
        f"- **Region:** {region}"
        + (" (primary), with a separate International section"
           if config.include_international(cfg) else ""),
        f"- **Cycles:** {cycles_phrase}",
        "",
        "## About",
        "",
        "I'm an international student studying in the United States, so I built "
        "this for the search I'm doing myself. The list is US roles only for now - "
        "that's where I'm searching. Use it to spot roles early and apply before "
        "they fill up - being first genuinely helps.",
        "",
        "## Where this is going",
        "",
        "I'm building this in the open and adding to it as it grows. Recently "
        "shipped: **email alerts**, the **Drop Radar**, **auto-detected sponsorship "
        "flags**, and the **live dashboard**. Next up: personalized alerts (pick "
        "your categories), per-company hiring pages, and a ghost-posting detector. "
        "If it helps you, a star means a lot and tells me to keep going.",
        "",
        "## How to use",
        "",
        "- Roles are grouped by cycle below - **newest posting on top, oldest at the bottom.**",
        "- A cycle section holds only roles whose **employer stated that cycle**. "
        "Postings that don't name one are in *Recently posted — cycle not stated* "
        "further down, with our guess marked `~`. Same quality bar, different "
        "amount of evidence.",
        "- The **Posted** column is the date the company published the role.",
        "- **Flags:** 🇺🇸 = requires U.S. citizenship or a security clearance · "
        "🛂 = the posting says it won't sponsor a work visa · 🏠 = the location "
        "says remote · 🆕 = spotted in the last 48 hours. Sponsorship flags are "
        "detected automatically from each job description - treat them as a "
        "strong hint and confirm on the posting.",
        f"- **✓ after a company name** = a real H-1B track record: USCIS approved "
        f"{h1b.BADGE_THRESHOLD}+ petitions for that employer in "
        f"{h1b.window_label() or 'recent fiscal years'} (matched automatically "
        "against the official [H-1B Employer Data Hub]"
        "(https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub)). "
        "No ✓ doesn't mean they won't sponsor - it means we can't prove they have.",
        "- Track your applications with [`data/internships.csv`](data/internships.csv) "
        "(opens in Excel / Google Sheets).",
        "- Missing a company? Adding one takes a single line, see "
        "[CONTRIBUTING.md](CONTRIBUTING.md).",
        "",
        "---",
        "",
    ]


def _footer() -> list[str]:
    return [
        "---",
        "",
        "## Hiring timeline",
        "",
        "Internships posted per week, from each role's real published date - "
        "redrawn automatically on every run. When this line takes off, "
        "recruiting season is open:",
        "",
        "<picture>",
        '  <source media="(prefers-color-scheme: dark)" srcset="docs/trends-dark.svg">',
        '  <img alt="Internships posted per week, drawn from real published dates" '
        'src="docs/trends-light.svg">',
        "</picture>",
        "",
        "## How it stays current",
        "",
        "A small Python engine reads public company hiring feeds directly, keeps the "
        "roles that match the scope above, de-duplicates across sources, records each "
        "role's published date once (so it never shifts), and regenerates this page "
        "through GitHub Actions. It polls every company concurrently (async) with "
        "retry/backoff and per-host rate limits. The full source is in this repo.",
        "",
        _engine_metrics(),
        "",
        "## How this list is built",
        "",
        "[METHODOLOGY.md](METHODOLOGY.md) documents exactly what every label "
        "claims — what separates a stated cycle from an inferred one, what the ✓ "
        "H-1B badge does and doesn't mean, how a role gets closed, and which "
        "limitations are known. Anything on this page that doesn't match the "
        "code is a bug worth reporting.",
        "",
        "## Contributing",
        "",
        "Adding a company takes one line, see [CONTRIBUTING.md](CONTRIBUTING.md), "
        "or just [open a request](../../issues/new?template=add-company.yml) with "
        "the board URL. **Spotted something wrong?** "
        "[Report the exact field](../../issues/new?template=wrong-data.yml) — "
        "wrong country, wrong cycle, closed role, bad sponsorship flag. Those "
        "reports usually fix a rule, which fixes every other role too.",
        "",
        "Also here: [PRIVACY.md](PRIVACY.md) (what the email list stores — an "
        "address and nothing else) · [SECURITY.md](SECURITY.md) · "
        "[ARCHITECTURE.md](ARCHITECTURE.md) · [MIT licensed](LICENSE).",
        "",
        "Built by one student with AI assistance, in the open. The part that "
        "matters isn't who typed it — it's that the rules, the tests, and every "
        "run's output are all public and checkable.",
        "",
        "## Note on dates",
        "",
        "The **Posted** column shows when a role was published, with the newest at the "
        "top. I pull the posting date straight from each job portal, but a lot of them "
        "don't expose one publicly, so those rows show a dash (—) for now instead of a "
        "guessed date. The ones that do publish a date are dated. Know the real date for "
        "a dashed role? Open a PR and I'll merge it.",
        "",
        "Roles can close at any time, so always confirm on the company's own site before "
        "applying.",
        "",
    ]


def _select(rows: list[dict], limit, per_company) -> list[dict]:
    """Pick which rows to show, then order them newest-first for display.

    1) cap each company to `per_company` (variety, newest kept),
    2) if still over `limit`, keep the most sought-after companies first,
    3) display newest on top.
    """
    rows = sorted(rows, key=_sort_key, reverse=True)
    if per_company:
        seen: dict[str, int] = {}
        capped = []
        for r in rows:
            c = (r.get("company") or "").strip().lower()
            if seen.get(c, 0) >= per_company:
                continue
            seen[c] = seen.get(c, 0) + 1
            capped.append(r)
        rows = capped
    if limit and len(rows) > limit:
        rows = sorted(rows, key=lambda r: priority.rank(r.get("company")))[:limit]
    return sorted(rows, key=lambda r: _date_str(r)[:10], reverse=True)


def _region_of(record: dict) -> str:
    return "US" if filters.is_united_states(record.get("location") or "") else "International"


def _new_this_week(open_jobs: list[dict]) -> int:
    cutoff = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    return sum(1 for r in open_jobs if (r.get("first_seen_at") or "") >= cutoff)


def _radar_section(store_data: dict, cycle: str, cap: int = 30) -> list[str]:
    """The Drop Radar: which companies haven't posted yet, and when to expect
    them — from the engine's own observed dates + hand-verified opening windows.

    The README teaser leads with the FORECAST (waiting, soonest first) — that's
    the radar's unique value; "open now" rows just echo the list above — then
    shows a few recent drops as proof the forecast is real. The dashboard keeps
    the full, searchable list."""
    rows = radar.rows(store_data, cycle)
    if not rows:
        return []
    waiting = [r for r in rows if r["status"] == "waiting"]
    opened = [r for r in rows if r["status"] == "open"]
    dropped = [r for r in rows if r["status"] == "dropped"]
    # Forecast first (what to watch for), then a handful of recent drops as proof.
    ordered = waiting + opened[:8] + dropped[:4]

    pages = config.pages_base()
    verified = sum(1 for r in rows if r.get("source") == "engine")
    lines = [
        '<a id="drop-radar"></a>',
        "",
        f"## 📅 Drop Radar — when companies usually post for {cycle}",
        "",
        "Stop refreshing career pages. 🎯 = the employer's **own posted date**, "
        "read from their careers API. (We may have discovered the role after it "
        "went live — the date is the employer's, not our discovery time.) "
        "The rest are typical opening "
        "**months**, hand-checked against each company's careers page and "
        "public recruiting guides. ✅ = already live in the list above.",
        "",
        "> **Heads up:** companies trend *earlier* every cycle, and \"~Aug\" is a "
        "month, not a day. Treat \"expected\" as when to **start watching**, and "
        "\"rolling\" companies as worth checking year-round.",
        "",
        "| Company | Typical opening | Expected this cycle | Status |",
        "|---|---|---|---|",
    ]
    for r in ordered[:cap]:
        if r["status"] == "open":
            status = f"✅ [open now]({r['url']})" if r["url"] else "✅ open now"
        elif r["status"] == "dropped":
            status = "🗓️ dropped"
        else:
            status = "⏳ waiting"
        mark = "🎯 " if r.get("source") == "engine" else ""
        lines.append(
            f"| {mark}{_md_cell(r['company'])} | {radar.pretty_last(r)} | "
            f"{radar.pretty_expected(r)} | {status} |"
        )
    verified_note = (f"**{verified}** dated from our own live observations 🎯 "
                     "(this grows every cycle). " if verified else "")
    lines.extend([
        "",
        f"_{len(rows)} companies on the [full radar]({pages}/#radar). {verified_note}"
        "\"~Aug\" = hand-verified typical month, not a promise of the day; "
        "\"rolling\" = posts year-round; \"waiting\" = not seen in our tracked "
        "feeds yet, not a guarantee it isn't out somewhere else._",
        "",
    ])
    return lines


def _closed_section(store_data: dict, cycles: list[str],
                    days: int = 14, cap: int = 40) -> list[str]:
    """Roles that recently closed, kept visible (collapsed) so nobody wastes an
    application on a listing that just died. Only tracked cycles appear here —
    an off-cycle tombstone (text-verified "Summer 2026") was never on the list,
    so it has no business in its obituary either."""
    cutoff = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    closed = [
        r for r in store_data.values()
        if not r.get("is_open") and (r.get("closed_at") or "") >= cutoff
        and r.get("season") in cycles
    ]
    if not closed:
        return []
    closed.sort(key=lambda r: r.get("closed_at") or "", reverse=True)
    closed = closed[:cap]
    lines = [
        "<details>",
        f"<summary><strong>Recently closed</strong> — {len(closed)} roles that "
        f"left the list in the last {days} days</summary>",
        "",
        "_Why each one left is in the last column, because the two reasons carry "
        "different evidence. **Gone from feed** = two consecutive complete reads "
        "of the employer's board no longer returned it (strong, but not the "
        "employer telling us directly). **Out of scope** = still posted, but it no longer "
        "passes our filters — our call, not theirs. **Not recorded** = closed "
        "before we started tracking the reason._",
        "",
        "| Company | Role | Cycle | Closed | Why |",
        "|---|---|---|---|---|",
    ]
    _WHY = {
        "gone-from-feed": "gone from feed",
        "out-of-scope": "out of scope",
    }
    for r in closed:
        closed_on = (r.get("closed_at") or "")[:10]
        why = _WHY.get(r.get("closed_reason"), "not recorded")
        lines.append(
            f"| {_md_cell(r.get('company'))} | {_md_cell(r.get('title'))} "
            f"| {_md_cell(r.get('season'))} | {closed_on} | {why} |"
        )
    lines.extend(["", "</details>", ""])
    return lines


def generate(store_data: dict) -> dict:
    cfg = config.load_config()
    cycles = config.cycles(cfg)
    per_company = config.max_per_company(cfg)

    open_jobs = [r for r in store_data.values() if r.get("is_open")]
    stated_open = [r for r in open_jobs if not r.get("season_inferred")]
    inferred_open = [r for r in open_jobs if r.get("season_inferred")]

    all_jobs = list(store_data.values())
    stated = [r for r in all_jobs if not r.get("season_inferred")]
    inferred = [r for r in all_jobs if r.get("season_inferred")]

    groups: dict[tuple[str, str], list[dict]] = {}
    for r in stated:
        # A multi-cycle posting ("Fall 2026/Summer 2027") belongs in EVERY
        # cycle it states — that's the point of keeping the full set.
        for cyc in (r.get("seasons") or [r.get("season", "")]):
            groups.setdefault((_region_of(r), cyc), []).append(r)

    sections: list[tuple[str, str, list[dict]]] = []
    displayed: list[dict] = []
    seen_display: set[str] = set()
    for region in ("US", "International"):
        for cycle in cycles:
            rows = _select(
                groups.get((region, cycle)) or [],
                config.section_limit(cfg, cycle),
                per_company,
            )
            if rows:
                heading = cycle if region == "US" else f"{cycle} (International)"
                sections.append((heading, cycle, rows))
                for r in rows:
                    if r.get("id") not in seen_display:
                        seen_display.add(r.get("id"))
                        displayed.append(r)

    rolling_rows = _select(inferred, None, per_company)
    shown_open = sum(1 for r in displayed if r.get("is_open")) + sum(1 for r in rolling_rows if r.get("is_open"))

    endpoints, employers = _company_count()
    lines = _header(cfg, len(open_jobs), endpoints,
                    _new_this_week(open_jobs), employers=employers,
                    shown=shown_open, stated=len(stated_open), inferred=len(inferred_open))
    for heading, cycle, rows in sections:
        lines.append(f"## {heading}  ({len(rows)} employer-stated)")
        lines.append("")
        lines.append("| Company | Role | Category | Location | Posted | Apply |")
        lines.append("|---|---|---|---|---|---|")
        lines.extend(_row(r, cycle) for r in rows)
        lines.append("")

    if rolling_rows:
        lines.extend([
            f"## Recently posted — cycle not stated  ({len(rolling_rows)} roles)",
            "",
            "These postings don't name a cycle, so we won't pretend they did. "
            "They're recent tech internships whose likely cycle (the ~ column) "
            "is inferred from the posting date alone — often exactly the "
            "early drops worth applying to first, just not *proven* to belong "
            "to a cycle. When a posting's own text later states one, the role "
            "moves up into that section.",
            "",
            "| Company | Role | Likely cycle | Category | Location | Posted | Apply |",
            "|---|---|---|---|---|---|---|",
        ])
        lines.extend(_rolling_row(r) for r in rolling_rows)
        lines.append("")

    if not displayed and not rolling_rows:
        lines.append(
            "_No matching roles right now, the list fills as companies post. "
            "Star it and check back._"
        )
        lines.append("")

    lines.extend(_radar_section(store_data, cycles[0]))
    lines.extend(_closed_section(store_data, cycles))
    lines.extend(_footer())

    with open(paths.README_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # The CSV is the machine-readable export: EVERY open role belongs in it,
    # not just the rows that survived the README's per-company display cap.
    _write_csv(sorted(open_jobs, key=lambda r: _date_str(r)[:10], reverse=True))

    return {"open": shown_open, "companies": employers}


def _csv_safe(value):
    """Neutralize spreadsheet formula injection.

    Excel, Sheets and LibreOffice all execute a cell that opens with =, +, -
    or @. Job titles and company names come from third parties, so a posting
    titled `=HYPERLINK(...)` would run in the spreadsheet of anyone who opened
    our CSV. Prefixing an apostrophe makes the cell inert text; nothing is lost
    for ordinary values, which never start with those characters.
    """
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _write_csv(open_jobs: list[dict]) -> None:
    fields = [
        "company", "title", "season", "season_inferred", "seasons", "program",
        "remote", "category", "location", "sponsorship", "h1b_approvals",
        "salary", "skills", "posted_at", "posted_at_source", "first_seen_at",
        "url",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore",
                            lineterminator="\r\n")
    writer.writeheader()
    for r in open_jobs:
        row = {k: r.get(k, "") for k in fields}
        row["h1b_approvals"] = h1b.approvals_for(r.get("company") or "") or ""
        row["skills"] = "; ".join(r.get("skills") or [])
        row["seasons"] = "; ".join(r.get("seasons") or [])
        row["program"] = filters.program_type(r.get("title") or "")
        row["remote"] = "yes" if filters.is_remote(
            r.get("location") or "", r.get("title") or "") else ""
        writer.writerow({k: _csv_safe(v) for k, v in row.items()})

    # Written twice: data/ is the repo tracker people clone, docs/ is what
    # GitHub Pages serves — the dashboard links to the latter, and without the
    # copy that link 404s.
    text = buffer.getvalue()
    os.makedirs(paths.DOCS_DIR, exist_ok=True)
    for target in (paths.CSV_PATH, os.path.join(paths.DOCS_DIR, "internships.csv")):
        with open(target, "w", newline="", encoding="utf-8") as f:
            f.write(text)
