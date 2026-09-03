"""Instant personal email delivery and outbox behavior."""

import json

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

    def json(self):
        return {"messageId": "test-message-id"}


def test_email_contains_company_role_keywords_compensation_and_apply_link():
    subject, html = personal_alerts.build_email([
        _record(salary="$45-$55/hr", class_year="Juniors+")
    ])
    assert subject == "[Acme] Software Engineering Intern — Summer 2027"
    assert "Acme" in html
    assert "Software Engineering Intern" in html
    assert "Python, React" in html
    assert "Compensation" in html
    assert "$45-$55/hr" in html
    assert "Juniors+ (employer-stated)" in html
    assert "https://example.com/jobs/1" in html
    assert "Apply now" in html
    assert "Tailor resume" in html
    assert "resume.html?job=job-1" in html
    assert "Your application angle" in html
    assert "Competition estimate" in html
    assert "relative estimate" in html
    assert "Summer 2027 availability" in html


def test_multi_job_subject_starts_with_company_name():
    subject, html = personal_alerts.build_email(
        [_record(), _record(id="job-2", company="Beta", title="Data Intern")]
    )
    assert subject == "[Acme + 1 more] 2 new internships"
    assert "Acme and more" in html
    assert "Beta" in html


def test_advice_uses_private_resume_profile_without_inventing_matches(monkeypatch):
    profile = {
        "graduation": "May 2029",
        "skills": ["Python", "React", "Docker"],
        "evidence": [
            {
                "name": "ShapeUp",
                "proof": "built a Python pipeline and deployed containerized inference",
                "skills": ["Python", "Docker"],
            }
        ],
    }
    monkeypatch.setenv("APPLICANT_PROFILE_JSON", json.dumps(profile))
    record = _record(skills=["Python", "React", "Java"], category="Software")

    _, html = personal_alerts.build_email([record])

    assert "Best resume proof: ShapeUp" in html
    assert "Direct matches: Python, React" in html
    assert "unmatched terms such as Java" in html
    assert "May 2029 graduation" in html


def test_big_company_strong_match_gets_personalized_urgency(monkeypatch):
    monkeypatch.setenv("APPLICANT_PROFILE_JSON", json.dumps({
        "skills": ["Python", "React", "Docker"],
    }))

    subject, html = personal_alerts.build_email([
        _record(company="Google", skills=["Python", "React", "Java"])
    ])

    assert subject.startswith("[Google · PRIORITY]")
    assert "Apply promptly" in html
    assert "Priority match for Google" in html
    assert "directly matches Python, React" in html
    assert "highly competitive employer" in html


def test_urgency_requires_both_high_competition_and_strong_match(monkeypatch):
    monkeypatch.setenv("APPLICANT_PROFILE_JSON", json.dumps({
        "skills": ["Python", "React"],
    }))

    ordinary_subject, ordinary_html = personal_alerts.build_email([_record()])
    weak_subject, weak_html = personal_alerts.build_email([
        _record(company="Google", skills=["Python", "Java", "Go"])
    ])

    assert "PRIORITY" not in ordinary_subject
    assert "Apply promptly" not in ordinary_html
    assert "PRIORITY" not in weak_subject
    assert "Apply promptly" not in weak_html


def test_underclassman_program_gets_the_loudest_notice():
    subject, html = personal_alerts.build_email([_record(
        company="NVIDIA",
        title="NVIDIA Ignite Software Intern",
        underclass_program_key="nvidia-ignite",
        underclass_program="NVIDIA Ignite",
        underclass_audience="Current freshmen and sophomores",
    )])

    assert subject.startswith("[🚨 NVIDIA Ignite OPEN]")
    assert "UNDERCLASSMAN PROGRAM JUST OPENED" in html
    assert "Current freshmen and sophomores" in html
    assert "Apply as soon as you can" in html


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

    message_id = personal_alerts.send_test_email()

    assert message_id == "test-message-id"
    assert sent[0][1]["json"]["subject"] == "Internship Alerts email test"
    assert sent[0][1]["json"]["to"] == [{"email": "me@example.com"}]
    assert "email alerts are working" in sent[0][1]["json"]["htmlContent"]


def test_preview_email_uses_production_layout_without_touching_state(monkeypatch):
    _email_env(monkeypatch)
    sent = []
    monkeypatch.setattr(
        personal_alerts.httpx,
        "post",
        lambda url, **kwargs: (sent.append((url, kwargs)), Response())[1],
    )

    message_id = personal_alerts.send_preview_email(_record())

    assert message_id == "test-message-id"
    assert sent[0][1]["json"]["subject"].startswith("[PREVIEW] [Acme]")
    assert "EMAIL FORMAT PREVIEW" in sent[0][1]["json"]["htmlContent"]
    assert "Your application angle" in sent[0][1]["json"]["htmlContent"]


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
