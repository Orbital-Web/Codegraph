from time import monotonic, sleep

from redis import Redis

from codegraph.configs.app_configs import (
    READINESS_INTERVAL,
    READINESS_TIMEOUT,
    REDIS_DB_NUMBER,
    REDIS_HOST,
    REDIS_PORT,
)
from codegraph.utils.logging import get_logger

logger = get_logger()


def get_redis_client() -> Redis:
    return Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB_NUMBER)


def wait_for_redis() -> bool:
    logger.info("Redis: readiness probe starting")

    redis_client = get_redis_client()
    start_time = monotonic()
    ready = False

    while True:
        try:
            if redis_client.ping():
                ready = True
                break
        except Exception:
            pass

        elapsed = monotonic() - start_time
        if elapsed > READINESS_TIMEOUT:
            break

        logger.warning(
            f"Redis: readiness probe ongoing, elapsed: {elapsed:.1f}s "
            f"timeout={READINESS_TIMEOUT:.1f}s)"
        )
        sleep(READINESS_INTERVAL)

    if not ready:
        logger.error(f"Redis: readiness probe did not succeed in {READINESS_TIMEOUT}")
        return False

    logger.info(f"Redis: readiness probe succeeded")
    return True
