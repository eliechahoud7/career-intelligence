-- =============================================================================
-- Silver tables: Formacode V14 + ROME 4.0 v62 <-> Formacode (snapshot rome_v62_formacode_v14)
-- GENERATED once from a spec. Source: career_intelligence.bronze (read-only).
--
-- Thesaurus: Formacode® V14 – Centre Inffo, Licence Ouverte 2.0. Correspondence: France
-- Travail – ROME 4.0, Licence Ouverte. NSF is NOT used (no ONISEP link through NSF).
--
-- Verified source encoding (Bronze, Phase 12 inspection):
--   * TG = 'Label - NNNNN' (exactly one parent) or, for the 65 top terms, the label of a
--     top-level domain. TS lists are exactly the reverse of TG. Codes are taken from the
--     trailing ' - NNNNN' (labels may themselves contain ' - ').
--   * code_arborescence: child = parent + one segment; niveau = segments - 1 (top = 1).
--   * The semantic field ('NNN LABEL') is constant down the tree; one top term per field.
--
-- Rules / approved decisions
--   * Labels from the OFFICIAL descriptors (typo riche): whitespace runs (incl. U+00A0,
--     U+202F, tabs) -> one space, trimmed, '' -> NULL. Notes: edges trimmed only.
--   * D1 TA self-references excluded (every TA list contains the descriptor itself).
--   * D2 TA targets outside the descriptors (annex lists) kept + flagged.
--   * D3 literal 'null' in grands domaines note_de_version -> NULL.
--   * D4 note_de_version / ex_synonyme_v_1 of the descriptors (always empty) not carried.
--   * D5 semantic field as columns of formacode (no separate table).
--   * D6 correspondence labels not carried (official labels only).
--   * D7 domain via the semantic field's top term (tree-code letter = consistency check).
--   * D8 narrower terms derived from code_formacode_parent (no separate table).
--   * rome_metier_formacode: every Bronze row kept — no filter, no DISTINCT, no weights.
--   * All 12 Bronze lineage columns kept (relationship rows: from the source row).
-- =============================================================================

