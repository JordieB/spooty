import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import time

from spooty.utils.spotify_helpers import (
    authenticate_spotify,
    clear_spotify_credentials,
)
from spooty.utils.logging_setup import get_logger

# Initialize logger
logger = get_logger(__name__)

# Setting config with improved theme
st.set_page_config(
    page_title="Spooty - Your Spotify Playlist Manager",
    page_icon="🎵",
    initial_sidebar_state="expanded",
    layout="wide",
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stApp {
        background-color: #f0f2f6;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        font-weight: bold;
    }
    .stAlert {
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# Capture query parameters early in the script
params = st.query_params
code = params.get("code", "")
st.session_state["code"] = code

# Display welcome message with improved styling
st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='color: #1DB954;'>Welcome to Spooty! 🎵</h1>
        <p style='font-size: 1.2rem;'>Your personal Spotify playlist manager</p>
    </div>
    """, unsafe_allow_html=True)

# Display Spotify authentication status and related options
with st.container():
    cols = st.columns([2, 1])
    
    # Main content column
    with cols[0]:
        st.markdown("### Spotify Connection")
        
        if "sp" not in st.session_state or st.session_state["sp"] is None:
            with st.spinner("Connecting to Spotify..."):
                st.session_state["sp"] = authenticate_spotify()
                if st.session_state["sp"]:
                    st.query_params.clear()
                    st.success("🎉 Successfully connected to Spotify!")
                    time.sleep(1)
                    st.rerun()
        elif st.session_state.get("sp"):
            st.success("✅ Connected to Spotify!")
            
            # Display user information
            try:
                user_info = st.session_state["sp"].current_user()
                st.markdown(f"""
                    <div style='margin-top: 1rem;'>
                        <p><strong>Username:</strong> {user_info['display_name']}</p>
                        <p><strong>Email:</strong> {user_info.get('email', 'Not available')}</p>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.warning("Could not fetch user information. Please try reconnecting.")

    # Sidebar column for actions
    with cols[1]:
        st.markdown("### Actions")
        with stylable_container(
            key="action_container",
            css_styles="""
                {
                    background-color: #ffffff;
                    padding: 1rem;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
            """
        ):
            if st.session_state.get("sp"):
                st.info("🔒 Manage Spotify Access")
                if st.button("Disconnect from Spotify", type="secondary"):
                    with st.spinner("Disconnecting..."):
                        clear_spotify_credentials()
                        time.sleep(1)
                        st.rerun()
            else:
                st.warning("🔑 Connect to Spotify to get started")
                if st.button("Connect to Spotify", type="primary"):
                    st.session_state["sp"] = authenticate_spotify()
                    st.rerun()

# Add feature highlights section
st.markdown("""
    <div style='margin-top: 2rem;'>
        <h2>✨ Features</h2>
        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;'>
            <div style='background-color: #ffffff; padding: 1rem; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <h3>🎵 Playlist Management</h3>
                <p>Create, edit, and organize your playlists with ease</p>
            </div>
            <div style='background-color: #ffffff; padding: 1rem; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <h3>🔄 Playlist Sync</h3>
                <p>Sync your liked songs across playlists</p>
            </div>
            <div style='background-color: #ffffff; padding: 1rem; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <h3>🔒 Privacy Controls</h3>
                <p>Manage your playlist privacy settings</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
