-- =============================================================================
-- Verification for the ROME v62 Bronze tables (career_intelligence.bronze.rome_*).
-- Expected values come from the local validation run (manifest, run 9e0aacb660b4).
-- Every check_* column must be TRUE.
-- =============================================================================

-- 1. Row counts per table vs source CSV records (29 tables)
SELECT count(*) AS tables, count_if(expected = actual) AS matching,
       count(*) = 29 AND count_if(expected = actual) = 29 AS check_row_counts,
       sum(actual) AS total_rows
FROM (
  SELECT 'arborescence_centre_interet' AS entity, 5698 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_centre_interet) AS actual
  UNION ALL SELECT 'arborescence_competences' AS entity, 19598 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_competences) AS actual
  UNION ALL SELECT 'arborescence_secteur_activite' AS entity, 4341 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_secteur_activite) AS actual
  UNION ALL SELECT 'arborescence_secteur_naf' AS entity, 3626 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_secteur_naf) AS actual
  UNION ALL SELECT 'arborescence_thematique' AS entity, 1660 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_thematique) AS actual
  UNION ALL SELECT 'centre_interet' AS entity, 30 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_centre_interet) AS actual
  UNION ALL SELECT 'coherence_item' AS entity, 124910 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_coherence_item) AS actual
  UNION ALL SELECT 'composition_bloc' AS entity, 8 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_composition_bloc) AS actual
  UNION ALL SELECT 'cr_gd_dp' AS entity, 1923 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_cr_gd_dp) AS actual
  UNION ALL SELECT 'cr_gd_dp_appellations' AS entity, 16377 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_cr_gd_dp_appellations) AS actual
  UNION ALL SELECT 'descriptif_rubrique' AS entity, 3 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_descriptif_rubrique) AS actual
  UNION ALL SELECT 'domaine_professionnel' AS entity, 110 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_domaine_professionnel) AS actual
  UNION ALL SELECT 'grand_domaine' AS entity, 14 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_grand_domaine) AS actual
  UNION ALL SELECT 'item' AS entity, 35981 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_item) AS actual
  UNION ALL SELECT 'liens_rome_referentiels' AS entity, 141163 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_liens_rome_referentiels) AS actual
  UNION ALL SELECT 'referentiel_appellation' AS entity, 14330 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_appellation) AS actual
  UNION ALL SELECT 'referentiel_code_rome' AS entity, 1923 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_code_rome) AS actual
  UNION ALL SELECT 'referentiel_code_rome_riasec' AS entity, 1923 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_code_rome_riasec) AS actual
  UNION ALL SELECT 'referentiel_competence' AS entity, 20088 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_competence) AS actual
  UNION ALL SELECT 'referentiel_contexte_travail' AS entity, 194 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_contexte_travail) AS actual
  UNION ALL SELECT 'referentiel_macro_competence_riasec' AS entity, 506 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_macro_competence_riasec) AS actual
  UNION ALL SELECT 'referentiel_savoir' AS entity, 15699 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_savoir) AS actual
  UNION ALL SELECT 'rubrique_mobilite' AS entity, 18601 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_rubrique_mobilite) AS actual
  UNION ALL SELECT 'secteur_activite' AS entity, 35 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_secteur_activite) AS actual
  UNION ALL SELECT 'secteur_naf' AS entity, 89 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_secteur_naf) AS actual
  UNION ALL SELECT 'sous_secteur_activite' AS entity, 40 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_sous_secteur_activite) AS actual
  UNION ALL SELECT 'texte' AS entity, 15048 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_texte) AS actual
  UNION ALL SELECT 'themes' AS entity, 17 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_themes) AS actual
  UNION ALL SELECT 'type_referentiel' AS entity, 0 AS expected, (SELECT count(*) FROM career_intelligence.bronze.rome_type_referentiel) AS actual
);

-- 2. Lineage: one archive, one version, one run per table
SELECT count(DISTINCT _source_archive_sha256) = 1 AND min(_source_archive_sha256) = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb' AS check_archive_sha,
       count(DISTINCT _rome_version) = 1 AND min(_rome_version) = '62' AS check_version
FROM (SELECT _source_archive_sha256, _rome_version FROM career_intelligence.bronze.rome_liens_rome_referentiels
      UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.bronze.rome_referentiel_code_rome
      UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.bronze.rome_arborescence_secteur_naf);

