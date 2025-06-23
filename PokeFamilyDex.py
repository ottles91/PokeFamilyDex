import requests
import time

API_BASE = "https://pokeapi.co/api/v2/"

def get_all_evolution_chains():
    url = f"{API_BASE}evolution-chain/?limit=9999"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["results"]

def get_species_dex_number(species_url):
    response = requests.get(species_url)
    response.raise_for_status()
    data = response.json()
    for entry in data["pokedex_numbers"]:
        if entry["pokedex"]["name"] == "national":
            return entry["entry_number"]
    return float("inf")

def traverse_evolution_chain(chain_node):
    species_name = chain_node["species"]["name"]
    evolutions = chain_node["evolves_to"]
    if not evolutions:
        return [[species_name]]
    all_branches = []
    for evo in evolutions:
        subpaths = traverse_evolution_chain(evo)
        for path in subpaths:
            all_branches.append([species_name] + path)
    return all_branches

def get_species_variants(species_name):
    """Returns other box-storable variants like Alolan or Galarian forms"""
    url = f"{API_BASE}pokemon-species/{species_name}"
    response = requests.get(url)
    response.raise_for_status()
    species_data = response.json()
    
    variants = set()
    for variety in species_data["varieties"]:
        poke_name = variety["pokemon"]["name"]
        if not variety["is_default"]:
            # Check if it's a HOME-storable form (e.g., alolan-raichu)
            if any(region in poke_name for region in ["alolan", "galarian", "hisuian", "paldean"]):
                variants.add(poke_name)
    return variants

def get_sorted_family(chain_url):
    response = requests.get(chain_url)
    response.raise_for_status()
    chain_data = response.json()["chain"]
    family_paths = traverse_evolution_chain(chain_data)

    # Get all species and regional variants
    flat_species = set()
    for path in family_paths:
        flat_species.update(path)
    for name in list(flat_species):
        flat_species.update(get_species_variants(name))

    # Get Dex number for sorting
    base_species = chain_data["species"]["url"]
    dex_num = get_species_dex_number(base_species)

    return dex_num, sorted(flat_species, key=lambda x: x)

def main():
    chains = get_all_evolution_chains()
    all_families = []

    print(f"Found {len(chains)} evolution chains...\n")

    for i, chain in enumerate(chains, start=1):
        try:
            dex_num, family = get_sorted_family(chain["url"])
            all_families.append((dex_num, family))

            # Real-time feedback
            display_name = " > ".join(family[:-1]) + f" / {family[-1]}" if len(family) > 1 else family[0]
            print(f"[{i}/{len(chains)}] {display_name}")
            
            time.sleep(0.2)  # Be polite to the API
        except Exception as e:
            print(f"[{i}/{len(chains)}] Error processing chain {chain['url']}: {e}")

    # Sort and write to file
    all_families.sort(key=lambda tup: tup[0])

    with open("pokedex_by_family.txt", "w") as f:
        for _, family in all_families:
            if len(family) == 1:
                f.write(f"{family[0]}\n")
            else:
                base = " > ".join(family[:-1])
                f.write(f"{base} / {family[-1]}\n")

    print("Saved to pokedex_by_family.txt")

if __name__ == "__main__":
    main()