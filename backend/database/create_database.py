from __future__ import annotations
from database.base import Base  # noqa: E402
from database.session import DATABASE_PATH, get_engine  # noqa: E402
from models.card import Card  # noqa: E402,F401

def create_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    try:
        Base.metadata.create_all(bind=engine)
    finally:
        engine.dispose()