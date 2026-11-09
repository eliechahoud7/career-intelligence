"""Tests for the ONISEP connector (offline: synthetic snapshot, no network)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from career_intelligence.ingestion import onisep

METIERS_XML = """<?xml version="1.0" encoding="UTF-8"?><metiers xmlns:exsl="http://exslt.org/common">
    <metier>
        <identifiant>MET.579</identifiant>
        <nom_metier>gardien/ne de police municipale</nom_metier>
        <romesV3>
            <romeV3>K1707</romeV3>
        </romesV3>
        <competences><![CDATA[<h5>Sens</h5><p>Contact &amp; écoute</p>]]></competences>
        <metiers_associes/>
    </metier>
    <metier>
        <identifiant>MET.69</identifiant>
        <nom_metier>accessoiriste</nom_metier>
        <romesV3/>
        <competences/>
        <metiers_associes/>
    </metier>
</metiers>"""

FORMATIONS_XML = """<?xml version="1.0" encoding="UTF-8"?><formations>
    <formation>
        <identifiant>FOR.10000</identifiant>
        <libelle_complet>TP tailleur de pierre</libelle_complet>
        <metiers_formation>
            <metier>
                <id>MET.579</id>
                <nom_metier>gardien/ne</nom_metier>
            </metier>
        </metiers_formation>
        <poursuites_etudes><poursuite id="7">BP</poursuite></poursuites_etudes>
    </formation>
