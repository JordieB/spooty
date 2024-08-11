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

3. **Add Spotify API Credentials**: Create a `.streamlit/secrets.toml` file in the root directory of your project and add your Spotify API credentials under the `[spotify_app]` section:

   ```ini
   [spotify_app]
   CLIENT_ID = "..."
   CLIENT_SECRET = "..."
   REDIRECT_URI = "http://localhost:8501/"
   ```

   Replace `...` with your actual Spotify API credentials. This setup assumes you are testing locally; if deploying to a different environment, adjust the `REDIRECT_URI` accordingly.

4. **Verify the Installation**: Once the dependencies are installed and the credentials are set, verify that everything is set up correctly by running the main Streamlit application.

   ```bash
   poetry run streamlit run src/spooty/Home.py
   ```

   This command should start the Streamlit server, and you can access the application in your browser at `http://localhost:8501`.

### Best Practices

To ensure smooth development and consistent builds, adhere to the following best practices:

1. **Sync `pyproject.toml` and `poetry.lock`**: If you manually update the `pyproject.toml` file (e.g., adding or updating dependencies manually instead of using `poetry add` or similar), ensure the changes are reflected in the `poetry.lock` file to maintain consistency across environments.

   ```bash
   poetry lock
   poetry install
   ```

2. **Handle Environment Changes**: If you change the Python version or make significant changes to dependencies, consider removing the existing virtual environment and reinstalling it to avoid conflicts or stale dependencies.

   ```bash
   poetry env remove $(poetry env info --path)
   poetry install
   ```

3. **Keep Dependencies Up-to-Date**: Regularly update your dependencies to the latest compatible versions by running:

   ```bash
   poetry update
   ```

   This ensures that your project remains secure and benefits from the latest features and bug fixes.

4. **Version Control**: Always commit your `pyproject.toml` and `poetry.lock` files to version control. This ensures that all team members and deployment environments use the exact same dependency versions.

5. **Testing and Linting**: Regularly run tests and linting tools to maintain code quality.

   ```bash
   poetry run lint
   poetry run test
   ```

6. **Check Before Formatting**: Before running `black`, it's often helpful to run it with the `--check` flag to see what files it will reformat without making changes:

   ```bash
   poetry run black . --check --verbose
   ```

7. **Clear Caches**: If you encounter issues with configuration not being respected, try clearing Poetry's cache to ensure your environment is not overriding your `pyproject.toml` settings:

   ```bash
   poetry cache clear --all pypoetry
   ```

### Project Structure

Here’s an overview of the project structure to help you navigate the codebase:

```
spooty/
│
├── .streamlit/
│   ├── config.toml        # Streamlit configuration
│   ├── secrets.toml       # Secrets like API keys (should not be committed)
│
├── dev_tools/
│   ├── __init__.py        # Package marker
│   ├── lint.py            # Linting and code quality checks
│
├── spooty/
│   ├── __init__.py        # Main package marker
│   ├── Home.py            # Main entry point for the Streamlit app
│   ├── pages/             # Subpackage for additional pages in the Streamlit app
│   │   ├── __init__.py
│   │   ├── backlog_sampler.py
│   │   ├── playlist_privacy.py
│   └── utils/
│       ├── __init__.py
│       ├── spotify_helpers.py
```
