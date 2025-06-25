"""
PokeFamilyDex.py

Generates a National Dex-ordered list of Pokémon grouped by evolutionary family,
including alternate forms and regional variants. The script fetches data from the
PokeAPI and outputs a human-readable list to 'pokedex_by_family.txt'.

Features:
- Sorts evolution families by National Dex number
- Includes variants and regional forms (except non-boxable forms)
- Applies display formatting for better readability
- Caches species and variant data to minimize API calls
- Filters out cosmetic-only or unsupported forms using SKIP_PATTERNS

Author: Cameron Ottley
Repository: https://github.com/ottles91/PokeFamilyDex
License: MIT 
"""

import requests
import time
import json
import os
from collections import defaultdict
import re

# Filenames for storing cached data locally
CACHE_FILE = "species_cache.json"          # Caches species dex numbers to reduce API calls
VARIANT_CACHE_FILE = "variant_cache.json"  # Caches known form variants of each species
API_BASE = "https://pokeapi.co/api/v2/"    # Base URL for all PokeAPI requests

# In-memory dictionaries to hold cached data during runtime
species_cache = {}
variant_cache = {}

# A list of name patterns that identify alternate forms not storable in Pokémon HOME.
# These forms will be excluded from the final output. Most are cosmetic, temporary,
# event-based, or otherwise not valid "boxable" forms.
SKIP_PATTERNS = [
    "-mega", "-primal", "-gmax", "-cap", "-belle", "-phd", "-rock-star",
    "-libre", "-pop-star", "-cosplay", "-starter", "-rainy", "-snowy",
    "-sunny", "-zen", "-origin", "-black", "-white", "-pirouette", "-battle-bond",
    "-ash", "-blade", "-complete", "-school", "-busted", "-dawn", "-ultra",
    "-necrozma-dusk", "-gulping", "-gorging", "-noice", "-crowned", "-eternamax",
    "-shadow", "-ice", "-hero", "-sprinting-build", "-gliding-build", "-limited-build",
    "-swimming-build", "-aquatic-mode", "-low-power-mode", "-cornerstone-mask",
    "-hearthflame-mask", "-wellspring-mask", "-stellar", "-terastal", "-glide-mode",
    "-dive-mode", "-kyogre-primal", "-groudon-primal", "-meteor", "necrozma-dusk", "-hangry",
    "-drive-mode"
]

# Attempt to load species dex number cache from file if it exists
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        try:
            species_cache = json.load(f)
        except json.JSONDecodeError:
            species_cache = {}  # Fallback to empty cache if file is corrupt or empty

# Attempt to load variant form cache from file if it exists
if os.path.exists(VARIANT_CACHE_FILE):
    with open(VARIANT_CACHE_FILE, "r") as f:
        try:
            variant_cache = json.load(f)
        except json.JSONDecodeError:
            variant_cache = {}  # Fallback to empty cache if file is corrupt or empty

