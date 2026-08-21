from flask import Blueprint, jsonify, request
import os, json, re
from data import DATA_DIR, regulation_default
from extensions import nome_vis, get_db, login_required, ambito_utente

bp = Blueprint('api_pokemon', __name__, url_prefix='/api')

# ⚠️ Il catalogo era caricato **una volta sola all'avvio**, e non guardava più il
# file. Misurato il 21/08/2026, il prezzo era doppio e silenzioso:
#
#   - un Pokémon aggiunto dall'editor finiva sul file e **compariva nel roster**
#     della regulation (che rilegge il file ogni volta), ma qui dava **404**: niente
#     stat, niente tipi, niente sprite. Compariva nell'elenco e non si apriva
#   - peggio: cambiando una base stat dall'editor, il file diceva 999 e questa API
#     continuava a rispondere 115 **senza nessun errore**. Il calcolatore faceva i
#     conti col valore vecchio fino al riavvio dell'app
#
# Ora la copia in memoria segue l'**mtime** del file, come già `_MOVESET` in
# blueprints/pokemon.py e `_TRADUZIONI` in extensions.py: è il pattern che questo
# progetto usa da sempre per i file che si modificano fuori dal processo.
#
# `data/catalog/pokemon.json` è il database completo; il vecchio file resta riserva.
PERCORSI_CATALOGO = (os.path.join(DATA_DIR, "catalog", "pokemon.json"),
                     os.path.join(DATA_DIR, "pokemon_catalog.json"))
POKEMON_CATALOG = {}
# ⚠️ `mtime` **e** dimensione, non il solo mtime: due salvataggi ravvicinati possono
# cadere nello stesso istante del filesystem, e sarebbe di nuovo il dato vecchio
# servito senza un errore. `st_mtime_ns` costa uno `stat()` come il resto.
_FIRMA = {"valore": None, "percorso": None}


def _firma_file(percorso):
    try:
        s = os.stat(percorso)
    except OSError:
        return None
    return (s.st_mtime_ns, s.st_size)


def aggiorna_catalogo(forza=False):
    """Rilegge il catalogo se il file è cambiato. Torna True se ha ricaricato."""
    global POKEMON_CATALOG
    for percorso in PERCORSI_CATALOGO:
        firma = _firma_file(percorso)
        if firma is None:
            continue
        if not forza and _FIRMA["valore"] == firma and _FIRMA["percorso"] == percorso:
            return False
        try:
            with open(percorso, encoding="utf-8") as f:
                caricato = json.load(f)
        except Exception as e:
            # ⚠️ Un file illeggibile **non** svuota la copia buona che abbiamo in
            # mano: meglio dati di un minuto fa che un catalogo vuoto, che qui
            # vorrebbe dire 404 su ogni Pokémon.
            print(f"[API] catalogo non rileggibile ({os.path.basename(percorso)}): {e}")
            return False
        POKEMON_CATALOG = caricato
        _FIRMA.update(valore=firma, percorso=percorso)
        _costruisci_indice()
        return True
    if not POKEMON_CATALOG:
        print("[API] catalogo non leggibile: nessuno dei percorsi noti risponde")
    return False

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

# Primi pezzi che NON devono diventare alias. La regola "prima parola della chiave"
# serve a far risolvere il nome nudo di chi esiste solo con un suffisso di forma
# ("palafin-zero-form" -> "Palafin"), ma su "mega-venusaur" registrava anche `mega`:
# con il fallback di _find_in_catalog, un nome inesistente come "Mega Machamp"
# rispondeva **Mega Venusaur** invece di 404 — risposta sbagliata invece di errore.
# Qui stanno solo i qualificatori di forma e i primi pezzi che da soli non sono un
# Pokémon (`Iron Hands` -> "Iron", `Tapu Koko` -> "Tapu"). Verificato l'11/08/2026:
# nessuno dei 295 nomi usati da MA, MB e Pokedex dipende da questi alias.
NON_ALIASABILI = {
    "mega", "primal", "alolan", "galarian", "hisuian", "paldean",
    "totem", "partner", "eternal", "original", "iron", "tapu",
}

# Qualificatori regionali, usati per riconoscere le forme scritte "X (Y Form)"
# invece che "Y X" — vedi l'alias in fondo a _costruisci_indice().
REGIONI = {"galarian", "alolan", "hisuian", "paldean", "kantonian"}


