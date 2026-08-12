from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from extensions import get_db, verifica_password, hash_password

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # ⚠️ Prima la riga cercava l'utente **con l'hash nel WHERE**, cioè confrontava
        # in SQL: funzionava solo perché sha256 dà sempre lo stesso risultato. Gli hash
        # nuovi hanno un sale casuale, quindi due hash della stessa password sono
        # diversi e un confronto per uguaglianza non troverebbe mai nessuno. Ora si
        # cerca per nome e si verifica in Python.
        db = get_db()
        utente = db.execute("SELECT * FROM users WHERE username=?",
                            (request.form.get("username", ""),)).fetchone()
        corretta, da_riscrivere = (False, False)
        if utente:
            corretta, da_riscrivere = verifica_password(
                utente["password"], request.form.get("password", ""))
        if corretta and da_riscrivere:
            # L'unico istante in cui la password in chiaro esiste: è qui che l'hash
            # vecchio diventa forte, senza che l'utente debba fare niente.
            db.execute("UPDATE users SET password=? WHERE id=?",
                       (hash_password(request.form.get("password", "")), utente["id"]))
            db.commit()
        db.close()
        if corretta:
            session["username"] = utente["username"]
            session["display_name"] = utente["display_name"]
            session["role"] = utente["role"]
            return redirect(url_for("dashboard.dashboard"))
        flash("Credenziali errate", "error")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))