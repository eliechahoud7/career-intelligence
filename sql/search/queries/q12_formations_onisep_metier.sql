-- q12 formations_onisep_metier — ONISEP training programmes linked to one ROME 4.0 v62
-- occupation (ODbL, "Source : Onisep"). Original ONISEP grain kept (decision D7): one row per
-- ONISEP ROME link x training link. Only resolved links can match a code_rome.
-- Parameters: :code_rome (required), :type_lien, :page_size, :offset
SELECT o.code_rome, o.code_rome_source, o.statut_code_rome,
       o.identifiant_metier_onisep, o.nom_metier_onisep, o.type_lien,
       o.identifiant_formation, o.libelle_formation, o.libelle_formation_source,
       o.formation_dans_catalogue, o.libelle_type_formation, o.niveau_de_sortie_indicatif,
       o.libelle_niveau_de_certification, o.duree, o.code_rncp, o.url_onisep,
       o._snapshot, o._source_sha256_lien_rome, o._source_sha256_lien_formation,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.v_metier_formation_onisep o
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_formation_onisep') l
WHERE o.code_rome = upper(trim(:code_rome))
  AND (:type_lien IS NULL OR o.type_lien = :type_lien)
ORDER BY o.type_lien, o.libelle_formation COLLATE UNICODE_CI_AI, o.identifiant_formation,
         o.identifiant_metier_onisep, o.code_rome_source
LIMIT :page_size OFFSET :offset
