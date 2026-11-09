"""ONISEP — Idéo open-data connector (Fiches métiers, Fiches formations, Formations initiales).

Source data © Onisep, licensed under the Open Database License (ODbL): attribution
"Source : Onisep" is required, and any *publicly used* derived database must be shared
under ODbL (share-alike). See docs/DATA_SOURCES.md.

Pipeline (local)::

    download the 3 files into one dated snapshot (raw, kept)  ->  read
    ->  validate  ->  one Bronze-ready Parquet per dataset + manifest

Bronze representation
---------------------
* XML datasets: one row per record (``<metier>`` / ``<formation>``). Every top-level child
  element becomes a STRING column named exactly like the tag:
    - text-only elements -> their text ('' when empty; HTML descriptions stay escaped text);
    - elements that contain child elements in the file -> the element's original XML
      fragment (e.g. ``<romesV3><romeV3>K1707</romeV3></romesV3>``), for parsing in Silver.
  Nothing is flattened, joined or inferred.
* CSV dataset: values as published ('' kept). Headers contain spaces/accents, which Delta
  does not accept, so they are converted to snake_case; the original -> Bronze mapping is
  recorded in the manifest (``column_mapping``).

Usage::

    python -m career_intelligence.ingestion.onisep            # reuse latest complete snapshot
    python -m career_intelligence.ingestion.onisep --force    # download a new snapshot (today)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
import uuid
import xml.etree.ElementTree as ET
import zipfile
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
    build_session,
    download_file,
    sha256_of,
)
from career_intelligence.utils.logging import get_logger

logger = get_logger("career_intelligence.ingestion.onisep")

SOURCE_NAME = "onisep"
ATTRIBUTION = "Source : Onisep — données sous licence ODbL"


@dataclass(frozen=True)
class Dataset:
    name: str  # also the Bronze table suffix: bronze.onisep_<name>
    resource_id: str  # entry in config/sources.yaml
    filename: str  # local file name inside the snapshot folder
    kind: str  # "xml_zip" | "csv"
    record_tag: str | None = None  # XML record element
    id_pattern: str = ""  # identifier format (MET.n / FOR.n)
    id_column: str = "identifiant"  # Bronze column holding / containing the identifier


DATASETS: dict[str, Dataset] = {
    d.name: d
    for d in (
        Dataset(
            "fiches_metiers",
            "onisep_fiches_metiers",
            "fiches_metiers.zip",
            "xml_zip",
            "metier",
            r"MET\.\d+",
        ),
        Dataset(
            "fiches_formations",
            "onisep_fiches_formations",
            "fiches_formations.zip",
            "xml_zip",
            "formation",
            r"FOR\.\d+",
        ),
        Dataset(
            "formations_initiales",
            "onisep_formations_initiales",
            "formations_initiales.csv",
            "csv",
            None,
            r"FOR\.\d+",
            "url_et_id_onisep",
        ),
    )
}
CSV_DELIMITER = ";"


# --------------------------------------------------------------------------- results
@dataclass
class Staged:
    dataset: Dataset
    frame: pd.DataFrame
    source_member: str
    source_records: int  # counted independently from the raw bytes
    column_mapping: dict[str, str] = field(default_factory=dict)
    xml_columns: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


class OnisepValidationError(ValueError):
    def __init__(self, report: ValidationReport):
        super().__init__("ONISEP validation failed: " + "; ".join(report.errors))
        self.report = report


# --------------------------------------------------------------------------- paths
def _raw_root(raw_dir: Path | None) -> Path:
    return (
        raw_dir or config.project_path(config.load_settings()["local"]["raw_dir"])
    ) / SOURCE_NAME


def _staging_root(staging_dir: Path | None) -> Path:
    base = staging_dir or config.project_path(config.load_settings()["local"]["staging_dir"])
    return base / SOURCE_NAME


def latest_snapshot(raw_dir: Path | None = None) -> Path | None:
    """Most recent snapshot folder (YYYYMMDD) that contains all dataset files."""
    root = _raw_root(raw_dir)
    complete = [
        p
        for p in root.glob("[0-9]" * 8)
        if all((p / d.filename).exists() for d in DATASETS.values())
    ]
    return max(complete, key=lambda p: p.name) if complete else None


# --------------------------------------------------------------------------- steps
def download(
    *, raw_dir: Path | None = None, force: bool = False, session: requests.Session | None = None
) -> Path:
    """Return the snapshot folder to process; download a new one (dated today, UTC) if needed."""
    if not force and (existing := latest_snapshot(raw_dir)):
        logger.info("Snapshot already present, skipping download: %s", existing)
        return existing

    http = config.load_settings()["ingestion"]["http"]
    session = session or build_session(
        http["max_retries"], http["backoff_factor"], http.get("user_agent")
    )
    snapshot = _raw_root(raw_dir) / datetime.now(UTC).strftime("%Y%m%d")
    for d in DATASETS.values():
        resource = config.get_resource(d.resource_id)
        download_file(
            resource["url"],
            snapshot / d.filename,
            session=session,
            timeout=max(http["timeout_seconds"], 120),
            expected_magic=ZIP_MAGIC if d.kind == "xml_zip" else None,
            min_size_bytes=100_000,
        )
    return snapshot


def _text(element: ET.Element) -> str:
    return element.text or ""


def read_xml(path: Path, dataset: Dataset) -> Staged:
    """One row per record; text-only tags -> text, tags with children -> XML fragment."""
    with zipfile.ZipFile(path) as zf:
        members = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected exactly one XML member, found {members}")
        raw = zf.read(members[0])
    # independent record count from the raw bytes (guards against parser surprises)
    source_records = len(re.findall(rb"<" + dataset.record_tag.encode() + rb"[\s>]", raw))
    root = ET.fromstring(raw)
    records = [r for r in root if r.tag == dataset.record_tag]
    if len(records) != len(root):
        raise ValueError(f"{path.name}: unexpected elements under <{root.tag}>")

    tags: list[str] = []
    xml_tags: set[str] = set()
    for rec in records:
        seen: set[str] = set()
        for child in rec:
            if child.tag in seen:
                raise ValueError(f"{path.name}: <{child.tag}> repeated inside one record")
            seen.add(child.tag)
            if child.tag not in tags:
                tags.append(child.tag)
            if len(child):
                xml_tags.add(child.tag)

    rows = []
    for rec in records:
        row = dict.fromkeys(tags)  # absent element -> NULL
        for child in rec:
            if child.tag in xml_tags:
                row[child.tag] = ET.tostring(child, encoding="unicode").strip()
            else:
                row[child.tag] = _text(child)
        rows.append(row)
    frame = pd.DataFrame(rows, columns=tags, dtype="string")
    logger.info(
        "Read %-22s %6d records  %2d columns (%d as XML fragments)",
        dataset.name,
        len(frame),
        len(tags),
        len(xml_tags),
    )
    return Staged(
        dataset, frame, members[0], source_records, xml_columns=[t for t in tags if t in xml_tags]
    )


def snake_case(header: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", header).encode("ascii", "ignore").decode()
    return re.sub(r"[^0-9a-z]+", "_", ascii_.lower()).strip("_")


def read_csv(path: Path, dataset: Dataset) -> Staged:
    text = path.read_bytes().decode("utf-8-sig")
    source_records = (
        sum(1 for row in csv.reader(io.StringIO(text, newline=""), delimiter=CSV_DELIMITER) if row)
        - 1
    )
    frame = pd.read_csv(
        io.StringIO(text, newline=""),
        sep=CSV_DELIMITER,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )
    mapping = {col: snake_case(col) for col in frame.columns}
    if len(set(mapping.values())) != len(mapping):
        raise ValueError(f"{path.name}: column names collide after normalisation: {mapping}")
    frame = frame.rename(columns=mapping).astype("string")
    logger.info("Read %-22s %6d rows     %2d columns", dataset.name, len(frame), frame.shape[1])
    return Staged(dataset, frame, path.name, source_records, column_mapping=mapping)


def read_snapshot(snapshot: Path) -> dict[str, Staged]:
    out = {}
    for d in DATASETS.values():
        reader = read_xml if d.kind == "xml_zip" else read_csv
        out[d.name] = reader(snapshot / d.filename, d)
    return out


def _ids(staged: Staged) -> pd.Series:
    d = staged.dataset
    return staged.frame[d.id_column].str.extract(f"({d.id_pattern})", expand=False)


def validate(staged: dict[str, Staged]) -> ValidationReport:
    report = ValidationReport()
    for name, s in staged.items():
        frame = s.frame
        if frame.empty:
            report.errors.append(f"{name}: no records")
            continue
        if len(frame) != s.source_records:
            report.errors.append(
                f"{name}: parsed {len(frame)} records but the raw file contains {s.source_records}"
            )
        if s.dataset.id_column not in frame.columns:
            report.errors.append(f"{name}: identifier column {s.dataset.id_column!r} missing")
            continue
        ids = _ids(s)
        if missing := int(ids.isna().sum()):
            report.errors.append(f"{name}: {missing} records without a {s.dataset.id_pattern} id")
        if dups := int(ids.dropna().duplicated().sum()):
            report.errors.append(f"{name}: {dups} duplicate identifiers")
        if s.dataset.kind == "xml_zip":
            exact = frame[s.dataset.id_column].str.fullmatch(s.dataset.id_pattern).fillna(False)
            if bad := int((~exact).sum()):
                report.errors.append(
                    f"{name}: {bad} identifiers not exactly {s.dataset.id_pattern}"
                )
        if full_dups := int(frame.duplicated().sum()):
            report.errors.append(f"{name}: {full_dups} fully duplicated records")

    # Cross-dataset references, by identifier only (reported, not enforced).
    if {"fiches_formations", "formations_initiales"} <= staged.keys():
        fiches = set(_ids(staged["fiches_formations"]).dropna())
        catalogue = set(_ids(staged["formations_initiales"]).dropna())
        report.warnings.append(
            "fiches_formations ids in formations_initiales: "
            f"{len(fiches & catalogue)}/{len(fiches)}"
        )
    if {"fiches_formations", "fiches_metiers"} <= staged.keys():
        met_ids = set(_ids(staged["fiches_metiers"]).dropna())
        refs = set(
            staged["fiches_formations"]
            .frame["metiers_formation"]
            .dropna()
            .str.findall(r"<id>(MET\.\d+)</id>")
            .explode()
            .dropna()
        )
        report.warnings.append(
            f"fiches_formations -> fiches_metiers references: {len(refs)} distinct, "
            f"{len(refs - met_ids)} not found"
        )
    return report


def add_lineage(
    staged: Staged, *, snapshot: str, url: str, sha256: str, run_id: str, ingested_at: pd.Timestamp
) -> pd.DataFrame:
    out = staged.frame.copy()
    lineage = {
        "_source_name": SOURCE_NAME,
        "_source_resource": staged.dataset.resource_id,
        "_dataset": staged.dataset.name,
        "_source_url": url,
        "_source_file": staged.source_member,
        "_source_sha256": sha256,
        "_snapshot": snapshot,
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
    force: bool = False,
    raw_dir: Path | None = None,
    staging_dir: Path | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Download (if needed), read, validate and stage the ONISEP datasets."""
    run_id = uuid.uuid4().hex[:12]
    snapshot_dir = download(raw_dir=raw_dir, force=force, session=session)
    snapshot = snapshot_dir.name
    logger.info("ONISEP ingestion run %s — snapshot %s", run_id, snapshot)

    staged = read_snapshot(snapshot_dir)
    report = validate(staged)
    for message in report.warnings:
        logger.info("validation: %s", message)
    if not report.ok:
        for message in report.errors:
            logger.error("validation: %s", message)
        raise OnisepValidationError(report)
    logger.info("Validation passed: %d datasets", len(staged))

    out_dir = _staging_root(staging_dir) / snapshot
    out_dir.mkdir(parents=True, exist_ok=True)
    ingested_at = pd.Timestamp.now(tz="UTC")
    datasets: dict[str, Any] = {}
    for name, s in staged.items():
        resource = config.get_resource(s.dataset.resource_id)
        raw_file = snapshot_dir / s.dataset.filename
        sha = sha256_of(raw_file)
        frame = add_lineage(
            s,
            snapshot=snapshot,
            url=resource["url"],
            sha256=sha,
            run_id=run_id,
            ingested_at=ingested_at,
        )
        path = out_dir / f"{name}.parquet"
        frame.to_parquet(path, engine="pyarrow", index=False)
        datasets[name] = {
            "resource": s.dataset.resource_id,
            "source_url": resource["url"],
            "raw_file": raw_file.name,
            "raw_sha256": sha,
            "raw_size_bytes": raw_file.stat().st_size,
            "source_member": s.source_member,
            "source_records": s.source_records,
            "rows": len(s.frame),
            "columns": list(s.frame.columns),
            "xml_fragment_columns": s.xml_columns,
            "column_mapping": s.column_mapping,
            "identifier": {"column": s.dataset.id_column, "pattern": s.dataset.id_pattern},
            "staging_file": path.name,
        }

    manifest = {
        "run_id": run_id,
        "source": SOURCE_NAME,
        "license": "ODbL",
        "attribution": ATTRIBUTION,
        "snapshot": snapshot,
        "raw_dir": str(snapshot_dir),
        "staging_dir": str(out_dir),
        "staged_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "lineage_columns": [
            "_source_name",
            "_source_resource",
            "_dataset",
            "_source_url",
            "_source_file",
            "_source_sha256",
            "_snapshot",
            "_run_id",
            "_source_row",
            "_ingested_at",
        ],
        "validation": report.to_dict(),
        "datasets": datasets,
    }
    manifest_file = out_dir / f"onisep_{snapshot}.manifest.json"
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %d Parquet files and %s", len(datasets), manifest_file)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download, validate and stage ONISEP datasets.")
    parser.add_argument("--force", action="store_true", help="download a new snapshot")
    args = parser.parse_args(argv)
    try:
        manifest = run(force=args.force)
    except (
        OnisepValidationError,
        DownloadError,
        config.ConfigError,
        OSError,
        ValueError,
        ET.ParseError,
    ) as exc:
        logger.error("%s", exc)
        return 1
    print(
        json.dumps(
            {
                "run_id": manifest["run_id"],
                "snapshot": manifest["snapshot"],
                "staging_dir": manifest["staging_dir"],
                "datasets": {
                    k: {"rows": v["rows"], "raw_sha256": v["raw_sha256"]}
                    for k, v in manifest["datasets"].items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
