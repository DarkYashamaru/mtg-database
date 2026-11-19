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
from models.printing import *


def create_database():
    # Remember whether this is an upgrade before create_all() creates missing
    # tables. Existing installations already completed the original full
    # rulings import, so they become the incremental-sync baseline below.
    preexisting_cards_table = inspect(engine).has_table("cards")
    preexisting_card_columns = (
        {column["name"] for column in inspect(engine).get_columns("cards")}
        if preexisting_cards_table
        else set()
    )
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    face_primary_key = inspector.get_pk_constraint("card_faces").get("constrained_columns")
    face_columns = {
        column["name"]: column for column in inspector.get_columns("card_faces")
    }
    # SQLite cannot relax a NOT NULL constraint in place. Rebuild the
    # source-derived face tables when upgrading either the old face-name key
    # or the old non-null type_line column.
    needs_face_rebuild = (
        face_primary_key == ["parent_id", "name"]
        or not face_columns["type_line"]["nullable"]
    )
    if needs_face_rebuild:
        with engine.begin() as connection:
            for table_name in ("face_subtypes", "face_card_types", "face_supertypes", "card_faces"):
                connection.execute(text(f"DROP TABLE {table_name}"))
            Card_Face.__table__.create(connection)
            Face_Supertypes.__table__.create(connection)
            Face_Types.__table__.create(connection)
            Face_Subtypes.__table__.create(connection)

    # These fields preserve the difference between an absent color array and
    # an explicitly empty one in Scryfall card-face data.
    face_columns = {column["name"] for column in inspect(engine).get_columns("card_faces")}
    for column_name in ("colors_present", "color_indicator_present"):
        if column_name not in face_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"ALTER TABLE card_faces ADD COLUMN {column_name} "
                        "BOOLEAN NOT NULL DEFAULT 0"
                    )
                )

    printing_value_primary_key = inspect(engine).get_pk_constraint(
        "printing_values"
    ).get("constrained_columns")
    if printing_value_primary_key == ["printing_id", "field", "value"]:
        # SQLite cannot alter a primary key in place. Preserve the existing
        # source-derived rows while rebuilding the table with array position
        # as its identity.
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE printing_values RENAME TO printing_values_legacy")
            )
            PrintingValue.__table__.create(connection)
            connection.execute(
                text(
                    """
                    INSERT INTO printing_values (printing_id, field, position, value)
                    SELECT printing_id, field, position, value
                    FROM printing_values_legacy
                    """
                )
            )
            connection.execute(text("DROP TABLE printing_values_legacy"))

    # This project predates a migration framework. Keep existing SQLite
    # installations compatible when additive Card fields are introduced.
    card_columns = {column["name"] for column in inspect(engine).get_columns("cards")}
    for column_name in (
        "num_decks",
        "potential_decks",
        "rulings_uri",
        "rulings_fetched_at",
    ):
        if column_name not in card_columns:
            with engine.begin() as connection:
                column_type = (
                    "TEXT"
                    if column_name in ("rulings_uri", "rulings_fetched_at")
                    else "INTEGER"
                )
                connection.execute(
                    text(f"ALTER TABLE cards ADD COLUMN {column_name} {column_type}")
                )

    if preexisting_cards_table and "rulings_fetched_at" not in preexisting_card_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE cards SET rulings_fetched_at = CURRENT_TIMESTAMP "
                    "WHERE rulings_fetched_at IS NULL"
                )
            )

    tag_columns = {column["name"] for column in inspect(engine).get_columns("tags")}
    if "is_active" not in tag_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE tags ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
            )


def vacuum_database() -> None:
    """Defragment the SQLite database during exclusive maintenance only."""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("VACUUM"))
