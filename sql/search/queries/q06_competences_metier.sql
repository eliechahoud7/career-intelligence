-- q06 competences_metier — skill elements of one ROME 4.0 v62 occupation.
-- Parameters: :code_rome (required), :types (comma-separated), :coeur_metier_seulement (default false),
--             :page_size, :offset
-- Order: type (savoir-faire, savoir-être, savoirs, contextes), then elements marked
--   coeur_metier = 'Principale' by the source first (decision P10), then label, then code.
SELECT c.code_rome, c.type_element, c.code_ogr_element, c.libelle_element,
       c.niveau_competence, c.coeur_metier, c.categorie, c.sous_categorie,
       c.code_ogr_macro_competence, c.libelle_macro_competence, c._rome_version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.v_metier_competence c
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_competence') l
WHERE c.code_rome = upper(trim(:code_rome))
  AND (:types IS NULL OR array_contains(split(:types, ','), c.type_element))
  AND (NOT coalesce(:coeur_metier_seulement, false) OR c.coeur_metier = 'Principale')
ORDER BY CASE c.type_element WHEN 'savoir_faire' THEN 1 WHEN 'savoir_etre' THEN 2 WHEN 'savoir' THEN 3 ELSE 4 END,
         CASE WHEN c.coeur_metier = 'Principale' THEN 0 ELSE 1 END,
         c.libelle_element COLLATE UNICODE_CI_AI, c.type_element, c.code_ogr_element
LIMIT :page_size OFFSET :offset
