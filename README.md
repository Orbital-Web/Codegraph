# CodeGraph

TODO: Description

## Features:
- TODO: 1
- TODO: 2

## Quick Setup
1. Start by installing Python 3.13.3 and Docker (may work with Python 3.11/3.12, though not tested)

2. Navigate to `/deployment` and start up the required containers

   ```bash
   docker compose -f docker/docker-compose-dev.yml -p codegraph-stack up -d
   ```

2. Navigate to `/backend`, create and activate the virtual environment, and download the requirements:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # for unix
   .\.venv\Scripts\activate   # for windows
   pip install -r requirements.txt
   ```

3. If you are using VSCode and want to run a debug instance, go to `Run` and launch `CodeGraph CLI`.

   Otherwise, make sure you are in `/backend` and run

   ```bash
   python -m dotenv -f ../.vscode/.env run python main.py
   ```

4. Follow the instructions in the CLI to create a new project, index it, and chat with the AI agent

5. (Optional) If you plan on contributing to the codebase, you should run

   ```
   pip install pre-commit
   pre-commit install
   ```

   So that the next time you commit, it automatically takes care of linting.