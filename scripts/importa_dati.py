#!/usr/bin/env python
"""Rimette dentro `hub.db` i dati di `data/backup/hub_export.json`.

    python scripts/importa_dati.py [--dry-run] [--sovrascrivi] [--file <export.json>]

È il **ritorno** di `esporta_dati.py`, che fino al 21/08/2026 non esisteva: un export
che nessuno sa rimettere dentro non è un backup, è un file. Il caso d'uso vero è il PC
nuovo — si clona il repo, si avvia l'app una volta perché `init_db()` crei lo schema,
e da qui rientrano giochi, team, progetti Arduino, build PC e progresso Python.

**Le regole, e il perché di ognuna:**

- **L'unità è la riga con la sua chiave primaria**, che per quasi tutte è l'`id` e
  per `python_progress` e `fanta_formazione` è doppia. Nessuna fusione per titolo o
  per nome: due giochi che si chiamano uguale con `id` diversi sono due righe
  diverse, e indovinare il contrario è il genere di scorciatoia che qui si paga. Le
  chiavi esterne (`team_members.team_id`, `pc_components.build_id`,
  `python_progress.topic_id`) puntano a quegli `id`: rimapparli vorrebbe dire
  riscriverle tutte. ⚠️ **La chiave si chiede allo schema, non si indovina** — vedi
  `chiave_di()`, e il 22/09/2026 sotto
- **Non sovrascrive niente senza dirlo.** Le righe che nel DB non ci sono entrano; una
  riga già presente e **identica** si salta in silenzio, ed è ciò che rende lo script
  rieseguibile; una riga già presente e **diversa** è un conflitto: lo script si
  **ferma** e li elenca. Per procedere serve `--sovrascrivi`, che è il momento in cui
  hai visto cosa stai per perdere
- ⚠️ **Le password esistenti non si toccano mai**, qualunque export si legga: stanno in
  `MAI_SOVRASCRITTE`, e sovrascriverle col nulla significherebbe distruggere l'unica
  copia buona. Per un utente **nuovo** invece dipende da quale dei due export è:
  l'export committabile non contiene password, quindi nasce con una **password casuale**
  che nessuno conosce e non entra finché un amministratore non gliela reimposta da
  `/utenti`; un backup `--completo` (§1.4, dal 18/09/2026) le contiene, e l'utente
  rientra con la sua. Lo script dice a schermo quale dei due casi è — ⚠️ e sono due
  messaggi diversi apposta: dire «rientrati senza password» dopo un backup completo
  sarebbe **falso**, e manderebbe a reimpostare a mano password già buone
- ⚠️ **`python_topics` è la trappola**, e ha una rete apposta. L'elenco lo semina
  `init_db()` con gli `id` 1..53 nell'ordine di `PYTHON_TOPICS`: se quell'ordine è
  cambiato fra l'export e oggi, l'`id` 7 nel backup è un argomento **diverso**
  dall'`id` 7 nel DB, e `python_progress` punta agli `id`. Importare le spunte così
  le metterebbe sugli argomenti sbagliati **senza nessun errore**. Perciò gli
  argomenti si confrontano per `(category, name)` a parità di `id`, e se non
  combaciano con del progresso da importare lo script si ferma
- **Copia di sicurezza prima di scrivere**, in `data/archive/hub_pre-import_*.db`.
  ⚠️ Quel nome è in `.gitignore`: la copia contiene gli hash delle password, ed è la
  ragione per cui `hub.db` non è versionato — la sua copia non può esserlo di nascosto

**Cosa NON tocca, e va detto perché il silenzio qui somiglia troppo a una svista:**

- `regulations` **c'è dal 18/09/2026**, ma solo se l'export è un `--completo`: quello
  committabile non la porta. È una tabella morta — la scrive `init_db()` e non la legge
  nessuno — e resta nell'elenco proprio per questo: così, con l'export normale, compare
  fra le «tabelle non presenti nell'export» invece di non comparire affatto
- `game_releases` è fuori **per scelta**: è la cache di IGDB, si rifà col pulsante
- le colonne che il DB ha e l'export no restano al loro default: le elenca
"""
import argparse
import datetime
import io
import json
import os
import secrets
import shutil
import sqlite3
import sys

