import re

def card_name_to_slug(name: str) -> str:
    """
    Transforms an MTG card name into a clean, URL-friendly slug.
    
    - Converts to lowercase
    - Removes punctuation like apostrophes completely (e.g., Death's -> deaths)
    - Replaces spaces, commas, and other special characters with a single hyphen
    - Strips leading/trailing hyphens
    """
    # 1. Convert to lowercase
    slug = name.lower()
    
    # 2. Remove apostrophes completely so "Death's" becomes "deaths"
    slug = slug.replace("'", "")
    
    # 3. Replace any non-alphanumeric character sequences with a single hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # 4. Clean up any trailing or leading hyphens left over from step 3
    return slug.strip('-')

def get_primary_card_name(card_name: str) -> str:
    """
    Takes a full card name (including double-faced '//' names) 
    and returns only the primary (front) face name.
    """
    if not card_name:
        return ""
        
    # Split by the double slash and take the first part, stripping trailing spaces
    return card_name.split("//")[0].strip()

# --- Example Usage ---
full_name = "Growing Rites of Itlimoc // Itlimoc, Cradle of the Sun"
clean_name = get_primary_card_name(full_name)

print(clean_name)  # Output: Growing Rites of Itlimoc