#!/usr/bin/env python
"""Le prove di «resta collegato su questo dispositivo». Non tocca `hub.db`.

    python scripts/prova_ricorda.py [--tieni]

Gira su un DB **suo**, creato da `init_db()` in una cartella temporanea, e guida le
route vere dal test client — `/login`, `/logout`, `/admin/utenti/<id>/password` e
`.../dimentica`.

⚠️ La cosa che queste prove devono difendere, prima di tutte le altre: **la password
non si ricorda**. Quello che si ricorda è una sessione, cioè un numero casuale da 32
byte che vive nel cookie e di cui nel DB resta solo l'impronta. Se un giorno qualcuno
«semplificasse» mettendo la password nel cookie, la prova qui sotto che legge il
cookie e lo confronta con la password sarebbe l'unica cosa a dirlo.

Cosa dimostra, in ordine:

- che **senza la spunta non cambia niente**: nessun cookie, nessuna riga, e chiudendo
  il browser si è fuori. Una spunta che ricorda anche quando non l'hai messa sarebbe
  il peggiore dei difetti, perché non si vede
- che **con la spunta** nasce una riga e un cookie, che il cookie **non contiene la
  password** e nemmeno lo username, e che il DB tiene l'**impronta** e non il token
- che un browser **senza sessione ma col cookie** rientra, e ci rientra **con il suo
  ruolo** — non da amministratore per sbaglio
- che il **logout revoca questo dispositivo** e non gli altri: un logout che lascia
  viva la riga rimetterebbe dentro al primo F5, cioè il contrario di «esci»
- che un **token scaduto** non vale più, e che la riga viene buttata invece di restare
  lì come un permesso morto
- che un **token inventato** non apre niente
- che **cambiare la password fa cadere tutti i dispositivi**, e che il pulsante
  «Dimentica i dispositivi» fa lo stesso **senza** toccare la password
"""
import argparse
import os
import shutil
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []
PW = "password-di-prova"


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def _cookie(client, nome):
    """Il valore del cookie, o `None`. Werkzeug ne ha cambiato l'API più volte."""
    try:
        return client.get_cookie(nome).value          # Werkzeug >= 2.3
    except Exception:
        pass
    for c in getattr(client, "cookie_jar", []) or []:
        if c.name == nome:
            return c.value
    return None


def _quante(db, uid=None):
    if uid is None:
        return db.execute("SELECT COUNT(*) FROM sessioni_ricordate").fetchone()[0]
    return db.execute("SELECT COUNT(*) FROM sessioni_ricordate WHERE user_id=?",
                      (uid,)).fetchone()[0]


