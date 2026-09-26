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
                        GIORNI_RICORDA, crea_sessione_ricordata, dimentica_sessione,
                        COOKIE_LINGUA, preferenze_utente, salva_preferenza, TEMI,
                        LINGUE)
import log_hub

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
            log_hub.registra("accesso", f"Login di «{utente['username']}»"
                             + (" con «resta collegato»" if token else ""))
            tema, lingua = preferenze_utente(db, utente["id"])
            db.close()
            risposta = make_response(redirect(url_for("dashboard.dashboard")))
            if token:
                _metti_cookie(risposta, token)
            # ⚠️ È **qui** che «segue l'utente» diventa vero: entrando da un PC nuovo,
            # il tema e la lingua salvati si trasferiscono a questo browser. Il tema
            # va in sessione (lo rende il server nell'attributo `data-theme`), la
            # lingua nel cookie, perché `lingua_attiva()` legge quello su ogni pagina.
            # Chi non ha mai scelto non si porta dietro niente, e decide il browser.
            session["tema"] = tema
            if lingua:
                risposta.set_cookie(COOKIE_LINGUA, lingua, max_age=31536000,
                                    samesite="Lax")
            return risposta
        db.close()
        # ⚠️ Il nome tentato si scrive, la password **mai**. Il nome è tagliato: chi
        # sbaglia campo ci scrive dentro la password, e 64 caratteri bastano a
        # riconoscere un nome senza farne un archivio di quello che si digita.
        # Il motivo distingue «non esiste» da «password sbagliata», che a schermo non
        # si dice di proposito: qui lo legge solo un amministratore.
        log_hub.registra("accesso", "Login fallito", livello="avviso",
                         tentato=(request.form.get("username") or "")[:64],
                         motivo="password errata" if utente else "utente inesistente")
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


@bp.route("/preferenze", methods=["POST"])
def preferenze():
    """Salva sull'utente il tema o la lingua che ha appena scelto.

    ⚠️ **Senza sessione risponde 200 e non fa niente**, invece di 401. Chi chiama è il
    pulsante del tema, che sta anche sulla pagina di login: un errore lì sarebbe un
    rosso in console per un'azione che ha funzionato benissimo — il tema **si è**
    cambiato, semplicemente non c'è nessuno a cui attribuirlo.
    """
    salvate = {}
    if "username" in session:
        dati = request.get_json(silent=True) or {}
        db = get_db()
        r = db.execute("SELECT id FROM users WHERE username=?",
                       (session["username"],)).fetchone()
        if r:
            for campo in ("tema", "lingua"):
                if campo in dati and salva_preferenza(db, r["id"], campo, dati[campo]):
                    salvate[campo] = dati[campo]
            db.commit()
        db.close()
        # La sessione tiene il tema per non rileggerlo a ogni pagina: va aggiornata
        # qui, o fino al prossimo login il server renderebbe quello di prima.
        if "tema" in salvate:
            session["tema"] = salvate["tema"]
    return {"ok": True, "salvate": sorted(salvate)}


@bp.route("/logout")
def logout():
    # ⚠️ Prima `session.clear()`, ma anche la riga: un logout che lascia viva la
    # sessione ricordata rimetterebbe dentro al primo `F5`, ed è esattamente il
    # contrario di quello che uno chiede premendo «esci».
    if "username" in session:
        log_hub.registra("accesso", f"Logout di «{session['username']}»")
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
