"""Tests for the BMO connector (offline: synthetic workbooks + fake HTTP session)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from career_intelligence.ingestion import bmo
from career_intelligence.ingestion.http import ZIP_MAGIC, DownloadError, download_file

HEADER = [
    "annee",
    "Code métier BMO",
    "Nom métier BMO",
    "Famille_met",
    "Lbl_fam_met",
    "REG",
    "NOM_REG",
    "Dept",
    "NomDept",
    "BE26",
    "NOMBE26",
    "clpe",
    "met",
    "xmet",
    "smet",
]
ROWS = [
    [
        "2026",
        "A0X40",
        "Agriculteurs",
        "Z",
        "Autres métiers",
        "01",
        "Guadeloupe",
        "971",
        "Guadeloupe",
        "101",
        "BASSIN BASSE-TERRE",
        "CLPE97101",
        "69",
        "30",
        "23",
    ],
    [
        "2026",
        "QAX01",
        "Ingénieurs ",
        "C",
        "Fonctions d'encadrement",
        "94",
        "Corse",
        "2A",
        "Corse-du-Sud",
        "9408",
        "PORTO VECCHIO",
        "CLPE2A002",
        "10",
        "*",
        "*",
    ],
    [
        "2026",
        "W1X80",
        "Formateurs",
        "S",
        "Fonctions sociales",
        "93",
        "PACA",
        "06",
        "Alpes-Maritimes",
        "9399",
        "MONACO",
        None,
        "*",
        "*",
        "*",
    ],
]


def make_workbook(path: Path, header=HEADER, rows=ROWS, sheet="BMO_2026_open_data") -> Path:
    wb = openpyxl.Workbook()
    wb.active.title = "Description_des_variables"
    wb.active.append(["Variables", "Description"])
    ws = wb.create_sheet(sheet)
    ws.append(header)
    for row in rows:
        ws.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def load(tmp_path: Path, **kwargs) -> pd.DataFrame:
    return bmo.standardize_columns(bmo.read_raw(make_workbook(tmp_path / "b.xlsx", **kwargs)))


# --------------------------------------------------------------------------- reading
def test_find_data_sheet(tmp_path: Path) -> None:
    assert bmo.find_data_sheet(make_workbook(tmp_path / "b.xlsx")) == ("BMO_2026_open_data", 2026)


def test_missing_data_sheet_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No sheet"):
        bmo.find_data_sheet(make_workbook(tmp_path / "b.xlsx", sheet="Feuil1"))


def test_values_are_read_as_text(tmp_path: Path) -> None:
    df = load(tmp_path)
    assert df["code_region"].tolist() == ["01", "94", "93"]  # leading zero kept
    assert df["code_departement"].tolist() == ["971", "2A", "06"]
    assert df["nb_projets_recrutement"].tolist() == ["69", "10", "*"]
    assert pd.isna(df.loc[2, "code_clpe"])  # empty cell -> null


@pytest.mark.parametrize("suffix", ["25", "26", "27"])
def test_year_suffixed_columns_are_mapped(tmp_path: Path, suffix: str) -> None:
    header = [h.replace("26", suffix) for h in HEADER]
    df = load(tmp_path, header=header)
    assert {"code_bassin_emploi", "libelle_bassin_emploi"} <= set(df.columns)


# --------------------------------------------------------------------------- validation
def test_valid_dataset_passes_with_warnings(tmp_path: Path) -> None:
    report = bmo.validate(load(tmp_path), 2026)
    assert report.ok, report.errors
    assert report.row_count == 3
    assert any("code_clpe: 1 null" in w for w in report.warnings)
    assert any("whitespace" in w for w in report.warnings)  # "Ingénieurs "
    assert any("statistical secrecy" in w for w in report.warnings)


def test_wrong_year_is_an_error(tmp_path: Path) -> None:
    assert any("annee" in e for e in bmo.validate(load(tmp_path), 2025).errors)


def test_missing_column_is_an_error(tmp_path: Path) -> None:
    header = HEADER[:-1]
    rows = [r[:-1] for r in ROWS]
    report = bmo.validate(load(tmp_path, header=header, rows=rows), 2026)
    assert not report.ok and "missing columns" in report.errors[0]


def test_duplicate_key_is_an_error(tmp_path: Path) -> None:
    report = bmo.validate(load(tmp_path, rows=[*ROWS, ROWS[0]]), 2026)
    assert any("duplicate rows" in e for e in report.errors)


def test_invalid_measure_and_code_are_errors(tmp_path: Path) -> None:
    bad = list(ROWS[0])
    bad[1], bad[12] = "XX", "12.5"
    report = bmo.validate(load(tmp_path, rows=[bad]), 2026)
    assert any("code_metier_bmo" in e for e in report.errors)
    assert any("nb_projets_recrutement" in e for e in report.errors)


def test_unexpected_null_is_an_error(tmp_path: Path) -> None:
    bad = list(ROWS[0])
    bad[7] = None  # Dept
    assert any(
        "code_departement: 1 null" in e
        for e in bmo.validate(load(tmp_path, rows=[bad]), 2026).errors
    )


def test_inconsistent_measures_are_warnings(tmp_path: Path) -> None:
    bad = list(ROWS[0])
    bad[13] = "500"  # xmet > met
    report = bmo.validate(load(tmp_path, rows=[bad]), 2026)
    assert report.ok
    assert any("nb_projets_difficiles > nb_projets_recrutement" in w for w in report.warnings)


def test_profile_counts_secret_values(tmp_path: Path) -> None:
    prof = bmo.profile(load(tmp_path))
    assert prof["nb_projets_difficiles"]["secret"] == 2
    assert prof["code_clpe"]["null"] == 1


# --------------------------------------------------------------------------- download
class FakeResponse:
    def __init__(self, body: bytes, status: int = 200, ctype: str = "application/octet-stream"):
        self._body, self.status_code, self.headers = body, status, {"Content-Type": ctype}

    def iter_content(self, chunk_size: int):
        stream = io.BytesIO(self._body)
        while chunk := stream.read(chunk_size):
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response, self.calls = response, []

    def get(self, url, stream=False, timeout=None):
        self.calls.append(url)
        return self.response


def test_download_file_writes_atomically(tmp_path: Path) -> None:
    body = ZIP_MAGIC + b"x" * 100
    result = download_file(
        "https://example.test/f.xlsx",
        tmp_path / "f.xlsx",
        session=FakeSession(FakeResponse(body)),
        expected_magic=ZIP_MAGIC,
    )
    assert result.size_bytes == len(body)
    assert (tmp_path / "f.xlsx").read_bytes() == body
    assert not (tmp_path / "f.xlsx.part").exists()


def test_download_rejects_html_error_page(tmp_path: Path) -> None:
    page = FakeResponse(b"<html>captcha</html>", ctype="text/html")
    with pytest.raises(DownloadError, match="signature"):
        download_file(
            "https://example.test/f.xlsx",
            tmp_path / "f.xlsx",
            session=FakeSession(page),
            expected_magic=ZIP_MAGIC,
        )
    assert not any(tmp_path.iterdir())


def test_download_rejects_http_error(tmp_path: Path) -> None:
    with pytest.raises(DownloadError, match="HTTP 404"):
        download_file(
            "https://example.test/f.xlsx",
            tmp_path / "f.xlsx",
            session=FakeSession(FakeResponse(b"", status=404)),
        )


def test_download_refuses_unverified_year(tmp_path: Path) -> None:
    with pytest.raises(bmo.config.ConfigError, match="No verified BMO URL"):
        bmo.download(2019, raw_dir=tmp_path)


# --------------------------------------------------------------------------- end to end
def test_run_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xlsx = make_workbook(tmp_path / "src.xlsx")
    session = FakeSession(FakeResponse(xlsx.read_bytes()))
    # Workbook too small for the production size threshold: relax it for the test.
    monkeypatch.setattr(
        bmo, "download_file", lambda *a, **kw: download_file(*a, **{**kw, "min_size_bytes": 1})
    )

    manifest = bmo.run(
        2026, raw_dir=tmp_path / "raw", staging_dir=tmp_path / "staging", session=session
    )

    assert len(session.calls) == 1
    staged = pd.read_parquet(manifest["staging_file"])
    assert len(staged) == 3
    assert staged["code_region"].tolist() == ["01", "94", "93"]
    assert {"_source_sha256", "_source_row", "_run_id", "_ingested_at"} <= set(staged.columns)
    saved = json.loads(
        Path(manifest["staging_file"]).with_suffix(".manifest.json").read_text(encoding="utf-8")
    )
    assert saved["validation"]["ok"] and saved["raw_sha256"] == manifest["raw_sha256"]

    # Second run reuses the raw file instead of downloading again.
    bmo.run(2026, raw_dir=tmp_path / "raw", staging_dir=tmp_path / "staging", session=session)
    assert len(session.calls) == 1
