"""Offline tests of the « Explorer les formations » page (Phase 15C).

Same harness as tests/test_app.py: the real entry point under Streamlit's AppTest, with
``create_client`` replaced by a client over a fake executor (no Databricks).
"""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit.testing.v1")

from career_intelligence.search.client import SearchClient  # noqa: E402
from career_intelligence.search.connection import AuthenticationError  # noqa: E402
from tests.test_app import (  # noqa: E402
    APP,
    DATA,
    ENTRY,
    AppTest,
    FakeExecutor,
    common,
    hero_title,
    text_of,
)

FORMACODE = {
    "licence": "Licence Ouverte (fr-lo); Licence Ouverte 2.0 (lov2)",
    "attribution": "France Travail – ROME 4.0; Formacode® V14 – Centre Inffo",
}
ONISEP = {"licence": "ODbL", "attribution": "Source : Onisep; France Travail – ROME 4.0"}

GRANDS = [
    {
        "code_grand_domaine_formacode": f"001{i:02d}",
        "libelle_grand_domaine_formacode": f"Grand domaine {i}",
        "nb_descripteurs": 100 + i,
        "nb_metiers": 200 + i,
        "_version": "v62",
        **FORMACODE,
    }
    for i in range(1, 15)
]
GRANDS[8]["libelle_grand_domaine_formacode"] = "Electronique, informatique, télécommunication"
DESCRIPTEURS = [
    {
        "code_formacode": "31054",
        "libelle_formacode": "Systèmes d'information",
        "libelle_champ_semantique": "Informatique",
        "code_grand_domaine_formacode": "00109",
        "libelle_grand_domaine_formacode": "Electronique, informatique, télécommunication",
        "niveau": 2,
        "est_terme_feuille": False,
        "nb_metiers": 2,
        **FORMACODE,
    },
    {
        "code_formacode": "31025",
        "libelle_formacode": "Informatique de gestion",
        "libelle_champ_semantique": "Informatique",
        "code_grand_domaine_formacode": "00109",
        "libelle_grand_domaine_formacode": "Electronique, informatique, télécommunication",
        "niveau": 3,
        "est_terme_feuille": True,
        "nb_metiers": 1,
        **FORMACODE,
    },
    {
        "code_formacode": "43448",
        "libelle_formacode": "Soins infirmiers",
        "libelle_champ_semantique": "Santé",
        "code_grand_domaine_formacode": "00112",
        "libelle_grand_domaine_formacode": "Santé, social, sécurité",
        "niveau": 3,
        "est_terme_feuille": True,
        "nb_metiers": 1,
        **FORMACODE,
    },
]
# Many-to-many: 31054 -> 2 occupations, M1805 -> 2 descriptors.
LIENS_FORMACODE = [
    {"code_formacode": "31054", "code_rome": "M1805", "libelle_rome": "Études et développement"},
    {"code_formacode": "31054", "code_rome": "M1810", "libelle_rome": "Production informatique"},
    {"code_formacode": "31025", "code_rome": "M1805", "libelle_rome": "Études et développement"},
]
LIENS_FORMACODE = [
    {**r, "libelle_grand_domaine": "Support à l'entreprise", **FORMACODE} for r in LIENS_FORMACODE
]
COUVERTURE = {
    "nb_metiers_avec_formation": 392,
    "nb_metiers_rome": 1923,
    "nb_codes_rome_non_resolus": 6,
    "nb_formations": 2346,
    "nb_metiers_onisep": 849,
    "_snapshot": "2026-11-09",
    "_rome_version": "62",
    **ONISEP,
}
FORMATIONS = [
    {
        "identifiant_formation": "FOR.100",
        "libelle_formation": "BTS services informatiques aux organisations",
        "libelle_type_formation": "brevet de technicien supérieur",
        "libelle_niveau_de_certification": "niveau 5",
        "duree": "2 ans",
        "code_rncp": "35340",
        "url_onisep": "https://www.onisep.fr/http/redirection/formation/slug/FOR.100",
        "formation_dans_catalogue": True,
        "nb_codes_rome": 2,
        **ONISEP,
    },
    {
        "identifiant_formation": "FOR.200",
        "libelle_formation": "Diplôme d'État d'infirmier",
        "libelle_type_formation": "diplôme d'État du paramédical",
        "libelle_niveau_de_certification": "niveau 6",
        "duree": "3 ans",
        "code_rncp": None,
        "url_onisep": None,
        "formation_dans_catalogue": False,
        "nb_codes_rome": 1,
        **ONISEP,
    },
]
LIENS_ONISEP = [
    # FOR.100: M1805 reached through two ONISEP occupations (original grain kept), one more
    # occupation, and one unresolved ONISEP ROME code.
    ("FOR.100", "formation_menant_au_metier", "MET.1", "développeur", "M1805", "M1805"),
    ("FOR.100", "formation_menant_au_metier", "MET.2", "analyste", "M1805", "M1805"),
    ("FOR.100", "formation_menant_au_metier", "MET.3", "technicien réseau", "M1810", "M1810"),
    ("FOR.100", "formation_minimale_requise", "MET.4", "assistant", "K19", None),
    ("FOR.200", "formation_minimale_requise", "MET.5", "infirmier", "J1506", "J1506"),
]
LIBELLES_ROME = {
    "M1805": "Études et développement",
    "M1810": "Production informatique",
    "J1506": "Infirmier / Infirmière en soins généraux (IDE)",
}
LIENS_ONISEP = [
    {
        "identifiant_formation": f,
        "type_lien": t,
        "identifiant_metier_onisep": m,
        "nom_metier_onisep": nom,
        "code_rome_source": src,
        "code_rome": rome,
        "statut_code_rome": "valide" if rome else "non_resolu",
        "libelle_rome": LIBELLES_ROME.get(rome),
        **ONISEP,
    }
    for f, t, m, nom, src, rome in LIENS_ONISEP
]

