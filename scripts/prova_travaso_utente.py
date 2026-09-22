#!/usr/bin/env python
"""Le prove di cosa succede ai dati di un utente. Non tocca `hub.db`.

    python scripts/prova_travaso_utente.py [--tieni]

Due operazioni, una macchina sola (`TABELLE_UTENTE` e `FIGLIE_DI` in
`extensions.py`): il **travaso** quando un utente viene eliminato — le righe cambiano
mano — e la **copia** su un altro utente, dove invece vanno duplicate. È la
differenza che le rende due lavori e non uno: nel travaso le figlie seguono il padre
da sole, perché il padre resta quello; nella copia il padre nuovo ha un id nuovo, e
ogni figlia va riscritta con quello.

Gira su un DB **suo**, creato da `init_db()` in una cartella temporanea, e guida le
route vere (`POST /admin/utenti/<id>/elimina` e `.../copia`) dal test client: un
ciclo ricopiato qui dentro proverebbe la copia, non il codice che gira davvero — ed è
esattamente il modo in cui il baco del travaso si era nascosto.

Cosa dimostra, tutto misurato il 22/09/2026:

- che i **contenuti passano all'amministratore** e non si perdono: giochi, team,
  progetti Arduino, build del PC **e leghe del Fantacalcio**. Fino a oggi le leghe
  non passavano — `fanta_leagues` non ha una chiave esterna verso `users`, quindi
  l'utente spariva e la sua lega restava intestata a un id che non esiste più,
  invisibile a tutti, **con rosa e formazione appese**
- che la **rosa e la formazione seguono la lega** senza che nessuno le tocchi: sono
  figlie di `fanta_leagues`, il proprietario lo ereditano dal padre
- che la cancellazione **riesce anche con le spunte di Python addosso**. Prima no:
  `python_progress.user_id` ha una chiave esterna verso `users(id)`, quindi la
  `DELETE` falliva con `FOREIGN KEY constraint failed` — 500, e la connessione
  nemmeno chiusa. Un utente che avesse spuntato **un** argomento non era
  eliminabile, e la pagina non diceva perché
- che quelle spunte si **cancellano** invece di essere intestate all'admin, e che
  quante erano **si legge a schermo**: sono lo stato personale di chi se ne va, e
  regalarle a un altro vorrebbe dire scrivere che ha fatto cose che non ha fatto
- che le righe **di chi resta non si muovono**: il travaso è dell'utente eliminato
  e di nessun altro
- che davanti a una **tabella con un proprietario e senza regola** la route si
  **rifiuta** e la nomina, invece di cancellare l'utente e lasciarne indietro i
  dati. È la rete che tiene `TABELLE_UTENTE` attaccata allo schema vero: una
  settima tabella con un `user_id` si fa trovare qui, non un anno dopo

E sulla **copia** (§4.3):

- che duplica davvero, e che le **figlie arrivano appese al padre nuovo**: non basta
  che esistano — si guarda l'id. Una figlia dimenticata non darebbe nessun errore,
  farebbe nascere il padre **vuoto**, e un team senza i suoi Pokémon somiglia a un
  team finché non lo apri
- che il **sorgente non perde niente**: copiare non è spostare
- che le spunte di Python **non** si copiano e che il messaggio lo **dice**
- che premuto due volte **lascia tutto in doppio**, e che l'avviso c'era prima. Non è
  un difetto tollerato di nascosto, è la decisione di Davide («aggiunge, non
  sostituisce») e si prova apposta, così nessuno la cambia credendo di correggere un
  baco. Renderla rieseguibile vorrebbe dire riconoscere «questa riga c'è già» dai
  **contenuti**, cioè fondere per titolo: la scorciatoia che `importa_dati.py`
  rifiuta per iscritto
- che una **figlia non dichiarata** in `FIGLIE_DI` ferma la copia e viene nominata,
  riconosciuta dalla sua **chiave esterna vera** e non da un elenco a mano
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


def _semina(db, uid, etichetta):
    """Una riga per ogni tabella con un proprietario, **e tutte le sue figlie**.

    Le figlie non sono decorazione: sono la differenza fra il travaso e la copia. Nel
    travaso seguono il padre da sole (il padre resta quello); nella copia il padre
    nuovo ha un id nuovo, e una figlia dimenticata farebbe nascere un team **senza i
    suoi Pokémon** — senza nessun errore.
    """
    db.execute("INSERT INTO games(title,user_id) VALUES(?,?)", (f"Gioco {etichetta}", uid))
    db.execute("INSERT INTO teams(name,user_id) VALUES(?,?)", (f"Team {etichetta}", uid))
    tid = db.execute("SELECT id FROM teams WHERE user_id=? ORDER BY id DESC LIMIT 1",
                     (uid,)).fetchone()["id"]
    for slot, nome in ((1, "Incineroar"), (2, "Amoonguss")):
        db.execute("INSERT INTO team_members(team_id,slot,pokemon) VALUES(?,?,?)",
                   (tid, slot, nome))
    db.execute("INSERT INTO arduino_projects(name,user_id) VALUES(?,?)",
               (f"Arduino {etichetta}", uid))
    db.execute("INSERT INTO pc_builds(name,user_id) VALUES(?,?)", (f"PC {etichetta}", uid))
    bid = db.execute("SELECT id FROM pc_builds WHERE user_id=? ORDER BY id DESC LIMIT 1",
                     (uid,)).fetchone()["id"]
    for categoria, nome in (("cpu", "Ryzen"), ("gpu", "Radeon"), ("ram", "32 GB")):
        db.execute("INSERT INTO pc_components(build_id,category,name) VALUES(?,?,?)",
                   (bid, categoria, nome))
    db.execute("INSERT INTO fanta_leagues(user_id,nome) VALUES(?,?)",
               (uid, f"Lega {etichetta}"))
    lid = db.execute("SELECT id FROM fanta_leagues WHERE user_id=? ORDER BY id DESC LIMIT 1",
                     (uid,)).fetchone()["id"]
    # La rosa e la formazione non hanno un `user_id`: il proprietario lo ereditano
    # dalla lega. Servono qui proprio per vedere se la seguono.
    for pid in (1001, 1002, 1003):
        db.execute("INSERT OR IGNORE INTO fanta_players(id,nome,squadra) VALUES(?,?,?)",
                   (pid, f"Giocatore {pid}", "Prova"))
        db.execute("INSERT INTO fanta_roster(league_id,player_id,prezzo) VALUES(?,?,?)",
                   (lid, pid, 10))
        db.execute("INSERT INTO fanta_formazione(league_id,player_id,titolare,ordine,ruolo)"
                   " VALUES(?,?,1,?,'P')", (lid, pid, pid))
    for topic, in db.execute("SELECT id FROM python_topics ORDER BY id LIMIT 5"):
        db.execute("INSERT INTO python_progress(user_id,topic_id,done) VALUES(?,?,1)",
                   (uid, topic))
    return {"lega": lid, "team": tid, "build": bid}


def _quante(db, tabella, uid):
    return db.execute(f"SELECT COUNT(*) FROM {tabella} WHERE user_id=?", (uid,)).fetchone()[0]


def prove(dove):
    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()

    db = extensions.get_db()
    for nome, ruolo in (("capo", "admin"), ("cavia", "user"), ("terzo", "user"),
                        ("nuovo", "user")):
        db.execute("INSERT INTO users(username,password,display_name,role) VALUES(?,?,?,?)",
                   (nome, "x", nome.capitalize(), ruolo))
    ids = {r["username"]: r["id"] for r in db.execute("SELECT id, username FROM users")}
    semi = _semina(db, ids["cavia"], "della cavia")
    lid = semi["lega"]
    _semina(db, ids["terzo"], "del terzo")
    db.commit()
    db.close()

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    def da_capo(c):
        with c.session_transaction() as s:
            s["username"] = "capo"
            s["role"] = "admin"
            s["user_id"] = ids["capo"]

    print("\n== 0. l'elenco delle tabelle con un proprietario è quello dello schema ==")
    db = extensions.get_db()
    trovate = extensions.tabelle_con_user_id(db)
    esito("lo schema ha sei tabelle con un `user_id`", len(trovate) == 6,
          ", ".join(trovate))
    esito("e `TABELLE_UTENTE` le copre tutte",
          extensions.tabelle_senza_regola(db) == [],
          f"senza regola: {extensions.tabelle_senza_regola(db)}")
    db.close()

    print("\n== 1. l'utente si elimina anche con le spunte di Python addosso ==")
    with app.test_client() as c:
        da_capo(c)
        r = c.post(f"/admin/utenti/{ids['cavia']}/elimina", follow_redirects=True)
        esito("la route risponde 200 invece di rompersi", r.status_code == 200,
              f"status={r.status_code}")
        testo = r.data.decode("utf-8", "replace")
        esito("e non dice che la chiave esterna ha bloccato tutto",
              "FOREIGN KEY" not in testo)
        db = extensions.get_db()
        esito("l'utente non c'è più",
              db.execute("SELECT COUNT(*) FROM users WHERE id=?",
                         (ids["cavia"],)).fetchone()[0] == 0)

        print("\n== 2. i contenuti sono passati all'amministratore ==")
        for tabella in ("games", "teams", "arduino_projects", "pc_builds", "fanta_leagues"):
            esito(f"{tabella}: niente è rimasto intestato a chi non esiste più",
                  _quante(db, tabella, ids["cavia"]) == 0,
                  f"orfane={_quante(db, tabella, ids['cavia'])}")
        esito("la lega del Fantacalcio è dell'amministratore",
              db.execute("SELECT user_id FROM fanta_leagues WHERE id=?",
                         (lid,)).fetchone()["user_id"] == ids["capo"])
        esito("e si è portata dietro la rosa",
              db.execute("SELECT COUNT(*) FROM fanta_roster WHERE league_id=?",
                         (lid,)).fetchone()[0] == 3)
        esito("e la formazione schierata",
              db.execute("SELECT COUNT(*) FROM fanta_formazione WHERE league_id=?",
                         (lid,)).fetchone()[0] == 3)
        esito("il messaggio a schermo dice quante righe sono passate",
              "5 righe di contenuto sono passate a te" in testo)

        print("\n== 3. le spunte di Python si cancellano, e lo dice ==")
        esito("le cinque spunte non ci sono più",
              _quante(db, "python_progress", ids["cavia"]) == 0)
        esito("non sono state regalate all'amministratore",
              _quante(db, "python_progress", ids["capo"]) == 0)
        esito("e quante erano si legge a schermo",
              "5 in python_progress" in testo,
              testo[testo.find("Righe cancellate"):][:90] if "Righe cancellate" in testo
              else "la frase non c'è")

        print("\n== 4. le righe di chi resta non si sono mosse ==")
        for tabella in ("games", "teams", "arduino_projects", "pc_builds",
                        "fanta_leagues"):
            esito(f"{tabella}: il terzo utente ha ancora la sua riga",
                  _quante(db, tabella, ids["terzo"]) == 1,
                  f"righe={_quante(db, tabella, ids['terzo'])}")
        esito("e le sue cinque spunte di Python",
              _quante(db, "python_progress", ids["terzo"]) == 5)
        db.close()

    print("\n== 5. la copia duplica, e i figli arrivano col padre nuovo ==")
    db = extensions.get_db()
    team_di_terzo = db.execute("SELECT id FROM teams WHERE user_id=?",
                               (ids["terzo"],)).fetchone()["id"]
    db.close()
    with app.test_client() as c:
        da_capo(c)
        r = c.post(f"/admin/utenti/{ids['terzo']}/copia",
                   data={"da": str(ids["nuovo"])}, follow_redirects=True)
        testo = r.data.decode("utf-8", "replace")
        esito("la route risponde", r.status_code == 200, f"status={r.status_code}")
        db = extensions.get_db()
        for tabella in ("games", "teams", "arduino_projects", "pc_builds",
                        "fanta_leagues"):
            esito(f"{tabella}: il destinatario ha la sua copia",
                  _quante(db, tabella, ids["nuovo"]) == 1,
                  f"righe={_quante(db, tabella, ids['nuovo'])}")
        # ⚠️ Il cuore della prova. Una figlia dimenticata non darebbe **nessun**
        # errore: il team nuovo nascerebbe e basta, vuoto. Quindi non si guarda che
        # le figlie esistano, si guarda che siano appese al padre **nuovo** e che
        # quelle del sorgente non si siano mosse.
        team_nuovo = db.execute("SELECT id FROM teams WHERE user_id=?",
                                (ids["nuovo"],)).fetchone()["id"]
        esito("il team copiato è una riga nuova, non quella di prima",
              team_nuovo != team_di_terzo, f"{team_di_terzo} → {team_nuovo}")
        esito("e i suoi due Pokémon sono appesi al team nuovo",
              db.execute("SELECT COUNT(*) FROM team_members WHERE team_id=?",
                         (team_nuovo,)).fetchone()[0] == 2)
        esito("mentre il team del sorgente ha ancora i suoi",
              db.execute("SELECT COUNT(*) FROM team_members WHERE team_id=?",
                         (team_di_terzo,)).fetchone()[0] == 2)
        build_nuova = db.execute("SELECT id FROM pc_builds WHERE user_id=?",
                                 (ids["nuovo"],)).fetchone()["id"]
        esito("i tre pezzi seguono la build nuova",
              db.execute("SELECT COUNT(*) FROM pc_components WHERE build_id=?",
                         (build_nuova,)).fetchone()[0] == 3)
        lega_nuova = db.execute("SELECT id FROM fanta_leagues WHERE user_id=?",
                                (ids["nuovo"],)).fetchone()["id"]
        esito("la rosa segue la lega nuova",
              db.execute("SELECT COUNT(*) FROM fanta_roster WHERE league_id=?",
                         (lega_nuova,)).fetchone()[0] == 3)
        esito("e la formazione schierata anche",
              db.execute("SELECT COUNT(*) FROM fanta_formazione WHERE league_id=?",
                         (lega_nuova,)).fetchone()[0] == 3)
        esito("il sorgente non ha perso niente: copiare non è spostare",
              all(_quante(db, t, ids["terzo"]) == 1 for t in
                  ("games", "teams", "arduino_projects", "pc_builds", "fanta_leagues")))

        print("\n== 6. le spunte di Python non si copiano, e lo dice ==")
        esito("il destinatario non ha spunte",
              _quante(db, "python_progress", ids["nuovo"]) == 0)
        esito("il sorgente le ha ancora tutte e cinque",
              _quante(db, "python_progress", ids["terzo"]) == 5)
        esito("e il messaggio dichiara di averle lasciate fuori",
              "spunte di Python non sono state copiate" in testo)
        esito("il messaggio dice cosa ha copiato, in italiano",
              "giochi" in testo and "leghe del Fantacalcio" in testo)
        db.close()

        print("\n== 7. premuto due volte lascia tutto in doppio — ed è dichiarato ==")
        # ⚠️ Non è un difetto tollerato di nascosto: è la decisione di Davide del
        # 22/09/2026 («aggiunge, non sostituisce»), e si prova **apposta**, così
        # nessuno la cambia per sbaglio credendo di correggere un baco. Renderla
        # rieseguibile vorrebbe dire riconoscere «questa riga c'è già» dai
        # **contenuti**, cioè fondere per titolo — la scorciatoia che
        # `importa_dati.py` rifiuta per iscritto.
        esito("l'avviso c'era prima di premere di nuovo",
              "le rifarebbe in doppio" in testo)
        r = c.post(f"/admin/utenti/{ids['terzo']}/copia",
                   data={"da": str(ids["nuovo"])}, follow_redirects=True)
        db = extensions.get_db()
        esito("e infatti ora ce ne sono due per tabella",
              all(_quante(db, t, ids["nuovo"]) == 2 for t in
                  ("games", "teams", "arduino_projects", "pc_builds", "fanta_leagues")),
              " ".join(f"{t}={_quante(db, t, ids['nuovo'])}" for t in
                       ("games", "teams", "pc_builds", "fanta_leagues")))
        db.close()

        r = c.post(f"/admin/utenti/{ids['terzo']}/copia",
                   data={"da": str(ids["terzo"])}, follow_redirects=True)
        testo = r.data.decode("utf-8", "replace")
        esito("copiare un utente in se stesso viene rifiutato",
              "stesso utente" in testo)

    print("\n== 8. una tabella con un proprietario e senza regola ferma tutto ==")
    db = extensions.get_db()
    db.execute("CREATE TABLE stampa_3d(id INTEGER PRIMARY KEY, "
               "user_id INTEGER REFERENCES users(id), nome TEXT)")
    db.execute("INSERT INTO stampa_3d(user_id,nome) VALUES(?,'Pezzo del terzo')",
               (ids["terzo"],))
    db.commit()
    esito("`tabelle_senza_regola()` la nomina",
          extensions.tabelle_senza_regola(db) == ["stampa_3d"],
          str(extensions.tabelle_senza_regola(db)))
    db.close()
    with app.test_client() as c:
        da_capo(c)
        r = c.post(f"/admin/utenti/{ids['terzo']}/elimina", follow_redirects=True)
        testo = r.data.decode("utf-8", "replace")
        esito("la route si rifiuta e la nomina", "stampa_3d" in testo)
        db = extensions.get_db()
        esito("l'utente è ancora lì",
              db.execute("SELECT COUNT(*) FROM users WHERE id=?",
                         (ids["terzo"],)).fetchone()[0] == 1)
        esito("e i suoi contenuti non si sono mossi di un millimetro",
              _quante(db, "games", ids["terzo"]) == 1
              and _quante(db, "fanta_leagues", ids["terzo"]) == 1
              and _quante(db, "python_progress", ids["terzo"]) == 5)
        db.close()
        r = c.post(f"/admin/utenti/{ids['terzo']}/copia",
                   data={"da": str(ids["nuovo"])}, follow_redirects=True)
        esito("e anche la copia si ferma sulla stessa tabella",
              "stampa_3d" in r.data.decode("utf-8", "replace"))

    print("\n== 9. una figlia non dichiarata ferma la copia ==")
    # ⚠️ È l'altra metà della rete, e la più insidiosa delle due: una figlia
    # dimenticata non darebbe **nessun** errore. Il padre nuovo nascerebbe e basta,
    # vuoto — un team senza i suoi Pokémon somiglia a un team, e ci si accorge del
    # buco il giorno che lo si apre. Qui la tabella si riconosce dalla **chiave
    # esterna vera**, non da un elenco a mano.
    db = extensions.get_db()
    db.execute("DROP TABLE stampa_3d")          # così resta in campo una causa sola
    db.execute("CREATE TABLE team_note(id INTEGER PRIMARY KEY, "
               "team_id INTEGER REFERENCES teams(id), testo TEXT)")
    db.commit()
    fuori = extensions.figlie_senza_regola(db)
    esito("`figlie_senza_regola()` la trova dalla chiave esterna",
          fuori == [("team_note", "teams")], str(fuori))
    quanti_prima = _quante(db, "games", ids["nuovo"])
    db.close()
    with app.test_client() as c:
        da_capo(c)
        r = c.post(f"/admin/utenti/{ids['terzo']}/copia",
                   data={"da": str(ids["nuovo"])}, follow_redirects=True)
        testo = r.data.decode("utf-8", "replace")
        esito("la copia si rifiuta e nomina la figlia e il suo padre",
              "team_note" in testo and "teams" in testo)
        db = extensions.get_db()
        esito("   e non ha copiato niente",
              _quante(db, "games", ids["nuovo"]) == quanti_prima,
              f"games={_quante(db, 'games', ids['nuovo'])} (erano {quanti_prima})")
        db.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true",
                    help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_travaso_")
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
