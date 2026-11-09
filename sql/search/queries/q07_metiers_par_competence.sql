-- q07 metiers_par_competence — ROME 4.0 v62 occupations linked to one skill element.
-- Parameters: :type_element (required), :code_ogr_element (required),
--             :coeur_metier_seulement (default false), :page_size, :offset
SELECT c.type_element, c.code_ogr_element, c.libelle_element,
       m.code_rome, m.libelle_rome, m.code_grand_domaine, m.libelle_grand_domaine,
       c.niveau_competence, c.coeur_metier, m._rome_version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.v_metier_competence c
JOIN career_intelligence.gold.metier m ON m.code_rome = c.code_rome
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_competence') l
WHERE c.type_element = :type_element
  AND c.code_ogr_element = trim(:code_ogr_element)
  AND (NOT coalesce(:coeur_metier_seulement, false) OR c.coeur_metier = 'Principale')
ORDER BY m.libelle_rome COLLATE UNICODE_CI_AI, m.code_rome
LIMIT :page_size OFFSET :offset
