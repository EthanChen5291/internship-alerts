"""Digest mailer: gating, composition, and the no-op-without-config contract."""

from datetime import UTC, datetime, timedelta

from intern_engine import mailer


def _record(hours_ago: float, **extra) -> dict:
    ts = (datetime.now(UTC) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec = {
        "id": f"x:{hours_ago}", "company": "Acme", "title": "SWE Intern",
        "season": "Summer 2027", "location": "NYC", "url": "https://x/1",
        "is_open": True, "first_seen_at": ts, "sponsorship": "unknown",
    }
    rec.update(extra)
    return rec


# --- what counts as news -------------------------------------------------------

def test_new_roles_window():
    store = {
        "a": _record(2),
        "b": _record(80),               # too old
        "c": _record(1, is_open=False),  # closed
    }
    fresh = mailer.new_roles(store)
    assert [r["id"] for r in fresh] == ["x:2"]


def test_already_sent_roles_are_never_repeated():
    # The duplicate-digest bug: the news window (48h) is wider than the send
    # interval (22h), so a role sits in two consecutive windows. Membership in
    # a previous digest — not the clock — is what keeps it out the second time.
    store = {"a": _record(2), "b": _record(20)}
    assert len(mailer.new_roles(store)) == 2
    fresh = mailer.new_roles(store, already_sent={"x:20"})
    assert [r["id"] for r in fresh] == ["x:2"]
    assert mailer.new_roles(store, already_sent={"x:2", "x:20"}) == []


class TestRecipientRotation:
    """Everyone gets served in turn once the list outgrows the daily quota."""

    def _subs(self, n):
        return [{"email": f"u{i}@x.com", "unsub_token": f"t{i}"} for i in range(n)]

    def test_small_list_is_sent_whole(self):
        subs = self._subs(10)
        got, cursor = mailer._recipients(subs, cursor=0)
        assert got == subs
        assert cursor == 0

    def test_oversized_list_rotates_instead_of_starving_the_tail(self):
        total = mailer._MAX_SENDS + 40
        subs = self._subs(total)
        first, cursor = mailer._recipients(subs, cursor=0)
        assert len(first) == mailer._MAX_SENDS
        second, _ = mailer._recipients(subs, cursor)
        # The 40 who were cut off last time lead the next digest.
        assert second[0]["email"] == f"u{mailer._MAX_SENDS}@x.com"
        # Two rounds cover everyone.
        assert {s["email"] for s in first} | {s["email"] for s in second} == {
            s["email"] for s in subs
        }


def test_new_roles_newest_first_and_uncapped():
    # new_roles reports the TRUE count (for the subject line); the HTML body
    # is what caps at _MAX_ROLES.
    store = {str(i): _record(i / 2, id=str(i)) for i in range(1, 45)}
    fresh = mailer.new_roles(store)
    assert len(fresh) == 44
    seen = [r["first_seen_at"] for r in fresh]
    assert seen == sorted(seen, reverse=True)


def test_digest_html_caps_rows_and_says_plus_n_more():
    fresh = [_record(i / 4, id=str(i), company=f"Co{i}") for i in range(40)]
    html = mailer.build_digest_html(fresh)
    listed = html.count("border-bottom:1px solid #e6e8eb")
    assert listed == mailer._MAX_ROLES
    assert f"plus {40 - mailer._MAX_ROLES} more new roles" in html


# --- daily gate ----------------------------------------------------------------

def test_should_send_requires_news():
    assert mailer.should_send({}, fresh_count=0) is False
    assert mailer.should_send({}, fresh_count=3) is True


def test_should_send_at_most_daily():
    now = datetime.now(UTC)
    recent = (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = (now - timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert mailer.should_send({"last_digest_at": recent}, 5) is False
    assert mailer.should_send({"last_digest_at": old}, 5) is True


# --- composition ---------------------------------------------------------------

def test_digest_html_lists_roles_and_unsub_slot():
    fresh = [
        _record(1, company="Stripe", title="Backend Intern", salary="$55/hr"),
        _record(2, company="Acme", sponsorship="no-sponsorship"),
    ]
    html = mailer.build_digest_html(fresh)
    assert "Stripe" in html and "Backend Intern" in html
    assert "$55/hr" in html
    assert "\U0001f6c2" in html            # 🛂 flag carried into the email
    assert "{{UNSUB_URL}}" in html          # per-recipient link slot survives


def test_sender_parsing(monkeypatch):
    monkeypatch.setenv("MAIL_FROM", "Intern Engine <alerts@example.com>")
    assert mailer._sender() == {"name": "Intern Engine", "email": "alerts@example.com"}
    monkeypatch.setenv("MAIL_FROM", "alerts@example.com")
    assert mailer._sender() == {"name": "Intern Engine", "email": "alerts@example.com"}
    monkeypatch.setenv("MAIL_FROM", "not-an-email")
    assert mailer._sender() is None


# --- the contract: unset env = silent no-op ------------------------------------

def test_send_digest_noop_without_env(monkeypatch):
    for var in ("BREVO_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "MAIL_FROM"):
        monkeypatch.delenv(var, raising=False)
    assert mailer.send_digest({"a": _record(1)}) == 0


class TestNewMeansUnsent:
    """"New" is decided by what we've sent, never by a clock window."""

    NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)

    def _store(self, **ages_hours):
        return {
            jid: {"id": jid, "is_open": True,
                  "first_seen_at": (self.NOW - timedelta(hours=h))
                  .strftime("%Y-%m-%dT%H:%M:%SZ")}
            for jid, h in ages_hours.items()
        }

    def test_an_unsent_role_older_than_the_old_window_still_goes_out(self):
        # Regression: the fixed 48h window meant a role missed during a failed
        # run aged out and could NEVER be mailed. Nothing should be skipped.
        store = self._store(stale=100)
        fresh = mailer.new_roles(store, now=self.NOW, already_sent={"other"})
        assert [r["id"] for r in fresh] == ["stale"]

    def test_already_sent_roles_never_repeat(self):
        store = self._store(a=1, b=2)
        fresh = mailer.new_roles(store, now=self.NOW, already_sent={"a"})
        assert [r["id"] for r in fresh] == ["b"]

    def test_lost_state_does_not_mail_the_back_catalogue(self):
        # sent_role_ids empty but a digest HAS gone out before: the 14-day
        # backstop applies, so an ancient role stays out.
        store = self._store(recent=24, ancient=24 * 30)
        fresh = mailer.new_roles(store, now=self.NOW, already_sent=set(),
                                 has_history=True)
        assert [r["id"] for r in fresh] == ["recent"]

    def test_first_ever_digest_stays_tight(self):
        # No history at all: only the last 48h, so standing up the mailer
        # doesn't blast every open role at the whole list.
        store = self._store(new=6, older=72)
        fresh = mailer.new_roles(store, now=self.NOW, already_sent=set(),
                                 has_history=False)
        assert [r["id"] for r in fresh] == ["new"]

    def test_closed_roles_are_never_news(self):
        store = self._store(a=1)
        store["a"]["is_open"] = False
        assert mailer.new_roles(store, now=self.NOW, already_sent=set()) == []


class TestDigestSubject:
    """The subject is the only thing seen on a lock screen — it must say who."""

    def test_names_the_employers(self):
        fresh = [_record(0, id="1", company="Stripe"),
                 _record(1, id="2", company="Anduril")]
        assert mailer.digest_subject(fresh) == "2 new internships · Stripe, Anduril"

    def test_singular_reads_naturally(self):
        assert mailer.digest_subject([_record(0, id="1", company="Ramp")]) == \
            "1 new internship · Ramp"

    def test_long_lists_are_truncated_with_a_count(self):
        fresh = [_record(i, id=str(i), company=f"Co{i}") for i in range(7)]
        assert mailer.digest_subject(fresh) == "7 new internships · Co0, Co1, Co2 +4"

    def test_repeat_employers_are_named_once(self):
        fresh = [_record(0, id="1", company="Akuna"), _record(1, id="2", company="Akuna")]
        assert mailer.digest_subject(fresh) == "2 new internships · Akuna"

    def test_missing_company_names_do_not_break_it(self):
        assert mailer.digest_subject([_record(0, id="1", company="")]) == "1 new internship"


class TestDigestBody:
    def test_marks_remote_roles_and_h1b(self):
        html = mailer.build_digest_html([_record(0, id="1", location="Remote - US")])
        assert ">R<" in html

    def test_unstated_cycle_says_so_rather_than_guessing(self):
        html = mailer.build_digest_html([_record(0, id="1", season="Not stated")])
        assert "cycle not stated" in html

    def test_skills_render_as_pills(self):
        html = mailer.build_digest_html([_record(0, id="1", skills=["Python", "Go"])])
        assert ">Python<" in html and ">Go<" in html

    def test_titles_are_escaped(self):
        html = mailer.build_digest_html([_record(0, id="1", title="C++ <b>Dev</b> Intern")])
        assert "&lt;b&gt;" in html

    def test_summary_line_reports_the_split(self):
        fresh = [_record(0, id="1", season="Summer 2027"),
                 _record(1, id="2", season="Not stated")]
        html = mailer.build_digest_html(fresh)
        assert "1 with a stated cycle" in html
