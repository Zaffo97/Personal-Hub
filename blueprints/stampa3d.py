"""Stampa 3D: i progetti con i loro file e link, e l'inventario delle bobine.

Sul modello di Arduino. La logica (link ammessi, file su disco, soglie) sta in
`stampa3d.py` alla radice, come quella dei negozi in `pc_negozi.py`.
"""
import os

from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   send_file, abort)
from extensions import (get_db, login_required, _i, _f,
                        ambito_utente, utente_id, e_admin)
import stampa3d as S

bp = Blueprint("stampa3d", __name__, url_prefix="/stampa3d")


def _torna():
    return redirect(url_for("stampa3d.stampa3d"))


@bp.route("/")
@login_required
def stampa3d():
    db = get_db()
    # Come in Arduino: l'admin vede tutto, con la tendina `?utente=` per isolarne uno.
    di = _i(request.args.get("utente")) or None
    cond, par = ambito_utente(di=di)
    progetti = [dict(r) for r in db.execute(
        f"SELECT * FROM stampa_progetti WHERE {cond} ORDER BY created_at DESC, id DESC",
        par).fetchall()]
    condf, parf = ambito_utente(colonna="p.user_id", di=di)
    file_per = {}
    for r in db.execute(
            "SELECT f.* FROM stampa_file f JOIN stampa_progetti p ON p.id=f.progetto_id "
            f"WHERE {condf} ORDER BY f.nome", parf).fetchall():
        d = dict(r)
        d["misura"] = S.misura(d["byte"])
        d["manca"] = not S.esiste(d["impronta"])
        file_per.setdefault(d["progetto_id"], []).append(d)
    for p in progetti:
        p["file"] = file_per.get(p["id"], [])
        p["cerca_mw"] = S.cerca_makerworld(p["nome"])
    bobine = [dict(r) for r in db.execute(
        f"SELECT * FROM stampa_filamenti WHERE {cond} ORDER BY materiale, colore, id",
        par).fetchall()]
    for b in bobine:
        b["quasi_finita"] = S.quasi_finita(b)
    nomi_utenti = {r["id"]: r["username"] for r in
                   db.execute("SELECT id, username FROM users")} if e_admin() else {}
    proprietari = []
    if e_admin():
        proprietari = [dict(r) for r in db.execute(
            "SELECT u.id, u.username, COUNT(p.id) AS quanti FROM users u "
            "JOIN stampa_progetti p ON p.user_id=u.id GROUP BY u.id, u.username "
            "ORDER BY u.username").fetchall()]
    db.close()
    return render_template("stampa3d.html", progetti=progetti, bobine=bobine,
                           stati=S.STATI, materiali=S.MATERIALI, partenze=S.PARTENZE,
                           estensioni=",".join(S.ESTENSIONI),
                           max_mb=S.MAX_BYTE // (1024 * 1024),
                           soglia=S.SOGLIA_BOBINA_G, siti=S.LINK,
                           proprietari=proprietari, filtro_utente=di,
                           nomi_utenti=nomi_utenti)


def _link(f, campo):
    """Il link del form se è di un sito ammesso. Se non lo è, lo si dice e non si salva."""
    grezzo = (f.get(campo) or "").strip()
    buono = S.link_valido(campo, grezzo)
    if grezzo and not buono:
        etichetta, siti = S.LINK[campo]
        flash(f"Link «{etichetta}» non salvato: si accettano solo indirizzi http(s) di "
              + ", ".join(siti), "error")
    return buono


def _carica(db, pid):
    """Scrive i file del form sul progetto `pid`. Torna quanti ne ha aggiunti."""
    aggiunti = 0
    for fs in request.files.getlist("file"):
        if not fs or not fs.filename:
            continue
        nome = os.path.basename(fs.filename.replace("\\", "/"))
        if not S.estensione_ammessa(nome):
            flash(f"«{nome}» non caricato: si accettano " + ", ".join(S.ESTENSIONI), "error")
            continue
        impronta, byte = S.salva_file(fs.stream)
        if not impronta:
            flash(f"«{nome}» non caricato: supera {S.MAX_BYTE // (1024 * 1024)} MB", "error")
            continue
        db.execute("INSERT INTO stampa_file(progetto_id,nome,impronta,byte) VALUES(?,?,?,?)",
                   (pid, nome, impronta, byte))
        aggiunti += 1
    return aggiunti


