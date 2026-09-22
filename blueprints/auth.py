"""Login, logout, e la spunta «ricorda credenziali».

⚠️ **Non si ricorda la password, si ricorda una sessione.** La password non esce mai
da `users`: la spunta scrive una riga in `sessioni_ricordate` e mette nel browser un
numero casuale da 32 byte, di cui nel DB resta solo l'impronta. Vale 30 giorni, si
revoca (dal logout per questo dispositivo, dalla pagina Utenti per tutti, e da sola a
ogni cambio password), e la scadenza sta **nella riga** — non solo nel `max_age` del
cookie, che vive sul PC di chi naviga e quindi non è un dato di cui fidarsi.
"""
from flask import (Blueprint, render_template, request, session, redirect,
                   url_for, flash, make_response)
from extensions import (get_db, verifica_password, hash_password, COOKIE_RICORDA,
                        GIORNI_RICORDA, crea_sessione_ricordata, dimentica_sessione)

bp = Blueprint("auth", __name__)


def _accendi_sessione(utente):
    session["username"] = utente["username"]
    session["display_name"] = utente["display_name"]
    session["role"] = utente["role"]
    # L'id serve a `ambito_utente()`: e' con questo che si decide **di chi**
    # sono le righe, non con lo username. Chi era gia' dentro quando la
    # colonna e' entrata in servizio lo riceve da `utente_id()`, che lo
    # ripesca per nome.
    session["user_id"] = utente["id"]


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
        if corretta:
            _accendi_sessione(utente)
            token = None
            if request.form.get("ricorda"):
                token = crea_sessione_ricordata(
                    db, utente["id"], request.headers.get("User-Agent", ""))
                db.commit()
            db.close()
            risposta = make_response(redirect(url_for("dashboard.dashboard")))
            if token:
                _metti_cookie(risposta, token)
            return risposta
        db.close()
        flash("Credenziali errate", "error")
    return render_template("login.html")


def _metti_cookie(risposta, token):
    """⚠️ `secure` segue la richiesta, non è fisso.

    In casa l'hub gira in **http**, e un cookie `secure` lì non verrebbe mandato
    mai: la spunta sembrerebbe rotta senza dare nessun errore. Il giorno che l'app
    esce di casa (§1.5) è in https, e il cookie diventa `secure` da sé. `httponly`
    e `samesite` invece valgono sempre: al token nessun JavaScript deve arrivare.
    """
    risposta.set_cookie(COOKIE_RICORDA, token,
                        max_age=GIORNI_RICORDA * 24 * 3600,
                        httponly=True, samesite="Lax", secure=request.is_secure)


@bp.route("/logout")
def logout():
    # ⚠️ Prima `session.clear()`, ma anche la riga: un logout che lascia viva la
    # sessione ricordata rimetterebbe dentro al primo `F5`, ed è esattamente il
    # contrario di quello che uno chiede premendo «esci».
    token = request.cookies.get(COOKIE_RICORDA)
    if token:
        db = get_db()
        dimentica_sessione(db, token)
        db.commit()
        db.close()
    session.clear()
    risposta = make_response(redirect(url_for("auth.login")))
    risposta.delete_cookie(COOKIE_RICORDA)
    return risposta
