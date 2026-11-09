-- =============================================================================
-- Career Intelligence — Unity Catalog setup (idempotent)
-- Run on a Databricks SQL warehouse (Free Edition: "Serverless Starter Warehouse").
--
-- Note (Free Edition): the REST/CLI call `databricks catalogs create` fails with
-- "Metastore storage root URL does not exist" because the account uses Default
-- Storage. CREATE CATALOG via SQL on a serverless warehouse uses Default Storage
-- and works.
-- =============================================================================

CREATE CATALOG IF NOT EXISTS career_intelligence
  COMMENT 'Career Intelligence project (France: occupations, skills, training, employment)';

CREATE SCHEMA IF NOT EXISTS career_intelligence.bronze
  COMMENT 'Raw data as ingested from sources, with lineage columns. Append-only.';

CREATE VOLUME IF NOT EXISTS career_intelligence.bronze.landing
  COMMENT 'Landing zone for raw/staged source files before Bronze tables';

-- Silver and gold schemas are created in their own phases.
