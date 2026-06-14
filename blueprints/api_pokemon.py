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

# ── Slug overrides per pokesprite ─────────────────────────────────────────────
# Supporta sia il formato "Heat Rotom" che "Rotom-Heat" (da roster)
POKESPRITE_SLUGS = {
    # Rotom forms
    'rotom-heat':   'rotom-heat',
    'rotom-wash':   'rotom-wash',
    'rotom-frost':  'rotom-frost',
    'rotom-fan':    'rotom-fan',
    'rotom-mow':    'rotom-mow',
    # Lycanroc
    'lycanroc':         'lycanroc-midday',
    'lycanroc-midday':  'lycanroc-midday',
    'lycanroc-midnight':'lycanroc-midnight',
    'lycanroc-dusk':    'lycanroc-dusk',
    # Ogerpon forms
    'ogerpon':              'ogerpon-teal-mask',
    'ogerpon-hearthflame':  'ogerpon-hearthflame-mask',
    'ogerpon-cornerstone':  'ogerpon-cornerstone-mask',
    'ogerpon-wellspring':   'ogerpon-wellspring-mask',
    # Urshifu
    'urshifu':          'urshifu-single-strike',
    'urshifu-rapid':    'urshifu-rapid-strike',
    # Indeedee
    'indeedee':     'indeedee-male',
    'indeedee-f':   'indeedee-female',
    # Basculegion
    'basculegion':  'basculegion-male',
    # Oinkologne
    'oinkologne':   'oinkologne-male',
    'oinkologne-f': 'oinkologne-female',
    # Maushold
    'maushold':         'maushold-family-of-three',
    'maushold-four':    'maushold-family-of-four',
    # Tatsugiri
    'tatsugiri':        'tatsugiri-curly',
    'tatsugiri-droopy': 'tatsugiri-droopy',
    'tatsugiri-stretchy':'tatsugiri-stretchy',
    # Squawkabilly
    'squawkabilly':         'squawkabilly-green-plumage',
    'squawkabilly-yellow':  'squawkabilly-yellow-plumage',
    'squawkabilly-blue':    'squawkabilly-blue-plumage',
    'squawkabilly-white':   'squawkabilly-white-plumage',
    # Palafin
    'palafin':      'palafin-zero',
    'palafin-hero': 'palafin-hero',
    # Dudunsparce
    'dudunsparce':       'dudunsparce-two-segment',
    'dudunsparce-three': 'dudunsparce-three-segment',
    # Gimmighoul
    'gimmighoul':       'gimmighoul-roaming',
    'gimmighoul-chest': 'gimmighoul',
    # Giratina
    'giratina':         'giratina-altered',
    'giratina-origin':  'giratina-origin',
    # Shaymin
    'shaymin':          'shaymin-land',
    'shaymin-sky':      'shaymin-sky',
    # Deoxys
    'deoxys':           'deoxys-normal',
    'deoxys-attack':    'deoxys-attack',
    'deoxys-defense':   'deoxys-defense',
    'deoxys-speed':     'deoxys-speed',
    # Tornadus / Thundurus / Landorus / Enamorus
    'tornadus':             'tornadus-incarnate',
    'tornadus-therian':     'tornadus-therian',
    'thundurus':            'thundurus-incarnate',
    'thundurus-therian':    'thundurus-therian',
    'landorus':             'landorus-incarnate',
    'landorus-therian':     'landorus-therian',
    'enamorus':             'enamorus-incarnate',
    'enamorus-therian':     'enamorus-therian',
    # Calyrex riders
    'calyrex-shadow':   'calyrex-shadow',
    'calyrex-ice':      'calyrex-ice',
    # Zacian / Zamazenta
    'zacian':           'zacian-hero',
    'zacian-crowned':   'zacian-crowned',
    'zamazenta':        'zamazenta-hero',
    'zamazenta-crowned':'zamazenta-crowned',
    # Necrozma
    'necrozma':             'necrozma',
    'necrozma-dawn':        'necrozma-dawn-wings',
    'necrozma-dusk':        'necrozma-dusk-mane',
    'necrozma-ultra':       'necrozma-ultra',
    # Kyurem
    'kyurem':           'kyurem',
    'kyurem-black':     'kyurem-black',
    'kyurem-white':     'kyurem-white',
    # Palkia / Dialga
    'palkia':           'palkia',
    'palkia-origin':    'palkia-origin',
    'dialga':           'dialga',
    'dialga-origin':    'dialga-origin',
    # Wormadam
    'wormadam':         'wormadam-plant',
    'wormadam-sandy':   'wormadam-sandy',
    'wormadam-trash':   'wormadam-trash',
    # Iron/Paradox mons (già in catalogo con questo formato)
    'iron-bundle':      'iron-bundle',
    'iron-valiant':     'iron-valiant',
    'iron-treads':      'iron-treads',
    'iron-moth':        'iron-moth',
    'iron-jugulis':     'iron-jugulis',
    'iron-hands':       'iron-hands',
    'iron-thorns':      'iron-thorns',
    'iron-crown':       'iron-crown',
    'iron-boulder':     'iron-boulder',
    'iron-leaves':      'iron-leaves',
    'roaring-moon':     'roaring-moon',
    'walking-wake':     'walking-wake',
    'sandy-shocks':     'sandy-shocks',
    'scream-tail':      'scream-tail',
    'brute-bonnet':     'brute-bonnet',
    'flutter-mane':     'flutter-mane',
    'slither-wing':     'slither-wing',
    'great-tusk':       'great-tusk',
    'gouging-fire':     'gouging-fire',
    'raging-bolt':      'raging-bolt',
    'chi-yu':           'chi-yu',
    'chien-pao':        'chien-pao',
    'wo-chien':         'wo-chien',
    'ting-lu':          'ting-lu',
    # Terapagos
    'terapagos':        'terapagos-normal',
    'terapagos-terastal':'terapagos-terastal',
    'terapagos-stellar':'terapagos-stellar',
    # Hisui forms
    'arcanine-hisui':       'arcanine-hisui',
    'voltorb-hisui':        'voltorb-hisui',
    'electrode-hisui':      'electrode-hisui',
    'typhlosion-hisui':     'typhlosion-hisui',
    'qwilfish-hisui':       'qwilfish-hisui',
    'sneasel-hisui':        'sneasel-hisui',
    'samurott-hisui':       'samurott-hisui',
    'lilligant-hisui':      'lilligant-hisui',
    'zorua-hisui':          'zorua-hisui',
    'zoroark-hisui':        'zoroark-hisui',
    'braviary-hisui':       'braviary-hisui',
    'sliggoo-hisui':        'sliggoo-hisui',
    'goodra-hisui':         'goodra-hisui',
    'avalugg-hisui':        'avalugg-hisui',
    'decidueye-hisui':      'decidueye-hisui',
    # Paldea forms
    'wooper-paldea':    'wooper-paldea',
    'tauros-paldea':    'tauros-paldea-combat',
    'tauros-aqua':      'tauros-paldea-aqua',
    'tauros-blaze':     'tauros-paldea-blaze',
    'oinkologne':       'oinkologne-male',
    # Koraidon / Miraidon
    'koraidon':         'koraidon',
    'miraidon':         'miraidon',
    # Fezandipiti
    'fezandipiti':      'fezandipiti',
    # Okidogi
    'okidogi':          'okidogi',
    # Munkidori
    'munkidori':        'munkidori',
    # Archaludon
    'archaludon':       'archaludon',
    # Hydrapple
    'hydrapple':        'hydrapple',
    # Pecharunt
    'pecharunt':        'pecharunt',
}


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace(' ', '-').replace('_', '-')


