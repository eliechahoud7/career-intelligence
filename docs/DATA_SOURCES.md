# Data Source Verification Log

**Scope:** France · French language  **Verification date:** 2026-11-09
Machine-readable registry: [`config/sources.yaml`](../config/sources.yaml).

No connector is written until its source is `verified` here. A URL is recorded only if it was
successfully requested during verification; nothing below comes from guesswork.

## Verification checklist (per source)

1. Official documentation located
2. Access model (open / registration / restricted)
3. Authentication method
4. Licence / terms of use
5. Rate limits / update frequency
6. Test request executed, sample inspected (samples kept outside the repo)
7. Schema of relevant entities documented
8. Join keys to other sources identified
9. Reachability from Databricks Free Edition — **still to test** (Phase 03)

## Status summary

| Resource | Domain | Access | Licence | Status |
|---|---|---|---|---|
| ROME 4.0 bulk files (CSV/JSON/XML zip) | occupations, skills | open, no auth | Licence Ouverte | ✅ verified |
| ROME ↔ Formacode V14 table | training bridge | open, no auth | Licence Ouverte | ✅ verified |
| ROME 4.0 APIs (francetravail.io) | occupations, skills | OAuth2, registration | francetravail.io terms | 🔒 requires registration (not needed) |
| ONISEP Idéo — Fiches métiers / Fiches formations / CSVs | occupations, training | open, no auth | **ODbL** | ✅ verified |
| France Travail BMO 2026 | employment | open, no auth | Licence Ouverte | ✅ verified |
| France Travail API Marché du travail | employment | OAuth2, registration | francetravail.io terms | 🔒 requires registration |
| France Travail API Offres d'emploi | job offers | **withdrawn** | — | ⛔ restricted |
| DARES FAP 2021 hierarchy | crosswalk | open, no auth | not specified | ✅ verified |
| DARES ROME (V3) × qualification → FAP341 table | crosswalk | captcha-protected site, **manual download** | **unconfirmed** | ✅ verified (manual, sha256-pinned) |

---

## 1. France Travail — ROME 4.0

