from flask import Blueprint, jsonify
import os, json, re
from data import DATA_DIR

bp = Blueprint('api_pokemon', __name__, url_prefix='/api')

# Carica catalogo una volta sola all'avvio
_catalog_path = os.path.join(DATA_DIR, "pokemon_catalog.json")
try:
    with open(_catalog_path, encoding="utf-8") as _f:
        POKEMON_CATALOG = json.load(_f)
except Exception as e:
    print(f"[API] pokemon_catalog.json error: {e}")
    POKEMON_CATALOG = {}

# Sprite fixes diretti (URL completo)
# Usato per: mimikyu, e mega custom fan-made che non esistono online
# (per le mega custom usiamo lo sprite del Pokémon base come fallback)
SPRITE_FIXES = {
    'mimikyu':          'https://raw.githubusercontent.com/msikma/pokesprite/master/pokemon/regular/mimikyu.png',
    'mimikyu-busted':   'https://raw.githubusercontent.com/msikma/pokesprite/master/pokemon/regular/mimikyu-busted.jpg',
    # ── Mega custom fan-made (non esistono sprite online) → fallback sprite base ──
    'meganium-mega':    'https://img.pokemondb.net/sprites/home/normal/meganium.png',
    'feraligatr-mega':  'https://img.pokemondb.net/sprites/home/normal/feraligatr.png',
    'dragonite-mega':   'https://img.pokemondb.net/sprites/home/normal/dragonite.png',
    'skarmory-mega':    'https://img.pokemondb.net/sprites/home/normal/skarmory.png',
    'starmie-mega':     'https://img.pokemondb.net/sprites/home/normal/starmie.png',
    'victreebel-mega':  'https://img.pokemondb.net/sprites/home/normal/victreebel.png',
    'clefable-mega':    'https://img.pokemondb.net/sprites/home/normal/clefable.png',
    'machamp-mega':     'https://img.pokemondb.net/sprites/home/normal/machamp.png',
    'emboar-mega':      'https://img.pokemondb.net/sprites/home/normal/emboar.png',
    'excadrill-mega':   'https://img.pokemondb.net/sprites/home/normal/excadrill.png',
    'golurk-mega':      'https://img.pokemondb.net/sprites/home/normal/golurk.png',
    'chandelure-mega':  'https://img.pokemondb.net/sprites/home/normal/chandelure.png',
    'froslass-mega':    'https://img.pokemondb.net/sprites/home/normal/froslass.png',
    'chesnaught-mega':  'https://img.pokemondb.net/sprites/home/normal/chesnaught.png',
    'delphox-mega':     'https://img.pokemondb.net/sprites/home/normal/delphox.png',
    'greninja-mega':    'https://img.pokemondb.net/sprites/home/normal/greninja.png',
    'hawlucha-mega':    'https://img.pokemondb.net/sprites/home/normal/hawlucha.png',
    'drampa-mega':      'https://img.pokemondb.net/sprites/home/normal/drampa.png',
    'glimmora-mega':    'https://img.pokemondb.net/sprites/home/normal/glimmora.png',
    'scovillain-mega':  'https://img.pokemondb.net/sprites/home/normal/scovillain.png',
    'crabominable-mega':'https://img.pokemondb.net/sprites/home/normal/crabominable.png',
    'chimecho-mega':    'https://img.pokemondb.net/sprites/home/normal/chimecho.png',
    'floette-mega':     'https://img.pokemondb.net/sprites/home/normal/floette-eternal.png',
}

# Base URL pokesprite (non più usato per hisui/mega, mantenuto per eventuali usi futuri)
POKESPRITE_BASE = "https://raw.githubusercontent.com/msikma/pokesprite/master/pokemon/regular"

# POKESPRITE_SLUGS: attualmente vuoto, mantenuto per compatibilità futura
# Le mega canoniche usano pokemondb, le mega custom usano SPRITE_FIXES
POKESPRITE_SLUGS: set = set()

