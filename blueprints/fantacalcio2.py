"""La Fantacalcio 2: la stessa sezione, con fonti che si possono usare.

§4.6 del backlog, 24/09/2026. Decisione di Davide: le fonti nuove si provano in una
sezione **a parte**, e la prima resta com'è per poterci tornare. Quindi qui:

- il **listone** arriva dai due Excel che Davide scarica col suo login e carica da
  questa pagina — nessun programma legge fantacalcio.it;
- **calendario e classifica** da football-data.org, con la sua chiave;
- le **probabili** non ci sono: un link le apre nel browser di chi guarda.

⚠️ **Tabelle sue, tutte** (`fanta2_*`), listone compreso: la prima sezione riscrive
il suo da sola entrando, e con una tabella in comune le due si sovrascriverebbero.

⚠️ **Di chi sono i dati**, esattamente come nella prima sezione: listone,
calendario e classifica sono condivisi; leghe, rose e formazioni sono **tue**, ogni
lettura passa da `ambito_utente()` e ogni scrittura da `solo_mie()`. Rosa e
formazione non hanno un `user_id`: lo ereditano dalla lega, quindi le loro query
passano **dalla lega** (§1.1). E ogni `UPDATE`/`DELETE` filtrato guarda il
`rowcount`.

⚠️ Le regole delle leghe (`REGOLE` e i valori ufficiali) si **importano** dalla
prima sezione invece di ricopiarle: sono le stesse, e due copie divergono. Il
giorno che la prima sezione si spegne, vanno spostate — è scritto nel backlog.
"""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify)

from extensions import (get_db, login_required, _i, ambito_utente, solo_mie,
                        utente_id, e_admin)
from data import (RUOLI_FANTA, ORDINE_RUOLI_FANTA, nome_ruolo, scomponi_modulo,
                  quanti_guai, MOD_DIFESA_SOGLIE, MOD_DIFESA_SOGLIE_QUARTI,
                  fasce_mod_difesa, soglie_mod_difesa, scrivi_soglie,
                  modificatore_difesa, controlla_formazione, leggi_rosa_incollata,
                  MINIMO_PARTITE_FIDATO)
from blueprints.fantacalcio import (REGOLE, UFFICIALI, VALORE_UFFICIALE,
                                    VALORE_PARTENZA, _prezzo, _numeri)
import fanta2 as G
import fanta2_fonti as F

bp = Blueprint("fantacalcio2", __name__, url_prefix="/fantacalcio2")

# Dove si guardano le probabili: la pagina **si apre nel browser** di chi guarda,
# che è l'uso che i termini di fantacalcio.it permettono (art. 9.3, «visualizzare»).
LINK_PROBABILI = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
# Dove si scaricano i due file, per chi non se lo ricorda: servono il login.
LINK_QUOTAZIONI = "https://www.fantacalcio.it/quotazioni-fantacalcio"
LINK_STATISTICHE = "https://www.fantacalcio.it/statistiche-serie-a"


def _torna(lid=None):
    return redirect(url_for("fantacalcio2.lega", lid=lid) if lid
                    else url_for("fantacalcio2.fantacalcio2"))


def _lega_mia(db, lid):
    """La lega `lid` **se è di chi sta guardando**, altrimenti `None`."""
    cond, par = ambito_utente()
    r = db.execute(f"SELECT * FROM fanta2_leagues WHERE id=? AND {cond}",
                   (lid,) + tuple(par)).fetchone()
    return dict(r) if r else None


def _rosa_della_lega(db, lid):
    """La rosa col listone dentro. Passa **dalla lega** (§1.1)."""
    cond, par = ambito_utente("l.user_id")
    return [dict(r) for r in db.execute(
        "SELECT r.id AS rid, r.prezzo, r.note, p.* FROM fanta2_roster r "
        "JOIN fanta2_leagues l ON l.id = r.league_id "
        "JOIN fanta2_players p ON p.id = r.player_id "
        f"WHERE r.league_id=? AND {cond} "
        "ORDER BY CASE p.ruolo_classic WHEN 'p' THEN 0 WHEN 'd' THEN 1 "
        "WHEN 'c' THEN 2 ELSE 3 END, p.nome",
        (lid,) + tuple(par)).fetchall()]


def _schierati(db, lid):
    """Chi è schierato in questa lega. ⚠️ Non filtra per proprietario e non deve:
    chi chiama ha già letto la lega con `_lega_mia()` o `ambito_utente()` (§1.1)."""
    return {r["player_id"]: dict(r) for r in db.execute(
        "SELECT player_id, titolare, ordine FROM fanta2_formazione WHERE league_id=? "
        "ORDER BY titolare DESC, ordine", (lid,)).fetchall()}


def _scendi_dal_campo(db, lid, player_ids):
    """Chi esce dalla rosa esce anche dal campo: sono due tabelle, e un DELETE sulla
    prima lascerebbe dei titolari che non ci sono più. Il chiamante ha già
    cancellato **con il filtro del proprietario** e guardato il `rowcount`."""
    if not player_ids:
        return 0
    segni = ",".join("?" * len(player_ids))
    return db.execute(
        f"DELETE FROM fanta2_formazione WHERE league_id=? AND player_id IN ({segni})",
        (lid,) + tuple(player_ids)).rowcount


def _calendario_se_vecchio(db):
    """Aggiorna calendario e classifica se hanno più di un giorno. Messaggio o `None`.

    Qui l'aggiornamento automatico entrando è permesso — è un'API con chiave, non
    una pagina da leggere. ⚠️ Se non risponde la sezione si apre lo stesso col dato
    di prima: il guaio diventa un avviso, non un errore 500.
    """
    eta = G.eta_calendario(db)
    if eta is not None and eta < G.VECCHIO_CALENDARIO:
        return None
    if not F.chiave_api():
        return None           # la pagina lo dice già nel riquadro del calendario
    messaggio, categoria = _aggiorna_calendario(db)
    return None if categoria == "success" else messaggio


