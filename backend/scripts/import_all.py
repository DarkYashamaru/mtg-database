from importers.import_colors import import_colors
from importers.import_oracle_cards import import_oracle_cards
from importers.import_tags import import_oracle_tags
from importers.import_catalogs import download_all_catalogs
from database.create_database import create_database

def import_data_to_database():

    create_database()

    print("Importing catalogs")
    download_all_catalogs()

    print("Importing colors")
    imported = import_colors()
    print(f"Imported {imported} colors")

    print("Importing cards")
    imported = import_oracle_cards()
    print(f"Imported {imported} cards")

    print("Importing tags")
    imported = import_oracle_tags()
    print(f"Imported {imported} tags")