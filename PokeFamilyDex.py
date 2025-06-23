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

def format_family(stages):
    output = []

    def sort_key(name):
        # Base name comes first
        region_order = ["", "alolan", "galarian", "hisuian", "paldean", "white", "black", "red", "blue", "striped"]
        for i, region in enumerate(region_order):
            if name.startswith(region + "-"):
                return (i, get_species_dex_number(species_name=name))
        return (len(region_order), get_species_dex_number(species_name=name))

    for stage in sorted(stages.keys()):
        forms = list(set(stages[stage]))  # de-dupe just in case
        forms.sort(key=sort_key)
        if len(forms) == 1:
            output.append(forms[0])
        else:
            output.append(" / ".join(forms))
    return " > ".join(output)

def get_sorted_family(chain_url):
    response = requests.get(chain_url)
    response.raise_for_status()
    chain_data = response.json()["chain"]
    stages = group_by_stage(chain_data)

    # Add variants to each stage
    for stage in list(stages.keys()):
        extra_forms = set()
        for name in stages[stage]:
            extra_forms.update(get_variants(name))
        stages[stage].extend(extra_forms)

    # Get Dex number for sorting
    base_species_url = chain_data["species"]["url"]
    dex_num = get_species_dex_number(base_species_url)

    return dex_num, format_family(stages)

def main():
    chains = get_all_evolution_chains()
    all_families = []

    print(f"Found {len(chains)} evolution chains...\n")

    for i, chain in enumerate(chains, start=1):
        try:
            dex_num, family_str = get_sorted_family(chain["url"])
            all_families.append((dex_num, family_str))
            print(f"[{i}/{len(chains)}] {family_str}")
            time.sleep(0.2)  # Be kind to the API
        except Exception as e:
            print(f"[{i}/{len(chains)}] Error: {e}")

    # Sort by National Dex number
    all_families.sort(key=lambda x: x[0])

    with open("pokedex_by_family.txt", "w") as f:
        for _, line in all_families:
            f.write(line + "\n")

    # Save updated species_cache
    with open(CACHE_FILE, "w") as f:
        json.dump(species_cache, f)

    # Save updated variant cache
    with open(VARIANT_CACHE_FILE, "w") as f:
        json.dump(variant_cache, f)

    print("\n✅ Saved to pokedex_by_family.txt")

if __name__ == "__main__":
    main()