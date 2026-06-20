from importers.import_colors import import_colors
from importers.import_oracle_cards import import_oracle_cards
from importers.import_tags import import_oracle_tags
from importers.import_catalogs import download_all_catalogs
from scripts.import_manual_themes import import_all_themes
from scripts.compute_card_to_themes import import_card_themes
from scripts.import_themes_from_edhrec import import_edhrec_themes

def import_data_to_database():

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

    print("Importing themes")
    imported = import_edhrec_themes()
    print(f"Imported {imported} themes")

    print("Calculating card to themes score")
    
    
