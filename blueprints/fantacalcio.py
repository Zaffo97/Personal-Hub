"""La sezione Fantacalcio: le leghe con le loro regole, e la rosa di ognuna.

§4.2 del backlog, aperta il 21/09/2026. Le decisioni di Davide che danno forma a
questo file: **due leghe**, tutte e due **Classic**, e le regole **strutturate** —
cioè in colonne che l'app può leggere, non in un testo libero da rileggere a occhio.

⚠️ **Di chi sono i dati.** `fanta_players` è il listone ed è **condiviso**, come il
catalogo Pokémon: nessun proprietario, e non deve averlo. `fanta_leagues` e
`fanta_roster` sono invece **tuoi**, quindi ogni lettura passa da `ambito_utente()`
e ogni scrittura da `solo_mie()`. La rosa non ha una colonna `user_id` di suo: il
proprietario le arriva dalla lega, quindi le sue query **devono** passare dalla
`fanta_leagues` per essere filtrate — una `SELECT` su `fanta_roster` da sola sarebbe
scoperta, ed è la trappola scritta in §1.1.

⚠️ E ogni `UPDATE`/`DELETE` filtrato guarda il `rowcount`: una scrittura che non
tocca niente **non dà errore**, e senza quel controllo il codice sotto andrebbe
avanti come se avesse funzionato.
"""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify)

from extensions import (get_db, login_required, _i, ambito_utente, solo_mie,
                        utente_id, e_admin)
from data import (RUOLI_FANTA, ORDINE_RUOLI_FANTA, scomponi_modulo,
                  MOD_DIFESA_SOGLIE, soglie_mod_difesa, scrivi_soglie,
                  modificatore_difesa, controlla_formazione,
                  leggi_rosa_incollata)
import fanta_import as I

bp = Blueprint("fantacalcio", __name__, url_prefix="/fantacalcio")

# Le colonne delle regole, in un posto solo: le usano il form, il salvataggio e la
# scheda che le mostra. ⚠️ **Sette su nove** vengono dal regolamento ufficiale, che
# `/regolamenti/leghe-private` elenca per esteso (riletto il 21/09/2026): il terzo
# valore di ogni riga dice quali. Porta inviolata e autogol no — quelli il
# regolamento non li fissa, e sono il motivo per cui queste regole stanno in colonne
# invece che in un testo da rileggere a occhio.
#
# ⚠️ **Il gol è uno solo.** Fino al 21/09/2026 c'erano quattro colonne, una per
# ruolo. Il regolamento ufficiale — riletto quel giorno su
# `/regolamenti/leghe-private` — dà **+3 a chiunque segni**, portiere compreso, e
# quattro caselle da riempire con lo stesso numero erano quattro occasioni di
# sbagliarne una senza accorgersene.
#
# La quarta voce di ogni riga sono i **valori proposti** nella tendina. Non sono
# una gabbia: la tendina ha sempre «Altro…», che scopre la casella per scrivere un
# numero qualsiasi. Servono a far vedere subito quello **giusto** — i valori del
# regolamento sono segnati «(ufficiale)» — invece di lasciare una casella vuota
# davanti a chi non ricorda se l'ammonizione toglie mezzo punto o uno.
REGOLE = [
    ("bonus_gol", "Gol segnato", True, [2, 2.5, 3, 3.5, 4]),
    ("bonus_assist", "Assist", True, [0, 0.5, 1, 1.5, 2]),
    ("malus_amm", "Ammonizione", True, [0, -0.25, -0.5, -1]),
    ("malus_esp", "Espulsione", True, [0, -0.5, -1, -2]),
    ("malus_gol_subito", "Gol subito (portiere)", True, [0, -0.5, -1]),
    ("bonus_imbattibilita", "Porta inviolata", False, [0, 0.5, 1, 1.5, 2]),
    ("bonus_rigore_parato", "Rigore parato", True, [0, 1, 2, 3]),
    ("malus_rigore_sbagliato", "Rigore sbagliato", True, [0, -1, -2, -3]),
    ("malus_autogol", "Autogol", False, [0, -1, -2, -3]),
]
UFFICIALI = {c for c, _, ufficiale, _ in REGOLE if ufficiale}
# Il valore che il regolamento ufficiale dà, per le voci che ci sono dentro: la
# tendina lo segna, così «(ufficiale)» dice **quale** numero lo è, non solo che
# la voce esiste nel regolamento.
VALORE_UFFICIALE = {
    "bonus_gol": 3, "bonus_assist": 1, "malus_amm": -0.5, "malus_esp": -1,
    "malus_gol_subito": -1, "bonus_rigore_parato": 3, "malus_rigore_sbagliato": -3,
}
# ⚠️ Con che valore nasce una lega nuova. **Non** è lo stesso dizionario di sopra:
# porta inviolata e autogol il regolamento non li fissa, ma un default ce l'hanno
# lo stesso — quello convenzionale, che è anche il `DEFAULT` scritto nella tabella.
# Il primo giro lasciava partire queste due da zero, cioè dal primo valore della
# tendina, e una lega nuova nasceva con l'autogol che non toglie niente: nessun
# errore, solo una regola sparita. L'ha preso la prova in browser.
VALORE_PARTENZA = dict(VALORE_UFFICIALE,
                       bonus_imbattibilita=1, malus_autogol=-2)


