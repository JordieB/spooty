# TODO: idea - limit tracks, artists, albums by those in Spotify official playlists
# TODO: idea - limit tracks by those in the user's playlists (e.g. "Liked Songs")
# TODO: idea - measure hz and ensure within range
# TODO: idea - limit tracks by those with titles that are within range 

import streamlit as st
from datetime import datetime

st.title('Binaural Beats Playlist Generator')

# Retrieve Spotify client
sp = st.session_state.get("sp")

# Input for frequency range
min_hz = st.number_input('Minimum Frequency (Hz)', min_value=0, value=35)
max_hz = st.number_input('Maximum Frequency (Hz)', min_value=0, value=45)

if st.button('Create Playlist with Set Frequency Range'):
    st.toast('Creating playlist...', icon='⏳')

    # Search for tracks within the frequency range
    query = f'binaural beats {min_hz}Hz {max_hz}Hz'
    results = sp.search(q=query, limit=50, type='track')

    # Extract track URIs
    track_uris = [track['uri'] for track in results['tracks']['items']]

    # Check if a playlist with the same name already exists
    user_id = sp.current_user()['id']
    existing_playlists = sp.user_playlists(user=user_id, limit=50)
    playlist_name = f'Binaural Beats {min_hz}-{max_hz} Hz'
    existing_playlist = next((pl for pl in existing_playlists['items'] if pl['name'] == playlist_name), None)

    if existing_playlist:
        # If playlist exists, update it with new tracks
        playlist_id = existing_playlist['id']
        if track_uris:  # Ensure there are URIs to add
            sp.playlist_add_items(playlist_id=playlist_id, items=track_uris)
        playlist_created = False
    else:
        # Create a new playlist
        playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=False)
        playlist_id = playlist['id']
        if track_uris:  # Ensure there are URIs to add
            sp.playlist_add_items(playlist_id=playlist_id, items=track_uris)
        playlist_created = True

    # Get timestamp of the last track added
    last_track_added_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if playlist_created:
        st.toast('Playlist created!', icon='✅')
        st.success(f'Playlist created successfully! ID: {playlist_id} | Last track added at: {last_track_added_time}')
    else:
        st.toast('Playlist updated!', icon='🔄')
        st.success(f'Playlist updated successfully! ID: {playlist_id} | Last track added at: {last_track_added_time}')
