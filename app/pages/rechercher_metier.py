"""Rechercher un métier — contract ``rechercher_metiers`` (filters from ``lister_domaines``)."""

import streamlit as st
from common import PROFILE_PAGE, attribution, hero, load, plain, section

CHAMPS = {
    "code_rome": "code ROME",
    "libelle_rome": "intitulé du métier",
    "appellation_long": "appellation",
    "appellation_court": "appellation",
    "definition": "définition",
    "acces_metier": "accès au métier",
}
# Visible labels only: the stored values ("", "O", "N") and the contract parameters are unchanged.
LIBELLES_CADRE = {
    "": "Tous les métiers",
    "O": "Métiers avec statut cadre",
    "N": "Métiers sans statut cadre",
}
LIBELLES_REGLEMENTE = {
    "": "Tous les métiers",
    "O": "Métiers soumis à une réglementation",
    "N": "Métiers non réglementés",
}
AIDE_CADRE = (
    "Un emploi cadre correspond à un poste impliquant généralement un niveau élevé de "
    "qualification, d'autonomie, d'expertise ou de responsabilités. Il ne nécessite pas "
    "forcément de manager une équipe. Le statut cadre dépend notamment de la classification "
    "conventionnelle du poste."
)
AIDE_REGLEMENTE = (
    "Un métier réglementé est une profession dont l'exercice est soumis à des conditions légales "
    "spécifiques, comme un diplôme obligatoire, une autorisation d'exercice ou une inscription à "
    "un ordre professionnel. Un métier non réglementé peut néanmoins nécessiter des "
    "qualifications ou des compétences particulières."
)
EXTRAIT = 160

hero(
    "Répertoire des métiers · ROME 4.0",
    "Rechercher un métier",
    [
        "Explorez les métiers, découvrez leurs compétences et accédez aux informations détaillées "
        "du répertoire ROME 4.0 de France Travail.",
        "Recherchez par nom de métier, code ROME ou mot-clé pour trouver les professions qui vous "
        "intéressent.",
    ],
)

qp = st.query_params
domaines = load("fetch_all", "lister_domaines").rows
grands = dict(zip(domaines["code_grand_domaine"], domaines["libelle_grand_domaine"], strict=False))

# Widgets have fixed keys, initialised once from the URL. Without keys, Streamlit derives a
# widget's identity from its arguments: seeding value=/index= from the URL gave the widget a new
# identity after each search, so the next edit was sent to the old widget and silently lost.
for key, value in {
    "f_q": qp.get("q", ""),
    "f_gd": qp.get("gd", ""),
    "f_dp": qp.get("dp", ""),
    "f_cadre": qp.get("cadre", ""),
    "f_regl": qp.get("regl", ""),
    "f_textes": qp.get("textes") == "1",
}.items():
    st.session_state.setdefault(key, value)


def _valid(key: str, options: list[str]) -> None:
    if st.session_state[key] not in options:
        st.session_state[key] = ""


with st.container(border=True, key="card-search"):
    q = st.text_input(
        "Métier, code ROME ou mot-clé",
        key="f_q",
        placeholder="ex. électricien, infirmier, M1805",
        max_chars=100,
        icon=":material/search:",
    )
    textes = st.checkbox(
        "Chercher aussi dans les textes",
        key="f_textes",
        help="Inclure la définition et les conditions d'accès au métier.",
    )
    st.space("small")
    domaine, statut = st.columns(2, gap="large")
    with domaine:
        section(":material/category:", "Domaine")
        options_gd = ["", *sorted(grands)]
        _valid("f_gd", options_gd)
        gd = st.selectbox(
            "Grand domaine",
            options_gd,
            key="f_gd",
            format_func=lambda c: f"{c} — {grands[c]}" if c else "Tous",
        )
        sous = domaines[domaines["code_grand_domaine"] == gd] if gd else domaines
        noms_dp = dict(
            zip(
                sous["code_domaine_professionnel"],
                sous["libelle_domaine_professionnel"],
                strict=False,
            )
        )
        options_dp = ["", *sorted(noms_dp)]
        _valid("f_dp", options_dp)
        dp = st.selectbox(
            "Domaine professionnel",
            options_dp,
            key="f_dp",
            format_func=lambda c: f"{c} — {noms_dp[c]}" if c else "Tous",
        )
    with statut:
        section(":material/verified_user:", "Statut du métier")
        options_on = ["", "O", "N"]
        _valid("f_cadre", options_on)
        _valid("f_regl", options_on)
        cadre = st.selectbox(
            "Emploi cadre",
            options_on,
            key="f_cadre",
            format_func=LIBELLES_CADRE.get,
            help=AIDE_CADRE,
        )
        reglemente = st.selectbox(
            "Emploi réglementé",
            options_on,
            key="f_regl",
            format_func=LIBELLES_REGLEMENTE.get,
            help=AIDE_REGLEMENTE,
        )

