-- =============================================================================
-- Verification for the Formacode Silver tables (snapshot rome_v62_formacode_v14).
-- Partly GENERATED (text, lineage, licence). Every check_* must be TRUE.
-- Expected values verified against Bronze during the Phase 12 inspection.
-- =============================================================================

-- 1. Row counts vs Bronze (TA: Bronze items minus self-references, D1)
WITH ta AS (
  SELECT b.code_du_terme AS a, regexp_extract(t.item, ' - ([0-9]{5})$', 1) AS c
  FROM career_intelligence.bronze.formacode_v14_descripteurs b
  LATERAL VIEW explode(split(b.ta_termes_associes, '###')) t AS item
  WHERE b.ta_termes_associes IS NOT NULL)
SELECT
  (SELECT count(*) FROM career_intelligence.silver.formacode_grand_domaine) = (SELECT count(*) FROM career_intelligence.bronze.formacode_v14_grands_domaines)
    AND (SELECT count(*) FROM career_intelligence.silver.formacode_grand_domaine) = 14                                   AS check_rows_grand_domaine,
  (SELECT count(*) FROM career_intelligence.silver.formacode) = (SELECT count(*) FROM career_intelligence.bronze.formacode_v14_descripteurs)
    AND (SELECT count(*) FROM career_intelligence.silver.formacode) = 2775                                               AS check_rows_formacode,
  (SELECT count(*) FROM career_intelligence.silver.rome_metier_formacode) = (SELECT count(*) FROM career_intelligence.bronze.rome_formacode_v14)
    AND (SELECT count(*) FROM career_intelligence.silver.rome_metier_formacode) = 5958                                   AS check_rows_rome_metier_formacode,
  (SELECT count(*) FROM ta) AS bronze_ta_items,
  (SELECT count_if(a = c) FROM ta) AS bronze_ta_self_references,
  (SELECT count(*) FROM career_intelligence.silver.formacode_terme_associe) = (SELECT count_if(a <> c) FROM ta)
    AND (SELECT count(*) FROM career_intelligence.silver.formacode_terme_associe) = 3166                                 AS check_rows_terme_associe;
-- Expected: TA items 4655 = 3166 related + 1489 self-references

-- 2. Primary keys: unique and non-null
SELECT
  (SELECT count(*) = count(DISTINCT code_grand_domaine) AND count_if(code_grand_domaine IS NULL) = 0 FROM career_intelligence.silver.formacode_grand_domaine) AS check_pk_grand_domaine,
  (SELECT count(*) = count(DISTINCT code_formacode) AND count_if(code_formacode IS NULL) = 0 FROM career_intelligence.silver.formacode)                    AS check_pk_formacode,
  (SELECT count(*) = count(DISTINCT code_formacode, code_formacode_associe)
          AND count_if(code_formacode IS NULL OR code_formacode_associe IS NULL OR code_formacode_associe = '') = 0
     FROM career_intelligence.silver.formacode_terme_associe)                                                                                            AS check_pk_terme_associe,
  (SELECT count(*) = count(DISTINCT code_rome, code_formacode) AND count_if(code_rome IS NULL OR code_formacode IS NULL) = 0
     FROM career_intelligence.silver.rome_metier_formacode)                                                                                              AS check_pk_rome_metier_formacode,
  (SELECT count_if(code_formacode = code_formacode_associe) FROM career_intelligence.silver.formacode_terme_associe) = 0                                AS check_no_self_reference;

-- 3. Source identifiers preserved (both directions): codes, domains, and the 5,958 pairs
SELECT
  (SELECT count(*) FROM career_intelligence.bronze.formacode_v14_descripteurs b FULL JOIN career_intelligence.silver.formacode s ON s.code_formacode = b.code_du_terme
     WHERE b.code_du_terme IS NULL OR s.code_formacode IS NULL OR b._source_row <> s._source_row) = 0             AS check_ids_formacode,
  (SELECT count(*) FROM career_intelligence.bronze.formacode_v14_grands_domaines b FULL JOIN career_intelligence.silver.formacode_grand_domaine s ON s.code_grand_domaine = b.code_du_terme
     WHERE b.code_du_terme IS NULL OR s.code_grand_domaine IS NULL) = 0                                             AS check_ids_grand_domaine,
  (SELECT count(*) FROM career_intelligence.bronze.rome_formacode_v14 b FULL JOIN career_intelligence.silver.rome_metier_formacode s
     ON s.code_rome = b.code_rome AND s.code_formacode = b.code_formacode
     WHERE b.code_rome IS NULL OR s.code_rome IS NULL OR b._source_row <> s._source_row) = 0                      AS check_pairs_identical_to_bronze;

