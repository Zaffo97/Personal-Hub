import json
from datetime import datetime
from flask import Blueprint, render_template, Response, session
from extensions import (get_db, login_required, sezioni_utente,
                        ambito_utente, utente_id)

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
    # ⚠️ Due domande diverse, due filtri diversi. I permessi per sezione dicono **cosa**
    # si vede; il proprietario dice **di chi** sono le righe contate. Senza il secondo,
    # la dashboard diceva a un utente quanti team e quanti giochi esistono in tutto —
    # cioè proprio il numero che le altre pagine gli nascondono.
    cond, par = ambito_utente()
    uid = utente_id()

    def se(slug, query, default=0):
        return db.execute(query, par).fetchone()[0] if slug in permesse else default

    # Il progresso di Python è personale per definizione: qui non vale la deroga
    # dell'amministratore, che sui propri argomenti è un utente come gli altri.
    done  = db.execute("SELECT COUNT(*) FROM python_progress WHERE user_id=? AND done=1",
                       (uid,)).fetchone()[0] if "python" in permesse else 0
    # L'elenco dei 53 argomenti è condiviso: il totale non si filtra.
    total = db.execute("SELECT COUNT(*) FROM python_topics").fetchone()[0] if "python" in permesse else 0
    stats = {
        "games":        se("gaming", f"SELECT COUNT(*) FROM games WHERE {cond}"),
        "games_done":   se("gaming", f"SELECT COUNT(*) FROM games WHERE status='Completato' AND {cond}"),
        "games_active": se("gaming", f"SELECT COUNT(*) FROM games WHERE status='In corso' AND {cond}"),
        "teams":        se("pokemon", f"SELECT COUNT(*) FROM teams WHERE {cond}"),
        "arduino":      se("arduino", f"SELECT COUNT(*) FROM arduino_projects WHERE {cond}"),
        "builds":       se("pcbuilder", f"SELECT COUNT(*) FROM pc_builds WHERE {cond}"),
        "python_done":  done, "python_total": total,
        "python_pct":   round(done / total * 100) if total else 0,
    }
    recent_games = db.execute(
        f"SELECT * FROM games WHERE {cond} ORDER BY created_at DESC LIMIT 6",
        par).fetchall() if "gaming" in permesse else []
    arduino_recent = db.execute(
        f"SELECT * FROM arduino_projects WHERE {cond} ORDER BY created_at DESC LIMIT 4",
        par).fetchall() if "arduino" in permesse else []
    # Qui la tabella ha un alias, quindi la condizione va chiesta con quello: `user_id`
    # nudo, in una join, non direbbe di quale delle due tabelle si parla.
    cond_b, par_b = ambito_utente("b.user_id")
    pc_builds = db.execute(f"""
        SELECT b.id, b.name, COALESCE(SUM(c.price), 0) AS total
        FROM pc_builds b LEFT JOIN pc_components c ON c.build_id=b.id
        WHERE {cond_b}
        GROUP BY b.id ORDER BY b.created_at DESC LIMIT 4""",
        par_b).fetchall() if "pcbuilder" in permesse else []
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
    # Stesso doppio filtro della dashboard: le sezioni permesse dicono quali chiavi
    # compaiono, il proprietario quali righe ci finiscono dentro.
    cond, par = ambito_utente()
    uid = utente_id()
    data = {
        "exported_at": datetime.now().isoformat(),
        "sezioni_incluse": permesse,
        "games":   [dict(r) for r in db.execute(
                       f"SELECT * FROM games WHERE {cond}", par).fetchall()]
                   if "gaming" in permesse else [],
        "teams":   [],
        "arduino": [dict(r) for r in db.execute(
                       f"SELECT * FROM arduino_projects WHERE {cond}", par).fetchall()]
                   if "arduino" in permesse else [],
        # L'elenco degli argomenti è condiviso, la spunta no: si esporta l'elenco con
        # **il progresso di chi scarica**, non con la colonna `done` della riga, che
        # dal 19/08/2026 è ferma alla fotografia della migrazione.
        "python":  [dict(r) for r in db.execute(
                       "SELECT t.id, t.category, t.name, COALESCE(p.done, 0) AS done "
                       "FROM python_topics t LEFT JOIN python_progress p "
                       "ON p.topic_id=t.id AND p.user_id=? ORDER BY t.id", (uid,)).fetchall()]
                   if "python" in permesse else [],
        "pc_builds": [],
    }
    if "pokemon" in permesse:
        for t in db.execute(f"SELECT * FROM teams WHERE {cond}", par).fetchall():
            m = [dict(x) for x in db.execute(
                "SELECT * FROM team_members WHERE team_id=? ORDER BY slot", (t["id"],)).fetchall()]
            d = dict(t); d["members"] = m; data["teams"].append(d)
    if "pcbuilder" in permesse:
        for b in db.execute(f"SELECT * FROM pc_builds WHERE {cond}", par).fetchall():
            c = [dict(x) for x in db.execute(
                "SELECT * FROM pc_components WHERE build_id=?", (b["id"],)).fetchall()]
            d = dict(b); d["components"] = c; data["pc_builds"].append(d)
    db.close()
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=personal-hub-export.json"},
    )