import os
import time
from typing import Optional, List, Dict, Tuple
from functools import lru_cache
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
from statistics import mean

import requests
import pandas as pd
import streamlit as st
from spotipy import Spotify  # type: ignore
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError  # type: ignore

from spooty.utils.logging_setup import get_logger

# Get logger for this module
logger = get_logger(__name__)

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
    logger.info("Starting playlist fetch with cache TTL=3600s")
    logger.info("Fetching playlists with filters: user=%s, collaborative=%s, prefix=%s",
                user_filter, collaborative_filter, name_prefix)
    
    # Fetch all playlists for the user with pagination and progress tracking
    all_playlists = []
    playlists = _sp.current_user_playlists()
    total_playlists = playlists.get('total', 0)
    processed = 0
    
    logger.info(f"Found {total_playlists} total playlists to process")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while playlists:
        batch_size = len(playlists["items"])
        all_playlists.extend(playlists["items"])
        processed += batch_size
        progress = processed / total_playlists
        progress_bar.progress(progress)
        status_text.text(f"Processing {processed}/{total_playlists} playlists...")
        logger.info(f"Processed batch of {batch_size} playlists. Progress: {processed}/{total_playlists}")
        
        playlists = _sp.next(playlists) if playlists["next"] else None
        if playlists:
            logger.debug("Waiting for rate limit before next batch...")
            time.sleep(API_RATE_LIMIT_DELAY)

    progress_bar.empty()
    status_text.empty()
    logger.info(f"Completed fetching all {processed} playlists")

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
    initial_count = len(df_playlists)
    for key, filter_func in filters.items():
        df_playlists = df_playlists[df_playlists[key].apply(filter_func)]
    
    final_count = len(df_playlists)
    logger.info(f"Applied filters: {initial_count} playlists filtered to {final_count}")
    return df_playlists


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts delay based on API response patterns"""
    def __init__(self, initial_delay: float = 1.0, min_delay: float = 0.1, max_delay: float = 2.0):
        self.current_delay = initial_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.response_times: List[float] = []
        self.error_count = 0
        
    def update(self, success: bool, response_time: float) -> None:
        """Update the rate limiter based on API response"""
        if success:
            self.response_times.append(response_time)
            if len(self.response_times) > 10:
                self.response_times.pop(0)
            
            # If we have enough samples and responses are fast, decrease delay
            if len(self.response_times) >= 5 and mean(self.response_times) < 0.5:
                self.current_delay = max(self.min_delay, self.current_delay * 0.9)
            self.error_count = 0
        else:
            # On error, increase delay
            self.error_count += 1
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
    
    def delay(self) -> None:
        """Apply the current delay"""
        time.sleep(self.current_delay)


@st.cache_data(ttl=3600)
def pull_tracks(_sp: Spotify, playlist_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pull track data for each playlist with batch processing and progress tracking.
    Handles both music tracks and podcast episodes gracefully.
    Uses adaptive rate limiting to optimize processing speed while avoiding rate limits.
    """
    logger.info("Starting track pull with cache TTL=3600s")
    logger.info("Pulling tracks for %d playlists", len(playlist_df))
    
    # Initialize progress tracking and rate limiter
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_playlists = len(playlist_df)
    total_tracks = 0
    skipped_playlists = []
    rate_limiter = AdaptiveRateLimiter()
    
    # Process playlists in batches
    tracks_dfs = []
    for i, (playlist_id, playlist_name) in enumerate(zip(playlist_df["id"], playlist_df["name"])):
        try:
            logger.info(f"Processing playlist {i + 1}/{total_playlists}: {playlist_name} ({playlist_id})")
            
            # Time the API call
            start_time = time.time()
            track_data = _sp.playlist_tracks(playlist_id)
            response_time = time.time() - start_time
            
            # Update rate limiter with success
            rate_limiter.update(True, response_time)
            
            if not track_data or "items" not in track_data:
                logger.warning(f"No track data returned for playlist {playlist_name}")
                skipped_playlists.append((playlist_name, playlist_id, "No track data returned"))
                continue
            
            # Filter out podcast episodes and extract track information
            valid_tracks = []
            for item in track_data["items"]:
                if not item or not isinstance(item, dict):
                    continue
                    
                track = item.get("track")
                if not track or not isinstance(track, dict):
                    continue
                    
                # Skip if track is None, is a podcast episode, or has no artists
                if (track.get("type") == "episode" or 
                    not track.get("artists") or 
                    not isinstance(track["artists"], list) or 
                    not track["artists"]):
                    continue
                    
                # Ensure all required fields are present
                if not all(key in track for key in ["id", "name", "artists"]):
                    continue
                    
                # Ensure first artist has required fields
                first_artist = track["artists"][0]
                if not isinstance(first_artist, dict) or not all(key in first_artist for key in ["id", "name"]):
                    continue
                    
                valid_tracks.append(track)
            
            if not valid_tracks:
                logger.info(f"Playlist '{playlist_name}' contains no valid music tracks, skipping")
                skipped_playlists.append((playlist_name, playlist_id, "No valid music tracks"))
                continue
                
            # Create DataFrame from valid tracks
            tracks = pd.DataFrame(valid_tracks)
            num_tracks = len(tracks)
            total_tracks += num_tracks
            logger.info(f"Found {num_tracks} valid music tracks in playlist {playlist_name}")
            
            # Extract required fields
            try:
                tracks["artist_name"] = tracks["artists"].apply(lambda x: x[0]["name"])
                tracks["artist_id"] = tracks["artists"].apply(lambda x: x[0]["id"])
                tracks = tracks[["artist_name", "artist_id", "name", "id"]]
                tracks.rename(columns={"name": "track_name", "id": "track_id"}, inplace=True)
                tracks["playlist_id"] = playlist_id
                tracks_dfs.append(tracks)
            except (KeyError, TypeError, IndexError) as e:
                logger.error(f"Error extracting track data: {e}")
                skipped_playlists.append((playlist_name, playlist_id, f"Data extraction error: {e}"))
                continue
            
            # Update progress
            progress = (i + 1) / total_playlists
            progress_bar.progress(progress)
            status_text.text(f"Processing playlist {i + 1}/{total_playlists}")
            
            logger.debug(f"Current rate limit delay: {rate_limiter.current_delay:.2f}s")
            rate_limiter.delay()
            
        except Exception as e:
            logger.error(f"Error processing playlist {playlist_name} ({playlist_id}): {str(e)}")
            skipped_playlists.append((playlist_name, playlist_id, str(e)))
            # Update rate limiter with failure
            rate_limiter.update(False, 0)
            continue

    progress_bar.empty()
    status_text.empty()
    
    # Report on skipped playlists
    if skipped_playlists:
        logger.warning(f"Skipped {len(skipped_playlists)} playlists:")
        for name, id_, reason in skipped_playlists:
            logger.warning(f"  - {name} ({id_}): {reason}")
    
    if not tracks_dfs:
        logger.warning("No tracks were processed successfully")
        return pd.DataFrame(columns=["artist_name", "artist_id", "track_name", "track_id", "playlist_id"])
    
    result_df = pd.concat(tracks_dfs, ignore_index=True)
    logger.info(f"Successfully processed {total_tracks} tracks from {len(tracks_dfs)} playlists")
    return result_df


