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


def test_sources_are_unverified_and_have_no_endpoints() -> None:
    sources = config.load_sources()
    assert sources, "source registry should not be empty"
    for src in sources:
        assert {"id", "name", "domains", "status", "base_url"} <= src.keys()
        # No endpoint may be recorded before verification.
        if src["status"] == "candidate":
            assert src["base_url"] is None


def test_get_secret_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI_TEST_SECRET", raising=False)
    with pytest.raises(config.ConfigError):
        config.get_secret("CI_TEST_SECRET")
    assert config.get_secret("CI_TEST_SECRET", required=False) is None


def test_env_file_is_gitignored() -> None:
    gitignore = (config.PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".venv/", ".env", ".databrickscfg", ".streamlit/secrets.toml"):
        assert pattern in gitignore
