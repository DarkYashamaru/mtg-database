from downloaders.download_oracle_cards import download_oracle_cards_if_needed
from downloaders.download_oracle_tags import download_oracle_tags_if_needed

def download_from_scryfall():
    print("Downloading oracle cards")
    download_oracle_cards_if_needed()
    print("Downloading oracle tags")
    download_oracle_tags_if_needed()