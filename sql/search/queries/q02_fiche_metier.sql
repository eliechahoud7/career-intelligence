-- q02 fiche_metier — one ROME 4.0 v62 occupation profile (single row, not paginated).
-- Parameters: :code_rome (required)
-- Texts come from search.v_metier_index (doubled source apostrophes corrected, decision P5).
-- The ROME parent attribute is deliberately not exposed (no approved use).
SELECT m.code_rome, m.code_ogr, m.libelle_rome,
       m.code_grand_domaine, m.libelle_grand_domaine,
       m.code_domaine_professionnel, m.libelle_domaine_professionnel,
       m.riasec_majeur, m.riasec_mineur,
       m.transition_eco, m.transition_num, m.transition_demo,
       m.emploi_reglemente, m.emploi_cadre,
       d.texte AS definition, a.texte AS acces_metier,
       m.nb_phrases_definition, m.nb_phrases_acces_metier,
       m.nb_appellations, m.nb_savoir_faire, m.nb_savoir_etre, m.nb_savoirs,
       m.nb_contextes_travail, m.nb_domaines_formation,
       m._rome_version, m._source_archive_sha256,
       l.licence, l.attribution
FROM career_intelligence.gold.metier m
LEFT JOIN career_intelligence.search.v_metier_index d ON d.code_rome = m.code_rome AND d.champ = 'definition'
LEFT JOIN career_intelligence.search.v_metier_index a ON a.code_rome = m.code_rome AND a.champ = 'acces_metier'
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'metier') l
WHERE m.code_rome = upper(trim(:code_rome))
