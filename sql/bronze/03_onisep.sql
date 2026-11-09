-- =============================================================================
-- Bronze tables: ONISEP Idéo open data (snapshot 20261109)
--
-- Source data © Onisep — Open Database License (ODbL). Attribution "Source : Onisep"
-- is required; any publicly used derived database must be shared under ODbL.
--
-- Prerequisites
--   1. python -m career_intelligence.ingestion.onisep
--   2. Upload (PowerShell):
--        databricks fs cp -r data\raw\onisep\20261109 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/onisep/20261109/raw --profile career-intelligence
--        databricks fs cp -r data\staging\onisep\20261109 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/onisep/20261109/parquet --profile career-intelligence
--
-- Each table is a 1:1 copy of its staging Parquet. Source columns are STRING:
--   * XML datasets: one row per record; text elements as text, elements with children as
--     their original XML fragment (see manifest "xml_fragment_columns");
--   * CSV dataset: values as published, headers converted to snake_case (see manifest
--     "column_mapping").
-- Lineage: _source_name, _source_resource, _dataset, _source_url, _source_file,
--          _source_sha256, _snapshot, _run_id, _source_row, _ingested_at.
-- =============================================================================

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.onisep_fiches_metiers
COMMENT 'ONISEP Idéo-Fiches métiers, raw: one row per <metier> (identifiant MET.n). Nested elements stored as XML fragments. Source : Onisep — licence ODbL.'
TBLPROPERTIES ('layer' = 'bronze', 'source.name' = 'onisep', 'source.resource' = 'onisep_fiches_metiers',
               'source.snapshot' = '20261109', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep',
               'source.raw_sha256' = 'eb04222a504af7626481e38876565ee3e992f5209f8575d10a6ff01a39939bc8')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/onisep/20261109/parquet/fiches_metiers.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.onisep_fiches_formations
COMMENT 'ONISEP Idéo-Fiches formations, raw: one row per <formation> (identifiant FOR.n), trainings linked to at least one métier. Nested elements stored as XML fragments. Source : Onisep — licence ODbL.'
TBLPROPERTIES ('layer' = 'bronze', 'source.name' = 'onisep', 'source.resource' = 'onisep_fiches_formations',
               'source.snapshot' = '20261109', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep',
               'source.raw_sha256' = '4fc73fba123e6593a9cc94d95a9325f2eee550e1e1270a7d002398586d4db2a3')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/onisep/20261109/parquet/fiches_formations.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.onisep_formations_initiales
COMMENT 'ONISEP Idéo-Formations initiales en France, raw CSV (all initial trainings; FOR.n id inside url_et_id_onisep). Headers snake_cased. Source : Onisep — licence ODbL.'
TBLPROPERTIES ('layer' = 'bronze', 'source.name' = 'onisep', 'source.resource' = 'onisep_formations_initiales',
               'source.snapshot' = '20261109', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep',
               'source.raw_sha256' = '355d7dd55f37affa8c19329eb1c0358bafa6da0abb0b5ba87c61dc74e5fe32e8')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/onisep/20261109/parquet/formations_initiales.parquet`;
