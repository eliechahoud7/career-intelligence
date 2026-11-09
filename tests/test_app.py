"""Offline tests of the Streamlit application (Phase 15B): search and profile pages.

The app runs through its real entry point (``app/streamlit_app.py``) with Streamlit's
AppTest; ``create_client`` is replaced by a client over a fake executor (no Databricks).
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

from career_intelligence.search import contracts as c  # noqa: E402
from career_intelligence.search.client import SearchClient, SearchError  # noqa: E402
from career_intelligence.search.connection import (  # noqa: E402
    AuthenticationError,
    ensure_read_only,
)

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
ENTRY = str(APP / "streamlit_app.py")
sys.path.insert(0, str(APP))
import common  # noqa: E402

DOMAINES = [
    {
        "code_grand_domaine": "J",
        "libelle_grand_domaine": "Santé",
        "code_domaine_professionnel": "J15",
        "libelle_domaine_professionnel": "Soins paramédicaux",
    },
    {
        "code_grand_domaine": "M",
        "libelle_grand_domaine": "Support à l'entreprise",
        "code_domaine_professionnel": "M18",
        "libelle_domaine_professionnel": "Systèmes d'information et de télécommunication",
    },
]
METIERS = [
    {
        "code_rome": f"J15{i:02d}",
        "libelle_rome": f"Infirmier / Infirmière n°{i}",
        "code_grand_domaine": "J",
        "libelle_grand_domaine": "Santé",
        "code_domaine_professionnel": "J15",
        "libelle_domaine_professionnel": "Soins paramédicaux",
        "champ_correspondant": "appellation_long" if i == 0 else "libelle_rome",
        "libelle_correspondant": "Infirmier puériculteur / Infirmière puéricultrice",
        "rang_pertinence": 5 if i == 0 else 4,
    }
    for i in range(25)
]
FICHE = {
    "code_rome": "J1506",
    "code_ogr": "38539",
    "libelle_rome": "Infirmier / Infirmière en soins généraux (IDE)",
    "code_grand_domaine": "J",
    "libelle_grand_domaine": "Santé",
    "code_domaine_professionnel": "J15",
    "libelle_domaine_professionnel": "Soins paramédicaux",
    "riasec_majeur": "S",
    "riasec_mineur": "I",
    "transition_eco": "Emploi Blanc",
    "transition_num": "N",
    "transition_demo": "O",
    "emploi_reglemente": "O",
    "emploi_cadre": None,
    "definition": "L'infirmier en soins généraux (IDE) dispense des soins *préventifs*.",
    "acces_metier": "Ce métier est accessible avec un Diplôme d'Etat d'Infirmier.\n- ligne 2",
    "nb_phrases_definition": 1,
    "nb_phrases_acces_metier": 2,
    "nb_appellations": 2,
    "nb_savoir_faire": 2,
    "nb_savoir_etre": 1,
    "nb_savoirs": 0,
    "nb_contextes_travail": 0,
    "nb_domaines_formation": 1,
    "_rome_version": "62",
}
APPELLATIONS = [
    {
        "code_rome": "J1506",
        "code_ogr_appellation": "1",
        "libelle_appellation_long": "IDE",
        "classification": "PRINCIPALE",
        "peu_usite": "N",
    },
    {
        "code_rome": "J1506",
        "code_ogr_appellation": "2",
        "libelle_appellation_long": "Infirmier hospitalier",
        "classification": "SYNONYME",
        "peu_usite": "O",
    },
]
COMPETENCES = [
    {
        "code_rome": "J1506",
        "type_element": "savoir_faire",
        "code_ogr_element": "1",
        "libelle_element": "Réaliser des soins",
        "coeur_metier": "Principale",
        "categorie": "Savoir-faire",
        "sous_categorie": "Soins",
    },
    {
        "code_rome": "J1506",
        "type_element": "savoir_faire",
        "code_ogr_element": "2",
        "libelle_element": "Évaluer une situation clinique",
        "coeur_metier": None,
        "categorie": "Savoir-faire",
        "sous_categorie": "Soins",
    },
    {
        "code_rome": "J1506",
        "type_element": "savoir_etre",
        "code_ogr_element": "3",
        "libelle_element": "Faire preuve d'empathie",
        "coeur_metier": None,
        "categorie": "Savoir-être professionnel",
        "sous_categorie": None,
    },
]
LICENCE = {
    "licence": "Licence Ouverte (fr-lo)",
    "attribution": "France Travail – ROME 4.0",
    "_rome_version": "62",
}
DATA = {
    "lister_domaines": DOMAINES,
    "rechercher_metiers": METIERS,
    "fiche_metier": [FICHE],
    "appellations_metier": APPELLATIONS,
    "competences_metier": COMPETENCES,
}


class FakeExecutor:
    """Serves DATA by contract (with paging); applies the real read-only guard."""

    def __init__(self, data=None, error=None):
        self.data = DATA if data is None else data
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def run(self, bound):
        ensure_read_only(bound)
        name, params = bound.contract.name, bound.parameters
        self.calls.append((name, params))
        if self.error:
            raise self.error
        rows = list(self.data.get(name, []))
        if name == "fiche_metier":
            rows = [r for r in rows if r["code_rome"] == params["code_rome"].strip().upper()]
        if name == "appellations_metier" and params.get("inclure_peu_usitees") is False:
            rows = [r for r in rows if r["peu_usite"] == "N"]
        if name == "competences_metier" and params.get("coeur_metier_seulement"):
            rows = [r for r in rows if r["coeur_metier"] == "Principale"]
        cols = list(bound.contract.columns)
        if bound.contract.paginated:
            total, off = len(rows), params["offset"]
            rows = [{**r, "total_resultats": total} for r in rows[off : off + params["page_size"]]]
        return cols, [tuple({**LICENCE, **r}.get(col) for col in cols) for r in rows]


@pytest.fixture
def fake(monkeypatch):
    def install(executor=None):
        executor = executor or FakeExecutor()
        monkeypatch.setattr(common, "create_client", lambda: SearchClient(executor))
        common.get_client.clear()
        common._query.clear()
        return executor

    yield install
    common.get_client.clear()
    common._query.clear()


def app(**query_params) -> AppTest:
    at = AppTest.from_file(ENTRY, default_timeout=30)
    at.query_params.update(query_params)
    return at


def text_of(at: AppTest) -> str:
    parts = []
    for kind in ("markdown", "caption", "info", "warning", "error", "title", "subheader"):
        parts += [str(e.value) for e in getattr(at, kind)]
    parts += [str(m.value) for m in at.metric]
    parts += [h.proto.body for h in at.get("html") if "<style>" not in h.proto.body]
    return html.unescape(re.sub(r"\\(.)", r"\1", "\n".join(parts)))  # unescape Markdown / HTML


def hero_title(at: AppTest) -> str:
    """Page title, rendered in the header card (<h1>) of the main area."""
    bodies = [h.proto.body for h in at.main.get("html")]
    return html.unescape(
        next(re.search(r"<h1>(.*?)</h1>", b).group(1) for b in bodies if "<h1>" in b)
    )


# --- Search page ---------------------------------------------------------------------------


def test_search_page_starts_without_query(fake):
    executor = fake()
    at = app().run()
    assert not at.exception
    assert hero_title(at) == "Rechercher un métier"
    assert "Recherchez par nom de métier, code ROME ou mot-clé" in text_of(at)
    assert len(at.info) == 0 and "Saisissez" not in text_of(at)  # no prompt text
    assert at.text_input(key="f_q").placeholder == "ex. électricien, infirmier, M1805"
    assert not at.button  # no results, so no pagination buttons yet
    assert [n for n, _ in executor.calls] == ["lister_domaines"]  # filters only, no search yet


def test_search_shows_results_match_and_attribution(fake):
    executor = fake()
    at = app()
    at.run()
    at.text_input[0].input("infirmier").run()
    assert not at.exception
    text = text_of(at)
    assert "25 métiers trouvés · Page 1 sur 2" in text
    assert "Correspondance — appellation" in text and "puériculteur" in text
    assert "Licence Ouverte" in text and "France Travail" in text
    search = [p for n, p in executor.calls if n == "rechercher_metiers"]
    assert search[-1]["q"] == "infirmier" and search[-1]["page_size"] == common.PAGE_SIZE
    assert at.query_params["q"] == ["infirmier"] or at.query_params["q"] == "infirmier"


def test_search_filters_are_passed_to_the_contract(fake):
    executor = fake()
    at = app(q="infirmier", gd="J", dp="J15", cadre="N", regl="O", textes="1").run()
    assert not at.exception
    params = [p for n, p in executor.calls if n == "rechercher_metiers"][-1]
    assert (params["code_grand_domaine"], params["code_domaine_professionnel"]) == ("J", "J15")
    assert (params["emploi_cadre"], params["emploi_reglemente"]) == ("N", "O")
    assert params["inclure_textes"] is True


def metiers(n: int) -> list[dict]:
    return [
        {**METIERS[1], "code_rome": f"K{i:04d}", "libelle_rome": f"Métier {i}"} for i in range(n)
    ]


def button(at: AppTest, label: str):
    return next(b for b in at.button if label in b.label)


def click(at: AppTest, label: str) -> None:
    """Click a pagination button; the result cache is cleared first so that every page shown
    comes from a fresh query and the parameters actually sent can be checked."""
    common._query.clear()
    button(at, label).click().run()
    assert not at.exception


def last_search(executor: FakeExecutor) -> dict:
    return [p for n, p in executor.calls if n == "rechercher_metiers"][-1]


def page_shown(at: AppTest) -> str:
    return next(m.value for m in at.markdown if "trouvé" in m.value)


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (25, "25 métiers trouvés · Page 1 sur 2"),
        (11, "11 métiers trouvés · Page 1 sur 1"),
        (1, "1 métier trouvé · Page 1 sur 1"),
    ],
)
def test_exact_result_count(fake, n, expected):
    fake(FakeExecutor({**DATA, "rechercher_metiers": metiers(n)}))
    at = app(q="infirmier").run()
    assert not at.exception
    assert page_shown(at) == f"**{expected}**"
    assert expected in [c.value for c in at.caption]  # also next to the page buttons
    assert "résultats par page" not in text_of(at)


def test_next_and_previous_pages(fake):
    executor = fake(FakeExecutor({**DATA, "rechercher_metiers": metiers(45)}))
    at = app(q="infirmier").run()
    assert "Page 1 sur 3" in page_shown(at) and last_search(executor)["offset"] == 0
    assert button(at, "Précédent").disabled and not button(at, "Suivant").disabled

    click(at, "Suivant")  # 1 -> 2
    assert "45 métiers trouvés · Page 2 sur 3" in page_shown(at)
    assert last_search(executor)["offset"] == 20 and at.query_params["page"] == "2"
    assert not button(at, "Précédent").disabled and not button(at, "Suivant").disabled

    click(at, "Suivant")  # 2 -> 3 (last page)
    assert "Page 3 sur 3" in page_shown(at) and last_search(executor)["offset"] == 40
    assert button(at, "Suivant").disabled and not button(at, "Précédent").disabled

    click(at, "Précédent")  # 3 -> 2
    assert "Page 2 sur 3" in page_shown(at) and last_search(executor)["offset"] == 20

    click(at, "Précédent")  # 2 -> 1
    assert "Page 1 sur 3" in page_shown(at) and last_search(executor)["offset"] == 0
    assert button(at, "Précédent").disabled
    assert "page" not in at.query_params


def test_single_page_disables_both_buttons(fake):
    fake(FakeExecutor({**DATA, "rechercher_metiers": metiers(11)}))
    at = app(q="infirmier").run()
    assert button(at, "Précédent").disabled and button(at, "Suivant").disabled


def test_navigation_preserves_query_and_filters(fake):
    executor = fake()
    filters = {"q": "infirmier", "gd": "J", "dp": "J15", "cadre": "N", "regl": "O", "textes": "1"}
    at = app(**filters).run()
    for label, offset in (("Suivant", 20), ("Précédent", 0)):
        click(at, label)
        params = last_search(executor)
        assert params["offset"] == offset and params["q"] == "infirmier"
        assert (params["code_grand_domaine"], params["code_domaine_professionnel"]) == ("J", "J15")
        assert (params["emploi_cadre"], params["emploi_reglemente"]) == ("N", "O")
        assert params["inclure_textes"] is True
        assert {k: at.query_params[k] for k in filters} == filters


def test_new_query_resets_to_page_one(fake):
    executor = fake()
    at = app(q="infirmier").run()
    button(at, "Suivant").click().run()
    assert last_search(executor)["offset"] == 20
    at.text_input(key="f_q").input("électricien").run()
    assert last_search(executor)["q"] == "électricien" and last_search(executor)["offset"] == 0
    assert "Page 1 sur 2" in page_shown(at) and "page" not in at.query_params


def test_cadre_and_reglemente_labels_and_help(fake):
    fake()
    at = app().run()
    cadre, regl = at.selectbox(key="f_cadre"), at.selectbox(key="f_regl")
    assert cadre.label == "Emploi cadre" and regl.label == "Emploi réglementé"
    assert cadre.options == [
        "Tous les métiers",
        "Métiers avec statut cadre",
        "Métiers sans statut cadre",
    ]
    assert regl.options == [
        "Tous les métiers",
        "Métiers soumis à une réglementation",
        "Métiers non réglementés",
    ]
    assert cadre.help.startswith("Un emploi cadre correspond à un poste impliquant")
    assert "Il ne nécessite pas forcément de manager une équipe." in cadre.help
    assert cadre.help.endswith("dépend notamment de la classification conventionnelle du poste.")
    assert regl.help.startswith("Un métier réglementé est une profession dont l'exercice")
    assert "inscription à un ordre professionnel" in regl.help
    assert regl.help.endswith("nécessiter des qualifications ou des compétences particulières.")
    assert cadre.value == "" and regl.value == ""  # default: all occupations


@pytest.mark.parametrize(
    ("cadre", "regl"), [("O", "N"), ("N", "O"), ("O", "O"), ("N", "N"), ("", "O")]
)
def test_cadre_and_reglemente_values_unchanged(fake, cadre, regl):
    # The new labels are display only: the URL and the contract still use "O" / "N" / None.
    executor = fake()
    at = app(q="infirmier").run()
    at.selectbox(key="f_cadre").set_value(cadre)
    at.selectbox(key="f_regl").set_value(regl).run()
    params = last_search(executor)
    assert params["emploi_cadre"] == (cadre or None)
    assert params["emploi_reglemente"] == (regl or None)
    expected_url = {k: v for k, v in (("cadre", cadre), ("regl", regl)) if v}
    assert {
        k: at.query_params[k] for k in ("cadre", "regl") if k in at.query_params
    } == expected_url


def test_query_edited_then_page_button_clicked_restarts_at_page_one(fake):
    # Typing a new query and clicking Suivant without pressing Enter sends both in one run:
    # the criteria change wins, the click is ignored.
    executor = fake()
    at = app(q="infirmier").run()
    at.text_input(key="f_q").set_value("électricien")
    click(at, "Suivant")
    assert last_search(executor)["q"] == "électricien" and last_search(executor)["offset"] == 0
    assert "Page 1 sur 2" in page_shown(at) and "page" not in at.query_params


def test_filter_change_resets_to_page_one(fake):
    executor = fake()
    at = app(q="infirmier").run()
    button(at, "Suivant").click().run()
    at.selectbox(key="f_cadre").set_value("O").run()
    params = last_search(executor)
    assert params["emploi_cadre"] == "O" and params["offset"] == 0
    assert "Page 1 sur 2" in page_shown(at)


def test_second_query_is_not_lost(fake):
    # Regression: widgets seeded with value=/index= from the URL changed identity after each
    # search, so the next edit went to a stale widget and was silently discarded.
    executor = fake()
    at = app().run()
    for query in ("infirmier", "électricien", "technicien"):
        at.text_input(key="f_q").input(query).run()
        assert last_search(executor)["q"] == query
        assert at.text_input(key="f_q").value == query
    at.selectbox(key="f_gd").set_value("J").run()
    at.selectbox(key="f_gd").set_value("M").run()
    assert last_search(executor)["code_grand_domaine"] == "M"


def test_search_empty_result(fake):
    fake(FakeExecutor({**DATA, "rechercher_metiers": []}))
    at = app(q="zzqxw").run()
    assert not at.exception
    assert "Aucun métier ne correspond" in text_of(at)


def test_search_validation_message(fake):
    executor = fake()
    at = app(q="a").run()
    assert not at.exception
    assert "Paramètre de recherche invalide" in at.warning[0].value
    assert "rechercher_metiers" not in [n for n, _ in executor.calls]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            RuntimeError("HTTP 500 from dbc-secret-host.cloud.databricks.com token=eyJabc.def.ghi"),
            "momentanément indisponible",
        ),
        (AuthenticationError("Databricks login required"), "databricks auth login"),
    ],
)
def test_search_errors_are_user_facing(fake, error, expected):
    fake(FakeExecutor(error=error))
    at = app(q="infirmier").run()
    assert not at.exception
    text = text_of(at)
    assert expected in text
    assert "dbc-secret-host" not in text and "eyJabc" not in text and "Traceback" not in text


def test_configuration_error_is_explained(fake, monkeypatch):
    def missing():
        raise SearchError("configuration")

    monkeypatch.setattr(common, "create_client", missing)
    common.get_client.clear()
    at = app(q="infirmier").run()
    assert not at.exception
    assert "DATABRICKS_SERVER_HOSTNAME" in at.error[0].value


# --- Profile page --------------------------------------------------------------------------


def profile(**query_params) -> AppTest:
    at = app(**query_params)
    at.switch_page(common.PROFILE_PAGE)
    return at.run()


def test_profile_renders_rome_information(fake):
    executor = fake()
    at = profile(code_rome="j1506")
    assert not at.exception
    assert hero_title(at) == FICHE["libelle_rome"]
    text = text_of(at)
    assert "Code ROME J1506" in text and "version 62" in text
    assert "Santé › Soins paramédicaux" in text
    assert "L'infirmier en soins généraux" in text
    assert any("\\*préventifs\\*" in m.value for m in at.markdown)  # escaped: shown literally
    assert "Emploi réglementé : Oui" in text and "Emploi cadre : Non renseigné" in text
    infos = dict(zip([c.value for c in at.caption], [None] * len(at.caption), strict=False))
    assert {"Code RIASEC majeur", "Transition écologique"} <= set(infos)
    assert "**S**" in text and "**Emploi Blanc**" in text and "**Oui**" in text
    assert [(m.label, m.value) for m in at.metric] == [
        ("Appellations", "2"),
        ("Savoir-faire", "2"),
        ("Savoir-être", "1"),
        ("Savoirs", "0"),
        ("Contextes de travail", "0"),
    ]
    assert "Savoir-faire (2)" in text and "Savoir-être professionnels (1)" in text
    # skills and job titles shown as badges; core skill marked; detail tables kept
    assert ":green-badge[:material/star: Réaliser des soins]" in [m.value for m in at.markdown]
    assert any("Infirmier hospitalier" in m.value and "history" in m.value for m in at.markdown)
    assert "Licence Ouverte" in text and "France Travail – ROME 4.0" in text
    names = [n for n, _ in executor.calls]
    assert names.count("fiche_metier") == 1
    assert {"appellations_metier", "competences_metier"} <= set(names)
    assert len(at.dataframe) == 3  # appellations + 2 skill groups


def test_profile_filters(fake):
    executor = fake()
    at = profile(code_rome="J1506")
    for toggle in at.toggle:
        toggle.set_value(not toggle.value)
    at.run()
    assert not at.exception
    calls = {n: p for n, p in executor.calls}
    assert calls["appellations_metier"]["inclure_peu_usitees"] is False
    assert calls["competences_metier"]["coeur_metier_seulement"] is True
    assert "Savoir-faire (1)" in text_of(at)


def test_profile_unknown_code(fake):
    fake()
    at = profile(code_rome="Z9999")
    assert not at.exception
    assert "Code ROME inconnu : Z9999" in at.warning[0].value


def test_profile_without_code(fake):
    executor = fake()
    at = profile()
    assert not at.exception
    assert "Choisissez un métier" in at.info[0].value
    assert executor.calls == []


def test_profile_shows_no_bmo_fap_or_rome_v3(fake):
    fake()
    text = text_of(profile(code_rome="J1506")).lower()
    for word in ("bmo", "fap", "rome v3", "recrutement", "code_rome_parent"):
        assert word not in text


# --- Static guards -------------------------------------------------------------------------

APP_FILES = sorted(APP.rglob("*.py"))


def test_app_files():
    assert [p.relative_to(APP).as_posix() for p in APP_FILES] == [
        "common.py",
        "pages/fiche_metier.py",
        "pages/rechercher_metier.py",
        "streamlit_app.py",
    ]


@pytest.mark.parametrize("path", APP_FILES, ids=lambda p: p.name)
def test_no_sql_no_direct_databricks_access(path):
    text = path.read_text(encoding="utf-8")
    assert not re.search(
        r"career_intelligence\.(bronze|silver|gold)\.\w|career_intelligence\.search\.v_", text
    )
    assert not re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|MERGE|DROP)\s+[\w*]", text)
    assert "databricks.sql" not in text and "import databricks" not in text
    assert "access_token" not in text and "DATABRICKS_TOKEN" not in text
    assert "st.exception" not in text


def test_only_registered_contracts_are_used():
    used = set()
    for path in APP_FILES:
        used |= set(re.findall(r'load\(\s*"\w+",\s*"(\w+)"', path.read_text(encoding="utf-8")))
    assert used == {
        "lister_domaines",
        "rechercher_metiers",
        "fiche_metier",
        "appellations_metier",
        "competences_metier",
    }
    assert used <= set(c.CONTRACTS)
