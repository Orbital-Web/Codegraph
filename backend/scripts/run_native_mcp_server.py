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
    mcp_server = ["python", "codegraph/tools/server.py"]

    mcp_server_process = subprocess.Popen(mcp_server, cwd=CWD, env=ENV)

    try:
        mcp_server_process.wait()
    except KeyboardInterrupt:
        mcp_server_process.terminate()
        mcp_server_process.wait()
