"""Offline tests of the search client and the Databricks connection module (Phase 15A).

No network, no Databricks: the CLI, the connector and the executor are replaced by fakes.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from career_intelligence.config import ConfigError
from career_intelligence.search import contracts as c
from career_intelligence.search.client import (
    SearchClient,
    SearchError,
    SearchResult,
    create_client,
    redact,
)
from career_intelligence.search.connection import (
    AuthenticationError,
    ConnectionSettings,
    DatabricksExecutor,
    ReadOnlyViolation,
    TokenProvider,
    ensure_read_only,
    is_auth_error,
    load_connection_settings,
)

HOST = "dbc-test-0000.cloud.databricks.com"
WAREHOUSE = "abc123def456"
TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.c2lnbmF0dXJl"
ENV = {
    "DATABRICKS_SERVER_HOSTNAME": f"https://{HOST}/",
    "DATABRICKS_WAREHOUSE_ID": WAREHOUSE,
    "DATABRICKS_CONFIG_PROFILE": "career-intelligence",
}


# --- Fakes ---------------------------------------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class CliRunner:
    """Fake ``databricks auth token``: hands out token-1, token-2, ..."""

    def __init__(self, returncode=0, prefix="Notice: CLI update available\n", expiry=None):
        self.calls: list[list[str]] = []
        self.returncode = returncode
        self.prefix = prefix
        self.expiry = expiry

    def __call__(self, args):
        self.calls.append(args)
        payload = {"access_token": f"token-{len(self.calls)}", "token_type": "Bearer"}
        if self.expiry:
            payload["expiry"] = self.expiry
        out = self.prefix + json.dumps(payload)
        return subprocess.CompletedProcess(args, self.returncode, out, f"error for {HOST}")


class Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, parameters=None):
        self.conn.executed.append((sql, parameters))
        if self.conn.failures:
            raise self.conn.failures.pop(0)
        self.description = [(col,) for col in self.conn.columns]

    def fetchall(self):
        return self.conn.rows


class Connection:
    def __init__(self, columns, rows, failures):
        self.columns, self.rows, self.failures = columns, rows, failures
        self.executed: list = []
        self.closed = False

    def cursor(self):
        return Cursor(self)

    def close(self):
        self.closed = True


class Connector:
    """Fake ``databricks.sql.connect``: records every connection and its kwargs."""

    def __init__(self, columns=("x",), rows=(), failures=()):
        self.columns, self.rows = list(columns), [tuple(r) for r in rows]
        self.failures = list(failures)
        self.connections: list[tuple[dict, Connection]] = []

    def __call__(self, **kwargs):
        conn = Connection(self.columns, self.rows, self.failures)
        self.connections.append((kwargs, conn))
        return conn


def fake_rows(name: str, n: int, total: int | None = None) -> list[tuple]:
    contract = c.get_contract(name)
    rows = []
    for i in range(n):
        row = {col: f"{col}-{i}" for col in contract.columns}
        if contract.paginated:
            row["total_resultats"] = n if total is None else total
        rows.append(tuple(row[col] for col in contract.columns))
    return rows


class FakeExecutor:
    def __init__(self, n=3, total=None, error=None, columns=None):
        self.n, self.total, self.error, self.columns = n, total, error, columns
        self.bound: list[c.BoundQuery] = []

    def run(self, bound):
        self.bound.append(bound)
        if self.error:
            raise self.error
        ensure_read_only(bound)
        name = bound.contract.name
        if bound.contract.paginated:
            size, offset = bound.parameters["page_size"], bound.parameters["offset"]
            total = self.n if self.total is None else self.total
            n = max(0, min(size, total - offset))
            rows = fake_rows(name, n, total)
        else:
            rows = fake_rows(name, self.n)
        return list(self.columns or bound.contract.columns), rows


def executor(connector, clock=None, runner=None, **kwargs):
    settings = ConnectionSettings(HOST, f"/sql/1.0/warehouses/{WAREHOUSE}", "career-intelligence")
    tokens = TokenProvider("career-intelligence", runner=runner or CliRunner(), cli="databricks")
    return DatabricksExecutor(
        settings, tokens=tokens, connect=connector, clock=clock or Clock(), **kwargs
    )


# --- Settings ------------------------------------------------------------------------------


def test_settings_from_environment():
    s = load_connection_settings(ENV)
    assert s.server_hostname == HOST
    assert s.http_path == f"/sql/1.0/warehouses/{WAREHOUSE}"
    assert s.profile == "career-intelligence"
    assert HOST not in repr(s) and WAREHOUSE not in repr(s)


def test_settings_explicit_http_path_wins():
    env = {**ENV, "DATABRICKS_HTTP_PATH": "/sql/1.0/warehouses/other999"}
    assert load_connection_settings(env).http_path == "/sql/1.0/warehouses/other999"


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({}, "DATABRICKS_SERVER_HOSTNAME"),
        ({"DATABRICKS_SERVER_HOSTNAME": HOST}, "DATABRICKS_WAREHOUSE_ID"),
        ({**ENV, "DATABRICKS_WAREHOUSE_ID": "abc/../x"}, "not a valid warehouse id"),
        ({**ENV, "DATABRICKS_SERVER_HOSTNAME": "bad host!"}, "not a valid host name"),
        ({**ENV, "DATABRICKS_HTTP_PATH": "/sql/1.0/endpoints/x;drop"}, "must look like"),
    ],
)
def test_settings_errors_name_variables_not_values(env, message):
    with pytest.raises(ConfigError, match=message) as err:
        load_connection_settings(env)
    assert WAREHOUSE not in str(err.value)


# --- Token provider ------------------------------------------------------------------------


def test_token_from_cli_cached_and_refreshed_after_ttl():
    runner, clock = CliRunner(), Clock()
    tp = TokenProvider("career-intelligence", ttl_seconds=600, runner=runner, clock=clock, cli="db")
    assert tp.token() == "token-1"
    assert runner.calls == [["db", "auth", "token", "--profile", "career-intelligence"]]
    clock.now += 599
    assert tp.token() == "token-1" and len(runner.calls) == 1
    clock.now += 2
    assert tp.token() == "token-2" and len(runner.calls) == 2


def test_token_invalidate_forces_refresh():
    runner = CliRunner()
    tp = TokenProvider(None, runner=runner, clock=Clock(), cli="db")
    assert tp.token() == "token-1"
    tp.invalidate()
    assert tp.token() == "token-2"
    assert runner.calls[0] == ["db", "auth", "token"]  # no profile -> CLI default


def test_token_lifetime_capped_by_cli_expiry():
    soon = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    runner, clock = CliRunner(expiry=soon), Clock()
    tp = TokenProvider("p", ttl_seconds=3600, runner=runner, clock=clock, cli="db")
    tp.token()
    clock.now += 5 * 60 - 60  # past expiry minus the 2-minute margin
    tp.token()
    assert len(runner.calls) == 2


def test_token_never_in_repr():
    tp = TokenProvider("p", runner=CliRunner(), clock=Clock(), cli="db")
    tp.token()
    assert "token-1" not in repr(tp) and "cached" in repr(tp)


def test_cli_failure_message_is_safe():
    tp = TokenProvider("p", runner=CliRunner(returncode=1), clock=Clock(), cli="db")
    with pytest.raises(AuthenticationError) as err:
        tp.token()
    assert "databricks auth login --profile p" in str(err.value)
    assert HOST not in str(err.value)  # CLI stderr is not propagated


@pytest.mark.parametrize("stdout", ["not json", '{"token_type": "Bearer"}', '{"access_token": ""}'])
def test_cli_unexpected_output(stdout):
    def runner(args):
        return subprocess.CompletedProcess(args, 0, stdout, "")

    with pytest.raises(AuthenticationError):
        TokenProvider("p", runner=runner, clock=Clock(), cli="db").token()


def test_cli_timeout_and_missing_cli(monkeypatch):
    def slow(args):
        raise subprocess.TimeoutExpired(args, 60)

    with pytest.raises(AuthenticationError, match="did not answer"):
        TokenProvider("p", runner=slow, clock=Clock(), cli="db").token()
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(ConfigError, match="CLI not found"):
        TokenProvider("p", runner=CliRunner(), clock=Clock()).token()


# --- Read-only guard -----------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(c.CONTRACTS))
def test_every_contract_passes_the_read_only_guard(name):
    contract = c.get_contract(name)
    values = {p.name: ("x1" if p.type == c.STRING else None) for p in contract.params}
    params = {k: (None if k.endswith(("_size", "offset")) else v) for k, v in values.items()}
    params |= {"page_size": 20, "offset": 0} if contract.paginated else {}
    ensure_read_only(c.BoundQuery(contract, c.load_sql(name), params))


def _bound(name="rechercher_metiers", **kw):
    return c.bind(name, q="infirmier", **kw)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: c.BoundQuery(
            b.contract, "DROP TABLE career_intelligence.gold.metier", b.parameters
        ),
        lambda b: c.BoundQuery(b.contract, b.sql + "; DELETE FROM x", b.parameters),
        lambda b: c.BoundQuery(
            b.contract, b.sql.replace("SELECT", "SELECT /*x*/", 1), b.parameters
        ),
        lambda b: c.BoundQuery(
            c.Contract(**{**b.contract.__dict__}), b.sql, b.parameters
        ),  # look-alike, not the registered object
        lambda b: c.BoundQuery(b.contract, b.sql, {**b.parameters, "extra": 1}),
    ],
)
def test_read_only_guard_refuses_tampering(mutate):
    with pytest.raises(ReadOnlyViolation):
        ensure_read_only(mutate(_bound()))


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO t SELECT 1",
        "SELECT 1; DROP TABLE t",
        "WITH a AS (SELECT 1) MERGE INTO t USING a ON 1=1 WHEN MATCHED THEN DELETE",
        "SET spark.sql.ansi.enabled = false",
        "CREATE OR REPLACE VIEW v AS SELECT 1",
    ],
)
def test_read_only_keyword_check(monkeypatch, sql):
    bound = _bound()
    monkeypatch.setattr(c, "load_sql", lambda _name: sql)  # pretend the file contained it
    with pytest.raises(ReadOnlyViolation):
        ensure_read_only(c.BoundQuery(bound.contract, sql, bound.parameters))


# --- Executor ------------------------------------------------------------------------------


def test_executor_passes_settings_token_and_named_parameters():
    connector = Connector(columns=["a"], rows=[(1,)])
    ex = executor(connector)
    bound = _bound()
    assert ex.run(bound) == (["a"], [(1,)])
    kwargs, conn = connector.connections[0]
    assert kwargs == {
        "server_hostname": HOST,
        "http_path": f"/sql/1.0/warehouses/{WAREHOUSE}",
        "access_token": "token-1",
    }
    assert conn.executed == [(bound.sql, bound.parameters)]
    assert "token" not in repr(ex) and HOST not in repr(ex)


def test_executor_reuses_then_renews_connection_by_age():
    connector, clock = Connector(), Clock()
    ex = executor(connector, clock=clock, max_connection_age=100)
    ex.run(_bound())
    ex.run(_bound())
    assert len(connector.connections) == 1
    clock.now += 100
    ex.run(_bound())
    assert len(connector.connections) == 2 and connector.connections[0][1].closed


def test_executor_retries_once_with_fresh_token_on_auth_error():
    connector = Connector(failures=[RuntimeError("HTTP 401 Unauthorized: invalid access token")])
    runner = CliRunner()
    ex = executor(connector, runner=runner)
    ex.run(_bound())
    assert [k["access_token"] for k, _ in connector.connections] == ["token-1", "token-2"]
    assert connector.connections[0][1].closed


def test_executor_gives_up_after_second_auth_error():
    failures = [RuntimeError("401 Unauthorized"), RuntimeError("403 PERMISSION_DENIED")]
    ex = executor(Connector(failures=failures))
    with pytest.raises(AuthenticationError):
        ex.run(_bound())


def test_executor_does_not_retry_other_errors():
    connector = Connector(failures=[RuntimeError("TABLE_OR_VIEW_NOT_FOUND")])
    with pytest.raises(RuntimeError, match="NOT_FOUND"):
        executor(connector).run(_bound())
    assert len(connector.connections) == 1


def test_executor_refuses_before_connecting():
    connector = Connector()
    bound = _bound()
    with pytest.raises(ReadOnlyViolation):
        executor(connector).run(c.BoundQuery(bound.contract, "DROP TABLE x", bound.parameters))
    assert connector.connections == []


def test_executor_close():
    connector = Connector()
    ex = executor(connector)
    ex.run(_bound())
    ex.close()
    assert connector.connections[0][1].closed


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("HTTP 401", True),
        ("Invalid access token", True),
        ("token is expired", True),
        ("PERMISSION_DENIED", True),
        ("PARSE_SYNTAX_ERROR", False),
        ("Connection reset", False),
    ],
)
def test_is_auth_error(message, expected):
    assert is_auth_error(RuntimeError(message)) is expected


class RequestError(Exception):
    """Shape of databricks.sql.exc.RequestError, as observed live for an invalid token."""

    def __init__(self, message, context):
        super().__init__(message)
        self.context = context


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        ({"http-code": 401, "method": "OpenSession"}, True),
        ({"http-code": "403"}, True),
        ({"http-code": 500}, False),
        ({"http-code": None}, False),
        ({"http-code": "n/a"}, False),
    ],
)
def test_is_auth_error_uses_connector_http_code(context, expected):
    exc = RequestError("Error during request to server: : something went wrong.", context)
    assert is_auth_error(exc) is expected


def test_real_invalid_token_error_is_retried():
    real = RequestError(
        "Error during request to server: : Credential was not sent or was of an unsupported "
        "type for this API..",
        {"http-code": 401, "method": "OpenSession"},
    )
    connector = Connector(failures=[real])
    executor(connector).run(_bound())
    assert [k["access_token"] for k, _ in connector.connections] == ["token-1", "token-2"]


# --- SearchClient --------------------------------------------------------------------------


def test_search_returns_typed_page():
    ex = FakeExecutor(total=45)
    result = SearchClient(ex).search("rechercher_metiers", q="infirmier", page=2, page_size=20)
    assert isinstance(result, SearchResult)
    assert result.columns == c.get_contract("rechercher_metiers").columns
    assert (result.total, result.page, result.pages) == (45, 2, 3)
    assert result.has_previous and result.has_next and len(result.rows) == 20
    assert ex.bound[0].parameters["offset"] == 20


def test_search_last_and_empty_pages():
    client = SearchClient(FakeExecutor(total=45))
    last = client.search("rechercher_metiers", q="infirmier", page=3, page_size=20)
    assert len(last.rows) == 5 and not last.has_next
    empty = SearchClient(FakeExecutor(total=0)).search("rechercher_metiers", q="zzz")
    assert empty.empty and empty.total == 0 and empty.pages == 0


def test_get_single_row_contract():
    client = SearchClient(FakeExecutor(n=1))
    row = client.get("fiche_metier", code_rome="J1506")
    assert set(row) == set(c.get_contract("fiche_metier").columns)
    assert SearchClient(FakeExecutor(n=0)).get("fiche_metier", code_rome="Z9999") is None
    with pytest.raises(ValueError, match="paginated"):
        client.get("rechercher_metiers", q="infirmier")


def test_fetch_all_pages_and_limit():
    ex = FakeExecutor(total=228)
    result = SearchClient(ex).fetch_all("rechercher_fap")
    assert len(result.rows) == 228 and result.total == 228
    assert [b.parameters["offset"] for b in ex.bound] == [0, 100, 200]
    with pytest.raises(SearchError) as err:
        SearchClient(FakeExecutor(total=5000)).fetch_all("rechercher_fap")
    assert err.value.kind == "validation"


def test_validation_error_is_user_facing():
    with pytest.raises(SearchError) as err:
        SearchClient(FakeExecutor()).search("rechercher_metiers", q="a")
    assert err.value.kind == "validation"
    assert err.value.message.startswith("Paramètre de recherche invalide")


def test_unknown_contract_never_reaches_executor():
    ex = FakeExecutor()
    with pytest.raises(SearchError):
        SearchClient(ex).search("DROP TABLE x")
    assert ex.bound == []


def test_unexpected_columns_are_refused():
    with pytest.raises(SearchError) as err:
        SearchClient(FakeExecutor(columns=["code_rome"])).search("rechercher_metiers", q="xx")
    assert err.value.kind == "internal"


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (ConfigError("Missing Databricks setting(s): DATABRICKS_SERVER_HOSTNAME"), "configuration"),
        (AuthenticationError("Databricks login required"), "authentication"),
        (ReadOnlyViolation("refused"), "internal"),
        (
            RuntimeError(
                f"Error during request to https://{HOST}/sql/1.0/warehouses/{WAREHOUSE}"
                f" with Authorization: Bearer {TOKEN}"
            ),
            "unavailable",
        ),
    ],
)
def test_errors_are_sanitised(error, kind, caplog):
    caplog.set_level(logging.DEBUG, logger="career_intelligence.search.client")
    with pytest.raises(SearchError) as err:
        SearchClient(FakeExecutor(error=error)).search("rechercher_metiers", q="infirmier")
    assert err.value.kind == kind
    assert err.value.__cause__ is None and err.value.__suppress_context__
    for text in (err.value.message, caplog.text):
        assert HOST not in text and WAREHOUSE not in text and TOKEN not in text


def test_redact():
    text = f"https://{HOST}/sql/1.0/warehouses/{WAREHOUSE} token={TOKEN} dapi0123456789abcdef0123"
    out = redact(text)
    for secret in (HOST, WAREHOUSE, TOKEN, "dapi0123456789abcdef0123"):
        assert secret not in out


def test_create_client_without_settings(monkeypatch):
    for var in ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("DATABRICKS_HTTP_PATH", raising=False)
    monkeypatch.setattr(
        "career_intelligence.search.client.load_connection_settings",
        lambda: load_connection_settings({}),
    )
    with pytest.raises(SearchError) as err:
        create_client()
    assert err.value.kind == "configuration"


def test_create_client_builds_databricks_executor(monkeypatch):
    monkeypatch.setattr(
        "career_intelligence.search.client.load_connection_settings",
        lambda: load_connection_settings(ENV),
    )
    client = create_client()
    assert repr(client) == "SearchClient(executor=DatabricksExecutor)"


def test_client_module_contains_no_sql():
    from pathlib import Path

    import career_intelligence.search.client as client_module
    import career_intelligence.search.connection as connection_module

    tables = re.compile(
        r"career_intelligence\.(bronze|silver|gold)\.|career_intelligence\.search\.v_"
    )
    statements = re.compile(r"\b(SELECT\s+[\w*]+\s*,|FROM\s+\w+\.\w+|INSERT\s+INTO|DELETE\s+FROM)")
    for module in (client_module, connection_module):
        text = Path(module.__file__).read_text(encoding="utf-8")
        assert not tables.search(text), module.__name__
        assert not statements.search(text), module.__name__
