from importers.theme_importer import import_theme
from data.themes.voltron_data import VOLTRON_DATA
from database.create_database import create_database
from database.session import get_db
from sqlalchemy.orm import Session

def import_voltron() -> int:
    return import_theme(
        theme_id=1,
        theme_name="Voltron",
        categories_data=VOLTRON_DATA,
        curated=True
    )

def import_all_themes():
    import_voltron()

def main() -> int:

    # 3. Initialize Database
    create_database()
    db: Session = next(get_db())

    import_voltron()


if __name__ == "__main__":
    raise SystemExit(main())