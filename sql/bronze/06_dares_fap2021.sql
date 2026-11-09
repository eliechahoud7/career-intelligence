-- =============================================================================
-- Bronze tables (Phase 13a): DARES FAP 2021 nomenclature + DARES XLSX 'Lisez-moi' sheet
--
-- dares_fap2021_nomenclature
--   Source  : DARES open-data portal, dataset dares_nomenclature_fap2021 (CSV export)
--             https://data.dares.travail-emploi.gouv.fr/api/explore/v2.1/catalog/datasets/dares_nomenclature_fap2021/exports/csv?use_labels=true
--   Version : dataset modified 2024-04-30 (snapshot 20240430); sha256 9c6b5f21…6e8d (pinned)
--   Format  : UTF-8 with BOM, ';', CRLF; one row per FAP341 with its FAP228/86/22 parents
--   Licence : UNCONFIRMED — none declared on the portal or on data.gouv.fr
--
-- dares_rome_qualif_fap2021_lisez_moi
--   Source  : 'Lisez-moi' sheet of Dares_Table_passage_ROME_Qualif_to_FAP2021_pour_visualisation.xlsx
--             (manual download 2026-11-09, sha256 e06876eb…cdec, archived in the volume)
--   Content : faithful dump, one row per sheet row (27), columns A-G as text; rows 16-25 hold
--             the qualification classes 0-9 (code, label, PCS codes where provided)
--   Licence : UNCONFIRMED (as the DARES correspondence table)
--
-- Every source value as published (text). 12 lineage columns.
--
-- Prerequisites
--   1. python -m career_intelligence.ingestion.fap2021
--      python -m career_intelligence.ingestion.dares --readme
--   2. Upload (PowerShell):
--        databricks fs cp -r data\raw\dares\fap2021_nomenclature\20240430 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/dares/fap2021_nomenclature/20240430/raw --profile career-intelligence
--        databricks fs cp -r data\staging\dares\fap2021_nomenclature\20240430 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/dares/fap2021_nomenclature/20240430/parquet --profile career-intelligence
--        databricks fs cp data\staging\dares\fap2021\20261109\rome_qualif_fap2021_lisez_moi.parquet `
--          dbfs:/Volumes/career_intelligence/bronze/landing/dares/fap2021/20261109/parquet/rome_qualif_fap2021_lisez_moi.parquet --profile career-intelligence
-- =============================================================================

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.dares_fap2021_nomenclature
COMMENT 'DARES FAP 2021 nomenclature, raw: one row per FAP341 (341) with its official FAP228 / FAP86 / FAP22 parents and labels. Licence UNCONFIRMED.'
TBLPROPERTIES (
  'layer' = 'bronze', 'source.name' = 'dares', 'source.resource' = 'dares_fap_hierarchy',
  'source.url' = 'https://data.dares.travail-emploi.gouv.fr/api/explore/v2.1/catalog/datasets/dares_nomenclature_fap2021/exports/csv?use_labels=true',
  'source.raw_sha256' = '9c6b5f2148d8273fcfa2af7fc85345faa7b2a1518c9cc55ad0d01d1ae48b6e8d',
  'source.version' = 'dataset modified 2024-04-30', 'source.snapshot' = '20240430',
  'source.license' = 'UNCONFIRMED',
  'source.attribution' = 'Source : Dares, nomenclature des familles professionnelles FAP-2021',
  'primary_key' = 'code_fap_341'
)
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/dares/fap2021_nomenclature/20240430/parquet/dares_fap2021_nomenclature.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.dares_rome_qualif_fap2021_lisez_moi
COMMENT 'DARES ROME x qualification -> FAP2021 table, raw dump of the XLSX ''Lisez-moi'' sheet (27 rows, columns A-G as text); contains the qualification classes 0-9. Licence UNCONFIRMED.'
TBLPROPERTIES (
  'layer' = 'bronze', 'source.name' = 'dares', 'source.resource' = 'dares_rome_qualif_fap2021',
  'source.page' = 'https://dares.travail-emploi.gouv.fr/donnees/la-nomenclature-des-familles-professionnelles-2021',
  'source.file' = 'Dares_Table_passage_ROME_Qualif_to_FAP2021_pour_visualisation.xlsx',
  'source.sheet' = 'Lisez-moi',
  'source.raw_sha256' = 'e06876eb1798a616f9308b54c5dbea7d1cfc502eb54751111dca76a46ec3cdec',
  'source.download' = 'manual (browser, captcha)', 'source.downloaded_on' = '2026-11-09',
  'source.license' = 'UNCONFIRMED',
  'source.attribution' = 'Source : Dares, nomenclature des familles professionnelles FAP-2021',
  'primary_key' = '_source_row'
)
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/dares/fap2021/20261109/parquet/rome_qualif_fap2021_lisez_moi.parquet`;
