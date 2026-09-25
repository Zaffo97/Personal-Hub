#!/usr/bin/env python
"""Le prove della Fantacalcio 2 (§4.6). Non tocca `hub.db` né la rete.

    python scripts/prova_fantacalcio2.py [--tieni]

Ogni prova gira su un DB **suo**, creato da `init_db()` in una cartella temporanea,
come `prova_fantacalcio.py`. Gli Excel sono **costruiti qui**, con la stessa forma di
quelli veri (titolo sopra, intestazione con `Id`, foglio `Ceduti`): i file veri non
vanno nel repository, e una prova che dipende da un download non è ripetibile.
Il calendario e la classifica sono **finti** anche loro: una prova che va in rete
fallisce a seconda di come va la linea, e consuma le chiamate della chiave.

Cosa dimostra, in ordine:

- che i due Excel si **riconoscono dal contenuto** e non dall'ordine o dal nome, che
  l'intestazione si cerca, e che un file sbagliato viene rifiutato
- che l'import **spegne e non cancella** (ceduti e usciti), che la rosa che li nomina
  sopravvive, che un file troppo corto viene rifiutato, e che rieseguirlo non cambia
  niente
- che **il listone della prima sezione non si tocca**
- che le squadre di football-data si abbinano **solo** quando il candidato è uno, e
  che l'ora italiana regge anche senza `tzdata`
- che le leghe restano **di chi le ha create** (§1.1), anche passando dalla rosa
- che il consiglio mette in fondo chi **non gioca** e ordina gli altri per
  fantamedia, e che «applica» passa dalla stessa validazione del campo
- che le pagine si aprono, e che nessun `<script>` e nessun handler inline ha un
  `SyntaxError` — anche con un apostrofo nel nome
"""
import argparse
import html as _html
import io
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile

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


# ── Gli Excel finti ──────────────────────────────────────────────────────────

def _cella(ref, valore):
    if isinstance(valore, (int, float)):
        return f'<c r="{ref}"><v>{valore}</v></c>'
    testo = _html.escape(str(valore))
    return f'<c r="{ref}" t="inlineStr"><is><t>{testo}</t></is></c>'


def _foglio(righe):
    corpo = []
    for i, riga in enumerate(righe, 1):
        celle = "".join(_cella(f"{chr(65 + j)}{i}", v) for j, v in enumerate(riga)
                        if v is not None)
        corpo.append(f'<row r="{i}">{celle}</row>')
    return ('<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.'
            'openxmlformats.org/spreadsheetml/2006/main"><sheetData>' +
            "".join(corpo) + "</sheetData></worksheet>")


