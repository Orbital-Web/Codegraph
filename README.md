# CodeGraph

CodeGraph is a CLI-based AI coding assistant that can index your workspace to answer questions about the codebase and fix/write code. It uses an agentic AI flow with access to a variety of MCP tools plus a custom graph (codegraph) of function/classes/modules and their relationships to effectively answer user queries.

The codegraph currently only supports `Python`, although there are other tools that allow the agent to still find relevent information to answer questions. The supported languages for semantic lookup will depend on the embedding model being used. The default model, [codet5p-110m-embedding](https://huggingface.co/Salesforce/codet5p-110m-embedding) supports `Python`, `C`, `C++`, `Go`, `Java`, `JavaScript`, `PHP`, and `Ruby`.

The project uses `LangGraph` for the agent, `Postgres` for the codegraph and other tables (+`Alembic` for versioning), `Chroma` for the vectorstore, `Redis` for the cache, and `Celery` for the background tasks.
<!-- + LiteLLM for managing different models -->

<!-- TODO: insert GIF/video here -->

## Features
<!-- list overall, tools, cli, and indexing functionalities -->
<!-- maybe talk about tests + github actions -->
- TODO: 1
- TODO: 2

## Quick Setup

1. Start by installing Python 3.13.3 and Docker (may work with earlier Python versions, though not tested)

2. Navigate to `/.vscode` and copy the contents of `env_template.txt` into `.env`, and `launch_template.txt` into `launch.json`.

   Note that you will still need to do this even if you are not using VSCode, though it is highly recommended that you have VSCode installed for the later steps.
   <!-- TODO: add instructions on the .env file and required environmental variables -->

3. Navigate to `/deployment` and start up the required containers

   ```bash
   docker compose -f docker/docker-compose-dev.yml -p codegraph-stack up -d
   ```

4. Navigate to `/backend`, create and activate the virtual environment, and install the requirements:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # for unix
   .\.venv\Scripts\activate   # for windows
   pip install -r requirements.txt
   ```

   *Note that because this project uses Celery, it may not work for Windows devices. Windows users are recommended to run this project in [WSL](https://learn.microsoft.com/en-us/windows/wsl/install)*

5. Still in `/backend`, you will need to run the DB migrations for postgres when running CodeGraph for the first time or if the DB models change, by running:

   ```bash
   alembic upgrade head
   ```

6. If you are using VSCode and want to run a debug instance, go to `Run` and launch `CodeGraph (all)`. If you get a module not found error, make sure you've set the Python interpreter path in VSCode to the one in `.venv/bin/python`.

   Otherwise, if you are not using VSCode, make sure you are in `/backend` and run each of these commands in a separate terminal:

   <!-- TODO: create a script to start all celery workers -->
   ```bash
   # start celery workers
   python -m dotenv -f ../.vscode/.env run celery -A codegraph.celery.workers.primary worker --pool=threads --concurrency=4 --prefetch-multiplier=1 --loglevel=INFO -Q celery
   python -m dotenv -f ../.vscode/.env run celery -A codegraph.celery.workers.indexing worker --pool=threads --concurrency=4 --prefetch-multiplier=1 --loglevel=INFO -Q indexing
   python -m dotenv -f ../.vscode/.env run celery -A codegraph.celery.workers.beat beat --loglevel=INFO

   # start codegraph cli
   python -m dotenv -f ../.vscode/.env run python main.py
   ```

7. Follow the instructions in the CLI to create a new project, index it, and chat with the AI agent

8. (Optional) If you plan on contributing to the codebase, you should run

   ```bash
   pip install pre-commit
   pre-commit install
   ```

   So that the next time you commit, it automatically takes care of linting.

<!-- TODO: add known limitations and potential future features -->