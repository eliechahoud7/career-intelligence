"""Tests for the ROME <-> Formacode V14 connector (offline: synthetic workbooks, fake HTTP)."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import openpyxl
import pandas as pd
import pyarrow.parquet as pq
import pytest

from career_intelligence.ingestion import formacode as fc

CORR_HEADER = [
    "Code ROME 26M10 V62",
    "Libellé fiche ROME 26M10 V62",
    "Code OGR ROME 26M10 V62",
    "Code FORMACODE V14",
    "Libellé FORMACODE V14",
]
CORR_ROWS = [
    ["A1101", "Conducteur d'engins agricoles", 6, "21011", "Machinisme Agricole"],
    ["A1101", "Conducteur d'engins agricoles", 6, "21040", "Polyculture"],
    ["A1102", "Conducteur d'engins forestiers", 403950, "21011", "Machinisme Agricole"],
    ["A1102", "Conducteur d'engins forestiers", 403950, "24154", "Energie"],  # unaccented
]
DESC_HEADER = [
    "Code du Terme",
    "Descripteur en majuscules",
    "Descripteur en typo riche",
    "Champ sémantique",
    "Synonymes",
    "TG (Terme Générique)",
    "NE (Note d’Explication)",
    "Code arborescence",
]
DESC_ROWS = [
    [
        21011,
        "MACHINISME AGRICOLE",
        "Machinisme agricole",
        "210 AGRICULTURE ",
        None,
        "Agriculture - 21054",
        None,
        "F0-1",
    ],
    [
        21040,
        "POLYCULTURE",
        "Polyculture",
        "210 AGRICULTURE ",
        "polyculture élevage",
        "Agriculture - 21054",
        "Note.",
        "F0-2",
    ],
    [24154, "ENERGIE", "Énergie", "241 ENERGIE", None, "Energie électricité - 00110", None, "K0"],
]
DOM_HEADER = [
    "Code du Terme",
    "Descripteur en majuscules",
    "Descripteur en typo riche",
    "TS (Termes Spécifiques)",
    "Note de version",
    "Code arborescence",
]
DOM_ROWS = [["00106", "AGRICULTURE", "Agriculture", "Agriculture - 21054", "null", "F0"]]


def workbook(sheets: dict[str, list[list]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def files(corr_rows=CORR_ROWS, desc_rows=DESC_ROWS) -> dict[str, bytes]:
    readme = [
        ["Version formacode", "V14"],
        ["Version ROME V4", "ROME 4.0 version 62 - 26M10"],
        ["Prochaine actualisation", "23/03/2027"],
    ]
    return {
        fc.CORRESPONDENCE: workbook(
            {"Lisez-moi": readme, "ROME 26M10 - Formacode V14": [CORR_HEADER, *corr_rows]}
        ),
        fc.DESCRIPTEURS: workbook({"Sheet1": [DESC_HEADER, *desc_rows]}),
        fc.GRANDS_DOMAINES: workbook({"ITM Report": [DOM_HEADER, *DOM_ROWS]}),
        fc.ALIGNEMENT_NSF: workbook(
            {"ITM Report": [["Code Formacode", "Terme NSF"], ["21011", "Agriculture - 210"]]}
        ),
    }


def resources(content: dict[str, bytes]) -> dict[str, dict]:
    names = {
        fc.CORRESPONDENCE: "corr.xlsx",
        fc.DESCRIPTEURS: "desc.xlsx",
        fc.GRANDS_DOMAINES: "dom.xlsx",
        fc.ALIGNEMENT_NSF: "nsf.xlsx",
    }
    return {
        rid: {
            "url": f"https://example.test/{names[rid]}",
            "local_file": names[rid],
            "sha256": hashlib.sha256(data).hexdigest(),
            "snapshot": "test_snap",
            "archive_only": rid == fc.ALIGNEMENT_NSF,
        }
        for rid, data in content.items()
    }


def place(tmp_path: Path, content: dict[str, bytes], res: dict[str, dict]) -> Path:
    folder = tmp_path / "raw" / "formacode" / "test_snap"
    folder.mkdir(parents=True)
    for rid, data in content.items():
        (folder / res[rid]["local_file"]).write_bytes(data)
    return folder


# --------------------------------------------------------------------------- cell conversion
@pytest.mark.parametrize(
    ("value", "expected"),
    [("00106", "00106"), (" x ", " x "), (15054, "15054"), (403950.0, "403950"), (None, None)],
)
def test_cell_text_is_faithful(value, expected) -> None:
    assert fc.cell_text(value) == expected


@pytest.mark.parametrize("value", [1.5, True, object()])
def test_cell_text_rejects_ambiguous_values(value) -> None:
    with pytest.raises(ValueError):
        fc.cell_text(value)


# --------------------------------------------------------------------------- reading
def test_read_all_preserves_source(tmp_path: Path) -> None:
    content = files()
    res = resources(content)
    sheets = fc.read_all(res, place(tmp_path, content, res))
    corr = sheets[fc.CORRESPONDENCE]
    assert list(corr.frame.columns) == [
        "code_rome",
        "libelle_fiche_rome",
        "code_ogr_rome",
        "code_formacode",
        "libelle_formacode",
    ]
    assert corr.column_mapping["Code ROME 26M10 V62"] == "code_rome"
    assert corr.frame["code_ogr_rome"].tolist() == ["6", "6", "403950", "403950"]
    assert corr.frame.loc[3, "libelle_formacode"] == "Energie"  # correspondence label kept
    assert corr.metadata["Version ROME V4"] == "ROME 4.0 version 62 - 26M10"
    desc = sheets[fc.DESCRIPTEURS].frame
    assert desc["code_du_terme"].tolist() == ["21011", "21040", "24154"]
    assert desc.loc[0, "champ_semantique"] == "210 AGRICULTURE "  # whitespace untouched
    assert pd.isna(desc.loc[0, "synonymes"])  # empty cell -> NULL
    dom = sheets[fc.GRANDS_DOMAINES].frame
    assert dom.loc[0, "code_du_terme"] == "00106"  # leading zeros kept
    assert dom.loc[0, "note_de_version"] == "null"  # literal kept


def test_unexpected_correspondence_column_is_rejected(tmp_path: Path) -> None:
    content = files()
    content[fc.CORRESPONDENCE] = workbook(
        {
            "Lisez-moi": [["k", "v"]],
            "ROME 26M10 - Formacode V14": [[*CORR_HEADER[:4], "Autre"], CORR_ROWS[0]],
        }
    )
    res = resources(content)
    with pytest.raises(ValueError, match="unexpected correspondence column"):
        fc.read_all(res, place(tmp_path, content, res))


# --------------------------------------------------------------------------- validation
def test_valid_sources_pass_with_stats(tmp_path: Path) -> None:
    content = files()
    res = resources(content)
    errors, stats = fc.validate(fc.read_all(res, place(tmp_path, content, res)))
    assert errors == []
    assert stats["distinct_rome"] == 2 and stats["distinct_formacode"] == 3
    assert stats["rome_with_several_formacodes"] == 2
    assert stats["formacodes_with_several_rome"] == 1  # 21011: many-to-many preserved


@pytest.mark.parametrize(
    ("corr_rows", "message"),
    [
        ([*CORR_ROWS, CORR_ROWS[0]], "fully duplicated"),
        (
            [*CORR_ROWS, [*CORR_ROWS[0][:4], "Autre libellé"]],
            "duplicated (code_rome, code_formacode)",
        ),
        ([*CORR_ROWS, ["A1101", "Autre", 6, "24154", "Energie"]], "distinct libelle_fiche_rome"),
        ([*CORR_ROWS, ["A11", "x", 7, "21011", "y"]], "code_rome: 1 missing/malformed"),
        ([*CORR_ROWS, ["A1103", "x", 8, "99999", "y"]], "not in V14 descriptors"),
        ([*CORR_ROWS, ["A1103", "x", 8, "2101", "y"]], "code_formacode: 1 missing/malformed"),
    ],
)
def test_correspondence_errors(tmp_path: Path, corr_rows, message) -> None:
    content = files(corr_rows=corr_rows)
    res = resources(content)
    errors, _ = fc.validate(fc.read_all(res, place(tmp_path, content, res)))
    assert any(message in e for e in errors), errors


def test_duplicate_descriptor_is_an_error(tmp_path: Path) -> None:
    content = files(desc_rows=[*DESC_ROWS, DESC_ROWS[0]])
    res = resources(content)
    errors, _ = fc.validate(fc.read_all(res, place(tmp_path, content, res)))
    assert any("descripteurs: 1 duplicated codes" in e for e in errors)


# --------------------------------------------------------------------------- checksums / download
class FakeResponse:
    def __init__(self, body: bytes):
        self.body, self.status_code, self.headers = body, 200, {"Content-Type": "application/x"}

    def iter_content(self, chunk_size: int):
        yield self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, by_url: dict[str, bytes]):
        self.by_url, self.calls = by_url, []

    def get(self, url, stream=False, timeout=None):
        self.calls.append(url)
        return FakeResponse(self.by_url[url])


def test_acquire_downloads_missing_files_and_checks_pins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fc, "MIN_SIZE_BYTES", 1)  # synthetic workbooks are ~5 KB
    content = files()
    res = resources(content)
    session = FakeSession({r["url"]: content[rid] for rid, r in res.items()})
    shas = fc.acquire(res, tmp_path / "raw", session=session)
    assert len(session.calls) == 4 and shas == {rid: r["sha256"] for rid, r in res.items()}
    fc.acquire(res, tmp_path / "raw", session=session)  # second run: files reused
    assert len(session.calls) == 4


def test_checksum_mismatch_stops(tmp_path: Path) -> None:
    content = files()
    res = resources(content)
    folder = place(tmp_path, content, res)
    res[fc.DESCRIPTEURS]["sha256"] = "0" * 64
    with pytest.raises(fc.FormacodeValidationError, match="formacode_v14_descripteurs: sha256"):
        fc.acquire(res, folder)


# --------------------------------------------------------------------------- pipeline
def test_run_stages_three_tables_not_nsf(tmp_path: Path) -> None:
    content = files()
    res = resources(content)
    place(tmp_path, content, res)
    manifest = fc.run(raw_dir=tmp_path / "raw", staging_dir=tmp_path / "staging", resources=res)
    out = tmp_path / "staging" / "formacode" / "test_snap"
    assert sorted(p.name for p in out.glob("*.parquet")) == [
        "formacode_v14_descripteurs.parquet",
        "formacode_v14_grands_domaines.parquet",
        "rome_formacode_v14.parquet",
    ]  # NSF alignment: archive only, no table
    corr = pd.read_parquet(out / "rome_formacode_v14.parquet")
    assert corr["_source_row"].tolist() == [2, 3, 4, 5]  # Excel row numbers
    assert set(corr["_source_name"]) == {"france_travail"}
    assert set(corr["_version"]) == {"ROME 4.0 version 62 - 26M10 x Formacode V14"}
    schema = pq.read_schema(out / "formacode_v14_descripteurs.parquet")
    assert {str(schema.field(c).type) for c in schema.names if not c.startswith("_")} == {"string"}
    saved = json.loads((out / "formacode_test_snap.manifest.json").read_text(encoding="utf-8"))
    assert saved["files"][fc.ALIGNEMENT_NSF]["archive_only"] is True
    assert manifest["tables"]["rome_formacode_v14"]["rows"] == 4
