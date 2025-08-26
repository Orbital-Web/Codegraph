from typing import Any

from celery import Celery
from celery.exceptions import WorkerShutdown
from celery.signals import worker_init

from codegraph.db.engine import SqlEngine, wait_for_db
from codegraph.redis.client import wait_for_redis
from codegraph.utils.logging import get_logger

logger = get_logger(__name__)


celery_app = Celery(__name__)
celery_app.config_from_object("codegraph.celery.configs.shared_default")


@worker_init.connect
def on_worker_init(sender: Celery, **kwargs: Any) -> None:
    logger.info("primary worker init")

    SqlEngine.init_engine()

    if not wait_for_redis():
        raise WorkerShutdown
    if not wait_for_db():
        raise WorkerShutdown
    # TODO: wait for index


celery_app.autodiscover_tasks(
    [
        "codegraph.celery.tasks.indexing",
    ]
)