-- 4. Foreign keys
SELECT
  (SELECT count(*) FROM career_intelligence.silver.rome_metier_formacode r LEFT ANTI JOIN career_intelligence.silver.rome_metier m ON m.code_rome = r.code_rome) = 0         AS check_fk_rome,
  (SELECT count(DISTINCT code_rome) FROM career_intelligence.silver.rome_metier_formacode) = 1923
    AND (SELECT count(*) FROM career_intelligence.silver.rome_metier m LEFT ANTI JOIN career_intelligence.silver.rome_metier_formacode r ON r.code_rome = m.code_rome) = 0    AS check_all_1923_rome_covered,
  (SELECT count(*) FROM career_intelligence.bronze.rome_formacode_v14 b JOIN career_intelligence.silver.rome_metier m ON m.code_rome = b.code_rome
     WHERE m.code_ogr <> b.code_ogr_rome OR m.libelle_rome <> b.libelle_fiche_rome) = 0                                      AS check_ogr_and_rome_label,
  (SELECT count(*) FROM career_intelligence.silver.rome_metier_formacode r LEFT ANTI JOIN career_intelligence.silver.formacode f ON f.code_formacode = r.code_formacode) = 0 AS check_fk_formacode,
  (SELECT count(DISTINCT code_formacode) FROM career_intelligence.silver.rome_metier_formacode) = 1220                                              AS check_1220_formacodes,
  (SELECT count(*) FROM career_intelligence.silver.formacode c LEFT ANTI JOIN career_intelligence.silver.formacode p ON p.code_formacode = c.code_formacode_parent
     WHERE c.code_formacode_parent IS NOT NULL) = 0                                                                          AS check_fk_parent,
  (SELECT count(*) FROM career_intelligence.silver.formacode f LEFT ANTI JOIN career_intelligence.silver.formacode_grand_domaine g ON g.code_grand_domaine = f.code_grand_domaine) = 0
    AND (SELECT count_if(code_grand_domaine IS NULL) FROM career_intelligence.silver.formacode) = 0                                                AS check_fk_domaine,
  (SELECT count(*) FROM career_intelligence.silver.formacode_terme_associe a LEFT ANTI JOIN career_intelligence.silver.formacode f ON f.code_formacode = a.code_formacode) = 0 AS check_fk_terme_associe_source;

-- 5. Related-term targets: resolved vs external (annex lists), flag consistent with a recount
SELECT
  count_if(terme_associe_dans_descripteurs)                         AS resolved_targets,
  count_if(NOT terme_associe_dans_descripteurs)                     AS external_targets,
  count(DISTINCT CASE WHEN NOT terme_associe_dans_descripteurs THEN code_formacode_associe END) AS external_distinct_codes,
  count_if(NOT terme_associe_dans_descripteurs) = 76 AND count_if(terme_associe_dans_descripteurs) = 3090 AS check_external_kept_and_flagged,
  (SELECT count(*) FROM career_intelligence.silver.formacode_terme_associe a LEFT JOIN career_intelligence.silver.formacode f ON f.code_formacode = a.code_formacode_associe
     WHERE a.terme_associe_dans_descripteurs <> (f.code_formacode IS NOT NULL)) = 0      AS check_flag_consistent,
  count_if(libelle_associe_source IS NULL) = 0                      AS check_external_labels_kept
FROM career_intelligence.silver.formacode_terme_associe;

