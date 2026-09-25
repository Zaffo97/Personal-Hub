"""La logica della Fantacalcio 2: import, calendario e consiglio, **in un posto solo**.

È `fanta_import.py` più la parte di `data.py` che la prima sezione usa per il
consiglio, rifatte per le fonti nuove (`fanta2_fonti.py`). La chiamano il blueprint
e lo script `scripts/importa_listone2.py`: la stessa logica scritta due volte è il
modo in cui una delle due resta indietro, e questo progetto l'ha già pagato.

Ogni funzione che scrive **non stampa niente**: torna un rapporto, e `scrivi=False`
è il `--dry-run`. Davanti ai numeri che sono il sintomo di un file sbagliato si
rifiuta, con `ok=False` e il motivo scritto.

⚠️ **Cosa cambia rispetto alla prima sezione**, e va detto a schermo, non scoperto:

- **niente probabili lette da un programma.** Davide le **guarda** (pagina «Chi
  gioca», un riquadro accanto alla rosa) e la titolarità la decide lui schierando: il
  consiglio non la sa. Dal 25/09/2026 non si **segna** più niente — i tre stati
  titolare / in dubbio / non gioca sono stati tolti su sua richiesta. Il consiglio
  ordina: prima chi può giocare (il calendario dice se la squadra gioca e se il
  giocatore è ceduto), poi la **fantamedia rifatta con le regole della lega**;
- **l'avversario si mostra e non si pesa** (decisione di Davide del 24/09/2026):
  nessuno pubblica quanto valga un avversario facile rispetto alla fantamedia, e un
  peso scelto qui sarebbe un numero inventato;
- l'**autogol** entra nella fantamedia, perché il file delle statistiche lo porta.
  La porta inviolata ancora no: nessuna delle due fonti la pubblica.
"""
from datetime import datetime

import fanta2_fonti as F
from data import (ORDINE_RUOLI_FANTA, MINIMO_PARTITE_FIDATO, scomponi_modulo,
                  nome_ruolo, fantamedia_regole, soglie_mod_difesa, modificatore_difesa)

# Il calendario invecchia in un giorno, come nella prima sezione, e per la stessa
# ragione: da lì esce la scadenza del timer, e un anticipo spostato cambia l'ora.
# Qui l'aggiornamento automatico è permesso — è un'API con chiave, non una pagina.
VECCHIO_CALENDARIO = 24

CAMPI_LISTONE = (
    "nome", "squadra", "squadra_slug", "ruolo_classic", "ruolo_mantra",
    "qi", "qa", "fvm", "partite_a_voto", "media_voto", "fantamedia", "gol",
    "gol_subiti", "rigori", "rigori_parati", "assist", "ammonizioni",
    "espulsioni", "autogol", "ceduto")
CAMPI_STATISTICHE = ("partite_a_voto", "media_voto", "fantamedia", "gol",
                     "gol_subiti", "rigori", "rigori_parati", "assist",
                     "ammonizioni", "espulsioni", "autogol")

# Quanto può calare il listone prima che sia un sintomo invece di un mercato.
SOGLIA_CALO = 0.70

# Come in `fanta_import`: per contare le rose di tutti bisogna scriverlo.
TUTTE_LE_ROSE = ("1=1", [])


def _rose(db, ids, ambito):
    """Quante volte ognuno di quegli id è in una rosa **visibile da `ambito`**.

    Il filtro passa dalla lega: `fanta2_roster` non ha un proprietario suo.
    """
    if not ids:
        return {}
    cond, par = ambito
    segni = ",".join("?" * len(ids))
    return {r["player_id"]: r["quante"] for r in db.execute(
        f"SELECT r.player_id, COUNT(*) AS quante FROM fanta2_roster r "
        f"JOIN fanta2_leagues l ON l.id=r.league_id "
        f"WHERE r.player_id IN ({segni}) AND {cond} GROUP BY r.player_id",
        list(ids) + list(par))}


