"""France Travail — Enquête Besoins en Main-d'Œuvre (BMO) connector.

Pipeline (local, pandas):

    download (raw .xlsx, immutable)  ->  read (all values as strings)
    ->  standardise column names      ->  validate
    ->  write Bronze-ready Parquet + manifest (for upload to Databricks)

Design choices
--------------
* Every cell is read as **text**: pandas would otherwise turn ``REG='01'`` into ``1``
  and the statistical-secrecy marker ``'*'`` would make measures untyped.
  Values are written to Parquet exactly as published; typing, ``'*'`` handling and
  whitespace cleaning belong to the Silver layer.
* Column names drift between editions (``BE25`` / ``BE26``…), so they are mapped to
  stable snake_case names by pattern.
* Row grain (verified on BMO 2026): occupation x department x bassin d'emploi x CLPE.
* Occupation codes are FAP2021: **no join with ROME here** (crosswalk pending).

Usage::

    python -m career_intelligence.ingestion.bmo            # download if missing, then process
    python -m career_intelligence.ingestion.bmo --force    # re-download
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from career_intelligence import config
from career_intelligence.ingestion.http import (
    ZIP_MAGIC,
    DownloadError,
    DownloadResult,
    build_session,
    download_file,
    sha256_of,
)
from career_intelligence.utils.logging import get_logger

logger = get_logger("career_intelligence.ingestion.bmo")

RESOURCE_ID = "ft_bmo"
SECRET_MARKER = "*"
DATA_SHEET_PATTERN = re.compile(r"^BMO_(\d{4})_open_data$", re.IGNORECASE)

# Source header (normalised: stripped, lower-case) -> canonical column name.
_EXACT_COLUMNS: dict[str, str] = {
    "annee": "annee",
    "code métier bmo": "code_metier_bmo",
    "nom métier bmo": "libelle_metier_bmo",
    "famille_met": "code_famille_metier",
    "lbl_fam_met": "libelle_famille_metier",
    "reg": "code_region",
    "nom_reg": "libelle_region",
    "dept": "code_departement",
    "nomdept": "libelle_departement",
    "clpe": "code_clpe",
    "met": "nb_projets_recrutement",
    "xmet": "nb_projets_difficiles",
    "smet": "nb_projets_saisonniers",
}
# Year-suffixed headers (BE25, NOMBE26, …).
_PATTERN_COLUMNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^be\d{2}$"), "code_bassin_emploi"),
    (re.compile(r"^nombe\d{2}$"), "libelle_bassin_emploi"),
]

MEASURE_COLUMNS = ["nb_projets_recrutement", "nb_projets_difficiles", "nb_projets_saisonniers"]
KEY_COLUMNS = ["code_metier_bmo", "code_departement", "code_bassin_emploi", "code_clpe"]
REQUIRED_COLUMNS = [*_EXACT_COLUMNS.values(), "code_bassin_emploi", "libelle_bassin_emploi"]
NULLABLE_COLUMNS = {"code_clpe"}  # null for Monaco (bassin 9399) in BMO 2026

_FORMATS: dict[str, re.Pattern[str]] = {
    "code_metier_bmo": re.compile(r"^[A-Z][A-Z0-9][A-Z]\d{2}$"),  # FAP2021, e.g. A0X40, QAX01
    "code_famille_metier": re.compile(r"^[A-Z]$"),
    "code_region": re.compile(r"^\d{2}$"),
    "code_departement": re.compile(r"^(\d{2,3}|2[AB])$"),
    "code_bassin_emploi": re.compile(r"^\d{3,4}$"),
}
_MEASURE_FORMAT = re.compile(r"^(\d+|\*)$")


# --------------------------------------------------------------------------- results
@dataclass
class ValidationReport:
    """Outcome of :func:`validate`. ``errors`` block ingestion, ``warnings`` do not."""

    row_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "row_count": self.row_count,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class BmoValidationError(ValueError):
    def __init__(self, report: ValidationReport):
        super().__init__("BMO validation failed: " + "; ".join(report.errors))
        self.report = report


# --------------------------------------------------------------------------- paths
def raw_path(year: int, raw_dir: Path | None = None) -> Path:
    base = raw_dir or config.project_path(config.load_settings()["local"]["raw_dir"])
    return base / "france_travail" / "bmo" / str(year) / f"bmo_{year}.xlsx"


def staging_path(year: int, staging_dir: Path | None = None) -> Path:
    base = staging_dir or config.project_path(config.load_settings()["local"]["staging_dir"])
    return base / "france_travail" / "bmo" / f"bmo_{year}.parquet"


# --------------------------------------------------------------------------- steps
def download(
    year: int,
    *,
    raw_dir: Path | None = None,
    force: bool = False,
    session: requests.Session | None = None,
) -> DownloadResult | None:
    """Download the BMO file for ``year`` from the verified registry URL.

    Returns ``None`` when the file is already present and ``force`` is False.
    """
    resource = config.get_resource(RESOURCE_ID)
    if int(resource.get("year", -1)) != year:
        raise config.ConfigError(
            f"No verified BMO URL for {year} (registry has {resource.get('year')}). "
            "Verify the new edition and update config/sources.yaml first."
        )
    dest = raw_path(year, raw_dir)
    if dest.exists() and not force:
        logger.info("Raw file already present, skipping download: %s", dest)
        return None

    http = config.load_settings()["ingestion"]["http"]
    session = session or build_session(
        http["max_retries"], http["backoff_factor"], http.get("user_agent")
    )
    return download_file(
        resource["url"],
        dest,
        session=session,
        timeout=http["timeout_seconds"],
        expected_magic=ZIP_MAGIC,
        min_size_bytes=100_000,
    )


def find_data_sheet(path: Path) -> tuple[str, int]:
    """Return (sheet name, year) of the data sheet, e.g. ('BMO_2026_open_data', 2026)."""
    with pd.ExcelFile(path, engine="openpyxl") as xl:
        for name in xl.sheet_names:
            if match := DATA_SHEET_PATTERN.match(name.strip()):
                return name, int(match.group(1))
        raise ValueError(
            f"No sheet matching {DATA_SHEET_PATTERN.pattern} in {path.name}: {xl.sheet_names}"
        )


def read_raw(path: Path, sheet_name: str | None = None) -> pd.DataFrame:
    """Read the data sheet with every value as text (only empty cells become null)."""
    sheet_name = sheet_name or find_data_sheet(path)[0]
    logger.info("Reading %s [%s]", path.name, sheet_name)
    return pd.read_excel(
        path,
        sheet_name=sheet_name,
        dtype=str,
        engine="openpyxl",
        keep_default_na=False,
        na_values=[""],
    )


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename source headers to stable canonical names. Unknown columns are kept as-is."""
    mapping: dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower()
        target = _EXACT_COLUMNS.get(key)
        if target is None:
            target = next((name for pat, name in _PATTERN_COLUMNS if pat.match(key)), None)
        if target is None:
            logger.warning("Unmapped BMO column kept as-is: %r", col)
            continue
        if target in mapping.values():
            raise ValueError(f"Several source columns map to {target!r}")
        mapping[col] = target
    return df.rename(columns=mapping)


