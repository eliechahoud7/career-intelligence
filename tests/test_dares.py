"""Tests for the DARES ROME x qualification -> FAP2021 connector (offline, synthetic files).

All fixture values are SYNTHETIC: the ROME codes (N99xx), FAP codes (Y9Y.., Z9Z..),
qualification labels and PCS lists are invented test values that only follow the official
formats. They are not excerpts of the DARES publication.
"""

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
# Synthetic codes and labels (official formats only).
# N9901: same family for every class. N9902: family depends on the qualification class.
MAPPING = {
    "N9901": ("Métier synthétique d'essai un", {q: "Y9Y01" for q in "0123456789"}),
    "N9902": (
        "Métier synthétique deux",
        {**{q: "Y9Y02b" for q in "123456"}, **{q: "Z9Z01" for q in "078"}, "9": "Z9Z02"},
    ),
}
FAP_LABELS = {
    "Y9Y01": "Famille synthétique Y9Y01",
    "Y9Y02b": "Famille synthétique Y9Y02b\xa0",  # trailing NBSP
    "Z9Z01": "Famille synthétique Z9Z01",
    "Z9Z02": "Famille synthétique é Z9Z02",
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


# Synthetic qualification classes 0-9 (invented labels and PCS lists).
README_QUALIFS = [
    (0, "Classe synthétique 0", None),
    (1, "Classe synthétique œ 1", None),
    (2, "Classe synthétique 2", "99XX, 98XX"),
    (3, "Classe synthétique 3", "97XX"),
    (4, "Classe synthétique 4", "96XX, 9600"),
    (5, "Classe synthétique 5", "9500"),
    (6, "Classe synthétique 6", "9400"),
    (7, "Classe synthétique 7", "93Z0"),
    (8, "Classe synthétique 8", "9200"),
    (9, "Classe synthétique 9", "9100, 91XX"),
]


def write_xlsx(path: Path, qualifs=README_QUALIFS) -> None:
    wb = openpyxl.Workbook()
    readme = wb.active
    readme.title = "Lisez-moi"
    readme.append(["Table de passage synthétique"])
    readme.append([])
    readme.append(["Nomenclature des qualifications"])
    readme.append(
        ["Code de la qualification", "Intitulé de la qualification", "PCS correspondantes"]
    )
    for code, label, pcs in qualifs:
        readme.append([code, label, pcs])
    readme.append(["source : fichier synthétique de test."])
    ws = wb.create_sheet("ROME_Qualif_to_FAP341")
    ws.append(["Rome", "Qualification", "Intitulé.Rome", "FAP_2021", "Intitulé.FAP"])
    ws.append(["N9901", None, "Métier un", "Y9Y01", "Famille Y9Y01"])
    ws.append(["N9902", "Q_123456", "Métier deux", "Y9Y02b", "Famille Y9Y02b"])
    ws.append(["N9902", "Q_078", "Métier deux", "Z9Z01", "Famille Z9Z01"])
    ws.append(["N9902", "Q_9", "Métier deux", "Z9Z02", "Famille Z9Z02"])
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


# --------------------------------------------------------------------------- readme (Phase 13a)
def test_read_readme_is_faithful(tmp_path: Path) -> None:
    _, folder = make(tmp_path)
    frame = dares.read_readme(folder / XLSX_NAME)
    assert list(frame.columns) == dares.README_COLUMNS and len(frame) == 15
    q = frame[frame["col_a"].fillna("").str.fullmatch(r"\d")]
    assert q["col_a"].tolist() == [str(i) for i in range(10)]  # numeric cells -> exact text
    assert q.iloc[1]["col_b"] == "Classe synthétique œ 1" and pd.isna(q.iloc[1]["col_c"])  # no PCS
    assert q.iloc[2]["col_c"] == "99XX, 98XX"  # PCS list kept as published


def test_run_readme_stages_with_lineage(tmp_path: Path) -> None:
    resource, _ = make(tmp_path)
    manifest = dares.run_readme(
        raw_dir=tmp_path / "raw", staging_dir=tmp_path / "stg", resource=resource
    )
    out = tmp_path / "stg" / "dares" / "fap2021" / "20261109"
    df = pd.read_parquet(out / f"{dares.README_DATASET}.parquet")
    assert manifest["qualification_rows"] == 10 and len(df) == 15
    assert len([c for c in df.columns if c.startswith("_")]) == 12
    assert set(df["_source_sheet"]) == {"Lisez-moi"}
    assert set(df["_source_sha256"]) == {resource["files"]["xlsx"]["sha256"]}
    assert not (out / f"{dares.DATASET}.parquet").exists()  # correspondence staging untouched


def test_run_readme_rejects_incomplete_qualification_table(tmp_path: Path) -> None:
    resource, folder = make(tmp_path)
    write_xlsx(folder / XLSX_NAME, qualifs=README_QUALIFS[:9])  # class 9 missing
    resource["files"]["xlsx"]["sha256"] = sha(folder / XLSX_NAME)
    with pytest.raises(dares.DaresValidationError, match="10 class rows"):
        dares.run_readme(raw_dir=tmp_path / "raw", staging_dir=tmp_path / "stg", resource=resource)


def test_run_readme_stops_on_checksum_mismatch(tmp_path: Path) -> None:
    resource, _ = make(tmp_path)
    resource["files"]["xlsx"]["sha256"] = "0" * 64
    with pytest.raises(dares.DaresValidationError, match="xlsx checksum mismatch"):
        dares.run_readme(raw_dir=tmp_path / "raw", staging_dir=tmp_path / "stg", resource=resource)


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
    assert (frame["Intitule_FAP341"] == "Famille synthétique Y9Y02b\xa0").sum() == 6  # NBSP kept
    assert (
        frame.loc[frame.FAP341 == "Z9Z02", "Intitule_FAP341"].iat[0]
        == "Famille synthétique é Z9Z02"
    )


def test_bytes_undefined_in_cp1252_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(HEADER.encode() + b"\r\nN9901;x\x81;0;Y9Y01;y\r\n")
    with pytest.raises(UnicodeDecodeError):
        dares.read_csv(path)


# --------------------------------------------------------------------------- validation
def test_valid_table_passes_with_stats(tmp_path: Path) -> None:
    _, folder = make(tmp_path)
    frame, records = dares.read_csv(folder / CSV_NAME)
    report = dares.validate(frame, records)
    assert report.ok, report.errors
    assert report.stats["rome_qualification_dependent"] == 1  # N9902
    assert report.stats["rome_single_fap"] == 1  # N9901
    assert report.stats["distinct_fap341"] == 4


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d + [d[0]], "fully duplicated"),
        (
            lambda d: (
                d
                + [
                    (
                        "N9901",
                        "Métier synthétique d'essai un",
                        "0",
                        "Z9Z02",
                        "Famille synthétique é Z9Z02",
                    )
                ]
            ),
            "duplicated (ROME, Qualif)",
        ),
        (lambda d: d[1:], "without exactly the 10 classes"),
        (lambda d: [("N99", *d[0][1:])] + d[1:], "ROME: 1 values not matching"),
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
    assert len(mapping) == 20 and mapping[("N9902", "8")] == "Z9Z01"
    frame, _ = dares.read_csv(folder / CSV_NAME)
    assert dares.cross_check_xlsx(frame, folder / XLSX_NAME) == []
    frame.loc[(frame.ROME == "N9902") & (frame.Qualif == "9"), "FAP341"] = "Y9Y01"
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
