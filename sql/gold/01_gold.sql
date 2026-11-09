-- =============================================================================
-- Gold layer (Phase 13b): integrated, read-optimised model — career_intelligence.gold
-- Source: career_intelligence.silver (read-only). 9 objects: 3 tables, 6 views.
--
-- Approved decisions
--   D2  ROME v62 and BMO are strictly separate: no object holds both a v62 code_rome and a
--       FAP / BMO column. The only ROME -> FAP route is v_rome_v3_fap (ROME **V3** x
--       qualification), never joined to ROME v62. code_rome_parent is an attribute only.
--   D3  BMO aggregates are MINIMUMS (sum of the published, non-secret cells): measures are
--       named *_minimum, with hidden-cell counts and est_complet_* flags; NULL when every
--       cell of the group is hidden. National level: code_geo = 'FR' (project constant).
--   D4  Tables: metier, bmo_recrutement, source_licence. Relationships: views.
--   D5  ONISEP (ODbL) data only in v_metier_formation_onisep.
--   D6  Unresolved ONISEP ROME codes kept in v_metier_formation_onisep (code_rome NULL,
--       statut_code_rome = 'non_resolu', key on code_rome_source); training outside the
--       ONISEP catalogue kept with formation_dans_catalogue = false.
--   D7  ONISEP grain preserved: one row per (ONISEP ROME link row x ONISEP training link row),
--       no DISTINCT, no collapsing.
--   D8  Assembled texts: definition = sentences joined with ' ', acces_metier = sentences
--       joined with a line break, both ordered by position_phrase.
--   D10 Dedicated schema career_intelligence.gold.
--   No NSF, no weights / scores / primary links, no apportioning of BMO figures.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS career_intelligence.gold
  COMMENT 'Integrated, read-optimised model for the application (built from silver).';

-- G1 -------------------------------------------------------------------------
CREATE OR REPLACE TABLE career_intelligence.gold.metier
COMMENT 'ROME 4.0 v62 occupation profile: labels, domains, RIASEC, flags, assembled definition and access texts, element counts. ROME data only (no ONISEP, no BMO). code_rome_parent is a published attribute, never used for joins. Key: code_rome.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'Licence Ouverte (fr-lo)',
               'source.attribution' = 'France Travail – ROME 4.0', 'primary_key' = 'code_rome')
AS
WITH textes AS (
  SELECT code_rome, libelle_type_texte,
         transform(array_sort(collect_list(struct(position_phrase, libelle_texte))), x -> x.libelle_texte) AS phrases,
         count(*) AS nb_phrases
  FROM career_intelligence.silver.rome_metier_texte
  GROUP BY code_rome, libelle_type_texte
),
nb AS (
  SELECT m.code_rome,
         (SELECT count(*) FROM career_intelligence.silver.rome_metier_appellation x WHERE x.code_rome = m.code_rome)      AS nb_appellations,
         (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_faire x WHERE x.code_rome = m.code_rome)     AS nb_savoir_faire,
         (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir_etre x WHERE x.code_rome = m.code_rome)      AS nb_savoir_etre,
         (SELECT count(*) FROM career_intelligence.silver.rome_metier_savoir x WHERE x.code_rome = m.code_rome)           AS nb_savoirs,
         (SELECT count(*) FROM career_intelligence.silver.rome_metier_contexte_travail x WHERE x.code_rome = m.code_rome) AS nb_contextes_travail,
         (SELECT count(*) FROM career_intelligence.silver.rome_metier_formacode x WHERE x.code_rome = m.code_rome)        AS nb_domaines_formation
  FROM career_intelligence.silver.rome_metier m
)
SELECT
  m.code_rome,
  m.code_ogr,
  m.libelle_rome,
  m.code_grand_domaine,
  gd.libelle_grand_domaine,
  m.code_domaine_professionnel,
  dp.libelle_domaine_professionnel,
  m.riasec_majeur,
  m.riasec_mineur,
  m.transition_eco,
  m.transition_num,
  m.transition_demo,
  m.emploi_reglemente,
  m.emploi_cadre,
  m.code_rome_parent,
  concat_ws(' ', d.phrases) AS definition,
  CAST(d.nb_phrases AS INT) AS nb_phrases_definition,
  concat_ws('\n', a.phrases) AS acces_metier,
  CAST(a.nb_phrases AS INT) AS nb_phrases_acces_metier,
  CAST(nb.nb_appellations AS INT) AS nb_appellations,
  CAST(nb.nb_savoir_faire AS INT) AS nb_savoir_faire,
  CAST(nb.nb_savoir_etre AS INT) AS nb_savoir_etre,
  CAST(nb.nb_savoirs AS INT) AS nb_savoirs,
  CAST(nb.nb_contextes_travail AS INT) AS nb_contextes_travail,
  CAST(nb.nb_domaines_formation AS INT) AS nb_domaines_formation,
  m._rome_version,
  m._source_archive_sha256,
  current_timestamp() AS _gold_built_at
