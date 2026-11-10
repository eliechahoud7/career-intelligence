-- q19 parcourir_domaines_formation — browse, without a keyword, the Formacode V14 descriptors of
-- one grand domain that are linked to at least one ROME 4.0 v62 occupation.
-- Parameters: :code_grand_domaine_formacode (required), :page_size, :offset
SELECT d.code_formacode, d.libelle_formacode, d.code_champ_semantique, d.libelle_champ_semantique,
       d.code_grand_domaine_formacode, d.libelle_grand_domaine_formacode,
       d.niveau, d.est_terme_feuille, d.code_formacode_parent, d.nb_metiers,
       d._version, d._source_sha256,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.search.v_domaine_formation d
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_domaine_formation') l
WHERE d.code_grand_domaine_formacode = trim(:code_grand_domaine_formacode)
ORDER BY d.libelle_formacode COLLATE UNICODE_CI_AI, d.code_formacode
LIMIT :page_size OFFSET :offset