def _find_in_catalog(key: str):
    if key in POKEMON_CATALOG:
        return POKEMON_CATALOG[key]
    # Try without trailing form suffix
    parts = key.rsplit('-', 1)
    if len(parts) == 2 and parts[0] in POKEMON_CATALOG:
        return POKEMON_CATALOG[parts[0]]
    return None


def _build_slug(key: str) -> str:
    """Converte la chiave normalizzata nello slug corretto per pokesprite/pokemondb."""
    if key in POKESPRITE_SLUGS:
        return POKESPRITE_SLUGS[key]
    # varianti con trattino dal roster (es. "Rotom-Heat" → "rotom-heat")
    key_lower = key.lower()
    if key_lower in POKESPRITE_SLUGS:
        return POKESPRITE_SLUGS[key_lower]
    return key


def _pokemondb_slug(key: str) -> str:
    """Slug per pokemondb (home sprites & artwork)."""
    if key in POKESPRITE_SLUGS:
        return POKESPRITE_SLUGS[key]
    key_lower = key.lower()
    if key_lower in POKESPRITE_SLUGS:
        return POKESPRITE_SLUGS[key_lower]
    # varianti con trattino dal roster (es. "Arcanine-Hisui" → slug hisuian)
    return key_lower


def _generate_alt_keys(key: str) -> list:
    """Genera chiavi alternative da provare nel catalogo."""
    alts = []
    # Rotom forms: "rotom-heat" → "heat-rotom"
    rotom_forms = ['heat', 'wash', 'frost', 'fan', 'mow']
    parts = key.split('-')
    if len(parts) == 2:
        if parts[0] == 'rotom' and parts[1] in rotom_forms:
            alts.append(f"{parts[1]}-rotom")
        elif parts[1] == 'rotom' and parts[0] in rotom_forms:
            alts.append(f"rotom-{parts[0]}")
    # Prova senza suffisso
    if len(parts) > 1:
        alts.append(parts[0])
    return alts


