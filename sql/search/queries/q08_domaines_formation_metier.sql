-- q08 domaines_formation_metier — Formacode V14 training domains linked to one ROME 4.0 v62
-- occupation. Many-to-many: every link is returned, no "best" domain.
-- Parameters: :code_rome (required), :page_size, :offset
SELECT d.code_rome, d.code_formacode, d.libelle_formacode,
       d.code_champ_semantique, d.libelle_champ_semantique,
       d.code_grand_domaine_formacode, d.libelle_grand_domaine_formacode,
       d.niveau, d.est_terme_feuille, d.code_formacode_parent,
       d._version, d._source_sha256,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.v_metier_domaine_formation d
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_domaine_formation') l
WHERE d.code_rome = upper(trim(:code_rome))
ORDER BY d.code_grand_domaine_formacode, d.libelle_formacode COLLATE UNICODE_CI_AI, d.code_formacode
LIMIT :page_size OFFSET :offset
