from importers.archetype_importer import import_archetype
from data.archetypes.voltron_data import VOLTRON_DATA
from database.create_database import create_database
from database.session import get_db
from sqlalchemy.orm import Session

def import_voltron() -> int:
    return import_archetype(
        archetype_id=1,
        archetype_name="Voltron",
        categories_data=VOLTRON_DATA,
    )

def import_all_archetypes():
    import_voltron()

def main() -> int:

    # 3. Initialize Database
    create_database()
    db: Session = next(get_db())

    import_voltron()


if __name__ == "__main__":
    raise SystemExit(main())