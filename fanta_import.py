"""Aggiornare listone e probabili: **una sola volta**, per due chiamanti.

Fino al 21/09/2026 questa logica stava dentro `scripts/importa_listone.py` e
`scripts/importa_probabili.py`, che erano gli unici a saperla. Poi Davide ha
chiesto un **pulsante** (e l'aggiornamento automatico entrando nella sezione), e
la strada facile sarebbe stata riscriverla nelle route.

⚠️ Non si fa, ed è una lezione già pagata in questo progetto: finché `main` del
moveset è stato scritto in due copie — `importa_mosse_specie.py` e
`pokeapi.moveset()` — una delle due è rimasta indietro, ed è esattamente così che
il difetto è sopravvissuto. Quindi la logica sta **qui**, e gli script e il web la
chiamano; gli script restano il rivestimento a riga di comando che stampa il
rapporto che queste funzioni restituiscono.

Ogni funzione:

- **non stampa niente** — torna un dizionario, e chi chiama decide se stamparlo a
  terminale o mostrarlo in una pagina;
- **non decide da sola se scrivere**: `scrivi=False` è il `--dry-run`;
- **si rifiuta** davanti ai numeri che sono il sintomo di una pagina letta male, e
  quel rifiuto arriva come `ok=False` con il motivo scritto, non come eccezione.

⚠️ Le due fonti non invecchiano allo stesso modo, ed è la ragione delle due soglie
qui sotto: il **listone** cambia a ogni mercato, le **probabili** cambiano fino al
fischio d'inizio. Sono i numeri che decidono l'aggiornamento automatico, quindi
stanno in un posto solo e si vedono.
"""
from datetime import datetime

import fantacalcio_it as F

# Dopo quante ore la copia in cache è considerata vecchia, entrando nella sezione.
# ⚠️ Non sono due gusti diversi: il listone si muove due volte l'anno, una
# formazione probabile si muove il sabato mattina.
VECCHIA_LISTONE = 24 * 7      # una settimana
VECCHIA_PROBABILI = 3         # tre ore

# Le colonne del listone che l'import riscrive. Restano qui perché sono la
# definizione di «cosa vuol dire aggiornato» per una voce.
CAMPI_LISTONE = (
    "nome", "slug", "squadra", "squadra_slug", "ruolo_classic", "ruolo_mantra",
    "ruolo_mantra_esteso", "qi", "qa", "fvm", "partite_a_voto", "media_voto",
    "fantamedia", "gol", "gol_subiti", "rigori", "rigori_parati", "assist",
    "ammonizioni", "espulsioni")

# Quanto può calare il listone prima che sia un sintomo invece di un mercato.
SOGLIA_CALO = 0.70
# Venti squadre giocano ogni giornata di Serie A: leggerne meno è un sintomo.
SQUADRE_ATTESE = 20


def _tabella_c_e(db, nome):
    return bool(db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                           "AND name=?", (nome,)).fetchone())


def serve_aggiornare(db, quale):
    """Se la copia di `quale` è più vecchia della sua soglia. `(sì/no, ore)`.

    ⚠️ Guarda l'**età della cache**, non quella delle righe nel DB: sono due cose
    diverse e la prima è quella che conta. Un import rifatto stamattina su una
    pagina scaricata tre giorni fa ha righe nuovissime e un contenuto vecchio di
    tre giorni — ed è precisamente il modo in cui questo dato dice il falso senza
    dare errore.
    """
    limite = VECCHIA_LISTONE if quale == "listone" else VECCHIA_PROBABILI
    nomi = ("quotazioni", "statistiche") if quale == "listone" else ("probabili",)
    eta = [F.eta_cache(n) for n in nomi]
    if any(e is None for e in eta):
        return True, None                     # non c'è: la prima volta si scarica
    piu_vecchia = max(eta)
    return piu_vecchia >= limite, piu_vecchia


# Il valore da passare come `ambito` quando si vogliono **tutte** le rose, di
# tutti gli utenti: è la situazione di uno script da riga di comando, che una
# sessione non ce l'ha. Si scrive, non si ottiene dimenticando un parametro.
TUTTE_LE_ROSE = ("1=1", [])


