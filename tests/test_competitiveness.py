"""Competition labels stay deterministic and explicitly non-numeric."""

from intern_engine import competitiveness


def test_top_employer_is_very_high_without_inventing_a_rate():
    result = competitiveness.estimate({
        "company": "Google", "category": "Software",
    })
    assert result.label == "Very high"
    assert "not an applicant count or acceptance rate" in result.explanation
    assert "%" not in result.explanation


def test_role_demand_can_raise_an_unknown_employer_to_high():
    result = competitiveness.estimate({
        "company": "Example New Startup", "category": "Data & ML/AI",
    })
    assert result.label == "High"
    assert "typically crowded role family" in result.explanation


def test_unknown_software_employer_stays_moderate():
    result = competitiveness.estimate({
        "company": "Example New Startup", "category": "Software",
    })
    assert result.label == "Moderate"
