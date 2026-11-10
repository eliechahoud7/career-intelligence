-- q20 metiers_par_formation_onisep — ROME 4.0 v62 occupations linked to one ONISEP training
-- programme through ONISEP's own links (ODbL, "Source : Onisep"). Original ONISEP grain kept
-- (decision D7): one row per ONISEP ROME link x training link. Unresolved ONISEP ROME codes are
-- kept (code_rome and libelle_rome NULL, statut_code_rome = 'non_resolu'), never guessed.
-- Parameters: :identifiant_formation (required), :type_lien, :page_size, :offset
SELECT o.identifiant_formation, o.libelle_formation, o.type_lien,
       o.identifiant_metier_onisep, o.nom_metier_onisep,
       o.code_rome_source, o.statut_code_rome, o.code_rome, m.libelle_rome,
       m.code_grand_domaine, m.libelle_grand_domaine,
       o._snapshot, m._rome_version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.v_metier_formation_onisep o
LEFT JOIN career_intelligence.gold.metier m ON m.code_rome = o.code_rome
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_formation_onisep') l
WHERE o.identifiant_formation = trim(:identifiant_formation)
  AND (:type_lien IS NULL OR o.type_lien = :type_lien)
ORDER BY o.type_lien, o.code_rome IS NULL, m.libelle_rome COLLATE UNICODE_CI_AI, o.code_rome_source,
         o.identifiant_metier_onisep, o.identifiant_formation
LIMIT :page_size OFFSET :offset
