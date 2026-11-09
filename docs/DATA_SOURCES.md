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
| DARES FAP ↔ PCS ↔ ROME table | crosswalk | captcha-protected site | not specified | ✋ manual download |

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

### 1b. ROME ↔ Formacode V14 — ✅ verified
`261014-ref-formacode-v14-rome-26m10-v62-pour-open-data.xlsx` — 5,958 rows:
`Code ROME`, `Libellé fiche ROME`, `Code OGR ROME`, `Code FORMACODE V14`, `Libellé FORMACODE V14`.
⚠️ The filename is release-specific (`261014-…-26m10-v62`), so connectors must find the current link from the data.gouv.fr dataset API instead of hard-coding it.

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
| Text quality | 257 `Nom métier BMO` values with trailing spaces | trimmed in Silver |
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
- **FAP ↔ PCS ↔ ROME table — ✋ manual download:** linked from the ROME dataset ("Les tables de correspondance ROME / autres référentiels – FAP / PCS / ROME" → `https://dares.travail-emploi.gouv.fr/donnees/la-nomenclature-des-familles-professionnelles-2021`). That site serves a **captcha** (bot protection) to automated clients, so the file must be downloaded manually in a browser into `data/raw/dares/`. Its ROME version (v3 vs 4.0) and its licence are **still to verify**.

---

## 5. Join keys between sources

| From | To | Key | Quality |
|---|---|---|---|
| ROME occupation | ROME skills / knowledge | `code_rome` ↔ `code_ogr` (`liens_rome_referentiels`) | native, complete |
| ONISEP occupation | ROME | `romesV3/romeV3` = `code_rome` | 928/1,138 MET; 6 invalid codes |
| ONISEP training | ONISEP occupation | `metiers_formation/metier/id` = `MET.xxx` | 2,349/2,349 |
| ONISEP training | ROME (transitive) | FOR → MET → `code_rome` | 2,212/2,349 (94 %) |
| ONISEP training | certifications | RNCP (URL), `code_scolarite`, Certif Info (table de passage) | 1,506 with RNCP |
| ROME | training domain | Formacode V14 (`rome_formacode`) | 5,958 links |
| BMO (FAP2021) | ROME | DARES FAP ↔ ROME crosswalk | **pending manual download**; many-to-many |
| Marché du travail API | ROME | expected `code_rome` | **unverified** (registration) |
| Territory | all employment data | INSEE region / department codes, bassin d'emploi | native in BMO |

## 6. Open items

- [ ] **PENDING (deferred 2026-11-09):** download the DARES FAP ↔ PCS ↔ ROME table manually; check its ROME version and licence. *Blocks any BMO ↔ ROME join; no join is attempted until then.*
- [x] ~~Decide whether to register on francetravail.io~~ — **decided 2026-11-09: not now.** BMO 2026 is the first employment dataset.
- [ ] Test outbound access from Databricks Free Edition serverless to `api.francetravail.fr`, `data.onisep.fr`, `www.francetravail.org` and `www.data.gouv.fr`.
- [ ] Read the francetravail.io terms of use if an API is adopted.
