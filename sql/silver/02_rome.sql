-- =============================================================================
-- Silver tables: ROME 4.0 (v62) — GENERATED once from a spec; edit with care.
-- Source : career_intelligence.bronze.rome_*   (read-only)
-- Target : career_intelligence.silver.rome_*   (rebuilt deterministically)
--
-- Rules
--   * Empty strings -> NULL (nullif). Codes/identifiers keep their text values and,
--     where possible, their source column names.
--   * position_phrase, numero_ordre -> INT. Flags keep source values (O/N, oui/non,
--     Principale) — no boolean reinterpretation.
--   * The polymorphic link table bronze.rome_liens_rome_referentiels is split by its
--     block identifiers (code_compo_bloc / code_rubrique):
--        2   -> rome_metier_appellation        5/1 -> rome_metier_savoir_faire
--        5/2 -> rome_metier_savoir_etre        5/3 -> rome_metier_savoir
--        6   -> rome_metier_contexte_travail   (block 1 = occupation self-link, validated only)
--   * coeur_metier comes from bronze.rome_coherence_item, which holds exactly the same
--     (code_rome, code_ogr) pairs as blocks 5 and 6.
--   * Macro-competence vs competence is kept: rome_competence.nature, parent in
--     rome_competence.code_ogr_macro_comp, hierarchy in rome_macro_competence. Know-how
--     links may target either level (rome_metier_savoir_faire.niveau_competence).
--   * Not carried to Silver (redundant): cr_gd_dp_appellations (display tree),
--     composition_bloc / descriptif_rubrique (block labels), item (union of competence,
--     savoir, contexte), type_referentiel (empty).
--   * All 9 lineage columns are kept from the row's primary Bronze table.
-- =============================================================================

-- rome_metier — key: code_rome
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier
COMMENT 'ROME occupations (fiches metier) with domain and RIASEC profile (1:1 joins). Key: code_rome. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome')
AS
SELECT
  b.code_rome,
  b.code_ogr,
  nullif(b.code_fiche_metier, '') AS code_fiche_metier,
  nullif(b.libelle_rome, '') AS libelle_rome,
  d.code_grand_domaine,
  d.code_domaine_professionel AS code_domaine_professionnel,
  nullif(r.riasec_majeur, '') AS riasec_majeur,
  nullif(r.riasec_mineur, '') AS riasec_mineur,
  nullif(b.transition_eco, '') AS transition_eco,
  nullif(b.transition_num, '') AS transition_num,
  nullif(b.transition_demo, '') AS transition_demo,
  nullif(b.emploi_reglemente, '') AS emploi_reglemente,
  nullif(b.emploi_cadre, '') AS emploi_cadre,
  nullif(b.code_rome_parent, '') AS code_rome_parent,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_referentiel_code_rome b
LEFT JOIN career_intelligence.bronze.rome_cr_gd_dp d ON d.code_rome = b.code_rome
LEFT JOIN career_intelligence.bronze.rome_referentiel_code_rome_riasec r ON r.code_rome = b.code_rome;

-- rome_grand_domaine — key: code_grand_domaine
CREATE OR REPLACE TABLE career_intelligence.silver.rome_grand_domaine
COMMENT 'ROME top-level domains. Key: code_grand_domaine. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_grand_domaine')
AS
SELECT
  b.code_grand_domaine,
  nullif(b.libelle_grand_domaine, '') AS libelle_grand_domaine,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_grand_domaine b;

-- rome_domaine_professionnel — key: code_domaine_professionnel
CREATE OR REPLACE TABLE career_intelligence.silver.rome_domaine_professionnel
COMMENT 'ROME professional domains; code_grand_domaine taken from bronze.rome_cr_gd_dp (one per domain). Key: code_domaine_professionnel. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_domaine_professionnel')
AS
SELECT
  b.code_domaine_professionnel,
  nullif(b.libelle_domaine_professionnel, '') AS libelle_domaine_professionnel,
  g.code_grand_domaine,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_domaine_professionnel b