def _process_artist_batch(_sp: Spotify, batch_ids: List[str]) -> List[Tuple[str, str, List[str]]]:
    """Helper function to process a batch of artist IDs"""
    if not batch_ids:
        logger.warning("Empty batch of artist IDs received")
        return []
        
    try:
        result = _sp.artists(batch_ids)
        if not result or not isinstance(result, dict) or "artists" not in result:
            logger.error("Invalid response from Spotify API")
            return []
            
        artist_data = result.get("artists", [])
        if not isinstance(artist_data, list):
            logger.error(f"Artists data is not a list: {type(artist_data)}")
            return []
            
        processed_artists = []
        for artist in artist_data:
            try:
                if not artist or not isinstance(artist, dict):
                    logger.warning(f"Invalid artist data: {artist}")
                    continue
                    
                # Check for required fields
                artist_id = artist.get("id")
                artist_name = artist.get("name")
                if not artist_id or not artist_name:
                    logger.warning(f"Missing required fields in artist data: {artist}")
                    continue
                    
                # Ensure genres is a list
                genres = artist.get("genres", [])
                if not isinstance(genres, list):
                    logger.warning(f"Invalid genres data for artist {artist_name}: {genres}")
                    genres = []
                    
                processed_artists.append((
                    artist_id,
                    artist_name,
                    genres
                ))
            except Exception as e:
                logger.error(f"Error processing individual artist: {str(e)}")
                continue
                
        return processed_artists
        
    except Exception as e:
        logger.error(f"Error processing artist batch: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def pull_artist_and_genre(_sp: Spotify, tracks: pd.DataFrame) -> pd.DataFrame:
    """
    Pull artist and genre data using track information with concurrent batch processing.
    Uses thread pooling to speed up API requests while respecting rate limits.
    Handles missing or invalid data gracefully.
    """
    if tracks.empty:
        logger.warning("No tracks provided for artist and genre processing")
        return pd.DataFrame(columns=["artist_id", "artist_name", "genres"])
        
    logger.info("Pulling artist and genre data for %d tracks", len(tracks))
    
    # Get unique artist IDs from tracks and filter out any None or invalid values
    unique_artist_ids = tracks["artist_id"].dropna().unique()
    if len(unique_artist_ids) == 0:
        logger.warning("No valid artist IDs found")
        return pd.DataFrame(columns=["artist_id", "artist_name", "genres"])
        
    total_artists = len(unique_artist_ids)
    logger.info(f"Found {total_artists} unique artists to process")
    
    # Initialize progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    processed_artists_data = []
    
    # Calculate optimal batch parameters
    max_workers = min(10, math.ceil(total_artists / BATCH_SIZE))  # Cap at 10 workers
    logger.info(f"Using {max_workers} workers for parallel processing")
    
    # Process artists in parallel batches
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all batches
        future_to_batch = {}
        for i in range(0, len(unique_artist_ids), BATCH_SIZE):
            batch_ids = unique_artist_ids[i:i + BATCH_SIZE].tolist()
            future = executor.submit(_process_artist_batch, _sp, batch_ids)
            future_to_batch[future] = (i, len(batch_ids))
        
        # Process completed batches
        for future in as_completed(future_to_batch):
            i, batch_size = future_to_batch[future]
            try:
                batch_results = future.result()
                if batch_results:  # Only extend if we got valid results
                    processed_artists_data.extend(batch_results)
                
                # Update progress
                progress = min((i + batch_size) / total_artists, 1.0)
                progress_bar.progress(progress)
                status_text.text(f"Processing artists {i + 1}-{min(i + BATCH_SIZE, total_artists)}/{total_artists}")
                
            except Exception as e:
                logger.error(f"Error processing batch starting at index {i}: {str(e)}")
            
            # Add a small delay between batches to respect rate limits
            time.sleep(API_RATE_LIMIT_DELAY / max_workers)

    progress_bar.empty()
    status_text.empty()
    
    if not processed_artists_data:
        logger.warning("No artist data was processed successfully")
        return pd.DataFrame(columns=["artist_id", "artist_name", "genres"])
    
    result_df = pd.DataFrame(
        processed_artists_data, columns=["artist_id", "artist_name", "genres"]
    )
    logger.info(f"Successfully processed {len(result_df)} artists")
    return result_df


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
    _sp: Spotify, user_id: str, df: pd.DataFrame, genre: str
) -> str:
    """
    Create a new playlist in Spotify and add the selected tracks.

    Args:
        _sp (Spotify): Authenticated Spotify client.
        user_id (str): Spotify user ID.
        df (pd.DataFrame): DataFrame containing track information.
        genre (str): Genre of the playlist.

    Returns:
        str: Snapshot ID of the newly created playlist.
    """
    playlist_name = f"Sample Playlist - {genre}"
    playlist_description = f"A playlist created from selected tracks of genre {genre}."
    new_playlist = _sp.user_playlist_create(
        user_id, playlist_name, description=playlist_description
    )
    playlist_id = new_playlist["id"]
    track_ids = df["track_id"].tolist()
    _sp.user_playlist_add_tracks(user_id, playlist_id, track_ids)
    return playlist_id


@st.cache_data
def process_library_data(_sp: Spotify) -> pd.DataFrame:
    """
    Process the user's Spotify library data by:
    1. Fetching all playlists
    2. Extracting tracks from each playlist
    3. Getting artist and genre information
    4. Combining all data into a single DataFrame

    This is a potentially long-running operation that:
    - Respects Spotify API rate limits
    - Shows progress for each step
    - Caches results to avoid unnecessary reprocessing
    - Handles podcast-only playlists gracefully

    Args:
        _sp (Spotify): Authenticated Spotify client.

    Returns:
        pd.DataFrame: Combined DataFrame containing:
            - Track information (name, id)
            - Artist information (name, id)
            - Genre information
            - Playlist associations
    """
    logger.info("Starting full library data processing")
    playlists_df = get_playlists(_sp)
    tracks_df = pull_tracks(_sp, playlists_df)
    artist_genre_df = pull_artist_and_genre(_sp, tracks_df)
    combined_df = tracks_df.merge(artist_genre_df, on="artist_id", how="left")
    logger.info("Completed full library data processing")
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
