"""France Travail — ROME 4.0 open-data connector (CSV archive).

Pipeline (local, pandas):

    download zip (raw, kept per ROME version)  ->  read every CSV as text
    ->  validate (structure, keys, relationships)
    ->  one Bronze-ready Parquet per CSV + manifest (for upload to Databricks)

Bronze representation
---------------------
One table per CSV file, columns and values exactly as published (text, empty
strings kept, multi-line definitions kept), plus lineage columns. Nothing is
joined, split or flattened. In particular ``liens_rome_referentiels`` is a
*polymorphic* link table whose ``code_ogr`` points to a different referential
depending on ``code_compo_bloc`` / ``code_rubrique`` (see LINK_TARGETS); it is
stored as-is and resolved in Silver.

Source quirks handled (ROME v62):
* ``arborescence_secteur_naf`` is cp1252, all other files UTF-8 with BOM-less text.
* ``centre_interet`` / ``secteur_activite`` contain quoted multi-line cells and
  blank lines between records (blank lines are not records).
* ``type_referentiel`` is empty (header only).

Usage::

    python -m career_intelligence.ingestion.rome            # reuse local raw zip if present
    python -m career_intelligence.ingestion.rome --force    # download the current release
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import uuid
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

logger = get_logger("career_intelligence.ingestion.rome")

RESOURCE_ID = "rome_bulk_csv"
ARCHIVE_NAME = "rome_open_data_csv.zip"
VERSION_FILE = "version.txt"
_MEMBER_PATTERN = re.compile(r"^unix_(?P<entity>.+?)_v(?P<suffix>\d+)(?:_utf8)?\.csv$")
_VERSION_PATTERN = re.compile(r"Num[eé]ro de version\s*:\s*(\d+)", re.IGNORECASE)

# Natural keys verified on ROME v62 (duplicates are reported as validation errors).
KEYS: dict[str, list[str]] = {
    "referentiel_code_rome": ["code_rome"],
    "referentiel_appellation": ["code_ogr"],
    "referentiel_competence": ["code_ogr"],
    "referentiel_savoir": ["code_ogr_savoir"],
    "referentiel_contexte_travail": ["code_ogr"],
    "referentiel_code_rome_riasec": ["code_rome"],
    "referentiel_macro_competence_riasec": ["code_ogr"],
    "item": ["code_ogr"],
    "grand_domaine": ["code_grand_domaine"],
    "domaine_professionnel": ["code_domaine_professionnel"],
    "cr_gd_dp": ["code_rome"],
    "composition_bloc": ["code_compo_bloc"],
    "descriptif_rubrique": ["code_rubrique"],
    "centre_interet": ["code_centre_interet"],
    "secteur_activite": ["code_sect_activite"],
    "sous_secteur_activite": ["code_ss_sect_activite"],
    "secteur_naf": ["code_tech_secteur_naf"],
    "themes": ["code_theme"],
    "texte": ["code_rome", "code_compo_bloc", "libelle_type_texte", "position_phrase"],
    "liens_rome_referentiels": ["code_rome", "code_compo_bloc", "code_rubrique", "code_ogr"],
    "coherence_item": ["code_rome", "code_ogr"],
    "rubrique_mobilite": ["code_rome", "code_rome_cible"],
    "arborescence_competences": ["code_ogr_macro_competence", "code_ogr_competence"],
    "arborescence_centre_interet": ["code_centre_interet", "code_rome"],
    "arborescence_secteur_naf": ["code_secteur_naf", "code_rome"],
    "arborescence_thematique": ["code_theme", "code_rome"],
}

# (child table, child column) -> (parent table, parent column)
FOREIGN_KEYS: list[tuple[str, str, str, str]] = [
    ("referentiel_appellation", "code_rome", "referentiel_code_rome", "code_rome"),
    ("cr_gd_dp", "code_rome", "referentiel_code_rome", "code_rome"),
    ("texte", "code_rome", "referentiel_code_rome", "code_rome"),
    ("liens_rome_referentiels", "code_rome", "referentiel_code_rome", "code_rome"),
    ("coherence_item", "code_rome", "referentiel_code_rome", "code_rome"),
    ("coherence_item", "code_ogr", "item", "code_ogr"),
    ("rubrique_mobilite", "code_rome", "referentiel_code_rome", "code_rome"),
    ("rubrique_mobilite", "code_rome_cible", "referentiel_code_rome", "code_rome"),
    ("referentiel_code_rome_riasec", "code_rome", "referentiel_code_rome", "code_rome"),
    ("arborescence_competences", "code_ogr_competence", "referentiel_competence", "code_ogr"),
    (
        "referentiel_macro_competence_riasec",
        "code_ogr",
        "arborescence_competences",
        "code_ogr_macro_competence",
    ),
]

# Polymorphic target of liens_rome_referentiels.code_ogr, by (code_compo_bloc, code_rubrique).
LINK_TARGETS: dict[tuple[str, str], tuple[str, str]] = {
    ("1", ""): ("referentiel_code_rome", "code_ogr"),  # the occupation itself
    ("2", ""): ("referentiel_appellation", "code_ogr"),  # job titles
    ("5", "1"): ("referentiel_competence", "code_ogr"),  # savoir-faire
    ("5", "2"): ("referentiel_competence", "code_ogr"),  # savoir-être professionnels
    ("5", "3"): ("referentiel_savoir", "code_ogr_savoir"),  # savoirs
    ("6", ""): ("referentiel_contexte_travail", "code_ogr"),  # contextes de travail
}

ALLOWED_EMPTY = {"type_referentiel"}


# --------------------------------------------------------------------------- results
@dataclass
class RomeTable:
    entity: str
    member: str
    encoding: str
    frame: pd.DataFrame


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


class RomeValidationError(ValueError):
    def __init__(self, report: ValidationReport):
        super().__init__("ROME validation failed: " + "; ".join(report.errors))
        self.report = report


# --------------------------------------------------------------------------- paths
def _raw_root(raw_dir: Path | None) -> Path:
    base = raw_dir or config.project_path(config.load_settings()["local"]["raw_dir"])
    return base / "france_travail" / "rome"


def _staging_root(staging_dir: Path | None) -> Path:
    base = staging_dir or config.project_path(config.load_settings()["local"]["staging_dir"])
    return base / "france_travail" / "rome"


def archive_version(archive: Path) -> tuple[str, str]:
    """Return (version number, full version.txt text) read from the archive."""
    with zipfile.ZipFile(archive) as zf:
        text = zf.read(VERSION_FILE).decode("utf-8", errors="replace")
    match = _VERSION_PATTERN.search(text)
    if not match:
        raise ValueError(f"No version number found in {VERSION_FILE}")
    return match.group(1), text


def latest_local_archive(raw_dir: Path | None = None) -> Path | None:
    """Most recent versioned raw archive already stored locally, if any."""
    candidates = sorted(
        _raw_root(raw_dir).glob(f"v*/{ARCHIVE_NAME}"),
        key=lambda p: int(p.parent.name[1:]) if p.parent.name[1:].isdigit() else -1,
    )
    return candidates[-1] if candidates else None


# --------------------------------------------------------------------------- steps
def download(
    *, raw_dir: Path | None = None, force: bool = False, session: requests.Session | None = None
) -> Path:
    """Return the raw archive to process, downloading the current release when needed.

    The archive is stored under ``rome/v<version>/`` so every release is kept.
    Re-downloading an already stored version with *different* content is an error.
    """
    if not force and (existing := latest_local_archive(raw_dir)):
        logger.info("Raw archive already present, skipping download: %s", existing)
        return existing

    resource = config.get_resource(RESOURCE_ID)
    http = config.load_settings()["ingestion"]["http"]
    session = session or build_session(
        http["max_retries"], http["backoff_factor"], http.get("user_agent")
    )
    tmp = _raw_root(raw_dir) / "_download" / ARCHIVE_NAME
    result = download_file(
        resource["url"],
        tmp,
        session=session,
        timeout=max(http["timeout_seconds"], 120),
        expected_magic=ZIP_MAGIC,
        min_size_bytes=1_000_000,
    )
    version, _ = archive_version(tmp)
    dest = _raw_root(raw_dir) / f"v{version}" / ARCHIVE_NAME
    if dest.exists():
        if sha256_of(dest) != result.sha256:
            raise ValueError(f"ROME v{version} already stored with different content: {dest}")
        tmp.unlink()
        logger.info("ROME v%s unchanged, keeping %s", version, dest)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tmp, dest)
        logger.info("Stored ROME v%s at %s", version, dest)
    return dest


def _decode(raw: bytes, member: str) -> tuple[str, str]:
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        logger.warning("%s is not valid UTF-8, decoding as cp1252", member)
        return raw.decode("cp1252"), "cp1252"


def read_archive(archive: Path) -> dict[str, RomeTable]:
    """Read every CSV of the archive with all values as text."""
    tables: dict[str, RomeTable] = {}
    with zipfile.ZipFile(archive) as zf:
        for member in sorted(zf.namelist()):
            match = _MEMBER_PATTERN.match(member)
            if not match:
                if member != VERSION_FILE:
                    logger.warning("Ignoring unexpected archive member: %s", member)
                continue
            text, encoding = _decode(zf.read(member), member)
            frame = pd.read_csv(
                io.StringIO(text, newline=""),
                dtype=str,
                keep_default_na=False,  # empty fields stay "" (as published)
                na_filter=False,
                skip_blank_lines=True,  # blank lines between records are not records
            )
            entity = match.group("entity")
            if entity in tables:
                raise ValueError(f"Two archive members map to entity {entity!r}")
            tables[entity] = RomeTable(entity, member, encoding, frame)
            logger.info(
                "Read %-40s %7d rows  %2d cols  %s", entity, len(frame), frame.shape[1], encoding
            )
    return tables


def validate(tables: dict[str, RomeTable]) -> ValidationReport:
    """Structural checks (errors) and documented-relationship checks (errors)."""
    report = ValidationReport()
    frames = {name: t.frame for name, t in tables.items()}

    expected = set(KEYS) | {c for fk in FOREIGN_KEYS for c in (fk[0], fk[2])} | ALLOWED_EMPTY
    if missing := sorted(expected - set(frames)):
        report.errors.append(f"missing entities: {missing}")
        return report

    for name, frame in frames.items():
        if frame.empty and name not in ALLOWED_EMPTY:
            report.errors.append(f"{name}: no rows")
        unnamed = [c for c in frame.columns if c.startswith("Unnamed")]
        if unnamed:
            report.errors.append(f"{name}: unnamed columns {unnamed}")

    for name, cols in KEYS.items():
        frame = frames[name]
        if absent := [c for c in cols if c not in frame.columns]:
            report.errors.append(f"{name}: missing key columns {absent}")
            continue
        if dups := int(frame.duplicated(cols).sum()):
            report.errors.append(f"{name}: {dups} duplicate rows on key {cols}")

    for child, ccol, parent, pcol in FOREIGN_KEYS:
        values = set(frames[child][ccol]) - {""}
        orphans = values - set(frames[parent][pcol])
        if orphans:
            report.errors.append(
                f"{child}.{ccol} -> {parent}.{pcol}: {len(orphans)} orphan values, "
                f"e.g. {sorted(orphans)[:5]}"
            )

    links = frames["liens_rome_referentiels"]
    groups = links.groupby(["code_compo_bloc", "code_rubrique"])["code_ogr"]
    for (bloc, rubrique), ogrs in groups:
        target = LINK_TARGETS.get((bloc, rubrique))
        if target is None:
            report.errors.append(f"liens_rome_referentiels: unknown block ({bloc}, {rubrique!r})")
            continue
        orphans = set(ogrs) - set(frames[target[0]][target[1]])
        if orphans:
            report.errors.append(
                f"liens_rome_referentiels block ({bloc}, {rubrique!r}) -> {target[0]}: "
                f"{len(orphans)} unresolved code_ogr"
            )

    for name in ("centre_interet", "secteur_activite"):
        multiline = int(frames[name].apply(lambda s: s.str.contains("\n")).any(axis=1).sum())
        if multiline:
            report.warnings.append(f"{name}: {multiline} rows with multi-line text (kept)")
    for name, t in tables.items():
        if t.encoding != "utf-8":
            report.warnings.append(f"{name}: source encoded {t.encoding} (decoded to UTF-8)")
    return report


def add_lineage(
    frame: pd.DataFrame,
    *,
    table: RomeTable,
    version: str,
    source_url: str,
    archive_sha256: str,
    run_id: str,
    ingested_at: pd.Timestamp,
) -> pd.DataFrame:
    out = frame.copy()
    out["_source_resource"] = RESOURCE_ID
    out["_source_url"] = source_url
    out["_source_file"] = table.member
    out["_source_archive_sha256"] = archive_sha256
    out["_source_encoding"] = table.encoding
    out["_rome_version"] = version
    out["_source_row"] = pd.Series(range(1, len(frame) + 1), index=frame.index, dtype="int64")
    out["_run_id"] = run_id
    out["_ingested_at"] = ingested_at
    # Explicit string dtype: otherwise an empty table (type_referentiel) would be written
    # with Parquet type `null` instead of `string`.
    text_cols = [c for c in out.columns if c not in ("_source_row", "_ingested_at")]
    return out.astype({c: "string" for c in text_cols})


# --------------------------------------------------------------------------- pipeline
def run(
    *,
    force: bool = False,
    raw_dir: Path | None = None,
    staging_dir: Path | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Download (if needed), read, validate and stage all ROME CSVs. Returns the manifest."""
    run_id = uuid.uuid4().hex[:12]
    resource = config.get_resource(RESOURCE_ID)
    archive = download(raw_dir=raw_dir, force=force, session=session)
    version, version_text = archive_version(archive)
    sha = sha256_of(archive)
    logger.info("ROME ingestion run %s — version %s (%s)", run_id, version, archive)

    tables = read_archive(archive)
    report = validate(tables)
    for message in report.warnings:
        logger.warning("validation: %s", message)
    if not report.ok:
        for message in report.errors:
            logger.error("validation: %s", message)
        raise RomeValidationError(report)
    logger.info("Validation passed: %d tables", len(tables))

    out_dir = _staging_root(staging_dir) / f"v{version}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ingested_at = pd.Timestamp.now(tz="UTC")
    table_info: dict[str, Any] = {}
    for name, table in sorted(tables.items()):
        staged = add_lineage(
            table.frame,
            table=table,
            version=version,
            source_url=resource["url"],
            archive_sha256=sha,
            run_id=run_id,
            ingested_at=ingested_at,
        )
        path = out_dir / f"{name}.parquet"
        staged.to_parquet(path, engine="pyarrow", index=False)
        table_info[name] = {
            "source_member": table.member,
            "encoding": table.encoding,
            "rows": len(table.frame),
            "source_columns": list(table.frame.columns),
            "key": KEYS.get(name),
            "staging_file": path.name,
        }

    manifest = {
        "run_id": run_id,
        "resource": RESOURCE_ID,
        "license": resource.get("license"),
        "source_url": resource["url"],
        "rome_version": version,
        "version_text": version_text,
        "raw_file": str(archive),
        "raw_sha256": sha,
        "raw_size_bytes": archive.stat().st_size,
        "staging_dir": str(out_dir),
        "staged_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "lineage_columns": [
            "_source_resource",
            "_source_url",
            "_source_file",
            "_source_archive_sha256",
            "_source_encoding",
            "_rome_version",
            "_source_row",
            "_run_id",
            "_ingested_at",
        ],
        "validation": report.to_dict(),
        "tables": table_info,
    }
    manifest_file = out_dir / f"rome_v{version}.manifest.json"
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %d Parquet files and %s", len(table_info), manifest_file)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download, validate and stage ROME 4.0 CSVs.")
    parser.add_argument("--force", action="store_true", help="download the current release")
    args = parser.parse_args(argv)
    try:
        manifest = run(force=args.force)
    except (RomeValidationError, DownloadError, config.ConfigError, OSError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    print(
        json.dumps(
            {
                "run_id": manifest["run_id"],
                "rome_version": manifest["rome_version"],
                "raw_file": manifest["raw_file"],
                "raw_sha256": manifest["raw_sha256"],
                "staging_dir": manifest["staging_dir"],
                "rows": {k: v["rows"] for k, v in manifest["tables"].items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
