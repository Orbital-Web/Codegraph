# CodeGraph

CodeGraph is a CLI-based AI coding assistant that can index your workspace to answer questions about the codebase and fix/write code. It uses an agentic AI flow with access to a variety of MCP tools plus a custom graph (codegraph) of function/classes/modules and their relationships to effectively answer user queries.

The codegraph currently only supports `Python`, although there are other tools that allow the agent to still find relevent information to answer questions. The supported languages for semantic lookup will depend on the embedding model being used. The default model, [codet5p-110m-embedding](https://huggingface.co/Salesforce/codet5p-110m-embedding) supports `Python`, `C`, `C++`, `Go`, `Java`, `JavaScript`, `PHP`, and `Ruby`.

The project uses `LangGraph` for the agent, `Postgres` for the codegraph and other tables (+`Alembic` for versioning), and `Chroma` for the vectorstore.
<!-- + LiteLLM for managing different models -->

<!-- TODO: insert GIF/video here -->

## Features:
<!-- list overall, tools, cli, and indexing functionalities -->
<!-- maybe talk about tests + github actions -->
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

<!-- TODO: add instructions on the .env file and required environmental variables -->
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

<!-- TODO: add known limitations and potential future features -->