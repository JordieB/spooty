import os

import streamlit as st

from utils.spotify_helpers import authenticate_spotify, clear_spotify_credentials


# Setting config
st.set_page_config(
    page_title="Spooty Homepage",
    page_icon="🏠",
    initial_sidebar_state="expanded",
)

# Capture query parameters early in the script
params = st.query_params
code = params.get('code', '')
st.session_state['code'] = code

# Display welcome message
st.title('Welcome to Spooty!')

# Display Spotify authentication status and related options
with st.container():
    cols = st.columns(2)

    # In the left column, handle starting/finishing authentication
    with cols[0]:
        if 'sp' not in st.session_state or st.session_state['sp'] is None:
            st.session_state['sp'] = authenticate_spotify()
            if st.session_state['sp']:
                st.query_params.clear()
                st.success("You've authenticated with Spotify!")
        elif st.session_state.get('sp'):
            st.success("You're authenticated with Spotify!")
    
    # In right column, handle clearing credentials
    with cols[1]:
        if st.session_state.get('sp'):
            if st.session_state['sp'] is not None:
                st.info('Click Below to Remove App\'s Access to Your Spotify Data')
                if st.button('Clear'):
                    # Clear creds
                    clear_spotify_credentials()
                    # Rerun app
                    st.rerun()