LEFT JOIN (SELECT DISTINCT code_domaine_professionel, code_grand_domaine FROM career_intelligence.bronze.rome_cr_gd_dp) g
  ON g.code_domaine_professionel = b.code_domaine_professionnel;

-- rome_appellation — key: code_ogr
CREATE OR REPLACE TABLE career_intelligence.silver.rome_appellation
COMMENT 'ROME job titles (appellations); classification PRINCIPALE / SYNONYME. Key: code_ogr. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_ogr')
AS
SELECT
  b.code_ogr,
  b.code_rome,
  nullif(b.libelle_appellation_long, '') AS libelle_appellation_long,
  nullif(b.libelle_appellation_court, '') AS libelle_appellation_court,
  nullif(b.classification, '') AS classification,
  nullif(b.peu_usite, '') AS peu_usite,
  nullif(b.transition_eco, '') AS transition_eco,
  nullif(b.transition_num, '') AS transition_num,
  nullif(b.transition_demo, '') AS transition_demo,
  nullif(b.emploi_reglemente, '') AS emploi_reglemente,
  nullif(b.emploi_cadre, '') AS emploi_cadre,
  nullif(b.origine, '') AS origine,
  nullif(b.code_rome_parent, '') AS code_rome_parent,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_referentiel_appellation b;

-- rome_competence — key: code_ogr
CREATE OR REPLACE TABLE career_intelligence.silver.rome_competence
COMMENT 'ROME skills, both levels: nature = Macro-compétence (506) or Compétence (19582); code_ogr_macro_comp = parent macro-competence of a Compétence (NULL for macros). Key: code_ogr. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_ogr')
AS
SELECT
  b.code_ogr,
  nullif(b.nature, '') AS nature,
  nullif(b.libelle_competence, '') AS libelle_competence,
  nullif(b.definition, '') AS definition,
  nullif(b.code_ogr_macro_comp, '') AS code_ogr_macro_comp,
  nullif(b.code_macro_comp, '') AS code_macro_comp,
  nullif(b.cat_comp, '') AS cat_comp,
  nullif(b.sous_cat_comp, '') AS sous_cat_comp,
  nullif(b.transition_eco, '') AS transition_eco,
  nullif(b.transition_num, '') AS transition_num,
  nullif(b.libelle_heterogeneite, '') AS libelle_heterogeneite,
  nullif(b.libelle_origine, '') AS libelle_origine,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_referentiel_competence b;

-- rome_macro_competence — key: code_ogr
CREATE OR REPLACE TABLE career_intelligence.silver.rome_macro_competence
COMMENT 'ROME macro-competences with their hierarchy path (domaine > enjeu > objectif) and RIASEC. has_child_competence = false for the 16 savoir-etre macros. Key: code_ogr. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_ogr')
AS
SELECT
  b.code_ogr,
  nullif(b.code_macro_comp, '') AS code_macro_competence,
  nullif(b.libelle_competence, '') AS libelle_macro_competence,
  nullif(b.cat_comp, '') AS cat_comp,
  nullif(b.sous_cat_comp, '') AS sous_cat_comp,
  a.code_domaine_competence,
  a.domaine_competence,
  a.code_enjeu,
  a.enjeu,
  a.code_objectif,
  a.objectif,
  a.has_child_competence,
  nullif(r.riasec_majeur, '') AS riasec_majeur,
  nullif(r.riasec_mineur, '') AS riasec_mineur,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_referentiel_competence b
JOIN (SELECT code_ogr_macro_competence,
             first(nullif(code_domaine_competence, '')) AS code_domaine_competence,
             first(nullif(domaine_competence, '')) AS domaine_competence,
             first(nullif(code_enjeu, '')) AS code_enjeu, first(nullif(enjeu, '')) AS enjeu,
             first(nullif(code_objectif, '')) AS code_objectif,
             first(nullif(objectif, '')) AS objectif,
             count_if(code_ogr_competence <> '') > 0 AS has_child_competence
      FROM career_intelligence.bronze.rome_arborescence_competences GROUP BY code_ogr_macro_competence) a
  ON a.code_ogr_macro_competence = b.code_ogr
