from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import get_db, login_required, _i
from data import ARDUINO_BOARDS, ARDUINO_STATUSES

bp = Blueprint("arduino", __name__, url_prefix="/arduino")


@bp.route("/")
@login_required
def arduino():
    db = get_db()
    projects = [dict(r) for r in
                db.execute("SELECT * FROM arduino_projects ORDER BY created_at DESC").fetchall()]
    db.close()
    return render_template("arduino.html", projects=projects,
                           boards=ARDUINO_BOARDS, statuses=ARDUINO_STATUSES)


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
        db.execute("UPDATE arduino_projects SET name=?,board=?,status=?,"
                   "tinkercad_url=?,code=?,description=? WHERE id=?", vals + (pid,))
    else:
        db.execute("INSERT INTO arduino_projects(name,board,status,tinkercad_url,code,description)"
                   " VALUES(?,?,?,?,?,?)", vals)
    db.commit(); db.close()
    flash("Salvato", "success"); return redirect(url_for("arduino.arduino"))


@bp.route("/<int:pid>/delete", methods=["POST"])
@login_required
def arduino_delete(pid):
    db = get_db(); db.execute("DELETE FROM arduino_projects WHERE id=?", (pid,))
    db.commit(); db.close()
    flash("Eliminato", "success"); return redirect(url_for("arduino.arduino"))