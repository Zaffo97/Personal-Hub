import os

from flask import (Blueprint, render_template, redirect, url_for, request, jsonify,
                   flash, abort, send_file)
from extensions import get_db, login_required, utente_id, e_admin, ambito_utente, _i
import python_esegui
import python_sorgenti as S

bp = Blueprint("python_tracker", __name__, url_prefix="/python")

STATI = ["Idea", "In corso", "Funziona", "Archiviato"]
CARTELLA_PYODIDE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "static", "vendor", "pyodide-314.0.7", "pyodide.asm.wasm")


def _esecuzione():
    """Cosa può fare chi guarda: il browser se Pyodide c'è, il PC se è admin."""
    return {"browser": os.path.isfile(CARTELLA_PYODIDE),
            "pc": e_admin() and python_esegui.attivo(),
            "tempo": python_esegui.TEMPO_MASSIMO}


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
    # Le note sono **di chi le scrive**, anche per l'admin: come le spunte, sono lo
    # studio di una persona, e vedere quelle degli altri mescolate alle proprie non
    # servirebbe a niente. A parità di argomento vince la più recente (vedi init_db).
    note = {}
    for r in db.execute("SELECT * FROM python_note WHERE user_id=? ORDER BY aggiornato_il, id",
                        (uid,)):
        note[r["topic_id"]] = {"testo": r["testo"] or "", "codice": r["codice"] or ""}
    condp, parp = ambito_utente(colonna="p.user_id")
    progetti = [dict(r) for r in db.execute(
        "SELECT p.*, (SELECT COUNT(*) FROM python_file f WHERE f.progetto_id=p.id) AS quanti "
        f"FROM python_progetti p WHERE {condp} ORDER BY p.created_at DESC, p.id DESC", parp)]
    cond, par = ambito_utente()
    frammenti = [dict(r) for r in db.execute(
        f"SELECT * FROM python_frammenti WHERE {cond} ORDER BY titolo COLLATE NOCASE", par)]
    nomi_utenti = {r["id"]: r["username"] for r in
                   db.execute("SELECT id, username FROM users")} if e_admin() else {}
    db.close()
    by_cat = {}
    for t in topics:
        by_cat.setdefault(t["category"], []).append(t)
    done  = sum(1 for t in topics if t["done"])
    total = len(topics)
    return render_template("python.html", by_cat=by_cat, done=done, total=total,
                           pct=round(done / total * 100) if total else 0,
                           note=note, progetti=progetti, frammenti=frammenti,
                           stati=STATI, esecuzione=_esecuzione(), nomi_utenti=nomi_utenti)


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


@bp.route("/esegui", methods=["POST"])
@login_required
def python_esegui_pc():
    """Esegue del codice **sul PC dell'hub**. Solo un amministratore: vedi python_esegui.py.

    ⚠️ Il controllo sta qui e non nel template: nascondere il pulsante non basta, una
    POST si manda anche a mano."""
    if not e_admin():
        return jsonify({"errore": "eseguire sul PC è riservato agli amministratori"}), 403
    d = request.get_json(silent=True) or {}
    file = d.get("file")
    if not isinstance(file, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                             for k, v in file.items()):
        return jsonify({"errore": "file mancanti o illeggibili"}), 400
    return jsonify(python_esegui.esegui(file, d.get("principale"), d.get("stdin") or "",
                                        bool(d.get("test"))))


# ── I progetti ────────────────────────────────────────────────────────────────

def _progetto(db, pid):
    cond, par = ambito_utente()
    return db.execute(f"SELECT * FROM python_progetti WHERE id=? AND {cond}",
                      (pid,) + tuple(par)).fetchone()


def _file_di(db, pid):
    """I file del progetto `pid`, che il chiamante ha **già** verificato con `_progetto()`."""
    return {r["nome"]: r["contenuto"] or "" for r in db.execute(
        "SELECT nome, contenuto FROM python_file WHERE progetto_id=? ORDER BY nome", (pid,))}


def _scrivi_file(db, pid, file, sostituisci):
    """Scrive i file sul progetto (già verificato). `sostituisci`: via quelli non nominati."""
    if sostituisci:
        db.execute("DELETE FROM python_file WHERE progetto_id=?", (pid,))
    else:
        for nome in file:
            db.execute("DELETE FROM python_file WHERE progetto_id=? AND nome=?", (pid, nome))
    for nome, testo in file.items():
        db.execute("INSERT INTO python_file(progetto_id, nome, contenuto) VALUES(?,?,?)",
                   (pid, nome, testo))


