"""Explorer le marché du travail — BMO recruitment intentions by FAP228 family and area.

Contracts: ``synthese_zones_bmo`` (all families of an area combined), ``recrutement_bmo``
(FAP228 x area) and ``lister_zones_geo`` (areas). Licence Ouverte, France Travail – BMO only:
no ROME occupation, no DARES FAP22/FAP86 grouping and no difficulty rate (decisions of Phase
15D). Every figure is a MINIMUM because of statistical secrecy. Three cases are kept apart:
a hidden value (every cell secret: « secret statistique »), a family x area pair absent from the
source (« non publié ») and any other missing value (« non disponible »).
"""

from typing import Any

import pandas as pd
import streamlit as st
from common import attribution, hero, load, plain, section

INDICATEURS = {
    "recrutement": ("nb_projets_recrutement_minimum", "Projets de recrutement"),
    "difficiles": ("nb_projets_difficiles_minimum", "Projets jugés difficiles"),
    "saisonniers": ("nb_projets_saisonniers_minimum", "Projets saisonniers"),
}
NIVEAUX = {"region": "Régions", "departement": "Départements"}
TOP = 15
SECRET, NON_PUBLIE, NON_DISPONIBLE = "secret statistique", "non publié", "non disponible"


def nombre(n: Any) -> str:
    return f"{int(n):,}".replace(",", " ")


def pct(part: Any, total: Any) -> float | None:
    return round(100 * part / total, 1) if total else None


def statut(row: dict[str, Any], indicateur: str) -> str | None:
    """Why an indicator has no value: hidden by secrecy, or otherwise not available."""
    if pd.notna(row[INDICATEURS[indicateur][0]]):
        return None
    if row["nb_cellules"] and row[f"nb_cellules_secretes_{indicateur}"] == row["nb_cellules"]:
        return SECRET
    return NON_DISPONIBLE


def valeur(row: dict[str, Any], indicateur: str) -> str:
    v = row[INDICATEURS[indicateur][0]]
    return f"au moins {nombre(v)}" if pd.notna(v) else statut(row, indicateur)


def remarques(row: dict[str, Any]) -> str:
    notes = [f"{INDICATEURS[i][1]} : {s}" for i in INDICATEURS if (s := statut(row, i)) is not None]
    return " · ".join(notes)


def tableau(rows: pd.DataFrame, libelle: str, entete: str, indicateur: str) -> pd.DataFrame:
    """Exact figures (minimums), share of hidden cells for the chosen indicator, and notes."""
    recs = rows.to_dict(orient="records")
    return pd.DataFrame(
        {
            entete: rows[libelle],
            "Projets de recrutement (min.)": rows["nb_projets_recrutement_minimum"],
            "Dont jugés difficiles (min.)": rows["nb_projets_difficiles_minimum"],
            "Dont saisonniers (min.)": rows["nb_projets_saisonniers_minimum"],
            f"Cellules masquées — {INDICATEURS[indicateur][1].lower()} (%)": [
                pct(r[f"nb_cellules_secretes_{indicateur}"], r["nb_cellules"]) for r in recs
            ],
            "Chiffre complet": rows[f"est_complet_{indicateur}"].map(
                lambda b: "Oui" if b else "Non (minimum)"
            ),
            "Remarques": [remarques(r) for r in recs],
        }
    )


def afficher_tableau(table: pd.DataFrame) -> None:
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            c: st.column_config.NumberColumn(format="localized")
            for c in table.columns
            if "(min.)" in c
        },
    )


def graphique(rows: pd.DataFrame, libelle: str, indicateur: str, titre: str) -> None:
    """Horizontal bars, largest first; values without a figure are listed, never drawn as 0."""
    colonne, nom = INDICATEURS[indicateur]
    publies = rows[rows[colonne].notna()]
    if publies.empty:
        st.info("Aucune valeur publiée pour cet indicateur.", icon=":material/visibility_off:")
        return
    axe = f"{nom} (minimum)"
    donnees = publies.nlargest(TOP, colonne)[[libelle, colonne]]
    donnees = donnees.rename(columns={libelle: "Libellé", colonne: axe})
    section(":material/bar_chart:", titre)
    st.bar_chart(
        donnees,
        x="Libellé",
        y=axe,
        horizontal=True,
        sort=f"-{axe}",
        x_label=axe,
        y_label="",
        height=max(220, 28 * len(donnees)),
    )
    if len(publies) > TOP:
        st.caption(f"Les {TOP} valeurs les plus élevées sur {len(publies)} ; détail ci-dessous.")
    caches = len(rows) - len(publies)
    if caches:
        st.caption(f":material/visibility_off: {caches} sans valeur publiée ({SECRET}).")


def choix_indicateur(cle: str) -> str:
    return st.selectbox(
        "Indicateur",
        list(INDICATEURS),
        key=cle,
        format_func=lambda i: INDICATEURS[i][1],
    )


# --- Territoires -----------------------------------------------------------------------------


