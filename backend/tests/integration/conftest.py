import pytest

from codegraph.db.engine import SqlEngine
from tests.integration.reset import reset_all


@pytest.fixture(scope="session", autouse=True)
def initialize_db() -> None:
    SqlEngine.init_engine()


@pytest.fixture()
def reset() -> None:
    reset_all()
