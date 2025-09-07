import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".vscode" / ".env"
if not ENV_PATH.exists():
    raise FileNotFoundError(f"Environment file not found at {ENV_PATH}")
load_dotenv(ENV_PATH)

CWD = ROOT_DIR / "backend"

ENV = os.environ.copy()
ENV.update(
    {
        "LOG_LEVEL": "DEBUG",
        "PYTHONBUFFERED": "1",
        "PYTHONPATH": ".",
    }
)

if __name__ == "__main__":
    model_server = [
        "uvicorn",
        "codegraph.model_service.server:app",
        "--host",
        "localhost",
        "--port",
        "9000",
        "--workers",
        "1",
    ]

    model_server_process = subprocess.Popen(model_server, cwd=CWD, env=ENV)

    try:
        model_server_process.wait()
    except KeyboardInterrupt:
        model_server_process.terminate()
        model_server_process.wait()
