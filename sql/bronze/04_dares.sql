-- =============================================================================
-- Bronze table: DARES — ROME (V3) x qualification -> FAP 2021 (FAP341)
-- Snapshot 20261109, MANUAL download (the DARES site is behind a captcha).
--
-- Source page : https://dares.travail-emploi.gouv.fr/donnees/la-nomenclature-des-familles-professionnelles-2021
-- File        : Dares_Table_passage_ROME_Qualif_to_FAP2021_pour_programme.csv
--               sha256 aa4fc948a59309879a297ed40165fcf1f67e1cbd92a6ca7d8dbfce8429f62d13
--               cp1252, ';', CRLF — decoded to UTF-8, values otherwise unchanged
-- Documentation: Dares_Table_passage_ROME_Qualif_to_FAP2021_pour_visualisation.xlsx
--               (archived in the volume under raw/; same mapping, verified pair by pair)
-- Licence     : UNCONFIRMED — no licence statement in the files or on the open-data
--               mirrors. Do not assume Licence Ouverte.
--
-- Semantics: key = (ROME, Qualif). ROME codes are ROME **V3**; Qualif is the DARES
-- 10-class scale built from PCS-2020 (0 = non précisé … 9 = ingénieurs et cadres).
-- NEVER collapse to ROME -> FAP: for 282 of the 532 ROME codes the FAP341 family depends
-- on the qualification class.
--
-- Prerequisites
--   1. python -m career_intelligence.ingestion.dares   (verifies the pinned checksums)
--   2. Upload (PowerShell):
--        databricks fs cp -r data\raw\dares\fap2021\20261109 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/dares/fap2021/20261109/raw --profile career-intelligence
--        databricks fs cp -r data\staging\dares\fap2021\20261109 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/dares/fap2021/20261109/parquet --profile career-intelligence
-- =============================================================================

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.dares_rome_qualif_fap2021
COMMENT 'DARES FAP-2021 correspondence, raw: ROME V3 x qualification class (0-9) -> FAP341. Key (ROME, Qualif). Qualification-dependent: never collapse to ROME -> FAP. All source columns STRING as published. Manual download 2026-11-09. Licence UNCONFIRMED.'
TBLPROPERTIES (
  'layer'                = 'bronze',
  'source.name'          = 'dares',
  'source.resource'      = 'dares_rome_qualif_fap2021',
  'source.page'          = 'https://dares.travail-emploi.gouv.fr/donnees/la-nomenclature-des-familles-professionnelles-2021',
  'source.download'      = 'manual (browser, captcha)',
  'source.downloaded_on' = '2026-11-09',
  'source.snapshot'      = '20261109',
  'source.raw_sha256'    = 'aa4fc948a59309879a297ed40165fcf1f67e1cbd92a6ca7d8dbfce8429f62d13',
  'source.xlsx_sha256'   = 'e06876eb1798a616f9308b54c5dbea7d1cfc502eb54751111dca76a46ec3cdec',
  'source.rome_version'  = 'V3',
  'source.license'       = 'UNCONFIRMED',
  'source.attribution'   = 'Source : Dares, nomenclature des familles professionnelles FAP-2021',
  'primary_key'          = 'ROME, Qualif'
)
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/dares/fap2021/20261109/parquet/rome_qualif_fap2021.parquet`;
