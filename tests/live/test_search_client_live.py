"""Live checks of the search client against Databricks (Phase 15A): authentication, token
refresh, reconnection, error handling and read-only execution.

Skipped unless configured (same variables as tests/live/test_search_live.py, except that the
token always comes from the Databricks CLI login):

    CAREER_INTELLIGENCE_LIVE=1
    DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH or DATABRICKS_WAREHOUSE_ID,
    DATABRICKS_CONFIG_PROFILE
"""

from __future__ import annotations

import os
import subprocess

import pytest

if os.environ.get("CAREER_INTELLIGENCE_LIVE") != "1":
    pytest.skip("live Databricks tests: set CAREER_INTELLIGENCE_LIVE=1", allow_module_level=True)

pytest.importorskip("databricks.sql", reason="install the [databricks] extra")

from career_intelligence.config import ConfigError  # noqa: E402
from career_intelligence.search import contracts as c  # noqa: E402
from career_intelligence.search.client import SearchClient, SearchError, create_client  # noqa: E402
from career_intelligence.search.connection import (  # noqa: E402
    ConnectionSettings,
    DatabricksExecutor,
    ReadOnlyViolation,
    TokenProvider,
    _run_cli,
    load_connection_settings,
)

try:
    SETTINGS = load_connection_settings()
except ConfigError as exc:
    pytest.skip(f"Databricks settings incomplete: {exc}", allow_module_level=True)


class CountingRunner:
    """Real ``databricks auth token`` calls, counted; optionally a bogus token first."""

    def __init__(self, bogus_first: bool = False) -> None:
        self.calls = 0
        self.bogus_first = bogus_first

    def __call__(self, args):
        self.calls += 1
        if self.bogus_first and self.calls == 1:
            out = '{"access_token": "invalid-token-for-test", "token_type": "Bearer"}'
            return subprocess.CompletedProcess(args, 0, out, "")
        return _run_cli(args)


def client_with(runner, **kwargs) -> tuple[SearchClient, DatabricksExecutor]:
    tokens = TokenProvider(SETTINGS.profile, runner=runner)
    executor = DatabricksExecutor(SETTINGS, tokens=tokens, **kwargs)
    return SearchClient(executor), executor


def test_create_client_end_to_end():
    client = create_client()
    row = client.get("fiche_metier", code_rome="J1506")
    assert row["code_rome"] == "J1506" and row["definition"].startswith("L'infirmier")
    page = client.search("rechercher_metiers", q="électricien", page=1, page_size=5)
    assert page.total >= 3 and len(page.rows) == 5 and page.pages >= 1
    fap = client.fetch_all("rechercher_fap")
    assert len(fap.rows) == fap.total == 228


def test_token_refresh_after_invalidate():
    runner = CountingRunner()
    client, executor = client_with(runner)
    client.get("fiche_metier", code_rome="M1805")
    assert runner.calls == 1
    client.get("fiche_metier", code_rome="M1805")
    assert runner.calls == 1  # cached token, reused connection
    executor._tokens.invalidate()
    executor.close()
    client.get("fiche_metier", code_rome="M1805")
    assert runner.calls == 2
    executor.close()


def test_reconnects_when_connection_too_old():
    runner = CountingRunner()
    client, executor = client_with(runner, max_connection_age=0)
    for code in ("J1506", "M1805"):
        assert client.get("fiche_metier", code_rome=code)["code_rome"] == code
    assert runner.calls == 1  # new connections, same in-memory token
    executor.close()


def test_rejected_token_is_replaced_once():
    runner = CountingRunner(bogus_first=True)
    client, executor = client_with(runner)
    row = client.get("fiche_metier", code_rome="J1506")
    assert row["code_rome"] == "J1506"
    assert runner.calls == 2  # bogus token refused by Databricks -> fresh CLI token
    executor.close()


def test_read_only_refusal_happens_before_any_connection():
    runner = CountingRunner()
    _, executor = client_with(runner)
    bound = c.bind("fiche_metier", code_rome="J1506")
    with pytest.raises(ReadOnlyViolation):
        executor.run(c.BoundQuery(bound.contract, "DROP VIEW career_intelligence.search.x", {}))
    assert runner.calls == 0


def test_unknown_warehouse_gives_safe_error():
    bad = ConnectionSettings(
        SETTINGS.server_hostname, "/sql/1.0/warehouses/0000000000000000", SETTINGS.profile
    )
    client = SearchClient(DatabricksExecutor(bad))
    with pytest.raises(SearchError) as err:
        client.get("fiche_metier", code_rome="J1506")
    assert err.value.kind in {"unavailable", "authentication"}
    assert SETTINGS.server_hostname not in err.value.message
