from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from codegraph.configs.constants import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_READONLY_PASSWORD,
    POSTGRES_READONLY_USER,
    POSTGRES_USER,
)


def _build_connection_endpoint(
    user: str, password: str, host: str, port: int, database: str
) -> str:
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def get_connection_endpoint(readonly: bool = False) -> str:
    args: Any = {
        "user": POSTGRES_READONLY_USER if readonly else POSTGRES_USER,
        "password": POSTGRES_READONLY_PASSWORD if readonly else POSTGRES_PASSWORD,
        "host": POSTGRES_HOST,
        "port": POSTGRES_PORT,
        "database": POSTGRES_DB,
    }
    return _build_connection_endpoint(**args)


class SqlEngine:
    _write_engine: Engine | None = None
    _read_engine: Engine | None = None

    @classmethod
    def init_engine(cls) -> None:
        if cls._write_engine:
            return

        cls._write_engine = create_engine(
            get_connection_endpoint(),
            pool_pre_ping=True,
        )

    @classmethod
    def init_readonly_engine(cls) -> None:
        if cls._read_engine:
            return

        cls._read_engine = create_engine(
            get_connection_endpoint(readonly=True),
            pool_pre_ping=True,
        )

    @classmethod
    def get_engine(cls) -> Engine:
        if not cls._write_engine:
            raise RuntimeError("Engine not initialized. You must call init_engine() first.")
        return cls._write_engine

    @classmethod
    def get_readonly_engine(cls) -> Engine:
        if not cls._read_engine:
            raise RuntimeError(
                "Readonly engine not initialized. You must call init_readonly_engine() first."
            )
        return cls._read_engine


@contextmanager
def get_session(readonly: bool = False) -> Generator[Session, None, None]:
    engine = SqlEngine.get_readonly_engine() if readonly else SqlEngine.get_engine()
    with Session(bind=engine, expire_on_commit=False) as session:
        yield session
