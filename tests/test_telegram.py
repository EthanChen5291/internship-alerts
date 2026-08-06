"""Telegram push: message shaping and the outbox contract."""

from __future__ import annotations

from intern_engine import telegram


def _rec(**extra):
    rec = {"id": "greenhouse:acme:1", "company": "Acme", "title": "SWE Intern",
           "location": "Austin, TX", "url": "https://x/1", "season": "Summer 2027",
           "is_open": True, "sponsorship": "unknown", "skills": ["Python", "Go"]}
    rec.update(extra)
    return rec


class TestMessageShaping:
    def test_links_the_title_and_bolds_the_employer(self):
        out = telegram.build_messages([_rec()])[0]
        assert "<b>Acme</b>" in out
        assert '<a href="https://x/1">SWE Intern</a>' in out

    def test_marks_remote_roles(self):
        out = telegram.build_messages([_rec(location="Remote - US")])[0]
        assert "🆁" in out

    def test_a_role_without_a_url_still_renders(self):
        # The footer always carries a dashboard link, so check the ROLE line.
        role_line = telegram._role_line(_rec(url=""))
        assert "SWE Intern" in role_line
        assert "<a href" not in role_line

    def test_escapes_html_in_employer_text(self):
        # Titles are third-party text; an unescaped < would break parse_mode.
        out = telegram.build_messages([_rec(title="C++ <Dev> Intern")])[0]
        assert "&lt;Dev&gt;" in out
        assert "<Dev>" not in out

    def test_not_stated_cycle_is_omitted_rather_than_printed(self):
        out = telegram.build_messages([_rec(season="Not stated")])[0]
        assert "Not stated" not in out

    def test_long_lists_split_under_the_size_cap(self):
        msgs = telegram.build_messages([_rec(id=str(i), title="Software Engineering Intern " * 6)
                                        for i in range(40)])
        assert len(msgs) > 1
        assert all(len(m) <= telegram._MAX_CHARS + 200 for m in msgs)

    def test_header_counts_and_footer_links_once(self):
        msgs = telegram.build_messages([_rec(), _rec(id="2")])
        assert "2 new internships" in msgs[0]
        assert sum("Open the dashboard" in m for m in msgs) == 1

    def test_no_roles_no_messages(self):
        assert telegram.build_messages([]) == []


class TestOutboxContract:
    """Mirrors notify.send_new_roles so the queue drains correctly."""

    def test_unconfigured_settles_everything_rather_than_accumulating(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        assert telegram.send_new_roles({}, ["a", "b"]) == ["a", "b"]

    def test_ids_missing_from_the_store_are_settled(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
        assert telegram.send_new_roles({}, ["gone"]) == ["gone"]

    def test_closed_roles_are_settled_without_sending(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
        store = {"a": _rec(is_open=False)}
        assert telegram.send_new_roles(store, ["a"]) == ["a"]

    def test_a_send_failure_keeps_the_role_queued(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

        def boom(*a, **k):
            raise RuntimeError("network down")

        monkeypatch.setattr(telegram.httpx, "post", boom)
        # Nothing announced -> nothing settled -> the outbox keeps it.
        assert telegram.send_new_roles({"a": _rec()}, ["a"]) == []

    def test_a_successful_send_settles_the_role(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
        sent = []

        class Resp:
            def raise_for_status(self): pass

        monkeypatch.setattr(telegram.httpx, "post",
                            lambda url, **k: (sent.append(k["json"]), Resp())[1])
        assert telegram.send_new_roles({"a": _rec()}, ["a"]) == ["a"]
        assert sent[0]["parse_mode"] == "HTML"
        assert sent[0]["disable_web_page_preview"] is True


class TestConfigured:
    def test_needs_both_token_and_chat(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        assert telegram.configured() is False
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
        assert telegram.configured() is True
