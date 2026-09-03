"""Underclassman watchlist stays exact and employer-specific."""

from intern_engine import programs


def test_verified_program_titles_match_the_right_employer():
    assert programs.match("Microsoft", "Explore Microsoft Intern")["name"] == "Microsoft Explore"
    assert programs.match("NVIDIA", "NVIDIA Ignite Software Intern")["name"] == "NVIDIA Ignite"
    assert programs.match("Duolingo", "Software Engineer, Thrive Intern")["name"] == "Duolingo Thrive"


def test_generic_words_and_wrong_employers_do_not_match():
    assert programs.match("Microsoft", "Software Intern working on File Explorer") is None
    assert programs.match("Acme", "Ignite Intern") is None
    assert programs.match("Thrive Global", "Software Intern") is None


def test_open_programs_only_uses_live_labeled_postings():
    store = {
        "open": {"is_open": True, "underclass_program_key": "nvidia-ignite"},
        "closed": {"is_open": False, "underclass_program_key": "duolingo-thrive"},
    }
    assert programs.open_programs(store) == {"nvidia-ignite": store["open"]}