-- 6. Tree rules (broader / narrower, depth, semantic field, domain)
SELECT
  (SELECT count_if(code_formacode_parent IS NULL) FROM career_intelligence.silver.formacode) = 65
    AND (SELECT count_if(niveau = 1) FROM career_intelligence.silver.formacode) = 65
    AND (SELECT count_if((code_formacode_parent IS NULL) <> (niveau = 1)) FROM career_intelligence.silver.formacode) = 0          AS check_65_roots,
  (SELECT count(DISTINCT code_champ_semantique) FROM career_intelligence.silver.formacode WHERE niveau = 1) = 65
    AND (SELECT count(DISTINCT code_champ_semantique) FROM career_intelligence.silver.formacode) = 65                            AS check_one_root_per_field,
  (SELECT count(*) FROM career_intelligence.silver.formacode c JOIN career_intelligence.silver.formacode p ON p.code_formacode = c.code_formacode_parent
     WHERE c.niveau <> p.niveau + 1 OR NOT startswith(c.code_arborescence, p.code_arborescence)
        OR c.code_champ_semantique <> p.code_champ_semantique OR c.code_grand_domaine <> p.code_grand_domaine) = 0 AS check_parent_consistency,
  (SELECT max(niveau) FROM career_intelligence.silver.formacode) = 6 AND (SELECT min(niveau) FROM career_intelligence.silver.formacode) = 1            AS check_depth_1_to_6,
  (SELECT count(*) FROM career_intelligence.silver.formacode f JOIN career_intelligence.silver.formacode_grand_domaine g ON g.code_grand_domaine = f.code_grand_domaine
     WHERE left(f.code_arborescence, 1) <> left(g.code_arborescence, 1)) = 0                               AS check_domain_matches_tree_letter,
  (SELECT count(*) FROM career_intelligence.silver.formacode f LEFT JOIN (SELECT code_formacode_parent, count(*) n FROM career_intelligence.silver.formacode
     WHERE code_formacode_parent IS NOT NULL GROUP BY 1) k ON k.code_formacode_parent = f.code_formacode
     WHERE f.nb_termes_specifiques <> coalesce(k.n, 0)) = 0                                                AS check_narrower_terms_derivable,
  (SELECT count_if(NOT est_terme_feuille) FROM career_intelligence.silver.formacode) = 689
    AND (SELECT count_if(est_terme_feuille) FROM career_intelligence.silver.formacode) = 2086                                     AS check_689_broad_2086_leaf,
  -- every top term listed under a domain in Bronze is a niveau-1 formacode of that domain, and vice versa
  (SELECT count(*) FROM (SELECT b.code_du_terme AS dom, regexp_extract(t.item, ' - ([0-9]{5})$', 1) AS top
                         FROM career_intelligence.bronze.formacode_v14_grands_domaines b
                         LATERAL VIEW explode(split(b.ts_termes_specifiques, '###')) t AS item) x
     FULL JOIN (SELECT code_grand_domaine AS dom, code_formacode AS top FROM career_intelligence.silver.formacode WHERE niveau = 1) y
       ON y.dom = x.dom AND y.top = x.top
     WHERE x.top IS NULL OR y.top IS NULL) = 0                                                             AS check_domain_top_terms;