# La console di Windows e' cp1252 e non sa scrivere le emoji. Come in esporta_dati.py
# non e' cosmetico: senza questa riga l'avviso di INTERRUZIONE — cioe' proprio il
# messaggio che spiega perche' ci si e' fermati — morirebbe su UnicodeEncodeError.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RADICE, "hub.db")
INGRESSO = os.path.join(RADICE, "data", "backup", "hub_export.json")
ARCHIVIO = os.path.join(RADICE, "data", "archive")
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)      # `inserisci()` importa `extensions.hash_password`

# ⚠️ L'ordine e' quello di inserimento, e **i padri vengono prima dei figli**:
# `get_db()` accende `PRAGMA foreign_keys`, quindi un `team_members` scritto prima del
# suo `teams` fallirebbe. E' lo stesso ordine di `TABELLE` in esporta_dati.py, ma qui
# non e' una coincidenza da cui dipendere: se una tabella nuova entra la', va messa
# **qui** al posto giusto, non in fondo.
ORDINE = [
    "users", "games", "teams", "team_members",
    "arduino_projects", "python_topics", "pc_builds", "pc_components",
    "python_progress",
    # ⚠️ Fantacalcio: la rosa **dopo** la lega, perché la nomina. E il listone
    # (`fanta_players`) non è in nessuno dei due export — si rifà dai due Excel
    # (pagina del Fantacalcio o `scripts/importa_listone.py`), **prima** di questo
    # ripristino, altrimenti le rose puntano a giocatori che non ci sono ancora.
    # ⚠️ La formazione **dopo** la rosa: nomina i giocatori che la rosa contiene.
    "fanta_leagues", "fanta_roster", "fanta_formazione",
    # ⚠️ Solo il backup `--completo` ce l'ha (§1.4, 18/09/2026). Con l'export
    # committabile questa riga fa solo comparire `regulations` fra le «tabelle non
    # presenti nell'export», che è la verità — prima non compariva affatto, ed è così
    # che una tabella resta fuori da un backup senza che nessuno se ne accorga.
    "regulations",
]

# Come si riconosce "la stessa riga": **si chiede allo schema**, non si indovina.
#
# ⚠️ Qui c'era un dizionario scritto a mano con dentro il solo `python_progress`, e un
# default `("id",)` per tutto il resto. Il 22/09/2026 ha smesso di funzionare in
# silenzio: `fanta_formazione`, nata il 21/09 con la chiave `(league_id, player_id)` e
# **senza** colonna `id`, non era stata aggiunta, quindi `indice()` cercava una
# colonna che non esiste e moriva con `KeyError: 'id'` — 19 prove su 23 rosse, e
# soprattutto **il ripristino intero rotto**: `esporta_dati.py` continuava a scrivere
# benissimo, quindi la copia di sicurezza c'era e sembrava a posto, e a non funzionare
# era l'unica cosa per cui esiste. È esattamente l'inciampo che `esporta_dati.py`
# aveva già pagato e già scritto (vedi `righe_tabella()`, «l'ordine si chiede allo
# schema»): la lezione era nel file gemello e non era passata di qua.
_CACHE_CHIAVI = {}

# Colonne che questo script non **sovrascrive** mai, per tabella. Su una riga nuova
# invece entrano, se l'export ce le ha: e' cio' che rendera' rileggibile il
# `--completo` di §1.4 senza toccare niente qui. Restano fuori anche dal **confronto**,
# per due ragioni: una password diversa non deve contare come conflitto (tanto non la
# si riscriverebbe comunque), e l'elenco dei conflitti si stampa a schermo — gli hash
# non ci vanno.
MAI_SOVRASCRITTE = {
    "users": {"password"},
    # ⚠️ `regulations.created_at` lo scrive `init_db()` **al momento**, quindi due DB
    # creati a secondi di distanza hanno la stessa riga con un timestamp diverso.
    # Senza questa riga ogni ripristino di un backup `--completo` su un DB appena
    # inizializzato si fermerebbe su un conflitto — su una **tabella morta**, per una
    # data — e l'unica via d'uscita sarebbe `--sovrascrivi`, cioè abituarsi a usare
    # proprio il flag pericoloso per un caso che pericoloso non è. Misurato scrivendo
    # `scripts/prova_esporta_completo.py` il 18/09/2026: la prova passava o falliva a
    # seconda che i due `init_db()` cadessero nello stesso secondo.
    "regulations": {"created_at"},
}


