-- =============================================================================
-- Verification for the Gold layer (career_intelligence.gold, 9 objects).
-- Every expected value is recomputed from silver. Every check_* must be TRUE.
-- =============================================================================

-- 1. Row counts vs Silver
SELECT
  (SELECT count(*) FROM career_intelligence.gold.metier) = (SELECT count(*) FROM career_intelligence.silver.rome_metier)                AS check_rows_metier,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_appellation) = (SELECT count(*) FROM career_intelligence.silver.rome_metier_appellation) AS check_rows_appellation,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_competence)
    = (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_faire) + (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_etre)
    + (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir) + (SELECT count(*) FROM career_intelligence.silver.rome_metier_contexte_travail) AS check_rows_competence,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_domaine_formation) = (SELECT count(*) FROM career_intelligence.silver.rome_metier_formacode) AS check_rows_domaine_formation,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_formation_onisep)
    = (SELECT count(*) FROM career_intelligence.silver.onisep_metier_rome r JOIN career_intelligence.silver.onisep_formation_metier f ON f.identifiant_metier = r.identifiant_metier)
    + (SELECT count(*) FROM career_intelligence.silver.onisep_metier_rome r JOIN career_intelligence.silver.onisep_metier_formation_min_requise m ON m.identifiant_metier = r.identifiant_metier)
                                                                                                                                         AS check_rows_formation_onisep,
  (SELECT count(*) FROM career_intelligence.gold.v_fap) = (SELECT count(DISTINCT code_fap228) FROM career_intelligence.silver.fap2021)  AS check_rows_fap,
  (SELECT count(*) FROM career_intelligence.gold.bmo_recrutement)
    = (SELECT count(*) FROM (SELECT DISTINCT code_metier_bmo, code_departement FROM career_intelligence.silver.bmo_2026))
    + (SELECT count(*) FROM (SELECT DISTINCT code_metier_bmo, code_region FROM career_intelligence.silver.bmo_2026))
    + (SELECT count(DISTINCT code_metier_bmo) FROM career_intelligence.silver.bmo_2026)                                               AS check_rows_bmo_recrutement,
  (SELECT count(*) FROM career_intelligence.gold.v_rome_v3_fap) = (SELECT count(*) FROM career_intelligence.silver.dares_rome_v3_fap341) AS check_rows_rome_v3_fap,
  (SELECT count(*) FROM career_intelligence.gold.source_licence) = 9                                                                    AS check_rows_source_licence;
-- Expected (2026-11-09): 1923 | 14330 | 124910 | 5958 | 13033 | 228 | 21536 (17710 + 3609 + 217) | 5320 | 9

-- 2. Primary keys: unique and non-null
SELECT
  (SELECT count(*) = count(DISTINCT code_rome) AND count_if(code_rome IS NULL) = 0 FROM career_intelligence.gold.metier)                  AS check_pk_metier,
  (SELECT count(*) = count(DISTINCT code_ogr_appellation) AND count_if(code_ogr_appellation IS NULL) = 0 FROM career_intelligence.gold.v_metier_appellation) AS check_pk_appellation,
  (SELECT count(*) = count(DISTINCT code_rome, type_element, code_ogr_element)
          AND count_if(code_rome IS NULL OR type_element IS NULL OR code_ogr_element IS NULL) = 0 FROM career_intelligence.gold.v_metier_competence) AS check_pk_competence,
  (SELECT count(*) = count(DISTINCT code_rome, code_formacode) AND count_if(code_rome IS NULL OR code_formacode IS NULL) = 0
     FROM career_intelligence.gold.v_metier_domaine_formation)                                                                          AS check_pk_domaine_formation,
  (SELECT count(*) = count(DISTINCT code_rome_source, identifiant_metier_onisep, type_lien, identifiant_formation)
          AND count_if(code_rome_source IS NULL OR identifiant_metier_onisep IS NULL OR type_lien IS NULL OR identifiant_formation IS NULL) = 0
     FROM career_intelligence.gold.v_metier_formation_onisep)                                                                           AS check_pk_formation_onisep,
  (SELECT count(*) = count(DISTINCT code_fap228) AND count_if(code_fap228 IS NULL) = 0 FROM career_intelligence.gold.v_fap)               AS check_pk_fap,
  (SELECT count(*) = count(DISTINCT code_fap228, niveau_geo, code_geo) AND count_if(code_fap228 IS NULL OR niveau_geo IS NULL OR code_geo IS NULL) = 0
     FROM career_intelligence.gold.bmo_recrutement)                                                                                     AS check_pk_bmo_recrutement,
  (SELECT count(*) = count(DISTINCT code_rome_v3, code_qualification) AND count_if(code_rome_v3 IS NULL OR code_qualification IS NULL) = 0
     FROM career_intelligence.gold.v_rome_v3_fap)                                                                                       AS check_pk_rome_v3_fap,
  (SELECT count(*) = count(DISTINCT objet_gold) FROM career_intelligence.gold.source_licence)                                         AS check_pk_source_licence;

