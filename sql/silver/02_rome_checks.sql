-- =============================================================================
-- Verification for the ROME Silver tables (career_intelligence.silver.rome_*).
-- Partly GENERATED (row counts, keys, empty strings, FKs); every check_* must be TRUE.
-- =============================================================================

-- 1. Row counts: each Silver table has exactly the rows of its Bronze source (24 tables)
SELECT count(*) AS tables, count_if(silver = bronze) AS matching,
       count(*) = 24 AND count_if(silver = bronze) = 24 AS check_row_counts
FROM (
  SELECT 'rome_metier' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_code_rome) AS bronze
  UNION ALL SELECT 'rome_grand_domaine' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_grand_domaine) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_grand_domaine) AS bronze
  UNION ALL SELECT 'rome_domaine_professionnel' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_domaine_professionnel) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_domaine_professionnel) AS bronze
  UNION ALL SELECT 'rome_appellation' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_appellation) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_appellation) AS bronze
  UNION ALL SELECT 'rome_competence' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_competence) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_competence) AS bronze
  UNION ALL SELECT 'rome_macro_competence' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_macro_competence) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_competence WHERE code_macro_comp <> '') AS bronze
  UNION ALL SELECT 'rome_savoir' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_savoir) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_savoir) AS bronze
  UNION ALL SELECT 'rome_contexte_travail' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_contexte_travail) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_referentiel_contexte_travail) AS bronze
  UNION ALL SELECT 'rome_centre_interet' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_centre_interet) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_centre_interet) AS bronze
  UNION ALL SELECT 'rome_secteur_activite' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_secteur_activite) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_secteur_activite) AS bronze
  UNION ALL SELECT 'rome_sous_secteur_activite' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_sous_secteur_activite) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_sous_secteur_activite) AS bronze
  UNION ALL SELECT 'rome_theme' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_theme) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_themes) AS bronze
  UNION ALL SELECT 'rome_secteur_naf' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_secteur_naf) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_secteur_naf) AS bronze
  UNION ALL SELECT 'rome_metier_appellation' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_appellation) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_liens_rome_referentiels WHERE code_compo_bloc = '2') AS bronze
  UNION ALL SELECT 'rome_metier_savoir_faire' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_faire) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_liens_rome_referentiels WHERE code_compo_bloc = '5' AND code_rubrique = '1') AS bronze
  UNION ALL SELECT 'rome_metier_savoir_etre' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_etre) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_liens_rome_referentiels WHERE code_compo_bloc = '5' AND code_rubrique = '2') AS bronze
  UNION ALL SELECT 'rome_metier_savoir' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_liens_rome_referentiels WHERE code_compo_bloc = '5' AND code_rubrique = '3') AS bronze
  UNION ALL SELECT 'rome_metier_contexte_travail' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_contexte_travail) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_liens_rome_referentiels WHERE code_compo_bloc = '6') AS bronze
  UNION ALL SELECT 'rome_metier_texte' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_texte) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_texte) AS bronze
  UNION ALL SELECT 'rome_metier_mobilite' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_mobilite) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_rubrique_mobilite) AS bronze
  UNION ALL SELECT 'rome_metier_centre_interet' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_centre_interet) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_centre_interet) AS bronze
  UNION ALL SELECT 'rome_metier_secteur_activite' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_secteur_activite) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_secteur_activite) AS bronze
  UNION ALL SELECT 'rome_metier_theme' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_theme) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_thematique) AS bronze
  UNION ALL SELECT 'rome_metier_secteur_naf' AS t, (SELECT count(*) FROM career_intelligence.silver.rome_metier_secteur_naf) AS silver, (SELECT count(*) FROM career_intelligence.bronze.rome_arborescence_secteur_naf) AS bronze
);

-- 2. Primary keys: unique and non-null (24 tables)
SELECT count(*) AS tables, sum(dup) AS duplicate_keys, sum(null_key) AS null_keys,
       sum(dup) = 0 AND sum(null_key) = 0 AS check_primary_keys
