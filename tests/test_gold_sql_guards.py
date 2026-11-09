"""Offline guards on the Gold SQL (approved decisions D2-D10).

Static checks only: no Databricks connection. They protect the approved
architecture against regressions in sql/gold/*.sql.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

GOLD_DIR = Path(__file__).resolve().parents[1] / "sql" / "gold"
BUILD = GOLD_DIR / "01_gold.sql"
CHECKS = GOLD_DIR / "01_gold_checks.sql"

EXPECTED = {
    "metier": "TABLE",
    "v_metier_appellation": "VIEW",
    "v_metier_competence": "VIEW",
    "v_metier_domaine_formation": "VIEW",
    "v_metier_formation_onisep": "VIEW",
    "v_fap": "VIEW",
    "bmo_recrutement": "TABLE",
    "v_rome_v3_fap": "VIEW",
    "source_licence": "TABLE",
}

CREATE_RE = re.compile(
    r"CREATE OR REPLACE (TABLE|VIEW) career_intelligence\.gold\.(\w+)", re.IGNORECASE
)


def strip_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def statements() -> dict[str, tuple[str, str]]:
    """Map object name -> (kind, statement text without comments)."""
    code = strip_comments(BUILD.read_text(encoding="utf-8"))
    out: dict[str, tuple[str, str]] = {}
    for stmt in re.split(r";\s*\n", code):
        m = CREATE_RE.search(stmt)
        if m:
            out[m.group(2)] = (m.group(1).upper(), stmt)
    return out


STMTS = statements()


def code_only(stmt: str) -> str:
    """Remove string literals (COMMENT texts, property values) so guards inspect SQL code."""
    return re.sub(r"'(?:[^']|'')*'", "''", stmt)


def silver_refs(stmt: str) -> set[str]:
    return set(re.findall(r"career_intelligence\.silver\.(\w+)", stmt))


def test_nine_objects_with_approved_kinds():
    # D4: core profiles and aggregates are tables, relationships are views.
    assert {name: kind for name, (kind, _) in STMTS.items()} == EXPECTED


def test_dedicated_gold_schema():
    # D10
    code = strip_comments(BUILD.read_text(encoding="utf-8"))
    assert "CREATE SCHEMA IF NOT EXISTS career_intelligence.gold" in code
    created = re.findall(r"CREATE OR REPLACE (?:TABLE|VIEW) (\S+)", code)
    assert created and all(n.startswith("career_intelligence.gold.") for n in created)


def test_gold_reads_only_silver():
    code = strip_comments(BUILD.read_text(encoding="utf-8"))
    assert "career_intelligence.bronze." not in code
    assert not re.search(
        r"(INSERT|UPDATE|DELETE|MERGE|ALTER|DROP)\b[^\n]*career_intelligence\.silver", code
    )


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_object_has_gold_layer_and_licence(name):
    stmt = STMTS[name][1]
    assert "'layer' = 'gold'" in stmt
    assert re.search(r"'source\.license' = '[^']+'", stmt)
    assert re.search(r"'source\.attribution' = '", stmt)


def test_licence_properties_match_source_licence_table():
    rows = re.findall(
        r"\('(\w+)', '(?:table|view)', '[^']*', '([^']*)'", STMTS["source_licence"][1]
    )
    from_table = dict(rows)
    assert set(from_table) == set(EXPECTED)
    for name, (_, stmt) in STMTS.items():
        prop = re.search(r"'source\.license' = '([^']+)'", stmt).group(1)
        assert from_table[name] == prop, name


def test_unconfirmed_licences_are_flagged():
    stmt = STMTS["source_licence"][1]
    for name in ("v_fap", "v_rome_v3_fap"):
        row = re.search(rf"\('{name}',[^\n]*", stmt).group(0)
        assert "'UNCONFIRMED" in row and ", false," in row


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_every_object_is_validated(name):
    assert f"career_intelligence.gold.{name}" in CHECKS.read_text(encoding="utf-8")


def test_d2_bmo_never_combined_with_rome_v62():
    rome_v62 = {"rome_metier"} | {"rome_metier_formacode"}
    for name, (_, stmt) in STMTS.items():
        refs = silver_refs(stmt)
        if "bmo_2026" in refs:
            assert not refs & rome_v62, name
            assert not any(r.startswith("rome_") or r.startswith("onisep_") for r in refs), name
            assert not re.search(r"\bcode_rome\b", code_only(stmt)), name


def test_d2_rome_v3_never_joined_to_rome_v62():
    code = strip_comments(BUILD.read_text(encoding="utf-8"))
    assert not re.search(r"code_rome\s*=\s*\w*\.?code_rome_v3", code)
    assert not re.search(r"code_rome_v3\s*=\s*\w*\.?code_rome\b", code)
    stmt = STMTS["v_rome_v3_fap"][1]
    assert not any(r.startswith("rome_") for r in silver_refs(stmt))
    assert not re.search(r"\bcode_rome\b", code_only(stmt))


def test_d2_code_rome_parent_is_attribute_only():
    code = strip_comments(BUILD.read_text(encoding="utf-8"))
    assert not re.search(r"code_rome_parent\s*(=|IN\b)", code, re.IGNORECASE)
    assert not re.search(r"=\s*\w*\.?code_rome_parent", code)
    for name, (_, stmt) in STMTS.items():
        if name != "metier":
            assert "code_rome_parent" not in stmt, name


def test_d3_bmo_measures_are_minimums():
    stmt = STMTS["bmo_recrutement"][1]
    aliases = re.findall(r"\bAS (nb_projets_\w+)", stmt)
    assert sorted(aliases) == [
        "nb_projets_difficiles_minimum",
        "nb_projets_recrutement_minimum",
        "nb_projets_saisonniers_minimum",
    ]
    # NULL (not 0) when every cell of the group is hidden; FR = project-defined national code.
    assert stmt.count("THEN NULL ELSE sum(") == 3
    assert "coalesce" not in stmt.lower()
    assert "'code_geo', 'FR'" in stmt


def test_no_bmo_apportioning_or_weights():
    code = code_only(strip_comments(BUILD.read_text(encoding="utf-8"))).lower()
    assert not re.search(r"\bas \w*(poids|weight|score|rang|rank|ponderation|principal)\w*", code)
    assert " / " not in code  # no division: BMO figures are never apportioned
    assert not re.search(r"\b\w*nsf\w*\b", re.sub(r"\btransform\b", "", code))


def test_d5_onisep_isolated():
    for name, (_, stmt) in STMTS.items():
        refs = silver_refs(stmt)
        if name == "v_metier_formation_onisep":
            assert any(r.startswith("onisep_") for r in refs)
            assert "'source.license' = 'ODbL'" in stmt
            assert "Source : Onisep" in stmt
        else:
            assert not any(r.startswith("onisep_") for r in refs), name


def test_d6_unresolved_links_kept():
    stmt = STMTS["v_metier_formation_onisep"][1]
    assert "code_rome_source" in stmt
    assert "statut_code" in stmt
    # no filter on the resolution status, no INNER join to rome_metier that would drop them
    assert not re.search(r"statut_code\s*=\s*'valide'", stmt)
    assert "rome_metier" not in silver_refs(stmt)
    assert "LEFT JOIN career_intelligence.silver.onisep_formation_initiale" in stmt


def test_d7_onisep_grain_not_collapsed():
    stmt = code_only(STMTS["v_metier_formation_onisep"][1]).upper()
    assert "DISTINCT" not in stmt
    assert "GROUP BY" not in stmt
    assert "UNION ALL" in stmt and not re.search(r"UNION\s+(?!ALL)", stmt)


def test_d8_texts_ordered_by_position():
    stmt = STMTS["metier"][1]
    assert "array_sort(collect_list(struct(position_phrase, libelle_texte)))" in stmt
    assert "concat_ws(' ', d.phrases)" in stmt
    assert "concat_ws('\\n', a.phrases)" in stmt


@pytest.mark.parametrize("path", sorted(GOLD_DIR.glob("*.sql")), ids=lambda p: p.name)
def test_no_semicolon_ending_a_comment_line(path):
    # The statement runner and the SQL editor split on ';' at end of line.
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if "--" in line:
            assert not line.split("--", 1)[1].rstrip().endswith(";"), f"{path.name}:{n}"