def _lega_mia(db, lid):
    """La lega `lid` **se è di chi sta guardando**, altrimenti `None`.

    Un punto solo per la domanda «questa lega è mia?»: ripeterla in sei route è il
    modo per dimenticarsela nella settima.
    """
    cond, par = ambito_utente()
    r = db.execute(f"SELECT * FROM fanta_leagues WHERE id=? AND {cond}",
                   (lid,) + tuple(par)).fetchone()
    return dict(r) if r else None


def _aggiorna(db, quale, forza_scrittura=False):
    """Rilegge dalla fonte e scrive. Torna `(messaggio, categoria)` per il flash.

    ⚠️ **Se la fonte non risponde, la sezione deve aprirsi lo stesso.** Questa
    funzione viene chiamata anche da una pagina che si sta semplicemente aprendo:
    un `requests` che va in timeout, o un sito che cambia forma, non possono
    diventare un errore 500 su una pagina che sa già cosa mostrare. Perciò ogni
    guaio esce da qui come **messaggio**, e il dato di prima resta dov'è.
    """
    # ⚠️ «in una tua rosa» dev'essere **tua**: da web c'è una sessione, e senza
    # questo l'avviso conterebbe le rose di tutti gli utenti (§1.1). La rosa non
    # ha un proprietario suo: lo eredita dalla lega, quindi il filtro è su quella.
    ambito = ambito_utente("l.user_id")
    try:
        if quale == "listone":
            r = I.aggiorna_listone(db, scarica=True, scrivi=True,
                                   forza=forza_scrittura, ambito=ambito)
            if not r["ok"]:
                return f"Listone non aggiornato: {r['motivo']}", "error"
            pezzi = [f"{r['letti']} giocatori"]
            if r["nuovi"]:
                pezzi.append(f"{len(r['nuovi'])} nuovi")
            if r["spenti"]:
                quanti = sum(1 for x in r["spenti"] if r["in_rosa"].get(x["id"]))
                pezzi.append(f"{len(r['spenti'])} usciti dalla Serie A" +
                             (f" ({quanti} in una tua rosa)" if quanti else ""))
            return "Listone aggiornato: " + ", ".join(pezzi), "success"

        r = I.aggiorna_probabili(db, scarica=True, scrivi=True,
                                 forza=forza_scrittura, ambito=ambito)
        if not r["ok"]:
            return f"Probabili non aggiornate: {r['motivo']}", "error"
        return (f"Probabili aggiornate: giornata {r['giornata']}, "
                f"{r['voci']} convocati, {r['squadre']} squadre"), "success"
    except Exception as e:
        # Il tipo dell'errore serve: «timeout» e «la pagina non ha più quella
        # forma» si rimediano in due modi diversi.
        return (f"Non sono riuscito a leggere fantacalcio.it "
                f"({type(e).__name__}). Il dato di prima è rimasto com'era.",
                "error")


def _aggiorna_se_vecchio(db, quale):
    """L'aggiornamento automatico entrando nella sezione. Torna il messaggio o `None`.

    ⚠️ Non aggiorna **a ogni visita**, e la ragione è che aprire la pagina
    significherebbe aspettare ogni volta che fantacalcio.it risponda — tre pagine
    da più di un mega. Aggiorna quando la copia è più vecchia della sua soglia
    (`fanta_import.VECCHIA_*`): una settimana per il listone, **tre ore** per le
    probabili, che cambiano fino al fischio d'inizio. Il pulsante «Aggiorna ora»
    resta per quando non si vuole aspettare la soglia.
    """
    serve, _ore = I.serve_aggiornare(db, quale)
    if not serve:
        return None
    messaggio, categoria = _aggiorna(db, quale)
    # Un aggiornamento automatico riuscito non merita un avviso: la pagina mostra
    # già la data del dato. Si parla solo quando è andato storto.
    return None if categoria == "success" else messaggio


def _giornata_probabili(db, chiesta=None):
    """La giornata da mostrare: quella chiesta, se c'è il dato, altrimenti l'ultima.

    ⚠️ **Non si inventa un numero.** Con l'archivio vuoto torna `None` e le pagine
    dicono che le probabili non sono state importate: un `1` di ripiego mostrerebbe
    una giornata vuota come se fosse una giornata senza convocati.
    """
    if chiesta:
        r = db.execute("SELECT giornata FROM fanta_probabili_squadre WHERE giornata=? "
                       "LIMIT 1", (chiesta,)).fetchone()
        if r:
            return r["giornata"]
    r = db.execute("SELECT MAX(giornata) AS g FROM fanta_probabili_squadre").fetchone()
    return r["g"] if r and r["g"] else None


