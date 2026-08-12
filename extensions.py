import sqlite3, os, hashlib, re, json
from functools import wraps
from flask import session, redirect, url_for, request
from data import PYTHON_TOPICS

DB = os.path.join(os.path.dirname(__file__), "hub.db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ── Lingua ───────────────────────────────────────────────────────────────────
# Sta in un cookie e non in localStorage perché la deve leggere anche Flask: le
# tendine di Pokémon, mosse e oggetti sono renderizzate dal server, e senza il
# cookie il server non saprebbe in che lingua scriverle.
LINGUE = ("it", "en")
COOKIE_LINGUA = "hub_lang"


def lingua_attiva():
    """'it' o 'en'. Fuori da una richiesta, o con un valore strano, torna 'it'."""
    try:
        scelta = request.cookies.get(COOKIE_LINGUA)
    except RuntimeError:          # nessun contesto di richiesta
        return "it"
    return scelta if scelta in LINGUE else "it"


def nome_vis(voce, chiave="", lingua=None):
    """Il nome da mostrare per una voce del catalogo, nella lingua attiva.

    Le **chiavi** del catalogo non cambiano mai: sono referenziate dai filtri delle
    regulation, dal motore degli effetti e dai team salvati. Cambia solo ciò che si
    legge a schermo. Se la traduzione manca si ricade sulla chiave, mai su una
    stringa vuota.
    """
    lingua = lingua or lingua_attiva()
    if isinstance(voce, dict):
        return voce.get(f"nome_{lingua}") or voce.get("name") or chiave
    return chiave or voce


# ── Le stringhe dell'interfaccia ─────────────────────────────────────────────
# `nome_vis` qui sopra traduce i **dati** (Pokémon, mosse, oggetti, abilità);
# questa parte traduce le **etichette**: titoli, pulsanti, intestazioni di tabella.
#
# La chiave del dizionario è **la frase italiana stessa**, non un codice inventato
# tipo `btn.salva`. Due ragioni: il template resta leggibile (`{{ t('Salva') }}` si
# capisce senza aprire il JSON) e una traduzione mancante **ricade sull'italiano**,
# che è sempre giusto, invece di mostrare a schermo il codice della chiave.
# Il prezzo è che cambiare la frase italiana in un template stacca la traduzione:
# per accorgersene c'è `scripts/controlla_traduzioni.py`.
I18N_DIR = os.path.join(DATA_DIR, "i18n")

# Cache con l'mtime, come per il moveset: il file lo si modifica a mano fuori dal
# processo, e rileggerlo quando cambia evita di riavviare l'app a ogni ritocco.
_TRADUZIONI = {}


def traduzioni(lingua=None):
    """Il dizionario italiano → lingua richiesta. Per l'italiano è vuoto: è la fonte."""
    lingua = lingua or lingua_attiva()
    if lingua == "it":
        return {}
    percorso = os.path.join(I18N_DIR, f"{lingua}.json")
    try:
        mtime = os.path.getmtime(percorso)
    except OSError:
        return {}
    voce = _TRADUZIONI.get(lingua)
    if voce is None or voce["mtime"] != mtime:
        with open(percorso, encoding="utf-8") as f:
            voce = {"mtime": mtime, "voci": json.load(f)}
        _TRADUZIONI[lingua] = voce
    return voce["voci"]


def t(testo, lingua=None):
    """La stringa d'interfaccia nella lingua attiva; se manca, l'italiano com'è."""
    return traduzioni(lingua).get(testo, testo)


def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, username TEXT UNIQUE,
        password TEXT, display_name TEXT, role TEXT DEFAULT 'user');
    CREATE TABLE IF NOT EXISTS games(
        id INTEGER PRIMARY KEY, title TEXT NOT NULL, platform TEXT, genre TEXT,
        status TEXT DEFAULT 'Wishlist', hours_hltb REAL, cover_url TEXT,
        prog_story INTEGER DEFAULT 0, prog_side INTEGER DEFAULT 0,
        prog_collect INTEGER DEFAULT 0,
        date_start TEXT, date_end TEXT, notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS teams(
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, format TEXT,
        record TEXT, description TEXT, notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS team_members(
        id INTEGER PRIMARY KEY,
        team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
        slot INTEGER, pokemon TEXT, mega_stone TEXT, nature TEXT,
        ability TEXT, held_item TEXT, tera_type TEXT,
        move1 TEXT, move2 TEXT, move3 TEXT, move4 TEXT,
        sp_hp INTEGER DEFAULT 0, sp_atk INTEGER DEFAULT 0,
        sp_def INTEGER DEFAULT 0, sp_spatk INTEGER DEFAULT 0,
        sp_spdef INTEGER DEFAULT 0, sp_spe INTEGER DEFAULT 0,
        sprite_url TEXT DEFAULT NULL);
    CREATE TABLE IF NOT EXISTS arduino_projects(
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, board TEXT,
        status TEXT DEFAULT 'Idea', tinkercad_url TEXT,
        code TEXT, description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS python_topics(
        id INTEGER PRIMARY KEY, category TEXT, name TEXT, done INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS pc_builds(
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS pc_components(
        id INTEGER PRIMARY KEY,
        build_id INTEGER REFERENCES pc_builds(id) ON DELETE CASCADE,
        category TEXT, name TEXT, price REAL DEFAULT 0, notes TEXT);
    """)
    # L'admin di un DB nuovo nasce gia' con lo schema forte. Sui DB esistenti
    # questa INSERT non fa nulla (OR IGNORE) e l'hash vecchio viene riscritto al
    # primo login riuscito.
    pw = hash_password("admin123")
    db.execute("INSERT OR IGNORE INTO users(username,password,display_name,role)"
               " VALUES(?,?,'Admin','admin')", ("admin", pw))
    if db.execute("SELECT COUNT(*) FROM python_topics").fetchone()[0] == 0:
        for cat, topics in PYTHON_TOPICS.items():
            for t in topics:
                db.execute("INSERT INTO python_topics(category,name) VALUES(?,?)", (cat, t))
    db.commit()
    # Migrazione colonne team_members
    for col, defval in [
        ("sp_hp","0"),("sp_atk","0"),("sp_def","0"),
        ("sp_spatk","0"),("sp_spdef","0"),("sp_spe","0"),
        ("sprite_url","NULL"),
    ]:
        try:
            db.execute(f"ALTER TABLE team_members ADD COLUMN {col} INTEGER DEFAULT {defval}")
            db.commit()
        except Exception:
            pass
    # Migrazione mechanic_type / mechanic_value
    for col in ["mechanic_type", "mechanic_value"]:
        try:
            db.execute(f"ALTER TABLE team_members ADD COLUMN {col} TEXT DEFAULT ''")
            db.commit()
        except Exception:
            pass
    db.execute("""
        UPDATE team_members
        SET mechanic_type = 'mega', mechanic_value = mega_stone
        WHERE (mega_stone IS NOT NULL AND mega_stone != '')
        AND (mechanic_type IS NULL OR mechanic_type = '')
    """)
    db.execute("""
        UPDATE team_members
        SET mechanic_type = 'tera', mechanic_value = tera_type
        WHERE (tera_type IS NOT NULL AND tera_type != '')
        AND (mechanic_type IS NULL OR mechanic_type = '')
    """)
    db.commit()
    # Tabella regulations
    db.executescript("""
        CREATE TABLE IF NOT EXISTS regulations(
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            roster_file TEXT,
            moves_file TEXT,
            items_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT OR IGNORE INTO regulations(id, label, roster_file, moves_file, items_file)
        VALUES('ma', 'Regulation MA', 'roster_ma.json', 'moves_ma.json', 'items_ma.json');
    """)
    db.commit()
    try:
        db.execute("ALTER TABLE teams ADD COLUMN regulation_id TEXT DEFAULT 'ma'")
        db.commit()
    except Exception:
        pass
    db.execute("UPDATE teams SET regulation_id='ma' WHERE regulation_id IS NULL")
    db.commit()
    # Migrazione: appid Steam del gioco, NULL per le voci inserite a mano.
    # hours_played sono le ore EFFETTIVAMENTE giocate lette da Steam:
    # nulla a che vedere con hours_hltb, che e' la stima di durata HowLongToBeat.
    # steam_tags sono i tag della community, molto piu' fini dei generi: un gioco che
    # per `genre` e' solo "Azione" qui puo' essere "Souls-like, Open World, Difficult".
    # Elenco separato da virgole, gia' ordinato dal piu' votato.
    # Permessi per sezione: elenco di slug separati da virgole. Nasce **vuota**, e
    # vuota vale "tutte le sezioni", così chi c'era prima non perde niente.
    try:
        db.execute("ALTER TABLE users ADD COLUMN sections TEXT")
        db.commit()
    except Exception:
        pass

    for col, tipo in [("steam_appid", "INTEGER"), ("hours_played", "REAL"),
                      ("steam_tags", "TEXT")]:
        try:
            db.execute(f"ALTER TABLE games ADD COLUMN {col} {tipo}")
            db.commit()
        except Exception:
            pass
    db.close()


# --- Password ---------------------------------------------------------------
# Fino al 12/08/2026 erano **sha256 senza sale**: due utenti con la stessa password
# avevano lo stesso hash, e un sha256 nudo si attacca con le tabelle precalcolate.
# Ora si usa `werkzeug.security`, che di suo fa scrypt con un sale casuale.
#
# ⚠️ Non esiste una migrazione in blocco, e non e' una scelta: sha256 e' a senso unico,
# quindi dal vecchio hash la password non si ricava. L'unica strada e' riconoscere
# l'hash vecchio **al login**, verificarlo con lo schema vecchio e riscriverlo forte in
# quel momento — l'utente non se ne accorge, e chi non entra mai resta com'e'.
_LEGACY = re.compile(r"^[0-9a-f]{64}$")


def hash_password(password):
    """Hash nuovo (scrypt con sale). Da usare per ogni scrittura da oggi in poi."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)


def verifica_password(memorizzato, password):
    """`(corretta, da_riscrivere)`.

    `da_riscrivere` e' True quando la verifica e' passata **con lo schema vecchio**:
    e' il momento buono per sostituire l'hash, perche' e' l'unico in cui la password in
    chiaro esiste.
    """
    from werkzeug.security import check_password_hash
    memorizzato = memorizzato or ""
    if _LEGACY.match(memorizzato):
        return hashlib.sha256(password.encode()).hexdigest() == memorizzato, True
    try:
        return check_password_hash(memorizzato, password), False
    except Exception:
        return False, False


def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if "username" not in session:
            return redirect(url_for("auth.login"))
        return f(*a, **kw)
    return wrap


# --- Permessi per sezione ---------------------------------------------------
# `users.sections` è un elenco di slug separati da virgole. **`NULL` o `*` valgono
# "tutte"**, ed è la scelta che tiene al sicuro chi c'era prima: la colonna nasce
# vuota, quindi nessun utente esistente perde accessi quando la funzione entra in
# servizio. Gli amministratori vedono sempre tutto, qualunque cosa dica la colonna.
TUTTE_LE_SEZIONI = "*"
# ⚠️ Serve un valore esplicito per "nessuna sezione": la stringa vuota vuol già dire
# "tutte", quindi senza questo un utente a cui l'admin toglie ogni spunta le
# riceverebbe **tutte**, cioè l'esatto contrario.
NESSUNA_SEZIONE = "-"


def sezioni_utente(username=None):
    """Gli slug che questo utente può vedere. `None` = tutte."""
    from data import SEZIONI_SLUG
    nome = username or session.get("username")
    if not nome:
        return []
    db = get_db()
    r = db.execute("SELECT role, sections FROM users WHERE username=?", (nome,)).fetchone()
    db.close()
    if not r:
        return []
    if (r["role"] or "") == "admin":
        return list(SEZIONI_SLUG)
    grezzo = (r["sections"] if "sections" in r.keys() else None) or ""
    grezzo = grezzo.strip()
    if grezzo == NESSUNA_SEZIONE:
        return []
    if not grezzo or grezzo == TUTTE_LE_SEZIONI:
        return list(SEZIONI_SLUG)
    scelte = {s.strip() for s in grezzo.split(",") if s.strip()}
    # Filtrate contro l'elenco vero: uno slug rimasto in DB dopo la rimozione di una
    # sezione non deve diventare un permesso fantasma.
    return [s for s in SEZIONI_SLUG if s in scelte]


def puo_vedere(slug):
    """L'utente in sessione può vedere questa sezione?"""
    return slug in sezioni_utente()


def _i(v, d=0):
    try: return int(v)
    except: return d


def _f(v, d=0.0):
    try: return float(v)
    except: return d