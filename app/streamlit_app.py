"""Career Intelligence — Streamlit entry point (Phase 15B).

Run from the project root:  streamlit run app/streamlit_app.py --server.address localhost
"""

import streamlit as st
from common import PROFILE_PAGE, SEARCH_PAGE, TITLE, apply_style, brand

st.set_page_config(page_title=TITLE, page_icon=":material/insights:", layout="centered")
apply_style()

search = st.Page(SEARCH_PAGE, title="Rechercher un métier", icon=":material/search:", default=True)
pages = [
    search,
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

page.run()
