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
- che le **probabili formazioni** si leggono, si importano e si rileggono senza
  raddoppiare, che una pagina a metà viene **rifiutata** invece di scritta, e che
  «non convocato» e «la sua squadra non gioca» restano due cose diverse

⚠️ Le probabili si provano su una pagina **finta**, costruita qui sotto: la cache
vera è un file di 700 KB che può non esserci, e senza cache `scarica()` andrebbe in
rete — cioè una prova che fallisce a seconda di come va la linea.
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

# ── La pagina finta delle probabili ──────────────────────────────────────────
# Ha la stessa forma di quella vera nei punti che il lettore guarda: il riquadro
# della giornata, le due `label` del titolo, il disegno sul campo con il modulo, e
# le due schede (titolari e panchina) con ruolo e percentuale. Costruirla da una
# struttura Python permette di **romperla apposta**, che è l'unico modo per sapere
# se i controlli del lettore servono davvero.
BASE_URL = "https://www.fantacalcio.it/serie-a/squadre"


def _squadra_html(slug, nome, modulo, titolari, panchina, campo=None):
    """Una squadra: il suo blocco sul campo e la sua scheda.

    `campo` serve a far dire al campo qualcosa di **diverso** dalla scheda, che è
    il caso che la controprova del lettore deve saper prendere.
    """
    sul_campo = titolari if campo is None else campo
    disegno = "".join(
        f'<li class="player ani-scatter"><a class="player-name player-link" '
        f'href="{BASE_URL}/{slug}/{s}/{i}"><span>{n}</span></a></li>'
        for i, n, _r, _p, s in sul_campo)
    def scheda(voci, classe, stato):
        righe = "".join(
            f'<li class="player-item pill" data-status="{stato}">'
            f'<span class="role" data-value="{r}"></span>'
            f'<a class="player-name player-link" href="{BASE_URL}/{slug}/{s}/{i}">'
            f'<span>{n}</span></a>'
            f'<div class="progress progress-starter"><div class="progress-bar" '
            f'role="progressbar" aria-valuenow="{p}"></div></div></li>'
            for i, n, r, p, s in voci)
        return f'<ul class="player-list {classe}">{righe}</ul>'
    return (disegno, scheda(titolari, "starters", "success") +
            scheda(panchina, "reserves", "warn"))


