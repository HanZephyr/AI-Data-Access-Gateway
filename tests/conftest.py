from collections.abc import Generator
from typing import cast

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from adg.control_plane.db import (  # type: ignore[import-untyped]
    create_engine_from_url,
    create_session_factory,
)
from adg.control_plane.models import Base  # type: ignore[import-untyped]


@pytest.fixture
def sqlite_engine() -> Engine:
    engine = cast(Engine, create_engine_from_url("sqlite:///:memory:"))
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(sqlite_engine: Engine) -> sessionmaker[Session]:
    return cast(sessionmaker[Session], create_session_factory(sqlite_engine))


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session