FROM career_intelligence.silver.rome_metier m
LEFT JOIN career_intelligence.silver.rome_grand_domaine gd ON gd.code_grand_domaine = m.code_grand_domaine
LEFT JOIN career_intelligence.silver.rome_domaine_professionnel dp ON dp.code_domaine_professionnel = m.code_domaine_professionnel
LEFT JOIN textes d ON d.code_rome = m.code_rome AND d.libelle_type_texte = 'definition'
LEFT JOIN textes a ON a.code_rome = m.code_rome AND a.libelle_type_texte = 'acces_metier'
LEFT JOIN nb ON nb.code_rome = m.code_rome;

-- G2 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.gold.v_metier_appellation
COMMENT 'Job titles (appellations) of each ROME 4.0 v62 occupation, for search. Key: code_ogr_appellation.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'Licence Ouverte (fr-lo)',
               'source.attribution' = 'France Travail – ROME 4.0', 'primary_key' = 'code_ogr_appellation')
AS
SELECT x.code_rome, x.code_ogr_appellation, a.libelle_appellation_long, a.libelle_appellation_court,
       a.classification, a.peu_usite, x._rome_version
FROM career_intelligence.silver.rome_metier_appellation x
JOIN career_intelligence.silver.rome_appellation a ON a.code_ogr = x.code_ogr_appellation;

-- G3 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.gold.v_metier_competence
COMMENT 'Skills (savoir-faire, savoir-être), knowledge and work contexts of each ROME 4.0 v62 occupation. Macro-competence vs competence kept (niveau_competence, parent macro). Key: code_rome, type_element, code_ogr_element.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'Licence Ouverte (fr-lo)',
               'source.attribution' = 'France Travail – ROME 4.0',
               'primary_key' = 'code_rome, type_element, code_ogr_element')
AS
SELECT x.code_rome, 'savoir_faire' AS type_element, x.code_ogr_competence AS code_ogr_element,
       c.libelle_competence AS libelle_element, c.nature AS niveau_competence,
       c.code_ogr_macro_comp AS code_ogr_macro_competence, mc.libelle_macro_competence,
       c.cat_comp AS categorie, c.sous_cat_comp AS sous_categorie, x.coeur_metier, x._rome_version
FROM career_intelligence.silver.rome_metier_savoir_faire x
JOIN career_intelligence.silver.rome_competence c ON c.code_ogr = x.code_ogr_competence
LEFT JOIN career_intelligence.silver.rome_macro_competence mc ON mc.code_ogr = c.code_ogr_macro_comp
UNION ALL
SELECT x.code_rome, 'savoir_etre', x.code_ogr_competence, c.libelle_competence, c.nature,
       c.code_ogr_macro_comp, NULL, c.cat_comp, c.sous_cat_comp, x.coeur_metier, x._rome_version
FROM career_intelligence.silver.rome_metier_savoir_etre x
JOIN career_intelligence.silver.rome_competence c ON c.code_ogr = x.code_ogr_competence
UNION ALL
SELECT x.code_rome, 'savoir', x.code_ogr_savoir, s.libelle_savoir, NULL, NULL, NULL,
       s.categorie_savoir, s.sous_categorie_savoir, x.coeur_metier, x._rome_version
FROM career_intelligence.silver.rome_metier_savoir x
JOIN career_intelligence.silver.rome_savoir s ON s.code_ogr_savoir = x.code_ogr_savoir
UNION ALL
SELECT x.code_rome, 'contexte_travail', x.code_ogr_contexte, t.libelle_cont_travail, NULL, NULL, NULL,
       t.libelle_type_cont_trav, NULL, x.coeur_metier, x._rome_version