def _probabili_della_rosa(db, giornata, rosa):
    """Attacca a ogni giocatore della rosa la sua probabile, se c'è.

    ⚠️ Un giocatore senza riga nelle probabili **non è «non convocato»**: può
    esserlo, oppure la sua squadra può non giocare quella giornata (rinvii,
    recuperi). Sono due cose diverse e la pagina le dice diverse, perché è
    esattamente il caso in cui un'etichetta sbagliata farebbe schierare un giocatore
    che non scende in campo. Chi decide è `fanta_probabili_squadre`: se la squadra
    è lì, la giornata la gioca.
    """
    if not giornata or not rosa:
        return {}
    squadre = {r["squadra_slug"]: dict(r) for r in db.execute(
        "SELECT * FROM fanta_probabili_squadre WHERE giornata=?", (giornata,)).fetchall()}
    ids = [g["id"] for g in rosa]
    segni = ",".join("?" * len(ids))
    righe = {r["player_id"]: dict(r) for r in db.execute(
        f"SELECT * FROM fanta_probabili WHERE giornata=? AND player_id IN ({segni})",
        [giornata] + ids).fetchall()}
    fuori = {}
    for g in rosa:
        squadra = squadre.get(g["squadra_slug"])
        voce = righe.get(g["id"])
        if voce:
            stato = "titolare" if voce["titolare"] else "panchina"
        elif squadra:
            stato = "fuori"          # la squadra gioca, lui non è fra i convocati
        else:
            stato = "non_gioca"      # la sua squadra non è in questa giornata
        fuori[g["id"]] = {"stato": stato,
                          "percentuale": (voce or {}).get("percentuale"),
                          "squadra": squadra}
    return fuori


def _numeri(f):
    """**Solo** le regole che il form ha davvero mandato, già convertite.

    ⚠️ Un campo vuoto non vale zero e non vale `None`: vale «non l'ho toccato», e
    quindi la colonna **non entra nella query**. Sono due bachi in uno, e la prova
    li ha presi tutti e due:

    - in `INSERT`, passare `None` per un campo non compilato **scavalca il `DEFAULT`
      della tabella**: una lega nuova nasceva con gol +NULL invece di +3, e nessuno
      dava errore — il bonus semplicemente non c'era;
    - in `UPDATE`, rimetterci il valore vecchio funziona, ma solo finché qualcuno
      non dimentica di passare `riga`. Non mettendo la colonna nel `SET`, il valore
      di prima resta perché non è stato toccato, che è la stessa cosa detta bene.
    """
    fuori = {}
    for colonna, _, _, _ in REGOLE:
        grezzo = f.get(colonna)
        # ⚠️ Dal 21/09/2026 ogni regola è una tendina, e la tendina manda sempre
        # qualcosa: `altro` vuol dire «guarda la casella qui accanto», che è
        # `<colonna>_altro`. Se anche quella è vuota la colonna **non entra nella
        # query** — la regola di sopra vale ancora, ed è quella che impedisce a un
        # campo lasciato stare di azzerare un bonus.
        if str(grezzo).strip() == "altro":
            grezzo = f.get(colonna + "_altro")
        if grezzo is None or str(grezzo).strip() == "":
            continue
        try:
            fuori[colonna] = float(str(grezzo).replace(",", "."))
        except ValueError:
            continue
    return fuori


@bp.route("/")
@login_required
def fantacalcio():
    db = get_db()
    # Entrando nella sezione: se la copia è più vecchia della sua soglia, si
    # rilegge. Non blocca la pagina se la fonte non risponde — il guaio diventa un
    # avviso e i numeri di prima restano.
    for quale in ("listone", "probabili"):
        guaio = _aggiorna_se_vecchio(db, quale)
        if guaio:
            flash(guaio, "error")
    di = _i(request.args.get("utente")) or None
    cond, par = ambito_utente(di=di)
    leghe = [dict(r) for r in db.execute(
        "SELECT l.*, (SELECT COUNT(*) FROM fanta_roster r WHERE r.league_id=l.id) "
        f"AS quanti FROM fanta_leagues l WHERE {cond} ORDER BY l.nome", par).fetchall()]
    listone = db.execute(
        "SELECT COUNT(*) AS attivi, MAX(visto_il) AS visto, "
        "(SELECT COUNT(*) FROM fanta_players WHERE attivo=0) AS spenti "
        "FROM fanta_players WHERE attivo=1").fetchone()
    # Lo stesso motivo per cui si dichiara la data del listone: una giornata vecchia
    # non dà errore, dà una formazione che non è più quella.
    stato_probabili = db.execute(
        "SELECT giornata, COUNT(*) AS quanti, MAX(aggiornato_il) AS quando "
        "FROM fanta_probabili GROUP BY giornata "
        "ORDER BY giornata DESC LIMIT 1").fetchone()
    nomi_utenti = {r["id"]: r["username"] for r in
                   db.execute("SELECT id, username FROM users")} if e_admin() else {}
    proprietari = []
    if e_admin():
        proprietari = [dict(r) for r in db.execute(
            "SELECT u.id, u.username, COUNT(l.id) AS quanti FROM users u "
            "JOIN fanta_leagues l ON l.user_id=u.id GROUP BY u.id, u.username "
            "ORDER BY u.username").fetchall()]
    eta = {q: I.serve_aggiornare(db, q)[1] for q in ("listone", "probabili")}
    db.close()
    return render_template("fantacalcio.html", leghe=leghe,
                           listone=dict(listone) if listone else {},
                           probabili=dict(stato_probabili) if stato_probabili else {},
                           regole=REGOLE, ufficiali=UFFICIALI,
                           valore_ufficiale=VALORE_UFFICIALE,
                           valore_partenza=VALORE_PARTENZA,
                           soglie_standard=MOD_DIFESA_SOGLIE,
                           soglie_lega={l["id"]: soglie_mod_difesa(
                               l.get("mod_difesa_soglie")) for l in leghe},
                           eta_cache=eta,
                           proprietari=proprietari, filtro_utente=di,
                           nomi_utenti=nomi_utenti)


