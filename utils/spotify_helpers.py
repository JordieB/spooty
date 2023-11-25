from typing import Optional
import time
import uuid

import pandas as pd
import numpy as np
import streamlit as st
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

def create_spotipy_client() -> Optional[Spotify]:
    """
    Initialize and authenticate the Spotify client using OAuth.

    Returns:
        Optional[Spotify]: An authenticated Spotify client if successful, 
                           None otherwise.
    """
    # Retrieve Spotify app credentials from Streamlit secrets
    CLIENT_ID = st.secrets.spotify_app['CLIENT_ID']
    CLIENT_SECRET = st.secrets.spotify_app['CLIENT_SECRET']
    REDIRECT_URI = st.secrets.spotify_app['REDIRECT_URI']
    
    # Define the scope of permissions for Spotify access
    scopes = [
        'playlist-read-private',
        'playlist-read-collaborative',
        'playlist-modify-private',
        'playlist-modify-public',
        'user-library-read'
    ]
    SCOPE = ' '.join(scopes)

    # Initialize Spotify OAuth manager
    auth_manager = SpotifyOAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI,
                                open_browser=True, scope=SCOPE)

    # Retrieve the authorization code from the URL parameters
    code = st.experimental_get_query_params().get('code', '')
    token_info = auth_manager.get_access_token(code) \
                 if code else auth_manager.get_cached_token()

    # Handle the case where the token is not obtained
    if not token_info:
        auth_url = auth_manager.get_authorize_url()
        st.warning('To Use App, Authorize Access to Your Spotify Data')
        if st.button('Authorize Access to Your Spotify Data', key='auth_but'):
            st.write('Click below to authorize this app on Spotify.')
            st.markdown(auth_url)
        return None

    # Return an authenticated Spotify client
    return Spotify(auth=token_info['access_token'])

@st.cache
def get_playlists(sp: Spotify, user_filter: Optional[str] = None, 
                  collaborative_filter: Optional[bool] = None, 
                  name_prefix: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch user's Spotify playlists with optional filtering.

    Args:
        sp (Spotify): Authenticated Spotify client.
        user_filter (Optional[str]): Filter by owner's display name.
        collaborative_filter (Optional[bool]): Filter for collaborative 
            playlists.
        name_prefix (Optional[str]): Filter by playlist name prefix.

    Returns:
        pd.DataFrame: DataFrame containing the playlists.
    """
    # Fetch all playlists for the user with pagination
    all_playlists = []
    playlists = sp.current_user_playlists()

    while playlists:
        all_playlists.extend(playlists['items'])
        playlists = sp.next(playlists) if playlists['next'] else None

    # Convert list of playlists to DataFrame
    df_playlists = pd.DataFrame(all_playlists)

    # Define filters based on function parameters
    filters = {
        'owner': lambda x: x.get('display_name') == user_filter \
            if user_filter else True,
        'collaborative': lambda x: x == collaborative_filter \
            if collaborative_filter is not None else True,
        'name': lambda x: x.startswith(name_prefix) if name_prefix else True
    }

    # Apply filters to the DataFrame
    for key, filter_func in filters.items():
        df_playlists = df_playlists[df_playlists[key].apply(filter_func)]

    return df_playlists

@st.cache
def pull_tracks(sp: Spotify, playlist_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pull track data for each playlist.

    Args:
        sp (Spotify): Authenticated Spotify client.
        playlist_df (pd.DataFrame): DataFrame containing playlist information.

    Returns:
        pd.DataFrame: DataFrame containing track information.
    """
    # Retrieve track data for each playlist
    tracks_dfs = []
    for playlist_id in playlist_df['playlist_id']:
        track_data = sp.playlist_tracks(playlist_id)

        # Extract relevant track information and transform into DataFrame
        tracks = pd.DataFrame([track['track'] \
                               for track in track_data['items']])
        tracks['artist_name'] = tracks['artists'].apply(
            lambda x: x[0]['name'])
        tracks['artist_id'] = tracks['artists'].apply(
            lambda x: x[0]['id'])
        tracks = tracks[['artist_name', 'artist_id', 'name', 'id']]
        tracks.rename(columns={'name': 'track_name', 'id': 'track_id'}, 
                      inplace=True)
        tracks['playlist_id'] = playlist_id
        tracks_dfs.append(tracks)
        time.sleep(1)  # Sleep to prevent hitting API rate limits

    return pd.concat(tracks_dfs, ignore_index=True)

@st.cache
def pull_artist_and_genre(sp: Spotify, tracks: pd.DataFrame) -> pd.DataFrame:
    """
    Pull artist and genre data using track information.

    Args:
        sp (Spotify): Authenticated Spotify client.
        tracks (pd.DataFrame): DataFrame containing track information.

    Returns:
        pd.DataFrame: DataFrame containing artist and genre information.
    """
    # Get unique artist IDs from tracks and fetch artist information
    unique_artist_ids = tracks['artist_id'].unique()
    processed_artists_data = []

    for i in range(0, len(unique_artist_ids), 50):
        # Spotify API limits artist queries to 50 at a time
        artist_data = sp.artists(unique_artist_ids[i:i + 50])['artists']
        
        # Extract artist information and compile into a list
        for artist in artist_data:
            processed_artists_data.append(
                [artist['id'], artist['name'], artist['genres']])
        time.sleep(1)  # Sleep to prevent hitting API rate limits

    # Convert artist information list to DataFrame
    return pd.DataFrame(processed_artists_data, 
                        columns=['artist_id', 'artist_name', 'genres'])