def validate(df: pd.DataFrame, expected_year: int) -> ValidationReport:
    """Check structure, formats, keys and basic consistency of a standardised BMO frame."""
    report = ValidationReport(row_count=len(df))

    if df.empty:
        report.errors.append("dataset is empty")
        return report
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        report.errors.append(f"missing columns: {missing}")
        return report

    for col in REQUIRED_COLUMNS:
        nulls = int(df[col].isna().sum())
        if nulls and col not in NULLABLE_COLUMNS:
            report.errors.append(f"{col}: {nulls} null values")
        elif nulls:
            report.warnings.append(f"{col}: {nulls} null values (allowed)")

    years = set(df["annee"].dropna().unique())
    if years != {str(expected_year)}:
        report.errors.append(f"annee: expected {{'{expected_year}'}}, found {sorted(years)}")

    for col, pattern in _FORMATS.items():
        bad = df[col].dropna()
        bad = bad[~bad.str.fullmatch(pattern)]
        if not bad.empty:
            report.errors.append(
                f"{col}: {len(bad)} values with unexpected format, e.g. {bad.unique()[:5].tolist()}"
            )

    for col in MEASURE_COLUMNS:
        values = df[col].fillna("")
        bad = values[~values.str.fullmatch(_MEASURE_FORMAT)]
        if not bad.empty:
            report.errors.append(
                f"{col}: {len(bad)} values that are neither integers nor '*', "
                f"e.g. {bad.unique()[:5].tolist()}"
            )
        secret = int((values == SECRET_MARKER).sum())
        report.warnings.append(
            f"{col}: {secret} values under statistical secrecy ({secret / len(df):.1%})"
        )

    duplicates = int(df.duplicated(KEY_COLUMNS).sum())
    if duplicates:
        report.errors.append(f"{duplicates} duplicate rows on key {KEY_COLUMNS}")

    total = pd.to_numeric(df["nb_projets_recrutement"], errors="coerce")
    for col in ("nb_projets_difficiles", "nb_projets_saisonniers"):
        part = pd.to_numeric(df[col], errors="coerce")
        inconsistent = int((part > total).sum())  # NaN comparisons are False
        if inconsistent:
            report.warnings.append(f"{col} > nb_projets_recrutement on {inconsistent} rows")

    for col in ("libelle_metier_bmo", "libelle_bassin_emploi", "libelle_departement"):
        values = df[col].dropna()
        padded = int((values != values.str.strip()).sum())
        if padded:
            report.warnings.append(f"{col}: {padded} values with leading/trailing whitespace")

    return report


