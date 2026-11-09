-- q15 lister_zones_geo — BMO 2026 geographical areas (national FR, regions, departements).
-- Parameters: :niveau_geo, :page_size, :offset
SELECT z.niveau_geo, z.code_geo, z.libelle_geo, z.nb_familles_fap228, z._source_sha256,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.search.v_zone_geo z
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'bmo_recrutement') l
WHERE (:niveau_geo IS NULL OR z.niveau_geo = :niveau_geo)
ORDER BY CASE z.niveau_geo WHEN 'national' THEN 1 WHEN 'region' THEN 2 ELSE 3 END, z.niveau_geo, z.code_geo
LIMIT :page_size OFFSET :offset