def leggi_i_due_file(file_a, file_b):
    """`(fogli_quotazioni, fogli_statistiche, problemi)` da due file in qualunque ordine.

    Quale sia quale lo dice il **contenuto** (`che_file_e()`), non l'ordine in cui
    sono stati scelti né il nome: scambiarli nel form non deve bastare a mettere le
    statistiche al posto delle quotazioni.
    """
    fogli, problemi = {}, []
    for dati in (file_a, file_b):
        if not dati:
            continue
        try:
            letti = F.leggi_xlsx(dati)
        except Exception as e:
            problemi.append(f"Un file non è un .xlsx leggibile ({type(e).__name__}).")
            continue
        quale = F.che_file_e(letti)
        if quale is None:
            problemi.append("Un file non è né le quotazioni né le statistiche di "
                            "fantacalcio.it: non ha le colonne che mi aspetto.")
        elif quale in fogli:
            problemi.append(f"Sono arrivati due file di {quale}.")
        else:
            fogli[quale] = letti
    return fogli.get("quotazioni"), fogli.get("statistiche"), problemi


def importa_listone(db, fogli_q, fogli_s, scrivi=True, forza=False,
                    ambito=TUTTE_LE_ROSE):
    """Porta i due Excel in `fanta2_players`. Torna il rapporto.

    ⚠️ **Le quotazioni comandano**: un giocatore che sta solo nelle statistiche non
    entra (lo si dice), e le statistiche aggiungono numeri, non giocatori. È la
    stessa regola della prima sezione.

    Chi non è più nel file viene **spento, non cancellato**, e chi è nel foglio
    «Ceduti» entra spento: in tutti e due i casi può essere nella rosa di qualcuno.
    """
    r = {"ok": False, "motivo": None, "letti": 0, "ceduti": 0, "problemi": [],
         "nuovi": [], "cambiati": 0, "riaccesi": [], "spenti": [],
         "solo_statistiche": [], "senza_statistiche": 0, "in_rosa": {},
         "scritto": False}
    if not fogli_q or not fogli_s:
        r["motivo"] = ("Servono tutti e due i file: le quotazioni e le statistiche.")
        return r
    quot, pq = F.quotazioni(fogli_q)
    stat, ps = F.statistiche(fogli_s)
    r["problemi"] = pq + ps
    if not quot:
        r["motivo"] = "Nessun giocatore letto dal file delle quotazioni."
        return r

    voci = {}
    for pid, q in quot.items():
        v = dict(q)
        s = stat.get(pid)
        if s:
            v.update({c: s.get(c) for c in CAMPI_STATISTICHE})
        else:
            r["senza_statistiche"] += 1
            v.update({c: None for c in CAMPI_STATISTICHE})
        voci[pid] = v
    r["solo_statistiche"] = [s for pid, s in stat.items() if pid not in quot]
    r["letti"] = len(voci)
    r["ceduti"] = sum(1 for v in voci.values() if v["ceduto"])

    prima = {x["id"]: dict(x) for x in db.execute("SELECT * FROM fanta2_players")}
    attivi_prima = sum(1 for x in prima.values() if x["attivo"])
    in_rosa_ora = r["letti"] - r["ceduti"]
    if attivi_prima and in_rosa_ora < attivi_prima * SOGLIA_CALO and not forza:
        r["motivo"] = (f"Il file ha {in_rosa_ora} giocatori in Serie A, nel DB ce ne "
                       f"sono {attivi_prima} attivi: sotto il {SOGLIA_CALO:.0%}. Un "
                       "calo così non è un mercato, è probabilmente il file sbagliato.")
        return r

    for pid, v in voci.items():
        vecchia = prima.get(pid)
        if vecchia is None:
            r["nuovi"].append(v)
            continue
        if not vecchia["attivo"] and not v["ceduto"]:
            r["riaccesi"].append(v)
        if any((vecchia.get(c) if vecchia.get(c) != "" else None) != v.get(c)
               for c in CAMPI_LISTONE):
            r["cambiati"] += 1
    r["spenti"] = [x for pid, x in prima.items() if pid not in voci and x["attivo"]]
    # Chi esce e chi è ceduto, se è in una **tua** rosa: sono gli unici che ti
    # riguardano davvero, ed è quello che il messaggio deve dire.
    usciti = [x["id"] for x in r["spenti"]] + [pid for pid, v in voci.items()
                                               if v["ceduto"]]
    r["in_rosa"] = _rose(db, usciti, ambito)
    r["ok"] = True
    if not scrivi:
        return r

    oggi = datetime.now().strftime("%Y-%m-%d")
    colonne = ", ".join(CAMPI_LISTONE)
    segni = ", ".join("?" * len(CAMPI_LISTONE))
    aggiorna = ", ".join(f"{c}=excluded.{c}" for c in CAMPI_LISTONE)
    for pid, v in voci.items():
        db.execute(
            f"INSERT INTO fanta2_players(id, {colonne}, attivo, visto_il, aggiornato_il) "
            f"VALUES(?, {segni}, ?, ?, CURRENT_TIMESTAMP) "
            f"ON CONFLICT(id) DO UPDATE SET {aggiorna}, attivo=excluded.attivo, "
            "visto_il=excluded.visto_il, aggiornato_il=CURRENT_TIMESTAMP",
            [pid] + [v.get(c) for c in CAMPI_LISTONE] + [0 if v["ceduto"] else 1, oggi])
    if r["spenti"]:
        db.executemany("UPDATE fanta2_players SET attivo=0, "
                       "aggiornato_il=CURRENT_TIMESTAMP WHERE id=?",
                       [(x["id"],) for x in r["spenti"]])
    db.commit()
    r["scritto"] = True
    return r


