"""Databricks SQL connection for the search layer — server side only (Phase 15A).

* Settings (workspace host, SQL warehouse) come from environment variables, optionally loaded
  from the git-ignored ``.env`` file. Nothing workspace-specific is stored in the repository.
* Authentication reuses the Databricks CLI login (decision A2): ``databricks auth token`` is
  called on the server and the short-lived OAuth token is kept in memory only. It is never
  written to disk, logged, returned to callers or shown in ``repr``.
* ``DatabricksExecutor`` runs **only** the SQL of a registered search contract (byte-identical
  to its file), after a read-only check, and reconnects with a fresh token once on an
  authentication failure.

The ``databricks.sql`` client is imported lazily, so this module (and the offline tests) work
without the optional ``[databricks]`` extra.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv

from career_intelligence.config import PROJECT_ROOT, ConfigError
from career_intelligence.search import contracts

TOKEN_TTL_SECONDS = 45 * 60  # OAuth access tokens last about one hour
TOKEN_EXPIRY_MARGIN_SECONDS = 120
CONNECTION_MAX_AGE_SECONDS = 45 * 60
CLI_TIMEOUT_SECONDS = 60

ENV_HOST = "DATABRICKS_SERVER_HOSTNAME"
ENV_HTTP_PATH = "DATABRICKS_HTTP_PATH"
ENV_WAREHOUSE_ID = "DATABRICKS_WAREHOUSE_ID"
ENV_PROFILE = "DATABRICKS_CONFIG_PROFILE"

_HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$")
_WAREHOUSE_RE = re.compile(r"^[A-Za-z0-9]+$")
_HTTP_PATH_RE = re.compile(r"^/sql/[0-9.]+/warehouses/[A-Za-z0-9]+$")


class AuthenticationError(RuntimeError):
    """The Databricks CLI login is missing or expired (message is safe to display)."""


class ReadOnlyViolation(RuntimeError):
    """A statement that is not a registered, read-only search contract was refused."""


# --- Settings ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ConnectionSettings:
    """Where to connect. Not secret, but kept out of ``repr`` and of user-facing messages."""

    server_hostname: str = field(repr=False)
    http_path: str = field(repr=False)
    profile: str | None = None


def load_connection_settings(env: Mapping[str, str] | None = None) -> ConnectionSettings:
    """Read the connection settings from ``env`` (default: the process environment + ``.env``)."""
    if env is None:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        env = os.environ
    host = (env.get(ENV_HOST) or "").strip()
    host = re.sub(r"^https?://", "", host).rstrip("/")
    http_path = (env.get(ENV_HTTP_PATH) or "").strip()
    warehouse = (env.get(ENV_WAREHOUSE_ID) or "").strip()
    profile = (env.get(ENV_PROFILE) or "").strip() or None

    missing = []
    if not host:
        missing.append(ENV_HOST)
    if not http_path and not warehouse:
        missing.append(f"{ENV_HTTP_PATH} (or {ENV_WAREHOUSE_ID})")
    if missing:
        raise ConfigError("Missing Databricks setting(s): " + ", ".join(missing))
    if not _HOST_RE.match(host):
        raise ConfigError(f"{ENV_HOST} is not a valid host name")
    if not http_path:
        if not _WAREHOUSE_RE.match(warehouse):
            raise ConfigError(f"{ENV_WAREHOUSE_ID} is not a valid warehouse id")
        http_path = f"/sql/1.0/warehouses/{warehouse}"
    if not _HTTP_PATH_RE.match(http_path):
        raise ConfigError(f"{ENV_HTTP_PATH} must look like /sql/1.0/warehouses/<id>")
    return ConnectionSettings(server_hostname=host, http_path=http_path, profile=profile)


# --- Token from the Databricks CLI ---------------------------------------------------------

Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", timeout=CLI_TIMEOUT_SECONDS
    )


def _parse_expiry(value: Any) -> float | None:
    """Seconds from now until ``value`` (ISO 8601), or None if absent / unparsable."""
    if not isinstance(value, str):
        return None
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    return (expiry - datetime.now(UTC)).total_seconds()


class TokenProvider:
    """Short-lived OAuth token from ``databricks auth token``, cached in memory."""

    def __init__(
        self,
        profile: str | None = None,
        ttl_seconds: float = TOKEN_TTL_SECONDS,
        runner: Runner | None = None,
        clock: Callable[[], float] = time.monotonic,
        cli: str | None = None,
    ) -> None:
        self._profile = profile
        self._ttl = ttl_seconds
        self._runner = runner or _run_cli
        self._clock = clock
        self._cli = cli
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        state = "cached" if self._token else "empty"
        return f"TokenProvider(profile={self._profile!r}, token=<{state}>)"

    def token(self) -> str:
        with self._lock:
            if self._token is None or self._clock() >= self._expires_at:
                self._token, lifetime = self._fetch()
                self._expires_at = self._clock() + lifetime
            return self._token

    def invalidate(self) -> None:
        with self._lock:
            self._token = None
            self._expires_at = 0.0

    def _fetch(self) -> tuple[str, float]:
        cli = self._cli or shutil.which("databricks")
        if not cli:
            raise ConfigError("Databricks CLI not found on PATH (needed for authentication)")
        args = [cli, "auth", "token"]
        if self._profile:
            args += ["--profile", self._profile]
        login = "databricks auth login" + (f" --profile {self._profile}" if self._profile else "")
        try:
            done = self._runner(args)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AuthenticationError(
                f"Databricks CLI did not answer; run `{login}` and retry"
            ) from exc
        if done.returncode != 0:
            # stderr is deliberately not propagated (it may contain workspace details).
            raise AuthenticationError(f"Databricks login required: run `{login}`")
        out = done.stdout or ""
        try:
            payload = json.loads(out[out.index("{") :])
            token = payload["access_token"]
        except (ValueError, KeyError, TypeError):
            raise AuthenticationError(
                f"Unexpected answer from the Databricks CLI; run `{login}`"
            ) from None
        if not isinstance(token, str) or not token:
            raise AuthenticationError(f"Databricks login required: run `{login}`")
        lifetime = self._ttl
        remaining = _parse_expiry(payload.get("expiry"))
        if remaining is not None:
            lifetime = min(lifetime, max(remaining - TOKEN_EXPIRY_MARGIN_SECONDS, 0.0))
        return token, lifetime


# --- Read-only guard -----------------------------------------------------------------------

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|COPY|OPTIMIZE|"
    r"VACUUM|REFRESH|RESTORE|REPLACE\s+TABLE|SET|USE|CALL|EXECUTE|MSCK|ANALYZE)\b",
    re.IGNORECASE,
)


def _code_only(sql: str) -> str:
    code = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    return re.sub(r"'(?:[^'\\]|\\.|'')*'", "''", code)


def ensure_read_only(bound: contracts.BoundQuery) -> None:
    """Refuse anything but the unmodified SQL of a registered contract, if it is a SELECT."""
    name = bound.contract.name
    if contracts.CONTRACTS.get(name) is not bound.contract:
        raise ReadOnlyViolation(f"{name!r} is not a registered search contract")
    if bound.sql != contracts.load_sql(name):
        raise ReadOnlyViolation(f"SQL of {name!r} differs from its contract file")
    code = _code_only(bound.sql)
    if ";" in code or not re.match(r"\s*(WITH|SELECT)\b", code, re.IGNORECASE):
        raise ReadOnlyViolation(f"{name!r} is not a single SELECT statement")
    if _FORBIDDEN.search(code):
        raise ReadOnlyViolation(f"{name!r} contains a non-read-only keyword")
    if set(bound.parameters) != set(bound.contract.param_names):
        raise ReadOnlyViolation(f"parameters of {name!r} do not match its contract")


# --- Executor ------------------------------------------------------------------------------

_AUTH_HINTS = (
    "401",
    "403",
    "unauthorized",
    "unauthenticated",
    "invalid access token",
    "invalid_token",
    "token is expired",
    "expired token",
    "token expired",
    "permission_denied",
    "credential was not sent",
)
_AUTH_HTTP_CODES = {401, 403}


def is_auth_error(exc: BaseException) -> bool:
    """True when Databricks refused the credentials.

    The connector's ``RequestError`` carries the HTTP status in ``exc.context["http-code"]``
    (an invalid token gives 401 "Credential was not sent or was of an unsupported type");
    the message is checked as a fallback.
    """
    context = getattr(exc, "context", None)
    if isinstance(context, dict):
        try:
            if int(context.get("http-code") or 0) in _AUTH_HTTP_CODES:
                return True
        except (TypeError, ValueError):
            pass
    text = f"{type(exc).__name__} {exc}".lower()
    return any(hint in text for hint in _AUTH_HINTS)


def _default_connect(**kwargs: Any) -> Any:
    try:
        from databricks import sql as dbsql
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise ConfigError(
            'databricks-sql-connector is not installed: pip install -e ".[databricks]"'
        ) from exc
    return dbsql.connect(**kwargs)


class DatabricksExecutor:
    """Runs bound search contracts on a SQL warehouse (one shared connection, serialised).

    The connector's connections are not meant to be shared between threads (DB-API
    threadsafety 1), so statements are serialised by a lock — adequate for a local app.
    """

    def __init__(
        self,
        settings: ConnectionSettings,
        tokens: TokenProvider | None = None,
        connect: Callable[..., Any] | None = None,
        max_connection_age: float = CONNECTION_MAX_AGE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._tokens = tokens or TokenProvider(settings.profile)
        self._connect = connect or _default_connect
        self._max_age = max_connection_age
        self._clock = clock
        self._conn: Any = None
        self._opened_at = 0.0
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f"DatabricksExecutor(profile={self._settings.profile!r})"

    def run(self, bound: contracts.BoundQuery) -> tuple[list[str], list[tuple]]:
        ensure_read_only(bound)
        with self._lock:
            for attempt in (1, 2):
                try:
                    conn = self._connection()
                    with conn.cursor() as cur:
                        cur.execute(bound.sql, parameters=bound.parameters)
                        columns = [d[0] for d in cur.description]
                        rows = [tuple(r) for r in cur.fetchall()]
                    return columns, rows
                except (ConfigError, AuthenticationError):
                    raise
                except Exception as exc:
                    if not is_auth_error(exc):
                        raise
                    self._reset(invalidate_token=True)
                    if attempt == 2:
                        raise AuthenticationError(
                            "Databricks refused the credentials; run `databricks auth login`"
                        ) from exc
        raise AssertionError("unreachable")  # pragma: no cover

    def close(self) -> None:
        with self._lock:
            self._reset(invalidate_token=False)

    def _connection(self) -> Any:
        if self._conn is not None and self._clock() - self._opened_at >= self._max_age:
            self._reset(invalidate_token=False)
        if self._conn is None:
            self._conn = self._connect(
                server_hostname=self._settings.server_hostname,
                http_path=self._settings.http_path,
                access_token=self._tokens.token(),
            )
            self._opened_at = self._clock()
        return self._conn

    def _reset(self, invalidate_token: bool) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            with contextlib.suppress(Exception):  # closing a broken connection must not fail
                conn.close()
        if invalidate_token:
            self._tokens.invalidate()