def prove(dove):
    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()

    db = extensions.get_db()
    for nome, ruolo in (("capo", "admin"), ("tizio", "user")):
        db.execute("INSERT INTO users(username,password,display_name,role) "
                   "VALUES(?,?,?,?)", (nome, extensions.hash_password(PW),
                                       nome.capitalize(), ruolo))
    db.commit()
    ids = {r["username"]: r["id"] for r in db.execute("SELECT id, username FROM users")}
    db.close()

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    def entra(c, chi="tizio", ricorda=False, pw=PW):
        dati = {"username": chi, "password": pw}
        if ricorda:
            dati["ricorda"] = "1"
        return c.post("/login", data=dati, follow_redirects=True)

    print("\n== 1. senza la spunta non cambia niente ==")
    with app.test_client() as c:
        r = entra(c)
        esito("il login riesce", r.status_code == 200 and b"Credenziali errate" not in r.data)
        esito("nessun cookie «ricorda»", _cookie(c, extensions.COOKIE_RICORDA) is None)
        db = extensions.get_db()
        esito("e nessuna riga in `sessioni_ricordate`", _quante(db) == 0)
        db.close()

    print("\n== 2. con la spunta: una riga, un cookie, e NESSUNA password ==")
    with app.test_client() as c:
        entra(c, ricorda=True)
        token = _cookie(c, extensions.COOKIE_RICORDA)
        esito("il cookie c'è", bool(token), f"lungo {len(token or '')}")
        # ⚠️ La prova che conta più di tutte: nel cookie non c'è la password, non c'è
        # il suo hash e non c'è nemmeno lo username. C'è un numero casuale e basta.
        esito("il cookie NON contiene la password", PW not in (token or ""))
        esito("né lo username", "tizio" not in (token or "").lower())
        db = extensions.get_db()
        esito("c'è una riga sola, ed è sua", _quante(db, ids["tizio"]) == 1)
        riga = db.execute("SELECT * FROM sessioni_ricordate").fetchone()
        esito("il DB tiene l'**impronta**, non il token",
              riga["impronta"] != token
              and riga["impronta"] == extensions._impronta(token),
              f"impronta {riga['impronta'][:16]}…")
        esito("e non c'è nessuna colonna che somigli a una password",
              not any("pass" in k.lower() for k in riga.keys()),
              ", ".join(riga.keys()))
        esito("la scadenza è scritta nella riga, non solo nel cookie",
              bool(riga["scade_il"]), riga["scade_il"])
        db.close()

    print("\n== 3. un browser col solo cookie rientra, e col suo ruolo ==")
    with app.test_client() as c:
        entra(c, chi="tizio", ricorda=True)
        token = _cookie(c, extensions.COOKIE_RICORDA)
    with app.test_client() as c2:
        c2.set_cookie(extensions.COOKIE_RICORDA, token)
        r = c2.get("/", follow_redirects=False)
        esito("la home non rimbalza al login", r.status_code == 200,
              f"status={r.status_code}")
        with c2.session_transaction() as s:
            esito("la sessione è stata rimessa in piedi col nome giusto",
                  s.get("username") == "tizio", str(s.get("username")))
            esito("e con il suo ruolo, non da amministratore",
                  s.get("role") == "user", str(s.get("role")))
            esito("e con il suo user_id, che serve a ambito_utente()",
                  s.get("user_id") == ids["tizio"])
        # ⚠️ `/admin/utenti` è la prova che il ruolo non si è gonfiato per strada:
        # un utente normale lì dentro non entra.
        r = c2.get("/admin/utenti", follow_redirects=True)
        esito("e da lì non entra in Utenti", b"Serve un account amministratore" in r.data)

    print("\n== 4. il logout revoca questo dispositivo e non gli altri ==")
    # ⚠️ Si riparte da zero, e non è pulizia: i blocchi qui sopra lasciano vive le
    # loro righe **di proposito** — un test client buttato via è un browser chiuso,
    # e una sessione ricordata deve sopravvivere a quello, che è tutto il punto.
    # Senza questa riga il conto qui sotto sarebbe quattro, e un «2 != 4» avrebbe
    # fatto sembrare rotto il codice invece della prova.
    db = extensions.get_db()
    db.execute("DELETE FROM sessioni_ricordate")
    db.commit()
    db.close()
    with app.test_client() as c:
        entra(c, ricorda=True)
        primo = _cookie(c, extensions.COOKIE_RICORDA)
    with app.test_client() as c:
        entra(c, ricorda=True)
        secondo = _cookie(c, extensions.COOKIE_RICORDA)
        db = extensions.get_db()
        esito("due dispositivi, due righe", _quante(db, ids["tizio"]) == 2)
        db.close()
        c.get("/logout")
        db = extensions.get_db()
        esito("dopo il logout ne resta una", _quante(db, ids["tizio"]) == 1)
        esito("ed è quella dell'altro dispositivo",
              db.execute("SELECT impronta FROM sessioni_ricordate").fetchone()["impronta"]
              == extensions._impronta(primo))
        db.close()
    with app.test_client() as c3:
        c3.set_cookie(extensions.COOKIE_RICORDA, secondo)
        r = c3.get("/", follow_redirects=True)
        esito("e col cookie appena revocato si finisce al login",
              b"Credenziali" in r.data or b"Username" in r.data)
    with app.test_client() as c4:
        c4.set_cookie(extensions.COOKIE_RICORDA, primo)
        esito("mentre l'altro dispositivo entra ancora",
              c4.get("/", follow_redirects=False).status_code == 200)

    print("\n== 5. una scaduta non vale più, e non resta lì ==")
    db = extensions.get_db()
    db.execute("UPDATE sessioni_ricordate SET scade_il='2020-01-01 00:00:00'")
    db.commit()
    db.close()
    with app.test_client() as c:
        c.set_cookie(extensions.COOKIE_RICORDA, primo)
        r = c.get("/", follow_redirects=True)
        esito("col token scaduto si finisce al login",
              b"Credenziali" in r.data or b"Username" in r.data)
        db = extensions.get_db()
        esito("e la riga scaduta è stata buttata", _quante(db) == 0)
        db.close()

    print("\n== 6. un token inventato non apre niente ==")
    with app.test_client() as c:
        c.set_cookie(extensions.COOKIE_RICORDA, "questo-me-lo-sono-inventato")
        r = c.get("/", follow_redirects=True)
        esito("si finisce al login", b"Credenziali" in r.data or b"Username" in r.data)
        with c.session_transaction() as s:
            esito("e in sessione non c'è nessuno", s.get("username") is None)

    print("\n== 7. cambiare la password fa cadere tutti i dispositivi ==")
    with app.test_client() as c:
        entra(c, ricorda=True)
        vivo = _cookie(c, extensions.COOKIE_RICORDA)
    with app.test_client() as c:
        entra(c, ricorda=True)
    db = extensions.get_db()
    esito("due dispositivi collegati", _quante(db, ids["tizio"]) == 2)
    db.close()
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "capo"; s["role"] = "admin"; s["user_id"] = ids["capo"]
        r = c.post(f"/admin/utenti/{ids['tizio']}/password",
                   data={"password": "unaltra-password"}, follow_redirects=True)
        testo = r.data.decode("utf-8", "replace")
        esito("il messaggio dice che i dispositivi sono caduti",
              "dispositivi" in testo and "disconnessi" in testo)
    db = extensions.get_db()
    esito("e infatti non ce n'è più nessuno", _quante(db, ids["tizio"]) == 0)
    db.close()
    with app.test_client() as c:
        c.set_cookie(extensions.COOKIE_RICORDA, vivo)
        r = c.get("/", follow_redirects=True)
        esito("il cookie di prima non apre più",
              b"Credenziali" in r.data or b"Username" in r.data)

    print("\n== 8. «Dimentica i dispositivi» senza toccare la password ==")
    with app.test_client() as c:
        entra(c, ricorda=True, pw="unaltra-password")
        esito("si rientra con la password nuova",
              _cookie(c, extensions.COOKIE_RICORDA) is not None)
    with app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "capo"; s["role"] = "admin"; s["user_id"] = ids["capo"]
        r = c.get("/admin/utenti")
        esito("la pagina Utenti dice quanti dispositivi ha",
              "1 dispositivo collegato" in r.data.decode("utf-8", "replace"))
        r = c.post(f"/admin/utenti/{ids['tizio']}/dimentica", follow_redirects=True)
        esito("il pulsante risponde e lo dichiara",
              "La password resta quella di prima" in r.data.decode("utf-8", "replace"))
    db = extensions.get_db()
    esito("nessun dispositivo resta", _quante(db, ids["tizio"]) == 0)
    db.close()
    with app.test_client() as c:
        r = entra(c, pw="unaltra-password")
        esito("e la password è davvero rimasta quella",
              b"Credenziali errate" not in r.data)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true",
                    help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_ricorda_")
    try:
        prove(dove)
    finally:
        if args.tieni:
            print(f"\ncartella tenuta: {dove}")
        else:
            shutil.rmtree(dove, ignore_errors=True)
    passate = sum(esiti)
    print(f"\n{passate} prove su {len(esiti)}." +
          ("  Tutte passate." if passate == len(esiti) else "  FALLITE."))
    return 0 if passate == len(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
