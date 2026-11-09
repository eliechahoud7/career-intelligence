-- q10 metiers_par_domaine_formation — ROME 4.0 v62 occupations linked to one Formacode V14 domain.
-- Parameters: :code_formacode (required), :page_size, :offset
SELECT d.code_formacode, d.libelle_formacode,
       m.code_rome, m.libelle_rome, m.code_grand_domaine, m.libelle_grand_domaine,
       m._rome_version, d._version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.v_metier_domaine_formation d
JOIN career_intelligence.gold.metier m ON m.code_rome = d.code_rome
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_domaine_formation') l
WHERE d.code_formacode = trim(:code_formacode)
ORDER BY m.libelle_rome COLLATE UNICODE_CI_AI, m.code_rome
LIMIT :page_size OFFSET :offset
