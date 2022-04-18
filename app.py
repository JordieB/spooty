import streamlit as st
import pandas as pd
import uuid
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def pull_playlists():
    # Init a list to hold playlist data
    all_pls = []
    # Pull down first page of current user's playlists
    pl = spotify.current_user_playlists()
    
    # Loop through to pull the rest of the pages
    while pl:
        # Add the playlist to the collection
        all_pls.append(pl)
        # If there is another page
        if pl['next']:
            # Pull it down
            pl = spotify.next(pl)
        else:
            # Else stop on the next iteration
            pl = None
    
    # Make a playlist dataframe
    dfs = []
    for pl_dict in all_pls:
        dfs.append(pd.DataFrame(pl_dict['items']))
    playlists = pd.concat(dfs)
    playlists.reset_index(drop=True, inplace=True)
    
    # Only grab backlog playlists (lack of folder dims) via prefix
    playlists = playlists.loc[playlists.loc[:,'name'].str[:3] == 'b -',:]
    # Grab only my playlists
    playlists = playlists.loc[playlists.loc[:,'owner'].apply(lambda x: x.get('display_name')) == 'Jordie',:]
    # Grab only my non-collab playlists
    playlists = playlists.loc[~playlists.loc[:,'collaborative'],:]
    # Grab only the columns I want
    playlists = playlists.reindex(columns=['id','name'])
    # Prefix column names in prep for joining track data
    playlists.columns = ['playlist_' + col for col in playlists.columns]
    
    return playlists

def pull_tracks(playlist_df):
    # Pull track data responses
    playlist_ids = playlist_df.playlist_id.values
    track_data = []
    for playlist_id in playlist_ids:
        track_data_dict = spotify.playlist_tracks(playlist_id)
        track_data_dict['playlist_id'] = playlist_id
        track_data.append(track_data_dict)
        time.sleep(1)
    
    # Pull data out of responses
    tracks_dfs = []
    for _tracks in track_data:
        tracks = pd.DataFrame(_t['track'] for _t in _tracks['items'])
        tracks.loc[:,'artist_name'] = tracks.loc[:,'artists'].apply(lambda x: x[0].get('name', np.nan))
        # For getting artist genres later
        tracks.loc[:,'artist_id'] = tracks.loc[:,'artists'].apply(lambda x: x[0].get('id', np.nan))
        tracks = tracks.reindex(columns=['artist_name','artist_id','name','id'])
        tracks = tracks.rename(columns={'name':'track_name','id':'track_id'})
        tracks.loc[:,'playlist_id'] = _tracks['playlist_id']
        tracks.reset_index(drop=True, inplace=True)

        tracks_dfs.append(tracks)

    # Create tracks df
    tracks = pd.concat(tracks_dfs, sort=False)
    tracks.reset_index(drop=True, inplace=True)
    
    return tracks

def pull_artist_and_genre(tracks):
    # Pull raw artist data using only unique artists
    unique_artist_ids = tracks.artist_id.unique()
    raw_artist_data = []

    for i in range(0,len(unique_artist_ids),50):
        payload = unique_artist_ids[i:(i+50)]
        artist_data = spotify.artists(payload)
        raw_artist_data.append(artist_data)
        time.sleep(1)
    
    # Process the data
    processed_artists_data = []
    
    for artist_data in raw_artist_data:
        for artist in artist_data['artists']:
            genres = artist['genres']
            name = artist['name']
            _id = artist['id']
            processed_artists_data.append([_id, name, genres])

    # Create df from processed data
    artists = pd.DataFrame(processed_artists_data,columns=['artist_id','artist_name','genres'])
    
    return artists

def refresh_data():
    # Pull data
    playlists = pull_playlists()
    tracks = pull_tracks(playlists)
    artists = pull_artist_and_genre(tracks)
    
    # Combine and clean
    combined = playlists.merge(tracks,on='playlist_id',how='left')
    combined = combined.merge(artists, on='artist_id', how='left')
    combined = combined.explode('genres')
    combined = combined.drop(columns=['artist_name_y'])
    combined = combined.rename(columns={'artist_name_x':'artist_name'})
    combined.reset_index(drop=True, inplace=True)
    
    return combined

def create_playlist(user_id, df, selected_genre):
    playlist_name = selected_genre + '_' + str(uuid.uuid4())
    is_public = False
    # Create playlist
    new_playlist = spotify.user_playlist_create(user_id, playlist_name, is_public)
    # Add playlist
    snapshot_id = spotify.playlist_add_items(new_playlist['id'], df.track_id.values)

    return snapshot_id

USERNAME = st.secrets['USERNAME']
CLIENT_ID = st.secrets['CLIENT_ID']
CLIENT_SECRET = st.secrets['CLIENT_SECRET']
REFRESH_TOKEN = st.secrets['REFRESH_TOKEN']
REDIRECT_URI = st.secrets['REDIRECT_URI']
SCOPE = st.secrets['REFRESH_TOKEN']
user_id = st.secrets['user_id']

auth_manager = SpotifyOAuth(
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    open_browser=False,  # False to get URL, True to enter it
    scope=SCOPE,
    username=USERNAME
)

refresh = auth_manager.refresh_access_token(REFRESH_TOKEN)
spotify = spotipy.Spotify(auth=refresh['access_token'])

if st.button('Refresh Data'):
    df = refresh_data()
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
    snapshot_id = create_playlist(user_id, display_df, selected_genre)
    st.write(f'Snapshot ID: {snapshot_id}')
