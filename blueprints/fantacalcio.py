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
from data import RUOLI_FANTA, ORDINE_RUOLI_FANTA, scomponi_modulo

bp = Blueprint("fantacalcio", __name__, url_prefix="/fantacalcio")

# Le colonne delle regole, in un posto solo: le usano il form, il salvataggio e la
# scheda che le mostra. ⚠️ Solo le prime tre vengono dal regolamento **ufficiale**
# di fantacalcio.it (letto il 21/09/2026); le altre non le fissa nessun regolamento
# perché cambiano da lega a lega, ed è il motivo per cui stanno qui e non in un testo.
REGOLE = [
    ("bonus_gol_p", "Gol del portiere", True),
    ("bonus_gol_d", "Gol del difensore", False),
    ("bonus_gol_c", "Gol del centrocampista", False),
    ("bonus_gol_a", "Gol dell'attaccante", False),
    ("bonus_assist", "Assist", False),
    ("malus_amm", "Ammonizione", True),
    ("malus_esp", "Espulsione", True),
    ("malus_gol_subito", "Gol subito (portiere)", False),
    ("bonus_imbattibilita", "Porta inviolata", False),
    ("bonus_rigore_parato", "Rigore parato", False),
    ("malus_rigore_sbagliato", "Rigore sbagliato", False),
    ("malus_autogol", "Autogol", False),
]
UFFICIALI = {c for c, _, ufficiale in REGOLE if ufficiale}


def _lega_mia(db, lid):
    """La lega `lid` **se è di chi sta guardando**, altrimenti `None`.

    Un punto solo per la domanda «questa lega è mia?»: ripeterla in sei route è il
    modo per dimenticarsela nella settima.
    """
    cond, par = ambito_utente()
    r = db.execute(f"SELECT * FROM fanta_leagues WHERE id=? AND {cond}",
                   (lid,) + tuple(par)).fetchone()
    return dict(r) if r else None


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
    for colonna, _, _ in REGOLE:
        grezzo = f.get(colonna)
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
    di = _i(request.args.get("utente")) or None
    cond, par = ambito_utente(di=di)
    leghe = [dict(r) for r in db.execute(
        "SELECT l.*, (SELECT COUNT(*) FROM fanta_roster r WHERE r.league_id=l.id) "
        f"AS quanti FROM fanta_leagues l WHERE {cond} ORDER BY l.nome", par).fetchall()]
    listone = db.execute(
        "SELECT COUNT(*) AS attivi, MAX(visto_il) AS visto, "
        "(SELECT COUNT(*) FROM fanta_players WHERE attivo=0) AS spenti "
        "FROM fanta_players WHERE attivo=1").fetchone()
    nomi_utenti = {r["id"]: r["username"] for r in
                   db.execute("SELECT id, username FROM users")} if e_admin() else {}
    proprietari = []
    if e_admin():
        proprietari = [dict(r) for r in db.execute(
            "SELECT u.id, u.username, COUNT(l.id) AS quanti FROM users u "
            "JOIN fanta_leagues l ON l.user_id=u.id GROUP BY u.id, u.username "
            "ORDER BY u.username").fetchall()]
    db.close()
    return render_template("fantacalcio.html", leghe=leghe,
                           listone=dict(listone) if listone else {},
                           regole=REGOLE, ufficiali=UFFICIALI,
                           proprietari=proprietari, filtro_utente=di,
                           nomi_utenti=nomi_utenti)


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

    db = get_db()
    riga = _lega_mia(db, lid) if lid else None
    valori = _numeri(f)
    comuni = {
        "nome": nome,
        "sistema": "classic",
        "moduli": moduli or None,
        "n_panchinari": _i(f.get("n_panchinari"), 7),
        "mod_difesa": 1 if f.get("mod_difesa") else 0,
        "note": (f.get("note") or "").strip() or None,
    }
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
                           regole=REGOLE, ufficiali=UFFICIALI)


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
