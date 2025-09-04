import json
from .constants import CACHE_FILE, VARIANT_CACHE_FILE

# Global caches (mutable, used across modules)
species_cache = {}
variant_cache = {}

def load_caches():
    """Load species and variant caches from disk if available."""
    global species_cache, variant_cache
    try:
        with open(CACHE_FILE, "r") as f:
            species_cache = json.load(f)
    except FileNotFoundError:
        species_cache = {}
    try:
        with open(VARIANT_CACHE_FILE, "r") as f:
            variant_cache = json.load(f)
    except FileNotFoundError:
        variant_cache = {}

def save_caches():
    """Persist caches to disk."""
    with open(CACHE_FILE, "w") as f:
        json.dump(species_cache, f)
    with open(VARIANT_CACHE_FILE, "w") as f:
        json.dump(variant_cache, f)