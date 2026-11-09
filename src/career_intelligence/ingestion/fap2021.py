"""DARES — FAP 2021 nomenclature (families 22 / 86 / 228 / 341), official hierarchy.

Source: DARES open-data portal, dataset ``dares_nomenclature_fap2021`` (CSV export, one row
per FAP341 with its FAP228, FAP86 and FAP22 parents and labels). The export is pinned by
sha256 in config/sources.yaml (resource ``dares_fap_hierarchy``); a different file stops the
run. Licence: **unconfirmed** (none declared on the portal or on data.gouv.fr).

Bronze representation: one row per source row, every value as published (text), headers
renamed to Delta-safe snake_case (original headers in the manifest), 12 lineage columns.

Usage::

    python -m career_intelligence.ingestion.fap2021            # reuse local raw file
    python -m career_intelligence.ingestion.fap2021 --force    # re-download (pin re-checked)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from career_intelligence import config
from career_intelligence.ingestion.http import (
    DownloadError,
    build_session,
    download_file,
    sha256_of,
)
from career_intelligence.ingestion.onisep import snake_case
from career_intelligence.utils.logging import get_logger

logger = get_logger("career_intelligence.ingestion.fap2021")

SOURCE_NAME = "dares"
RESOURCE_ID = "dares_fap_hierarchy"
TABLE = "dares_fap2021_nomenclature"
DELIMITER = ";"
EXPECTED_HEADER = [
    "Code FAP 22",
    "Intitulé FAP 22",
    "Code FAP 86",
    "Intitulé FAP 86",
    "Code FAP 228",
    "Intitulé FAP 228",
    "Code FAP 341",
    "Intitulé FAP 341",
]
PATTERNS = {  # official code formats (verified on the 2024-04-30 export)
    "code_fap_22": r"[A-Z]",
    "code_fap_86": r"[A-Z][0-9A-Z][A-Z]",
    "code_fap_228": r"[A-Z][0-9A-Z][A-Z]\d{2}",
    "code_fap_341": r"[A-Z][0-9A-Z][A-Z]\d{2}[a-z]?",
}
LEVELS = [
    ("code_fap_341", "code_fap_228"),
    ("code_fap_228", "code_fap_86"),
    ("code_fap_86", "code_fap_22"),
]


class Fap2021ValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("FAP 2021 validation failed: " + "; ".join(errors))
        self.errors = errors


def acquire(
    resource: dict[str, Any],
    folder: Path,
    *,
    force: bool = False,
    session: requests.Session | None = None,
) -> tuple[Path, str]:
    dest = folder / resource["local_file"]
    if force or not dest.exists():
        http = config.load_settings()["ingestion"]["http"]
        download_file(
            resource["url"],
            dest,
            session=session
            or build_session(http["max_retries"], http["backoff_factor"], http.get("user_agent")),
            timeout=max(http["timeout_seconds"], 90),
            min_size_bytes=10_000,
        )
    sha = sha256_of(dest)
    if sha != resource["sha256"]:
        raise Fap2021ValidationError([f"sha256 {sha} != pinned {resource['sha256']} ({dest.name})"])
    logger.info("Checksum verified: %s…", sha[:12])
    return dest, sha


def read(path: Path) -> tuple[pd.DataFrame, dict[str, str], int]:
    text = path.read_bytes().decode("utf-8-sig")
    records = sum(1 for r in csv.reader(io.StringIO(text, newline=""), delimiter=DELIMITER) if r)
    frame = pd.read_csv(
        io.StringIO(text, newline=""),
        sep=DELIMITER,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        quoting=csv.QUOTE_NONE,
    )
    if list(frame.columns) != EXPECTED_HEADER:
        raise Fap2021ValidationError([f"unexpected header {list(frame.columns)}"])
    mapping = {h: snake_case(h).replace("intitule_", "libelle_") for h in frame.columns}
    return frame.rename(columns=mapping).astype("string"), mapping, records - 1


def validate(frame: pd.DataFrame, source_records: int) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    if len(frame) != source_records:
        errors.append(f"parsed {len(frame)} rows, file has {source_records}")
    if n := int((frame == "").any(axis=1).sum()):
        errors.append(f"{n} rows with an empty field")
    for col, pat in PATTERNS.items():
        if n := int((~frame[col].str.fullmatch(pat)).sum()):
            errors.append(f"{col}: {n} values not matching {pat}")
    if n := int(frame["code_fap_341"].duplicated().sum()):
        errors.append(f"code_fap_341: {n} duplicates")
    for child, parent in LEVELS:  # official hierarchy: one parent per code
        if (m := int(frame.groupby(child)[parent].nunique().max())) != 1:
            errors.append(f"{child}: up to {m} different {parent}")
    for code in ("code_fap_22", "code_fap_86", "code_fap_228", "code_fap_341"):
        label = code.replace("code_", "libelle_")
        if (m := int(frame.groupby(code)[label].nunique().max())) != 1:
            errors.append(f"{code}: up to {m} different labels")
    stats = {f"distinct_{c}": int(frame[c].nunique()) for c in PATTERNS} | {"rows": len(frame)}
    return errors, stats


def add_lineage(
    frame: pd.DataFrame,
    *,
    resource: dict[str, Any],
    sha256: str,
    run_id: str,
    ingested_at: pd.Timestamp,
) -> pd.DataFrame:
    out = frame.copy()
    for col, value in {
        "_source_name": SOURCE_NAME,
        "_source_resource": RESOURCE_ID,
        "_dataset": TABLE,
        "_source_url": resource["url"],
        "_source_file": resource["local_file"],
        "_source_sheet": "csv",
        "_source_sha256": sha256,
        "_version": resource["version"],
        "_snapshot": resource["snapshot"],
        "_run_id": run_id,
    }.items():
        out[col] = pd.Series(value, index=out.index, dtype="string")
    out["_source_row"] = pd.Series(range(2, len(out) + 2), index=out.index, dtype="int64")
    out["_ingested_at"] = ingested_at
    return out


def run(
    *,
    force: bool = False,
    raw_dir: Path | None = None,
    staging_dir: Path | None = None,
    resource: dict[str, Any] | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    resource = resource or config.get_resource(RESOURCE_ID)
    settings = config.load_settings()["local"]
    raw = (raw_dir or config.project_path(settings["raw_dir"])) / "dares" / "fap2021_nomenclature"
    folder = raw / resource["snapshot"]
    run_id = uuid.uuid4().hex[:12]
    path, sha = acquire(resource, folder, force=force, session=session)
    frame, mapping, records = read(path)
    errors, stats = validate(frame, records)
    if errors:
        for e in errors:
            logger.error("validation: %s", e)
        raise Fap2021ValidationError(errors)
    logger.info("Validation passed: %s", stats)

    base = staging_dir or config.project_path(settings["staging_dir"])
    out_dir = base / "dares" / "fap2021_nomenclature" / resource["snapshot"]
    out_dir.mkdir(parents=True, exist_ok=True)
    staged = add_lineage(
        frame, resource=resource, sha256=sha, run_id=run_id, ingested_at=pd.Timestamp.now(tz="UTC")
    )
    out = out_dir / f"{TABLE}.parquet"
    staged.to_parquet(out, engine="pyarrow", index=False)
    manifest = {
        "run_id": run_id,
        "resource": RESOURCE_ID,
        "table": TABLE,
        "source_url": resource["url"],
        "local_file": resource["local_file"],
        "sha256": sha,
        "size_bytes": path.stat().st_size,
        "version": resource["version"],
        "snapshot": resource["snapshot"],
        "license": resource.get("license"),
        "column_mapping": mapping,
        "validation": {"ok": True, "stats": stats},
        "staging_file": out.name,
        "staged_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    mf = out_dir / f"{TABLE}.manifest.json"
    mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s and %s", out, mf)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest the DARES FAP 2021 nomenclature.")
    parser.add_argument("--force", action="store_true", help="re-download (pin re-checked)")
    args = parser.parse_args(argv)
    try:
        manifest = run(force=args.force)
    except (Fap2021ValidationError, DownloadError, config.ConfigError, OSError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    print(
        json.dumps(
            {k: manifest[k] for k in ("run_id", "snapshot", "sha256")}
            | manifest["validation"]["stats"],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