TRAINING_DATA = {
    "lister_grands_domaines_formation": GRANDS,
    "rechercher_domaines_formation": DESCRIPTEURS,
    "parcourir_domaines_formation": DESCRIPTEURS,
    "metiers_par_domaine_formation": LIENS_FORMACODE,
    "couverture_onisep": [COUVERTURE],
    "rechercher_formations_onisep": FORMATIONS,
    "metiers_par_formation_onisep": LIENS_ONISEP,
}


def _match(q: str, *texts) -> bool:
    return all(any(w in str(t).lower() for t in texts) for w in q.lower().split())


class TrainingExecutor(FakeExecutor):
    """FakeExecutor plus the training contracts, filtered as their SQL does."""

    def __init__(self, error=None, **overrides):
        self.source = {**TRAINING_DATA, **overrides}
        super().__init__({**DATA, **self.source}, error)

    def run(self, bound):
        name, p = bound.contract.name, bound.parameters
        rows = list(self.source.get(name, []))
        if name == "rechercher_domaines_formation":
            q = p["q"]
            rows = [
                r for r in rows if r["code_formacode"] == q or _match(q, r["libelle_formacode"])
            ]
        if name in ("rechercher_domaines_formation", "parcourir_domaines_formation"):
            gd = p["code_grand_domaine_formacode"]
            rows = [r for r in rows if gd is None or r["code_grand_domaine_formacode"] == gd]
        if name == "metiers_par_domaine_formation":
            rows = [r for r in rows if r["code_formacode"] == p["code_formacode"]]
        if name == "rechercher_formations_onisep":
            rows = [r for r in rows if _match(p["q"], r["libelle_formation"], r["code_rncp"])]
        if name == "metiers_par_formation_onisep":
            rows = [r for r in rows if r["identifiant_formation"] == p["identifiant_formation"]]
        if name in self.source:
            self.data = {**self.data, name: rows}
        return super().run(bound)


@pytest.fixture
def fake(monkeypatch):
    def install(executor=None, **overrides):
        executor = executor or TrainingExecutor(**overrides)
        monkeypatch.setattr(common, "create_client", lambda: SearchClient(executor))
        common.get_client.clear()
        common._query.clear()
        return executor

    yield install
    common.get_client.clear()
    common._query.clear()


def formations_page(**query_params) -> AppTest:
    at = AppTest.from_file(ENTRY, default_timeout=30)
    at.query_params.update(query_params)
    at.switch_page(common.TRAINING_PAGE)
    return at.run()


def page_links(node) -> list:
    """Every page link under an AppTest block (``Block.get`` does not search the sidebar)."""
    if type(node).__name__ == "PageLink":
        return [node]
    return [x for child in getattr(node, "children", {}).values() for x in page_links(child)]


def calls(executor, name: str) -> list[dict]:
    return [p for n, p in executor.calls if n == name]


def submit(at: AppTest, field: str, value: str, button: str) -> None:
    """Type without Enter, then click the « Rechercher » button."""
    at.text_input(key=field).set_value(value)
    at.button(key=button).click().run()
    assert not at.exception


# --- Page and navigation -------------------------------------------------------------------


def test_training_page_renders(fake):
    fake()
    at = formations_page()
    assert not at.exception
    assert hero_title(at) == "Explorer les formations"
    assert [t.label for t in at.tabs] == [
        ":material/category: Domaines de formation",
        ":material/school: Formations ONISEP",
    ]
    assert (APP / common.TRAINING_PAGE).exists()


