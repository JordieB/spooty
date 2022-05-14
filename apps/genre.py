import streamlit as st
import pandas as pd

def app():
    df = pd.read_feather('data.feather')
    df = df.loc[:,['artist_name','genres']].drop_duplicates().reset_index()

    selected_artist = st.selectbox(
        'Select an artist:',
        df.artist_name.sort_values().unique().tolist()
    )

    desired_genres = df.loc[df.loc[:,'artist_name'] == selected_artist, ['genres']]
    st.dataframe(desired_genres)