# Mappa nome.lower() → slug pokemondb/pokesprite
# Supporta sia il formato "Heat Rotom" che "Rotom-Heat" (da roster)
FORM_SPRITE_SLUGS = {
    # ── Mega canoniche (presenti su pokemondb) ──────────────────────────────────────
    'mega venusaur':        'venusaur-mega',
    'mega charizard x':     'charizard-mega-x',
    'mega charizard y':     'charizard-mega-y',
    'mega blastoise':       'blastoise-mega',
    'mega beedrill':        'beedrill-mega',
    'mega pidgeot':         'pidgeot-mega',
    'mega alakazam':        'alakazam-mega',
    'mega slowbro':         'slowbro-mega',
    'mega gengar':          'gengar-mega',
    'mega kangaskhan':      'kangaskhan-mega',
    'mega pinsir':          'pinsir-mega',
    'mega gyarados':        'gyarados-mega',
    'mega aerodactyl':      'aerodactyl-mega',
    'mega ampharos':        'ampharos-mega',
    'mega scizor':          'scizor-mega',
    'mega heracross':       'heracross-mega',
    'mega houndoom':        'houndoom-mega',
    'mega tyranitar':       'tyranitar-mega',
    'mega gardevoir':       'gardevoir-mega',
    'mega sableye':         'sableye-mega',
    'mega aggron':          'aggron-mega',
    'mega medicham':        'medicham-mega',
    'mega manectric':       'manectric-mega',
    'mega sharpedo':        'sharpedo-mega',
    'mega camerupt':        'camerupt-mega',
    'mega altaria':         'altaria-mega',
    'mega absol':           'absol-mega',
    'mega glalie':          'glalie-mega',
    'mega salamence':       'salamence-mega',
    'mega metagross':       'metagross-mega',
    'mega latias':          'latias-mega',
    'mega latios':          'latios-mega',
    'mega lucario':         'lucario-mega',
    'mega abomasnow':       'abomasnow-mega',
    'mega lopunny':         'lopunny-mega',
    'mega garchomp':        'garchomp-mega',
    'mega gallade':         'gallade-mega',
    'mega audino':          'audino-mega',
    'mega steelix':         'steelix-mega',
    'mega sceptile':        'sceptile-mega',
    'mega blaziken':        'blaziken-mega',
    'mega swampert':        'swampert-mega',
    'mega mawile':          'mawile-mega',
    'mega banette':         'banette-mega',
    'mega diancie':         'diancie-mega',
    'mega rayquaza':        'rayquaza-mega',
    'mega mewtwo x':        'mewtwo-mega-x',
    'mega mewtwo y':        'mewtwo-mega-y',
    # ── Mega custom fan-made (slug → SPRITE_FIXES usa sprite base) ─────────────────
    'mega skarmory':        'skarmory-mega',
    'mega dragonite':       'dragonite-mega',
    'mega emboar':          'emboar-mega',
    'mega excadrill':       'excadrill-mega',
    'mega golurk':          'golurk-mega',
    'mega chandelure':      'chandelure-mega',
    'mega froslass':        'froslass-mega',
    'mega chesnaught':      'chesnaught-mega',
    'mega delphox':         'delphox-mega',
    'mega greninja':        'greninja-mega',
    'mega hawlucha':        'hawlucha-mega',
    'mega drampa':          'drampa-mega',
    'mega glimmora':        'glimmora-mega',
    'mega scovillain':      'scovillain-mega',
    'mega starmie':         'starmie-mega',
    'mega victreebel':      'victreebel-mega',
    'mega clefable':        'clefable-mega',
    'mega machamp':         'machamp-mega',
    'mega crabominable':    'crabominable-mega',
    'mega meganium':        'meganium-mega',
    'mega feraligatr':      'feraligatr-mega',
    'mega chimecho':        'chimecho-mega',
    'mega floette':         'floette-mega',
    # ── Rotom ───────────────────────────────────────────────────────────────────
    'heat rotom':           'rotom-heat',
    'wash rotom':           'rotom-wash',
    'frost rotom':          'rotom-frost',
    'fan rotom':            'rotom-fan',
    'mow rotom':            'rotom-mow',
    'rotom-heat':           'rotom-heat',
    'rotom-wash':           'rotom-wash',
    'rotom-frost':          'rotom-frost',
    'rotom-fan':            'rotom-fan',
    'rotom-mow':            'rotom-mow',
    # ── Alolan ────────────────────────────────────────────────────────────────
    'alolan raichu':        'raichu-alola',
    'alolan ninetales':     'ninetales-alola',
    'alolan sandslash':     'sandslash-alola',
    'alolan sandshrew':     'sandshrew-alola',
    'alolan vulpix':        'vulpix-alola',
    'alolan exeggutor':     'exeggutor-alola',
    'alolan marowak':       'marowak-alola',
    'alolan muk':           'muk-alola',
    'alolan grimer':        'grimer-alola',
    'alolan geodude':       'geodude-alola',
    'alolan graveler':      'graveler-alola',
    'alolan golem':         'golem-alola',
    'alolan persian':       'persian-alola',
    'alolan meowth':        'meowth-alola',
    # varianti con trattino dal roster
    'raichu-alola':         'raichu-alola',
    'ninetales-alola':      'ninetales-alola',
    'exeggutor-alola':      'exeggutor-alola',
    'marowak-alola':        'marowak-alola',
    'muk-alola':            'muk-alola',
    'persian-alola':        'persian-alola',
    # ── Galarian ──────────────────────────────────────────────────────────────
    'galarian slowbro':     'slowbro-galar',
    'galarian slowking':    'slowking-galar',
    'galarian weezing':     'weezing-galar',
    'galarian mr. mime':    'mr-mime-galar',
    'galarian ponyta':      'ponyta-galar',
    'galarian rapidash':    'rapidash-galar',
    'galarian corsola':     'corsola-galar',
    'galarian linoone':     'linoone-galar',
    'galarian meowth':      'meowth-galar',
    "galarian farfetch'd": 'farfetchd-galar',
    'galarian zigzagoon':   'zigzagoon-galar',
    'galarian articuno':    'articuno-galar',
    'galarian zapdos':      'zapdos-galar',
    'galarian moltres':     'moltres-galar',
    # varianti con trattino dal roster
    'slowbro-galar':        'slowbro-galar',
    'slowking-galar':       'slowking-galar',
    'weezing-galar':        'weezing-galar',
    'stunfisk-galar':       'stunfisk-galar',
    'articuno-galar':       'articuno-galar',
    'zapdos-galar':         'zapdos-galar',
    'moltres-galar':        'moltres-galar',
    # ── Hisuian (pokemondb usa slug -hisuian, non -hisui) ───────────────────────
    'hisuian arcanine':     'arcanine-hisuian',
    'hisuian typhlosion':   'typhlosion-hisuian',
    'hisuian samurott':     'samurott-hisuian',
    'hisuian decidueye':    'decidueye-hisuian',
    'hisuian zorua':        'zorua-hisuian',
    'hisuian zoroark':      'zoroark-hisuian',
    'hisuian goodra':       'goodra-hisuian',
    'hisuian avalugg':      'avalugg-hisuian',
    'hisuian lilligant':    'lilligant-hisuian',
    'hisuian braviary':     'braviary-hisuian',
    'hisuian electrode':    'electrode-hisuian',
    'hisuian sliggoo':      'sliggoo-hisuian',
    # varianti con trattino dal roster (es. "Arcanine-Hisui" → slug hisuian)
    'arcanine-hisui':       'arcanine-hisuian',
    'typhlosion-hisui':     'typhlosion-hisuian',
    'samurott-hisui':       'samurott-hisuian',
    'decidueye-hisui':      'decidueye-hisuian',
    'zoroark-hisui':        'zoroark-hisuian',
    'goodra-hisui':         'goodra-hisuian',
    # ── Aegislash ─────────────────────────────────────────────────────────────
    'aegislash (shield forme)': 'aegislash-shield',
    'aegislash (blade forme)':  'aegislash-blade',
    'aegislash-shield':         'aegislash-shield',
    'aegislash-blade':          'aegislash-blade',
    # ── Tauros Paldea ─────────────────────────────────────────────────────────
    'tauros (combat breed)':        'tauros-paldea-combat-breed',
    'tauros (blaze breed)':         'tauros-paldea-blaze-breed',
    'tauros (aqua breed)':          'tauros-paldea-aqua-breed',
    'tauros-paldea-combat':         'tauros-paldea-combat-breed',
    'tauros-paldea-blaze':          'tauros-paldea-blaze-breed',
    'tauros-paldea-aqua':           'tauros-paldea-aqua-breed',
    # ── Palafin ───────────────────────────────────────────────────────────────
    'palafin (hero form)':  'palafin-hero',
    'palafin (zero form)':  'palafin',
    'palafin-hero':         'palafin-hero',
    # ── Altre forme ───────────────────────────────────────────────────────────
    'basculegion (female)': 'basculegion-f',
    'basculegion (male)':   'basculegion-m',
    'basculegion-f':        'basculegion-f',
    'basculegion-m':        'basculegion-m',
    'meowstic (female)':    'meowstic-f',
    'meowstic (male)':      'meowstic-m',
    'meowstic-f':           'meowstic-f',
    'meowstic-m':           'meowstic-m',
    'indeedee (female)':    'indeedee-f',
    'indeedee-f':           'indeedee-f',
    'gourgeist (small)':    'gourgeist-small',
    'gourgeist (large)':    'gourgeist-large',
    'gourgeist (super)':    'gourgeist-super',
    'lycanroc-dusk':        'lycanroc-dusk',
    'lycanroc-midday':      'lycanroc-midday',
    'lycanroc-midnight':    'lycanroc-midnight',
    'eternal flower floette': 'floette-eternal',
    'morpeko':              'morpeko',
    'mr. rime':             'mr-rime',
}


