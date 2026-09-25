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
    """'it' o 'en'. Fuori da una richiesta, o con un valore strano, torna 'it'.

    ⚠️ Legge **il cookie**, non il DB, e di proposito: questa funzione gira su ogni
    pagina e su ogni tendina renderizzata dal server, e una query per volta sarebbe
    un prezzo pagato mille volte per un dato che cambia due volte l'anno. La scelta
    salvata sull'utente viene **scritta nel cookie al login** (vedi `auth.login`), e
    da lì in poi le due dicono la stessa cosa. Chi non ha una sessione — la pagina di
    login — ha comunque il cookie, ed è il motivo per cui il cookie resta.
    """
    try:
        scelta = request.cookies.get(COOKIE_LINGUA)
    except RuntimeError:          # nessun contesto di richiesta
        return "it"
    return scelta if scelta in LINGUE else "it"


TEMI = ("dark", "light", "oceano", "sabbia")


def tema_in_sessione():
    """Il tema salvato di chi sta guardando, o `None`.

    ⚠️ Sta **in sessione**, non riletto dal DB a ogni pagina: lo scrive `login()` e lo
    aggiorna il salvataggio. Una query per pagina per un dato che cambia due volte
    l'anno sarebbe un prezzo pagato mille volte — la stessa ragione per cui
    `lingua_attiva()` legge il cookie.
    """
    try:
        scelto = session.get("tema")
    except RuntimeError:
        return None
    return scelto if scelto in TEMI else None


def salva_preferenza(db, uid, campo, valore):
    """Scrive `tema` o `lingua` sull'utente. Torna True se ha scritto.

    ⚠️ La colonna **non** arriva da chi chiama senza passare di qui: finisce dentro
    una query, e un nome di colonna che viene da fuori è la porta d'ingresso di
    sempre. E il valore si controlla contro l'elenco dei validi — non per diffidenza
    del browser, ma perché un `data-theme` inesistente lascerebbe la pagina col solo
    `:root` senza dare nessun errore.
    """
    if campo == "tema":
        if valore not in TEMI:
            return False
    elif campo == "lingua":
        if valore not in LINGUE:
            return False
    else:
        return False
    db.execute(f"UPDATE users SET {campo}=? WHERE id=?", (valore, uid))
    return True


