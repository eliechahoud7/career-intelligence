-- =============================================================================
-- Search layer (Phase 14): career_intelligence.search — 4 views over Gold, no copied data.
-- Source: career_intelligence.gold (read-only). Parameterized queries: sql/search/queries/.
--
-- Approved decisions
--   P1  Dedicated schema, views only (nothing materialized).
--   P3  Matching is done by the queries: case- and accent-insensitive substring
--       (COLLATE UNICODE_CI_AI + contains), every word required, exact match for codes.
--   P5  France Travail writes every apostrophe of the ROME texts as two apostrophes
--       (source file unix_texte_v462_utf8.csv, 6,635 sentences). Bronze, Silver and Gold
--       stay faithful to the source. ONLY v_metier_index corrects them, for display and
--       search, in the champs 'definition' and 'acces_metier'.
--   Separation: no view combines ROME v62 with BMO, FAP or ROME V3. ONISEP is not
--       reshaped here (queries read gold.v_metier_formation_onisep directly).
--       code_rome_parent is not used. No weight, score or rank column.
--   Licence: each view carries the licence of the Gold objects it reads
--       (property source.gold_objects), as published in gold.source_licence.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS career_intelligence.search
  COMMENT 'Search layer: views over gold and parameterized query contracts (sql/search/queries).';

-- S1 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.search.v_metier_index
COMMENT 'One row per searchable text of a ROME 4.0 v62 occupation: code, name, long and short job titles (short only when different), definition and access text (doubled apostrophes of the source corrected). Key: code_rome, champ, code_ogr_appellation.'
TBLPROPERTIES ('layer' = 'search', 'source.license' = 'Licence Ouverte (fr-lo)',
               'source.attribution' = 'France Travail – ROME 4.0',
               'source.gold_objects' = 'metier, v_metier_appellation',
               'primary_key' = 'code_rome, champ, code_ogr_appellation')
AS
SELECT code_rome, 'code_rome' AS champ, 1 AS ordre_champ, CAST(NULL AS STRING) AS code_ogr_appellation,
       code_rome AS texte, 0 AS nb_apostrophes_corrigees, _rome_version
FROM career_intelligence.gold.metier
UNION ALL
SELECT code_rome, 'libelle_rome', 2, NULL, libelle_rome, 0, _rome_version
FROM career_intelligence.gold.metier
UNION ALL
SELECT code_rome, 'appellation_long', 3, code_ogr_appellation, libelle_appellation_long, 0, _rome_version
FROM career_intelligence.gold.v_metier_appellation
UNION ALL
SELECT code_rome, 'appellation_court', 4, code_ogr_appellation, libelle_appellation_court, 0, _rome_version
FROM career_intelligence.gold.v_metier_appellation
WHERE libelle_appellation_court <> libelle_appellation_long
UNION ALL
SELECT code_rome, 'definition', 5, NULL, replace(definition, repeat(chr(39), 2), chr(39)),
       CAST((length(definition) - length(replace(definition, repeat(chr(39), 2), chr(39)))) AS INT), _rome_version
FROM career_intelligence.gold.metier
UNION ALL
SELECT code_rome, 'acces_metier', 6, NULL, replace(acces_metier, repeat(chr(39), 2), chr(39)),
       CAST((length(acces_metier) - length(replace(acces_metier, repeat(chr(39), 2), chr(39)))) AS INT), _rome_version
FROM career_intelligence.gold.metier;

-- S2 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.search.v_element_competence
COMMENT 'One row per ROME skill element (savoir-faire, savoir-être, savoir, contexte de travail) with the number of occupations linked to it (a count, not a weight). Link attributes (niveau_competence, coeur_metier) stay in gold.v_metier_competence. Key: type_element, code_ogr_element.'
TBLPROPERTIES ('layer' = 'search', 'source.license' = 'Licence Ouverte (fr-lo)',
               'source.attribution' = 'France Travail – ROME 4.0',
               'source.gold_objects' = 'v_metier_competence',
               'primary_key' = 'type_element, code_ogr_element')
AS
SELECT type_element, code_ogr_element, libelle_element, categorie, sous_categorie,
       code_ogr_macro_competence, libelle_macro_competence,
       CAST(count(DISTINCT code_rome) AS INT) AS nb_metiers,
       _rome_version
FROM career_intelligence.gold.v_metier_competence
GROUP BY type_element, code_ogr_element, libelle_element, categorie, sous_categorie,
         code_ogr_macro_competence, libelle_macro_competence, _rome_version;

-- S3 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.search.v_domaine_formation
COMMENT 'One row per Formacode V14 training domain linked to at least one ROME occupation, with the number of linked occupations (a count, not a weight). Links stay many-to-many in gold.v_metier_domaine_formation. Key: code_formacode.'
TBLPROPERTIES ('layer' = 'search', 'source.license' = 'Licence Ouverte (fr-lo); Licence Ouverte 2.0 (lov2)',
               'source.attribution' = 'France Travail – ROME 4.0; Formacode® V14 – Centre Inffo',
               'source.gold_objects' = 'v_metier_domaine_formation',
               'primary_key' = 'code_formacode')
AS
SELECT code_formacode, libelle_formacode, code_champ_semantique, libelle_champ_semantique,
       code_grand_domaine_formacode, libelle_grand_domaine_formacode, niveau, est_terme_feuille,
       code_formacode_parent,
       CAST(count(DISTINCT code_rome) AS INT) AS nb_metiers,
       _version, _source_sha256
FROM career_intelligence.gold.v_metier_domaine_formation
GROUP BY code_formacode, libelle_formacode, code_champ_semantique, libelle_champ_semantique,
         code_grand_domaine_formacode, libelle_grand_domaine_formacode, niveau, est_terme_feuille,
         code_formacode_parent, _version, _source_sha256;

-- S4 -------------------------------------------------------------------------
CREATE OR REPLACE VIEW career_intelligence.search.v_zone_geo
COMMENT 'One row per BMO 2026 geographical area (departement, region, national FR) with the number of FAP228 families published there. No ROME column. Key: niveau_geo, code_geo.'
TBLPROPERTIES ('layer' = 'search', 'source.license' = 'Licence Ouverte (fr-lo)',
               'source.attribution' = 'France Travail – Enquête Besoins en Main-d''Oeuvre (BMO) 2026',
               'source.gold_objects' = 'bmo_recrutement',
               'primary_key' = 'niveau_geo, code_geo')
AS
SELECT niveau_geo, code_geo, libelle_geo,
       CAST(count(DISTINCT code_fap228) AS INT) AS nb_familles_fap228,
       min(_source_sha256) AS _source_sha256
FROM career_intelligence.gold.bmo_recrutement
GROUP BY niveau_geo, code_geo, libelle_geo;
