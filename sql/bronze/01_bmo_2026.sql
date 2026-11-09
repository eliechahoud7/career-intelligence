-- =============================================================================
-- Bronze table: France Travail BMO 2026
--
-- Prerequisites
--   1. Local staging file produced by:  python -m career_intelligence.ingestion.bmo
--   2. Uploaded to the landing volume (PowerShell):
--        databricks fs cp data\staging\france_travail\bmo\bmo_2026.parquet `
--          dbfs:/Volumes/career_intelligence/bronze/landing/france_travail/bmo/2026/bmo_2026.parquet `
--          --profile career-intelligence
--
-- The table is a 1:1 copy of the staging Parquet: all 15 source columns as text
-- (codes keep leading zeros; '*' = statistical secrecy) + 8 lineage columns.
-- No cleaning or typing here — that is the Silver layer's job.
-- =============================================================================

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.bmo_2026
COMMENT 'France Travail - Enquete Besoins en Main-d''Oeuvre 2026, raw (all source values as text, * = statistical secrecy). Grain: FAP2021 occupation x department x bassin d''emploi x CLPE. Licence Ouverte. Loaded from local staging Parquet.'
TBLPROPERTIES (
  'source.resource'     = 'ft_bmo',
  'source.url'          = 'https://www.francetravail.org/files/live/sites/peorg/files/documents/Statistiques-et-analyses/Open-data/BMO/Base-open-data-BMO-2026.xlsx',
  'source.raw_sha256'   = '735d0443b799b4c18c145055f87244a355a48b6286ee98ddbab272491d9792e0',
  'source.landing_file' = '/Volumes/career_intelligence/bronze/landing/france_travail/bmo/2026/bmo_2026.parquet',
  'layer'               = 'bronze'
)
AS SELECT *
FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/bmo/2026/bmo_2026.parquet`;
