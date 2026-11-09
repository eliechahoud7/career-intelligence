"""DARES — FAP 2021 correspondence: ROME (V3) x qualification -> FAP341.

The official table maps a ROME **V3** code *and* a qualification class (0-9) to one FAP341
family. It must never be collapsed into ROME -> FAP: for 282 of the 532 ROME codes the
family depends on the qualification class.

Source acquisition is **manual**: the DARES website is behind a captcha, so the files are
downloaded in a browser and copied into ``data/raw/dares/fap2021/<YYYYMMDD>/``. This
connector never downloads; it verifies the files against the sha256 pinned in
config/sources.yaml (resource ``dares_rome_qualif_fap2021``) and refuses anything else.

Licence: **unconfirmed** (no statement in the files or on the open-data mirrors).

Pipeline (local)::

    verify checksums  ->  decode cp1252 strictly  ->  read CSV as text  ->  validate
    ->  cross-check the XLSX "pour visualisation" mapping  ->  Bronze-ready Parquet + manifest

Usage::

    python -m career_intelligence.ingestion.dares
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from career_intelligence import config
from career_intelligence.ingestion.http import sha256_of
from career_intelligence.utils.logging import get_logger

logger = get_logger("career_intelligence.ingestion.dares")

SOURCE_NAME = "dares"
RESOURCE_ID = "dares_rome_qualif_fap2021"
DATASET = "rome_qualif_fap2021"
ENCODING = "cp1252"
DELIMITER = ";"
EXPECTED_COLUMNS = ["ROME", "Intitule_ROME", "Qualif", "FAP341", "Intitule_FAP341"]
QUALIF_CLASSES = [str(i) for i in range(10)]
ROME_PATTERN = r"[A-N]\d{4}"
FAP341_PATTERN = r"[A-Z][0-9A-Z][A-Z]\d{2}[a-z]?"  # e.g. A0X43, A0X41c, QAX01


class DaresValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("DARES validation failed: " + "; ".join(errors))
        self.errors = errors


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


# --------------------------------------------------------------------------- paths
def snapshot_dir(resource: dict[str, Any], raw_dir: Path | None = None) -> Path:
    base = raw_dir or config.project_path(config.load_settings()["local"]["raw_dir"])
    return base / "dares" / "fap2021" / resource["snapshot"]


def _staging_dir(resource: dict[str, Any], staging_dir: Path | None = None) -> Path:
    base = staging_dir or config.project_path(config.load_settings()["local"]["staging_dir"])
    return base / "dares" / "fap2021" / resource["snapshot"]


# --------------------------------------------------------------------------- steps
def verify_files(resource: dict[str, Any], folder: Path) -> dict[str, str]:
    """Check every pinned file exists and matches its sha256. Returns {role: sha256}."""
    errors, shas = [], {}
    for role, spec in resource["files"].items():
        path = folder / spec["name"]
        if not path.is_file():
            errors.append(f"missing {role} file: {path}")
            continue
        sha = sha256_of(path)
        if sha != spec["sha256"]:
            errors.append(f"{role} checksum mismatch: expected {spec['sha256']}, got {sha}")
        shas[role] = sha
    if errors:
        raise DaresValidationError(errors)
    logger.info("Checksums verified: %s", ", ".join(f"{k}={v[:12]}…" for k, v in shas.items()))
    return shas


def read_csv(path: Path) -> tuple[pd.DataFrame, int]:
    """Decode strictly as cp1252 and read every value as text, exactly as published."""
    raw = path.read_bytes()
    text = raw.decode(ENCODING)  # strict: undefined cp1252 bytes raise
    records = sum(
        1 for row in csv.reader(io.StringIO(text, newline=""), delimiter=DELIMITER) if row
    )
    frame = pd.read_csv(
        io.StringIO(text, newline=""),
        sep=DELIMITER,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        quoting=csv.QUOTE_NONE,
    ).astype("string")
    logger.info("Read %s: %d rows, %d columns", path.name, len(frame), frame.shape[1])
    return frame, records - 1


def validate(frame: pd.DataFrame, source_records: int) -> ValidationReport:
    report = ValidationReport()
    if list(frame.columns) != EXPECTED_COLUMNS:
        report.errors.append(f"columns {list(frame.columns)} != expected {EXPECTED_COLUMNS}")
        return report
    if frame.empty:
        report.errors.append("no rows")
        return report
    if len(frame) != source_records:
        report.errors.append(f"parsed {len(frame)} rows but the file has {source_records} records")
    if empty := int((frame == "").any(axis=1).sum()):
        report.errors.append(f"{empty} rows with an empty field")
    if dups := int(frame.duplicated().sum()):
        report.errors.append(f"{dups} fully duplicated rows")
    if pair_dups := int(frame.duplicated(["ROME", "Qualif"]).sum()):
        report.errors.append(f"{pair_dups} duplicated (ROME, Qualif) pairs")
    for col, pattern in (("ROME", ROME_PATTERN), ("FAP341", FAP341_PATTERN)):
        bad = frame.loc[~frame[col].str.fullmatch(pattern), col]
        if len(bad):
            report.errors.append(
                f"{col}: {len(bad)} values not matching {pattern}, e.g. {sorted(set(bad))[:5]}"
            )
    bad_q = sorted(set(frame["Qualif"]) - set(QUALIF_CLASSES))
    if bad_q:
        report.errors.append(f"Qualif values outside 0-9: {bad_q}")
    classes = frame.groupby("ROME")["Qualif"].apply(lambda s: sorted(s) == QUALIF_CLASSES)
    if incomplete := int((~classes).sum()):
        report.errors.append(f"{incomplete} ROME codes without exactly the 10 classes 0-9")
    for code, label in (("ROME", "Intitule_ROME"), ("FAP341", "Intitule_FAP341")):
        if (n := int(frame.groupby(code)[label].nunique().max())) != 1:
            report.errors.append(f"{code}: up to {n} different labels per code")

    fap_per_rome = frame.groupby("ROME")["FAP341"].nunique()
    report.stats = {
        "rows": len(frame),
        "distinct_rome": int(frame["ROME"].nunique()),
        "distinct_qualif": int(frame["Qualif"].nunique()),
        "distinct_fap341": int(frame["FAP341"].nunique()),
        "rome_qualification_dependent": int((fap_per_rome > 1).sum()),
        "rome_single_fap": int((fap_per_rome == 1).sum()),
        "labels_with_edge_whitespace": int(
            (frame["Intitule_FAP341"] != frame["Intitule_FAP341"].str.strip()).sum()
        ),
    }
    return report


def expand_xlsx(path: Path) -> dict[tuple[str, str], str]:
    """Expand the compact 'pour visualisation' sheet: empty class = all; 'Q_246' = 2, 4, 6."""
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["ROME_Qualif_to_FAP341"]
        rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0]]
    finally:
        wb.close()
    mapping: dict[tuple[str, str], str] = {}
    for rome, qualif, _label, fap, *_ in rows:
        if qualif is None:
            classes = QUALIF_CLASSES
        elif re.fullmatch(r"Q_\d+", str(qualif)):
            classes = list(str(qualif)[2:])
        else:
            raise ValueError(f"unexpected Qualification value in XLSX: {qualif!r}")
        for c in classes:
            if (rome, c) in mapping:
                raise ValueError(f"XLSX defines ({rome}, {c}) twice")
            mapping[(rome, c)] = fap
    return mapping


def cross_check_xlsx(frame: pd.DataFrame, xlsx_path: Path) -> list[str]:
    """The XLSX must encode exactly the same (ROME, Qualif) -> FAP341 mapping as the CSV."""
    x = expand_xlsx(xlsx_path)
    c = dict(zip(zip(frame["ROME"], frame["Qualif"], strict=True), frame["FAP341"], strict=True))
    errors = []
    if x.keys() != c.keys():
        errors.append(
            f"XLSX/CSV pair sets differ: {len(x.keys() - c.keys())} only in XLSX, "
            f"{len(c.keys() - x.keys())} only in CSV"
        )
    if diff := sum(1 for k in x.keys() & c.keys() if x[k] != c[k]):
        errors.append(f"{diff} pairs with a different FAP341 in XLSX and CSV")
    return errors


def add_lineage(
    frame: pd.DataFrame,
    *,
    resource: dict[str, Any],
    file_name: str,
    sha256: str,
    run_id: str,
    ingested_at: pd.Timestamp,
) -> pd.DataFrame:
    out = frame.copy()
    lineage = {
        "_source_name": SOURCE_NAME,
        "_source_resource": RESOURCE_ID,
        "_dataset": DATASET,
        "_source_url": resource["source_page"],
        "_download_method": "manual",
        "_downloaded_on": resource["downloaded_on"],
        "_source_file": file_name,
        "_source_sha256": sha256,
        "_source_encoding": ENCODING,
        "_snapshot": resource["snapshot"],
        "_run_id": run_id,
    }
    for col, value in lineage.items():
        out[col] = pd.Series(value, index=out.index, dtype="string")
    out["_source_row"] = pd.Series(range(1, len(out) + 1), index=out.index, dtype="int64")
    out["_ingested_at"] = ingested_at
    return out


# --------------------------------------------------------------------------- pipeline
def run(
    *,
    raw_dir: Path | None = None,
    staging_dir: Path | None = None,
    resource: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resource = resource or config.get_manual_resource(RESOURCE_ID)
    folder = snapshot_dir(resource, raw_dir)
    run_id = uuid.uuid4().hex[:12]
    logger.info("DARES ingestion run %s — snapshot %s (%s)", run_id, resource["snapshot"], folder)

    shas = verify_files(resource, folder)
    csv_path = folder / resource["files"]["csv"]["name"]
    xlsx_path = folder / resource["files"]["xlsx"]["name"]
    frame, source_records = read_csv(csv_path)
    report = validate(frame, source_records)
    if report.ok:
        report.errors += cross_check_xlsx(frame, xlsx_path)
    if not report.ok:
        for message in report.errors:
            logger.error("validation: %s", message)
        raise DaresValidationError(report.errors)
    logger.info("Validation passed: %s", report.stats)

    out_dir = _staging_dir(resource, staging_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    staged = add_lineage(
        frame,
        resource=resource,
        file_name=csv_path.name,
        sha256=shas["csv"],
        run_id=run_id,
        ingested_at=pd.Timestamp.now(tz="UTC"),
    )
    out = out_dir / f"{DATASET}.parquet"
    staged.to_parquet(out, engine="pyarrow", index=False)

    manifest = {
        "run_id": run_id,
        "source": SOURCE_NAME,
        "resource": RESOURCE_ID,
        "license": resource["license"],
        "attribution": "Source : Dares, nomenclature des familles professionnelles FAP-2021",
        "source_page": resource["source_page"],
        "download_method": resource["download_method"],
        "downloaded_on": resource["downloaded_on"],
        "snapshot": resource["snapshot"],
        "files": {
            role: {
                "name": spec["name"],
                "sha256": shas[role],
                "size_bytes": (folder / spec["name"]).stat().st_size,
            }
            for role, spec in resource["files"].items()
        },
        "encoding": ENCODING,
        "delimiter": DELIMITER,
        "rome_version": "V3 (stated in the XLSX 'Lisez-moi' sheet)",
        "key": ["ROME", "Qualif"],
        "staging_file": out.name,
        "staged_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "validation": {
            "ok": True,
            "errors": [],
            "stats": report.stats,
            "xlsx_mapping_identical": True,
        },
    }
    manifest_file = out_dir / f"{DATASET}.manifest.json"
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s and %s", out, manifest_file)
    return manifest


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(
        description="Verify, validate and stage the DARES ROME x "
        "qualification -> FAP2021 table (manual download)."
    ).parse_args(argv)
    try:
        manifest = run()
    except (
        DaresValidationError,
        config.ConfigError,
        OSError,
        ValueError,
        UnicodeDecodeError,
    ) as exc:
        logger.error("%s", exc)
        return 1
    print(
        json.dumps(
            {k: manifest[k] for k in ("run_id", "snapshot", "files", "staging_file")}, indent=2
        )
    )
    print(json.dumps(manifest["validation"]["stats"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