# ── Calendario e classifica ─────────────────────────────────────────────────

def eta_calendario(db):
    """Da quante ore il calendario non si aggiorna, o `None` se non c'è."""
    r = db.execute("SELECT MAX(aggiornato_il) AS q FROM fanta2_calendario").fetchone()
    if not r or not r["q"]:
        return None
    # `CURRENT_TIMESTAMP` di SQLite è **UTC**: confrontarlo con l'ora locale
    # sposterebbe l'età di una o due ore senza dare errore.
    quando = datetime.strptime(r["q"], "%Y-%m-%d %H:%M:%S")
    return (datetime.utcnow() - quando).total_seconds() / 3600


def aggiorna_calendario(db, scrivi=True):
    """Rilegge partite e classifica da football-data.org. Torna il rapporto.

    Due chiamate: tutta la stagione e la classifica. ⚠️ Senza chiave non parte, e
    lo dice: una sezione che si apre senza calendario è meglio di una che finge di
    averlo.
    """
    r = {"ok": False, "motivo": None, "partite": 0, "giornate": 0,
         "con_ora": 0, "non_abbinate": [], "squadre": 0, "scritto": False}
    chiave = F.chiave_api()
    if not chiave:
        r["motivo"] = (f"Manca la chiave di football-data.org: va nella variabile "
                       f"d'ambiente {F.VARIABILE_CHIAVE}.")
        return r
    partite = F.partite(chiave)
    tabella = F.classifica(chiave)
    if not partite:
        r["motivo"] = "football-data.org non ha restituito nessuna partita."
        return r
    squadre_listone = {x["squadra_slug"] for x in db.execute(
        "SELECT DISTINCT squadra_slug FROM fanta2_players WHERE attivo=1 "
        "AND squadra_slug IS NOT NULL")}
    nomi = {p["casa"] for p in partite} | {p["fuori"] for p in partite}
    abbinate, sole = F.abbina_squadre(sorted(n for n in nomi if n), squadre_listone)
    r.update(partite=len(partite), giornate=len({p["giornata"] for p in partite}),
             con_ora=sum(1 for p in partite if p["stato"] in F.CON_ORA),
             non_abbinate=sole, squadre=len(nomi), senza_listone=not squadre_listone)
    r["ok"] = True
    if not scrivi:
        return r
    db.execute("DELETE FROM fanta2_calendario")
    db.executemany(
        "INSERT INTO fanta2_calendario(match_id, giornata, stato, inizio, utc, casa, "
        "casa_slug, fuori, fuori_slug, gol_casa, gol_fuori, aggiornata_fonte) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        [(p["match_id"], p["giornata"], p["stato"], p["inizio"], p["utc"],
          p["casa"], abbinate.get(p["casa"]), p["fuori"], abbinate.get(p["fuori"]),
          p["gol_casa"], p["gol_fuori"], p["aggiornata"]) for p in partite])
    db.execute("DELETE FROM fanta2_classifica")
    db.executemany(
        "INSERT INTO fanta2_classifica(squadra_slug, squadra, posizione, punti, "
        "giocate, gol_fatti, gol_subiti) VALUES(?,?,?,?,?,?,?)",
        [(abbinate.get(t["squadra"]) or F.slug_squadra(t["squadra"]), t["squadra"],
          t["posizione"], t["punti"], t["giocate"], t["gol_fatti"], t["gol_subiti"])
         for t in tabella])
    db.commit()
    r["scritto"] = True
    return r