def _rose(db, ids, ambito):
    """Quante volte ognuno di quegli id è in una rosa. `{player_id: quante}`.

    ⚠️ `ambito` è `(condizione, parametri)` come lo dà `ambito_utente("l.user_id")`,
    ed è **obbligatorio**. Il primo giro ne aveva fatto un parametro con default
    `None` che voleva dire «tutte», e `controlla_proprietario.py` l'ha preso:
    chiamata dal pulsante «Aggiorna», questa query contava le rose di **tutti gli
    utenti**, e il messaggio «2 dei giocatori usciti sono in una tua rosa» parlava
    di rose altrui. Un default che vuol dire «vedi tutto» è la stessa classe di
    errore di §1.1 — chi vuole tutto lo scrive, con `TUTTE_LE_ROSE`.

    `fanta_roster` non ha una colonna sua per il proprietario, quindi il filtro
    passa **dalla lega** — la JOIN non è un abbellimento, è dove sta il permesso.
    """
    if not ids:
        return {}
    cond, par = ambito
    segni = ",".join("?" * len(ids))
    righe = db.execute(
        f"SELECT r.player_id, COUNT(*) AS quante FROM fanta_roster r "
        f"JOIN fanta_leagues l ON l.id=r.league_id "
        f"WHERE r.player_id IN ({segni}) AND {cond} GROUP BY r.player_id",
        list(ids) + list(par))
    return {r["player_id"]: r["quante"] for r in righe}


def aggiorna_listone(db, scarica=True, scrivi=True, forza=False,
                     ambito=TUTTE_LE_ROSE):
    """Rilegge il listone e lo porta in `hub.db`. Torna il rapporto.

    Chi esce dal listone viene **spento, non cancellato**: cancellarlo porterebbe
    via la riga di rosa che lo nomina, cioè il dato che è di Davide e che la fonte
    non sa ricostruire. Un giocatore spento che torna si riaccende da sé.
    """
    r = {"ok": False, "motivo": None, "letti": 0, "squadre": 0, "problemi": [],
         "nuovi": [], "cambiati": [], "riaccesi": [], "spenti": [],
         "trasferiti": [], "in_rosa": {}, "scritto": False}
    voci, problemi = F.giocatori(forza=scarica)
    r["problemi"] = problemi
    if not voci:
        r["motivo"] = ("Nessun giocatore letto: la pagina non ha la forma che mi "
                       "aspetto.")
        return r
    r["letti"] = len(voci)
    r["squadre"] = len({v["squadra"] for v in voci.values()})
    r["per_ruolo"] = {}
    for v in voci.values():
        r["per_ruolo"][v["ruolo_classic"]] = r["per_ruolo"].get(v["ruolo_classic"], 0) + 1

    prima = {x["id"]: dict(x) for x in db.execute("SELECT * FROM fanta_players")}
    attivi_prima = sum(1 for x in prima.values() if x["attivo"])
    r["nel_db"], r["attivi_prima"] = len(prima), attivi_prima

    if attivi_prima and len(voci) < attivi_prima * SOGLIA_CALO and not forza:
        r["motivo"] = (f"Il listone letto ha {len(voci)} giocatori, nel DB ce ne "
                       f"sono {attivi_prima} attivi: sotto il {SOGLIA_CALO:.0%}. "
                       "Un calo così non è un mercato, è una pagina letta male.")
        return r

    for pid, v in voci.items():
        vecchia = prima.get(pid)
        if vecchia is None:
            r["nuovi"].append(v)
            continue
        if not vecchia["attivo"]:
            r["riaccesi"].append(v)
        diff = [c for c in CAMPI_LISTONE
                if (vecchia.get(c) or None) != (v.get(c) or None)]
        if diff:
            r["cambiati"].append((v, diff, vecchia))
            if "squadra" in diff:
                r["trasferiti"].append((v, vecchia))
    r["spenti"] = [x for pid, x in prima.items()
                   if pid not in voci and x["attivo"]]
    r["in_rosa"] = _rose(db, [x["id"] for x in r["spenti"]], ambito)

    r["ok"] = True
    if not scrivi:
        return r

    oggi = datetime.now().strftime("%Y-%m-%d")
    colonne = ", ".join(CAMPI_LISTONE)
    segni = ", ".join("?" * len(CAMPI_LISTONE))
    aggiorna = ", ".join(f"{c}=excluded.{c}" for c in CAMPI_LISTONE)
    for pid, v in voci.items():
        db.execute(
            f"INSERT INTO fanta_players(id, {colonne}, attivo, visto_il, aggiornato_il) "
            f"VALUES(?, {segni}, 1, ?, CURRENT_TIMESTAMP) "
            f"ON CONFLICT(id) DO UPDATE SET {aggiorna}, attivo=1, "
            "visto_il=excluded.visto_il, aggiornato_il=CURRENT_TIMESTAMP",
            [pid] + [v.get(c) for c in CAMPI_LISTONE] + [oggi])
    if r["spenti"]:
        db.executemany("UPDATE fanta_players SET attivo=0, "
                       "aggiornato_il=CURRENT_TIMESTAMP WHERE id=?",
                       [(x["id"],) for x in r["spenti"]])
    db.commit()
    r["scritto"] = True
    r["attivi_dopo"] = db.execute(
        "SELECT COUNT(*) FROM fanta_players WHERE attivo=1").fetchone()[0]
    return r