@bp.route('/pokemon/<path:name>')
def api_pokemon(name):
    key = _normalize_key(name)
    data = _find_in_catalog(key)

    if not data:
        for alt in _generate_alt_keys(key):
            data = _find_in_catalog(alt)
            if data:
                key = alt
                break

    if not data:
        return jsonify({'ok': False, 'error': f'not found: {name}'}), 404

    slug = _build_slug(key)

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


@bp.route('/regulation/<string:reg_id>/data')
def api_regulation_data(reg_id):
    """Restituisce il roster Pokémon della regulation richiesta con i base stat Speed.
    Usato dallo Speed Tier di calcolatori.html per mostrare solo i Pokémon della regulation attiva.
    Response: { ok: true, reg_id, roster: [name, ...], count: N }
    """
    reg_path = os.path.join(DATA_DIR, "regulations.json")
    try:
        with open(reg_path, encoding='utf-8') as f:
            regs = json.load(f)
    except Exception:
        regs = [{"id": "ma", "roster_file": "roster_ma.json"}]

    reg = next((r for r in regs if r['id'] == reg_id), None)
    if not reg:
        return jsonify({'ok': False, 'error': f'Regulation not found: {reg_id}'}), 404

    roster_file = reg.get('roster_file', f'roster_{reg_id}.json')
    try:
        with open(os.path.join(DATA_DIR, roster_file), encoding='utf-8') as f:
            data = json.load(f)
        roster = sorted(data.get('pokemon', []))
    except Exception:
        return jsonify({'ok': False, 'error': f'Roster file not found: {roster_file}'}), 404

    return jsonify({'ok': True, 'reg_id': reg_id, 'roster': roster, 'count': len(roster)})


@bp.route('/moves')
def api_moves():
    moves_path = os.path.join(DATA_DIR, "moves_ma.json")
    try:
        with open(moves_path, encoding='utf-8') as f:
            moves = json.load(f)
        return jsonify({'ok': True, 'moves': moves.get('moves', moves)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