def test_sidebar_navigation_and_search_page_unchanged(fake):
    # The links are rendered by the entry point, before every page. (AppTest drops the sidebar
    # after switch_page, so they are checked on the default page.)
    executor = fake()
    at = AppTest.from_file(ENTRY, default_timeout=30).run()
    assert not at.exception
    links = page_links(at.sidebar)
    assert [p.proto.label for p in links][:2] == ["Rechercher un métier", "Explorer les formations"]
    assert links[1].proto.page == "formations"
    assert at.text_input(key="f_q") and at.button(key="btn-rechercher")  # search unchanged
    assert [n for n, _ in executor.calls] == ["lister_domaines"]  # no training query there


# --- A. Formacode training domains -----------------------------------------------------------


def test_fourteen_grand_domains_and_linked_descriptor_notice(fake):
    executor = fake()
    at = formations_page()
    assert not at.exception
    table = at.dataframe[0].value
    assert len(table) == 14 and list(table.columns) == [
        "Code",
        "Grand domaine",
        "Descripteurs reliés",
        "Métiers associés",
    ]
    assert table["Code"].iloc[0] == "00101"
    notice = at.info[0].value
    total = sum(g["nb_descripteurs"] for g in GRANDS)
    assert f"{total:,}".replace(",", " ") in notice
    assert "reliés à au moins un métier" in notice and "2 775" in notice
    assert len(at.selectbox(key="fc_gd").options) == 15  # "Tous" + 14
    assert calls(executor, "rechercher_domaines_formation") == []


def test_browse_grand_domain_without_keyword(fake):
    executor = fake()
    at = formations_page()
    at.selectbox(key="fc_gd").set_value("00109").run()
    assert not at.exception
    assert (
        calls(executor, "parcourir_domaines_formation")[-1]["code_grand_domaine_formacode"]
        == "00109"
    )
    table = at.dataframe[0].value
    assert list(table["Code"]) == ["31054", "31025"]  # official codes and labels shown
    assert list(table["Descripteur"]) == ["Systèmes d'information", "Informatique de gestion"]
    assert list(table["Type de terme"]) == ["Générique", "Spécifique"]
    assert "2 descripteurs trouvés · Page 1 sur 1" in text_of(at)


def test_keyword_search_with_grand_domain_filter(fake):
    executor = fake()
    at = formations_page()
    at.selectbox(key="fc_gd").set_value("00109")
    submit(at, "fc_q", "informatique", "btn-formacode")
    params = calls(executor, "rechercher_domaines_formation")[-1]
    assert params["q"] == "informatique" and params["code_grand_domaine_formacode"] == "00109"
    assert list(at.dataframe[0].value["Code"]) == ["31025"]
    assert "1 descripteur trouvé" in text_of(at)


def test_keyword_typed_without_button_does_not_search(fake):
    executor = fake()
    at = formations_page()
    at.text_input(key="fc_q").set_value("soins")
    assert calls(executor, "rechercher_domaines_formation") == []
    at.text_input(key="fc_q").run()  # Enter / leaving the field still searches
    assert calls(executor, "rechercher_domaines_formation")[-1]["q"] == "soins"


def test_descriptor_shows_all_linked_occupations(fake):
    executor = fake()
    at = formations_page()
    submit(at, "fc_q", "31054", "btn-formacode")
    at.selectbox(key="fc_sel").set_value("31054").run()
    assert not at.exception
    assert calls(executor, "metiers_par_domaine_formation")[-1]["code_formacode"] == "31054"
    links = {(p.proto.label, p.proto.query_string) for p in page_links(at.main)}
    assert ("Études et développement", "code_rome=M1805") in links
    assert ("Production informatique", "code_rome=M1810") in links
    assert "2 métiers associés" in text_of(at)


def test_occupation_linked_to_several_descriptors(fake):
    # Many-to-many: M1805 is listed under both 31054 and 31025.
    fake()
    at = formations_page()
    at.selectbox(key="fc_gd").set_value("00109").run()
    for code in ("31054", "31025"):
        at.selectbox(key="fc_sel").set_value(code).run()
        labels = [p.proto.label for p in page_links(at.main)]
        assert "Études et développement" in labels


def test_formacode_attribution_and_trademark(fake):
    fake()
    text = text_of(formations_page())
    assert "Formacode® V14 – Centre Inffo" in text and "Licence Ouverte 2.0" in text
    assert "marque déposée du Centre Inffo" in text


def test_formacode_empty_result(fake):
    fake()
    at = formations_page()
    submit(at, "fc_q", "zzqxw", "btn-formacode")
    assert any("Aucun descripteur ne correspond" in i.value for i in at.info)


