import pytest

from codegraph.utils.configuration import initialize_and_wait_for_services
from tests.integration.reset import reset_all


@pytest.fixture(scope="package", autouse=True)
def initialize_and_wait() -> None:
    ready = initialize_and_wait_for_services()  # not using celery workers
    if not ready:
        pytest.fail("Failed to initialize services")


@pytest.fixture()
def reset() -> None:
    reset_all()