def xlsx(fogli):
    """Un `.xlsx` minimo da `{nome: [righe]}`: bytes, come arriva da un upload."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        nomi = list(fogli)
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://'
                   'schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.'
                   'org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.'
                   'org/officeDocument/2006/relationships"><sheets>' +
                   "".join(f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>'
                           for i, n in enumerate(nomi, 1)) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/relationships">' +
                   "".join(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml" '
                           'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                           'relationships/worksheet"/>' for i in range(1, len(nomi) + 1)) +
                   "</Relationships>")
        for i, n in enumerate(nomi, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _foglio(fogli[n]))
    return buf.getvalue()


TESTA_Q = ["Id", "R", "RM", "Nome", "Squadra", "Qt.A", "Qt.I", "Diff.", "Qt.A M",
           "Qt.I M", "Diff.M", "FVM", "FVM M"]
TESTA_S = ["Id", "R", "Rm", "Nome", "Squadra", "Pv", "Mv", "Fm", "Gf", "Gs", "Rp",
           "Rc", "R+", "R-", "Ass", "Amm", "Esp", "Au"]

# (id, ruolo, mantra, nome, squadra, qa, fvm) — una rosa che basta a un 4-4-2 con
# panchina, divisa fra quattro squadre, più un nome con l'apostrofo.
GIOCATORI = [
    (1, "P", "Por", "Portiere Uno", "Roma", 15, 60),
    (2, "P", "Por", "Portiere Due", "Lazio", 8, 20),
    (11, "D", "Dc", "Dif Uno", "Roma", 18, 120), (12, "D", "Dc", "Dif Due", "Roma", 12, 80),
    (13, "D", "Dd;E", "Dif Tre", "Lazio", 10, 60), (14, "D", "Dc", "Dif Quattro", "Lazio", 9, 40),
    (15, "D", "Dc", "Dif Cinque", "Como", 8, 30),
    (21, "C", "M;C", "Cen Uno", "Roma", 20, 150), (22, "C", "C", "Cen Due", "Lazio", 15, 90),
    (23, "C", "C;T", "Cen Tre", "Como", 12, 70), (24, "C", "M", "Cen Quattro", "Como", 10, 50),
    (25, "C", "C", "N'Dri", "Venezia", 9, 30),
    (31, "A", "Pc", "Att Uno", "Roma", 30, 250), (32, "A", "Pc", "Att Due", "Venezia", 22, 160),
    (33, "A", "A", "Att Tre", "Lazio", 14, 70),
]
# id -> (Pv, Mv, Fm, Gf, Gs, Rp, Rc, R+, R-, Ass, Amm, Esp, Au)
STAT = {g[0]: (5, 6.2, 6.5, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0) for g in GIOCATORI}
STAT[1] = (5, 6.4, 5.8, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0)
STAT[31] = (5, 7.1, 10.6, 6, 0, 0, 2, 1, 1, 0, 1, 0, 0)
STAT[32] = (5, 6.0, 7.0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 1)     # un autogol
STAT[33] = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)        # mai a voto
CEDUTO = (99, "C", "C", "Ceduto Tizio", "Roma", 5, 10)


def file_quotazioni(giocatori=GIOCATORI, ceduti=(CEDUTO,), titolo=True):
    def righe(elenco):
        return ([["Quotazioni Fantacalcio Stagione 2026 27"]] if titolo else []) + \
            [TESTA_Q] + [[g[0], g[1], g[2], g[3], g[4], g[5], g[5], 0, g[5], g[5], 0,
                          g[6], g[6]] for g in elenco]
    return xlsx({"Tutti": righe(giocatori), "Ceduti": righe(ceduti)})


def file_statistiche(giocatori=GIOCATORI):
    righe = [["Statistiche Fantacalcio Stagione 2026 27"], TESTA_S]
    for g in giocatori:
        s = STAT.get(g[0], (0,) * 13)
        righe.append([g[0], g[1], g[2], g[3], g[4]] + list(s))
    return xlsx({"Tutti": righe})


# Il calendario finto: giornata 6, con **Como–Venezia rinviata**.
PARTITE = [
    {"match_id": 1, "giornata": 6, "stato": "TIMED", "utc": "2026-10-10T13:00:00Z",
     "inizio": "2026-10-10 15:00", "casa": "Roma", "fuori": "Lazio"},
    {"match_id": 2, "giornata": 6, "stato": "POSTPONED", "utc": "2026-10-11T13:00:00Z",
     "inizio": "2026-10-11 15:00", "casa": "Como 1907", "fuori": "Venezia FC"},
    {"match_id": 3, "giornata": 7, "stato": "SCHEDULED", "utc": "2026-10-17T13:00:00Z",
     "inizio": "2026-10-17 15:00", "casa": "Lazio", "fuori": "Roma"},
    {"match_id": 4, "giornata": 5, "stato": "FINISHED", "utc": "2026-09-20T13:00:00Z",
     "inizio": "2026-09-20 15:00", "casa": "Venezia FC", "fuori": "Roma"},
]
# I campi che `fanta2_fonti.partite()` mette in ogni voce e che qui non contano.
for _p in PARTITE:
    for _k in ("casa_id", "fuori_id", "gol_casa", "gol_fuori", "aggiornata"):
        _p.setdefault(_k, None)
CLASSIFICA = [
    {"squadra": "Roma", "posizione": 1, "punti": 13, "giocate": 5, "gol_fatti": 14, "gol_subiti": 3},
    {"squadra": "Lazio", "posizione": 3, "punti": 10, "giocate": 5, "gol_fatti": 8, "gol_subiti": 3},
    {"squadra": "Como 1907", "posizione": 9, "punti": 7, "giocate": 5, "gol_fatti": 6, "gol_subiti": 6},
    {"squadra": "Venezia FC", "posizione": 18, "punti": 2, "giocate": 5, "gol_fatti": 3, "gol_subiti": 11},
]


def prove(dove):
    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()
    # ⚠️ Mai i download veri: entrando nella sezione gli Excel si importano e si
    # cancellano. Una cartella della prova, vuota finché la sezione 10 non la riempie.
    scaricati = os.path.join(dove, "download")
    os.makedirs(scaricati)
    os.environ["FANTA2_CARTELLA_DOWNLOAD"] = scaricati

    # ⚠️ Niente rete, mai: senza chiave le pagine non aggiornano il calendario da
    # sole, e le due letture dell'API **sollevano** se qualcuno le chiama per caso.
    # I blocchi che provano l'aggiornamento le sostituiscono da sé.
    import fanta2_fonti as F
    import fanta2 as G
    F.chiave_api = lambda: None

    def _niente_rete(*a, **k):
        raise AssertionError("la prova non deve leggere la rete")
    F.partite = F.classifica = _niente_rete

    db = extensions.get_db()
    for nome in ("davide", "altro"):
        db.execute("INSERT INTO users(username,password,display_name,role) "
                   "VALUES(?,'x',?,'user')", (nome, nome.title()))
    # La prima sezione ha il suo listone: deve restare com'è.
    db.execute("INSERT INTO fanta_players(id,nome,squadra,ruolo_classic,attivo) "
               "VALUES(1,'Primo Listone','ROM','p',1)")
    db.commit()
    ids = {r["username"]: r["id"] for r in db.execute("SELECT id, username FROM users")}
    db.close()

    # --- 1. i due file ---------------------------------------------------------
    print("\n== 1. i due Excel si riconoscono dal contenuto ==")
    fq, fs, pr = G.leggi_i_due_file(file_statistiche(), file_quotazioni())
    esito("scambiati nel form, si riconoscono lo stesso", fq and fs and not pr, str(pr))
    q, pq = F.quotazioni(fq)
    esito("il foglio Ceduti entra, segnato", q.get(99, {}).get("ceduto") == 1
          and q[1]["ceduto"] == 0)
    esito("il ruolo Mantra prende la forma della prima sezione",
          q[13]["ruolo_mantra"] == "dd|e", q[13]["ruolo_mantra"])
    q2, _ = F.quotazioni(F.leggi_xlsx(file_quotazioni(titolo=False)))
    esito("⚠️ l'intestazione si cerca: senza la riga del titolo legge lo stesso",
          len(q2) == len(q))
    s, _ = F.statistiche(fs)
    esito("i rigori diventano «segnati / tirati»", s[31]["rigori"] == "1 / 2",
          s[31]["rigori"])
    esito("e l'autogol c'è", s[32]["autogol"] == 1)
    _, _, pr = G.leggi_i_due_file(file_quotazioni(), file_quotazioni())
    esito("⚠️ due file di quotazioni vengono rifiutati", bool(pr), str(pr))
    _, _, pr = G.leggi_i_due_file(b"non sono un excel", file_quotazioni())
    esito("⚠️ un file che non è un .xlsx viene rifiutato", bool(pr), str(pr))
    altro = xlsx({"Foglio1": [["Nome", "Cognome"], ["a", "b"]]})
    _, _, pr = G.leggi_i_due_file(altro, file_quotazioni())
    esito("⚠️ e anche un .xlsx che non è di fantacalcio.it", bool(pr), str(pr))

    # --- 2. l'import -----------------------------------------------------------
    print("\n== 2. l'import spegne e non cancella ==")
    db = extensions.get_db()
    r = G.importa_listone(db, fq, fs)
    esito("il primo import scrive tutti", r["ok"] and len(r["nuovi"]) == len(GIOCATORI) + 1,
          str(r["motivo"]))
    riga = db.execute("SELECT attivo, ceduto FROM fanta2_players WHERE id=99").fetchone()
    esito("⚠️ il ceduto entra spento", riga["attivo"] == 0 and riga["ceduto"] == 1)
    r = G.importa_listone(db, fq, fs)
    esito("rieseguito non cambia niente", r["ok"] and not r["nuovi"] and not r["cambiati"],
          f"nuovi {len(r['nuovi'])} cambiati {r['cambiati']}")
    esito("⚠️ il listone della prima sezione non si tocca",
          db.execute("SELECT COUNT(*) FROM fanta_players").fetchone()[0] == 1)
    db.close()

    # --- 3. squadre e ore ------------------------------------------------------
    print("\n== 3. squadre di football-data e ora italiana ==")
    abb, sole = F.abbina_squadre(["Como 1907", "Venezia FC", "Roma", "Inter"],
                                 {"como", "venezia", "roma", "lazio"})
    esito("Como 1907 e Venezia FC si abbinano", abb.get("Como 1907") == "como"
          and abb.get("Venezia FC") == "venezia")
    esito("⚠️ una squadra che non c'è resta non abbinata, senza indovinare",
          sole == ["Inter"], str(sole))
    _, sole = F.abbina_squadre(["Hellas Verona"], {"hellas-verona", "verona"})
    esito("e con due candidati vince quello esatto, non il primo",
          F.abbina_squadre(["Hellas Verona"], {"hellas-verona", "verona"})[0]
          .get("Hellas Verona") == "hellas-verona")
    salvata = F._ROMA
    F._ROMA = None
    esito("senza tzdata: ottobre è ora legale", F.ora_italiana("2026-10-10T13:00:00Z")
          == "2026-10-10 15:00")
    esito("dicembre no", F.ora_italiana("2026-12-10T13:00:00Z") == "2026-12-10 14:00")
    esito("⚠️ e il cambio cade alle 01:00 UTC dell'ultima domenica di ottobre",
          F.ora_italiana("2026-10-25T00:30:00Z") == "2026-10-25 02:30"
          and F.ora_italiana("2026-10-25T01:30:00Z") == "2026-10-25 02:30")
    F._ROMA = salvata

    # --- 4. il calendario ------------------------------------------------------
    print("\n== 4. il calendario ==")
    db = extensions.get_db()
    r = G.aggiorna_calendario(db)
    esito("senza chiave non parte, e lo dice", not r["ok"] and "chiave" in r["motivo"])
    F.chiave_api = lambda: "finta"
    F.partite = lambda chiave: PARTITE
    F.classifica = lambda chiave: CLASSIFICA
    r = G.aggiorna_calendario(db)
    esito("con la chiave scrive partite e classifica",
          r["ok"] and r["partite"] == 4 and not r["non_abbinate"], str(r))
    esito("la giornata corrente è la prima con partite da giocare (la 6)",
          G.giornata_corrente(db) == 6)
    sc = G.scadenza(db, 6)
    esito("la scadenza è la prima partita con l'ora esatta",
          sc and sc["inizio"] == "2026-10-10 15:00" and sc["senza_ora"] == 0, str(sc))
    esito("⚠️ una giornata solo SCHEDULED non ha scadenza: l'ora non è certa",
          G.scadenza(db, 7) is None)
    F.chiave_api = lambda: None
    F.partite = F.classifica = _niente_rete
    db.close()

    # --- 5. di chi sono le leghe --------------------------------------------------
    print("\n== 5. le leghe sono di chi le crea ==")
    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    def cliente(nome):
        c = app.test_client()
        with c.session_transaction() as s:
            s["username"] = nome
            s["role"] = "user"
            s["user_id"] = ids[nome]
        return c

    c = cliente("davide")
    c.post("/fantacalcio2/lega/salva", data={
        "nome": "L'Inter dei \"miei\"", "moduli": "4-4-2,3-4-3", "n_panchinari": "7",
        "bonus_gol": "3", "malus_autogol": "-2"})
    db = extensions.get_db()
    lid = db.execute("SELECT id FROM fanta2_leagues").fetchone()["id"]
    esito("la lega nasce nelle tabelle della Fantacalcio 2",
          db.execute("SELECT COUNT(*) FROM fanta_leagues").fetchone()[0] == 0)
    db.close()
    # La rosa: metà dall'incolla (anteprima e conferma, come da pagina), metà dalla
    # ricerca uno per volta. Le righe della conferma si mandano come le manda il
    # form: `riga_N` spuntata e `pid_N` col giocatore scelto.
    incollati = [g[0] for g in GIOCATORI[:8]]
    dati = {}
    for n, pid in enumerate(incollati):
        dati[f"riga_{n}"], dati[f"pid_{n}"], dati[f"prezzo_{n}"] = "1", str(pid), "5"
    dati["riga_99"], dati["pid_99"] = "1", "123456"          # un id inventato
    c.post(f"/fantacalcio2/lega/{lid}/rosa/incolla/conferma", data=dati)
    for g in GIOCATORI[8:] + [CEDUTO]:
        c.post(f"/fantacalcio2/lega/{lid}/rosa/aggiungi",
               data={"player_id": str(g[0]), "prezzo": "3"})
    db = extensions.get_db()
    in_rosa = db.execute("SELECT COUNT(*) FROM fanta2_roster WHERE league_id=?",
                         (lid,)).fetchone()[0]
    db.close()
    esito("la rosa entra intera, e l'id inventato no", in_rosa == len(GIOCATORI) + 1,
          f"{in_rosa} in rosa")
    anteprima = c.post(f"/fantacalcio2/lega/{lid}/rosa/incolla",
                       data={"testo": "Att Uno\nNessuno Così"})
    esito("l'anteprima dell'incolla riconosce chi c'è e dichiara chi no",
          anteprima.status_code == 200 and "Att Uno" in anteprima.data.decode("utf-8"))

    a = cliente("altro")
    r = a.get(f"/fantacalcio2/lega/{lid}", follow_redirects=True)
    esito("un altro utente non vede la lega", b"Lega non trovata" in r.data)
    a.post("/fantacalcio2/lega/salva", data={"lega_id": lid, "nome": "presa"})
    a.post(f"/fantacalcio2/lega/{lid}/elimina")
    a.post(f"/fantacalcio2/lega/{lid}/rosa/svuota", data={"ruolo": "tutti"})
    a.post(f"/fantacalcio2/lega/{lid}/rosa/modifica", data={"togli": ["1", "2", "3"]})
    db = extensions.get_db()
    lega = db.execute("SELECT nome FROM fanta2_leagues WHERE id=?", (lid,)).fetchone()
    resta = db.execute("SELECT COUNT(*) FROM fanta2_roster WHERE league_id=?",
                       (lid,)).fetchone()[0]
    db.close()
    esito("⚠️ né la rinomina, né la cancella, né le svuota o corregge la rosa",
          lega and lega["nome"] != "presa" and resta == in_rosa)
    esito("e la sua ricerca nel listone non vede le rose di Davide",
          b"in rosa" not in a.get("/fantacalcio2/listone").data)

    # --- 6. il consiglio -----------------------------------------------------------
    print("\n== 6. il consiglio senza la titolarità ==")
    import blueprints.fantacalcio2 as B
    db = extensions.get_db()
    lega, ctx = None, None
    with app.test_request_context():
        from flask import session
        session["username"], session["role"], session["user_id"] = "davide", "user", ids["davide"]
        lega, ctx = B._consiglio(db, lid)
    db.close()
    per_id = {v["g"]["id"]: v for v in ctx["valutazioni"]}
    esito("il ceduto non gioca", per_id[99]["gioca"] is False
          and per_id[99]["partita"]["perche"] == "ceduto")
    esito("⚠️ Como–Venezia rinviata: i loro giocatori non giocano, e si dice perché",
          per_id[23]["gioca"] is False
          and per_id[23]["partita"]["perche"] == "partita rinviata",
          str(per_id[23]["partita"]))
    esito("Roma–Lazio si gioca, con l'avversario e la sua classifica",
          per_id[31]["gioca"] is True and per_id[31]["partita"]["avversario"] == "Lazio"
          and per_id[31]["partita"]["avv"]["posizione"] == 3)
    esito("l'autogol toglie dalla fantamedia della lega",
          round(per_id[32]["fm"], 2) == round(6.0 + (2 * 3 - 2) / 5, 2),
          str(per_id[32]["fm"]))
    esito("⚠️ chi non ha partite a voto non ha fantamedia (non zero)",
          per_id[33]["fm"] is None)
    c442 = next(x for x in ctx["consigli"] if x["modulo"] == "4-4-2")
    titolari = [v["g"]["id"] for v in c442["titolari"]]
    esito("in attacco: prima chi gioca con la fantamedia più alta",
          [i for i in titolari if i >= 31] == [31, 33], str(titolari))
    esito("⚠️ chi non gioca finisce titolare solo se il reparto non si riempie",
          32 not in titolari and {v["g"]["id"] for v in c442["forzati"]} <= {15, 23, 24, 25},
          str([v["g"]["nome"] for v in c442["forzati"]]))
    esito("in panchina al massimo tanti per ruolo quanti ne gioca il modulo "
          "(prima di chi avanza)",
          [v["g"]["ruolo_classic"] for v in c442["panchina"][:1]] == ["p"])
    r = c.post(f"/fantacalcio2/lega/{lid}/consiglio/applica", data={"modulo": "4-4-2"},
               follow_redirects=True)
    db = extensions.get_db()
    tit = db.execute("SELECT COUNT(*) FROM fanta2_formazione WHERE league_id=? "
                     "AND titolare=1", (lid,)).fetchone()[0]
    db.close()
    esito("«applica» scrive una formazione da 11", tit == 11,
          f"{tit} titolari")

    # La formazione si salva anche a metà (25/09/2026), mai sbagliata.
    def salvata():
        db = extensions.get_db()
        righe = db.execute("SELECT player_id, titolare FROM fanta2_formazione "
                           "WHERE league_id=? ORDER BY titolare DESC, ordine",
                           (lid,)).fetchall()
        db.close()
        return ([r["player_id"] for r in righe if r["titolare"]],
                [r["player_id"] for r in righe if not r["titolare"]])
    ruolo = {v["g"]["id"]: v["g"]["ruolo_classic"] for v in ctx["valutazioni"]}
    difensori = [i for i in titolari if ruolo[i] == "d"]
    nove = [i for i in titolari if i not in difensori[:2]]
    r = c.post(f"/fantacalcio2/lega/{lid}/formazione/salva",
               data={"modulo": "4-4-2", "titolare": nove, "panchinaro": []},
               follow_redirects=True)
    pagina = r.data.decode("utf-8", "replace")
    esito("⚠️ una formazione da 9, panchina vuota, si salva e si rilegge uguale",
          salvata() == (nove, []), str(salvata()))
    esito("e dice cosa manca, nel messaggio e nell'avviso sopra il campo",
          "Non è ancora completa: mancano 2 difensori" in pagina
          and "<strong>Non è completa</strong>" in pagina)
    r = c.post(f"/fantacalcio2/lega/{lid}/formazione/salva",
               data={"modulo": "4-4-2", "titolare": nove[:-1],
                     "panchinaro": [nove[0]]}, follow_redirects=True)
    esito("un doppione invece non si salva, e la formazione di prima resta",
          "schierato due volte" in r.data.decode("utf-8", "replace")
          and salvata() == (nove, []))
    attaccanti = [i for i in ruolo if ruolo[i] == "a"]
    r = c.post(f"/fantacalcio2/lega/{lid}/formazione/salva",
               data={"modulo": "4-4-2", "titolare": attaccanti[:3]},
               follow_redirects=True)
    esito("né un attaccante in più di quanti il modulo ne vuole",
          "ne vuole 2" in r.data.decode("utf-8", "replace")
          and salvata() == (nove, []), f"{len(attaccanti)} attaccanti in rosa")
    c.post(f"/fantacalcio2/lega/{lid}/consiglio/applica", data={"modulo": "4-4-2"})

    # --- 7. l'avviso e il campo ----------------------------------------------------
    print("\n== 7. l'avviso sulla formazione e chi esce dalla rosa ==")
    db = extensions.get_db()
    # Si mette titolare a forza uno che non gioca: l'avviso lo deve dire.
    db.execute("UPDATE fanta2_formazione SET titolare=1 WHERE league_id=? AND "
               "player_id IN (23)", (lid,))
    db.execute("INSERT OR REPLACE INTO fanta2_formazione(league_id,player_id,titolare,"
               "ordine,ruolo) VALUES(?,23,1,20,'c')", (lid,))
    db.commit()
    db.close()
    pagina = c.get(f"/fantacalcio2/lega/{lid}").data.decode("utf-8", "replace")
    esito("un titolare con la partita rinviata viene dichiarato",
          "chi non gioca" in pagina and "partita rinviata" in pagina)
    db = extensions.get_db()
    rid = db.execute("SELECT id FROM fanta2_roster WHERE league_id=? AND player_id=23",
                     (lid,)).fetchone()["id"]
    db.close()
    c.post(f"/fantacalcio2/lega/{lid}/rosa/{rid}/rimuovi")
    db = extensions.get_db()
    esito("chi esce dalla rosa esce anche dal campo",
          not db.execute("SELECT 1 FROM fanta2_formazione WHERE league_id=? AND "
                         "player_id=23", (lid,)).fetchone())
    db.close()

    # --- 8. le pagine, e la sintassi di ogni script -----------------------------
    print("\n== 8. le pagine si aprono e il JavaScript compila ==")
    try:
        import esprima
    except ImportError:
        esprima = None
    HANDLER = re.compile(r"""\bon(?:click|change|submit|input)\s*=\s*("([^"]*)"|'([^']*)')""", re.I)
    SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script>", re.S | re.I)

    def rotti(pagina):
        fuori = []
        for m in SCRIPT.finditer(pagina):
            try:
                esprima.parseScript(m.group(1), {"tolerant": False})
            except Exception as e:
                fuori.append(f"<script>: {str(e)[:60]}")
        for m in HANDLER.finditer(SCRIPT.sub("", pagina)):
            codice = _html.unescape(m.group(2) if m.group(2) is not None else m.group(3))
            try:
                esprima.parseScript("function _(){%s}" % codice, {"tolerant": False})
            except Exception as e:
                fuori.append(f"{codice[:50]} -> {str(e)[:40]}")
        return fuori

    pagine = {"elenco": "/fantacalcio2/", "lega": f"/fantacalcio2/lega/{lid}",
              "campo": f"/fantacalcio2/lega/{lid}/formazione",
              "listone": "/fantacalcio2/listone?spenti=1"}
    for nome, url in pagine.items():
        r = c.get(url)
        testo = r.data.decode("utf-8", "replace")
        esito(f"{nome}: si apre", r.status_code == 200, str(r.status_code))
        if esprima is None:
            esito("⚠️ senza `esprima` la sintassi non è provata", False, "pip install esprima")
        else:
            guai = rotti(testo)
            esito(f"{nome}: nessuno script né handler rotto", not guai, str(guai[:3]))
    anteprima = c.post(f"/fantacalcio2/lega/{lid}/rosa/incolla", data={"testo": "N'Dri"})
    esito("anteprima dell'incolla: si apre, e compila",
          anteprima.status_code == 200 and (esprima is None or
                                            not rotti(anteprima.data.decode("utf-8"))))
    r = c.get("/fantacalcio2/api/giocatore/31").get_json()
    esito("la scheda porta la partita e le rose",
          r["partita"]["avversario"] == "Lazio" and r["rose"], str(r.get("partita")))
    elenco = c.get("/fantacalcio2/").data.decode("utf-8")
    esito("⚠️ l'attribuzione chiesta dai termini di football-data è in pagina",
          F.ATTRIBUZIONE in elenco)

    # --- 9a. chi gioca, segnato da te ---------------------------------------------
    # Decisione di Davide del 25/09/2026: la titolarità la segna lui, con le probabili
    # nel riquadro accanto. Si prova che la scelta si salva **sua**, che il consiglio
    # la usa nell'ordine dichiarato, e che l'avviso sulla formazione la guarda.
    print("\n== 9a. chi gioca, segnato da te ==")
    r = c.get(f"/fantacalcio2/lega/{lid}/chi-gioca")
    testo = r.data.decode("utf-8", "replace")
    esito("la pagina si apre, col riquadro delle probabili",
          r.status_code == 200 and "<iframe" in testo and B.LINK_PROBABILI in testo)
    if esprima is not None:
        guai = rotti(testo)
        esito("e il suo JavaScript compila", not guai, str(guai[:3]))
    esito("un altro utente non apre la pagina di una lega non sua",
          b"Lega non trovata" in a.get(f"/fantacalcio2/lega/{lid}/chi-gioca",
                                       follow_redirects=True).data)

    def segna(cl, pid, stato, giornata=6):
        return cl.post("/fantacalcio2/chi-gioca/segna",
                       data={"player_id": pid, "stato": stato, "giornata": giornata})

    esito("una scelta si salva", segna(c, 31, "titolare").get_json() == {
        "ok": True, "stato": "titolare"})
    esito("⚠️ uno stato inventato viene rifiutato", segna(c, 31, "forse").status_code == 400)
    esito("⚠️ e una giornata che non è quella in corso anche",
          segna(c, 31, "titolare", giornata=7).status_code == 409)
    esito("e un giocatore che non c'è", segna(c, 123456, "titolare").status_code == 404)
    segna(c, 21, "titolare")
    segna(c, 22, "dubbio")
    segna(c, 33, "fuori")
    segna(a, 31, "fuori")                     # l'altro utente la pensa diversamente
    db = extensions.get_db()
    mie = {r["player_id"]: r["stato"] for r in db.execute(
        "SELECT player_id, stato FROM fanta2_titolari WHERE user_id=?", (ids["davide"],))}
    db.close()
    esito("⚠️ le scelte di un altro utente non toccano le tue",
          mie == {31: "titolare", 21: "titolare", 22: "dubbio", 33: "fuori"}, str(mie))

    db = extensions.get_db()
    with app.test_request_context():
        from flask import session
        session["username"], session["role"], session["user_id"] = "davide", "user", ids["davide"]
        _, ctx = B._consiglio(db, lid)
    db.close()
    c442 = next(x for x in ctx["consigli"] if x["modulo"] == "4-4-2")
    cen = [v["g"]["id"] for v in c442["titolari"] if v["g"]["ruolo_classic"] == "c"]
    esito("⚠️ a centrocampo: prima il titolare, poi quello in dubbio (a fantamedia pari)",
          cen[:2] == [21, 22], str(cen))
    att = [v["g"]["id"] for v in c442["titolari"] if v["g"]["ruolo_classic"] == "a"]
    # Tre attaccanti: 31 segnato titolare, 32 con la partita rinviata, 33 segnato
    # «non gioca». Ne servono due, quindi uno che non gioca entra per forza: fra due
    # esclusi decide la fantamedia (32 ne ha una, 33 no), e resta dichiarato forzato.
    esito("in attacco: il titolare segnato è il primo, e il secondo posto è un forzato",
          att == [31, 32] and [v["g"]["id"] for v in c442["forzati"]
                               if v["g"]["ruolo_classic"] == "a"] == [32]
          and 33 not in att, f"{att} forzati {[v['g']['id'] for v in c442['forzati']]}")
    esito("⚠️ e sulla scelta dell'altro utente il consiglio tace: 31 resta titolare",
          next(v for v in ctx["valutazioni"] if v["g"]["id"] == 31)["scelta"] == "titolare")

    c.post(f"/fantacalcio2/lega/{lid}/consiglio/applica", data={"modulo": "4-4-2"})
    segna(c, 21, "fuori")                     # ci ripensi dopo aver schierato
    pagina = c.get(f"/fantacalcio2/lega/{lid}").data.decode("utf-8", "replace")
    esito("l'avviso dice chi hai schierato e poi segnato «non gioca»",
          "segnato «non gioca»" in _html.unescape(pagina) or "segnato «non gioca»" in pagina)
    esito("un secondo clic sullo stesso stato lo toglie",
          segna(c, 21, "").get_json() == {"ok": True, "stato": None})
    db = extensions.get_db()
    esito("…e la riga sparisce davvero",
          not db.execute("SELECT 1 FROM fanta2_titolari WHERE user_id=? AND player_id=21",
                         (ids["davide"],)).fetchone())
    db.close()
    campo = c.get(f"/fantacalcio2/lega/{lid}/formazione").data.decode("utf-8", "replace")
    esito("il campo porta la scelta accanto al giocatore",
          '"titolare"' in campo and (esprima is None or not rotti(campo)))

    # --- 9. upload dalla pagina, e la lega che se ne va ------------------------------
    print("\n== 9. il caricamento dalla pagina, e l'eliminazione ==")
    meno = [g for g in GIOCATORI if g[0] != 15]          # Dif Cinque esce dal file
    r = c.post("/fantacalcio2/listone/carica", data={
        "file_a": (io.BytesIO(file_quotazioni(meno)), "a.xlsx"),
        "file_b": (io.BytesIO(file_statistiche(meno)), "b.xlsx")},
        content_type="multipart/form-data", follow_redirects=True)
    db = extensions.get_db()
    riga = db.execute("SELECT attivo FROM fanta2_players WHERE id=15").fetchone()
    esito("chi non è più nel file resta, spento", riga and riga["attivo"] == 0)
    esito("e resta nella rosa che lo nomina",
          db.execute("SELECT 1 FROM fanta2_roster WHERE league_id=? AND player_id=15",
                     (lid,)).fetchone() is not None)
    db.close()
    pochi = GIOCATORI[:3]
    c.post("/fantacalcio2/listone/carica", data={
        "file_a": (io.BytesIO(file_quotazioni(pochi)), "a.xlsx"),
        "file_b": (io.BytesIO(file_statistiche(pochi)), "b.xlsx")},
        content_type="multipart/form-data")
    db = extensions.get_db()
    attivi = db.execute("SELECT COUNT(*) FROM fanta2_players WHERE attivo=1").fetchone()[0]
    db.close()
    esito("⚠️ un file con un terzo dei giocatori viene rifiutato", attivi == len(meno),
          f"{attivi} attivi")
    c.post(f"/fantacalcio2/lega/{lid}/elimina")
    db = extensions.get_db()
    esito("⚠️ la lega se ne va con la rosa **e** con la formazione",
          not db.execute("SELECT 1 FROM fanta2_roster WHERE league_id=?", (lid,)).fetchone()
          and not db.execute("SELECT 1 FROM fanta2_formazione WHERE league_id=?",
                             (lid,)).fetchone())
    esito("⚠️ e alla fine il listone della prima sezione è ancora com'era",
          db.execute("SELECT COUNT(*) FROM fanta_players").fetchone()[0] == 1)
    db.close()

    # --- 10. gli Excel presi dai download ----------------------------------------
    print("\n== 10. gli Excel presi dalla cartella dei download ==")
    import fanta2_fonti as F

    def metti(nome, dati, eta=0):
        percorso = os.path.join(scaricati, nome)
        with open(percorso, "wb") as f:
            f.write(dati)
        if eta:
            os.utime(percorso, (time.time() - eta, time.time() - eta))
        return percorso

    def c_e(nome):
        return os.path.exists(os.path.join(scaricati, nome))

    esito("la cartella è quella della variabile", F.cartella_download() == scaricati)
    Q, S = ("Quotazioni_Fantacalcio_Stagione_2026_27.xlsx",
            "Statistiche_Fantacalcio_Stagione_2026_27.xlsx")
    metti(Q, file_quotazioni())
    pagina = c.get("/fantacalcio2/", follow_redirects=True).data.decode("utf-8", "replace")
    esito("con un file solo non importa, lo dice, e il file resta",
          "manca quello delle statistiche" in pagina and c_e(Q))
    metti(S, file_statistiche())
    metti("Quotazioni_Fantacalcio_Stagione_2026_27 (1).xlsx",
          file_quotazioni(GIOCATORI[:3]), eta=3600)
    metti("Fantacalcio_mie_note.xlsx", xlsx({"Foglio1": [["a", "b"], [1, 2]]}))
    metti("altro.xlsx", file_quotazioni())
    pagina = c.get("/fantacalcio2/", follow_redirects=True).data.decode("utf-8", "replace")
    db = extensions.get_db()
    riga = db.execute("SELECT attivo FROM fanta2_players WHERE id=15").fetchone()
    db.close()
    esito("⚠️ con tutti e due importa il più recente (Dif Cinque torna attivo)",
          "Listone caricato dai download" in pagina and riga and riga["attivo"] == 1)
    esito("e cancella i due file, copia vecchia compresa",
          not c_e(Q) and not c_e(S)
          and not c_e("Quotazioni_Fantacalcio_Stagione_2026_27 (1).xlsx"))
    esito("⚠️ ma non tocca gli altri: né un .xlsx col nome giusto e un altro contenuto, "
          "né uno che non ha «fantacalcio» nel nome",
          c_e("Fantacalcio_mie_note.xlsx") and c_e("altro.xlsx"))
    metti(Q, file_quotazioni(GIOCATORI[:3]))
    metti(S, file_statistiche(GIOCATORI[:3]))
    pagina = c.get("/fantacalcio2/", follow_redirects=True).data.decode("utf-8", "replace")
    esito("⚠️ un import rifiutato (un terzo dei giocatori) lascia i file dove sono",
          "Listone non caricato dai download" in pagina and c_e(Q) and c_e(S))
    os.remove(os.path.join(scaricati, Q))
    os.remove(os.path.join(scaricati, S))
    esito("la pagina dice dove guarda, e ha il pulsante",
          scaricati in pagina and "Leggi i download" in pagina)
    r = c.post("/fantacalcio2/listone/dai-download", follow_redirects=True)
    esito("il pulsante, a cartella vuota: lo dice",
          "Nessun Excel di fantacalcio.it" in r.data.decode("utf-8", "replace"))
    metti(Q, file_quotazioni(meno))
    metti(S, file_statistiche(meno))
    r = c.post("/fantacalcio2/listone/dai-download", follow_redirects=True)
    db = extensions.get_db()
    riga = db.execute("SELECT attivo FROM fanta2_players WHERE id=15").fetchone()
    db.close()
    esito("⚠️ il pulsante importa (Dif Cinque di nuovo spento) e cancella",
          "Listone caricato dai download" in r.data.decode("utf-8", "replace")
          and riga["attivo"] == 0 and not c_e(Q) and not c_e(S))

    casa = os.path.join(dove, "casa")
    os.makedirs(os.path.join(casa, ".config"))
    xdg = os.environ.pop("XDG_CONFIG_HOME", None)
    try:
        esito("Linux senza user-dirs.dirs: ~/Downloads",
              F._download_linux(casa) == os.path.join(casa, "Downloads"))
        with open(os.path.join(casa, ".config", "user-dirs.dirs"), "w",
                  encoding="utf-8") as f:
            f.write('# commento\nXDG_DESKTOP_DIR="$HOME/Scrivania"\n'
                    'XDG_DOWNLOAD_DIR="$HOME/Scaricati"\n')
        esito("⚠️ Linux in italiano: legge «Scaricati» da user-dirs.dirs",
              F._download_linux(casa) == casa + "/Scaricati")
    finally:
        if xdg is not None:
            os.environ["XDG_CONFIG_HOME"] = xdg


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true",
                    help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_fanta2_")
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