FROM (
  SELECT 'rome_metier' AS t, count(*) - count(DISTINCT code_rome) AS dup, count_if(code_rome IS NULL) AS null_key FROM career_intelligence.silver.rome_metier
  UNION ALL SELECT 'rome_grand_domaine' AS t, count(*) - count(DISTINCT code_grand_domaine) AS dup, count_if(code_grand_domaine IS NULL) AS null_key FROM career_intelligence.silver.rome_grand_domaine
  UNION ALL SELECT 'rome_domaine_professionnel' AS t, count(*) - count(DISTINCT code_domaine_professionnel) AS dup, count_if(code_domaine_professionnel IS NULL) AS null_key FROM career_intelligence.silver.rome_domaine_professionnel
  UNION ALL SELECT 'rome_appellation' AS t, count(*) - count(DISTINCT code_ogr) AS dup, count_if(code_ogr IS NULL) AS null_key FROM career_intelligence.silver.rome_appellation
  UNION ALL SELECT 'rome_competence' AS t, count(*) - count(DISTINCT code_ogr) AS dup, count_if(code_ogr IS NULL) AS null_key FROM career_intelligence.silver.rome_competence
  UNION ALL SELECT 'rome_macro_competence' AS t, count(*) - count(DISTINCT code_ogr) AS dup, count_if(code_ogr IS NULL) AS null_key FROM career_intelligence.silver.rome_macro_competence
  UNION ALL SELECT 'rome_savoir' AS t, count(*) - count(DISTINCT code_ogr_savoir) AS dup, count_if(code_ogr_savoir IS NULL) AS null_key FROM career_intelligence.silver.rome_savoir
  UNION ALL SELECT 'rome_contexte_travail' AS t, count(*) - count(DISTINCT code_ogr) AS dup, count_if(code_ogr IS NULL) AS null_key FROM career_intelligence.silver.rome_contexte_travail
  UNION ALL SELECT 'rome_centre_interet' AS t, count(*) - count(DISTINCT code_centre_interet) AS dup, count_if(code_centre_interet IS NULL) AS null_key FROM career_intelligence.silver.rome_centre_interet
  UNION ALL SELECT 'rome_secteur_activite' AS t, count(*) - count(DISTINCT code_sect_activite) AS dup, count_if(code_sect_activite IS NULL) AS null_key FROM career_intelligence.silver.rome_secteur_activite
  UNION ALL SELECT 'rome_sous_secteur_activite' AS t, count(*) - count(DISTINCT code_ss_sect_activite) AS dup, count_if(code_ss_sect_activite IS NULL) AS null_key FROM career_intelligence.silver.rome_sous_secteur_activite
  UNION ALL SELECT 'rome_theme' AS t, count(*) - count(DISTINCT code_theme) AS dup, count_if(code_theme IS NULL) AS null_key FROM career_intelligence.silver.rome_theme
  UNION ALL SELECT 'rome_secteur_naf' AS t, count(*) - count(DISTINCT code_secteur_naf) AS dup, count_if(code_secteur_naf IS NULL) AS null_key FROM career_intelligence.silver.rome_secteur_naf
  UNION ALL SELECT 'rome_metier_appellation' AS t, count(*) - count(DISTINCT code_rome, code_ogr_appellation) AS dup, count_if(code_rome IS NULL OR code_ogr_appellation IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_appellation
  UNION ALL SELECT 'rome_metier_savoir_faire' AS t, count(*) - count(DISTINCT code_rome, code_ogr_competence) AS dup, count_if(code_rome IS NULL OR code_ogr_competence IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_savoir_faire
  UNION ALL SELECT 'rome_metier_savoir_etre' AS t, count(*) - count(DISTINCT code_rome, code_ogr_competence) AS dup, count_if(code_rome IS NULL OR code_ogr_competence IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_savoir_etre
  UNION ALL SELECT 'rome_metier_savoir' AS t, count(*) - count(DISTINCT code_rome, code_ogr_savoir) AS dup, count_if(code_rome IS NULL OR code_ogr_savoir IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_savoir
  UNION ALL SELECT 'rome_metier_contexte_travail' AS t, count(*) - count(DISTINCT code_rome, code_ogr_contexte) AS dup, count_if(code_rome IS NULL OR code_ogr_contexte IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_contexte_travail
  UNION ALL SELECT 'rome_metier_texte' AS t, count(*) - count(DISTINCT code_rome, libelle_type_texte, position_phrase) AS dup, count_if(code_rome IS NULL OR libelle_type_texte IS NULL OR position_phrase IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_texte
  UNION ALL SELECT 'rome_metier_mobilite' AS t, count(*) - count(DISTINCT code_rome, code_rome_cible) AS dup, count_if(code_rome IS NULL OR code_rome_cible IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_mobilite
  UNION ALL SELECT 'rome_metier_centre_interet' AS t, count(*) - count(DISTINCT code_rome, code_centre_interet) AS dup, count_if(code_rome IS NULL OR code_centre_interet IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_centre_interet
  UNION ALL SELECT 'rome_metier_secteur_activite' AS t, count(*) - count(DISTINCT code_rome, code_sect_activite, coalesce(code_ss_sect_activite, '<null>')) AS dup, count_if(code_rome IS NULL OR code_sect_activite IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_secteur_activite
  UNION ALL SELECT 'rome_metier_theme' AS t, count(*) - count(DISTINCT code_rome, code_theme) AS dup, count_if(code_rome IS NULL OR code_theme IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_theme
  UNION ALL SELECT 'rome_metier_secteur_naf' AS t, count(*) - count(DISTINCT code_rome, code_secteur_naf) AS dup, count_if(code_rome IS NULL OR code_secteur_naf IS NULL) AS null_key FROM career_intelligence.silver.rome_metier_secteur_naf
);

-- 3. Foreign keys: no orphans (every non-NULL reference resolves)
SELECT count(*) AS fks_checked, sum(orphans) AS orphans, sum(orphans) = 0 AS check_foreign_keys
FROM (
  SELECT 'rome_metier_appellation.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_appellation x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_savoir_faire.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_savoir_faire x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_savoir_etre.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_savoir_etre x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_savoir.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_savoir x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_contexte_travail.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_contexte_travail x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_texte.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_texte x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_mobilite.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_mobilite x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_centre_interet.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_centre_interet x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_secteur_activite.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_secteur_activite x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_theme.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_theme x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier_secteur_naf.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_secteur_naf x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_appellation.code_rome -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_appellation x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome WHERE x.code_rome IS NOT NULL
  UNION ALL SELECT 'rome_metier.code_rome_parent -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome_parent WHERE x.code_rome_parent IS NOT NULL
  UNION ALL SELECT 'rome_metier.code_domaine_professionnel -> rome_domaine_professionnel.code_domaine_professionnel' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier x LEFT ANTI JOIN career_intelligence.silver.rome_domaine_professionnel p ON p.code_domaine_professionnel = x.code_domaine_professionnel WHERE x.code_domaine_professionnel IS NOT NULL
  UNION ALL SELECT 'rome_metier.code_grand_domaine -> rome_grand_domaine.code_grand_domaine' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier x LEFT ANTI JOIN career_intelligence.silver.rome_grand_domaine p ON p.code_grand_domaine = x.code_grand_domaine WHERE x.code_grand_domaine IS NOT NULL
  UNION ALL SELECT 'rome_domaine_professionnel.code_grand_domaine -> rome_grand_domaine.code_grand_domaine' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_domaine_professionnel x LEFT ANTI JOIN career_intelligence.silver.rome_grand_domaine p ON p.code_grand_domaine = x.code_grand_domaine WHERE x.code_grand_domaine IS NOT NULL
  UNION ALL SELECT 'rome_competence.code_ogr_macro_comp -> rome_macro_competence.code_ogr' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_competence x LEFT ANTI JOIN career_intelligence.silver.rome_macro_competence p ON p.code_ogr = x.code_ogr_macro_comp WHERE x.code_ogr_macro_comp IS NOT NULL
  UNION ALL SELECT 'rome_macro_competence.code_ogr -> rome_competence.code_ogr' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_macro_competence x LEFT ANTI JOIN career_intelligence.silver.rome_competence p ON p.code_ogr = x.code_ogr WHERE x.code_ogr IS NOT NULL
  UNION ALL SELECT 'rome_metier_appellation.code_ogr_appellation -> rome_appellation.code_ogr' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_appellation x LEFT ANTI JOIN career_intelligence.silver.rome_appellation p ON p.code_ogr = x.code_ogr_appellation WHERE x.code_ogr_appellation IS NOT NULL
  UNION ALL SELECT 'rome_metier_savoir_faire.code_ogr_competence -> rome_competence.code_ogr' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_savoir_faire x LEFT ANTI JOIN career_intelligence.silver.rome_competence p ON p.code_ogr = x.code_ogr_competence WHERE x.code_ogr_competence IS NOT NULL
  UNION ALL SELECT 'rome_metier_savoir_etre.code_ogr_competence -> rome_macro_competence.code_ogr' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_savoir_etre x LEFT ANTI JOIN career_intelligence.silver.rome_macro_competence p ON p.code_ogr = x.code_ogr_competence WHERE x.code_ogr_competence IS NOT NULL
  UNION ALL SELECT 'rome_metier_savoir.code_ogr_savoir -> rome_savoir.code_ogr_savoir' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_savoir x LEFT ANTI JOIN career_intelligence.silver.rome_savoir p ON p.code_ogr_savoir = x.code_ogr_savoir WHERE x.code_ogr_savoir IS NOT NULL
  UNION ALL SELECT 'rome_metier_contexte_travail.code_ogr_contexte -> rome_contexte_travail.code_ogr' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_contexte_travail x LEFT ANTI JOIN career_intelligence.silver.rome_contexte_travail p ON p.code_ogr = x.code_ogr_contexte WHERE x.code_ogr_contexte IS NOT NULL
  UNION ALL SELECT 'rome_metier_mobilite.code_rome_cible -> rome_metier.code_rome' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_mobilite x LEFT ANTI JOIN career_intelligence.silver.rome_metier p ON p.code_rome = x.code_rome_cible WHERE x.code_rome_cible IS NOT NULL
  UNION ALL SELECT 'rome_metier_centre_interet.code_centre_interet -> rome_centre_interet.code_centre_interet' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_centre_interet x LEFT ANTI JOIN career_intelligence.silver.rome_centre_interet p ON p.code_centre_interet = x.code_centre_interet WHERE x.code_centre_interet IS NOT NULL
  UNION ALL SELECT 'rome_metier_secteur_activite.code_sect_activite -> rome_secteur_activite.code_sect_activite' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_secteur_activite x LEFT ANTI JOIN career_intelligence.silver.rome_secteur_activite p ON p.code_sect_activite = x.code_sect_activite WHERE x.code_sect_activite IS NOT NULL
  UNION ALL SELECT 'rome_metier_secteur_activite.code_ss_sect_activite -> rome_sous_secteur_activite.code_ss_sect_activite' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_secteur_activite x LEFT ANTI JOIN career_intelligence.silver.rome_sous_secteur_activite p ON p.code_ss_sect_activite = x.code_ss_sect_activite WHERE x.code_ss_sect_activite IS NOT NULL
  UNION ALL SELECT 'rome_sous_secteur_activite.code_sect_activite -> rome_secteur_activite.code_sect_activite' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_sous_secteur_activite x LEFT ANTI JOIN career_intelligence.silver.rome_secteur_activite p ON p.code_sect_activite = x.code_sect_activite WHERE x.code_sect_activite IS NOT NULL
  UNION ALL SELECT 'rome_metier_theme.code_theme -> rome_theme.code_theme' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_theme x LEFT ANTI JOIN career_intelligence.silver.rome_theme p ON p.code_theme = x.code_theme WHERE x.code_theme IS NOT NULL
  UNION ALL SELECT 'rome_metier_secteur_naf.code_secteur_naf -> rome_secteur_naf.code_secteur_naf' AS fk, count(*) AS orphans FROM career_intelligence.silver.rome_metier_secteur_naf x LEFT ANTI JOIN career_intelligence.silver.rome_secteur_naf p ON p.code_secteur_naf = x.code_secteur_naf WHERE x.code_secteur_naf IS NOT NULL
);

-- 4. The six link blocks of bronze.rome_liens_rome_referentiels are fully accounted for
WITH blocks AS (
  SELECT code_compo_bloc AS bloc, code_rubrique AS rub, count(*) AS bronze
  FROM career_intelligence.bronze.rome_liens_rome_referentiels GROUP BY ALL),
silver AS (
  SELECT '1' AS bloc, '' AS rub, (SELECT count(*) FROM career_intelligence.bronze.rome_liens_rome_referentiels l
         JOIN career_intelligence.silver.rome_metier m ON m.code_rome = l.code_rome AND m.code_ogr = l.code_ogr
         WHERE l.code_compo_bloc = '1') AS silver   -- self-link: validated, no table
  UNION ALL SELECT '2', '',  (SELECT count(*) FROM career_intelligence.silver.rome_metier_appellation)
  UNION ALL SELECT '5', '1', (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_faire)
  UNION ALL SELECT '5', '2', (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_etre)
  UNION ALL SELECT '5', '3', (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir)
  UNION ALL SELECT '6', '',  (SELECT count(*) FROM career_intelligence.silver.rome_metier_contexte_travail))
SELECT b.bloc, b.rub, b.bronze, s.silver, b.bronze = s.silver AS check_block
FROM blocks b FULL JOIN silver s USING (bloc, rub) ORDER BY 1, 2;
-- Expected (v62): 1:1923  2:14330  5/1:60517  5/2:6343  5/3:40715  6:17335 (total 141163)

-- 5. Domain rules
SELECT
  -- job-title links agree with rome_appellation.code_rome
  (SELECT count(*) FROM career_intelligence.silver.rome_metier_appellation ma JOIN career_intelligence.silver.rome_appellation a
     ON a.code_ogr = ma.code_ogr_appellation WHERE a.code_rome <> ma.code_rome) = 0     AS check_appellation_rome,
  -- know-how links target both levels, soft-skill links only the 16 savoir-etre macros
  (SELECT count(DISTINCT niveau_competence) FROM career_intelligence.silver.rome_metier_savoir_faire) = 2        AS check_savoir_faire_two_levels,
  (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_etre e JOIN career_intelligence.silver.rome_macro_competence m
     ON m.code_ogr = e.code_ogr_competence WHERE m.cat_comp = 'Savoir-être professionnel')
    = (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_etre)                                  AS check_savoir_etre_targets,
  -- macro / child distinction: 506 macros (16 childless = savoir-etre), 19582 children each with one parent
  (SELECT count(*) FROM career_intelligence.silver.rome_macro_competence) = 506
    AND (SELECT count_if(NOT has_child_competence) FROM career_intelligence.silver.rome_macro_competence) = 16
    AND (SELECT count_if(NOT has_child_competence AND cat_comp <> 'Savoir-être professionnel')
           FROM career_intelligence.silver.rome_macro_competence) = 0                                             AS check_macro_structure,
  (SELECT count_if(nature = 'Compétence' AND code_ogr_macro_comp IS NULL)
        + count_if(nature = 'Macro-compétence' AND code_ogr_macro_comp IS NOT NULL)
     FROM career_intelligence.silver.rome_competence) = 0                                                         AS check_parent_by_level,
  -- coeur_metier carried over 1:1 from coherence_item (22031 'Principale')
  (SELECT count_if(coeur_metier = 'Principale') FROM career_intelligence.silver.rome_metier_savoir_faire)
  + (SELECT count_if(coeur_metier = 'Principale') FROM career_intelligence.silver.rome_metier_savoir_etre)
  + (SELECT count_if(coeur_metier = 'Principale') FROM career_intelligence.silver.rome_metier_savoir)
  + (SELECT count_if(coeur_metier = 'Principale') FROM career_intelligence.silver.rome_metier_contexte_travail)
    = (SELECT count_if(coeur_metier = 'Principale') FROM career_intelligence.bronze.rome_coherence_item)          AS check_coeur_metier,
  -- 1:1 enrichments of rome_metier are complete
  (SELECT count_if(code_domaine_professionnel IS NULL OR code_grand_domaine IS NULL
                   OR riasec_majeur IS NULL) FROM career_intelligence.silver.rome_metier) = 0                    AS check_metier_enrichment,
  -- exactly one principal centre of interest / sector per occupation
  (SELECT count(*) FROM (SELECT code_rome FROM career_intelligence.silver.rome_metier_centre_interet WHERE principal = 'oui'
     GROUP BY 1 HAVING count(*) <> 1)) = 0
    AND (SELECT count(DISTINCT code_rome) FROM career_intelligence.silver.rome_metier_centre_interet WHERE principal = 'oui') = 1923
                                                                                           AS check_principal_ci,
  (SELECT count(DISTINCT code_rome) FROM career_intelligence.silver.rome_metier_secteur_activite WHERE principal = 'oui') = 1923
    AND (SELECT count_if(principal = 'oui') FROM career_intelligence.silver.rome_metier_secteur_activite) = 1923   AS check_principal_sector;

-- 6. No empty strings left in Silver string columns
SELECT sum(empty) AS empty_strings, sum(empty) = 0 AS check_no_empty_strings
FROM (
  SELECT 'rome_appellation' AS t, count_if(code_ogr = '' OR code_rome = '' OR libelle_appellation_long = '' OR libelle_appellation_court = '' OR classification = '' OR peu_usite = '' OR transition_eco = '' OR transition_num = '' OR transition_demo = '' OR emploi_reglemente = '' OR emploi_cadre = '' OR origine = '' OR code_rome_parent = '') AS empty FROM career_intelligence.silver.rome_appellation
  UNION ALL SELECT 'rome_centre_interet' AS t, count_if(code_centre_interet = '' OR libelle_centre_interet = '' OR definition_centre_interet = '') AS empty FROM career_intelligence.silver.rome_centre_interet
  UNION ALL SELECT 'rome_competence' AS t, count_if(code_ogr = '' OR nature = '' OR libelle_competence = '' OR definition = '' OR code_ogr_macro_comp = '' OR code_macro_comp = '' OR cat_comp = '' OR sous_cat_comp = '' OR transition_eco = '' OR transition_num = '' OR libelle_heterogeneite = '' OR libelle_origine = '') AS empty FROM career_intelligence.silver.rome_competence
  UNION ALL SELECT 'rome_contexte_travail' AS t, count_if(code_ogr = '' OR libelle_cont_travail = '' OR code_type_cont_trav = '' OR libelle_type_cont_trav = '') AS empty FROM career_intelligence.silver.rome_contexte_travail
  UNION ALL SELECT 'rome_domaine_professionnel' AS t, count_if(code_domaine_professionnel = '' OR libelle_domaine_professionnel = '' OR code_grand_domaine = '') AS empty FROM career_intelligence.silver.rome_domaine_professionnel
  UNION ALL SELECT 'rome_grand_domaine' AS t, count_if(code_grand_domaine = '' OR libelle_grand_domaine = '') AS empty FROM career_intelligence.silver.rome_grand_domaine
  UNION ALL SELECT 'rome_macro_competence' AS t, count_if(code_ogr = '' OR code_macro_competence = '' OR libelle_macro_competence = '' OR cat_comp = '' OR sous_cat_comp = '' OR code_domaine_competence = '' OR domaine_competence = '' OR code_enjeu = '' OR enjeu = '' OR code_objectif = '' OR objectif = '' OR riasec_majeur = '' OR riasec_mineur = '') AS empty FROM career_intelligence.silver.rome_macro_competence
  UNION ALL SELECT 'rome_metier' AS t, count_if(code_rome = '' OR code_ogr = '' OR code_fiche_metier = '' OR libelle_rome = '' OR code_grand_domaine = '' OR code_domaine_professionnel = '' OR riasec_majeur = '' OR riasec_mineur = '' OR transition_eco = '' OR transition_num = '' OR transition_demo = '' OR emploi_reglemente = '' OR emploi_cadre = '' OR code_rome_parent = '') AS empty FROM career_intelligence.silver.rome_metier
  UNION ALL SELECT 'rome_metier_appellation' AS t, count_if(code_rome = '' OR code_ogr_appellation = '') AS empty FROM career_intelligence.silver.rome_metier_appellation
  UNION ALL SELECT 'rome_metier_centre_interet' AS t, count_if(code_rome = '' OR code_centre_interet = '' OR principal = '') AS empty FROM career_intelligence.silver.rome_metier_centre_interet
  UNION ALL SELECT 'rome_metier_contexte_travail' AS t, count_if(code_rome = '' OR code_ogr_contexte = '' OR coeur_metier = '') AS empty FROM career_intelligence.silver.rome_metier_contexte_travail
  UNION ALL SELECT 'rome_metier_mobilite' AS t, count_if(code_rome = '' OR code_rome_cible = '') AS empty FROM career_intelligence.silver.rome_metier_mobilite
  UNION ALL SELECT 'rome_metier_savoir' AS t, count_if(code_rome = '' OR code_ogr_savoir = '' OR coeur_metier = '') AS empty FROM career_intelligence.silver.rome_metier_savoir
  UNION ALL SELECT 'rome_metier_savoir_etre' AS t, count_if(code_rome = '' OR code_ogr_competence = '' OR coeur_metier = '') AS empty FROM career_intelligence.silver.rome_metier_savoir_etre
  UNION ALL SELECT 'rome_metier_savoir_faire' AS t, count_if(code_rome = '' OR code_ogr_competence = '' OR niveau_competence = '' OR coeur_metier = '') AS empty FROM career_intelligence.silver.rome_metier_savoir_faire
  UNION ALL SELECT 'rome_metier_secteur_activite' AS t, count_if(code_rome = '' OR code_sect_activite = '' OR code_ss_sect_activite = '' OR principal = '') AS empty FROM career_intelligence.silver.rome_metier_secteur_activite
  UNION ALL SELECT 'rome_metier_secteur_naf' AS t, count_if(code_rome = '' OR code_secteur_naf = '') AS empty FROM career_intelligence.silver.rome_metier_secteur_naf
  UNION ALL SELECT 'rome_metier_texte' AS t, count_if(code_rome = '' OR code_compo_bloc = '' OR libelle_type_texte = '' OR libelle_texte = '') AS empty FROM career_intelligence.silver.rome_metier_texte
  UNION ALL SELECT 'rome_metier_theme' AS t, count_if(code_rome = '' OR code_theme = '') AS empty FROM career_intelligence.silver.rome_metier_theme
  UNION ALL SELECT 'rome_savoir' AS t, count_if(code_ogr_savoir = '' OR libelle_savoir = '' OR categorie_savoir = '' OR sous_categorie_savoir = '' OR transition_eco = '' OR transition_num = '') AS empty FROM career_intelligence.silver.rome_savoir
  UNION ALL SELECT 'rome_secteur_activite' AS t, count_if(code_sect_activite = '' OR libelle_sect_activite = '' OR definition_sect_activite = '') AS empty FROM career_intelligence.silver.rome_secteur_activite
  UNION ALL SELECT 'rome_secteur_naf' AS t, count_if(code_secteur_naf = '' OR code_tech_secteur_naf = '' OR libelle_secteur_naf = '') AS empty FROM career_intelligence.silver.rome_secteur_naf
  UNION ALL SELECT 'rome_sous_secteur_activite' AS t, count_if(code_ss_sect_activite = '' OR libelle_ss_sect_activite = '' OR definition_ss_sect_activite = '' OR code_sect_activite = '') AS empty FROM career_intelligence.silver.rome_sous_secteur_activite
  UNION ALL SELECT 'rome_theme' AS t, count_if(code_theme = '' OR libelle_theme = '' OR definition_theme = '') AS empty FROM career_intelligence.silver.rome_theme
);

-- 7. Lineage kept: every Silver ROME row carries the v62 archive checksum
SELECT count(*) AS rows_checked, count_if(_source_archive_sha256 IS NULL OR _rome_version IS NULL) AS missing,
       count_if(_source_archive_sha256 IS NULL OR _rome_version IS NULL) = 0
         AND count(DISTINCT _source_archive_sha256) = 1 AS check_lineage
FROM (
  SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_grand_domaine
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_domaine_professionnel
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_appellation
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_competence
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_macro_competence
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_savoir
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_contexte_travail
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_centre_interet
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_secteur_activite
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_sous_secteur_activite
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_theme
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_secteur_naf
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_appellation
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_savoir_faire
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_savoir_etre
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_savoir
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_contexte_travail
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_texte
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_mobilite
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_centre_interet
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_secteur_activite
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_theme
  UNION ALL SELECT _source_archive_sha256, _rome_version FROM career_intelligence.silver.rome_metier_secteur_naf
);