def onglet_territoires(france: dict[str, Any]) -> None:
    with st.container(border=True, key="card-territoires"):
        gauche, droite = st.columns(2)
        with gauche:
            niveau = st.radio(
                "Comparer",
                list(NIVEAUX),
                key="bmo_niveau",
                format_func=NIVEAUX.get,
                horizontal=True,
            )
        with droite:
            indicateur = choix_indicateur("bmo_ind_zones")
    zones = load("fetch_all", "synthese_zones_bmo", niveau_geo=niveau).rows
    graphique(
        zones,
        "libelle_geo",
        indicateur,
        f"{NIVEAUX[niveau]} — toutes familles de métiers confondues",
    )
    st.caption(
        "Somme des minimums publiés de chaque famille : un minimum, pas un total exact. "
        f"France entière : {valeur(france, indicateur)}."
    )
    afficher_tableau(tableau(zones, "libelle_geo", "Zone", indicateur))

    st.divider()
    section(":material/location_on:", "Familles de métiers d'une zone")
    options = ["FR", *zones["code_geo"]]
    noms = {
        "FR": "France entière",
        **dict(zip(zones["code_geo"], zones["libelle_geo"], strict=True)),
    }
    if st.session_state.get("bmo_zone") not in options:
        st.session_state["bmo_zone"] = "FR"
    zone = st.selectbox("Zone", options, key="bmo_zone", format_func=noms.get)
    niveau_zone = "national" if zone == "FR" else niveau
    familles = load(
        "fetch_all",
        "recrutement_bmo",
        code_geo=zone,
        niveau_geo=niveau_zone,
        tri="minimum_desc",
    ).rows
    if familles.empty:
        st.info("Aucune famille de métiers publiée pour cette zone.", icon=":material/info:")
        return
    graphique(familles, "libelle_metier_bmo", indicateur, f"{noms[zone]} — familles de métiers")
    absentes = int(france["nb_familles_publiees"]) - len(familles)
    if absentes > 0:
        st.caption(
            f":material/remove: {absentes} famille(s) de métiers {NON_PUBLIE}e(s) dans cette zone "
            "(absentes de l'enquête pour cette zone, ce qui ne signifie pas zéro projet)."
        )
    afficher_tableau(tableau(familles, "libelle_metier_bmo", "Famille de métiers", indicateur))


# --- Familles de métiers ---------------------------------------------------------------------


def onglet_familles(nationales: pd.DataFrame) -> None:
    with st.container(border=True, key="card-familles"):
        recherche = st.text_input(
            "Filtrer les familles de métiers",
            key="bmo_fam_q",
            placeholder="ex. cuisine, infirmiers, S1X20",
            max_chars=100,
            icon=":material/search:",
        ).strip()
    liste = nationales
    if recherche:
        mots = recherche.lower().split()
        cle = (nationales["code_fap228"] + " " + nationales["libelle_metier_bmo"]).str.lower()
        liste = nationales[cle.map(lambda t: all(m in t for m in mots))]
    st.caption(f"{len(liste)} famille(s) de métiers sur {len(nationales)} (nomenclature FAP 2021).")
    if liste.empty:
        st.info("Aucune famille de métiers ne correspond.", icon=":material/search_off:")
        return
    noms = dict(zip(liste["code_fap228"], liste["libelle_metier_bmo"], strict=True))
    if st.session_state.get("bmo_fam") not in noms:
        st.session_state["bmo_fam"] = None
    code = st.selectbox(
        "Famille de métiers",
        list(noms),
        key="bmo_fam",
        index=None,
        placeholder="Choisir une famille de métiers",
        format_func=lambda c: f"{c} — {noms[c]}",
    )
    if not code:
        afficher_tableau(tableau(liste, "libelle_metier_bmo", "Famille de métiers", "recrutement"))
        return

    ligne = liste[liste["code_fap228"] == code].to_dict(orient="records")[0]
    with st.container(border=True, key="card-famille"):
        section(":material/work:", f"{noms[code]} ({code})")
        st.caption("France entière")
        colonnes = st.columns(3)
        for colonne, (i, (_, nom)) in zip(colonnes, INDICATEURS.items(), strict=True):
            v = ligne[INDICATEURS[i][0]]
            colonne.metric(
                f"{nom} (minimum)",
                nombre(v) if pd.notna(v) else statut(ligne, i),
                help=(
                    f"{pct(ligne[f'nb_cellules_secretes_{i}'], ligne['nb_cellules'])} % des "
                    "cellules de l'enquête sont masquées (secret statistique) pour cet indicateur."
                ),
            )

    gauche, droite = st.columns(2)
    with gauche:
        niveau = st.radio(
            "Comparer par",
            list(NIVEAUX),
            key="bmo_fam_niveau",
            format_func=NIVEAUX.get,
            horizontal=True,
        )
    with droite:
        indicateur = choix_indicateur("bmo_ind_fam")
    zones = load("fetch_all", "recrutement_bmo", code_fap228=code, niveau_geo=niveau).rows
    graphique(zones, "libelle_geo", indicateur, f"{noms[code]} — {NIVEAUX[niveau].lower()}")
    toutes = load("fetch_all", "lister_zones_geo", niveau_geo=niveau).rows
    absentes = toutes[~toutes["code_geo"].isin(zones["code_geo"])]
    if not absentes.empty:
        st.caption(
            f":material/remove: {NON_PUBLIE.capitalize()} pour {len(absentes)} zone(s) : "
            + ", ".join(plain(n) for n in absentes["libelle_geo"])
            + " (absence de l'enquête, pas zéro projet)."
        )
    afficher_tableau(tableau(zones, "libelle_geo", "Zone", indicateur))


