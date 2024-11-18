import streamlit as st
from src.spooty.utils.spotify_helpers import get_playlists, set_playlist_public_status

def main():
    st.title("Spooty's Playlist Privacy Manager")

    sp = st.session_state.get("sp")
    if not sp:
        st.error("Spotify client not initialized.")
        return

    playlists = get_playlists(sp)
    playlist_names = playlists["name"].values
    playlist_ids = playlists["id"].values

    if playlists.empty:
        st.write("No playlists found!")
        return

    # Inject custom CSS to limit the height of the multi-select dropdown
    st.markdown(
        """
        <style>
        div[data-baseweb="select"] {
            max-height: 300px;
            overflow: auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Checkbox to select/deselect all playlists
    select_all = st.checkbox("Select/Deselect All", key="select_all")

    # Display buttons with appropriate states
    col1, col2 = st.columns(2)
    with col1:
        make_private = st.button("Make Selected Playlists Private", key="private")
    with col2:
        make_public = st.button("Make Selected Playlists Public", key="public")

    # Container for the multi-select widget
    container = st.container()
    selected_playlists = container.multiselect(
        "Selected Playlists",
        options=playlist_names,
        default=playlist_names if select_all else [],
    )

    # Process button actions after selections have been made
    if make_private:
        for pl_id, pl_name in zip(playlist_ids, playlist_names):
            if pl_name in selected_playlists:
                set_playlist_public_status(sp, pl_id, pl_name, False)

    if make_public:
        for pl_id, pl_name in zip(playlist_ids, playlist_names):
            if pl_name in selected_playlists:
                set_playlist_public_status(sp, pl_id, pl_name, True)

if __name__ == "__main__":
    main()