-- 3. Foreign keys
SELECT
  (SELECT count(*) FROM career_intelligence.gold.v_metier_appellation x LEFT ANTI JOIN career_intelligence.gold.metier m USING (code_rome)) = 0       AS check_fk_appellation,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_competence x LEFT ANTI JOIN career_intelligence.gold.metier m USING (code_rome)) = 0        AS check_fk_competence,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_domaine_formation x LEFT ANTI JOIN career_intelligence.gold.metier m USING (code_rome)) = 0 AS check_fk_domaine_formation_rome,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_domaine_formation x LEFT ANTI JOIN career_intelligence.silver.formacode f USING (code_formacode)) = 0 AS check_fk_formacode,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_formation_onisep x LEFT ANTI JOIN career_intelligence.gold.metier m USING (code_rome)
     WHERE x.code_rome IS NOT NULL) = 0                                                                                               AS check_fk_onisep_rome,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_formation_onisep x LEFT ANTI JOIN career_intelligence.silver.onisep_metier o
     ON o.identifiant = x.identifiant_metier_onisep) = 0                                                                              AS check_fk_onisep_metier,
  (SELECT count(*) FROM career_intelligence.gold.bmo_recrutement x LEFT ANTI JOIN career_intelligence.gold.v_fap f USING (code_fap228)) = 0          AS check_fk_bmo_fap,
  (SELECT count(*) FROM career_intelligence.gold.v_rome_v3_fap x LEFT ANTI JOIN career_intelligence.gold.v_fap f USING (code_fap228)) = 0            AS check_fk_rome_v3_fap,
  (SELECT count_if(bmo_disponible) FROM career_intelligence.gold.v_fap) = (SELECT count(DISTINCT code_metier_bmo) FROM career_intelligence.silver.bmo_2026) AS check_bmo_disponible;

