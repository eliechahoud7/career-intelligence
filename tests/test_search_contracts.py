"""Offline tests of the search layer (Phase 14): SQL files, contracts registry and guards.

Static checks only: no Databricks connection (live checks: tests/live/test_search_live.py).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from career_intelligence.search import contracts as c

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIR = ROOT / "sql" / "search"
VIEWS = SEARCH_DIR / "01_search.sql"
CHECKS = SEARCH_DIR / "01_search_checks.sql"
GOLD = ROOT / "sql" / "gold" / "01_gold.sql"
QUERY_FILES = sorted(c.QUERIES_DIR.glob("*.sql"))
ALL_SEARCH_SQL = sorted(SEARCH_DIR.rglob("*.sql"))

ROME_V62 = {
    "gold.metier",
    "gold.v_metier_appellation",
    "gold.v_metier_competence",
    "gold.v_metier_domaine_formation",
    "gold.v_metier_formation_onisep",
    "search.v_metier_index",
    "search.v_element_competence",
    "search.v_domaine_formation",
}
BMO_FAP = {"gold.bmo_recrutement", "gold.v_fap", "search.v_zone_geo"}
ROME_V3 = {"gold.v_rome_v3_fap"}
ONISEP = "gold.v_metier_formation_onisep"


def strip_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def code_only(sql: str) -> str:
    """SQL without comments and string literals."""
    return re.sub(r"'(?:[^']|'')*'", "''", strip_comments(sql))


def sql_of(contract: c.Contract) -> str:
    return (c.QUERIES_DIR / contract.file).read_text(encoding="utf-8")


def reads(sql: str) -> set[str]:
    return set(re.findall(r"career_intelligence\.((?:gold|search|silver|bronze)\.\w+)", sql))


def markers(sql: str) -> set[str]:
    return set(re.findall(r"(?<![:\w]):([a-z_]\w*)", code_only(sql)))


def order_by(sql: str) -> str:
    code = code_only(sql)
    tail = code[code.rindex("ORDER BY") + len("ORDER BY") :]
    return tail.split("LIMIT")[0]


def gold_licences() -> dict[str, str]:
    stmt = GOLD.read_text(encoding="utf-8").split("gold.source_licence", 1)[1]
    return dict(re.findall(r"\('(\w+)', '(?:table|view)', '[^']*', '([^']*)'", stmt))


CONTRACTS = list(c.CONTRACTS.values())
IDS = [k.name for k in CONTRACTS]


# --- Registry <-> files --------------------------------------------------------------------


def test_twenty_two_contracts_one_file_each():
    assert len(CONTRACTS) == 22
    assert sorted(k.file for k in CONTRACTS) == [f.name for f in QUERY_FILES]
    assert [f.name[:3] for f in QUERY_FILES] == [f"q{i:02d}" for i in range(1, 23)]


@pytest.mark.parametrize("contract", CONTRACTS, ids=IDS)
def test_single_read_only_statement(contract):
    sql = sql_of(contract)
    code = code_only(sql)
    assert ";" not in code
    assert re.match(r"\s*(WITH|SELECT)\b", code)
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE)\b", code)
    assert sql.startswith(f"-- {contract.file[:3]} {contract.name} ")


@pytest.mark.parametrize("contract", CONTRACTS, ids=IDS)
def test_parameters_match_registry(contract):
    assert markers(sql_of(contract)) == set(contract.param_names)


@pytest.mark.parametrize("contract", CONTRACTS, ids=IDS)
def test_pagination_and_total(contract):
    code = code_only(sql_of(contract))
    paginated = code.rstrip().endswith("LIMIT :page_size OFFSET :offset")
    assert paginated == contract.paginated
    assert ("count(*) OVER () AS total_resultats" in code) == contract.paginated
    assert ("total_resultats" in contract.columns) == contract.paginated


@pytest.mark.parametrize("contract", [k for k in CONTRACTS if k.paginated], ids=lambda k: k.name)
def test_order_is_total_on_the_key(contract):
    # Every key column is an ORDER BY expression, so pages are deterministic and disjoint.
    exprs = {e.strip().split(".")[-1] for e in order_by(sql_of(contract)).split(",")}
    assert set(contract.key) <= exprs, (contract.key, exprs)


@pytest.mark.parametrize("contract", CONTRACTS, ids=IDS)
def test_declared_columns_and_key_are_selected(contract):
    code = code_only(sql_of(contract))
    for col in contract.columns:
        assert re.search(rf"\b{col}\b", code), col
    assert set(contract.key) <= set(contract.columns)
    assert len(set(contract.columns)) == len(contract.columns)


@pytest.mark.parametrize("contract", CONTRACTS, ids=IDS)
def test_reads_match_registry_and_only_gold_or_search(contract):
    found = reads(sql_of(contract))
    assert found == set(contract.reads)
    assert all(r.startswith(("gold.", "search.")) for r in found)


# --- Licence and lineage -------------------------------------------------------------------


@pytest.mark.parametrize("contract", CONTRACTS, ids=IDS)
def test_licence_columns_from_source_licence(contract):
    assert contract.licence_object in c.OBJETS_GOLD
    assert {"licence", "attribution"} <= set(contract.columns)
    if contract.name != "licences":
        assert f"WHERE objet_gold = '{contract.licence_object}'" in sql_of(contract)
        read_gold = {r.split(".")[1] for r in contract.reads if r.startswith("gold.")}
        assert contract.licence_object in read_gold or contract.reads[0].startswith("search.")


@pytest.mark.parametrize("contract", CONTRACTS, ids=IDS)
def test_lineage_column_present(contract):
    lineage = {"_rome_version", "_version", "_source_sha256", "_snapshot"}
    if contract.name not in {"rechercher_fap", "licences"}:  # v_fap and source_licence carry none
        assert lineage & set(contract.columns)


def test_onisep_isolation_and_attribution():
    users = {k.name for k in CONTRACTS if ONISEP in reads(sql_of(k)) | set(k.reads)}
    assert users == {
        "rechercher_formations_onisep",
        "formations_onisep_metier",
        "metiers_par_formation_onisep",
        "couverture_onisep",
    }
    for name in users:
        k = c.get_contract(name)
        assert k.licence_object == "v_metier_formation_onisep"
    assert gold_licences()["v_metier_formation_onisep"] == "ODbL"
    gold_sql = GOLD.read_text(encoding="utf-8")
    assert "'ODbL', 'Source : Onisep" in gold_sql


def test_dares_contracts_expose_unconfirmed_licence():
    for name in ("rechercher_fap", "rechercher_rome_v3"):
        assert "licence_confirmee" in c.get_contract(name).columns


def test_view_licences_equal_gold_source_licence():
    licences = gold_licences()
    stmts = [
        s
        for s in re.split(r";\s*\n", strip_comments(VIEWS.read_text(encoding="utf-8")))
        if "VIEW" in s
    ]
    assert len(stmts) == 4
    for stmt in stmts:
        target = re.search(r"CREATE OR REPLACE VIEW career_intelligence\.(search\.\w+)", stmt)
        assert target
        assert "'layer' = 'search'" in stmt and "'source.attribution' = '" in stmt
        lic = re.search(r"'source\.license' = '([^']+)'", stmt).group(1)
        objs = re.search(r"'source\.gold_objects' = '([^']+)'", stmt).group(1).split(", ")
        assert {licences[o] for o in objs} == {lic}
        sources = reads(stmt) - {target.group(1)}
        assert {r.split(".")[1] for r in sources} == set(objs)
        assert all(r.startswith("gold.") for r in sources)


# --- Separation (D2) -----------------------------------------------------------------------


@pytest.mark.parametrize("contract", CONTRACTS, ids=IDS)
def test_rome_v62_bmo_fap_v3_never_combined(contract):
    r = (reads(sql_of(contract)) | set(contract.reads)) - {"gold.source_licence"}
    groups = [bool(r & ROME_V62), bool(r & BMO_FAP), bool(r & ROME_V3)]
    assert sum(groups) <= 1, r
    if r & (BMO_FAP | ROME_V3):
        assert "code_rome" not in contract.columns
        assert not re.search(r"\bcode_rome\b", code_only(sql_of(contract)))


def test_no_code_rome_parent_and_no_v3_v62_comparison():
    # Executable SQL only: comments and the checks file's guard literal may name the column.
    for path in ALL_SEARCH_SQL:
        code = code_only(path.read_text(encoding="utf-8"))
        assert not re.search(r"\bcode_rome_parent\b", code), path.name
        assert not re.search(r"code_rome_v3\s*=\s*\w*\.?code_rome\b", code), path.name
        assert not re.search(r"\bcode_rome\s*=\s*\w*\.?code_rome_v3", code), path.name


def test_bmo_minimum_semantics():
    k = c.get_contract("recrutement_bmo")
    measures = [col for col in k.columns if col.startswith("nb_projets_")]
    assert measures and all(col.endswith("_minimum") for col in measures)
    assert {"nature_valeur", "nb_cellules"} <= set(k.columns)
    assert all(
        f"est_complet_{m}" in k.columns for m in ("recrutement", "difficiles", "saisonniers")
    )
    code = code_only(sql_of(k))
    assert "'minimum' AS nature_valeur" in sql_of(k)
    assert "coalesce(b.nb_projets" not in code and "coalesce(nb_projets" not in code
    assert not re.search(r"nb_projets_\w+\s*[-+*/]|[-+*/]\s*\w*\.?nb_projets_", code)
    assert "DESC NULLS LAST" in code
    assert dict((p.name, p) for p in k.params)["tri"].default == "geo"


def test_ranking_uses_match_tiers_not_weights():
    for k in CONTRACTS:
        if not k.paginated:  # fiche_metier: a single row, no ORDER BY
            assert "ORDER BY" not in code_only(sql_of(k))
            continue
        order = order_by(sql_of(k))
        if k.name == "recrutement_bmo":
            order = order.replace("nb_projets_recrutement_minimum", "")
        assert "nb_" not in order, k.name
        assert not re.search(r"(poids|weight|score|ponderation)", code_only(sql_of(k)), re.I)
    keyword = [k for k in CONTRACTS if any(p.keyword for p in k.params)]
    assert {k.name for k in keyword} == {
        "rechercher_metiers",
        "rechercher_competences",
        "rechercher_domaines_formation",
        "rechercher_formations_onisep",
        "rechercher_fap",
        "rechercher_rome_v3",
    }
    for k in keyword:
        sql = sql_of(k)
        assert "rang_pertinence" in k.columns
        assert "COLLATE UNICODE_CI_AI" in sql
        assert "replace(:q, '\\u2019', chr(39))" in sql
        assert re.search(r"ORDER BY \w*\.?rang_pertinence", sql)


def test_fiche_texts_come_from_corrected_index():
    sql = sql_of(c.get_contract("fiche_metier"))
    assert "d.texte AS definition" in sql and "a.texte AS acces_metier" in sql
    assert not re.search(r"\bm\.(definition|acces_metier)\b", sql)


def test_search_views_correct_apostrophes_only_in_rome_texts():
    sql = VIEWS.read_text(encoding="utf-8")
    assert sql.count("replace(definition, repeat(chr(39), 2), chr(39))") == 2
    assert sql.count("replace(acces_metier, repeat(chr(39), 2), chr(39))") == 2
    assert code_only(sql).count("replace(") == 4


# --- SQL hygiene ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ALL_SEARCH_SQL, ids=lambda p: p.name)
def test_no_semicolon_ending_a_comment_line(path):
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if "--" in line:
            assert not line.split("--", 1)[1].rstrip().endswith(";"), f"{path.name}:{n}"


@pytest.mark.parametrize("path", sorted((ROOT / "sql").rglob("*.sql")), ids=lambda p: p.name)
def test_chr_only_below_256(path):
    # Spark's chr(n) returns chr(n % 256): chr(8217) is NOT a curly apostrophe.
    for n in re.findall(r"\bchr\((\d+)\)", path.read_text(encoding="utf-8")):
        assert int(n) < 256, path.name


def test_views_file_and_checks_cover_the_four_views():
    views = re.findall(
        r"VIEW career_intelligence\.search\.(\w+)", VIEWS.read_text(encoding="utf-8")
    )
    assert views == ["v_metier_index", "v_element_competence", "v_domaine_formation", "v_zone_geo"]
    checks = CHECKS.read_text(encoding="utf-8")
    assert all(f"career_intelligence.search.{v}" in checks for v in views)


# --- bind() --------------------------------------------------------------------------------


def test_bind_normalises_and_paginates():
    b = c.bind("rechercher_metiers", q="  Électricien ’  bâtiment ", page=3, page_size=10)
    assert b.parameters["q"] == "Électricien ' bâtiment"
    assert b.parameters["page_size"] == 10 and b.parameters["offset"] == 20
    assert b.parameters["inclure_textes"] is False
    assert set(b.parameters) == set(b.contract.param_names)
    assert b.sql == sql_of(b.contract)


def test_bind_statement_parameters_typed_and_null():
    b = c.bind("recrutement_bmo", code_fap228="V1X80")
    params = {p["name"]: p for p in b.statement_parameters()}
    assert params["code_fap228"] == {"name": "code_fap228", "type": "STRING", "value": "V1X80"}
    assert params["code_geo"] == {"name": "code_geo", "type": "STRING"}  # NULL
    assert params["niveau_geo"]["value"] == "national" and params["tri"]["value"] == "geo"
    assert params["offset"] == {"name": "offset", "type": "INT", "value": "0"}
    b2 = c.bind("rechercher_metiers", q="infirmier", inclure_textes=True)
    assert {p["name"]: p for p in b2.statement_parameters()}["inclure_textes"]["value"] == "true"


def test_bind_multi_value_parameters():
    b = c.bind("rechercher_competences", q="soudure", types=["savoir_faire", "savoir", "savoir"])
    assert b.parameters["types"] == "savoir_faire,savoir"
    assert c.bind("licences", objets="v_fap, metier").parameters["objets"] == "v_fap,metier"
    assert c.bind("rechercher_competences", q="soudure", types=[]).parameters["types"] is None


@pytest.mark.parametrize(
    ("name", "kwargs", "message"),
    [
        ("rechercher_metiers", {}, "required"),
        ("rechercher_metiers", {"q": "a"}, "length"),
        ("rechercher_metiers", {"q": "x" * 101}, "length"),
        ("rechercher_metiers", {"q": "   "}, "required"),
        ("rechercher_metiers", {"q": "infirmier", "emploi_cadre": "oui"}, "not in"),
        ("rechercher_metiers", {"q": "infirmier", "inclure_textes": "yes"}, "boolean"),
        ("rechercher_metiers", {"q": "infirmier", "code_rome_v3": "J1506"}, "unknown"),
        ("rechercher_competences", {"q": "soudure", "types": ["skills"]}, "unknown value"),
        ("recrutement_bmo", {}, "at least one"),
        ("recrutement_bmo", {"code_fap228": "V1X80", "tri": "random"}, "not in"),
        ("rechercher_rome_v3", {}, "at least one"),
        ("rechercher_rome_v3", {"code_rome": "J1506"}, "unknown"),
        ("fiche_metier", {"code_rome": 1506}, "string"),
        ("unknown_contract", {}, "Unknown search contract"),
    ],
)
def test_bind_rejects_invalid_values(name, kwargs, message):
    with pytest.raises(ValueError, match=message):
        c.bind(name, **kwargs)


@pytest.mark.parametrize(
    ("page", "page_size"), [(0, 20), (-1, 20), (1, 0), (1, 101), (1.5, 20), (True, 20)]
)
def test_bind_rejects_invalid_pages(page, page_size):
    with pytest.raises(ValueError, match="page"):
        c.bind("rechercher_metiers", q="infirmier", page=page, page_size=page_size)


def test_fiche_metier_is_not_paginated():
    b = c.bind("fiche_metier", code_rome="J1506")
    assert set(b.parameters) == {"code_rome"}


# --- Phase 15C: training exploration contracts ----------------------------------------------

TRAINING = {
    "lister_grands_domaines_formation": "v_metier_domaine_formation",
    "parcourir_domaines_formation": "v_metier_domaine_formation",
    "metiers_par_formation_onisep": "v_metier_formation_onisep",
    "couverture_onisep": "v_metier_formation_onisep",
}


@pytest.mark.parametrize(("name", "licence_object"), TRAINING.items())
def test_training_contracts_licence_and_separation(name, licence_object):
    k = c.get_contract(name)
    assert k.licence_object == licence_object
    r = reads(sql_of(k))
    if licence_object == "v_metier_domaine_formation":  # Formacode never mixed with ONISEP
        assert ONISEP not in r
    else:
        assert not r & {"gold.v_metier_domaine_formation", "search.v_domaine_formation"}
    assert not r & (BMO_FAP | ROME_V3)


def test_grands_domaines_are_counts_over_linked_descriptors():
    k = c.get_contract("lister_grands_domaines_formation")
    code = code_only(sql_of(k))
    assert "count(DISTINCT d.code_formacode)" in code and "count(DISTINCT d.code_rome)" in code
    assert k.param_names == ("page_size", "offset")
    assert c.bind(k.name).parameters == {"page_size": 20, "offset": 0}


def test_parcourir_requires_grand_domain_and_keeps_links_unweighted():
    b = c.bind("parcourir_domaines_formation", code_grand_domaine_formacode=" 00109 ")
    assert b.parameters["code_grand_domaine_formacode"] == "00109"
    assert "rang_pertinence" not in b.contract.columns  # browsing, not keyword ranking
    with pytest.raises(ValueError, match="required"):
        c.bind("parcourir_domaines_formation")


def test_metiers_par_formation_keeps_onisep_grain_and_unresolved_codes():
    k = c.get_contract("metiers_par_formation_onisep")
    sql = sql_of(k)
    code = code_only(sql)
    assert "LEFT JOIN career_intelligence.gold.metier m ON m.code_rome = o.code_rome" in sql
    assert "DISTINCT" not in code and "GROUP BY" not in code  # decision D7
    assert {"statut_code_rome", "code_rome_source", "nom_metier_onisep"} <= set(k.columns)
    assert k.key == c.get_contract("formations_onisep_metier").key
    b = c.bind(k.name, identifiant_formation="FOR.1234", type_lien="formation_minimale_requise")
    assert b.parameters["type_lien"] == "formation_minimale_requise"


def test_couverture_onisep_counts_resolved_codes_only():
    k = c.get_contract("couverture_onisep")
    code = code_only(sql_of(k))
    assert not k.paginated and k.param_names == ()
    assert "count(DISTINCT code_rome) AS INT) AS nb_metiers_avec_formation" in code
    assert "CASE WHEN statut_code_rome = '' THEN code_rome_source END" in code  # literal blanked
    assert "FROM career_intelligence.gold.metier" in code
    assert c.bind(k.name).parameters == {}


@pytest.mark.parametrize(
    ("name", "kwargs", "message"),
    [
        ("lister_grands_domaines_formation", {"code_grand_domaine_formacode": "00101"}, "unknown"),
        ("parcourir_domaines_formation", {"code_grand_domaine_formacode": "   "}, "required"),
        ("parcourir_domaines_formation", {"code_grand_domaine_formacode": 101}, "string"),
        ("parcourir_domaines_formation", {"q": "info"}, "unknown"),
        ("metiers_par_formation_onisep", {}, "required"),
        (
            "metiers_par_formation_onisep",
            {"identifiant_formation": "F", "type_lien": "x"},
            "not in",
        ),
        ("metiers_par_formation_onisep", {"code_rome": "J1506"}, "unknown"),
        ("couverture_onisep", {"code_rome": "J1506"}, "unknown"),
    ],
)
def test_training_contracts_reject_invalid_values(name, kwargs, message):
    with pytest.raises(ValueError, match=message):
        c.bind(name, **kwargs)


# --- Phase 15D: labour market (BMO) ----------------------------------------------------------


def test_synthese_zones_bmo_keeps_minimum_semantics():
    k = c.get_contract("synthese_zones_bmo")
    sql = sql_of(k)
    code = code_only(sql)
    assert k.reads == ("gold.bmo_recrutement", "gold.source_licence")
    assert k.licence_object == "bmo_recrutement"
    measures = [col for col in k.columns if col.startswith("nb_projets_")]
    assert measures == [
        "nb_projets_recrutement_minimum",
        "nb_projets_difficiles_minimum",
        "nb_projets_saisonniers_minimum",
    ]
    for m in measures:  # sum of minimums: NULL stays NULL, never coalesced to 0
        assert f"sum(b.{m}) AS {m}" in code
    assert "coalesce" not in code.lower()
    assert not re.search(r"nb_projets_\w+\s*[-+*/]|[-+*/]\s*\w*\.?nb_projets_", code)
    assert "'minimum' AS nature_valeur" in sql
    for i in ("recrutement", "difficiles", "saisonniers"):
        assert f"est_complet_{i}" in k.columns and f"nb_familles_secretes_{i}" in k.columns
        assert f"bool_and(b.est_complet_{i})" in code
    assert not re.search(r"\b(code_rome|code_fap22|code_fap86|taux|ratio)\b", code)


def test_synthese_zones_bmo_parameters():
    b = c.bind("synthese_zones_bmo", niveau_geo="region")
    assert b.parameters == {"niveau_geo": "region", "page_size": 20, "offset": 0}
    with pytest.raises(ValueError, match="required"):
        c.bind("synthese_zones_bmo")
    with pytest.raises(ValueError, match="not in"):
        c.bind("synthese_zones_bmo", niveau_geo="bassin")
    with pytest.raises(ValueError, match="unknown"):
        c.bind("synthese_zones_bmo", niveau_geo="region", code_fap228="S1X20")
