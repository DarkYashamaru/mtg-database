from downloaders.download_oracle_cards import download_oracle_cards_if_needed
from downloaders.download_default_cards import download_default_cards_if_needed
from downloaders.download_oracle_tags import download_oracle_tags_if_needed
from downloaders.download_catalog_files import download_all_catalog_files
from downloaders.download_symbology import download_symbology
from tools.logger import logger

def download_from_scryfall():
    logger.info("Downloading catalog files")
    download_all_catalog_files()
    logger.info("Downloading symbology")
    download_symbology()
    logger.info("Downloading oracle cards")
    download_oracle_cards_if_needed()
    logger.info("Downloading default cards")
    download_default_cards_if_needed()
    logger.info("Downloading oracle tags")
    download_oracle_tags_if_needed()
