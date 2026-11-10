"""Offline tests of the « Explorer le marché du travail » page (Phase 15D, BMO 2026).

Same harness as tests/test_app.py: the real entry point under Streamlit's AppTest, with
``create_client`` replaced by a client over a fake executor (no Databricks).
"""

from __future__ import annotations

import math
import re

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
from tests.test_app_formations import page_links  # noqa: E402

PAGE = APP / common.LABOUR_PAGE
BMO = {
    "licence": "Licence Ouverte (fr-lo)",
    "attribution": "France Travail – Enquête Besoins en Main-d'Oeuvre (BMO) 2026",
}
ZONES = {
    "national": [("FR", "France")],
    "region": [("11", "Île-de-France"), ("94", "Corse")],
    "departement": [("75", "Paris"), ("2A", "Corse-du-Sud")],
}
FAMILLES = {
    "S1X20": "Aides de cuisine et employés polyvalents de la restauration",
    "T4X60": "Agents d'entretien de locaux",
    "V0X40": "Infirmiers",
}


def ligne(fap, niveau, code, rec, dif, sai, cellules=10, secrets=(1, 5, 7)):
    """One gold.bmo_recrutement row; a None measure means every cell is secret."""
    s_rec, s_dif, s_sai = (
        cellules if v is None else n for v, n in zip((rec, dif, sai), secrets, strict=True)
    )
    return {
        "code_fap228": fap,
        "libelle_metier_bmo": FAMILLES[fap],
        "niveau_geo": niveau,
        "code_geo": code,
        "libelle_geo": dict(ZONES[niveau])[code],
        "annee": "2026",
        "nb_projets_recrutement_minimum": rec,
        "nb_projets_difficiles_minimum": dif,
        "nb_projets_saisonniers_minimum": sai,
        "nb_cellules": cellules,
        "nb_cellules_secretes_recrutement": s_rec,
        "nb_cellules_secretes_difficiles": s_dif,
        "nb_cellules_secretes_saisonniers": s_sai,
        "est_complet_recrutement": s_rec == 0,
        "est_complet_difficiles": s_dif == 0,
        "est_complet_saisonniers": s_sai == 0,
        "nature_valeur": "minimum",
        "_source_sha256": "735d0443",
        **BMO,
    }


RECRUTEMENT = [
    ligne("S1X20", "national", "FR", 97076, 34508, 38457),
    ligne("T4X60", "national", "FR", 80760, 32507, 16556),
    ligne("V0X40", "national", "FR", 50000, 40000, None, secrets=(0, 0, 0)),
    ligne("S1X20", "region", "11", 20000, 8000, 5000),
    ligne("T4X60", "region", "11", 15000, 6000, 2000),
    ligne("V0X40", "region", "11", 9000, 7000, None),
    ligne("S1X20", "region", "94", 900, None, 400),
    ligne("T4X60", "region", "94", None, None, None),  # every cell secret
    # V0X40 has no row at all for Corse (94) and Corse-du-Sud (2A): « non publié »
    ligne("S1X20", "departement", "75", 12000, 5000, 3000),
    ligne("T4X60", "departement", "75", 9000, 4000, 1000),
    ligne("V0X40", "departement", "75", 6000, 5000, None),
    ligne("S1X20", "departement", "2A", 500, None, 250),
    ligne("T4X60", "departement", "2A", None, None, None),
]


def synthese(niveau):
    rows = []
    for code, nom in ZONES[niveau]:
        zone = [r for r in RECRUTEMENT if r["niveau_geo"] == niveau and r["code_geo"] == code]
        total = {}
        for m in ("recrutement", "difficiles", "saisonniers"):
            vals = [r[f"nb_projets_{m}_minimum"] for r in zone]
            known = [v for v in vals if v is not None]
            total[f"nb_projets_{m}_minimum"] = sum(known) if known else None
            total[f"nb_familles_secretes_{m}"] = len(vals) - len(known)
            total[f"nb_cellules_secretes_{m}"] = sum(r[f"nb_cellules_secretes_{m}"] for r in zone)
            total[f"est_complet_{m}"] = all(r[f"est_complet_{m}"] for r in zone)
        rows.append(
            {
                "niveau_geo": niveau,
                "code_geo": code,
                "libelle_geo": nom,
                "annee": "2026",
                "nb_familles_publiees": len(zone),
                "nb_cellules": sum(r["nb_cellules"] for r in zone),
                "nature_valeur": "minimum",
                "_source_sha256": "735d0443",
                **total,
                **BMO,
            }
        )
    return rows


