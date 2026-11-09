-- q17 licences — licence, attribution and restrictions of Gold objects, for display.
-- Parameters: :objets (comma-separated objet_gold values, optional), :page_size, :offset
SELECT s.objet_gold, s.type_objet, s.sources, s.licence, s.attribution, s.licence_confirmee, s.restrictions,
       count(*) OVER () AS total_resultats
FROM career_intelligence.gold.source_licence s
WHERE (:objets IS NULL OR array_contains(split(:objets, ','), s.objet_gold))
ORDER BY s.objet_gold
LIMIT :page_size OFFSET :offset
