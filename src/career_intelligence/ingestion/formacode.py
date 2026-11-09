"""ROME 4.0 <-> Formacode V14 correspondence + Formacode V14 thesaurus (Centre Inffo).

Four official files, all pinned by sha256 in config/sources.yaml:

* ``rome_formacode``               France Travail correspondence ROME v62 x Formacode V14 (xlsx)
* ``formacode_v14_descripteurs``   Centre Inffo thesaurus descriptors (xlsx)
* ``formacode_v14_grands_domaines`` Centre Inffo top-level domains (xls)
* ``formacode_v14_alignement_nsf`` Formacode -> NSF alignment (xls) — **archived only**: NSF is
  too coarse to link ROME occupations to ONISEP programmes, so no table is built from it.

Bronze representation: one table per loaded file, one row per source row, every value as
text exactly as published (Excel numeric identifiers -> their exact integer text; empty cells
-> NULL; labels, whitespace and literal 'null' strings untouched). Headers with spaces/accents
are renamed to Delta-safe snake_case; the original headers are kept in the manifest. The
correspondence keeps its own labels (no replacement by thesaurus labels in Bronze).

Usage::

    python -m career_intelligence.ingestion.formacode            # reuse local raw files
    python -m career_intelligence.ingestion.formacode --force    # re-download (pins re-checked)
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
    build_session,
    download_file,
    sha256_of,
)
from career_intelligence.ingestion.onisep import snake_case
from career_intelligence.utils.logging import get_logger

logger = get_logger("career_intelligence.ingestion.formacode")

OLE_MAGIC = b"\xd0\xcf\x11\xe0"  # legacy .xls (OLE2 compound file)
MIN_SIZE_BYTES = 10_000  # smallest real file is ~30 KB; guards against error pages
CORRESPONDENCE = "rome_formacode"
DESCRIPTEURS = "formacode_v14_descripteurs"
GRANDS_DOMAINES = "formacode_v14_grands_domaines"
ALIGNEMENT_NSF = "formacode_v14_alignement_nsf"
RESOURCES = [CORRESPONDENCE, DESCRIPTEURS, GRANDS_DOMAINES, ALIGNEMENT_NSF]
TABLES = {  # resource -> Bronze table name (NSF alignment: archive only)
    CORRESPONDENCE: "rome_formacode_v14",
    DESCRIPTEURS: "formacode_v14_descripteurs",
    GRANDS_DOMAINES: "formacode_v14_grands_domaines",
}
CORRESPONDENCE_SHEET = re.compile(r"^ROME .+ - Formacode V\d+$")
README_SHEET = "Lisez-moi"
# Version-specific correspondence headers ("Code ROME 26M10 V62") -> stable names.
CORRESPONDENCE_COLUMNS = [
    (re.compile(r"^Code ROME\b"), "code_rome"),
    (re.compile(r"^Libellé fiche ROME\b"), "libelle_fiche_rome"),
    (re.compile(r"^Code OGR ROME\b"), "code_ogr_rome"),
    (re.compile(r"^Code FORMACODE\b"), "code_formacode"),
    (re.compile(r"^Libellé FORMACODE\b"), "libelle_formacode"),
]
ROME_PATTERN, FORMACODE_PATTERN, OGR_PATTERN = r"[A-N]\d{4}", r"\d{5}", r"\d+"


class FormacodeValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("Formacode validation failed: " + "; ".join(errors))
        self.errors = errors


@dataclass
class Sheet:
    resource: str
    sheet: str
    frame: pd.DataFrame
    column_mapping: dict[str, str]
    metadata: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------- helpers
def cell_text(value: Any) -> str | None:
    """Faithful text for a cell: str as-is, integral numbers as exact integer text, None -> None."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"unexpected boolean cell: {value!r}")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"non-integral numeric cell: {value!r}")
        return str(int(value))
    if isinstance(value, str):
        return value
    raise ValueError(f"unexpected cell type {type(value).__name__}: {value!r}")


