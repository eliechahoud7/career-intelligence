-- q22 synthese_zones_bmo — BMO 2026 recruitment projects of every FAP228 family combined, by
-- geographical area, for comparisons between areas. Each indicator is the sum of the published
-- family minimums, so it is still a MINIMUM: NULL when every family of the area is hidden, never
-- 0. Families fully hidden in the area are counted per indicator; family x area pairs absent
-- from the source are not rows of gold.bmo_recrutement and are never counted as 0. No ROME column.
-- Parameters: :niveau_geo (required), :page_size, :offset
SELECT b.niveau_geo, b.code_geo, b.libelle_geo, b.annee,
       sum(b.nb_projets_recrutement_minimum) AS nb_projets_recrutement_minimum,
       sum(b.nb_projets_difficiles_minimum) AS nb_projets_difficiles_minimum,
       sum(b.nb_projets_saisonniers_minimum) AS nb_projets_saisonniers_minimum,
       CAST(count(*) AS INT) AS nb_familles_publiees,
       CAST(count_if(b.nb_projets_recrutement_minimum IS NULL) AS INT) AS nb_familles_secretes_recrutement,
       CAST(count_if(b.nb_projets_difficiles_minimum IS NULL) AS INT) AS nb_familles_secretes_difficiles,
       CAST(count_if(b.nb_projets_saisonniers_minimum IS NULL) AS INT) AS nb_familles_secretes_saisonniers,
       CAST(sum(b.nb_cellules) AS INT) AS nb_cellules,
       CAST(sum(b.nb_cellules_secretes_recrutement) AS INT) AS nb_cellules_secretes_recrutement,
       CAST(sum(b.nb_cellules_secretes_difficiles) AS INT) AS nb_cellules_secretes_difficiles,
       CAST(sum(b.nb_cellules_secretes_saisonniers) AS INT) AS nb_cellules_secretes_saisonniers,
       bool_and(b.est_complet_recrutement) AS est_complet_recrutement,
       bool_and(b.est_complet_difficiles) AS est_complet_difficiles,
       bool_and(b.est_complet_saisonniers) AS est_complet_saisonniers,
       'minimum' AS nature_valeur,
       min(b._source_sha256) AS _source_sha256,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.bmo_recrutement b
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'bmo_recrutement') l
WHERE b.niveau_geo = :niveau_geo
GROUP BY b.niveau_geo, b.code_geo, b.libelle_geo, b.annee, l.licence, l.attribution
ORDER BY b.niveau_geo, b.code_geo
LIMIT :page_size OFFSET :offset
