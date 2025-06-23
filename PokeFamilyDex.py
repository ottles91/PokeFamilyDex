import requests
import time
import json
import os
from collections import defaultdict
import re

CACHE_FILE = "species_cache.json"
VARIANT_CACHE_FILE = "variant_cache.json"
API_BASE = "https://pokeapi.co/api/v2/"

species_cache = {}
variant_cache = {}

# Load cache from file if it exists
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        try:
            species_cache = json.load(f)
        except json.JSONDecodeError:
            species_cache = {}
            
# Load variant cache if available
if os.path.exists(VARIANT_CACHE_FILE):
    with open(VARIANT_CACHE_FILE, "r") as f:
        try:
            variant_cache = json.load(f)
        except json.JSONDecodeError:
            variant_cache = {}

def display_name(name):
    # Explicit overrides
    special_cases = {
        "nidoran-f": "Nidoran♀",
        "nidoran-m": "Nidoran♂",
        "mime-jr": "Mime Jr",
        "mr-mime": "Mr. Mime",
        "mr-mime-galar": "Mr. Mime (Galar)",
        "mr-rime": "Mr. Rime",
    }
    if name in special_cases:
        return special_cases[name]

    # Paradox & Tapus & Treasures of Ruin: two-word proper names
    double_word_prefixes = {
        "tapu", "great", "scream", "brute", "flutter", "slither", "sandy",
        "iron", "wo", "chien", "ting", "chi", "roaring", "walking", "gouging", "raging"
    }

    parts = name.split("-")

    # Tauros (Paldea form handling)
    if name.startswith("tauros-paldea"):
        breed = " ".join(p.capitalize() for p in parts[2:-1] + [parts[-1]])
        return f"Tauros (Paldea {breed})"

    # Jangmo-o, Hakamo-o, Kommo-o (preserve hyphen unless followed by a suffix like -totem)
    if name.startswith(("jangmo-o", "hakamo-o", "kommo-o")):
        if name.endswith("-totem"):
            base = name.rsplit("-totem", 1)[0].replace("-", "-").capitalize()
            return f"{base} (Totem)"
        return name.replace("-", "-").capitalize()

    # Two-word proper names
    if parts[0] in double_word_prefixes and len(parts) >= 2:
        base_name = " ".join(p.capitalize() for p in parts[:2])
        suffix = parts[2:]  # e.g. "galar", "totem"
        if suffix:
            form = " ".join(p.capitalize() for p in suffix)
            return f"{base_name} ({form})"
        return base_name

    # Fallback: Base name + form in parens
    base = parts[0].capitalize()
    if len(parts) == 1:
        return base
    form = " ".join(p.capitalize() for p in parts[1:])
    return f"{base} ({form})"

def normalize_species_name(name):
    """
    Strip known suffixes (like '-alola', '-totem', '-galar') from a Pokémon form name
    so we can fetch the correct dex number from the base species endpoint.
    """
    # Handles things like: raticate-totem-alola -> raticate
    # Strip everything after first known suffix
    suffixes = [
        "-alola", "-galar", "-hisui", "-hisuian", "-paldea",
        "-totem", "-white-striped", "-red-striped", "-blue-striped",
        "-mega", "-gmax", "-three-segment", "-rainy", "-sunny", "-snowy", 
        "-primal", "-defense", "-speed", "-attack", "-sandy", "-trash",
        "-mow", "-frost", "-heat", "-wash", "-fan", "-origin", "-sky", 
        "-female", "-zen", "therian", "-black", "-white", "-resolute",
        "-pirouette","-battle-bond", "-ash", "-eternal", "-blade",
        "-small", "-super", "-large", "-complete", "-50-power-construct",
        "-10-power-construct", "-unbound", "-pom-pom", "-sensu", "-pau"
        "-own-tempo", "-midnight", "-dusk", "-school", "-green", "-orange-meteor",
        "-indigo", "-red", "-blue-meteor", "-violet-meteor", "-indigo-meteor", 
        "-orange", "-yellow", "-blue", "-yellow-meteor", "-green-meteor",
        "-minior-violet", "-busted", "-dawn", "-ultra", "-original", "-gorging",
        "-gulping", "-low-key", "-noice", "-hangry", "-crowned", "-eternamax",
        "-rapid-strike", "-dada", "-shadow", -"ice", "-family-of-three", 
        "-white-plumage", "-yellow-plumage", "-blue-plumage", "-hero",
        "-droopy", "-stretchy", "-roaming", "-sprinting-build", "gliding-build",
        "-limited-build", "-swimming-build", "-glide-mode", "-dive-mode",
        "-aquatic-mode", "-low-power-mode", "-hearthflame-mask", "-wellspring-mask",
        "-cornerstone-mask", "-stellar", "-terastal"
    ]
    pattern = re.compile(f"({'|'.join(suffixes)})")
    return pattern.split(name)[0]

