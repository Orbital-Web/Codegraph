# CodeGraph

TODO: Description

## Features:
- TODO: 1
- TODO: 2

## Quick Setup
1. Start by installing Python 3.13.3 and Docker

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
   Otherwise, # TODO: