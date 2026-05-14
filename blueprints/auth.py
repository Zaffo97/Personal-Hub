import hashlib
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from extensions import get_db

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        pw = hashlib.sha256(request.form.get("password", "").encode()).hexdigest()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form.get("username", ""), pw),
        ).fetchone()
        db.close()
        if user:
            session["username"] = user["username"]
            session["display_name"] = user["display_name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard.dashboard"))
        flash("Credenziali errate", "error")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))