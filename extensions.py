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


def tf(testo, valori=None, lingua=None):
    """Come `t()`, ma con i segnaposto `{nome}` sostituiti.

    Gemella di `tf()` in `base.html`, e con la stessa ragione d'essere: la frase
    resta **intera** nel dizionario invece di essere spezzata in pezzi da
    concatenare, così l'inglese può metterne le parole in un altro ordine.
    `{{ n }} {{ t('team salvati') }}` non è traducibile bene — il numero è
    incastrato in mezzo e la frase non esiste da nessuna parte per intero.

    Sostituzione a mano e non `str.format()`: le frasi contengono graffe che non
    sono segnaposto (i blocchi `effect` mostrati negli editor), e `format()` ci
    andrebbe a sbattere.
    """
    out = t(testo, lingua)
    for chiave, valore in (valori or {}).items():
        out = out.replace("{" + chiave + "}", str(valore))
    return out


def categorie(db, lingua=None):
    """`{chiave: etichetta tradotta}` per le categorie di oggetti o abilità.

    Una funzione sola perché la stessa mappa serve a tre schermate — i due editor e
    il catalogo — e in due posti per ognuna: le tendine rese da Jinja e le tabelle
    che il browser costruisce da sé, che se la prendono già tradotta con `|tojson`.
    ⚠️ La **chiave** non compare qui perché non cambia mai: è il dato.
    """
    from data import CATEGORIE_OGGETTI, CATEGORIE_ABILITA
    mappa = CATEGORIE_ABILITA if db in ("abilities", "abilita") else CATEGORIE_OGGETTI
    return {chiave: t(etichetta, lingua) for chiave, etichetta in mappa.items()}


# --- La chiave che firma i cookie di sessione -------------------------------
# ⚠️ Fino al 21/08/2026 il default era la costante `"dev-secret-change-me"`, scritta
# nel codice e quindi su GitHub: chi la conosce **si firma da solo un cookie di
# sessione da amministratore**, senza bisogno di nessuna password. Era il buco piu'
# grave dei quattro che §1.5 elencava prima di esporre l'app.
#
# Ora la chiave non ha piu' un valore di riserva costante. Nell'ordine:
#   1. la variabile d'ambiente `SECRET_KEY` — e' quella che si mette sul server
#   2. `data/secret_key.txt`, generata al primo avvio con 32 byte casuali
#
# Il file e' in `.gitignore` per la stessa ragione di `hub.db`. Non e' un ripiego:
# generare una chiave nuova a ogni avvio farebbe cadere le sessioni a ogni riavvio
# dell'app, e in locale sarebbe un fastidio quotidiano che invita a rimettere una
# costante — cioe' a rifare il buco.
CHIAVE = os.path.join(os.path.dirname(__file__), "data", "secret_key.txt")


def chiave_di_sessione():
    """La chiave con cui Flask firma i cookie. Mai una costante scritta nel codice."""
    dall_ambiente = os.environ.get("SECRET_KEY")
    if dall_ambiente:
        return dall_ambiente
    if os.path.exists(CHIAVE):
        with open(CHIAVE, encoding="utf-8") as f:
            salvata = f.read().strip()
        if salvata:
            return salvata
    import secrets
    nuova = secrets.token_hex(32)
    os.makedirs(os.path.dirname(CHIAVE), exist_ok=True)
    with open(CHIAVE, "w", encoding="utf-8") as f:
        f.write(nuova + "\n")
    return nuova


