"""Employer-stated student-standing labels favor precision over recall."""

import pytest

from intern_engine import eligibility


@pytest.mark.parametrize("text", [
    "Applicants must be rising juniors or seniors.",
    "Open to college juniors and above.",
    "Junior/senior students are encouraged to apply.",
    "Junior class standing or higher is required.",
    "Candidates need at least junior standing.",
    "We seek junior or senior undergraduate students.",
])
def test_explicit_junior_or_above_language_is_labeled(text):
    assert eligibility.classify(text) == "Juniors+"


@pytest.mark.parametrize("text", [
    "Junior Software Developer Intern",
    "You will mentor junior engineers and senior researchers.",
    "Open to all undergraduate students.",
    "Sophomore standing or above is required.",
    "",
])
def test_job_seniority_and_non_junior_requirements_do_not_trigger(text):
    assert eligibility.classify(text) is None