def _aggiorna_calendario(db):
    try:
        r = G.aggiorna_calendario(db)
    except Exception as e:
        return (f"Non sono riuscito a leggere football-data.org ({type(e).__name__}). "
                "Il calendario di prima è rimasto com'era."), "error"
    if not r["ok"]:
        return f"Calendario non aggiornato: {r['motivo']}", "error"
    testo = (f"Calendario aggiornato: {r['partite']} partite, {r['con_ora']} con "
             "l'ora esatta")
    if r["non_abbinate"]:
        return (testo + ". ⚠️ Squadre che non trovo nel listone: " +
                ", ".join(r["non_abbinate"])), "error"
    if r.get("senza_listone"):
        return (testo + ". ⚠️ Il listone è vuoto, quindi le squadre non sono "
                "abbinate: carica i due Excel e riaggiorna il calendario."), "error"
    return testo, "success"


def _contesto_giornata(db):
    """Giornata, partite e classifica: servono a tre pagine, si leggono in un posto."""
    giornata = G.giornata_corrente(db)
    calendario_c_e = bool(db.execute(
        "SELECT 1 FROM fanta2_calendario LIMIT 1").fetchone())
    return {"giornata": giornata,
            "partite": G.partite_della_giornata(db, giornata),
            "tabella": G.classifica(db),
            "calendario_c_e": calendario_c_e,
            "scadenza": G.scadenza(db, giornata)}


def _scelte(db, giornata):
    """`{player_id: stato}`: chi gioca **secondo te**, per quella giornata.

    ⚠️ `solo_mie()` e non `ambito_utente()`, anche in lettura: per un admin
    `ambito_utente()` vuol dire «tutti», e il suo consiglio mescolerebbe le scelte di
    altri utenti con le sue — due persone possono pensarla diversamente sullo stesso
    giocatore, ed è per questo che la tabella ha un `user_id`.
    """
    if not giornata:
        return {}
    cond, par = solo_mie()
    return {r["player_id"]: r["stato"] for r in db.execute(
        f"SELECT player_id, stato FROM fanta2_titolari WHERE giornata=? AND {cond}",
        (giornata,) + tuple(par))}


def _valuta(db, lega, rosa, ctx):
    return G.valuta_rosa(rosa, ctx["partite"], ctx["tabella"], lega,
                         ctx["calendario_c_e"], _scelte(db, ctx["giornata"]))


def _allerta(db, lid, rosa, valutazioni):
    """Cosa non torna nella formazione salvata, o `None` se non c'è niente da dire."""
    schierati = _schierati(db, lid)
    if not schierati:
        return None
    nomi = {g["id"]: g["nome"] for g in rosa}
    mancanti = [p for p in schierati if p not in nomi]
    if mancanti:
        segni = ",".join("?" * len(mancanti))
        nomi.update({r["id"]: r["nome"] for r in db.execute(
            f"SELECT id, nome FROM fanta2_players WHERE id IN ({segni})",
            mancanti).fetchall()})
    allerta = G.controlla_schierati(schierati, valutazioni, nomi,
                                    {g["id"] for g in rosa})
    # La formazione si salva anche a metà (25/09/2026): quello che manca si dice qui,
    # contando solo chi è ancora in rosa — chi se n'è andato è già fra gli `spariti`.
    lega = db.execute("SELECT modulo_scelto, n_panchinari FROM fanta2_leagues "
                      "WHERE id=?", (lid,)).fetchone()
    ruoli = {g["id"]: g["ruolo_classic"] for g in rosa}
    in_rosa = [(p, r) for p, r in schierati.items() if p in ruoli]
    _, allerta["mancano"] = G.controlla_formazione_larga(
        lega["modulo_scelto"] if lega else None,
        [p for p, r in in_rosa if r.get("titolare")],
        [p for p, r in in_rosa if not r.get("titolare")],
        ruoli, lega["n_panchinari"] if lega else None)
    return allerta if _quanti(allerta) else None


def _quanti(allerta):
    """Le cose da guardare: quelle della prima sezione più quello che **manca**."""
    return quanti_guai(allerta) + len((allerta or {}).get("mancano") or ())


@bp.route("/")
@login_required
def fantacalcio2():
    db = get_db()
    guaio = _calendario_se_vecchio(db)
    if guaio:
        flash(guaio, "error")
    di = _i(request.args.get("utente")) or None
    cond, par = ambito_utente(di=di)
    leghe = [dict(r) for r in db.execute(
        "SELECT l.*, (SELECT COUNT(*) FROM fanta2_roster r WHERE r.league_id=l.id) "
        f"AS quanti FROM fanta2_leagues l WHERE {cond} ORDER BY l.nome", par).fetchall()]
    listone = db.execute(
        "SELECT COUNT(*) AS attivi, MAX(visto_il) AS visto, "
        "(SELECT COUNT(*) FROM fanta2_players WHERE attivo=0) AS spenti "
        "FROM fanta2_players WHERE attivo=1").fetchone()
    proprietari, nomi_utenti = [], {}
    if e_admin():
        nomi_utenti = {r["id"]: r["username"] for r in
                       db.execute("SELECT id, username FROM users")}
        proprietari = [dict(r) for r in db.execute(
            "SELECT u.id, u.username, COUNT(l.id) AS quanti FROM users u "
            "JOIN fanta2_leagues l ON l.user_id=u.id GROUP BY u.id, u.username "
            "ORDER BY u.username").fetchall()]
    ctx = _contesto_giornata(db)
    guai_lega = {}
    for l in leghe:
        rosa_l = _rosa_della_lega(db, l["id"])
        quanti = _quanti(_allerta(db, l["id"], rosa_l, _valuta(db, l, rosa_l, ctx)))
        if quanti:
            guai_lega[l["id"]] = quanti
    eta = G.eta_calendario(db)
    db.close()
    return render_template(
        "fantacalcio2.html", leghe=leghe, listone=dict(listone) if listone else {},
        regole=REGOLE, ufficiali=UFFICIALI, valore_ufficiale=VALORE_UFFICIALE,
        valore_partenza=VALORE_PARTENZA, soglie_standard=MOD_DIFESA_SOGLIE,
        soglie_quarti=MOD_DIFESA_SOGLIE_QUARTI,
        soglie_lega={l["id"]: soglie_mod_difesa(l.get("mod_difesa_soglie"))
                     for l in leghe},
        guai_lega=guai_lega, scadenza=ctx["scadenza"], giornata=ctx["giornata"],
        eta_calendario=eta, chiave=bool(F.chiave_api()),
        variabile_chiave=F.VARIABILE_CHIAVE, attribuzione=F.ATTRIBUZIONE,
        link_probabili=LINK_PROBABILI, link_quotazioni=LINK_QUOTAZIONI,
        link_statistiche=LINK_STATISTICHE,
        proprietari=proprietari, filtro_utente=di, nomi_utenti=nomi_utenti)


