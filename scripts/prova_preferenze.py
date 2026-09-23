#!/usr/bin/env python
"""Le prove di «tema e lingua seguono l'utente». Non tocca `hub.db`.

    python scripts/prova_preferenze.py [--tieni]

Era la **falla 2 di §1.4**: il tema stava in `localStorage` e la lingua nel cookie
`hub_lang`, tutti e due **per browser**. Quindi cambiando PC — o ripristinando su una
macchina nuova, che è il caso d'uso di `importa_dati.py` — si ripartiva da capo, e
nessun export poteva prenderseli perché non erano nel DB.

⚠️ **Quello che queste prove devono dimostrare non è «si salva»**, è «**segue la
persona**»: un secondo test client è un browser nuovo, senza `localStorage` e senza
cookie, ed è lì che si vede se la colonna serve a qualcosa. Una prova che salva e
rilegge dalla stessa sessione passerebbe anche con la falla intatta.

Cosa dimostra, in ordine:

- che senza sessione l'endpoint **risponde 200 e non scrive niente**: il pulsante del
  tema sta anche sulla pagina di login, e un 401 lì sarebbe un rosso in console per
  un'azione riuscita
- che il tema scelto finisce sulla colonna, e che da un **browser nuovo** la pagina
  nasce già con quel `data-theme` — reso dal server, non applicato dal JS
- che la lingua fa lo stesso, e che al login il **cookie** viene riscritto dal DB:
  `lingua_attiva()` legge quello a ogni pagina, quindi senza questo passo la scelta
  resterebbe scritta e inerte
- che un valore **inventato** non entra: un `data-theme` inesistente lascerebbe la
  pagina col solo `:root`, cioè giusta per caso
- che chi non ha mai scelto non si porta dietro niente, e decide il browser
- che le due colonne **entrano nell'export**, che è la ragione per cui esistono
"""
import argparse
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


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def _colonne(db, uid):
    r = db.execute("SELECT tema, lingua FROM users WHERE id=?", (uid,)).fetchone()
    return (r["tema"], r["lingua"]) if r else (None, None)