def _normalize_key(name: str) -> str:
    return name.lower().strip()


def _find_in_catalog(key: str):
    """
    Cerca dati nel catalogo con fallback progressivi.
    """
    data = POKEMON_CATALOG.get(key)
    if data:
        return data

    data = next((v for k, v in POKEMON_CATALOG.items() if k.lower() == key), None)
    if data:
        return data

    data = next((v for v in POKEMON_CATALOG.values() if v.get('name', '').lower() == key), None)
    if data:
        return data

    for poke_data in POKEMON_CATALOG.values():
        for form_name, form_data in poke_data.get('forms', {}).items():
            if form_name.lower() == key:
                # FIX: usa 'or' invece di get(..., fallback) per evitare
                # che una lista vuota [] nella forma blocchi il fallback al Pokémon base
                abilities = (
                    form_data.get('abilities') or
                    poke_data.get('abilities') or
                    []
                )
                return {
                    'name': form_name,
                    'base_stats': form_data.get('base_stats', {}),
                    'types': form_data.get('types') or poke_data.get('types', []),
                    'abilities': abilities,
                }

    alt_keys = _generate_alt_keys(key)
    for alt in alt_keys:
        for poke_data in POKEMON_CATALOG.values():
            for form_name, form_data in poke_data.get('forms', {}).items():
                if form_name.lower() == alt:
                    # FIX: stesso fallback robusto per il lookup via alt_keys
                    abilities = (
                        form_data.get('abilities') or
                        poke_data.get('abilities') or
                        []
                    )
                    return {
                        'name': form_name,
                        'base_stats': form_data.get('base_stats', {}),
                        'types': form_data.get('types') or poke_data.get('types', []),
                        'abilities': abilities,
                    }

    return None