@bp.route("/listone/carica", methods=["POST"])
@login_required
def carica_listone():
    """I due Excel, caricati da chi li ha scaricati. **Letti e non salvati.**

    ⚠️ I file restano in memoria il tempo di leggerli: sono contenuti di
    fantacalcio.it presi con un account, e scriverli su disco in una cartella del
    progetto sarebbe il primo passo per ritrovarli su GitHub.
    """
    a = request.files.get("file_a")
    b = request.files.get("file_b")
    fq, fs, problemi = G.leggi_i_due_file(a.read() if a else None,
                                          b.read() if b else None)
    for p in problemi:
        flash(p, "error")
    if problemi:
        return _torna()
    db = get_db()
    r = G.importa_listone(db, fq, fs, forza=bool(request.form.get("forza")),
                          ambito=ambito_utente("l.user_id"))
    db.close()
    if not r["ok"]:
        flash(f"Listone non caricato: {r['motivo']}", "error")
        return _torna()
    pezzi = [f"{r['letti'] - r['ceduti']} in Serie A", f"{r['ceduti']} ceduti"]
    if r["nuovi"]:
        pezzi.append(f"{len(r['nuovi'])} nuovi")
    if r["cambiati"]:
        pezzi.append(f"{r['cambiati']} cambiati")
    if r["spenti"]:
        pezzi.append(f"{len(r['spenti'])} non più nel file")
    if r["in_rosa"]:
        pezzi.append(f"{len(r['in_rosa'])} di quelli usciti sono in una tua rosa")
    flash("Listone caricato: " + ", ".join(pezzi), "success")
    if r["senza_statistiche"] or r["solo_statistiche"]:
        flash(f"{r['senza_statistiche']} giocatori senza statistiche, "
              f"{len(r['solo_statistiche'])} solo nelle statistiche (non entrano)",
              "error")
    return _torna()


@bp.route("/calendario/aggiorna", methods=["POST"])
@login_required
def aggiorna_calendario():
    """«Aggiorna ora»: un POST, perché scrive e chiama un'API con un limite al
    minuto — un GET si rifarebbe da solo a ogni ricarica."""
    db = get_db()
    messaggio, categoria = _aggiorna_calendario(db)
    db.close()
    flash(messaggio, categoria)
    dove = request.form.get("torna_a")
    return redirect(dove if dove and dove.startswith("/fantacalcio2")
                    else url_for("fantacalcio2.fantacalcio2"))


@bp.route("/lega/salva", methods=["POST"])
@login_required
def lega_salva():
    f = request.form
    lid = _i(f.get("lega_id", 0))
    nome = (f.get("nome") or "").strip()
    if not nome:
        flash("Il nome della lega è obbligatorio", "error")
        return _torna()
    moduli = (f.get("moduli") or "").strip()
    sbagliati = [m.strip() for m in moduli.split(",")
                 if m.strip() and not scomponi_modulo(m)]
    if sbagliati:
        flash(f"Moduli che non tornano (i dieci di movimento devono fare 10): "
              f"{', '.join(sbagliati)}", "error")
        return _torna()
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
            return _torna()

    db = get_db()
    comuni = {
        "nome": nome, "sistema": "classic", "moduli": moduli or None,
        "n_panchinari": _i(f.get("n_panchinari"), 7),
        "mod_difesa": 1 if f.get("mod_difesa") else 0,
        "mod_difesa_portiere": 1 if f.get("mod_difesa_portiere") else 0,
        "note": (f.get("note") or "").strip() or None,
    }
    if soglie:
        comuni["mod_difesa_soglie"] = scrivi_soglie(
            sorted(soglie, key=lambda x: x[0], reverse=True))
    comuni.update(_numeri(f))
    if lid:
        if _lega_mia(db, lid) is None:
            db.close()
            flash("Lega non trovata", "error")
            return _torna()
        cond, par = solo_mie()
        sets = ", ".join(f"{c}=?" for c in comuni)
        cur = db.execute(f"UPDATE fanta2_leagues SET {sets} WHERE id=? AND {cond}",
                         list(comuni.values()) + [lid] + list(par))
        if cur.rowcount == 0:
            db.close()
            flash("Lega non trovata", "error")
            return _torna()
    else:
        comuni["user_id"] = utente_id()
        colonne = ", ".join(comuni)
        segni = ", ".join("?" * len(comuni))
        db.execute(f"INSERT INTO fanta2_leagues({colonne}) VALUES({segni})",
                   list(comuni.values()))
    db.commit()
    db.close()
    flash("Salvato", "success")
    return _torna()


