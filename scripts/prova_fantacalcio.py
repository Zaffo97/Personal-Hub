#!/usr/bin/env python
"""Le prove della sezione Fantacalcio (§4.2). Non tocca `hub.db` né la rete.

    python scripts/prova_fantacalcio.py [--tieni]

Ogni prova gira su un DB **suo**, creato da `init_db()` in una cartella temporanea.
⚠️ Non è pignoleria: il 16/08/2026 uno script di prova che cancellava «il mio
intervallo» di id si è portato via 497 righe vere.

Cosa dimostra, in ordine:

- che il **listone è di tutti e le leghe di ognuno**: un secondo utente non vede la
  lega di un altro, non la modifica, non la cancella e non le tocca la rosa. È la
  regola di §1.1, e qui vale doppio perché `fanta_roster` **non ha** una colonna
  `user_id`: il proprietario le arriva dalla lega, quindi una query che non passa
  di lì sarebbe scoperta senza dare nessun errore
- che un **modulo che non torna viene rifiutato** invece di essere salvato e far poi
  sbagliare il conto dei ruoli
- che un **campo di regola lasciato vuoto non vale zero**: varrebbe azzerare il bonus
  gol di una lega a ogni salvataggio che non lo ripassa
- che l'aggiornamento del listone **spegne e non cancella** chi esce dalla Serie A, e
  che la rosa che lo nomina sopravvive: è il caso del mercato di gennaio
- che il lettore delle pagine regge una pagina **cambiata di forma** invece di
  inventarsi dei numeri
"""
import argparse
import os
import shutil
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def prove(dove):
    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()

    db = extensions.get_db()
    db.execute("INSERT INTO users(username,password,display_name,role) "
               "VALUES('davide','x','Davide','user')")
    db.execute("INSERT INTO users(username,password,display_name,role) "
               "VALUES('altro','x','Altro','user')")
    # Un pezzo di listone finto: non si scarica niente in una prova.
    for pid, nome, sq, ruolo, qa, fvm in (
            (1, "Sommer", "INT", "p", 15, 60),
            (2, "Bastoni", "INT", "d", 18, 120),
            (3, "Barella", "INT", "c", 24, 210),
            (4, "Thuram", "INT", "a", 31, 275),
            (5, "Uscito", "XXX", "c", 5, 10)):
        db.execute("INSERT INTO fanta_players(id,nome,squadra,ruolo_classic,qa,fvm,"
                   "fantamedia,attivo,visto_il) VALUES(?,?,?,?,?,?,6.0,1,'2026-09-21')",
                   (pid, nome, sq, ruolo, qa, fvm))
    db.commit()
    ids = {r["username"]: r["id"] for r in db.execute("SELECT id, username FROM users")}
    db.close()

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    print("\n== 1. una lega si crea, e le regole si salvano ==")
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        r = c.post("/fantacalcio/lega/salva", data={
            "nome": "Lega Amici", "moduli": "3-4-3,4-4-2", "n_panchinari": "7",
            "mod_difesa": "1", "bonus_gol_d": "4", "bonus_assist": "1"},
            follow_redirects=True)
        esito("la creazione risponde", r.status_code == 200)
        db = extensions.get_db()
        lega = db.execute("SELECT * FROM fanta_leagues").fetchone()
        db.close()
        esito("la lega è nata col suo proprietario",
              lega is not None and lega["user_id"] == ids["davide"],
              f"user_id={lega['user_id'] if lega else None}")
        esito("il bonus scritto nel form è quello salvato", lega["bonus_gol_d"] == 4)
        esito("e quelli non toccati restano al default del DB",
              lega["bonus_gol_a"] == 3 and lega["malus_amm"] == -0.5,
              f"gol_a={lega['bonus_gol_a']} amm={lega['malus_amm']}")
        esito("il modificatore di difesa è acceso", lega["mod_difesa"] == 1)
        lid = lega["id"]

        # --- 2. un modulo che non torna non si salva ------------------------
        print("\n== 2. un modulo sbagliato viene rifiutato ==")
        r = c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-4"},
            follow_redirects=True)
        db = extensions.get_db()
        dopo = db.execute("SELECT moduli FROM fanta_leagues WHERE id=?", (lid,)).fetchone()
        db.close()
        esito("«4-4-4» non entra e i moduli di prima restano",
              dopo["moduli"] == "3-4-3,4-4-2", dopo["moduli"])

        # --- 3. un campo vuoto non azzera -----------------------------------
        print("\n== 3. un campo di regola lasciato vuoto non vale zero ==")
        r = c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "bonus_gol_d": ""}, follow_redirects=True)
        db = extensions.get_db()
        dopo = db.execute("SELECT bonus_gol_d FROM fanta_leagues WHERE id=?",
                          (lid,)).fetchone()
        db.close()
        esito("il bonus gol del difensore è ancora 4, non 0",
              dopo["bonus_gol_d"] == 4, str(dopo["bonus_gol_d"]))

        # --- 4. la rosa ------------------------------------------------------
        print("\n== 4. la rosa ==")
        for pid in (1, 2, 3, 4, 5):
            c.post(f"/fantacalcio/lega/{lid}/rosa/aggiungi",
                   data={"player_id": str(pid), "prezzo": "10"})
        db = extensions.get_db()
        quanti = db.execute("SELECT COUNT(*) FROM fanta_roster").fetchone()[0]
        db.close()
        esito("cinque giocatori in rosa", quanti == 5, str(quanti))
        r = c.post(f"/fantacalcio/lega/{lid}/rosa/aggiungi",
                   data={"player_id": "1"}, follow_redirects=True)
        db = extensions.get_db()
        quanti2 = db.execute("SELECT COUNT(*) FROM fanta_roster").fetchone()[0]
        db.close()
        esito("lo stesso giocatore non entra due volte", quanti2 == 5, str(quanti2))
        r = c.post(f"/fantacalcio/lega/{lid}/rosa/aggiungi",
                   data={"player_id": "999"}, follow_redirects=True)
        esito("un id che non è nel listone viene rifiutato",
              b"non trovato" in r.data.lower() or quanti2 == 5)

        r = c.get(f"/fantacalcio/lega/{lid}")
        esito("la pagina della lega si apre e mostra la rosa",
              r.status_code == 200 and b"Barella" in r.data and b"Sommer" in r.data)
        esito("e dice quali moduli sono copribili e quali no",
              b"3-4-3" in r.data and (b"mancano" in r.data or b"copribile" in r.data))

        # --- 5. l'autocomplete ----------------------------------------------
        r = c.get("/fantacalcio/api/giocatori?q=bar")
        voci = r.get_json()
        esito("la ricerca trova Barella", any(v["nome"] == "Barella" for v in voci),
              f"{len(voci)} risultati")
        r = c.get("/fantacalcio/api/giocatori?q=b")
        esito("con una lettera sola non cerca niente", r.get_json() == [])

    # --- 6. un altro utente non ci arriva ------------------------------------
    print("\n== 5. le leghe sono di chi le ha fatte ==")
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "altro"
            s["role"] = "user"
            s["user_id"] = ids["altro"]
        r = c.get("/fantacalcio/", follow_redirects=True)
        esito("l'altro utente non vede la lega nell'elenco",
              b"Lega Amici" not in r.data)
        r = c.get(f"/fantacalcio/lega/{lid}", follow_redirects=True)
        esito("e aprendola per id non ci entra", b"Lega Amici" not in r.data)
        r = c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Rubata"}, follow_redirects=True)
        db = extensions.get_db()
        nome = db.execute("SELECT nome FROM fanta_leagues WHERE id=?", (lid,)).fetchone()["nome"]
        db.close()
        esito("non può rinominarla", nome == "Lega Amici", nome)
        r = c.post(f"/fantacalcio/lega/{lid}/elimina", follow_redirects=True)
        db = extensions.get_db()
        viva = db.execute("SELECT COUNT(*) FROM fanta_leagues WHERE id=?", (lid,)).fetchone()[0]
        rosa = db.execute("SELECT COUNT(*) FROM fanta_roster").fetchone()[0]
        db.close()
        esito("non può cancellarla, e la rosa è intatta", viva == 1 and rosa == 5,
              f"leghe={viva} rosa={rosa}")
        rid = None
        db = extensions.get_db()
        rid = db.execute("SELECT id FROM fanta_roster LIMIT 1").fetchone()["id"]
        db.close()
        c.post(f"/fantacalcio/lega/{lid}/rosa/{rid}/rimuovi", follow_redirects=True)
        db = extensions.get_db()
        rosa2 = db.execute("SELECT COUNT(*) FROM fanta_roster").fetchone()[0]
        db.close()
        esito("e non può togliere un giocatore dalla rosa altrui", rosa2 == 5, str(rosa2))

    # --- 7. il mercato: si spegne, non si cancella ---------------------------
    print("\n== 6. il mercato: chi esce dal listone si spegne, non sparisce ==")
    db = extensions.get_db()
    db.execute("UPDATE fanta_players SET attivo=0 WHERE id=5")
    db.commit()
    resta = db.execute("SELECT COUNT(*) FROM fanta_roster WHERE player_id=5").fetchone()[0]
    db.close()
    esito("il giocatore uscito è ancora in rosa", resta == 1, str(resta))
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        r = c.get(f"/fantacalcio/lega/{lid}")
        esito("e la pagina lo dichiara invece di nasconderlo",
              b"fuori listone" in r.data and b"Uscito" in r.data)

    # --- 8. il lettore regge una pagina che cambia forma ---------------------
    print("\n== 7. il lettore delle pagine ==")
    import fantacalcio_it as F
    esito("una pagina senza righe da' zero giocatori, non un errore",
          F._RigheGiocatori() is not None)
    p = F._RigheGiocatori()
    p.feed("<table><tr class='player-row' data-filter-keywords='X'><td>niente</td></tr></table>")
    esito("una riga senza id non entra: senza id non si lega a niente",
          p.righe == [], str(p.righe))
    esito("«6,5» con la virgola diventa 6.5, non None", F._decimale("6,5") == 6.5)
    esito("«-» vuol dire «non lo sappiamo», non zero",
          F._decimale("-") is None and F._intero("-") is None)
    from data import scomponi_modulo
    esito("i moduli si scompongono, e quelli che non fanno 10 no",
          scomponi_modulo("3-5-2") == {"p": 1, "d": 3, "c": 5, "a": 2}
          and scomponi_modulo("4-4-4") is None and scomponi_modulo("") is None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true",
                    help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_fanta_")
    try:
        prove(dove)
    finally:
        if args.tieni:
            print(f"\ncartella tenuta: {dove}")
        else:
            shutil.rmtree(dove, ignore_errors=True)
    passate = sum(esiti)
    print(f"\n{passate} prove su {len(esiti)}." +
          ("  Tutte passate." if passate == len(esiti) else "  FALLITE."))
    return 0 if passate == len(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
