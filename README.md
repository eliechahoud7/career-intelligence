# Career Intelligence

**Multi-Source Data Integration & Search Platform** for professional orientation.

Career Intelligence integrates several external data sources — occupations, skills,
training programmes and labour-market information — into a unified Delta Lake model
on Databricks, and exposes it through a Streamlit search application.

> **Status:** Phase 0 — repository initialised. Data sources are being verified;
> no connector or application feature is implemented yet.

## Features (planned)

- 🔎 Search occupations and read their descriptions
- 🧩 Explore the skills associated with each occupation
- 🎓 Discover training programmes linked to occupations and skills
- 📈 Consult employment / labour-market indicators

## Architecture

```
External APIs ─► Bronze (raw) ─► Silver (clean) ─► Gold (integrated) ─► Streamlit
                 └──────────── Delta Lake on Databricks Free Edition ────────────┘
```

See the full [project specification](docs/PROJECT_SPECIFICATION.md).

## Tech stack

Python 3.12 · PySpark · Delta Lake · Databricks Free Edition · SQL · REST APIs · Streamlit · pytest · Ruff

## Repository layout

```
career-intelligence/
├── app/                      # Streamlit application
├── config/
│   ├── settings.example.yaml # non-secret settings template
│   └── sources.yaml          # candidate data-source registry (unverified)
├── data/                     # local working data (git-ignored)
├── docs/
│   ├── PROJECT_SPECIFICATION.md
│   └── DATA_SOURCES.md       # source verification log
├── notebooks/                # Databricks notebooks: 00_setup, 01_bronze, 02_silver, 03_gold
├── scripts/                  # helper scripts (PowerShell / Python)
├── sql/                      # Databricks SQL DDL and views
├── src/career_intelligence/  # Python package
│   ├── config.py             # settings & secrets loading
│   ├── ingestion/            # source connectors (Bronze)
│   ├── transformation/       # PySpark transformations (Silver/Gold)
│   ├── search/               # query layer for the app
│   └── utils/                # logging and helpers
├── tests/                    # pytest suite
├── .env.example              # environment-variable template
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Getting started (Windows / PowerShell)

```powershell
# 1. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies (runtime + dev tools) and the package in editable mode
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps

# 3. Create local configuration from the templates (both files are git-ignored)
Copy-Item .env.example .env
Copy-Item config\settings.example.yaml config\settings.yaml

# 4. Run checks
python -m pytest
python -m ruff check .
```

> If script execution is blocked, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

PySpark is provided by the Databricks runtime. For local Spark execution (requires Java 17)
install the optional extra: `python -m pip install -e ".[spark]"`.

## Configuration & secrets

- Non-secret settings: `config/settings.yaml` (copied from the example).
- Secrets: environment variables in `.env` locally, **Databricks secret scopes** in the workspace.
- `.env`, `config/settings.yaml`, `.databrickscfg` and `.streamlit/secrets.toml` are git-ignored.
  **Never commit credentials.**

## Data sources

No source is assumed accessible. Each candidate is verified (documentation, licence,
authentication, test request, reachability from Databricks) before a connector is written.
Progress is tracked in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

## Roadmap

0. ✅ Repository initialisation
1. ⏳ Data-source verification
2. Databricks workspace setup
3. Bronze connectors
4. Silver transformations & quality checks
5. Gold integrated model & SQL views
6. Search layer & Streamlit app
7. Documentation & evaluation

## License

Academic project — all rights reserved unless stated otherwise. Each external data source
remains subject to its own licence and terms of use.
