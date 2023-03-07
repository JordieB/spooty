import streamlit as st

st.set_page_config(
    page_title="Spooty Homepage",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'localhost',
        'Report a bug': 'localhost',
        'About': 'Lorem ipsum'
    }
)