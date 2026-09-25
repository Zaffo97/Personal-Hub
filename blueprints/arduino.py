from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import (get_db, login_required, _i,
                        ambito_utente, utente_id, e_admin)
from data import ARDUINO_BOARDS, ARDUINO_STATUSES
import arduino_circuito as C

bp = Blueprint("arduino", __name__, url_prefix="/arduino")


@bp.route("/")
@login_required
def arduino():
    db = get_db()
    # L'admin vede i progetti di tutti, con scritto di chi sono e la tendina
    # `?utente=` per isolarne uno; gli altri vedono i propri.
    di = _i(request.args.get("utente")) or None
    cond, par = ambito_utente(di=di)
    projects = [dict(r) for r in db.execute(
        f"SELECT * FROM arduino_projects WHERE {cond} ORDER BY created_at DESC",
        par).fetchall()]
    for p in projects:
        # La tabella si ricalcola a ogni apertura (vedi init_db): un controllo nuovo
        # vale anche per i circuiti salvati prima.
        p["circuito"] = C.analizza(p.get("wokwi_diagramma"), p.get("board"))
        p["anteprime"] = [(C.LINK[c][0], u) for c in ("tinkercad_url", "wokwi_url")
                          for u in [C.incorpora(c, p.get(c))] if u]
        # Un link salvato prima del controllo (fino al 25/09/2026 il campo Tinkercad
        # finiva in un `href` così com'era): se non passa, non si mostra.
        for c in ("tinkercad_url", "wokwi_url"):
            p[c + "_ok"] = C.link_valido(c, p.get(c))
    nomi_utenti = {r["id"]: r["username"] for r in
                   db.execute("SELECT id, username FROM users")} if e_admin() else {}
    proprietari = []
    if e_admin():
        proprietari = [dict(r) for r in db.execute(
            "SELECT u.id, u.username, COUNT(a.id) AS quanti FROM users u "
            "JOIN arduino_projects a ON a.user_id=u.id GROUP BY u.id, u.username "
            "ORDER BY u.username").fetchall()]
    db.close()
    return render_template("arduino.html", projects=projects,
                           boards=ARDUINO_BOARDS, statuses=ARDUINO_STATUSES,
                           proprietari=proprietari, filtro_utente=di,
                           nomi_utenti=nomi_utenti,
                           tinkercad_nuovo=C.TINKERCAD_NUOVO, wokwi_nuovo=C.WOKWI_NUOVO)


def _link(f, campo):
    """Il link del form se è del sito giusto. Se non lo è, lo si dice e non si salva."""
    grezzo = (f.get(campo) or "").strip()
    buono = C.link_valido(campo, grezzo)
    if grezzo and not buono:
        etichetta, siti = C.LINK[campo]
        flash(f"Link «{etichetta}» non salvato: si accettano solo indirizzi http(s) di "
              + ", ".join(siti), "error")
    return buono


@bp.route("/save", methods=["POST"])
@login_required
def arduino_save():
    f   = request.form
    pid = _i(f.get("proj_id", 0))
    campi = {
        "name": f.get("name", ""), "board": f.get("board", "Arduino Uno"),
        "status": f.get("status", "Idea"),
        "tinkercad_url": _link(f, "tinkercad_url"), "wokwi_url": _link(f, "wokwi_url"),
        "code": f.get("code", ""), "description": f.get("description", "") or None,
    }
    # Il diagram.json: vuoto lo toglie, illeggibile **non** sovrascrive quello di prima
    # (si perderebbe un circuito buono per un incolla venuto male), e lo si dice.
    testo = (f.get("wokwi_diagramma") or "").strip()
    _, errore = C.leggi_diagramma(testo)
    if errore:
        flash(f"diagram.json non salvato: {errore}", "error")
    else:
        campi["wokwi_diagramma"] = testo or None
    db = get_db()
    if pid:
        cond, par = ambito_utente()
        assegna = ",".join(f"{k}=?" for k in campi)
        cur = db.execute(f"UPDATE arduino_projects SET {assegna} WHERE id=? AND {cond}",
                         tuple(campi.values()) + (pid,) + tuple(par))
        if cur.rowcount == 0:
            db.close(); flash("Non trovato", "error")
            return redirect(url_for("arduino.arduino"))
    else:
        db.execute("INSERT INTO arduino_projects(name,board,status,tinkercad_url,wokwi_url,"
                   "code,description,wokwi_diagramma,user_id) VALUES(?,?,?,?,?,?,?,?,?)",
                   (campi["name"], campi["board"], campi["status"], campi["tinkercad_url"],
                    campi["wokwi_url"], campi["code"], campi["description"],
                    campi.get("wokwi_diagramma"), utente_id()))
    db.commit(); db.close()
    flash("Salvato", "success"); return redirect(url_for("arduino.arduino"))


@bp.route("/<int:pid>/delete", methods=["POST"])
@login_required
def arduino_delete(pid):
    db = get_db()
    cond, par = ambito_utente()
    cur = db.execute(f"DELETE FROM arduino_projects WHERE id=? AND {cond}",
                     (pid,) + tuple(par))
    db.commit(); db.close()
    flash("Eliminato" if cur.rowcount else "Non trovato",
          "success" if cur.rowcount else "error")
    return redirect(url_for("arduino.arduino"))
