import streamlit as st
from typing import Optional

from spooty.utils.spotify_helpers import (
    authenticate_spotify,
    get_playlists,
    sync_playlist_with_liked_songs,
)

st.set_page_config(
    page_title="Playlist Sync",
    page_icon="🔄",
    layout="wide",
)

st.title("🔄 Playlist Sync")
st.write(
    "Sync your playlists with your liked songs. This tool will help you create a new playlist "
    "or update an existing one with songs from a source playlist that you've liked."
)

# Authenticate with Spotify
sp = authenticate_spotify()
if not sp:
    st.stop()

# Get current user's ID
current_user = sp.current_user()
user_id = current_user["id"]

# Get all playlists
playlists_df = get_playlists(sp)
if playlists_df.empty:
    st.error("No playlists found. Please create a playlist first.")
    st.stop()

# Source playlist selection
st.subheader("1. Select Source Playlist")
source_playlist = st.selectbox(
    "Choose the playlist you want to sync from:",
    options=playlists_df["name"].tolist(),
    index=0,
)
source_playlist_id = playlists_df[playlists_df["name"] == source_playlist]["id"].iloc[0]

# Destination playlist selection
st.subheader("2. Select Destination Playlist")
destination_option = st.radio(
    "Choose what to do with the synced songs:",
    ["Create a new playlist", "Update an existing playlist"],
)

if destination_option == "Create a new playlist":
    new_playlist_name = st.text_input(
        "Enter a name for the new playlist:",
        value=f"Liked Songs from {source_playlist}",
    )
    destination_playlist_id = None
else:
    destination_playlist = st.selectbox(
        "Choose the playlist to update:",
        options=playlists_df["name"].tolist(),
        index=0,
    )
    destination_playlist_id = playlists_df[playlists_df["name"] == destination_playlist]["id"].iloc[0]
    new_playlist_name = None

# Sync button
if st.button("Sync Playlists"):
    with st.spinner("Syncing playlists..."):
        try:
            destination_id = sync_playlist_with_liked_songs(
                sp,
                source_playlist_id,
                destination_playlist_id,
                new_playlist_name,
                user_id,
            )
            
            if destination_option == "Create a new playlist":
                st.success(f"Successfully created new playlist: {new_playlist_name}")
            else:
                st.success(f"Successfully updated playlist: {destination_playlist}")
            
            # Get the playlist URL
            playlist = sp.playlist(destination_id)
            st.markdown(f"[Open Playlist in Spotify]({playlist['external_urls']['spotify']})")
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}") 