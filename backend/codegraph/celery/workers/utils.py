import multiprocessing

from celery.exceptions import WorkerShutdown

from codegraph.db.engine import SqlEngine, wait_for_db
from codegraph.redis.client import wait_for_redis
from codegraph.utils.logging import get_logger

logger = get_logger()


def initialize_and_wait() -> None:
    SqlEngine.init_engine()

    if not wait_for_redis():
        raise WorkerShutdown
    if not wait_for_db():
        raise WorkerShutdown
    # TODO: wait for index


def configure_multiprocessing() -> None:
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        logger.warning("Could not set multiprocessing start method to 'spawn'")
