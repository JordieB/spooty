import streamlit as st
from utils import refresh_data, create_playlist

# Init Spotify Client
sp = st.session_state['sp']
# Grab user_id, used for creating playlists
user_id = sp.me()['id']
# Pull down playlist, track, and genre data (uses cache if possible)
df = refresh_data(sp)

# Allow user input
selected_genre = st.selectbox(
    'Select a genre:',
    df.genres.sort_values().unique()
)
selected_sample_size = st.number_input('How many songs?',
                                       min_value=1)

# Filter data based on user input
sample_df = df.loc[df.loc[:,'genres'].str.contains(selected_genre, na=False),:]
sample_df = sample_df.drop_duplicates(subset='track_id')
pop_size = sample_df.shape[0]

# Pull as many records as possible when sample size is too high
if selected_sample_size >= pop_size:
    used_sample_size = pop_size
    st.write('## Used all available songs')
else:
    used_sample_size = selected_sample_size
    st.write('## Used a sample of available songs')
display_df = sample_df.sample(n=used_sample_size, replace=False).reset_index(drop=True)

# Add re-roll button
if st.button('Re-Roll'):
    st.experimental_rerun()

# Show user track names
st.dataframe(display_df.loc[:,['track_name']], use_container_width=True)

# If pressed, create playlists from this sample
if st.button('Save Sample as Playlist'):
    snapshot_id = create_playlist(sp, user_id, display_df, selected_genre)
    st.write(f'Snapshot ID: {snapshot_id}')