def _generate_alt_keys(key: str) -> list:
    alts = []

    rotom_match = re.match(r'^rotom-(.+)$', key)
    if rotom_match:
        alts.append(f"{rotom_match.group(1)} rotom")

    alola_match = re.match(r'^(.+)-alola$', key)
    if alola_match:
        alts.append(f"alolan {alola_match.group(1)}")

    # Hisuian: supporta sia 'NAME-hisui' che 'NAME-hisuian'
    hisui_match = re.match(r'^(.+)-hisu(?:i|ian)$', key)
    if hisui_match:
        alts.append(f"hisuian {hisui_match.group(1)}")

    galar_match = re.match(r'^(.+)-galar$', key)
    if galar_match:
        alts.append(f"galarian {galar_match.group(1)}")

    tauros_match = re.match(r'^tauros-paldea-(combat|blaze|aqua)(?:-breed)?$', key)
    if tauros_match:
        breed = tauros_match.group(1)
        alts.append(f"tauros ({breed} breed)")

    aegislash_match = re.match(r'^aegislash-(blade|shield)$', key)
    if aegislash_match:
        alts.append(f"aegislash ({aegislash_match.group(1)} forme)")

    if key == 'palafin (zero form)':
        alts.append('palafin')

    gender_match = re.match(r'^(.+)-(f|m)$', key)
    if gender_match:
        base = gender_match.group(1)
        gender = 'female' if gender_match.group(2) == 'f' else 'male'
        alts.append(f"{base} ({gender})")

    lycanroc_match = re.match(r'^lycanroc-(dusk|midday|midnight)$', key)
    if lycanroc_match:
        alts.append(f"lycanroc ({lycanroc_match.group(1)})")

    return alts


@bp.route('/pokemon/<path:name>')
def api_pokemon(name):
    key = _normalize_key(name)

    data = _find_in_catalog(key)

    if not data:
        return jsonify({'ok': False, 'error': f'not found: {name}'}), 404

    # Risolvi lo slug per lo sprite
    slug = FORM_SPRITE_SLUGS.get(key)
    if not slug:
        for alt in _generate_alt_keys(key):
            slug = FORM_SPRITE_SLUGS.get(alt)
            if slug:
                break
    if not slug:
        slug = re.sub(r'[^a-z0-9]+', '-', key).strip('-')

    # Scegli la fonte dello sprite
    if slug in SPRITE_FIXES:
        sprite    = SPRITE_FIXES[slug]
        sprite_hd = SPRITE_FIXES[slug]
    elif slug in POKESPRITE_SLUGS:
        sprite    = f"{POKESPRITE_BASE}/{slug}.png"
        sprite_hd = f"{POKESPRITE_BASE}/{slug}.png"
    else:
        sprite    = f"https://img.pokemondb.net/sprites/home/normal/{slug}.png"
        sprite_hd = f"https://img.pokemondb.net/artwork/large/{slug}.jpg"

    return jsonify({
        'ok':       True,
        'name':     data.get('name', name),
        'stats':    data.get('base_stats', {}),
        'types':    data.get('types', []),
        'abilities': data.get('abilities', []),
        'sprite':   sprite,
        'sprite_hd': sprite_hd,
    })


@bp.route('/moves')
def api_moves():
    moves_path = os.path.join(DATA_DIR, "moves_ma.json")
    try:
        with open(moves_path, encoding='utf-8') as f:
            moves = json.load(f)
        return jsonify({'ok': True, 'moves': moves.get('moves', moves)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
