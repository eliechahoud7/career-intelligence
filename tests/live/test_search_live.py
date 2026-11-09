"""Live tests of the search contracts on a Databricks SQL warehouse (Phase 14, decision P9).

Skipped unless explicitly configured:

    CAREER_INTELLIGENCE_LIVE=1
    DATABRICKS_SERVER_HOSTNAME=<workspace host, without https://>
    DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<warehouse id>
    DATABRICKS_TOKEN=<token>   (optional: otherwise `databricks auth token` is called, using
                                DATABRICKS_CONFIG_PROFILE; the token is kept in memory only)

Requires the optional extra: ``pip install -e ".[databricks]"``.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

if os.environ.get("CAREER_INTELLIGENCE_LIVE") != "1":
    pytest.skip("live Databricks tests: set CAREER_INTELLIGENCE_LIVE=1", allow_module_level=True)

dbsql = pytest.importorskip("databricks.sql", reason="install the [databricks] extra")

from career_intelligence.search import contracts as c  # noqa: E402

HOST = os.environ.get("DATABRICKS_SERVER_HOSTNAME")
HTTP_PATH = os.environ.get("DATABRICKS_HTTP_PATH")
if not HOST or not HTTP_PATH:
    pytest.skip(
        "DATABRICKS_SERVER_HOSTNAME / DATABRICKS_HTTP_PATH not set", allow_module_level=True
    )


def _token() -> str:
    token = os.environ.get("DATABRICKS_TOKEN")
    if token:
        return token
    out = subprocess.run(
        ["databricks", "auth", "token"], capture_output=True, text=True, check=True, shell=True
    ).stdout
    return json.loads(out[out.index("{") :])["access_token"]


@pytest.fixture(scope="module")
def conn():
    connection = dbsql.connect(server_hostname=HOST, http_path=HTTP_PATH, access_token=_token())
    yield connection
    connection.close()


def run(conn, name: str, **kwargs) -> tuple[list[str], list[dict]]:
    bound = c.bind(name, **kwargs)
    with conn.cursor() as cur:
        cur.execute(bound.sql, parameters=bound.parameters)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
    return cols, rows


def run_all(conn, name: str, **kwargs) -> list[dict]:
    """Every page of a paginated contract (page_size 100)."""
    rows, page = [], 1
    while True:
        _, batch = run(conn, name, page=page, page_size=100, **kwargs)
        rows += batch
        if not batch or len(rows) >= batch[0]["total_resultats"]:
            return rows
        page += 1


def scalar(conn, sql: str):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()[0]


SAMPLES = {
    "rechercher_metiers": {"q": "électricien"},
    "fiche_metier": {"code_rome": "J1506"},
    "appellations_metier": {"code_rome": "M1805"},
    "lister_domaines": {},
    "rechercher_competences": {"q": "sécurité"},
    "competences_metier": {"code_rome": "M1805"},
    "metiers_par_competence": {"type_element": "savoir_etre", "code_ogr_element": "300489"},
    "domaines_formation_metier": {"code_rome": "M1805"},
    "rechercher_domaines_formation": {"q": "informatique"},
    "metiers_par_domaine_formation": {"code_formacode": "31054"},
    "rechercher_formations_onisep": {"q": "bts"},
    "formations_onisep_metier": {"code_rome": "J1506"},
    "rechercher_fap": {"q": "infirmier"},
    "recrutement_bmo": {"code_fap228": "V1X80", "niveau_geo": "region"},
    "lister_zones_geo": {},
    "rechercher_rome_v3": {"code_rome_v3": "J1506"},
    "licences": {},
}


def test_samples_cover_every_contract():
    assert set(SAMPLES) == set(c.CONTRACTS)


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_columns_licence_and_uniqueness(conn, name):
    contract = c.get_contract(name)
    cols, _ = run(conn, name, **SAMPLES[name])
    assert tuple(cols) == contract.columns
    rows = (
        run_all(conn, name, **SAMPLES[name])
        if contract.paginated
        else run(conn, name, **SAMPLES[name])[1]
    )
    assert rows, name
    keys = [tuple(r[k] for k in contract.key) for r in rows]
    assert len(keys) == len(set(keys)), "duplicate result keys"
    if contract.paginated:
        assert {r["total_resultats"] for r in rows} == {len(rows)}
    if name == "licences":  # lists the licence of every Gold object
        assert len(rows) == scalar(
            conn, "SELECT count(*) FROM career_intelligence.gold.source_licence"
        )
        return
    _, lic = run(conn, "licences", objets=contract.licence_object)
    assert {(r["licence"], r["attribution"]) for r in rows} == {
        (lic[0]["licence"], lic[0]["attribution"])
    }


# --- Keyword matching ----------------------------------------------------------------------


def codes(rows):
    return [r["code_rome"] for r in rows]


def test_case_and_accent_insensitive(conn):
    variants = ["Électricien", "ELECTRICIEN", "electricien", "  électricien  "]
    results = [codes(run_all(conn, "rechercher_metiers", q=v)) for v in variants]
    assert all(r == results[0] for r in results)
    assert {"F1602", "F1629", "I1309"} <= set(results[0])


def test_exact_code_ranks_first(conn):
    _, rows = run(conn, "rechercher_metiers", q="m1805")
    assert rows[0]["code_rome"] == "M1805" and rows[0]["rang_pertinence"] == 1


def test_tiers_are_non_decreasing(conn):
    rows = run_all(conn, "rechercher_metiers", q="infirmier", inclure_textes=True)
    tiers = [r["rang_pertinence"] for r in rows]
    assert tiers == sorted(tiers) and set(tiers) <= {1, 2, 3, 4, 5, 6}


def test_every_word_required(conn):
    assert "F1602" in codes(run_all(conn, "rechercher_metiers", q="elec batiment"))
    # Both words must occur in the same text: "Electricien plombier" matches, nothing else.
    for r in run_all(conn, "rechercher_metiers", q="elec plomb"):
        text = r["libelle_correspondant"].lower()
        assert "elec" in text and "plomb" in text
    assert run_all(conn, "rechercher_metiers", q="elec boulanger") == []
    _, none = run(conn, "rechercher_metiers", q="zzqxw")
    assert none == []


def test_texts_only_on_request(conn):
    without = run_all(conn, "rechercher_metiers", q="diplome d'etat d'infirmier")
    with_texts = run_all(
        conn, "rechercher_metiers", q="diplome d’etat d’infirmier", inclure_textes=True
    )
    assert without == [] and with_texts
    assert {r["champ_correspondant"] for r in with_texts} <= {"definition", "acces_metier"}


def test_ligature_and_curly_apostrophe(conn):
    rows = run_all(conn, "rechercher_competences", q="oeuvre")
    assert any("œuvre" in r["libelle_element"].lower() for r in rows)
    for q in ("systèmes d’information", "SYSTEMES D'INFORMATION"):
        assert "31054" in [
            r["code_formacode"] for r in run_all(conn, "rechercher_domaines_formation", q=q)
        ]


def test_fiche_texts_corrected(conn):
    _, rows = run(conn, "fiche_metier", code_rome="J1506")
    assert len(rows) == 1
    assert rows[0]["definition"].startswith("L'infirmier") and "''" not in rows[0]["definition"]
    assert "''" not in rows[0]["acces_metier"]


# --- Pagination ----------------------------------------------------------------------------


def test_pagination_disjoint_complete_and_stable(conn):
    full = run_all(conn, "rechercher_metiers", q="technicien")
    total = len(full)
    assert total > 20
    pages, page = [], 1
    while len(pages) < total:
        _, batch = run(conn, "rechercher_metiers", q="technicien", page=page, page_size=7)
        assert batch and {r["total_resultats"] for r in batch} == {total}
        pages += batch
        page += 1
    assert codes(pages) == codes(full)
    assert len(set(codes(pages))) == total
    _, beyond = run(conn, "rechercher_metiers", q="technicien", page=page, page_size=7)
    assert beyond == []


# --- Referential integrity and relationship preservation ------------------------------------


def test_competence_and_formacode_links_preserved(conn):
    rows = run_all(
        conn, "metiers_par_competence", type_element="savoir_etre", code_ogr_element="300489"
    )
    gold = scalar(
        conn,
        "SELECT count(*) FROM career_intelligence.gold.v_metier_competence "
        "WHERE type_element = 'savoir_etre' AND code_ogr_element = '300489'",
    )
    assert len(rows) == gold
    links = run_all(conn, "domaines_formation_metier", code_rome="M1805")
    assert len(links) == scalar(
        conn,
        "SELECT count(*) FROM career_intelligence.gold.v_metier_domaine_formation "
        "WHERE code_rome = 'M1805'",
    )


def test_onisep_grain_and_status(conn):
    rows = run_all(conn, "formations_onisep_metier", code_rome="J1506")
    gold = scalar(
        conn,
        "SELECT count(*) FROM career_intelligence.gold.v_metier_formation_onisep "
        "WHERE code_rome = 'J1506'",
    )
    assert len(rows) == gold
    assert {r["statut_code_rome"] for r in rows} == {"valide"}
    assert all("Source : Onisep" in r["attribution"] and r["licence"] == "ODbL" for r in rows)


def test_onisep_unresolved_codes_visible(conn):
    rows = run_all(conn, "rechercher_formations_onisep", q="bts")
    total_unresolved = scalar(
        conn,
        "SELECT count(DISTINCT identifiant_formation) FROM career_intelligence.gold."
        "v_metier_formation_onisep WHERE statut_code_rome = 'non_resolu'",
    )
    assert total_unresolved > 0
    assert all(r["nb_codes_rome_non_resolus"] >= 0 for r in rows)


# --- BMO / ROME separation and minimum semantics -------------------------------------------


def test_bmo_minimums_and_null_semantics(conn):
    rows = run_all(conn, "recrutement_bmo", code_geo="75", niveau_geo="departement")
    assert rows and all(r["nature_valeur"] == "minimum" for r in rows)
    for r in rows:
        hidden_all = r["nb_cellules_secretes_recrutement"] == r["nb_cellules"]
        assert (r["nb_projets_recrutement_minimum"] is None) == hidden_all
        assert r["est_complet_recrutement"] == (r["nb_cellules_secretes_recrutement"] == 0)
    assert any(r["nb_projets_recrutement_minimum"] is None for r in rows)


def test_bmo_minimum_sort_nulls_last(conn):
    rows = run_all(
        conn, "recrutement_bmo", code_geo="75", niveau_geo="departement", tri="minimum_desc"
    )
    values = [r["nb_projets_recrutement_minimum"] for r in rows]
    known = [v for v in values if v is not None]
    assert known == sorted(known, reverse=True)
    assert values == known + [None] * (len(values) - len(known))
    default = run_all(conn, "recrutement_bmo", code_geo="75", niveau_geo="departement")
    assert [r["code_fap228"] for r in default] == sorted(r["code_fap228"] for r in default)


def test_national_totals_match_gold(conn):
    rows = run_all(conn, "recrutement_bmo", code_geo="FR")
    assert len(rows) == 217
    assert sum(r["nb_projets_recrutement_minimum"] or 0 for r in rows) == scalar(
        conn,
        "SELECT sum(nb_projets_recrutement_minimum) FROM career_intelligence.gold.bmo_recrutement "
        "WHERE niveau_geo = 'national'",
    )


def test_rome_v3_kept_separate(conn):
    cols, rows = run(conn, "rechercher_rome_v3", code_rome_v3="J1506")
    assert "code_rome" not in cols
    assert {r["nomenclature"] for r in rows} == {"ROME V3"}
    assert {r["licence_confirmee"] for r in rows} == {False}
    assert len(rows) == 10  # one row per qualification class
    for name in ("recrutement_bmo", "rechercher_fap", "lister_zones_geo"):
        cols, _ = run(conn, name, **SAMPLES[name])
        assert "code_rome" not in cols


def test_search_schema_has_no_rome_bmo_column_mix(conn):
    n = scalar(
        conn,
        "SELECT count(*) FROM (SELECT table_name, collect_set(column_name) AS cols "
        "FROM career_intelligence.information_schema.columns WHERE table_schema = 'search' "
        "GROUP BY table_name) WHERE array_contains(cols, 'code_rome') AND exists(cols, "
        "x -> x LIKE '%fap%' OR x LIKE 'nb\\\\_projets%' OR x = 'code_rome_v3')",
    )
    assert n == 0


def test_dares_licences_flagged(conn):
    _, rows = run(conn, "rechercher_fap", q="infirmier")
    assert {r["licence_confirmee"] for r in rows} == {False}
