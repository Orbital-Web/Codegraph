from codegraph.db.engine import SqlEngine, wait_for_db
from codegraph.index.chroma import wait_for_index
from codegraph.model_service.client import wait_for_model_server
from codegraph.redis.client import wait_for_redis


def initialize_and_wait_for_services() -> bool:
    """Initializes and waits for required services to be ready. Returns whether all services are
    ready.
    """
    SqlEngine.init_engine()

    if not wait_for_redis():
        return False
    if not wait_for_db():
        return False
    if not wait_for_index():
        return False
    if not wait_for_model_server():
        return False

    return True


# TODO: add initialize_and_wait_for_workers() -> bool
