# Data Source Verification Log

No connector is implemented until its source has a **verified** entry here.
The machine-readable registry is [`config/sources.yaml`](../config/sources.yaml).

## Verification checklist (per source)

1. **Official documentation** located (URL recorded, retrieval date).
2. **Access model** confirmed: open / free registration / paid / bulk download only.
3. **Authentication** method confirmed (none, API key, OAuth2 client credentials…).
4. **Licence / terms of use** reviewed — reuse and storage allowed for an academic project?
5. **Rate limits / quotas** noted.
6. **Test request** executed successfully; sample response stored in `data/sample/` (git-ignored).
7. **Schema** of the relevant entities documented (fields, identifiers, languages).
8. **Join keys** to other sources identified (e.g. occupation codes, ISCO mapping).
9. **Reachability from Databricks Free Edition** confirmed (outbound network from serverless compute).

## Status

| ID | Source | Domain(s) | Status | Verified on | Notes |
|----|--------|-----------|--------|-------------|-------|
| `esco` | ESCO (European Commission) | occupations, skills | candidate | — | — |
| `rome_france_travail` | ROME (France Travail) | occupations, skills | candidate | — | — |
| `onet` | O*NET (US DoL) | occupations, skills | candidate | — | — |
| `training_programs` | *to be selected* | training | candidate | — | — |
| `labour_market` | *to be selected* | employment | candidate | — | — |

## Source entries

<!-- Copy this template for each source once verification starts.

### <source id>
- **Documentation:** <url> (retrieved YYYY-MM-DD)
- **Access / auth:**
- **Licence:**
- **Rate limits:**
- **Endpoints / files used:**
- **Test result:**
- **Key entities & identifiers:**
- **Decision:** verified | rejected — <reason>
-->
