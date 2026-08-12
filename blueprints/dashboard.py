import json
from datetime import datetime
from flask import Blueprint, render_template, Response, session
from extensions import get_db, login_required, sezioni_utente

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def dashboard():
    # ⚠️ La Dashboard la vedono tutti, ma **non tutti i suoi contenuti**: prima
    # mostrava conteggi e ultimi elementi di ogni sezione a chiunque fosse entrato,
    # quindi da qui si leggeva quanti team Pokémon o quante build PC esistono anche
    # senza avere quelle sezioni. I permessi sarebbero stati decorativi.
    permesse = sezioni_utente()
    db = get_db()

    def se(slug, query, default=0):
        return db.execute(query).fetchone()[0] if slug in permesse else default

    done  = db.execute("SELECT COUNT(*) FROM python_topics WHERE done=1").fetchone()[0] if "python" in permesse else 0
    total = db.execute("SELECT COUNT(*) FROM python_topics").fetchone()[0] if "python" in permesse else 0
    stats = {
        "games":        se("gaming", "SELECT COUNT(*) FROM games"),
        "games_done":   se("gaming", "SELECT COUNT(*) FROM games WHERE status='Completato'"),
        "games_active": se("gaming", "SELECT COUNT(*) FROM games WHERE status='In corso'"),
        "teams":        se("pokemon", "SELECT COUNT(*) FROM teams"),
        "arduino":      se("arduino", "SELECT COUNT(*) FROM arduino_projects"),
        "builds":       se("pcbuilder", "SELECT COUNT(*) FROM pc_builds"),
        "python_done":  done, "python_total": total,
        "python_pct":   round(done / total * 100) if total else 0,
    }
    recent_games = db.execute(
        "SELECT * FROM games ORDER BY created_at DESC LIMIT 6").fetchall() if "gaming" in permesse else []
    arduino_recent = db.execute(
        "SELECT * FROM arduino_projects ORDER BY created_at DESC LIMIT 4").fetchall() if "arduino" in permesse else []
    pc_builds = db.execute("""
        SELECT b.id, b.name, COALESCE(SUM(c.price), 0) AS total
        FROM pc_builds b LEFT JOIN pc_components c ON c.build_id=b.id
        GROUP BY b.id ORDER BY b.created_at DESC LIMIT 4""").fetchall() if "pcbuilder" in permesse else []
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
    # ⚠️ Questo scarico dava **l'intero database** a chiunque avesse fatto login: un
    # utente con la sola sezione Gaming si portava via team Pokémon e build PC. Ora
    # esporta solo le sezioni che quell'utente può vedere — la voce nella sidebar
    # resta per tutti, ma il file contiene ciò a cui si ha diritto.
    permesse = sezioni_utente()
    db = get_db()
    data = {
        "exported_at": datetime.now().isoformat(),
        "sezioni_incluse": permesse,
        "games":   [dict(r) for r in db.execute("SELECT * FROM games").fetchall()]
                   if "gaming" in permesse else [],
        "teams":   [],
        "arduino": [dict(r) for r in db.execute("SELECT * FROM arduino_projects").fetchall()]
                   if "arduino" in permesse else [],
        "python":  [dict(r) for r in db.execute("SELECT * FROM python_topics").fetchall()]
                   if "python" in permesse else [],
        "pc_builds": [],
    }
    if "pokemon" in permesse:
        for t in db.execute("SELECT * FROM teams").fetchall():
            m = [dict(x) for x in db.execute(
                "SELECT * FROM team_members WHERE team_id=? ORDER BY slot", (t["id"],)).fetchall()]
            d = dict(t); d["members"] = m; data["teams"].append(d)
    if "pcbuilder" in permesse:
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