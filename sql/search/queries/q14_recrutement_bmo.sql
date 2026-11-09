-- q14 recrutement_bmo — BMO 2026 recruitment projects by FAP228 family and geographical area.
-- Values are MINIMUMS (statistical secrecy): NULL when every cell is hidden, never 0. No ROME
-- column: BMO figures are never attributed to ROME occupations.
-- Parameters: :code_fap228, :niveau_geo (default 'national'), :code_geo (at least one of
--             :code_fap228 / :code_geo), :tri ('geo' default, or 'minimum_desc' with NULLs last),
--             :page_size, :offset
SELECT b.code_fap228, b.libelle_metier_bmo, b.niveau_geo, b.code_geo, b.libelle_geo, b.annee,
       b.nb_projets_recrutement_minimum, b.nb_projets_difficiles_minimum, b.nb_projets_saisonniers_minimum,
       b.nb_cellules, b.nb_cellules_secretes_recrutement, b.nb_cellules_secretes_difficiles,
       b.nb_cellules_secretes_saisonniers,
       b.est_complet_recrutement, b.est_complet_difficiles, b.est_complet_saisonniers,
       'minimum' AS nature_valeur,
       b._source_sha256,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.bmo_recrutement b
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'bmo_recrutement') l
WHERE (:code_fap228 IS NOT NULL OR :code_geo IS NOT NULL)
  AND (:code_fap228 IS NULL OR b.code_fap228 = upper(trim(:code_fap228)))
  AND b.niveau_geo = coalesce(:niveau_geo, 'national')
  AND (:code_geo IS NULL OR b.code_geo = upper(trim(:code_geo)))
ORDER BY CASE WHEN :tri = 'minimum_desc' THEN b.nb_projets_recrutement_minimum END DESC NULLS LAST,
         b.niveau_geo, b.code_geo, b.code_fap228
LIMIT :page_size OFFSET :offset
