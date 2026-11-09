-- =============================================================================
-- Silver table: France Travail BMO 2026
-- Source : career_intelligence.bronze.bmo_2026  (read-only)
-- Target : career_intelligence.silver.bmo_2026  (rebuilt deterministically)
--
-- Transformations (only these):
--   1. Measures (source met / xmet / smet, named nb_projets_* since staging)
--      -> INT. Strict CAST: any value other than digits or '*' makes the
--      statement fail instead of silently producing NULL.
--   2. '*' (statistical secrecy) -> NULL.
--   3. One BOOLEAN flag per measure: <measure>_secret = original value was '*'.
--   4. Labels: every run of whitespace — spaces, tabs, non-breaking spaces
--      (U+00A0, U+202F) — becomes one normal space, then leading/trailing
--      spaces are removed. (SQL trim() alone does not remove U+00A0.)
--   5. Codes (occupation, family, region, department, bassin, CLPE), annee and
--      all lineage columns are copied unchanged (codes stay text: '01', '2A').
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS career_intelligence.silver
  COMMENT 'Cleaned, typed, source-specific tables derived from bronze.';

CREATE OR REPLACE TABLE career_intelligence.silver.bmo_2026
COMMENT 'France Travail BMO 2026, cleaned: measures as INT (NULL = statistical secrecy, see *_secret flags), labels whitespace-normalised. Grain: FAP2021 occupation x department x bassin d''emploi x CLPE. Source: career_intelligence.bronze.bmo_2026.'
TBLPROPERTIES (
  'layer' = 'silver',
  'source.table' = 'career_intelligence.bronze.bmo_2026',
  'source.raw_sha256' = '735d0443b799b4c18c145055f87244a355a48b6286ee98ddbab272491d9792e0'
)
AS
SELECT
  annee,
  code_metier_bmo,
  regexp_replace(regexp_replace(libelle_metier_bmo,     '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', '') AS libelle_metier_bmo,
  code_famille_metier,
  regexp_replace(regexp_replace(libelle_famille_metier, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', '') AS libelle_famille_metier,
  code_region,
  regexp_replace(regexp_replace(libelle_region,         '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', '') AS libelle_region,
  code_departement,
  regexp_replace(regexp_replace(libelle_departement,    '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', '') AS libelle_departement,
  code_bassin_emploi,
  regexp_replace(regexp_replace(libelle_bassin_emploi,  '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', '') AS libelle_bassin_emploi,
  code_clpe,

  CASE WHEN nb_projets_recrutement = '*' THEN NULL ELSE CAST(nb_projets_recrutement AS INT) END AS nb_projets_recrutement,
  nb_projets_recrutement = '*'                                                                AS nb_projets_recrutement_secret,
  CASE WHEN nb_projets_difficiles  = '*' THEN NULL ELSE CAST(nb_projets_difficiles  AS INT) END AS nb_projets_difficiles,
  nb_projets_difficiles = '*'                                                                 AS nb_projets_difficiles_secret,
  CASE WHEN nb_projets_saisonniers = '*' THEN NULL ELSE CAST(nb_projets_saisonniers AS INT) END AS nb_projets_saisonniers,
  nb_projets_saisonniers = '*'                                                                AS nb_projets_saisonniers_secret,

  _source_resource,
  _source_url,
  _source_file,
  _source_sha256,
  _source_sheet,
  _source_row,
  _run_id,
  _ingested_at
FROM career_intelligence.bronze.bmo_2026;
