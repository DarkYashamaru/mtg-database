import re
import unicodedata

def card_name_to_slug(name: str) -> str:
    """
    Transforms an MTG card name into a clean, URL-friendly slug.
    
    - Strips accents/diacritics (e.g., ñ -> n, í -> i)
    - Converts to lowercase
    - Removes punctuation like apostrophes completely (e.g., Death's -> deaths)
    - Replaces spaces, commas, and other special characters with a single hyphen
    - Strips leading/trailing hyphens
    """
    if not name:
        return ""

    # 1. Decompose unicode characters (e.g., 'ñ' becomes 'n' + 'Combining Tilde')
    normalized = unicodedata.normalize('NFD', name)
    
    # 2. Encode to ASCII while ignoring errors (drops the accents), then decode back to a string
    slug = normalized.encode('ascii', 'ignore').decode('utf-8')
    
    # 3. Convert to lowercase
    slug = slug.lower()
    
    # 4. Remove apostrophes completely so "Death's" becomes "deaths"
    slug = slug.replace("'", "")
    
    # 5. Replace any remaining non-alphanumeric character sequences with a single hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # 6. Clean up any trailing or leading hyphens
    return slug.strip('-')

def get_primary_card_name(card_name: str) -> str:
    """
    Takes a full card name (including double-faced '//' names) 
    and returns only the primary (front) face name.
    """
    if not card_name:
        return ""
    return card_name.split("//")[0].strip()

# --- Verification ---

test_cards = [
    "Clavileño, First of the Blessed",
    "Círdan the Shipwright",
    "Death's Shadow",
    "Growing Rites of Itlimoc // Itlimoc, Cradle of the Sun"
]

for card in test_cards:
    primary = get_primary_card_name(card)
    slug = card_name_to_slug(primary)
    print(f"Original: {card:<55} -> Slug: {slug}")