@bp.route("/save", methods=["POST"])
@login_required
def stampa3d_save():
    f = request.form
    pid = _i(f.get("proj_id", 0))
    nome = (f.get("nome") or "").strip()
    if not nome:
        flash("Il nome serve", "error"); return _torna()
    stato = f.get("stato") if f.get("stato") in S.STATI else "Idea"
    grammi = _f(f.get("grammi"), None)
    vals = (nome, stato, (f.get("stampante") or "").strip() or None,
            f.get("materiale") or None,
            _link(f, "link_modello"), _link(f, "link_disegno"),
            grammi if grammi and grammi > 0 else None,
            (f.get("note") or "").strip() or None)
    db = get_db()
    if pid:
        cond, par = ambito_utente()
        cur = db.execute("UPDATE stampa_progetti SET nome=?,stato=?,stampante=?,materiale=?,"
                         "link_modello=?,link_disegno=?,grammi=?,note=? "
                         f"WHERE id=? AND {cond}", vals + (pid,) + tuple(par))
        if cur.rowcount == 0:
            db.close(); flash("Non trovato", "error"); return _torna()
    else:
        cur = db.execute("INSERT INTO stampa_progetti(nome,stato,stampante,materiale,"
                         "link_modello,link_disegno,grammi,note,user_id) "
                         "VALUES(?,?,?,?,?,?,?,?,?)", vals + (utente_id(),))
        pid = cur.lastrowid
    aggiunti = _carica(db, pid)
    db.commit(); db.close()
    flash("Salvato" + (f", {aggiunti} file allegati" if aggiunti else ""), "success")
    return _torna()


@bp.route("/<int:pid>/delete", methods=["POST"])
@login_required
def stampa3d_delete(pid):
    db = get_db()
    condf, parf = ambito_utente(colonna="p.user_id")
    impronte = [r["impronta"] for r in db.execute(
        "SELECT f.impronta FROM stampa_file f JOIN stampa_progetti p ON p.id=f.progetto_id "
        f"WHERE p.id=? AND {condf}", (pid,) + tuple(parf))]
    cond, par = ambito_utente()
    cur = db.execute(f"DELETE FROM stampa_progetti WHERE id=? AND {cond}",
                     (pid,) + tuple(par))
    db.commit()
    if cur.rowcount:
        S.togli_orfani(db, impronte)
    db.close()
    flash("Eliminato" if cur.rowcount else "Non trovato",
          "success" if cur.rowcount else "error")
    return _torna()


def _file(db, fid):
    cond, par = ambito_utente(colonna="p.user_id")
    return db.execute(
        "SELECT f.* FROM stampa_file f JOIN stampa_progetti p ON p.id=f.progetto_id "
        f"WHERE f.id=? AND {cond}", (fid,) + tuple(par)).fetchone()


@bp.route("/file/<int:fid>")
@login_required
def stampa3d_file(fid):
    db = get_db()
    r = _file(db, fid)
    db.close()
    if not r:
        abort(404)
    if not S.esiste(r["impronta"]):
        flash(f"«{r['nome']}» manca dal disco (i file non sono nell'export)", "error")
        return _torna()
    return send_file(S.percorso(r["impronta"]), as_attachment=True, download_name=r["nome"])


@bp.route("/file/<int:fid>/delete", methods=["POST"])
@login_required
def stampa3d_file_delete(fid):
    db = get_db()
    r = _file(db, fid)
    if not r:
        db.close(); flash("Non trovato", "error"); return _torna()
    db.execute("DELETE FROM stampa_file WHERE id=?", (r["id"],))
    db.commit()
    S.togli_orfani(db, [r["impronta"]])
    db.close()
    flash(f"«{r['nome']}» tolto", "success")
    return _torna()


# ── Le bobine ────────────────────────────────────────────────────────────────