def _costruisci_indice():
    _INDICE.clear()
    for chiave, voce in POKEMON_CATALOG.items():
        record = {"data": voce, "slug": _slug_forma(chiave)}
        _INDICE.setdefault(_normalize_key(chiave), record)
        # `nome_it` e `nome_en` fanno risolvere il Pokemon in tutte e due le lingue:
        # nella casella del calcolatore l'utente scrive "Crinealato" o "Flutter Mane"
        # a seconda della lingua attiva, ma la chiave del catalogo e' una sola.
        for etichetta in (voce.get("name"), voce.get("nome_it"), voce.get("nome_en")):
            if etichetta:
                _INDICE.setdefault(_normalize_key(etichetta), record)
        for nome_forma, forma in (voce.get("forms") or {}).items():
            # la forma eredita dal base ciò che non ridefinisce
            unita = {
                "name": nome_forma,
                "types": forma.get("types") or voce.get("types", []),
                "base_stats": forma.get("base_stats") or voce.get("base_stats", {}),
                "abilities": forma.get("abilities") or voce.get("abilities", []),
                "nome_it": forma.get("nome_it") or nome_forma,
                "nome_en": forma.get("nome_en") or nome_forma,
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
        if len(parti) > 1 and parti[0] not in NON_ALIASABILI:
            _INDICE.setdefault(parti[0], _INDICE[chiave])
        # "meowstic-male" -> anche "meowstic-m" ; idem female/f
        for lungo, corto in (("male", "m"), ("female", "f")):
            if parti[-1] == lungo:
                _INDICE.setdefault("-".join(parti[:-1] + [corto]), _INDICE[chiave])
        # "darmanitan-galarian-form" -> anche "galarian-darmanitan".
        # Delle 57 voci con un qualificatore regionale, 56 usano il prefisso
        # ("Galarian Zapdos") e **una sola** la parentesi: `Darmanitan (Galarian
        # Form)`. Finché c'era l'alias spurio `galarian` l'incoerenza era nascosta
        # dietro una risposta sbagliata; tolto quello, `Galarian Darmanitan` dava
        # 404. Il nome nel catalogo non si tocca — è l'identità della forma, la
        # usano i filtri delle regulation — quindi la differenza si colma qui.
        if len(parti) > 2 and parti[-1] == "form" and parti[-2] in REGIONI:
            _INDICE.setdefault("-".join([parti[-2]] + parti[:-2]), _INDICE[chiave])


# Il primo caricamento: sta qui e non in cima perché `aggiorna_catalogo()` chiama
# `_costruisci_indice()`, che è definita subito sopra.
aggiorna_catalogo(forza=True)


def _find_in_catalog(key: str):
    # ⚠️ È qui che la copia in memoria si riallinea al file, e ci sta perché è il
    # collo di bottiglia di ogni lettura del catalogo: sopra c'è una `stat()`, non
    # una rilettura — il JSON si ricarica solo quando il file è davvero cambiato.
    aggiorna_catalogo()
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

    # Mosse che questa voce puo' imparare nella regulation richiesta. `moves: null`
    # non e' "nessuna mossa" ma "non lo sappiamo": succede sulle forme inventate, che
    # PokeAPI non conosce. Chi legge deve mostrare tutte le mosse in quel caso, non
    # zero — altrimenti proprio le forme di Davide diventerebbero inutilizzabili.
    from blueprints.pokemon import _list_regulation_files, mosse_legali
    reg_id = request.args.get('reg') or regulation_default()
    reg = next((r for r in _list_regulation_files() if r.get('id') == reg_id), None)
    mosse, sorgente = mosse_legali(data.get('name') or key, reg)
    if mosse is None and (data.get('name') or '') != key:
        mosse, sorgente = mosse_legali(key, reg)

    return jsonify({
        'ok':       True,
        'name':     data.get('name', name),
        # `nome` e' il nome da mostrare nella lingua attiva; `name` resta la chiave
        # con cui il resto del codice indicizza il catalogo.
        'nome':     nome_vis(data, data.get('name', name)),
        'nome_it':  data.get('nome_it') or data.get('name', name),
        'nome_en':  data.get('nome_en') or data.get('name', name),
        'stats':    data.get('base_stats', {}),
        'types':    data.get('types', []),
        'abilities': data.get('abilities', []),
        'sprite':   sprite,
        'sprite_hd': sprite_hd,
        'moves':        mosse,
        'moves_source': sorgente,
    })


@bp.route('/regulation/<string:reg_id>/data')
def api_regulation_data(reg_id):
    """Restituisce il roster Pokémon della regulation richiesta.
    Usato dallo Speed Tier di calcolatori.html per mostrare solo i Pokémon della regulation attiva.
    Response: { ok: true, reg_id, roster: [name, ...], count: N }

    Legge il **filtro** della regulation, come ogni altro loader. Prima leggeva il
    vecchio `roster_file`: stessa storia di /api/moves. Conseguenze misurate
    l'11/08/2026 — su MA lo Speed Tier mostrava i **208** nomi ereditati invece dei
    **279** veri, e nessuna delle 59 Mega; su `pokedex` e `mb`, che un `roster_file`
    non ce l'hanno mai avuto, l'endpoint dava 404 e il tab ricadeva in silenzio sulla
    lista statica da 158 nomi. L'import è dentro la funzione perché blueprints.pokemon
    è il posto dove vive la logica di filtro del catalogo.
    """
    from blueprints.pokemon import (_list_regulation_files, _load_roster, load_items,
                                    _load_mega_map)

    reg = next((r for r in _list_regulation_files() if r.get('id') == reg_id), None)
    if not reg:
        return jsonify({'ok': False, 'error': f'Regulation not found: {reg_id}'}), 404

    roster = _load_roster(reg)
    if not roster:
        return jsonify({'ok': False, 'error': f'Roster vuoto per la regulation {reg_id}'}), 404

    # `regulation` e `items` erano letti da team_form.html e non sono mai esistiti qui:
    # `CURRENT_MECHANICS` restava vuoto a ogni caricamento, quindi il selettore della
    # meccanica mostrava la sola voce "nessuna" e **la Mega non era selezionabile per
    # nessun membro del team**, su nessuna regulation — benche' tutte e tre abbiano
    # `"mechanics": ["mega"]` nel registro. Stessa famiglia dei tre endpoint fantasma
    # dell'11/08: JS scritto contro una risposta mai implementata.
    return jsonify({
        'ok': True, 'reg_id': reg_id, 'roster': roster, 'count': len(roster),
        'regulation': {
            'id': reg.get('id'), 'label': reg.get('label'),
            'mechanics': reg.get('mechanics') or [],
            'moveset': reg.get('moveset') or 'main',
        },
        'items': load_items(reg_id).get('items', {}),
        # La mega_map arrivava solo da Jinja al caricamento della pagina, quindi
        # restava quella della regulation iniziale anche dopo aver cambiato tendina:
        # con `pokedex` come default, che una mega_map non ce l'ha, il selettore Mega
        # non si popolava mai. Qui segue la regulation come tutto il resto.
        'mega_map': _load_mega_map(reg),
    })


@bp.route('/moves')
def api_moves():
    """Mosse della regulation richiesta. Default: la prima del registro.

    Prima leggeva moves_ma.json hardcoded e quindi rispondeva con le mosse di MA
    qualunque regulation fosse attiva. L'import è dentro la funzione perché
    blueprints.pokemon è il posto dove vive la logica di filtro del catalogo.
    """
    reg_id = request.args.get('reg') or regulation_default()
    try:
        from blueprints.pokemon import load_moves
        dati = load_moves(reg_id)
        return jsonify({'ok': True, 'reg_id': reg_id, 'moves': dati.get('moves', {})})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# TEAM: i sei Pokemon salvati, per il quick-load del calcolatore
# ---------------------------------------------------------------------------
# ⚠️ Questa route **non esisteva**, e nessuno se n'era accorto perche' l'errore
# moriva in un `catch(e){console.warn(...)}`: il pulsante 📊 sulle schede di
# /pokemon apriva il calcolatore e la barra dei sei Pokemon non compariva, senza
# dire perche'. Era il quarto endpoint fantasma del progetto (dopo /api/regulations,
# `d.moves` e `d.regulation`), tutti trovati allo stesso modo: leggendo cosa il JS
# chiede e cercandolo nella url_map.
#
# Il contratto lo detta il client, che era gia' scritto (`calcolatori-ui.js`):
# `d.ok` e `d.members`, e di ogni membro legge `pokemon`, `nature`, `mega_stone` e
# sei campi `ev_*`. Due di quei nomi **nel DB non esistono**, e la differenza non e'
# cosmetica:
#
#   * `ev_*` <- `sp_*`. Non sono gli EV del gioco vero (252 a stat, 510 in tutto):
#     sono gli **SP** di questo progetto, max 32 per stat e 66 in totale. Il
#     calcolatore usa lo stesso fondo di scala — i suoi campi hanno `max="32"` — e
#     la regola #8 e' scritta cosi': «32 SP atk». Il rinomino e' una traduzione fra
#     due nomi della stessa cosa, non una conversione.
#   * `mega_stone` e' la **colonna vecchia**, e su ogni riga salvata da quando
#     esistono le meccaniche vale `NULL`: oggi la Mega si scrive in
#     `mechanic_type='mega'` + `mechanic_value`. Si risponde con la colonna se c'e',
#     altrimenti con la meccanica, cosi' il client resta com'e'.
#
# Gli IV non si mandano **di proposito**: questo progetto non li salva, e il client
# fa gia' la cosa giusta (`m[ivMap[s]]!==undefined ? ... : 31`). Mandare uno zero
# sarebbe un dato inventato che cambia i conti.
@bp.route('/team/<int:tid>')
@login_required
def api_team(tid):
    # Il team e' di qualcuno: si legge con la condizione del proprietario, come
    # ovunque dal 19/08/2026. Un team che non e' tuo risponde «non trovato».
    cond, par = ambito_utente()
    db = get_db()
    team = db.execute(f"SELECT * FROM teams WHERE id=? AND {cond}",
                      [tid] + list(par)).fetchone()
    if not team:
        db.close()
        return jsonify({"ok": False, "error": "Team non trovato"}), 404
    membri = []
    for m in db.execute("SELECT * FROM team_members WHERE team_id=? ORDER BY slot",
                        (tid,)).fetchall():
        voce = dict(m)
        for stat in ("hp", "atk", "def", "spatk", "spdef", "spe"):
            voce["ev_" + stat] = voce.get("sp_" + stat) or 0
        if not voce.get("mega_stone") and (voce.get("mechanic_type") or "") == "mega":
            voce["mega_stone"] = voce.get("mechanic_value") or None
        membri.append(voce)
    db.close()
    return jsonify({"ok": True, "team": dict(team), "members": membri})
