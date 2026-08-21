#!/usr/bin/env python
"""Rimette dentro `hub.db` i dati di `data/backup/hub_export.json`.

    python scripts/importa_dati.py [--dry-run] [--sovrascrivi] [--file <export.json>]

È il **ritorno** di `esporta_dati.py`, che fino al 21/08/2026 non esisteva: un export
che nessuno sa rimettere dentro non è un backup, è un file. Il caso d'uso vero è il PC
nuovo — si clona il repo, si avvia l'app una volta perché `init_db()` crei lo schema,
e da qui rientrano giochi, team, progetti Arduino, build PC e progresso Python.

**Le regole, e il perché di ognuna:**

- **L'unità è la riga con il suo `id`.** Nessuna fusione per titolo o per nome: due
  giochi che si chiamano uguale con `id` diversi sono due righe diverse, e indovinare
  il contrario è il genere di scorciatoia che qui si paga. Le chiavi esterne
  (`team_members.team_id`, `pc_components.build_id`, `python_progress.topic_id`)
  puntano a quegli `id`: rimapparli vorrebbe dire riscriverle tutte
- **Non sovrascrive niente senza dirlo.** Le righe che nel DB non ci sono entrano; una
  riga già presente e **identica** si salta in silenzio, ed è ciò che rende lo script
  rieseguibile; una riga già presente e **diversa** è un conflitto: lo script si
  **ferma** e li elenca. Per procedere serve `--sovrascrivi`, che è il momento in cui
  hai visto cosa stai per perdere
- ⚠️ **Le password non si toccano mai.** L'export non le contiene di proposito (viene
  committato), quindi qui non c'è niente con cui riscriverle: sovrascriverle
  significherebbe distruggere l'unica copia buona con il nulla. Un utente **nuovo**
  nasce perciò con una password casuale che nessuno conosce — non entra finché un
  amministratore non gliela reimposta da `/utenti`, e lo script lo dice a schermo.
  Il verso è quello giusto: un utente che non entra è un problema visibile, un utente
  che entra con una password nota da tutti no
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

- `regulations` non è nell'export (falla 1 di §1.4: è omessa **per caso**, non per
  scelta, ed è comunque una tabella morta). Finché non entra là, qui non c'è
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
]

# Come si riconosce "la stessa riga". Il default e' `id`; `python_progress` non ce
# l'ha, ha la chiave doppia — lo stesso inciampo che in esporta_dati.py faceva
# dichiarare **assente** una tabella che c'era.
CHIAVI = {"python_progress": ("user_id", "topic_id")}

# Colonne che questo script non **sovrascrive** mai, per tabella. Su una riga nuova
# invece entrano, se l'export ce le ha: e' cio' che rendera' rileggibile il
# `--completo` di §1.4 senza toccare niente qui. Restano fuori anche dal **confronto**,
# per due ragioni: una password diversa non deve contare come conflitto (tanto non la
# si riscriverebbe comunque), e l'elenco dei conflitti si stampa a schermo — gli hash
# non ci vanno.
MAI_SOVRASCRITTE = {"users": {"password"}}


def leggibile(percorso):
    """Il path relativo alla radice se ci sta dentro, altrimenti quello assoluto.

    Un `--db` fuori dal repo — il caso delle prove, che girano su una **copia** —
    con `relpath` diventa una collana di punti e barre che non dice niente.
    """
    intero = os.path.abspath(percorso)
    if os.path.commonpath([intero, RADICE]) == RADICE:
        return os.path.relpath(intero, RADICE)
    return intero


def chiave_di(tabella):
    return CHIAVI.get(tabella, ("id",))


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

    chiave = chiave_di(tabella)
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
    chiave = chiave_di(tabella)
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
    piani, mancanti, schema_rotto = {}, [], []
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
        piani[tabella] = p

    ignorate = [t for t in dati if t not in ORDINE]

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
                                if tuple(r[c] for c in chiave_di(tabella)) == chiave)
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
    if utenti_nuovi:
        print(f"\n⚠️  {utenti_nuovi} utenti sono rientrati **senza password**: l'export")
        print("    non le contiene di proposito. Non possono entrare finché un")
        print("    amministratore non gliela reimposta da /utenti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
