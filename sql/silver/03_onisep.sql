-- =============================================================================
-- Silver tables: ONISEP Idéo open data (snapshot 20261109) — GENERATED once from a spec.
-- Source : career_intelligence.bronze.onisep_*   (read-only)
-- Target : career_intelligence.silver.onisep_*   (rebuilt deterministically)
--
-- Source data © Onisep — Open Database License (ODbL): attribution "Source : Onisep" is
-- required, and any publicly used database derived from these tables must be shared under
-- ODbL (share-alike). Every table carries source.license / source.attribution properties.
--
-- Rules
--   * Identifiers (MET.n, FOR.n, ROME codes, T-ITM / T-IDEO2 / REF ids) are kept verbatim.
--   * Labels: every whitespace run (space, tab, U+00A0, U+202F) -> one space, trimmed,
--     '' -> NULL. HTML / long descriptions: edges trimmed only, '' -> NULL (internal
--     non-breaking spaces are French typography and are kept).
--   * Nested XML parsed with from_xml / xpath and explicit schemas:
--       single-value blocks -> columns; small labelled lists -> ARRAY<STRUCT> (NULL when
--       the source element is empty); id-based relationships -> relationship tables.
--   * Unresolved references are KEPT and flagged, never dropped or corrected:
--       onisep_metier_rome.statut_code, *.formation_dans_catalogue, *.metier_associe_connu.
--   * Dates dd/MM/yyyy -> DATE. duree_formation loses its literal surrounding quotes.
--   * Training sheet <-> initial programme: same FOR.n identifier (1:1) — validated FK,
--     no separate table.
--   * All 10 Bronze lineage columns are kept (relationship rows: from the parent record).
-- =============================================================================

