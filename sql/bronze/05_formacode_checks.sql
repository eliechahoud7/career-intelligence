-- =============================================================================
-- Verification for the Formacode Bronze tables (snapshot rome_v62_formacode_v14).
-- Expected values come from the local validation run (manifest). Every check_* must be TRUE.
-- Read-only; no NSF/ONISEP integration.
-- =============================================================================

-- 1. Correspondence: counts, uniqueness, nulls, formats, vs staged Parquet
SELECT
  count(*)                                                            AS rows_corr,
  count(*) = 5958                                                     AS check_rows,
  count(*) = (SELECT count(*) FROM parquet.`/Volumes/career_intelligence/bronze/landing/formacode/rome_v62_formacode_v14/parquet/rome_formacode_v14.parquet`)
                                                                      AS check_rows_vs_staged,
  count(DISTINCT code_rome) = 1923                                    AS check_1923_rome,
  count(DISTINCT code_formacode) = 1220                               AS check_1220_formacode,
  count(*) = count(DISTINCT code_rome, code_formacode)                AS check_unique_pairs,
  count_if(code_rome IS NULL OR libelle_fiche_rome IS NULL OR code_ogr_rome IS NULL
           OR code_formacode IS NULL OR libelle_formacode IS NULL) = 0 AS check_no_nulls,
  count_if(NOT code_rome RLIKE '^[A-N][0-9]{4}$' OR NOT code_formacode RLIKE '^[0-9]{5}$'
           OR NOT code_ogr_rome RLIKE '^[0-9]+$') = 0                 AS check_identifier_formats
FROM career_intelligence.bronze.rome_formacode_v14;

-- 2. Many-to-many preserved (no collapsing, no weights)
SELECT
  (SELECT count_if(n > 1) FROM (SELECT code_rome, count(*) n FROM career_intelligence.bronze.rome_formacode_v14 GROUP BY 1)) AS rome_with_several_formacodes,
  (SELECT count_if(n > 1) FROM (SELECT code_formacode, count(*) n FROM career_intelligence.bronze.rome_formacode_v14 GROUP BY 1)) AS formacodes_with_several_rome,
  (SELECT count_if(n > 1) FROM (SELECT code_rome, count(*) n FROM career_intelligence.bronze.rome_formacode_v14 GROUP BY 1)) = 1354
  AND (SELECT count_if(n > 1) FROM (SELECT code_formacode, count(*) n FROM career_intelligence.bronze.rome_formacode_v14 GROUP BY 1)) = 844
                                                                      AS check_many_to_many;

-- 3. Compatibility with ROME v62: every code (and OGR, label) matches silver.rome_metier
SELECT
  (SELECT count(DISTINCT c.code_rome) FROM career_intelligence.bronze.rome_formacode_v14 c
     JOIN career_intelligence.silver.rome_metier m ON m.code_rome = c.code_rome) = 1923      AS check_rome_codes_in_v62,
  (SELECT count(*) FROM career_intelligence.silver.rome_metier m WHERE NOT EXISTS
     (SELECT 1 FROM career_intelligence.bronze.rome_formacode_v14 c WHERE c.code_rome = m.code_rome)) = 0
                                                                                             AS check_every_v62_code_covered,
  (SELECT count(*) FROM career_intelligence.bronze.rome_formacode_v14 c
     JOIN career_intelligence.silver.rome_metier m ON m.code_rome = c.code_rome
     WHERE m.code_ogr <> c.code_ogr_rome OR m.libelle_rome <> c.libelle_fiche_rome) = 0      AS check_ogr_and_label_match;

-- 4. Every correspondence Formacode resolves to an official V14 descriptor
SELECT
  (SELECT count(DISTINCT c.code_formacode) FROM career_intelligence.bronze.rome_formacode_v14 c
     JOIN career_intelligence.bronze.formacode_v14_descripteurs d ON d.code_du_terme = c.code_formacode) = 1220
                                                                                             AS check_formacodes_resolve,
  (SELECT count(*) FROM career_intelligence.bronze.rome_formacode_v14 c
     LEFT ANTI JOIN career_intelligence.bronze.formacode_v14_descripteurs d ON d.code_du_terme = c.code_formacode) = 0
                                                                                             AS check_no_unresolved_links,
  (SELECT count(DISTINCT code_formacode) FROM (
     SELECT code_formacode, count(DISTINCT libelle_formacode) n FROM career_intelligence.bronze.rome_formacode_v14
     GROUP BY 1 HAVING n > 1)) AS formacodes_with_label_variants_in_correspondence;