def leggibile(percorso):
    """Il path relativo alla radice se ci sta dentro, altrimenti quello assoluto.

    Un `--db` fuori dal repo — il caso delle prove, che girano su una **copia** —
    con `relpath` diventa una collana di punti e barre che non dice niente.
    """
    intero = os.path.abspath(percorso)
    if os.path.commonpath([intero, RADICE]) == RADICE:
        return os.path.relpath(intero, RADICE)
    return intero


def chiave_di(db, tabella):
    """Le colonne che individuano «la stessa riga», prese dalla chiave primaria.

    Torna una tupla vuota se la tabella non ha una chiave primaria: lì non si tira a
    indovinare — `piano_tabella()` si ferma e lo dice. Una riga senza un modo per
    riconoscerla rientrerebbe **doppia** a ogni riesecuzione, che è il contrario di
    quello che questo script promette.
    """
    if tabella in _CACHE_CHIAVI:
        return _CACHE_CHIAVI[tabella]
    try:
        schema = [(r[1], r[5]) for r in db.execute(f"PRAGMA table_info({tabella})")]
    except sqlite3.Error:
        schema = []
    chiave = tuple(nome for nome, pk in sorted(schema, key=lambda x: x[1]) if pk)
    _CACHE_CHIAVI[tabella] = chiave
    return chiave


def schema_db(db, tabella):
    """Le colonne della tabella nel DB, o `None` se la tabella non c'e'."""
    try:
        righe = db.execute(f"PRAGMA table_info({tabella})").fetchall()
    except sqlite3.Error:
        return None
    return [r[1] for r in righe] or None


def uguali(a, b):
    """Confronto di due valori della stessa colonna, tolleranti sui numeri.

    `hours_hltb` e' REAL: SQLite torna `40.0` dove il JSON puo' avere `40`. Senza
    questa tolleranza ogni riesecuzione vedrebbe un conflitto che non c'e', e lo
    script si fermerebbe sempre — cioe' smetterebbe di essere rieseguibile.
    """
    if a is None or b is None:
        return a is b or (a is None and b is None)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        return float(a) == float(b)
    return str(a) == str(b)


def indice(db, tabella, colonne, chiave):
    """`{chiave: riga}` di cio' che c'e' gia' nel DB, per le sole colonne dell'export."""
    campi = ", ".join(colonne)
    cur = db.execute(f"SELECT {campi} FROM {tabella}")
    fuori = {}
    for r in cur.fetchall():
        d = {c: r[c] for c in colonne}
        fuori[tuple(d[c] for c in chiave)] = d
    return fuori


def piano_tabella(db, tabella, righe_export):
    """`(nuove, identiche, conflitti, colonne_assenti_nel_db, colonne_solo_nel_db)`.

    `conflitti` e' la lista `(chiave, differenze)` dove `differenze` sono le sole
    colonne che cambierebbero: e' quello che viene stampato prima di sovrascrivere.
    """
    colonne_db = schema_db(db, tabella)
    if colonne_db is None:
        return None
    colonne_export = list(righe_export[0].keys()) if righe_export else []
    assenti = [c for c in colonne_export if c not in colonne_db]
    solo_db = [c for c in colonne_db if c not in colonne_export]
    if assenti:
        return ("SCHEMA", assenti)

    # ⚠️ Prima di toccare le righe: la chiave dev'essere **usabile**, cioè esistere e
    # stare dentro le colonne dell'export. Senza questi due controlli il caso di
    # `fanta_formazione` usciva come `KeyError: 'id'` dentro `indice()` — un errore
    # che non dice né quale tabella né cosa fare, e che ha tenuto rotto il ripristino
    # per un giorno intero senza che l'export desse il minimo segno.
    chiave = chiave_di(db, tabella)
    if not chiave:
        return ("CHIAVE", "non ha una chiave primaria: non c'è modo di sapere se una "
                          "riga dell'export è già dentro")
    fuori_export = [c for c in chiave if colonne_export and c not in colonne_export]
    if fuori_export:
        return ("CHIAVE", "la chiave primaria è (" + ", ".join(chiave) + ") e "
                          "nell'export manca " + ", ".join(fuori_export))
    presenti = indice(db, tabella, colonne_export, chiave) if colonne_export else {}
    nuove, identiche, conflitti = [], 0, []
    for riga in righe_export:
        k = tuple(riga[c] for c in chiave)
        vecchia = presenti.get(k)
        if vecchia is None:
            nuove.append(riga)
            continue
        intoccabili = MAI_SOVRASCRITTE.get(tabella, set())
        diverse = {c: (vecchia[c], riga[c]) for c in colonne_export
                   if c not in intoccabili and not uguali(vecchia[c], riga[c])}
        if diverse:
            conflitti.append((k, diverse))
        else:
            identiche += 1
    return (nuove, identiche, conflitti, assenti, solo_db)


