import pytest

from intern_engine import config, paths


def test_missing_config_uses_validated_safe_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CONFIG_PATH", str(tmp_path / "missing.json"))
    cfg = config.load_config()
    assert cfg["regions"] == ["US"]
    assert cfg["role_scope"] == "tech"
    assert cfg["default_cycle"] in cfg["cycles"]


def test_malformed_existing_config_is_fatal(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text('{"regions":', encoding="utf-8")
    monkeypatch.setattr(paths, "CONFIG_PATH", str(path))
    with pytest.raises(config.ConfigError, match="unreadable"):
        config.load_config()


@pytest.mark.parametrize(
    "raw, message",
    [
        ({"regions": []}, "regions must contain"),
        ({"regions": ["Mars"]}, "unsupported regions"),
        ({"cycles": ["2027 Summer"]}, "cycles must use labels"),
        ({"default_cycle": "Spring 2030"}, "default_cycle"),
        ({"include_international": "yes"}, "true or false"),
        ({"max_age_days": True}, "must be an integer"),
    ],
)
def test_scope_configuration_rejects_unsafe_shapes(raw, message):
    with pytest.raises(config.ConfigError, match=message):
        config.validate_config(raw)


def test_empty_regions_fail_closed_even_for_unvalidated_callers():
    assert config.restrict_region({"regions": []}) is True


def test_personal_role_exclusions_match_category_and_title_phrases():
    cfg = {
        "excluded_categories": ["Hardware"],
        "excluded_title_terms": ["data science", "data scientist"],
    }
    assert config.role_excluded(cfg, "Firmware Engineering Intern", "Hardware")
    assert config.role_excluded(cfg, "Summer Data Science Intern", "Data & ML/AI")
    assert config.role_excluded(cfg, "Data Scientist Intern", "Data & ML/AI")
    assert not config.role_excluded(cfg, "Machine Learning Intern", "Data & ML/AI")
    assert not config.role_excluded(cfg, "Embedded Software Intern", "Software")


@pytest.mark.parametrize("field", ["excluded_categories", "excluded_title_terms"])
def test_personal_role_exclusions_require_string_lists(field):
    with pytest.raises(config.ConfigError, match=field):
        config.validate_config({field: "Hardware"})