- **Documentation:** data.gouv.fr dataset [58da857388ee384902e505f5](https://www.data.gouv.fr/datasets/58da857388ee384902e505f5/) (organisation: France Travail); API catalogue entry [672cf64aa47b8d4c15d13d58](https://www.data.gouv.fr/fr/dataservices/672cf64aa47b8d4c15d13d58); technical doc PDF `open_data_v3.1.pdf` listed in the dataset.
- **Version:** ROME 4.0 **v62 "26M10"**, published 2026-10-19 (`version.txt`). About 2 releases a year; next Formacode table update announced for 2027-03-23.
- **Licence:** Licence Ouverte / Open Licence (`fr-lo`) — free reuse with attribution.

### 1a. Bulk open-data files — ✅ verified (recommended)

| Format | URL | Result |
|---|---|---|
| CSV zip | `https://api.francetravail.fr/api-nomenclatureemploi/v1/open-data/csv` | 200, 4.56 MB |
| JSON zip | `https://api.francetravail.fr/api-nomenclatureemploi/v1/open-data/json` | 200, 5.53 MB |
| XML zip | `https://api.francetravail.fr/api-nomenclatureemploi/v1/open-data/xml` | 200, 6.12 MB |
| PDF zip | `…/open-data/pdf` | 200, > 58 MB (not needed) |

No authentication. **GET only** — a `HEAD` request returns 404.

**Key CSV tables (v62):**

| File | Rows | Columns (main) |
|---|---|---|
| `unix_referentiel_code_rome` | 1,923 | `code_rome`, `code_ogr`, `libelle_rome`, `transition_eco/num/demo`, `emploi_reglemente`, `emploi_cadre`, `code_rome_parent` |
| `unix_referentiel_appellation` | 14,330 | `code_ogr`, `libelle_appellation_long/court`, `code_rome`, `classification`, `peu_usite`… (job-title synonyms → search) |
| `unix_cr_gd_dp` | 1,923 | `code_rome` → `code_grand_domaine` (14) → `code_domaine_professionel` (110) |
| `unix_texte` | 15,048 | `code_rome`, `libelle_type_texte` (definition, accès…), `position_phrase`, `libelle_texte` |
| `unix_referentiel_competence` | 20,088 | `code_ogr`, `libelle_competence`, `definition`, `code_ogr_macro_comp`, `cat_comp`, `sous_cat_comp` |
| `unix_arborescence_competences` | 19,598 | domaine → enjeu → objectif → macro-compétence → compétence |
| `unix_referentiel_savoir` | 15,699 | `code_ogr_savoir`, `libelle_savoir`, `categorie_savoir`, `sous_categorie_savoir` |
| `unix_liens_rome_referentiels` | 141,163 | `code_rome`, `code_compo_bloc`, `code_rubrique`, `code_ogr` (**occupation ↔ skill/knowledge link table**) |
| `unix_coherence_item` | 124,910 | `code_rome`, `code_ogr`, `coeur_metier` |
| `unix_rubrique_mobilite` | 18,601 | `code_rome` → `code_rome_cible` (career mobility) |
| `unix_referentiel_code_rome_riasec` | 1,923 | RIASEC profile per ROME |
| `unix_arborescence_secteur_naf` | 3,626 | ROME ↔ NAF sector (**cp1252-encoded**) |

**JSON** `unix_fiche_emploi_metier_v462.json`: 1,923 nested documents
(`rome{code_rome,intitule,code_ogr}`, `appellations[]`, `definition`, `acces_metier`,
`competences{savoir_faire, savoir_etre_professionnel, savoirs}`, `contextes_travail[]`,
`secteurs_activite[]`, `mobilites[]`). ⚠️ **Encoded cp1252, not UTF-8.**

**Phase 06 — full archive inspection (v62, sha256 `ae63cf91…7fcb`) and Bronze load:**

- 29 CSVs + `version.txt`; comma-separated, quoted, LF. Phase 02 counts for `centre_interet`
  (**30**, not 60) and `secteur_activite` (**35**, not 70) were wrong: they contain quoted
  multi-line cells *and* blank lines between records. `type_referentiel` is empty.
- All referentials have unique codes; all link tables are unique on their natural key.
  *Correction (Phase 07):* `arborescence_competences` was reported as having 15 competences
  under 2 macro-competences — wrong: those "duplicates" were the 16 empty `code_ogr_competence`
  values. Every competence has **exactly one** macro-competence; the 16 savoir-être
  macro-competences have **no** child competence.
- `referentiel_competence` holds **both levels**: 506 macro-compétences (490 savoir-faire,
  16 savoir-être; `code_macro_comp` set) and 19,582 compétences (all savoir-faire;
  parent in `code_ogr_macro_comp`, identical to `arborescence_competences`).
- `coherence_item` contains exactly the (occupation, item) pairs of link blocks 5 and 6;
  it only adds `coeur_metier` (22,031 `Principale`).
- `arborescence_secteur_naf.code_secteur_naf` joins `secteur_naf.code_secteur_naf`
  (not `code_tech_secteur_naf`).
- `item` (35,981) = `referentiel_competence` (20,088) ⊎ `referentiel_savoir` (15,699) ⊎
  `referentiel_contexte_travail` (194), with no overlap.
- **`liens_rome_referentiels.code_ogr` is polymorphic** — its target depends on the block:

  | `code_compo_bloc` | `code_rubrique` | Target | Links | Occupations |
  |---|---|---|---|---|
  | 1 | – | `referentiel_code_rome.code_ogr` (the occupation) | 1,923 | 1,923 |
  | 2 | – | `referentiel_appellation.code_ogr` | 14,330 | 1,923 |
  | 5 | 1 | `referentiel_competence` — savoir-faire | 60,517 | 1,923 |
  | 5 | 2 | `referentiel_competence` — savoir-être | 6,343 | 1,918 |
  | 5 | 3 | `referentiel_savoir.code_ogr_savoir` | 40,715 | 1,923 |
  | 6 | – | `referentiel_contexte_travail.code_ogr` | 17,335 | 1,923 |

  0 unresolved links; 0 orphans on 11 other foreign keys.
- **Bronze:** one table per CSV, `career_intelligence.bronze.rome_<entity>` (29 tables, 443,935
  rows), text exactly as published (empty fields `''`, multi-line text kept, cp1252 decoded),
  lineage `_source_*`, `_rome_version`, `_source_row`, `_run_id`, `_ingested_at`.
  Load: `sql/bronze/02_rome.sql`; checks: `sql/bronze/02_rome_checks.sql`.
  The JSON archive is not loaded (same content, denormalised).
- **Silver (Phase 07):** 24 tables `career_intelligence.silver.rome_*` — 13 reference tables
  (`rome_metier`, `rome_appellation`, `rome_competence`, `rome_macro_competence`, `rome_savoir`,
  `rome_contexte_travail`, domains, centres d'intérêt, sectors, themes, NAF) and 11
  occupation-link tables; the polymorphic link table is split by block into
  `rome_metier_appellation` (2), `rome_metier_savoir_faire` (5/1 — target is a Compétence
  **or** a Macro-compétence, see `niveau_competence`: 47,480 / 13,037), `rome_metier_savoir_etre`
  (5/2), `rome_metier_savoir` (5/3), `rome_metier_contexte_travail` (6). `''` → NULL, flags kept
  as published (O/N, oui/non). Not carried over (redundant): `cr_gd_dp_appellations`,
  `composition_bloc`, `descriptif_rubrique`, `item`, `type_referentiel`.
  Build: `sql/silver/02_rome.sql`; checks: `sql/silver/02_rome_checks.sql`.
- **Open:** `code_rome_parent` differs from `code_rome` for 1,391 occupations (405 distinct
  parents, all existing). Its meaning is not documented in the open data — kept as published,
  not interpreted.

### 1b. ROME ↔ Formacode V14 — ✅ verified, loaded to Bronze (Phase 11)

**Phase 11 — Bronze load (snapshot `rome_v62_formacode_v14`, all files sha256-pinned):**

| Bronze table | Source file | Publisher / licence | sha256 | Rows |
|---|---|---|---|---|
| `bronze.rome_formacode_v14` | `261014-ref-formacode-v14-rome-26m10-v62-pour-open-data.xlsx` | France Travail — Licence Ouverte (`fr-lo`) | `1f1f144c…8d12` | 5,958 |
| `bronze.formacode_v14_descripteurs` | `descripteur-formacode-des-champs-semantiques-20241212.xlsx` | Centre Inffo — Licence Ouverte 2.0 (`lov2`) | `02f248f0…207d` | 2,775 |
| `bronze.formacode_v14_grands_domaines` | `grands-domaines-20241212.xls` | Centre Inffo — Licence Ouverte 2.0 | `f713514f…3b47` | 14 |
| *(archive only, no table)* | `alignement-formacode-nsf-20241212.xls` | Centre Inffo — Licence Ouverte 2.0 | `8e3dff7d…27e8` | — |

- **Versions:** correspondence "ROME 4.0 version 62 - 26M10" × Formacode V14, realised
  15/10/2026, published 19/10/2026, next update 23/03/2027 (built with Centre Inffo's
  V13→V14 transcoding of 15/11/2024). Thesaurus V14 files dated 12/12/2024, reloaded on
  data.gouv.fr 20/12/2024 (dataset `6745a0e3ae06305f8ef67aae`, published from a user account
  named "Centre Inffo", not a certified organisation). Formacode® is a trademark of Centre Inffo.
- **Compatibility (verified in SQL):** 1,923/1,923 ROME codes = `silver.rome_metier` (OGR and
  labels identical, every v62 code covered); 1,220/1,220 Formacodes resolve to official V14
  descriptors; no duplicate (ROME, Formacode) pair; many-to-many preserved (1,354 ROME codes
  with several Formacodes, 844 Formacodes with several ROME codes; up to 95 / 79), no weights.
- **Fidelity:** values as published (68,724 cells compared: 0 differences); Excel numeric
  identifiers (Formacode descriptor codes, OGR) stored as their exact integer text; empty
  cells NULL; domain codes keep leading zeros (`00106`); whitespace and literal `null` kept.
  Headers → snake_case (original headers in the manifest). The descriptor file has 14
  columns (incl. `NA`, empty `Note de version` / `ex-synonyme V-1`, `Code arborescence`).
- **Labels:** the correspondence's Formacode labels are auto-Title-Cased and 73 codes have
  accented/unaccented variants — kept as published in Bronze; **official labels are
  `formacode_v14_descripteurs.descripteur_en_typo_riche`** (to be used from Silver on).
- **No NSF/ONISEP bridge:** the NSF alignment is archived in the landing volume only.
- Connector: `career_intelligence.ingestion.formacode`; load/checks:
  `sql/bronze/05_formacode.sql`, `sql/bronze/05_formacode_checks.sql`.

**Phase 12 — Silver (4 tables, `career_intelligence.silver`):**

| Table | Rows | Key | Content |
|---|---|---|---|
| `formacode_grand_domaine` | 14 | `code_grand_domaine` | official domain labels; literal `'null'` note → NULL (D3) |
| `formacode` | 2,775 | `code_formacode` | official V14 label, semantic field (code + label, D5), `code_formacode_parent`, `code_grand_domaine`, `niveau` 1–6, `nb_termes_specifiques`, `est_terme_feuille` (689 broad / 2,086 leaf), synonyms as arrays, notes |
| `formacode_terme_associe` | 3,166 | (`code_formacode`, `code_formacode_associe`) | related terms (TA); self-references excluded (D1); 76 targets outside the descriptors (annex lists, 49 codes) kept with `terme_associe_dans_descripteurs = false` (D2) |
| `rome_metier_formacode` | 5,958 | (`code_rome`, `code_formacode`) | every correspondence link, many-to-many, broad and leaf terms, no weights / primary link, no correspondence labels (D6) |

- **Verified encoding of the thesaurus:** TG = `Label - NNNNN` (exactly one parent) or, for the
  65 top terms (one per semantic field), the label of a top-level domain; TS lists are exactly
  the reverse of TG (so narrower terms are derived from `code_formacode_parent`, D8);
  `code_arborescence` extends the parent's by one segment (`niveau` = segments − 1); the
  semantic field is constant down the tree; domain = domain of the field's top term (D7),
  equal to the tree-code letter for all 2,775. Codes are parsed from the trailing ` - NNNNN`
  (labels may contain ` - `). Every TA list contains its own descriptor (export artefact).
- **Labels** come only from the official descriptors (whitespace-normalised); the
  correspondence's Title-Case labels remain in Bronze. Always-empty descriptor columns
  (`note_de_version`, `ex_synonyme_v_1`) are not carried (D4).
- Build: `sql/silver/04_formacode.sql`; checks: `sql/silver/04_formacode_checks.sql`.

*Phase 02 notes:*
`261014-ref-formacode-v14-rome-26m10-v62-pour-open-data.xlsx` — 5,958 rows:
`Code ROME`, `Libellé fiche ROME`, `Code OGR ROME`, `Code FORMACODE V14`, `Libellé FORMACODE V14`.
⚠️ The filename is release-specific (`261014-…-26m10-v62`). *Superseded (Phase 11):* the
connector uses the URL **and sha256 pinned** in `config/sources.yaml` for reproducibility; at
each ROME release the new URL is looked up on the data.gouv.fr ROME dataset, verified, and the
registry entry (URL, sha256, snapshot) is updated deliberately.

### 1c. ROME 4.0 REST APIs — 🔒 requires registration
- 4 APIs: Métiers, Compétences, Contextes de travail, Fiches métiers. Rate limit **1 call/s**.
- Auth: OAuth2 *client credentials*. Token endpoint confirmed to exist:
  `POST https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire`
  returns `400 {"error":"invalid_client"}` without credentials. API gateway `https://api.francetravail.io/partenaire/` returns `401` without a token.
- Resource paths, scopes and response schemas are only visible after logging in to francetravail.io (catalogue pages are JS shells), so **they are not recorded**.
- **Assessment:** not needed, because the bulk files contain the full referential without auth or rate limits.

---

## 2. ONISEP — Idéo open data

- **Documentation:** data.gouv.fr organisation [ONISEP](https://www.data.gouv.fr/organizations/534fff9ba3a7292c64a78031/) — 59 datasets, all mirrored from `data.onisep.fr`; each dataset has a "Documentation" and "Tables de référence" xlsx.
- **Licence:** **ODbL** on all 59 datasets. Reuse is allowed with **attribution ("Source : Onisep")**, and any *publicly used* derived database must be shared under ODbL (share-alike).
- **Access:** direct download, no authentication. Updated roughly monthly (most datasets modified 2026-11-04 to 11-06).
- ⚠️ **Schema changes announced:** structure change on 2026-01-20 (Métiers, Formations initiales); `<centres_interet>` IDs and labels redesigned in October 2026; `<poursuites_etudes>` block being simplified in 2 phases.

| Dataset | URL (verified) | Size | Content |
|---|---|---|---|
| Idéo-Fiches métiers | `https://data.onisep.fr/api/v1/downloads/5fe0808a2da6f/5fe0808a2da6f.zip` | 2.8 MB (XML 13 MB) | 1,138 `<metier>` |
| Idéo-Fiches formations | `https://data.onisep.fr/api/v1/downloads/5fe07a9ecc960/5fe07a9ecc960.zip` | 1.5 MB (XML 16 MB) | 2,349 `<formation>` |
| Idéo-Métiers Onisep (CSV) | `https://data.onisep.fr/api/v1/downloads/5fa5949243f97/5fa5949243f97.csv` | 0.6 MB | 1,560 rows |
| Idéo-Formations initiales en France (CSV) | `https://data.onisep.fr/api/v1/downloads/5fa591127f501/5fa591127f501.csv` | 2.4 MB | 5,799 rows |
| Table de passage certifications/formations | `https://data.onisep.fr/api/v1/downloads/6152ccdf850ef/6152ccdf850ef.csv` | 1.6 MB | 5,245 rows |
| Nomenclature domaines / sous-domaines | `https://data.onisep.fr/api/v1/downloads/5fa58d750a60c/5fa58d750a60c.csv` | 7 KB | 132 rows |

CSV files are UTF-8 with BOM and `;`-separated (the nomenclature file uses mixed quoting).

**Fiches métiers (`<metier>`):** `identifiant` (MET.xxx), `nom_metier`, `libelle_feminin/masculin`,
`synonymes`, **`romesV3/romeV3`** (ROME code), `competences`, `nature_travail`, `condition_travail`,
`acces_metier`, `vie_professionnelle` (salary text), `accroche_metier` — **HTML fragments** —
`statuts`, `niveau_acces_min`, `formations_min_requise`, `secteurs_activite`, `centres_interet`.

**Fiches formations (`<formation>`):** `identifiant` (FOR.xxx), `code_scolarite`, `libelle_complet`,
`type_Formation`, `duree_formation`, `url` (often a France Compétences **RNCP** URL), `nsf_discipline`,
`nsf_fonction`, `niveau_certification`, `niveau_etudes`, `sous_tutelle`, **`metiers_formation/metier/id`** (MET.xxx).

**Phase 08 — Bronze load (snapshot 20261109):**

| Dataset | Raw file (sha256) | Records | Bronze table |
|---|---|---|---|
| Idéo-Fiches métiers | `fiches_metiers.zip` (`eb04222a…9bc8`) | 1,138 `<metier>` | `bronze.onisep_fiches_metiers` (21 cols) |
| Idéo-Fiches formations | `fiches_formations.zip` (`4fc73fba…b2a3`) | 2,349 `<formation>` | `bronze.onisep_fiches_formations` (31 cols) |
| Idéo-Formations initiales en France | `formations_initiales.csv` (`355d7dd5…2e8`) | 5,799 rows | `bronze.onisep_formations_initiales` (16 cols) |

- **Structure:** every record has the same top-level elements in the same order, none
  repeated; no namespaces; `id` attributes only inside nested blocks. Text-only elements →
  STRING columns named like the tag (HTML descriptions are CDATA in the source → kept as text);
  elements with children (`romesV3`, `formations_min_requise`, `metiers_formation`,
  `nsf_discipline`…) → their **original XML fragment** (parse in Silver with `xpath`).
  Round-trip check: all 3,487 records rebuilt from the staged data are canonically identical
  to the source XML. CSV headers → snake_case (mapping in the manifest).
- **Relationships (identifiers only, nothing inferred):** all 2,349 Fiches formations ids are
  in Formations initiales (the full catalogue, 5,799 `FOR.n`); Fiches formations reference
  984 distinct métiers, all present in Fiches métiers; 931 Fiches métiers carry ≥ 1 ROME code.
- Raw files are kept per snapshot (`data/raw/onisep/<YYYYMMDD>/`); ONISEP has no version
  number. Load: `sql/bronze/03_onisep.sql`; checks: `sql/bronze/03_onisep_checks.sql`.
- **Licence obligations carried into the platform:** every ONISEP-derived table records
  `source.license = ODbL` and `source.attribution = Source : Onisep`; the application must
  display "Source : Onisep", and any publicly used database derived from these tables
  (Silver/Gold, exports) must be published under ODbL.

**Phase 09 — Silver (8 tables, `career_intelligence.silver.onisep_*`, all ODbL):**

| Table | Rows | Key | Content |
|---|---|---|---|
| `onisep_metier` | 1,138 | `identifiant` (MET.n) | occupation; small lists (synonymes, statuts, secteurs, centres d'intérêt, publications, sources) as `ARRAY<STRUCT>` |
| `onisep_formation` | 2,349 | `identifiant` (FOR.n) | training sheet; = `onisep_formation_initiale.identifiant` (1:1, validated FK) |
| `onisep_formation_initiale` | 5,799 | `identifiant` (FOR.n from the URL) | full initial-training catalogue; `codes_nsf`, `domaines_sous_domaines` as arrays |
| `onisep_metier_rome` | 976 | (`identifiant_metier`, `code_rome_source`) | occupation → ROME, `statut_code` valide / non_resolu |
| `onisep_formation_metier` | 6,756 | (`identifiant_formation`, `identifiant_metier`) | training sheet → occupation (984 occupations, 0 orphans) |
| `onisep_metier_formation_min_requise` | 7,184 | (`identifiant_metier`, `identifiant_formation`) | occupation → minimum required training; 58 FOR ids outside the catalogue (flagged) |
| `onisep_metier_associe` | 825 | (`identifiant_metier`, `identifiant_metier_associe`) | related occupations; 200 MET ids not in Fiches métiers (flagged) |
| `onisep_formation_poursuite` | 2,664 | (`identifiant_formation`, `identifiant_formation_poursuite`) | further study; 1 FOR id outside the catalogue (flagged) |

- **ROME linkage (recalculated from Bronze):** 976 occupation→code links on 931 occupations;
  **968 links valid** in ROME v62; **8 links unresolved** — 6 truncated codes `A15`, `B16` (×3),
  `H2`, `K15`, `K19`, `N2`, kept verbatim with `statut_code = 'non_resolu'`. Occupations:
  931 with any code, **928 with ≥ 1 valid code**, 3 with only unresolved codes, 5 mixing
  both, 207 without code. (Earlier summaries quoted 928 or 931: both are right — "valid"
  vs "any" code.)
- **Normalisation:** labels — whitespace runs (incl. U+00A0, tabs) → one space, trimmed,
  `''` → NULL; HTML descriptions — edges trimmed only (internal NBSP are French typography);
  `duree_formation` loses its literal quotes (`"3 ans"` → `3 ans`); dates → `DATE`.
- **Open:** `metier_transverse` is either `oui` or empty in the source; kept as text (`oui` /
  NULL) — whether empty means "non" is not documented. `niveau_certification` (fiche) and
  `niveau_de_certification` (catalogue) use different code systems (`niveau 7` vs `1`), kept
  as published.
- Build: `sql/silver/03_onisep.sql`; checks: `sql/silver/03_onisep_checks.sql`.

**Measured linkage:**
- 928 / 1,138 ONISEP occupations carry ≥ 1 ROME code valid in v62. The codes used have the same format as ROME 4.0 even though the tag is named `romesV3`.
- Those occupations reference 407 distinct valid ROME codes, i.e. **21 % of the 1,923 ROME codes**.
- 6 invalid / truncated codes (e.g. `A15`, `K19`, `H2`) must be rejected in Silver.
- 2,212 / 2,349 trainings (94 %) reach ≥ 1 ROME code via `FOR → MET → ROME`.
- 1,506 trainings expose an RNCP id in their URL.

---

## 3. France Travail — employment & labour-market data

Organisation on data.gouv.fr: [France Travail](https://www.data.gouv.fr/organizations/534fffa3a3a7292c64a78094/) — 15 datasets, 13 API entries.

### 3a. Enquête Besoins en Main-d'Œuvre (BMO) — ✅ verified (recommended)
- **Dataset:** [561fa564c751df4f2acdbb48](https://www.data.gouv.fr/datasets/561fa564c751df4f2acdbb48/) — Licence Ouverte, annual, editions 2015–2026.
- **URL:** `https://www.francetravail.org/files/live/sites/peorg/files/documents/Statistiques-et-analyses/Open-data/BMO/Base-open-data-BMO-2026.xlsx` (3.8 MB, no auth).
- **Schema** (sheet `BMO_2026_open_data`, 53,786 rows): `annee`, `Code métier BMO` (**FAP2021**, 217 codes), `Nom métier BMO`, `Famille_met`, `Lbl_fam_met`, `REG`, `NOM_REG`, `Dept`, `NomDept`, `BE26`, `NOMBE26` (bassin d'emploi), `clpe`, `met` (recruitment projects), `xmet` (judged difficult), `smet` (seasonal).
- ⚠️ 43,899 rows (82 %) contain `*` (statistical secrecy) in at least one measure. Aggregate at department or region level, where secrecy matters less.
- ⚠️ The schema drifts between editions: the data uses `BE26` but the description sheet says `BE25`. Older years are zipped, and their filenames are inconsistent.
- ⚠️ Occupation codes are **FAP2021, not ROME** → a crosswalk is required (§4).

**Phase 03 profiling (full file, 2026-11-09, sha256 `735d0443…92e0`):**

| Aspect | Finding | Handling |
|---|---|---|
| Row grain | unique on **(occupation, department, bassin, CLPE)**. Not on (occupation, bassin): a bassin may span several departments (19 do) and CLPEs (184 do) | key used in validation; rows are disjoint pieces → additive to department / region |
| Types | pandas infers `REG`, `BE26`, `annee` as int → loses leading zeros (`01`→`1`); `Dept` mixes `01`…`976`, `2A`, `2B` | read **everything as text** |
| Missing values | only `clpe`: 100 nulls, all bassin `9399` MONACO | allowed (warning) |
| Secrecy `*` | `met` 24.2 % · `xmet` 48.6 % · `smet` 74.2 % of rows | kept verbatim in Bronze; typed to null + flag in Silver |
| Codes | 217 occupation codes, all match `[A-Z][A-Z0-9][A-Z]\d{2}` (e.g. `A0X40`, `QAX01`); 8 families; 18 regions; 101 departments; 406 bassins; 361 CLPE | format checks |
| Consistency | `xmet ≤ met` and `smet ≤ met` on all non-secret rows; no zero values | check (warning if violated) |
| Text quality | 1 occupation label (257 rows) ends with a **non-breaking space** U+00A0 — SQL `trim()` does not remove it; 2 bassin labels contain an internal double space (`AIX  GARDANNE SALON`, `LURE  / HERICOURT`) | Silver: every whitespace run (space, tab, U+00A0, U+202F) → one space, then edges trimmed. 257 occupation rows and 254 bassin rows changed, whitespace only |
| Code ↔ label | strictly 1:1 for occupation, family, region, department and bassin | — |
| Totals | 2,237,486 recruitment projects in non-secret cells | — |

Connector: `career_intelligence.ingestion.bmo` → raw `data/raw/france_travail/bmo/2026/bmo_2026.xlsx`,
Bronze-ready `data/staging/france_travail/bmo/bmo_2026.parquet` + `.manifest.json` (git-ignored).

### 3b. API Marché du travail — 🔒 requires registration
- Catalogue: [672cf65f739fcf87e0f02be2](https://www.data.gouv.fr/fr/dataservices/672cf65f739fcf87e0f02be2) — `access_type: open`, **10 calls/s**, sign-up at `https://francetravail.io/inscription`.
- Described content: job seekers registered and new, offers, hirings, recruitment difficulty, offered salary, territorial dynamics indicator — **by métier, sector, skill and territory**.
- Same OAuth2 mechanism as §1c. Paths, scopes, schemas and the métier code used (expected to be ROME) **cannot be verified until an account exists**.

### 3c. API Offres d'emploi — ⛔ restricted
Withdrawn from francetravail.io "le temps d'une analyse des modalités de distribution et de réutilisation", following mass automated use by AI tools. Access only on request via the contact form. **Excluded from scope.**

### 3d. Other France Travail datasets (not retained)
Demandeurs d'emploi inscrits (quarterly CVS-CJO series), Offres d'emploi diffusées, Offres collectées et satisfaites, Entrées en formation, Sortants de formation, Emploi intérimaire. They are mostly national or regional aggregates **without an occupation dimension**, so they are of limited value for occupation-level search. They can be revisited if a contextual "national indicators" page is wanted.

---

## 4. Crosswalk — DARES FAP 2021

- **Hierarchy — ✅ verified:** `https://data.dares.travail-emploi.gouv.fr/api/explore/v2.1/catalog/datasets/dares_nomenclature_fap2021/exports/csv?use_labels=true` — 341 rows, columns `Code FAP 22 / 86 / 228 / 341` + labels. **No ROME column.** Licence "not specified" on data.gouv.fr.
- **ROME × qualification → FAP341 table — ✅ verified (manual download, Phase 10).**
  The DARES site (incl. its static files) serves a captcha to automated clients and the
  open-data mirrors only hold the hierarchy, so the files were downloaded in a browser on
  2026-11-09 from `https://dares.travail-emploi.gouv.fr/donnees/la-nomenclature-des-familles-professionnelles-2021`
  (no direct file URL obtainable) into `data/raw/dares/fap2021/20261109/`:

  | File | sha256 | Role |
  |---|---|---|
  | `Dares_Table_passage_ROME_Qualif_to_FAP2021_pour_programme.csv` | `aa4fc948…2d13` | loaded |
  | `Dares_Table_passage_ROME_Qualif_to_FAP2021_pour_visualisation.xlsx` | `e06876eb…cdec` | documentation, archived in the volume |

  - **Format:** cp1252 (strict), `;`, CRLF, no quotes; columns `ROME; Intitule_ROME; Qualif;
    FAP341; Intitule_FAP341`; 5,320 rows = 532 ROME codes × 10 qualification classes; 337
    FAP341 codes; key **(ROME, Qualif)**, one FAP341 per pair. The XLSX (compact form:
    empty class = all, `Q_246` = classes 2, 4, 6) encodes exactly the same 5,320 pairs; 50
    ROME labels are worded differently between the two files (codes and mapping identical).
  - **ROME version: V3** (stated in the XLSX). **Qualification:** DARES 10-class scale built
    from PCS-2020 (0 non précisé, 1 manœuvres … 9 ingénieurs et cadres); DARES notes it
    differs from France Travail's (class 4 = indépendants here, ouvriers hautement qualifiés
    at France Travail).
  - **Qualification-dependent:** 282 ROME codes map to 2-5 FAP341 families depending on the
    class; 250 to one. **Never collapse to ROME → FAP.**
  - **Bronze:** `career_intelligence.bronze.dares_rome_qualif_fap2021` (5,320 rows, all
    source columns STRING, values byte-identical to the source after decoding, incl. class 0
    and 77 labels ending with a non-breaking space; 13 lineage columns recording manual
    download, date, checksum, encoding). Connector: `career_intelligence.ingestion.dares`
    (never downloads; refuses files whose sha256 differs from the pinned value).
    Load/checks: `sql/bronze/04_dares.sql`, `sql/bronze/04_dares_checks.sql`.
  - **Licence: UNCONFIRMED.** No statement in either file; the open-data mirrors list it as
    "not specified". Other DARES open datasets use Licence Ouverte v2.0, but this is **not
    assumed** for this table. Attribution used: "Source : Dares, nomenclature des familles
    professionnelles FAP-2021".
  - **Compatibility analysis (approved recommendation B — integrable only with
    qualification limitations):**
    - all 532 DARES ROME V3 codes exist in ROME v62 and are exactly the 532 v62 codes with
      `code_rome_parent = code_rome`; the other 1,391 v62 codes all have a parent among them.
      The same code often has a **narrower meaning in v62** (e.g. L1101 "Animation musicale
      et scénique" → "DJ"): a direct DARES-code = v62-code join is **not safe**.
      `code_rome_parent` is documented by France Travail as the occupation "dont peut
      dériver/hériter le métier"; its equality with the V3 code is demonstrated, not
      documented — **not used** until approved.
    - BMO `code_metier_bmo` = FAP 2021 at the **228 level** (217/217, identical labels); all
      337 FAP341 roll up (official DARES hierarchy) to 226 FAP228, covering all 217 BMO codes.
      Unmapped: 4 FAP341 without ROME (`T2B60b`, `V5X84b`, `X0X00`, `X0X01`); 9 FAP228 reached
      by DARES but absent from BMO (public administration, magistrates, police/army), so 19
      ROME V3 codes (K14xx–K19xx) reach no BMO occupation.
    - **BMO has no qualification field**; 666 of the 922 BMO→ROME links hold only for some
      classes, and for 113 of 217 BMO occupations every link is conditional. Qualification
      must not be inferred; BMO counts must not be apportioned to ROME codes.

---

## 5. Join keys between sources

| From | To | Key | Quality |
|---|---|---|---|
| ROME occupation | ROME skills / knowledge | `code_rome` ↔ `code_ogr` (`liens_rome_referentiels`) | native, complete |
| ONISEP occupation | ROME | `romesV3/romeV3` = `code_rome` | 928/1,138 MET; 6 invalid codes |
| ONISEP training | ONISEP occupation | `metiers_formation/metier/id` = `MET.xxx` | 2,349/2,349 |
| ONISEP training | ROME (transitive) | FOR → MET → `code_rome` | 2,212/2,349 (94 %) |
| ONISEP training | certifications | RNCP (URL), `code_scolarite`, Certif Info (table de passage) | 1,506 with RNCP |
| ROME | training domain | Formacode V14 (`silver.rome_metier_formacode` → `silver.formacode`) | 5,958 links, many-to-many; 1,923/1,923 ROME v62, 1,220/1,220 Formacodes resolved (445 broad, 775 leaf) |
| BMO (FAP2021, 228 level) | ROME (V3) | `bronze.dares_rome_qualif_fap2021` (ROME × qualification → FAP341, rolled up to FAP228 via the DARES hierarchy) | many-to-many, **qualification-dependent**; ROME V3 ≠ v62 scope — not joined yet |
| Marché du travail API | ROME | expected `code_rome` | **unverified** (registration) |
| Territory | all employment data | INSEE region / department codes, bassin d'emploi | native in BMO |

## 6. Open items

- [x] ~~Download the DARES FAP ↔ ROME table manually; check its ROME version~~ — done (Phase 10): ROME **V3** × qualification → FAP341, loaded to Bronze.
- [ ] **DARES licence:** confirm the reuse conditions of the correspondence table (site legal notice) — currently UNCONFIRMED.
- [ ] **Decision pending:** whether `code_rome_parent` may bridge ROME V3 families to v62 codes in Silver/Gold; and how BMO figures are presented given qualification-conditional links (no apportioning).
- [x] ~~Decide whether to register on francetravail.io~~ — **decided 2026-11-09: not now.** BMO 2026 is the first employment dataset.
- [ ] Test outbound access (still open: BMO was loaded by uploading the local staging file, so this is not yet needed) from Databricks Free Edition serverless to `api.francetravail.fr`, `data.onisep.fr`, `www.francetravail.org` and `www.data.gouv.fr`.
- [ ] Read the francetravail.io terms of use if an API is adopted.
