"""Instant personal email delivery and outbox behavior."""

from intern_engine import personal_alerts


def _record(**extra):
    record = {
        "id": "job-1",
        "company": "Acme",
        "title": "Software Engineering Intern",
        "location": "Chicago, IL",
        "url": "https://example.com/jobs/1",
        "season": "Summer 2027",
        "is_open": True,
        "skills": ["Python", "React"],
    }
    record.update(extra)
    return record


def _email_env(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "key")
    monkeypatch.setenv("MAIL_FROM", "Alerts <alerts@example.com>")
    monkeypatch.setenv("ALERT_EMAIL_TO", "me@example.com")


class Response:
    def raise_for_status(self):
        return None


def test_email_contains_company_role_keywords_and_apply_link():
    subject, html = personal_alerts.build_email([_record()])
    assert subject == "1 new tech internship"
    assert "Acme" in html
    assert "Software Engineering Intern" in html
    assert "Python, React" in html
    assert "https://example.com/jobs/1" in html


def test_unconfigured_email_settles_instead_of_growing_forever(monkeypatch):
    for name in ("BREVO_API_KEY", "MAIL_FROM", "ALERT_EMAIL_TO"):
        monkeypatch.delenv(name, raising=False)
    assert personal_alerts.send_email({}, ["a"]) == ["a"]


def test_email_success_sends_to_the_personal_destination(monkeypatch):
    _email_env(monkeypatch)
    sent = []
    monkeypatch.setattr(
        personal_alerts.httpx,
        "post",
        lambda url, **kwargs: (sent.append((url, kwargs)), Response())[1],
    )
    assert personal_alerts.send_email({"job-1": _record()}, ["job-1"]) == ["job-1"]
    assert sent[0][1]["json"]["to"] == [{"email": "me@example.com"}]
    assert sent[0][1]["json"]["sender"] == {
        "name": "Alerts", "email": "alerts@example.com"
    }


def test_setup_email_uses_expected_subject_and_destination(monkeypatch):
    _email_env(monkeypatch)
    sent = []
    monkeypatch.setattr(
        personal_alerts.httpx,
        "post",
        lambda url, **kwargs: (sent.append((url, kwargs)), Response())[1],
    )

    personal_alerts.send_test_email()

    assert sent[0][1]["json"]["subject"] == "Internship Alerts email test"
    assert sent[0][1]["json"]["to"] == [{"email": "me@example.com"}]
    assert "email alerts are working" in sent[0][1]["json"]["htmlContent"]


def test_email_failure_keeps_open_roles_queued(monkeypatch):
    _email_env(monkeypatch)
    monkeypatch.setattr(
        personal_alerts.httpx, "post", lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("network down")
        )
    )
    assert personal_alerts.send_email({"job-1": _record()}, ["job-1"]) == []


def test_closed_and_missing_roles_are_settled_without_delivery(monkeypatch):
    _email_env(monkeypatch)
    monkeypatch.setattr(
        personal_alerts.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not send")),
    )
    assert personal_alerts.send_email({"closed": _record(is_open=False)}, ["gone", "closed"]) == [
        "gone", "closed"
    ]