@bp.route("/lega/<int:lid>/elimina", methods=["POST"])
@login_required
def lega_elimina(lid):
    """Via la lega, con la sua rosa **e la sua formazione**.

    ⚠️ Il `ON DELETE CASCADE` dello schema SQLite lo applica solo coi foreign key
    accesi, quindi le figlie si tolgono a mano — **tutte e due**: la prima sezione
    toglie la rosa e non la formazione, ed è segnalato nel backlog.
    """
    db = get_db()
    cond, par = solo_mie()
    mia = f"league_id IN (SELECT id FROM fanta2_leagues WHERE id=? AND {cond})"
    db.execute(f"DELETE FROM fanta2_roster WHERE {mia}", (lid,) + tuple(par))
    db.execute(f"DELETE FROM fanta2_formazione WHERE {mia}", (lid,) + tuple(par))
    cur = db.execute(f"DELETE FROM fanta2_leagues WHERE id=? AND {cond}",
                     (lid,) + tuple(par))
    db.commit()
    db.close()
    flash("Eliminata" if cur.rowcount else "Lega non trovata",
          "success" if cur.rowcount else "error")
    return _torna()


@bp.route("/lega/<int:lid>")
@login_required
def lega(lid):
    db = get_db()
    guaio = _calendario_se_vecchio(db)
    if guaio:
        flash(guaio, "error")
    riga = _lega_mia(db, lid)
    if riga is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    rosa = _rosa_della_lega(db, lid)
    ctx = _contesto_giornata(db)
    valutazioni = _valuta(db, riga, rosa, ctx)
    allerta = _allerta(db, lid, rosa, valutazioni)
    db.close()

    partita = {v["g"]["id"]: v["partita"] for v in valutazioni}
    fm_lega = {v["g"]["id"]: v["fm"] for v in valutazioni}
    scelta = {v["g"]["id"]: v["scelta"] for v in valutazioni}
    per_ruolo = {r: [g for g in rosa if g["ruolo_classic"] == r]
                 for r in ORDINE_RUOLI_FANTA}
    spenti = [g for g in rosa if not g["attivo"]]
    moduli = [m.strip() for m in (riga.get("moduli") or "").split(",") if m.strip()]
    copertura = []
    for m in moduli:
        serve = scomponi_modulo(m)
        if not serve:
            continue
        mancano = {r: serve[r] - len([g for g in per_ruolo[r] if g["attivo"]])
                   for r in ORDINE_RUOLI_FANTA}
        copertura.append({"modulo": m, "serve": serve,
                          "mancano": {r: n for r, n in mancano.items() if n > 0}})
    soglie = soglie_mod_difesa(riga.get("mod_difesa_soglie"))
    return render_template(
        "fanta2_lega.html", lega=riga, rosa=rosa, per_ruolo=per_ruolo,
        ruoli=RUOLI_FANTA, nome_ruolo=nome_ruolo, ordine=ORDINE_RUOLI_FANTA,
        spenti=spenti, copertura=copertura,
        speso=sum(g["prezzo"] or 0 for g in rosa),
        regole=REGOLE, ufficiali=UFFICIALI, valore_ufficiale=VALORE_UFFICIALE,
        soglie=soglie, fasce=fasce_mod_difesa(soglie),
        soglie_standard=MOD_DIFESA_SOGLIE,
        esempi_difesa=[(m, modificatore_difesa(m, soglie))
                       for m in (5.5, 6.0, 6.5, 7.0, 7.5)],
        partita=partita, fm_lega=fm_lega, scelta=scelta, scelte=G.SCELTE,
        allerta=allerta, link_probabili=LINK_PROBABILI,
        attribuzione=F.ATTRIBUZIONE, **ctx)


def _consiglio(db, lid):
    """Tutto quello che serve al consiglio: `(lega, contesto)`. Una funzione sola per
    la pagina e per «applica», che devono vedere **lo stesso** consiglio."""
    lega = _lega_mia(db, lid)
    if lega is None:
        return None, None
    rosa = _rosa_della_lega(db, lid)
    ctx = _contesto_giornata(db)
    valutazioni = _valuta(db, lega, rosa, ctx)
    moduli = [m.strip() for m in (lega.get("moduli") or "").split(",")
              if m.strip() and scomponi_modulo(m.strip())]
    ctx.update(rosa=rosa, valutazioni=valutazioni,
               per_ruolo=G.per_reparto(valutazioni),
               consigli=G.consiglia_moduli(valutazioni, moduli,
                                           lega.get("n_panchinari"), regole=lega))
    return lega, ctx


@bp.route("/lega/<int:lid>/chi-gioca")
@login_required
def chi_gioca(lid):
    """Le probabili di fantacalcio.it **accanto** alla tua rosa, per segnare chi gioca.

    Decisione di Davide del 25/09/2026. A sinistra la pagina del sito in un riquadro
    — il browser di Davide la carica e la mostra, nessun programma la legge — e a
    destra la rosa con tre stati per giocatore. Si salva a ogni clic.
    ⚠️ Il riquadro può restare bianco (un sito può rifiutare di farsi incorniciare,
    o il browser bloccarlo): la pagina lo dice e mette il link per aprirla a parte.
    """
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    rosa = _rosa_della_lega(db, lid)
    ctx = _contesto_giornata(db)
    valutazioni = _valuta(db, lega, rosa, ctx)
    db.close()
    return render_template(
        "fanta2_chi_gioca.html", lega=lega, ruoli=RUOLI_FANTA,
        ordine=ORDINE_RUOLI_FANTA, per_ruolo=G.per_reparto(valutazioni),
        scelte=G.SCELTE, link_probabili=LINK_PROBABILI,
        attribuzione=F.ATTRIBUZIONE, **ctx)