class BmoExecutor(FakeExecutor):
    """FakeExecutor plus the BMO contracts, filtered and ordered as their SQL does."""

    def __init__(self, error=None, recrutement=None, zones=None):
        self.recrutement = RECRUTEMENT if recrutement is None else recrutement
        self.zones = ZONES if zones is None else zones
        super().__init__(dict(DATA), error)

    def run(self, bound):
        name, p = bound.contract.name, bound.parameters
        if name == "synthese_zones_bmo":
            rows = synthese(p["niveau_geo"]) if self.recrutement else []
        elif name == "lister_zones_geo":
            rows = [
                {"niveau_geo": n, "code_geo": c, "libelle_geo": lib, **BMO}
                for n, zs in self.zones.items()
                for c, lib in zs
                if p["niveau_geo"] in (None, n)
            ]
        elif name == "recrutement_bmo":
            rows = [
                r
                for r in self.recrutement
                if r["niveau_geo"] == (p["niveau_geo"] or "national")
                and p["code_fap228"] in (None, r["code_fap228"])
                and p["code_geo"] in (None, r["code_geo"])
            ]
            rows.sort(key=lambda r: (r["code_geo"], r["code_fap228"]))
            if p["tri"] == "minimum_desc":
                rows.sort(
                    key=lambda r: (
                        r["nb_projets_recrutement_minimum"] is None,
                        -(r["nb_projets_recrutement_minimum"] or 0),
                    )
                )
        else:
            return super().run(bound)
        self.data = {**self.data, name: rows}
        return super().run(bound)


@pytest.fixture
def fake(monkeypatch):
    def install(executor=None):
        executor = executor or BmoExecutor()
        monkeypatch.setattr(common, "create_client", lambda: SearchClient(executor))
        common.get_client.clear()
        common._query.clear()
        return executor

    yield install
    common.get_client.clear()
    common._query.clear()


def marche() -> AppTest:
    at = AppTest.from_file(ENTRY, default_timeout=30)
    at.switch_page(common.LABOUR_PAGE)
    return at.run()


def calls(executor, name):
    return [p for n, p in executor.calls if n == name]


def table_with(at: AppTest, column: str, last: bool = False):
    tables = [d.value for d in at.dataframe if column in d.value.columns]
    return tables[-1] if last else tables[0]


def charts(at: AppTest) -> list:
    return at.get("vega_lite_chart")


# --- Page, framing and attribution ---------------------------------------------------------


def test_page_frames_intentions_minimums_and_year(fake):
    fake()
    at = marche()
    assert not at.exception
    assert hero_title(at) == "Explorer le marché du travail"
    text = text_of(at)
    assert "BMO 2026" in text  # year from the data
    assert "Intentions, pas offres d'emploi" in text and "non des offres d'emploi" in text
    assert "Des minimums" in text and "supérieur ou égal" in text
    assert "« secret statistique »" in text and "« non publié »" in text
    assert "France entière : au moins 227 836 projets de recrutement" in text
    assert [t.label for t in at.tabs] == [
        ":material/map: Territoires",
        ":material/work: Familles de métiers",
        ":material/trending_down: Difficultés de recrutement",
    ]


def test_bmo_attribution_only(fake):
    fake()
    captions = [c.value for c in marche().caption]
    sources = [c for c in captions if c.startswith(":material/verified: Source")]
    assert len(sources) == 1
    assert "France Travail" in sources[0] and "BMO" in sources[0]
    assert "Licence Ouverte" in sources[0]
    assert not any("Dares" in c or "Onisep" in c for c in captions)


def test_no_rome_link_no_rate_no_fap_hierarchy(fake):
    executor = fake()
    at = marche()
    source = PAGE.read_text(encoding="utf-8")
    assert "PROFILE_PAGE" not in source and "code_rome" not in source
    assert "rechercher_fap" not in source and not re.search(r"code_fap(22|86)", source)
    for table in at.dataframe:
        assert not any("taux" in c.lower() or "ratio" in c.lower() for c in table.value.columns)
    names = {n for n, _ in executor.calls}
    assert names <= {"synthese_zones_bmo", "recrutement_bmo", "lister_zones_geo"}


# --- A. Territories ------------------------------------------------------------------------


def test_regions_compared_with_chart_and_exact_table(fake):
    executor = fake()
    at = marche()
    assert {p["niveau_geo"] for p in calls(executor, "synthese_zones_bmo")} == {
        "national",
        "region",
    }
    table = table_with(at, "Zone")
    assert list(table["Zone"]) == ["Île-de-France", "Corse"]
    assert list(table["Projets de recrutement (min.)"]) == [44000, 900]
    assert list(table["Chiffre complet"]) == ["Non (minimum)", "Non (minimum)"]
    assert charts(at)


def test_departements_and_secret_values(fake):
    fake()
    at = marche()
    at.radio(key="bmo_niveau").set_value("departement").run()
    assert not at.exception
    table = table_with(at, "Zone")
    assert list(table["Zone"]) == ["Paris", "Corse-du-Sud"]
    at.selectbox(key="bmo_ind_zones").set_value("difficiles").run()
    table = table_with(at, "Zone")
    corse = table[table["Zone"] == "Corse-du-Sud"].iloc[0]
    assert math.isnan(corse["Dont jugés difficiles (min.)"])  # hidden, never 0
    assert "Projets jugés difficiles : secret statistique" in corse["Remarques"]
    assert "1 sans valeur publiée (secret statistique)" in text_of(at)


