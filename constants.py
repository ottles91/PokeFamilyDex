# Filenames for storing cached data locally
CACHE_FILE = "species_cache.json"          # Caches species dex numbers to reduce API calls
VARIANT_CACHE_FILE = "variant_cache.json"  # Caches known form variants of each species
API_BASE = "https://pokeapi.co/api/v2/"    # Base URL for all PokeAPI requests

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