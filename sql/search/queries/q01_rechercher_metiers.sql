-- q01 rechercher_metiers — search ROME 4.0 v62 occupations by code, name, job title or (optionally) texts.
-- Parameters: :q (required), :code_grand_domaine, :code_domaine_professionnel, :emploi_cadre,
--             :emploi_reglemente, :inclure_textes, :page_size, :offset
-- Match tiers (rang_pertinence, lower is better, match quality only — no relationship weight):
--   1 exact ROME code, 2 name equals the query, 3 name starts with the query, 4 every word in the
--   name, 5 every word in a job title, 6 every word in the definition or access text (only when
--   :inclure_textes is true). Ties: name (accent- and case-insensitive), then code_rome.
WITH p AS (
  SELECT nullif(regexp_replace(trim(replace(:q, '\u2019', chr(39))), '\\s+', ' '), '') AS q
),
t AS (
  SELECT q, filter(split(q, ' '), w -> w <> '') AS mots FROM p
),
correspondances AS (
  SELECT i.code_rome, i.champ, i.ordre_champ, i.code_ogr_appellation, i.texte,
         CASE
           WHEN i.champ = 'code_rome' AND i.texte = upper(t.q) THEN 1
           WHEN i.champ = 'libelle_rome' AND (i.cle COLLATE UNICODE_CI_AI) = t.q THEN 2
           WHEN i.champ = 'libelle_rome' AND startswith(i.cle COLLATE UNICODE_CI_AI, t.q) THEN 3
           WHEN i.champ = 'libelle_rome' AND forall(t.mots, w -> contains(i.cle COLLATE UNICODE_CI_AI, w)) THEN 4
           WHEN i.champ IN ('appellation_long', 'appellation_court')
                AND forall(t.mots, w -> contains(i.cle COLLATE UNICODE_CI_AI, w)) THEN 5
           WHEN i.champ IN ('definition', 'acces_metier') AND coalesce(:inclure_textes, false)
                AND forall(t.mots, w -> contains(i.cle COLLATE UNICODE_CI_AI, w)) THEN 6
         END AS rang_pertinence
  FROM (SELECT *, replace(texte, '\u2019', chr(39)) AS cle
        FROM career_intelligence.search.v_metier_index) i
  CROSS JOIN t
  WHERE t.q IS NOT NULL
),
meilleure AS (
  SELECT code_rome, champ, texte, rang_pertinence,
         row_number() OVER (PARTITION BY code_rome
                            ORDER BY rang_pertinence, ordre_champ, texte, code_ogr_appellation) AS n
  FROM correspondances
  WHERE rang_pertinence IS NOT NULL
)
SELECT m.code_rome, m.libelle_rome,
       m.code_grand_domaine, m.libelle_grand_domaine,
       m.code_domaine_professionnel, m.libelle_domaine_professionnel,
       m.emploi_cadre, m.emploi_reglemente,
       b.champ AS champ_correspondant, b.texte AS libelle_correspondant, b.rang_pertinence,
       m.nb_appellations, m._rome_version,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM meilleure b
JOIN career_intelligence.gold.metier m ON m.code_rome = b.code_rome
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'metier') l
WHERE b.n = 1
  AND (:code_grand_domaine IS NULL OR m.code_grand_domaine = :code_grand_domaine)
  AND (:code_domaine_professionnel IS NULL OR m.code_domaine_professionnel = :code_domaine_professionnel)
  AND (:emploi_cadre IS NULL OR m.emploi_cadre = :emploi_cadre)
  AND (:emploi_reglemente IS NULL OR m.emploi_reglemente = :emploi_reglemente)
ORDER BY b.rang_pertinence, m.libelle_rome COLLATE UNICODE_CI_AI, m.code_rome
LIMIT :page_size OFFSET :offset
