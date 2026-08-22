from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]
CLASSIFICATION_DATABASE_PATH = BACKEND_DIR / "card_classification.sqlite"


def classification_database_url(database_path: Path = CLASSIFICATION_DATABASE_PATH) -> str:
    return f"sqlite:///{database_path.resolve().as_posix()}"


def get_classification_engine(database_path: Path = CLASSIFICATION_DATABASE_PATH) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(classification_database_url(database_path), future=True)


def get_classification_session_factory(
    database_path: Path = CLASSIFICATION_DATABASE_PATH,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_classification_engine(database_path),
        autoflush=False,
        expire_on_commit=False,
    )


classification_engine = get_classification_engine()

ClassificationSessionLocal = sessionmaker(
    bind=classification_engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_classification_db() -> Iterator[Session]:
    db = ClassificationSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def classification_session_scope(
    database_path: Path = CLASSIFICATION_DATABASE_PATH,
) -> Iterator[Session]:
    engine = get_classification_engine(database_path)
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
