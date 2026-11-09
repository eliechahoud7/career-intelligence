# Project Specification — Career Intelligence

**Multi-Source Data Integration & Search Platform**

| Item | Value |
|------|-------|
| Version | 0.1 (initial draft) |
| Date | 2026-11-09 |
| Author | Elie Chahoud |
| Status | Draft — repository initialised, data sources not yet verified |

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

Users should be able to:

1. **Search occupations** by keyword and browse their descriptions.
2. **Explore skills** associated with an occupation (and, conversely, occupations requiring a skill).
3. **Discover training programmes** leading to an occupation or developing a skill.
4. **Consult employment information** (e.g. demand, job-offer volumes or statistics) for an occupation, where available.

### 2.2 Technical / academic objectives

1. Build a reproducible **ingestion pipeline** from several external REST APIs / open datasets.
2. Apply a **medallion architecture** (Bronze → Silver → Gold) with **PySpark** and **Delta Lake** on **Databricks Free Edition**.
3. Perform **data integration**: harmonise identifiers, map entities across sources, handle multilingual labels and duplicates.
4. Expose integrated data through **SQL** tables/views and a **Streamlit** application.
5. Apply software-engineering good practice: modular code, configuration without hard-coded secrets, tests, version control.

## 3. Scope

### In scope
- 3 to 5 external data sources covering occupations, skills, training and employment (final selection after verification — see [DATA_SOURCES.md](DATA_SOURCES.md)).
- Batch ingestion (manual or scheduled runs); no real-time streaming.
- Keyword search with filters, implemented with SQL / Spark (no external search engine).
- A Streamlit front-end for search and exploration.
- Basic data-quality checks (schema, nulls, duplicates, referential integrity between Gold tables).

### Out of scope (for this project)
- User accounts, authentication, personalised recommendations.
- Machine-learning models, semantic/vector search, LLM features (possible future extensions).
- Production-grade hosting, high availability, CI/CD deployment pipelines.
- Scraping websites whose terms of use do not allow it.

## 4. Constraints and principles

- **No assumed data access:** each source is verified (documentation, licence, authentication, test call) before a connector is written.
- **No secrets in the repository:** credentials via `.env` locally (git-ignored) and Databricks secret scopes in the workspace.
- **Platform limits:** Databricks Free Edition (serverless compute, quotas, Unity Catalog). Its outbound network access and quotas must be checked early, as they determine whether ingestion runs inside Databricks or locally with upload of raw files.
- **Proportionate complexity:** Master's-level project; prefer simple, well-documented solutions over additional tools.

## 5. Architecture

### 5.1 Overview

```
 External sources                 Databricks Free Edition (Unity Catalog)                    Presentation
 ────────────────                 ─────────────────────────────────────────                  ────────────
 ┌──────────────┐  REST / files   ┌──────────┐   PySpark   ┌──────────┐   PySpark   ┌──────────┐   SQL    ┌────────────┐
 │ Occupations  │ ──────────────► │  BRONZE  │ ──────────► │  SILVER  │ ──────────► │   GOLD   │ ───────► │ Streamlit  │
 │ Skills       │   connectors    │ raw JSON │  clean,     │ typed,   │  integrate, │ search-  │          │ search UI  │
 │ Training     │   (Python)      │ + ingest │  type,      │ deduped, │  map IDs,   │ ready    │          └────────────┘
 │ Employment   │                 │ metadata │  dedupe     │ per src  │  aggregate  │ model    │
 └──────────────┘                 └──────────┘             └──────────┘             └──────────┘
                                         Delta Lake tables throughout
```

### 5.2 Layers

| Layer | Content | Rules |
|-------|---------|-------|
| **Bronze** | Raw payloads per source, stored as received + ingestion metadata (`_source`, `_ingested_at`, `_request`, `_run_id`). | Append-only; never altered; allows replay. |
| **Silver** | One cleaned table per source entity (e.g. `silver.esco_occupation`). | Explicit schema, types, normalised text, deduplication, language handling. |
| **Gold** | Integrated, source-agnostic model used by the app. | Unified identifiers, cross-source mappings, search-friendly columns. |

### 5.3 Target Gold data model (provisional — refined after source verification)

```
occupation ──< occupation_skill >── skill
     │                                 │
     ├──< occupation_training >── training_program ──< training_skill >──┘
     │
     └──< employment_indicator
occupation_source_mapping  (links source-specific codes to the unified occupation id)
```

### 5.4 Components (repository mapping)

| Component | Location | Technology |
|-----------|----------|------------|
| Configuration loading | `src/career_intelligence/config.py`, `config/` | Python, YAML, dotenv |
| Source connectors | `src/career_intelligence/ingestion/` | Python, `requests` |
| Transformations | `src/career_intelligence/transformation/` | PySpark |
| Pipeline notebooks | `notebooks/00_setup … 03_gold` | Databricks notebooks |
| SQL DDL / views | `sql/` | Databricks SQL |
| Search layer | `src/career_intelligence/search/` | SQL / Python |
| Web application | `app/` | Streamlit |
| Tests | `tests/` | pytest |

### 5.5 Security

- Secrets only in environment variables / Databricks secret scopes; templates (`.env.example`, `config/settings.example.yaml`) contain placeholders only.
- `.gitignore` excludes `.venv`, `.env*`, `.databrickscfg`, Streamlit secrets, key files and all data files.

## 6. Delivery plan (incremental)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | Repository initialisation, specification | **Done** |
| 1 | Data-source verification and selection (France, French) | **Done** — see DATA_SOURCES.md |
| 2 | Databricks workspace setup (catalog, schemas, volume, secrets) | **In progress** — catalog, `bronze` schema, `landing` volume |
| 3 | Bronze connectors (one source at a time) | **In progress** — BMO 2026 → `bronze.bmo_2026`; ROME 4.0 v62 → 29 `bronze.rome_*` tables; ONISEP → 3 `bronze.onisep_*` tables |
| 4 | Silver transformations + data-quality checks | **In progress** — `silver.bmo_2026`, 24 `silver.rome_*` tables |
| 5 | Gold integrated model + SQL views | Planned |
| 6 | Search layer + Streamlit application | Planned |
| 7 | Documentation, evaluation, final report | Planned |

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Source requires approval/registration or changes terms | Delays, loss of a domain | Verify early; keep alternative candidates per domain. |
| Free Edition network or quota limits | Ingestion cannot run in Databricks | Run connectors locally and upload raw files to a UC volume. |
| Weak cross-source identifiers | Poor integration quality | Use standard classifications (e.g. ISCO) as pivot; document mapping quality. |
| Multilingual labels | Inconsistent search | Fix a primary language; keep alternatives as secondary columns. |
| Scope creep | Unfinished project | Strict phase plan; extensions listed as future work. |

## 8. Success criteria

- At least 3 verified sources ingested end-to-end into Gold Delta tables.
- Cross-source occupation mapping documented with measured coverage.
- Streamlit app answers the four functional use cases (§2.1).
- Pipeline re-runnable from Bronze; tests pass; no secrets in Git history.