LEFT JOIN career_intelligence.bronze.rome_referentiel_macro_competence_riasec r ON r.code_ogr = b.code_ogr
WHERE b.code_macro_comp <> '';

-- rome_savoir — key: code_ogr_savoir
CREATE OR REPLACE TABLE career_intelligence.silver.rome_savoir
COMMENT 'ROME knowledge items (savoirs). Key: code_ogr_savoir. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_ogr_savoir')
AS
SELECT
  b.code_ogr_savoir,
  nullif(b.libelle_savoir, '') AS libelle_savoir,
  nullif(b.categorie_savoir, '') AS categorie_savoir,
  nullif(b.sous_categorie_savoir, '') AS sous_categorie_savoir,
  nullif(b.transition_eco, '') AS transition_eco,
  nullif(b.transition_num, '') AS transition_num,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_referentiel_savoir b;

-- rome_contexte_travail — key: code_ogr
CREATE OR REPLACE TABLE career_intelligence.silver.rome_contexte_travail
COMMENT 'ROME work contexts. Key: code_ogr. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_ogr')
AS
SELECT
  b.code_ogr,
  nullif(b.libelle_cont_travail, '') AS libelle_cont_travail,
  nullif(b.code_type_cont_trav, '') AS code_type_cont_trav,
  nullif(b.libelle_type_cont_trav, '') AS libelle_type_cont_trav,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_referentiel_contexte_travail b;

-- rome_centre_interet — key: code_centre_interet
CREATE OR REPLACE TABLE career_intelligence.silver.rome_centre_interet
COMMENT 'ROME centres of interest (definitions are multi-line). Key: code_centre_interet. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_centre_interet')
AS
SELECT
  b.code_centre_interet,
  nullif(b.libelle_centre_interet, '') AS libelle_centre_interet,
  nullif(b.definition_centre_interet, '') AS definition_centre_interet,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_centre_interet b;

-- rome_secteur_activite — key: code_sect_activite
CREATE OR REPLACE TABLE career_intelligence.silver.rome_secteur_activite
COMMENT 'ROME activity sectors. Key: code_sect_activite. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_sect_activite')
AS
SELECT
  b.code_sect_activite,
  nullif(b.libelle_sect_activite, '') AS libelle_sect_activite,
  nullif(b.definition_sect_activite, '') AS definition_sect_activite,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_secteur_activite b;

-- rome_sous_secteur_activite — key: code_ss_sect_activite
CREATE OR REPLACE TABLE career_intelligence.silver.rome_sous_secteur_activite
COMMENT 'ROME activity sub-sectors. Key: code_ss_sect_activite. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_ss_sect_activite')
AS
SELECT
  b.code_ss_sect_activite,
  nullif(b.libelle_ss_sect_activite, '') AS libelle_ss_sect_activite,
  nullif(b.definition_ss_sect_activite, '') AS definition_ss_sect_activite,
  b.code_sect_activite,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_sous_secteur_activite b;

-- rome_theme — key: code_theme
CREATE OR REPLACE TABLE career_intelligence.silver.rome_theme
COMMENT 'ROME themes. Key: code_theme. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_theme')
AS
SELECT
  b.code_theme,
  nullif(b.libelle_theme, '') AS libelle_theme,
  nullif(b.definition_theme, '') AS definition_theme,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_themes b;

-- rome_secteur_naf — key: code_secteur_naf
CREATE OR REPLACE TABLE career_intelligence.silver.rome_secteur_naf
COMMENT 'NAF sectors used by ROME. code_tech_secteur_naf is a technical id; occupation links use code_secteur_naf. Key: code_secteur_naf. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_secteur_naf')
AS
SELECT
  b.code_secteur_naf,
  b.code_tech_secteur_naf,
  nullif(b.libelle_secteur_naf, '') AS libelle_secteur_naf,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_secteur_naf b;

