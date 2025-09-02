from pathlib import Path

from alembic import command
from alembic.config import Config
from codegraph.index.chroma import ChromaIndex
from codegraph.utils.logging import get_logger

logger = get_logger()


def reset_db() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def reset_index() -> None:
    ChromaIndex.wipe_collection()


def reset_all() -> None:
    logger.info("Resetting database")
    reset_db()
    logger.info("Resetting index")
    reset_index()