FROM career_intelligence.silver.rome_metier_contexte_travail x
JOIN career_intelligence.silver.rome_contexte_travail t ON t.code_ogr = x.code_ogr_contexte;

-- G4 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.gold.v_metier_domaine_formation
COMMENT 'Training domains (Formacode V14) of each ROME 4.0 v62 occupation: all correspondence links, many-to-many, broad and leaf terms, official labels, no weights. Key: code_rome, code_formacode.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'Licence Ouverte (fr-lo); Licence Ouverte 2.0 (lov2)',
               'source.attribution' = 'France Travail – ROME 4.0; Formacode® V14 – Centre Inffo',
               'primary_key' = 'code_rome, code_formacode')
AS
SELECT x.code_rome, x.code_formacode, f.libelle_formacode, f.code_champ_semantique, f.libelle_champ_semantique,
       f.code_grand_domaine AS code_grand_domaine_formacode, g.libelle_grand_domaine AS libelle_grand_domaine_formacode,
       f.niveau, f.est_terme_feuille, f.code_formacode_parent, x._version, x._source_sha256
FROM career_intelligence.silver.rome_metier_formacode x
JOIN career_intelligence.silver.formacode f ON f.code_formacode = x.code_formacode
JOIN career_intelligence.silver.formacode_grand_domaine g ON g.code_grand_domaine = f.code_grand_domaine;

-- G5 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.gold.v_metier_formation_onisep
COMMENT 'ONISEP training linked to ROME occupations through ONISEP''s own links (ODbL). One row per (ONISEP occupation->ROME link, ONISEP occupation<->training link). type_lien = formation_menant_au_metier | formation_minimale_requise. Unresolved ONISEP ROME codes kept (code_rome NULL, statut_code_rome = non_resolu); training outside the catalogue kept (formation_dans_catalogue = false). Key: code_rome_source, identifiant_metier_onisep, type_lien, identifiant_formation.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'ODbL',
               'source.attribution' = 'Source : Onisep; France Travail – ROME 4.0',
               'primary_key' = 'code_rome_source, identifiant_metier_onisep, type_lien, identifiant_formation')
AS
WITH liens AS (
  SELECT r.code_rome_source, r.code_rome, r.statut_code AS statut_code_rome, r.identifiant_metier,
         'formation_menant_au_metier' AS type_lien, fm.identifiant_formation,
         CAST(NULL AS STRING) AS libelle_formation_source,
         r._source_sha256 AS _source_sha256_lien_rome, fm._source_sha256 AS _source_sha256_lien_formation,
         r._snapshot
  FROM career_intelligence.silver.onisep_metier_rome r
  JOIN career_intelligence.silver.onisep_formation_metier fm ON fm.identifiant_metier = r.identifiant_metier
  UNION ALL
  SELECT r.code_rome_source, r.code_rome, r.statut_code, r.identifiant_metier,
         'formation_minimale_requise', mr.identifiant_formation, mr.libelle_formation,
         r._source_sha256, mr._source_sha256, r._snapshot
  FROM career_intelligence.silver.onisep_metier_rome r
  JOIN career_intelligence.silver.onisep_metier_formation_min_requise mr ON mr.identifiant_metier = r.identifiant_metier
)
SELECT l.code_rome_source, l.code_rome, l.statut_code_rome,
       l.identifiant_metier AS identifiant_metier_onisep, om.nom_metier AS nom_metier_onisep,
       l.type_lien, l.identifiant_formation,
       coalesce(fi.libelle_formation_principal, l.libelle_formation_source) AS libelle_formation,
       l.libelle_formation_source,
       fi.identifiant IS NOT NULL AS formation_dans_catalogue,
       fi.libelle_type_formation, fi.niveau_de_sortie_indicatif, fi.libelle_niveau_de_certification,
       fi.duree, fi.code_rncp, fi.url_onisep,
       l._snapshot, l._source_sha256_lien_rome, l._source_sha256_lien_formation
FROM liens l
JOIN career_intelligence.silver.onisep_metier om ON om.identifiant = l.identifiant_metier
LEFT JOIN career_intelligence.silver.onisep_formation_initiale fi ON fi.identifiant = l.identifiant_formation;

