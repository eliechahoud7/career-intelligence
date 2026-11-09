-- q05 rechercher_competences — search ROME skill elements (savoir-faire, savoir-être, savoirs,
-- contextes de travail) by OGR code or label.
-- Parameters: :q (required), :types (comma-separated type_element values), :categorie,
--             :page_size, :offset
-- Match tiers: 1 exact OGR code, 2 label equals the query, 3 label starts with the query,
--   4 every word in the label. Ties: label, type_element, code_ogr_element.
WITH p AS (
  SELECT nullif(regexp_replace(trim(replace(:q, '\u2019', chr(39))), '\\s+', ' '), '') AS q
),
t AS (
  SELECT q, filter(split(q, ' '), w -> w <> '') AS mots FROM p
),
r AS (
  SELECT e.*,
         CASE
           WHEN e.code_ogr_element = t.q THEN 1
           WHEN (e.cle COLLATE UNICODE_CI_AI) = t.q THEN 2
           WHEN startswith(e.cle COLLATE UNICODE_CI_AI, t.q) THEN 3
           WHEN forall(t.mots, w -> contains(e.cle COLLATE UNICODE_CI_AI, w)) THEN 4
         END AS rang_pertinence
  FROM (SELECT *, replace(libelle_element, '\u2019', chr(39)) AS cle
        FROM career_intelligence.search.v_element_competence) e
  CROSS JOIN t
  WHERE t.q IS NOT NULL
)
SELECT r.type_element, r.code_ogr_element, r.libelle_element, r.categorie, r.sous_categorie,
       r.code_ogr_macro_competence, r.libelle_macro_competence, r.nb_metiers, r.rang_pertinence,
       r._rome_version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM r
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_competence') l
WHERE r.rang_pertinence IS NOT NULL
  AND (:types IS NULL OR array_contains(split(:types, ','), r.type_element))
  AND (:categorie IS NULL OR r.categorie = :categorie)
ORDER BY r.rang_pertinence, r.libelle_element COLLATE UNICODE_CI_AI, r.type_element, r.code_ogr_element
LIMIT :page_size OFFSET :offset
