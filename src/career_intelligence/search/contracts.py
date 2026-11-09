"""Search query contracts (Phase 14): the interface between the SQL search layer and the app.

Each contract names one parameterized SQL file in ``sql/search/queries``, its parameters
(type, required, default, allowed values), its output columns, the key that makes a result row
unique, the Gold / Search objects it reads, and the ``gold.source_licence`` entry whose licence
and attribution it returns.

``bind()`` validates the caller's values and returns the SQL text with named parameters
(``:name``) ready for the Databricks Statement Execution API or ``databricks-sql-connector``.
No database connection is made here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from typing import Any

from career_intelligence.config import PROJECT_ROOT

QUERIES_DIR = PROJECT_ROOT / "sql" / "search" / "queries"

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100
QUERY_MIN_LENGTH = 2
QUERY_MAX_LENGTH = 100

STRING, INT, BOOLEAN = "STRING", "INT", "BOOLEAN"

TYPES_ELEMENT = ("savoir_faire", "savoir_etre", "savoir", "contexte_travail")
NIVEAUX_GEO = ("national", "region", "departement")
TYPES_LIEN = ("formation_menant_au_metier", "formation_minimale_requise")
OUI_NON = ("O", "N")
QUALIFICATIONS = tuple(str(i) for i in range(10))
OBJETS_GOLD = (
    "metier",
    "v_metier_appellation",
    "v_metier_competence",
    "v_metier_domaine_formation",
    "v_metier_formation_onisep",
    "v_fap",
    "bmo_recrutement",
    "v_rome_v3_fap",
    "source_licence",
)

LICENCE_COLUMNS = ("licence", "attribution")
PAGINATION_PARAMS = ("page_size", "offset")


@dataclass(frozen=True)
class Param:
    name: str
    type: str = STRING
    required: bool = False
    default: Any = None
    choices: tuple[str, ...] | None = None
    multi: bool = False  # comma-separated list of ``choices``
    keyword: bool = False  # free-text query: normalised and length-checked


@dataclass(frozen=True)
class Contract:
    name: str
    file: str
    description: str
    params: tuple[Param, ...]
    columns: tuple[str, ...]
    key: tuple[str, ...]
    reads: tuple[str, ...]
    licence_object: str
    paginated: bool = True
    one_of: tuple[str, ...] = ()  # at least one of these parameters is required

    @property
    def param_names(self) -> tuple[str, ...]:
        names = tuple(p.name for p in self.params)
        return names + PAGINATION_PARAMS if self.paginated else names


@dataclass(frozen=True)
class BoundQuery:
    contract: Contract
    sql: str
    parameters: dict[str, Any]

    def statement_parameters(self) -> list[dict[str, str]]:
        """Parameters in the Statement Execution API format (a missing value means NULL)."""
        types = {p.name: p.type for p in self.contract.params}
        types.update(dict.fromkeys(PAGINATION_PARAMS, INT))
        out = []
        for name, value in self.parameters.items():
            item = {"name": name, "type": types[name]}
            if value is not None:
                item["value"] = str(value).lower() if isinstance(value, bool) else str(value)
            out.append(item)
        return out


def _q(required: bool = True) -> Param:
    return Param("q", required=required, keyword=True)


def _code_rome() -> Param:
    return Param("code_rome", required=True)


_TOTAL = ("total_resultats",)

CONTRACTS: dict[str, Contract] = {
    c.name: c
    for c in (
        Contract(
            "rechercher_metiers",
            "q01_rechercher_metiers.sql",
            "Search ROME 4.0 v62 occupations by code, name, job title or texts.",
            (
                _q(),
                Param("code_grand_domaine"),
                Param("code_domaine_professionnel"),
                Param("emploi_cadre", choices=OUI_NON),
                Param("emploi_reglemente", choices=OUI_NON),
                Param("inclure_textes", BOOLEAN, default=False),
            ),
            (
                "code_rome",
                "libelle_rome",
                "code_grand_domaine",
                "libelle_grand_domaine",
                "code_domaine_professionnel",
                "libelle_domaine_professionnel",
                "emploi_cadre",
                "emploi_reglemente",
                "champ_correspondant",
                "libelle_correspondant",
                "rang_pertinence",
                "nb_appellations",
                "_rome_version",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_rome",),
            ("search.v_metier_index", "gold.metier", "gold.source_licence"),
            "metier",
        ),
        Contract(
            "fiche_metier",
            "q02_fiche_metier.sql",
            "Profile of one ROME 4.0 v62 occupation (texts with corrected apostrophes).",
            (_code_rome(),),
            (
                "code_rome",
                "code_ogr",
                "libelle_rome",
                "code_grand_domaine",
                "libelle_grand_domaine",
                "code_domaine_professionnel",
                "libelle_domaine_professionnel",
                "riasec_majeur",
                "riasec_mineur",
                "transition_eco",
                "transition_num",
                "transition_demo",
                "emploi_reglemente",
                "emploi_cadre",
                "definition",
                "acces_metier",
                "nb_phrases_definition",
                "nb_phrases_acces_metier",
                "nb_appellations",
                "nb_savoir_faire",
                "nb_savoir_etre",
                "nb_savoirs",
                "nb_contextes_travail",
                "nb_domaines_formation",
                "_rome_version",
                "_source_archive_sha256",
                *LICENCE_COLUMNS,
            ),
            ("code_rome",),
            ("gold.metier", "search.v_metier_index", "gold.source_licence"),
            "metier",
            paginated=False,
        ),
        Contract(
            "appellations_metier",
            "q03_appellations_metier.sql",
            "Job titles of one ROME 4.0 v62 occupation.",
            (_code_rome(), Param("inclure_peu_usitees", BOOLEAN, default=True)),
            (
                "code_rome",
                "code_ogr_appellation",
                "libelle_appellation_long",
                "libelle_appellation_court",
                "classification",
                "peu_usite",
                "_rome_version",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_ogr_appellation",),
            ("gold.v_metier_appellation", "gold.source_licence"),
            "v_metier_appellation",
        ),
        Contract(
            "lister_domaines",
            "q04_lister_domaines.sql",
            "ROME 4.0 v62 professional domains with their number of occupations.",
            (Param("code_grand_domaine"),),
            (
                "code_grand_domaine",
                "libelle_grand_domaine",
                "code_domaine_professionnel",
                "libelle_domaine_professionnel",
                "nb_metiers",
                "_rome_version",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_domaine_professionnel",),
            ("gold.metier", "gold.source_licence"),
            "metier",
        ),
        Contract(
            "rechercher_competences",
            "q05_rechercher_competences.sql",
            "Search ROME skill elements by OGR code or label.",
            (
                _q(),
                Param("types", choices=TYPES_ELEMENT, multi=True),
                Param("categorie"),
            ),
            (
                "type_element",
                "code_ogr_element",
                "libelle_element",
                "categorie",
                "sous_categorie",
                "code_ogr_macro_competence",
                "libelle_macro_competence",
                "nb_metiers",
                "rang_pertinence",
                "_rome_version",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("type_element", "code_ogr_element"),
            ("search.v_element_competence", "gold.source_licence"),
            "v_metier_competence",
        ),
        Contract(
            "competences_metier",
            "q06_competences_metier.sql",
            "Skill elements of one ROME 4.0 v62 occupation.",
            (
                _code_rome(),
                Param("types", choices=TYPES_ELEMENT, multi=True),
                Param("coeur_metier_seulement", BOOLEAN, default=False),
            ),
            (
                "code_rome",
                "type_element",
                "code_ogr_element",
                "libelle_element",
                "niveau_competence",
                "coeur_metier",
                "categorie",
                "sous_categorie",
                "code_ogr_macro_competence",
                "libelle_macro_competence",
                "_rome_version",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("type_element", "code_ogr_element"),
            ("gold.v_metier_competence", "gold.source_licence"),
            "v_metier_competence",
        ),
        Contract(
            "metiers_par_competence",
            "q07_metiers_par_competence.sql",
            "ROME 4.0 v62 occupations linked to one skill element.",
            (
                Param("type_element", required=True, choices=TYPES_ELEMENT),
                Param("code_ogr_element", required=True),
                Param("coeur_metier_seulement", BOOLEAN, default=False),
            ),
            (
                "type_element",
                "code_ogr_element",
                "libelle_element",
                "code_rome",
                "libelle_rome",
                "code_grand_domaine",
                "libelle_grand_domaine",
                "niveau_competence",
                "coeur_metier",
                "_rome_version",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_rome",),
            ("gold.v_metier_competence", "gold.metier", "gold.source_licence"),
            "v_metier_competence",
        ),
        Contract(
            "domaines_formation_metier",
            "q08_domaines_formation_metier.sql",
            "Formacode V14 training domains linked to one ROME 4.0 v62 occupation (all links).",
            (_code_rome(),),
            (
                "code_rome",
                "code_formacode",
                "libelle_formacode",
                "code_champ_semantique",
                "libelle_champ_semantique",
                "code_grand_domaine_formacode",
                "libelle_grand_domaine_formacode",
                "niveau",
                "est_terme_feuille",
                "code_formacode_parent",
                "_version",
                "_source_sha256",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_formacode",),
            ("gold.v_metier_domaine_formation", "gold.source_licence"),
            "v_metier_domaine_formation",
        ),
        Contract(
            "rechercher_domaines_formation",
            "q09_rechercher_domaines_formation.sql",
            "Search Formacode V14 training domains linked to ROME occupations.",
            (_q(), Param("code_grand_domaine_formacode")),
            (
                "code_formacode",
                "libelle_formacode",
                "code_champ_semantique",
                "libelle_champ_semantique",
                "code_grand_domaine_formacode",
                "libelle_grand_domaine_formacode",
                "niveau",
                "est_terme_feuille",
                "code_formacode_parent",
                "nb_metiers",
                "rang_pertinence",
                "_version",
                "_source_sha256",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_formacode",),
            ("search.v_domaine_formation", "gold.source_licence"),
            "v_metier_domaine_formation",
        ),
        Contract(
            "metiers_par_domaine_formation",
            "q10_metiers_par_domaine_formation.sql",
            "ROME 4.0 v62 occupations linked to one Formacode V14 domain.",
            (Param("code_formacode", required=True),),
            (
                "code_formacode",
                "libelle_formacode",
                "code_rome",
                "libelle_rome",
                "code_grand_domaine",
                "libelle_grand_domaine",
                "_rome_version",
                "_version",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_rome",),
            ("gold.v_metier_domaine_formation", "gold.metier", "gold.source_licence"),
            "v_metier_domaine_formation",
        ),
        Contract(
            "rechercher_formations_onisep",
            "q11_rechercher_formations_onisep.sql",
            "Search ONISEP training programmes (ODbL, display 'Source : Onisep').",
            (
                _q(),
                Param("type_formation"),
                Param("niveau_certification"),
                Param("dans_catalogue", BOOLEAN),
            ),
            (
                "identifiant_formation",
                "libelle_formation",
                "libelle_type_formation",
                "niveau_de_sortie_indicatif",
                "libelle_niveau_de_certification",
                "duree",
                "code_rncp",
                "url_onisep",
                "formation_dans_catalogue",
                "nb_metiers_onisep",
                "nb_codes_rome",
                "nb_codes_rome_non_resolus",
                "rang_pertinence",
                "_snapshot",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("identifiant_formation",),
            ("gold.v_metier_formation_onisep", "gold.source_licence"),
            "v_metier_formation_onisep",
        ),
        Contract(
            "formations_onisep_metier",
            "q12_formations_onisep_metier.sql",
            "ONISEP training programmes linked to one ROME 4.0 v62 occupation (ODbL, D7 grain).",
            (_code_rome(), Param("type_lien", choices=TYPES_LIEN)),
            (
                "code_rome",
                "code_rome_source",
                "statut_code_rome",
                "identifiant_metier_onisep",
                "nom_metier_onisep",
                "type_lien",
                "identifiant_formation",
                "libelle_formation",
                "libelle_formation_source",
                "formation_dans_catalogue",
                "libelle_type_formation",
                "niveau_de_sortie_indicatif",
                "libelle_niveau_de_certification",
                "duree",
                "code_rncp",
                "url_onisep",
                "_snapshot",
                "_source_sha256_lien_rome",
                "_source_sha256_lien_formation",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_rome_source", "identifiant_metier_onisep", "type_lien", "identifiant_formation"),
            ("gold.v_metier_formation_onisep", "gold.source_licence"),
            "v_metier_formation_onisep",
        ),
        Contract(
            "rechercher_fap",
            "q13_rechercher_fap.sql",
            "Browse or search FAP 2021 families (FAP228) and their hierarchy.",
            (_q(required=False), Param("code_fap22"), Param("bmo_disponible", BOOLEAN)),
            (
                "code_fap228",
                "libelle_fap228",
                "code_fap86",
                "libelle_fap86",
                "code_fap22",
                "libelle_fap22",
                "nb_fap341",
                "bmo_disponible",
                "rang_pertinence",
                *LICENCE_COLUMNS,
                "licence_confirmee",
                *_TOTAL,
            ),
            ("code_fap228",),
            ("gold.v_fap", "gold.source_licence"),
            "v_fap",
        ),
        Contract(
            "recrutement_bmo",
            "q14_recrutement_bmo.sql",
            "BMO 2026 recruitment projects (minimums) by FAP228 family and area.",
            (
                Param("code_fap228"),
                Param("niveau_geo", default="national", choices=NIVEAUX_GEO),
                Param("code_geo"),
                Param("tri", default="geo", choices=("geo", "minimum_desc")),
            ),
            (
                "code_fap228",
                "libelle_metier_bmo",
                "niveau_geo",
                "code_geo",
                "libelle_geo",
                "annee",
                "nb_projets_recrutement_minimum",
                "nb_projets_difficiles_minimum",
                "nb_projets_saisonniers_minimum",
                "nb_cellules",
                "nb_cellules_secretes_recrutement",
                "nb_cellules_secretes_difficiles",
                "nb_cellules_secretes_saisonniers",
                "est_complet_recrutement",
                "est_complet_difficiles",
                "est_complet_saisonniers",
                "nature_valeur",
                "_source_sha256",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("code_fap228", "niveau_geo", "code_geo"),
            ("gold.bmo_recrutement", "gold.source_licence"),
            "bmo_recrutement",
            one_of=("code_fap228", "code_geo"),
        ),
        Contract(
            "lister_zones_geo",
            "q15_lister_zones_geo.sql",
            "BMO 2026 geographical areas.",
            (Param("niveau_geo", choices=NIVEAUX_GEO),),
            (
                "niveau_geo",
                "code_geo",
                "libelle_geo",
                "nb_familles_fap228",
                "_source_sha256",
                *LICENCE_COLUMNS,
                *_TOTAL,
            ),
            ("niveau_geo", "code_geo"),
            ("search.v_zone_geo", "gold.source_licence"),
            "bmo_recrutement",
        ),
        Contract(
            "rechercher_rome_v3",
            "q16_rechercher_rome_v3.sql",
            "DARES ROME V3 x qualification -> FAP correspondence (ROME V3, not v62).",
            (
                _q(required=False),
                Param("code_rome_v3"),
                Param("code_qualification", choices=QUALIFICATIONS),
            ),
            (
                "nomenclature",
                "code_rome_v3",
                "libelle_rome_v3",
                "code_qualification",
                "libelle_qualification",
                "code_fap341",
                "libelle_fap341",
                "code_fap228",
                "libelle_fap228",
                "depend_qualification",
                "bmo_disponible",
                "rang_pertinence",
                "_snapshot",
                "_source_sha256",
                *LICENCE_COLUMNS,
                "licence_confirmee",
                *_TOTAL,
            ),
            ("code_rome_v3", "code_qualification"),
            ("gold.v_rome_v3_fap", "gold.source_licence"),
            "v_rome_v3_fap",
            one_of=("q", "code_rome_v3"),
        ),
        Contract(
            "licences",
            "q17_licences.sql",
            "Licence, attribution and restrictions of Gold objects.",
            (Param("objets", choices=OBJETS_GOLD, multi=True),),
            (
                "objet_gold",
                "type_objet",
                "sources",
                "licence",
                "attribution",
                "licence_confirmee",
                "restrictions",
                *_TOTAL,
            ),
            ("objet_gold",),
            ("gold.source_licence",),
            "source_licence",
        ),
    )
}


def get_contract(name: str) -> Contract:
    try:
        return CONTRACTS[name]
    except KeyError:
        raise ValueError(f"Unknown search contract: {name!r}") from None


@cache
def load_sql(name: str) -> str:
    """SQL text of a contract (one statement, named ``:parameters``)."""
    return (QUERIES_DIR / get_contract(name).file).read_text(encoding="utf-8")


def normalise_keyword(value: str) -> str:
    """Collapse whitespace and unify apostrophes, as the SQL does."""
    return re.sub(r"\s+", " ", value.replace("’", "'")).strip()


def _validate(param: Param, value: Any) -> Any:
    if value is None:
        return None
    if param.type == BOOLEAN:
        if not isinstance(value, bool):
            raise ValueError(f"{param.name}: expected a boolean, got {value!r}")
        return value
    if param.type == INT:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{param.name}: expected an integer, got {value!r}")
        return value
    if param.multi:
        items = value.split(",") if isinstance(value, str) else list(value)
        items = [str(i).strip() for i in items if str(i).strip()]
        if not items:
            return None
        bad = [i for i in items if i not in (param.choices or ())]
        if bad:
            raise ValueError(f"{param.name}: unknown value(s) {bad}, allowed {param.choices}")
        return ",".join(dict.fromkeys(items))
    if not isinstance(value, str):
        raise ValueError(f"{param.name}: expected a string, got {value!r}")
    value = normalise_keyword(value) if param.keyword else value.strip()
    if not value:
        return None
    if param.keyword and not QUERY_MIN_LENGTH <= len(value) <= QUERY_MAX_LENGTH:
        raise ValueError(
            f"{param.name}: length must be {QUERY_MIN_LENGTH}-{QUERY_MAX_LENGTH} characters"
        )
    if param.choices is not None and value not in param.choices:
        raise ValueError(f"{param.name}: {value!r} not in {param.choices}")
    return value


def bind(name: str, page: int = 1, page_size: int = PAGE_SIZE_DEFAULT, **values: Any) -> BoundQuery:
    """Validate ``values`` for contract ``name`` and return the SQL with its parameters."""
    contract = get_contract(name)
    known = {p.name: p for p in contract.params}
    unknown = set(values) - set(known)
    if unknown:
        raise ValueError(f"{name}: unknown parameter(s) {sorted(unknown)}")
    params: dict[str, Any] = {}
    for p in contract.params:
        value = _validate(p, values.get(p.name))
        if value is None:
            value = p.default
        if p.required and value is None:
            raise ValueError(f"{name}: parameter {p.name!r} is required")
        params[p.name] = value
    if contract.one_of and all(params[n] is None for n in contract.one_of):
        raise ValueError(f"{name}: at least one of {contract.one_of} is required")
    if contract.paginated:
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("page must be an integer >= 1")
        if isinstance(page_size, bool) or not isinstance(page_size, int):
            raise ValueError("page_size must be an integer")
        if not 1 <= page_size <= PAGE_SIZE_MAX:
            raise ValueError(f"page_size must be between 1 and {PAGE_SIZE_MAX}")
        params["page_size"] = page_size
        params["offset"] = (page - 1) * page_size
    return BoundQuery(contract, load_sql(name), params)
