-- q03 appellations_metier — job titles of one ROME 4.0 v62 occupation.
-- Parameters: :code_rome (required), :inclure_peu_usitees (default true), :page_size, :offset
SELECT a.code_rome, a.code_ogr_appellation, a.libelle_appellation_long, a.libelle_appellation_court,
       a.classification, a.peu_usite, a._rome_version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.v_metier_appellation a
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_appellation') l
WHERE a.code_rome = upper(trim(:code_rome))
  AND (coalesce(:inclure_peu_usitees, true) OR a.peu_usite = 'N')
ORDER BY a.libelle_appellation_long COLLATE UNICODE_CI_AI, a.code_ogr_appellation
LIMIT :page_size OFFSET :offset
