-- =============================================================================
-- Verification for the Search views (career_intelligence.search, 4 views).
-- Every expected value is recomputed from gold. Every check_* must be TRUE.
-- The parameterized queries (sql/search/queries) are verified by tests/live.
-- =============================================================================

-- 1. Row counts vs Gold
SELECT
  (SELECT count(*) FROM career_intelligence.search.v_metier_index)
    = 4 * (SELECT count(*) FROM career_intelligence.gold.metier)
    + (SELECT count(*) FROM career_intelligence.gold.v_metier_appellation)
    + (SELECT count_if(libelle_appellation_court <> libelle_appellation_long) FROM career_intelligence.gold.v_metier_appellation) AS check_rows_metier_index,
  (SELECT count(*) FROM career_intelligence.search.v_element_competence)
    = (SELECT count(*) FROM (SELECT DISTINCT type_element, code_ogr_element FROM career_intelligence.gold.v_metier_competence)) AS check_rows_element_competence,
  (SELECT count(*) FROM career_intelligence.search.v_domaine_formation)
    = (SELECT count(DISTINCT code_formacode) FROM career_intelligence.gold.v_metier_domaine_formation)                       AS check_rows_domaine_formation,
  (SELECT count(*) FROM career_intelligence.search.v_zone_geo)
    = (SELECT count(*) FROM (SELECT DISTINCT niveau_geo, code_geo FROM career_intelligence.gold.bmo_recrutement))              AS check_rows_zone_geo;
-- Expected (2026-11-09): 24532 (4 x 1923 + 14330 + 2510) | 32432 | 1220 | 120 (101 + 18 + 1)

-- 2. Keys unique and non-null
SELECT
  (SELECT count(*) = count(DISTINCT code_rome, champ, coalesce(code_ogr_appellation, ''))
          AND count_if(code_rome IS NULL OR champ IS NULL OR texte IS NULL) = 0
          AND count_if((champ LIKE 'appellation%') <> (code_ogr_appellation IS NOT NULL)) = 0
     FROM career_intelligence.search.v_metier_index)                                                                      AS check_pk_metier_index,
  (SELECT count(*) = count(DISTINCT type_element, code_ogr_element) AND count_if(code_ogr_element IS NULL OR libelle_element IS NULL) = 0
     FROM career_intelligence.search.v_element_competence)                                                                AS check_pk_element_competence,
  (SELECT count(*) = count(DISTINCT code_formacode) AND count_if(code_formacode IS NULL OR libelle_formacode IS NULL) = 0
     FROM career_intelligence.search.v_domaine_formation)                                                                 AS check_pk_domaine_formation,
  (SELECT count(*) = count(DISTINCT niveau_geo, code_geo) AND count_if(code_geo IS NULL OR libelle_geo IS NULL) = 0
     FROM career_intelligence.search.v_zone_geo)                                                                          AS check_pk_zone_geo;

