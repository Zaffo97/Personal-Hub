from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import get_db, login_required, _i, _f
from data import GAME_STATUSES, GAME_PLATFORMS

bp = Blueprint("gaming", __name__, url_prefix="/gaming")


def _game_upsert(gid=None):
    f  = request.form
    db = get_db()
    vals = (
        f.get("title", ""), f.get("platform", ""), f.get("genre", ""),
        f.get("status", "Wishlist"),
        _f(f.get("hours_hltb")), f.get("cover_url", "") or None,
        _i(f.get("prog_story")), _i(f.get("prog_side")), _i(f.get("prog_collect")),
        f.get("date_start") or None, f.get("date_end") or None,
        f.get("notes", ""),
    )
    if gid:
        db.execute(
            "UPDATE games SET title=?,platform=?,genre=?,status=?,"
            "hours_hltb=?,cover_url=?,prog_story=?,prog_side=?,prog_collect=?,"
            "date_start=?,date_end=?,notes=? WHERE id=?",
            vals + (gid,),
        )
    else:
        db.execute(
            "INSERT INTO games(title,platform,genre,status,hours_hltb,cover_url,"
            "prog_story,prog_side,prog_collect,date_start,date_end,notes)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            vals,
        )
    db.commit(); db.close()


@bp.route("/")
@login_required
def gaming():
    db    = get_db()
    filt  = request.args.get("status", "")
    q     = request.args.get("q", "")
    sql   = "SELECT * FROM games WHERE 1=1"; params = []
    if filt: sql += " AND status=?";     params.append(filt)
    if q:    sql += " AND title LIKE ?"; params.append(f"%{q}%")
    sql  += " ORDER BY created_at DESC"
    games  = db.execute(sql, params).fetchall()
    counts = {s: db.execute("SELECT COUNT(*) FROM games WHERE status=?", (s,)).fetchone()[0]
              for s in GAME_STATUSES}
    counts["Tutti"] = db.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    db.close()
    return render_template("gaming.html", games=games, statuses=GAME_STATUSES,
                           platforms=GAME_PLATFORMS, current_filter=filt, q=q, counts=counts)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def game_new():
    if request.method == "POST":
        _game_upsert(); flash("Gioco aggiunto!", "success")
        return redirect(url_for("gaming.gaming"))
    return render_template("game_form.html", game=None,
                           statuses=GAME_STATUSES, platforms=GAME_PLATFORMS)


@bp.route("/<int:gid>/edit", methods=["GET", "POST"])
@login_required
def game_edit(gid):
    db   = get_db()
    game = db.execute("SELECT * FROM games WHERE id=?", (gid,)).fetchone()
    db.close()
    if not game:
        flash("Non trovato", "error"); return redirect(url_for("gaming.gaming"))
    if request.method == "POST":
        _game_upsert(gid); flash("Aggiornato!", "success")
        return redirect(url_for("gaming.gaming"))
    return render_template("game_form.html", game=game,
                           statuses=GAME_STATUSES, platforms=GAME_PLATFORMS)


@bp.route("/<int:gid>/delete", methods=["POST"])
@login_required
def game_delete(gid):
    db = get_db(); db.execute("DELETE FROM games WHERE id=?", (gid,))
    db.commit(); db.close()
    flash("Eliminato", "success"); return redirect(url_for("gaming.gaming"))