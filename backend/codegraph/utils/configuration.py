from codegraph.db.engine import SqlEngine, wait_for_db
from codegraph.index.chroma import ChromaIndex, wait_for_index
from codegraph.redis.client import wait_for_redis


def initialize_and_wait_for_services() -> bool:
    """Initializes and waits for dependent services to be ready. Returns whether all services are
    ready."""
    SqlEngine.init_engine()

    if not wait_for_redis():
        return False
    if not wait_for_db():
        return False
    if not wait_for_index():
        return False

    ChromaIndex.init_index()

    return True


# TODO: add initialize_and_wait_for_workers() -> bool
