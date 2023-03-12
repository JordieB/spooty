import streamlit as st
import os
from utils import create_spotipy_client

st.set_page_config(
    page_title="Spooty Homepage",
    page_icon="🏠",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://lmgtfy.app/',
        'Report a bug': 'https://lmgtfy.app/',
        'About': 'Lorem ipsum'
    }
)

st.title('Welcome to Spooty!')
st.write('Spooty is a quick hobby project by JordieB@Github. Working features are on the left, and feel free to close that sidebar.')

with st.container():
    cols = st.columns(2)
    # Left-side, handle auth-flow
    with cols[0]:
        # If user has never auth'd
        if 'sp' not in st.session_state:
            # Start auth flow
            st.session_state['sp'] = create_spotipy_client()
            st.success('You\'ve Authenticated!')
        # If user cleared auth manually
        else:
            # If client is avail aka truthy
            if st.session_state['sp'] is not None:
                st.success('You\'ve Authenticated!')
            else:
                # Start auth flow
                st.session_state['sp'] = create_spotipy_client()
                st.success('You\'ve Authenticated!')
    # Right-side, handle clearing auth
    with cols[1]:
        if 'sp' in st.session_state:
            if st.session_state['sp'] is not None:
                st.info('Click Below to Remove App\'s Access to Your Spotify Data')
                if st.button('Clear'):
                    os.remove('.cache')
                    st.session_state['sp'] = None
                    st.experimental_get_query_params()['code'] = None