-- onisep_metier — key: identifiant
CREATE OR REPLACE TABLE career_intelligence.silver.onisep_metier
COMMENT 'ONISEP occupations (Idéo-Fiches métiers). Labels normalised; HTML descriptions trimmed only; small labelled lists as ARRAY<STRUCT>. ROME codes, required training and related occupations are in relationship tables. Key: identifiant. Source : Onisep (licence ODbL).'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'onisep', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep', 'primary_key' = 'identifiant')
AS
SELECT
  b.identifiant,
  nullif(regexp_replace(regexp_replace(b.nom_metier, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS nom_metier,
  nullif(regexp_replace(regexp_replace(b.libelle_feminin, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_feminin,
  nullif(regexp_replace(regexp_replace(b.libelle_masculin, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_masculin,
  nullif(regexp_replace(b.accroche_metier, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS accroche_metier,
  nullif(regexp_replace(b.format_court, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS format_court,
  nullif(regexp_replace(b.competences, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS competences,
  nullif(regexp_replace(b.condition_travail, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS condition_travail,
  nullif(regexp_replace(b.nature_travail, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS nature_travail,
  nullif(regexp_replace(b.acces_metier, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS acces_metier,
  nullif(regexp_replace(b.vie_professionnelle, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS vie_professionnelle,
  nullif(regexp_replace(regexp_replace(from_xml(b.niveau_acces_min, 'id STRING, libelle STRING').id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS niveau_acces_min_id,
  nullif(regexp_replace(regexp_replace(from_xml(b.niveau_acces_min, 'id STRING, libelle STRING').libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS niveau_acces_min_libelle,
  nullif(regexp_replace(regexp_replace(from_xml(b.secteurs_activite, 'metier_transverse STRING').metier_transverse, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS metier_transverse,
  transform(from_xml(b.synonymes, 'synonyme ARRAY<STRUCT<nom_metier: STRING, libelle_feminin: STRING, libelle_masculin: STRING>>').synonyme, s -> named_struct('nom_metier', nullif(regexp_replace(regexp_replace(s.nom_metier, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'libelle_feminin', nullif(regexp_replace(regexp_replace(s.libelle_feminin, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'libelle_masculin', nullif(regexp_replace(regexp_replace(s.libelle_masculin, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) AS synonymes,
  transform(from_xml(b.statuts, 'statut ARRAY<STRUCT<id: STRING, libelle: STRING>>').statut, s -> named_struct('id', nullif(regexp_replace(regexp_replace(s.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'libelle', nullif(regexp_replace(regexp_replace(s.libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) AS statuts,
  transform(from_xml(b.secteurs_activite, 'secteur_activite ARRAY<STRUCT<id: STRING, libelle: STRING>>').secteur_activite, s -> named_struct('id', nullif(regexp_replace(regexp_replace(s.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'libelle', nullif(regexp_replace(regexp_replace(s.libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) AS secteurs_activite,
  transform(from_xml(b.centres_interet, 'centre_interet ARRAY<STRUCT<id: STRING, libelle: STRING>>').centre_interet, s -> named_struct('id', nullif(regexp_replace(regexp_replace(s.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'libelle', nullif(regexp_replace(regexp_replace(s.libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) AS centres_interet,
  transform(from_xml(b.publications, 'publication ARRAY<STRUCT<code_librairie: STRING, titre_publication: STRING, editeur: STRING, annee: STRING, collection: STRING>>').publication, s -> named_struct('code_librairie', nullif(regexp_replace(regexp_replace(s.code_librairie, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'titre_publication', nullif(regexp_replace(regexp_replace(s.titre_publication, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'editeur', nullif(regexp_replace(regexp_replace(s.editeur, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'annee', nullif(regexp_replace(regexp_replace(s.annee, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'collection', nullif(regexp_replace(regexp_replace(s.collection, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) AS publications,
  transform(from_xml(b.sources_numeriques, 'source ARRAY<STRUCT<valeur: STRING, commentaire: STRING>>').source, s -> named_struct('valeur', nullif(regexp_replace(regexp_replace(s.valeur, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'commentaire', nullif(regexp_replace(regexp_replace(s.commentaire, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) AS sources_numeriques,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sha256,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.onisep_fiches_metiers b;

-- onisep_formation — key: identifiant
CREATE OR REPLACE TABLE career_intelligence.silver.onisep_formation
COMMENT 'ONISEP training sheets (Idéo-Fiches formations): trainings linked to at least one ONISEP occupation. identifiant = onisep_formation_initiale.identifiant (1:1). duree_formation without the literal quotes of the source. Key: identifiant. Source : Onisep (licence ODbL).'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'onisep', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep', 'primary_key' = 'identifiant')
AS
SELECT
  b.identifiant,
  nullif(regexp_replace(regexp_replace(b.code_scolarite, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS code_scolarite,
  nullif(regexp_replace(regexp_replace(b.libelle_complet, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_complet,
  nullif(regexp_replace(regexp_replace(b.sigle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS sigle,
  nullif(regexp_replace(regexp_replace(b.libelle_generique, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_generique,
  nullif(regexp_replace(regexp_replace(b.libelle_specifique, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_specifique,
  nullif(regexp_replace(regexp_replace(b.type_option, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS type_option,
  nullif(regexp_replace(regexp_replace(from_xml(b.type_Formation, 'type_formation_sigle STRING').type_formation_sigle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS type_formation_sigle,
  nullif(regexp_replace(regexp_replace(from_xml(b.type_Formation, 'type_formation_libelle_court STRING').type_formation_libelle_court, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS type_formation_libelle_court,
  nullif(regexp_replace(regexp_replace(from_xml(b.type_Formation, 'type_formation_libelle STRING').type_formation_libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS type_formation_libelle,
  nullif(regexp_replace(regexp_replace(regexp_replace(b.duree_formation, '^\\s*"|"\\s*$', ''), '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS duree_formation,
  nullif(regexp_replace(regexp_replace(b.niveau_certification, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS niveau_certification,
  nullif(regexp_replace(regexp_replace(b.niv_code, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS niv_code,
  nullif(regexp_replace(regexp_replace(from_xml(b.niveau_etudes, 'id STRING, libelle STRING').id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS niveau_etudes_id,
  nullif(regexp_replace(regexp_replace(from_xml(b.niveau_etudes, 'id STRING, libelle STRING').libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS niveau_etudes_libelle,
  nullif(regexp_replace(regexp_replace(from_xml(b.nsf_discipline, 'NSF_discipline_code STRING, NSF_discipline_libelle STRING').NSF_discipline_code, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS nsf_discipline_code,
  nullif(regexp_replace(regexp_replace(from_xml(b.nsf_discipline, 'NSF_discipline_code STRING, NSF_discipline_libelle STRING').NSF_discipline_libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS nsf_discipline_libelle,
  nullif(regexp_replace(regexp_replace(from_xml(b.nsf_fonction, 'NSF_fonction_code STRING, NSF_fonction_libelle STRING').NSF_fonction_code, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS nsf_fonction_code,
  nullif(regexp_replace(regexp_replace(from_xml(b.nsf_fonction, 'NSF_fonction_code STRING, NSF_fonction_libelle STRING').NSF_fonction_libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS nsf_fonction_libelle,
  transform(from_xml(b.nature_certificat, 'libelle_nature_certificat ARRAY<STRING>').libelle_nature_certificat, s -> nullif(regexp_replace(regexp_replace(s, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '')) AS natures_certificat,
  nullif(regexp_replace(regexp_replace(b.sous_tutelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS sous_tutelle,
  nullif(regexp_replace(regexp_replace(b.url, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS url,
  nullif(regexp_replace(b.descriptif_format_court, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS descriptif_format_court,
  nullif(regexp_replace(b.descriptif_acces, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS descriptif_acces,
  nullif(regexp_replace(b.attendus, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS attendus,
  nullif(regexp_replace(b.descriptif_poursuite_etudes, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS descriptif_poursuite_etudes,
  transform(from_xml(b.element_enseignement, 'element_enseignement_libelle ARRAY<STRING>').element_enseignement_libelle, s -> nullif(regexp_replace(regexp_replace(s, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '')) AS elements_enseignement,
  transform(from_xml(b.sous_domaines_web, 'sous_domaine_web ARRAY<STRUCT<id: STRING, libelle: STRING>>').sous_domaine_web, s -> named_struct('id', nullif(regexp_replace(regexp_replace(s.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'libelle', nullif(regexp_replace(regexp_replace(s.libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) AS sous_domaines_web,
  transform(from_xml(b.publications, 'publication ARRAY<STRUCT<code_librairie: STRING, titre_publication: STRING, editeur: STRING, annee: STRING, collection: STRING>>').publication, s -> named_struct('code_librairie', nullif(regexp_replace(regexp_replace(s.code_librairie, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'titre_publication', nullif(regexp_replace(regexp_replace(s.titre_publication, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'editeur', nullif(regexp_replace(regexp_replace(s.editeur, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'annee', nullif(regexp_replace(regexp_replace(s.annee, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''), 'collection', nullif(regexp_replace(regexp_replace(s.collection, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), ''))) AS publications,
  transform(from_xml(b.sources_numeriques, 'source ARRAY<STRING>').source, s -> nullif(regexp_replace(regexp_replace(s, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '')) AS sources_numeriques,
  nullif(regexp_replace(regexp_replace(b.annee_premiere_session, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS annee_premiere_session,
  nullif(regexp_replace(regexp_replace(b.annee_derniere_session, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS annee_derniere_session,
  to_date(b.creation_date, 'dd/MM/yyyy') AS creation_date,
  to_date(b.modification_date, 'dd/MM/yyyy') AS modification_date,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sha256,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.onisep_fiches_formations b;

-- onisep_formation_initiale — key: identifiant
CREATE OR REPLACE TABLE career_intelligence.silver.onisep_formation_initiale
COMMENT 'ONISEP initial training programmes (Idéo-Formations initiales en France), the full catalogue. identifiant = FOR.n extracted from url_onisep. code_nsf and domaines_sous_domaines are the source pipe-separated lists as arrays. Key: identifiant. Source : Onisep (licence ODbL).'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'onisep', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep', 'primary_key' = 'identifiant')
AS
SELECT
  regexp_extract(b.url_et_id_onisep, 'FOR\\.[0-9]+', 0) AS identifiant,
  nullif(regexp_replace(regexp_replace(b.url_et_id_onisep, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS url_onisep,
  nullif(regexp_replace(regexp_replace(b.libelle_formation_principal, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_formation_principal,
  nullif(regexp_replace(regexp_replace(b.sigle_formation, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS sigle_formation,
  nullif(regexp_replace(regexp_replace(b.sigle_type_formation, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS sigle_type_formation,
  nullif(regexp_replace(regexp_replace(b.libelle_type_formation, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_type_formation,
  nullif(regexp_replace(regexp_replace(b.code_scolarite, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS code_scolarite,
  nullif(regexp_replace(regexp_replace(b.code_rncp, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS code_rncp,
  CASE WHEN nullif(regexp_replace(regexp_replace(b.code_nsf, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') IS NULL THEN NULL ELSE transform(split(b.code_nsf, '\\|'), s -> nullif(regexp_replace(regexp_replace(s, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '')) END AS codes_nsf,
  nullif(regexp_replace(regexp_replace(b.duree, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS duree,
  nullif(regexp_replace(regexp_replace(b.niveau_de_sortie_indicatif, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS niveau_de_sortie_indicatif,
  nullif(regexp_replace(regexp_replace(b.niveau_de_certification, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS niveau_de_certification,
  nullif(regexp_replace(regexp_replace(b.libelle_niveau_de_certification, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_niveau_de_certification,
  nullif(regexp_replace(regexp_replace(b.tutelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS tutelle,
  CASE WHEN nullif(regexp_replace(regexp_replace(b.domaine_sous_domaine, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') IS NULL THEN NULL ELSE transform(split(b.domaine_sous_domaine, ' \\| '), s -> nullif(regexp_replace(regexp_replace(s, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '')) END AS domaines_sous_domaines,
  to_date(b.date_creation, 'dd/MM/yyyy') AS date_creation,
  to_date(b.date_de_modification, 'dd/MM/yyyy') AS date_de_modification,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sha256,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.onisep_formations_initiales b;

-- onisep_metier_rome — key: identifiant_metier, code_rome_source
CREATE OR REPLACE TABLE career_intelligence.silver.onisep_metier_rome
COMMENT 'ONISEP occupation -> ROME code, from <romesV3>, exactly as published. code_rome is set only when the code exists in silver.rome_metier; statut_code = valide | non_resolu (truncated or unknown codes are kept, never corrected). Key: identifiant_metier, code_rome_source. Source : Onisep (licence ODbL).'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'onisep', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep', 'primary_key' = 'identifiant_metier, code_rome_source')
AS
SELECT
  b.identifiant AS identifiant_metier,
  CAST(b.pos + 1 AS INT) AS position,
  b.code AS code_rome_source,
  m.code_rome,
  CASE WHEN m.code_rome IS NOT NULL THEN 'valide' ELSE 'non_resolu' END AS statut_code,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sha256,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM (SELECT f.*, r.pos, r.code FROM career_intelligence.bronze.onisep_fiches_metiers f
      LATERAL VIEW posexplode(xpath(f.romesV3, '/romesV3/romeV3/text()')) r AS pos, code) b
LEFT JOIN career_intelligence.silver.rome_metier m ON m.code_rome = b.code;

-- onisep_formation_metier — key: identifiant_formation, identifiant_metier
CREATE OR REPLACE TABLE career_intelligence.silver.onisep_formation_metier
COMMENT 'ONISEP training sheet -> ONISEP occupation, from <metiers_formation>. Only identifiers are kept (the embedded names/synonyms duplicate onisep_metier). Key: identifiant_formation, identifiant_metier. Source : Onisep (licence ODbL).'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'onisep', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep', 'primary_key' = 'identifiant_formation, identifiant_metier')
AS
SELECT
  b.identifiant AS identifiant_formation,
  CAST(r.pos + 1 AS INT) AS position,
  nullif(regexp_replace(regexp_replace(r.m.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS identifiant_metier,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sha256,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.onisep_fiches_formations b
LATERAL VIEW posexplode(from_xml(b.metiers_formation, 'metier ARRAY<STRUCT<id: STRING>>').metier) r AS pos, m;

-- onisep_metier_formation_min_requise — key: identifiant_metier, identifiant_formation
CREATE OR REPLACE TABLE career_intelligence.silver.onisep_metier_formation_min_requise
COMMENT 'ONISEP occupation -> minimum required training (FOR.n), from <formations_min_requise>. formation_dans_catalogue = the FOR id exists in onisep_formation_initiale; libelle_formation kept as published (the only information for ids outside the catalogue). Key: identifiant_metier, identifiant_formation. Source : Onisep (licence ODbL).'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'onisep', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep', 'primary_key' = 'identifiant_metier, identifiant_formation')
AS
SELECT
  b.identifiant AS identifiant_metier,
  CAST(r.pos + 1 AS INT) AS position,
  nullif(regexp_replace(regexp_replace(r.f.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS identifiant_formation,
  nullif(regexp_replace(regexp_replace(r.f.libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_formation,
  nullif(regexp_replace(regexp_replace(r.f.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') IN (SELECT regexp_extract(url_et_id_onisep, 'FOR\\.[0-9]+', 0) FROM career_intelligence.bronze.onisep_formations_initiales) AS formation_dans_catalogue,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sha256,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.onisep_fiches_metiers b
LATERAL VIEW posexplode(from_xml(b.formations_min_requise, 'formation_min_requise ARRAY<STRUCT<id: STRING, libelle: STRING>>').formation_min_requise) r AS pos, f;

-- onisep_metier_associe — key: identifiant_metier, identifiant_metier_associe
CREATE OR REPLACE TABLE career_intelligence.silver.onisep_metier_associe
COMMENT 'ONISEP occupation -> related occupation, from <metiers_associes>. metier_associe_connu = the MET id exists in onisep_metier; libelle kept as published. Key: identifiant_metier, identifiant_metier_associe. Source : Onisep (licence ODbL).'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'onisep', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep', 'primary_key' = 'identifiant_metier, identifiant_metier_associe')
AS
SELECT
  b.identifiant AS identifiant_metier,
  CAST(r.pos + 1 AS INT) AS position,
  nullif(regexp_replace(regexp_replace(r.a.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS identifiant_metier_associe,
  nullif(regexp_replace(regexp_replace(r.a.libelle, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_metier_associe,
  nullif(regexp_replace(regexp_replace(r.a.id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') IN (SELECT identifiant FROM career_intelligence.bronze.onisep_fiches_metiers) AS metier_associe_connu,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sha256,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.onisep_fiches_metiers b
LATERAL VIEW posexplode(from_xml(b.metiers_associes, 'metier_associe ARRAY<STRUCT<id: STRING, libelle: STRING>>').metier_associe) r AS pos, a;

-- onisep_formation_poursuite — key: identifiant_formation, identifiant_formation_poursuite
CREATE OR REPLACE TABLE career_intelligence.silver.onisep_formation_poursuite
COMMENT 'ONISEP training sheet -> possible further study (FOR.n, from the id attribute of <formation_poursuite_Etudes>). formation_dans_catalogue = id exists in onisep_formation_initiale. Key: identifiant_formation, identifiant_formation_poursuite. Source : Onisep (licence ODbL).'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'onisep', 'source.license' = 'ODbL', 'source.attribution' = 'Source : Onisep', 'primary_key' = 'identifiant_formation, identifiant_formation_poursuite')
AS
SELECT
  b.identifiant AS identifiant_formation,
  CAST(r.pos + 1 AS INT) AS position,
  nullif(regexp_replace(regexp_replace(r.p._id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS identifiant_formation_poursuite,
  nullif(regexp_replace(regexp_replace(r.p._VALUE, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_formation_poursuite,
  nullif(regexp_replace(regexp_replace(r.p._id, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') IN (SELECT regexp_extract(url_et_id_onisep, 'FOR\\.[0-9]+', 0) FROM career_intelligence.bronze.onisep_formations_initiales) AS formation_dans_catalogue,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sha256,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.onisep_fiches_formations b
LATERAL VIEW posexplode(from_xml(b.poursuites_etudes, 'poursuite_etudes STRUCT<formation_poursuite_Etudes: ARRAY<STRUCT<_id: STRING, _VALUE: STRING>>>').poursuite_etudes.formation_poursuite_Etudes) r AS pos, p;
