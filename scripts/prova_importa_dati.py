#!/usr/bin/env python
"""Le prove di `scripts/importa_dati.py`. Non tocca `hub.db`.

    python scripts/prova_importa_dati.py [--tieni]

Ogni prova gira su un DB **suo**, creato da `init_db()` in una cartella temporanea e
buttato alla fine. ⚠️ Non è pignoleria: il 16/08/2026 uno script di prova che
cancellava «il mio intervallo» di id si è portato via **497 righe vere** dalla cache
delle uscite. Un test che condivide lo stato con i dati veri misura anche quelli.

Cosa dimostra, in ordine:

- il **giro vero**: DB appena creato da `init_db()` → import → ogni tabella
  dell'export ha le sue righe, e l'app ci si apre sopra. ⚠️ Di una si guarda
  anche il **contenuto**: `fanta_formazione` è l'unica senza una colonna `id`,
  ed è quella che il 22/09/2026 teneva rotto il ripristino intero
- **rieseguibile**: la seconda esecuzione non scrive niente e lo dice
- le **quattro reti** che devono fermarlo: righe in conflitto, `python_topics`
  riordinato con delle spunte da importare, `username` duplicato con `id` diverso,
  DB più vecchio dell'export
- che `--sovrascrivi` **non tocchi la password**, che è l'unica cosa che l'export non
  contiene e quindi l'unica che non può essere rimessa a posto se si perde
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(RADICE, "data", "backup", "hub_export.json")
IMPORTA = os.path.join(RADICE, "scripts", "importa_dati.py")
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []


def esito(nome, ok, dettaglio=""):
    esiti.append((nome, ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def gira(db, *extra, file=EXPORT):
    r = subprocess.run([sys.executable, IMPORTA, "--db", db, "--file", file, *extra],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=RADICE)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def db_vergine(dove, nome, col_listone=True):
    """Un DB come lo crea `init_db()` su un PC nuovo: schema, `admin`, i 53 argomenti.

    ⚠️ Con `col_listone` ci mette anche i giocatori che l'export nomina. Il listone
    **non sta nell'export** — è una copia di fantacalcio.it che si rifà in un
    minuto — ma la rosa e la formazione lo nominano, e su un DB dove
    `fanta_players` è vuoto quelle righe violano la foreign key. È il passo che un
    ripristino vero fa **prima** (`importa_listone.py`), e qui si finge.

    Trovato il 21/09/2026: finché la rosa era vuota questa prova passava senza
    toccare il caso, e si è rotta appena una rosa vera è entrata nell'export.
    """
    import extensions
    percorso = os.path.join(dove, nome)
    vecchio, extensions.DB = extensions.DB, percorso
    try:
        extensions.init_db()
    finally:
        extensions.DB = vecchio
    if col_listone:
        export = json.load(io_json(EXPORT))
        ids = {r["player_id"] for t in ("fanta_roster", "fanta_formazione")
               for r in export.get(t, []) if r.get("player_id")}
        if ids:
            c = sqlite3.connect(percorso)
            c.executemany("INSERT OR IGNORE INTO fanta_players(id, nome, attivo) "
                          "VALUES(?, 'finto', 1)", [(i,) for i in sorted(ids)])
            c.commit()
            c.close()
    return percorso


def conta(db, tabella):
    c = sqlite3.connect(db)
    try:
        return c.execute(f"SELECT COUNT(*) FROM {tabella}").fetchone()[0]
    finally:
        c.close()


def esegui(db, *sql):
    c = sqlite3.connect(db)
    for q in sql:
        c.execute(q)
    c.commit()
    c.close()


def valore(db, query):
    c = sqlite3.connect(db)
    try:
        r = c.execute(query).fetchone()
        return r[0] if r else None
    finally:
        c.close()


def prove(dove):
    export = json.load(io_json(EXPORT))

    # --- 1. il giro vero: DB vergine -> import ------------------------------
    base = db_vergine(dove, "base.db")
    rc, out = gira(base, "--dry-run")
    esito("--dry-run non scrive", rc == 0 and conta(base, "games") == 0
          and "Non ho scritto niente" in out)
    rc, out = gira(base)
    combaciano = all(conta(base, t) == len(righe) for t, righe in export.items())
    esito("import su DB vergine -> le tabelle dell'export combaciano tutte",
          rc == 0 and combaciano,
          " ".join(f"{t}={conta(base, t)}" for t in export))
    esito("l'utente rientrato senza password è dichiarato a schermo",
          "senza password" in out)
    esito("la copia di sicurezza è stata lasciata", "Copia di sicurezza" in out)

    # ⚠️ Il conteggio non basta, e il 22/09/2026 si è visto perché: la tabella che
    # ha tenuto rotto **tutto** il ripristino è `fanta_formazione`, l'unica senza
    # una colonna `id`. Qui si guarda una riga **dentro**, ritrovata per la sua
    # chiave vera `(league_id, player_id)`: è il caso che la vecchia `chiave_di()`
    # non sapeva nemmeno indirizzare.
    schierati = export.get("fanta_formazione") or []
    if schierati:
        atteso = schierati[0]
        c = sqlite3.connect(base)
        c.row_factory = sqlite3.Row
        riga = c.execute("SELECT * FROM fanta_formazione WHERE league_id=? AND "
                         "player_id=?", (atteso["league_id"],
                                         atteso["player_id"])).fetchone()
        c.close()
        esito("la formazione schierata torna indietro riga per riga, non solo come conto",
              riga is not None
              and all(riga[k] == v for k, v in atteso.items()),
              f"({atteso['league_id']}, {atteso['player_id']}) "
              + ("assente" if riga is None else dict(riga).__str__()[:70]))
    else:
        esito("la formazione schierata torna indietro riga per riga, non solo come conto",
              False, "l'export non ha righe di fanta_formazione: prova non eseguita")

    # --- 1b. il ripristino senza listone -------------------------------------
    # ⚠️ Il caso del 21/09/2026: la rosa e la formazione nominano giocatori che
    # stanno **solo** nel listone, e il listone non è nell'export. Su un DB dove
    # `fanta_players` è vuoto SQLite diceva «FOREIGN KEY constraint failed», che
    # non fa capire né cosa manca né cosa fare.
    export = json.load(io_json(EXPORT))
    if any(r.get("player_id") for t in ("fanta_roster", "fanta_formazione")
           for r in export.get(t, [])):
        nudo = db_vergine(dove, "senza_listone.db", col_listone=False)
        rc, out = gira(nudo)
        esito("⚠️ ripristino senza listone: si ferma e dice di importarlo prima",
              rc == 1 and "importa_listone.py" in out)
        esito("   e non ha scritto niente", conta(nudo, "games") == 0,
              f"games={conta(nudo, 'games')}")
        esito("   il messaggio nomina la tabella che lo causa",
              "fanta_roster" in out or "fanta_formazione" in out)
    else:
        esito("⚠️ (export senza rose: il caso «senza listone» non si può provare)",
              True, "rimettere una rosa nell'export per riattivarla")

    rc, out = gira(base)
    esito("rieseguibile: la seconda volta non fa niente e lo dice",
          rc == 0 and "Niente da fare" in out)
    # ⚠️ Le prove non devono sporcare il repo: la copia di sicurezza di un DB che sta
    # fuori da qui va **accanto a quel DB**. Con la destinazione fissa in
    # `data/archive/` un giro di prove lasciava 13 file con dentro gli hash.
    esito("un DB fuori dal repo non lascia copie in data/archive/",
          not [f for f in os.listdir(os.path.join(RADICE, "data", "archive"))
               if f.startswith("hub_pre-import")]
          and any(f.startswith("hub_pre-import") for f in os.listdir(dove)))

    # --- 2. l'app si apre sul DB ripristinato -------------------------------
    esito("l'app si apre sul DB ripristinato e mostra i dati", *app_regge(base))

    # --- 3. conflitto: si ferma, e la password resta -------------------------
    conf = os.path.join(dove, "conflitto.db")
    shutil.copy2(base, conf)
    esegui(conf,
           "UPDATE games SET title='TITOLO CAMBIATO A MANO' "
           "WHERE id=(SELECT MIN(id) FROM games)",
           "UPDATE users SET display_name='Nome cambiato' WHERE id=1")
    pw_prima = valore(conf, "SELECT password FROM users WHERE id=1")
    rc, out = gira(conf)
    esito("conflitto -> si ferma", rc == 1 and "INTERROTTO" in out)
    esito("conflitto -> dice quale riga e quale colonna cambierebbe",
          "TITOLO CAMBIATO A MANO" in out and "display_name" in out)
    esito("conflitto -> non ha scritto niente, nemmeno le righe nuove",
          valore(conf, "SELECT title FROM games WHERE id=(SELECT MIN(id) FROM games)")
          == "TITOLO CAMBIATO A MANO")

    rc, out = gira(conf, "--sovrascrivi")
    atteso = min(export["games"], key=lambda g: g["id"])["title"]
    esito("--sovrascrivi -> le righe tornano quelle dell'export",
          rc == 0
          and valore(conf, "SELECT title FROM games WHERE id=(SELECT MIN(id) FROM games)") == atteso
          and valore(conf, "SELECT display_name FROM users WHERE id=1") == "Admin")
    esito("--sovrascrivi -> LA PASSWORD NON È STATA TOCCATA",
          valore(conf, "SELECT password FROM users WHERE id=1") == pw_prima)

    # --- 4. python_topics riordinato + spunte da importare -------------------
    topics = os.path.join(dove, "topics.db")
    shutil.copy2(base, topics)
    esegui(topics, "UPDATE python_topics SET name='ARGOMENTO DIVERSO' WHERE id=7")
    con_spunte = os.path.join(dove, "export_con_spunte.json")
    falso = dict(export, python_progress=[{"user_id": 1, "topic_id": 7, "done": 1}])
    with open(con_spunte, "w", encoding="utf-8") as f:
        json.dump(falso, f, ensure_ascii=False)
    rc, out = gira(topics, file=con_spunte)
    esito("argomenti riordinati + spunte da importare -> si ferma",
          rc == 1 and "INTERROTTO" in out and "id 7" in out)
    esito("argomenti riordinati -> nessuna spunta è finita sull'argomento sbagliato",
          conta(topics, "python_progress") == 0)

    # Senza spunte la rete lascia passare — ma un argomento rinominato **è** un
    # conflitto, quindi si ferma comunque, un passo dopo. Sono due reti distinte.
    senza = os.path.join(dove, "topics_senza.db")
    shutil.copy2(base, senza)
    esegui(senza, "UPDATE python_topics SET name='ARGOMENTO DIVERSO' WHERE id=7",
           "DELETE FROM games")
    rc, out = gira(senza)
    esito("argomenti riordinati senza spunte -> passa la rete, si ferma al conflitto",
          rc == 1 and "Nessuna spunta da importare" in out)
    rc, out = gira(senza, "--sovrascrivi")
    esito("argomenti riordinati senza spunte + --sovrascrivi -> riallinea e scrive",
          rc == 0 and valore(senza, "SELECT name FROM python_topics WHERE id=7")
          != "ARGOMENTO DIVERSO" and conta(senza, "games") == len(export["games"]))

    # --- 5. stesso username con id diverso ----------------------------------
    utenti = os.path.join(dove, "username.db")
    shutil.copy2(base, utenti)
    altro = export["users"][1]["username"]
    esegui(utenti, "DELETE FROM python_progress",
           "UPDATE games SET user_id=NULL", "UPDATE teams SET user_id=NULL",
           "UPDATE pc_builds SET user_id=NULL", "DELETE FROM users WHERE id=2")
    c = sqlite3.connect(utenti)
    c.execute("INSERT INTO users(id, username, password, display_name, role) "
              "VALUES(99, ?, 'x', 'Altro', 'user')", (altro,))
    c.commit(); c.close()
    rc, out = gira(utenti)
    esito("stesso username con id diverso -> si ferma e li nomina entrambi",
          rc == 1 and "UNIQUE" in out and altro in out and "99 nel DB" in out)

    # --- 6. un export CON le password (il `--completo` di §1.4, che ancora non c'è) --
    # ⚠️ Prova a futuro: la colonna `password` nell'export non deve finire due volte
    # nella stessa INSERT, e quella di un utente **già presente** non va toccata
    # nemmeno se l'export ne porta una.
    completo = os.path.join(dove, "export_completo.json")
    utenti_pw = [dict(u, password="hash-finto-dell-export") for u in export["users"]]
    with open(completo, "w", encoding="utf-8") as f:
        json.dump(dict(export, users=utenti_pw), f, ensure_ascii=False)
    conpw = db_vergine(dove, "con_password.db")
    pw_admin = valore(conpw, "SELECT password FROM users WHERE id=1")
    rc, out = gira(conpw, file=completo)
    esito("export con le password -> l'utente nuovo entra con la sua",
          rc == 0 and valore(conpw, "SELECT password FROM users WHERE id=2")
          == "hash-finto-dell-export")
    esito("export con le password -> quella dell'admin già presente non si tocca",
          valore(conpw, "SELECT password FROM users WHERE id=1") == pw_admin)

    # --- 7. DB più vecchio dell'export --------------------------------------
    vecchio = os.path.join(dove, "vecchio.db")
    shutil.copy2(base, vecchio)
    c = sqlite3.connect(vecchio)
    try:
        c.execute("ALTER TABLE games DROP COLUMN steam_tags")
        c.commit(); c.close()
    except sqlite3.OperationalError as e:
        c.close()
        esito("DB più vecchio dell'export -> si ferma", False,
              f"DROP COLUMN non supportato da questo SQLite: {e}")
    else:
        rc, out = gira(vecchio)
        esito("DB più vecchio dell'export -> si ferma e dice cosa fare",
              rc == 1 and "steam_tags" in out and "init_db()" in out)

    # --- 8. quando non si sa riconoscere «la stessa riga» -------------------
    # ⚠️ La rete messa il 22/09/2026 **dopo** aver pagato il caso opposto: la chiave
    # veniva da un dizionario scritto a mano, `fanta_formazione` non c'era, e lo
    # script moriva con un `KeyError: 'id'` che non diceva né quale tabella né cosa
    # fare. Ora la chiave si chiede allo schema — e quando lo schema non la dà, o
    # l'export non la porta, ci si **ferma nominando la tabella** invece di
    # rifarne le righe doppie a ogni riesecuzione.
    senza_pk = os.path.join(dove, "senza_pk.db")
    shutil.copy2(db_vergine(dove, "per_pk.db"), senza_pk)
    esegui(senza_pk,
           "DROP TABLE fanta_formazione",
           "CREATE TABLE fanta_formazione(league_id INTEGER, player_id INTEGER,"
           " titolare INTEGER NOT NULL, ordine INTEGER NOT NULL, ruolo TEXT)")
    rc, out = gira(senza_pk)
    esito("tabella senza chiave primaria -> si ferma e la nomina",
          rc == 1 and "fanta_formazione" in out and "chiave primaria" in out)
    esito("   e non ha scritto niente, nemmeno le tabelle sane",
          conta(senza_pk, "games") == 0, f"games={conta(senza_pk, 'games')}")

    # L'altra metà: lo schema la chiave ce l'ha, ma l'export non la porta. Succede
    # il giorno che `esporta_dati.py` esclude una colonna di troppo — e allora una
    # riga dell'export non è più indirizzabile, che è la stessa cosa.
    monco = os.path.join(dove, "export_monco.json")
    dati = json.load(io_json(EXPORT))
    dati["fanta_formazione"] = [{k: v for k, v in r.items() if k != "league_id"}
                                for r in (dati.get("fanta_formazione") or [])]
    with open(monco, "w", encoding="utf-8") as f:
        json.dump(dati, f)
    pulito = db_vergine(dove, "per_export_monco.db")
    rc, out = gira(pulito, file=monco)
    esito("chiave che l'export non porta -> si ferma e dice quale colonna manca",
          rc == 1 and "fanta_formazione" in out and "league_id" in out)
    esito("   e anche qui non ha scritto niente",
          conta(pulito, "games") == 0, f"games={conta(pulito, 'games')}")


def io_json(percorso):
    import io as _io
    return _io.open(percorso, encoding="utf-8")


def app_regge(percorso_db):
    """Il DB ripristinato non è solo pieno: l'app ci lavora sopra.

    Un ripristino che riempie le tabelle ma lascia la pagina in errore non è un
    ripristino — ed è il genere di cosa che i conteggi non vedono.
    """
    import extensions
    vecchio = extensions.DB
    extensions.DB = percorso_db
    try:
        import app as modulo_app
        modulo_app.app.config["TESTING"] = True
        with modulo_app.app.test_client() as client:
            with client.session_transaction() as s:
                s["username"] = "admin"
                s["role"] = "admin"
            # ⚠️ La barra finale ci vuole: senza, Flask risponde **308** e non 200.
            # I prefissi sono quelli dei Blueprint — il PC Builder è `/pcbuilder`,
            # non `/pc`, e un URL inventato darebbe un 404 che somiglia a un guasto.
            pagine = {"/": None, "/gaming/": None, "/pokemon/": None,
                      "/pcbuilder/": None, "/python/": None, "/arduino/": None}
            for via in list(pagine):
                pagine[via] = client.get(via).status_code
            titolo = json.load(io_json(EXPORT))["games"][0]["title"]
            corpo = client.get("/gaming/").get_data(as_text=True)
        rotte = [v for v, s in pagine.items() if s != 200]
        return (not rotte and titolo.split()[0] in corpo,
                f"{len(pagine)} pagine a 200" if not rotte else f"in errore: {rotte}")
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    finally:
        extensions.DB = vecchio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tieni", action="store_true",
                    help="non cancella la cartella temporanea (per guardarci dentro)")
    args = ap.parse_args()

    if not os.path.exists(EXPORT):
        print(f"Export non trovato: {EXPORT}")
        return 1

    dove = tempfile.mkdtemp(prefix="prova_importa_")
    print(f"Prove in {dove}\n")
    try:
        prove(dove)
    finally:
        if args.tieni:
            print(f"\n(--tieni: la cartella resta in {dove})")
        else:
            shutil.rmtree(dove, ignore_errors=True)

    print()
    falliti = [n for n, ok in esiti if not ok]
    print(f"{len(esiti) - len(falliti)} prove su {len(esiti)}." +
          (f"  FALLITE: {falliti}" if falliti else "  Tutte passate."))
    return 1 if falliti else 0


if __name__ == "__main__":
    sys.exit(main())
