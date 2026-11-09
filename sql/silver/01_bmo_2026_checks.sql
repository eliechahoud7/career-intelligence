-- =============================================================================
-- Verification for career_intelligence.silver.bmo_2026 (compared with bronze).
-- Every column named check_* must be TRUE.
-- =============================================================================

-- 1. Row count, keys, conversions, secrecy, consistency
WITH b AS (
  SELECT count(*)                                AS n,
         count_if(nb_projets_recrutement = '*')  AS met_s,
         count_if(nb_projets_difficiles  = '*')  AS xmet_s,
         count_if(nb_projets_saisonniers = '*')  AS smet_s,
         sum(try_cast(nb_projets_recrutement AS INT)) AS met_sum
  FROM career_intelligence.bronze.bmo_2026
), s AS (
  SELECT count(*) AS n,
         count(DISTINCT code_metier_bmo, code_departement, code_bassin_emploi,
               coalesce(code_clpe, '<null>'))    AS n_keys,
         count_if(nb_projets_recrutement_secret) AS met_s,
         count_if(nb_projets_difficiles_secret)  AS xmet_s,
         count_if(nb_projets_saisonniers_secret) AS smet_s,
         -- NULL value must mean "secret", and only that
         count_if((nb_projets_recrutement IS NULL) <> nb_projets_recrutement_secret
               OR (nb_projets_difficiles  IS NULL) <> nb_projets_difficiles_secret
               OR (nb_projets_saisonniers IS NULL) <> nb_projets_saisonniers_secret) AS bad_conv,
         count_if(nb_projets_recrutement < 0 OR nb_projets_difficiles < 0
               OR nb_projets_saisonniers < 0)    AS negatives,
         count_if(nb_projets_difficiles  > nb_projets_recrutement) AS xmet_gt_met,
         count_if(nb_projets_saisonniers > nb_projets_recrutement) AS smet_gt_met,
         sum(nb_projets_recrutement)             AS met_sum
  FROM career_intelligence.silver.bmo_2026
)
SELECT s.n                         AS silver_rows,
       s.n = 53786 AND s.n = b.n   AS check_row_count,
       s.n_keys = s.n              AS check_unique_business_key,
       s.bad_conv = 0              AS check_numeric_conversion,
       s.negatives = 0             AS check_non_negative,
       s.met_s = b.met_s AND s.xmet_s = b.xmet_s AND s.smet_s = b.smet_s AS check_secret_counts,
       s.xmet_gt_met = 0 AND s.smet_gt_met = 0 AS check_parts_le_total,
       s.met_sum = b.met_sum       AS check_total_projects
FROM s CROSS JOIN b;

-- 2. Row-level comparison with bronze on _source_row: codes and lineage
--    unchanged; labels changed only in whitespace.
SELECT count(*)                                              AS joined_rows,
       count_if(s._source_row IS NULL)                       AS missing_in_silver,
       count_if(NOT (b.code_metier_bmo     <=> s.code_metier_bmo
                 AND b.code_famille_metier <=> s.code_famille_metier
                 AND b.code_region         <=> s.code_region
                 AND b.code_departement    <=> s.code_departement
                 AND b.code_bassin_emploi  <=> s.code_bassin_emploi
                 AND b.code_clpe           <=> s.code_clpe
                 AND b.annee               <=> s.annee
                 AND b._source_sha256      <=> s._source_sha256
                 AND b._run_id             <=> s._run_id
                 AND b._ingested_at        <=> s._ingested_at)) AS changed_codes_or_lineage,
       count_if(b.libelle_metier_bmo     <> s.libelle_metier_bmo)     AS changed_metier,
       count_if(b.libelle_bassin_emploi  <> s.libelle_bassin_emploi)  AS changed_bassin,
       count_if(b.libelle_famille_metier <> s.libelle_famille_metier
             OR b.libelle_region         <> s.libelle_region
             OR b.libelle_departement    <> s.libelle_departement)    AS changed_other_labels,
       -- labels must differ from bronze ONLY in whitespace
       count_if(NOT (
             regexp_replace(b.libelle_metier_bmo,    '[\\s\\x{00A0}\\x{202F}]', '') = regexp_replace(s.libelle_metier_bmo,    ' ', '')
         AND regexp_replace(b.libelle_bassin_emploi, '[\\s\\x{00A0}\\x{202F}]', '') = regexp_replace(s.libelle_bassin_emploi, ' ', '')))
                                                                      AS non_whitespace_changes,
       -- no edge space, double space, tab or non-breaking space may remain
       count_if(concat_ws('|', s.libelle_metier_bmo, s.libelle_bassin_emploi, s.libelle_departement,
                               s.libelle_region, s.libelle_famille_metier)
                RLIKE '(^|\\|) | ($|\\|)|  |[\\t\\x{00A0}\\x{202F}]') AS remaining_ws_issues
FROM career_intelligence.bronze.bmo_2026 b
LEFT JOIN career_intelligence.silver.bmo_2026 s USING (_source_row);
-- Expected (2026-11-09): 53786 | 0 | 0 | 257 | 254 | 0 | 0 | 0

-- 3. Sample
SELECT * FROM career_intelligence.silver.bmo_2026 ORDER BY _source_row LIMIT 5;
