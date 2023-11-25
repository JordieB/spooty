from time import sleep
from uuid import uuid4
from pandas import DataFrame, concat
import numpy as np
import streamlit as st
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

def create_spotipy_client():

    # SECRETS
    CLIENT_ID = st.secrets.spotify_app['CLIENT_ID']
    CLIENT_SECRET = st.secrets.spotify_app['CLIENT_SECRET']
    REDIRECT_URI = st.secrets.spotify_app['REDIRECT_URI']
    scopes = [
        'playlist-modify-private',
        'playlist-read-private',
        'user-library-read'
    ]
    SCOPE = ' '.join(scopes)

    auth_manager = SpotifyOAuth(
        CLIENT_ID,
        CLIENT_SECRET,
        REDIRECT_URI,
        open_browser=True,
        scope=SCOPE
    )

    # Init var for response code
    code = ''
    # Init var for user token
    token_info = ''
    # Init var for spotify client
    spotify = None
    # If user return to this page via redirect from Spotify OAuth,
    # Grab response code
    if 'code' in st.experimental_get_query_params():
        code = st.experimental_get_query_params()['code']
    # If response code is found:
    if code:
        # Get token
        token_info = auth_manager.get_access_token(code=code)
    else:
        # Attempt to grab a cached token
        token_info = auth_manager.get_cached_token()

    # If there was no cached token,
    if not token_info:
        # Get the auth_url
        auth_url = auth_manager.get_authorize_url()
        # Ask the user to start auth process
        st.warning('To Use App, You Need to Authorize Access to Your Spotify Data')
        if st.button(label='Authorize Access to Your Spotify Data',
                    key='auth_but'):
            # If clicked, display auth URL
            st.write('Click the link to Spotify below to open a new tab and authorize this app.')
            st.markdown(f"{auth_url}")
    # Cached token found
    else:
        # Create spotify client
        spotify = Spotify(auth=token_info['access_token'])
        

    if spotify:
        return spotify
    else:
        pass

@st.cache_data
def pull_playlists(_spotify):
    # Init a list to hold playlist data
    all_pls = []
    # Pull down first page of current user's playlists
    pl = _spotify.current_user_playlists()
    
    # Loop through to pull the rest of the pages
    while pl:
        # Add the playlist to the collection
        all_pls.append(pl)
        # If there is another page
        if pl['next']:
            # Pull it down
            pl = _spotify.next(pl)
        else:
            # Else stop on the next iteration
            pl = None
    
    # Make a playlist dataframe
    dfs = []
    for pl_dict in all_pls:
        dfs.append(DataFrame(pl_dict['items']))
    playlists = concat(dfs)
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

@st.cache_data
def pull_tracks(_spotify, playlist_df):
    # Pull track data responses
    playlist_ids = playlist_df.playlist_id.values
    track_data = []
    for playlist_id in playlist_ids:
        track_data_dict = _spotify.playlist_tracks(playlist_id)
        track_data_dict['playlist_id'] = playlist_id
        track_data.append(track_data_dict)
        sleep(1)
    
    # Pull data out of responses
    tracks_dfs = []
    for _tracks in track_data:
        tracks = DataFrame(_t['track'] for _t in _tracks['items'])
        tracks.loc[:,'artist_name'] = tracks.loc[:,'artists'].apply(lambda x: x[0].get('name', np.nan))
        # For getting artist genres later
        tracks.loc[:,'artist_id'] = tracks.loc[:,'artists'].apply(lambda x: x[0].get('id', np.nan))
        tracks = tracks.reindex(columns=['artist_name','artist_id','name','id'])
        tracks = tracks.rename(columns={'name':'track_name','id':'track_id'})
        tracks.loc[:,'playlist_id'] = _tracks['playlist_id']
        tracks.reset_index(drop=True, inplace=True)

        tracks_dfs.append(tracks)

    # Create tracks df
    tracks = concat(tracks_dfs, sort=False)
    tracks.reset_index(drop=True, inplace=True)
    
    return tracks

@st.cache_data
def pull_artist_and_genre(_spotify, tracks):
    # Pull raw artist data using only unique artists
    unique_artist_ids = tracks.artist_id.unique()
    raw_artist_data = []

    for i in range(0,len(unique_artist_ids),50):
        payload = unique_artist_ids[i:(i+50)]
        artist_data = _spotify.artists(payload)
        raw_artist_data.append(artist_data)
        sleep(1)
    
    # Process the data
    processed_artists_data = []
    
    for artist_data in raw_artist_data:
        for artist in artist_data['artists']:
            genres = artist['genres']
            name = artist['name']
            _id = artist['id']
            processed_artists_data.append([_id, name, genres])

    # Create df from processed data
    artists = DataFrame(processed_artists_data,columns=['artist_id','artist_name','genres'])
    
    return artists

@st.cache_data
def refresh_data(_spotify):
    # Pull data
    playlists = pull_playlists(_spotify, )
    tracks = pull_tracks(_spotify, playlists)
    artists = pull_artist_and_genre(_spotify, tracks)
    
    # Combine and clean
    combined = playlists.merge(tracks,on='playlist_id',how='left')
    combined = combined.merge(artists, on='artist_id', how='left')
    combined = combined.explode('genres')
    combined = combined.drop(columns=['artist_name_y'])
    combined = combined.rename(columns={'artist_name_x':'artist_name'})
    combined.reset_index(drop=True, inplace=True)
    
    return combined

def create_playlist(_spotify, user_id, df, selected_genre, is_public=False):

    playlist_name = selected_genre + '_' + str(uuid4())
    # Create playlist
    new_playlist = _spotify.user_playlist_create(user_id, playlist_name, is_public)
    # Add playlist
    snapshot_id = _spotify.playlist_add_items(new_playlist['id'], df.track_id.values)

    return snapshot_id