@bp.route("/chi-gioca/segna", methods=["POST"])
@login_required
def segna():
    """Una scelta sola, dal clic: `player_id`, `giornata`, `stato` (vuoto = togli).

    Risponde in JSON perché la chiama la pagina senza ricaricarsi. ⚠️ Di quello che
    arriva non si fida niente: lo stato dev'essere uno dei tre, il giocatore deve
    esistere nel listone, e la giornata **dev'essere quella corrente** — una scelta
    scritta su una giornata a caso non la leggerebbe mai nessuno, e sparirebbe senza
    errore. La riga porta l'`user_id` di chi clicca, sempre.
    """
    pid = _i(request.form.get("player_id"))
    giornata = _i(request.form.get("giornata"))
    stato = (request.form.get("stato") or "").strip()
    if stato and stato not in G.SCELTE:
        return jsonify({"errore": "Stato non valido"}), 400
    uid = utente_id()
    db = get_db()
    corrente = G.giornata_corrente(db)
    if not corrente or giornata != corrente:
        db.close()
        return jsonify({"errore": "La giornata non è quella in corso: ricarica la "
                                  "pagina"}), 409
    if not db.execute("SELECT 1 FROM fanta2_players WHERE id=?", (pid,)).fetchone():
        db.close()
        return jsonify({"errore": "Giocatore non trovato nel listone"}), 404
    if stato:
        db.execute("INSERT INTO fanta2_titolari(user_id, giornata, player_id, stato) "
                   "VALUES(?,?,?,?) ON CONFLICT(user_id, giornata, player_id) "
                   "DO UPDATE SET stato=excluded.stato, aggiornato_il=CURRENT_TIMESTAMP",
                   (uid, giornata, pid, stato))
    else:
        db.execute("DELETE FROM fanta2_titolari WHERE user_id=? AND giornata=? "
                   "AND player_id=?", (uid, giornata, pid))
    db.commit()
    db.close()
    return jsonify({"ok": True, "stato": stato or None})