def giornata_corrente(db):
    """La prima giornata con una partita ancora da giocare, o `None`.

    ⚠️ Le rinviate **non contano**: una partita della giornata 3 rinviata a data da
    destinarsi terrebbe la sezione ferma alla 3 per mesi.
    """
    segni = ",".join("?" * len(F.DA_GIOCARE))
    r = db.execute(f"SELECT MIN(giornata) AS g FROM fanta2_calendario "
                   f"WHERE stato IN ({segni})", tuple(F.DA_GIOCARE)).fetchone()
    return r["g"] if r and r["g"] else None


def scadenza(db, giornata):
    """La scadenza nella forma del timer (`_fanta_timer.html`), o `None`.

    ⚠️ Si fida **solo** delle partite con l'ora esatta: `SCHEDULED` ha una data
    approssimativa, e un timer su quella sarebbe un numero che scorre e mente.
    Quelle senza ora si contano in `senza_ora`, e il timer le dichiara.
    """
    if not giornata:
        return None
    righe = [dict(x) for x in db.execute(
        "SELECT * FROM fanta2_calendario WHERE giornata=? ORDER BY inizio",
        (giornata,))]
    con_ora = [x for x in righe if x["stato"] in F.CON_ORA and x["inizio"]]
    if not con_ora:
        return None
    prima = con_ora[0]
    try:
        quando = datetime.strptime(prima["inizio"], "%Y-%m-%d %H:%M").strftime(
            "%d/%m/%Y alle %H:%M")
    except ValueError:
        quando = prima["inizio"]
    return {"giornata": giornata, "inizio": prima["inizio"], "quando": quando,
            "casa": prima["casa"], "fuori": prima["fuori"], "quante": len(righe),
            "senza_ora": len([x for x in righe if x["stato"] not in F.CON_ORA
                              and x["stato"] not in F.NON_SI_GIOCA])}


def partite_della_giornata(db, giornata):
    """`{squadra_slug: partita}` per quella giornata, vista da ogni squadra."""
    if not giornata:
        return {}
    fuori = {}
    for x in db.execute("SELECT * FROM fanta2_calendario WHERE giornata=? "
                        "ORDER BY inizio", (giornata,)):
        x = dict(x)
        gioca = x["stato"] not in F.NON_SI_GIOCA
        for mia, loro, nome_loro, in_casa in (
                (x["casa_slug"], x["fuori_slug"], x["fuori"], True),
                (x["fuori_slug"], x["casa_slug"], x["casa"], False)):
            if mia:
                fuori[mia] = {"avversario": nome_loro, "avversario_slug": loro,
                              "in_casa": in_casa, "stato": x["stato"],
                              "inizio": x["inizio"], "gioca": gioca,
                              "ora_certa": x["stato"] in F.CON_ORA}
    return fuori


def classifica(db):
    return {x["squadra_slug"]: dict(x) for x in db.execute(
        "SELECT * FROM fanta2_classifica ORDER BY posizione")}


