# Pokedex by Family

This Python script uses the [PokéAPI](https://pokeapi.co/) to generate a National Dex–ordered list of all Pokémon grouped by evolutionary family. It includes regional forms and alternate species variations that are storable in **Pokémon HOME**, while excluding special forms like Mega Evolutions and Gigantamax that cannot be placed in **Pokemon Home**.

## Features

- Groups Pokémon by **evolutionary family**, organized by stage
- Orders Pokémon by **National Dex number** within each family
- Includes **regional variants** (Alolan, Galarian, Hisuian, etc.)
- Eloquently handles Paradox Pokémon, Ultra Beasts, alternate forms, regional variants and other edge cases
- Excludes non-boxable forms (e.g. Mega, fused Pokemon, Cosplay Pikachu, seasonal castforms)
- Caches species and variant data locally to reduce API calls
- Outputs a clean `.txt` file — one species per line — with nicely formatted names

## Example Output

`Meowth (Alola)  
Meowth (Galar)  
Persian  
Persian (Alola)  
Perrserker`

## Requirements

- Python 3.7+
- [`requests`](https://pypi.org/project/requests/)

Install requests:

```bash
pip install requests
```

## Running the Script

```bash
python pokedex_by_family.py
```

Output will be saved to:
`pokedex_by_family.txt`

## Notes:

- Cached data is stored in species_cache.json and variant_cache.json
- The script respects API rate limits by inserting a small delay between calls
- Designed to assist Pokémon HOME box organization and tracking

## Known Limitations

This is an initial implementation and currently doesn't correctly collect data for the following Pokemon:

- Burmy Plant Cloak
- Burmy Sandy Cloak
- Burmy Trash Cloak
- Wormadam Plant Cloak
- Squawkabilly Green Plumage
- Squawkabilly White Plumage
- All Gigantamax Pokemon

## Liscense

License: MIT