def test_formacode_descriptor_without_occupation(fake):
    fake(metiers_par_domaine_formation=[])
    at = formations_page()
    submit(at, "fc_q", "31054", "btn-formacode")
    at.selectbox(key="fc_sel").set_value("31054").run()
    assert any("Aucun métier n'est relié à ce descripteur" in i.value for i in at.info)


def test_formacode_validation_message(fake):
    fake()
    at = formations_page()
    submit(at, "fc_q", "a", "btn-formacode")  # below the 2-character minimum
    assert any("Paramètre de recherche invalide" in w.value for w in at.warning)


# --- C. ONISEP training ----------------------------------------------------------------------


def test_onisep_coverage_from_gold(fake):
    executor = fake()
    at = formations_page()
    assert calls(executor, "couverture_onisep") == [{}]
    metric = next(m for m in at.metric if "formation ONISEP" in m.label)
    assert metric.value == "392 / 1 923"
    text = text_of(at)
    assert "environ 20,4 %" in text
    assert "La couverture ONISEP est partielle" not in text and "cite 407" not in text


def test_onisep_attribution_separate_from_formacode(fake):
    fake()
    captions = [c.value for c in formations_page().caption]
    onisep = [c for c in captions if "ODbL" in c and "Source : Onisep" in c]
    formacode = [c for c in captions if "Centre Inffo" in c and "Licence Ouverte" in c]
    assert len(onisep) == 1 and len(formacode) == 1
    assert "Onisep" not in formacode[0] and "Inffo" not in onisep[0]


def test_onisep_attribution_prefix_not_duplicated(fake):
    # Regression: the stored ONISEP attribution starts with "Source : Onisep"; the page used to
    # show « Source : Source : Onisep ».
    fake()
    at = formations_page()
    text = text_of(at)
    assert "Source : Source" not in text
    sources = [c.value for c in at.caption if c.value.startswith(":material/verified: Source")]
    onisep = [c for c in sources if "Onisep" in c]
    assert len(onisep) == 1 and onisep[0].count("Source :") == 1
    assert "Source : Onisep; France Travail – ROME 4.0 — Licence : ODbL" in text


def test_onisep_search_and_table(fake):
    executor = fake()
    at = formations_page()
    submit(at, "on_q", "bts", "btn-onisep")
    assert calls(executor, "rechercher_formations_onisep")[-1]["q"] == "bts"
    table = next(d.value for d in at.dataframe if "Formation" in d.value.columns)
    assert list(table["Formation"]) == ["BTS services informatiques aux organisations"]
    assert table["Niveau"].iloc[0] == "niveau 5" and table["Métiers ROME"].iloc[0] == 2


def test_onisep_training_occupations_keep_grain_and_unresolved_codes(fake):
    executor = fake()
    at = formations_page()
    submit(at, "on_q", "bts", "btn-onisep")
    at.selectbox(key="on_sel").set_value("FOR.100").run()
    assert not at.exception
    assert calls(executor, "metiers_par_formation_onisep")[-1]["identifiant_formation"] == "FOR.100"
    labels = [p.proto.label for p in page_links(at.main)]
    assert labels.count("Études et développement") == 1  # one entry per ROME code...
    text = text_of(at)
    assert "Métier ONISEP : développeur, analyste" in text  # ...listing every ONISEP link
    assert "Formations menant au métier** (2 métier(s) ROME)" in text
    assert "Formation minimale requise** (0 métier(s) ROME)" in text
    assert "K19 — assistant" in text and "non résolus" in text  # never resolved or dropped
    assert "K19" not in labels


def test_onisep_training_outside_catalogue(fake):
    fake()
    at = formations_page()
    submit(at, "on_q", "infirmier", "btn-onisep")
    at.selectbox(key="on_sel").set_value("FOR.200").run()
    text = text_of(at)
    assert "absente du catalogue ONISEP" in text
    assert "Infirmier / Infirmière en soins généraux (IDE)" in [
        p.proto.label for p in page_links(at.main)
    ]


def test_onisep_empty_result(fake):
    fake()
    at = formations_page()
    submit(at, "on_q", "zzqxw", "btn-onisep")
    assert any("Aucune formation ne correspond" in i.value for i in at.info)


# --- Errors ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RuntimeError("socket closed by host 10.0.0.1"), "momentanément indisponible"),
        (AuthenticationError("Databricks login required"), "databricks auth login"),
    ],
)
def test_errors_are_user_facing(fake, error, expected):
    fake(TrainingExecutor(error=error))
    at = formations_page()
    assert not at.exception
    text = text_of(at)
    assert expected in text
    assert "10.0.0.1" not in text and "Traceback" not in text
