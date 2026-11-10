"""Explorer les formations — Formacode V14 training domains and ONISEP training programmes.

Contracts: ``lister_grands_domaines_formation``, ``rechercher_domaines_formation``,
``parcourir_domaines_formation``, ``metiers_par_domaine_formation`` (Formacode, Licence Ouverte)
and ``couverture_onisep``, ``rechercher_formations_onisep``, ``metiers_par_formation_onisep``
(ONISEP, ODbL). The two sources are shown in separate tabs, each with its own attribution.
Only descriptors linked to at least one ROME occupation exist in Gold; ONISEP coverage is
partial and computed from Gold, never extrapolated.
"""

from typing import Any

import pandas as pd
import streamlit as st
from common import PROFILE_PAGE, attribution, hero, load, plain, section

# Documented in docs/DATA_SOURCES.md (Silver counts, not exposed by Gold).
DESCRIPTEURS_THESAURUS = 2775
TYPES_LIEN = {
    "formation_menant_au_metier": "Formations menant au métier",
    "formation_minimale_requise": "Formation minimale requise",
}


def nombre(n: Any) -> str:
    """French thousands separator (narrow no-break space)."""
    return f"{int(n):,}".replace(",", " ")


def pourcentage(part: int, total: int) -> str:
    return f"{100 * part / total:.1f}".replace(".", ",") + " %"


def pagination(cle: str, criteres: dict[str, Any]) -> int:
    """Current page of a result list; back to page 1 whenever its criteria change."""
    if st.session_state.get(f"{cle}_criteres") != criteres:
        st.session_state[f"{cle}_criteres"] = criteres
        st.session_state[f"{cle}_page"] = 1
    return st.session_state.get(f"{cle}_page", 1)


def boutons_pages(cle: str, resultat: Any) -> None:
    if resultat.pages <= 1:
        return
    prec, info, suiv = st.columns([1, 2, 1], vertical_alignment="center")
    if prec.button(
        "Précédent",
        key=f"{cle}_prec",
        icon=":material/chevron_left:",
        disabled=not resultat.has_previous,
        width="stretch",
    ):
        st.session_state[f"{cle}_page"] = resultat.page - 1
        st.rerun()
    with info.container(horizontal_alignment="center"):
        st.caption(f"Page {resultat.page} sur {resultat.pages}")
    if suiv.button(
        "Suivant",
        key=f"{cle}_suiv",
        icon=":material/chevron_right:",
        icon_position="right",
        disabled=not resultat.has_next,
        width="stretch",
    ):
        st.session_state[f"{cle}_page"] = resultat.page + 1
        st.rerun()


def choix(cle: str, options: list[str]) -> None:
    """Forget a selection that is no longer offered (new search or page)."""
    if st.session_state.get(cle) not in options:
        st.session_state[cle] = None


def lien_metier(cle: str, code_rome: str, libelle: str, detail: str | None = None) -> None:
    with st.container(border=True, key=f"result-{cle}-{code_rome}"):
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.badge(plain(code_rome), color="blue", icon=":material/tag:")
            st.page_link(
                PROFILE_PAGE,
                label=libelle,
                query_params={"code_rome": code_rome},
                icon=":material/arrow_forward:",
                icon_position="right",
            )
        if detail:
            st.caption(detail)


# --- Formacode -----------------------------------------------------------------------------


