"""Career Intelligence — Streamlit entry point (Phase 15B).

Run from the project root:  streamlit run app/streamlit_app.py --server.address localhost
"""

import streamlit as st
from common import (
    LABOUR_PAGE,
    PROFILE_PAGE,
    SEARCH_PAGE,
    TITLE,
    TRAINING_PAGE,
    apply_style,
    brand,
)

st.set_page_config(page_title=TITLE, page_icon=":material/insights:", layout="centered")
apply_style()

search = st.Page(SEARCH_PAGE, title="Rechercher un métier", icon=":material/search:", default=True)
training = st.Page(
    TRAINING_PAGE, title="Explorer les formations", icon=":material/school:", url_path="formations"
)
labour = st.Page(
    LABOUR_PAGE, title="Explorer le marché du travail", icon=":material/work:", url_path="marche"
)
pages = [
    search,
    training,
    labour,
    st.Page(PROFILE_PAGE, title="Fiche métier", url_path="fiche", visibility="hidden"),
]

page = st.navigation(pages, position="hidden")

with st.sidebar:
    brand(TITLE)
    st.caption(
        "Explorez les métiers du marché du travail français, leurs compétences et leurs "
        "appellations grâce aux données officielles de France Travail."
    )
    st.divider()
    st.page_link(search, label="Rechercher un métier", icon=":material/search:")
    st.page_link(training, label="Explorer les formations", icon=":material/school:")
    st.page_link(labour, label="Explorer le marché du travail", icon=":material/work:")

page.run()
