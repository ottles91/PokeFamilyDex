import requests
import time
import json
import os
from collections import defaultdict

CACHE_FILE = "species_cache.json"
API_BASE = "https://pokeapi.co/api/v2/"

species_cache = {}

# Load cache from file if it exists
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        try:
            species_cache = json.load(f)
        except json.JSONDecodeError:
            species_cache = {}

def get_all_evolution_chains():
    url = f"{API_BASE}evolution-chain/?limit=9999"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["results"]

def get_species_dex_number(species_url=None, species_name=None):
    if species_name:
        if species_name in species_cache:
            return species_cache[species_name]
        url = f"{API_BASE}pokemon-species/{species_name}"
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
    """Returns alternate forms like alolan/galarian variants"""
    url = f"{API_BASE}pokemon-species/{species_name}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    variants = set()
    for variety in data["varieties"]:
        name = variety["pokemon"]["name"]
        if not variety["is_default"]:
            if any(region in name for region in ["alolan", "galarian", "hisuian", "paldean"]):
                variants.add(name)
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

    for stage in sorted(stages.keys()):
        forms = stages[stage]
        forms.sort(key=lambda name: get_species_dex_number(species_name=name))
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
        
    print("\n✅ Saved to pokedex_by_family.txt")

if __name__ == "__main__":
    main()