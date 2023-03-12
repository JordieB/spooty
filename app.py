import streamlit as st
import os
import spotipy
from utils import create_spotipy_client

sp = create_spotipy_client()
sp.write(True)