def partita_di(g, partite, tabella, calendario_c_e):
    """La partita di un giocatore nella giornata, con l'avversario in classifica.

    Tre risposte, e sono tre cose diverse:
    - `gioca=False` perché è **ceduto**, o perché la sua squadra **non gioca**
      (nessuna partita in calendario, o partita rinviata/annullata);
    - `gioca=True` con l'avversario;
    - `gioca=None` quando **non lo sappiamo** — calendario non importato, o una
      squadra non abbinata. «Non lo sappiamo» non è «non gioca».
    """
    if g.get("ceduto") or not g.get("attivo", 1):
        return {"gioca": False, "perche": "ceduto"}
    if not calendario_c_e:
        return {"gioca": None, "perche": "senza calendario"}
    p = partite.get(g.get("squadra_slug"))
    if p is None:
        return {"gioca": False, "perche": "la squadra non gioca"}
    voce = dict(p)
    if not p["gioca"]:
        voce["perche"] = "partita " + {"POSTPONED": "rinviata",
                                       "CANCELLED": "annullata",
                                       "SUSPENDED": "sospesa"}.get(p["stato"], p["stato"])
    voce["avv"] = tabella.get(p.get("avversario_slug"))
    return voce


# ── Il consiglio, senza la titolarità ────────────────────────────────────────

def fantamedia_lega(g, regole):
    """La fantamedia rifatta con le regole della lega, **autogol compreso**.

    È `fantamedia_regole()` della prima sezione più l'autogol, che lì non c'era
    perché le pagine non lo pubblicavano: il file delle statistiche sì (`Au`).
    """
    fm, pezzi = fantamedia_regole(g, regole)
    partite = g.get("partite_a_voto") or 0
    autogol = g.get("autogol") or 0
    valore = regole.get("malus_autogol") if hasattr(regole, "get") else None
    if fm is None or not autogol or valore in (None, 0):
        return fm, pezzi
    punti = autogol * float(valore)
    return fm + punti / partite, pezzi + [
        {"voce": "autogol", "quanti": autogol, "valore": float(valore), "punti": punti}]


def valuta_rosa(rosa, partite, tabella, regole, calendario_c_e):
    """Una riga per giocatore: fantamedia della lega e la sua partita.

    `escluso` è la domanda che conta per il consiglio: **di sicuro non gioca**, perché
    lo dice il calendario (ceduto, squadra ferma, partita rinviata).
    """
    fuori = []
    for g in rosa:
        fm, pezzi = fantamedia_lega(g, regole)
        partita = partita_di(g, partite, tabella, calendario_c_e)
        fuori.append({
            "g": g, "fm": fm, "pezzi": pezzi,
            "partite": g.get("partite_a_voto") or 0,
            "fidata": (g.get("partite_a_voto") or 0) >= MINIMO_PARTITE_FIDATO,
            "partita": partita, "gioca": partita.get("gioca"),
            "escluso": partita.get("gioca") is False,
        })
    return fuori


def _chiave(v):
    """L'ordine dentro un reparto: prima chi **può** giocare, poi la fantamedia.

    ⚠️ Chi non ha fantamedia (nessuna partita a voto) va **dopo** chi ce l'ha, non
    in mezzo con zero: zero vorrebbe dire «ha giocato male», e non è quello che si
    sa. A parità, più partite a voto, poi il nome — per non lasciar decidere a caso.
    """
    return (v["escluso"],
            v["fm"] is None,
            -(v["fm"] or 0),
            -(v["partite"] or 0),
            v["g"].get("nome") or "")


def per_reparto(valutazioni):
    return {r: sorted([v for v in valutazioni if v["g"].get("ruolo_classic") == r],
                      key=_chiave) for r in ORDINE_RUOLI_FANTA}


def modificatore(titolari, regole):
    """Il modificatore di difesa di questo undici **se giocano tutti**. `None` se la
    lega non lo usa.

    Stessa struttura della prima sezione (portiere + migliori 3, o migliori 4, e
    servono 4 difensori a voto). ⚠️ Là il numero veniva moltiplicato per la
    probabilità che quei quattro giochino; qui la probabilità non c'è, e la pagina
    lo dice: è il valore **pieno**, cioè il massimo.
    """
    if not regole or not regole.get("mod_difesa"):
        return None
    soglie = soglie_mod_difesa(regole.get("mod_difesa_soglie"))
    col_portiere = (regole.get("mod_difesa_portiere") or 0) != 0
    voto = lambda v: v["g"].get("media_voto")
    dif = sorted([v for v in titolari if v["g"].get("ruolo_classic") == "d"
                  and voto(v) is not None and not v["escluso"]],
                 key=voto, reverse=True)
    por = [v for v in titolari if v["g"].get("ruolo_classic") == "p"
           and voto(v) is not None and not v["escluso"]]
    if len(dif) < 4:
        return {"punti": 0.0, "media": None, "chi": [], "col_portiere": col_portiere,
                "perche": f"servono 4 difensori a voto, questo undici ne ha {len(dif)}"}
    if col_portiere and not por:
        return {"punti": 0.0, "media": None, "chi": [], "col_portiere": col_portiere,
                "perche": "il portiere non ha una media voto"}
    chi = ([por[0]] + dif[:3]) if col_portiere else dif[:4]
    media = round(sum(voto(v) for v in chi) / len(chi), 2)
    return {"punti": modificatore_difesa(media, soglie), "media": media, "chi": chi,
            "col_portiere": col_portiere, "perche": None}


