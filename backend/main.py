from scripts.download_all_data import download_from_scryfall
from scripts.import_all import import_data_to_database


def download_data():
    print("Downloading bulk data from scryfall")
    download_from_scryfall()
    print("Downloads finished")

def import_data():
    print("Importing scryfall data to the database")
    import_data_to_database()
    print("Finished importing")

def main() -> int:    
    download_data()
    import_data()
    return 0


if __name__ == "__main__":
    main()