-- 4. Relationships preserved (both directions vs Silver)
SELECT
  (SELECT count(*) FROM (SELECT code_rome, 'savoir_faire' t, code_ogr_competence c FROM career_intelligence.silver.rome_metier_savoir_faire
                         UNION ALL SELECT code_rome, 'savoir_etre', code_ogr_competence FROM career_intelligence.silver.rome_metier_savoir_etre
                         UNION ALL SELECT code_rome, 'savoir', code_ogr_savoir FROM career_intelligence.silver.rome_metier_savoir
                         UNION ALL SELECT code_rome, 'contexte_travail', code_ogr_contexte FROM career_intelligence.silver.rome_metier_contexte_travail) s
     FULL JOIN career_intelligence.gold.v_metier_competence g ON g.code_rome = s.code_rome AND g.type_element = s.t AND g.code_ogr_element = s.c
     WHERE s.code_rome IS NULL OR g.code_rome IS NULL) = 0                                                                               AS check_competence_sets,
  (SELECT count(*) FROM career_intelligence.silver.rome_metier_formacode s FULL JOIN career_intelligence.gold.v_metier_domaine_formation g
     ON g.code_rome = s.code_rome AND g.code_formacode = s.code_formacode WHERE s.code_rome IS NULL OR g.code_rome IS NULL) = 0          AS check_formacode_pairs,
  (SELECT count(*) FROM career_intelligence.silver.rome_metier_appellation s FULL JOIN career_intelligence.gold.v_metier_appellation g
     ON g.code_rome = s.code_rome AND g.code_ogr_appellation = s.code_ogr_appellation WHERE s.code_rome IS NULL OR g.code_rome IS NULL) = 0 AS check_appellation_pairs,
  (SELECT count(*) FROM (
      SELECT r.code_rome_source, r.identifiant_metier, 'formation_menant_au_metier' AS t, f.identifiant_formation
      FROM career_intelligence.silver.onisep_metier_rome r JOIN career_intelligence.silver.onisep_formation_metier f ON f.identifiant_metier = r.identifiant_metier
      UNION ALL
      SELECT r.code_rome_source, r.identifiant_metier, 'formation_minimale_requise', m.identifiant_formation
      FROM career_intelligence.silver.onisep_metier_rome r JOIN career_intelligence.silver.onisep_metier_formation_min_requise m ON m.identifiant_metier = r.identifiant_metier) s
     FULL JOIN career_intelligence.gold.v_metier_formation_onisep g
       ON g.code_rome_source = s.code_rome_source AND g.identifiant_metier_onisep = s.identifiant_metier AND g.type_lien = s.t AND g.identifiant_formation = s.identifiant_formation
     WHERE s.code_rome_source IS NULL OR g.code_rome_source IS NULL) = 0                                                                AS check_onisep_rows_exact,
  (SELECT count(*) FROM career_intelligence.silver.dares_rome_v3_fap341 s FULL JOIN career_intelligence.gold.v_rome_v3_fap g
     ON g.code_rome_v3 = s.code_rome_v3 AND g.code_qualification = s.code_qualification AND g.code_fap341 = s.code_fap341
     WHERE s.code_rome_v3 IS NULL OR g.code_rome_v3 IS NULL) = 0                                                                         AS check_rome_v3_pairs,
  (SELECT count_if(depend_qualification) FROM (SELECT DISTINCT code_rome_v3, depend_qualification FROM career_intelligence.gold.v_rome_v3_fap)) = 282 AS check_282_depend_qualification;

-- 5. D6 unresolved references explicit; D7 grain (no artificial duplication)
SELECT
  count_if(statut_code_rome = 'non_resolu')                                                                         AS rows_non_resolu,
  count(DISTINCT CASE WHEN statut_code_rome = 'non_resolu' THEN code_rome_source END)                               AS codes_non_resolus,
  count_if(statut_code_rome = 'non_resolu' AND code_rome IS NULL) = count_if(statut_code_rome = 'non_resolu')
    AND count_if(statut_code_rome = 'valide' AND (code_rome IS NULL OR code_rome <> code_rome_source)) = 0           AS check_d6_status_consistent,
  (SELECT count(DISTINCT r.identifiant_metier, r.code_rome_source) FROM career_intelligence.silver.onisep_metier_rome r WHERE r.statut_code = 'non_resolu')
    = count(DISTINCT CASE WHEN statut_code_rome = 'non_resolu' THEN concat(identifiant_metier_onisep, '|', code_rome_source) END)
    + (SELECT count(*) FROM career_intelligence.silver.onisep_metier_rome r WHERE r.statut_code = 'non_resolu'
       AND NOT EXISTS (SELECT 1 FROM career_intelligence.silver.onisep_formation_metier f WHERE f.identifiant_metier = r.identifiant_metier)
       AND NOT EXISTS (SELECT 1 FROM career_intelligence.silver.onisep_metier_formation_min_requise m WHERE m.identifiant_metier = r.identifiant_metier)) AS check_d6_all_unresolved_links_exposed,
  count_if(NOT formation_dans_catalogue) = (SELECT count(*) FROM career_intelligence.silver.onisep_metier_rome r
     JOIN career_intelligence.silver.onisep_metier_formation_min_requise m ON m.identifiant_metier = r.identifiant_metier WHERE NOT m.formation_dans_catalogue)
    AND count_if(NOT formation_dans_catalogue AND libelle_formation IS NULL) = 0                                      AS check_d6_outside_catalogue_kept,
  count_if(type_lien = 'formation_menant_au_metier' AND NOT formation_dans_catalogue) = 0                           AS check_fiches_in_catalogue,
  (SELECT count(*) FROM (SELECT identifiant_metier, code_rome_source FROM career_intelligence.silver.onisep_metier_rome GROUP BY 1, 2 HAVING count(*) > 1)) = 0 AS check_d7_no_duplicate_source_links