@bp.route("/progetto/nuovo", methods=["POST"])
@login_required
def progetto_nuovo():
    nome = (request.form.get("nome") or "").strip()
    if not nome:
        flash("Il nome serve", "error"); return redirect(url_for("python_tracker.python_tracker"))
    db = get_db()
    cur = db.execute("INSERT INTO python_progetti(nome, user_id) VALUES(?,?)", (nome, utente_id()))
    pid = cur.lastrowid
    _scrivi_file(db, pid, {"main.py": 'print("Ciao!")\n'}, sostituisci=True)
    db.commit(); db.close()
    return redirect(url_for("python_tracker.progetto", pid=pid))


@bp.route("/progetto/<int:pid>")
@login_required
def progetto(pid):
    db = get_db()
    p = _progetto(db, pid)
    if not p:
        db.close(); flash("Progetto non trovato", "error")
        return redirect(url_for("python_tracker.python_tracker"))
    file = _file_di(db, pid)
    db.close()
    return render_template("python_progetto.html", p=dict(p), file=file, stati=STATI,
                           esecuzione=_esecuzione(), github=S.github_valido(p["github_url"]))


@bp.route("/progetto/<int:pid>/salva", methods=["POST"])
@login_required
def progetto_salva(pid):
    """Salva tutto il progetto in una volta: dati e file. Tutto o niente."""
    d = request.get_json(silent=True) or {}
    file = d.get("file")
    if not isinstance(file, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                             for k, v in file.items()):
        return jsonify({"errore": "file illeggibili"}), 400
    cattivi = [n for n in file if not python_esegui.nome_valido(n)]
    if cattivi:
        return jsonify({"errore": "nomi di file non validi: " + ", ".join(cattivi[:5])}), 400
    if len(file) > S.FILE_MASSIMI:
        return jsonify({"errore": f"troppi file ({len(file)}, massimo {S.FILE_MASSIMI})"}), 400
    if sum(len(v.encode("utf-8")) for v in file.values()) > S.BYTE_TOTALI:
        return jsonify({"errore": "il progetto supera i 3 MB"}), 400
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"errore": "il nome serve"}), 400
    avvisi = []
    github = (d.get("github_url") or "").strip()
    if github and not S.github_valido(github):
        avvisi.append("link GitHub non salvato: serve github.com/proprietario/repo")
        github = None
    principale = d.get("principale") or "main.py"
    if principale not in file:
        avvisi.append(f"il file da eseguire «{principale}» non c'è")
    db = get_db()
    cond, par = ambito_utente()
    cur = db.execute("UPDATE python_progetti SET nome=?, stato=?, descrizione=?, github_url=?, "
                     f"principale=?, stdin=? WHERE id=? AND {cond}",
                     (nome, d.get("stato") if d.get("stato") in STATI else "Idea",
                      (d.get("descrizione") or "").strip() or None, github or None,
                      principale, d.get("stdin") or None, pid) + tuple(par))
    if cur.rowcount == 0:
        db.close(); return jsonify({"errore": "progetto non trovato"}), 404
    _scrivi_file(db, pid, file, sostituisci=True)
    db.commit(); db.close()
    return jsonify({"ok": True, "avvisi": avvisi})


def _aggiungi(pid, prendi):
    """Carica file da una fonte (`prendi()` → (file, saltati)) sul progetto, e lo dice."""
    db = get_db()
    if not _progetto(db, pid):
        db.close(); abort(404)
    try:
        file, saltati = prendi(db)
    except (ValueError, LookupError) as e:
        db.close(); flash(str(e), "error")
        return redirect(url_for("python_tracker.progetto", pid=pid))
    except Exception as e:
        db.close(); flash(f"Non riuscito: {e}", "error")
        return redirect(url_for("python_tracker.progetto", pid=pid))
    presenti = _file_di(db, pid)
    if len(set(presenti) | set(file)) > S.FILE_MASSIMI:
        db.close(); flash(f"Oltre {S.FILE_MASSIMI} file: non ho aggiunto niente", "error")
        return redirect(url_for("python_tracker.progetto", pid=pid))
    _scrivi_file(db, pid, file, sostituisci=False)
    db.commit(); db.close()
    sostituiti = sorted(set(file) & set(presenti))
    msg = f"{len(file)} file aggiunti" + (f" ({len(sostituiti)} sostituiti: {', '.join(sostituiti[:5])})"
                                        if sostituiti else "")
    flash(msg, "success" if file else "error")
    if saltati:
        flash(f"Saltati {len(saltati)}: " + "; ".join(saltati[:8])
              + (" …" if len(saltati) > 8 else ""), "error")
    return redirect(url_for("python_tracker.progetto", pid=pid))


@bp.route("/progetto/<int:pid>/carica", methods=["POST"])
@login_required
def progetto_carica(pid):
    def prendi(_db):
        tutti, saltati = {}, []
        for fs in request.files.getlist("file"):
            if not fs or not fs.filename:
                continue
            f, s = S.da_caricamento(fs.filename, fs.read(S.BYTE_TOTALI + 1))
            tutti.update(f); saltati += s
        return tutti, saltati
    return _aggiungi(pid, prendi)


