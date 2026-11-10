# Project Specification — Career Intelligence

**Multi-Source Data Integration & Search Platform**

| Item | Value |
|------|-------|
| Version | 1.0 (as delivered) |
| Date | 2026-11-10 (initial draft 0.1: 2026-11-09) |
| Author | Elie Chahoud |
| Status | Delivered — six sources loaded Bronze → Gold, SQL search layer, four-page Streamlit application, validated (see §6) |

---

## 1. Context

Choosing a profession or a training path requires information that is scattered
across many public sources: occupation repositories, skills taxonomies, training
catalogues and labour-market statistics. Each uses its own identifiers, formats
and access conditions.

Inspired by professional orientation platforms such as JobRetex, **Career
Intelligence** integrates several of these sources into a single, consistent data
model and exposes them through a simple search interface.

## 2. Objectives

### 2.1 Functional objectives

Users should be able to (original objectives, with their delivered status):

| # | Objective | Delivered |
|---|---|---|
| 1 | **Search occupations** by keyword and browse their descriptions. | **Yes** — « Rechercher un métier » and « Fiche métier » (ROME 4.0 v62). |
| 2 | **Explore skills** associated with an occupation (and, conversely, occupations requiring a skill). | **Partly** — skills of an occupation on « Fiche métier ». The reverse direction exists as query contracts (`rechercher_competences`, `metiers_par_competence`) but has no page. |
| 3 | **Discover training programmes** leading to an occupation or developing a skill. | **Partly** — « Explorer les formations »: Formacode training domains and ONISEP programmes with their occupations (ONISEP covers 392 of 1,923 occupations). No source links training to individual skills. |
| 4 | **Consult employment information** for an occupation, where available. | **By family, not by occupation** — « Explorer le marché du travail »: BMO 2026 recruitment intentions by FAP228 family and area. BMO is not linked to ROME occupations (see §6.2). |

### 2.2 Technical / academic objectives

1. Build a reproducible **ingestion pipeline** from several official open datasets (delivered with bulk files; no REST API was used).
2. Apply a **medallion architecture** (Bronze → Silver → Gold) with **Delta Lake** on **Databricks Free Edition** (delivered with **Databricks SQL** scripts; the initial draft named PySpark).
3. Perform **data integration**: harmonise identifiers, map entities across sources, handle multilingual labels and duplicates.
4. Expose integrated data through **SQL** tables/views and a **Streamlit** application.
5. Apply software-engineering good practice: modular code, configuration without hard-coded secrets, tests, version control.

## 3. Scope

### In scope
- 3 to 5 external data sources covering occupations, skills, training and employment (final selection after verification — see [DATA_SOURCES.md](DATA_SOURCES.md)).
- Batch ingestion (manual or scheduled runs); no real-time streaming.
- Keyword search with filters, implemented in SQL (no external search engine).
- A Streamlit front-end for search and exploration.
- Basic data-quality checks (schema, nulls, duplicates, referential integrity between Gold tables).

### Out of scope (for this project)
- User accounts, authentication, personalised recommendations.
- Machine-learning models, semantic/vector search, LLM features (possible future extensions).
- Production-grade hosting, high availability, CI/CD deployment pipelines.
- Scraping websites whose terms of use do not allow it.

## 4. Constraints and principles

- **No assumed data access:** each source is verified (documentation, licence, authentication, test call) before a connector is written.
- **No secrets in the repository:** workspace settings in `.env` locally (git-ignored); authentication through the Databricks CLI OAuth login, so no token is stored.
- **Platform limits:** Databricks Free Edition (serverless compute, quotas, Unity Catalog). Its outbound network access and quotas must be checked early, as they determine whether ingestion runs inside Databricks or locally with upload of raw files.
- **Proportionate complexity:** Master's-level project; prefer simple, well-documented solutions over additional tools.

## 5. Architecture

### 5.1 Overview (as delivered)

