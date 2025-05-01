import streamlit as st
import pandas as pd
from typing import List, Optional

from spooty.utils.spotify_helpers import create_sample_playlist, process_library_data
from spooty.utils.logging_setup import get_logger

# Get logger for this module
logger = get_logger(__name__)

def flatten_genres(genres_list: List[str]) -> str:
    """Convert a list of genres into a single string for searching."""
    return " ".join(genres_list) if genres_list else ""

def validate_dataframe(df: pd.DataFrame) -> Optional[str]:
    """
    Validate the DataFrame has all required columns and data.
    Returns an error message if validation fails, None if successful.
    """
    required_columns = ["track_id", "track_name", "artist_name", "genres"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return f"Missing required columns: {', '.join(missing_columns)}"
    
    if df.empty:
        return "No music data found in your library"
        
    if df["genres"].isna().all():
        return "No genre information found in your library"
        
    return None

try:
    # Init Spotify Client
    sp = st.session_state.get("sp")
    if not sp:
        st.error("Please connect to Spotify first.")
        st.stop()

    # Show loading message while fetching data
    with st.spinner("Loading your music library..."):
        # Grab user_id, used for creating playlists
        try:
            user_id = sp.me()["id"]
        except Exception as e:
            logger.error(f"Failed to get user ID: {str(e)}")
            st.error(f"Failed to get user ID: {str(e)}")
            st.stop()

        # Pull down playlist, track, and genre data (uses cache if possible)
        try:
            df = process_library_data(sp)
            
            # Validate the DataFrame
            error_msg = validate_dataframe(df)
            if error_msg:
                logger.error(f"Data validation failed: {error_msg}")
                st.error(error_msg)
                st.stop()
                
        except Exception as e:
            logger.error(f"Failed to process library data: {str(e)}")
            st.error(f"Failed to load your music library: {str(e)}")
            st.stop()

    # Process genres
    df['genres_str'] = df['genres'].apply(flatten_genres)
    available_genres = sorted(list(set(
        genre for genres in df['genres'].dropna() 
        for genre in genres if genre
    )))

    if not available_genres:
        logger.warning("No genres found in library")
        st.warning("No genres found in your library.")
        st.stop()

    # Allow user input
    st.subheader("1. Select a Genre")
    selected_genre = st.selectbox(
        "Choose a genre from your library:", 
        options=available_genres,
        index=0
    )

    st.subheader("2. Choose Sample Size")
    # Filter data based on selected genre to show available songs
    try:
        genre_df = df[df['genres_str'].str.contains(selected_genre, na=False, case=False)]
        unique_tracks = genre_df.drop_duplicates(subset="track_id")
        available_songs = len(unique_tracks)

        if available_songs == 0:
            logger.warning(f"No songs found for genre: {selected_genre}")
            st.warning(f"No songs found in the '{selected_genre}' genre.")
            st.stop()

        st.info(f"Found {available_songs} unique songs in the '{selected_genre}' genre.")
        
        selected_sample_size = int(st.number_input(
            "How many songs would you like to sample?", 
            min_value=1,
            max_value=available_songs,
            value=min(10, available_songs)
        ))

        # Sample tracks
        display_df = unique_tracks.sample(
            n=min(selected_sample_size, available_songs), 
            replace=False
        ).reset_index(drop=True)

        # Add re-roll button with feedback
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🎲 Re-Roll"):
                st.toast("Rolling new songs...", icon="🎲")
                st.rerun()
        
        # Show user track names with artist information
        st.subheader("3. Preview Selected Songs")
        st.dataframe(
            display_df[["track_name", "artist_name"]].rename(
                columns={"track_name": "Track", "artist_name": "Artist"}
            ),
            use_container_width=True,
            hide_index=True
        )

        # Save playlist button
        st.subheader("4. Save as Playlist")
        if st.button("💾 Save Sample as Playlist"):
            with st.spinner("Creating playlist..."):
                try:
                    snapshot_id = create_sample_playlist(sp, user_id, display_df, selected_genre)
                    st.success("✅ Playlist created successfully!")
                    
                    # Get the playlist URL
                    playlist = sp.playlist(snapshot_id)
                    st.markdown(
                        f"[Open Playlist in Spotify]({playlist['external_urls']['spotify']})"
                    )
                except Exception as e:
                    logger.error(f"Failed to create playlist: {str(e)}")
                    st.error(f"Failed to create playlist: {str(e)}")

    except Exception as e:
        logger.error(f"Error processing genre data: {str(e)}")
        st.error(f"An error occurred while processing genre data: {str(e)}")

except Exception as e:
    logger.error(f"An unexpected error occurred: {str(e)}")
    st.error(f"An unexpected error occurred: {str(e)}")