-- 3. Keys of the core referentials are unique
SELECT
  (SELECT count(*) = count(DISTINCT code_rome) FROM career_intelligence.bronze.rome_referentiel_code_rome)      AS check_key_rome,
  (SELECT count(*) = count(DISTINCT code_ogr)  FROM career_intelligence.bronze.rome_referentiel_appellation)    AS check_key_appellation,
  (SELECT count(*) = count(DISTINCT code_ogr)  FROM career_intelligence.bronze.rome_referentiel_competence)     AS check_key_competence,
  (SELECT count(*) = count(DISTINCT code_ogr_savoir) FROM career_intelligence.bronze.rome_referentiel_savoir)   AS check_key_savoir,
  (SELECT count(*) = count(DISTINCT code_ogr)  FROM career_intelligence.bronze.rome_item)                        AS check_key_item,
  (SELECT count(*) = count(DISTINCT code_rome, code_compo_bloc, code_rubrique, code_ogr)
     FROM career_intelligence.bronze.rome_liens_rome_referentiels)                                                AS check_key_liens;

-- 4. Occupation <-> skill/knowledge relationships: every link resolves to its
--    block-specific target (polymorphic code_ogr), and every link occupation exists.
WITH l AS (SELECT * FROM career_intelligence.bronze.rome_liens_rome_referentiels),
targets AS (
  SELECT '1' AS bloc, ''  AS rub, code_ogr       AS ogr FROM career_intelligence.bronze.rome_referentiel_code_rome
  UNION ALL SELECT '2', '',  code_ogr       FROM career_intelligence.bronze.rome_referentiel_appellation
  UNION ALL SELECT '5', '1', code_ogr       FROM career_intelligence.bronze.rome_referentiel_competence
  UNION ALL SELECT '5', '2', code_ogr       FROM career_intelligence.bronze.rome_referentiel_competence
  UNION ALL SELECT '5', '3', code_ogr_savoir FROM career_intelligence.bronze.rome_referentiel_savoir
  UNION ALL SELECT '6', '',  code_ogr       FROM career_intelligence.bronze.rome_referentiel_contexte_travail)
SELECT l.code_compo_bloc, l.code_rubrique, count(*) AS links,
       count(DISTINCT l.code_rome) AS occupations,
       count_if(t.ogr IS NULL) AS unresolved
FROM l LEFT JOIN targets t ON t.bloc = l.code_compo_bloc AND t.rub = l.code_rubrique AND t.ogr = l.code_ogr
GROUP BY ALL ORDER BY ALL;
-- Expected (v62): (1,'',1923) (2,'',14330) (5,'1',60517) (5,'2',6343) (5,'3',40715) (6,'',17335); unresolved = 0

SELECT
  (SELECT count_if(r.code_rome IS NULL) = 0 FROM career_intelligence.bronze.rome_liens_rome_referentiels l
     LEFT JOIN career_intelligence.bronze.rome_referentiel_code_rome r USING (code_rome))                   AS check_fk_liens_rome,
  (SELECT count_if(r.code_rome IS NULL) = 0 FROM career_intelligence.bronze.rome_referentiel_appellation a
     LEFT JOIN career_intelligence.bronze.rome_referentiel_code_rome r USING (code_rome))                   AS check_fk_appellation_rome,
  (SELECT count_if(i.code_ogr IS NULL) = 0 FROM career_intelligence.bronze.rome_coherence_item c
     LEFT JOIN career_intelligence.bronze.rome_item i USING (code_ogr))                                     AS check_fk_coherence_item,
  (SELECT count_if(r.code_rome IS NULL) = 0 FROM career_intelligence.bronze.rome_rubrique_mobilite m
     LEFT JOIN career_intelligence.bronze.rome_referentiel_code_rome r ON r.code_rome = m.code_rome_cible)   AS check_fk_mobilite_cible,
  -- 16 rows are macro-competences without a child competence (code_ogr_competence = ''): not orphans
  (SELECT count_if(c.code_ogr IS NULL) = 0 FROM career_intelligence.bronze.rome_arborescence_competences a
     LEFT JOIN career_intelligence.bronze.rome_referentiel_competence c ON c.code_ogr = a.code_ogr_competence
     WHERE a.code_ogr_competence <> '')                                                                     AS check_fk_arbo_competence;

-- 5. Source quirks preserved: multi-line definitions, cp1252 file decoded, empty table typed
SELECT
  (SELECT count_if(definition_centre_interet LIKE '%\n%') FROM career_intelligence.bronze.rome_centre_interet) = 30 AS check_multiline_kept,
  (SELECT count_if(_source_encoding = 'cp1252') FROM career_intelligence.bronze.rome_arborescence_secteur_naf) = 3626 AS check_cp1252_flagged,
  -- in this cp1252 file, accents occur in libelle_rome (NAF labels are ASCII-only): decoded, no mojibake
  (SELECT count_if(libelle_rome RLIKE '[éèàçô]') > 0 AND count_if(libelle_rome LIKE '%Ã%' OR libelle_secteur_naf LIKE '%Ã%') = 0
     FROM career_intelligence.bronze.rome_arborescence_secteur_naf) AS check_cp1252_accents,
  (SELECT count(*) FROM career_intelligence.bronze.rome_type_referentiel) = 0 AS check_empty_table;