```
 Official open data          Local Python               Databricks Free Edition (Unity Catalog, Delta Lake)            Local app
 ──────────────────          ────────────               ───────────────────────────────────────────────────            ─────────
 ROME 4.0 v62, BMO 2026, ──► connectors: download, ──► BRONZE ─SQL─► SILVER ─SQL─► GOLD ─SQL─► SEARCH ──────────► SearchClient ──► Streamlit
 ROME↔Formacode,             validate, stage as        raw text      typed,        integrated  4 views +            read-only,       4 pages
 Formacode V14, ONISEP,      Parquet + manifest        + lineage     cleaned       model       22 query contracts   validated        (French)
 DARES FAP 2021              (upload to UC volume)                                                                  parameters
```

Ingestion runs locally (Free Edition outbound access is restricted); every transformation is a
Databricks SQL script in `sql/` with a companion check file whose `check_*` columns must be `true`.

### 5.2 Layers

| Layer | Content | Rules |
|-------|---------|-------|
| **Bronze** | One table per source file, every value as text, plus lineage columns (`_source_*`, `_run_id`, `_ingested_at`, checksum). | Faithful to the source; rebuilt from the pinned files. |
| **Silver** | One cleaned table per source entity (e.g. `silver.rome_metier`, `silver.bmo_2026`, `silver.formacode`). | Explicit types, normalised whitespace, statistical secrecy as `NULL` + flag, source codes kept verbatim. |
| **Gold** | Integrated model: 3 tables + 6 views (see §5.3). | Built from Silver only; no weights or invented links; licence of every object in `gold.source_licence`. |
| **Search** | 4 views over Gold and 22 parameterized query contracts (`sql/search/queries/`). | Read-only; case- and accent-insensitive matching; ranking by match tier only. |

### 5.3 Gold data model (as delivered)

```
metier (ROME 4.0 v62, 1,923) ──< v_metier_appellation
                             ──< v_metier_competence         (savoir-faire, savoir-être, savoirs, work contexts)
                             ──< v_metier_domaine_formation  >── Formacode V14 descriptors (many-to-many)
                             ──< v_metier_formation_onisep   >── ONISEP training programmes (ODbL)
bmo_recrutement (FAP228 × area, minimums)   v_fap (FAP 2021 hierarchy)       [no link to metier]
v_rome_v3_fap (DARES ROME V3 × qualification → FAP341)                       [ROME V3, never joined to v62]
source_licence (licence and attribution of every Gold object)
```

The provisional model of the initial draft (unified occupation id, `training_skill`,
`employment_indicator` per occupation) was not built: the sources share the ROME code for
occupations, provide no training ↔ skill link, and publish employment data by FAP family.

### 5.4 Components (repository mapping)

| Component | Location | Technology |
|-----------|----------|------------|
| Configuration loading | `src/career_intelligence/config.py`, `config/` | Python, YAML, dotenv |
| Source connectors | `src/career_intelligence/ingestion/` | Python, `requests`, pandas, Parquet |
| Bronze / Silver / Gold / Search | `sql/` (with `*_checks.sql`) | Databricks SQL, Delta Lake |
| Query contracts and client | `src/career_intelligence/search/`, `sql/search/queries/` | Python, databricks-sql-connector |
| Web application | `app/` | Streamlit |
| Tests | `tests/` (`tests/live`: opt-in, against Databricks) | pytest |

`notebooks/`, `scripts/` and `src/career_intelligence/transformation/` are unused placeholders
from the initial structure.

### 5.5 Security

- Secrets only in environment variables; templates (`.env.example`, `config/settings.example.yaml`) contain placeholders only.
- The application authenticates with the developer's Databricks CLI login (short-lived OAuth token kept in memory, never stored or logged) and runs on `localhost` only.
- The client executes only registered contract files, unchanged, after a read-only check.
- `.gitignore` excludes `.venv`, `.env*`, `.databrickscfg`, Streamlit secrets, key files and all data files.

