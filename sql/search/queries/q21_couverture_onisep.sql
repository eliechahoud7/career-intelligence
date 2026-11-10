-- q21 couverture_onisep — coverage of ROME 4.0 v62 by ONISEP training links (ODbL,
-- "Source : Onisep"): distinct resolved ROME codes with at least one ONISEP training link in
-- Gold, out of every ROME v62 occupation. Unresolved ONISEP ROME codes are counted separately
-- (decision D6), never added to the coverage. Counts only, one row.
-- Parameters: none
SELECT o.nb_metiers_avec_formation, m.nb_metiers_rome, o.nb_codes_rome_non_resolus,
       o.nb_formations, o.nb_metiers_onisep,
       o._snapshot, m._rome_version,
       l.licence, l.attribution
FROM (SELECT CAST(count(DISTINCT code_rome) AS INT) AS nb_metiers_avec_formation,
             CAST(count(DISTINCT CASE WHEN statut_code_rome = 'non_resolu' THEN code_rome_source END) AS INT) AS nb_codes_rome_non_resolus,
             CAST(count(DISTINCT identifiant_formation) AS INT) AS nb_formations,
             CAST(count(DISTINCT identifiant_metier_onisep) AS INT) AS nb_metiers_onisep,
             max(_snapshot) AS _snapshot
      FROM career_intelligence.gold.v_metier_formation_onisep) o
CROSS JOIN (SELECT CAST(count(*) AS INT) AS nb_metiers_rome, max(_rome_version) AS _rome_version
            FROM career_intelligence.gold.metier) m
CROSS JOIN (SELECT licence, attribution FROM career_intelligence.gold.source_licence WHERE objet_gold = 'v_metier_formation_onisep') l
