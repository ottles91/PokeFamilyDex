# Pokedex by Family

This Python script uses the [PokéAPI](https://pokeapi.co/) to generate a National Dex–ordered list of all Pokémon grouped by evolutionary family, including regional forms and variations that are storable in Pokémon HOME.

## Features

- Groups Pokémon by evolutionary family
- Orders each family by evolutionary stage and National Dex number
- Includes regional variants (Alolan, Galarian, Hisuian, etc.)
- Includes Paradox Pokémon, Treasures of Ruin, and other modern edge cases
- Excludes forms that cannot be stored in HOME (e.g. Mega, Gmax, cosplay Pikachu)
- Caches data locally to reduce API calls
- Outputs a flat, one-species-per-line `.txt` file with nicely formatted names

## Example Output

Bulbasaur
Ivysaur
Venusaur
Meowth
Meowth (Alola)
Meowth (Galar)
Persian
Persian (Alola)
Perrserker

## Requirements

- Python 3.7+
- [`requests`](https://pypi.org/project/requests/)

Install dependencies:

```bash
pip install requests
```

## Running the Script

```bash
python pokedex_by_family.py
```

Output will be saved to:
pokedex_by_family.txt

## Notes:

- Cached data is stored in species_cache.json and variant_cache.json
- The script respects API rate limits by inserting a small delay between calls
- Designed to assist Pokémon HOME box organization and tracking

## Liscense

No formal license is applied, but credit is appreciated!