def password_di_default():
    """`True` se l'amministratore entra ancora con `admin123`.

    Serve all'avviso in dashboard: il seme di `init_db()` deve restare — un DB nuovo
    ha bisogno di un modo per entrarci — ma finche' nessuno la cambia quella password
    e' scritta nel repo, e la pagina di login la stampava pure. Toglierla di la' senza
    dire a chi ce l'ha ancora che ce l'ha ancora avrebbe solo reso il buco piu' zitto.

    ⚠️ **Si apre la connessione da se', e non c'e' nessun `except`.** Nata con un
    parametro `db` per riusare quella del chiamante, ha subito prodotto il baco che
    doveva evitare: in dashboard la connessione era gia' chiusa due righe sopra, e
    l'`except sqlite3.Error` traduceva l'errore in «no, la password non e' quella di
    default» — cioe' un **avviso di sicurezza che spariva per un guasto**, in
    silenzio, che e' il verso peggiore. Se questa query non risponde c'e' un problema
    vero, e va visto.
    """
    db = get_db()
    try:
        r = db.execute("SELECT password FROM users WHERE username='admin'").fetchone()
        return bool(r) and verifica_password(r["password"], "admin123")[0]
    finally:
        db.close()


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
    -- ── Fantacalcio (§4.2) ────────────────────────────────────────────────
    -- `fanta_players` e' il **listone**, ed e' un dato condiviso come il catalogo
    -- Pokemon: non ha un proprietario e non deve averlo. La chiave primaria e'
    -- l'id di fantacalcio.it, non un progressivo nostro, perche' e' quello che
    -- lega le tre pagine della fonte fra loro e i nostri dati alla fonte.
    -- ⚠️ `attivo` esiste per il **mercato**: un giocatore che a gennaio lascia la
    -- Serie A esce dal listone, ma puo' stare nella rosa di qualcuno. Si spegne,
    -- non si cancella - cancellarlo porterebbe via la riga di rosa con se'.
    CREATE TABLE IF NOT EXISTS fanta_players(
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL, slug TEXT,
        squadra TEXT, squadra_slug TEXT,
        ruolo_classic TEXT, ruolo_mantra TEXT, ruolo_mantra_esteso TEXT,
        qi INTEGER, qa INTEGER, fvm INTEGER,
        partite_a_voto INTEGER, media_voto REAL, fantamedia REAL,
        gol INTEGER, gol_subiti INTEGER, rigori TEXT, rigori_parati INTEGER,
        assist INTEGER, ammonizioni INTEGER, espulsioni INTEGER,
        attivo INTEGER DEFAULT 1,
        visto_il TEXT,
        aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    -- Le leghe, con le loro regole. Sono **dati dell'utente**: ogni SELECT qui
    -- sopra va filtrata con ambito_utente(), e una query nuova nasce scoperta.
    -- ⚠️ Dei valori di default **sette** vengono dal regolamento ufficiale, che
    -- `/regolamenti/leghe-private` elenca per esteso (riletto il 21/09/2026): gol
    -- +3 rigori compresi, assist +1, ammonizione -0,5, espulsione -1, gol subito
    -- -1, rigore parato +3, rigore sbagliato -3. I cartellini si fermano a -1
    -- comunque siano combinati. Restano **convenzionali** solo `bonus_imbattibilita`
    -- e `malus_autogol`, che il regolamento davvero non fissa perche' cambiano da
    -- lega a lega: quelli sono un punto di partenza da correggere, ed e' il motivo
    -- per cui queste regole stanno in colonne e non in un testo libero.
    -- (Fino a quel giorno qui era scritto «solo TRE»: era la prima lettura, fatta
    -- sulla pagina sbagliata, non una regola diversa.)
    -- ⚠️ `bonus_gol` e' **uno solo**, dal 21/09/2026. Prima erano quattro colonne
    -- (una per ruolo) e per il regolamento ufficiale di fantacalcio.it il gol vale
    -- **+3 comunque**, chiunque lo segni: quattro caselle da riempire con lo stesso
    -- numero erano quattro occasioni di sbagliarne una. La migrazione piu' sotto
    -- travasa il vecchio valore e toglie le quattro colonne, ma **solo** se in ogni
    -- lega erano uguali fra loro: dove non lo fossero, resterebbero li' invece di
    -- perdere in silenzio una differenza voluta.
    -- Il modificatore di difesa ha la **struttura** del regolamento ufficiale
    -- (media del portiere + migliori 3 difensori, esclusi bonus e malus, e serve
    -- che almeno 4 difensori portino voto) e i **valori** in `mod_difesa_soglie`,
    -- perche' quelli la piattaforma li lascia personalizzare.
    CREATE TABLE IF NOT EXISTS fanta_leagues(
        id INTEGER PRIMARY KEY, user_id INTEGER,
        nome TEXT NOT NULL,
        sistema TEXT DEFAULT 'classic',
        moduli TEXT DEFAULT '3-4-3,3-5-2,4-3-3,4-4-2,4-5-1,5-3-2,5-4-1',
        n_panchinari INTEGER DEFAULT 7,
        mod_difesa INTEGER DEFAULT 0,
        mod_difesa_portiere INTEGER DEFAULT 1,
        mod_difesa_soglie TEXT,
        bonus_gol REAL DEFAULT 3,
        bonus_assist REAL DEFAULT 1,
        malus_amm REAL DEFAULT -0.5, malus_esp REAL DEFAULT -1,
        malus_gol_subito REAL DEFAULT -1,
        bonus_imbattibilita REAL DEFAULT 1,
        bonus_rigore_parato REAL DEFAULT 3,
        malus_rigore_sbagliato REAL DEFAULT -3,
        malus_autogol REAL DEFAULT -2,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    -- La rosa: quali giocatori sono miei, in quale lega, e a che prezzo.
    -- ⚠️ Nessun ON DELETE CASCADE verso `fanta_players`: il listone si aggiorna,
    -- la rosa no. Un giocatore spento resta in rosa e la pagina lo dichiara.
    CREATE TABLE IF NOT EXISTS fanta_roster(
        id INTEGER PRIMARY KEY,
        league_id INTEGER REFERENCES fanta_leagues(id) ON DELETE CASCADE,
        player_id INTEGER REFERENCES fanta_players(id),
        prezzo REAL DEFAULT 0, note TEXT,
        UNIQUE(league_id, player_id));
    -- Le probabili formazioni, una giornata per volta. Dato **condiviso** come il
    -- listone (le formazioni della Serie A non sono di nessun utente) e
    -- **rigenerabile dalla fonte**: per questo non entra nell'export, esattamente
    -- come `fanta_players`. Quello che l'export deve salvare sono le leghe e le
    -- rose, che nessuna fonte sa ricostruire.
    -- La chiave e' (giornata, squadra): la pagina si riscrive di continuo fino al
    -- fischio d'inizio, quindi l'import **sovrascrive** la giornata che rilegge e
    -- lascia stare le altre.
    CREATE TABLE IF NOT EXISTS fanta_probabili_squadre(
        giornata INTEGER NOT NULL,
        squadra_slug TEXT NOT NULL,
        squadra TEXT, modulo TEXT,
        avversario TEXT, avversario_slug TEXT,
        in_casa INTEGER, match_id INTEGER,
        aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(giornata, squadra_slug));
    -- ⚠️ `player_id` **non** e' una foreign key verso `fanta_players`, ed e' una
    -- scelta: il 21/09/2026 dodici convocati delle probabili non erano nel listone
    -- (sono giocatori veri che la fonte non quota). Con il vincolo sarebbero stati
    -- buttati via in silenzio; senza, entrano e l'import dice quanti sono. Chi
    -- legge deve quindi fare una LEFT JOIN, non una JOIN.
    -- Il `modulo` qui e' quello **vero della squadra di Serie A** (3-4-2-1, quattro
    -- numeri): non ha niente a che vedere con i moduli del fantacalcio, che sono a
    -- tre e stanno in `fanta_leagues.moduli`. Confonderli non darebbe errore.
    CREATE TABLE IF NOT EXISTS fanta_probabili(
        giornata INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        nome TEXT, squadra_slug TEXT, ruolo TEXT,
        titolare INTEGER, percentuale INTEGER,
        aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(giornata, player_id));
    CREATE INDEX IF NOT EXISTS ix_probabili_giocatore
        ON fanta_probabili(player_id);
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

    # --- Proprietario delle righe (19/08/2026) -------------------------------
    # Fino a qui i contenuti non erano di nessuno: un team salvato da un utente lo
    # vedevano tutti. La colonna sta **solo sulle quattro tabelle radice**;
    # `team_members` e `pc_components` il proprietario lo ereditano dal padre con una
    # join, perche' ripeterlo sui figli vuol dire poterlo far divergere.
    #
    # ⚠️ Il travaso ad `admin` gira **solo nel giro in cui la colonna nasce**, non a
    # ogni avvio. Un `UPDATE ... WHERE user_id IS NULL` permanente sarebbe il solito
    # fallback silenzioso: una riga scritta domani senza proprietario diventerebbe
    # dell'admin da sola, e nessuno lo saprebbe. Cosi' invece resta `NULL`, e una riga
    # `NULL` non la vede nessuno — sbagliato in modo **visibile**, che e' il verso
    # giusto.
    # --- Il progresso di Python e' di chi lo fa (19/08/2026) -----------------
    # ⚠️ `python_topics` e' il caso storto: non e' contenuto dell'utente, e' un elenco
    # fisso di 53 voci seminato qui sopra, con la spunta `done` **sulla riga stessa**.
    # Quindi la spunta di uno era la spunta di tutti. La soluzione non e' un
    # `user_id` sull'elenco — servirebbero 53 righe per utente, e aggiungere un
    # argomento domani vorrebbe dire toccarle tutte — ma una tabella a parte: l'elenco
    # resta uno e condiviso, il progresso e' di chi lo mette.
    db.executescript("""
        CREATE TABLE IF NOT EXISTS python_progress(
            user_id INTEGER REFERENCES users(id),
            topic_id INTEGER REFERENCES python_topics(id),
            done INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, topic_id)
        );
    """)
    db.commit()
    # Il travaso delle spunte gia' messe, una volta sola: se la tabella e' vuota e
    # nell'elenco ci sono spunte, sono dell'admin — e' l'unico utente che c'era
    # quando `done` viveva sulla riga.
    if db.execute("SELECT COUNT(*) FROM python_progress").fetchone()[0] == 0:
        admin = db.execute(
            "SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        if admin:
            db.execute(
                "INSERT OR IGNORE INTO python_progress(user_id, topic_id, done) "
                "SELECT ?, id, 1 FROM python_topics WHERE done=1", (admin["id"],))
            db.commit()
    # ⚠️ La colonna `python_topics.done` **resta nel DB e nessuno la legge piu'**:
    # toglierla e' una migrazione a se', da fare con l'inventario del codice morto.
    # Fino ad allora e' la fotografia delle spunte dell'admin al 19/08/2026.

    for tabella in ("games", "teams", "arduino_projects", "pc_builds"):
        try:
            db.execute(f"ALTER TABLE {tabella} ADD COLUMN user_id INTEGER REFERENCES users(id)")
            db.commit()
        except Exception:
            continue                     # la colonna c'e' gia': niente da travasare
        admin = db.execute(
            "SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        if admin:
            db.execute(f"UPDATE {tabella} SET user_id=? WHERE user_id IS NULL", (admin["id"],))
            db.commit()

    # --- Calendario uscite ---------------------------------------------------
    # ⚠️ **Non e' la tua libreria, e non va in `games`.** Sono centinaia di titoli che
    # non possiedi: dentro `games` finirebbero nei conteggi della sezione, nei filtri
    # per genere e piattaforma, nel suggeritore "se ti e' piaciuto" e nell'export.
    # Sta in una tabella sua, che si puo' **buttare e rifare** senza perdere niente:
    # e' una cache di IGDB, non un dato curato.
    #
    # Per questo `game_releases` **non e' in `TABELLE` di `esporta_dati.py`**, e qui la
    # differenza va detta: `regulations` e' fuori dall'export **per caso** (vedi il
    # backlog), questa e' fuori **per scelta**. Esportare una cache rigenerabile
    # gonfierebbe il diff a ogni aggiornamento senza aggiungere niente da salvare.
    #
    # `igdb_release_id` e' UNIQUE perche' l'unita' del dato e' l'**uscita**, non il
    # gioco: lo stesso titolo esce su cinque piattaforme, e su IGDB sono cinque righe
    # con cinque date che possono essere diverse. E' anche cio' che rende l'import
    # rieseguibile senza duplicare (UPSERT su quella chiave).
    db.executescript("""
        CREATE TABLE IF NOT EXISTS game_releases(
            id INTEGER PRIMARY KEY,
            igdb_release_id INTEGER UNIQUE,
            igdb_game_id INTEGER,
            title TEXT NOT NULL,
            platform TEXT,
            platform_abbr TEXT,
            release_date TEXT,
            precisione TEXT,
            human TEXT,
            cover_url TEXT,
            igdb_url TEXT,
            region TEXT,
            hypes INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_releases_data ON game_releases(release_date);
        CREATE INDEX IF NOT EXISTS ix_releases_piattaforma ON game_releases(platform);
    """)
    # `hypes` e' quante persone su IGDB hanno messo in lista d'attesa il gioco, ed e'
    # l'unica misura dell'attesa che quel dump abbia davvero: misurato il 17/08/2026 su
    # 5954 uscite future, `follows` e' vuoto su **tutte** e `total_rating_count` e'
    # valorizzato sul 2% e conta i voti dei giochi **gia' usciti** (Elden Ring 2251),
    # cioe' non misura l'attesa. `hypes` c'e' sul 39% delle righe, fino a 982.
    # ⚠️ Aggiunta dopo, quindi serve l'ALTER per i DB che esistono gia': la CREATE TABLE
    # qui sopra tocca solo i DB nuovi. Stessa forma delle colonne aggiunte a `games`.
    try:
        db.execute("ALTER TABLE game_releases ADD COLUMN hypes INTEGER")
        db.commit()
    except Exception:
        pass

    # ── Fantacalcio: le regole della lega, rifatte il 21/09/2026 ─────────────
    # Le due colonne nuove del modificatore di difesa. Come sopra: la CREATE TABLE
    # vale solo per i DB nuovi, qui c'e' gia' una lega vera.
    for colonna, tipo in (("mod_difesa_portiere", "INTEGER DEFAULT 1"),
                          ("mod_difesa_soglie", "TEXT"),
                          ("bonus_gol", "REAL DEFAULT 3")):
        try:
            db.execute(f"ALTER TABLE fanta_leagues ADD COLUMN {colonna} {tipo}")
            db.commit()
        except Exception:
            pass
    # ⚠️ Il travaso dei quattro bonus gol in uno. La regola e' **non perdere in
    # silenzio**: se in qualche lega i quattro valori erano diversi fra loro, quella
    # differenza era voluta, quindi le colonne vecchie **restano dove sono** e il
    # travaso non si fa. Dove invece erano uguali - il caso normale, ed e' quello
    # che il regolamento ufficiale prevede - il valore si sposta e le quattro
    # colonne se ne vanno.
    try:
        vecchie = [r[1] for r in db.execute("PRAGMA table_info(fanta_leagues)")]
        if "bonus_gol_a" in vecchie:
            diverse = db.execute(
                "SELECT COUNT(*) FROM fanta_leagues WHERE bonus_gol_p<>bonus_gol_d "
                "OR bonus_gol_d<>bonus_gol_c OR bonus_gol_c<>bonus_gol_a").fetchone()[0]
            if not diverse:
                db.execute("UPDATE fanta_leagues SET bonus_gol=COALESCE(bonus_gol_a,3) "
                           "WHERE bonus_gol IS NULL")
                for colonna in ("bonus_gol_p", "bonus_gol_d", "bonus_gol_c",
                                "bonus_gol_a"):
                    db.execute(f"ALTER TABLE fanta_leagues DROP COLUMN {colonna}")
                db.commit()
    except Exception:
        # Un DROP COLUMN che non passa (SQLite vecchio) non deve impedire l'avvio:
        # le colonne restano, e il codice legge `bonus_gol` che ormai c'e'.
        pass
    db.commit()
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


# --- Proprietario delle righe -----------------------------------------------
# I permessi per sezione qui sopra dicono **quali sezioni** vedi. Questi dicono
# **di chi sono i dati** dentro, ed è una domanda diversa: un utente con la sezione
# Pokémon deve vedere i propri team, non quelli di tutti.

def utente_id():
    """L'id numerico dell'utente in sessione, o `None` se non c'è nessuno.

    ⚠️ Fino al 19/08/2026 in sessione c'erano solo `username`, `display_name` e
    `role`. Il cookie sopravvive al riavvio dell'app, quindi le sessioni già aperte
    non hanno `user_id` e non l'avrebbero mai: si ripesca **per nome una volta
    sola** e lo si scrive in sessione. Senza questo ramo, chi era già dentro si
    vedrebbe la sezione vuota senza capire perché.
    """
    if session.get("user_id"):
        return session["user_id"]
    nome = session.get("username")
    if not nome:
        return None
    db = get_db()
    r = db.execute("SELECT id FROM users WHERE username=?", (nome,)).fetchone()
    db.close()
    if not r:
        return None
    session["user_id"] = r["id"]
    return r["id"]


def e_admin():
    """L'utente in sessione è un amministratore?"""
    return (session.get("role") or "") == "admin"


def ambito_utente(colonna="user_id", di=None):
    """Condizione SQL e parametri che limitano una query a chi la sta facendo.

    Torna **sempre una condizione**, mai la stringa vuota, così il punto di chiamata
    la compone allo stesso modo ovunque e non deve sapere chi sta guardando::

        cond, par = ambito_utente()
        db.execute(f"SELECT * FROM teams WHERE {cond} ORDER BY created_at DESC", par)

    - utente normale → le sue righe e basta;
    - amministratore → tutto (`1=1`), e con `di=<id utente>` filtra su uno solo;
    - ⚠️ **nessuna sessione → niente** (`0=1`), ed è il ramo che deve fallire chiuso.
      Una condizione vuota qui vorrebbe dire «mostra tutto» proprio nel caso in cui
      non sappiamo a chi stiamo rispondendo.

    `colonna` serve per le query con un alias (`t.user_id`). Non arriva mai
    dall'utente: è scritta nel codice, come il resto della query.
    """
    if e_admin():
        if di:
            return f"{colonna}=?", [di]
        return "1=1", []
    uid = utente_id()
    if not uid:
        return "0=1", []
    return f"{colonna}=?", [uid]


def solo_mie(colonna="user_id"):
    """Come `ambito_utente()`, ma **senza la deroga dell'amministratore**.

    Serve dove «vedo tutto» sarebbe la risposta sbagliata: l'import da Steam cerca
    quali appid ci sono **già** per non duplicarli, e se quell'elenco comprendesse
    anche le righe altrui un admin che importa la propria libreria finirebbe a
    **riscrivere le ore giocate di un altro utente** invece di crearsi la sua riga.
    La regola, in una frase: si **legge** con `ambito_utente()`, si **importa** con
    questa.

    ⚠️ Anche qui nessuna sessione vuol dire `0=1`, non «tutte».
    """
    uid = utente_id()
    if not uid:
        return "0=1", []
    return f"{colonna}=?", [uid]


def _i(v, d=0):
    try: return int(v)
    except: return d


def _f(v, d=0.0):
    try: return float(v)
    except: return d