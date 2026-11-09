"""Configuration loading.

Non-secret settings come from a YAML file; secrets and per-environment
overrides come from environment variables (optionally loaded from a local,
git-ignored ``.env`` file). Nothing in this module stores credentials.

Resolution order for the settings file:
    1. ``CI_SETTINGS_FILE`` environment variable
    2. ``config/settings.yaml`` (local, git-ignored)
    3. ``config/settings.example.yaml`` (committed template)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_SETTINGS = CONFIG_DIR / "settings.yaml"
EXAMPLE_SETTINGS = CONFIG_DIR / "settings.example.yaml"
SOURCES_FILE = CONFIG_DIR / "sources.yaml"


class ConfigError(RuntimeError):
    """Raised when configuration is missing or invalid."""


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Top-level YAML must be a mapping: {path}")
    return data


def resolve_settings_path() -> Path:
    """Return the settings file to use, following the documented order."""
    override = os.getenv("CI_SETTINGS_FILE")
    if override:
        path = Path(override)
        return path if path.is_absolute() else PROJECT_ROOT / path
    return DEFAULT_SETTINGS if DEFAULT_SETTINGS.is_file() else EXAMPLE_SETTINGS


def load_settings(load_env: bool = True) -> dict[str, Any]:
    """Load settings from YAML and apply environment-variable overrides."""
    if load_env:
        load_dotenv(PROJECT_ROOT / ".env", override=False)

    settings = _read_yaml(resolve_settings_path())

    if env := os.getenv("CI_ENV"):
        settings.setdefault("project", {})["environment"] = env
    if level := os.getenv("CI_LOG_LEVEL"):
        settings.setdefault("logging", {})["level"] = level.upper()
    return settings


def load_sources() -> list[dict[str, Any]]:
    """Return the candidate data-source registry from ``config/sources.yaml``."""
    sources = _read_yaml(SOURCES_FILE).get("sources", [])
    if not isinstance(sources, list):
        raise ConfigError("'sources' must be a list in sources.yaml")
    return sources


def get_resource(resource_id: str) -> dict[str, Any]:
    """Return one resource from the registry, enriched with its parent source's metadata.

    Raises ConfigError if the resource is unknown or not marked as ``verified``,
    so that connectors can only use endpoints that passed verification.
    """
    for source in load_sources():
        for resource in source.get("resources", []):
            if resource.get("id") == resource_id:
                status = resource.get("status")
                if status != "verified" or not resource.get("url"):
                    raise ConfigError(f"Resource '{resource_id}' is not verified (status={status})")
                return {
                    **resource,
                    "source_id": source["id"],
                    "publisher": source.get("publisher"),
                    "license": resource.get("license") or source.get("license"),
                }
    raise ConfigError(f"Unknown resource id in sources.yaml: {resource_id}")


def project_path(relative: str | Path) -> Path:
    """Resolve a path from settings (relative to the project root) to an absolute path."""
    path = Path(relative)
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_secret(name: str, required: bool = True) -> str | None:
    """Read a secret from the environment. Never logs or returns defaults for secrets."""
    value = os.getenv(name)
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value