def test_zone_detail_ranks_families_and_counts_unpublished(fake):
    executor = fake()
    at = marche()
    at.selectbox(key="bmo_zone").set_value("94").run()
    assert not at.exception
    params = calls(executor, "recrutement_bmo")[-1]
    assert (params["code_geo"], params["niveau_geo"], params["tri"]) == (
        "94",
        "region",
        "minimum_desc",
    )
    table = table_with(at, "Famille de métiers")
    assert list(table["Famille de métiers"]) == [FAMILLES["S1X20"], FAMILLES["T4X60"]]
    assert "Projets de recrutement : secret statistique" in table["Remarques"].iloc[1]
    assert "1 famille(s) de métiers non publiée(s) dans cette zone" in text_of(at)


def test_hidden_share_is_shown(fake):
    fake()
    table = table_with(marche(), "Zone")
    column = "Cellules masquées — projets de recrutement (%)"
    assert list(table[column]) == [10.0, 55.0]  # 3 / 30 and 11 / 20 hidden cells


# --- B. Occupational families --------------------------------------------------------------


def test_family_list_filter_and_national_figures(fake):
    executor = fake()
    at = marche()
    assert {"code_geo": "FR"}.items() <= calls(executor, "recrutement_bmo")[0].items()
    at.text_input(key="bmo_fam_q").input("infirm").run()
    assert "1 famille(s) de métiers sur 3" in text_of(at)
    at.selectbox(key="bmo_fam").set_value("V0X40").run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics == {
        "Projets de recrutement (minimum)": "50 000",
        "Projets jugés difficiles (minimum)": "40 000",
        "Projets saisonniers (minimum)": "secret statistique",
    }


def test_family_compared_by_area_with_unpublished_zones(fake):
    executor = fake()
    at = marche()
    at.selectbox(key="bmo_fam").set_value("V0X40").run()
    params = calls(executor, "recrutement_bmo")[-1]
    assert (params["code_fap228"], params["niveau_geo"]) == ("V0X40", "region")
    assert list(table_with(at, "Zone", last=True)["Zone"]) == ["Île-de-France"]
    assert "Non publié pour 1 zone(s) : Corse" in text_of(at)
    at.radio(key="bmo_fam_niveau").set_value("departement").run()
    assert "Non publié pour 1 zone(s) : Corse-du-Sud" in text_of(at)


def test_family_filter_without_match(fake):
    fake()
    at = marche()
    at.text_input(key="bmo_fam_q").input("zzqxw").run()
    assert any("Aucune famille de métiers ne correspond" in i.value for i in at.info)


# --- C. Recruitment difficulties -----------------------------------------------------------


def test_difficulties_ranked_by_minimum_count_without_rate(fake):
    fake()
    at = marche()
    assert "Aucun taux de difficulté" not in text_of(at)
    table = table_with(at, "Cellules masquées — projets jugés difficiles (%)")
    assert list(table["Famille de métiers"]) == [
        FAMILLES["V0X40"],
        FAMILLES["S1X20"],
        FAMILLES["T4X60"],
    ]
    assert list(table["Dont jugés difficiles (min.)"]) == [40000, 34508, 32507]


def test_difficulties_hidden_values_last(fake):
    fake()
    at = marche()
    at.selectbox(key="bmo_dif_zone").set_value("94").run()
    table = table_with(at, "Cellules masquées — projets jugés difficiles (%)")
    assert table["Dont jugés difficiles (min.)"].isna().all()
    assert any("Aucune valeur publiée pour cet indicateur" in i.value for i in at.info)


# --- Empty data and errors -----------------------------------------------------------------


def test_no_bmo_data(fake):
    fake(BmoExecutor(recrutement=[]))
    at = marche()
    assert not at.exception
    assert "Les données BMO ne sont pas disponibles." in [i.value for i in at.info]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RuntimeError("socket closed by host 10.0.0.1"), "momentanément indisponible"),
        (AuthenticationError("Databricks login required"), "databricks auth login"),
    ],
)
def test_errors_are_user_facing(fake, error, expected):
    fake(BmoExecutor(error=error))
    at = marche()
    assert not at.exception
    text = text_of(at)
    assert expected in text and "10.0.0.1" not in text and "Traceback" not in text


# --- Navigation ----------------------------------------------------------------------------


def test_sidebar_has_the_labour_market_entry(fake):
    fake()
    at = AppTest.from_file(ENTRY, default_timeout=30).run()
    links = page_links(at.sidebar)
    assert [p.proto.label for p in links] == [
        "Rechercher un métier",
        "Explorer les formations",
        "Explorer le marché du travail",
    ]
    assert links[2].proto.page == "marche"