-- G6 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.gold.v_fap
COMMENT 'FAP 2021 families at the 228 level (BMO grain) with FAP86 / FAP22 parents, number of FAP341 sub-families and BMO availability. Key: code_fap228.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'UNCONFIRMED (DARES FAP 2021); Licence Ouverte (BMO availability flag)',
               'source.attribution' = 'Source : Dares, nomenclature des familles professionnelles FAP-2021; France Travail – BMO',
               'primary_key' = 'code_fap228')
AS
SELECT f.code_fap228, f.libelle_fap228, f.code_fap86, f.libelle_fap86, f.code_fap22, f.libelle_fap22,
       CAST(count(*) AS INT) AS nb_fap341,
       f.code_fap228 IN (SELECT code_metier_bmo FROM career_intelligence.silver.bmo_2026) AS bmo_disponible
FROM career_intelligence.silver.fap2021 f
GROUP BY f.code_fap228, f.libelle_fap228, f.code_fap86, f.libelle_fap86, f.code_fap22, f.libelle_fap22;

-- G7 -------------------------------------------------------------------------
CREATE OR REPLACE TABLE career_intelligence.gold.bmo_recrutement
COMMENT 'BMO 2026 recruitment projects by FAP228 family (BMO occupation) and geography (departement, region, national FR). Values are MINIMUMS: sums of the published non-secret cells; *_minimum is NULL when every cell is hidden; est_complet_* true only without hidden cells. No ROME column. Key: code_fap228, niveau_geo, code_geo.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'Licence Ouverte (fr-lo)',
               'source.attribution' = 'France Travail – Enquête Besoins en Main-d''Oeuvre (BMO) 2026',
               'primary_key' = 'code_fap228, niveau_geo, code_geo')
AS
WITH grouped AS (
  SELECT b.annee, b.code_metier_bmo, b.libelle_metier_bmo, g.niveau_geo, g.code_geo, g.libelle_geo,
         b.nb_projets_recrutement, b.nb_projets_recrutement_secret,
         b.nb_projets_difficiles, b.nb_projets_difficiles_secret,
         b.nb_projets_saisonniers, b.nb_projets_saisonniers_secret,
         b._source_sha256, b._source_file
  FROM career_intelligence.silver.bmo_2026 b
  LATERAL VIEW inline(array(
    named_struct('niveau_geo', 'departement', 'code_geo', b.code_departement, 'libelle_geo', b.libelle_departement),
    named_struct('niveau_geo', 'region',      'code_geo', b.code_region,      'libelle_geo', b.libelle_region),
    named_struct('niveau_geo', 'national',    'code_geo', 'FR',               'libelle_geo', 'France'))) g
)
SELECT
  code_metier_bmo AS code_fap228,
  libelle_metier_bmo,
  niveau_geo, code_geo, libelle_geo, annee,
  CASE WHEN count_if(NOT nb_projets_recrutement_secret) = 0 THEN NULL ELSE sum(nb_projets_recrutement) END AS nb_projets_recrutement_minimum,
  CASE WHEN count_if(NOT nb_projets_difficiles_secret) = 0 THEN NULL ELSE sum(nb_projets_difficiles) END   AS nb_projets_difficiles_minimum,
  CASE WHEN count_if(NOT nb_projets_saisonniers_secret) = 0 THEN NULL ELSE sum(nb_projets_saisonniers) END AS nb_projets_saisonniers_minimum,
  CAST(count(*) AS INT) AS nb_cellules,
  CAST(count_if(nb_projets_recrutement_secret) AS INT) AS nb_cellules_secretes_recrutement,
  CAST(count_if(nb_projets_difficiles_secret) AS INT)  AS nb_cellules_secretes_difficiles,
  CAST(count_if(nb_projets_saisonniers_secret) AS INT) AS nb_cellules_secretes_saisonniers,
  count_if(nb_projets_recrutement_secret) = 0 AS est_complet_recrutement,
  count_if(nb_projets_difficiles_secret) = 0  AS est_complet_difficiles,
  count_if(nb_projets_saisonniers_secret) = 0 AS est_complet_saisonniers,
  min(_source_sha256) AS _source_sha256,
  min(_source_file) AS _source_file,
  current_timestamp() AS _gold_built_at
FROM grouped
GROUP BY code_metier_bmo, libelle_metier_bmo, niveau_geo, code_geo, libelle_geo, annee;

