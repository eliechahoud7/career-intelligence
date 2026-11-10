-- q18 lister_grands_domaines_formation — Formacode V14 grand domains, with the number of
-- descriptors linked to at least one ROME 4.0 v62 occupation and the number of occupations
-- linked to them (counts, not weights). Gold holds only the descriptors linked to an occupation.
-- Parameters: :page_size, :offset
SELECT d.code_grand_domaine_formacode, d.libelle_grand_domaine_formacode,
       CAST(count(DISTINCT d.code_formacode) AS INT) AS nb_descripteurs,
       CAST(count(DISTINCT d.code_rome) AS INT) AS nb_metiers,
       d._version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.v_metier_domaine_formation d
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_domaine_formation') l
GROUP BY d.code_grand_domaine_formacode, d.libelle_grand_domaine_formacode, d._version,
         l.licence, l.attribution
ORDER BY d.code_grand_domaine_formacode
LIMIT :page_size OFFSET :offset
