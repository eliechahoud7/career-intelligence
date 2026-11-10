# Career Intelligence

**Multi-source data integration and search platform for career guidance in France.**

## Overview

Choosing an occupation or a training path means consulting public data that is scattered across
several publishers: the ROME occupation repository, training classifications and catalogues, and
labour-market surveys. Each source has its own identifiers, formats and licence.

Career Intelligence integrates six official French open datasets into a layered data model on
Databricks (Bronze → Silver → Gold → Search) and exposes it through a French-language Streamlit
application. It lets a user:

- search occupations and read their profile and skills;
- explore training domains and training programmes linked to occupations;
- explore recruitment intentions by occupational family and area.

**Objectives:** build a reproducible ingestion pipeline from official open data, integrate the
sources without inventing relationships, validate data quality at every layer, and serve the data
through a read-only SQL search layer and a web application.

> **Status:** complete and validated as an academic portfolio project that runs locally.
> Six datasets are loaded from Bronze to Gold and exposed through 22 SQL query contracts and four
> application pages. Final validation: 622 offline tests passed (2 skipped), 55 live Databricks
> tests passed, and 325/325 SQL data-quality checks are `true` (see
> [Testing & Validation](#testing--validation)).

## Screenshots

Captured from the application running locally on live Databricks data (interface in French).

<p align="center">
  <img src="docs/images/01-recherche-metier.png" alt="Rechercher un métier: search results for « infirmier » with domain and status filters" width="860">
  <br><em>Rechercher un métier — search by name, ROME code or keyword, with domain and status filters.</em>
</p>

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="docs/images/03-fiche-metier.png" alt="Fiche métier J1506: header, badges, counters and definition">
      <br><em>Fiche métier — profile of a ROME 4.0 occupation (J1506).</em>
    </td>
    <td width="50%" valign="top">
      <img src="docs/images/04-fiche-competences.png" alt="Fiche métier J1506: skills tab with core skills marked">
      <br><em>Fiche métier — skills, with core skills marked.</em>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="docs/images/05-formations-domaines.png" alt="Explorer les formations: the 14 Formacode grand domains">
      <br><em>Explorer les formations — the 14 Formacode grand domains (1,220 descriptors linked to an occupation).</em>
    </td>
    <td width="50%" valign="top">
      <img src="docs/images/08-formations-onisep-metiers.png" alt="Explorer les formations: an ONISEP programme and its ROME occupations">
      <br><em>Explorer les formations — an ONISEP programme and its occupations (Source : Onisep, ODbL).</em>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="docs/images/09-marche-territoires.png" alt="Explorer le marché du travail: reading guide and regional comparison chart">
      <br><em>Explorer le marché du travail — BMO 2026 recruitment intentions by region (minimums).</em>
    </td>
    <td width="50%" valign="top">
      <img src="docs/images/11-marche-difficultes.png" alt="Explorer le marché du travail: families with the most difficult recruitment projects">
      <br><em>Explorer le marché du travail — families with the most recruitment projects judged difficult (minimum counts).</em>
    </td>
  </tr>
</table>

All 12 screenshots, including filtered search, Formacode and ONISEP details, a family view and
the mobile layout, are in [`docs/images/`](docs/images/).

## Key Features

| Page | What it offers | Data |
|---|---|---|
| **Rechercher un métier** — profession search | Search by occupation name, job title, ROME code or keyword (optionally in definitions and access texts); filters by domain, professional domain, *cadre* and regulated status; pagination; « Rechercher » button | ROME 4.0 v62 |
| **Fiche métier** — occupation profile | Definition and access conditions, job titles, skills (savoir-faire, savoir-être, savoirs, work contexts) with core skills marked, RIASEC and transition indicators | ROME 4.0 v62 |
| **Explorer les formations** — training exploration | The 14 Formacode grand domains and their descriptors with the linked occupations (many-to-many); ONISEP training programmes, their linked occupations and the ONISEP coverage (392 / 1,923 occupations) | Formacode V14, ROME ↔ Formacode, ONISEP |
| **Explorer le marché du travail** — labour-market analysis | BMO 2026 recruitment intentions: comparison of regions and departments, ranking of FAP228 families in an area, one family across areas, families with the most projects judged difficult; charts and exact-figure tables | BMO 2026 |

Search is case- and accent-insensitive, requires every word of the query, and ranks results by
match tier only (for example, an exact code before a label match), never by a weight or score.
Where source data is displayed, the page shows its source attribution and licence (on the search
page, once results are listed).

## Architecture

```
 Official open-data files (France Travail, Centre Inffo, ONISEP, DARES)
            │
            ▼
 Python connectors  ── download (or read manual downloads), validate, stage as Parquet + manifest
            │           local, src/career_intelligence/ingestion/
            ▼
 Unity Catalog volume  bronze.landing
            │
            ▼                 Databricks Free Edition · Delta Lake · Databricks SQL (sql/)
 ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────────────────────────┐
 │  BRONZE  │ ─► │  SILVER  │ ─► │   GOLD   │ ─► │ SEARCH: 4 views + 22 query contracts │
 │ raw text │    │ cleaned, │    │integrated│    │ (sql/search/queries/q01…q22)         │
 │+ lineage │    │  typed   │    │  model   │    └──────────────────┬───────────────────┘
 └──────────┘    └──────────┘    └──────────┘                       │ serverless SQL warehouse
            each layer has a *_checks.sql file                      ▼
                                              SearchClient (read-only, validated parameters)
                                                                    │
                                                                    ▼
                                              Streamlit application (4 pages, localhost)
```

- **All transformations are written in Databricks SQL**, not PySpark: every layer is built by SQL
  scripts in `sql/`, each paired with a check file.
- **Ingestion runs locally**: the connectors produce Bronze-ready Parquet files that are uploaded
  to a Unity Catalog volume with the Databricks CLI.
- **The application contains no SQL**: `SearchClient` (`src/career_intelligence/search/`) runs
  only the registered contract files, byte-identical to the repository, after a read-only check,
  with typed and validated parameters.

## Data Sources

| Dataset | Publisher | Role in the project | Licence | Shown in the app |
|---|---|---|---|---|
| ROME 4.0, version 62 ("26M10") | France Travail | Occupations, job titles, skills, texts, domains | Licence Ouverte (Etalab) | Yes |
| BMO 2026 (Besoins en Main-d'Œuvre) | France Travail | Recruitment intentions by FAP2021 family and area | Licence Ouverte (Etalab) | Yes |
| ROME ↔ Formacode V14 correspondence | France Travail | Occupation ↔ training-domain links (5,958, many-to-many) | Licence Ouverte (Etalab) | Yes |
| Formacode® V14 thesaurus and grand domains | Centre Inffo | Official training-domain labels and hierarchy | Licence Ouverte 2.0 | Yes |
| ONISEP Idéo open data (occupations, training sheets, initial training catalogue) | ONISEP | Training programmes and their links to occupations | **ODbL** | Yes |
| DARES FAP 2021 nomenclature and ROME × qualification → FAP correspondence | DARES | FAP hierarchy; ROME **V3** × qualification → FAP341 | **Unconfirmed** | **No** |

Before each connector was written, the source documentation and licence information were
reviewed and a test download was checked (sha256 checksum); the francetravail.io APIs were not
used. Reviewing a licence does not mean it was confirmed: **the DARES reuse licence remains
unconfirmed, so DARES data is loaded up to Gold but is not exposed in the application.** Each
source stays subject to its own licence and terms. Review evidence, schemas and measured
coverage: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

### Attribution obligations

| Source | Licence | Obligation |
|---|---|---|
| France Travail — ROME 4.0, BMO, ROME ↔ Formacode correspondence | Licence Ouverte (Etalab) | Attribution to France Travail |
| Centre Inffo — Formacode® V14 thesaurus | Licence Ouverte 2.0 | Attribute "Formacode® V14 – Centre Inffo" (Formacode® is a registered trademark) |
| DARES — FAP 2021 nomenclature and ROME × qualification → FAP correspondence | **Unconfirmed** (no statement in the files; not assumed to be Licence Ouverte) | Attribute "Source : Dares, nomenclature des familles professionnelles FAP-2021"; confirm reuse conditions before any public release |
| **ONISEP — Idéo open data** | **Open Database License (ODbL)** | Display **"Source : Onisep"**; any publicly used database derived from ONISEP data must be shared under **ODbL** (share-alike) |

All ONISEP-derived tables (Bronze and Silver) and the Gold view `v_metier_formation_onisep` carry the
table properties `source.license = ODbL` and `source.attribution = Source : Onisep`, and the
application displays "Source : Onisep" wherever ONISEP-derived data is shown.

## Data Engineering Pipeline

### 1. Ingestion (local Python)

| Dataset | Command | Output (git-ignored) |
|---|---|---|
| France Travail BMO | `python -m career_intelligence.ingestion.bmo [--year 2026] [--force]` | `data/raw/france_travail/bmo/<year>/bmo_<year>.xlsx` (raw, immutable)<br>`data/staging/france_travail/bmo/bmo_<year>.parquet` + `.manifest.json` |
| France Travail ROME 4.0 | `python -m career_intelligence.ingestion.rome [--force]` | `data/raw/france_travail/rome/v<version>/rome_open_data_csv.zip` (kept per release)<br>`data/staging/france_travail/rome/v<version>/<entity>.parquet` (one per CSV) + `rome_v<version>.manifest.json` |
| ONISEP (Fiches métiers, Fiches formations, Formations initiales) | `python -m career_intelligence.ingestion.onisep [--force]` | `data/raw/onisep/<YYYYMMDD>/` (3 files, kept per snapshot)<br>`data/staging/onisep/<YYYYMMDD>/<dataset>.parquet` + `onisep_<YYYYMMDD>.manifest.json` |
| ROME ↔ Formacode V14 + Formacode V14 thesaurus | `python -m career_intelligence.ingestion.formacode [--force]` | `data/raw/formacode/<snapshot>/` (4 files, sha256-pinned)<br>`data/staging/formacode/<snapshot>/<table>.parquet` (3 tables) + manifest |
| DARES ROME × qualification → FAP 2021 (manual download) | `python -m career_intelligence.ingestion.dares` (`--readme`: qualification classes from the XLSX `Lisez-moi` sheet) | reads `data/raw/dares/fap2021/<YYYYMMDD>/` (files downloaded in a browser, sha256-pinned in `config/sources.yaml`)<br>`data/staging/dares/fap2021/<YYYYMMDD>/rome_qualif_fap2021[_lisez_moi].parquet` + `.manifest.json` |
| DARES FAP 2021 nomenclature (22 / 86 / 228 / 341) | `python -m career_intelligence.ingestion.fap2021 [--force]` | `data/raw/dares/fap2021_nomenclature/<snapshot>/` (sha256-pinned)<br>`data/staging/dares/fap2021_nomenclature/<snapshot>/dares_fap2021_nomenclature.parquet` + manifest |

Each run downloads a file only if it is missing (`--force` to refresh), reads every value as text,
standardises column names, validates structure, formats, keys and consistency, and writes a
Parquet file with lineage columns (`_source_*`, `_run_id`, `_ingested_at`) and a JSON manifest
(sha256 checksum, validation report, column profile). The DARES, FAP 2021 and Formacode
connectors refuse any file whose checksum differs from the value pinned in `config/sources.yaml`;
download URLs come only from verified entries in that registry.

### 2. Bronze — raw, faithful copies

One Delta table per source file (39 tables), every value kept as text, with lineage columns.
Statistical-secrecy markers (`*` in BMO) and source typos are preserved as published.

### 3. Silver — cleaned, typed, per source

40 tables: types applied, whitespace normalised (including non-breaking spaces), statistical
secrecy turned into `NULL` plus a `*_secret` flag, source codes kept verbatim, relationships
extracted into link tables, unresolved or invalid codes flagged rather than dropped.

### 4. Gold — integration

3 tables and 6 views built from Silver only: occupations with their job titles, skills, Formacode
domains and ONISEP training; BMO recruitment aggregated by FAP228 family and area; the DARES
correspondence kept separate. Links are never weighted or invented, and the licence and
attribution of every Gold object are recorded in `gold.source_licence`.

### 5. Search — serving layer

4 views over Gold and 22 parameterized query contracts, described in the next section.

### Data-quality validation

Each layer has a companion `*_checks.sql` file (13 files) whose `check_*` columns must all be
`true`: row counts against the source, key uniqueness, referential integrity, recomputation of
derived values from the previous layer, and licence properties.

<details>
<summary>Load steps on Databricks (run on the SQL warehouse, in order)</summary>

1. `sql/00_setup/01_catalog_schema_volume.sql` — catalog, schema, volume (idempotent)
2. Upload the staged BMO file:
   `databricks fs cp data\staging\france_travail\bmo\bmo_2026.parquet dbfs:/Volumes/career_intelligence/bronze/landing/france_travail/bmo/2026/bmo_2026.parquet --profile career-intelligence`
3. `sql/bronze/01_bmo_2026.sql`, then `sql/bronze/01_bmo_2026_checks.sql`
4. `sql/silver/01_bmo_2026.sql`, then `sql/silver/01_bmo_2026_checks.sql`
5. ROME: upload the raw zip and the staging folder (commands in the header of `sql/bronze/02_rome.sql`), then `sql/bronze/02_rome.sql` (29 tables) and `sql/bronze/02_rome_checks.sql`
6. `sql/silver/02_rome.sql` (24 tables) and `sql/silver/02_rome_checks.sql`
7. ONISEP: upload raw + staging folders (commands in the header of `sql/bronze/03_onisep.sql`), then `sql/bronze/03_onisep.sql` and `sql/bronze/03_onisep_checks.sql`
8. `sql/silver/03_onisep.sql` (8 tables; needs `silver.rome_metier`) and `sql/silver/03_onisep_checks.sql`
9. DARES: download the two files manually (site behind a captcha) into `data/raw/dares/fap2021/<YYYYMMDD>/`, run the connector, upload (commands in the header of `sql/bronze/04_dares.sql`), then `sql/bronze/04_dares.sql` and `sql/bronze/04_dares_checks.sql`
10. Formacode: run the connector, upload (commands in the header of `sql/bronze/05_formacode.sql`), then `sql/bronze/05_formacode.sql` and `sql/bronze/05_formacode_checks.sql` (needs `silver.rome_metier`)
11. `sql/silver/04_formacode.sql` (4 tables) and `sql/silver/04_formacode_checks.sql`
12. DARES FAP hierarchy + qualification readme: run both connectors, upload (commands in the header of `sql/bronze/06_dares_fap2021.sql`), then `sql/bronze/06_dares_fap2021.sql` and `sql/bronze/06_dares_fap2021_checks.sql`
13. `sql/silver/05_dares.sql` (3 tables) and `sql/silver/05_dares_checks.sql`
14. `sql/gold/01_gold.sql` (3 tables + 6 views) and `sql/gold/01_gold_checks.sql`
15. `sql/search/01_search.sql` (4 views) and `sql/search/01_search_checks.sql`

Every `check_*` column must be `true` before moving to the next step.
</details>

## Data Model

All objects live in the Unity Catalog catalog `career_intelligence`, volume
`bronze.landing` → `/Volumes/career_intelligence/bronze/landing/`.

| Schema | Objects | Content |
|---|---|---|
| `bronze` | 39 tables | `bmo_2026`; 29 `rome_*` (one per ROME CSV); 3 `onisep_*`; `rome_formacode_v14`, `formacode_v14_descripteurs`, `formacode_v14_grands_domaines`; `dares_rome_qualif_fap2021`, `dares_rome_qualif_fap2021_lisez_moi`, `dares_fap2021_nomenclature` |
| `silver` | 40 tables | `bmo_2026`; 24 `rome_*` (13 reference entities + 11 occupation links); 8 `onisep_*` (occupations, training sheets, catalogue + 5 relationships); `formacode`, `formacode_grand_domaine`, `formacode_terme_associe`, `rome_metier_formacode`; `fap2021`, `dares_qualification`, `dares_rome_v3_fap341` |
| `gold` | 3 tables + 6 views | see below |
| `search` | 4 views + 22 query contracts | see below |

### Gold

```
metier (ROME 4.0 v62, 1,923) ──< v_metier_appellation          job titles (14,330)
                             ──< v_metier_competence           skills and work contexts (124,910 links)
                             ──< v_metier_domaine_formation  >── Formacode V14 descriptors (5,958 links, many-to-many)
                             ──< v_metier_formation_onisep   >── ONISEP training programmes (13,033 rows, ODbL)
bmo_recrutement (FAP228 × area, 21,536 rows, minimums)   v_fap (FAP228 hierarchy)   [no link to metier]
v_rome_v3_fap (DARES ROME V3 × qualification → FAP341, 5,320)                       [never joined to v62]
source_licence (licence and attribution of every Gold object)
```

| Object | Type | Key | Notes |
|---|---|---|---|
| `metier` | table | `code_rome` | Occupation, domains, texts, RIASEC, transition indicators |
| `v_metier_appellation` | view | `code_ogr_appellation` | Job titles of each occupation |
| `v_metier_competence` | view | `code_rome, type_element, code_ogr_element` | Savoir-faire, savoir-être, savoirs, work contexts |
| `v_metier_domaine_formation` | view | `code_rome, code_formacode` | Every ROME ↔ Formacode link, no weights |
| `v_metier_formation_onisep` | view | `code_rome_source, identifiant_metier_onisep, type_lien, identifiant_formation` | ONISEP grain preserved; unresolved ROME codes kept with `code_rome = NULL` |
| `bmo_recrutement` | table | `code_fap228, niveau_geo, code_geo` | Department, region and national levels; `*_minimum` measures, hidden-cell counts, `est_complet_*` flags |
| `v_fap` | view | `code_fap228` | FAP 2021 hierarchy (DARES, licence unconfirmed) |
| `v_rome_v3_fap` | view | `code_rome_v3, code_qualification` | DARES correspondence; ROME **V3**, not v62 |
| `source_licence` | table | `objet_gold` | Licence, attribution and restrictions per Gold object |

### Search

| View | Key | Purpose |
|---|---|---|
| `v_metier_index` | `code_rome, champ, code_ogr_appellation` | Searchable texts of each occupation (code, name, job titles, definition, access text) |
| `v_element_competence` | `type_element, code_ogr_element` | Skill elements with their number of occupations |
| `v_domaine_formation` | `code_formacode` | The 1,220 Formacode descriptors linked to an occupation |
| `v_zone_geo` | `niveau_geo, code_geo` | BMO areas: national, 18 regions, 101 departments |

The 22 query contracts (`sql/search/queries/q01…q22_*.sql`) are registered in
`career_intelligence.search.contracts`, which records each one's parameters, output columns, key,
sources and licence; `bind()` validates the inputs. The application uses 15 of them; the others
(`rechercher_competences`, `metiers_par_competence`, `domaines_formation_metier`,
`formations_onisep_metier`, `rechercher_fap`, `rechercher_rome_v3`, `licences`) are available but
have no page.

| Search need | Contracts |
|---|---|
| Occupations by name, ROME code or keyword | `rechercher_metiers`, `fiche_metier`, `appellations_metier` |
| Descriptions and professional domains | `fiche_metier`, `lister_domaines` |
| Skills, knowledge, work contexts | `rechercher_competences`, `competences_metier`, `metiers_par_competence` |
| Formacode training domains | `domaines_formation_metier`, `rechercher_domaines_formation`, `metiers_par_domaine_formation`, `lister_grands_domaines_formation`, `parcourir_domaines_formation` |
| ONISEP programmes (ODbL — display "Source : Onisep") | `rechercher_formations_onisep`, `formations_onisep_metier`, `metiers_par_formation_onisep`, `couverture_onisep` |
| BMO recruitment by FAP and area (minimums) | `rechercher_fap`, `recrutement_bmo`, `lister_zones_geo`, `synthese_zones_bmo` |
| DARES ROME **V3** × qualification → FAP | `rechercher_rome_v3` |
| Licences and attributions | `licences` |

```python
from career_intelligence.search.contracts import bind

query = bind("rechercher_metiers", q="électricien", page=1, page_size=20)
cursor.execute(query.sql, parameters=query.parameters)  # databricks-sql-connector
```

Full layer documentation (decisions, row counts, rules): [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)
§6–§7.

## Technology Stack

| Area | Technologies |
|---|---|
| Language | Python 3.12 |
| Ingestion | `requests`, pandas, `openpyxl` and `xlrd` (Excel files), `pyarrow` (Parquet) |
| Data platform | Databricks Free Edition: Unity Catalog, Delta Lake, serverless SQL warehouse |
| Transformations | Databricks SQL (`sql/`) |
| Data access | `databricks-sql-connector` (optional extra `databricks`), Databricks CLI (OAuth login, file upload) |
| Application | Streamlit |
| Configuration | PyYAML, `python-dotenv` |
| Quality | pytest, Ruff |

Declared but **unused**: the optional extra `spark` in `pyproject.toml` (`pyspark`, `delta-spark`).
No PySpark code exists in the project.

## Repository Structure

```
career-intelligence/
├── app/                        # Streamlit application
│   ├── streamlit_app.py        # entry point and sidebar navigation
│   ├── common.py               # data access through SearchClient, shared components, styles
│   └── pages/                  # rechercher_metier, fiche_metier, explorer_formations,
│                               # explorer_marche_travail
├── .streamlit/config.toml      # application theme
├── config/
│   ├── settings.example.yaml   # non-secret settings template
│   └── sources.yaml            # verified data-source registry (URLs, checksums, licences)
├── data/                       # local raw and staging files (git-ignored, README only)
├── docs/
│   ├── PROJECT_SPECIFICATION.md
│   ├── DATA_SOURCES.md         # source verification log, Gold and Search documentation
│   └── images/                 # README screenshots
├── sql/                        # Databricks SQL: 00_setup, bronze, silver, gold, search
│   └── search/queries/         # q01…q22 parameterized query contracts
├── src/career_intelligence/    # Python package
│   ├── config.py               # settings and environment loading
│   ├── ingestion/              # six source connectors + HTTP helper
│   ├── search/                 # contracts registry, Databricks connection, SearchClient
│   └── utils/                  # logging
├── tests/                      # pytest suite (tests/live: opt-in Databricks tests)
├── .env.example                # environment-variable template
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

`notebooks/`, `scripts/` and `src/career_intelligence/transformation/` are **empty placeholders**
from the initial project structure: every transformation is a SQL script in `sql/`.

## Installation & Configuration

**Prerequisites:** Windows with PowerShell, Python 3.12, the
[Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install), and a Databricks
workspace (Free Edition) where the pipeline has been loaded (see
[Data Engineering Pipeline](#data-engineering-pipeline)).

```powershell
# 1. Create and activate the virtual environment (Python 3.12)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install the dependencies, the package and the Databricks SQL client
python -m pip install -r requirements-dev.txt
python -m pip install -e ".[databricks]"

# 3. Create the local configuration from the templates (both files are git-ignored)
Copy-Item .env.example .env
Copy-Item config\settings.example.yaml config\settings.yaml
```

> If script execution is blocked, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Databricks authentication** uses the Databricks CLI OAuth login; no token is stored in the
repository or in `.env`:

```powershell
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile career-intelligence
```

**`.env`** holds only non-secret workspace settings:

| Variable | Value |
|---|---|
| `DATABRICKS_CONFIG_PROFILE` | the CLI profile name (template: `career-intelligence`) |
| `DATABRICKS_SERVER_HOSTNAME` | workspace host without `https://` |
| `DATABRICKS_WAREHOUSE_ID` | SQL warehouse id (or `DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<id>`) |

`.env`, `config/settings.yaml`, `.databrickscfg` and `.streamlit/secrets.toml` are git-ignored.
**Never commit credentials.**

## Running the Application

From the project root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py --server.address localhost
```

The application opens at http://localhost:8501. It runs **locally only** and needs the configured
Databricks workspace with the loaded tables: every page queries the SQL warehouse through the
search contracts, using the developer's CLI login (the short-lived OAuth token is kept in memory
and never stored). Keep `--server.address localhost`: without it Streamlit also listens on the
network, and every query would run with your Databricks login. The first query after the
warehouse has been idle can take some time while it starts; results are then cached for an hour.

## Testing & Validation

```powershell
python -m pytest              # offline suite
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

| Check | Result (2026-11-10) | What it covers |
|---|---|---|
| Offline tests (pytest) | **622 passed, 2 skipped** | Connectors on local fixtures; static guards on the Gold and Search SQL; query-contract registry and parameter validation; `SearchClient` error handling and secret redaction; the four Streamlit pages run with a fake executor (search, filters, pagination, empty results, errors, attribution) |
| Skipped tests | 2 | The two opt-in live suites, skipped unless configured |
| Live Databricks tests | **55 passed** | Every contract against the SQL warehouse (columns, key uniqueness, licence columns), matching and pagination, relationship counts compared with Gold, BMO minimum semantics, authentication and read-only execution |
| SQL data-quality checks | **325 / 325 `check_*` true** | The 13 `*_checks.sql` files, from Bronze to Search |
| Ruff | `ruff check` clean; `ruff format --check`: 43 files formatted | Lint and formatting |
| `pip check` | No broken requirements | Installed dependency consistency |

To run the live suites, install the `databricks` extra and set the connection in the session:

```powershell
$env:CAREER_INTELLIGENCE_LIVE = "1"
$env:DATABRICKS_SERVER_HOSTNAME = "<your-workspace>.cloud.databricks.com"
$env:DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/<warehouse-id>"
$env:DATABRICKS_CONFIG_PROFILE = "career-intelligence"   # token from `databricks auth token`
python -m pytest tests/live
```

These results validate the implementation and the loaded data at that date. They do not cover
visual rendering in browsers or performance under load.

## Limitations, Scope & Licence

**Platform and deployment**

- The project runs on **Databricks Free Edition**, and the application runs **locally only**,
  with the developer's Databricks login.
- **There is no public deployment.** Free Edition is for personal, non-commercial use and its
  acceptable-use policy forbids giving third parties access.
- Free Edition compute quotas and the stopped-when-idle SQL warehouse can make queries slow or
  temporarily unavailable.

**Data**

- **BMO figures are minimums**: France Travail hides small values for statistical secrecy, so each
  figure is the sum of the published cells. Fully hidden values and family × area pairs absent
  from the survey are shown as such, never as zero, and no difficulty rate is calculated.
- **BMO is published by FAP228 occupational family and is never linked directly to ROME 4.0 v62
  occupations.**
- **ROME V3** (used by the DARES correspondence) is kept distinct from **ROME 4.0 v62** and never
  joined to it.
- **DARES data is not exposed** in the application, because its licence is unconfirmed.
- **ONISEP coverage is partial**: 392 of the 1,923 ROME occupations have at least one ONISEP
  training link.
- Formacode exploration covers the **1,220 descriptors linked to at least one occupation** (out of
  2,775 in the thesaurus).
- There are no machine-learning models, recommendations or job advertisements.

The scope decisions behind these limits are documented in
[docs/PROJECT_SPECIFICATION.md](docs/PROJECT_SPECIFICATION.md) §6.

**Licence**

The code is **Proprietary — All Rights Reserved** (academic portfolio project). No licence is
granted to copy, modify or redistribute it. Each data source remains subject to its own licence
and terms of use; the attribution obligations are listed under
[Attribution obligations](#attribution-obligations) and must be preserved.