-- G8 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.gold.v_rome_v3_fap
COMMENT 'DARES correspondence ROME **V3** x qualification -> FAP341 / FAP228, with qualification labels and BMO availability. ROME V3 is NOT ROME 4.0 v62: no code_rome column, no BMO figures. depend_qualification = the FAP341 varies across classes for this ROME V3 code. Key: code_rome_v3, code_qualification.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'UNCONFIRMED (DARES); Licence Ouverte (BMO availability flag)',
               'source.attribution' = 'Source : Dares, nomenclature des familles professionnelles FAP-2021; France Travail – BMO',
               'primary_key' = 'code_rome_v3, code_qualification')
AS
SELECT d.code_rome_v3, d.libelle_rome_v3, d.code_qualification, q.libelle_qualification,
       d.code_fap341, f.libelle_fap341, f.code_fap228, f.libelle_fap228,
       f.code_fap228 IN (SELECT code_metier_bmo FROM career_intelligence.silver.bmo_2026) AS bmo_disponible,
       size(collect_set(d.code_fap341) OVER (PARTITION BY d.code_rome_v3)) > 1 AS depend_qualification,
       d._source_sha256, d._snapshot
FROM career_intelligence.silver.dares_rome_v3_fap341 d
JOIN career_intelligence.silver.fap2021 f ON f.code_fap341 = d.code_fap341
JOIN career_intelligence.silver.dares_qualification q ON q.code_qualification = d.code_qualification;

-- G9 -------------------------------------------------------------------------
CREATE OR REPLACE TABLE career_intelligence.gold.source_licence
COMMENT 'Licence, attribution and restrictions of each Gold object, for display by the application. Key: objet_gold.'
TBLPROPERTIES ('layer' = 'gold', 'source.license' = 'Project metadata',
               'source.attribution' = 'Career Intelligence project', 'primary_key' = 'objet_gold')
AS
SELECT * FROM VALUES
  ('metier', 'table', 'silver.rome_* (ROME 4.0 v62)', 'Licence Ouverte (fr-lo)', 'France Travail – ROME 4.0', true, NULL),
  ('v_metier_appellation', 'view', 'silver.rome_metier_appellation, silver.rome_appellation', 'Licence Ouverte (fr-lo)', 'France Travail – ROME 4.0', true, NULL),
  ('v_metier_competence', 'view', 'silver.rome_metier_* skill links, silver.rome_competence / rome_savoir / rome_contexte_travail', 'Licence Ouverte (fr-lo)', 'France Travail – ROME 4.0', true, NULL),
  ('v_metier_domaine_formation', 'view', 'silver.rome_metier_formacode, silver.formacode*', 'Licence Ouverte (fr-lo); Licence Ouverte 2.0 (lov2)', 'France Travail – ROME 4.0; Formacode® V14 – Centre Inffo', true, 'Formacode® is a registered trademark of Centre Inffo'),
  ('v_metier_formation_onisep', 'view', 'silver.onisep_* , silver.rome_metier', 'ODbL', 'Source : Onisep; France Travail – ROME 4.0', true, 'ODbL share-alike: any publicly used database derived from this object must be published under ODbL; display "Source : Onisep"'),
  ('v_fap', 'view', 'silver.fap2021, silver.bmo_2026', 'UNCONFIRMED (DARES FAP 2021); Licence Ouverte (BMO availability flag)', 'Source : Dares, nomenclature des familles professionnelles FAP-2021; France Travail – BMO', false, 'DARES reuse conditions to be confirmed before any public release'),
  ('bmo_recrutement', 'table', 'silver.bmo_2026', 'Licence Ouverte (fr-lo)', 'France Travail – Enquête Besoins en Main-d''Oeuvre (BMO) 2026', true, 'Values are minimums (statistical secrecy); never exact counts'),
  ('v_rome_v3_fap', 'view', 'silver.dares_rome_v3_fap341, silver.fap2021, silver.dares_qualification, silver.bmo_2026', 'UNCONFIRMED (DARES); Licence Ouverte (BMO availability flag)', 'Source : Dares, nomenclature des familles professionnelles FAP-2021; France Travail – BMO', false, 'ROME V3, not ROME 4.0 v62; DARES reuse conditions to be confirmed before any public release'),
  ('source_licence', 'table', 'project documentation (docs/DATA_SOURCES.md)', 'Project metadata', 'Career Intelligence project', true, NULL)
AS t(objet_gold, type_objet, sources, licence, attribution, licence_confirmee, restrictions);