criteres = {
    "q": q.strip(),
    "gd": gd,
    "dp": dp,
    "cadre": cadre,
    "regl": reglemente,
    "textes": "1" if textes else "",
}
criteres = {k: v for k, v in criteres.items() if v}
anciens = {k: v for k, v in qp.to_dict().items() if k != "page"}
criteres_modifies = criteres != anciens  # a new query or filter always restarts at page 1
page = int(qp.get("page", "1")) if qp.get("page", "1").isdigit() and not criteres_modifies else 1
st.query_params.from_dict({**criteres, **({"page": str(page)} if page > 1 else {})})
st.session_state["derniere_recherche"] = st.query_params.to_dict()

if not criteres.get("q"):
    st.stop()

resultat = load(
    "search",
    "rechercher_metiers",
    page=page,
    q=criteres["q"],
    code_grand_domaine=gd or None,
    code_domaine_professionnel=dp or None,
    emploi_cadre=cadre or None,
    emploi_reglemente=reglemente or None,
    inclure_textes=textes,
)

if resultat.empty:
    if page > 1:
        st.info("Cette page ne contient plus de résultats.")
    else:
        st.info(
            "Aucun métier ne correspond. Essayez moins de mots, le singulier "
            "(« infirmier » plutôt que « infirmiers ») "
            "ou cochez « Chercher aussi dans les textes »."
        )
    st.stop()

trouves = "métier trouvé" if resultat.total == 1 else "métiers trouvés"
compte = f"{resultat.total} {trouves} · Page {page} sur {resultat.pages}"
st.space("small")
st.markdown(f"**{compte}**")

for i, r in enumerate(resultat.records()):
    with st.container(border=True, key=f"result-{i}"):
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.badge(plain(r["code_rome"]), color="blue", icon=":material/tag:")
            st.page_link(
                PROFILE_PAGE,
                label=r["libelle_rome"],
                query_params={"code_rome": r["code_rome"]},
                icon=":material/arrow_forward:",
                icon_position="right",
            )
        st.caption(
            f":material/category: {plain(r['libelle_grand_domaine'])} › "
            f"{plain(r['libelle_domaine_professionnel'])}"
        )
        champ = r["champ_correspondant"]
        texte = str(r["libelle_correspondant"] or "")
        detail = ""
        if champ not in ("code_rome", "libelle_rome"):
            extrait = texte if len(texte) <= EXTRAIT else texte[:EXTRAIT].rstrip() + "…"
            detail = f" : « {plain(extrait)} »"
        st.caption(f":material/manage_search: Correspondance — {CHAMPS.get(champ, champ)}{detail}")

st.space("small")
prec, info, suiv = st.columns([1, 2, 1], vertical_alignment="center")
precedent = prec.button(
    "Précédent",
    icon=":material/chevron_left:",
    disabled=not resultat.has_previous,
    width="stretch",
)
if precedent and not criteres_modifies:
    st.query_params["page"] = str(page - 1)
    st.rerun()
with info.container(horizontal_alignment="center"):
    st.caption(compte)
suivant = suiv.button(
    "Suivant",
    icon=":material/chevron_right:",
    icon_position="right",
    disabled=not resultat.has_next,
    width="stretch",
)
if suivant and not criteres_modifies:
    st.query_params["page"] = str(page + 1)
    st.rerun()

premier = resultat.records()[0]
attribution(premier["licence"], premier["attribution"])