@bp.route("/lega/<int:lid>/formazione")
@login_required
def formazione(lid):
    """Il campo, e il consiglio sotto, come nella prima sezione."""
    db = get_db()
    guaio = _calendario_se_vecchio(db)
    if guaio:
        flash(guaio, "error")
    lega, ctx = _consiglio(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    schierati = _schierati(db, lid)
    allerta = _allerta(db, lid, ctx["rosa"], ctx["valutazioni"])
    db.close()

    moduli = [m.strip() for m in (lega.get("moduli") or "").split(",")
              if m.strip() and scomponi_modulo(m.strip())]
    scelto = lega.get("modulo_scelto")
    if scelto not in moduli:
        scelto = moduli[0] if moduli else None
    consigli = ctx["consigli"]
    chiesto = (request.args.get("dettaglio") or "").strip()
    dettaglio = (next((c for c in consigli if c["modulo"] == chiesto), None)
                 or next((c for c in consigli if c["modulo"] == scelto), None)
                 or next((c for c in consigli if c["migliore"]), None)
                 or (consigli[0] if consigli else None))
    partita = {v["g"]["id"]: v["partita"] for v in ctx["valutazioni"]}
    fm_lega = {v["g"]["id"]: v["fm"] for v in ctx["valutazioni"]}
    scelta = {v["g"]["id"]: v["scelta"] for v in ctx["valutazioni"]}
    return render_template(
        "fanta2_formazione.html", lega=lega, ruoli=RUOLI_FANTA,
        ordine=ORDINE_RUOLI_FANTA, moduli=moduli, modulo=scelto,
        schierati=schierati, allerta=allerta,
        reparti={m: scomponi_modulo(m) for m in moduli}, dettaglio=dettaglio,
        minimo_partite=MINIMO_PARTITE_FIDATO, partita=partita, fm_lega=fm_lega,
        scelta=scelta, scelte=G.SCELTE,
        link_probabili=LINK_PROBABILI, attribuzione=F.ATTRIBUZIONE, **ctx)


def _scrivi_formazione(db, lid, modulo, titolari, panchinari, rosa):
    """Scrive formazione e modulo. `False` se la lega non è di chi scrive.
    **Chiude il db in ogni caso.** La usano il campo e «applica»."""
    cond, par = solo_mie()
    db.execute("DELETE FROM fanta2_formazione WHERE league_id=? AND league_id IN "
               f"(SELECT id FROM fanta2_leagues WHERE id=? AND {cond})",
               (lid, lid) + tuple(par))
    db.executemany(
        "INSERT INTO fanta2_formazione(league_id, player_id, titolare, ordine, ruolo)"
        " VALUES(?,?,?,?,?)",
        [(lid, p, 1, i, rosa.get(p)) for i, p in enumerate(titolari)] +
        [(lid, p, 0, i, rosa.get(p)) for i, p in enumerate(panchinari)])
    cur = db.execute(f"UPDATE fanta2_leagues SET modulo_scelto=? WHERE id=? AND {cond}",
                     (modulo, lid) + tuple(par))
    if cur.rowcount == 0:
        db.execute("DELETE FROM fanta2_formazione WHERE league_id=?", (lid,))
        db.commit()
        db.close()
        return False
    db.commit()
    db.close()
    return True


@bp.route("/lega/<int:lid>/formazione/salva", methods=["POST"])
@login_required
def formazione_salva(lid):
    """Salva la formazione anche **incompleta**, mai **sbagliata** (25/09/2026).
    Il ruolo lo decide la rosa, non il form."""
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    modulo = (request.form.get("modulo") or "").strip()
    titolari = [_i(x) for x in request.form.getlist("titolare") if _i(x)]
    panchinari = [_i(x) for x in request.form.getlist("panchinaro") if _i(x)]
    rosa = {g["id"]: g["ruolo_classic"] for g in _rosa_della_lega(db, lid)}
    ammessi = [m.strip() for m in (lega.get("moduli") or "").split(",") if m.strip()]
    guai = []
    if ammessi and modulo not in ammessi:
        guai.append(f"Il modulo {modulo or '—'} non è fra quelli ammessi da questa "
                    f"lega ({', '.join(ammessi)}).")
    sbagli, mancano = G.controlla_formazione_larga(modulo, titolari, panchinari, rosa,
                                                   lega.get("n_panchinari"))
    guai += sbagli
    if guai:
        db.close()
        for g in guai:
            flash(g, "error")
        return redirect(url_for("fantacalcio2.formazione", lid=lid))
    if not _scrivi_formazione(db, lid, modulo, titolari, panchinari, rosa):
        flash("Lega non trovata", "error")
        return _torna()
    flash(f"Formazione salvata: {modulo}, {len(titolari)} titolari e "
          f"{len(panchinari)} in panchina", "success")
    if mancano:
        flash("Non è ancora completa: " + ", ".join(mancano) + ".", "info")
    return redirect(url_for("fantacalcio2.formazione", lid=lid))


@bp.route("/lega/<int:lid>/consiglio/applica", methods=["POST"])
@login_required
def consiglio_applica(lid):
    """Porta il consiglio nel campo passando dalla **stessa** validazione del campo."""
    db = get_db()
    lega, ctx = _consiglio(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    modulo = (request.form.get("modulo") or "").strip()
    scelto = next((c for c in ctx["consigli"] if c["modulo"] == modulo), None)
    if scelto is None:
        db.close()
        flash(f"Il modulo {modulo or '—'} non è fra quelli consigliabili per questa "
              "lega", "error")
        return redirect(url_for("fantacalcio2.formazione", lid=lid, _anchor="consiglio"))
    titolari = [v["g"]["id"] for v in scelto["titolari"]]
    panchinari = [v["g"]["id"] for v in scelto["panchina"]]
    rosa = {g["id"]: g["ruolo_classic"] for g in ctx["rosa"]}
    guai = controlla_formazione(modulo, titolari, panchinari, rosa,
                                lega.get("n_panchinari"))
    if guai:
        db.close()
        for g in guai:
            flash(g, "error")
        return redirect(url_for("fantacalcio2.formazione", lid=lid, _anchor="consiglio"))
    if not _scrivi_formazione(db, lid, modulo, titolari, panchinari, rosa):
        flash("Lega non trovata", "error")
        return _torna()
    flash(f"Consiglio applicato: {modulo}, {len(titolari)} titolari e "
          f"{len(panchinari)} in panchina. Ora aggiustalo come vuoi.", "success")
    return redirect(url_for("fantacalcio2.formazione", lid=lid))


@bp.route("/lega/<int:lid>/rosa/aggiungi", methods=["POST"])
@login_required
def rosa_aggiungi(lid):
    pid = _i(request.form.get("player_id"))
    db = get_db()
    if _lega_mia(db, lid) is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    esiste = db.execute("SELECT nome FROM fanta2_players WHERE id=?", (pid,)).fetchone()
    if not esiste:
        db.close()
        flash("Giocatore non trovato nel listone", "error")
        return _torna(lid)
    try:
        db.execute("INSERT INTO fanta2_roster(league_id, player_id, prezzo, note) "
                   "VALUES(?,?,?,?)",
                   (lid, pid, _prezzo(request.form.get("prezzo")),
                    (request.form.get("note") or "").strip() or None))
        db.commit()
        flash(f"{esiste['nome']} aggiunto", "success")
    except Exception:
        flash(f"{esiste['nome']} è già in questa rosa", "error")
    db.close()
    return _torna(lid)


@bp.route("/lega/<int:lid>/rosa/<int:rid>/rimuovi", methods=["POST"])
@login_required
def rosa_rimuovi(lid, rid):
    db = get_db()
    cond, par = solo_mie("l.user_id")
    mia = f"league_id IN (SELECT l.id FROM fanta2_leagues l WHERE {cond})"
    riga = db.execute(f"SELECT player_id FROM fanta2_roster WHERE id=? AND "
                      f"league_id=? AND {mia}", (rid, lid) + tuple(par)).fetchone()
    cur = db.execute(f"DELETE FROM fanta2_roster WHERE id=? AND league_id=? AND {mia}",
                     (rid, lid) + tuple(par))
    scesi = _scendi_dal_campo(db, lid, [riga["player_id"]]) if cur.rowcount else 0
    db.commit()
    db.close()
    flash(("Tolto dalla rosa, ed era schierato" if scesi else "Tolto dalla rosa")
          if cur.rowcount else "Non trovato", "success" if cur.rowcount else "error")
    return _torna(lid)


@bp.route("/lega/<int:lid>/rosa/modifica", methods=["POST"])
@login_required
def rosa_modifica(lid):
    """Prezzi corretti e righe tolte in un colpo. I `rid` si rileggono dalla rosa di
    **questa** lega prima di usarli: un id di un'altra lega non tocca niente."""
    db = get_db()
    cond, par = solo_mie("l.user_id")
    mia = f"league_id IN (SELECT l.id FROM fanta2_leagues l WHERE {cond})"
    righe = {r["id"]: dict(r) for r in db.execute(
        f"SELECT id, player_id, prezzo FROM fanta2_roster WHERE league_id=? AND {mia}",
        (lid,) + tuple(par)).fetchall()}
    togli = [r for r in (_i(v, None) for v in request.form.getlist("togli"))
             if r in righe]
    tolti, scesi = 0, 0
    if togli:
        segni = ",".join("?" * len(togli))
        tolti = db.execute(
            f"DELETE FROM fanta2_roster WHERE id IN ({segni}) AND league_id=? AND {mia}",
            tuple(togli) + (lid,) + tuple(par)).rowcount
        if tolti:
            scesi = _scendi_dal_campo(db, lid, [righe[r]["player_id"] for r in togli])
    corretti = 0
    for rid, prima in righe.items():
        if rid in togli or f"prezzo_{rid}" not in request.form:
            continue
        adesso = _prezzo(request.form.get(f"prezzo_{rid}"))
        if adesso == (prima["prezzo"] or 0):
            continue
        corretti += db.execute(
            f"UPDATE fanta2_roster SET prezzo=? WHERE id=? AND league_id=? AND {mia}",
            (adesso, rid, lid) + tuple(par)).rowcount
    db.commit()
    db.close()
    pezzi = []
    if corretti:
        pezzi.append(f"{corretti} prezz{'i corretti' if corretti > 1 else 'o corretto'}")
    if tolti:
        pezzi.append(f"{tolti} tolt{'i' if tolti > 1 else 'o'} dalla rosa" +
                     (f" ({scesi} er{'ano' if scesi > 1 else 'a'} schierat"
                      f"{'i' if scesi > 1 else 'o'})" if scesi else ""))
    flash(", ".join(pezzi).capitalize() if pezzi else "Niente da cambiare",
          "success" if pezzi else "error")
    return _torna(lid)


def _listone(db):
    """Il listone intero, per abbinare una rosa incollata. Condiviso, non filtrato.
    ⚠️ `attivo` qui vuol dire «in Serie A»: i ceduti sono spenti."""
    return [dict(r) for r in db.execute(
        "SELECT id, nome, squadra, squadra_slug, ruolo_classic, qa, fvm, "
        "fantamedia, attivo FROM fanta2_players").fetchall()]


def _ids_in_rosa(db, lid):
    cond, par = ambito_utente("l.user_id")
    return {r["player_id"] for r in db.execute(
        "SELECT r.player_id FROM fanta2_roster r "
        "JOIN fanta2_leagues l ON l.id = r.league_id "
        f"WHERE r.league_id=? AND {cond}", (lid,) + tuple(par)).fetchall()}


@bp.route("/lega/<int:lid>/rosa/incolla", methods=["POST"])
@login_required
def rosa_incolla(lid):
    """L'anteprima della rosa incollata: **legge e mostra, non scrive niente.**"""
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    testo = request.form.get("testo") or ""
    righe = leggi_rosa_incollata(testo, _listone(db), _ids_in_rosa(db, lid))
    db.close()
    if not righe:
        flash("Non ho letto nessun nome: incolla una riga per giocatore", "error")
        return _torna(lid)
    conto = {s: len([r for r in righe if r["stato"] == s])
             for s in ("ok", "conferma", "scegli", "niente")}
    return render_template("fanta2_rosa_incolla.html", lega=lega, righe=righe,
                           testo=testo, conto=conto, ruoli=RUOLI_FANTA)


@bp.route("/lega/<int:lid>/rosa/incolla/conferma", methods=["POST"])
@login_required
def rosa_incolla_conferma(lid):
    """Scrive **solo** le righe spuntate; il `player_id` si ricontrolla nel listone."""
    db = get_db()
    if _lega_mia(db, lid) is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    validi = {r["id"] for r in db.execute("SELECT id FROM fanta2_players").fetchall()}
    indici = sorted({_i(k[4:]) for k in request.form if k.startswith("pid_")
                     and _i(k[4:]) is not None})
    aggiunti, saltati, ignoti = 0, 0, 0
    for n in indici:
        if not request.form.get(f"riga_{n}"):
            continue
        pid = _i(request.form.get(f"pid_{n}"))
        if pid is None or pid not in validi:
            ignoti += 1
            continue
        try:
            db.execute("INSERT INTO fanta2_roster(league_id, player_id, prezzo) "
                       "VALUES(?,?,?)", (lid, pid, _prezzo(request.form.get(f"prezzo_{n}"))))
            aggiunti += 1
        except Exception:
            saltati += 1
    db.commit()
    db.close()
    pezzi = [f"{aggiunti} in rosa"]
    if saltati:
        pezzi.append(f"{saltati} già in rosa da prima")
    if ignoti:
        pezzi.append(f"{ignoti} senza un giocatore valido")
    flash(", ".join(pezzi), "success" if aggiunti else "error")
    return _torna(lid)


@bp.route("/lega/<int:lid>/rosa/svuota", methods=["POST"])
@login_required
def rosa_svuota(lid):
    """Svuota un ruolo o tutta la rosa; chi esce dalla rosa esce anche dal campo."""
    ruolo = (request.form.get("ruolo") or "").strip().lower()
    if ruolo not in ("tutti",) + tuple(ORDINE_RUOLI_FANTA):
        flash("Non so quale parte della rosa svuotare", "error")
        return _torna(lid)
    db = get_db()
    if _lega_mia(db, lid) is None:
        db.close()
        flash("Lega non trovata", "error")
        return _torna()
    cond, par = solo_mie("l.user_id")
    mia = f"league_id IN (SELECT l.id FROM fanta2_leagues l WHERE {cond})"
    filtro = "" if ruolo == "tutti" else " AND p.ruolo_classic=?"
    coda = () if ruolo == "tutti" else (ruolo,)
    righe = [dict(r) for r in db.execute(
        f"SELECT r.id, r.player_id FROM fanta2_roster r "
        f"JOIN fanta2_players p ON p.id = r.player_id "
        f"WHERE r.league_id=? AND r.{mia}{filtro}",
        (lid,) + tuple(par) + coda).fetchall()]
    if not righe:
        db.close()
        flash("Non c'era niente da togliere", "error")
        return _torna(lid)
    segni = ",".join("?" * len(righe))
    tolti = db.execute(
        f"DELETE FROM fanta2_roster WHERE id IN ({segni}) AND league_id=? AND {mia}",
        tuple(r["id"] for r in righe) + (lid,) + tuple(par)).rowcount
    scesi = _scendi_dal_campo(db, lid, [r["player_id"] for r in righe]) if tolti else 0
    db.commit()
    db.close()
    quali = "Rosa svuotata" if ruolo == "tutti" else f"Reparto {nome_ruolo(ruolo, 2)} svuotato"
    flash(f"{quali}: {tolti} tolt{'i' if tolti > 1 else 'o'} dalla rosa" +
          (f" ({scesi} er{'ano' if scesi > 1 else 'a'} schierat"
           f"{'i' if scesi > 1 else 'o'})" if scesi else ""), "success")
    return _torna(lid)


# Le colonne per cui il listone si può ordinare. L'URL sceglie **una chiave** di
# questo dizionario, mai un nome di colonna che finisca nella query.
ORDINI_LISTONE = {
    "fvm": ("fvm DESC", "valore di mercato"),
    "qa": ("qa DESC", "quotazione attuale"),
    "fantamedia": ("fantamedia DESC", "fantamedia"),
    "media_voto": ("media_voto DESC", "media voto"),
    "partite": ("partite_a_voto DESC", "partite a voto"),
    "gol": ("gol DESC", "gol"),
    "assist": ("assist DESC", "assist"),
    "nome": ("nome ASC", "nome"),
}


@bp.route("/listone")
@login_required
def listone():
    """Il listone da sfogliare. I ceduti si vedono solo chiedendolo, e dichiarati."""
    db = get_db()
    q = (request.args.get("q") or "").strip()
    ruolo = (request.args.get("ruolo") or "").strip().lower()
    squadra = (request.args.get("squadra") or "").strip()
    ordine = request.args.get("ordine") if request.args.get("ordine") in ORDINI_LISTONE else "fvm"
    spenti = request.args.get("spenti") == "1"
    dove, par = [], []
    if not spenti:
        dove.append("attivo=1")
    if q:
        dove.append("nome LIKE ?")
        par.append(f"%{q}%")
    if ruolo in ORDINE_RUOLI_FANTA:
        dove.append("ruolo_classic=?")
        par.append(ruolo)
    else:
        ruolo = ""
    if squadra:
        dove.append("squadra=?")
        par.append(squadra)
    filtro = (" WHERE " + " AND ".join(dove)) if dove else ""
    colonna = ORDINI_LISTONE[ordine][0]
    chiave = colonna.split()[0]
    righe = [dict(r) for r in db.execute(
        f"SELECT * FROM fanta2_players{filtro} "
        f"ORDER BY ({chiave} IS NULL), {colonna}, nome", par).fetchall()]
    squadre = [r["squadra"] for r in db.execute(
        "SELECT DISTINCT squadra FROM fanta2_players WHERE squadra IS NOT NULL "
        "AND attivo=1 ORDER BY squadra").fetchall()]
    totali = db.execute(
        "SELECT COUNT(*) AS attivi, MAX(visto_il) AS visto, "
        "(SELECT COUNT(*) FROM fanta2_players WHERE attivo=0) AS spenti "
        "FROM fanta2_players WHERE attivo=1").fetchone()
    cond, par_u = ambito_utente("l.user_id")
    mie = {}
    for r in db.execute(
            "SELECT r.player_id, l.id AS lid, l.nome FROM fanta2_roster r "
            f"JOIN fanta2_leagues l ON l.id=r.league_id WHERE {cond}", par_u):
        mie.setdefault(r["player_id"], []).append({"lid": r["lid"], "nome": r["nome"]})
    db.close()
    return render_template("fanta2_listone.html", righe=righe, squadre=squadre,
                           ruoli=RUOLI_FANTA, ordine=ordine, ordini=ORDINI_LISTONE,
                           q=q, ruolo=ruolo, squadra=squadra, spenti=spenti,
                           totali=dict(totali) if totali else {}, mie=mie)


@bp.route("/api/giocatore/<int:pid>")
@login_required
def api_giocatore(pid):
    """La scheda: riga del listone (condivisa), la sua partita della giornata
    (condivisa) e in quali **tue** rose sta (filtrata passando dalle leghe)."""
    db = get_db()
    riga = db.execute("SELECT * FROM fanta2_players WHERE id=?", (pid,)).fetchone()
    if riga is None:
        db.close()
        return jsonify({"errore": "Giocatore non trovato nel listone"}), 404
    voce = dict(riga)
    ctx = _contesto_giornata(db)
    partita = G.partita_di(voce, ctx["partite"], ctx["tabella"], ctx["calendario_c_e"])
    cond, par = ambito_utente("l.user_id")
    rose = [{"lid": r["lid"], "lega": r["lega"], "prezzo": r["prezzo"]}
            for r in db.execute(
                "SELECT l.id AS lid, l.nome AS lega, r.prezzo FROM fanta2_roster r "
                f"JOIN fanta2_leagues l ON l.id=r.league_id WHERE r.player_id=? AND {cond} "
                "ORDER BY l.nome", (pid,) + tuple(par)).fetchall()]
    db.close()
    return jsonify({"giocatore": voce, "giornata": ctx["giornata"],
                    "partita": partita, "rose": rose})


@bp.route("/api/giocatori")
@login_required
def api_giocatori():
    """I giocatori che combaciano con `q`. I ceduti restano cercabili ma dichiarati."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    db = get_db()
    righe = db.execute(
        "SELECT id, nome, squadra, ruolo_classic, qa, fvm, fantamedia, attivo "
        "FROM fanta2_players WHERE nome LIKE ? "
        "ORDER BY attivo DESC, fvm DESC, nome LIMIT 25", (f"%{q}%",)).fetchall()
    db.close()
    return jsonify([dict(r) for r in righe])
