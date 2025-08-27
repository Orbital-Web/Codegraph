from typing import Any

from celery import Celery
from celery.signals import celeryd_init, worker_init

from codegraph.celery.workers.utils import configure_multiprocessing, initialize_and_wait
from codegraph.utils.logging import get_logger

logger = get_logger(__name__)


celery_app = Celery(__name__)
celery_app.config_from_object("codegraph.celery.configs.shared_default")


@celeryd_init.connect
def on_celeryd_init(sender: Celery, **kwargs: Any) -> None:
    logger.info("indexing celeryd init")
    configure_multiprocessing()


@worker_init.connect
def on_worker_init(sender: Celery, **kwargs: Any) -> None:
    logger.info("indexing worker init")
    initialize_and_wait()


celery_app.autodiscover_tasks(
    [
        "codegraph.celery.tasks.indexing",
    ]
)
