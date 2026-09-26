#!/usr/bin/env python
"""Le prove del log dell'hub (`log_hub.py`, `/admin/log`). Non tocca `hub.db` né `logs/`.

    python scripts/prova_log.py [--tieni]

Gira su un DB **suo** in una cartella temporanea e guida le route vere dal test
client. Il log finisce accanto a quel DB — è la scelta di `log_hub.cartella()` — e la
prima cosa che la prova controlla è proprio questa: che il `logs/` vero **non cambi**.

Cosa dimostra, in ordine:

- che i due **login falliti** si scrivono come avviso, col nome tentato e il motivo,
  e che **nessuna password** — né tentata, né giusta, né creata, né cambiata — finisce
  nel file. È la cosa che un log di accessi non deve mai fare
- che il **login**, il **rientro** con «resta collegato», la **sezione non permessa**
  e il **logout** hanno ognuno la sua riga, con utente e indirizzo
- che le **azioni sugli utenti** (creare, cambiare la password) si scrivono
- che un **import** si scrive coi suoi numeri (Steam, che non chiede la rete)
- che un'**eccezione** in una route arriva nel log col traceback, e che la risposta
  resta quella di prima (il log guarda, non cambia l'errore)
- che l'**avvio** con `wsgi.py` si scrive, e con `create_app()` da solo no
- che `/admin/log` si apre, filtra, **esegue l'escape** di un nome tentato con dentro
  del codice, e a un utente normale resta chiusa
- che la **rotazione** tiene al più `QUANTI_VECCHI` file vecchi e la lettura li
  attraversa dal più recente
- che una **riga illeggibile** si conta invece di sparire
- che se il log **non si può scrivere**, la richiesta va avanti lo stesso
"""
import argparse
import contextlib
import io
import json
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
PW_SBAGLIATA = "sbagliata-di-prova-9876"
PW_NUOVO = "creata-dall-admin-5555"
PW_CAMBIATA = "cambiata-dall-admin-7777"


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def _impronta_vera():
    """Dimensione e data di ogni file del `logs/` vero, per dire che non è cambiato."""
    vera = os.path.join(RADICE, "logs")
    if not os.path.isdir(vera):
        return {}
    return {n: (os.path.getsize(os.path.join(vera, n)),
                os.path.getmtime(os.path.join(vera, n))) for n in os.listdir(vera)}


def _righe(log_hub):
    """Le righe del log corrente, dalla più vecchia."""
    percorso = os.path.join(log_hub.cartella(), log_hub.NOME)
    if not os.path.exists(percorso):
        return []
    with io.open(percorso, encoding="utf-8") as f:
        return [json.loads(r) for r in f if r.strip()]


def _grezzo(log_hub):
    testo = ""
    for n in range(log_hub.QUANTI_VECCHI + 1):
        p = log_hub._file(n)
        if os.path.exists(p):
            with io.open(p, encoding="utf-8") as f:
                testo += f.read()
    return testo


