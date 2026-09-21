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