def consiglia_formazione(valutazioni, modulo, n_panchinari=7, regole=None):
    """L'undici e la panchina per **un** modulo, in ordine di fantamedia.

    - `forzati`: titolari che **non giocano** ma servono a riempire il reparto — con
      due portieri di cui uno ceduto e l'altro senza partita, un portiere lo schieri
      lo stesso. La pagina lo dichiara;
    - la panchina segue la stessa regola della prima sezione: al massimo quanti ne
      gioca il modulo per ruolo (un secondo portiere di riserva non entra mai), e
      quello che avanza rientra solo se restano posti.
    """
    serve = scomponi_modulo(modulo)
    if not serve:
        return None
    reparti = per_reparto(valutazioni)
    titolari, avanzi = [], []
    for ruolo in ORDINE_RUOLI_FANTA:
        titolari += reparti[ruolo][:serve[ruolo]]
        avanzi += reparti[ruolo][serve[ruolo]:]
    panchina, scartati, conto = [], [], {}
    for v in sorted(avanzi, key=_chiave):
        r = v["g"].get("ruolo_classic")
        if v["escluso"] or conto.get(r, 0) >= serve.get(r, 0):
            scartati.append(v)
            continue
        panchina.append(v)
        conto[r] = conto.get(r, 0) + 1
    panchina = (panchina + scartati)[:n_panchinari or 0]
    somme = [v["fm"] for v in titolari if v["fm"] is not None and not v["escluso"]]
    somma = round(sum(somme), 2) if somme else None
    mod = modificatore(titolari, regole)
    return {"modulo": modulo, "titolari": titolari, "panchina": panchina,
            "somma": somma, "mod": mod,
            "totale": None if somma is None else round(somma + (mod or {}).get("punti", 0), 2),
            "senza_fm": len([v for v in titolari if v["fm"] is None]),
            "forzati": [v for v in titolari if v["escluso"]],
            "incerti": [v for v in titolari if v["gioca"] is None]}


def consiglia_moduli(valutazioni, moduli, n_panchinari=7, regole=None):
    """Un consiglio per modulo, col migliore segnato sul `totale`."""
    fuori = [c for c in (consiglia_formazione(valutazioni, m, n_panchinari, regole)
                         for m in moduli) if c]
    migliore = max((c for c in fuori if c["totale"] is not None),
                   key=lambda c: c["totale"], default=None)
    for c in fuori:
        c["migliore"] = migliore is not None and c["modulo"] == migliore["modulo"]
    return fuori


