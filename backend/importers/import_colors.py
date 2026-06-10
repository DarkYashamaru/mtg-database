from __future__ import annotations
from database.create_database import create_database  # noqa: E402
from database.session import session_scope  # noqa: E402
from models.color import Color  # noqa: E402

def create_color(name:str, symbol:str) -> Color:
    return Color(name = name, symbol = symbol)

def import_colors() -> int:

    white = create_color("White", 'W')
    blue = create_color("Blue", 'U')
    black = create_color("Black", 'B')
    red = create_color("Red", 'R')
    green = create_color("Green", 'G')
    colorless = create_color("Colorless", 'C')

    colors = [white, blue, black, red, green, colorless]

    create_database()

    imported_count = 0

    try:

        with session_scope() as session:

            for color in colors:
                session.merge(color)
                imported_count += 1

            session.commit()            
            session.expunge_all()

    except Exception as e:
        print(e)

    return imported_count