@bp.route("/progetto/<int:pid>/github", methods=["POST"])
@login_required
def progetto_github(pid):
    def prendi(db):
        return S.da_github(_progetto(db, pid)["github_url"])
    return _aggiungi(pid, prendi)


@bp.route("/progetto/<int:pid>/zip")
@login_required
def progetto_zip(pid):
    db = get_db()
    p = _progetto(db, pid)
    if not p:
        db.close(); abort(404)
    file = _file_di(db, pid)
    db.close()
    import io
    nome = "".join(c if c.isalnum() or c in "-_ " else "_" for c in p["nome"]).strip() or "progetto"
    return send_file(io.BytesIO(S.a_zip(file)), as_attachment=True,
                     download_name=f"{nome}.zip", mimetype="application/zip")


@bp.route("/progetto/<int:pid>/elimina", methods=["POST"])
@login_required
def progetto_elimina(pid):
    db = get_db()
    cond, par = ambito_utente()
    cur = db.execute(f"DELETE FROM python_progetti WHERE id=? AND {cond}", (pid,) + tuple(par))
    db.commit(); db.close()
    flash("Progetto eliminato" if cur.rowcount else "Non trovato",
          "success" if cur.rowcount else "error")
    return redirect(url_for("python_tracker.python_tracker"))


# ── Le note per argomento ───────────────────────────────────────────────────────

@bp.route("/nota/<int:tid>", methods=["POST"])
@login_required
def nota_salva(tid):
    uid = utente_id()
    d = request.get_json(silent=True) or {}
    testo, codice = (d.get("testo") or "").strip(), d.get("codice") or ""
    db = get_db()
    if not uid or not db.execute("SELECT 1 FROM python_topics WHERE id=?", (tid,)).fetchone():
        db.close(); return jsonify({"errore": "argomento non trovato"}), 404
    ultima = db.execute("SELECT id FROM python_note WHERE user_id=? AND topic_id=? "
                        "ORDER BY aggiornato_il DESC, id DESC", (uid, tid)).fetchone()
    if not testo and not codice.strip():
        db.execute("DELETE FROM python_note WHERE user_id=? AND topic_id=?", (uid, tid))
    elif ultima:
        db.execute("UPDATE python_note SET testo=?, codice=?, aggiornato_il=CURRENT_TIMESTAMP "
                   "WHERE id=? AND user_id=?", (testo, codice, ultima["id"], uid))
    else:
        db.execute("INSERT INTO python_note(user_id, topic_id, testo, codice) VALUES(?,?,?,?)",
                   (uid, tid, testo, codice))
    db.commit(); db.close()
    return jsonify({"ok": True})


# ── I frammenti ──────────────────────────────────────────────────────────────────

@bp.route("/frammento/salva", methods=["POST"])
@login_required
def frammento_salva():
    f = request.form
    fid = _i(f.get("frammento_id"))
    titolo = (f.get("titolo") or "").strip()
    if not titolo:
        flash("Il titolo serve", "error"); return redirect(url_for("python_tracker.python_tracker") + "#frammenti")
    # I tag si normalizzano: minuscoli, senza doppioni, separati da virgola.
    tag = ", ".join(dict.fromkeys(t.strip().lower() for t in (f.get("tag") or "").split(",") if t.strip()))
    vals = (titolo, tag or None, f.get("codice") or "", (f.get("note") or "").strip() or None)
    db = get_db()
    if fid:
        cond, par = ambito_utente()
        cur = db.execute(f"UPDATE python_frammenti SET titolo=?, tag=?, codice=?, note=? "
                         f"WHERE id=? AND {cond}", vals + (fid,) + tuple(par))
        if cur.rowcount == 0:
            db.close(); flash("Non trovato", "error")
            return redirect(url_for("python_tracker.python_tracker") + "#frammenti")
    else:
        db.execute("INSERT INTO python_frammenti(titolo, tag, codice, note, user_id) VALUES(?,?,?,?,?)",
                   vals + (utente_id(),))
    db.commit(); db.close()
    flash("Frammento salvato", "success")
    return redirect(url_for("python_tracker.python_tracker") + "#frammenti")


@bp.route("/frammento/<int:fid>/elimina", methods=["POST"])
@login_required
def frammento_elimina(fid):
    db = get_db()
    cond, par = ambito_utente()
    cur = db.execute(f"DELETE FROM python_frammenti WHERE id=? AND {cond}", (fid,) + tuple(par))
    db.commit(); db.close()
    flash("Frammento eliminato" if cur.rowcount else "Non trovato",
          "success" if cur.rowcount else "error")
    return redirect(url_for("python_tracker.python_tracker") + "#frammenti")
