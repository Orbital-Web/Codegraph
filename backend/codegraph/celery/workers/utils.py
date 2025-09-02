import multiprocessing

from celery.exceptions import WorkerShutdown

from codegraph.utils.configuration import initialize_and_wait_for_services
from codegraph.utils.logging import get_logger

logger = get_logger()


def initialize_and_wait() -> None:
    ready = initialize_and_wait_for_services()
    if not ready:
        raise WorkerShutdown


def configure_multiprocessing() -> None:
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        logger.warning("Could not set multiprocessing start method to 'spawn'")