-- 3. Referential integrity and exact correspondence with Gold
SELECT
  (SELECT count(*) FROM career_intelligence.search.v_metier_index i LEFT ANTI JOIN career_intelligence.gold.metier m USING (code_rome)) = 0 AS check_fk_index_metier,
  (SELECT count(*) FROM career_intelligence.search.v_metier_index i
     LEFT ANTI JOIN career_intelligence.gold.v_metier_appellation a ON a.code_rome = i.code_rome AND a.code_ogr_appellation = i.code_ogr_appellation
     WHERE i.champ LIKE 'appellation%') = 0                                                                               AS check_fk_index_appellation,
  (SELECT count(*) FROM career_intelligence.gold.metier m JOIN career_intelligence.search.v_metier_index i ON i.code_rome = m.code_rome
     WHERE (i.champ = 'code_rome' AND i.texte <> m.code_rome) OR (i.champ = 'libelle_rome' AND i.texte <> m.libelle_rome)) = 0 AS check_index_names_verbatim,
  (SELECT count(*) FROM career_intelligence.gold.v_metier_appellation a JOIN career_intelligence.search.v_metier_index i
     ON i.code_rome = a.code_rome AND i.code_ogr_appellation = a.code_ogr_appellation
     WHERE (i.champ = 'appellation_long' AND i.texte <> a.libelle_appellation_long)
        OR (i.champ = 'appellation_court' AND i.texte <> a.libelle_appellation_court)) = 0                                AS check_index_appellations_verbatim,
  (SELECT count(*) FROM career_intelligence.search.v_element_competence e
     LEFT ANTI JOIN career_intelligence.gold.v_metier_competence c ON c.type_element = e.type_element AND c.code_ogr_element = e.code_ogr_element) = 0 AS check_fk_element,
  (SELECT count(*) FROM career_intelligence.search.v_domaine_formation d LEFT ANTI JOIN career_intelligence.gold.v_metier_domaine_formation g USING (code_formacode)) = 0 AS check_fk_formacode,
  (SELECT count(*) FROM career_intelligence.search.v_zone_geo z
     LEFT ANTI JOIN career_intelligence.gold.bmo_recrutement b ON b.niveau_geo = z.niveau_geo AND b.code_geo = z.code_geo AND b.libelle_geo = z.libelle_geo) = 0 AS check_fk_zone;

-- 4. P5: doubled apostrophes corrected only in the Search index, Gold left faithful to the source
SELECT
  (SELECT count_if(instr(texte, repeat(chr(39), 2)) > 0) FROM career_intelligence.search.v_metier_index) = 0              AS check_p5_no_doubled_apostrophe,
  (SELECT count(*) FROM career_intelligence.gold.metier m JOIN career_intelligence.search.v_metier_index i ON i.code_rome = m.code_rome
     WHERE (i.champ = 'definition'   AND (i.texte <> array_join(split(m.definition,   repeat(chr(39), 2)), chr(39))
                                          OR i.nb_apostrophes_corrigees <> size(split(m.definition,   repeat(chr(39), 2))) - 1))
        OR (i.champ = 'acces_metier' AND (i.texte <> array_join(split(m.acces_metier, repeat(chr(39), 2)), chr(39))
                                          OR i.nb_apostrophes_corrigees <> size(split(m.acces_metier, repeat(chr(39), 2))) - 1))) = 0 AS check_p5_texts_equal_gold_corrected,
  (SELECT sum(nb_apostrophes_corrigees) FROM career_intelligence.search.v_metier_index)
    = (SELECT sum(size(split(libelle_texte, repeat(chr(39), 2))) - 1) FROM career_intelligence.silver.rome_metier_texte
       WHERE libelle_type_texte IN ('definition', 'acces_metier'))                                                        AS check_p5_all_source_pairs_corrected,
  (SELECT count_if(champ NOT IN ('definition', 'acces_metier') AND nb_apostrophes_corrigees <> 0) FROM career_intelligence.search.v_metier_index) = 0 AS check_p5_only_rome_texts,
  (SELECT count_if(instr(definition, repeat(chr(39), 2)) > 0) FROM career_intelligence.gold.metier) > 0                    AS check_p5_gold_still_faithful,
  (SELECT sum(nb_apostrophes_corrigees) FROM career_intelligence.search.v_metier_index)                                    AS apostrophe_pairs_corrected;
-- Expected pairs corrected: 10205 (definition 7195 + acces_metier 3010)