-- rome_metier_appellation — key: code_rome, code_ogr_appellation
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_appellation
COMMENT 'Occupation -> job title (liens block 2). Key: code_rome, code_ogr_appellation. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_ogr_appellation')
AS
SELECT
  l.code_rome,
  l.code_ogr AS code_ogr_appellation,
  l._source_resource,
  l._source_url,
  l._source_file,
  l._source_archive_sha256,
  l._source_encoding,
  l._rome_version,
  l._source_row,
  l._run_id,
  l._ingested_at
FROM career_intelligence.bronze.rome_liens_rome_referentiels l
WHERE l.code_compo_bloc = '2' AND l.code_rubrique = '';

-- rome_metier_savoir_faire — key: code_rome, code_ogr_competence
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_savoir_faire
COMMENT 'Occupation -> know-how (liens block 5 / rubrique 1). The target is either a Compétence or directly a Macro-compétence: see niveau_competence. coeur_metier from bronze.rome_coherence_item. Key: code_rome, code_ogr_competence. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_ogr_competence')
AS
SELECT
  l.code_rome,
  l.code_ogr AS code_ogr_competence,
  k.nature AS niveau_competence,
  nullif(c.coeur_metier, '') AS coeur_metier,
  l._source_resource,
  l._source_url,
  l._source_file,
  l._source_archive_sha256,
  l._source_encoding,
  l._rome_version,
  l._source_row,
  l._run_id,
  l._ingested_at
FROM career_intelligence.bronze.rome_liens_rome_referentiels l
JOIN career_intelligence.bronze.rome_referentiel_competence k ON k.code_ogr = l.code_ogr
LEFT JOIN career_intelligence.bronze.rome_coherence_item c ON c.code_rome = l.code_rome AND c.code_ogr = l.code_ogr
WHERE l.code_compo_bloc = '5' AND l.code_rubrique = '1';

-- rome_metier_savoir_etre — key: code_rome, code_ogr_competence
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_savoir_etre
COMMENT 'Occupation -> soft skill (liens block 5 / rubrique 2); targets are the 16 savoir-etre macro-competences. coeur_metier from bronze.rome_coherence_item. Key: code_rome, code_ogr_competence. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_ogr_competence')
AS
SELECT
  l.code_rome,
  l.code_ogr AS code_ogr_competence,
  nullif(c.coeur_metier, '') AS coeur_metier,
  l._source_resource,
  l._source_url,
  l._source_file,
  l._source_archive_sha256,
  l._source_encoding,
  l._rome_version,
  l._source_row,
  l._run_id,
  l._ingested_at
FROM career_intelligence.bronze.rome_liens_rome_referentiels l
LEFT JOIN career_intelligence.bronze.rome_coherence_item c ON c.code_rome = l.code_rome AND c.code_ogr = l.code_ogr
WHERE l.code_compo_bloc = '5' AND l.code_rubrique = '2';

-- rome_metier_savoir — key: code_rome, code_ogr_savoir
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_savoir
COMMENT 'Occupation -> knowledge (liens block 5 / rubrique 3). coeur_metier from bronze.rome_coherence_item. Key: code_rome, code_ogr_savoir. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_ogr_savoir')
AS
SELECT
  l.code_rome,
  l.code_ogr AS code_ogr_savoir,
  nullif(c.coeur_metier, '') AS coeur_metier,
  l._source_resource,
  l._source_url,
  l._source_file,
  l._source_archive_sha256,
  l._source_encoding,
  l._rome_version,
  l._source_row,
  l._run_id,
  l._ingested_at
FROM career_intelligence.bronze.rome_liens_rome_referentiels l
LEFT JOIN career_intelligence.bronze.rome_coherence_item c ON c.code_rome = l.code_rome AND c.code_ogr = l.code_ogr
WHERE l.code_compo_bloc = '5' AND l.code_rubrique = '3';

