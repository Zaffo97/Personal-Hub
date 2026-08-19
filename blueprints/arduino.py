from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import (get_db, login_required, _i,
                        ambito_utente, utente_id, e_admin)
from data import ARDUINO_BOARDS, ARDUINO_STATUSES

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
                           nomi_utenti=nomi_utenti)


@bp.route("/save", methods=["POST"])
@login_required
def arduino_save():
    f   = request.form
    pid = _i(f.get("proj_id", 0))
    vals = (
        f.get("name", ""), f.get("board", "Arduino Uno"), f.get("status", "Idea"),
        f.get("tinkercad_url", "") or None,
        f.get("code", ""), f.get("description", "") or None,
    )
    db = get_db()
    if pid:
        cond, par = ambito_utente()
        cur = db.execute("UPDATE arduino_projects SET name=?,board=?,status=?,"
                         f"tinkercad_url=?,code=?,description=? WHERE id=? AND {cond}",
                         vals + (pid,) + tuple(par))
        if cur.rowcount == 0:
            db.close(); flash("Non trovato", "error")
            return redirect(url_for("arduino.arduino"))
    else:
        db.execute("INSERT INTO arduino_projects(name,board,status,tinkercad_url,"
                   "code,description,user_id) VALUES(?,?,?,?,?,?,?)",
                   vals + (utente_id(),))
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