-- 7. Official labels; many-to-many and broad + leaf terms preserved in the occupation link
SELECT
  (SELECT count(*) FROM career_intelligence.silver.formacode s JOIN career_intelligence.bronze.formacode_v14_descripteurs b ON b.code_du_terme = s.code_formacode
     WHERE s.libelle_formacode <> regexp_replace(regexp_replace(b.descripteur_en_typo_riche, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', '')) = 0 AS check_official_labels,
  (SELECT count(*) FROM information_schema.columns WHERE table_schema = 'silver' AND table_name = 'rome_metier_formacode'
     AND column_name LIKE 'libelle%') = 0                                                                   AS check_no_correspondence_labels,
  (SELECT count_if(n > 1) FROM (SELECT code_rome, count(*) n FROM career_intelligence.silver.rome_metier_formacode GROUP BY 1)) = 1354
    AND (SELECT count_if(n > 1) FROM (SELECT code_formacode, count(*) n FROM career_intelligence.silver.rome_metier_formacode GROUP BY 1)) = 844
    AND (SELECT max(n) FROM (SELECT code_rome, count(*) n FROM career_intelligence.silver.rome_metier_formacode GROUP BY 1)) = 95
    AND (SELECT max(n) FROM (SELECT code_formacode, count(*) n FROM career_intelligence.silver.rome_metier_formacode GROUP BY 1)) = 79 AS check_many_to_many,
  (SELECT count(DISTINCT r.code_formacode) FROM career_intelligence.silver.rome_metier_formacode r JOIN career_intelligence.silver.formacode f USING (code_formacode) WHERE NOT f.est_terme_feuille) = 445
    AND (SELECT count(DISTINCT r.code_formacode) FROM career_intelligence.silver.rome_metier_formacode r JOIN career_intelligence.silver.formacode f USING (code_formacode) WHERE f.est_terme_feuille) = 775
                                                                                                            AS check_445_broad_775_leaf,
  (SELECT count(DISTINCT x.code_rome) FROM career_intelligence.silver.rome_metier_formacode x JOIN career_intelligence.silver.formacode c ON c.code_formacode = x.code_formacode
     JOIN career_intelligence.silver.rome_metier_formacode y ON y.code_rome = x.code_rome AND y.code_formacode = c.code_formacode_parent) = 559 AS check_parent_child_pairs_kept;

-- 8. Normalised text: no empty strings, no edge whitespace; labels without double spaces /
--    tabs / NBSP (long notes keep internal typography); array items normalised; D3 applied
SELECT sum(empty_strings) AS empty_strings, sum(edge_whitespace) AS edge_whitespace, sum(label_ws_issues) AS label_ws_issues,
       sum(empty_strings) + sum(edge_whitespace) + sum(label_ws_issues) = 0 AS check_normalised_text
FROM (
  SELECT 'formacode' AS t, count_if(code_formacode = '' OR libelle_formacode = '' OR libelle_majuscules = '' OR code_champ_semantique = '' OR libelle_champ_semantique = '' OR code_formacode_parent = '' OR code_grand_domaine = '' OR code_arborescence = '' OR note_explication = '' OR note_application = '') AS empty_strings, count_if(code_formacode RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR libelle_formacode RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR libelle_majuscules RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR code_champ_semantique RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR libelle_champ_semantique RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR code_formacode_parent RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR code_grand_domaine RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR code_arborescence RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR note_explication RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR note_application RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$') AS edge_whitespace, count_if(code_formacode RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_formacode RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_majuscules RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR code_champ_semantique RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_champ_semantique RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR code_formacode_parent RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR code_grand_domaine RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR code_arborescence RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]') AS label_ws_issues FROM career_intelligence.silver.formacode
  UNION ALL SELECT 'formacode_grand_domaine' AS t, count_if(code_grand_domaine = '' OR libelle_grand_domaine = '' OR libelle_majuscules = '' OR code_arborescence = '' OR note_de_version = '') AS empty_strings, count_if(code_grand_domaine RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR libelle_grand_domaine RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR libelle_majuscules RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR code_arborescence RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR note_de_version RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$') AS edge_whitespace, count_if(code_grand_domaine RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_grand_domaine RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_majuscules RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR code_arborescence RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR note_de_version RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]') AS label_ws_issues FROM career_intelligence.silver.formacode_grand_domaine
  UNION ALL SELECT 'formacode_terme_associe' AS t, count_if(code_formacode = '' OR code_formacode_associe = '' OR libelle_associe_source = '') AS empty_strings, count_if(code_formacode RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR code_formacode_associe RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR libelle_associe_source RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$') AS edge_whitespace, count_if(code_formacode RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR code_formacode_associe RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR libelle_associe_source RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]') AS label_ws_issues FROM career_intelligence.silver.formacode_terme_associe
  UNION ALL SELECT 'rome_metier_formacode' AS t, count_if(code_rome = '' OR code_formacode = '') AS empty_strings, count_if(code_rome RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$' OR code_formacode RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$') AS edge_whitespace, count_if(code_rome RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]' OR code_formacode RLIKE '[\\s\\x{00A0}\\x{202F}]{2,}|[\\t\\x{00A0}\\x{202F}]') AS label_ws_issues FROM career_intelligence.silver.rome_metier_formacode
);

SELECT
  (SELECT count_if(exists(synonymes, s -> s IS NULL OR s RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$|[\\s\\x{00A0}\\x{202F}]{2,}')
                 OR exists(synonymes_metier, s -> s IS NULL OR s RLIKE '^[\\s\\x{00A0}\\x{202F}]|[\\s\\x{00A0}\\x{202F}]$|[\\s\\x{00A0}\\x{202F}]{2,}')) FROM career_intelligence.silver.formacode) = 0 AS check_array_items_normalised,
  (SELECT count_if(note_de_version = 'null') FROM career_intelligence.silver.formacode_grand_domaine) = 0                                         AS check_d3_null_literal,
  (SELECT count(*) FROM information_schema.columns WHERE table_schema = 'silver' AND table_name = 'formacode'
     AND column_name IN ('note_de_version', 'ex_synonyme_v_1')) = 0                                                         AS check_d4_empty_columns_not_carried;

-- 9. Lineage complete, one checksum per table (= pinned Bronze checksums)
SELECT count(*) AS tables, sum(incomplete) AS incomplete_rows, max(shas) AS max_checksums,
       sum(incomplete) = 0 AND max(shas) = 1
       AND count_if(sha IN ('02f248f08185b8bf87e2088fee26068e6ec558141adfef3c4f6dd04a0561207d',
                            'f713514f3df9bd18476ee64de3c971f2e7c392d9e7b5c4b3255c95efbea43b47',
                            '1f1f144c25f6776b336fe78bc252ab2c23e715b222b191ef829f15264ca68d12')) = 4 AS check_lineage
FROM (
  SELECT 'formacode_grand_domaine' AS t, count_if(_source_name IS NULL OR _source_resource IS NULL OR _dataset IS NULL OR _source_url IS NULL OR _source_file IS NULL OR _source_sheet IS NULL OR _source_sha256 IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _source_row IS NULL OR _ingested_at IS NULL) AS incomplete, count(DISTINCT _source_sha256) AS shas, min(_source_sha256) AS sha FROM career_intelligence.silver.formacode_grand_domaine
  UNION ALL SELECT 'formacode' AS t, count_if(_source_name IS NULL OR _source_resource IS NULL OR _dataset IS NULL OR _source_url IS NULL OR _source_file IS NULL OR _source_sheet IS NULL OR _source_sha256 IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _source_row IS NULL OR _ingested_at IS NULL) AS incomplete, count(DISTINCT _source_sha256) AS shas, min(_source_sha256) AS sha FROM career_intelligence.silver.formacode
  UNION ALL SELECT 'formacode_terme_associe' AS t, count_if(_source_name IS NULL OR _source_resource IS NULL OR _dataset IS NULL OR _source_url IS NULL OR _source_file IS NULL OR _source_sheet IS NULL OR _source_sha256 IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _source_row IS NULL OR _ingested_at IS NULL) AS incomplete, count(DISTINCT _source_sha256) AS shas, min(_source_sha256) AS sha FROM career_intelligence.silver.formacode_terme_associe
  UNION ALL SELECT 'rome_metier_formacode' AS t, count_if(_source_name IS NULL OR _source_resource IS NULL OR _dataset IS NULL OR _source_url IS NULL OR _source_file IS NULL OR _source_sheet IS NULL OR _source_sha256 IS NULL OR _version IS NULL OR _snapshot IS NULL OR _run_id IS NULL OR _source_row IS NULL OR _ingested_at IS NULL) AS incomplete, count(DISTINCT _source_sha256) AS shas, min(_source_sha256) AS sha FROM career_intelligence.silver.rome_metier_formacode
);

-- 10. Licence properties
SHOW TBLPROPERTIES career_intelligence.silver.formacode_grand_domaine ('source.license');
SHOW TBLPROPERTIES career_intelligence.silver.formacode ('source.license');
SHOW TBLPROPERTIES career_intelligence.silver.formacode_terme_associe ('source.license');
SHOW TBLPROPERTIES career_intelligence.silver.rome_metier_formacode ('source.license');