-- formacode_grand_domaine — key: code_grand_domaine
CREATE OR REPLACE TABLE career_intelligence.silver.formacode_grand_domaine
COMMENT 'Formacode V14 top-level domains (Centre Inffo), official labels normalised. Their top terms are formacode rows with niveau = 1. Key: code_grand_domaine.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'formacode', 'source.license' = 'Licence Ouverte 2.0 (lov2)', 'source.attribution' = 'Formacode® V14 – Centre Inffo', 'primary_key' = 'code_grand_domaine')
AS
SELECT
  b.code_du_terme AS code_grand_domaine,
  nullif(regexp_replace(regexp_replace(b.descripteur_en_typo_riche, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_grand_domaine,
  nullif(regexp_replace(regexp_replace(b.descripteur_en_majuscules, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_majuscules,
  b.code_arborescence,
  CASE WHEN nullif(regexp_replace(regexp_replace(b.note_de_version, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') = 'null' THEN NULL ELSE nullif(regexp_replace(regexp_replace(b.note_de_version, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') END AS note_de_version,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sheet,
  b._source_sha256,
  b._version,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.formacode_v14_grands_domaines b;

-- formacode — key: code_formacode
CREATE OR REPLACE TABLE career_intelligence.silver.formacode
COMMENT 'Formacode V14 descriptors (Centre Inffo): official labels, semantic field, parent (from TG; NULL for the 65 top terms), domain (via the semantic field top term), depth, broad/leaf. Narrower terms = rows whose code_formacode_parent is this code. Key: code_formacode.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'formacode', 'source.license' = 'Licence Ouverte 2.0 (lov2)', 'source.attribution' = 'Formacode® V14 – Centre Inffo', 'primary_key' = 'code_formacode')
AS
WITH top_domaine AS (   -- D7: domain of each semantic field = domain of its top term
  SELECT left(trim(t.champ_semantique), 3) AS code_champ, g.code_du_terme AS code_grand_domaine
  FROM career_intelligence.bronze.formacode_v14_descripteurs t
  JOIN career_intelligence.bronze.formacode_v14_grands_domaines g
    ON nullif(regexp_replace(regexp_replace(g.descripteur_en_typo_riche, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') = nullif(regexp_replace(regexp_replace(t.tg_terme_generique, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '')
  WHERE NOT t.tg_terme_generique RLIKE ' - ([0-9]{5})$'
)
SELECT
  b.code_du_terme AS code_formacode,
  nullif(regexp_replace(regexp_replace(b.descripteur_en_typo_riche, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_formacode,
  nullif(regexp_replace(regexp_replace(b.descripteur_en_majuscules, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_majuscules,
  left(trim(b.champ_semantique), 3) AS code_champ_semantique,
  nullif(regexp_replace(regexp_replace(substr(trim(b.champ_semantique), 5), '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_champ_semantique,
  nullif(regexp_extract(b.tg_terme_generique, ' - ([0-9]{5})$', 1), '') AS code_formacode_parent,
  td.code_grand_domaine,
  b.code_arborescence,
  CAST(size(regexp_extract_all(b.code_arborescence, '[A-Z][0-9]+', 0)) - 1 AS INT) AS niveau,
  CAST(CASE WHEN b.ts_termes_specifiques IS NULL THEN 0 ELSE size(split(b.ts_termes_specifiques, '###')) END AS INT) AS nb_termes_specifiques,
  b.ts_termes_specifiques IS NULL AS est_terme_feuille,
  CASE WHEN nullif(regexp_replace(regexp_replace(b.synonymes, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') IS NULL THEN NULL ELSE transform(split(b.synonymes, '###'), s -> nullif(regexp_replace(regexp_replace(s, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '')) END AS synonymes,
  CASE WHEN nullif(regexp_replace(regexp_replace(b.synonymes_metier, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') IS NULL THEN NULL ELSE transform(split(b.synonymes_metier, '###'), s -> nullif(regexp_replace(regexp_replace(s, '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '')) END AS synonymes_metier,
  nullif(regexp_replace(b.ne_note_dexplication, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS note_explication,
  nullif(regexp_replace(b.na_note_dapplication, '^[\\s\\x{00A0}\\x{202F}]+|[\\s\\x{00A0}\\x{202F}]+$', ''), '') AS note_application,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sheet,
  b._source_sha256,
  b._version,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.formacode_v14_descripteurs b
LEFT JOIN top_domaine td ON td.code_champ = left(trim(b.champ_semantique), 3);

-- formacode_terme_associe — key: code_formacode, code_formacode_associe
CREATE OR REPLACE TABLE career_intelligence.silver.formacode_terme_associe
COMMENT 'Formacode V14 related terms (TA). Self-references (every source TA list contains the descriptor itself) are excluded; targets outside the 2,775 descriptors (annex lists) are kept with terme_associe_dans_descripteurs = false. position = order in the source list. Key: code_formacode, code_formacode_associe.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'formacode', 'source.license' = 'Licence Ouverte 2.0 (lov2)', 'source.attribution' = 'Formacode® V14 – Centre Inffo', 'primary_key' = 'code_formacode, code_formacode_associe')
AS
SELECT
  b.code_du_terme AS code_formacode,
  CAST(t.pos + 1 AS INT) AS position,
  regexp_extract(t.item, ' - ([0-9]{5})$', 1) AS code_formacode_associe,
  nullif(regexp_replace(regexp_replace(regexp_extract(t.item, '^(.*) - [0-9]{5}$', 1), '[\\s\\x{00A0}\\x{202F}]+', ' '), '^ | $', ''), '') AS libelle_associe_source,
  regexp_extract(t.item, ' - ([0-9]{5})$', 1) IN (SELECT code_du_terme FROM career_intelligence.bronze.formacode_v14_descripteurs) AS terme_associe_dans_descripteurs,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sheet,
  b._source_sha256,
  b._version,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.formacode_v14_descripteurs b
LATERAL VIEW posexplode(split(b.ta_termes_associes, '###')) t AS pos, item
WHERE b.ta_termes_associes IS NOT NULL
  -- D1: drop self-references
  AND regexp_extract(t.item, ' - ([0-9]{5})$', 1) <> b.code_du_terme;

-- rome_metier_formacode — key: code_rome, code_formacode
CREATE OR REPLACE TABLE career_intelligence.silver.rome_metier_formacode
COMMENT 'ROME 4.0 v62 occupation -> Formacode V14 descriptor (France Travail correspondence): all 5,958 links, many-to-many, broad and leaf terms, no weights, no primary link. Labels: silver.rome_metier / silver.formacode (correspondence labels stay in Bronze). Key: code_rome, code_formacode.'
TBLPROPERTIES ('layer' = 'silver', 'source.dataset' = 'rome_formacode', 'source.license' = 'Licence Ouverte (fr-lo)', 'source.attribution' = 'France Travail – ROME 4.0; Formacode® V14 – Centre Inffo', 'primary_key' = 'code_rome, code_formacode')
AS
SELECT
  b.code_rome,
  b.code_formacode,
  b._source_name,
  b._source_resource,
  b._dataset,
  b._source_url,
  b._source_file,
  b._source_sheet,
  b._source_sha256,
  b._version,
  b._snapshot,
  b._run_id,
  b._source_row,
  b._ingested_at
FROM career_intelligence.bronze.rome_formacode_v14 b;
