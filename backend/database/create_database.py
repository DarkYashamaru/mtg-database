from database.base import Base
from sqlalchemy import inspect, text

from database.session import engine

# import all models
from models.card import *
from models.marker import *
from models.tag import *
from models.archetype import *
from models.category import *
from models.catalogs import *
from models.color import *
from models.themes import *


def create_database():
    Base.metadata.create_all(bind=engine)

    # This project predates a migration framework. Keep existing SQLite
    # installations compatible when additive Card fields are introduced.
    card_columns = {column["name"] for column in inspect(engine).get_columns("cards")}
    for column_name in ("num_decks", "potential_decks"):
        if column_name not in card_columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE cards ADD COLUMN {column_name} INTEGER"))