def onglet_formacode() -> None:
    grands = load("fetch_all", "lister_grands_domaines_formation").rows
    noms = dict(
        zip(
            grands["code_grand_domaine_formacode"],
            grands["libelle_grand_domaine_formacode"],
            strict=True,
        )
    )
    nb_lies = int(grands["nb_descripteurs"].sum())
    st.info(
        f"Cette page présente les {nombre(nb_lies)} descripteurs Formacode® V14 reliés à au "
        f"moins un métier du répertoire ROME (sur {nombre(DESCRIPTEURS_THESAURUS)} descripteurs "
        "du thésaurus). Un descripteur peut être relié à plusieurs métiers, et un métier à "
        "plusieurs descripteurs.",
        icon=":material/info:",
    )

    with st.container(border=True, key="card-formacode"):
        options = ["", *grands["code_grand_domaine_formacode"]]
        if st.session_state.get("fc_gd") not in options:
            st.session_state["fc_gd"] = ""
        gd = st.selectbox(
            "Grand domaine de formation",
            options,
            key="fc_gd",
            format_func=lambda c: f"{c} — {noms[c]}" if c else "Tous les grands domaines",
        )
        st.text_input(
            "Descripteur ou code Formacode",
            key="fc_q",
            placeholder="ex. informatique, soudage, 31054",
            max_chars=100,
            icon=":material/search:",
        )
        st.button("Rechercher", key="btn-formacode", type="primary", icon=":material/search:")
    q = st.session_state.get("fc_q", "").strip()

    if not q and not gd:
        section(":material/category:", f"Les {len(grands)} grands domaines Formacode")
        table = grands[
            [
                "code_grand_domaine_formacode",
                "libelle_grand_domaine_formacode",
                "nb_descripteurs",
                "nb_metiers",
            ]
        ].rename(
            columns={
                "code_grand_domaine_formacode": "Code",
                "libelle_grand_domaine_formacode": "Grand domaine",
                "nb_descripteurs": "Descripteurs reliés",
                "nb_metiers": "Métiers associés",
            }
        )
        st.dataframe(table, hide_index=True, width="stretch")
        st.caption(
            "Choisissez un grand domaine ou recherchez un descripteur pour voir les métiers "
            "associés. Les nombres sont des décomptes de liens, pas des pondérations."
        )
    else:
        page = pagination("fc", {"q": q, "gd": gd})
        if q:
            res = load(
                "search",
                "rechercher_domaines_formation",
                page=page,
                q=q,
                code_grand_domaine_formacode=gd or None,
            )
        else:
            res = load(
                "search",
                "parcourir_domaines_formation",
                page=page,
                code_grand_domaine_formacode=gd,
            )
        descripteurs(res)

    attribution(grands["licence"].iloc[0], grands["attribution"].iloc[0])
    st.caption("Formacode® est une marque déposée du Centre Inffo.")


def descripteurs(res: Any) -> None:
    if res.empty:
        st.info(
            "Aucun descripteur ne correspond. Essayez un autre mot, le singulier, ou un autre "
            "grand domaine.",
            icon=":material/search_off:",
        )
        return
    trouves = "descripteur trouvé" if res.total == 1 else "descripteurs trouvés"
    st.markdown(f"**{res.total} {trouves} · Page {res.page} sur {res.pages}**")
    rows = res.rows
    table = pd.DataFrame(
        {
            "Code": rows["code_formacode"],
            "Descripteur": rows["libelle_formacode"],
            "Champ sémantique": rows["libelle_champ_semantique"],
            "Grand domaine": rows["libelle_grand_domaine_formacode"],
            "Niveau": rows["niveau"],
            "Type de terme": rows["est_terme_feuille"].map(
                lambda f: "Spécifique" if f else "Générique"
            ),
            "Métiers": rows["nb_metiers"],
        }
    )
    st.dataframe(table, hide_index=True, width="stretch")
    boutons_pages("fc", res)

    libelles = dict(zip(rows["code_formacode"], rows["libelle_formacode"], strict=True))
    choix("fc_sel", list(libelles))
    code = st.selectbox(
        "Voir les métiers associés à un descripteur",
        list(libelles),
        key="fc_sel",
        index=None,
        placeholder="Choisir un descripteur de cette page",
        format_func=lambda c: f"{c} — {libelles[c]}",
    )
    if code:
        metiers_du_descripteur(code, libelles[code])


def metiers_du_descripteur(code: str, libelle: str) -> None:
    res = load("fetch_all", "metiers_par_domaine_formation", code_formacode=code)
    with st.container(border=True, key="card-descripteur"):
        section(":material/school:", f"{libelle} ({code})")
        if res.empty:
            st.info("Aucun métier n'est relié à ce descripteur.", icon=":material/info:")
            return
        n = res.total
        st.caption(f"{n} métier{'s' if n > 1 else ''} associé{'s' if n > 1 else ''}")
    for r in res.records():
        domaine = f":material/category: {plain(r['libelle_grand_domaine'])}"
        lien_metier("fc", r["code_rome"], r["libelle_rome"], domaine)


# --- ONISEP --------------------------------------------------------------------------------


def onglet_onisep() -> None:
    couv = load("get", "couverture_onisep")
    if couv is None:
        st.info("Les données ONISEP ne sont pas disponibles.", icon=":material/info:")
        return
    avec, total = couv["nb_metiers_avec_formation"], couv["nb_metiers_rome"]
    with st.container(border=True, key="card-couverture"):
        section(":material/pie_chart:", "Couverture partielle des données ONISEP")
        st.metric(
            "Métiers ROME ayant au moins une formation ONISEP",
            f"{nombre(avec)} / {nombre(total)}",
            border=False,
            help="Calculé sur les liens formation ↔ métier publiés par l'ONISEP.",
        )
        st.caption(f"Soit environ {pourcentage(avec, total)} des métiers du répertoire ROME.")

    with st.container(border=True, key="card-onisep"):
        st.text_input(
            "Formation, code RNCP ou identifiant ONISEP",
            key="on_q",
            placeholder="ex. bts, infirmier, électricien",
            max_chars=100,
            icon=":material/search:",
        )
        st.button("Rechercher", key="btn-onisep", type="primary", icon=":material/search:")
    q = st.session_state.get("on_q", "").strip()
    if q:
        page = pagination("on", {"q": q})
        res = load("search", "rechercher_formations_onisep", page=page, q=q)
        formations(res)
    else:
        st.caption(
            f"Recherchez parmi les {nombre(couv['nb_formations'])} formations ONISEP reliées à "
            "des métiers."
        )

    attribution(couv["licence"], couv["attribution"])
    st.caption(
        "Données ONISEP sous licence ODbL : toute base de données dérivée doit être partagée "
        "sous la même licence."
    )


