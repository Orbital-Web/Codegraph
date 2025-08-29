from datetime import timedelta
from typing import Any

from celery import Celery
from celery.exceptions import WorkerShutdown
from celery.signals import beat_init

from codegraph.celery.constants import (
    CELERY_BEAT_EXPIRES_DEFAULT,
    CeleryPriority,
    CeleryQueue,
    CeleryTask,
)
from codegraph.redis.client import wait_for_redis
from codegraph.utils.logging import get_logger

logger = get_logger()

celery_app = Celery(__name__)
celery_app.config_from_object("codegraph.celery.configs.shared_default")


@beat_init.connect
def on_beat_init(sender: Any, **kwargs: Any) -> None:
    logger.info("beat init")

    if not wait_for_redis():
        raise WorkerShutdown


celery_app.conf.beat_schedule = {
    "queue-indexing": {
        "task": CeleryTask.QUEUE_INDEXING,
        "schedule": timedelta(minutes=5),
        "options": {
            "queue": CeleryQueue.PRIMARY,  # indexing queue is for RUNNING, not queuing
            "priority": CeleryPriority.MEDIUM,
            "expires": CELERY_BEAT_EXPIRES_DEFAULT,
        },
    },
}