def preferenze_utente(db, uid):
    """`(tema, lingua)` salvati sull'utente. `None` dove non ha mai scelto.

    ⚠️ I valori si **validano leggendoli**, non solo scrivendoli: una riga arrivata
    da un `importa_dati.py` di un DB più vecchio, o ritoccata a mano, non deve poter
    mettere un `data-theme` che non esiste — la pagina resterebbe col solo `:root`,
    cioè giusta per caso.
    """
    r = db.execute("SELECT tema, lingua FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        return None, None
    tema = r["tema"] if r["tema"] in TEMI else None
    lingua = r["lingua"] if r["lingua"] in LINGUE else None
    return tema, lingua


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


# --- La fusione del Fantacalcio (25/09/2026) ----------------------------------
# Decisione di Davide: si tiene la sezione nata il 24/09 come «Fantacalcio 2», quella
# vecchia (che leggeva le pagine di fantacalcio.it) se ne va, e la 2 ne prende il
# nome. Nel DB vuol dire: le tabelle `fanta_*` vecchie via, le `fanta2_*` rinominate
# `fanta_*`. Deve girare **prima** delle CREATE TABLE qui sotto: su un DB non ancora
# fuso le `fanta_*` esistono già con lo schema vecchio, `IF NOT EXISTS` le lascerebbe
# stare e il codice nuovo leggerebbe colonne che non ci sono.
FANTA_VECCHIE = ("fanta_formazione", "fanta_roster", "fanta_leagues",
                 "fanta_probabili", "fanta_probabili_squadre", "fanta_calendario",
                 "fanta_players",
                 # Le scelte di «Chi gioca», tolte il 25/09/2026 e morte da allora.
                 "fanta2_titolari")
FANTA_DA_RINOMINARE = ("players", "leagues", "roster", "formazione", "calendario",
                       "classifica")


def _unisci_fantacalcio(db):
    """La fusione, **una volta sola**: se `fanta2_leagues` non c'è, è già fatta.

    Torna il rapporto (`None` se non c'era niente da fare), e lo stampa.

    ⚠️ Una lega che la sezione vecchia aveva e la nuova no — **stesso proprietario e
    stesso nome** — si porta nelle tabelle nuove con la sua rosa, invece di sparire
    con le tabelle: il 25/09/2026 era «Triplete», 25 giocatori (decisione di Davide).
    La formazione vecchia **non** si porta, e nemmeno le righe di rosa di un giocatore
    che il listone nuovo non ha: quelle si contano e si dicono.

    ⚠️ Prima di toccare niente lascia una copia del DB: in `data/archive/` se il DB è
    quello del progetto, accanto al DB se è un altro (una prova non deve sporcare la
    cartella del repository). Tutto il resto è **una transazione**: una fusione a metà
    — tabelle vecchie cancellate e nuove non ancora rinominate — non deve esistere.
    """
    tabelle = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "fanta2_leagues" not in tabelle:
        return None
    qui = os.path.dirname(os.path.abspath(__file__))
    dove = os.path.dirname(os.path.abspath(DB))
    cartella = os.path.join(DATA_DIR, "archive") if dove == qui else dove
    os.makedirs(cartella, exist_ok=True)
    copia = os.path.join(cartella, "hub_pre-unione-fantacalcio.db")
    if not os.path.exists(copia):
        dest = sqlite3.connect(copia)
        db.backup(dest)
        dest.close()

    r = {"copia": copia, "leghe": [], "rosa": 0, "rosa_persa": 0, "tolte": []}
    db.execute("BEGIN")
    try:
        if "fanta_leagues" in tabelle and "fanta_roster" in tabelle:
            nuove = [c[1] for c in db.execute("PRAGMA table_info(fanta2_leagues)")]
            for lega in db.execute("SELECT * FROM fanta_leagues ORDER BY id").fetchall():
                gia = db.execute(
                    "SELECT 1 FROM fanta2_leagues WHERE nome=? AND user_id IS ?",
                    (lega["nome"], lega["user_id"])).fetchone()
                if gia:
                    continue
                colonne = [c for c in lega.keys() if c != "id" and c in nuove]
                nuovo = db.execute(
                    f"INSERT INTO fanta2_leagues({', '.join(colonne)}) "
                    f"VALUES({', '.join('?' for _ in colonne)})",
                    [lega[c] for c in colonne]).lastrowid
                prima = db.execute("SELECT COUNT(*) FROM fanta_roster WHERE league_id=?",
                                   (lega["id"],)).fetchone()[0]
                portate = db.execute(
                    "INSERT INTO fanta2_roster(league_id, player_id, prezzo, note) "
                    "SELECT ?, player_id, prezzo, note FROM fanta_roster "
                    "WHERE league_id=? AND player_id IN (SELECT id FROM fanta2_players)",
                    (nuovo, lega["id"])).rowcount
                r["leghe"].append(lega["nome"])
                r["rosa"] += portate
                r["rosa_persa"] += prima - portate
        for t in FANTA_VECCHIE:
            if t in tabelle:
                db.execute(f"DROP TABLE {t}")
                r["tolte"].append(t)
        for t in FANTA_DA_RINOMINARE:
            if f"fanta2_{t}" in tabelle:
                db.execute(f"ALTER TABLE fanta2_{t} RENAME TO fanta_{t}")
        # Il permesso segue la sezione: chi aveva spuntato «Fantacalcio 2» la vede
        # ancora. Chi aveva `fantacalcio` vede quella nuova, che ora si chiama così.
        # Senza, `sezioni_utente()` scarterebbe lo slug sparito in silenzio.
        if "users" in tabelle:
            db.execute("UPDATE users SET sections=REPLACE(sections, 'fantacalcio2', "
                       "'fantacalcio') WHERE sections LIKE '%fantacalcio2%'")
        db.commit()
    except Exception:
        db.rollback()
        raise
    print(f"[DB] Fantacalcio unito: copia in {copia}. "
          f"Leghe portate dalla sezione vecchia: {', '.join(r['leghe']) or 'nessuna'} "
          f"({r['rosa']} in rosa"
          + (f", {r['rosa_persa']} fuori dal listone nuovo e non portati" if r["rosa_persa"] else "")
          + f"). Tabelle tolte: {len(r['tolte'])}.")
    return r


def init_db():
    db = get_db()
    _unisci_fantacalcio(db)
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
    -- ── Fantacalcio (§4.2, §4.6) ──────────────────────────────────────────
    -- Fonti **in regola**: il listone dai due Excel che Davide scarica col suo
    -- login, calendario e classifica da football-data.org. Fino al 25/09/2026 queste
    -- tabelle si chiamavano `fanta2_*` e accanto c'era la sezione vecchia, che
    -- leggeva le pagine di fantacalcio.it: la fusione in `_unisci_fantacalcio()` ha
    -- tolto quella e dato a queste il nome.
    -- `fanta_players` e' il **listone**, ed e' un dato condiviso come il catalogo
    -- Pokemon: non ha un proprietario e non deve averlo. La chiave primaria e'
    -- l'id di fantacalcio.it, lo stesso nei due file.
    -- ⚠️ `attivo` esiste per il **mercato**: un giocatore che lascia la Serie A esce
    -- dal listone, ma puo' stare nella rosa di qualcuno. Si spegne, non si
    -- cancella - cancellarlo porterebbe via la riga di rosa con se'.
    -- `ceduto` e' il foglio «Ceduti» del file: chi ha lasciato la Serie A, spento e
    -- non cancellato. `autogol` c'e' perche' il file delle statistiche lo porta.
    CREATE TABLE IF NOT EXISTS fanta_players(
        id INTEGER PRIMARY KEY,
        nome TEXT NOT NULL,
        squadra TEXT, squadra_slug TEXT,
        ruolo_classic TEXT, ruolo_mantra TEXT,
        qi INTEGER, qa INTEGER, fvm INTEGER,
        partite_a_voto INTEGER, media_voto REAL, fantamedia REAL,
        gol INTEGER, gol_subiti INTEGER, rigori TEXT, rigori_parati INTEGER,
        assist INTEGER, ammonizioni INTEGER, espulsioni INTEGER, autogol INTEGER,
        ceduto INTEGER DEFAULT 0,
        attivo INTEGER DEFAULT 1,
        visto_il TEXT,
        aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    -- Le leghe, con le loro regole. Sono **dati dell'utente**: ogni SELECT qui
    -- sopra va filtrata con ambito_utente(), e una query nuova nasce scoperta.
    -- ⚠️ Dei valori di default **sette** vengono dal regolamento ufficiale, che
    -- `/regolamenti/leghe-private` elenca per esteso (riletto il 21/09/2026): gol
    -- +3 rigori compresi, assist +1, ammonizione -0,5, espulsione -1, gol subito
    -- -1, rigore parato +3, rigore sbagliato -3. Restano **convenzionali** solo
    -- `bonus_imbattibilita` e `malus_autogol`, che il regolamento non fissa perche'
    -- cambiano da lega a lega: e' il motivo per cui queste regole stanno in colonne
    -- e non in un testo libero.
    -- ⚠️ `bonus_gol` e' **uno solo**, dal 21/09/2026: per il regolamento il gol vale
    -- +3 chiunque lo segni, e quattro caselle uguali erano quattro occasioni di
    -- sbagliarne una.
    -- Il modificatore di difesa ha la **struttura** del regolamento ufficiale
    -- (media del portiere + migliori 3 difensori, esclusi bonus e malus, e serve
    -- che almeno 4 difensori portino voto) e i **valori** in `mod_difesa_soglie`,
    -- perche' quelli la piattaforma li lascia personalizzare.
    -- Il `modulo_scelto` e' quello della formazione schierata: sta qui e non su ogni
    -- riga di `fanta_formazione` perche' una formazione ne ha **uno**.
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
        modulo_scelto TEXT,
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
    -- La formazione schierata, **una per lega**: decisione di Davide del
    -- 21/09/2026, contro l'alternativa «una per giornata». Non c'e' quindi una
    -- colonna `giornata`, ed e' voluto: senza storico **non e' verificabile a
    -- posteriori** se il consiglio consigliava bene.
    -- `ordine` e' il posto in campo per i titolari e **l'ordine di subentro** per i
    -- panchinari: e' l'ordine che decide chi entra al posto di chi non gioca.
    CREATE TABLE IF NOT EXISTS fanta_formazione(
        league_id INTEGER REFERENCES fanta_leagues(id) ON DELETE CASCADE,
        player_id INTEGER REFERENCES fanta_players(id),
        titolare INTEGER NOT NULL,
        ordine INTEGER NOT NULL,
        ruolo TEXT,
        PRIMARY KEY(league_id, player_id));
    -- Il calendario da football-data.org: **tutta la stagione**, una riga per
    -- partita, riscritta a ogni aggiornamento. Dato condiviso e rigenerabile,
    -- quindi fuori dall'export come il listone.
    -- ⚠️ `stato` conta quanto l'ora: `SCHEDULED` vuol dire che l'ora e'
    -- **approssimativa**, e solo `TIMED` (o una partita gia' cominciata) ha l'ora
    -- vera. `inizio` e' 'YYYY-MM-DD HH:MM' in **ora italiana**, senza fuso: il
    -- browser che fa il conto alla rovescia sta nello stesso fuso della Serie A.
    -- ⚠️ `casa_slug`/`fuori_slug` possono essere NULL: una squadra che non si
    -- abbina al listone resta senza, e la pagina lo dice invece di indovinare.
    CREATE TABLE IF NOT EXISTS fanta_calendario(
        match_id INTEGER PRIMARY KEY,
        giornata INTEGER, stato TEXT,
        inizio TEXT, utc TEXT,
        casa TEXT, casa_slug TEXT, fuori TEXT, fuori_slug TEXT,
        gol_casa INTEGER, gol_fuori INTEGER,
        aggiornata_fonte TEXT,
        aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    -- La classifica **totale**: l'unica del piano gratuito (niente casa/trasferta,
    -- `form` vuoto). Serve a mostrare l'avversario accanto al giocatore, non a
    -- pesarlo: decisione di Davide del 24/09/2026.
    -- `stemma` e' l'indirizzo dell'immagine sul CDN di football-data.org, non il
    -- file: lo carica il browser (25/09/2026).
    CREATE TABLE IF NOT EXISTS fanta_classifica(
        squadra_slug TEXT PRIMARY KEY,
        squadra TEXT, posizione INTEGER, punti INTEGER, giocate INTEGER,
        gol_fatti INTEGER, gol_subiti INTEGER, stemma TEXT,
        aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    -- ── «Ricorda credenziali» (22/09/2026) ────────────────────────────────
    -- ⚠️ **Qui dentro non c'e' nessuna password, e non ci sara' mai.** Quello che
    -- si ricorda e' una **sessione**: un numero casuale da 32 byte che vive nel
    -- cookie del browser, e di cui qui resta solo l'**impronta** — cosi' chi
    -- leggesse questa tabella non potrebbe farsi passare per nessuno, esattamente
    -- come per `users.password`.
    -- ⚠️ Un cookie soltanto **firmato** non sarebbe bastato: una firma si verifica
    -- ma non si **revoca**, e la richiesta di Davide dice «con scadenza e con la
    -- possibilita' di revocarla». Una riga in tabella si cancella; una firma no.
    -- Per questo la riga c'e', e per questo `scade_il` e' scritta dentro e non
    -- lasciata al solo `max_age` del cookie, che vive sul PC di chi naviga.
    CREATE TABLE IF NOT EXISTS sessioni_ricordate(
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        impronta TEXT NOT NULL UNIQUE,
        creata_il TEXT NOT NULL,
        scade_il TEXT NOT NULL,
        usata_il TEXT,
        da TEXT);
    -- ── Stampa 3D (§4, dal 25/09/2026) ──────────────────────────────────────
    -- Sul modello di Arduino: il progetto e' un **dato dell'utente**, quindi ogni
    -- SELECT va filtrata con ambito_utente(). I link si controllano per dominio in
    -- `stampa3d.py`, come quelli dei negozi del PC Builder.
    CREATE TABLE IF NOT EXISTS stampa_progetti(
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        nome TEXT NOT NULL,
        stato TEXT DEFAULT 'Idea',
        stampante TEXT, materiale TEXT,
        link_modello TEXT, link_disegno TEXT,
        grammi REAL, note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    -- I file allegati. ⚠️ Il file sta su disco in `data/stampa3d/` col nome della
    -- sua **impronta** (sha256), non con quello caricato: due righe con lo stesso
    -- file - una copia fra utenti, lo stesso .3mf in due progetti - puntano allo
    -- stesso file, e il file si toglie dal disco solo quando nessuna riga lo nomina
    -- piu'. Il nome caricato resta qui, ed e' quello con cui si riscarica.
    -- ⚠️ I file **non** sono nell'export (sono binari): una riga ripristinata su un
    -- PC nuovo senza la cartella dice «file mancante», non finge.
    CREATE TABLE IF NOT EXISTS stampa_file(
        id INTEGER PRIMARY KEY,
        progetto_id INTEGER REFERENCES stampa_progetti(id) ON DELETE CASCADE,
        nome TEXT NOT NULL, impronta TEXT NOT NULL, byte INTEGER,
        caricato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    -- L'inventario delle bobine. `peso_rimasto` si scala a mano o da un progetto
    -- stampato (i suoi `grammi`): nessuna stampante lo dice all'hub, oggi.
    CREATE TABLE IF NOT EXISTS stampa_filamenti(
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        materiale TEXT, marca TEXT, colore TEXT, colore_hex TEXT,
        peso_totale REAL DEFAULT 1000, peso_rimasto REAL,
        prezzo REAL, note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
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

    # --- Tema e lingua seguono l'utente, non il browser (22/09/2026) ----------
    # ⚠️ Erano le **due personalizzazioni che nessun export poteva prendere** (§1.4,
    # falla 2): il tema in `localStorage` e la lingua nel cookie `hub_lang`, tutti e
    # due **per browser**. Quindi cambiando PC — o ripristinando su una macchina
    # nuova, che è il caso d'uso di tutto `importa_dati.py` — si ripartiva da capo,
    # e nessuno lo diceva.
    # ⚠️ **Il browser resta la via veloce e non sparisce**: `localStorage` e il
    # cookie servono ancora alla pagina di login, dove un utente non c'è. Qui si
    # aggiunge la **verità che segue la persona**, e `NULL` vuol dire «non ha mai
    # scelto», che è diverso da «ha scelto lo scuro».
    for colonna in ("tema", "lingua"):
        try:
            db.execute(f"ALTER TABLE users ADD COLUMN {colonna} TEXT")
            db.commit()
        except Exception:
            pass                            # la colonna c'e' gia'

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

    # Lo stemma della squadra, dal 25/09/2026. Stessa forma di sopra: la CREATE TABLE
    # vale solo per i DB nuovi. Si riempie al primo «Aggiorna» del calendario.
    try:
        db.execute("ALTER TABLE fanta_classifica ADD COLUMN stemma TEXT")
        db.commit()
    except Exception:
        pass

    # PC Builder, dal 25/09/2026: stato del pezzo, prezzi scritti a mano con la loro
    # data, soglia per l'avviso e indirizzi incollati dei negozi (`pc_negozi.py`).
    # Solo ALTER, come le colonne di `games`: gira anche sui DB nuovi, subito dopo la
    # CREATE TABLE, quindi l'elenco sta in un posto solo. `stato` NULL vuol dire «non
    # indicato» — le righe di prima — e non «posseduto»: gli avvisi le ignorano.
    for col, tipo in [("stato", "TEXT"), ("prezzo_data", "TEXT"), ("obiettivo", "REAL"),
                      ("valore_usato", "REAL"), ("valore_usato_data", "TEXT"),
                      ("link_amazon", "TEXT"), ("link_eprice", "TEXT"),
                      ("link_bpm", "TEXT"), ("link_versus", "TEXT"),
                      # il pezzo del catalogo OpenDB a cui è collegato (`pc_catalogo.py`)
                      ("opendb_id", "TEXT")]:
        try:
            db.execute(f"ALTER TABLE pc_components ADD COLUMN {col} {tipo}")
            db.commit()
        except Exception:
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


# --- Le tabelle che hanno un proprietario -----------------------------------
# Non è un promemoria: è l'elenco su cui gira il travaso di `admin.py`, e sta qui
# perché dev'esserne **uno solo**. La lezione è del 22/09/2026: l'elenco viveva
# scritto a mano dentro `utente_elimina()` e si era fermato alle quattro radici del
# 19/08, mentre le tabelle con un `user_id` erano diventate sei. Le due dimenticate
# fallivano in due modi opposti, e nessuno dei due si vedeva leggendo il codice:
# `fanta_leagues` non ha una chiave esterna verso `users`, quindi l'utente spariva e
# la sua lega restava intestata a un id che non esiste più, portandosi dietro rosa e
# formazione; `python_progress` invece la chiave esterna ce l'ha, quindi la
# cancellazione **falliva** — FOREIGN KEY constraint failed, 500, e la connessione
# nemmeno chiusa.
#
# Cosa dice il valore:
#   `passa`    → le righe cambiano proprietario. Sono **contenuto**, nessuna fonte
#                sa ricostruirle, e non si perde niente (decisione del 19/08/2026)
#   `cancella` → le righe si cancellano, e quante erano **si dice a schermo**. Non
#                sono contenuto, sono lo stato personale di chi non c'è più:
#                intestare a un altro le spunte di Python vorrebbe dire scrivere
#                che ha fatto cose che non ha fatto, cioè inventare un dato
TABELLE_UTENTE = {
    "games": "passa",
    "teams": "passa",
    "arduino_projects": "passa",
    "pc_builds": "passa",
    "fanta_leagues": "passa",
    "stampa_progetti": "passa",
    "stampa_filamenti": "passa",
    "python_progress": "cancella",
    # ⚠️ `cancella` qui non è ordine, è **sicurezza**, e la rete si è fatta trovare
    # subito: questa tabella è nata il 22/09/2026 e `tabelle_senza_regola()` l'ha
    # messa davanti prima che servisse ricordarsene. Se fosse `passa`, eliminare un
    # utente regalerebbe all'amministratore le sue sessioni ricordate — cioè dei
    # cookie vivi su browser altrui — e il pulsante «copia» le duplicherebbe su un
    # secondo utente, che è la stessa cosa scritta peggio. Le righe `cancella` non
    # si copiano e non passano: spariscono, ed è l'unica risposta giusta.
    "sessioni_ricordate": "cancella",
}


def tabelle_con_user_id(db):
    """Le tabelle che nello schema **vero** hanno una colonna `user_id`."""
    nomi = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return [n for n in nomi
            if any(c["name"] == "user_id" for c in db.execute(f"PRAGMA table_info({n})"))]


# Le **figlie**: righe che un `user_id` non ce l'hanno e il proprietario lo ereditano
# dal padre. Nel travaso di `utente_elimina()` seguono il padre da sole, perché il
# padre resta quello e cambia solo a chi è intestato. In una **copia** no: il padre
# nuovo ha un id nuovo, e la figlia va riscritta con quello — per questo l'elenco
# serve qui e non serviva prima.
FIGLIE_DI = {
    "teams": (("team_members", "team_id"),),
    "pc_builds": (("pc_components", "build_id"),),
    "fanta_leagues": (("fanta_roster", "league_id"),
                      ("fanta_formazione", "league_id")),
    # La copia duplica la **riga**, non il file: il file sta su disco col nome della
    # sua impronta, e due righe che la nominano sono lo stesso file (stampa3d.py).
    "stampa_progetti": (("stampa_file", "progetto_id"),),
}


def tabelle_senza_regola(db):
    """Le tabelle con un proprietario di cui `TABELLE_UTENTE` non dice niente.

    È il pezzo che tiene l'elenco attaccato allo schema invece che alla memoria di
    chi lo legge: una settima tabella con un `user_id` compare **qui**, e chi la
    aggiunge se la trova davanti, invece di scoprirla un anno dopo da una lega
    orfana. Chi la usa deve **fermarsi**, non tirare a indovinare: passare o
    cancellare le righe di una tabella che non si conosce è esattamente il
    fallback silenzioso che questo progetto paga ogni volta.
    """
    return [t for t in tabelle_con_user_id(db) if t not in TABELLE_UTENTE]


def _tabelle(db):
    return [r["name"] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def figlie_senza_regola(db):
    """Le tabelle che puntano a una riga copiata e che `FIGLIE_DI` non nomina.

    Stessa rete di `tabelle_senza_regola()`, dall'altro lato: là si guarda chi ha un
    `user_id`, qui chi ha una **chiave esterna** verso una tabella che la copia
    duplica. Una figlia dimenticata non darebbe errore — il padre nuovo nascerebbe
    **vuoto**, e un team senza i suoi sei Pokémon somiglia a un team.
    Torna `[(figlia, padre), …]`; le tabelle gia' dichiarate non compaiono.
    """
    copiate = {t for t, r in TABELLE_UTENTE.items() if r == "passa"}
    dichiarate = {n for figlie in FIGLIE_DI.values() for n, _ in figlie}
    note = copiate | dichiarate
    fuori = set()
    for t in _tabelle(db):
        if t in note:
            continue
        try:
            legami = list(db.execute(f"PRAGMA foreign_key_list({t})"))
        except sqlite3.Error:
            continue
        for r in legami:
            if r["table"] in note:
                fuori.add((t, r["table"]))
    return sorted(fuori)


def _inserisci_copia(db, tabella, riga, cambi):
    """Riscrive una riga con dei valori sostituiti. `None` vuol dire «togli la colonna».

    L'`id` si toglie, non si copia: lo assegna SQLite, ed e' tutto il punto di una
    copia. ⚠️ `fanta_formazione` un `id` non ce l'ha — la sua chiave e'
    `(league_id, player_id)` — e qui va bene da sola perche' si guarda cosa la riga
    **ha**, non cosa dovrebbe avere.
    """
    colonne, valori = [], []
    for c in riga.keys():
        if c in cambi and cambi[c] is None:
            continue
        colonne.append(c)
        valori.append(cambi[c] if c in cambi else riga[c])
    segni = ", ".join("?" for _ in colonne)
    cur = db.execute(f"INSERT INTO {tabella}({', '.join(colonne)}) "
                     f"VALUES({segni})", valori)
    return cur.lastrowid


def copia_dati_utente(db, da, a):
    """Duplica i contenuti dell'utente `da` su `a`. Torna `{tabella: quante righe}`.

    ⚠️ **Aggiunge, non sostituisce** — decisione di Davide del 22/09/2026. Le righe
    entrano con un id nuovo **accanto** a quelle che il destinatario ha gia', e non
    si perde niente di suo. Il prezzo e' che **non e' rieseguibile**: premuto due
    volte lascia tutto in doppio. E non c'e' un modo onesto di renderlo tale — per
    riconoscere «questa riga c'e' gia'» servirebbe confrontare i **contenuti**, cioe'
    fondere per titolo o per nome, ed e' esattamente la scorciatoia che
    `importa_dati.py` rifiuta per iscritto. Quindi si dichiara: chi chiama mette i
    numeri nella conferma, prima.

    ⚠️ Le tabelle marcate `cancella` in `TABELLE_UTENTE` **non si copiano**: sono
    stato personale — oggi le spunte di Python — e copiarle scriverebbe che il
    destinatario ha studiato quello che non ha studiato. Chi chiama lo dice a
    schermo invece di tacerlo, che e' l'altra meta' della decisione.

    Non apre ne' chiude transazioni: e' il chiamante che decide l'unita' di lavoro,
    perche' una copia a meta' e' il caso peggiore di tutti.
    """
    fatte = {}
    for tabella, regola in TABELLE_UTENTE.items():
        if regola != "passa":
            continue
        righe = db.execute(f"SELECT * FROM {tabella} WHERE user_id=?",
                           (da,)).fetchall()
        for riga in righe:
            nuovo = _inserisci_copia(db, tabella, riga, {"id": None, "user_id": a})
            fatte[tabella] = fatte.get(tabella, 0) + 1
            for figlia, colonna in FIGLIE_DI.get(tabella, ()):
                for f in db.execute(f"SELECT * FROM {figlia} WHERE {colonna}=?",
                                    (riga["id"],)).fetchall():
                    _inserisci_copia(db, figlia, f, {"id": None, colonna: nuovo})
                    fatte[figlia] = fatte.get(figlia, 0) + 1
    return fatte


def conteggi_utente(db):
    """`{user_id: {tabella: quante}}` per le tabelle che la copia duplica.

    Serve alla pagina Utenti: la conferma deve dire **cosa** sta per raddoppiare, e
    un «sei sicuro?» senza numeri davanti a un pulsante non rieseguibile non e' una
    conferma, e' un passaggio da premere in fretta.
    """
    fuori = {}
    for tabella, regola in TABELLE_UTENTE.items():
        if regola != "passa":
            continue
        for r in db.execute(f"SELECT user_id, COUNT(*) AS quante FROM {tabella} "
                            f"WHERE user_id IS NOT NULL GROUP BY user_id"):
            fuori.setdefault(r["user_id"], {})[tabella] = r["quante"]
    return fuori


# --- «Ricorda credenziali» --------------------------------------------------
# ⚠️ Quello che si ricorda è **una sessione, non la password**: la password non esce
# mai da `users`, e qui non entra mai. Il cookie porta un numero casuale da 32 byte;
# nel DB ne resta solo l'impronta sha256, che basta a riconoscerlo e non basta a
# rifarlo. Un token casuale da 256 bit non ha bisogno di scrypt — scrypt serve a
# rendere cara la forza bruta su un segreto **indovinabile**, e questo non lo è.
COOKIE_RICORDA = "hub_ricorda"
GIORNI_RICORDA = 30


def _ora():
    import datetime
    return datetime.datetime.now().replace(microsecond=0).isoformat(" ")


def _impronta(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def crea_sessione_ricordata(db, uid, da=""):
    """Scrive la riga e torna il **token in chiaro**, che esiste solo qui e nel cookie."""
    import datetime, secrets
    token = secrets.token_urlsafe(32)
    scade = (datetime.datetime.now() + datetime.timedelta(days=GIORNI_RICORDA))
    db.execute("INSERT INTO sessioni_ricordate(user_id, impronta, creata_il, "
               "scade_il, da) VALUES(?,?,?,?,?)",
               (uid, _impronta(token), _ora(),
                scade.replace(microsecond=0).isoformat(" "), (da or "")[:160]))
    return token


def utente_da_ricordare(db, token):
    """L'utente a cui appartiene il token, o `None`. Le scadute le butta.

    ⚠️ **Il token non si ruota a ogni uso**, ed è una scelta: ruotarlo è la difesa
    da un cookie rubato, ma una pagina che parte con tre `fetch()` in parallelo ne
    manderebbe tre copie insieme, la prima vincerebbe e le altre due si
    troverebbero davanti un token appena cancellato — cioè si verrebbe buttati
    fuori a caso, e quel baco non lo riprodurrebbe nessuno. Le difese qui sono la
    **scadenza** (30 giorni, scritta nella riga e non solo nel cookie) e la
    **revoca**, che è esplicita e non dipende dalla fortuna.
    """
    if not token:
        return None
    db.execute("DELETE FROM sessioni_ricordate WHERE scade_il < ?", (_ora(),))
    r = db.execute("SELECT s.id, u.id AS uid, u.username, u.display_name, u.role "
                   "FROM sessioni_ricordate s JOIN users u ON u.id = s.user_id "
                   "WHERE s.impronta = ?", (_impronta(token),)).fetchone()
    if not r:
        return None
    db.execute("UPDATE sessioni_ricordate SET usata_il=? WHERE id=?", (_ora(), r["id"]))
    return r


def dimentica_sessione(db, token):
    """Revoca **questo** dispositivo: è quello che fa il logout."""
    if token:
        db.execute("DELETE FROM sessioni_ricordate WHERE impronta=?", (_impronta(token),))


def dimentica_tutte(db, uid):
    """Revoca **tutti** i dispositivi di un utente. Torna quante righe erano.

    ⚠️ La chiama anche il cambio password, e non è un di più: se la password è stata
    cambiata perché qualcuno la sapeva, lasciare vivi i cookie di quel qualcuno
    vorrebbe dire non aver cambiato niente.
    """
    cur = db.execute("DELETE FROM sessioni_ricordate WHERE user_id=?", (uid,))
    return cur.rowcount


def _i(v, d=0):
    try: return int(v)
    except: return d


def _f(v, d=0.0):
    try: return float(v)
    except: return d