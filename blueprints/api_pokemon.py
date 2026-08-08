from flask import Blueprint, jsonify
import os, json, re
from data import DATA_DIR

bp = Blueprint('api_pokemon', __name__, url_prefix='/api')

# Carica catalogo una volta sola all'avvio
# data/catalog/pokemon.json è il database completo; il vecchio file resta fallback.
POKEMON_CATALOG = {}
for _catalog_path in (os.path.join(DATA_DIR, "catalog", "pokemon.json"),
                      os.path.join(DATA_DIR, "pokemon_catalog.json")):
    try:
        with open(_catalog_path, encoding="utf-8") as _f:
            POKEMON_CATALOG = json.load(_f)
        break
    except Exception as e:
        _errore = e
if not POKEMON_CATALOG:
    print(f"[API] catalogo non leggibile: {_errore}")

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

PDB_SPRITE = "https://img.pokemondb.net/sprites/home/normal"
PDB_ART    = "https://img.pokemondb.net/artwork/large"

# ── Sprite mancanti ───────────────────────────────────────────────────────────
# chiave catalogo -> (slug sprite, slug artwork HD)
# HD None = su pokemondb l'artwork grande non esiste, si ricade sullo sprite normale.
# Verificati uno per uno caricandoli davvero in browser.
SPRITE_SLUG_OVERRIDES = {
    # forme con suffisso che pokemondb non usa
    'palafin-zero-form':       ('palafin',       'palafin'),
    'morpeko-full-belly-mode': ('morpeko',       'morpeko-full-belly'),
    'aegislash-shield-forme':  ('aegislash',     'aegislash'),
    'eternal-flower-floette':  ('floette',       'floette'),
    # pokemondb nomina le mega "<nome>-mega", il catalogo "mega-<nome>"
    'mega-banette':            ('banette-mega',  'banette-mega'),
    # mega fan-made senza sprite proprio -> si usa la forma base
    'mega-chimecho':           ('chimecho',      'chimecho'),
    'mega-crabominable':       ('crabominable',  'crabominable'),
    # erano indirizzati al repo pokesprite, che non li contiene
    'archaludon':              ('archaludon',    'archaludon'),
    'mimikyu':                 ('mimikyu',       'mimikyu'),
    'hydrapple':               ('hydrapple',     None),
    # sprite ok ma artwork grande assente
    'sinistcha':               ('sinistcha',     None),
    # forme con suffisso verboso rispetto a pokemondb
    'aegislash-blade-forme':   ('aegislash-blade', 'aegislash-blade'),
    'palafin-hero-form':       ('palafin-hero',    'palafin-hero'),
    'mega-floette':            ('floette',         'floette'),
    # Gourgeist: gli sprite ci sono, l'artwork grande no
    'gourgeist-small':         ('gourgeist-small',   None),
    'gourgeist-large':         ('gourgeist-large',   None),
    'gourgeist-super':         ('gourgeist-super',   None),
    'gourgeist-average':       ('gourgeist',         'gourgeist'),
    # forme di genere: pokemondb tiene il maschio come forma base
    'meowstic-male':           ('meowstic',          'meowstic'),
    'meowstic-female':         ('meowstic-female',   'meowstic-female'),
    'basculegion-male':        ('basculegion',       'basculegion'),
    'basculegion-female':      ('basculegion-female','basculegion-female'),
    # Mega Meowstic e' fan-made: si ricade sulla forma base del genere giusto
    'meowstic-mega-male':      ('meowstic-male',     'meowstic-male'),
    'meowstic-mega-female':    ('meowstic-female',   'meowstic-female'),
}

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
    """Normalizza un nome in chiave: minuscolo, senza punteggiatura, trattini singoli.

    Deve reggere sia le chiavi del catalogo ("mr-rime") sia i nomi visualizzati
    dall'interfaccia ("Mr. Rime", "Palafin (Zero Form)", "Mega Charizard X").
    """
    s = name.strip().lower()
    for ch in "().,'’\"":
        s = s.replace(ch, " ")
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


# pokemondb usa l'aggettivo completo: "raichu-alolan", non "raichu-alola".
# Mappa entrambe le forme (prefisso "Alolan X" e suffisso "X-Alola") sullo stesso slug.
_REGIONI = {
    "alolan": "alolan", "alola": "alolan",
    "galarian": "galarian", "galar": "galarian",
    "hisuian": "hisuian", "hisui": "hisuian",
    "paldean": "paldean", "paldea": "paldean",
}


