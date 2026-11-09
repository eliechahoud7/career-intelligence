"""Tests for the DARES FAP 2021 nomenclature connector (offline, synthetic CSV)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from career_intelligence.ingestion import fap2021

HEADER = ";".join(fap2021.EXPECTED_HEADER)
ROWS = [
    "A;Agriculture, marine, pêche;A0X;Agriculteurs;A0X41;Eleveurs;A0X41c;Eleveurs de lapins",
    "A;Agriculture, marine, pêche;A0X;Agriculteurs;A0X41;Eleveurs;A0X41d;Eleveurs d'ovins",
    "Q;Banque et assurances;QAX;Employés banque;QAX01;Employés de la banque;QAX01;"
    "Employés de la banque",
]


def write(path: Path, rows=ROWS, header=HEADER) -> bytes:
    data = ("\ufeff" + header + "\r\n" + "".join(r + "\r\n" for r in rows)).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def resource(data: bytes) -> dict:
    return {
        "url": "https://example.test/fap.csv",
        "local_file": "fap.csv",
        "sha256": hashlib.sha256(data).hexdigest(),
        "version": "test",
        "snapshot": "20240430",
        "license": "UNCONFIRMED",
    }


def test_read_keeps_values_and_renames_headers(tmp_path: Path) -> None:
    write(tmp_path / "fap.csv")
    frame, mapping, records = fap2021.read(tmp_path / "fap.csv")
    assert records == 3 and len(frame) == 3
    assert list(frame.columns) == [
        "code_fap_22",
        "libelle_fap_22",
        "code_fap_86",
        "libelle_fap_86",
        "code_fap_228",
        "libelle_fap_228",
        "code_fap_341",
        "libelle_fap_341",
    ]
    assert mapping["Intitulé FAP 341"] == "libelle_fap_341"
    assert frame.loc[2, "code_fap_341"] == "QAX01"  # FAP341 identical to its FAP228
    assert frame.loc[0, "libelle_fap_22"] == "Agriculture, marine, pêche"  # UTF-8, BOM stripped


def test_unexpected_header_is_rejected(tmp_path: Path) -> None:
    write(tmp_path / "fap.csv", header=HEADER.replace("Code FAP 86", "FAP86"))
    with pytest.raises(fap2021.Fap2021ValidationError, match="unexpected header"):
        fap2021.read(tmp_path / "fap.csv")


def test_valid_hierarchy_passes(tmp_path: Path) -> None:
    write(tmp_path / "fap.csv")
    errors, stats = fap2021.validate(*fap2021.read(tmp_path / "fap.csv")[::2])
    assert errors == []
    assert stats == {
        "distinct_code_fap_22": 2,
        "distinct_code_fap_86": 2,
        "distinct_code_fap_228": 2,
        "distinct_code_fap_341": 3,
        "rows": 3,
    }


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([*ROWS, ROWS[0]], "code_fap_341: 1 duplicates"),
        (
            ["A;Agriculture, marine, pêche;A0X;Agriculteurs;A0X41;Eleveurs;a0x41c;x"],
            "code_fap_341: 1 values not matching",
        ),
        (["A;Agriculture, marine, pêche;A0X;Agriculteurs;A0X41;Eleveurs;A0X41c;"], "empty field"),
        (
            [*ROWS, "A;Autre libellé;A0X;Agriculteurs;A0X41;Eleveurs;A0X41e;x"],
            "code_fap_22: up to 2 different labels",
        ),
    ],
)
def test_structural_errors(tmp_path: Path, rows, message) -> None:
    write(tmp_path / "fap.csv", rows=rows)
    frame, _, records = fap2021.read(tmp_path / "fap.csv")
    errors, _ = fap2021.validate(frame, records)
    assert any(message in e for e in errors), errors


def test_code_with_two_official_parents_is_an_error(tmp_path: Path) -> None:
    write(tmp_path / "fap.csv")
    frame, _, _ = fap2021.read(tmp_path / "fap.csv")
    conflict = pd.concat([frame, frame.iloc[[0]].assign(code_fap_228="A0X42")])
    errors, _ = fap2021.validate(conflict, len(conflict))
    assert any("code_fap_341: up to 2 different code_fap_228" in e for e in errors), errors


def test_checksum_mismatch_stops(tmp_path: Path) -> None:
    data = write(tmp_path / "raw" / "f.csv")
    res = resource(data) | {"sha256": "0" * 64, "local_file": "f.csv"}
    with pytest.raises(fap2021.Fap2021ValidationError, match="sha256"):
        fap2021.acquire(res, tmp_path / "raw")


def test_run_stages_parquet_with_lineage(tmp_path: Path) -> None:
    folder = tmp_path / "raw" / "dares" / "fap2021_nomenclature" / "20240430"
    data = write(folder / "fap.csv")
    manifest = fap2021.run(
        raw_dir=tmp_path / "raw", staging_dir=tmp_path / "stg", resource=resource(data)
    )
    out = tmp_path / "stg" / "dares" / "fap2021_nomenclature" / "20240430"
    df = pd.read_parquet(out / "dares_fap2021_nomenclature.parquet")
    assert len(df) == 3 and df["_source_row"].tolist() == [2, 3, 4]
    lineage = [c for c in df.columns if c.startswith("_")]
    assert len(lineage) == 12 and set(df["_source_sha256"]) == {hashlib.sha256(data).hexdigest()}
    schema = pq.read_schema(out / "dares_fap2021_nomenclature.parquet")
    assert {str(schema.field(c).type) for c in df.columns if not c.startswith("_")} == {"string"}
    saved = json.loads((out / "dares_fap2021_nomenclature.manifest.json").read_text("utf-8"))
    assert saved["license"] == "UNCONFIRMED" and manifest["validation"]["stats"]["rows"] == 3
