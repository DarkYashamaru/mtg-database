from importers.import_colors import import_colors
from importers.import_oracle_cards import import_oracle_cards, backfill_shared_front_face_images
from importers.import_tags import import_oracle_tags
from importers.import_catalogs import download_all_catalogs
from scripts.import_manual_themes import import_all_themes
from scripts.compute_card_to_themes import import_card_themes
from scripts.import_themes_from_edhrec import import_edhrec_themes
from tools.logger import logger

def import_data_to_database():

    logger.info("Importing catalogs")
    download_all_catalogs()

    logger.info("Importing colors")
    imported = import_colors()
    logger.info(f"Imported {imported} colors")

    logger.info("Importing cards")
    imported = import_oracle_cards()
    logger.info(f"Imported {imported} cards")

    logger.info("Backfilling shared-front card face images")
    updated_faces = backfill_shared_front_face_images()
    logger.info(f"Backfilled {updated_faces} shared-front face images")

    logger.info("Importing tags")
    imported = import_oracle_tags()
    logger.info(f"Imported {imported} tags")

    logger.info("Importing themes")
    imported = import_edhrec_themes()
    logger.info(f"Imported {imported} themes")

    logger.info("Calculating card to themes score")
    
    