def prove(dove):
    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()

    db = extensions.get_db()
    db.execute("INSERT INTO users(username,password,display_name,role) VALUES(?,?,?,?)",
               ("tizio", extensions.hash_password(PW), "Tizio", "user"))
    db.commit()
    uid = db.execute("SELECT id FROM users WHERE username='tizio'").fetchone()["id"]
    esito("le colonne `tema` e `lingua` esistono sullo schema",
          _colonne(db, uid) == (None, None),
          "e nascono NULL: «non ha mai scelto» non e' «ha scelto lo scuro»")
    db.close()

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    def entra(c):
        return c.post("/login", data={"username": "tizio", "password": PW},
                      follow_redirects=True)

    print("\n== 1. senza sessione non scrive, e non protesta ==")
    with app.test_client() as c:
        r = c.post("/preferenze", json={"tema": "sabbia"})
        esito("risponde 200", r.status_code == 200, f"status={r.status_code}")
        esito("e dichiara di non aver salvato niente",
              (r.get_json() or {}).get("salvate") == [])
        db = extensions.get_db()
        esito("la colonna e' ancora vuota", _colonne(db, uid) == (None, None))
        db.close()

    print("\n== 2. da dentro, il tema finisce sulla colonna ==")
    with app.test_client() as c:
        entra(c)
        r = c.post("/preferenze", json={"tema": "sabbia"})
        esito("l'endpoint dice cosa ha salvato",
              (r.get_json() or {}).get("salvate") == ["tema"])
        db = extensions.get_db()
        esito("e la colonna lo ha", _colonne(db, uid)[0] == "sabbia")
        db.close()
        r = c.get("/", follow_redirects=True)
        esito("la pagina di questa sessione nasce gia' sabbia",
              b'data-theme="sabbia"' in r.data)

    print("\n== 3. e SEGUE l'utente su un browser nuovo ==")
    # ⚠️ Il cuore di tutto: client nuovo = niente localStorage, niente cookie. Se la
    # pagina nasce sabbia qui, la colonna sta facendo il suo mestiere.
    with app.test_client() as c2:
        r = entra(c2)
        # ⚠️ Si guarda il **tag `<html>`**, non tutta la pagina: `data-theme="dark"`
        # compare in ogni pagina dentro il CSS dei temi (`:root,[data-theme="dark"]`),
        # quindi cercarlo nel corpo direbbe sempre di sì. Ci sono cascato scrivendo
        # questa prova, ed è lo stesso inciampo dei `t()` citati nei commenti che
        # `controlla_traduzioni.py` contava come stringhe vere.
        import re as _re
        tag = _re.search(rb"<html[^>]*>", r.data)
        tag = tag.group(0) if tag else b""
        esito("appena entrato, la pagina e' gia' sabbia",
              b'data-theme="sabbia"' in tag, tag.decode("utf-8", "replace"))
        esito("   ed e' il **server** ad averlo scritto, non il JS",
              b'data-theme="dark"' not in tag)

    print("\n== 4. la lingua, e il cookie riscritto al login ==")
    with app.test_client() as c:
        entra(c)
        c.post("/preferenze", json={"lingua": "en"})
        db = extensions.get_db()
        esito("la colonna lingua ha 'en'", _colonne(db, uid)[1] == "en")
        db.close()
    with app.test_client() as c3:
        entra(c3)
        # ⚠️ `lingua_attiva()` legge il **cookie**, non il DB: se il login non lo
        # riscrivesse, la scelta resterebbe salvata e inerte — il caso peggiore,
        # perche' il dato c'e' e non fa niente.
        try:
            biscotto = c3.get_cookie(extensions.COOKIE_LINGUA)
            valore = biscotto.value if biscotto else None
        except Exception:
            valore = next((x.value for x in getattr(c3, "cookie_jar", [])
                           if x.name == extensions.COOKIE_LINGUA), None)
        esito("al login il cookie e' stato riscritto dal DB", valore == "en", str(valore))
        r = c3.get("/", follow_redirects=True)
        esito("e la pagina e' in inglese", b'lang="en"' in r.data)

    print("\n== 5. un valore inventato non entra ==")
    with app.test_client() as c:
        entra(c)
        r = c.post("/preferenze", json={"tema": "fucsia", "lingua": "klingon"})
        esito("l'endpoint non salva niente",
              (r.get_json() or {}).get("salvate") == [])
        db = extensions.get_db()
        esito("e le colonne tengono i valori buoni",
              _colonne(db, uid) == ("sabbia", "en"), str(_colonne(db, uid)))
        db.close()

    print("\n== 6. chi non ha mai scelto non si porta dietro niente ==")
    db = extensions.get_db()
    db.execute("INSERT INTO users(username,password,display_name,role) VALUES(?,?,?,?)",
               ("nuovo", extensions.hash_password(PW), "Nuovo", "user"))
    db.commit()
    db.close()
    with app.test_client() as c:
        r = c.post("/login", data={"username": "nuovo", "password": PW},
                   follow_redirects=True)
        import re as _re2
        tag = _re2.search(rb"<html[^>]*>", r.data)
        tag = tag.group(0) if tag else b""
        esito("la pagina nasce col default, e decide il browser",
              b'data-theme="dark"' in tag, tag.decode("utf-8", "replace"))

    print("\n== 7. e adesso l'export se le porta dietro ==")
    # Era il punto di tutta la voce: due personalizzazioni che nessun export poteva
    # prendere, perche' non erano nel DB.
    import scripts.esporta_dati as E  # noqa: F401  (import per il percorso)
    db = extensions.get_db()
    righe = [dict(r) for r in db.execute("SELECT * FROM users")]
    db.close()
    colonne = set(righe[0]) if righe else set()
    esito("`users` ha le due colonne, quindi l'export le legge",
          {"tema", "lingua"} <= colonne, ", ".join(sorted(colonne)))
    tizio = next((r for r in righe if r["username"] == "tizio"), {})
    esito("   e per «tizio» valgono sabbia / en",
          (tizio.get("tema"), tizio.get("lingua")) == ("sabbia", "en"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true",
                    help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_preferenze_")
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
