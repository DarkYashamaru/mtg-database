from downloaders.download_oracle_cards import download_oracle_cards_if_needed
from downloaders.download_oracle_tags import download_oracle_tags_if_needed
from tools.logger import logger

def download_from_scryfall():
    logger.info("Downloading oracle cards")
    download_oracle_cards_if_needed()
    logger.info("Downloading oracle tags")
    download_oracle_tags_if_needed()