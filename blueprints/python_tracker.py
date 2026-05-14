from flask import Blueprint, render_template, redirect, url_for
from extensions import get_db, login_required

bp = Blueprint("python_tracker", __name__, url_prefix="/python")


@bp.route("/")
@login_required
def python_tracker():
    db     = get_db()
    topics = db.execute("SELECT * FROM python_topics ORDER BY id").fetchall()
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
    cur = db.execute("SELECT done FROM python_topics WHERE id=?", (tid,)).fetchone()
    if cur:
        db.execute("UPDATE python_topics SET done=? WHERE id=?",
                   (0 if cur["done"] else 1, tid))
        db.commit()
    db.close()
    return redirect(url_for("python_tracker.python_tracker"))