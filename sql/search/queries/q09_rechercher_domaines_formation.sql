-- q09 rechercher_domaines_formation — search Formacode V14 training domains linked to ROME
-- occupations, by code or label.
-- Parameters: :q (required), :code_grand_domaine_formacode, :page_size, :offset
-- Match tiers: 1 exact Formacode code, 2 label equals the query, 3 label starts with the query,
--   4 every word in the label. Ties: label, code_formacode.
WITH p AS (
  SELECT nullif(regexp_replace(trim(replace(:q, '\u2019', chr(39))), '\\s+', ' '), '') AS q
),
t AS (
  SELECT q, filter(split(q, ' '), w -> w <> '') AS mots FROM p
),
r AS (
  SELECT d.*,
         CASE
           WHEN d.code_formacode = t.q THEN 1
           WHEN (d.cle COLLATE UNICODE_CI_AI) = t.q THEN 2
           WHEN startswith(d.cle COLLATE UNICODE_CI_AI, t.q) THEN 3
           WHEN forall(t.mots, w -> contains(d.cle COLLATE UNICODE_CI_AI, w)) THEN 4
         END AS rang_pertinence
  FROM (SELECT *, replace(libelle_formacode, '\u2019', chr(39)) AS cle
        FROM career_intelligence.search.v_domaine_formation) d
  CROSS JOIN t
  WHERE t.q IS NOT NULL
)
SELECT r.code_formacode, r.libelle_formacode, r.code_champ_semantique, r.libelle_champ_semantique,
       r.code_grand_domaine_formacode, r.libelle_grand_domaine_formacode,
       r.niveau, r.est_terme_feuille, r.code_formacode_parent, r.nb_metiers, r.rang_pertinence,
       r._version, r._source_sha256,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM r
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_domaine_formation') l
WHERE r.rang_pertinence IS NOT NULL
  AND (:code_grand_domaine_formacode IS NULL OR r.code_grand_domaine_formacode = :code_grand_domaine_formacode)
ORDER BY r.rang_pertinence, r.libelle_formacode COLLATE UNICODE_CI_AI, r.code_formacode
LIMIT :page_size OFFSET :offset
