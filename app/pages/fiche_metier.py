"""Fiche métier — contracts ``fiche_metier``, ``appellations_metier``, ``competences_metier``.

ROME 4.0 (v62) data only. Texts come from the search layer (doubled source apostrophes
corrected). No BMO, FAP or ROME V3 information is shown or linked here (decision D2).
"""

import streamlit as st
from common import SEARCH_PAGE, attribution, hero, load, oui_non, plain

TYPES = {
    "savoir_faire": "Savoir-faire",
    "savoir_etre": "Savoir-être professionnels",
    "savoir": "Savoirs",
    "contexte_travail": "Contextes de travail",
}
CLASSIFICATIONS = {"PRINCIPALE": "Appellations principales", "SYNONYME": "Synonymes"}

st.page_link(
    SEARCH_PAGE,
    label="Retour à la recherche",
    icon=":material/arrow_back:",
    query_params=st.session_state.get("derniere_recherche", {}),
)

code = (st.query_params.get("code_rome") or "").strip().upper()
if not code:
    st.info("Choisissez un métier depuis la page de recherche.", icon=":material/info:")
    st.stop()

fiche = load("get", "fiche_metier", code_rome=code)
if fiche is None:
    st.warning(f"Code ROME inconnu : {plain(code)}", icon=":material/search_off:")
    st.stop()

hero(
    f"Fiche métier · ROME 4.0, version {fiche['_rome_version']}",
    fiche["libelle_rome"],
    [f"{fiche['libelle_grand_domaine']} › {fiche['libelle_domaine_professionnel']}"],
)

cadre, reglemente = oui_non(fiche["emploi_cadre"]), oui_non(fiche["emploi_reglemente"])
with st.container(horizontal=True, gap="small"):
    st.badge(f"Code ROME {plain(fiche['code_rome'])}", color="blue", icon=":material/tag:")
    st.badge(
        f"Emploi cadre : {cadre}",
        color="green" if cadre == "Oui" else "gray",
        icon=":material/workspace_premium:",
    )
    st.badge(
        f"Emploi réglementé : {reglemente}",
        color="green" if reglemente == "Oui" else "gray",
        icon=":material/gavel:",
    )

chiffres = [
    ("Appellations", "nb_appellations", ":material/badge:"),
    ("Savoir-faire", "nb_savoir_faire", ":material/construction:"),
    ("Savoir-être", "nb_savoir_etre", ":material/diversity_3:"),
    ("Savoirs", "nb_savoirs", ":material/menu_book:"),
    ("Contextes de travail", "nb_contextes_travail", ":material/apartment:"),
]
with st.container(horizontal=True, gap="small"):
    for libelle, champ, icone in chiffres:
        st.metric(libelle, fiche[champ], border=True, icon=icone, width="content")

presentation, appellations, competences, complements = st.tabs(
    [
        ":material/description: Présentation",
        ":material/badge: Appellations",
        ":material/psychology: Compétences",
        ":material/info: Informations complémentaires",
    ]
)

with presentation:
    with st.container(border=True, key="card-definition"):
        st.subheader(":material/description: Définition")
        st.markdown(plain(fiche["definition"]))
    with st.container(border=True, key="card-acces"):
        st.subheader(":material/school: Accès au métier")
        st.markdown(plain(fiche["acces_metier"]))

