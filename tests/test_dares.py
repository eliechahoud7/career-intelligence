"""Tests for the DARES ROME x qualification -> FAP2021 connector (offline, synthetic files)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import openpyxl
import pandas as pd
import pyarrow.parquet as pq
import pytest

from career_intelligence.ingestion import dares

HEADER = "ROME;Intitule_ROME;Qualif;FAP341;Intitule_FAP341"
CSV_NAME, XLSX_NAME = "table_programme.csv", "table_visualisation.xlsx"
# A1101: same family for every class. A1204: family depends on the qualification class.
MAPPING = {
    "A1101": ("Conduite d'engins agricoles", {q: "A0X43" for q in "0123456789"}),
    "A1204": (
        "Protection du patrimoine naturel",
        {**{q: "A0X42b" for q in "123456"}, **{q: "G1X70" for q in "078"}, "9": "H1X91"},
    ),
}
FAP_LABELS = {
    "A0X43": "Conducteurs d'engins",
    "A0X42b": "Sylviculteurs\xa0",  # trailing NBSP
    "G1X70": "Techniciens HSE",
    "H1X91": "Ingénieurs HSE",
}


def rows(mapping=MAPPING):
    return [
        (r, lab, q, f, FAP_LABELS[f])
        for r, (lab, m) in mapping.items()
        for q, f in sorted(m.items())
    ]


def write_csv(path: Path, data) -> None:
    text = HEADER + "\r\n" + "".join(";".join(r) + "\r\n" for r in data)
    path.write_bytes(text.encode("cp1252"))


def write_xlsx(path: Path) -> None:
    wb = openpyxl.Workbook()
    wb.active.title = "Lisez-moi"
    ws = wb.create_sheet("ROME_Qualif_to_FAP341")
    ws.append(["Rome", "Qualification", "Intitulé.Rome", "FAP_2021", "Intitulé.FAP"])
    ws.append(["A1101", None, "Conduite", "A0X43", "Conducteurs"])
    ws.append(["A1204", "Q_123456", "Protection", "A0X42b", "Sylviculteurs"])
    ws.append(["A1204", "Q_078", "Protection", "G1X70", "Techniciens"])
    ws.append(["A1204", "Q_9", "Protection", "H1X91", "Ingénieurs"])
    wb.save(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make(tmp_path: Path, data=None) -> tuple[dict, Path]:
    folder = tmp_path / "raw" / "dares" / "fap2021" / "20261109"
    folder.mkdir(parents=True)
    write_csv(folder / CSV_NAME, rows() if data is None else data)
    write_xlsx(folder / XLSX_NAME)
    resource = {
        "snapshot": "20261109",
        "downloaded_on": "2026-11-09",
        "source_page": "https://dares.example/page",
        "download_method": "manual",
        "license": "UNCONFIRMED",
        "files": {
            "csv": {"name": CSV_NAME, "sha256": sha(folder / CSV_NAME)},
            "xlsx": {"name": XLSX_NAME, "sha256": sha(folder / XLSX_NAME)},
        },
    }
    return resource, folder


# --------------------------------------------------------------------------- checksums
def test_checksums_verified(tmp_path: Path) -> None:
    resource, folder = make(tmp_path)
    assert dares.verify_files(resource, folder)["csv"] == resource["files"]["csv"]["sha256"]


def test_checksum_mismatch_stops(tmp_path: Path) -> None:
    resource, folder = make(tmp_path)
    resource["files"]["csv"]["sha256"] = "0" * 64
    with pytest.raises(dares.DaresValidationError, match="csv checksum mismatch"):
        dares.verify_files(resource, folder)


def test_missing_file_stops(tmp_path: Path) -> None:
    resource, folder = make(tmp_path)
    (folder / XLSX_NAME).unlink()
    with pytest.raises(dares.DaresValidationError, match="missing xlsx"):
        dares.verify_files(resource, folder)


# --------------------------------------------------------------------------- reading
def test_read_keeps_values_exactly(tmp_path: Path) -> None:
    _, folder = make(tmp_path)
    frame, records = dares.read_csv(folder / CSV_NAME)
    assert list(frame.columns) == dares.EXPECTED_COLUMNS and len(frame) == records == 20
    assert set(frame["Qualif"]) == set("0123456789")  # class 0 kept, as text
    assert (frame["Intitule_FAP341"] == "Sylviculteurs\xa0").sum() == 6  # NBSP kept
    assert frame.loc[frame.FAP341 == "H1X91", "Intitule_FAP341"].iat[0] == "Ingénieurs HSE"


def test_bytes_undefined_in_cp1252_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(HEADER.encode() + b"\r\nA1101;x\x81;0;A0X43;y\r\n")
    with pytest.raises(UnicodeDecodeError):
        dares.read_csv(path)


# --------------------------------------------------------------------------- validation
def test_valid_table_passes_with_stats(tmp_path: Path) -> None:
    _, folder = make(tmp_path)
    frame, records = dares.read_csv(folder / CSV_NAME)
    report = dares.validate(frame, records)
    assert report.ok, report.errors
    assert report.stats["rome_qualification_dependent"] == 1  # A1204
    assert report.stats["rome_single_fap"] == 1  # A1101
    assert report.stats["distinct_fap341"] == 4


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d + [d[0]], "fully duplicated"),
        (
            lambda d: (
                d + [("A1101", "Conduite d'engins agricoles", "0", "H1X91", "Ingénieurs HSE")]
            ),
            "duplicated (ROME, Qualif)",
        ),
        (lambda d: d[1:], "without exactly the 10 classes"),
        (lambda d: [("A11", *d[0][1:])] + d[1:], "ROME: 1 values not matching"),
        (lambda d: [(*d[0][:2], "X", *d[0][3:])] + d[1:], "outside 0-9"),
        (lambda d: [(d[0][0], "Autre libellé", *d[0][2:])] + d[1:], "different labels"),
        (lambda d: [(*d[0][:3], "", *d[0][4:])] + d[1:], "empty field"),
    ],
)
def test_structural_errors(tmp_path: Path, mutate, message) -> None:
    _, folder = make(tmp_path, mutate(rows()))
    frame, records = dares.read_csv(folder / CSV_NAME)
    report = dares.validate(frame, records)
    assert any(message in e for e in report.errors), report.errors


# --------------------------------------------------------------------------- XLSX
def test_xlsx_expansion_and_cross_check(tmp_path: Path) -> None:
    _, folder = make(tmp_path)
    mapping = dares.expand_xlsx(folder / XLSX_NAME)
    assert len(mapping) == 20 and mapping[("A1204", "8")] == "G1X70"
    frame, _ = dares.read_csv(folder / CSV_NAME)
    assert dares.cross_check_xlsx(frame, folder / XLSX_NAME) == []
    frame.loc[(frame.ROME == "A1204") & (frame.Qualif == "9"), "FAP341"] = "A0X43"
    assert any("different FAP341" in e for e in dares.cross_check_xlsx(frame, folder / XLSX_NAME))


# --------------------------------------------------------------------------- pipeline
def test_run_stages_parquet_with_lineage(tmp_path: Path) -> None:
    resource, _ = make(tmp_path)
    manifest = dares.run(
        raw_dir=tmp_path / "raw", staging_dir=tmp_path / "staging", resource=resource
    )
    out = tmp_path / "staging" / "dares" / "fap2021" / "20261109"
    df = pd.read_parquet(out / "rome_qualif_fap2021.parquet")
    assert len(df) == 20 and df["_source_row"].tolist() == list(range(1, 21))
    assert set(df["_download_method"]) == {"manual"}
    assert set(df["_source_sha256"]) == {resource["files"]["csv"]["sha256"]}
    assert set(df["_source_encoding"]) == {"cp1252"}
    schema = pq.read_schema(out / "rome_qualif_fap2021.parquet")
    assert {str(schema.field(c).type) for c in dares.EXPECTED_COLUMNS} == {"string"}
    saved = json.loads((out / "rome_qualif_fap2021.manifest.json").read_text(encoding="utf-8"))
    assert saved["license"] == "UNCONFIRMED" and saved["validation"]["xlsx_mapping_identical"]
    assert manifest["key"] == ["ROME", "Qualif"]


def test_run_stops_on_checksum_mismatch(tmp_path: Path) -> None:
    resource, folder = make(tmp_path)
    write_csv(folder / CSV_NAME, rows()[:-1])  # file changed after pinning
    with pytest.raises(dares.DaresValidationError, match="checksum mismatch"):
        dares.run(raw_dir=tmp_path / "raw", staging_dir=tmp_path / "staging", resource=resource)
    assert not (tmp_path / "staging").exists()
