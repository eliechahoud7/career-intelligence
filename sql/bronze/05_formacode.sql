-- =============================================================================
-- Bronze tables: ROME 4.0 v62 <-> Formacode V14 + Formacode V14 thesaurus
-- Snapshot rome_v62_formacode_v14 (all files sha256-pinned in config/sources.yaml)
--
--   rome_formacode_v14            France Travail — "ROME 26M10 - Formacode V14"
--                                 realised 15/10/2026, published 19/10/2026, next update 23/03/2027
--                                 Licence Ouverte (ROME dataset, fr-lo)
--   formacode_v14_descripteurs    Centre Inffo — descripteur-formacode-des-champs-semantiques-20241212.xlsx
--   formacode_v14_grands_domaines Centre Inffo — grands-domaines-20241212.xls
--                                 Licence Ouverte 2.0 (lov2); Formacode® is a trademark of Centre Inffo
--   (alignement-formacode-nsf-20241212.xls is ARCHIVED in raw/ only — no table, no NSF bridge)
--
-- One row per source row; every source value as published (text; Excel numeric
-- identifiers -> exact integer text; empty cells -> NULL). Headers renamed to snake_case;
-- original headers are in the manifest. The correspondence keeps its own Formacode labels
-- (Title Case, 73 codes with accented/unaccented variants) — official labels are in
-- formacode_v14_descripteurs. Many-to-many: no weights, no primary link.
--
-- Prerequisites
--   1. python -m career_intelligence.ingestion.formacode
--   2. Upload (PowerShell):
--        databricks fs cp -r data\raw\formacode\rome_v62_formacode_v14 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/formacode/rome_v62_formacode_v14/raw --profile career-intelligence
--        databricks fs cp -r data\staging\formacode\rome_v62_formacode_v14 `
--          dbfs:/Volumes/career_intelligence/bronze/landing/formacode/rome_v62_formacode_v14/parquet --profile career-intelligence
-- =============================================================================

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.rome_formacode_v14
COMMENT 'France Travail correspondence ROME 4.0 v62 (26M10) x Formacode V14, raw: one row per (ROME, Formacode) link, many-to-many, no weights. Labels as published (not the official Formacode labels). Licence Ouverte.'
TBLPROPERTIES (
  'layer' = 'bronze', 'source.name' = 'france_travail', 'source.resource' = 'rome_formacode',
  'source.url' = 'https://www.francetravail.org/files/live/sites/peorg/files/documents/Statistiques-et-analyses/Open-data/ROME/261014-ref-formacode-v14-rome-26m10-v62-pour-open-data.xlsx',
  'source.raw_sha256' = '1f1f144c25f6776b336fe78bc252ab2c23e715b222b191ef829f15264ca68d12',
  'source.rome_version' = 'ROME 4.0 version 62 - 26M10', 'source.formacode_version' = 'V14',
  'source.realised_on' = '2026-10-15', 'source.published_on' = '2026-10-19', 'source.next_update' = '2027-03-23',
  'source.license' = 'Licence Ouverte (fr-lo)', 'source.attribution' = 'France Travail – ROME 4.0',
  'primary_key' = 'code_rome, code_formacode'
)
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/formacode/rome_v62_formacode_v14/parquet/rome_formacode_v14.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.formacode_v14_descripteurs
COMMENT 'Formacode V14 thesaurus descriptors (Centre Inffo), raw: 2,775 descriptors with official labels, semantic field, synonyms, TG/TS/TA relations (Label - code lists separated by ###), notes and tree code. Licence Ouverte 2.0.'
TBLPROPERTIES (
  'layer' = 'bronze', 'source.name' = 'centre_inffo', 'source.resource' = 'formacode_v14_descripteurs',
  'source.url' = 'https://static.data.gouv.fr/resources/formacode-r-version-14-thesaurus-de-loffre-de-formation-et-de-certification/20241220-124826/descripteur-formacode-des-champs-semantiques-20241212.xlsx',
  'source.raw_sha256' = '02f248f08185b8bf87e2088fee26068e6ec558141adfef3c4f6dd04a0561207d',
  'source.formacode_version' = 'V14', 'source.file_date' = '2024-12-12', 'source.published_on' = '2024-12-20',
  'source.license' = 'Licence Ouverte 2.0 (lov2)', 'source.attribution' = 'Formacode® V14 – Centre Inffo',
  'primary_key' = 'code_du_terme'
)
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/formacode/rome_v62_formacode_v14/parquet/formacode_v14_descripteurs.parquet`;

CREATE TABLE IF NOT EXISTS career_intelligence.bronze.formacode_v14_grands_domaines
COMMENT 'Formacode V14 top-level domains (Centre Inffo), raw: 14 domains, codes as published (e.g. 00106). Licence Ouverte 2.0.'
TBLPROPERTIES (
  'layer' = 'bronze', 'source.name' = 'centre_inffo', 'source.resource' = 'formacode_v14_grands_domaines',
  'source.url' = 'https://static.data.gouv.fr/resources/formacode-r-version-14-thesaurus-de-loffre-de-formation-et-de-certification/20241220-125109/grands-domaines-20241212.xls',
  'source.raw_sha256' = 'f713514f3df9bd18476ee64de3c971f2e7c392d9e7b5c4b3255c95efbea43b47',
  'source.formacode_version' = 'V14', 'source.file_date' = '2024-12-12', 'source.published_on' = '2024-12-20',
  'source.license' = 'Licence Ouverte 2.0 (lov2)', 'source.attribution' = 'Formacode® V14 – Centre Inffo',
  'primary_key' = 'code_du_terme'
)
AS SELECT * FROM parquet.`/Volumes/career_intelligence/bronze/landing/formacode/rome_v62_formacode_v14/parquet/formacode_v14_grands_domaines.parquet`;
