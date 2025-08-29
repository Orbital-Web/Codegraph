from celery import shared_task
from celery.app.task import Task
from redis.lock import Lock
from sqlalchemy import select

from codegraph.celery.constants import (
    REDIS_INDEXING_LOCK_TIMEOUT,
    CeleryPriority,
    CeleryQueue,
    CeleryTask,
    RedisLock,
)
from codegraph.db.engine import get_session
from codegraph.db.models import Project
from codegraph.graph.indexing.pipeline import run_indexing as run_indexing_pipeline
from codegraph.redis.client import get_redis_client
from codegraph.utils.logging import get_logger

logger = get_logger()


def _get_indexing_lock_name(project_id: int) -> str:
    return f"{RedisLock.INDEXING_PREFIX.value}:{project_id}"


@shared_task(name=CeleryTask.QUEUE_INDEXING, bind=True)
def queue_indexing(self: Task) -> None:  # type: ignore[type-arg]
    """Enqueue indexing tasks for all projects."""
    with get_session() as session:
        project_ids = session.execute(select(Project.id)).scalars().all()

    redis_client = get_redis_client()
    for project_id in project_ids:
        # if lock is being held, indexing is already running so skip
        lock: Lock = redis_client.lock(
            _get_indexing_lock_name(project_id),
            timeout=REDIS_INDEXING_LOCK_TIMEOUT,
        )
        if lock.locked():
            continue

        logger.info(f"queue_indexing ({project_id}): queued")
        self.app.send_task(
            CeleryTask.RUN_INDEXING,
            kwargs={"project_id": project_id},
            queue=CeleryQueue.INDEXING,
            priority=CeleryPriority.MEDIUM,
        )


@shared_task(name=CeleryTask.RUN_INDEXING)
def run_indexing(project_id: int) -> None:
    """Run indexing for a single project. Ensures indexing on a project won't overlap."""
    logger.info(f"run_indexing ({project_id}): starting")

    # acquire lock to prevent overlap
    redis_client = get_redis_client()
    lock: Lock = redis_client.lock(
        _get_indexing_lock_name(project_id),
        timeout=REDIS_INDEXING_LOCK_TIMEOUT,
    )
    if not lock.acquire(blocking=False):
        return

    # run indexing
    try:
        run_indexing_pipeline(project_id, lock)
    except Exception as e:
        logger.error(f"run_indexing ({project_id}): {e}")
    finally:
        # release lock
        if lock.owned():
            lock.release()
            logger.info(f"run_indexing ({project_id}): completed")
        else:
            logger.error(f"run_indexing ({project_id}): lock not owned")
