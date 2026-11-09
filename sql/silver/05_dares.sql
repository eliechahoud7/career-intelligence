-- =============================================================================
-- Silver tables (Phase 13a): FAP 2021 hierarchy, DARES qualification classes,
-- DARES ROME V3 x qualification -> FAP341 correspondence.
-- Source: career_intelligence.bronze (read-only). Licence of all DARES sources: UNCONFIRMED.
--
-- Rules
--   * Codes kept verbatim (text). Labels: whitespace runs (incl. U+00A0, U+202F, tabs) -> one
--     space, trimmed, '' -> NULL; case is NOT changed (3 official FAP341 labels start in
--     lowercase and stay so).
--   * fap2021: the OFFICIAL parent links of the nomenclature are used (FAP341 -> 228 -> 86 -> 22).
--     the 5-character prefix rule is only a validation check (see the checks file).
--   * dares_qualification: rows 0-9 of the qualification table of the archived XLSX
--     'Lisez-moi' sheet (below its header row). PCS codes kept as published (raw text +
--     array split on ', '; 'XX' wildcards kept); NULL where the source gives none (classes 0, 1).
--   * dares_rome_v3_fap341: identifier named code_rome_v3 — ROME **V3**, NOT ROME 4.0 v62:
--     never joined to silver.rome_metier, no use of code_rome_parent, no BMO figures.
--     Key (code_rome_v3, code_qualification), one FAP341 per pair; qualification-dependent
--     mappings preserved. FAP labels come from fap2021 (official), not repeated here.
--   * Lineage columns kept from the Bronze source rows.
-- =============================================================================

CREATE OR REPLACE TABLE career_intelligence.silver.fap2021
COMMENT 'DARES FAP 2021 nomenclature: one row per FAP341 with its official FAP228 / FAP86 / FAP22 parents and labels. Key: code_fap341. Licence UNCONFIRMED.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'dares_fap2021', 'source.license' = 'UNCONFIRMED',
               'source.attribution' = 'Source : Dares, nomenclature des familles professionnelles FAP-2021',
               'primary_key' = 'code_fap341')
AS
SELECT
  b.code_fap_341 AS code_fap341,
  nullif(regexp_replace(regexp_replace(b.libelle_fap_341, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_fap341,
  b.code_fap_228 AS code_fap228,
  nullif(regexp_replace(regexp_replace(b.libelle_fap_228, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_fap228,
  b.code_fap_86 AS code_fap86,
  nullif(regexp_replace(regexp_replace(b.libelle_fap_86, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_fap86,
  b.code_fap_22 AS code_fap22,
  nullif(regexp_replace(regexp_replace(b.libelle_fap_22, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_fap22,
  b._source_name, b._source_resource, b._dataset, b._source_url, b._source_file, b._source_sheet,
  b._source_sha256, b._version, b._snapshot, b._run_id, b._source_row, b._ingested_at
FROM career_intelligence.bronze.dares_fap2021_nomenclature b;

CREATE OR REPLACE TABLE career_intelligence.silver.dares_qualification
COMMENT 'DARES FAP-2021 qualification classes 0-9 (built from PCS-2020), from the archived XLSX Lisez-moi sheet: official label and PCS codes as published (none for classes 0 and 1). Differs from France Travail qualification codes (class 4 = indépendants here). Key: code_qualification. Licence UNCONFIRMED.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'dares_qualification', 'source.license' = 'UNCONFIRMED',
               'source.attribution' = 'Source : Dares, nomenclature des familles professionnelles FAP-2021',
               'primary_key' = 'code_qualification')
AS
SELECT
  b.col_a AS code_qualification,
  nullif(regexp_replace(regexp_replace(b.col_b, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_qualification,
  nullif(regexp_replace(regexp_replace(b.col_c, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS pcs_correspondantes,
  CASE WHEN nullif(trim(b.col_c), '') IS NULL THEN NULL
       ELSE transform(split(trim(b.col_c), ',\\s*'), s -> trim(s)) END AS codes_pcs,
  b._source_name, b._source_resource, b._dataset, b._source_url, b._source_file, b._source_sheet,
  b._source_sha256, b._version, b._snapshot, b._run_id, b._source_row, b._ingested_at
FROM career_intelligence.bronze.dares_rome_qualif_fap2021_lisez_moi b
WHERE b.col_a RLIKE '^[0-9]$'
  AND b._source_row > (SELECT min(_source_row) FROM career_intelligence.bronze.dares_rome_qualif_fap2021_lisez_moi
                       WHERE col_a = 'Code de la qualification');

CREATE OR REPLACE TABLE career_intelligence.silver.dares_rome_v3_fap341
COMMENT 'DARES correspondence ROME V3 x qualification class -> FAP341 (5,320 rows). code_rome_v3 is ROME V3, not ROME 4.0 v62: do not join to silver.rome_metier. Qualification-dependent: never collapse to ROME -> FAP. Key: code_rome_v3, code_qualification. Licence UNCONFIRMED.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'dares_rome_qualif_fap2021', 'source.license' = 'UNCONFIRMED',
               'source.attribution' = 'Source : Dares, nomenclature des familles professionnelles FAP-2021',
               'source.rome_version' = 'V3', 'primary_key' = 'code_rome_v3, code_qualification')
AS
SELECT
  b.ROME AS code_rome_v3,
  nullif(regexp_replace(regexp_replace(b.Intitule_ROME, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_rome_v3,
  b.Qualif AS code_qualification,
  b.FAP341 AS code_fap341,
  b._source_name, b._source_resource, b._dataset, b._source_url, b._download_method, b._downloaded_on,
  b._source_file, b._source_sha256, b._source_encoding, b._snapshot, b._run_id, b._source_row, b._ingested_at
FROM career_intelligence.bronze.dares_rome_qualif_fap2021 b;