-- rome_metier_contexte_travail — key: code_rome, code_ogr_contexte
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_contexte_travail
COMMENT 'Occupation -> work context (liens block 6). coeur_metier from bronze.rome_coherence_item. Key: code_rome, code_ogr_contexte. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_ogr_contexte')
AS
SELECT
  l.code_rome,
  l.code_ogr AS code_ogr_contexte,
  nullif(c.coeur_metier, '') AS coeur_metier,
  l._source_resource,
  l._source_url,
  l._source_file,
  l._source_archive_sha256,
  l._source_encoding,
  l._rome_version,
  l._source_row,
  l._run_id,
  l._ingested_at
FROM career_intelligence.bronze.rome_liens_rome_referentiels l
LEFT JOIN career_intelligence.bronze.rome_coherence_item c ON c.code_rome = l.code_rome AND c.code_ogr = l.code_ogr
WHERE l.code_compo_bloc = '6' AND l.code_rubrique = '';

-- rome_metier_texte — key: code_rome, libelle_type_texte, position_phrase
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_texte
COMMENT 'Occupation texts by sentence: libelle_type_texte = definition | acces_metier. Key: code_rome, libelle_type_texte, position_phrase. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, libelle_type_texte, position_phrase')
AS
SELECT
  b.code_rome,
  b.code_compo_bloc,
  nullif(b.libelle_type_texte, '') AS libelle_type_texte,
  CAST(b.position_phrase AS INT) AS position_phrase,
  nullif(b.libelle_texte, '') AS libelle_texte,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_texte b;

-- rome_metier_mobilite — key: code_rome, code_rome_cible
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_mobilite
COMMENT 'Career mobility: occupation -> target occupation, ordered. Key: code_rome, code_rome_cible. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_rome_cible')
AS
SELECT
  b.code_rome,
  b.code_rome_cible,
  CAST(b.numero_ordre AS INT) AS numero_ordre,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_rubrique_mobilite b;

-- rome_metier_centre_interet — key: code_rome, code_centre_interet
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_centre_interet
COMMENT 'Occupation -> centre of interest; principal = oui for exactly one per occupation. Key: code_rome, code_centre_interet. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_centre_interet')
AS
SELECT
  b.code_rome,
  b.code_centre_interet,
  nullif(b.principal, '') AS principal,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_arborescence_centre_interet b;

-- rome_metier_secteur_activite — key: code_rome, code_sect_activite, code_ss_sect_activite
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_secteur_activite
COMMENT 'Occupation -> activity sector, optionally at sub-sector level (code_ss_sect_activite NULL = sector-level link). principal = oui once per occupation. Key: code_rome, code_sect_activite, code_ss_sect_activite. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_sect_activite, code_ss_sect_activite')
AS
SELECT
  b.code_rome,
  b.code_sect_activite,
  nullif(b.code_ss_sect_activite, '') AS code_ss_sect_activite,
  nullif(b.principal, '') AS principal,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_arborescence_secteur_activite b;

-- rome_metier_theme — key: code_rome, code_theme
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_theme
COMMENT 'Occupation -> theme. Key: code_rome, code_theme. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_theme')
AS
SELECT
  b.code_rome,
  b.code_theme,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_arborescence_thematique b;

-- rome_metier_secteur_naf — key: code_rome, code_secteur_naf
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_secteur_naf
COMMENT 'Occupation -> NAF sector (joins rome_secteur_naf.code_secteur_naf). Key: code_rome, code_secteur_naf. Source: ROME 4.0 (bronze.rome_*), empty strings -> NULL.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome', 'primary_key' = 'code_rome, code_secteur_naf')
AS
SELECT
  b.code_rome,
  b.code_secteur_naf,
  b._source_resource,
  b._source_url,
  b._source_file,
  b._source_archive_sha256,
  b._source_encoding,
  b._rome_version,
  b._source_row,
  b._run_id,
  b._ingested_at
FROM career_intelligence.bronze.rome_arborescence_secteur_naf b;
