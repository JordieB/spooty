import streamlit as st
from multiapp import MultiApp
from apps import sample, genre

app = MultiApp()

app.add_app('Sample Backlog', sample.app)
app.add_app('Genre Search', genre.app)

app.run()
