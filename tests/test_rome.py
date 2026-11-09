"""Tests for the ROME connector (offline: synthetic archive, no network)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from career_intelligence.ingestion import rome

VERSION_TXT = "Numero de version : 62\n\nDate de publication : 19/10/2026\n"

# Minimal but consistent mini-ROME: 2 occupations, 1 title, 2 skills, 1 knowledge, 1 context.
CSV: dict[str, str] = {
    "referentiel_code_rome": "code_rome,code_ogr,libelle_rome\n"
    'A1101,6,"Conducteur / Conductrice d\'engins agricoles"\nA1102,7,Bûcheron\n',
    "referentiel_appellation": "code_ogr,libelle_appellation_long,code_rome\n"
    "11987,Chauffeur,A1101\n",
    "referentiel_competence": "code_ogr,libelle_competence\n"
    "100023,Abattre un arbre\n100024,Être rigoureux\n",
    "referentiel_savoir": "code_ogr_savoir,libelle_savoir\n100003,Engins agricoles\n",
    "referentiel_contexte_travail": "code_ogr,libelle_cont_travail\n126450,Travail posté\n",
    "referentiel_code_rome_riasec": "code_rome,riasec_majeur\nA1101,R\nA1102,R\n",
    "referentiel_macro_competence_riasec": "code_ogr,riasec_majeur\n300230,R\n",
    "item": "code_ogr,libelle,code_rubrique\n100023,Abattre un arbre,1\n100024,Être rigoureux,2\n"
    "100003,Engins agricoles,3\n126450,Travail posté,\n",
    "grand_domaine": "code_grand_domaine,libelle_grand_domaine\nA,Agriculture\n",
    "domaine_professionnel": "code_domaine_professionnel,libelle_domaine_professionnel\n"
    "A11,Engins\n",
    "cr_gd_dp": "code_rome,code_grand_domaine\nA1101,A\nA1102,A\n",
    "composition_bloc": "code_compo_bloc,libelle_bloc\n1,Code ROME\n2,Emplois\n5,Compétences\n",
    "descriptif_rubrique": "code_rubrique,code_compo_bloc,libelle_rubrique\n1,5,Savoir-faire\n",
    # quoted multi-line cell + blank line between records (as in the real file)
    "centre_interet": "code_centre_interet,libelle_centre_interet,definition_centre_interet\n"
    '1,Créer,"Ligne 1.\n\nLigne 2."\n\n2,Aider,"Texte."\n\n',
    "secteur_activite": "code_sect_activite,libelle_sect_activite\n110,Juridique\n",
    "sous_secteur_activite": "code_ss_sect_activite,code_sect_activite\n145,110\n",
    "secteur_naf": "code_tech_secteur_naf,code_secteur_naf,libelle_secteur_naf\n1,0,Transverse\n",
    "themes": "code_theme,libelle_theme\n001,Environnement\n",
    "texte": "code_rome,code_compo_bloc,libelle_type_texte,position_phrase,libelle_texte\n"
    "A1101,3,definition,1,Réalise des travaux.\n",
    "liens_rome_referentiels": "code_rome,code_compo_bloc,code_rubrique,code_ogr\n"
    "A1101,1,,6\nA1101,2,,11987\nA1101,5,1,100023\nA1101,5,2,100024\nA1101,5,3,100003\n"
    "A1101,6,,126450\n",
    "coherence_item": "code_rome,code_ogr,coeur_metier\nA1101,100023,Principale\nA1101,100003,\n",
    "rubrique_mobilite": "code_rome,code_rome_cible,numero_ordre\nA1101,A1102,1\n",
    "arborescence_competences": "code_ogr_macro_competence,code_ogr_competence\n300230,100023\n"
    "300231,100023\n",
    "arborescence_centre_interet": "code_centre_interet,code_rome\n1,A1101\n",
    "arborescence_thematique": "code_theme,code_rome\n001,A1101\n",
    "type_referentiel": "code_type_referentiel,libelle_type_referentiel\n",
}
CP1252_ENTITY = "arborescence_secteur_naf"
CP1252_CSV = "code_secteur_naf,code_rome,libelle_secteur_naf\n1,A1101,Activités agricoles\n"


def make_archive(path: Path, csv: dict[str, str] | None = None) -> Path:
    csv = CSV if csv is None else csv
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("version.txt", VERSION_TXT)
        for entity, text in csv.items():
            zf.writestr(f"unix_{entity}_v462_utf8.csv", text.encode("utf-8"))
        zf.writestr(f"unix_{CP1252_ENTITY}_v462_utf8.csv", CP1252_CSV.encode("cp1252"))
    return path


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    return make_archive(tmp_path / "raw" / "france_travail" / "rome" / "v62" / rome.ARCHIVE_NAME)


def test_archive_version(archive: Path) -> None:
    version, text = rome.archive_version(archive)
    assert version == "62" and "19/10/2026" in text


def test_read_archive_handles_quirks(archive: Path) -> None:
    tables = rome.read_archive(archive)
    assert len(tables) == len(CSV) + 1
    ci = tables["centre_interet"].frame
    assert len(ci) == 2  # blank lines are not records
    assert ci.loc[0, "definition_centre_interet"] == "Ligne 1.\n\nLigne 2."  # multi-line kept
    naf = tables[CP1252_ENTITY]
    assert naf.encoding == "cp1252"
    assert naf.frame.loc[0, "libelle_secteur_naf"] == "Activités agricoles"
    links = tables["liens_rome_referentiels"].frame
    assert links.loc[0, "code_rubrique"] == ""  # empty field kept as published
    assert tables["themes"].frame.loc[0, "code_theme"] == "001"  # leading zeros kept
    assert tables["type_referentiel"].frame.empty


def test_valid_archive_passes(archive: Path) -> None:
    report = rome.validate(rome.read_archive(archive))
    assert report.ok, report.errors
    assert any("multi-line" in w for w in report.warnings)
    assert any("cp1252" in w for w in report.warnings)


def test_duplicate_key_is_an_error(tmp_path: Path) -> None:
    csv = {**CSV, "item": CSV["item"] + "100023,Abattre un arbre,1\n"}
    report = rome.validate(rome.read_archive(make_archive(tmp_path / "a.zip", csv)))
    assert any("item: 1 duplicate" in e for e in report.errors)


def test_orphan_foreign_key_is_an_error(tmp_path: Path) -> None:
    csv = {**CSV, "texte": CSV["texte"] + "Z9999,3,definition,1,Orphelin.\n"}
    report = rome.validate(rome.read_archive(make_archive(tmp_path / "a.zip", csv)))
    assert any("texte.code_rome" in e and "orphan" in e for e in report.errors)


def test_unresolved_polymorphic_link_is_an_error(tmp_path: Path) -> None:
    csv = {**CSV, "liens_rome_referentiels": CSV["liens_rome_referentiels"] + "A1101,5,3,999\n"}
    report = rome.validate(rome.read_archive(make_archive(tmp_path / "a.zip", csv)))
    assert any("block (5, '3')" in e and "unresolved" in e for e in report.errors)


def test_unknown_link_block_is_an_error(tmp_path: Path) -> None:
    csv = {**CSV, "liens_rome_referentiels": CSV["liens_rome_referentiels"] + "A1101,9,,6\n"}
    report = rome.validate(rome.read_archive(make_archive(tmp_path / "a.zip", csv)))
    assert any("unknown block" in e for e in report.errors)


def test_missing_entity_is_an_error(tmp_path: Path) -> None:
    csv = {k: v for k, v in CSV.items() if k != "item"}
    report = rome.validate(rome.read_archive(make_archive(tmp_path / "a.zip", csv)))
    assert not report.ok and "missing entities" in report.errors[0]


def test_run_stages_one_parquet_per_csv(archive: Path, tmp_path: Path) -> None:
    manifest = rome.run(raw_dir=tmp_path / "raw", staging_dir=tmp_path / "staging")

    assert manifest["rome_version"] == "62"
    assert len(manifest["tables"]) == len(CSV) + 1
    out = Path(manifest["staging_dir"])
    links = pd.read_parquet(out / "liens_rome_referentiels.parquet")
    assert len(links) == 6
    assert links["_source_row"].tolist() == [1, 2, 3, 4, 5, 6]
    assert set(links["_rome_version"]) == {"62"}
    assert set(links["_source_file"]) == {"unix_liens_rome_referentiels_v462_utf8.csv"}
    # empty table must keep string types, not Parquet `null`
    schema = pq.read_schema(out / "type_referentiel.parquet")
    assert str(schema.field("code_type_referentiel").type) == "string"
    saved = json.loads((out / "rome_v62.manifest.json").read_text(encoding="utf-8"))
    assert saved["validation"]["ok"]
    assert saved["tables"]["centre_interet"]["rows"] == 2


def test_download_skipped_when_archive_present(archive: Path, tmp_path: Path) -> None:
    assert rome.download(raw_dir=tmp_path / "raw") == archive