FROM career_intelligence.gold.v_metier_formation_onisep;
-- Expected: 54 rows from 8 unresolved links (6 codes); 57 minimum-training rows outside the catalogue

-- 6. D3: BMO minimums reconcile across levels and with Silver; NULL only when all cells hidden
WITH s AS (
  SELECT count(*) AS cells, count_if(nb_projets_recrutement_secret) AS sec_r, count_if(nb_projets_difficiles_secret) AS sec_d,
         count_if(nb_projets_saisonniers_secret) AS sec_s, sum(nb_projets_recrutement) AS r, sum(nb_projets_difficiles) AS d, sum(nb_projets_saisonniers) AS sa
  FROM career_intelligence.silver.bmo_2026),
g AS (
  SELECT niveau_geo, sum(nb_cellules) AS cells, sum(nb_cellules_secretes_recrutement) AS sec_r, sum(nb_cellules_secretes_difficiles) AS sec_d,
         sum(nb_cellules_secretes_saisonniers) AS sec_s, sum(nb_projets_recrutement_minimum) AS r, sum(nb_projets_difficiles_minimum) AS d,
         sum(nb_projets_saisonniers_minimum) AS sa
  FROM career_intelligence.gold.bmo_recrutement GROUP BY niveau_geo)
SELECT
  (SELECT count(*) FROM g) = 3
    AND (SELECT count(*) FROM g JOIN s ON g.cells = s.cells AND g.sec_r = s.sec_r AND g.sec_d = s.sec_d AND g.sec_s = s.sec_s
                                     AND g.r = s.r AND g.d = s.d AND g.sa = s.sa) = 3                               AS check_d3_levels_reconcile,
  (SELECT count_if(est_complet_recrutement <> (nb_cellules_secretes_recrutement = 0) OR est_complet_difficiles <> (nb_cellules_secretes_difficiles = 0)
                   OR est_complet_saisonniers <> (nb_cellules_secretes_saisonniers = 0)) FROM career_intelligence.gold.bmo_recrutement) = 0 AS check_d3_complete_flags,
  (SELECT count_if((nb_projets_recrutement_minimum IS NULL) <> (nb_cellules_secretes_recrutement = nb_cellules)
                   OR (nb_projets_difficiles_minimum IS NULL) <> (nb_cellules_secretes_difficiles = nb_cellules)
                   OR (nb_projets_saisonniers_minimum IS NULL) <> (nb_cellules_secretes_saisonniers = nb_cellules))
     FROM career_intelligence.gold.bmo_recrutement) = 0                                                             AS check_d3_null_only_when_all_hidden,
  (SELECT count_if(niveau_geo = 'national' AND (code_geo <> 'FR' OR libelle_geo <> 'France')) FROM career_intelligence.gold.bmo_recrutement) = 0
    AND (SELECT count(DISTINCT niveau_geo) FROM career_intelligence.gold.bmo_recrutement) = 3                       AS check_geo_levels,
  (SELECT count_if(est_complet_recrutement) FROM career_intelligence.gold.bmo_recrutement WHERE niveau_geo = 'national') AS national_complete_families;
-- Expected national complete families: 0 (all 217 national totals include hidden cells)

-- 7. D8: assembled texts equal a recomputation from silver
SELECT
  (SELECT count(*) FROM career_intelligence.gold.metier g JOIN (
      SELECT code_rome,
             concat_ws(' ', transform(array_sort(collect_list(CASE WHEN libelle_type_texte = 'definition' THEN struct(position_phrase, libelle_texte) END)), x -> x.libelle_texte)) AS def,
             concat_ws('\n', transform(array_sort(collect_list(CASE WHEN libelle_type_texte = 'acces_metier' THEN struct(position_phrase, libelle_texte) END)), x -> x.libelle_texte)) AS acc,
             count_if(libelle_type_texte = 'definition') AS nd, count_if(libelle_type_texte = 'acces_metier') AS na
      FROM career_intelligence.silver.rome_metier_texte GROUP BY code_rome) t USING (code_rome)
     WHERE g.definition <> t.def OR g.acces_metier <> t.acc OR g.nb_phrases_definition <> t.nd OR g.nb_phrases_acces_metier <> t.na) = 0 AS check_d8_texts,
  (SELECT count_if(definition IS NULL OR acces_metier IS NULL) FROM career_intelligence.gold.metier) = 0              AS check_d8_texts_present,
  (SELECT count(*) FROM career_intelligence.gold.metier g WHERE g.nb_savoir_faire <> (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_faire x WHERE x.code_rome = g.code_rome)
     OR g.nb_domaines_formation <> (SELECT count(*) FROM career_intelligence.silver.rome_metier_formacode x WHERE x.code_rome = g.code_rome)) = 0 AS check_counts;

