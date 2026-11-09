-- q13 rechercher_fap — browse or search FAP 2021 families (FAP228 level) and their hierarchy.
-- Licence UNCONFIRMED (DARES). No ROME column.
-- Parameters: :q (optional: without it every family is listed by label), :code_fap22,
--             :bmo_disponible, :page_size, :offset
-- Match tiers: 1 exact FAP228 code, 2 label equals the query, 3 label starts with the query,
--   4 every word in the label. Ties: label, code_fap228.
WITH p AS (
  SELECT nullif(regexp_replace(trim(replace(:q, '\u2019', chr(39))), '\\s+', ' '), '') AS q
),
t AS (
  SELECT q, filter(split(q, ' '), w -> w <> '') AS mots FROM p
),
r AS (
  SELECT f.*,
         CASE
           WHEN t.q IS NULL THEN NULL
           WHEN f.code_fap228 = upper(t.q) THEN 1
           WHEN (f.cle COLLATE UNICODE_CI_AI) = t.q THEN 2
           WHEN startswith(f.cle COLLATE UNICODE_CI_AI, t.q) THEN 3
           WHEN forall(t.mots, w -> contains(f.cle COLLATE UNICODE_CI_AI, w)) THEN 4
         END AS rang_pertinence,
         t.q AS q
  FROM (SELECT *, replace(libelle_fap228, '\u2019', chr(39)) AS cle
        FROM career_intelligence.gold.v_fap) f
  CROSS JOIN t
)
SELECT r.code_fap228, r.libelle_fap228, r.code_fap86, r.libelle_fap86, r.code_fap22, r.libelle_fap22,
       r.nb_fap341, r.bmo_disponible, r.rang_pertinence,
       l.licence, l.attribution, l.licence_confirmee,
       count(*) OVER () AS total_resultats
FROM r
CROSS JOIN (SELECT licence, attribution, licence_confirmee FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_fap') l
WHERE (r.q IS NULL OR r.rang_pertinence IS NOT NULL)
  AND (:code_fap22 IS NULL OR r.code_fap22 = upper(trim(:code_fap22)))
  AND (:bmo_disponible IS NULL OR r.bmo_disponible = :bmo_disponible)
ORDER BY r.rang_pertinence, r.libelle_fap228 COLLATE UNICODE_CI_AI, r.code_fap228
LIMIT :page_size OFFSET :offset
