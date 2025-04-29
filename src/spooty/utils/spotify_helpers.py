import os
import time
from typing import Optional, List, Dict
from functools import lru_cache
import logging

import requests
import pandas as pd
import streamlit as st
from spotipy import Spotify  # type: ignore
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for batch processing
BATCH_SIZE = 50
API_RATE_LIMIT_DELAY = 1.0  # seconds


def clear_spotify_credentials():
    """
    Clears Spotify credentials by removing the cache file and resetting
    the session state.
    """
    if os.path.exists(".cache"):
        os.remove(".cache")
    st.session_state["sp"] = None
    st.query_params.clear()


def authenticate_spotify() -> Optional[Spotify]:
    """
    Manage the Spotify OAuth authentication flow outside of the Streamlit
    caching mechanism.

    Returns:
        Optional[Spotify]: An authenticated Spotify client if successful, None
            otherwise.
    """
    # Retrieve Spotify app credentials from Streamlit secrets
    CLIENT_ID = st.secrets.spotify_app["CLIENT_ID"]
    CLIENT_SECRET = st.secrets.spotify_app["CLIENT_SECRET"]
    REDIRECT_URI = st.secrets.spotify_app["REDIRECT_URI"]

    # Define the scope of permissions for Spotify access
    scopes = [
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-private",
        "playlist-modify-public",
        "user-library-read",
    ]
    SCOPE = " ".join(scopes)

    # Initialize Spotify OAuth manager
    auth_manager = SpotifyOAuth(
        CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, open_browser=True, scope=SCOPE
    )

    try:
        # Attempt to get token
        token_info = (
            auth_manager.get_access_token(st.session_state["code"])
            if st.session_state["code"]
            else auth_manager.get_cached_token()
        )

        # If wasn't successful
        if not token_info:
            # Send user to auth
            auth_url = auth_manager.get_authorize_url()
            st.warning("To Use App, Authorize Access to Your Spotify Data")
            st.markdown(f"Click [here]({auth_url}) to authorize.")
            return None

        # Token will be automatically refreshed if it is expired
        return Spotify(auth_manager=auth_manager)

    except SpotifyOauthError as e:
        st.error(f"Authentication error: {e}")
        # Check if authorization code has expired
        if "Authorization code expired" in str(e):
            st.warning("Your authorization code has expired. Please re-authenticate.")
            auth_url = auth_manager.get_authorize_url()
            st.markdown(f"Click [here]({auth_url}) to re-authenticate.")
        return None


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_playlists(
    _sp: Spotify,
    user_filter: Optional[str] = None,
    collaborative_filter: Optional[bool] = None,
    name_prefix: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch user's Spotify playlists with optional filtering and improved caching.
    """
    logger.info("Fetching playlists with filters: user=%s, collaborative=%s, prefix=%s",
                user_filter, collaborative_filter, name_prefix)
    
    # Fetch all playlists for the user with pagination and progress tracking
    all_playlists = []
    playlists = _sp.current_user_playlists()
    total_playlists = playlists.get('total', 0)
    processed = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while playlists:
        all_playlists.extend(playlists["items"])
        processed += len(playlists["items"])
        progress = processed / total_playlists
        progress_bar.progress(progress)
        status_text.text(f"Processing {processed}/{total_playlists} playlists...")
        
        playlists = _sp.next(playlists) if playlists["next"] else None
        time.sleep(API_RATE_LIMIT_DELAY)

    progress_bar.empty()
    status_text.empty()

    # Convert list of playlists to DataFrame
    df_playlists = pd.DataFrame(all_playlists)

    # Define filters based on function parameters
    filters = {
        "owner": lambda x: (
            x.get("display_name") == user_filter if user_filter else True
        ),
        "collaborative": lambda x: (
            x == collaborative_filter if collaborative_filter is not None else True
        ),
        "name": lambda x: x.startswith(name_prefix) if name_prefix else True,
    }

    # Apply filters to the DataFrame
    for key, filter_func in filters.items():
        df_playlists = df_playlists[df_playlists[key].apply(filter_func)]

    return df_playlists


@st.cache_data(ttl=3600)
def pull_tracks(_sp: Spotify, playlist_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pull track data for each playlist with batch processing and progress tracking.
    """
    logger.info("Pulling tracks for %d playlists", len(playlist_df))
    
    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_playlists = len(playlist_df)
    
    # Process playlists in batches
    tracks_dfs = []
    for i, playlist_id in enumerate(playlist_df["playlist_id"]):
        try:
            track_data = _sp.playlist_tracks(playlist_id)
            
            # Extract relevant track information and transform into DataFrame
            tracks = pd.DataFrame([track["track"] for track in track_data["items"]])
            tracks["artist_name"] = tracks["artists"].apply(lambda x: x[0]["name"])
            tracks["artist_id"] = tracks["artists"].apply(lambda x: x[0]["id"])
            tracks = tracks[["artist_name", "artist_id", "name", "id"]]
            tracks.rename(columns={"name": "track_name", "id": "track_id"}, inplace=True)
            tracks["playlist_id"] = playlist_id
            tracks_dfs.append(tracks)
            
            # Update progress
            progress = (i + 1) / total_playlists
            progress_bar.progress(progress)
            status_text.text(f"Processing playlist {i + 1}/{total_playlists}")
            
            time.sleep(API_RATE_LIMIT_DELAY)
            
        except Exception as e:
            logger.error(f"Error processing playlist {playlist_id}: {str(e)}")
            st.warning(f"Error processing playlist {playlist_id}. Skipping...")
            continue

    progress_bar.empty()
    status_text.empty()
    
    return pd.concat(tracks_dfs, ignore_index=True)


@st.cache_data(ttl=3600)
def pull_artist_and_genre(_sp: Spotify, tracks: pd.DataFrame) -> pd.DataFrame:
    """
    Pull artist and genre data using track information with batch processing.
    """
    logger.info("Pulling artist and genre data for %d tracks", len(tracks))
    
    # Get unique artist IDs from tracks
    unique_artist_ids = tracks["artist_id"].unique()
    total_artists = len(unique_artist_ids)
    
    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    processed_artists_data = []
    
    # Process artists in batches
    for i in range(0, len(unique_artist_ids), BATCH_SIZE):
        try:
            batch_ids = unique_artist_ids[i:i + BATCH_SIZE]
            artist_data = _sp.artists(batch_ids)["artists"]
            
            # Extract artist information
            for artist in artist_data:
                processed_artists_data.append(
                    [artist["id"], artist["name"], artist["genres"]]
                )
            
            # Update progress
            progress = min((i + BATCH_SIZE) / total_artists, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Processing artists {i + 1}-{min(i + BATCH_SIZE, total_artists)}/{total_artists}")
            
            time.sleep(API_RATE_LIMIT_DELAY)
            
        except Exception as e:
            logger.error(f"Error processing artist batch: {str(e)}")
            st.warning(f"Error processing artist batch. Some data may be missing.")
            continue

    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(
        processed_artists_data, columns=["artist_id", "artist_name", "genres"]
    )


def set_playlist_public_status(_sp, playlist_id, playlist_name, is_public):
    """
    Set the public/private status of a Spotify playlist.

    Args:
        playlist_id (str): The Spotify ID of the playlist.
        is_public (bool): True to make the playlist public, False to make it private.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    access_token = _sp.auth_manager.get_access_token(as_dict=False)
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'public': is_public
    }

    response = requests.put(url, headers=headers, json=payload)

    if response.status_code == 200:
        st.toast((f"Playlist '{playlist_name} ({playlist_id})' privacy status updated "
                 f"successfully."))
    else:
        st.toast((f"Failed to update playlist '{playlist_name} ({playlist_id})' privacy"
                  f" status. Status code: {response.status_code}"), icon="🚨")


def create_sample_playlist(
    sp: Spotify, user_id: str, df: pd.DataFrame, genre: str
) -> str:
    """
    Create a new playlist in Spotify and add the selected tracks.

    Args:
        sp (Spotify): Authenticated Spotify client.
        user_id (str): Spotify user ID.
        df (pd.DataFrame): DataFrame containing track information.
        genre (str): Genre of the playlist.

    Returns:
        str: Snapshot ID of the newly created playlist.
    """
    playlist_name = f"Sample Playlist - {genre}"
    playlist_description = f"A playlist created from selected tracks of genre {genre}."
    new_playlist = sp.user_playlist_create(
        user_id, playlist_name, description=playlist_description
    )
    playlist_id = new_playlist["id"]
    track_ids = df["track_id"].tolist()
    sp.user_playlist_add_tracks(user_id, playlist_id, track_ids)
    return playlist_id


@st.cache_data
def refresh_data(_sp: Spotify) -> pd.DataFrame:
    """
    Pull down playlist, track, and genre data using the authenticated Spotify client.

    Args:
        _sp (Spotify): Authenticated Spotify client.

    Returns:
        pd.DataFrame: DataFrame containing track and genre information.
    """
    playlists_df = get_playlists(_sp)
    tracks_df = pull_tracks(_sp, playlists_df)
    artist_genre_df = pull_artist_and_genre(_sp, tracks_df)
    combined_df = tracks_df.merge(artist_genre_df, on="artist_id", how="left")
    return combined_df


@st.cache_data
def get_liked_songs(_sp: Spotify) -> pd.DataFrame:
    """
    Fetch all of the user's liked songs from Spotify.

    Args:
        _sp (Spotify): Hashed authenticated Spotify client.

    Returns:
        pd.DataFrame: DataFrame containing liked songs information.
    """
    all_tracks = []
    results = _sp.current_user_saved_tracks(limit=50)
    
    while results:
        for item in results['items']:
            track = item['track']
            all_tracks.append({
                'track_id': track['id'],
                'track_name': track['name'],
                'artist_name': track['artists'][0]['name'],
                'artist_id': track['artists'][0]['id']
            })
        if results['next']:
            results = _sp.next(results)
        else:
            results = None
        time.sleep(0.1)  # Small delay to prevent rate limiting
    
    return pd.DataFrame(all_tracks)


def sync_playlist_with_liked_songs(
    _sp: Spotify,
    source_playlist_id: str,
    destination_playlist_id: Optional[str] = None,
    destination_playlist_name: Optional[str] = None,
    user_id: Optional[str] = None
) -> str:
    """
    Sync a playlist with liked songs, creating a new playlist or updating an existing one.

    Args:
        _sp (Spotify): Authenticated Spotify client.
        source_playlist_id (str): ID of the source playlist.
        destination_playlist_id (Optional[str]): ID of the destination playlist. If None, a new playlist will be created.
        destination_playlist_name (Optional[str]): Name for the new playlist if creating one.
        user_id (Optional[str]): Spotify user ID. Required if creating a new playlist.

    Returns:
        str: ID of the destination playlist.
    """
    # Get source playlist tracks
    source_tracks = []
    results = _sp.playlist_tracks(source_playlist_id)
    while results:
        source_tracks.extend([item['track']['id'] for item in results['items']])
        if results['next']:
            results = _sp.next(results)
        else:
            results = None
        time.sleep(0.1)

    # Get liked songs
    liked_songs = get_liked_songs(_sp)
    liked_track_ids = set(liked_songs['track_id'].tolist())

    # Filter source tracks to only those that are liked
    tracks_to_add = [track_id for track_id in source_tracks if track_id in liked_track_ids]

    # If no destination playlist is specified, create a new one
    if not destination_playlist_id:
        if not user_id or not destination_playlist_name:
            raise ValueError("user_id and destination_playlist_name are required when creating a new playlist")
        
        # Create new playlist
        new_playlist = _sp.user_playlist_create(
            user_id,
            destination_playlist_name,
            description=f"Playlist created from {source_playlist_id} containing only liked songs"
        )
        destination_playlist_id = new_playlist['id']
    else:
        # Get existing tracks in destination playlist
        existing_tracks = []
        results = _sp.playlist_tracks(destination_playlist_id)
        while results:
            existing_tracks.extend([item['track']['id'] for item in results['items']])
            if results['next']:
                results = _sp.next(results)
            else:
                results = None
            time.sleep(0.1)
        
        # Remove tracks that are already in the destination playlist
        tracks_to_add = [track_id for track_id in tracks_to_add if track_id not in existing_tracks]

    # Add tracks to destination playlist in batches of 100 (Spotify API limit)
    for i in range(0, len(tracks_to_add), 100):
        batch = tracks_to_add[i:i + 100]
        if batch:
            _sp.playlist_add_items(destination_playlist_id, batch)
            time.sleep(0.1)

    return destination_playlist_id
