-- =============================================================================
-- Verification for career_intelligence.bronze.dares_rome_qualif_fap2021 (snapshot 20261109).
-- Expected values come from the local validation run (rome_qualif_fap2021.manifest.json).
-- Every check_* column must be TRUE. Read-only: no joins to BMO, no use of code_rome_parent.
-- =============================================================================

-- 1. Rows, uniqueness, nulls/empties, distinct codes
SELECT
  count(*)                                                              AS row_count,
  count(*) = 5320                                                       AS check_rows,
  count(*) = (SELECT count(*) FROM parquet.`/Volumes/career_intelligence/bronze/landing/dares/fap2021/20261109/parquet/rome_qualif_fap2021.parquet`)
                                                                        AS check_rows_vs_staged,
  count(*) = count(DISTINCT ROME, Intitule_ROME, Qualif, FAP341, Intitule_FAP341) AS check_unique_rows,
  count(*) = count(DISTINCT ROME, Qualif)                               AS check_unique_key,
  count_if(ROME IS NULL OR Intitule_ROME IS NULL OR Qualif IS NULL OR FAP341 IS NULL OR Intitule_FAP341 IS NULL
           OR ROME = '' OR Intitule_ROME = '' OR Qualif = '' OR FAP341 = '' OR Intitule_FAP341 = '') = 0
                                                                        AS check_no_null_or_empty,
  count(DISTINCT ROME)                                                  AS distinct_rome,
  count(DISTINCT Qualif)                                                AS distinct_qualif,
  count(DISTINCT FAP341)                                                AS distinct_fap341,
  count(DISTINCT ROME) = 532 AND count(DISTINCT Qualif) = 10 AND count(DISTINCT FAP341) = 337
                                                                        AS check_distinct_counts
FROM career_intelligence.bronze.dares_rome_qualif_fap2021;

-- 2. Qualification structure: every ROME code has exactly the classes 0-9 (class 0 kept)
SELECT
  (SELECT count(*) FROM (SELECT ROME FROM career_intelligence.bronze.dares_rome_qualif_fap2021
     GROUP BY ROME HAVING sort_array(collect_list(Qualif)) <> array('0','1','2','3','4','5','6','7','8','9'))) = 0
                                                                        AS check_ten_classes_per_rome,
  (SELECT count_if(Qualif = '0') FROM career_intelligence.bronze.dares_rome_qualif_fap2021) = 532
                                                                        AS check_class0_kept,
  (SELECT count_if(n > 1) FROM (SELECT ROME, count(DISTINCT FAP341) n FROM career_intelligence.bronze.dares_rome_qualif_fap2021 GROUP BY ROME)) = 282
                                                                        AS check_282_qualification_dependent,
  (SELECT count_if(n = 1) FROM (SELECT ROME, count(DISTINCT FAP341) n FROM career_intelligence.bronze.dares_rome_qualif_fap2021 GROUP BY ROME)) = 250
                                                                        AS check_250_single_family;

-- 3. Identifiers preserved as text (formats, leading zeros) and labels consistent per code
SELECT
  count_if(NOT ROME RLIKE '^[A-N][0-9]{4}$') = 0                        AS check_rome_format,
  count_if(NOT FAP341 RLIKE '^[A-Z][0-9A-Z][A-Z][0-9]{2}[a-z]?$') = 0   AS check_fap341_format,
  count_if(NOT Qualif RLIKE '^[0-9]$') = 0                              AS check_qualif_format,
  (SELECT max(n) FROM (SELECT ROME, count(DISTINCT Intitule_ROME) n FROM career_intelligence.bronze.dares_rome_qualif_fap2021 GROUP BY ROME)) = 1
  AND (SELECT max(n) FROM (SELECT FAP341, count(DISTINCT Intitule_FAP341) n FROM career_intelligence.bronze.dares_rome_qualif_fap2021 GROUP BY FAP341)) = 1
                                                                        AS check_one_label_per_code,
  count_if(Intitule_FAP341 RLIKE '\\x{00A0}$') = 77                     AS check_source_whitespace_untouched
FROM career_intelligence.bronze.dares_rome_qualif_fap2021;

-- 4. Schema: 5 source columns STRING + 13 lineage columns
SELECT
  count_if(column_name IN ('ROME','Intitule_ROME','Qualif','FAP341','Intitule_FAP341') AND data_type = 'STRING') = 5
                                                                        AS check_source_columns_string,
  count_if(column_name LIKE '\\_%') = 13                                AS check_lineage_columns
FROM career_intelligence.information_schema.columns
WHERE table_schema = 'bronze' AND table_name = 'dares_rome_qualif_fap2021';

-- 5. Lineage: manual download recorded, one checksum (= pinned sha256), row numbers 1..n
SELECT
  count(DISTINCT _source_sha256) = 1
    AND min(_source_sha256) = 'aa4fc948a59309879a297ed40165fcf1f67e1cbd92a6ca7d8dbfce8429f62d13' AS check_checksum,
  count_if(_download_method <> 'manual' OR _downloaded_on <> '2026-11-09' OR _snapshot <> '20261109'
           OR _source_encoding <> 'cp1252' OR _source_url IS NULL OR _run_id IS NULL OR _ingested_at IS NULL) = 0
                                                                        AS check_lineage_values,
  min(_source_row) = 1 AND max(_source_row) = count(*) AND count(DISTINCT _source_row) = count(*)
                                                                        AS check_source_rows
FROM career_intelligence.bronze.dares_rome_qualif_fap2021;

-- 6. Licence recorded as unconfirmed (expect UNCONFIRMED)
SHOW TBLPROPERTIES career_intelligence.bronze.dares_rome_qualif_fap2021 ('source.license');

-- 7. Sample: a qualification-dependent ROME code
SELECT ROME, Qualif, FAP341, Intitule_FAP341 FROM career_intelligence.bronze.dares_rome_qualif_fap2021
WHERE ROME = 'A1204' ORDER BY Qualif;
