import json
from datetime import datetime
from flask import Blueprint, render_template, Response, session
from extensions import get_db, login_required

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def dashboard():
    db = get_db()
    done  = db.execute("SELECT COUNT(*) FROM python_topics WHERE done=1").fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM python_topics").fetchone()[0]
    stats = {
        "games":        db.execute("SELECT COUNT(*) FROM games").fetchone()[0],
        "games_done":   db.execute("SELECT COUNT(*) FROM games WHERE status='Completato'").fetchone()[0],
        "games_active": db.execute("SELECT COUNT(*) FROM games WHERE status='In corso'").fetchone()[0],
        "teams":        db.execute("SELECT COUNT(*) FROM teams").fetchone()[0],
        "arduino":      db.execute("SELECT COUNT(*) FROM arduino_projects").fetchone()[0],
        "builds":       db.execute("SELECT COUNT(*) FROM pc_builds").fetchone()[0],
        "python_done":  done, "python_total": total,
        "python_pct":   round(done / total * 100) if total else 0,
    }
    recent_games   = db.execute("SELECT * FROM games ORDER BY created_at DESC LIMIT 6").fetchall()
    arduino_recent = db.execute("SELECT * FROM arduino_projects ORDER BY created_at DESC LIMIT 4").fetchall()
    pc_builds = db.execute("""
        SELECT b.id, b.name, COALESCE(SUM(c.price), 0) AS total
        FROM pc_builds b LEFT JOIN pc_components c ON c.build_id=b.id
        GROUP BY b.id ORDER BY b.created_at DESC LIMIT 4""").fetchall()
    db.close()
    return render_template(
        "dashboard.html",
        stats=stats,
        recent_games=recent_games,
        arduino_recent=arduino_recent,
        pc_builds=pc_builds,
        now=datetime.now().strftime("%A %d %B %Y"),
        display_name=session.get("display_name", ""),
    )


@bp.route("/export")
@login_required
def export_data():
    db = get_db()
    data = {
        "exported_at": datetime.now().isoformat(),
        "games":   [dict(r) for r in db.execute("SELECT * FROM games").fetchall()],
        "teams":   [],
        "arduino": [dict(r) for r in db.execute("SELECT * FROM arduino_projects").fetchall()],
        "python":  [dict(r) for r in db.execute("SELECT * FROM python_topics").fetchall()],
        "pc_builds": [],
    }
    for t in db.execute("SELECT * FROM teams").fetchall():
        m = [dict(x) for x in db.execute(
            "SELECT * FROM team_members WHERE team_id=? ORDER BY slot", (t["id"],)).fetchall()]
        d = dict(t); d["members"] = m; data["teams"].append(d)
    for b in db.execute("SELECT * FROM pc_builds").fetchall():
        c = [dict(x) for x in db.execute(
            "SELECT * FROM pc_components WHERE build_id=?", (b["id"],)).fetchall()]
        d = dict(b); d["components"] = c; data["pc_builds"].append(d)
    db.close()
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=personal-hub-export.json"},
    )