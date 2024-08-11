# Spooty

## Overview

**Spooty** is a Python-based application designed to interact with the Spotify API, providing users with features such as playlist management, privacy controls, and more. Built using Streamlit for the frontend and Spotipy for Spotify integration, Spooty offers a clean and user-friendly interface for managing Spotify playlists and exploring music data.

## Build Guide

### Requirements

Before you can build and run Spooty, ensure you have the following tools installed on your system:

1. **Python**: Ensure that Python 3.11 or a compatible version is installed. You can download it from [python.org](https://www.python.org/downloads/).
   
2. **Poetry**: This project uses Poetry for dependency management. Install Poetry by following the instructions on [Poetry's official website](https://python-poetry.org/docs/#installation).

### Steps to Build

Follow these steps to set up the project and get Spooty running on your local machine:

1. **Clone the Repository**: First, clone the Spooty repository to your local machine.
   
   ```bash
   git clone https://github.com/JordieB/spooty.git
   cd spooty
   ```

2. **Install Dependencies**: Run the following command to install all necessary dependencies. Poetry will create a virtual environment in the project directory (if configured) and install the dependencies listed in `pyproject.toml`.

   ```bash
   poetry install
   ```

3. **Add Spotify API Credentials**: Add your Spotify API credentials to the `.streamlit/secrets.toml` file. Use the following format:

   ```ini
   [spotify_app]
   CLIENT_ID = "..."
   CLIENT_SECRET = "..."
   REDIRECT_URI = "http://localhost:8501/"
   ```

4. **Verify the Installation**: Once the dependencies are installed, verify that everything is set up correctly by running the main Streamlit application.

   ```bash
   poetry run streamlit run src/spooty/Home.py
   ```

   This command should start the Streamlit server, and you can access the application in your browser at `http://localhost:8501`.

### Project Structure

Here’s an overview of the project structure to help you navigate the codebase:

```
spooty/
│
├── .streamlit/
│   ├── config.toml        # Streamlit configuration
│   ├── secrets.toml       # Secrets like API keys (should not be committed)
│
├── src/
│   ├── spooty/
│   │   ├── __init__.py    # Main package marker
│   │   ├── Home.py        # Main entry point for the Streamlit app
│   │   ├── pages/         # Subpackage for additional pages in the Streamlit app
│   │   │   ├── __init__.py
│   │   │   ├── 1_Backlog_Sampler.py
│   │   │   ├── [...]
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── spotify_helpers.py
│   │
│   └── tests/             # Test files
│       ├── __init__.py
│
├── .gitignore             # Git ignore file
├── LICENSE                # Project license
├── logging.conf           # Python Logging configuration
├── Makefile               # Makefile for project management
├── poetry.lock            # Poetry lock file
├── pyproject.toml         # Poetry configuration
└── README.md              # Project README
```