# --- Difficultés de recrutement --------------------------------------------------------------


def onglet_difficultes(zones_regions: pd.DataFrame) -> None:
    st.info(
        "Aucun taux de difficulté n'est calculé. Les deux chiffres nécessaires sont des minimums "
        "dont une partie des cellules est masquée : leur rapport ne serait pas fiable. Le "
        "classement repose sur le nombre minimum de projets jugés difficiles, à lire avec la "
        "part de cellules masquées, qui peut dépasser la moitié.",
        icon=":material/info:",
    )
    options = ["FR", *zones_regions["code_geo"]]
    noms = {
        "FR": "France entière",
        **dict(zip(zones_regions["code_geo"], zones_regions["libelle_geo"], strict=True)),
    }
    if st.session_state.get("bmo_dif_zone") not in options:
        st.session_state["bmo_dif_zone"] = "FR"
    zone = st.selectbox("Zone", options, key="bmo_dif_zone", format_func=noms.get)
    familles = load(
        "fetch_all",
        "recrutement_bmo",
        code_geo=zone,
        niveau_geo="national" if zone == "FR" else "region",
    ).rows
    if familles.empty:
        st.info("Aucune famille de métiers publiée pour cette zone.", icon=":material/info:")
        return
    colonne = INDICATEURS["difficiles"][0]
    familles = familles.sort_values(
        [colonne, "code_fap228"], ascending=[False, True], na_position="last"
    )
    graphique(
        familles,
        "libelle_metier_bmo",
        "difficiles",
        f"{noms[zone]} — familles avec le plus de projets jugés difficiles",
    )
    afficher_tableau(tableau(familles, "libelle_metier_bmo", "Famille de métiers", "difficiles"))


# --- Page ------------------------------------------------------------------------------------

synthese = load("fetch_all", "synthese_zones_bmo", niveau_geo="national").rows
if synthese.empty:
    st.info("Les données BMO ne sont pas disponibles.", icon=":material/info:")
    st.stop()
france = synthese.to_dict(orient="records")[0]
annee = france["annee"]

hero(
    f"Enquête Besoins en Main-d'Œuvre · BMO {annee}",
    "Explorer le marché du travail",
    [
        "Les intentions de recrutement déclarées par les employeurs pour l'année "
        f"{annee}, par famille de métiers et par territoire.",
    ],
)
with st.container(border=True, key="card-lecture"):
    section(":material/info:", "Comment lire ces chiffres")
    st.markdown(
        f"- **Intentions, pas offres d'emploi** : l'enquête BMO {annee} recense des *projets "
        "de recrutement* envisagés par les employeurs, et non des offres d'emploi publiées "
        "ni des embauches réalisées.\n"
        "- **Des minimums** : pour protéger le secret statistique, France Travail masque les "
        "petites valeurs. Chaque chiffre affiché est la somme des valeurs publiées : le nombre "
        "réel est supérieur ou égal.\n"
        f"- **« {SECRET} »** : toutes les valeurs de la famille ou de la zone sont masquées. "
        f"**« {NON_PUBLIE} »** : l'enquête ne contient aucune ligne pour cette famille dans "
        "cette zone. Aucun de ces cas ne vaut zéro.\n"
        "- **Familles de métiers FAP 2021** (217 familles de l'enquête) : elles ne sont pas "
        "rattachées aux fiches métier ROME."
    )
    st.caption(
        f"France entière : {valeur(france, 'recrutement')} projets de recrutement, dont "
        f"{valeur(france, 'difficiles')} jugés difficiles et "
        f"{valeur(france, 'saisonniers')} saisonniers."
    )

territoires, familles_tab, difficultes = st.tabs(
    [
        ":material/map: Territoires",
        ":material/work: Familles de métiers",
        ":material/trending_down: Difficultés de recrutement",
    ]
)
with territoires:
    onglet_territoires(france)
with familles_tab:
    onglet_familles(load("fetch_all", "recrutement_bmo", code_geo="FR").rows)
with difficultes:
    onglet_difficultes(load("fetch_all", "synthese_zones_bmo", niveau_geo="region").rows)

attribution(france["licence"], france["attribution"])
