-- q04 lister_domaines — ROME 4.0 v62 professional domains with their number of occupations.
-- Parameters: :code_grand_domaine, :page_size, :offset
SELECT m.code_grand_domaine, m.libelle_grand_domaine,
       m.code_domaine_professionnel, m.libelle_domaine_professionnel,
       CAST(count(*) AS INT) AS nb_metiers, m._rome_version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.metier m
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'metier') l
WHERE (:code_grand_domaine IS NULL OR m.code_grand_domaine = upper(trim(:code_grand_domaine)))
GROUP BY m.code_grand_domaine, m.libelle_grand_domaine, m.code_domaine_professionnel,
         m.libelle_domaine_professionnel, m._rome_version, l.licence, l.attribution
ORDER BY m.code_grand_domaine, m.code_domaine_professionnel
LIMIT :page_size OFFSET :offset