def controlla_schierati(schierati, valutazioni, nomi, in_rosa):
    """Cosa non torna nella formazione salvata. Stessa forma della prima sezione.

    - `fuori`: titolari che **non giocano** — ceduti, squadra senza partita, partita
      rinviata. È un fatto del calendario, non un'opinione di una redazione;
    - `occasioni`: panchinari che giocano con una fantamedia più alta di un titolare
      dello stesso ruolo **che non gioca**. Solo in quel caso: «in panchina c'è uno
      più bravo» non è un guaio, è la tua scelta;
    - `spariti`: schierati ma non più in rosa (la rete, come nella prima sezione).

    `incerti` resta vuoto e c'è solo perché il riquadro abbia la stessa forma: qui
    non c'è una percentuale che possa mettere in dubbio un titolare (dal 25/09/2026
    non ci sono più nemmeno i «in dubbio» segnati a mano).
    """
    per_id = {v["g"]["id"]: v for v in valutazioni}
    fuori, occasioni, spariti = [], [], []
    for pid, riga in (schierati or {}).items():
        voce = {"id": pid, "nome": nomi.get(pid, "?"), "perche": None}
        if pid not in in_rosa:
            spariti.append(voce)
            continue
        v = per_id.get(pid)
        if v and riga.get("titolare") and v["escluso"]:
            voce["perche"] = v["partita"].get("perche")
            fuori.append(voce)
    ruoli_scoperti = {per_id[x["id"]]["g"].get("ruolo_classic") for x in fuori
                      if x["id"] in per_id}
    for pid, riga in (schierati or {}).items():
        v = per_id.get(pid)
        if (v and not riga.get("titolare") and not v["escluso"]
                and v["g"].get("ruolo_classic") in ruoli_scoperti):
            occasioni.append({"id": pid, "nome": nomi.get(pid, "?"), "fm": v["fm"]})
    return {"fuori": sorted(fuori, key=lambda x: x["nome"]), "incerti": [],
            "occasioni": sorted(occasioni, key=lambda x: -(x["fm"] or 0)),
            "spariti": sorted(spariti, key=lambda x: x["nome"])}


def controlla_formazione_larga(modulo, titolari, panchinari, rosa, n_panchinari=None):
    """La validazione della Fantacalcio 2: `(sbagli, mancano)`, due liste di frasi.

    Richiesta di Davide del 25/09/2026: la formazione si salva **anche incompleta**,
    perché si costruisce saltando fra una pagina e l'altra. Quindi due elenchi:

    - `sbagli`: una formazione **sbagliata**, che non si salva — modulo illeggibile,
      giocatore non in rosa, doppione, più giocatori di un ruolo di quanti il modulo
      ne vuole (un attaccante al posto di un difensore), panchina oltre il limite;
    - `mancano`: una formazione **a metà**, che si salva e si dice — «mancano 2
      difensori», la panchina non piena.

    ⚠️ È la gemella larga di `data.controlla_formazione()`, che resta severa per la
    prima sezione e non si tocca. Il modulo **ammesso dalla lega** lo guarda chi
    chiama, come lì.
    """
    serve = scomponi_modulo(modulo)
    if not serve:
        return ([f"«{modulo or '—'}» non è un modulo: i dieci di movimento devono "
                 "fare 10."], [])
    sbagli = []
    tutti = list(titolari) + list(panchinari)
    fuori_rosa = [p for p in tutti if p not in rosa]
    if fuori_rosa:
        sbagli.append(f"{len(fuori_rosa)} giocatore non è in questa rosa."
                      if len(fuori_rosa) == 1 else
                      f"{len(fuori_rosa)} giocatori non sono in questa rosa.")
    visti, doppi = set(), []
    for p in tutti:
        if p in visti:
            doppi.append(p)
        visti.add(p)
    if doppi:
        sbagli.append("Un giocatore è schierato due volte."
                      if len(doppi) == 1 else
                      f"{len(doppi)} giocatori sono schierati due volte.")
    if sbagli:
        return sbagli, []

    per_ruolo = {}
    for p in titolari:
        per_ruolo[rosa[p]] = per_ruolo.get(rosa[p], 0) + 1
    mancano = []
    for ruolo in ORDINE_RUOLI_FANTA:
        ha, vuole = per_ruolo.get(ruolo, 0), serve[ruolo]
        if ha > vuole:
            sbagli.append(f"Hai {ha} {nome_ruolo(ruolo, ha)} in campo, il {modulo} "
                          f"ne vuole {vuole}.")
        elif ha < vuole:
            manca = vuole - ha
            mancano.append(f"{'manca' if manca == 1 else 'mancano'} {manca} "
                           f"{nome_ruolo(ruolo, manca)}")
    if n_panchinari is not None and len(panchinari) > n_panchinari:
        sbagli.append(f"In panchina ce ne sono {len(panchinari)}, questa lega ne "
                      f"ammette {n_panchinari}.")
    elif n_panchinari and len(panchinari) < n_panchinari:
        mancano.append(f"panchina {len(panchinari)} su {n_panchinari}")
    return sbagli, mancano
