import os
import subprocess
import threading
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


def monitor_process(process_name: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None

    for line in process.stdout:
        print(f"{process_name.ljust(16)} {line}")


if __name__ == "__main__":
    workers = {
        "Celery Primary": [
            "celery",
            "-A",
            "codegraph.celery.workers.primary",
            "worker",
            "--pool=threads",
            "--concurrency=4",
            "--prefetch-multiplier=1",
            "--loglevel=INFO",
            "-Q",
            "celery",
        ],
        "Celery Indexing": [
            "celery",
            "-A",
            "codegraph.celery.workers.indexing",
            "worker",
            "--pool=threads",
            "--concurrency=4",
            "--prefetch-multiplier=1",
            "--loglevel=INFO",
            "-Q",
            "indexing",
        ],
        "Celery Beat": [
            "celery",
            "-A",
            "codegraph.celery.workers.beat",
            "beat",
            "--loglevel=INFO",
        ],
    }

    processes: list[subprocess.Popen[str]] = []

    for worker_name, args in workers.items():
        process = subprocess.Popen(
            args,
            cwd=CWD,
            env=ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
        )
        processes.append(process)

        monitor = threading.Thread(target=monitor_process, args=(worker_name, process), daemon=True)
        monitor.start()

    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait()