@bp.route("/aggiorna/<quale>", methods=["POST"])
@login_required
def aggiorna(quale):
    """Il pulsante «Aggiorna ora»: rilegge dalla fonte adesso, senza aspettare.

    ⚠️ È un `POST` di proposito. Scarica tre pagine da fantacalcio.it e riscrive
    delle righe: un `GET` così si rifarebbe da solo a ogni ricarica del browser,
    e basterebbe tenere premuto F5 per martellare la fonte.
    """
    if quale not in ("listone", "probabili"):
        flash("Non so cosa aggiornare", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    db = get_db()
    messaggio, categoria = _aggiorna(db, quale)
    db.close()
    flash(messaggio, categoria)
    dove = request.form.get("torna_a")
    return redirect(dove if dove and dove.startswith("/fantacalcio")
                    else url_for("fantacalcio.fantacalcio"))


@bp.route("/lega/salva", methods=["POST"])
@login_required
def lega_salva():
    f = request.form
    lid = _i(f.get("lega_id", 0))
    nome = (f.get("nome") or "").strip()
    if not nome:
        flash("Il nome della lega è obbligatorio", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    moduli = (f.get("moduli") or "").strip()
    # ⚠️ Un modulo scritto male non si salva «tanto poi si vede»: senza questo
    # controllo la validazione della formazione direbbe di no a una rosa giusta.
    sbagliati = [m.strip() for m in moduli.split(",")
                 if m.strip() and not scomponi_modulo(m)]
    if sbagliati:
        flash(f"Moduli che non tornano (i dieci di movimento devono fare 10): "
              f"{', '.join(sbagliati)}", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    # Le soglie del modificatore di difesa arrivano come tre coppie media/punti.
    # ⚠️ Si salvano solo se ne è arrivata almeno una **leggibile**: una riga scritta
    # male non diventa una tabella a caso, si tiene quella di prima. Chi non tocca
    # niente non le manda affatto, e allora la colonna resta com'è.
    soglie = []
    for media, punti in zip(f.getlist("soglia_media"), f.getlist("soglia_punti")):
        media, punti = (media or "").strip(), (punti or "").strip()
        if not media or not punti:
            continue
        try:
            soglie.append((float(media.replace(",", ".")),
                           float(punti.replace(",", "."))))
        except ValueError:
            flash(f"Soglia del modificatore che non è un numero: «{media}: {punti}»",
                  "error")
            return redirect(url_for("fantacalcio.fantacalcio"))

    db = get_db()
    riga = _lega_mia(db, lid) if lid else None
    valori = _numeri(f)
    comuni = {
        "nome": nome,
        "sistema": "classic",
        "moduli": moduli or None,
        "n_panchinari": _i(f.get("n_panchinari"), 7),
        "mod_difesa": 1 if f.get("mod_difesa") else 0,
        "mod_difesa_portiere": 1 if f.get("mod_difesa_portiere") else 0,
        "note": (f.get("note") or "").strip() or None,
    }
    if soglie:
        comuni["mod_difesa_soglie"] = scrivi_soglie(
            sorted(soglie, key=lambda x: x[0], reverse=True))
    comuni.update(valori)

    if lid:
        if riga is None:
            db.close()
            flash("Lega non trovata", "error")
            return redirect(url_for("fantacalcio.fantacalcio"))
        cond, par = solo_mie()
        sets = ", ".join(f"{c}=?" for c in comuni)
        cur = db.execute(f"UPDATE fanta_leagues SET {sets} WHERE id=? AND {cond}",
                         list(comuni.values()) + [lid] + list(par))
        if cur.rowcount == 0:
            db.close()
            flash("Lega non trovata", "error")
            return redirect(url_for("fantacalcio.fantacalcio"))
    else:
        comuni["user_id"] = utente_id()
        colonne = ", ".join(comuni)
        segni = ", ".join("?" * len(comuni))
        db.execute(f"INSERT INTO fanta_leagues({colonne}) VALUES({segni})",
                   list(comuni.values()))
    db.commit()
    db.close()
    flash("Salvato", "success")
    return redirect(url_for("fantacalcio.fantacalcio"))


@bp.route("/lega/<int:lid>/elimina", methods=["POST"])
@login_required
def lega_elimina(lid):
    db = get_db()
    cond, par = solo_mie()
    # La rosa se ne va con la lega: `ON DELETE CASCADE` sullo schema, ma SQLite lo
    # applica solo con i foreign key accesi, quindi la si toglie qui a mano.
    db.execute("DELETE FROM fanta_roster WHERE league_id IN "
               f"(SELECT id FROM fanta_leagues WHERE id=? AND {cond})",
               (lid,) + tuple(par))
    cur = db.execute(f"DELETE FROM fanta_leagues WHERE id=? AND {cond}",
                     (lid,) + tuple(par))
    db.commit()
    db.close()
    flash("Eliminata" if cur.rowcount else "Lega non trovata",
          "success" if cur.rowcount else "error")
    return redirect(url_for("fantacalcio.fantacalcio"))


@bp.route("/lega/<int:lid>")
@login_required
def lega(lid):
    db = get_db()
    # Anche qui: la pagina mostra le probabili della rosa, quindi vale la stessa
    # regola dell'elenco: se la copia ha più di tre ore si rilegge.
    guaio = _aggiorna_se_vecchio(db, "probabili")
    if guaio:
        flash(guaio, "error")
    riga = _lega_mia(db, lid)
    if riga is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    # ⚠️ La rosa si legge **passando dalla lega**: `fanta_roster` non ha un
    # proprietario suo, quindi una SELECT diretta sarebbe scoperta (§1.1).
    cond, par = ambito_utente("l.user_id")
    rosa = [dict(r) for r in db.execute(
        "SELECT r.id AS rid, r.prezzo, r.note, p.* FROM fanta_roster r "
        "JOIN fanta_leagues l ON l.id = r.league_id "
        "JOIN fanta_players p ON p.id = r.player_id "
        f"WHERE r.league_id=? AND {cond} "
        "ORDER BY CASE p.ruolo_classic WHEN 'p' THEN 0 WHEN 'd' THEN 1 "
        "WHEN 'c' THEN 2 ELSE 3 END, p.nome",
        (lid,) + tuple(par)).fetchall()]

    # Le probabili della giornata, attaccate alla rosa. Dato condiviso: non passa
    # da `ambito_utente()` perché le formazioni della Serie A non sono di nessuno.
    giornata = _giornata_probabili(db, _i(request.args.get("giornata")))
    probabili = _probabili_della_rosa(db, giornata, rosa)
    aggiornate = db.execute("SELECT MAX(aggiornato_il) AS q FROM fanta_probabili "
                            "WHERE giornata=?", (giornata,)).fetchone() if giornata else None
    db.close()

    per_ruolo = {r: [g for g in rosa if g["ruolo_classic"] == r]
                 for r in ORDINE_RUOLI_FANTA}
    spenti = [g for g in rosa if not g["attivo"]]
    moduli = [m.strip() for m in (riga.get("moduli") or "").split(",") if m.strip()]
    # Quanti ne servirebbero per ogni modulo ammesso, e se la rosa ci arriva.
    copertura = []
    for m in moduli:
        serve = scomponi_modulo(m)
        if not serve:
            continue
        mancano = {r: serve[r] - len([g for g in per_ruolo[r] if g["attivo"]])
                   for r in ORDINE_RUOLI_FANTA}
        copertura.append({"modulo": m, "serve": serve,
                          "mancano": {r: n for r, n in mancano.items() if n > 0}})
    speso = sum(g["prezzo"] or 0 for g in rosa)
    return render_template("fanta_lega.html", lega=riga, rosa=rosa,
                           per_ruolo=per_ruolo, ruoli=RUOLI_FANTA,
                           ordine=ORDINE_RUOLI_FANTA, spenti=spenti,
                           copertura=copertura, speso=speso,
                           regole=REGOLE, ufficiali=UFFICIALI,
                           valore_ufficiale=VALORE_UFFICIALE,
                           soglie=soglie_mod_difesa(riga.get("mod_difesa_soglie")),
                           soglie_standard=MOD_DIFESA_SOGLIE,
                           esempi_difesa=[(m, modificatore_difesa(
                               m, soglie_mod_difesa(riga.get("mod_difesa_soglie"))))
                               for m in (5.5, 6.0, 6.5, 7.0, 7.5)],
                           giornata=giornata, probabili=probabili,
                           probabili_aggiornate=(aggiornate["q"] if aggiornate else None))


def _rosa_della_lega(db, lid):
    """La rosa, coi campi che servono a schierare. Passa **dalla lega** (§1.1)."""
    cond, par = ambito_utente("l.user_id")
    return [dict(r) for r in db.execute(
        "SELECT r.prezzo, p.* FROM fanta_roster r "
        "JOIN fanta_leagues l ON l.id = r.league_id "
        "JOIN fanta_players p ON p.id = r.player_id "
        f"WHERE r.league_id=? AND {cond} "
        "ORDER BY CASE p.ruolo_classic WHEN 'p' THEN 0 WHEN 'd' THEN 1 "
        "WHEN 'c' THEN 2 ELSE 3 END, p.nome",
        (lid,) + tuple(par)).fetchall()]


@bp.route("/lega/<int:lid>/formazione")
@login_required
def formazione(lid):
    """Il campo da gioco: si schiera qui, ed è di questa lega.

    ⚠️ Una formazione sola per lega, senza giornata: è la scelta di Davide del
    21/09/2026. Le **probabili** invece la giornata ce l'hanno, e si vedono accanto
    a ogni giocatore mentre si schiera — è tutto il motivo per cui sono state fatte
    prima di questa pagina.
    """
    db = get_db()
    guaio = _aggiorna_se_vecchio(db, "probabili")
    if guaio:
        flash(guaio, "error")
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    rosa = _rosa_della_lega(db, lid)
    giornata = _giornata_probabili(db)
    probabili = _probabili_della_rosa(db, giornata, rosa)
    schierati = {r["player_id"]: dict(r) for r in db.execute(
        "SELECT * FROM fanta_formazione WHERE league_id=? ORDER BY titolare DESC, ordine",
        (lid,)).fetchall()}
    db.close()

    moduli = [m.strip() for m in (lega.get("moduli") or "").split(",")
              if m.strip() and scomponi_modulo(m.strip())]
    # Il modulo da mostrare: quello salvato se è ancora fra gli ammessi, altrimenti
    # il primo. ⚠️ Un modulo tolto dalle regole dopo aver schierato lascerebbe la
    # pagina su un modulo che la lega non ammette più, e il salvataggio lo
    # rifiuterebbe senza che si capisca perché.
    scelto = lega.get("modulo_scelto")
    if scelto not in moduli:
        scelto = moduli[0] if moduli else None

    per_ruolo = {r: [g for g in rosa if g["ruolo_classic"] == r]
                 for r in ORDINE_RUOLI_FANTA}
    return render_template(
        "fanta_formazione.html", lega=lega, rosa=rosa, per_ruolo=per_ruolo,
        ruoli=RUOLI_FANTA, ordine=ORDINE_RUOLI_FANTA, moduli=moduli,
        modulo=scelto, schierati=schierati, probabili=probabili,
        giornata=giornata,
        reparti={m: scomponi_modulo(m) for m in moduli})


@bp.route("/lega/<int:lid>/formazione/salva", methods=["POST"])
@login_required
def formazione_salva(lid):
    """Salva la formazione, **se torna**.

    Davide ha scelto la validazione severa: quello che non torna non si salva,
    come già succede a un modulo scritto male. ⚠️ Il ruolo di ogni giocatore lo
    decide la **rosa**, non il form: un `ruolo` mandato dal browser direbbe che
    un attaccante è un difensore, e il conto dei reparti tornerebbe lo stesso.
    """
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    modulo = (request.form.get("modulo") or "").strip()
    titolari = [_i(x) for x in request.form.getlist("titolare") if _i(x)]
    panchinari = [_i(x) for x in request.form.getlist("panchinaro") if _i(x)]
    rosa = {g["id"]: g["ruolo_classic"] for g in _rosa_della_lega(db, lid)}

    ammessi = [m.strip() for m in (lega.get("moduli") or "").split(",") if m.strip()]
    guai = []
    if ammessi and modulo not in ammessi:
        guai.append(f"Il modulo {modulo or '—'} non è fra quelli ammessi da questa "
                    f"lega ({', '.join(ammessi)}).")
    guai += controlla_formazione(modulo, titolari, panchinari, rosa,
                                 lega.get("n_panchinari"))
    if guai:
        db.close()
        for g in guai:
            flash(g, "error")
        return redirect(url_for("fantacalcio.formazione", lid=lid))

    # Si riscrive per intero: una formazione è una cosa sola, e aggiornarla riga
    # per riga vorrebbe dire poter lasciare in campo qualcuno che è stato tolto.
    # ⚠️ Due forme della stessa condizione, e non sono intercambiabili: `UPDATE`
    # non ha un alias, quindi vuole la colonna nuda. Scritta con l'alias dà
    # «no such column: l.user_id» — l'ha presa la prova al primo giro.
    cond, par = solo_mie()
    db.execute("DELETE FROM fanta_formazione WHERE league_id=? AND league_id IN "
               f"(SELECT id FROM fanta_leagues WHERE id=? AND {cond})",
               (lid, lid) + tuple(par))
    db.executemany(
        "INSERT INTO fanta_formazione(league_id, player_id, titolare, ordine, ruolo)"
        " VALUES(?,?,?,?,?)",
        [(lid, p, 1, i, rosa.get(p)) for i, p in enumerate(titolari)] +
        [(lid, p, 0, i, rosa.get(p)) for i, p in enumerate(panchinari)])
    cur = db.execute(f"UPDATE fanta_leagues SET modulo_scelto=? WHERE id=? AND {cond}",
                     (modulo, lid) + tuple(par))
    if cur.rowcount == 0:
        # La lega non è di chi salva: la formazione appena scritta non deve
        # restare. ⚠️ `_lega_mia()` l'aveva già detto in cima, ma qui si guarda il
        # `rowcount` perché una scrittura che non tocca niente **non dà errore**.
        db.execute("DELETE FROM fanta_formazione WHERE league_id=?", (lid,))
        db.commit()
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    db.commit()
    db.close()
    flash(f"Formazione salvata: {modulo}, {len(titolari)} titolari e "
          f"{len(panchinari)} in panchina", "success")
    return redirect(url_for("fantacalcio.formazione", lid=lid))


@bp.route("/lega/<int:lid>/rosa/aggiungi", methods=["POST"])
@login_required
def rosa_aggiungi(lid):
    pid = _i(request.form.get("player_id"))
    db = get_db()
    if _lega_mia(db, lid) is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    esiste = db.execute("SELECT nome FROM fanta_players WHERE id=?", (pid,)).fetchone()
    if not esiste:
        db.close()
        flash("Giocatore non trovato nel listone", "error")
        return redirect(url_for("fantacalcio.lega", lid=lid))
    try:
        prezzo = float(str(request.form.get("prezzo") or 0).replace(",", "."))
    except ValueError:
        prezzo = 0.0
    try:
        db.execute("INSERT INTO fanta_roster(league_id, player_id, prezzo, note) "
                   "VALUES(?,?,?,?)",
                   (lid, pid, prezzo, (request.form.get("note") or "").strip() or None))
        db.commit()
        flash(f"{esiste['nome']} aggiunto", "success")
    except Exception:
        # L'unico vincolo qui è UNIQUE(league_id, player_id): averlo già in rosa
        # non è un errore da mostrare come tale.
        flash(f"{esiste['nome']} è già in questa rosa", "error")
    db.close()
    return redirect(url_for("fantacalcio.lega", lid=lid))


@bp.route("/lega/<int:lid>/rosa/<int:rid>/rimuovi", methods=["POST"])
@login_required
def rosa_rimuovi(lid, rid):
    db = get_db()
    cond, par = solo_mie("l.user_id")
    cur = db.execute(
        "DELETE FROM fanta_roster WHERE id=? AND league_id=? AND league_id IN "
        f"(SELECT l.id FROM fanta_leagues l WHERE {cond})",
        (rid, lid) + tuple(par))
    db.commit()
    db.close()
    flash("Tolto dalla rosa" if cur.rowcount else "Non trovato",
          "success" if cur.rowcount else "error")
    return redirect(url_for("fantacalcio.lega", lid=lid))


def _listone(db):
    """Il listone intero, coi campi che servono ad abbinare un nome incollato.

    Dato **condiviso** come il catalogo Pokémon: non passa da `ambito_utente()` e
    non deve. Sono 597 righe (misurate il 21/09/2026) e si leggono in una volta
    perché l'abbinamento deve poter dire «questo nome ne trova due»: una query per
    riga incollata non saprebbe mai quanti omonimi ci sono.
    """
    return [dict(r) for r in db.execute(
        "SELECT id, nome, squadra, squadra_slug, ruolo_classic, qa, fvm, "
        "fantamedia, attivo FROM fanta_players").fetchall()]


def _ids_in_rosa(db, lid):
    """Gli id già in quella rosa. Passa **dalla lega**, come ogni lettura di §1.1."""
    cond, par = ambito_utente("l.user_id")
    return {r["player_id"] for r in db.execute(
        "SELECT r.player_id FROM fanta_roster r "
        "JOIN fanta_leagues l ON l.id = r.league_id "
        f"WHERE r.league_id=? AND {cond}", (lid,) + tuple(par)).fetchall()}


@bp.route("/lega/<int:lid>/rosa/incolla", methods=["POST"])
@login_required
def rosa_incolla(lid):
    """L'anteprima della rosa incollata: **legge e mostra, non scrive niente.**

    Una rosa sono ~25 giocatori e la ricerca ne aggiunge uno per volta: è il
    motivo per cui questa pagina esiste. Il passo in due tempi però non è una
    comodità, è la parte che la rende sicura — l'abbinamento di un nome può
    sbagliare **senza dare errore** (`Thuram` sono due giocatori in due squadre e
    due ruoli), e l'unico modo di accorgersene è vederlo prima che sia scritto.

    ⚠️ È un `POST` anche se non scrive: il testo incollato è un dato, non un
    parametro da mettere in un URL, e una rosa di venticinque nomi in querystring
    sarebbe anche troppo lunga.
    """
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    testo = request.form.get("testo") or ""
    righe = leggi_rosa_incollata(testo, _listone(db), _ids_in_rosa(db, lid))
    db.close()
    if not righe:
        flash("Non ho letto nessun nome: incolla una riga per giocatore", "error")
        return redirect(url_for("fantacalcio.lega", lid=lid))
    conto = {s: len([r for r in righe if r["stato"] == s])
             for s in ("ok", "conferma", "scegli", "niente")}
    return render_template("fanta_rosa_incolla.html", lega=lega, righe=righe,
                           testo=testo, conto=conto, ruoli=RUOLI_FANTA)


@bp.route("/lega/<int:lid>/rosa/incolla/conferma", methods=["POST"])
@login_required
def rosa_incolla_conferma(lid):
    """Scrive in rosa **solo** le righe spuntate, e dice riga per riga com'è andata.

    ⚠️ Di quello che torna dal browser non si fida niente: il `player_id` viene
    ricontrollato nel listone (un id inventato non entra) e la lega è la solita
    `_lega_mia()`. Il nome che l'anteprima mostrava non viene nemmeno riletto —
    quello che conta è l'id, come per l'incrocio delle tre pagine della fonte.
    """
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    validi = {r["id"] for r in db.execute("SELECT id FROM fanta_players").fetchall()}
    indici = sorted({_i(k[4:]) for k in request.form if k.startswith("pid_")
                     and _i(k[4:]) is not None})
    aggiunti, saltati, ignoti = 0, 0, 0
    for n in indici:
        if not request.form.get(f"riga_{n}"):
            continue                      # la spunta è la decisione: senza, non si scrive
        pid = _i(request.form.get(f"pid_{n}"))
        if pid is None or pid not in validi:
            ignoti += 1
            continue
        try:
            prezzo = float(str(request.form.get(f"prezzo_{n}") or 0).replace(",", "."))
        except ValueError:
            prezzo = 0.0
        try:
            db.execute("INSERT INTO fanta_roster(league_id, player_id, prezzo) "
                       "VALUES(?,?,?)", (lid, pid, prezzo))
            aggiunti += 1
        except Exception:
            # L'unico vincolo è UNIQUE(league_id, player_id): averlo già in rosa
            # non è un errore, è una riga che non serve.
            saltati += 1
    db.commit()
    db.close()
    pezzi = [f"{aggiunti} in rosa"]
    if saltati:
        pezzi.append(f"{saltati} già in rosa da prima")
    if ignoti:
        pezzi.append(f"{ignoti} senza un giocatore valido")
    flash(", ".join(pezzi), "success" if aggiunti else "error")
    return redirect(url_for("fantacalcio.lega", lid=lid))


@bp.route("/probabili")
@login_required
def probabili():
    """Le probabili della giornata, partita per partita, coi **tuoi** segnati.

    Le formazioni sono un dato condiviso e si leggono senza filtro. Quello che
    invece è tuo è **quali di quei giocatori hai in rosa**, e quella parte passa da
    `ambito_utente()` sulle leghe: `fanta_roster` non ha un proprietario suo (§1.1).
    """
    db = get_db()
    # ⚠️ Solo quando si guarda l'**ultima** giornata: chiedere una giornata
    # passata è guardare l'archivio, e rileggere la fonte lì vorrebbe dire
    # riscrivere la giornata di oggi mentre si guarda quella di ieri.
    if not _i(request.args.get("giornata")):
        guaio = _aggiorna_se_vecchio(db, "probabili")
        if guaio:
            flash(guaio, "error")
    giornata = _giornata_probabili(db, _i(request.args.get("giornata")))
    giornate = [r["giornata"] for r in db.execute(
        "SELECT DISTINCT giornata FROM fanta_probabili_squadre ORDER BY giornata DESC")]
    squadre, voci, miei, aggiornate = {}, {}, {}, None
    if giornata:
        squadre = {r["squadra_slug"]: dict(r) for r in db.execute(
            "SELECT * FROM fanta_probabili_squadre WHERE giornata=? "
            "ORDER BY match_id, in_casa DESC", (giornata,)).fetchall()}
        for r in db.execute(
                "SELECT * FROM fanta_probabili WHERE giornata=? "
                "ORDER BY titolare DESC, CASE ruolo WHEN 'p' THEN 0 WHEN 'd' THEN 1 "
                "WHEN 'c' THEN 2 ELSE 3 END, percentuale DESC, nome", (giornata,)):
            voci.setdefault(r["squadra_slug"], []).append(dict(r))
        cond, par = ambito_utente("l.user_id")
        for r in db.execute(
                "SELECT r.player_id, l.id AS lid, l.nome AS lega FROM fanta_roster r "
                f"JOIN fanta_leagues l ON l.id=r.league_id WHERE {cond}", par):
            miei.setdefault(r["player_id"], []).append(
                {"lid": r["lid"], "lega": r["lega"]})
        fila = db.execute("SELECT MAX(aggiornato_il) AS q FROM fanta_probabili "
                          "WHERE giornata=?", (giornata,)).fetchone()
        aggiornate = fila["q"] if fila else None
    db.close()

    # Una voce per partita: le squadre stanno nel DB una per riga, e l'avversario
    # ce l'hanno dentro. Si rimettono insieme per `match_id`, non per nome.
    partite, viste = [], set()
    for slug, s in squadre.items():
        if slug in viste:
            continue
        altro = squadre.get(s["avversario_slug"] or "")
        casa, fuori = (s, altro) if s["in_casa"] else (altro, s)
        viste.update({slug, s["avversario_slug"]})
        partite.append({"casa": casa, "fuori": fuori,
                        "match_id": s["match_id"]})
    return render_template("fanta_probabili.html", giornata=giornata,
                           giornate=giornate, partite=partite, voci=voci,
                           miei=miei, ruoli=RUOLI_FANTA, aggiornate=aggiornate)


@bp.route("/api/giocatori")
@login_required
def api_giocatori():
    """I giocatori del listone che combaciano con `q`. Dato condiviso, non filtrato.

    ⚠️ Gli spenti restano cercabili ma **dichiarati**: servono quando si ricostruisce
    una rosa vecchia, e nasconderli farebbe sembrare che il giocatore non sia mai
    esistito.
    """
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    db = get_db()
    righe = db.execute(
        "SELECT id, nome, squadra, ruolo_classic, qa, fvm, fantamedia, attivo "
        "FROM fanta_players WHERE nome LIKE ? "
        "ORDER BY attivo DESC, fvm DESC, nome LIMIT 25", (f"%{q}%",)).fetchall()
    db.close()
    return jsonify([dict(r) for r in righe])
