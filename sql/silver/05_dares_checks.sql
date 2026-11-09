-- =============================================================================
-- Verification for the Phase 13a DARES Silver tables. Every check_* must be TRUE.
-- =============================================================================

-- 1. Row counts vs Bronze
SELECT
  (SELECT count(*) FROM career_intelligence.silver.fap2021) = 341
    AND (SELECT count(*) FROM career_intelligence.silver.fap2021) = (SELECT count(*) FROM career_intelligence.bronze.dares_fap2021_nomenclature) AS check_rows_fap2021,
  (SELECT count(*) FROM career_intelligence.silver.dares_qualification) = 10                                     AS check_rows_qualification,
  (SELECT count(*) FROM career_intelligence.silver.dares_rome_v3_fap341) = 5320
    AND (SELECT count(*) FROM career_intelligence.silver.dares_rome_v3_fap341) = (SELECT count(*) FROM career_intelligence.bronze.dares_rome_qualif_fap2021) AS check_rows_correspondence;

-- 2. Primary keys: unique and non-null
SELECT
  (SELECT count(*) = count(DISTINCT code_fap341) AND count_if(code_fap341 IS NULL) = 0 FROM career_intelligence.silver.fap2021) AS check_pk_fap2021,
  (SELECT count(*) = count(DISTINCT code_qualification) AND count_if(code_qualification IS NULL) = 0
     FROM career_intelligence.silver.dares_qualification)                                                       AS check_pk_qualification,
  (SELECT count(*) = count(DISTINCT code_rome_v3, code_qualification)
          AND count_if(code_rome_v3 IS NULL OR code_qualification IS NULL OR code_fap341 IS NULL) = 0
     FROM career_intelligence.silver.dares_rome_v3_fap341)                                                      AS check_pk_correspondence;

-- 3. Official hierarchy: one parent per level, all levels resolve, prefix rule agrees (check only)
SELECT
  count(DISTINCT code_fap228) = 228 AND count(DISTINCT code_fap86) = 86 AND count(DISTINCT code_fap22) = 22 AS check_level_counts,
  count_if(code_fap228 IS NULL OR code_fap86 IS NULL OR code_fap22 IS NULL
           OR libelle_fap341 IS NULL OR libelle_fap228 IS NULL OR libelle_fap86 IS NULL OR libelle_fap22 IS NULL) = 0 AS check_parents_and_labels_present,
  (SELECT max(n) FROM (SELECT code_fap228, count(DISTINCT code_fap86, libelle_fap228) n FROM career_intelligence.silver.fap2021 GROUP BY 1)) = 1
    AND (SELECT max(n) FROM (SELECT code_fap86, count(DISTINCT code_fap22, libelle_fap86) n FROM career_intelligence.silver.fap2021 GROUP BY 1)) = 1
    AND (SELECT max(n) FROM (SELECT code_fap22, count(DISTINCT libelle_fap22) n FROM career_intelligence.silver.fap2021 GROUP BY 1)) = 1
                                                                                                                AS check_single_parent_and_label,
  count_if(left(code_fap341, 5) <> code_fap228) = 0                                                            AS check_prefix_rule_agrees,
  count_if(code_fap341 = code_fap228)                                                                           AS fap341_identical_to_fap228
FROM career_intelligence.silver.fap2021;
-- Expected: 162 FAP341 codes are identical to their FAP228 parent