def display_name(name):
    """
    Converts a Pokémon API species name into a properly formatted display name.

    Handles:
    - Special cases like Nidoran♀/♂, Mr. Mime, Type: Null, etc.
    - Paradox Pokémon and two-word prefix forms (e.g., "Iron Bundle")
    - Regional Tauros naming (e.g., "Tauros (Paldea Blaze)")
    - Totem variants for Jangmo-o line
    - Default conversion to "Base (Form)" format for other cases

    Args:
        name (str): The internal API species or form name (e.g., "mr-mime-galar").

    Returns:
        str: The human-readable display name (e.g., "Mr. Mime (Galar)").
    """
    
    # Handle known name overrides with unusual symbols or punctuation
    special_cases = {
        "nidoran-f": "Nidoran♀",
        "nidoran-m": "Nidoran♂",
        "mime-jr": "Mime Jr",
        "mr-mime": "Mr. Mime",
        "mr-mime-galar": "Mr. Mime (Galar)",
        "mr-rime": "Mr. Rime",
        "type-null": "Type: Null",
        "ho-oh": "Ho-Oh",
        "porygon-z": "Porygon-Z",
    }
    if name in special_cases:
        return special_cases[name]

    # Covers paradox Pokémon and other two-word prefixes like "Iron Bundle"
    double_word_prefixes = {
        "tapu", "great", "scream", "brute", "flutter", "slither", "sandy",
        "iron", "wo", "chien", "ting", "chi", "roaring", "walking", "gouging", "raging"
    }

    parts = name.split("-")

    # Special handling for Tauros (Paldea X) naming format
    if name.startswith("tauros-paldea"):
        breed = " ".join(p.capitalize() for p in parts[2:-1] + [parts[-1]])
        return f"Tauros (Paldea {breed})"

    # Totem variant handling for Jangmo-o family
    if name.startswith(("jangmo-o", "hakamo-o", "kommo-o")):
        if name.endswith("-totem"):
            base = name.rsplit("-totem", 1)[0].replace("-", "-").capitalize()
            return f"{base} (Totem)"
        return name.replace("-", "-").capitalize()

    # Handle double-word names like "Iron Bundle" or "Sandy Shocks"
    if parts[0] in double_word_prefixes and len(parts) >= 2:
        base_name = " ".join(p.capitalize() for p in parts[:2])
        suffix = parts[2:]
        if suffix:
            form = " ".join(p.capitalize() for p in suffix)
            return f"{base_name} ({form})"
        return base_name

    # Default case: Base form + form name (if any)
    base = parts[0].capitalize()
    if len(parts) == 1:
        return base
    form = " ".join(p.capitalize() for p in parts[1:])
    return f"{base} ({form})"

def normalize_species_name(name):
    """
    Normalize a Pokémon species name by stripping known suffixes that indicate
    regional variants or alternate forms, returning the base species name.

    This helps standardize species names for consistent lookups, e.g.:
    "pikachu-gmax" → "pikachu".

    Args:
        name (str): The original species or form name.

    Returns:
        str: The normalized base species name without regional or form suffixes.
    """

    # List of suffixes that identify alternate regional or form variations.
    # These are used to strip names back to their base species (e.g. "pikachu-gmax" → "pikachu").
    suffixes = [
        "-alola", "-galar", "-hisui", "-hisuian", "-paldea",
        "-totem", "-white-striped", "-red-striped", "-blue-striped",
        *SKIP_PATTERNS  # Includes other form-related suffixes you defined globally
    ]

    # Compile a regex pattern that matches any of the suffixes
    pattern = re.compile(f"({'|'.join(suffixes)})")

    # Split the name on the first matching suffix and return the base name
    return pattern.split(name)[0]

def get_all_evolution_chains():
    """
    Fetches the complete list of all Pokémon evolution chains from the PokeAPI.

    Uses a high limit parameter to retrieve all chains in a single request.

    Returns:
        list of dict: Each dict contains metadata about an evolution chain,
        including its URL to fetch detailed chain data.
    """

    # The high limit ensures that all available chains are retrieved in one call.
    url = f"{API_BASE}evolution-chain/?limit=9999"

    # Sends the request and raises an error if the request fails
    response = requests.get(url)
    response.raise_for_status()

    # Returns just the list of evolution chain metadata (URLs, etc.)
    return response.json()["results"]

def get_species_dex_number(species_url=None, species_name=None):
    """
    Retrieves the National Pokédex number for a given Pokémon species.

    Parameters:
        species_url (str, optional): The URL of the Pokémon species endpoint in the API.
        species_name (str, optional): The species name (may include form suffixes).

    Returns:
        int or float: The National Dex number if found; otherwise float('inf') as a fallback.

    Notes:
        - If a species name with a form suffix is provided, the function normalizes
          it to the base species before fetching the Dex number.
        - Results are cached in `species_cache` to avoid redundant API calls.
        - Falls back to `float('inf')` and logs a warning if the API call fails or no
          Dex number is found.
    """

    if species_name:
        # Use cached value if available
        if species_name in species_cache:
            return species_cache[species_name]

        # Normalize the name to strip form suffixes (e.g., '-therian', '-attack')
        normalized_name = normalize_species_name(species_name)
        url = f"{API_BASE}pokemon-species/{normalized_name}"

        # If the normalized name is different, recursively get the base species' Dex number
        if normalized_name != species_name:
            species_cache[species_name] = get_species_dex_number(species_name=normalized_name)
            return species_cache[species_name]

    elif species_url:
        # Extract species name from the URL if given
        species_name = species_url.rstrip('/').split("/")[-1]

        # Use cached value if available
        if species_name in species_cache:
            return species_cache[species_name]

        url = species_url
    else:
        # No valid input provided; return fallback
        return float("inf")

    try:
        # Query the species endpoint and extract the National Dex number
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        for entry in data["pokedex_numbers"]:
            if entry["pokedex"]["name"] == "national":
                species_cache[species_name] = entry["entry_number"]
                return entry["entry_number"]
    except Exception as e:
        # Log a warning and return fallback if API request fails
        print(f"⚠️  Warning: using fallback Dex number for {species_name} via {normalized_name}")

    # Default fallback if no Dex number is found or request fails
    species_cache[species_name] = float("inf")
    return float("inf")

