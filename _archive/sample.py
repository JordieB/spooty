import streamlit as st
import pandas as pd
import uuid
import utils

def app():
    spotify = utils.init_spotipy()

    if st.button('Refresh Data'):
        df = utils.refresh_data()
        df.to_feather('data.feather')
        last_refresh = pd.Timestamp.now()
        st.write(f'Last refreshed @ {last_refresh}')

    df = pd.read_feather('data.feather')

    selected_genre = st.selectbox(
        'Select a genre:',
        df.genres.sort_values().unique().tolist()
    )

    selected_sample_size = st.number_input('How many songs?', min_value=1)

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

    display_df = sample_df.sample(n=used_sample_size, replace=False)

    st.dataframe(display_df.loc[:,['track_name']])

    if st.button('Create Playlist Based on This Sample'):
        snapshot_id = utils.create_playlist(user_id, display_df, selected_genre)
        st.write(f'Snapshot ID: {snapshot_id}')