def read_rows(path: Path, sheet: str | re.Pattern[str] | int = 0) -> tuple[str, list[tuple]]:
    """Return (sheet name, rows) from .xlsx (openpyxl) or .xls (xlrd), cells untouched."""
    if path.suffix.lower() == ".xls":
        import xlrd

        book = xlrd.open_workbook(path)
        names = book.sheet_names()
        name = _pick_sheet(names, sheet, path)
        sh = book.sheet_by_name(name)
        rows = []
        for i in range(sh.nrows):
            row = []
            for j in range(sh.ncols):
                ctype, value = sh.cell_type(i, j), sh.cell_value(i, j)
                row.append(None if ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK) else value)
            rows.append(tuple(row))
        return name, rows
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        name = _pick_sheet(wb.sheetnames, sheet, path)
        return name, [tuple(r) for r in wb[name].iter_rows(values_only=True)]
    finally:
        wb.close()


def _pick_sheet(names: list[str], sheet: str | re.Pattern[str] | int, path: Path) -> str:
    if isinstance(sheet, int):
        return names[sheet]
    if isinstance(sheet, re.Pattern):
        matches = [n for n in names if sheet.match(n)]
    else:
        matches = [n for n in names if n == sheet]
    if len(matches) != 1:
        raise ValueError(f"{path.name}: expected one sheet matching {sheet!r}, found {names}")
    return matches[0]


def to_frame(rows: list[tuple], mapping: dict[str, str], path: Path) -> pd.DataFrame:
    header, data = rows[0], [r for r in rows[1:] if any(c is not None for c in r)]
    if any(h is None for h in header):
        raise ValueError(f"{path.name}: empty header cell in {header}")
    width = len(header)
    if bad := [r for r in data if len(r) != width]:
        raise ValueError(f"{path.name}: {len(bad)} rows with a width other than {width}")
    columns = [mapping[str(h)] for h in header]
    records = [[cell_text(c) for c in r] for r in data]
    return pd.DataFrame(records, columns=columns, dtype="string")


def correspondence_mapping(header: tuple) -> dict[str, str]:
    mapping = {}
    for h in header:
        target = next((name for pat, name in CORRESPONDENCE_COLUMNS if pat.match(str(h))), None)
        if target is None:
            raise ValueError(f"unexpected correspondence column {h!r}")
        mapping[str(h)] = target
    if sorted(mapping.values()) != sorted(name for _, name in CORRESPONDENCE_COLUMNS):
        raise ValueError(f"correspondence columns incomplete: {list(mapping)}")
    return mapping


def generic_mapping(header: tuple, path: Path) -> dict[str, str]:
    mapping = {str(h): snake_case(str(h)) for h in header}
    if len(set(mapping.values())) != len(mapping):
        raise ValueError(f"{path.name}: column names collide after normalisation: {mapping}")
    return mapping


# --------------------------------------------------------------------------- steps
def raw_dir_for(snapshot: str, raw_dir: Path | None = None) -> Path:
    base = raw_dir or config.project_path(config.load_settings()["local"]["raw_dir"])
    return base / "formacode" / snapshot


def acquire(
    resources: dict[str, dict[str, Any]],
    folder: Path,
    *,
    force: bool = False,
    session: requests.Session | None = None,
) -> dict[str, str]:
    """Download missing files (or all with force) and verify every pinned sha256."""
    http = config.load_settings()["ingestion"]["http"]
    errors, shas = [], {}
    for rid, res in resources.items():
        dest = folder / res["local_file"]
        if force or not dest.exists():
            session = session or build_session(
                http["max_retries"], http["backoff_factor"], http.get("user_agent")
            )
            download_file(
                res["url"],
                dest,
                session=session,
                timeout=max(http["timeout_seconds"], 120),
                expected_magic=OLE_MAGIC if dest.suffix.lower() == ".xls" else ZIP_MAGIC,
                min_size_bytes=MIN_SIZE_BYTES,
            )
        sha = sha256_of(dest)
        shas[rid] = sha
        if sha != res["sha256"]:
            errors.append(f"{rid}: sha256 {sha} != pinned {res['sha256']} ({dest.name})")
    if errors:
        raise FormacodeValidationError(errors)
    logger.info("Checksums verified for %d files", len(shas))
    return shas