## 6. Delivery plan (incremental)

### 6.1 Phases

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | Repository initialisation, specification | **Done** |
| 1 | Data-source verification and selection (France, French) | **Done** — see DATA_SOURCES.md |
| 2 | Databricks workspace setup (catalog, schemas, volume) | **Done** — catalog `career_intelligence`, schemas `bronze`, `silver`, `gold`, `search`, volume `bronze.landing` |
| 3 | Bronze connectors (one source at a time) | **Done** — BMO 2026; ROME 4.0 v62 (29 tables); ONISEP (3); DARES ROME × qualification → FAP 2021; ROME ↔ Formacode V14 + thesaurus (3); DARES FAP 2021 nomenclature + qualification readme (2) |
| 4 | Silver transformations + data-quality checks | **Done** — `silver.bmo_2026`, 24 `silver.rome_*`, 8 `silver.onisep_*`, 4 Formacode and 3 DARES tables |
| 5 | Gold integrated model + SQL views | **Done** — 3 tables (`metier`, `bmo_recrutement`, `source_licence`) + 6 views; see DATA_SOURCES.md §6 |
| 6 | Search layer + Streamlit application | **Done** — 4 Search views + 22 query contracts; four pages: « Rechercher un métier », « Fiche métier », « Explorer les formations », « Explorer le marché du travail » |
| 7 | Documentation, evaluation, final report | **Done** — final integration and validation (2026-11-10): 622 offline and 55 live tests pass, 325/325 `check_*` true |

### 6.2 Scope decisions and features not implemented

| Decision | Reason |
|---|---|
| Transformations in Databricks SQL instead of PySpark | Simpler and sufficient for batch, tabular open data; every script has a SQL check file. |
| Bulk files instead of REST APIs | The francetravail.io APIs need registration and the job-offer API is restricted; all selected datasets are published as files. |
| No BMO figures per ROME occupation | BMO is published by FAP family; the only ROME → FAP route (DARES) uses ROME **V3** and depends on the qualification, which BMO does not record. |
| BMO values shown as minimums, no difficulty rate | Statistical secrecy hides cells; a ratio of two minimums is not reliable. |
| DARES data loaded but not shown (no qualification page, no FAP22/FAP86 grouping) | The DARES licence is unconfirmed (no statement from the publisher). |
| Formacode limited to the 1,220 descriptors linked to an occupation | Only these are exposed by Gold; the other descriptors stay in Silver. |
| No page for occupations by skill; no training ↔ skill link | Query contracts exist for the first; no source provides the second. |
| No public deployment | Databricks Free Edition is for personal, non-commercial use and its acceptable-use policy forbids giving third parties access; the application runs locally. |

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Source requires approval/registration or changes terms | Delays, loss of a domain | Verify early; keep alternative candidates per domain. |
| Free Edition network or quota limits | Ingestion cannot run in Databricks | Run connectors locally and upload raw files to a UC volume. |
| Weak cross-source identifiers | Poor integration quality | Use standard classifications (e.g. ISCO) as pivot; document mapping quality. |
| Multilingual labels | Inconsistent search | Fix a primary language; keep alternatives as secondary columns. |
| Scope creep | Unfinished project | Strict phase plan; extensions listed as future work. |

## 8. Success criteria

| Criterion | Outcome |
|---|---|
| At least 3 verified sources ingested end-to-end into Gold Delta tables. | **Met** — six datasets. |
| Cross-source occupation mapping documented with measured coverage. | **Met** — DATA_SOURCES.md §4–§7 (e.g. Formacode 1,923/1,923 occupations, ONISEP 392/1,923). |
| Streamlit app answers the four functional use cases (§2.1). | **Partly met** — objective 1 fully, 2–4 within the limits of the sources (§2.1, §6.2). |
| Pipeline re-runnable from Bronze; tests pass; no secrets in Git history. | **Met** — SQL scripts with checks; all tests pass; no credential in the history. |