def formations(res: Any) -> None:
    if res.empty:
        st.info(
            "Aucune formation ne correspond. Essayez moins de mots ou un autre intitulé.",
            icon=":material/search_off:",
        )
        return
    trouvees = "formation trouvée" if res.total == 1 else "formations trouvées"
    st.markdown(f"**{res.total} {trouvees} · Page {res.page} sur {res.pages}**")
    rows = res.rows
    table = pd.DataFrame(
        {
            "Formation": rows["libelle_formation"],
            "Type": rows["libelle_type_formation"],
            "Niveau": rows["libelle_niveau_de_certification"],
            "Durée": rows["duree"],
            "RNCP": rows["code_rncp"],
            "Métiers ROME": rows["nb_codes_rome"],
            "Fiche ONISEP": rows["url_onisep"],
        }
    )
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={"Fiche ONISEP": st.column_config.LinkColumn(display_text="Ouvrir")},
    )
    boutons_pages("on", res)

    libelles = dict(zip(rows["identifiant_formation"], rows["libelle_formation"], strict=True))
    choix("on_sel", list(libelles))
    ident = st.selectbox(
        "Voir les métiers associés à une formation",
        list(libelles),
        key="on_sel",
        index=None,
        placeholder="Choisir une formation de cette page",
        format_func=lambda i: libelles[i],
    )
    if ident:
        hors = rows.loc[rows["identifiant_formation"] == ident, "formation_dans_catalogue"]
        metiers_de_la_formation(ident, libelles[ident], not bool(hors.iloc[0]))


def metiers_de_la_formation(ident: str, libelle: str, hors_catalogue: bool) -> None:
    res = load("fetch_all", "metiers_par_formation_onisep", identifiant_formation=ident)
    with st.container(border=True, key="card-formation"):
        section(":material/school:", libelle)
        st.caption(f"Identifiant ONISEP : {plain(ident)}")
        if hors_catalogue:
            st.caption(
                ":material/info: Formation absente du catalogue ONISEP des formations "
                "initiales : seul son intitulé est connu."
            )
        if res.empty:
            st.info("Aucun métier n'est relié à cette formation.", icon=":material/info:")
            return
    rows = res.rows
    for type_lien, titre in TYPES_LIEN.items():
        liens = rows[rows["type_lien"] == type_lien]
        if liens.empty:
            continue
        valides = liens[liens["code_rome"].notna()]
        st.markdown(f"**{titre}** ({valides['code_rome'].nunique()} métier(s) ROME)")
        # One entry per ROME code; the ONISEP occupations behind each link are all listed.
        for code, groupe in valides.groupby("code_rome", sort=False):
            via = ", ".join(dict.fromkeys(groupe["nom_metier_onisep"]))
            lien_metier(
                type_lien, code, groupe["libelle_rome"].iloc[0], f"Métier ONISEP : {plain(via)}"
            )
        non_resolus = liens[liens["code_rome"].isna()]
        if not non_resolus.empty:
            with st.container(border=True, key=f"card-non-resolus-{type_lien}"):
                st.caption(
                    ":material/help: Codes ROME cités par l'ONISEP sans correspondance dans "
                    "le répertoire ROME 4.0 (non résolus) :"
                )
                uniques = non_resolus.drop_duplicates(["code_rome_source", "nom_metier_onisep"])
                for r in uniques.itertuples():
                    st.caption(f"{plain(r.code_rome_source)} — {plain(r.nom_metier_onisep)}")


# --- Page ----------------------------------------------------------------------------------

hero(
    "Formacode® V14 · ONISEP",
    "Explorer les formations",
    [
        "Parcourez les domaines de formation Formacode et les formations de l'ONISEP, et "
        "découvrez les métiers du répertoire ROME 4.0 auxquels ils sont reliés.",
    ],
)

domaines, onisep = st.tabs(
    [":material/category: Domaines de formation", ":material/school: Formations ONISEP"]
)
with domaines:
    onglet_formacode()
with onisep:
    onglet_onisep()
