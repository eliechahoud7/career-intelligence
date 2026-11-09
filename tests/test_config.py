"""Tests for configuration loading and repository hygiene."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence import config


def test_example_settings_load(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_SETTINGS_FILE", str(config.EXAMPLE_SETTINGS))
    monkeypatch.delenv("CI_ENV", raising=False)
    settings = config.load_settings(load_env=False)
    assert settings["project"]["name"] == "career-intelligence"
    assert set(settings["databricks"]["schemas"]) == {"bronze", "silver", "gold"}


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_SETTINGS_FILE", str(config.EXAMPLE_SETTINGS))
    monkeypatch.setenv("CI_ENV", "test")
    monkeypatch.setenv("CI_LOG_LEVEL", "debug")
    settings = config.load_settings(load_env=False)
    assert settings["project"]["environment"] == "test"
    assert settings["logging"]["level"] == "DEBUG"


def test_missing_settings_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CI_SETTINGS_FILE", str(tmp_path / "nope.yaml"))
    with pytest.raises(config.ConfigError):
        config.load_settings(load_env=False)


ALLOWED_STATUSES = {"verified", "requires_registration", "manual_download", "restricted"}


def test_source_registry_structure() -> None:
    sources = config.load_sources()
    assert sources, "source registry should not be empty"
    for src in sources:
        assert {"id", "name", "publisher", "domains", "license", "resources"} <= src.keys()
        for res in src["resources"]:
            assert {"id", "type", "url", "auth", "status"} <= res.keys()
            assert res["status"] in ALLOWED_STATUSES


def test_only_verified_resources_have_urls() -> None:
    """No endpoint may be recorded unless it was successfully requested."""
    for src in config.load_sources():
        for res in src["resources"]:
            if res["status"] == "verified":
                assert res["url"], f"{res['id']} is verified but has no url"
            else:
                assert res["url"] is None, f"{res['id']} is not verified but has a url"


def test_registry_contains_no_credentials() -> None:
    text = config.SOURCES_FILE.read_text(encoding="utf-8").lower()
    for marker in ("client_secret:", "api_key:", "password:", "token:"):
        assert marker not in text


def test_get_secret_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI_TEST_SECRET", raising=False)
    with pytest.raises(config.ConfigError):
        config.get_secret("CI_TEST_SECRET")
    assert config.get_secret("CI_TEST_SECRET", required=False) is None


def test_env_file_is_gitignored() -> None:
    gitignore = (config.PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".venv/", ".env", ".databrickscfg", ".streamlit/secrets.toml"):
        assert pattern in gitignore