-- 4. Qualification classes: exactly 0-9; labels and PCS equal the archived readme rows
SELECT
  sort_array(collect_list(q.code_qualification)) = array('0','1','2','3','4','5','6','7','8','9')            AS check_ten_classes,
  count_if(q.libelle_qualification IS NULL) = 0                                                                 AS check_labels_present,
  count_if(q.libelle_qualification <> regexp_replace(regexp_replace(b.col_b, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', '')
           OR NOT (q.pcs_correspondantes <=> nullif(regexp_replace(regexp_replace(b.col_c, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) = 0
                                                                                                                AS check_equal_to_readme,
  count_if(q.code_qualification IN ('0', '1') AND (q.pcs_correspondantes IS NOT NULL OR q.codes_pcs IS NOT NULL)) = 0
    AND count_if(q.code_qualification NOT IN ('0', '1') AND q.codes_pcs IS NULL) = 0                            AS check_pcs_only_where_published,
  count_if(size(q.codes_pcs) <> size(split(q.pcs_correspondantes, ','))) = 0
    AND count_if(exists(q.codes_pcs, c -> NOT c RLIKE '^[0-9]{2}[0-9A-Z]{2}$')) = 0                             AS check_pcs_codes_well_formed,
  sum(size(q.codes_pcs))                                                                                        AS pcs_codes_total
FROM career_intelligence.silver.dares_qualification q
JOIN career_intelligence.bronze.dares_rome_qualif_fap2021_lisez_moi b ON b._source_row = q._source_row;
-- Expected PCS codes total: 112 (classes 2-9)

-- 5. Correspondence: identical to Bronze, links resolve, qualification-dependence preserved
SELECT
  (SELECT count(*) FROM career_intelligence.bronze.dares_rome_qualif_fap2021 b
     FULL JOIN career_intelligence.silver.dares_rome_v3_fap341 s
       ON s.code_rome_v3 = b.ROME AND s.code_qualification = b.Qualif AND s.code_fap341 = b.FAP341
     WHERE b.ROME IS NULL OR s.code_rome_v3 IS NULL OR b._source_row <> s._source_row) = 0            AS check_rows_identical_to_bronze,
  (SELECT count(*) FROM career_intelligence.silver.dares_rome_v3_fap341 c
     LEFT ANTI JOIN career_intelligence.silver.fap2021 f ON f.code_fap341 = c.code_fap341) = 0        AS check_fap341_resolve,
  (SELECT count(DISTINCT code_fap341) FROM career_intelligence.silver.dares_rome_v3_fap341) = 337     AS check_337_fap341,
  (SELECT count(*) FROM career_intelligence.silver.dares_rome_v3_fap341 c
     LEFT ANTI JOIN career_intelligence.silver.dares_qualification q ON q.code_qualification = c.code_qualification) = 0 AS check_qualification_resolve,
  (SELECT count(*) FROM (SELECT code_rome_v3 FROM career_intelligence.silver.dares_rome_v3_fap341 GROUP BY 1
     HAVING sort_array(collect_list(code_qualification)) <> array('0','1','2','3','4','5','6','7','8','9'))) = 0
    AND (SELECT count(DISTINCT code_rome_v3) FROM career_intelligence.silver.dares_rome_v3_fap341) = 532  AS check_532_rome_v3_x_10_classes,
  (SELECT count_if(n > 1) FROM (SELECT code_rome_v3, count(DISTINCT code_fap341) n FROM career_intelligence.silver.dares_rome_v3_fap341 GROUP BY 1)) = 282
                                                                                                        AS check_282_qualification_dependent,
  (SELECT max(n) FROM (SELECT code_rome_v3, count(DISTINCT libelle_rome_v3) n FROM career_intelligence.silver.dares_rome_v3_fap341 GROUP BY 1)) = 1
                                                                                                        AS check_one_rome_v3_label;

-- 6. ROME V3 kept separate from ROME 4.0 v62: no 'code_rome' column, V3 marked, no BMO / parent columns
SELECT
  count_if(column_name = 'code_rome') = 0                                                                      AS check_no_code_rome_column,
  count_if(column_name = 'code_rome_v3') = 1                                                                   AS check_code_rome_v3_present,
  count_if(column_name IN ('code_rome_parent', 'code_metier_bmo') OR column_name LIKE 'nb\\_projets%') = 0    AS check_no_parent_or_bmo_columns,
  count_if(column_name LIKE 'libelle\\_fap%') = 0                                                              AS check_fap_labels_not_duplicated
FROM career_intelligence.information_schema.columns
WHERE table_schema = 'silver' AND table_name = 'dares_rome_v3_fap341';

-- 7. Normalised text: no empty strings, no edge whitespace, no double spaces / NBSP / tabs in labels
SELECT
  (SELECT count_if(libelle_fap341 RLIKE '^\\s|\\s$|\\s{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_fap228 RLIKE '^\\s|\\s$|\\s{2,}|[\\t\\x{00A0}\\x{202F}]'
                   OR libelle_fap86 RLIKE '^\\s|\\s$|\\s{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_fap22 RLIKE '^\\s|\\s$|\\s{2,}|[\\t\\x{00A0}\\x{202F}]'
                   OR libelle_fap341 = '' OR libelle_fap228 = '') FROM career_intelligence.silver.fap2021)
  + (SELECT count_if(libelle_qualification RLIKE '^\\s|\\s$|\\s{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_qualification = ''
                     OR pcs_correspondantes RLIKE '^\\s|\\s$|\\s{2,}' OR pcs_correspondantes = ''
                     OR exists(codes_pcs, c -> c = '' OR c <> trim(c))) FROM career_intelligence.silver.dares_qualification)
  + (SELECT count_if(libelle_rome_v3 RLIKE '^\\s|\\s$|\\s{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_rome_v3 = '' OR code_rome_v3 = '' OR code_fap341 = '')
       FROM career_intelligence.silver.dares_rome_v3_fap341) = 0                                               AS check_normalised_text;

-- 8. Lineage complete, checksums = pinned Bronze values
SELECT
  (SELECT count_if(_source_url IS NULL OR _run_id IS NULL OR _ingested_at IS NULL OR _source_row IS NULL) = 0
          AND count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = '9c6b5f2148d8273fcfa2af7fc85345faa7b2a1518c9cc55ad0d01d1ae48b6e8d'
     FROM career_intelligence.silver.fap2021)                                                                   AS check_lineage_fap2021,
  (SELECT count_if(_source_url IS NULL OR _run_id IS NULL OR _ingested_at IS NULL OR _source_row IS NULL) = 0
          AND count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = 'e06876eb1798a616f9308b54c5dbea7d1cfc502eb54751111dca76a46ec3cdec'
     FROM career_intelligence.silver.dares_qualification)                                                       AS check_lineage_qualification,
  (SELECT count_if(_source_url IS NULL OR _run_id IS NULL OR _ingested_at IS NULL OR _source_row IS NULL) = 0
          AND count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = 'aa4fc948a59309879a297ed40165fcf1f67e1cbd92a6ca7d8dbfce8429f62d13'
     FROM career_intelligence.silver.dares_rome_v3_fap341)                                                      AS check_lineage_correspondence;

-- 9. Licence properties (expect UNCONFIRMED)
SHOW TBLPROPERTIES career_intelligence.silver.fap2021 ('source.license');
SHOW TBLPROPERTIES career_intelligence.silver.dares_qualification ('source.license');
SHOW TBLPROPERTIES career_intelligence.silver.dares_rome_v3_fap341 ('source.license');
