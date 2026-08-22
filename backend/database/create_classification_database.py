from pathlib import Path

try:
    from backend.database.classification_base import ClassificationBase
    from backend.database.classification_session import CLASSIFICATION_DATABASE_PATH, get_classification_engine
except ModuleNotFoundError:
    from database.classification_base import ClassificationBase
    from database.classification_session import CLASSIFICATION_DATABASE_PATH, get_classification_engine

# import all classification models
try:
    from backend.models.card_classification import *  # noqa: F401,F403
except ModuleNotFoundError:
    from models.card_classification import *  # noqa: F401,F403


def create_classification_database(database_path: Path = CLASSIFICATION_DATABASE_PATH) -> None:
    engine = get_classification_engine(database_path)
    try:
        ClassificationBase.metadata.create_all(bind=engine)
    finally:
        engine.dispose()