def profile(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Per-column counts used for the inspection report and stored in the manifest."""
    result: dict[str, dict[str, int]] = {}
    for col in df.columns:
        series = df[col]
        stats = {
            "non_null": int(series.notna().sum()),
            "null": int(series.isna().sum()),
            "distinct": int(series.nunique(dropna=True)),
        }
        if col in MEASURE_COLUMNS:
            stats["secret"] = int((series == SECRET_MARKER).sum())
        result[col] = stats
    return result


def add_lineage(
    df: pd.DataFrame, *, source_url: str, source_file: Path, sha256: str, sheet: str, run_id: str
) -> pd.DataFrame:
    """Append ingestion metadata columns (prefixed with ``_``) for Bronze traceability."""
    out = df.copy()
    out["_source_resource"] = RESOURCE_ID
    out["_source_url"] = source_url
    out["_source_file"] = source_file.name
    out["_source_sha256"] = sha256
    out["_source_sheet"] = sheet
    out["_source_row"] = range(2, len(df) + 2)  # Excel row number (header is row 1)
    out["_run_id"] = run_id
    out["_ingested_at"] = pd.Timestamp.now(tz="UTC")
    return out


def write_staging(df: pd.DataFrame, dest: Path) -> Path:
    """Write the Bronze-ready Parquet file (text columns stay text)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest, engine="pyarrow", index=False)
    logger.info("Wrote %s (%d rows)", dest, len(df))
    return dest


# --------------------------------------------------------------------------- pipeline
def run(
    year: int | None = None,
    *,
    force: bool = False,
    raw_dir: Path | None = None,
    staging_dir: Path | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Download (if needed), read, validate and stage BMO. Returns the run manifest."""
    settings = config.load_settings()
    year = year or int(settings["ingestion"]["bmo"]["year"])
    run_id = uuid.uuid4().hex[:12]
    logger.info("BMO ingestion run %s for year %s", run_id, year)

    resource = config.get_resource(RESOURCE_ID)
    downloaded = download(year, raw_dir=raw_dir, force=force, session=session)
    src = raw_path(year, raw_dir)
    if not src.exists():
        raise FileNotFoundError(src)
    sha = downloaded.sha256 if downloaded else sha256_of(src)

    sheet, sheet_year = find_data_sheet(src)
    if sheet_year != year:
        raise ValueError(f"Sheet {sheet!r} does not match requested year {year}")

    df = standardize_columns(read_raw(src, sheet))
    report = validate(df, year)
    for message in report.warnings:
        logger.warning("validation: %s", message)
    if not report.ok:
        for message in report.errors:
            logger.error("validation: %s", message)
        raise BmoValidationError(report)
    logger.info("Validation passed: %d rows", report.row_count)

    staged = add_lineage(
        df, source_url=resource["url"], source_file=src, sha256=sha, sheet=sheet, run_id=run_id
    )
    out = write_staging(staged, staging_path(year, staging_dir))

    manifest = {
        "run_id": run_id,
        "resource": RESOURCE_ID,
        "year": year,
        "license": resource.get("license"),
        "source_url": resource["url"],
        "raw_file": str(src),
        "raw_sha256": sha,
        "raw_size_bytes": src.stat().st_size,
        "downloaded_at": downloaded.downloaded_at if downloaded else None,
        "sheet": sheet,
        "staging_file": str(out),
        "staged_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "columns": list(staged.columns),
        "validation": report.to_dict(),
        "profile": profile(df),
    }
    manifest_file = out.with_suffix(".manifest.json")
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote manifest %s", manifest_file)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download, validate and stage the BMO dataset.")
    parser.add_argument("--year", type=int, default=None, help="BMO edition (default: settings)")
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args(argv)
    try:
        manifest = run(args.year, force=args.force)
    except (BmoValidationError, DownloadError, config.ConfigError, OSError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    print(
        json.dumps(
            {k: manifest[k] for k in ("run_id", "year", "raw_file", "raw_sha256", "staging_file")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