-- 5. Counts are recomputed facts, not weights
SELECT
  (SELECT count(*) FROM career_intelligence.search.v_element_competence e JOIN (
      SELECT type_element, code_ogr_element, count(*) AS n FROM career_intelligence.gold.v_metier_competence GROUP BY 1, 2) g
     ON g.type_element = e.type_element AND g.code_ogr_element = e.code_ogr_element WHERE g.n <> e.nb_metiers) = 0       AS check_nb_metiers_element,
  (SELECT sum(nb_metiers) FROM career_intelligence.search.v_element_competence) = (SELECT count(*) FROM career_intelligence.gold.v_metier_competence) AS check_element_links_total,
  (SELECT sum(nb_metiers) FROM career_intelligence.search.v_domaine_formation) = (SELECT count(*) FROM career_intelligence.gold.v_metier_domaine_formation) AS check_formacode_links_total,
  (SELECT count(*) FROM career_intelligence.search.v_zone_geo z JOIN (
      SELECT niveau_geo, code_geo, count(*) AS n FROM career_intelligence.gold.bmo_recrutement GROUP BY 1, 2) g
     ON g.niveau_geo = z.niveau_geo AND g.code_geo = z.code_geo WHERE g.n <> z.nb_familles_fap228) = 0                    AS check_nb_familles_zone,
  (SELECT count_if(niveau_geo = 'national' AND (code_geo <> 'FR' OR nb_familles_fap228 <> 217)) FROM career_intelligence.search.v_zone_geo) = 0 AS check_zone_national;

-- 6. Matching behaviour of the warehouse collation used by every query
SELECT
  (SELECT count_if(contains(texte COLLATE UNICODE_CI_AI, 'electricien')) FROM career_intelligence.search.v_metier_index)
    = (SELECT count_if(contains(texte COLLATE UNICODE_CI_AI, 'ÉLECTRICIEN')) FROM career_intelligence.search.v_metier_index)
    AND (SELECT count_if(contains(texte COLLATE UNICODE_CI_AI, 'electricien')) FROM career_intelligence.search.v_metier_index) > 0 AS check_case_accent_insensitive,
  (SELECT count_if(contains(texte COLLATE UNICODE_CI_AI, 'oeuvre')) FROM career_intelligence.search.v_metier_index)
    >= (SELECT count_if(instr(lower(texte), 'œuvre') > 0) FROM career_intelligence.search.v_metier_index)
    AND (SELECT count_if(instr(lower(texte), 'œuvre') > 0) FROM career_intelligence.search.v_metier_index) > 0              AS check_ligature_oe,
  (SELECT count_if(contains(texte COLLATE UNICODE_CI_AI, 'd' || chr(39) || 'etat')) FROM career_intelligence.search.v_metier_index WHERE champ = 'acces_metier') > 0 AS check_apostrophe_searchable;

-- 7. Separation, isolation and published schema
WITH c AS (SELECT table_name, collect_set(column_name) AS cols FROM career_intelligence.information_schema.columns
           WHERE table_schema = 'search' GROUP BY table_name)
SELECT
  count_if(array_contains(cols, 'code_rome') AND exists(cols, x -> x LIKE '%fap%' OR x LIKE 'nb\\_projets%' OR x LIKE '%bmo%' OR x LIKE '%geo%' OR x = 'code_rome_v3')) = 0 AS check_no_rome_v62_with_bmo_fap_v3,
  count_if(exists(cols, x -> x LIKE '%onisep%' OR x LIKE 'identifiant%' OR x LIKE '%rncp%')) = 0                      AS check_onisep_not_reshaped,
  count_if(exists(cols, x -> x = 'code_rome_parent')) = 0                                                               AS check_no_code_rome_parent,
  count_if(exists(cols, x -> x RLIKE '(poids|weight|score|rang|rank|ponderation|principal)')) = 0                       AS check_no_weights,
  count(*) = 4                                                                                                           AS check_four_views,
  (SELECT count_if(table_type <> 'VIEW') FROM career_intelligence.information_schema.tables WHERE table_schema = 'search') = 0 AS check_views_only
FROM c;

-- 8. Licences (equality with gold.source_licence is enforced by tests/test_search_contracts.py)
SHOW TBLPROPERTIES career_intelligence.search.v_metier_index ('source.license');
SHOW TBLPROPERTIES career_intelligence.search.v_element_competence ('source.license');
SHOW TBLPROPERTIES career_intelligence.search.v_domaine_formation ('source.license');
SHOW TBLPROPERTIES career_intelligence.search.v_zone_geo ('source.license');