def get_all_evolution_chains():
    url = f"{API_BASE}evolution-chain/?limit=9999"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["results"]

def get_species_dex_number(species_url=None, species_name=None):
    if species_name:
        if species_name in species_cache:
            return species_cache[species_name]

        # Normalize to base name for species lookup
        normalized_name = normalize_species_name(species_name)

        url = f"{API_BASE}pokemon-species/{normalized_name}"
    elif species_url:
        species_name = species_url.rstrip('/').split("/")[-1]
        if species_name in species_cache:
            return species_cache[species_name]
        url = species_url
    else:
        return float("inf")

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        for entry in data["pokedex_numbers"]:
            if entry["pokedex"]["name"] == "national":
                species_cache[species_name] = entry["entry_number"]
                return entry["entry_number"]
    except Exception as e:
        print(f"Warning: could not fetch dex number for {species_name}: {e}")

    species_cache[species_name] = float("inf")
    return float("inf")

def get_variants(species_name):
    if species_name in variant_cache:
        return set(variant_cache[species_name])

    url = f"{API_BASE}pokemon-species/{species_name}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    variants = set()
    for variety in data["varieties"]:
        name = variety["pokemon"]["name"]

        if not variety["is_default"]:
            # Skip non-boxable forms
            if (
                "-mega" in name or
                "-gmax" in name or
                "-cap" in name or
                "-belle" in name or
                "-phd" in name or
                "-rock-star" in name or
                "-libre" in name or
                "-pop-star" in name or
                "-cosplay" in name or
                "-starter" in name
            ):
                continue

            variants.add(name)

    variant_cache[species_name] = list(variants)
    return variants

def group_by_stage(chain_node, stage=0, stages=None):
    if stages is None:
        stages = defaultdict(list)

    name = chain_node["species"]["name"]
    stages[stage].append(name)

    for evo in chain_node["evolves_to"]:
        group_by_stage(evo, stage + 1, stages)

    return stages

def get_form_sort_key(name):
    region_priority = {
        "": 0,
        "alola": 1,
        "galar": 2,
        "hisui": 3,
        "paldea": 4,
        "white-striped": 5,
        "blue-striped": 6,
        "red-striped": 7,
        "totem": 8
    }

    parts = name.split("-")
    base = parts[0]
    region = "-".join(parts[1:]) if len(parts) > 1 else ""

    # Special handling for perrserker (it's galarian meowth's evolution, not literally named "galarian-perrserker")
    if name == "perrserker":
        region = "galar"

    if region in region_priority:
        priority = region_priority[region]
    else:
        priority = 99

    dex = get_species_dex_number(species_name=name)
    return (priority, dex, name)


def format_family(stages):
    flat_list = []

    for stage in sorted(stages.keys()):
        forms = list(set(stages[stage]))
        forms.sort(key=get_form_sort_key)
        flat_list.extend(forms)

    return flat_list

def parse_evolution_chain(url):
    response = requests.get(url)
    response.raise_for_status()
    chain = response.json()["chain"]

    stages = {}
    queue = [(chain, 0)]  # (node, stage)

    while queue:
        node, stage = queue.pop(0)
        name = node["species"]["name"]

        if stage not in stages:
            stages[stage] = []

        stages[stage].append(name)

        # Add variants of this species
        variants = get_variants(name)
        stages[stage].extend(variants)

        for evo in node.get("evolves_to", []):
            queue.append((evo, stage + 1))

    return stages

def get_sorted_family(url):
    stages = parse_evolution_chain(url)
    flattened = format_family(stages)
    dex_number = get_species_dex_number(species_name=flattened[0])
    return dex_number, flattened

def main():
    chains = get_all_evolution_chains()
    all_species = []

    print(f"Found {len(chains)} evolution chains...\n")

    for i, chain in enumerate(chains, start=1):
        try:
            dex_num, species_list = get_sorted_family(chain["url"])
            all_species.append((dex_num, species_list))
            for species in species_list:
                print(display_name(species))
            time.sleep(0.2)  # Be kind to the API
        except Exception as e:
            print(f"[{i}/{len(chains)}] Error: {e}")

    # Sort by National Dex number of base species
    all_species.sort(key=lambda x: x[0])

    # Flatten and write to file
    with open("pokedex_by_family.txt", "w") as f:
        for _, species_list in all_species:
            for species in species_list:
                f.write(display_name(species) + "\n")

    # Save caches
    with open(CACHE_FILE, "w") as f:
        json.dump(species_cache, f)

    with open(VARIANT_CACHE_FILE, "w") as f:
        json.dump(variant_cache, f)

    print("\n✅ Saved to pokedex_by_family.txt")

if __name__ == "__main__":
    main()