-- Expected label variants: 73 (accented / unaccented, kept as published)

-- 5. Thesaurus: 2,775 unique descriptors, 14 unique domains, identifiers well-formed
SELECT
  (SELECT count(*) FROM career_intelligence.bronze.formacode_v14_descripteurs) = 2775        AS check_2775_descripteurs,
  (SELECT count(*) = count(DISTINCT code_du_terme) AND count_if(NOT code_du_terme RLIKE '^[0-9]{5}$') = 0
          AND count_if(descripteur_en_typo_riche IS NULL OR champ_semantique IS NULL) = 0
     FROM career_intelligence.bronze.formacode_v14_descripteurs)                             AS check_descripteurs_keys,
  (SELECT count(*) FROM career_intelligence.bronze.formacode_v14_grands_domaines) = 14      AS check_14_domaines,
  (SELECT count(*) = count(DISTINCT code_du_terme) AND count_if(NOT code_du_terme RLIKE '^[0-9]{5}$') = 0
     FROM career_intelligence.bronze.formacode_v14_grands_domaines)                          AS check_domaines_keys,
  (SELECT count(DISTINCT champ_semantique) FROM career_intelligence.bronze.formacode_v14_descripteurs) AS distinct_semantic_fields;

-- 6. Schema: all source columns STRING; 12 lineage columns per table
SELECT table_name,
       count_if(column_name NOT LIKE '\\_%')                                AS source_columns,
       count_if(column_name NOT LIKE '\\_%' AND data_type <> 'STRING') = 0  AS check_source_strings,
       count_if(column_name LIKE '\\_%') = 12                               AS check_lineage_columns
FROM career_intelligence.information_schema.columns
WHERE table_schema = 'bronze' AND table_name IN ('rome_formacode_v14', 'formacode_v14_descripteurs', 'formacode_v14_grands_domaines')
GROUP BY table_name ORDER BY table_name;
-- Expected source columns: formacode_v14_descripteurs 14, formacode_v14_grands_domaines 6, rome_formacode_v14 5

-- 7. Lineage: pinned checksum, complete lineage, Excel row numbers 2..n+1
SELECT 'rome_formacode_v14' AS t,
       count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = '1f1f144c25f6776b336fe78bc252ab2c23e715b222b191ef829f15264ca68d12'
         AND count_if(_source_url IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _ingested_at IS NULL) = 0
         AND min(_source_row) = 2 AND max(_source_row) = count(*) + 1 AS check_lineage
FROM career_intelligence.bronze.rome_formacode_v14
UNION ALL
SELECT 'formacode_v14_descripteurs',
       count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = '02f248f08185b8bf87e2088fee26068e6ec558141adfef3c4f6dd04a0561207d'
         AND count_if(_source_url IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _ingested_at IS NULL) = 0
         AND min(_source_row) = 2 AND max(_source_row) = count(*) + 1
FROM career_intelligence.bronze.formacode_v14_descripteurs
UNION ALL
SELECT 'formacode_v14_grands_domaines',
       count(DISTINCT _source_sha256) = 1 AND min(_source_sha256) = 'f713514f3df9bd18476ee64de3c971f2e7c392d9e7b5c4b3255c95efbea43b47'
         AND count_if(_source_url IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _ingested_at IS NULL) = 0
         AND min(_source_row) = 2 AND max(_source_row) = count(*) + 1
FROM career_intelligence.bronze.formacode_v14_grands_domaines;

-- 8. Licence properties
SHOW TBLPROPERTIES career_intelligence.bronze.rome_formacode_v14 ('source.license');
SHOW TBLPROPERTIES career_intelligence.bronze.formacode_v14_descripteurs ('source.license');
SHOW TBLPROPERTIES career_intelligence.bronze.formacode_v14_grands_domaines ('source.license');