def get_variants(species_name):
    """
    Fetches all alternate variants of a given Pokémon species (e.g., regional forms, aesthetic variations).
    Filters out non-boxable forms using the SKIP_PATTERNS list.
    Caches results to avoid repeated API calls.
    """
    # Return cached variants if available
    if species_name in variant_cache:
        return set(variant_cache[species_name])

    # Query the species endpoint from the PokéAPI
    url = f"{API_BASE}pokemon-species/{species_name}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    variants = set()

    # Iterate over all varieties defined for the species
    for variety in data["varieties"]:
        name = variety["pokemon"]["name"]

        # Only include non-default variants that aren't in the skip list
        if not variety["is_default"] and not any(pattern in name for pattern in SKIP_PATTERNS):
            variants.add(name)

    # Cache the result for future use
    variant_cache[species_name] = list(variants)
    return variants

def group_by_stage(chain_node, stage=0, stages=None):
    """
    Recursively groups Pokémon in an evolution chain by their stage in the chain.

    Args:
        chain_node (dict): A node in the evolution chain representing a species and its evolutions.
        stage (int): The current stage level (e.g., 0 for base form, 1 for first evolution).
        stages (defaultdict): A dictionary mapping stage numbers to lists of species names.

    Returns:
        defaultdict: A dictionary of evolution stages, where each key is a stage number
                     and the value is a list of species names at that stage.
    """
    if stages is None:
        stages = defaultdict(list)

    # Add the current species to its corresponding evolution stage
    name = chain_node["species"]["name"]
    stages[stage].append(name)

    # Recurse through all evolutions of the current species
    for evo in chain_node["evolves_to"]:
        group_by_stage(evo, stage + 1, stages)

    return stages

def get_form_sort_key(name):
    """
    Generates a sorting key for Pokémon forms based on regional variant priority,
    National Dex number, and name. Used to consistently order forms.

    Args:
        name (str): The internal API name of the Pokémon form.

    Returns:
        tuple: A tuple of (priority, dex_number, name) used for sorting.
    """

    # Priority for known regional or form suffixes
    region_priority = {
        "": 0,               # Base form
        "alola": 1,
        "galar": 2,
        "hisui": 3,
        "paldea": 4,
        "white-striped": 5,
        "blue-striped": 6,
        "red-striped": 7,
        "totem": 8
    }

    # Split the name into parts using hyphen
    parts = name.split("-")
    base = parts[0]

    # Join all remaining parts to determine the region/form identifier
    region = "-".join(parts[1:]) if len(parts) > 1 else ""

    # Special handling for known exception that lacks a suffix
    if name == "perrserker":
        region = "galar"

    # Use predefined priority or fall back to a large number
    priority = region_priority.get(region, 99)

    # Get the species' National Dex number (used for secondary sort)
    dex = get_species_dex_number(species_name=name)

    return (priority, dex, name)

