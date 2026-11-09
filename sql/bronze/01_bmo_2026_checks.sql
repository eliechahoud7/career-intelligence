-- =============================================================================
-- Verification queries for career_intelligence.bronze.bmo_2026
-- Expected values come from the local validation run (see the .manifest.json).
-- Verified on 2026-11-09: all checks matched.
-- =============================================================================

-- 1. Profile — expected: 53786 rows | 217 occupations | 101 departments | 406 bassins |
--    100 null CLPE | 13039 / 26130 / 39908 '*' | 1 sha (735d0443…) | rows 2..53787 |
--    2237486 recruitment projects (non-secret cells)
SELECT count(*)                                   AS row_count,
       count(DISTINCT code_metier_bmo)            AS occupations,
       count(DISTINCT code_departement)           AS departements,
       count(DISTINCT code_bassin_emploi)         AS bassins,
       count_if(code_clpe IS NULL)                AS clpe_null,
       count_if(nb_projets_recrutement = '*')     AS met_secret,
       count_if(nb_projets_difficiles = '*')      AS xmet_secret,
       count_if(nb_projets_saisonniers = '*')     AS smet_secret,
       count(DISTINCT _source_sha256)             AS n_sha,
       min(_source_sha256)                        AS sha,
       min(_source_row)                           AS min_row,
       max(_source_row)                           AS max_row,
       sum(try_cast(nb_projets_recrutement AS INT)) AS total_met
FROM career_intelligence.bronze.bmo_2026;

-- 2. Grain — expected: 0
SELECT count(*) AS duplicate_keys FROM (
  SELECT code_metier_bmo, code_departement, code_bassin_emploi, code_clpe, count(*) AS c
  FROM career_intelligence.bronze.bmo_2026
  GROUP BY ALL HAVING c > 1);

-- 3. Text codes preserved (leading zeros, Corsica) — expected: rows for '01', '2A'
SELECT code_region, code_departement, count(*) AS n
FROM career_intelligence.bronze.bmo_2026
WHERE code_region = '01' OR code_departement IN ('2A', '2B')
GROUP BY ALL ORDER BY ALL;

-- 4. Sample
SELECT * FROM career_intelligence.bronze.bmo_2026 ORDER BY _source_row LIMIT 5;
