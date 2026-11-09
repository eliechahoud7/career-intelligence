-- =============================================================================
-- Verification for the Phase 13a DARES Bronze tables. Every check_* must be TRUE.
-- =============================================================================

-- 1. FAP 2021 nomenclature: counts, keys, formats, one official parent per code
SELECT
  count(*)                                                              AS rows_nomenclature,
  count(*) = 341
    AND count(*) = (SELECT count(*) FROM parquet.`/Volumes/career_intelligence/bronze/landing/dares/fap2021_nomenclature/20240430/parquet/dares_fap2021_nomenclature.parquet`)
                                                                        AS check_rows,
  count(DISTINCT code_fap_341) = 341 AND count(DISTINCT code_fap_228) = 228
    AND count(DISTINCT code_fap_86) = 86 AND count(DISTINCT code_fap_22) = 22 AS check_distinct_levels,
  count_if(code_fap_22 IS NULL OR code_fap_86 IS NULL OR code_fap_228 IS NULL OR code_fap_341 IS NULL
           OR libelle_fap_22 IS NULL OR libelle_fap_86 IS NULL OR libelle_fap_228 IS NULL OR libelle_fap_341 IS NULL
           OR code_fap_341 = '' OR libelle_fap_341 = '') = 0           AS check_no_null_or_empty,
  count_if(NOT code_fap_22 RLIKE '^[A-Z]$' OR NOT code_fap_86 RLIKE '^[A-Z][0-9A-Z][A-Z]$'
           OR NOT code_fap_228 RLIKE '^[A-Z][0-9A-Z][A-Z][0-9]{2}$'
           OR NOT code_fap_341 RLIKE '^[A-Z][0-9A-Z][A-Z][0-9]{2}[a-z]?$') = 0 AS check_code_formats,
  (SELECT max(n) FROM (SELECT code_fap_228, count(DISTINCT code_fap_86) n FROM career_intelligence.bronze.dares_fap2021_nomenclature GROUP BY 1)) = 1
    AND (SELECT max(n) FROM (SELECT code_fap_86, count(DISTINCT code_fap_22) n FROM career_intelligence.bronze.dares_fap2021_nomenclature GROUP BY 1)) = 1
                                                                        AS check_single_parents
FROM career_intelligence.bronze.dares_fap2021_nomenclature;

-- 2. Readme dump: 27 sheet rows, one qualification header, exactly 10 classes 0-9
SELECT
  count(*) = 27                                                         AS check_rows_readme,
  count_if(col_a = 'Code de la qualification' AND col_b = 'Intitulé de la qualification'
           AND col_c = 'PCS correspondantes') = 1                       AS check_qualification_header,
  count_if(col_a RLIKE '^[0-9]$') = 10
    AND count(DISTINCT CASE WHEN col_a RLIKE '^[0-9]$' THEN col_a END) = 10 AS check_ten_classes,
  min(_source_row) = 1 AND max(_source_row) = 27                        AS check_sheet_rows
FROM career_intelligence.bronze.dares_rome_qualif_fap2021_lisez_moi;

-- 3. Schema: source columns STRING, 12 lineage columns
SELECT table_name,
       count_if(column_name NOT LIKE '\\_%')                                AS source_columns,
       count_if(column_name NOT LIKE '\\_%' AND data_type <> 'STRING') = 0  AS check_source_strings,
       count_if(column_name LIKE '\\_%') = 12                               AS check_lineage_columns
FROM career_intelligence.information_schema.columns
WHERE table_schema = 'bronze' AND table_name IN ('dares_fap2021_nomenclature', 'dares_rome_qualif_fap2021_lisez_moi')
GROUP BY table_name ORDER BY table_name;
-- Expected source columns: dares_fap2021_nomenclature 8, dares_rome_qualif_fap2021_lisez_moi 7

-- 4. Lineage: pinned checksums, complete lineage
SELECT 'dares_fap2021_nomenclature' AS t,
       count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = '9c6b5f2148d8273fcfa2af7fc85345faa7b2a1518c9cc55ad0d01d1ae48b6e8d'
         AND count_if(_source_url IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _ingested_at IS NULL) = 0
         AND min(_source_row) = 2 AND max(_source_row) = count(*) + 1 AS check_lineage
FROM career_intelligence.bronze.dares_fap2021_nomenclature
UNION ALL
SELECT 'dares_rome_qualif_fap2021_lisez_moi',
       count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = 'e06876eb1798a616f9308b54c5dbea7d1cfc502eb54751111dca76a46ec3cdec'
         AND count_if(_source_url IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _ingested_at IS NULL) = 0
FROM career_intelligence.bronze.dares_rome_qualif_fap2021_lisez_moi;

-- 5. Licence properties (expect UNCONFIRMED)
SHOW TBLPROPERTIES career_intelligence.bronze.dares_fap2021_nomenclature ('source.license');
SHOW TBLPROPERTIES career_intelligence.bronze.dares_rome_qualif_fap2021_lisez_moi ('source.license');
