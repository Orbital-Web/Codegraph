from enum import Enum, auto

CELERY_REDIS_HEALTH_CHECK_INTERVAL = 60

# Celery task timeouts
CELERY_RESULT_EXPIRES = 24 * 60 * 60
CELERY_BEAT_EXPIRES_DEFAULT = 15 * 60

# Redis lock timeouts
REDIS_INDEXING_LOCK_TIMEOUT = 120


class CeleryPriority(int, Enum):
    HIGHEST = 0
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    LOWEST = auto()


class CeleryQueue(str, Enum):
    # primary queues ("celery" is the default queue)
    PRIMARY = "celery"

    # indexing queues
    INDEXING = "indexing"


class CeleryTask(str, Enum):
    QUEUE_INDEXING = "queue_indexing"
    RUN_INDEXING = "run_indexing"


class RedisLock(str, Enum):
    INDEXING_PREFIX = "lock:indexing"