def format_family(stages):
    """
    Flattens and formats the evolutionary stages dictionary into a single sorted list of Pokémon names.
    
    - Removes duplicate names.
    - Filters out unwanted form patterns (e.g., Mega, Primal, etc.).
    - Sorts forms using the get_form_sort_key function for consistent ordering.

    Args:
        stages (dict): A dictionary where keys are evolution stages (0 = base, 1 = first evo, etc.)
                       and values are lists of Pokémon names at that stage.

    Returns:
        list: A flat, sorted list of Pokémon names for this family line.
    """

    flat_list = []

    # Process stages in evolutionary order (0 -> 1 -> 2...)
    for stage in sorted(stages.keys()):
        # Remove duplicates within the stage
        forms = list(set(stages[stage]))

        # Filter out forms we don't want to include (e.g., non-boxable)
        forms = [f for f in forms if not any(pattern in f for pattern in SKIP_PATTERNS)]

        # Sort the forms using a custom sort key (region, dex number, name)
        forms.sort(key=get_form_sort_key)

        # Add the cleaned and sorted forms to the final list
        flat_list.extend(forms)

    return flat_list

def parse_evolution_chain(url):
    """
    Parses a Pokémon evolution chain from the given API URL into a dictionary of stages.

    - Fetches and traverses the evolution chain from the API.
    - Groups species and their form variants by their evolutionary stage.
    - Uses breadth-first traversal to maintain correct stage depth.

    Args:
        url (str): API URL pointing to a specific evolution chain.

    Returns:
        dict: A dictionary mapping each evolution stage (0, 1, 2...) to a list of Pokémon species names,
              including variant forms for each base species.
    """

    response = requests.get(url)
    response.raise_for_status()
    chain = response.json()["chain"]

    stages = {}
    queue = [(chain, 0)]  # Each item is a tuple of (node, stage_level)

    # Perform a breadth-first traversal of the evolution tree
    while queue:
        node, stage = queue.pop(0)
        name = node["species"]["name"]

        # Initialize the stage list if it hasn't been seen yet
        if stage not in stages:
            stages[stage] = []

        # Add the base species to its stage
        stages[stage].append(name)

        # Add any variant forms of this species (e.g., regional variants)
        variants = get_variants(name)
        stages[stage].extend(variants)

        # Enqueue evolved forms to process in the next stage
        for evo in node.get("evolves_to", []):
            queue.append((evo, stage + 1))

    return stages

def get_sorted_family(url):
    """
    Given an evolution chain URL, returns a sorted list of species in the family.

    - Parses the full evolution chain into staged groups.
    - Flattens and sorts the species list, filtering out unwanted forms.
    - Retrieves the National Dex number of the base species for sorting.

    Args:
        url (str): API URL to a specific Pokémon evolution chain.

    Returns:
        tuple: (dex_number, species_list)
            - dex_number (int): National Dex number of the first Pokémon in the family.
            - species_list (list): Ordered list of species and valid variants.
    """
    stages = parse_evolution_chain(url)
    flattened = format_family(stages)
    dex_number = get_species_dex_number(species_name=flattened[0])
    return dex_number, flattened

def main():
    """
    Main execution function:
    - Fetches all Pokémon evolution chains.
    - Processes each chain into a sorted family list.
    - Prints species names to the console.
    - Writes the full Pokédex listing to a text file.
    - Saves species and variant caches to avoid redundant API calls.
    """
    chains = get_all_evolution_chains()
    all_species = []

    print(f"Found {len(chains)} evolution chains...\n")

    for i, chain in enumerate(chains, start=1):
        try:
            # Get the sorted family and its Dex number
            dex_num, species_list = get_sorted_family(chain["url"])
            all_species.append((dex_num, species_list))

            # Print the display names to the console
            for species in species_list:
                print(display_name(species))

            # Respectful pause between requests to avoid hammering the API
            time.sleep(0.2)

        except Exception as e:
            print(f"[{i}/{len(chains)}] Error: {e}")

    # Sort species families by Dex number
    all_species.sort(key=lambda x: x[0])

    # Write results to output file
    with open("pokedex_by_family.txt", "w") as f:
        for _, species_list in all_species:
            for species in species_list:
                f.write(display_name(species) + "\n")

    # Save cache files to reduce future API calls
    with open(CACHE_FILE, "w") as f:
        json.dump(species_cache, f)
    with open(VARIANT_CACHE_FILE, "w") as f:
        json.dump(variant_cache, f)

    print("\nSaved to pokedex_by_family.txt")

if __name__ == "__main__":
    main()