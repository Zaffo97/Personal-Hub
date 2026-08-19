"""Gestione utenti e permessi per sezione — solo per gli amministratori.

Il modello è quello chiesto a backlog: utenti **normali** e **amministratori**, e per
ognuno una spunta per sezione. Chi è admin vede tutto per definizione, quindi su di lui
le spunte non compaiono: sarebbero una promessa che il codice non mantiene.

⚠️ I permessi vivono in `users.sections`, un elenco di slug separati da virgole.
**Vuoto vale «tutte»**: è la scelta che tiene al sicuro chi c'era prima, perché la
colonna nasce vuota su tutti gli utenti esistenti.
"""
import re

from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   session)

from data import SEZIONI, SEZIONI_SLUG
from extensions import get_db, login_required, NESSUNA_SEZIONE, hash_password

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Dal 12/08/2026 le password nuove nascono già con lo schema forte (scrypt con sale
# di `werkzeug.security`). Le vecchie restano leggibili e vengono riscritte al primo
# login riuscito — vedi `verifica_password()` in extensions.py.
_hash = hash_password


def solo_admin(f):
    """Come login_required, ma richiede anche il ruolo. Applicato a tutto il blueprint."""
    from functools import wraps

    @wraps(f)
    def wrap(*a, **kw):
        if "username" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Serve un account amministratore.", "error")
            return redirect(url_for("dashboard.dashboard"))
        return f(*a, **kw)
    return wrap


@bp.before_request
@solo_admin
def _blocca_non_admin():
    """Il controllo sta qui e non sulle singole viste: una route nuova nasce protetta."""
    return None


def _sezioni_dal_form():
    """Le spunte del form -> valore per la colonna.

    ⚠️ Tre casi, non due, ed è il punto in cui è facile sbagliare: **tutte spuntate**
    si scrive vuoto (così resta «tutte» anche se domani se ne aggiunge una),
    **nessuna** si scrive `NESSUNA_SEZIONE` — perché `",".join([])` darebbe la stringa
    vuota, cioè esattamente il contrario di quello che l'admin ha appena spuntato.
    """
    scelte = [s for s in SEZIONI_SLUG if request.form.get("sez_" + s)]
    if len(scelte) == len(SEZIONI_SLUG):
        return ""
    if not scelte:
        return NESSUNA_SEZIONE
    return ",".join(scelte)


@bp.route("/utenti")
def utenti():
    db = get_db()
    righe = db.execute("SELECT id, username, display_name, role, sections"
                       " FROM users ORDER BY username COLLATE NOCASE").fetchall()
    db.close()
    utenti = []
    for r in righe:
        grezzo = (r["sections"] or "").strip()
        if r["role"] == "admin":
            permesse, nota = list(SEZIONI_SLUG), "tutte (amministratore)"
        elif not grezzo:
            permesse, nota = list(SEZIONI_SLUG), "tutte"
        elif grezzo == NESSUNA_SEZIONE:
            permesse, nota = [], "nessuna — vede solo la Dashboard"
        else:
            permesse = [s for s in SEZIONI_SLUG if s in
                        {x.strip() for x in grezzo.split(",")}]
            nota = f"{len(permesse)} su {len(SEZIONI_SLUG)}"
        utenti.append({"id": r["id"], "username": r["username"],
                       "display_name": r["display_name"], "role": r["role"],
                       "permesse": permesse, "nota": nota})
    return render_template("admin_utenti.html", utenti=utenti, sezioni=SEZIONI,
                           io_sono=session.get("username"))


@bp.route("/utenti/nuovo", methods=["POST"])
def utente_nuovo():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        flash("Nome utente non valido: da 3 a 32 caratteri fra lettere, cifre, . _ -", "error")
        return redirect(url_for("admin.utenti"))
    if len(password) < 8:
        flash("La password deve essere di almeno 8 caratteri.", "error")
        return redirect(url_for("admin.utenti"))

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        db.close()
        flash(f"Esiste già un utente «{username}».", "error")
        return redirect(url_for("admin.utenti"))
    ruolo = "admin" if request.form.get("role") == "admin" else "user"
    db.execute("INSERT INTO users(username,password,display_name,role,sections)"
               " VALUES(?,?,?,?,?)",
               (username, _hash(password),
                (request.form.get("display_name") or username).strip(),
                ruolo, "" if ruolo == "admin" else _sezioni_dal_form()))
    db.commit(); db.close()
    flash(f"Utente «{username}» creato.", "success")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:uid>/permessi", methods=["POST"])
def utente_permessi(uid):
    db = get_db()
    r = db.execute("SELECT username, role FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        db.close(); flash("Utente non trovato.", "error")
        return redirect(url_for("admin.utenti"))

    ruolo = "admin" if request.form.get("role") == "admin" else "user"
    # ⚠️ Non ci si può togliere il ruolo da soli, e non si può togliere l'ultimo
    # amministratore: senza questo controllo bastano due clic per chiudere fuori
    # tutti dalla schermata che serve a rimettere i permessi.
    if r["role"] == "admin" and ruolo != "admin":
        rimasti = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND id<>?",
                             (uid,)).fetchone()[0]
        if r["username"] == session.get("username"):
            db.close(); flash("Non puoi togliere a te stesso il ruolo di amministratore.", "error")
            return redirect(url_for("admin.utenti"))
        if rimasti == 0:
            db.close(); flash("Deve restare almeno un amministratore.", "error")
            return redirect(url_for("admin.utenti"))

    db.execute("UPDATE users SET role=?, sections=? WHERE id=?",
               (ruolo, "" if ruolo == "admin" else _sezioni_dal_form(), uid))
    db.commit(); db.close()
    flash(f"Permessi di «{r['username']}» aggiornati.", "success")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:uid>/password", methods=["POST"])
def utente_password(uid):
    password = request.form.get("password") or ""
    if len(password) < 8:
        flash("La password deve essere di almeno 8 caratteri.", "error")
        return redirect(url_for("admin.utenti"))
    db = get_db()
    r = db.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        db.close(); flash("Utente non trovato.", "error")
        return redirect(url_for("admin.utenti"))
    db.execute("UPDATE users SET password=? WHERE id=?", (_hash(password), uid))
    db.commit(); db.close()
    flash(f"Password di «{r['username']}» cambiata.", "success")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:uid>/elimina", methods=["POST"])
def utente_elimina(uid):
    db = get_db()
    r = db.execute("SELECT username, role FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        db.close(); flash("Utente non trovato.", "error")
        return redirect(url_for("admin.utenti"))
    if r["username"] == session.get("username"):
        db.close(); flash("Non puoi eliminare te stesso.", "error")
        return redirect(url_for("admin.utenti"))
    if r["role"] == "admin":
        rimasti = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND id<>?",
                             (uid,)).fetchone()[0]
        if rimasti == 0:
            db.close(); flash("Deve restare almeno un amministratore.", "error")
            return redirect(url_for("admin.utenti"))
    # I contenuti dell'utente **passano all'amministratore**, non si cancellano:
    # deciso il 19/08/2026. È la stessa scelta fatta per le righe che esistevano
    # prima che il proprietario esistesse, e l'unica che non perde niente — oggi
    # `hub_export.json` è la sola copia di `hub.db`, e la lancia Davide a mano.
    # ⚠️ Va fatto **prima** della DELETE: `get_db()` accende le chiavi esterne e
    # `user_id` punta a `users(id)`, quindi senza il travaso la cancellazione
    # fallirebbe invece di lasciare righe orfane.
    io_admin = db.execute("SELECT id FROM users WHERE username=?",
                          (session.get("username"),)).fetchone()
    passati = 0
    if io_admin:
        for tabella in ("games", "teams", "arduino_projects", "pc_builds"):
            cur = db.execute(f"UPDATE {tabella} SET user_id=? WHERE user_id=?",
                             (io_admin["id"], uid))
            passati += cur.rowcount
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit(); db.close()
    if passati:
        flash(f"Utente «{r['username']}» eliminato. {passati} righe di contenuto "
              "sono passate a te.", "success")
    else:
        flash(f"Utente «{r['username']}» eliminato.", "success")
    return redirect(url_for("admin.utenti"))