def prove(dove):
    prima_vera = _impronta_vera()

    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()

    db = extensions.get_db()
    # `tizio` vede solo il Gaming: serve la sezione non permessa.
    for nome, ruolo, sezioni in (("capo", "admin", ""), ("tizio", "user", "gaming")):
        db.execute("INSERT INTO users(username,password,display_name,role,sections) "
                   "VALUES(?,?,?,?,?)", (nome, extensions.hash_password(PW),
                                         nome.capitalize(), ruolo, sezioni))
    db.commit()
    ids = {r["username"]: r["id"] for r in db.execute("SELECT id, username FROM users")}
    db.close()

    import log_hub
    esito("il log sta accanto al DB di prova",
          os.path.abspath(log_hub.cartella()) == os.path.join(os.path.abspath(dove), "logs"),
          log_hub.cartella())

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    @app.route("/prova-errore")
    def _prova_errore():
        raise RuntimeError("guasto provocato dalla prova")

    esito("create_app() da solo non scrive un avvio",
          not any(r["categoria"] == "avvio" for r in _righe(log_hub)))

    def entra(c, chi, pw=PW, ricorda=False):
        dati = {"username": chi, "password": pw}
        if ricorda:
            dati["ricorda"] = "1"
        return c.post("/login", data=dati, follow_redirects=True)

    print("\n— accessi")
    with app.test_client() as c:
        entra(c, "nessuno", PW_SBAGLIATA)
        entra(c, "tizio", PW_SBAGLIATA)
        entra(c, "<script>alert(1)</script>", PW_SBAGLIATA)
    righe = _righe(log_hub)
    fallite = [r for r in righe if r["messaggio"] == "Login fallito"]
    esito("tre login falliti, tutti come avviso",
          len(fallite) == 3 and all(r["livello"] == "avviso" for r in fallite))
    esito("col nome tentato e il motivo giusto",
          [(r["dati"]["tentato"], r["dati"]["motivo"]) for r in fallite[:2]]
          == [("nessuno", "utente inesistente"), ("tizio", "password errata")],
          str([(r["dati"]["tentato"], r["dati"]["motivo"]) for r in fallite[:2]]))
    esito("con l'indirizzo, e senza utente (nessuno è dentro)",
          all(r["ip"] == "127.0.0.1" and r["utente"] is None for r in fallite))

    with app.test_client() as c:
        entra(c, "capo", ricorda=True)
        token = c.get_cookie(extensions.COOKIE_RICORDA).value
        # Rientro: un browser nuovo con solo il cookie.
        with app.test_client() as c2:
            c2.set_cookie(extensions.COOKIE_RICORDA, token)
            c2.get("/")
        righe = _righe(log_hub)
        esito("il login riuscito si scrive, con chi è entrato",
              any(r["messaggio"] == "Login di «capo» con «resta collegato»"
                  and r["utente"] == "capo" for r in righe))
        esito("il rientro con «resta collegato» si scrive",
              any(r["messaggio"] == "Rientro di «capo» con «resta collegato»"
                  for r in righe))
        esito("il token del cookie non è nel log", token not in _grezzo(log_hub))

        print("\n— utenti")
        c.post("/admin/utenti/nuovo", data={"username": "nuovo", "password": PW_NUOVO,
                                             "role": "user", "sez_gaming": "1"})
        c.post(f"/admin/utenti/{ids['tizio']}/password", data={"password": PW_CAMBIATA})
        righe = _righe(log_hub)
        esito("la creazione di un utente si scrive",
              any(r["categoria"] == "utenti" and r["messaggio"] == "Utente «nuovo» creato"
                  for r in righe))
        esito("il cambio password si scrive",
              any(r["categoria"] == "utenti"
                  and r["messaggio"] == "Password di «tizio» cambiata" for r in righe))

        print("\n— import")
        r = c.post("/gaming/steam/importa",
                   json={"giochi": [{"appid": 10, "titolo": "Gioco di prova", "ore": 3}]})
        esito("l'import da Steam risponde", r.status_code == 200, str(r.get_json()))
        esito("e si scrive coi suoi numeri",
              any(x["categoria"] == "import" and x.get("dati", {}).get("nuovi") == 1
                  for x in _righe(log_hub)))

        print("\n— errori")
        preso = None
        try:
            c.get("/prova-errore")
        except RuntimeError as e:          # in TESTING l'eccezione arriva fin qui
            preso = e
        esito("l'eccezione arriva a chi chiama come prima", preso is not None)
        errori = [x for x in _righe(log_hub) if x["categoria"] == "errore"]
        esito("e nel log c'è, come errore, col percorso",
              len(errori) == 1 and errori[0]["livello"] == "errore"
              and "GET /prova-errore" in errori[0]["messaggio"],
              errori[0]["messaggio"] if errori else "nessuna riga")
        esito("col traceback intero",
              bool(errori) and "guasto provocato dalla prova"
              in errori[0]["dati"]["traceback"]
              and "Traceback" in errori[0]["dati"]["traceback"])

        print("\n— la pagina")
        r = c.get("/admin/log")
        html = r.get_data(as_text=True)
        esito("/admin/log si apre", r.status_code == 200)
        esito("e mostra gli eventi", "Login di «capo» con «resta collegato»" in html
              and "guasto provocato dalla prova" in html)
        esito("il nome tentato con del codice esce con l'escape",
              "<script>alert(1)</script>" not in html
              and "&lt;script&gt;alert(1)&lt;/script&gt;" in html)
        r = c.get("/admin/log?categoria=errore")
        html = r.get_data(as_text=True)
        esito("il filtro per categoria tiene solo quella",
              "guasto provocato dalla prova" in html and "Login fallito" not in html)
        html = c.get("/admin/log?livello=avviso&q=tizio").get_data(as_text=True)
        esito("livello e ricerca insieme", "Login fallito" in html
              and "1 evento." in html, "1 evento." if "1 evento." in html else "conto diverso")
        html = c.get("/admin/log?q=info").get_data(as_text=True)
        esito("la ricerca guarda i valori, non i nomi dei campi",
              "Nessun evento con questi filtri." in html)

        c.get("/logout")
        esito("il logout si scrive", any(x["messaggio"] == "Logout di «capo»"
                                         for x in _righe(log_hub)))

    with app.test_client() as c:
        entra(c, "tizio", PW_CAMBIATA)
        c.get("/pokemon/")
        esito("una sezione non permessa si scrive come avviso",
              any(x["messaggio"].startswith("Sezione non permessa: pokemon")
                  and x["livello"] == "avviso" and x["utente"] == "tizio"
                  for x in _righe(log_hub)))
        r = c.get("/admin/log")
        esito("a un utente normale /admin/log resta chiusa",
              r.status_code == 302 and "/admin/log" not in r.headers.get("Location", ""))

    grezzo = _grezzo(log_hub)
    esito("nessuna password nel log",
          not any(p in grezzo for p in (PW, PW_SBAGLIATA, PW_NUOVO, PW_CAMBIATA)))

    print("\n— avvio")
    import wsgi  # noqa: F401 — l'import è l'avvio
    esito("wsgi.py scrive l'avvio",
          any(x["categoria"] == "avvio" and "WSGI" in x["messaggio"]
              for x in _righe(log_hub)))

    print("\n— rotazione e lettura")
    quante_prima = len(_righe(log_hub))
    vecchio_max = log_hub.MAX_BYTE
    log_hub.MAX_BYTE = 1500
    try:
        for i in range(80):
            log_hub.registra("import", f"riga di rotazione {i:03d}")
    finally:
        log_hub.MAX_BYTE = vecchio_max
    file_log = sorted(os.listdir(log_hub.cartella()))
    esito(f"al più {log_hub.QUANTI_VECCHI + 1} file", len(file_log) == log_hub.QUANTI_VECCHI + 1,
          ", ".join(file_log))
    esito("il corrente non supera di molto il tetto",
          os.path.getsize(log_hub._file()) < 1500 + 200)
    esito("prima di ruotare c'erano righe", quante_prima > 0)
    letto = log_hub.leggi(categoria="import", testo="rotazione", limite=1000)
    numeri = [int(r["messaggio"].rsplit(" ", 1)[1]) for r in letto["righe"]]
    esito("la lettura attraversa i file dal più recente",
          numeri and numeri[0] == 79 and numeri == sorted(numeri, reverse=True)
          and letto["file_letti"] == log_hub.QUANTI_VECCHI + 1,
          f"{len(numeri)} righe, dalla {numeri[0] if numeri else '-'}")
    esito("e il limite dice quante ce n'erano",
          log_hub.leggi(testo="rotazione", limite=5)["trovate"] == len(numeri)
          and len(log_hub.leggi(testo="rotazione", limite=5)["righe"]) == 5)

    with io.open(log_hub._file(), "a", encoding="utf-8") as f:
        f.write('{"quando": "2026-09-26 10:00:00", "messaggio": "tronc\n')
    esito("una riga illeggibile si conta", log_hub.leggi()["illeggibili"] == 1)
    with app.test_client() as c:
        entra(c, "capo")
        html = c.get("/admin/log").get_data(as_text=True)
        esito("e la pagina lo dice", "1 righe del file non si leggono" in html)

    print("\n— quando il log non si può scrivere")
    blocco = os.path.join(dove, "blocco")
    with open(blocco, "w") as f:
        f.write("un file dove dovrebbe esserci una cartella")
    db_vero = extensions.DB
    extensions.DB = os.path.join(blocco, "x.db")     # logs/ dentro un file: impossibile
    errori = io.StringIO()
    try:
        with contextlib.redirect_stderr(errori):
            log_hub.registra("accesso", "non si può scrivere")
        esito("registra() non solleva", True)
    except Exception as e:
        esito("registra() non solleva", False, repr(e))
    finally:
        extensions.DB = db_vero
    esito("e lo dice in console", "log non scritto" in errori.getvalue(),
          errori.getvalue().strip()[:90])

    esito("il logs/ vero non è stato toccato", _impronta_vera() == prima_vera)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true",
                    help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_log_")
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