def argomenti_disallineati(db, dati):
    """Gli `id` di `python_topics` che nel DB sono un argomento **diverso**.

    ⚠️ E' la rete descritta in cima: `python_progress.topic_id` punta a questi `id`,
    e se l'elenco e' stato riordinato le spunte finirebbero sull'argomento sbagliato
    senza che niente lo segnali.
    """
    export = {r["id"]: (r.get("category"), r.get("name"))
              for r in dati.get("python_topics", [])}
    if not export:
        return []
    fuori = []
    for r in db.execute("SELECT id, category, name FROM python_topics").fetchall():
        atteso = export.get(r["id"])
        if atteso and (atteso[0] != r["category"] or atteso[1] != r["name"]):
            fuori.append((r["id"], f"{r['category']} / {r['name']}",
                          f"{atteso[0]} / {atteso[1]}"))
    return fuori


def username_in_collisione(db, dati):
    """Utenti dell'export con lo stesso `username` di uno gia' presente ma `id` diverso.

    `users.username` e' UNIQUE: senza questo controllo l'INSERT solleverebbe a meta'
    strada, e il messaggio di sqlite non direbbe **quale** utente.
    """
    presenti = {r["username"]: r["id"]
                for r in db.execute("SELECT id, username FROM users").fetchall()}
    fuori = []
    for r in dati.get("users", []):
        altro = presenti.get(r.get("username"))
        if altro is not None and altro != r.get("id"):
            fuori.append((r.get("username"), r.get("id"), altro))
    return fuori


def inserisci(db, tabella, riga):
    colonne = list(riga.keys())
    valori = [riga[c] for c in colonne]
    if tabella == "users" and "password" not in colonne:
        # ⚠️ Una password casuale che nessuno conosce, non una vuota e non una nota:
        # l'utente non entra finche' un amministratore non gliela reimposta. Il conto
        # lo stampa `main()`, perche' un utente che non puo' entrare e non lo sa e'
        # esattamente il tipo di silenzio che questo progetto paga.
        # ⚠️ `not in colonne` non e' una cautela di troppo: se un giorno l'export
        # `--completo` di §1.4 portera' le password vere, senza questa condizione la
        # colonna finirebbe due volte nella stessa INSERT.
        from extensions import hash_password
        colonne.append("password")
        valori.append(hash_password(secrets.token_hex(32)))
    campi = ", ".join(colonne)
    segni = ", ".join("?" for _ in colonne)
    db.execute(f"INSERT INTO {tabella}({campi}) VALUES({segni})", valori)


