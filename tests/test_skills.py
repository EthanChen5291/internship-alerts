"""Skill-tag and pay extraction: precision-first, like the sponsorship tests."""

from intern_engine import skills


def test_extract_basic_stack():
    text = ("Requirements: strong Python and C++ skills, experience with PyTorch "
            "or TensorFlow, familiarity with AWS and Docker. Git required.")
    got = skills.extract(text)
    assert "Python" in got
    assert "C++" in got
    assert "PyTorch" in got
    assert "TensorFlow" in got
    assert "AWS" in got
    assert "Docker" in got
    assert "Git" in got


def test_extract_whole_words_only():
    # None of these mention a real skill: "go" the verb, "Spring 2027" the
    # season, "spark" the marketing verb, "javascript" absent.
    text = ("Go above and beyond in our Spring 2027 program. Spark your "
            "creativity! We iterate rapidly and swiftly ship rustic ideas.")
    assert skills.extract(text) == []


def test_english_words_are_not_mistaken_for_stacks():
    # Real false positives from live postings: ordinary prose was tagging
    # roles with React/Rust/Swift/Angular. Names that are also English words
    # only match capitalized, which is how tech stacks are actually written.
    prose = (
        "You will react quickly to incidents, help with reducing rust on "
        "legacy code, give a swift response to customers, and understand "
        "angular momentum in our simulations. We go to market fast."
    )
    assert skills.extract(prose) == []


def test_capitalized_stack_names_still_match():
    text = ("Experience with React Native, Rust, SwiftUI, AngularJS and Vue.js. "
            "Familiarity with Go programming is a plus.")
    found = skills.extract(text)
    for want in ("React", "Rust", "Swift", "Angular", "Vue", "Go"):
        assert want in found, f"{want} missing from {found}"


def test_extract_java_vs_javascript():
    assert skills.extract("We use JavaScript heavily.") == ["JavaScript"]
    got = skills.extract("Java and JavaScript are both used.")
    assert "Java" in got and "JavaScript" in got


def test_extract_cap_and_order():
    text = ("Python Java C++ C# Rust TypeScript JavaScript SQL Swift Kotlin "
            "MATLAB golang")
    got = skills.extract(text)
    assert len(got) == skills.MAX_SKILLS
    assert got[0] == "Python"  # canonical order, not text order


def test_extract_additional_common_skills():
    text = ("Build Next.js services with Express.js, Bash shell scripting, "
            "dbt, Databricks, Snowflake, and Selenium.")
    found = skills.extract(text)
    for want in ("Bash", "Next.js", "Express", "dbt", "Databricks", "Snowflake", "Selenium"):
        assert want in found, f"{want} missing from {found}"


def test_title_mentioned_skill_ranks_first():
    found = skills.extract("Python, React, SQL, and AWS are required.", "React Engineer")
    assert found[0] == "React"


def test_extract_empty():
    assert skills.extract(None) == []
    assert skills.extract("") == []


def test_pay_hourly_range():
    assert skills.extract_pay("The pay range is $41.50 - $55 per hour.") == "$41.5–$55/hr"


def test_pay_hourly_single():
    assert skills.extract_pay("Interns earn $45/hr plus housing.") == "$45/hr"


def test_pay_annual_range():
    text = "Base salary: $120,000 - $140,000 per year depending on level."
    assert skills.extract_pay(text) == "$120k–$140k/yr"


def test_pay_hourly_beats_annual():
    text = "Pay is $50/hour ($104,000 annualized)."
    assert skills.extract_pay(text) == "$50/hr"


def test_pay_rejects_nonsense():
    # No period marker, out-of-range values, or bare dollar figures: no pay.
    assert skills.extract_pay("We raised $5,000,000 last year.") is None
    assert skills.extract_pay("A $5 gift card per hour of user testing") is None
    assert skills.extract_pay("Millions of dollars in impact") is None
    assert skills.extract_pay(None) is None