def _slug_forma(nome: str) -> str:
    """Slug pokemondb per una forma alternativa, dal suo nome visualizzato."""
    n = _normalize_key(nome)
    parti = n.split("-")
    if len(parti) < 2:
        return n
    # "mega-charizard-x" -> "charizard-mega-x" ; "mega-venusaur" -> "venusaur-mega"
    if parti[0] == "mega":
        return "-".join([parti[1], "mega"] + parti[2:])
    # "alolan-raichu" -> "raichu-alolan"
    if parti[0] in _REGIONI:
        return "-".join(parti[1:] + [_REGIONI[parti[0]]])
    # "raichu-alola" -> "raichu-alolan"
    if parti[-1] in _REGIONI:
        return "-".join(parti[:-1] + [_REGIONI[parti[-1]]])
    # "heat-rotom" -> "rotom-heat" (pokemondb mette sempre il base davanti)
    if parti[-1] == "rotom" and len(parti) == 2:
        return f"rotom-{parti[0]}"
    return n


# ── Indice di ricerca ─────────────────────────────────────────────────────────
# Il catalogo tiene 84 forme annidate dentro `forms` di 72 Pokémon: senza questo
# indice sarebbero irraggiungibili e Mega/forme regionali darebbero 404.
_INDICE = {}


def _costruisci_indice():
    _INDICE.clear()
    for chiave, voce in POKEMON_CATALOG.items():
        record = {"data": voce, "slug": _slug_forma(chiave)}
        _INDICE.setdefault(_normalize_key(chiave), record)
        if voce.get("name"):
            _INDICE.setdefault(_normalize_key(voce["name"]), record)
        for nome_forma, forma in (voce.get("forms") or {}).items():
            # la forma eredita dal base ciò che non ridefinisce
            unita = {
                "name": nome_forma,
                "types": forma.get("types") or voce.get("types", []),
                "base_stats": forma.get("base_stats") or voce.get("base_stats", {}),
                "abilities": forma.get("abilities") or voce.get("abilities", []),
            }
            _INDICE.setdefault(
                _normalize_key(nome_forma),
                {"data": unita, "slug": _slug_forma(nome_forma)},
            )

    # ── Alias ────────────────────────────────────────────────────────────────
    # Alcune voci esistono solo col suffisso di forma ("palafin-zero-form"):
    # senza questi alias il nome nudo ("Palafin") darebbe 404.
    for chiave in list(_INDICE):
        parti = chiave.split("-")
        if len(parti) > 1:
            _INDICE.setdefault(parti[0], _INDICE[chiave])
        # "meowstic-male" -> anche "meowstic-m" ; idem female/f
        for lungo, corto in (("male", "m"), ("female", "f")):
            if parti[-1] == lungo:
                _INDICE.setdefault("-".join(parti[:-1] + [corto]), _INDICE[chiave])


_costruisci_indice()


def _find_in_catalog(key: str):
    rec = _INDICE.get(key)
    if rec:
        return rec["data"]
    # fallback: prova senza il suffisso di forma finale
    parti = key.rsplit("-", 1)
    if len(parti) == 2:
        rec = _INDICE.get(parti[0])
        if rec:
            return rec["data"]
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

    # Lo slug della forma viene dall'indice (es. "Mega Venusaur" -> "venusaur-mega").
    # Tutti gli sprite vengono da pokemondb: il repo pokesprite non contiene le forme
    # regionali, le Rotom ne' i Pokemon recenti, e dava 404 su 38 nomi.
    rec = _INDICE.get(key)
    slug = rec["slug"] if rec else _slug_forma(_build_slug(key))

    override = SPRITE_SLUG_OVERRIDES.get(key) or SPRITE_SLUG_OVERRIDES.get(slug)
    if override:
        s_slug, hd_slug = override
        sprite    = f"{PDB_SPRITE}/{s_slug}.png"
        sprite_hd = f"{PDB_ART}/{hd_slug}.jpg" if hd_slug else sprite
    elif slug in SPRITE_FIXES:
        sprite    = SPRITE_FIXES[slug]
        sprite_hd = SPRITE_FIXES[slug]
    else:
        sprite    = f"{PDB_SPRITE}/{slug}.png"
        sprite_hd = f"{PDB_ART}/{slug}.jpg"

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