def read_all(resources: dict[str, dict[str, Any]], folder: Path) -> dict[str, Sheet]:
    path = folder / resources[CORRESPONDENCE]["local_file"]
    name, rows = read_rows(path, CORRESPONDENCE_SHEET)
    mapping = correspondence_mapping(rows[0])
    _, readme = read_rows(path, README_SHEET)
    metadata = {str(r[0]).strip(): cell_text(r[1]) for r in readme if r and r[0] is not None}
    out = {
        CORRESPONDENCE: Sheet(
            CORRESPONDENCE, name, to_frame(rows, mapping, path), mapping, metadata
        )
    }
    for rid in (DESCRIPTEURS, GRANDS_DOMAINES):
        path = folder / resources[rid]["local_file"]
        name, rows = read_rows(path, 0)
        mapping = generic_mapping(rows[0], path)
        out[rid] = Sheet(rid, name, to_frame(rows, mapping, path), mapping)
    for s in out.values():
        logger.info(
            "Read %-30s %5d rows %2d columns (sheet %r)",
            s.resource,
            len(s.frame),
            s.frame.shape[1],
            s.sheet,
        )
    return out


def validate(sheets: dict[str, Sheet]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    corr = sheets[CORRESPONDENCE].frame
    desc = sheets[DESCRIPTEURS].frame
    dom = sheets[GRANDS_DOMAINES].frame

    def fmt(frame: pd.DataFrame, col: str, pattern: str, label: str) -> None:
        bad = frame[col].isna() | ~frame[col].fillna("").str.fullmatch(pattern)
        if n := int(bad.sum()):
            errors.append(
                f"{label}.{col}: {n} missing/malformed, e.g. {frame.loc[bad, col].head(5).tolist()}"
            )

    # correspondence
    if corr.isna().any(axis=None):
        errors.append(f"correspondence: {int(corr.isna().any(axis=1).sum())} rows with NULLs")
    fmt(corr, "code_rome", ROME_PATTERN, "correspondence")
    fmt(corr, "code_formacode", FORMACODE_PATTERN, "correspondence")
    fmt(corr, "code_ogr_rome", OGR_PATTERN, "correspondence")
    if n := int(corr.duplicated().sum()):
        errors.append(f"correspondence: {n} fully duplicated rows")
    if n := int(corr.duplicated(["code_rome", "code_formacode"]).sum()):
        errors.append(f"correspondence: {n} duplicated (code_rome, code_formacode) pairs")
    for code, other in (("code_rome", "libelle_fiche_rome"), ("code_rome", "code_ogr_rome")):
        if (m := int(corr.groupby(code)[other].nunique().max())) != 1:
            errors.append(f"correspondence: up to {m} distinct {other} per {code}")
    # descriptors / domains
    fmt(desc, "code_du_terme", FORMACODE_PATTERN, "descripteurs")
    if n := int(desc["code_du_terme"].duplicated().sum()):
        errors.append(f"descripteurs: {n} duplicated codes")
    if n := int(desc["descripteur_en_typo_riche"].isna().sum()):
        errors.append(f"descripteurs: {n} descriptors without label")
    fmt(dom, "code_du_terme", r"\d{5}", "grands_domaines")
    if n := int(dom["code_du_terme"].duplicated().sum()):
        errors.append(f"grands_domaines: {n} duplicated codes")
    # cross-reference: every correspondence Formacode is an official V14 descriptor
    unknown = sorted(set(corr["code_formacode"].dropna()) - set(desc["code_du_terme"].dropna()))
    if unknown:
        errors.append(
            f"correspondence: {len(unknown)} Formacodes not in V14 descriptors, e.g. {unknown[:5]}"
        )

    per_rome = corr.groupby("code_rome")["code_formacode"].nunique()
    per_fc = corr.groupby("code_formacode")["code_rome"].nunique()
    stats = {
        "correspondence_rows": len(corr),
        "distinct_rome": int(corr["code_rome"].nunique()),
        "distinct_formacode": int(corr["code_formacode"].nunique()),
        "rome_with_several_formacodes": int((per_rome > 1).sum()),
        "formacodes_with_several_rome": int((per_fc > 1).sum()),
        "max_formacodes_per_rome": int(per_rome.max()),
        "max_rome_per_formacode": int(per_fc.max()),
        "formacodes_with_several_labels_in_correspondence": int(
            (corr.groupby("code_formacode")["libelle_formacode"].nunique() > 1).sum()
        ),
        "descripteurs": len(desc),
        "grands_domaines": len(dom),
    }
    return errors, stats


def add_lineage(
    s: Sheet,
    *,
    res: dict[str, Any],
    source_name: str,
    sha256: str,
    version: str,
    snapshot: str,
    run_id: str,
    ingested_at: pd.Timestamp,
) -> pd.DataFrame:
    out = s.frame.copy()
    for col, value in {
        "_source_name": source_name,
        "_source_resource": s.resource,
        "_dataset": TABLES[s.resource],
        "_source_url": res["url"],
        "_source_file": res["local_file"],
        "_source_sheet": s.sheet,
        "_source_sha256": sha256,
        "_version": version,
        "_snapshot": snapshot,
        "_run_id": run_id,
    }.items():
        out[col] = pd.Series(value, index=out.index, dtype="string")
    out["_source_row"] = pd.Series(range(2, len(out) + 2), index=out.index, dtype="int64")
    out["_ingested_at"] = ingested_at
    return out


# --------------------------------------------------------------------------- pipeline
def run(
    *,
    force: bool = False,
    raw_dir: Path | None = None,
    staging_dir: Path | None = None,
    resources: dict[str, dict[str, Any]] | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    resources = resources or {rid: config.get_resource(rid) for rid in RESOURCES}
    snapshot = resources[CORRESPONDENCE]["snapshot"]
    folder = raw_dir_for(snapshot, raw_dir)
    run_id = uuid.uuid4().hex[:12]
    logger.info("Formacode ingestion run %s — snapshot %s", run_id, snapshot)

    shas = acquire(resources, folder, force=force, session=session)
    sheets = read_all(resources, folder)
    errors, stats = validate(sheets)
    if errors:
        for e in errors:
            logger.error("validation: %s", e)
        raise FormacodeValidationError(errors)
    logger.info("Validation passed: %s", stats)

    base = staging_dir or config.project_path(config.load_settings()["local"]["staging_dir"])
    out_dir = base / "formacode" / snapshot
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = sheets[CORRESPONDENCE].metadata
    versions = {
        CORRESPONDENCE: (
            f"{meta.get('Version ROME V4')} x Formacode {meta.get('Version formacode')}"
        ),
        DESCRIPTEURS: resources[DESCRIPTEURS].get("version") or "Formacode V14",
        GRANDS_DOMAINES: resources[GRANDS_DOMAINES].get("version") or "Formacode V14",
    }
    ingested_at = pd.Timestamp.now(tz="UTC")
    tables = {}
    for rid, s in sheets.items():
        source_name = "france_travail" if rid == CORRESPONDENCE else "centre_inffo"
        frame = add_lineage(
            s,
            res=resources[rid],
            source_name=source_name,
            sha256=shas[rid],
            version=versions[rid],
            snapshot=snapshot,
            run_id=run_id,
            ingested_at=ingested_at,
        )
        path = out_dir / f"{TABLES[rid]}.parquet"
        frame.to_parquet(path, engine="pyarrow", index=False)
        tables[TABLES[rid]] = {
            "resource": rid,
            "rows": len(s.frame),
            "sheet": s.sheet,
            "column_mapping": s.column_mapping,
            "staging_file": path.name,
        }

    manifest = {
        "run_id": run_id,
        "snapshot": snapshot,
        "files": {
            rid: {
                "url": res["url"],
                "local_file": res["local_file"],
                "sha256": shas[rid],
                "size_bytes": (folder / res["local_file"]).stat().st_size,
                "archive_only": bool(res.get("archive_only")),
            }
            for rid, res in resources.items()
        },
        "licenses": {
            CORRESPONDENCE: "Licence Ouverte (France Travail, ROME dataset fr-lo)",
            "formacode_v14": "Licence Ouverte 2.0 (lov2) — Formacode® Centre Inffo",
        },
        "correspondence_readme": meta,
        "versions": versions,
        "tables": tables,
        "validation": {"ok": True, "errors": [], "stats": stats},
        "staged_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    mf = out_dir / f"formacode_{snapshot}.manifest.json"
    mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %d Parquet files and %s", len(tables), mf)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest ROME<->Formacode V14 + V14 thesaurus.")
    parser.add_argument("--force", action="store_true", help="re-download (pins re-checked)")
    args = parser.parse_args(argv)
    try:
        manifest = run(force=args.force)
    except (
        FormacodeValidationError,
        DownloadError,
        config.ConfigError,
        OSError,
        ValueError,
    ) as exc:
        logger.error("%s", exc)
        return 1
    print(
        json.dumps(
            {
                "run_id": manifest["run_id"],
                "snapshot": manifest["snapshot"],
                "tables": {k: v["rows"] for k, v in manifest["tables"].items()},
                "stats": manifest["validation"]["stats"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
