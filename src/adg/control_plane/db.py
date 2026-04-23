from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from adg.app.settings import get_settings


def create_engine_from_url(database_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    poolclass: type[StaticPool] | None = None
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url == "sqlite:///:memory:":
            poolclass = StaticPool

    return create_engine(
        database_url,
        connect_args=connect_args,
        future=True,
        poolclass=poolclass,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


engine = create_engine_from_url(get_settings().control_plane_database_url)
SessionLocal = create_session_factory(engine)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
