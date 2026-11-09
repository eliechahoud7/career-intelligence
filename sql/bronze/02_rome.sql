-- =============================================================================
-- Bronze tables: France Travail ROME 4.0 (v62) — one table per CSV of the official archive.
-- GENERATED from data/staging/france_travail/rome/v62/rome_v62.manifest.json (run 9e0aacb660b4).
--
-- Prerequisites
--   1. python -m career_intelligence.ingestion.rome
--   2. Upload (PowerShell):
--        databricks fs cp data\raw\france_travail\rome\v62\rome_open_data_csv.zip `
--          dbfs:/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/raw/rome_open_data_csv.zip --profile career-intelligence
--        databricks fs cp -r data\staging\france_travail\rome\v62 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet --profile career-intelligence
--
-- Each table is a 1:1 copy of its staging Parquet: source columns exactly as published
-- (text; empty fields = ''), plus lineage columns _source_resource, _source_url, _source_file, _source_archive_sha256, _source_encoding, _rome_version, _source_row, _run_id, _ingested_at.
-- Nothing is joined, split or typed here.
-- =============================================================================


CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_arborescence_centre_interet
COMMENT 'ROME 4.0 v62 raw - arborescence centre interet. Source member unix_arborescence_centre_interet_v462_utf8.csv (utf-8). Natural key: code_centre_interet, code_rome. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_arborescence_centre_interet_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/arborescence_centre_interet.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_arborescence_competences
COMMENT 'ROME 4.0 v62 raw - skill hierarchy domaine > enjeu > objectif > macro-competence > competence. Source member unix_arborescence_competences_v462_utf8.csv (utf-8). Natural key: code_ogr_macro_competence, code_ogr_competence. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_arborescence_competences_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/arborescence_competences.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_arborescence_secteur_activite
COMMENT 'ROME 4.0 v62 raw - arborescence secteur activite. Source member unix_arborescence_secteur_activite_v462_utf8.csv (utf-8). Natural key: none. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_arborescence_secteur_activite_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/arborescence_secteur_activite.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_arborescence_secteur_naf
COMMENT 'ROME 4.0 v62 raw - arborescence secteur naf. Source member unix_arborescence_secteur_naf_v462_utf8.csv (cp1252). Natural key: code_secteur_naf, code_rome. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_arborescence_secteur_naf_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/arborescence_secteur_naf.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_arborescence_thematique
COMMENT 'ROME 4.0 v62 raw - arborescence thematique. Source member unix_arborescence_thematique_v462_utf8.csv (utf-8). Natural key: code_theme, code_rome. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_arborescence_thematique_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/arborescence_thematique.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_centre_interet
COMMENT 'ROME 4.0 v62 raw - centre interet. Source member unix_centre_interet_v462_utf8.csv (utf-8). Natural key: code_centre_interet. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_centre_interet_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/centre_interet.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_coherence_item
COMMENT 'ROME 4.0 v62 raw - occupation x item, coeur_metier flag. Source member unix_coherence_item_v462_utf8.csv (utf-8). Natural key: code_rome, code_ogr. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_coherence_item_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/coherence_item.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_composition_bloc
COMMENT 'ROME 4.0 v62 raw - composition bloc. Source member unix_composition_bloc_v462_utf8.csv (utf-8). Natural key: code_compo_bloc. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_composition_bloc_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/composition_bloc.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_cr_gd_dp
COMMENT 'ROME 4.0 v62 raw - cr gd dp. Source member unix_cr_gd_dp_v462_utf8.csv (utf-8). Natural key: code_rome. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_cr_gd_dp_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/cr_gd_dp.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_cr_gd_dp_appellations
COMMENT 'ROME 4.0 v62 raw - cr gd dp appellations. Source member unix_cr_gd_dp_appellations_v462_utf8.csv (utf-8). Natural key: none. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_cr_gd_dp_appellations_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/cr_gd_dp_appellations.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_descriptif_rubrique
COMMENT 'ROME 4.0 v62 raw - descriptif rubrique. Source member unix_descriptif_rubrique_v462_utf8.csv (utf-8). Natural key: code_rubrique. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_descriptif_rubrique_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/descriptif_rubrique.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_domaine_professionnel
COMMENT 'ROME 4.0 v62 raw - domaine professionnel. Source member unix_domaine_professionnel_v462_utf8.csv (utf-8). Natural key: code_domaine_professionnel. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_domaine_professionnel_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/domaine_professionnel.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_grand_domaine
COMMENT 'ROME 4.0 v62 raw - grand domaine. Source member unix_grand_domaine_v462_utf8.csv (utf-8). Natural key: code_grand_domaine. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_grand_domaine_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/grand_domaine.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_item
COMMENT 'ROME 4.0 v62 raw - union of skills, knowledge and work contexts by code_ogr. Source member unix_item_v462_utf8.csv (utf-8). Natural key: code_ogr. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_item_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/item.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_liens_rome_referentiels
COMMENT 'ROME 4.0 v62 raw - POLYMORPHIC link occupation -> code_ogr; target depends on code_compo_bloc/code_rubrique. Source member unix_liens_rome_referentiels_v462_utf8.csv (utf-8). Natural key: code_rome, code_compo_bloc, code_rubrique, code_ogr. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_liens_rome_referentiels_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/liens_rome_referentiels.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_referentiel_appellation
COMMENT 'ROME 4.0 v62 raw - job titles (appellations) per ROME code. Source member unix_referentiel_appellation_v462_utf8.csv (utf-8). Natural key: code_ogr. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_referentiel_appellation_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/referentiel_appellation.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_referentiel_code_rome
COMMENT 'ROME 4.0 v62 raw - occupations (fiches ROME). Source member unix_referentiel_code_rome_v462_utf8.csv (utf-8). Natural key: code_rome. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_referentiel_code_rome_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/referentiel_code_rome.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_referentiel_code_rome_riasec
COMMENT 'ROME 4.0 v62 raw - referentiel code rome riasec. Source member unix_referentiel_code_rome_riasec_v462_utf8.csv (utf-8). Natural key: code_rome. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_referentiel_code_rome_riasec_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/referentiel_code_rome_riasec.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_referentiel_competence
COMMENT 'ROME 4.0 v62 raw - skills: savoir-faire and savoir-etre. Source member unix_referentiel_competence_v462_utf8.csv (utf-8). Natural key: code_ogr. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_referentiel_competence_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/referentiel_competence.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_referentiel_contexte_travail
COMMENT 'ROME 4.0 v62 raw - work contexts. Source member unix_referentiel_contexte_travail_v462_utf8.csv (utf-8). Natural key: code_ogr. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_referentiel_contexte_travail_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/referentiel_contexte_travail.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_referentiel_macro_competence_riasec
COMMENT 'ROME 4.0 v62 raw - referentiel macro competence riasec. Source member unix_referentiel_macro_competence_riasec_v462_utf8.csv (utf-8). Natural key: code_ogr. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_referentiel_macro_competence_riasec_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/referentiel_macro_competence_riasec.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_referentiel_savoir
COMMENT 'ROME 4.0 v62 raw - knowledge items (savoirs). Source member unix_referentiel_savoir_v462_utf8.csv (utf-8). Natural key: code_ogr_savoir. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_referentiel_savoir_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/referentiel_savoir.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_rubrique_mobilite
COMMENT 'ROME 4.0 v62 raw - career mobility occupation -> target occupation. Source member unix_rubrique_mobilite_v462_utf8.csv (utf-8). Natural key: code_rome, code_rome_cible. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_rubrique_mobilite_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/rubrique_mobilite.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_secteur_activite
COMMENT 'ROME 4.0 v62 raw - secteur activite. Source member unix_secteur_activite_v462_utf8.csv (utf-8). Natural key: code_sect_activite. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_secteur_activite_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/secteur_activite.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_secteur_naf
COMMENT 'ROME 4.0 v62 raw - secteur naf. Source member unix_secteur_naf_v462_utf8.csv (utf-8). Natural key: code_tech_secteur_naf. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_secteur_naf_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/secteur_naf.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_sous_secteur_activite
COMMENT 'ROME 4.0 v62 raw - sous secteur activite. Source member unix_sous_secteur_activite_v462_utf8.csv (utf-8). Natural key: code_ss_sect_activite. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_sous_secteur_activite_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/sous_secteur_activite.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_texte
COMMENT 'ROME 4.0 v62 raw - occupation texts (definition, acces_metier) by sentence. Source member unix_texte_v462_utf8.csv (utf-8). Natural key: code_rome, code_compo_bloc, libelle_type_texte, position_phrase. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_texte_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/texte.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_themes
COMMENT 'ROME 4.0 v62 raw - themes. Source member unix_themes_v462_utf8.csv (utf-8). Natural key: code_theme. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_themes_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/themes.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_type_referentiel
COMMENT 'ROME 4.0 v62 raw - type referentiel. Source member unix_type_referentiel_v462_utf8.csv (utf-8). Natural key: none. Licence Ouverte.'
TBLPROPERTIES ('layer' = 'bronze', 'source.resource' = 'rome_bulk_csv', 'source.rome_version' = '62',
               'source.member' = 'unix_type_referentiel_v462_utf8.csv', 'source.raw_sha256' = 'ae63cf9155c59710175ed214b9ad4310e5d52c88582eb9a8c90e8505cacf7fcb')
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/france_travail/rome/v62/parquet/type_referentiel.parquet`;
