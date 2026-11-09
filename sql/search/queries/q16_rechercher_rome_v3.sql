-- q16 rechercher_rome_v3 — DARES correspondence ROME V3 x qualification -> FAP341 / FAP228.
-- ROME V3 is NOT ROME 4.0 v62: identifiers are named code_rome_v3, never joined to v62, and
-- the mapping depends on the qualification class. No BMO figures (only bmo_disponible, so the
-- application can open q14 by FAP228). Licence UNCONFIRMED (DARES).
-- Parameters: :q, :code_rome_v3 (at least one), :code_qualification, :page_size, :offset
-- Match tiers: 1 exact ROME V3 code, 2 label equals the query, 3 label starts with the query,
--   4 every word in the label. Ties: label, code_rome_v3, code_qualification.
WITH p AS (
  SELECT nullif(regexp_replace(trim(replace(:q, '\u2019', chr(39))), '\\s+', ' '), '') AS q
),
t AS (
  SELECT q, filter(split(q, ' '), w -> w <> '') AS mots FROM p
),
r AS (
  SELECT v.*,
         CASE
           WHEN t.q IS NULL THEN NULL
           WHEN v.code_rome_v3 = upper(t.q) THEN 1
           WHEN (v.cle COLLATE UNICODE_CI_AI) = t.q THEN 2
           WHEN startswith(v.cle COLLATE UNICODE_CI_AI, t.q) THEN 3
           WHEN forall(t.mots, w -> contains(v.cle COLLATE UNICODE_CI_AI, w)) THEN 4
         END AS rang_pertinence,
         t.q AS q
  FROM (SELECT *, replace(libelle_rome_v3, '\u2019', chr(39)) AS cle
        FROM career_intelligence.gold.v_rome_v3_fap) v
  CROSS JOIN t
)
SELECT 'ROME V3' AS nomenclature,
       r.code_rome_v3, r.libelle_rome_v3, r.code_qualification, r.libelle_qualification,
       r.code_fap341, r.libelle_fap341, r.code_fap228, r.libelle_fap228,
       r.depend_qualification, r.bmo_disponible, r.rang_pertinence,
       r._snapshot, r._source_sha256,
       l.licence, l.attribution, l.licence_confirmee,
       count(*) OVER () AS total_resultats
FROM r
CROSS JOIN (SELECT licence, attribution, licence_confirmee FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_rome_v3_fap') l
WHERE (r.q IS NOT NULL OR :code_rome_v3 IS NOT NULL)
  AND (r.q IS NULL OR r.rang_pertinence IS NOT NULL)
  AND (:code_rome_v3 IS NULL OR r.code_rome_v3 = upper(trim(:code_rome_v3)))
  AND (:code_qualification IS NULL OR r.code_qualification = :code_qualification)
ORDER BY r.rang_pertinence, r.libelle_rome_v3 COLLATE UNICODE_CI_AI, r.code_rome_v3, r.code_qualification
LIMIT :page_size OFFSET :offset