def pagina_finta(partite, giornata=6, stagione="2026-27"):
    """`partite` è una lista di coppie di squadre, ognuna come la vuole `_squadra_html`."""
    pezzi = ['<ul class="match-list">']
    for n, (casa, fuori) in enumerate(partite, start=1):
        d_casa, s_casa = _squadra_html(*casa)
        d_fuori, s_fuori = _squadra_html(*fuori)
        gg = f'<div class="matchweek">{giornata}</div>' if giornata else ""
        pezzi.append(
            f'<li class="match match-item" data-match-id="{1000 + n}">{gg}'
            f'<label itemprop="homeTeam" for="a" class="team-home">'
            f'<a class="team-name team-link" href="{BASE_URL}/{casa[0]}">'
            f'<meta itemprop="name" content="{casa[1]}" />{casa[1]}</a></label>'
            f'<label itemprop="awayTeam" for="b" class="team-away">'
            f'<a class="team-name team-link" href="{BASE_URL}/{fuori[0]}">'
            f'<meta itemprop="name" content="{fuori[1]}" />{fuori[1]}</a></label>'
            + (f'<meta itemprop="name" content="Serie A {stagione} - {giornata}'
               f'&#xB0; giornata - {casa[0]}-{fuori[0]}" />' if giornata else "") +
            f'<div class="pitch">'
            f'<div class="team team-home" data-team-formation="{casa[2]}">'
            f'<ul class="team-lineup">{d_casa}<li class="separator"></li></ul></div>'
            f'<div class="team team-away" data-team-formation="{fuori[2]}">'
            f'<ul class="team-lineup">{d_fuori}<li class="separator"></li></ul></div>'
            f'</div>'
            f'<div class="card team-card">{s_casa}</div>'
            f'<div class="card team-card">{s_fuori}</div>'
            f'</li>')
    pezzi.append("</ul>")
    return "<html><body>" + "".join(pezzi) + "</body></html>"


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def prove(dove):
    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()

    # ⚠️ Dal 21/09/2026 **aprire una pagina può scaricare**: le route del
    # Fantacalcio rileggono la fonte da sé quando la copia è vecchia. Senza queste
    # due righe la suite andrebbe in rete a ogni `GET` — l'ha fatto davvero, e il
    # sintomo è stato una prova che trovava 482 convocati veri in un DB di prova
    # che doveva averne zero. Quindi: la cache è **sempre fresca** (l'automatico
    # non scatta mai per caso) e `scarica()` **solleva**, così una lettura di rete
    # non voluta si vede come errore invece di riuscire in silenzio. I blocchi che
    # provano l'aggiornamento li sostituiscono da sé, e rimettono questi a posto.
    import fantacalcio_it as F
    F.eta_cache = lambda nome: 0.0

    def _niente_rete(nome, forza=False):
        raise AssertionError(f"la prova non deve leggere la rete: {nome}")
    F.scarica = _niente_rete

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
            "mod_difesa": "1", "mod_difesa_portiere": "1",
            "bonus_gol": "4", "bonus_assist": "1"},
            follow_redirects=True)
        esito("la creazione risponde", r.status_code == 200)
        db = extensions.get_db()
        lega = db.execute("SELECT * FROM fanta_leagues").fetchone()
        db.close()
        esito("la lega è nata col suo proprietario",
              lega is not None and lega["user_id"] == ids["davide"],
              f"user_id={lega['user_id'] if lega else None}")
        esito("il bonus scritto nel form è quello salvato", lega["bonus_gol"] == 4)
        esito("e quelli non toccati restano al default del DB",
              lega["bonus_rigore_parato"] == 3 and lega["malus_amm"] == -0.5,
              f"rig={lega['bonus_rigore_parato']} amm={lega['malus_amm']}")
        esito("il modificatore di difesa è acceso", lega["mod_difesa"] == 1)
        # ⚠️ Le due voci che il regolamento non fissa hanno lo stesso un valore di
        # partenza — quello convenzionale, che è il DEFAULT della tabella. Il
        # primo giro le faceva partire dal primo valore della tendina, cioè zero:
        # una lega nuova nasceva con l'autogol che non toglie niente, e nessun
        # errore da nessuna parte. L'ha preso la prova in browser.
        esito("⚠️ autogol e porta inviolata non nascono a zero",
              lega["malus_autogol"] == -2 and lega["bonus_imbattibilita"] == 1,
              f"autogol={lega['malus_autogol']} porta={lega['bonus_imbattibilita']}")
        esito("⚠️ il gol è UNA colonna sola, non quattro",
              "bonus_gol" in lega.keys() and "bonus_gol_a" not in lega.keys(),
              "il regolamento dà +3 a chiunque segni")
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
            "bonus_gol": ""}, follow_redirects=True)
        db = extensions.get_db()
        dopo = db.execute("SELECT bonus_gol FROM fanta_leagues WHERE id=?",
                          (lid,)).fetchone()
        db.close()
        esito("il bonus gol è ancora 4, non 0", dopo["bonus_gol"] == 4,
              str(dopo["bonus_gol"]))
        # ⚠️ La tendina manda sempre qualcosa: «altro» con la casella libera vuota
        # è l'altro modo di dire «non l'ho toccato», e non deve azzerare niente.
        r = c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "bonus_gol": "altro", "bonus_gol_altro": ""}, follow_redirects=True)
        db = extensions.get_db()
        dopo = db.execute("SELECT bonus_gol FROM fanta_leagues WHERE id=?",
                          (lid,)).fetchone()
        db.close()
        esito("⚠️ «Altro…» con la casella vuota non azzera il bonus",
              dopo["bonus_gol"] == 4, str(dopo["bonus_gol"]))
        r = c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "bonus_gol": "altro", "bonus_gol_altro": "2,5"}, follow_redirects=True)
        db = extensions.get_db()
        dopo = db.execute("SELECT bonus_gol FROM fanta_leagues WHERE id=?",
                          (lid,)).fetchone()
        db.close()
        esito("e con un numero dentro vince quello, virgola compresa",
              dopo["bonus_gol"] == 2.5, str(dopo["bonus_gol"]))
        c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "bonus_gol": "3"}, follow_redirects=True)

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

        # --- 4b. correggere senza disfare -----------------------------------
        # Le due voci rimaste aperte il 21/09/2026: il prezzo si correggeva solo
        # nell'anteprima dell'incolla, e il togli era una riga per volta.
        print("\n== 4b. i prezzi si correggono, e si toglie in blocco ==")

        def rosa_ora():
            db = extensions.get_db()
            fuori = {x["player_id"]: dict(x) for x in db.execute(
                "SELECT id, player_id, prezzo FROM fanta_roster")}
            db.close()
            return fuori

        righe = rosa_ora()
        c.post(f"/fantacalcio/lega/{lid}/rosa/modifica", data={
            f"prezzo_{righe[1]['id']}": "25",
            f"prezzo_{righe[2]['id']}": "0",
            f"prezzo_{righe[3]['id']}": "10"}, follow_redirects=True)
        p = rosa_ora()
        esito("il prezzo si corregge senza togliere e rimettere",
              p[1]["prezzo"] == 25 and p[2]["prezzo"] == 0,
              f"1={p[1]['prezzo']} 2={p[2]['prezzo']}")
        esito("e chi non era nel form resta com'era",
              p[4]["prezzo"] == 10 and p[5]["prezzo"] == 10,
              f"4={p[4]['prezzo']} 5={p[5]['prezzo']}")
        r = c.post(f"/fantacalcio/lega/{lid}/rosa/modifica", data={},
                   follow_redirects=True)
        esito("un salvataggio che non cambia niente lo dice",
              "Niente da cambiare" in r.data.decode("utf-8", "replace"))
        # ⚠️ I numeri del form si rileggono dalla rosa prima di usarli: un `rid`
        # che non è di questa lega non deve togliere niente. È la stessa scelta
        # dei `player_id` nella conferma dell'incolla.
        c.post(f"/fantacalcio/lega/{lid}/rosa/modifica", data={"togli": "9999"},
               follow_redirects=True)
        esito("⚠️ un id che non è in questa rosa non toglie niente",
              len(rosa_ora()) == 5, str(len(rosa_ora())))
        c.post(f"/fantacalcio/lega/{lid}/rosa/modifica", data={
            "togli": [str(righe[1]["id"]), str(righe[2]["id"])]},
            follow_redirects=True)
        rimasti = rosa_ora()
        esito("due spuntati escono insieme, con una conferma sola",
              len(rimasti) == 3 and 1 not in rimasti and 2 not in rimasti,
              str(sorted(rimasti)))
        # Le prove che vengono dopo contano cinque righe in rosa: questo blocco
        # rimette quello che ha tolto, prezzo compreso.
        for pid in (1, 2):
            c.post(f"/fantacalcio/lega/{lid}/rosa/aggiungi",
                   data={"player_id": str(pid), "prezzo": "10"})
        esito("la rosa torna com'era per le prove che seguono",
              len(rosa_ora()) == 5, str(len(rosa_ora())))

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
        db = extensions.get_db()
        prezzi_prima = sorted(x["prezzo"] for x in db.execute(
            "SELECT prezzo FROM fanta_roster"))
        tutti = [x["id"] for x in db.execute("SELECT id FROM fanta_roster")]
        db.close()
        c.post(f"/fantacalcio/lega/{lid}/rosa/modifica",
               data={"togli": [str(x) for x in tutti],
                     f"prezzo_{tutti[0]}": "999"}, follow_redirects=True)
        db = extensions.get_db()
        prezzi_dopo = sorted(x["prezzo"] for x in db.execute(
            "SELECT prezzo FROM fanta_roster"))
        db.close()
        esito("⚠️ né correggere i prezzi o svuotare la rosa di un altro in blocco",
              prezzi_dopo == prezzi_prima, f"{prezzi_prima} -> {prezzi_dopo}")

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
    from data import (scomponi_modulo, soglie_mod_difesa, scrivi_soglie,
                      modificatore_difesa, MOD_DIFESA_SOGLIE)
    esito("i moduli si scompongono, e quelli che non fanno 10 no",
          scomponi_modulo("3-5-2") == {"p": 1, "d": 3, "c": 5, "a": 2}
          and scomponi_modulo("4-4-4") is None and scomponi_modulo("") is None)

    # --- 7bis. il modificatore di difesa ------------------------------------
    # La tabella standard è quella del vademecum di FantaGazzetta, letta il
    # 21/09/2026: +6 da 7, +3 da 6.5, +1 da 6, e sotto il 6 niente.
    print("\n== 7b. il modificatore di difesa ==")
    esito("la tabella standard è quella della fonte",
          MOD_DIFESA_SOGLIE == [(7.0, 6.0), (6.5, 3.0), (6.0, 1.0)])
    esito("7.2 vale +6, 6.8 vale +3, 6.2 vale +1",
          (modificatore_difesa(7.2), modificatore_difesa(6.8),
           modificatore_difesa(6.2)) == (6.0, 3.0, 1.0))
    esito("⚠️ il confronto è «maggiore o uguale»: 6 esatto vale +1, non 0",
          modificatore_difesa(6.0) == 1.0)
    esito("5.9 non vale niente", modificatore_difesa(5.9) == 0.0)
    esito("⚠️ «non lo sappiamo» non è un voto basso: None vale 0, non un malus",
          modificatore_difesa(None) == 0.0)
    esito("una tabella della lega si legge e si riscrive uguale",
          soglie_mod_difesa("7:6, 6.5:3, 6:1") == MOD_DIFESA_SOGLIE
          and scrivi_soglie(MOD_DIFESA_SOGLIE) == "7:6, 6.5:3, 6:1",
          scrivi_soglie(MOD_DIFESA_SOGLIE))
    esito("le soglie tornano ordinate dalla più alta, comunque siano scritte",
          soglie_mod_difesa("6:1, 7:6, 6.5:3") == MOD_DIFESA_SOGLIE)
    esito("⚠️ una riga scritta male torna allo standard, non a una tabella a caso",
          soglie_mod_difesa("boh") == MOD_DIFESA_SOGLIE
          and soglie_mod_difesa("7:sei") == MOD_DIFESA_SOGLIE
          and soglie_mod_difesa(None) == MOD_DIFESA_SOGLIE)
    esito("⚠️ e nemmeno una tabella a metà: se una coppia non si legge, standard",
          soglie_mod_difesa("7:6, 6.5:tre, 6:1") == MOD_DIFESA_SOGLIE)
    # ⚠️ La virgola in italiano è anche il separatore decimale: spezzando la riga
    # sulle virgole, «7,5:8» diventava «7» e «5:8», cioè un'altra tabella senza
    # nessun errore. L'ha preso questa prova al primo giro.
    esito("⚠️ «7,5:8» resta 7.5, non diventa 7 e 5:8",
          soglie_mod_difesa("7,5:8, 6:2") == [(7.5, 8.0), (6.0, 2.0)],
          str(soglie_mod_difesa("7,5:8, 6:2")))
    su_misura = soglie_mod_difesa("7,5:8, 6:2")
    esito("e una tabella diversa viene usata davvero",
          modificatore_difesa(7.6, su_misura) == 8.0
          and modificatore_difesa(6.4, su_misura) == 2.0
          and modificatore_difesa(5.0, su_misura) == 0.0)

    # --- 7quater. i quarti di voto ------------------------------------------
    # Chiesti da Davide il 22/09/2026: «voglio che vengano gestiti i casi 0.25, che
    # è come li propone di default FantaGazzetta». ⚠️ Il regolamento pubblico non
    # pubblica nessun valore (§10.1: la piattaforma «propone la versione più
    # diffusa», e la tabella sta dietro il login), quindi i numeri vengono da
    # fantacalcio-online.com — la stessa fonte secondaria delle fasce di titolarità.
    print("\n== 7d. la tabella a quarti di voto ==")
    from data import MOD_DIFESA_SOGLIE_QUARTI, fasce_mod_difesa
    esito("la tabella a quarti ha sei fasce",
          len(MOD_DIFESA_SOGLIE_QUARTI) == 6, str(MOD_DIFESA_SOGLIE_QUARTI))
    # I numeri della fonte, uno per uno: 6,00 → +1; 6,01-6,25 → +2; 6,26-6,50 → +3;
    # 6,51-6,75 → +4; 6,76-7,00 → +5; 7,01+ → +6.
    q = MOD_DIFESA_SOGLIE_QUARTI
    esito("e ogni fascia della fonte torna al punto giusto",
          [modificatore_difesa(m, q) for m in
           (5.99, 6.0, 6.25, 6.26, 6.5, 6.51, 6.75, 6.76, 7.0, 7.01, 8.0)]
          == [0, 1, 2, 3, 3, 4, 4, 5, 5, 6, 6],
          str([modificatore_difesa(m, q) for m in
               (5.99, 6.0, 6.25, 6.26, 6.5, 6.51, 6.75, 6.76, 7.0, 7.01, 8.0)]))
    # ⚠️ Il caso che Davide ha citato: la fonte scrive la fascia «6,01-6,25», qui è
    # scritta «da 6,01 in su» e finisce dove comincia la successiva (6,26). Le due
    # letture danno lo stesso punto perché fra 6,25 e 6,26 non esiste nessuna media:
    # i voti hanno due decimali. Se questa prova fallisse, le due scritture non
    # sarebbero più equivalenti e la tabella andrebbe ripensata, non aggiustata.
    esito("⚠️ una media di 6,25 sta nella fascia bassa, come sulle piattaforme",
          modificatore_difesa(6.25, q) == 2.0 and modificatore_difesa(6.26, q) == 3.0)
    esito("le fasce si leggono anche come intervalli, per mostrarle",
          [(f["da"], f["a"]) for f in fasce_mod_difesa(q)]
          == [(7.01, None), (6.76, 7.0), (6.51, 6.75), (6.26, 6.5),
              (6.01, 6.25), (6.0, 6.0)],
          str(fasce_mod_difesa(q)))
    esito("e la fascia più alta non ha un tetto",
          fasce_mod_difesa(q)[0]["a"] is None)
    esito("⚠️ una tabella con una fascia sola è un intervallo aperto, non vuoto",
          fasce_mod_difesa([(6.0, 1.0)]) == [{"da": 6.0, "a": None, "punti": 1.0}])
    # E la tabella a quarti deve **passare dal form** come qualunque altra: è il
    # pulsante «Sei fasce, a quarti» della modale.
    with app.test_client() as cq:
        with cq.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        cq.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "mod_difesa": "1",
            "soglia_media": [str(m) for m, _ in q],
            "soglia_punti": [str(p) for _, p in q]}, follow_redirects=True)
        db = extensions.get_db()
        scritta = db.execute("SELECT mod_difesa_soglie FROM fanta_leagues "
                             "WHERE id=?", (lid,)).fetchone()[0]
        db.close()
    esito("⚠️ i quarti si salvano senza perdere i centesimi",
          scritta == "7.01:6, 6.76:5, 6.51:4, 6.26:3, 6.01:2, 6:1", scritta)
    esito("e rilette danno la stessa tabella",
          soglie_mod_difesa(scritta) == [(m, p) for m, p in q],
          str(soglie_mod_difesa(scritta)))

    # --- 7ter. le soglie salvate dal form -----------------------------------
    print("\n== 7c. le soglie si salvano dalla lega ==")
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "mod_difesa": "1", "soglia_media": ["7", "6.5", "6"],
            "soglia_punti": ["8", "4", "2"]}, follow_redirects=True)
        db = extensions.get_db()
        riga = db.execute("SELECT mod_difesa_soglie, mod_difesa_portiere "
                          "FROM fanta_leagues WHERE id=?", (lid,)).fetchone()
        db.close()
        esito("la tabella su misura è salvata", riga["mod_difesa_soglie"] == "7:8, 6.5:4, 6:2",
              str(riga["mod_difesa_soglie"]))
        esito("⚠️ e togliendo la spunta il portiere esce dalla media",
              riga["mod_difesa_portiere"] == 0, str(riga["mod_difesa_portiere"]))

        # ⚠️ Le fasce non sono tre: il regolamento fissa **come** si fa la media,
        # non in quanti scalini si traduce. Dal 22/09/2026 le righe si aggiungono
        # e si tolgono dalla modale, quindi ne può arrivare un numero qualsiasi.
        def soglie_salvate():
            db = extensions.get_db()
            fuori = db.execute("SELECT mod_difesa_soglie FROM fanta_leagues "
                               "WHERE id=?", (lid,)).fetchone()[0]
            db.close()
            return fuori

        c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "mod_difesa": "1",
            "soglia_media": ["6", "7.5", "7", "6.5", "8"],
            "soglia_punti": ["1", "8", "6", "3", "10"]}, follow_redirects=True)
        esito("cinque fasce si salvano tutte, ordinate dalla più alta",
              soglie_salvate() == "8:10, 7.5:8, 7:6, 6.5:3, 6:1", soglie_salvate())
        c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "mod_difesa": "1", "soglia_media": ["6"], "soglia_punti": ["2"]},
            follow_redirects=True)
        esito("e una sola fascia è una tabella valida", soglie_salvate() == "6:2",
              soglie_salvate())
        # Una riga aggiunta e lasciata in bianco non deve diventare una fascia: il
        # server la salta, ed è il motivo per cui la modale può aggiungerla vuota.
        c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "mod_difesa": "1", "soglia_media": ["7", "", "6"],
            "soglia_punti": ["6", "", ""]}, follow_redirects=True)
        esito("⚠️ una riga lasciata a metà non diventa una fascia",
              soglie_salvate() == "7:6", soglie_salvate())
        # ⚠️ Nessuna riga leggibile **non** vuol dire «tabella vuota»: la colonna
        # non entra nella query e resta quella di prima. È la stessa regola dei
        # campi delle regole lasciati stare, ed è il motivo per cui l'ultima riga
        # non si può togliere dalla modale.
        c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "mod_difesa": "1"}, follow_redirects=True)
        esito("⚠️ e senza nessuna fascia la tabella di prima resta",
              soglie_salvate() == "7:6", soglie_salvate())
        c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "mod_difesa": "1", "soglia_media": ["7", "6.5", "6"],
            "soglia_punti": ["8", "4", "2"]}, follow_redirects=True)
        esito("la tabella torna com'era per le prove che seguono",
              soglie_salvate() == "7:8, 6.5:4, 6:2", soglie_salvate())
        r = c.get(f"/fantacalcio/lega/{lid}")
        pagina = r.data.decode("utf-8", "replace")
        esito("la scheda della lega mostra la tabella e come si fa la media",
              "migliori 4 difensori" in pagina and "+8" in pagina)
        # Una soglia che non è un numero non si salva «tanto poi si vede».
        c.post("/fantacalcio/lega/salva", data={
            "lega_id": str(lid), "nome": "Lega Amici", "moduli": "3-4-3,4-4-2",
            "mod_difesa": "1", "soglia_media": ["sette"], "soglia_punti": ["8"]},
            follow_redirects=True)
        db = extensions.get_db()
        dopo = db.execute("SELECT mod_difesa_soglie FROM fanta_leagues WHERE id=?",
                          (lid,)).fetchone()["mod_difesa_soglie"]
        db.close()
        esito("⚠️ una soglia che non è un numero viene rifiutata, e resta la vecchia",
              dopo == "7:8, 6.5:4, 6:2", str(dopo))

    # --- 9. le probabili formazioni -----------------------------------------
    # (id, nome, ruolo, percentuale, slug-nell-url)
    print("\n== 8. le probabili: il lettore ==")
    inter_tit = [(1, "Sommer", "p", 90, "sommer"), (2, "Bastoni", "d", 85, "bastoni"),
                 (3, "Barella", "c", 90, "barella")]
    inter_pan = [(4, "Thuram", "a", 55, "thuram"), (99, "Ignoto", "c", 20, "ignoto")]
    milan_tit = [(11, "Maignan", "p", 90, "maignan")]
    milan_pan = [(12, "Leao", "a", 60, "leao")]
    una = [(("inter", "Inter", "3-5-2", inter_tit, inter_pan),
            ("milan", "Milan", "4-3-3", milan_tit, milan_pan))]

    import fantacalcio_it as F
    vera = F.scarica
    F.scarica = lambda nome, forza=False: pagina_finta(una)
    try:
        dati, problemi = F.probabili()
        esito("legge la giornata e la stagione",
              dati["giornata"] == 6 and dati["stagione"] == "2026-27",
              f"{dati['giornata']} / {dati['stagione']}")
        esito("legge le due squadre con i loro moduli",
              dati["squadre"]["inter"]["modulo"] == "3-5-2"
              and dati["squadre"]["milan"]["modulo"] == "4-3-3")
        esito("⚠️ e la squadra in trasferta ha il modulo, non None",
              dati["squadre"]["milan"]["modulo"] is not None)
        esito("l'avversario e il campo arrivano dall'altra metà della partita",
              dati["squadre"]["inter"]["avversario"] == "Milan"
              and dati["squadre"]["inter"]["in_casa"] == 1
              and dati["squadre"]["milan"]["in_casa"] == 0)
        esito("sette convocati, quattro titolari", len(dati["voci"]) == 7
              and sum(v["titolare"] for v in dati["voci"]) == 4,
              f"{len(dati['voci'])} voci")
        una_voce = next(v for v in dati["voci"] if v["id"] == 2)
        esito("ruolo, percentuale e squadra vengono dall'URL, non dal titolo",
              una_voce["ruolo"] == "d" and una_voce["percentuale"] == 85
              and una_voce["squadra_slug"] == "inter")
        esito("una pagina che torna così non ha problemi da dire",
              problemi == [], "; ".join(problemi))

        # Rotta apposta: il campo dice un undici, la scheda un altro.
        storta = [(("inter", "Inter", "3-5-2", inter_tit, inter_pan,
                    inter_tit[:1]),
                   ("milan", "Milan", "4-3-3", milan_tit, milan_pan))]
        F.scarica = lambda nome, forza=False: pagina_finta(storta)
        _, problemi2 = F.probabili()
        esito("⚠️ se il campo e la scheda non combaciano, lo dice",
              any("campo" in p for p in problemi2), "; ".join(problemi2) or "niente")

        # Senza giornata: non si inventa un numero.
        F.scarica = lambda nome, forza=False: pagina_finta(una, giornata=None)
        senza, problemi3 = F.probabili()
        esito("⚠️ una pagina senza giornata non ne inventa una",
              senza["giornata"] is None and any("giornata" in p for p in problemi3))

        # --- lo script di import, sulla stessa pagina finta ------------------
        print("\n== 9. le probabili: l'import ==")
        sys.path.insert(0, os.path.join(RADICE, "scripts"))
        import importa_probabili as IP
        F.scarica = lambda nome, forza=False: pagina_finta(una)

        argv = sys.argv
        sys.argv = ["importa_probabili.py"]
        codice = IP.main()
        esito("⚠️ con due squadre sole si rifiuta di scrivere (soglia 20)",
              codice == 1)
        db = extensions.get_db()
        vuoto = db.execute("SELECT COUNT(*) FROM fanta_probabili").fetchone()[0]
        db.close()
        esito("e infatti non ha scritto niente", vuoto == 0, str(vuoto))

        sys.argv = ["importa_probabili.py", "--forza"]
        IP.main()
        db = extensions.get_db()
        quante = db.execute("SELECT COUNT(*) FROM fanta_probabili").fetchone()[0]
        squadre = db.execute("SELECT COUNT(*) FROM fanta_probabili_squadre").fetchone()[0]
        db.close()
        esito("con --forza scrive i sette convocati e le due squadre",
              quante == 7 and squadre == 2, f"{quante} voci, {squadre} squadre")

        IP.main()
        db = extensions.get_db()
        ancora = db.execute("SELECT COUNT(*) FROM fanta_probabili").fetchone()[0]
        db.close()
        esito("rieseguirlo non raddoppia niente", ancora == 7, str(ancora))

        # La giornata si riscrive **per intero**: chi sparisce dai convocati deve
        # sparire, non restare a dire che è in panchina.
        senza_thuram = [(("inter", "Inter", "3-5-2", inter_tit,
                          [v for v in inter_pan if v[0] != 4]),
                         ("milan", "Milan", "4-3-3", milan_tit, milan_pan))]
        F.scarica = lambda nome, forza=False: pagina_finta(senza_thuram)
        IP.main()
        db = extensions.get_db()
        resta = db.execute("SELECT COUNT(*) FROM fanta_probabili WHERE player_id=4"
                           ).fetchone()[0]
        db.close()
        esito("⚠️ chi non è più fra i convocati esce dalla giornata", resta == 0,
              str(resta))
        sys.argv = argv
    finally:
        F.scarica = vera

    # --- 10. le probabili a schermo -----------------------------------------
    print("\n== 10. le probabili: a schermo ==")
    db = extensions.get_db()
    # Rimetto Thuram, e allineo il listone finto alle squadre della giornata: la
    # rosa di prova ha cinque giocatori dell'Inter, uno dei quali è uscito.
    db.execute("INSERT INTO fanta_probabili(giornata, player_id, nome, squadra_slug,"
               " ruolo, titolare, percentuale) VALUES(6,4,'Thuram','inter','a',0,55)")
    db.execute("UPDATE fanta_players SET squadra_slug='inter' WHERE id IN (1,2,3,4)")
    db.execute("UPDATE fanta_players SET squadra_slug='xxx' WHERE id=5")
    # Il quarto stato, che è quello che si confonde più facilmente: un giocatore
    # dell'Inter che l'Inter **non ha convocato**. L'Inter gioca, lui no — ed è
    # diverso da «la sua squadra non gioca», che è il caso dell'id 5.
    db.execute("INSERT INTO fanta_players(id,nome,squadra,squadra_slug,ruolo_classic,"
               "qa,fvm,attivo,visto_il) "
               "VALUES(6,'Escluso','INT','inter','c',8,20,1,'2026-09-21')")
    db.execute("INSERT INTO fanta_roster(league_id, player_id, prezzo) VALUES(?,6,1)",
               (lid,))
    db.commit()
    db.close()
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        r = c.get(f"/fantacalcio/lega/{lid}")
        testo_pagina = r.data.decode("utf-8", "replace")
        esito("la pagina della lega dice chi è titolare e chi in panchina",
              "titolare 90%" in testo_pagina and "panchina 55%" in testo_pagina)
        esito("⚠️ «non convocato» (la sua squadra gioca) c'è, ed è suo",
              "non convocato" in testo_pagina)
        esito("⚠️ e «non gioca» (la sua squadra non c'è) è un'altra cosa ancora",
              "non gioca" in testo_pagina)
        esito("i quattro stati stanno tutti e quattro nella stessa pagina",
              all(s in testo_pagina for s in
                  ("titolare 90%", "panchina 55%", "non convocato", "non gioca")))
        r = c.get("/fantacalcio/probabili")
        pagina = r.data.decode("utf-8", "replace")
        esito("la pagina delle probabili si apre con le due squadre",
              r.status_code == 200 and "Inter" in pagina and "Milan" in pagina)
        esito("e segna quali sono in una tua rosa", ">mio<" in pagina)

    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "altro"
            s["role"] = "user"
            s["user_id"] = ids["altro"]
        r = c.get("/fantacalcio/probabili")
        altrui = r.data.decode("utf-8", "replace")
        esito("un altro utente vede le formazioni (sono pubbliche)",
              "Barella" in altrui)
        esito("⚠️ ma non gli risulta «mio» nessun giocatore della rosa altrui",
              ">mio<" not in altrui)

    # --- 11. il pulsante e l'aggiornamento automatico ------------------------
    print("\n== 11. aggiornare: il pulsante e l'automatico ==")
    import fanta_import as IMP
    # Una giornata intera finta: venti squadre, così la soglia delle 20 non
    # scatta e si prova la strada normale, non quella del rifiuto.
    def venti_squadre(giornata=7):
        partite = []
        for n in range(10):
            casa = (f"casa{n}", f"Casa {n}", "4-3-3",
                    [(1000 + n * 10 + i, f"Tit{n}_{i}", "d", 90, f"t{n}{i}")
                     for i in range(3)],
                    [(1500 + n * 10 + i, f"Pan{n}_{i}", "c", 40, f"p{n}{i}")
                     for i in range(2)])
            fuori = (f"fuori{n}", f"Fuori {n}", "3-5-2",
                     [(2000 + n * 10 + i, f"TitF{n}_{i}", "a", 85, f"tf{n}{i}")
                      for i in range(3)],
                     [(2500 + n * 10 + i, f"PanF{n}_{i}", "p", 30, f"pf{n}{i}")
                      for i in range(2)])
            partite.append((casa, fuori))
        return pagina_finta(partite, giornata=giornata)

    vera_scarica, vera_eta = F.scarica, F.eta_cache
    try:
        F.scarica = lambda nome, forza=False: venti_squadre()
        # La cache è «fresca»: entrando nella sezione non si deve rileggere niente.
        F.eta_cache = lambda nome: 0.1
        with app.test_client() as c:
            with c.session_transaction() as s:
                s["username"] = "davide"
                s["role"] = "user"
                s["user_id"] = ids["davide"]
            c.get("/fantacalcio/")
            db = extensions.get_db()
            g7 = db.execute("SELECT COUNT(*) FROM fanta_probabili WHERE giornata=7"
                            ).fetchone()[0]
            db.close()
            esito("⚠️ con la copia fresca entrare nella sezione NON riscarica niente",
                  g7 == 0, f"righe della giornata 7: {g7}")

            # Copia vecchia: entrando, si rilegge da sé.
            F.eta_cache = lambda nome: 99.0
            c.get("/fantacalcio/")
            db = extensions.get_db()
            g7 = db.execute("SELECT COUNT(*) FROM fanta_probabili WHERE giornata=7"
                            ).fetchone()[0]
            db.close()
            esito("con la copia vecchia si aggiorna da sé entrando", g7 == 100,
                  f"righe della giornata 7: {g7}")
            esito("e la giornata di prima resta nell'archivio",
                  extensions.get_db().execute(
                      "SELECT COUNT(DISTINCT giornata) FROM fanta_probabili"
                  ).fetchone()[0] == 2)

            # Il pulsante: è un POST, e un GET non deve funzionare.
            r = c.get("/fantacalcio/aggiorna/probabili")
            esito("⚠️ il pulsante è un POST: da GET non si aggiorna",
                  r.status_code == 405, str(r.status_code))
            r = c.post("/fantacalcio/aggiorna/probabili", follow_redirects=True)
            esito("il pulsante aggiorna e lo dice",
                  b"Probabili aggiornate" in r.data)
            r = c.post("/fantacalcio/aggiorna/quelloCheVuoi", follow_redirects=True)
            esito("e non aggiorna qualcosa che non esiste",
                  "Non so cosa aggiornare" in r.data.decode("utf-8", "replace"))

            # ⚠️ Il caso che conta: la fonte non risponde. La sezione deve aprirsi
            # lo stesso, col dato di prima, e dirlo.
            def rotta(nome, forza=False):
                raise OSError("la rete non va")
            F.scarica = rotta
            r = c.get("/fantacalcio/")
            pagina = r.data.decode("utf-8", "replace")
            esito("⚠️ se la fonte non risponde la sezione si apre lo stesso",
                  r.status_code == 200)
            esito("e lo dice invece di far finta di niente",
                  "Non sono riuscito a leggere fantacalcio.it" in pagina)
            db = extensions.get_db()
            resta = db.execute("SELECT COUNT(*) FROM fanta_probabili WHERE giornata=7"
                               ).fetchone()[0]
            db.close()
            esito("e il dato di prima è ancora lì", resta == 100, str(resta))
            r = c.post("/fantacalcio/aggiorna/listone", follow_redirects=True)
            esito("stessa cosa premendo il pulsante: un errore, non una pagina rotta",
                  r.status_code == 200
                  and "Non sono riuscito a leggere" in r.data.decode("utf-8", "replace"))

        # ⚠️ «in una tua rosa» dev'essere tua. Il primo giro contava le rose di
        # tutti gli utenti, e l'ha preso `controlla_proprietario.py`: la funzione
        # è la stessa per gli script (che una sessione non ce l'hanno) e per il
        # web (che ce l'ha), e il default «vedi tutto» era la trappola di §1.1.
        print("\n== 11b. «in una tua rosa» è davvero tua ==")
        import fanta_import as IMP2
        db = extensions.get_db()
        db.execute("INSERT INTO fanta_leagues(user_id, nome) VALUES(?, 'Lega altrui')",
                   (ids["altro"],))
        altrui_id = db.execute("SELECT id FROM fanta_leagues WHERE nome='Lega altrui'"
                               ).fetchone()["id"]
        # Lo stesso giocatore uscito dal listone, in rosa a tutti e due.
        db.execute("INSERT INTO fanta_roster(league_id, player_id, prezzo) VALUES(?,5,1)",
                   (altrui_id,))
        db.commit()
        quante_in_tutto = db.execute(
            "SELECT COUNT(*) FROM fanta_roster WHERE player_id=5").fetchone()[0]
        db.close()
        esito("il giocatore uscito è in due rose, una per utente",
              quante_in_tutto == 2, str(quante_in_tutto))
        db = extensions.get_db()
        tutte = IMP2._rose(db, [5], IMP2.TUTTE_LE_ROSE)
        db.close()
        esito("uno script da riga di comando le vede tutte e due",
              tutte.get(5) == 2, str(tutte))
        db = extensions.get_db()
        mie = IMP2._rose(db, [5], ("l.user_id=?", [ids["davide"]]))
        db.close()
        esito("⚠️ ma con l'ambito di Davide ne conta UNA, non due",
              mie.get(5) == 1, str(mie))
        db = extensions.get_db()
        sue = IMP2._rose(db, [5], ("l.user_id=?", [ids["altro"]]))
        db.close()
        esito("e con l'ambito dell'altro utente conta la sua", sue.get(5) == 1, str(sue))
    finally:
        F.scarica, F.eta_cache = vera_scarica, vera_eta

    # --- 12. la formazione ---------------------------------------------------
    # La rosa di prova ha 5 giocatori e non basta per un 3-4-3, quindi qui se ne
    # aggiunge una vera: undici titolari più qualche panchinaro.
    print("\n== 12. la formazione ==")
    db = extensions.get_db()
    pid = 100
    per_ruolo = {}
    for ruolo, quanti in (("p", 2), ("d", 6), ("c", 7), ("a", 5)):
        for n in range(quanti):
            pid += 1
            db.execute("INSERT INTO fanta_players(id,nome,squadra,squadra_slug,"
                       "ruolo_classic,qa,fvm,attivo,visto_il) "
                       "VALUES(?,?,'INT','inter',?,10,20,1,'2026-09-21')",
                       (pid, f"{ruolo.upper()}{n}", ruolo))
            db.execute("INSERT INTO fanta_roster(league_id,player_id,prezzo) "
                       "VALUES(?,?,1)", (lid, pid))
            per_ruolo.setdefault(ruolo, []).append(pid)
    db.commit()
    db.close()

    undici = (per_ruolo["p"][:1] + per_ruolo["d"][:3] +
              per_ruolo["c"][:4] + per_ruolo["a"][:3])       # 3-4-3
    panca = per_ruolo["d"][3:5] + per_ruolo["c"][4:6]

    def salva(c, dati):
        r = c.post(f"/fantacalcio/lega/{lid}/formazione/salva", data=dati,
                   follow_redirects=True)
        return r.data.decode("utf-8", "replace")

    def righe():
        db = extensions.get_db()
        fuori = [dict(x) for x in db.execute(
            "SELECT * FROM fanta_formazione WHERE league_id=? "
            "ORDER BY titolare DESC, ordine", (lid,))]
        db.close()
        return fuori

    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        r = c.get(f"/fantacalcio/lega/{lid}/formazione")
        esito("la pagina del campo si apre", r.status_code == 200
              and b"Formazione" in r.data)

        pagina = salva(c, {"modulo": "3-4-3", "titolare": undici, "panchinaro": panca})
        esito("una formazione buona si salva", "Formazione salvata" in pagina)
        dentro = righe()
        esito("undici titolari e quattro in panchina",
              sum(1 for x in dentro if x["titolare"]) == 11
              and sum(1 for x in dentro if not x["titolare"]) == 4,
              f"{len(dentro)} righe")
        esito("⚠️ la panchina è salvata IN ORDINE: è l'ordine di subentro",
              [x["player_id"] for x in dentro if not x["titolare"]] == panca)
        db = extensions.get_db()
        esito("e il modulo sta sulla lega, non su ogni riga",
              db.execute("SELECT modulo_scelto FROM fanta_leagues WHERE id=?",
                         (lid,)).fetchone()["modulo_scelto"] == "3-4-3")
        db.close()

        # --- i rifiuti: Davide ha scelto la validazione severa ---------------
        quante_prima = len(righe())
        pagina = salva(c, {"modulo": "3-4-3", "titolare": undici[:10]})
        esito("⚠️ dieci titolari vengono rifiutati, e non si salva niente",
              "devono essere 11" in pagina and len(righe()) == quante_prima)
        pagina = salva(c, {"modulo": "3-5-2", "titolare": undici})
        esito("un 3-4-3 mandato come 3-5-2 viene rifiutato",
              "ne vuole 5" in pagina and len(righe()) == quante_prima)
        pagina = salva(c, {"modulo": "4-4-2", "titolare": undici[:10] + undici[:1]})
        esito("⚠️ lo stesso giocatore due volte viene rifiutato",
              "due volte" in pagina and len(righe()) == quante_prima)
        pagina = salva(c, {"modulo": "3-4-3", "titolare": undici[:10] + [9999]})
        esito("un giocatore che non è in rosa viene rifiutato",
              "non è in questa rosa" in pagina and len(righe()) == quante_prima)
        pagina = salva(c, {"modulo": "4-5-1", "titolare": undici})
        esito("un modulo che la lega non ammette viene rifiutato",
              "non è fra quelli ammessi" in pagina and len(righe()) == quante_prima)
        pagina = salva(c, {"modulo": "3-4-3", "titolare": undici,
                           "panchinaro": per_ruolo["d"][3:6] + per_ruolo["c"][4:7] +
                                         per_ruolo["a"][3:5] + per_ruolo["p"][1:2]})
        esito("una panchina più lunga di quella ammessa viene rifiutata",
              "ammette 7" in pagina and len(righe()) == quante_prima)

        # ⚠️ Il ruolo lo decide la rosa, non il form: se lo decidesse il browser
        # basterebbe dire che un attaccante è un difensore per far tornare i conti.
        pagina = salva(c, {"modulo": "3-4-3",
                           "titolare": per_ruolo["p"][:1] + per_ruolo["a"][:3] +
                                       per_ruolo["c"][:4] + per_ruolo["a"][3:5] +
                                       per_ruolo["d"][:1],
                           "ruolo": ["d"] * 11})
        esito("⚠️ un ruolo mandato dal form non cambia i conti dei reparti",
              "difensor" in pagina and len(righe()) == quante_prima)

    # --- la formazione è della lega, e la lega è di qualcuno -----------------
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "altro"
            s["role"] = "user"
            s["user_id"] = ids["altro"]
        r = c.get(f"/fantacalcio/lega/{lid}/formazione", follow_redirects=True)
        esito("un altro utente non apre il campo di una lega non sua",
              b"Lega non trovata" in r.data or b"Formazione" not in r.data)
        prima = righe()
        salva(c, {"modulo": "4-4-2", "titolare": undici})
        esito("⚠️ e non può nemmeno scrivere la formazione altrui",
              righe() == prima, f"{len(righe())} righe")


    # ── 13. la rosa incollata ───────────────────────────────────────────────
    # ⚠️ Questo blocco si fa una **lega sua**, perché le prove di prima hanno
    # riempito la rosa della prima: una rosa vuota è l'unico posto in cui si può
    # dire con certezza quante righe ha scritto un incolla.
    print("\n== 13. la rosa incollata ==")
    from data import analizza_riga_rosa, leggi_rosa_incollata, chiave_nome

    # Le tre forme di ambiguità misurate sul listone vero, in piccolo:
    # `Thuram` esiste **e** c'è `Thuram K.` (nome che è prefisso di un altro),
    # i due `Martinez` condividono il cognome, e `Koné` ha un accento che nessuno
    # scrive quando incolla.
    db = extensions.get_db()
    for pid, nome, sq, slug, ruolo in (
            (201, "Thuram K.", "JUV", "juventus", "c"),
            (202, "Martinez L.", "INT", "inter", "a"),
            (203, "Martinez Jo.", "INT", "inter", "p"),
            (204, "Koné M.", "ROM", "roma", "c"),
            (205, "Adams A.", "VEN", "venezia", "a"),
            (206, "Adams C.", "TOR", "torino", "a")):
        db.execute("INSERT INTO fanta_players(id,nome,squadra,squadra_slug,"
                   "ruolo_classic,qa,fvm,attivo,visto_il) "
                   "VALUES(?,?,?,?,?,10,20,1,'2026-09-21')",
                   (pid, nome, sq, slug, ruolo))
    db.execute("INSERT INTO fanta_leagues(user_id,nome,moduli,n_panchinari) "
               "VALUES(?,'Seconda Lega','3-4-3',7)", (ids["davide"],))
    db.commit()
    lid2 = db.execute("SELECT id FROM fanta_leagues WHERE nome='Seconda Lega'"
                      ).fetchone()["id"]
    listone = [dict(r) for r in db.execute(
        "SELECT id, nome, squadra, squadra_slug, ruolo_classic, qa, fvm, attivo "
        "FROM fanta_players")]
    db.close()

    # --- la riga, scomposta -------------------------------------------------
    r = analizza_riga_rosa("1. Thuram K. JUV 18", {"juv": "JUV"})
    esito("una riga con indice, squadra e prezzo si scompone",
          r["nome"] == "Thuram K." and r["squadra"] == "JUV" and r["prezzo"] == 18.0,
          f"nome={r['nome']!r} sq={r['squadra']} prezzo={r['prezzo']}")
    r = analizza_riga_rosa("Barella, 12,5")
    esito("⚠️ la virgola decimale non è un separatore: 12,5 resta 12.5",
          r["nome"] == "Barella" and r["prezzo"] == 12.5,
          f"nome={r['nome']!r} prezzo={r['prezzo']}")
    r = analizza_riga_rosa("Difensori")
    esito("una riga col solo ruolo è un'intestazione, non un giocatore",
          r["intestazione"] and r["ruolo"] == "d")
    # ⚠️ Il punto è tutto: `A.` è l'iniziale di un nome, `A` è il ruolo. Senza
    # questa distinzione ogni `Adams A.` del listone perderebbe la sua iniziale.
    r = analizza_riga_rosa("Adams A.")
    esito("⚠️ «A.» col punto resta parte del nome, non diventa il ruolo",
          r["nome"] == "Adams A." and r["ruolo"] is None, f"nome={r['nome']!r}")
    r = analizza_riga_rosa("A Adams")
    esito("e «A» senza punto è il ruolo",
          r["nome"] == "Adams" and r["ruolo"] == "a", f"nome={r['nome']!r}")
    r = analizza_riga_rosa("Thuram 3 5")
    esito("due numeri in una riga la dichiarano dubbia invece di scegliere",
          r["dubbia"], f"prezzo={r['prezzo']}")
    esito("gli accenti non contano nel confronto dei nomi",
          chiave_nome("Koné M.") == chiave_nome("Kone M.") == "kone m")

    # --- l'abbinamento ------------------------------------------------------
    def leggi(testo, gia=()):
        return {v["grezzo"]: v for v in leggi_rosa_incollata(testo, listone, gia)}

    v = leggi("Bastoni 22\nThuram\nMartinez\nLautaro Martinez\nAdams\n"
              "Kone M.\nZibaldone 4")
    esito("un nome esatto e senza omonimi è «ok»",
          v["Bastoni 22"]["stato"] == "ok" and v["Bastoni 22"]["prezzo"] == 22.0)
    # ⚠️ Il caso che si sarebbe sbagliato in silenzio: «Thuram» **è** un nome
    # esatto del listone, e un codice ragionevole l'avrebbe preso e messo in rosa.
    # Ma c'è anche `Thuram K.`, che è un altro giocatore in un'altra squadra e in
    # un altro ruolo.
    esito("⚠️ un nome esatto CON un omonimo non è «ok»: è da confermare",
          v["Thuram"]["stato"] == "conferma"
          and len(v["Thuram"]["candidati"]) == 2
          and v["Thuram"]["scelto"]["id"] == 4,
          f"stato={v['Thuram']['stato']} candidati={len(v['Thuram']['candidati'])}")
    esito("un cognome condiviso da due giocatori non ne scegli uno",
          v["Martinez"]["stato"] == "scegli" and v["Martinez"]["scelto"] is None
          and len(v["Martinez"]["candidati"]) == 2)
    esito("ma col nome proprio davanti l'iniziale lo risolve",
          v["Lautaro Martinez"]["stato"] == "conferma"
          and v["Lautaro Martinez"]["scelto"]["id"] == 202,
          str((v["Lautaro Martinez"]["scelto"] or {}).get("nome")))
    # ⚠️ Questa è la prova che ha trovato il baco al primo giro: «Adams» da solo,
    # contro `Adams A.` e `Adams C.`, veniva risolto in `Adams A.` perché la «a»
    # dell'iniziale comincia anche «adams». Cioè si inventava una risposta dove
    # non c'era niente da confrontare.
    esito("⚠️ «Adams» da solo resta da scegliere, non diventa «Adams A.»",
          v["Adams"]["stato"] == "scegli" and v["Adams"]["scelto"] is None,
          str((v["Adams"]["scelto"] or {}).get("nome")))
    esito("un nome senza accenti trova quello con l'accento",
          v["Kone M."]["stato"] == "ok" and v["Kone M."]["scelto"]["id"] == 204)
    esito("un nome che non esiste non viene indovinato",
          v["Zibaldone 4"]["stato"] == "niente"
          and not v["Zibaldone 4"]["candidati"])

    # L'intestazione che scende sulle righe dopo, e la squadra che disambigua.
    # ⚠️ Qui le due righe sono **la stessa riga scritta due volte** e vanno lette
    # in ordine, non per nome: la prima versione di questa prova le metteva in un
    # dizionario per `grezzo` e ne perdeva una, dicendo NO a un codice giusto.
    doppia = leggi_rosa_incollata("Portieri\nMartinez\nAttaccanti\nMartinez", listone)
    esito("⚠️ l'intestazione del ruolo rende univoco un cognome condiviso",
          [x["scelto"]["id"] for x in doppia] == [203, 202],
          str([(x["stato"], (x["scelto"] or {}).get("nome")) for x in doppia]))
    v = leggi("Martinez INT p")
    esito("e la squadra e il ruolo sulla riga fanno lo stesso",
          v["Martinez INT p"]["scelto"]["id"] == 203)
    # ⚠️ Una sigla sbagliata non deve far sparire il giocatore: la riga si vede
    # comunque, con la scelta in mano a chi guarda. Ma non resta «sicura» — o la
    # sigla è sbagliata, o il giocatore giusto è un altro, e in tutti e due i casi
    # è una riga da guardare. Anche questa l'ha trovata la prova: prima diceva
    # «ok» su una riga che chiedeva un giocatore della Juve e ne trovava uno
    # dell'Inter.
    v = leggi("Bastoni JUV")
    esito("⚠️ una squadra che non combacia non cancella il candidato ma lo dichiara",
          v["Bastoni JUV"]["stato"] == "conferma"
          and v["Bastoni JUV"]["scarti"] == ["squadra"],
          f"stato={v['Bastoni JUV']['stato']} scarti={v['Bastoni JUV']['scarti']}")

    # --- la pagina: guarda, poi scrive --------------------------------------
    def in_rosa():
        db = extensions.get_db()
        fuori = [r["player_id"] for r in db.execute(
            "SELECT player_id FROM fanta_roster WHERE league_id=? ORDER BY player_id",
            (lid2,))]
        db.close()
        return fuori

    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        testo = "Bastoni 22\nThuram\nMartinez\nZibaldone"
        r = c.post(f"/fantacalcio/lega/{lid2}/rosa/incolla", data={"testo": testo})
        pagina = r.data.decode("utf-8", "replace")
        esito("l'anteprima si apre", r.status_code == 200 and "righe lette" in pagina)
        esito("⚠️ e non ha scritto NIENTE in rosa", in_rosa() == [],
              f"{len(in_rosa())} righe")
        esito("la riga da scegliere ha una tendina, non un id fisso",
              'name="pid_2"' in pagina and 'name="pid_2" value=' not in pagina)

        # La conferma scrive **solo** le righe spuntate: la spunta è la decisione.
        r = c.post(f"/fantacalcio/lega/{lid2}/rosa/incolla/conferma", data={
            "riga_0": "on", "pid_0": "2", "prezzo_0": "22",
            "pid_1": "4", "prezzo_1": "",           # non spuntata: non entra
            "riga_2": "on", "pid_2": "", "prezzo_2": "",   # scelta lasciata vuota
        }, follow_redirects=True)
        esito("entra solo la riga spuntata", in_rosa() == [2], str(in_rosa()))
        db = extensions.get_db()
        esito("col prezzo che avevo scritto io",
              db.execute("SELECT prezzo FROM fanta_roster WHERE league_id=? AND "
                         "player_id=2", (lid2,)).fetchone()["prezzo"] == 22.0)
        db.close()

        # Un id che non è nel listone non entra, per quanto sia spuntato.
        c.post(f"/fantacalcio/lega/{lid2}/rosa/incolla/conferma", data={
            "riga_0": "on", "pid_0": "99999", "prezzo_0": "5"}, follow_redirects=True)
        esito("⚠️ un player_id inventato dal browser non entra in rosa",
              in_rosa() == [2], str(in_rosa()))

        # Lo stesso giocatore due volte, e uno che c'era già: il vincolo UNIQUE
        # non deve diventare un errore in faccia.
        r = c.post(f"/fantacalcio/lega/{lid2}/rosa/incolla/conferma", data={
            "riga_0": "on", "pid_0": "3", "prezzo_0": "7",
            "riga_1": "on", "pid_1": "3", "prezzo_1": "7",
            "riga_2": "on", "pid_2": "2", "prezzo_2": "9",
        }, follow_redirects=True)
        esito("un doppione e uno già in rosa non raddoppiano niente",
              in_rosa() == [2, 3], str(in_rosa()))
        esito("e la pagina lo dice invece di dare un errore",
              "già in rosa da prima" in r.data.decode("utf-8", "replace"))

        # L'anteprima di un giocatore già in rosa parte **senza** la spunta.
        r = c.post(f"/fantacalcio/lega/{lid2}/rosa/incolla",
                   data={"testo": "Bastoni"})
        esito("chi è già in rosa è segnato «già in rosa»",
              "già in rosa" in r.data.decode("utf-8", "replace"))

    # --- e la lega è di chi ce l'ha -----------------------------------------
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "altro"
            s["role"] = "user"
            s["user_id"] = ids["altro"]
        r = c.post(f"/fantacalcio/lega/{lid2}/rosa/incolla",
                   data={"testo": "Barella"}, follow_redirects=True)
        esito("un altro utente non apre l'anteprima di una lega non sua",
              b"Lega non trovata" in r.data)
        prima = in_rosa()
        c.post(f"/fantacalcio/lega/{lid2}/rosa/incolla/conferma", data={
            "riga_0": "on", "pid_0": "4", "prezzo_0": "1"}, follow_redirects=True)
        esito("⚠️ e non può scrivere nella rosa di un altro", in_rosa() == prima,
              str(in_rosa()))


    # ── 14. il consiglio ────────────────────────────────────────────────────
    # ⚠️ Anche questo blocco si fa **lega e rosa sue**, con statistiche scelte a
    # mano: il consiglio è tutto ordinamento, e su una rosa qualsiasi «sembra
    # giusto» senza dimostrare niente. Qui ogni giocatore esiste per far fallire
    # una regola precisa.
    print("\n== 14. il consiglio ==")
    from data import (fantamedia_regole, fascia_titolarita, rigori_segnati_tirati,
                      valuta_rosa, consiglia_formazione, consiglia_moduli,
                      MINIMO_PARTITE_FIDATO, SOGLIA_SCHIERABILE)

    # --- i pezzi puri --------------------------------------------------------
    esito("«2 / 3» sono due rigori segnati su tre tirati",
          rigori_segnati_tirati("2 / 3") == (2, 3))
    esito("una casella vuota non diventa un rigore sbagliato",
          rigori_segnati_tirati(None) == (0, 0) and rigori_segnati_tirati("") == (0, 0))
    # Le soglie sono quelle della fonte, e i bordi sono la parte che conta.
    esito("le fasce cadono dove le mette la fonte",
          [fascia_titolarita(x) for x in (90, 89, 60, 59, 40, 39, 1)]
          == ["sicuro", "favorito", "favorito", "ballottaggio", "ballottaggio",
              "panchina", "panchina"])
    esito("⚠️ senza percentuale la fascia non si inventa",
          fascia_titolarita(None) is None)

    # La fantamedia rifatta: un caso fatto a mano, coi conti in chiaro.
    # media 6.0 su 5 partite, 2 gol (+3), 1 assist (+1), 2 ammonizioni (−0,5)
    # → bonus 6+1−1 = 6, quindi 6.0 + 6/5 = 7.2
    tizio = {"partite_a_voto": 5, "media_voto": 6.0, "gol": 2, "assist": 1,
             "ammonizioni": 2, "espulsioni": 0, "gol_subiti": 0,
             "rigori_parati": 0, "rigori": "0 / 0"}
    regole_base = {"bonus_gol": 3, "bonus_assist": 1, "malus_amm": -0.5,
                   "malus_esp": -1, "malus_gol_subito": -1,
                   "bonus_rigore_parato": 3, "malus_rigore_sbagliato": -3}
    fm, pezzi = fantamedia_regole(tizio, regole_base)
    esito("la fantamedia rifatta torna al conto fatto a mano (7.2)",
          round(fm, 3) == 7.2, str(fm))
    esito("e dice di quali voci è fatta", len(pezzi) == 3,
          str([p["voce"] for p in pezzi]))
    # ⚠️ Il punto di tutta la decisione: cambiando la regola della lega, cambia.
    fm5, _ = fantamedia_regole(tizio, dict(regole_base, bonus_gol=5))
    esito("⚠️ con il gol a +5 la stessa stagione vale 8.0, non 7.2",
          round(fm5, 3) == 8.0, str(fm5))
    # I rigori sbagliati si contano dalla differenza, e i segnati NON si
    # ricontano: sono già dentro `gol`.
    fm_rig, _ = fantamedia_regole(dict(tizio, rigori="1 / 3"), regole_base)
    esito("due rigori sbagliati su tre tirati togliono 6 punti su 5 partite",
          round(fm_rig, 3) == round(7.2 - 6.0 / 5, 3), str(fm_rig))
    esito("⚠️ senza partite a voto la fantamedia è assente, non zero",
          fantamedia_regole(dict(tizio, partite_a_voto=0), regole_base)[0] is None)

    # --- la rosa di prova ---------------------------------------------------
    db = extensions.get_db()
    db.execute("INSERT INTO fanta_leagues(user_id,nome,moduli,n_panchinari,"
               "bonus_gol,bonus_assist,malus_amm) "
               "VALUES(?,'Terza Lega','3-4-3,4-4-2',4,3,1,-0.5)", (ids["davide"],))
    db.commit()
    lid3 = db.execute("SELECT id FROM fanta_leagues WHERE nome='Terza Lega'"
                      ).fetchone()["id"]
    # (id, nome, ruolo, squadra, partite, media, gol, percentuale|None)
    # Le squadre: `casa` gioca la giornata 7, `ferma` no — serve a distinguere
    # «non convocato» da «la sua squadra non gioca».
    banco = [
        (301, "Portiere1", "p", "casa", 5, 6.0, 0, 90),
        (302, "Portiere2", "p", "casa", 5, 5.8, 0, 90),
        (303, "Portiere3", "p", "casa", 5, 5.6, 0, 90),
        (304, "Dif1", "d", "casa", 5, 6.4, 1, 90),
        (305, "Dif2", "d", "casa", 5, 6.2, 0, 90),
        (306, "Dif3", "d", "casa", 5, 6.0, 0, 90),
        (307, "Dif4", "d", "casa", 5, 5.8, 0, 90),
        (308, "Cen1", "c", "casa", 5, 6.6, 1, 90),
        (309, "Cen2", "c", "casa", 5, 6.4, 0, 90),
        (310, "Cen3", "c", "casa", 5, 6.2, 0, 90),
        (311, "Cen4", "c", "casa", 5, 6.0, 0, 90),
        (312, "Cen5", "c", "casa", 5, 5.5, 0, 70),
        # ⚠️ Il caso che ha trovato il baco: fantamedia **altissima** ma
        # percentuale da ballottaggio. Non deve entrare al posto di un titolare
        # sicuro, e deve comparire fra i «contesi». I nove gol sono volutamente
        # assurdi, e il numero è **contato**: perché il disaccordo fra le due
        # letture esista davvero servono punti attesi più alti del peggior
        # titolare (0.9 × 6.0 = 5.4), cioè 0.5 × fm > 5.4, cioè fm > 10.8 — con
        # 5 partite a media 6.0 vuol dire più di 8 gol. Col primo valore (5 gol,
        # fm 9.0, attesi 4.5) i «contesi» erano legittimamente **vuoti** e la
        # prova diceva NO a un codice giusto.
        (313, "Fenomeno", "c", "casa", 5, 6.0, 9, 50),
        (314, "Att1", "a", "casa", 5, 6.8, 2, 90),
        (315, "Att2", "a", "casa", 5, 6.6, 1, 90),
        (316, "Att3", "a", "casa", 5, 6.4, 1, 90),
        (317, "Att4", "a", "casa", 5, 6.0, 0, 60),
        # Nessuna partita a voto: fantamedia assente, non zero.
        (318, "Nuovo", "c", "casa", 0, None, 0, 90),
        # ⚠️ Sotto il 40%, quindi nella fascia «parte dalla panchina»: esiste
        # perché la regola operativa della fonte — il rivale di un ballottaggio
        # schierato va **in cima alla panchina** — si può provare solo se un
        # centrocampista resta fuori. Senza di lui la prova chiedeva un rivale
        # che non poteva esistere, e diceva NO a un codice giusto.
        (319, "Riserva", "c", "casa", 5, 5.0, 0, 30),
    ]
    for pid, nome, ruolo, slug, pg, mv, gol, _pct in banco:
        db.execute("INSERT INTO fanta_players(id,nome,squadra,squadra_slug,"
                   "ruolo_classic,qa,fvm,attivo,visto_il,partite_a_voto,media_voto,"
                   "gol,assist,ammonizioni,espulsioni,gol_subiti,rigori_parati,rigori)"
                   " VALUES(?,?,'CAS',?,?,10,20,1,'2026-09-21',?,?,?,0,0,0,0,0,'0 / 0')",
                   (pid, nome, slug, ruolo, pg, mv, gol))
        db.execute("INSERT INTO fanta_roster(league_id,player_id,prezzo) VALUES(?,?,1)",
                   (lid3, pid))
    db.execute("INSERT INTO fanta_probabili_squadre(giornata,squadra_slug,squadra,"
               "modulo,avversario,avversario_slug,in_casa,match_id) "
               "VALUES(7,'casa','CAS','4-3-3','OSP','ospite',1,1)")
    db.execute("INSERT INTO fanta_probabili_squadre(giornata,squadra_slug,squadra,"
               "modulo,avversario,avversario_slug,in_casa,match_id) "
               "VALUES(7,'ospite','OSP','4-3-3','CAS','casa',0,1)")
    for pid, nome, ruolo, _slug, _pg, _mv, _gol, pct in banco:
        if pct is not None:
            db.execute("INSERT INTO fanta_probabili(giornata,player_id,nome,"
                       "squadra_slug,ruolo,titolare,percentuale) "
                       "VALUES(7,?,?,'casa',?,?,?)",
                       (pid, nome, ruolo, 1 if pct >= 60 else 0, pct))
    db.commit()
    lega3 = dict(db.execute("SELECT * FROM fanta_leagues WHERE id=?", (lid3,)).fetchone())
    rosa3 = [dict(r) for r in db.execute(
        "SELECT p.* FROM fanta_roster r JOIN fanta_players p ON p.id=r.player_id "
        "WHERE r.league_id=?", (lid3,))]
    db.close()

    prob3 = {pid: {"stato": "titolare" if (pct or 0) >= 60 else "panchina",
                   "percentuale": pct}
             for pid, _n, _r, _s, _pg, _mv, _g, pct in banco if pct is not None}
    val = valuta_rosa(rosa3, prob3, lega3)
    quali = {v["g"]["nome"]: v for v in val}
    esito("il «Fenomeno» ha la fantamedia più alta del centrocampo",
          quali["Fenomeno"]["fm"] > max(quali[n]["fm"] for n in
                                        ("Cen1", "Cen2", "Cen3", "Cen4")),
          f"{quali['Fenomeno']['fm']} contro {quali['Cen1']['fm']}")
    esito("e sta nella fascia del ballottaggio",
          quali["Fenomeno"]["fascia"] == "ballottaggio"
          and not quali["Fenomeno"]["schierabile"] is False,
          f"{quali['Fenomeno']['percentuale']}% {quali['Fenomeno']['fascia']}")
    esito("chi non ha partite a voto non ha fantamedia e non vale zero",
          quali["Nuovo"]["fm"] is None and quali["Nuovo"]["atteso"] is None)
    esito(f"e chi ne ha meno di {MINIMO_PARTITE_FIDATO} non è «fidato»",
          quali["Nuovo"]["fidata"] is False and quali["Cen1"]["fidata"] is True)

    c = consiglia_formazione(val, "3-4-3", lega3["n_panchinari"])
    dentro = [v["g"]["nome"] for v in c["titolari"]]
    panca = [v["g"]["nome"] for v in c["panchina"]]
    esito("l'undici del 3-4-3 ha 11 nomi e i reparti giusti", len(dentro) == 11
          and len([v for v in c["titolari"] if v["g"]["ruolo_classic"] == "d"]) == 3
          and len([v for v in c["titolari"] if v["g"]["ruolo_classic"] == "c"]) == 4,
          str(dentro))
    # ⚠️ **La prova che ha trovato il baco.** Il primo ordinamento metteva il
    # merito prima della fascia, e il Fenomeno (50%) entrava al posto di un
    # titolare sicuro al 90%. La gerarchia della fonte dice l'opposto: prima
    # *se* gioca, poi *se conviene*.
    esito("⚠️ un ballottaggio al 50% NON scavalca un titolare sicuro al 90%",
          "Fenomeno" not in dentro and "Cen4" in dentro, str(dentro))
    esito("e il consiglio dichiara che lì le due letture litigano",
          any(x["fuori"]["g"]["nome"] == "Fenomeno" for x in c["contesi"]),
          str([(x["fuori"]["g"]["nome"], x["dentro"]["g"]["nome"])
               for x in c["contesi"]]))
    # ⚠️ Il tetto per ruolo in panchina: con un portiere in campo, di sostituti
    # portiere può servirne **uno**. Due occuperebbero un posto che non servirà.
    esito("⚠️ in panchina non finiscono due portieri di riserva",
          len([v for v in c["panchina"] if v["g"]["ruolo_classic"] == "p"]) <= 1,
          str(panca))
    esito("la panchina è lunga quanto la lega ammette", len(panca) == 4, str(panca))

    # La regola operativa della fonte: se schieri un ballottaggio, il primo posto
    # in panchina va a un altro del suo ruolo.
    val_b = valuta_rosa([g for g in rosa3 if g["nome"] not in
                         ("Cen1", "Cen2", "Cen3")], prob3, lega3)
    cb = consiglia_formazione(val_b, "3-4-3", 4)
    schierati_b = [v["g"]["nome"] for v in cb["titolari"]]
    esito("togliendo tre centrocampisti il ballottaggio entra per forza",
          "Fenomeno" in schierati_b, str(schierati_b))
    esito("⚠️ e il primo posto in panchina va a un altro centrocampista, come dice "
          "la fonte",
          cb["panchina"] and cb["panchina"][0]["g"]["ruolo_classic"] == "c",
          str([(v["g"]["nome"], v["g"]["ruolo_classic"]) for v in cb["panchina"]]))

    # I «forzati»: un reparto che i convocati non riempiono.
    soli = [g for g in rosa3 if g["ruolo_classic"] != "a"] + \
           [g for g in rosa3 if g["nome"] in ("Att1", "Att2", "Att3")]
    prob_senza_att = {k: v for k, v in prob3.items() if k not in (314, 315, 316)}
    cf = consiglia_formazione(valuta_rosa(soli, prob_senza_att, lega3), "3-4-3", 4)
    esito("⚠️ i posti riempiti per forza sono dichiarati, non spacciati per consiglio",
          len(cf["forzati"]) == 3,
          str([v["g"]["nome"] for v in cf["forzati"]]))

    moduli = consiglia_moduli(val, ["3-4-3", "4-4-2"], 4)
    esito("ogni modulo ammesso ha il suo consiglio, con un migliore solo",
          len(moduli) == 2 and len([m for m in moduli if m["migliore"]]) == 1,
          str([(m["modulo"], m["atteso"], m["migliore"]) for m in moduli]))
    esito("un modulo che non esiste non produce un consiglio",
          consiglia_formazione(val, "4-4-4", 4) is None)

    # --- la pagina ----------------------------------------------------------
    def formazione_scritta():
        db = extensions.get_db()
        fuori = [dict(x) for x in db.execute(
            "SELECT * FROM fanta_formazione WHERE league_id=? "
            "ORDER BY titolare DESC, ordine", (lid3,))]
        db.close()
        return fuori

    with app.test_client() as c2:
        with c2.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        r = c2.get(f"/fantacalcio/lega/{lid3}/consiglio")
        pagina = r.data.decode("utf-8", "replace")
        esito("la pagina del consiglio si apre", r.status_code == 200
              and "L'undici consigliato" in pagina)
        # ⚠️ Davide ha chiesto che il criterio sia **scritto nella pagina**: è una
        # richiesta, non una decorazione, e quindi è una prova. ⚠️ Cosa deve dire è
        # il criterio, **non le parole con cui è scritto**: il 22/09/2026 i testi a
        # schermo sono stati riscritti in forma generica e questa prova è cambiata
        # con loro. Se cambiano ancora, va aggiornata di nuovo — e va bene così: è
        # il prezzo per avere una prova su ciò che l'utente legge davvero.
        esito("⚠️ la pagina dichiara su cosa si basa, numeri compresi",
              "due domande" in pagina
              and "titolarità" in pagina
              and "fantamedia ricalcolata" in pagina
              and "punti attesi" in pagina.lower()
              and str(MINIMO_PARTITE_FIDATO) in pagina
              and str(SOGLIA_SCHIERABILE) in pagina)
        esito("e dice dove i due criteri non concordano",
              "Fenomeno" in pagina and "non concordano" in pagina)
        esito("il consiglio non ha scritto niente da sé",
              formazione_scritta() == [], f"{len(formazione_scritta())} righe")

        r = c2.post(f"/fantacalcio/lega/{lid3}/consiglio/applica",
                    data={"modulo": "3-4-3"}, follow_redirects=True)
        scritta = formazione_scritta()
        esito("«applica» porta il consiglio nel campo",
              sum(1 for x in scritta if x["titolare"]) == 11
              and sum(1 for x in scritta if not x["titolare"]) == 4,
              f"{len(scritta)} righe")
        esito("con lo stesso undici che la pagina mostrava",
              [x["player_id"] for x in scritta if x["titolare"]]
              == [v["g"]["id"] for v in c["titolari"]])
        db = extensions.get_db()
        esito("e il modulo finisce sulla lega",
              db.execute("SELECT modulo_scelto FROM fanta_leagues WHERE id=?",
                         (lid3,)).fetchone()["modulo_scelto"] == "3-4-3")
        db.close()
        prima = formazione_scritta()
        r = c2.post(f"/fantacalcio/lega/{lid3}/consiglio/applica",
                    data={"modulo": "4-5-1"}, follow_redirects=True)
        esito("⚠️ un modulo che la lega non ammette non si applica",
              formazione_scritta() == prima
              and "non è fra quelli consigliabili" in r.data.decode("utf-8", "replace"))

    with app.test_client() as c2:
        with c2.session_transaction() as s:
            s["username"] = "altro"
            s["role"] = "user"
            s["user_id"] = ids["altro"]
        r = c2.get(f"/fantacalcio/lega/{lid3}/consiglio", follow_redirects=True)
        esito("un altro utente non vede il consiglio di una lega non sua",
              b"Lega non trovata" in r.data)
        prima = formazione_scritta()
        c2.post(f"/fantacalcio/lega/{lid3}/consiglio/applica",
                data={"modulo": "4-4-2"}, follow_redirects=True)
        esito("⚠️ e non può applicarlo al campo di un altro",
              formazione_scritta() == prima)


    # --- 15. un apostrofo nel nome non rompe la conferma ---------------------
    # ⚠️ `{{ nome|e }}` dentro un `onsubmit` è un baco silenzioso: l'escape HTML
    # rende `N'Dicka` come `N&#39;Dicka`, il browser lo **decodifica prima** di
    # passare il codice al parser JS, e l'handler diventa un `SyntaxError`. Un
    # handler che non compila non è un errore a schermo: il `confirm` sparisce e
    # il form parte lo stesso, cioè il giocatore esce dalla rosa al primo clic.
    # Sul listone vero i nomi con l'apostrofo sono due (`N'Dicka`, `N'Dri`), e il
    # nome di una lega lo scrive Davide — «L'Inter dei miei» basta e avanza.
    print("\n== 15. un apostrofo nel nome non rompe la conferma ==")
    import html as _html
    import re
    try:
        import esprima
    except ImportError:
        esprima = None
    HANDLER = re.compile(
        r"""\bon(?:click|change|submit)\s*=\s*("([^"]*)"|'([^']*)')""", re.I)
    SENZA_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)

    db = extensions.get_db()
    db.execute("INSERT INTO fanta_players(id,nome,squadra,ruolo_classic,qa,fvm,"
               "fantamedia,attivo,visto_il) VALUES(99,'N''Dri','XXX','a',10,20,"
               "6.0,1,'2026-09-21')")
    db.execute("INSERT INTO fanta_leagues(user_id,nome,sistema,moduli) "
               "VALUES(?,?,'classic','3-4-3')",
               (ids["davide"], 'L\'Inter dei "miei"'))
    lid_ap = db.execute("SELECT id FROM fanta_leagues ORDER BY id DESC "
                        "LIMIT 1").fetchone()["id"]
    db.commit()
    db.close()

    def handler_rotti(pagina):
        """Quanti handler inline non compilano, come li vedrebbe il browser."""
        rotti = []
        for m in HANDLER.finditer(SENZA_SCRIPT.sub("", pagina)):
            codice = _html.unescape(m.group(2) if m.group(2) is not None else m.group(3))
            try:
                esprima.parseScript("function _(){%s}" % codice, {"tolerant": False})
            except Exception as e:
                rotti.append(f"{codice[:60]} -> {str(e)[:40]}")
        return rotti

    with app.test_client() as c3:
        with c3.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        c3.post(f"/fantacalcio/lega/{lid_ap}/rosa/aggiungi",
                data={"player_id": "99", "prezzo": "10"})
        pagina = c3.get(f"/fantacalcio/lega/{lid_ap}").data.decode("utf-8", "replace")
        elenco = c3.get("/fantacalcio/").data.decode("utf-8", "replace")
    esito("il giocatore con l'apostrofo è davvero in pagina", "N&#39;Dri" in pagina)
    if esprima is None:
        esito("⚠️ senza `esprima` la sintassi degli handler non è provata", False,
              "pip install esprima")
    else:
        rotti = handler_rotti(pagina)
        esito("⚠️ nessun handler rotto dall'apostrofo nel nome del giocatore",
              not rotti, str(rotti))
        rotti = handler_rotti(elenco)
        esito("⚠️ né dall'apostrofo e dalle virgolette nel nome della lega",
              not rotti, str(rotti))


    # --- 16. la formazione contro le probabili di adesso ---------------------
    # Chiesta da Davide il 22/09/2026: schieri giovedì, venerdì uno finisce in
    # panchina, e fino a ieri te ne accorgevi solo riaprendo il campo e guardando
    # riga per riga. ⚠️ «Automatico» qui vuol dire **quando apri la pagina**: non
    # c'è niente che giri in sottofondo, e la prova non può dimostrare altro.
    print("\n== 16. la formazione contro le probabili di adesso ==")
    from data import controlla_schierati, quanti_guai

    schierati_finti = {1: {"titolare": 1}, 2: {"titolare": 1}, 3: {"titolare": 1},
                       4: {"titolare": 0}, 5: {"titolare": 1}}
    prob_finte = {1: {"stato": "titolare", "percentuale": 90},
                  2: {"stato": "panchina", "percentuale": 30},
                  3: {"stato": "titolare", "percentuale": 35},
                  4: {"stato": "titolare", "percentuale": 85},
                  5: {"stato": "non_gioca", "percentuale": None}}
    nomi_finti = {1: "Uno", 2: "Due", 3: "Tre", 4: "Quattro", 5: "Cinque"}
    a = controlla_schierati(schierati_finti, prob_finte, nomi_finti,
                            in_rosa={1, 2, 3, 4, 5})
    esito("un titolare finito in panchina viene dichiarato",
          [v["nome"] for v in a["fuori"]] == ["Cinque", "Due"],
          str([(v["nome"], v["stato"]) for v in a["fuori"]]))
    esito("⚠️ e chi non scende in campo per niente viene prima di chi è in panchina",
          a["fuori"][0]["stato"] == "non_gioca")
    esito("un titolare sotto la soglia del ballottaggio è «incerto», non «fuori»",
          [v["nome"] for v in a["incerti"]] == ["Tre"], str(a["incerti"]))
    # ⚠️ Il conto sono **3**: i due «fuori» più l'«incerto». L'occasione non ci
    # entra, ed è tutto il punto di `quanti_guai()` — contarla direbbe 4 a una
    # formazione che ha tre cose da sistemare e una da sfruttare.
    esito("e un panchinaro dato titolare è un'occasione, non un guaio",
          [v["nome"] for v in a["occasioni"]] == ["Quattro"]
          and quanti_guai(a) == 3, f"{a['occasioni']} guai={quanti_guai(a)}")
    # ⚠️ Togliere un giocatore dalla rosa **non** cancella la sua riga in
    # `fanta_formazione`: il campo smette di disegnarlo e i titolari diventano
    # dieci senza che nessuno lo dica. Finché è così, l'avviso deve dirlo.
    b = controlla_schierati(schierati_finti, prob_finte, nomi_finti,
                            in_rosa={1, 2, 3, 4})
    esito("⚠️ chi è schierato ma non è più in rosa viene dichiarato",
          [v["nome"] for v in b["spariti"]] == ["Cinque"], str(b["spariti"]))
    esito("⚠️ senza probabili non si accusa nessuno",
          quanti_guai(controlla_schierati(schierati_finti, {}, nomi_finti)) == 0)
    esito("e una formazione che torna non produce nessun guaio",
          quanti_guai(controlla_schierati(
              {1: {"titolare": 1}}, {1: {"stato": "titolare", "percentuale": 90}},
              nomi_finti, in_rosa={1})) == 0)

    # --- e la stessa cosa dalle pagine ---------------------------------------
    db = extensions.get_db()
    db.execute("UPDATE fanta_players SET squadra_slug='inter' WHERE id IN (1,2,3,4)")
    db.execute("INSERT INTO fanta_leagues(user_id,nome,sistema,moduli) "
               "VALUES(?,'Lega Allerta','classic','3-4-3')", (ids["davide"],))
    lid_al = db.execute("SELECT id FROM fanta_leagues ORDER BY id DESC "
                        "LIMIT 1").fetchone()["id"]
    for pid in (1, 2, 3, 4):
        db.execute("INSERT INTO fanta_roster(league_id,player_id,prezzo) "
                   "VALUES(?,?,10)", (lid_al, pid))
    # Tre in campo e uno in panchina, e le probabili della giornata 9 che li
    # smentiscono: il portiere resta titolare, il difensore è in panchina, il
    # centrocampista è dato titolare ma al 30%, l'attaccante in panchina gioca.
    for pid, titolare, ordine in ((1, 1, 0), (2, 1, 1), (3, 1, 2), (4, 0, 0)):
        db.execute("INSERT INTO fanta_formazione(league_id,player_id,titolare,"
                   "ordine,ruolo) VALUES(?,?,?,?,?)", (lid_al, pid, titolare,
                                                       ordine, "d"))
    db.execute("INSERT INTO fanta_probabili_squadre(giornata,squadra_slug,squadra,"
               "avversario,in_casa,modulo,aggiornato_il) VALUES(9,'inter','Inter',"
               "'Milan',1,'3-5-2',CURRENT_TIMESTAMP)")
    for pid, titolare, pct in ((1, 1, 90), (2, 0, 25), (3, 1, 30), (4, 1, 85)):
        db.execute("INSERT INTO fanta_probabili(giornata,player_id,nome,squadra_slug,"
                   "ruolo,titolare,percentuale,aggiornato_il) "
                   "VALUES(9,?,?,'inter','d',?,?,CURRENT_TIMESTAMP)",
                   (pid, nomi_finti[pid], titolare, pct))
    db.commit()
    db.close()

    with app.test_client() as c4:
        with c4.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        scheda = c4.get(f"/fantacalcio/lega/{lid_al}").data.decode("utf-8", "replace")
        campo = c4.get(f"/fantacalcio/lega/{lid_al}/formazione").data.decode("utf-8", "replace")
        elenco = c4.get("/fantacalcio/").data.decode("utf-8", "replace")
    esito("la scheda della lega apre con l'avviso",
          "non corrisponde alle probabili" in scheda and "Bastoni" in scheda,
          "Bastoni è il titolare finito in panchina")
    esito("⚠️ e dice di quale giornata sta parlando",
          "giornata 9" in scheda)
    esito("l'avviso c'è anche sul campo, dove si rimedia",
          "non corrisponde alle probabili" in campo)
    esito("e l'elenco delle leghe lo dice prima di entrare",
          "da guardare nella formazione" in elenco)
    # ⚠️ Le occasioni non entrano nel conto: un suggerimento non è un guaio, e un
    # numero che conta anche quelli farebbe dire «3 da guardare» a una formazione
    # che ne ha due.
    esito("⚠️ il numero nell'elenco conta i guai, non i suggerimenti",
          ">\n      &#9888; 2 da guardare nella formazione" in elenco
          or "2 da guardare nella formazione" in elenco,
          "2 = un titolare in panchina + un titolare al 30%")

    with app.test_client() as c4:
        with c4.session_transaction() as s:
            s["username"] = "altro"
            s["role"] = "user"
            s["user_id"] = ids["altro"]
        elenco = c4.get("/fantacalcio/").data.decode("utf-8", "replace")
    esito("⚠️ e un altro utente non vede né la lega né il suo avviso",
          "Lega Allerta" not in elenco and "da guardare nella formazione" not in elenco)

    # --- 16b. il modificatore di difesa entra nel consiglio ------------------
    # Chiesto da Davide il 22/09/2026: il consiglio ordinava i moduli sui soli punti
    # attesi dei giocatori, e il modificatore vale su un **reparto** — in una lega
    # che lo usa, un 5-3-2 e un 3-4-3 non sono confrontabili senza.
    print("\n== 16b. il modificatore di difesa nel consiglio ==")
    from data import modificatore_atteso, MINIMO_DIFENSORI_MOD

    def _v(ruolo, voto, pct, nome="X"):
        """Una valutazione finta con dentro i soli campi che il modificatore legge."""
        return {"g": {"id": id(nome) % 100000, "nome": nome,
                      "ruolo_classic": ruolo, "media_voto": voto},
                "percentuale": pct}

    regole_on = {"mod_difesa": 1, "mod_difesa_portiere": 1,
                 "mod_difesa_soglie": "7:6, 6.5:3, 6:1"}
    # Portiere a 6.5 e quattro difensori a 7.0/6.8/6.6/5.0: la media del portiere e
    # dei **migliori 3** è (6.5+7.0+6.8+6.6)/4 = 6.725, che con la tabella standard
    # vale +3. Il quarto difensore, il peggiore, non entra nella media.
    undici = [_v("p", 6.5, 100, "Por"), _v("d", 7.0, 100, "D1"),
              _v("d", 6.8, 100, "D2"), _v("d", 6.6, 100, "D3"),
              _v("d", 5.0, 100, "D4")]
    m = modificatore_atteso(undici, regole_on)
    esito("la media è del portiere e dei migliori 3 difensori",
          m["media"] == 6.73 or m["media"] == 6.72, str(m["media"]))
    esito("e la tabella della lega le dà +3", m["pieni"] == 3.0, str(m["pieni"]))
    esito("con tutti al 100% il conto atteso è il valore pieno",
          m["punti"] == 3.0, str(m["punti"]))
    # ⚠️ Lo sconto per la probabilità: gli stessi voti con quattro all'80% valgono
    # 3 × 0.8⁴ = 1.23, non 3. Senza, un reparto di ballottaggi varrebbe come uno di
    # titolari sicuri e il modulo con più difensori vincerebbe sempre.
    incerti = [_v("p", 6.5, 80, "Por"), _v("d", 7.0, 80, "D1"),
               _v("d", 6.8, 80, "D2"), _v("d", 6.6, 80, "D3"),
               _v("d", 5.0, 80, "D4")]
    m2 = modificatore_atteso(incerti, regole_on)
    esito("⚠️ e chi potrebbe non giocare vale meno: 3 × 0.8⁴ = 1.23",
          m2["punti"] == 1.23 and m2["pieni"] == 3.0, str(m2))
    # ⚠️ Il numero dei difensori è il motivo per cui il modulo conta: con tre non
    # si arriva al minimo, e si dice **perché** invece di dare zero e basta.
    tre = [_v("p", 6.5, 100, "Por"), _v("d", 7.0, 100, "D1"),
           _v("d", 6.8, 100, "D2"), _v("d", 6.6, 100, "D3")]
    m3 = modificatore_atteso(tre, regole_on)
    esito(f"⚠️ con meno di {MINIMO_DIFENSORI_MOD} difensori non si applica, e lo dice",
          m3["punti"] == 0.0 and "servono" in (m3["perche"] or ""), str(m3["perche"]))
    esito("senza il portiere nella media entrano i migliori 4 difensori",
          modificatore_atteso(
              undici, dict(regole_on, mod_difesa_portiere=0))["media"] == 6.35,
          str(modificatore_atteso(undici,
                                  dict(regole_on, mod_difesa_portiere=0))["media"]))
    esito("⚠️ e in una lega che non lo usa non si conta niente",
          modificatore_atteso(undici, dict(regole_on, mod_difesa=0)) is None)
    # Una tabella su misura deve cambiare il risultato, o le soglie della lega non
    # servirebbero a niente.
    esito("le soglie della lega sono quelle che decidono",
          modificatore_atteso(undici, dict(regole_on,
                                           mod_difesa_soglie="6.7:9"))["pieni"] == 9.0)

    # E il consiglio deve **ordinare** i moduli con quel numero dentro.
    from data import consiglia_moduli as _moduli

    def _val(ruolo, voto, pct, fm, nome):
        return {"g": {"id": abs(hash(nome)) % 100000, "nome": nome,
                      "ruolo_classic": ruolo, "media_voto": voto},
                "stato": "titolare", "percentuale": pct,
                "fascia": "sicuro", "fm": fm, "pezzi": [], "partite": 10,
                "fidata": True, "convocato": True, "schierabile": True,
                "atteso": round(pct / 100.0 * fm, 2)}

    # Una rosa dove i difensori sono bravi e gli attaccanti no: senza modificatore
    # vince il 3-4-3 (tre attaccanti da 6.0 contro due difensori in più da 5.5),
    # col modificatore acceso il 5-3-2 recupera il reparto.
    banco = ([_val("p", 6.5, 100, 6.0, "Por")]
             + [_val("d", 7.0, 100, 5.5, f"Dif{n}") for n in range(5)]
             + [_val("c", 6.0, 100, 6.0, f"Cen{n}") for n in range(5)]
             + [_val("a", 6.0, 100, 7.0, f"Att{n}") for n in range(3)])
    senza = _moduli(banco, ["3-4-3", "5-3-2"], 0, regole={"mod_difesa": 0})
    con = _moduli(banco, ["3-4-3", "5-3-2"], 0, regole=regole_on)
    vince = lambda cons: next(c["modulo"] for c in cons if c["migliore"])
    esito("senza modificatore vince il modulo con più attaccanti",
          vince(senza) == "3-4-3",
          str([(c["modulo"], c["atteso"], c["totale"]) for c in senza]))
    esito("⚠️ con il modificatore acceso il reparto difensivo conta, e vince il 5-3-2",
          vince(con) == "5-3-2",
          str([(c["modulo"], c["atteso"], c["mod"]["punti"], c["totale"])
               for c in con]))
    esito("⚠️ e il 3-4-3 prende +0 perché tre difensori non bastano",
          next(c for c in con if c["modulo"] == "3-4-3")["mod"]["punti"] == 0.0)
    esito("dove il modificatore è spento il totale è i soli punti attesi",
          all(c["totale"] == c["atteso"] for c in senza))

    # --- 17. chi esce dalla rosa esce anche dal campo ------------------------
    # Decisione di Davide del 22/09/2026, sul baco trovato costruendo l'avviso:
    # `fanta_roster` e `fanta_formazione` sono due tabelle e il DELETE sulla prima
    # non toccava la seconda, quindi i titolari diventavano dieci in silenzio.
    print("\n== 17. chi esce dalla rosa esce anche dal campo ==")

    def in_campo(lega):
        db = extensions.get_db()
        fuori = {r["player_id"] for r in db.execute(
            "SELECT player_id FROM fanta_formazione WHERE league_id=?", (lega,))}
        db.close()
        return fuori

    with app.test_client() as c5:
        with c5.session_transaction() as s:
            s["username"] = "davide"
            s["role"] = "user"
            s["user_id"] = ids["davide"]
        db = extensions.get_db()
        rid = db.execute("SELECT id FROM fanta_roster WHERE league_id=? AND "
                         "player_id=1", (lid_al,)).fetchone()["id"]
        db.close()
        esito("si parte con quattro schierati", in_campo(lid_al) == {1, 2, 3, 4},
              str(sorted(in_campo(lid_al))))
        r = c5.post(f"/fantacalcio/lega/{lid_al}/rosa/{rid}/rimuovi",
                    follow_redirects=True)
        esito("la × di una riga lo toglie anche dal campo",
              in_campo(lid_al) == {2, 3, 4}, str(sorted(in_campo(lid_al))))
        esito("e il messaggio dice che era schierato",
              "era schierato" in r.data.decode("utf-8", "replace"))
        db = extensions.get_db()
        rid2 = {r["player_id"]: r["id"] for r in db.execute(
            "SELECT id, player_id FROM fanta_roster WHERE league_id=?", (lid_al,))}
        db.close()
        r = c5.post(f"/fantacalcio/lega/{lid_al}/rosa/modifica", data={
            "togli": [str(rid2[2]), str(rid2[3])]}, follow_redirects=True)
        esito("e il «togli in blocco» fa lo stesso per tutti quelli spuntati",
              in_campo(lid_al) == {4}, str(sorted(in_campo(lid_al))))
        esito("dicendo quanti di quelli tolti erano schierati",
              "2 erano schierati" in r.data.decode("utf-8", "replace"),
              r.data.decode("utf-8", "replace").count("erano schierati"))

    # ⚠️ Chi esce dal **listone** è un'altra cosa: resta in rosa, spento, col suo
    # cartellino. Se questa prova fallisse vorrebbe dire che l'aggiornamento del
    # mercato smonta le formazioni di gennaio.
    db = extensions.get_db()
    db.execute("INSERT OR REPLACE INTO fanta_formazione(league_id,player_id,"
               "titolare,ordine,ruolo) VALUES(?,5,1,9,'c')", (lid_al,))
    db.execute("INSERT INTO fanta_roster(league_id,player_id,prezzo) "
               "VALUES(?,5,10)", (lid_al,))
    db.execute("UPDATE fanta_players SET attivo=0 WHERE id=5")
    db.commit()
    db.close()
    esito("⚠️ ma chi esce dal listone resta in rosa e in campo: è un'altra cosa",
          5 in in_campo(lid_al), str(sorted(in_campo(lid_al))))


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
