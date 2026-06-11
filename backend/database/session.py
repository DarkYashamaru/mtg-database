from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_DIR = BACKEND_DIR / "data"
DATABASE_PATH = DATABASE_DIR / "cards.sqlite"


def database_url() -> str:
    return f"sqlite:///{DATABASE_PATH.resolve().as_posix()}"


def get_engine() -> Engine:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url(), future=True)


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )

engine = create_engine(
    database_url(),
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    engine = get_engine()
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()