-- 8. D2 / D5 guards on the published schema
WITH c AS (SELECT table_name, collect_set(column_name) AS cols FROM career_intelligence.information_schema.columns
           WHERE table_schema = 'gold' GROUP BY table_name)
SELECT
  count_if(array_contains(cols, 'code_rome') AND exists(cols, x -> x LIKE '%fap%' OR x LIKE 'nb\\_projets%' OR x LIKE 'code\\_metier\\_bmo%' OR x = 'bmo_disponible')) = 0 AS check_d2_no_rome_v62_with_bmo,
  count_if(table_name = 'v_rome_v3_fap' AND array_contains(cols, 'code_rome')) = 0                                    AS check_d2_rome_v3_not_v62,
  count_if(table_name <> 'v_metier_formation_onisep' AND exists(cols, x -> x LIKE '%onisep%' OR x LIKE 'identifiant\\_%')) = 0 AS check_d5_onisep_isolated,
  count_if(exists(cols, x -> x RLIKE '(poids|weight|score|rang|rank|principal|ponderation)')) = 0                       AS check_no_weights,
  count_if(table_name = 'bmo_recrutement' AND exists(cols, x -> x LIKE 'nb\\_projets%' AND NOT x LIKE '%\\_minimum')) = 0 AS check_d3_minimum_names,
  count(*) = 9                                                                                                         AS check_nine_objects
FROM c;

-- 9. Licences: properties match source_licence; lineage present
SELECT
  (SELECT count(*) FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_formation_onisep' AND licence = 'ODbL') = 1 AS check_onisep_odbl,
  (SELECT count_if(NOT licence_confirmee) FROM career_intelligence.gold.source_licence) = 2
    AND (SELECT count_if(NOT licence_confirmee AND licence NOT LIKE 'UNCONFIRMED%') FROM career_intelligence.gold.source_licence) = 0 AS check_unconfirmed_flagged,
  (SELECT count_if(_rome_version IS NULL OR _source_archive_sha256 IS NULL) FROM career_intelligence.gold.metier) = 0
    AND (SELECT count_if(_source_sha256 IS NULL) FROM career_intelligence.gold.bmo_recrutement) = 0
    AND (SELECT count_if(_source_sha256 IS NULL) FROM career_intelligence.gold.v_metier_domaine_formation) = 0
    AND (SELECT count_if(_source_sha256 IS NULL OR _snapshot IS NULL) FROM career_intelligence.gold.v_rome_v3_fap) = 0
    AND (SELECT count_if(_source_sha256_lien_rome IS NULL OR _source_sha256_lien_formation IS NULL) FROM career_intelligence.gold.v_metier_formation_onisep) = 0 AS check_lineage;

SHOW TBLPROPERTIES career_intelligence.gold.metier ('source.license');
SHOW TBLPROPERTIES career_intelligence.gold.v_metier_appellation ('source.license');
SHOW TBLPROPERTIES career_intelligence.gold.v_metier_competence ('source.license');
SHOW TBLPROPERTIES career_intelligence.gold.v_metier_domaine_formation ('source.license');
SHOW TBLPROPERTIES career_intelligence.gold.v_metier_formation_onisep ('source.license');
SHOW TBLPROPERTIES career_intelligence.gold.v_fap ('source.license');
SHOW TBLPROPERTIES career_intelligence.gold.bmo_recrutement ('source.license');
SHOW TBLPROPERTIES career_intelligence.gold.v_rome_v3_fap ('source.license');
SHOW TBLPROPERTIES career_intelligence.gold.source_licence ('source.license');