def sovrascrivi_riga(db, tabella, riga):
    chiave = chiave_di(db, tabella)
    fuori = MAI_SOVRASCRITTE.get(tabella, set()) | set(chiave)
    colonne = [c for c in riga.keys() if c not in fuori]
    if not colonne:
        return 0
    assegna = ", ".join(f"{c}=?" for c in colonne)
    dove = " AND ".join(f"{c}=?" for c in chiave)
    cur = db.execute(f"UPDATE {tabella} SET {assegna} WHERE {dove}",
                     [riga[c] for c in colonne] + [riga[c] for c in chiave])
    return cur.rowcount


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    ap.add_argument("--sovrascrivi", action="store_true",
                    help="sovrascrive le righe in conflitto (mai le password)")
    ap.add_argument("--file", default=INGRESSO,
                    help=f"export da rileggere (default: {leggibile(INGRESSO)})")
    ap.add_argument("--db", default=DB, help="DB su cui scrivere (default: hub.db)")
    args = ap.parse_args()

    if not os.path.exists(args.file):
        print(f"Export non trovato: {args.file}")
        return 1
    if not os.path.exists(args.db):
        print(f"{leggibile(args.db)} non esiste.")
        print("    Lo schema lo crea `init_db()`: avvia l'app una volta e riprova.")
        return 1

    with io.open(args.file, encoding="utf-8") as f:
        dati = json.load(f)

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    # --- Il piano, tabella per tabella -------------------------------------
    piani, mancanti, schema_rotto, chiave_rotta = {}, [], [], []
    for tabella in ORDINE:
        righe = dati.get(tabella)
        if righe is None:
            mancanti.append(tabella)
            continue
        p = piano_tabella(db, tabella, righe)
        if p is None:
            schema_rotto.append((tabella, "la tabella non esiste nel DB"))
            continue
        if p[0] == "SCHEMA":
            schema_rotto.append((tabella, "colonne assenti nel DB: " + ", ".join(p[1])))
            continue
        if p[0] == "CHIAVE":
            chiave_rotta.append((tabella, p[1]))
            continue
        piani[tabella] = p

    # Le chiavi che cominciano per `_` non sono tabelle: il backup `--completo` ci mette
    # `_meta` con la data. Elencarle fra le «sconosciute» farebbe sembrare un problema
    # una cosa voluta.
    ignorate = [t for t in dati if t not in ORDINE and not t.startswith("_")]
    con_password = any("password" in r for r in (dati.get("users") or []))

    print(f"Export:  {leggibile(args.file)}")
    print(f"DB:      {leggibile(args.db)}\n")
    print(f"  {'tabella':<18} {'nuove':>7} {'già uguali':>12} {'in conflitto':>14}")
    for tabella in ORDINE:
        if tabella not in piani:
            continue
        nuove, identiche, conflitti, _, _ = piani[tabella]
        print(f"  {tabella:<18} {len(nuove):>7} {identiche:>12} {len(conflitti):>14}")

    if mancanti:
        print(f"\n  (tabelle non presenti nell'export: {', '.join(mancanti)})")
    if ignorate:
        print(f"  (chiavi dell'export che questo script non conosce: {', '.join(ignorate)})")
    for tabella in ORDINE:
        if tabella in piani and piani[tabella][4] and dati.get(tabella):
            print(f"  ({tabella}: colonne che l'export non ha, restano al default: "
                  f"{', '.join(piani[tabella][4])})")

    if schema_rotto:
        print("\n⚠️  INTERROTTO: il DB è più vecchio dell'export.")
        for tabella, perche in schema_rotto:
            print(f"      {tabella}: {perche}")
        print("\n    Lo schema lo porta avanti `init_db()`, non questo script: avvia")
        print("    l'app una volta e riprova. Scrivere ora perderebbe quelle colonne.")
        db.close()
        return 1

    if chiave_rotta:
        print("\n⚠️  INTERROTTO: non so riconoscere «la stessa riga».")
        for tabella, perche in chiave_rotta:
            print(f"      {tabella}: {perche}")
        print("\n    La chiave si chiede allo schema, e senza non si tira a indovinare:")
        print("    scrivere ora rifarebbe quelle righe **doppie** a ogni riesecuzione.")
        db.close()
        return 1

    # --- Le due reti --------------------------------------------------------
    collisioni = username_in_collisione(db, dati)
    if collisioni:
        print("\n⚠️  INTERROTTO: stesso username con id diverso.")
        for username, id_export, id_db in collisioni:
            print(f"      «{username}»: id {id_export} nell'export, {id_db} nel DB")
        print("\n    `users.username` è UNIQUE, quindi queste righe non possono")
        print("    convivere. Va deciso a mano quale delle due tenere: rimapparle")
        print("    da qui vorrebbe dire riscrivere ogni `user_id` che le punta.")
        db.close()
        return 1

    storti = argomenti_disallineati(db, dati)
    if storti:
        progresso = len(dati.get("python_progress") or [])
        print(f"\n⚠️  {len(storti)} argomenti Python hanno lo stesso id ma nome diverso:")
        for topic_id, nel_db, nell_export in storti[:5]:
            print(f"      id {topic_id}: DB «{nel_db}» ≠ export «{nell_export}»")
        if len(storti) > 5:
            print(f"      … e altri {len(storti) - 5}")
        if progresso:
            print(f"\n    INTERROTTO: ci sono {progresso} spunte da importare, e")
            print("    `python_progress.topic_id` punta a questi id. Importarle ora")
            print("    le metterebbe sugli argomenti sbagliati senza nessun errore.")
            print("    L'elenco lo semina `init_db()` da PYTHON_TOPICS: o si riallinea")
            print("    quello all'export, o le spunte vanno rifatte a mano.")
            db.close()
            return 1
        print("    Nessuna spunta da importare, quindi nessun danno: proseguo.")

    # --- I conflitti --------------------------------------------------------
    tutti_conflitti = [(t, piani[t][2]) for t in ORDINE
                       if t in piani and piani[t][2]]
    if tutti_conflitti and not args.sovrascrivi:
        quanti = sum(len(c) for _, c in tutti_conflitti)
        print(f"\n⚠️  INTERROTTO: {quanti} righe esistono già con un contenuto diverso.")
        for tabella, conflitti in tutti_conflitti:
            for chiave, differenze in conflitti[:3]:
                # una chiave di una colonna sola si stampa nuda: `(7,)` con la virgola
                # e' la ripr. di una tupla Python, non un id, e in un messaggio che va
                # letto in fretta somiglia troppo a un refuso
                etichetta = chiave[0] if len(chiave) == 1 else chiave
                print(f"      {tabella} {etichetta}:")
                for colonna, (nel_db, nell_export) in list(differenze.items())[:4]:
                    print(f"          {colonna}: {nel_db!r} → {nell_export!r}")
            if len(conflitti) > 3:
                print(f"      … e altre {len(conflitti) - 3} righe in {tabella}")
        print("\n    Le righe nuove non sono state scritte: o tutto o niente.")
        print("    Se l'export è la versione buona:  --sovrascrivi")
        db.close()
        return 1

    da_scrivere = sum(len(piani[t][0]) for t in piani)
    da_sovrascrivere = sum(len(piani[t][2]) for t in piani) if args.sovrascrivi else 0
    if not da_scrivere and not da_sovrascrivere:
        print("\nNiente da fare: il DB ha già tutto quello che c'è nell'export.")
        db.close()
        return 0

    # ⚠️ Il listone non è nell'export, e le righe del Fantacalcio lo nominano: la
    # rosa dice **quale** giocatore hai comprato, la formazione **chi** hai
    # schierato. Su un DB dove `fanta_players` è vuoto quelle righe violano la
    # foreign key, e SQLite lo dice a modo suo — «FOREIGN KEY constraint failed»,
    # che non fa capire né cosa manca né cosa fare.
    #
    # Trovato il 21/09/2026: finché la rosa era vuota il caso non si presentava,
    # e si è visto **appena una rosa vera è entrata nell'export**. Il commento in
    # `esporta_dati.py` lo dichiarava da sempre («il listone va reimportato
    # prima»); quello che mancava era dirlo **qui**, dove serve.
    mancanti = {}
    for tabella, listone in (("fanta_roster", "fanta_players"),
                             ("fanta_formazione", "fanta_players")):
        nuove = piani.get(tabella, ([],))[0]
        for riga in nuove:
            pid = riga.get("player_id")
            if pid is None:
                continue
            if not db.execute(f"SELECT 1 FROM {listone} WHERE id=?", (pid,)).fetchone():
                mancanti.setdefault(tabella, set()).add(pid)
    if mancanti:
        quanti = sum(len(v) for v in mancanti.values())
        print(f"\n⚠️  {quanti} giocator{'e' if quanti == 1 else 'i'} nominat"
              f"{'o' if quanti == 1 else 'i'} dal Fantacalcio non "
              f"{'è' if quanti == 1 else 'sono'} in questo DB:")
        for tabella, ids in mancanti.items():
            print(f"     {tabella}: {len(ids)} ({', '.join(str(i) for i in sorted(ids)[:8])}"
                  f"{'…' if len(ids) > 8 else ''})")
        print("    Il **listone** non sta nell'export di proposito — è una copia dei")
        print("    due Excel di fantacalcio.it che si rifà in un minuto — ma la rosa e")
        print("    la formazione lo nominano, quindi va importato PRIMA, dalla pagina")
        print("    del Fantacalcio oppure con:")
        print("        python scripts/importa_listone.py QUOTAZIONI.xlsx STATISTICHE.xlsx")
        print("    INTERROTTO: niente scritto.")
        db.close()
        return 1

    if args.dry_run:
        print(f"\n--dry-run: {da_scrivere} righe da inserire, "
              f"{da_sovrascrivere} da sovrascrivere. Non ho scritto niente.")
        db.close()
        return 0

    # --- La copia di sicurezza, poi la scrittura ----------------------------
    # ⚠️ Il nome sta in `.gitignore`: qui dentro ci sono gli hash delle password, ed e'
    # la ragione per cui `hub.db` non e' versionato. Una copia versionata di nascosto
    # sarebbe lo stesso buco con un altro nome.
    # ⚠️ La copia segue il DB, non la radice: con un `--db` fuori dal repo — cioe' le
    # prove — una destinazione fissa in `data/archive/` sporcherebbe una cartella
    # versionata a ogni giro, con dei file che contengono gli hash delle password.
    dentro = os.path.commonpath([os.path.abspath(args.db), RADICE]) == RADICE
    accanto = ARCHIVIO if dentro else os.path.dirname(os.path.abspath(args.db))
    os.makedirs(accanto, exist_ok=True)
    quando = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    copia = os.path.join(accanto, f"hub_pre-import_{quando}.db")
    shutil.copy2(args.db, copia)
    print(f"\nCopia di sicurezza: {leggibile(copia)}")

    utenti_nuovi = len(piani.get("users", ([], 0, [], [], []))[0])
    scritte, sovrascritte, a_vuoto = 0, 0, []
    try:
        db.execute("BEGIN")
        for tabella in ORDINE:
            if tabella not in piani:
                continue
            nuove, _, conflitti, _, _ = piani[tabella]
            for riga in nuove:
                inserisci(db, tabella, riga)
                scritte += 1
            if args.sovrascrivi:
                for chiave, _ in conflitti:
                    riga = next(r for r in dati[tabella]
                                if tuple(r[c] for c in chiave_di(db, tabella)) == chiave)
                    # ⚠️ `rowcount` a zero e' la trappola gia' pagata in `_team_upsert()`:
                    # un UPDATE che non tocca niente non da' errore, e il codice sotto
                    # continua come se avesse funzionato.
                    if sovrascrivi_riga(db, tabella, riga) == 0:
                        a_vuoto.append((tabella, chiave))
                    else:
                        sovrascritte += 1
        if a_vuoto:
            raise RuntimeError(f"{len(a_vuoto)} UPDATE non hanno toccato nessuna riga: "
                               f"{a_vuoto[:3]}")
        db.commit()
    except Exception as e:
        db.rollback()
        db.close()
        print(f"\n⚠️  INTERROTTO e annullato: {e}")
        print(f"    Il DB è com'era. La copia resta in {leggibile(copia)}.")
        return 1
    db.close()

    print(f"Scritte {scritte} righe nuove, {sovrascritte} sovrascritte.")
    if utenti_nuovi and not con_password:
        print(f"\n⚠️  {utenti_nuovi} utenti sono rientrati **senza password**: l'export")
        print("    non le contiene di proposito. Non possono entrare finché un")
        print("    amministratore non gliela reimposta da /utenti.")
        print("    Per riaverle serve un backup fatto con `esporta_dati.py --completo`.")
    elif utenti_nuovi:
        # ⚠️ Dirlo, e dirlo solo qui: la riga di sopra sarebbe **falsa** con un backup
        # completo, e un avviso falso è peggio di nessun avviso — manderebbe a
        # reimpostare a mano password che sono appena rientrate giuste.
        print(f"\n{utenti_nuovi} utenti sono rientrati **con la loro password**: "
              "l'export è un backup completo.")
        print("    Quelli già nel DB tengono la password che hanno: non si sovrascrive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
