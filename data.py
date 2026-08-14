import os
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Regulation di partenza del sito. Non è una costante scritta a mano: è **la prima**
# di data/regulations.json, cioè lo stesso criterio del fallback `regs[0]` che tutte
# le route usano già quando l'id richiesto non esiste. Per cambiare il default si
# sposta una voce in cima al file, e non si tocca il codice.
REGULATION_DEFAULT_EMERGENZA = "ma"   # se il registro non è leggibile esiste solo questa


def regulation_default():
    """Id della regulation di partenza: la prima del registro."""
    try:
        with open(os.path.join(DATA_DIR, "regulations.json"), encoding="utf-8") as f:
            return json.load(f)[0]["id"]
    except Exception:
        return REGULATION_DEFAULT_EMERGENZA


def _load_roster():
    """Carica roster e mega_map da data/roster_ma.json.
    Se il file non esiste, usa liste vuote come fallback."""
    path = os.path.join(DATA_DIR, "roster_ma.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d.get("pokemon", []), d.get("mega_map", {})
    except Exception as e:
        print(f"[WARN] Impossibile caricare roster_ma.json: {e}")
        return [], {}

REG_MA_ROSTER, POKEMON_TO_MEGA = _load_roster()
MEGA_EVOLUTIONS_MA = sorted(set(m for v in POKEMON_TO_MEGA.values() for m in v))

NATURES = [
    "Hardy","Lonely","Brave","Adamant","Naughty","Bold","Docile","Relaxed","Impish","Lax",
    "Timid","Hasty","Serious","Jolly","Naive","Modest","Mild","Quiet","Bashful","Rash",
    "Calm","Gentle","Sassy","Careful","Quirky",
]

NATURE_EFFECTS = {
    "Lonely":("+Atk","-Def"),"Brave":("+Atk","-Spe"),"Adamant":("+Atk","-SpA"),"Naughty":("+Atk","-SpD"),
    "Bold":("+Def","-Atk"),"Relaxed":("+Def","-Spe"),"Impish":("+Def","-SpA"),"Lax":("+Def","-SpD"),
    "Timid":("+Spe","-Atk"),"Hasty":("+Spe","-Def"),"Jolly":("+Spe","-SpA"),"Naive":("+Spe","-SpD"),
    "Modest":("+SpA","-Atk"),"Mild":("+SpA","-Def"),"Quiet":("+SpA","-Spe"),"Rash":("+SpA","-SpD"),
    "Calm":("+SpD","-Atk"),"Gentle":("+SpD","-Def"),"Sassy":("+SpD","-Spe"),"Careful":("+SpD","-SpA"),
}

PYTHON_TOPICS = {
    "Introduzione":["Python HOME","Python Intro","Python Get Started","Python Syntax","Python Comments","Python Variables","Python Data Types"],
    "Stringhe e I/O":["Python Strings","Python String Methods","Python String Formatting","Python User Input"],
    "Operatori e Controllo":["Python Operators","Python If...Else","Python Match","Python While Loops","Python For Loops"],
    "Strutture Dati":["Python Lists","Python Tuples","Python Sets","Python Dictionaries"],
    "Funzioni e Scope":["Python Functions","Python Lambda","Python Arrays","Python Scope"],
    "OOP":["Python Classes","Python Inheritance","Python Iterators","Python Polymorphism","Python Encapsulation"],
    "Moduli e File":["Python Modules","Python Dates","Python Math","Python JSON","Python RegEx","Python PIP","Python File Open","Python File Write","Python File Delete"],
    "Error Handling":["Python Try...Except","Python Exception Handling","Python User-Defined Exceptions"],
    "Avanzato":["Python Decorators","Python Generators","Python Context Managers","Python Threading","Python Multiprocessing"],
    "Standard Library":["Python os Module","Python sys Module","Python collections","Python itertools","Python functools","Python pathlib","Python argparse"],
}

PC_CATEGORIES    = ["CPU","GPU","Motherboard","RAM","Storage SSD","Storage HDD","PSU","Case","CPU Cooler","Case Fan","Monitor","Tastiera","Mouse","Cuffie","Webcam","Scheda Audio","Altro"]
# Le sezioni su cui si danno i permessi. `slug` è il nome del **blueprint** Flask:
# è così che il controllo in `app.py` sa a quale sezione appartiene una richiesta
# senza dover elencare le route una per una. Il Pokémon ne ha due, perché le API
# stanno in un blueprint separato ma sono la stessa sezione per chi guarda.
# La Dashboard non è qui di proposito: è la pagina di arrivo dopo il login e la
# vedono tutti, altrimenti chi entra si troverebbe davanti un errore.
SEZIONI = [
    ("gaming",     "🎮 Gaming",         "/gaming",    ["gaming"]),
    ("pokemon",    "🐉 Pokémon VGC",    "/pokemon",   ["pokemon", "api_pokemon"]),
    ("arduino",    "🔌 Arduino",        "/arduino",   ["arduino"]),
    ("python",     "🐍 Python Tracker", "/python",    ["python_tracker"]),
    ("pcbuilder",  "🖥️ PC Builder",     "/pcbuilder", ["pcbuilder"]),
]
SEZIONI_SLUG = [s[0] for s in SEZIONI]
# blueprint -> sezione, ricavata da SEZIONI così le due non possono divergere
BLUEPRINT_SEZIONE = {bp: slug for slug, _, _, bps in SEZIONI for bp in bps}

# ── Categorie di oggetti e abilità ───────────────────────────────────────────
# ⚠️ La **chiave** è il dato: sta in `category` dentro il catalogo, è il `value` delle
# tendine e il suffisso delle classi CSS (`cat-berry`, `cat-weather_override`). Non si
# tocca. Qui c'è solo l'etichetta italiana, che poi passa da `t()` come tutto il resto.
# Sta in un posto solo perché la usano tre schermate: i due editor e il catalogo.
CATEGORIE_OGGETTI = {
    "berry":      "Bacca",
    "choice":     "Scelta obbligata",
    "conditional": "Condizionale",
    "damage":     "Danno",
    "defensive":  "Difensivo",
    "healing":    "Cura",
    "orb":        "Sfera",
    "support":    "Supporto",
    "survival":   "Sopravvivenza",
    "terrain":    "Terreno",
    "type_boost": "Bonus di tipo",
    "utility":    "Utilità",
    "weather":    "Meteo",
    # ⚠️ `other` mancava, ed è **339 oggetti su 397**: la categoria di gran lunga più
    # comune. Senza, il badge e il filtro ricadevano sulla chiave grezza, e la tendina
    # non permetteva di filtrare l'86% del catalogo. Trovato il 13/08/2026 traducendo.
    "other":      "altro",
}
CATEGORIE_ABILITA = {
    "none":              "nessun effetto",
    "weather_override":  "impone il meteo",
    "weather_setter":    "evoca il meteo",
    "weather_boost":     "bonus col meteo",
    "type_immunity":     "immunità di tipo",
    "damage_reduction":  "riduzione del danno",
    "stab_boost":        "bonus STAB",
    "stat_modifier":     "modifica una stat",
    "power_boost":       "bonus di potenza",
    "speed_boost":       "bonus di Velocità",
    "status_boost":      "bonus con lo stato",
    "stat_boost_low_hp": "bonus a PS bassi",
    "other":             "altro",
}

GAME_STATUSES    = ["In corso","Completato","Pausa","Wishlist","Abbandonato"]
GAME_PLATFORMS   = ["PC","PlayStation 5","PlayStation 4","Nintendo Switch","Xbox","Mobile","Altro"]
ARDUINO_STATUSES = ["Idea","In sviluppo","Completato","Pubblicato"]
ARDUINO_BOARDS   = ["Arduino Uno","Arduino Nano","Arduino Mega","Arduino Leonardo","Arduino Pro Mini","ESP8266","ESP32","Raspberry Pi","Altro"]

SLUG_OVERRIDES = {
    "mr-rime": "mr-rime",
    "tauros-paldea-combat": "tauros-paldea-combat-breed",
    "tauros-paldea-blaze": "tauros-paldea-blaze-breed",
    "tauros-paldea-aqua": "tauros-paldea-aqua-breed",
    "meowstic-m": "meowstic-male",
    "meowstic-f": "meowstic-female",
    "basculegion-m": "basculegion-male",
    "basculegion-f": "basculegion-female",
    "mega-venusaur": "venusaur-mega",
    "mega-charizard-x": "charizard-mega-x",
    "mega-charizard-y": "charizard-mega-y",
    "mega-blastoise": "blastoise-mega",
    "mega-beedrill": "beedrill-mega",
    "mega-pidgeot": "pidgeot-mega",
    "mega-alakazam": "alakazam-mega",
    "mega-slowbro": "slowbro-mega",
    "mega-gengar": "gengar-mega",
    "mega-kangaskhan": "kangaskhan-mega",
    "mega-pinsir": "pinsir-mega",
    "mega-gyarados": "gyarados-mega",
    "mega-aerodactyl": "aerodactyl-mega",
    "mega-meganium": "meganium-mega",
    "mega-ampharos": "ampharos-mega",
    "mega-scizor": "scizor-mega",
    "mega-heracross": "heracross-mega",
    "mega-houndoom": "houndoom-mega",
    "mega-tyranitar": "tyranitar-mega",
    "mega-blaziken": "blaziken-mega",
    "mega-gardevoir": "gardevoir-mega",
    "mega-mawile": "mawile-mega",
    "mega-aggron": "aggron-mega",
    "mega-medicham": "medicham-mega",
    "mega-manectric": "manectric-mega",
    "mega-sharpedo": "sharpedo-mega",
    "mega-camerupt": "camerupt-mega",
    "mega-altaria": "altaria-mega",
    "mega-banette": "banette-mega",
    "mega-absol": "absol-mega",
    "mega-glalie": "glalie-mega",
    "mega-salamence": "salamence-mega",
    "mega-metagross": "metagross-mega",
    "mega-latias": "latias-mega",
    "mega-latios": "latios-mega",
    "mega-garchomp": "garchomp-mega",
    "mega-lucario": "lucario-mega",
    "mega-abomasnow": "abomasnow-mega",
    "mega-gallade": "gallade-mega",
    "mega-audino": "audino-mega",
    "mega-diancie": "diancie-mega",
    "mega-sableye": "sableye-mega",
    "mega-lopunny": "lopunny-mega",
    "mega-steelix": "steelix-mega",
    "mega-clefable": "clefable-mega",
    "mega-dragonite": "dragonite-mega",
    "mega-excadrill": "excadrill-mega",
    "mega-feraligatr": "feraligatr-mega",
    "mega-froslass": "froslass-mega",
    "mega-golurk": "golurk-mega",
    "mega-greninja": "greninja-mega",
    "mega-hawlucha": "hawlucha-mega",
    "mega-skarmory": "skarmory-mega",
    "mega-starmie": "starmie-mega",
    "mega-victreebel": "victreebel-mega",
    "mega-drampa": "drampa-mega",
    "mega-scovillain": "scovillain-mega",
    "mega-chesnaught": "chesnaught-mega",
    "mega-delphox": "delphox-mega",
    "mega-emboar": "emboar-mega",
    "mega-glimmora": "glimmora-mega",
    "mega-chandelure": "chandelure-mega",
    "mega-meowstic-(male)": "meowstic-male",
    "mega-meowstic-(f)": "meowstic-female",
    "mega-meowstic-(m)": "meowstic-male",
    "mega-floette": "floette-eternal",
    "eternal-flower-floette": "floette-eternal",
    "mega-crabominable": "crabominable",
    "alolan-ninetales": "ninetales-alola",
    "alolan-raichu": "raichu-alola",
    "hisuian-arcanine": "arcanine-hisui",
    "hisuian-typhlosion": "typhlosion-hisui",
    "hisuian-samurott": "samurott-hisui",
    "hisuian-decidueye": "decidueye-hisui",
    "hisuian-zoroark": "zoroark-hisui",
    "hisuian-avalugg": "avalugg-hisui",
    "hisuian-goodra": "goodra-hisui",
    "galarian-slowbro": "slowbro-galar",
    "galarian-slowking": "slowking-galar",
    "heat-rotom": "rotom-heat",
    "wash-rotom": "rotom-wash",
    "frost-rotom": "rotom-frost",
    "fan-rotom": "rotom-fan",
    "mow-rotom": "rotom-mow",
    "palafin-(hero-form)": "palafin-hero",
    "palafin-(zero-form)": "palafin",
    "aegislash-(blade-forme)": "aegislash-blade",
    "aegislash-(shield-forme)": "aegislash-shield",
    "meowstic-(male)": "meowstic-male",
    "meowstic-(female)": "meowstic-female",
    "basculegion-(male)": "basculegion-male",
    "basculegion-(female)": "basculegion-female",
    "morpeko-(full-belly-mode)": "morpeko",
    "gourgeist-(average)": "gourgeist",
    "gourgeist-(small)": "gourgeist-small",
    "gourgeist-(large)": "gourgeist-large",
    "gourgeist-(super)": "gourgeist-super",
}

# `ABILITIES_CALC` stava qui: elenco di 20 nomi inglesi delle abilità "supportate
# dal calcolatore". Rimossa l'11/08/2026 perché **non la importava nessuno**: chi
# marca le abilità che incidono è `abilityIncideSulDanno()` in calcolatori-core.js,
# che legge il blocco `effect` del catalogo — quindi l'elenco non solo era inerte,
# era anche destinato a divergere dai dati veri.

# Carica base stats dal catalogo. data/catalog/pokemon.json è il database di
# default completo; data/pokemon_catalog.json resta come fallback finché c'è.
def _load_champions_bst():
    for path in (os.path.join(DATA_DIR, "catalog", "pokemon.json"),
                 os.path.join(DATA_DIR, "pokemon_catalog.json")):
        try:
            with open(path, encoding="utf-8") as f:
                catalog = json.load(f)
            print(f"[DATA] Catalogo caricato: {len(catalog)} Pokémon da {os.path.basename(path)}")
            return catalog
        except Exception:
            continue
    if True:
        print("[DATA] Errore catalogo: nessun file leggibile")
        return {
            'pikachu': {'base_stats': {'hp':35,'atk':55,'def':40,'spa':50,'spd':50,'spe':90}, 'types':['Elettro'], 'abilities':[], 'moves':[]},
            'mimikyu': {'base_stats': {'hp':90,'atk':72,'def':90,'spa':50,'spd':94,'spe':96}, 'types':['Spettro','Folletto'], 'abilities':[], 'moves':[]},
        }

CHAMPIONS_BST = _load_champions_bst()