def aggiorna_probabili(db, scarica=True, scrivi=True, giornata=None,
                       forza=False, ambito=TUTTE_LE_ROSE):
    """Rilegge le probabili e le porta in `hub.db`. Torna il rapporto.

    ⚠️ La giornata che rilegge viene **sovrascritta per intero**, le altre non si
    toccano. Una formazione non è un dato da aggiornare campo per campo: se un
    giocatore sparisce dai convocati la sua riga deve sparire, altrimenti resta a
    dire che è in panchina quando la fonte non lo nomina più.
    """
    r = {"ok": False, "motivo": None, "giornata": None, "stagione": None,
         "squadre": 0, "voci": 0, "titolari": 0, "problemi": [], "tolti": [],
         "ignoti": [], "miei": 0, "miei_titolari": 0, "scritto": False,
         "entrano": 0, "riscritte": 0}
    if not _tabella_c_e(db, "fanta_probabili"):
        r["motivo"] = ("In hub.db non c'è la tabella `fanta_probabili`. Lo schema "
                       "lo crea `init_db()`: avvia l'app una volta e riprova.")
        return r

    dati, problemi = F.probabili(forza=scarica)
    r["problemi"] = problemi
    r["stagione"] = dati["stagione"]
    giornata = giornata or dati["giornata"]
    r["giornata"] = giornata
    squadre, voci = dati["squadre"], dati["voci"]
    r["squadre"], r["voci"] = len(squadre), len(voci)
    r["titolari"] = sum(v["titolare"] for v in voci)

    if giornata is None:
        r["motivo"] = ("La pagina non dice che giornata è, e senza quella il dato "
                       "non ha una chiave.")
        return r
    if len(squadre) < SQUADRE_ATTESE and not forza:
        r["motivo"] = (f"Ho letto {len(squadre)} squadre invece di "
                       f"{SQUADRE_ATTESE}: mezza giornata scritta sembra una "
                       "giornata intera.")
        return r

    prima = {x["player_id"]: dict(x) for x in db.execute(
        "SELECT * FROM fanta_probabili WHERE giornata=?", (giornata,))}
    letti = {v["id"] for v in voci}
    r["tolti"] = [x for pid, x in prima.items() if pid not in letti]
    r["entrano"] = len(letti - set(prima))
    r["riscritte"] = len(letti & set(prima))
    r["gia_scritte"] = len(prima)

    # ⚠️ Stesso discorso di `_rose()`: «nelle tue rose» dev'essere davvero tue.
    in_rosa = _rose(db, list(letti), ambito)
    miei = [v for v in voci if v["id"] in in_rosa]
    r["miei"] = len(miei)
    r["miei_titolari"] = sum(1 for v in miei if v["titolare"])
    # ⚠️ Un convocato può non essere nel listone (il 21/09/2026 erano dodici):
    # entra lo stesso e viene detto. Con una foreign key sarebbe sparito in
    # silenzio, ed è il motivo per cui quella colonna non ne ha una.
    noti = {x["id"] for x in db.execute("SELECT id FROM fanta_players")}
    r["ignoti"] = [v for v in voci if v["id"] not in noti]

    r["ok"] = True
    if not scrivi:
        return r

    db.execute("DELETE FROM fanta_probabili WHERE giornata=?", (giornata,))
    db.execute("DELETE FROM fanta_probabili_squadre WHERE giornata=?", (giornata,))
    db.executemany(
        "INSERT INTO fanta_probabili_squadre(giornata, squadra_slug, squadra, modulo,"
        " avversario, avversario_slug, in_casa, match_id, aggiornato_il)"
        " VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
        [(giornata, s["squadra_slug"], s["squadra"], s["modulo"], s["avversario"],
          s["avversario_slug"], s["in_casa"], s["match_id"])
         for s in squadre.values()])
    db.executemany(
        "INSERT INTO fanta_probabili(giornata, player_id, nome, squadra_slug, ruolo,"
        " titolare, percentuale, aggiornato_il)"
        " VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
        [(giornata, v["id"], v["nome"], v["squadra_slug"], v["ruolo"],
          v["titolare"], v["percentuale"]) for v in voci])
    db.commit()
    r["scritto"] = True
    r["giornate_in_archivio"] = db.execute(
        "SELECT COUNT(DISTINCT giornata) FROM fanta_probabili").fetchone()[0]
    return r