@bp.route("/bobina/save", methods=["POST"])
@login_required
def bobina_save():
    f = request.form
    bid = _i(f.get("bobina_id", 0))
    totale = _f(f.get("peso_totale"), 1000.0) or 1000.0
    rimasto = _f(f.get("peso_rimasto"), None)
    if rimasto is None:
        rimasto = totale
    prezzo = _f(f.get("prezzo"), None)
    hexa = (f.get("colore_hex") or "").strip()
    if not (len(hexa) == 7 and hexa[0] == "#" and
            all(c in "0123456789abcdefABCDEF" for c in hexa[1:])):
        hexa = None
    vals = (f.get("materiale") or None, (f.get("marca") or "").strip() or None,
            (f.get("colore") or "").strip() or None, hexa,
            totale, max(rimasto, 0.0), prezzo if prezzo and prezzo > 0 else None,
            (f.get("note") or "").strip() or None)
    db = get_db()
    if bid:
        cond, par = ambito_utente()
        cur = db.execute("UPDATE stampa_filamenti SET materiale=?,marca=?,colore=?,colore_hex=?,"
                         f"peso_totale=?,peso_rimasto=?,prezzo=?,note=? WHERE id=? AND {cond}",
                         vals + (bid,) + tuple(par))
        if cur.rowcount == 0:
            db.close(); flash("Non trovata", "error"); return _torna()
    else:
        db.execute("INSERT INTO stampa_filamenti(materiale,marca,colore,colore_hex,peso_totale,"
                   "peso_rimasto,prezzo,note,user_id) VALUES(?,?,?,?,?,?,?,?,?)",
                   vals + (utente_id(),))
    db.commit(); db.close()
    flash("Bobina salvata", "success")
    return _torna()


@bp.route("/bobina/<int:bid>/delete", methods=["POST"])
@login_required
def bobina_delete(bid):
    db = get_db()
    cond, par = ambito_utente()
    cur = db.execute(f"DELETE FROM stampa_filamenti WHERE id=? AND {cond}",
                     (bid,) + tuple(par))
    db.commit(); db.close()
    flash("Bobina eliminata" if cur.rowcount else "Non trovata",
          "success" if cur.rowcount else "error")
    return _torna()


def _scala(db, bid, grammi, proprietario=None):
    """Toglie `grammi` dalla bobina. Non va sotto zero, e lo dice.

    `proprietario`, se c'è, deve essere quello della bobina: un progetto scala solo
    le bobine di chi l'ha fatto, anche quando a premere è l'admin che li vede tutti.
    """
    cond, par = ambito_utente()
    b = db.execute(f"SELECT * FROM stampa_filamenti WHERE id=? AND {cond}",
                   (bid,) + tuple(par)).fetchone()
    if not b or (proprietario is not None and b["user_id"] != proprietario):
        flash("Bobina non trovata", "error"); return False
    prima = b["peso_rimasto"] or 0.0
    dopo = max(prima - grammi, 0.0)
    db.execute(f"UPDATE stampa_filamenti SET peso_rimasto=? WHERE id=? AND {cond}",
               (dopo, bid) + tuple(par))
    nome = " ".join(x for x in (b["materiale"], b["colore"]) if x) or "bobina"
    if prima - grammi < 0:
        flash(f"{nome}: ne restavano {prima:g} g, non {grammi:g}. Portata a 0", "error")
    else:
        flash(f"{nome}: {prima:g} → {dopo:g} g", "success")
    return True


@bp.route("/bobina/<int:bid>/usa", methods=["POST"])
@login_required
def bobina_usa(bid):
    grammi = _f(request.form.get("grammi"), 0.0)
    if grammi <= 0:
        flash("Quanti grammi?", "error"); return _torna()
    db = get_db()
    if _scala(db, bid, grammi):
        db.commit()
    db.close()
    return _torna()


@bp.route("/<int:pid>/scala", methods=["POST"])
@login_required
def stampa3d_scala(pid):
    """Scala i grammi del progetto da una bobina, e lo segna «Stampato»."""
    db = get_db()
    cond, par = ambito_utente()
    p = db.execute(f"SELECT * FROM stampa_progetti WHERE id=? AND {cond}",
                   (pid,) + tuple(par)).fetchone()
    if not p or not p["grammi"]:
        db.close(); flash("Il progetto non ha i grammi", "error"); return _torna()
    if _scala(db, _i(request.form.get("bobina_id")), p["grammi"], proprietario=p["user_id"]):
        db.execute(f"UPDATE stampa_progetti SET stato='Stampato' WHERE id=? AND {cond}",
                   (pid,) + tuple(par))
        db.commit()
    db.close()
    return _torna()
