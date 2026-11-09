"""Python client of the search layer (Phase 15A): the only way the application queries data.

``SearchClient`` names a contract from ``contracts.py``, validates the inputs with ``bind()``,
runs the bound statement through an executor (``DatabricksExecutor`` in production, a fake in
tests) and returns a ``SearchResult``. It never builds SQL.

Every failure becomes a ``SearchError`` whose ``message`` is safe to show to users (French, no
host, token or stack trace); technical details are logged server side with secrets redacted.
"""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from career_intelligence.config import ConfigError
from career_intelligence.search import contracts
from career_intelligence.search.connection import (
    AuthenticationError,
    DatabricksExecutor,
    ReadOnlyViolation,
    load_connection_settings,
)

logger = logging.getLogger(__name__)

FETCH_ALL_MAX_ROWS = 1000

MESSAGES = {
    "validation": "Paramètre de recherche invalide : {detail}",
    "configuration": (
        "La connexion à Databricks n'est pas configurée. Renseignez DATABRICKS_SERVER_HOSTNAME "
        "et DATABRICKS_WAREHOUSE_ID (ou DATABRICKS_HTTP_PATH) dans le fichier .env."
    ),
    "authentication": (
        "Connexion Databricks impossible : exécutez `databricks auth login` puis réessayez."
    ),
    "unavailable": (
        "Le service de données est momentanément indisponible. Réessayez dans un instant."
    ),
    "internal": "Une erreur interne est survenue. Les détails ont été journalisés.",
}

_REDACTIONS = (
    (re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]*"), "<token>"),  # JWT / OAuth access token
    (re.compile(r"\bdapi[0-9a-f]{16,}\b", re.IGNORECASE), "<token>"),  # personal access token
    (
        re.compile(r"(access_token|authorization|bearer)\S*\s*[:=]?\s*\S+", re.IGNORECASE),
        r"\1=<redacted>",
    ),
    (re.compile(r"[\w.-]+\.(?:cloud\.)?databricks\.com", re.IGNORECASE), "<workspace>"),
    (re.compile(r"[\w.-]+\.azuredatabricks\.net", re.IGNORECASE), "<workspace>"),
    (re.compile(r"/sql/[0-9.]+/warehouses/\w+"), "<warehouse>"),
)


def redact(text: str) -> str:
    """Remove tokens, workspace hosts and warehouse paths from a message."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


class SearchError(RuntimeError):
    """A search failed. ``message`` is user-facing; ``kind`` drives the UI behaviour."""

    def __init__(self, kind: str, detail: str = "") -> None:
        self.kind = kind
        self.message = MESSAGES[kind].format(detail=detail)
        super().__init__(self.message)


class Executor(Protocol):
    def run(self, bound: contracts.BoundQuery) -> tuple[list[str], list[tuple]]: ...


@dataclass(frozen=True)
class SearchResult:
    contract: str
    rows: pd.DataFrame
    total: int
    page: int
    page_size: int | None

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(self.rows.columns)

    @property
    def pages(self) -> int:
        if not self.page_size:
            return 1 if self.total else 0
        return math.ceil(self.total / self.page_size)

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def empty(self) -> bool:
        return self.rows.empty

    def records(self) -> list[dict[str, Any]]:
        return self.rows.to_dict(orient="records")


class SearchClient:
    def __init__(self, executor: Executor) -> None:
        self._executor = executor

    def __repr__(self) -> str:
        return f"SearchClient(executor={type(self._executor).__name__})"

    def search(
        self,
        name: str,
        page: int = 1,
        page_size: int = contracts.PAGE_SIZE_DEFAULT,
        **params: Any,
    ) -> SearchResult:
        """Run one page of contract ``name``."""
        try:
            bound = contracts.bind(name, page=page, page_size=page_size, **params)
        except ValueError as exc:
            raise SearchError("validation", str(exc)) from exc
        columns, rows = self._execute(bound)
        contract = bound.contract
        if tuple(columns) != contract.columns:
            logger.error("Contract %s returned unexpected columns %s", name, columns)
            raise SearchError("internal")
        frame = pd.DataFrame(rows, columns=list(columns))
        if contract.paginated:
            total = int(frame["total_resultats"].iloc[0]) if len(frame) else 0
            return SearchResult(name, frame, total, page, page_size)
        return SearchResult(name, frame, len(frame), 1, None)

    def get(self, name: str, **params: Any) -> dict[str, Any] | None:
        """The single row of a non-paginated contract (e.g. ``fiche_metier``), or None."""
        if contracts.get_contract(name).paginated:
            raise ValueError(f"{name} is paginated: use search() or fetch_all()")
        result = self.search(name, **params)
        return result.records()[0] if len(result.rows) else None

    def fetch_all(
        self, name: str, max_rows: int = FETCH_ALL_MAX_ROWS, **params: Any
    ) -> SearchResult:
        """Every page of a paginated contract (for short lists such as filter options)."""
        frames, total = [], 0
        for result in self._pages(name, **params):
            frames.append(result.rows)
            total = result.total
            if total > max_rows:
                raise SearchError("validation", f"plus de {max_rows} résultats, affinez la requête")
        rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        return SearchResult(name, rows, total, 1, None)

    def _pages(self, name: str, **params: Any) -> Iterator[SearchResult]:
        page = 1
        while True:
            result = self.search(name, page=page, page_size=contracts.PAGE_SIZE_MAX, **params)
            yield result
            if not result.has_next:
                return
            page += 1

    def _execute(self, bound: contracts.BoundQuery) -> tuple[list[str], list[tuple]]:
        name = bound.contract.name
        try:
            return self._executor.run(bound)
        except ConfigError as exc:
            logger.warning("Search %s: configuration error: %s", name, redact(str(exc)))
            raise SearchError("configuration") from None
        except AuthenticationError as exc:
            logger.warning("Search %s: authentication error: %s", name, redact(str(exc)))
            raise SearchError("authentication") from None
        except ReadOnlyViolation as exc:
            logger.error("Search %s refused: %s", name, redact(str(exc)))
            raise SearchError("internal") from None
        except Exception as exc:  # noqa: BLE001 - connector / network errors of any type
            logger.error("Search %s failed: %s: %s", name, type(exc).__name__, redact(str(exc)))
            raise SearchError("unavailable") from None


def create_client() -> SearchClient:
    """Production client: settings from the environment, token from the Databricks CLI."""
    try:
        settings = load_connection_settings()
    except ConfigError as exc:
        logger.warning("Databricks settings: %s", exc)
        raise SearchError("configuration") from None
    return SearchClient(DatabricksExecutor(settings))