</formations>"""

CSV_TEXT = (
    "code NSF;libellé formation principal;code RNCP;URL et ID Onisep;domaine/sous-domaine\n"
    "211;conseiller commercial;42066;https://www.onisep.fr/http/redirection/formation/slug/FOR.10000;agro\n"
    "232;tailleur de pierre;;https://www.onisep.fr/http/redirection/formation/slug/FOR.12623;bâtiment\n"
)


def make_snapshot(
    root: Path, *, metiers=METIERS_XML, formations=FORMATIONS_XML, csv_text=CSV_TEXT
) -> Path:
    snap = root / "onisep" / "20261109"
    snap.mkdir(parents=True)
    for name, member, xml in [
        ("fiches_metiers.zip", "Ideo-Fiches metiers.xml", metiers),
        ("fiches_formations.zip", "Ideo-Fiches formations.xml", formations),
    ]:
        with zipfile.ZipFile(snap / name, "w") as zf:
            zf.writestr(member, xml.encode("utf-8"))
    (snap / "formations_initiales.csv").write_bytes(b"\xef\xbb\xbf" + csv_text.encode("utf-8"))
    return snap


@pytest.fixture
def snapshot(tmp_path: Path) -> Path:
    return make_snapshot(tmp_path / "raw")


# --------------------------------------------------------------------------- reading
def test_xml_text_and_fragments(snapshot: Path) -> None:
    s = onisep.read_xml(snapshot / "fiches_metiers.zip", onisep.DATASETS["fiches_metiers"])
    f = s.frame
    assert list(f.columns) == [
        "identifiant",
        "nom_metier",
        "romesV3",
        "competences",
        "metiers_associes",
    ]
    assert s.source_records == 2 and len(f) == 2
    assert s.xml_columns == ["romesV3"]  # only tags that have child elements somewhere
    assert ET.fromstring(f.loc[0, "romesV3"]).findtext("romeV3") == "K1707"
    assert f.loc[1, "romesV3"] == "<romesV3 />"  # empty complex element kept as XML
    assert f.loc[0, "competences"] == "<h5>Sens</h5><p>Contact &amp; écoute</p>"
    assert f.loc[1, "competences"] == ""  # empty text element -> ''


def test_xml_attributes_preserved(snapshot: Path) -> None:
    s = onisep.read_xml(snapshot / "fiches_formations.zip", onisep.DATASETS["fiches_formations"])
    frag = ET.fromstring(s.frame.loc[0, "poursuites_etudes"])
    assert frag.find("poursuite").get("id") == "7"


def test_repeated_top_level_tag_is_rejected(tmp_path: Path) -> None:
    xml = METIERS_XML.replace(
        "<nom_metier>accessoiriste</nom_metier>",
        "<nom_metier>a</nom_metier><nom_metier>b</nom_metier>",
    )
    snap = make_snapshot(tmp_path / "raw", metiers=xml)
    with pytest.raises(ValueError, match="repeated"):
        onisep.read_xml(snap / "fiches_metiers.zip", onisep.DATASETS["fiches_metiers"])


def test_csv_headers_normalised_values_kept(snapshot: Path) -> None:
    s = onisep.read_csv(
        snapshot / "formations_initiales.csv", onisep.DATASETS["formations_initiales"]
    )
    assert list(s.frame.columns) == [
        "code_nsf",
        "libelle_formation_principal",
        "code_rncp",
        "url_et_id_onisep",
        "domaine_sous_domaine",
    ]
    assert s.column_mapping["libellé formation principal"] == "libelle_formation_principal"
    assert s.frame.loc[1, "code_rncp"] == ""  # empty kept as published
    assert s.frame.loc[1, "domaine_sous_domaine"] == "bâtiment"  # BOM stripped, UTF-8 kept
    assert s.source_records == 2


def test_snake_case() -> None:
    assert onisep.snake_case("URL et ID Onisep") == "url_et_id_onisep"
    assert onisep.snake_case("domaine/sous-domaine") == "domaine_sous_domaine"
    assert onisep.snake_case("date création") == "date_creation"


# --------------------------------------------------------------------------- validation
def test_valid_snapshot_passes(snapshot: Path) -> None:
    report = onisep.validate(onisep.read_snapshot(snapshot))
    assert report.ok, report.errors
    assert any("1/1" in w for w in report.warnings)  # fiches_formations ⊂ formations_initiales
    assert any("1 distinct, 0 not found" in w for w in report.warnings)


def test_duplicate_identifier_is_an_error(tmp_path: Path) -> None:
    xml = METIERS_XML.replace("MET.69", "MET.579")
    report = onisep.validate(onisep.read_snapshot(make_snapshot(tmp_path / "raw", metiers=xml)))
    assert any("fiches_metiers: 1 duplicate identifiers" in e for e in report.errors)


def test_malformed_identifier_is_an_error(tmp_path: Path) -> None:
    xml = METIERS_XML.replace("MET.69", "69")
    report = onisep.validate(onisep.read_snapshot(make_snapshot(tmp_path / "raw", metiers=xml)))
    assert any("without a" in e for e in report.errors)


def test_csv_row_without_for_id_is_an_error(tmp_path: Path) -> None:
    csv_text = CSV_TEXT + "999;sans id;;https://www.onisep.fr/autre;x\n"
    report = onisep.validate(
        onisep.read_snapshot(make_snapshot(tmp_path / "raw", csv_text=csv_text))
    )
    assert any("formations_initiales: 1 records without" in e for e in report.errors)


def test_record_count_mismatch_is_an_error(snapshot: Path) -> None:
    staged = onisep.read_snapshot(snapshot)
    staged["fiches_metiers"].source_records = 3
    report = onisep.validate(staged)
    assert any("raw file contains 3" in e for e in report.errors)


# --------------------------------------------------------------------------- pipeline
def test_run_stages_parquet_with_lineage(snapshot: Path, tmp_path: Path) -> None:
    manifest = onisep.run(raw_dir=tmp_path / "raw", staging_dir=tmp_path / "staging")

    assert manifest["snapshot"] == "20261109" and manifest["license"] == "ODbL"
    out = Path(manifest["staging_dir"])
    metiers = pd.read_parquet(out / "fiches_metiers.parquet")
    assert len(metiers) == 2
    assert metiers["_source_row"].tolist() == [1, 2]
    assert set(metiers["_source_name"]) == {"onisep"}
    assert set(metiers["_dataset"]) == {"fiches_metiers"}
    assert set(metiers["_source_file"]) == {"Ideo-Fiches metiers.xml"}
    assert metiers["_source_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    schema = pq.read_schema(out / "formations_initiales.parquet")
    source_types = {str(schema.field(c).type) for c in schema.names if not c.startswith("_")}
    assert source_types == {"string"}
    saved = json.loads((out / "onisep_20261109.manifest.json").read_text(encoding="utf-8"))
    assert saved["validation"]["ok"]
    assert saved["datasets"]["fiches_metiers"]["xml_fragment_columns"] == ["romesV3"]
    assert saved["datasets"]["formations_initiales"]["rows"] == 2


def test_download_skipped_when_snapshot_complete(snapshot: Path, tmp_path: Path) -> None:
    assert onisep.download(raw_dir=tmp_path / "raw") == snapshot


def test_incomplete_snapshot_is_not_reused(snapshot: Path, tmp_path: Path) -> None:
    (snapshot / "formations_initiales.csv").unlink()
    assert onisep.latest_snapshot(tmp_path / "raw") is None
