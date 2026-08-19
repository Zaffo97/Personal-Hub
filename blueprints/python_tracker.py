from flask import Blueprint, render_template, redirect, url_for
from extensions import get_db, login_required, utente_id

bp = Blueprint("python_tracker", __name__, url_prefix="/python")


@bp.route("/")
@login_required
def python_tracker():
    db  = get_db()
    uid = utente_id()
    # L'elenco dei 53 argomenti e' uno solo e condiviso; la spunta viene da
    # `python_progress`, che e' per utente. La LEFT JOIN fa nascere a zero chi non ha
    # ancora spuntato niente, senza dover seminare 53 righe a ogni utente nuovo.
    # ⚠️ `done` prende il nome della colonna vecchia di proposito: i template la
    # leggono cosi', e cambiarlo qui vorrebbe dire cambiarlo anche li'.
    topics = db.execute(
        "SELECT t.id, t.category, t.name, COALESCE(p.done, 0) AS done "
        "FROM python_topics t "
        "LEFT JOIN python_progress p ON p.topic_id=t.id AND p.user_id=? "
        "ORDER BY t.id", (uid,)).fetchall()
    db.close()
    by_cat = {}
    for t in topics:
        by_cat.setdefault(t["category"], []).append(t)
    done  = sum(1 for t in topics if t["done"])
    total = len(topics)
    return render_template("python.html", by_cat=by_cat, done=done, total=total,
                           pct=round(done / total * 100) if total else 0)


@bp.route("/toggle/<int:tid>", methods=["POST"])
@login_required
def python_toggle(tid):
    db  = get_db()
    uid = utente_id()
    # Senza sessione non si spunta niente: `utente_id()` torna None solo li', e una
    # riga con `user_id` nullo sarebbe una spunta di nessuno.
    if uid and db.execute("SELECT 1 FROM python_topics WHERE id=?", (tid,)).fetchone():
        riga = db.execute("SELECT done FROM python_progress WHERE user_id=? AND topic_id=?",
                          (uid, tid)).fetchone()
        nuovo = 0 if (riga and riga["done"]) else 1
        db.execute("INSERT INTO python_progress(user_id, topic_id, done) VALUES(?,?,?) "
                   "ON CONFLICT(user_id, topic_id) DO UPDATE SET done=excluded.done",
                   (uid, tid, nuovo))
        db.commit()
    db.close()
    return redirect(url_for("python_tracker.python_tracker"))