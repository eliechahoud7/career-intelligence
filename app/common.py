"""Shared helpers of the Streamlit application (Phase 15B).

All data access goes through ``SearchClient`` (registered search contracts, no SQL here).
Credentials stay on the server: the client is created by ``create_client()`` from the
environment and the Databricks CLI login, and only user-facing messages are displayed.
"""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

from career_intelligence.config import load_settings
from career_intelligence.search.client import SearchClient, SearchError, create_client

_APP = load_settings().get("app", {})
TITLE: str = _APP.get("title", "Career Intelligence")
PAGE_SIZE: int = int(_APP.get("page_size", 20))

SEARCH_PAGE = "pages/rechercher_metier.py"
PROFILE_PAGE = "pages/fiche_metier.py"
TRAINING_PAGE = "pages/explorer_formations.py"
LABOUR_PAGE = "pages/explorer_marche_travail.py"

OUI_NON = {"O": "Oui", "N": "Non"}


@st.cache_resource(show_spinner=False)
def get_client() -> SearchClient:
    """One client (connection + in-memory token) per server process."""
    return create_client()


@st.cache_data(ttl=3600, max_entries=500, show_spinner=False)
def _query(method: str, name: str, page: int, params: tuple[tuple[str, Any], ...]) -> Any:
    client = get_client()
    kwargs = dict(params)
    if method == "search":
        return client.search(name, page=page, page_size=PAGE_SIZE, **kwargs)
    if method == "fetch_all":
        return client.fetch_all(name, **kwargs)
    return client.get(name, **kwargs)


def load(method: str, name: str, page: int = 1, **params: Any) -> Any:
    """Run a contract (``search`` / ``fetch_all`` / ``get``); on failure show the error and stop."""
    try:
        with st.spinner("Chargement des données…"):
            return _query(method, name, page, tuple(sorted(params.items())))
    except SearchError as err:
        show_error(err)
        st.stop()


def show_error(err: SearchError) -> None:
    """Display only the user-facing message of a search error (never a trace or a host)."""
    if err.kind == "validation":
        st.warning(err.message)
    elif err.kind == "configuration":
        st.error(err.message)
        st.caption("Voir la section « Lancer l'application » du README.")
    else:
        st.error(err.message)


_MARKDOWN = re.compile(r"([\\`*_{}\[\]()<>#+\-.!|~])")


def plain(text: Any) -> str:
    """Source text rendered literally by ``st.markdown`` (escaped, line breaks kept)."""
    if text is None:
        return ""
    return _MARKDOWN.sub(r"\\\1", str(text)).replace("\n", "  \n")


def oui_non(value: Any) -> str:
    return OUI_NON.get(value, "Non renseigné")


def attribution(licence: str, source: str) -> None:
    st.divider()
    st.caption(f":material/verified: Source : {plain(source)} — Licence : {plain(licence)}")


# --- Visual design -------------------------------------------------------------------------
# Colours, radii and the navy sidebar come from .streamlit/config.toml (official theming).
# The CSS below only styles this app's own HTML classes (ci-*) and containers created with a
# key, which Streamlit exposes through its documented ".st-key-<key>" class. It does not rely
# on Streamlit's internal DOM structure.

_CSS = """
<style>
.ci-hero {
  background: linear-gradient(135deg, #142B4A 0%, #1B3A66 55%, #2563EB 100%);
  border-radius: 18px; padding: 1.6rem 2rem 1.5rem; color: #FFFFFF;
  box-shadow: 0 10px 30px rgba(20, 43, 74, 0.18);
}
.ci-hero .ci-eyebrow {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase;
  color: #5EEAD4; margin: 0 0 0.45rem;
}
.ci-hero h1 {
  color: #FFFFFF; font-size: 2rem; font-weight: 700; line-height: 1.2; margin: 0 0 0.55rem;
  padding: 0;
}
.ci-hero p {
  color: #DBEAFE; font-size: 1rem; line-height: 1.6; margin: 0.2rem 0; max-width: 54rem;
}
.ci-brand { display: flex; align-items: center; gap: 0.7rem; padding: 0.2rem 0 0.4rem; }
.ci-brand .ci-mark {
  width: 38px; height: 38px; border-radius: 11px; flex: none;
  background: linear-gradient(135deg, #2563EB, #0D9488);
  display: flex; align-items: center; justify-content: center;
  color: #FFFFFF; font-weight: 800; font-size: 0.95rem; letter-spacing: 0.02em;
  box-shadow: 0 4px 14px rgba(13, 148, 136, 0.35);
}
.ci-brand .ci-name {
  font-weight: 700; font-size: 1.12rem; color: #FFFFFF; letter-spacing: 0.01em;
}
.ci-brand .ci-tag {
  font-size: 0.7rem; color: #5EEAD4; letter-spacing: 0.08em; text-transform: uppercase;
}
[class*="st-key-card"], [class*="st-key-result"] {
  background: #FFFFFF; border-radius: 14px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06), 0 6px 18px rgba(15, 23, 42, 0.05);
}
[class*="st-key-result"]:hover { box-shadow: 0 6px 22px rgba(37, 99, 235, 0.14); }
[class*="st-key-result"] a p {
  font-weight: 600; color: #142B4A; white-space: normal; overflow: visible; text-overflow: clip;
}
.st-key-card-search input { font-size: 1.05rem; }
@media (max-width: 640px) {
  .st-key-btn-rechercher button { width: 100%; min-height: 2.75rem; }
}
</style>
"""

_MARK = "CI"  # monogram (inline SVG is removed by the st.html sanitiser)


def apply_style() -> None:
    """Inject the app stylesheet (once per page run)."""
    st.html(_CSS)


def brand(title: str) -> None:
    """Application identity at the top of the sidebar."""
    st.html(
        f'<div class="ci-brand"><div class="ci-mark">{_MARK}</div><div>'
        f'<div class="ci-name">{html.escape(title)}</div>'
        '<div class="ci-tag">Intelligence métiers</div></div></div>'
    )


def hero(eyebrow: str, title: str, paragraphs: list[str]) -> None:
    """Page header card (all values are HTML-escaped)."""
    body = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    st.html(
        f'<div class="ci-hero"><div class="ci-eyebrow">{html.escape(eyebrow)}</div>'
        f"<h1>{html.escape(title)}</h1>{body}</div>"
    )


def section(icon: str, title: str) -> None:
    """Small section heading inside a card (``icon`` is a Material icon shortcode)."""
    st.markdown(f":blue[{icon}] **{plain(title)}**")
