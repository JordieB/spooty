import streamlit as st

from src.spooty.utils.spotify_helpers import create_playlist, refresh_data

# Init Spotify Client
sp = st.session_state["sp"]

# Grab user_id, used for creating playlists
user_id = sp.me()["id"]

# Pull down playlist, track, and genre data (uses cache if possible)
df = refresh_data(sp)

# Allow user input
selected_genre = st.selectbox(
    "Select a genre:", df.genres.sort_values().unique(), index=0
)
selected_sample_size = int(st.number_input("How many songs?", min_value=1))

# Filter data based on user input
if selected_genre is not None:
    sample_df = df.loc[df["genres"].str.contains(selected_genre, na=False), :]
else:
    sample_df = df.copy()  # Handle case where genre is not selected
sample_df = sample_df.drop_duplicates(subset="track_id")
pop_size = sample_df.shape[0]

# Pull as many records as possible when sample size is too high
if selected_sample_size >= pop_size:
    used_sample_size = pop_size
    st.write("## Used all available songs")
else:
    used_sample_size = selected_sample_size
    st.write("## Used a sample of available songs")
display_df = sample_df.sample(n=used_sample_size, replace=False).reset_index(drop=True)

# Add re-roll button
if st.button("Re-Roll"):
    st.rerun()

# Show user track names
st.dataframe(display_df.loc[:, ["track_name"]], use_container_width=True)

# If pressed, create playlists from this sample
if st.button("Save Sample as Playlist"):
    if selected_genre is not None:
        snapshot_id = create_playlist(sp, user_id, display_df, selected_genre)
        st.write(f"Snapshot ID: {snapshot_id}")
    else:
        st.error("Please select a genre before saving the playlist.")