with appellations:
    toutes = st.toggle("Inclure les appellations peu usitées", value=True)
    res = load("fetch_all", "appellations_metier", code_rome=code, inclure_peu_usitees=toutes)
    st.caption(f"{res.total} appellation(s)")
    if not res.empty:
        ordre = {c: i for i, c in enumerate(CLASSIFICATIONS)}  # principales before synonyms
        groupes = sorted(
            res.rows.groupby("classification", sort=False), key=lambda g: ordre.get(g[0], 99)
        )
        for classification, groupe in groupes:
            with st.container(border=True, key=f"card-appellations-{classification.lower()}"):
                titre = CLASSIFICATIONS.get(classification, classification.capitalize())
                st.markdown(f"**{plain(titre)}** ({len(groupe)})")
                with st.container(horizontal=True, gap="small"):
                    for a in groupe.itertuples():
                        rare = a.peu_usite == "O"
                        st.badge(
                            plain(a.libelle_appellation_long),
                            color="gray" if rare or classification != "PRINCIPALE" else "blue",
                            icon=":material/history:" if rare else None,
                            help="Appellation peu usitée" if rare else None,
                        )
        st.caption(":material/history: appellation peu usitée")
        with st.expander("Afficher le tableau détaillé", icon=":material/table:"):
            table = res.rows[["libelle_appellation_long", "classification", "peu_usite"]].copy()
            table["peu_usite"] = table["peu_usite"].map(oui_non)
            st.dataframe(
                table.rename(
                    columns={
                        "libelle_appellation_long": "Appellation",
                        "classification": "Classification",
                        "peu_usite": "Peu usitée",
                    }
                ),
                hide_index=True,
                width="stretch",
            )

with competences:
    coeur = st.toggle("Compétences cœur de métier seulement", value=False)
    res = load("fetch_all", "competences_metier", code_rome=code, coeur_metier_seulement=coeur)
    if res.empty:
        st.info("Aucun élément pour ce filtre.", icon=":material/info:")
    else:
        st.caption(":material/star: compétence cœur de métier")
    for type_element, titre in TYPES.items():
        groupe = res.rows[res.rows["type_element"] == type_element] if not res.empty else res.rows
        if groupe.empty:
            continue
        with st.container(border=True, key=f"card-{type_element}"):
            st.subheader(f"{titre} ({len(groupe)})")
            for categorie, elements in groupe.groupby("categorie", sort=False, dropna=False):
                if groupe["categorie"].nunique(dropna=False) > 1:
                    st.markdown(
                        f"**{plain(categorie if isinstance(categorie, str) else 'Autres')}**"
                    )
                with st.container(horizontal=True, gap="small"):
                    for e in elements.itertuples():
                        principal = e.coeur_metier == "Principale"
                        st.badge(
                            plain(e.libelle_element),
                            color="green" if principal else "gray",
                            icon=":material/star:" if principal else None,
                            help=e.sous_categorie if isinstance(e.sous_categorie, str) else None,
                        )
            with st.expander("Afficher le tableau détaillé", icon=":material/table:"):
                table = groupe[["libelle_element", "categorie", "sous_categorie", "coeur_metier"]]
                table = table.copy()
                table["coeur_metier"] = table["coeur_metier"].map(
                    lambda v: "Oui" if v == "Principale" else ""
                )
                st.dataframe(
                    table.rename(
                        columns={
                            "libelle_element": "Élément",
                            "categorie": "Catégorie",
                            "sous_categorie": "Sous-catégorie",
                            "coeur_metier": "Cœur de métier",
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )

with complements:
    valeurs = [
        ("Code RIASEC majeur", fiche["riasec_majeur"] or "Non renseigné"),
        ("Code RIASEC mineur", fiche["riasec_mineur"] or "Non renseigné"),
        ("Transition écologique", fiche["transition_eco"] or "Non renseigné"),
        ("Transition numérique", oui_non(fiche["transition_num"])),
        ("Transition démographique", oui_non(fiche["transition_demo"])),
    ]
    for ligne in (valeurs[:2], valeurs[2:]):
        for colonne, (libelle, valeur) in zip(st.columns(len(ligne)), ligne, strict=True):
            with colonne.container(border=True, key=f"card-info-{libelle}"):
                st.caption(libelle)
                st.markdown(f"**{plain(valeur)}**")
    st.caption("Valeurs publiées par France Travail dans le répertoire ROME, sans interprétation.")

attribution(fiche["licence"], fiche["attribution"])
