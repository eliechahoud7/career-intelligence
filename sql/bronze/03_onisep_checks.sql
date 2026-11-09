-- =============================================================================
-- Verification for the ONISEP Bronze tables (snapshot 20261109).
-- Expected values come from the local validation run (onisep_20261109.manifest.json).
-- Every check_* column must be TRUE.
-- =============================================================================

-- 1. Row counts = source records = staged Parquet rows
SELECT
  (SELECT count(*) FROM career_intelligence.bronze.onisep_fiches_metiers)       = 1138 AS check_rows_fiches_metiers,
  (SELECT count(*) FROM career_intelligence.bronze.onisep_fiches_formations)    = 2349 AS check_rows_fiches_formations,
  (SELECT count(*) FROM career_intelligence.bronze.onisep_formations_initiales) = 5799 AS check_rows_formations_initiales,
  (SELECT count(*) FROM parquet.`/Volumes/career_intelligence/bronze/landing/onisep/20261109/parquet/fiches_metiers.parquet`)       = 1138
  AND (SELECT count(*) FROM parquet.`/Volumes/career_intelligence/bronze/landing/onisep/20261109/parquet/fiches_formations.parquet`) = 2349
  AND (SELECT count(*) FROM parquet.`/Volumes/career_intelligence/bronze/landing/onisep/20261109/parquet/formations_initiales.parquet`) = 5799
    AS check_rows_staged_parquet;

-- 2. Identifiers: present, well-formed, unique; no fully duplicated records
SELECT
  (SELECT count(*) = count(DISTINCT identifiant) AND count_if(NOT identifiant RLIKE '^MET\\.[0-9]+$') = 0
     FROM career_intelligence.bronze.onisep_fiches_metiers)                     AS check_id_fiches_metiers,
  (SELECT count(*) = count(DISTINCT identifiant) AND count_if(NOT identifiant RLIKE '^FOR\\.[0-9]+$') = 0
     FROM career_intelligence.bronze.onisep_fiches_formations)                  AS check_id_fiches_formations,
  (SELECT count_if(regexp_extract(url_et_id_onisep, 'FOR\\.[0-9]+', 0) = '') = 0
          AND count(DISTINCT regexp_extract(url_et_id_onisep, 'FOR\\.[0-9]+', 0)) = count(*)
     FROM career_intelligence.bronze.onisep_formations_initiales)               AS check_id_formations_initiales,
  (SELECT count(*) = (SELECT count(*) FROM (SELECT DISTINCT * EXCEPT (_source_row) FROM career_intelligence.bronze.onisep_formations_initiales))
     FROM career_intelligence.bronze.onisep_formations_initiales)               AS check_no_duplicate_rows_csv;

-- 3. Schema: expected column counts, all source columns STRING
SELECT table_name,
       count_if(column_name NOT LIKE '\\_%')                                       AS source_columns,
       count_if(column_name LIKE '\\_%')                                           AS lineage_columns,
       count_if(column_name NOT LIKE '\\_%' AND data_type <> 'STRING') = 0         AS check_source_strings,
       count_if(column_name LIKE '\\_%') = 10                                      AS check_lineage_columns
FROM career_intelligence.information_schema.columns
WHERE table_schema = 'bronze' AND table_name LIKE 'onisep\\_%'
GROUP BY table_name ORDER BY table_name;
-- Expected source columns: fiches_formations 31, fiches_metiers 21, formations_initiales 16

-- 4. Lineage: one source file, one checksum (= downloaded file), one snapshot per table
SELECT 'fiches_metiers' AS dataset,
       count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = 'eb04222a504af7626481e38876565ee3e992f5209f8575d10a6ff01a39939bc8'
         AND count_if(_source_name <> 'onisep' OR _snapshot <> '20261109' OR _ingested_at IS NULL) = 0
         AND min(_source_row) = 1 AND max(_source_row) = count(*)                AS check_lineage
FROM career_intelligence.bronze.onisep_fiches_metiers
UNION ALL
SELECT 'fiches_formations',
       count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = '4fc73fba123e6593a9cc94d95a9325f2eee550e1e1270a7d002398586d4db2a3'
         AND count_if(_source_name <> 'onisep' OR _snapshot <> '20261109' OR _ingested_at IS NULL) = 0
         AND min(_source_row) = 1 AND max(_source_row) = count(*)
FROM career_intelligence.bronze.onisep_fiches_formations
UNION ALL
SELECT 'formations_initiales',
       count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = '355d7dd55f37affa8c19329eb1c0358bafa6da0abb0b5ba87c61dc74e5fe32e8'
         AND count_if(_source_name <> 'onisep' OR _snapshot <> '20261109' OR _ingested_at IS NULL) = 0
         AND min(_source_row) = 1 AND max(_source_row) = count(*)
FROM career_intelligence.bronze.onisep_formations_initiales;

-- 5. XML fragments are parseable and keep the relationship identifiers (read-only checks,
--    no ROME join): ROME codes in fiches_metiers, MET ids in fiches_formations.
SELECT
  (SELECT count_if(romesV3 LIKE '<romesV3%' ) = count(*) FROM career_intelligence.bronze.onisep_fiches_metiers)   AS check_romes_fragment,
  (SELECT count_if(size(xpath(romesV3, '/romesV3/romeV3/text()')) > 0)
     FROM career_intelligence.bronze.onisep_fiches_metiers) = 931                                                  AS check_metiers_with_rome_code,
  (SELECT count(DISTINCT m) FROM career_intelligence.bronze.onisep_fiches_formations
     LATERAL VIEW explode(xpath(metiers_formation, '/metiers_formation/metier/id/text()')) AS m) = 984            AS check_formation_metier_refs,
  (SELECT count(*) FROM (SELECT explode(xpath(metiers_formation, '/metiers_formation/metier/id/text()')) AS m
                         FROM career_intelligence.bronze.onisep_fiches_formations) r
     LEFT ANTI JOIN career_intelligence.bronze.onisep_fiches_metiers f ON f.identifiant = r.m) = 0               AS check_formation_metier_refs_resolve,
  (SELECT count(*) FROM career_intelligence.bronze.onisep_fiches_formations ff
     LEFT ANTI JOIN career_intelligence.bronze.onisep_formations_initiales fi
     ON regexp_extract(fi.url_et_id_onisep, 'FOR\\.[0-9]+', 0) = ff.identifiant) = 0                               AS check_fiches_in_catalogue;

-- 6. Sample
SELECT identifiant, nom_metier, romesV3, left(accroche_metier, 60) AS accroche, _snapshot, _source_row
FROM career_intelligence.bronze.onisep_fiches_metiers ORDER BY _source_row LIMIT 3;
