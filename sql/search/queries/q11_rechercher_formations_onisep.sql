-- q11 rechercher_formations_onisep — search ONISEP training programmes (ODbL, "Source : Onisep").
-- Reads gold.v_metier_formation_onisep directly (decision P6): one result row per programme,
-- with the number of ONISEP occupations and of ROME codes it is linked to, including the count
-- of unresolved ROME codes (statut 'non_resolu').
-- Parameters: :q (required), :type_formation, :niveau_certification, :dans_catalogue,
--             :page_size, :offset
-- Match tiers: 1 exact ONISEP identifier or RNCP code, 2 label equals the query, 3 label starts
--   with the query, 4 every word in the label. Ties: label, identifiant_formation.
WITH p AS (
  SELECT nullif(regexp_replace(trim(replace(:q, '\u2019', chr(39))), '\\s+', ' '), '') AS q
),
t AS (
  SELECT q, filter(split(q, ' '), w -> w <> '') AS mots FROM p
),
f AS (
  SELECT identifiant_formation, libelle_formation, libelle_type_formation, niveau_de_sortie_indicatif,
         libelle_niveau_de_certification, duree, code_rncp, url_onisep, formation_dans_catalogue,
         CAST(count(DISTINCT identifiant_metier_onisep) AS INT) AS nb_metiers_onisep,
         CAST(count(DISTINCT code_rome) AS INT) AS nb_codes_rome,
         CAST(count(DISTINCT CASE WHEN statut_code_rome = 'non_resolu' THEN code_rome_source END) AS INT) AS nb_codes_rome_non_resolus,
         _snapshot
  FROM career_intelligence.gold.v_metier_formation_onisep
  GROUP BY identifiant_formation, libelle_formation, libelle_type_formation, niveau_de_sortie_indicatif,
           libelle_niveau_de_certification, duree, code_rncp, url_onisep, formation_dans_catalogue, _snapshot
),
r AS (
  SELECT f.*,
         CASE
           WHEN upper(f.identifiant_formation) = upper(t.q) OR f.code_rncp = t.q THEN 1
           WHEN (replace(f.libelle_formation, '\u2019', chr(39)) COLLATE UNICODE_CI_AI) = t.q THEN 2
           WHEN startswith(replace(f.libelle_formation, '\u2019', chr(39)) COLLATE UNICODE_CI_AI, t.q) THEN 3
           WHEN forall(t.mots, w -> contains(replace(f.libelle_formation, '\u2019', chr(39)) COLLATE UNICODE_CI_AI, w)) THEN 4
         END AS rang_pertinence
  FROM f
  CROSS JOIN t
  WHERE t.q IS NOT NULL
)
SELECT r.identifiant_formation, r.libelle_formation, r.libelle_type_formation,
       r.niveau_de_sortie_indicatif, r.libelle_niveau_de_certification, r.duree, r.code_rncp,
       r.url_onisep, r.formation_dans_catalogue,
       r.nb_metiers_onisep, r.nb_codes_rome, r.nb_codes_rome_non_resolus, r.rang_pertinence,
       r._snapshot,
       l.licence, l.attribution,
       count(*) OVER () AS total_resultats
FROM r
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_formation_onisep') l
WHERE r.rang_pertinence IS NOT NULL
  AND (:type_formation IS NULL OR r.libelle_type_formation = :type_formation)
  AND (:niveau_certification IS NULL OR r.libelle_niveau_de_certification = :niveau_certification)
  AND (:dans_catalogue IS NULL OR r.formation_dans_catalogue = :dans_catalogue)
ORDER BY r.rang_pertinence, r.libelle_formation COLLATE UNICODE_CI_AI, r.identifiant_formation
LIMIT :page_size OFFSET :offset
