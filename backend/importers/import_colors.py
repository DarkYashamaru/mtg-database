from __future__ import annotations
from database.create_database import create_database  # noqa: E402
from database.session import session_scope  # noqa: E402
from models.color import Color  # noqa: E402

def import_colors() -> int:

    white = Color(id=1, name="White", symbol='W')
    blue = Color(id=2, name="Blue", symbol='U')
    black = Color(id=3, name="Black", symbol='B')
    red = Color(id=4, name="Red", symbol='R')
    green = Color(id=5, name="Green", symbol='G')
    colorless = Color(id=6, name="Colorless", symbol='C')

    colors = [white, blue, black, red, green, colorless]

    imported_count = 0

    with session_scope() as session:

        for color in colors:
            session.merge(color)
            imported_count += 1

        session.commit()            
        session.expunge_all()

    return imported_count