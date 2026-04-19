# 6-tier Brawl Stars rarity system:
#   RARE  — basic mechanics, beginner-friendly
#   SR    — Super Rare: slightly more unique abilities
#   EPIC  — unique main attacks or supers
#   MYTH  — Mythic: highly unique mechanics not seen in lower tiers
#   LEG   — Legendary: most complex / environmental / special-form mechanics
#   ULEG  — Ultra Legendary: newest ultra-high-cost brawlers
RARITY = {
    # Rare
    "shelly": "RARE", "nita": "RARE", "colt": "RARE", "bull": "RARE", "brock": "RARE",
    "el primo": "RARE", "elprimo": "RARE", "barley": "RARE", "poco": "RARE",

    # Super Rare
    "rico": "SR", "darryl": "SR", "penny": "SR", "jacky": "SR", "gus": "SR",
    "rosa": "SR", "jessie": "SR", "dynamike": "SR", "tick": "SR",
    "8-bit": "SR", "8bit": "SR", "emz": "SR", "carl": "SR", "pam": "SR",

    # Epic
    "piper": "EPIC", "frank": "EPIC", "bibi": "EPIC", "edgar": "EPIC", "stu": "EPIC",
    "bea": "EPIC", "nani": "EPIC", "griff": "EPIC", "grom": "EPIC", "bonnie": "EPIC",
    "hank": "EPIC", "pearl": "EPIC", "maisie": "EPIC", "willow": "EPIC", "mandy": "EPIC",
    "buster": "EPIC", "larry": "EPIC", "gray": "EPIC", "angelo": "EPIC",

    # Mythic
    "mortis": "MYTH", "tara": "MYTH", "gene": "MYTH", "sprout": "MYTH", "fang": "MYTH",
    "squeak": "MYTH", "byron": "MYTH", "mr. p": "MYTH", "mrp": "MYTH", "max": "MYTH",
    "moe": "MYTH", "janet": "MYTH", "clancy": "MYTH", "melodie": "MYTH", "juju": "MYTH",
    "lily": "MYTH", "berry": "MYTH", "shade": "MYTH", "finx": "MYTH", "draco": "MYTH",
    "ollie": "MYTH", "meeple": "MYTH", "lumi": "MYTH", "r-t": "MYTH", "rt": "MYTH",
    "eve": "MYTH",

    # Legendary
    "spike": "LEG", "crow": "LEG", "leon": "LEG", "sandy": "LEG", "amber": "LEG",
    "meg": "LEG", "surge": "LEG", "chester": "LEG", "kenji": "LEG", "cordelius": "LEG",
    "charlie": "LEG", "doug": "LEG",

    # Ultra Legendary
    "kaze": "ULEG", "sirius": "ULEG",

    # Skins / alt forms — map to source rarity
    "bullhorn": "RARE", "shellstrike": "RARE", "coltrane": "RARE", "brockade": "RARE",
    "spikemoss": "LEG", "barleytop": "RARE", "jessamine": "SR", "nitroshade": "RARE",
    "el primate": "RARE", "elprimate": "RARE", "mortis g": "MYTH",
    "pocotune": "RARE", "bosun": "RARE", "piperose": "EPIC", "pamela": "SR",
    "darrylite": "SR", "pennant": "SR", "taralei": "LEG", "crowstep": "LEG",
    "rico-7": "SR", "rico7": "SR",
}

ROLE = {
    "shelly": "DAMAGE", "nita": "TANK", "colt": "MARKSMAN", "bull": "TANK",
    "brock": "ARTILLERY", "el primo": "TANK", "barley": "ARTILLERY", "poco": "SUPPORT",
    "rosa": "TANK", "jessie": "SUMMONER", "dynamike": "ARTILLERY", "tick": "ARTILLERY",
    "8-bit": "MARKSMAN", "penny": "ARTILLERY", "carl": "DAMAGE", "jacky": "TANK",
    "gus": "SUPPORT", "emz": "DAMAGE", "stu": "DAMAGE",
    "piper": "MARKSMAN", "pam": "HEALER", "frank": "TANK", "bibi": "TANK", "bea": "MARKSMAN",
    "nani": "MARKSMAN", "edgar": "ASSASSIN", "griff": "DAMAGE", "grom": "ARTILLERY",
    "bonnie": "DAMAGE", "fang": "ASSASSIN", "eve": "SUMMONER", "janet": "MARKSMAN",
    "clancy": "MARKSMAN", "mandy": "MARKSMAN", "moe": "MARKSMAN", "lumi": "DAMAGE",
    "mortis": "ASSASSIN", "tara": "CONTROLLER", "gene": "CONTROLLER", "max": "SUPPORT",
    "mr. p": "SUMMONER", "sprout": "ARTILLERY", "byron": "HEALER", "squeak": "ARTILLERY",
    "buster": "TANK", "gray": "CONTROLLER", "r-t": "DAMAGE", "willow": "CONTROLLER",
    "maisie": "DAMAGE", "hank": "TANK", "pearl": "DAMAGE", "finx": "CONTROLLER",
    "shade": "ASSASSIN", "berry": "HEALER", "angelo": "MARKSMAN", "larry": "DAMAGE",
    "melodie": "ASSASSIN", "juju": "CONTROLLER", "draco": "TANK", "lily": "ASSASSIN",
    "leon": "ASSASSIN", "spike": "DAMAGE", "crow": "ASSASSIN", "sandy": "SUPPORT",
    "amber": "DAMAGE", "meg": "MARKSMAN", "surge": "DAMAGE", "chester": "DAMAGE",
    "kenji": "ASSASSIN", "cordelius": "ASSASSIN", "charlie": "CONTROLLER", "doug": "HEALER",
    "kaze": "ASSASSIN", "sirius": "MARKSMAN",
    "rico": "DAMAGE", "darryl": "TANK",
    "bullhorn": "ARTILLERY", "shellstrike": "DAMAGE", "coltrane": "MARKSMAN",
    "brockade": "ARTILLERY", "spikemoss": "DAMAGE", "barleytop": "ARTILLERY",
    "jessamine": "SUMMONER", "nitroshade": "ASSASSIN", "pocotune": "HEALER",
    "bosun": "TRAP", "piperose": "MARKSMAN", "pamela": "HEALER", "darrylite": "TANK",
    "pennant": "DAMAGE",
}


RARITY_LABEL = {
    "RARE": "Rare",
    "SR":   "Super Rare",
    "EPIC": "Epic",
    "MYTH": "Mythic",
    "LEG":  "Legendary",
    "ULEG": "Ultra Legendary",
}


def rarity_of(brawler: str) -> str:
    return RARITY.get(brawler.lower(), "RARE")


def role_of(brawler: str) -> str:
    return ROLE.get(brawler.lower(), "DAMAGE")


def rarity_rank(rarity: str) -> int:
    return {"ULEG": 0, "LEG": 1, "MYTH": 2, "EPIC": 3, "SR": 4, "RARE": 5}.get(rarity, 6)


def rarity_label(rarity: str) -> str:
    return RARITY_LABEL.get(rarity, rarity)


def display_name(brawler: str) -> str:
    return brawler.replace("_", " ").title()


def short_code(brawler: str) -> str:
    n = brawler.strip()
    if len(n) >= 2:
        return n[:2].upper()
    return (n + "X")[:2].upper()
