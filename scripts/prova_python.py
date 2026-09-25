#!/usr/bin/env python
"""Le prove della sezione Python: esecuzione, file dei progetti, note e frammenti.

    python scripts/prova_python.py [--tieni]

Non tocca `hub.db` e non va in rete (GitHub è sostituito). **Esegue davvero** del codice
sul PC, in cartelle temporanee: è quello che la sezione fa.

Quello che queste prove devono tenere fermo sono i difetti che non darebbero errore:

- una **chiave dell'hub** (variabile d'ambiente) che arriva al codice eseguito
- un ciclo infinito che lascia **processi figli vivi** dopo lo scadere del tempo
- un nome di file con `..` che scrive **fuori** dalla cartella temporanea
- un non amministratore che esegue codice **sul PC** mandando la POST a mano
- lo zip di GitHub con la sua cartella in cima, che diventerebbe un prefisso su ogni file
- un salvataggio con un file dal nome cattivo che ne salva **metà**
- la nota o il progetto di un altro utente
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []
PW = "password-di-prova"
NOME = "Gioco dell'impiccato \"v2\""


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def zip_di(file, radice=""):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for n, c in file.items():
            z.writestr(radice + n, c)
    return b.getvalue()


def prove_esecuzione():
    import python_esegui as E
    print("\n== 1. eseguire sul PC ==")
    os.environ["FOOTBALL_DATA_API_KEY"] = "segreto-di-prova"
    r = E.esegui({"main.py": "import util, os\nprint(util.doppio(21))\nprint(input())\n"
                             "print(os.environ.get('FOOTBALL_DATA_API_KEY'))\n",
                  "util.py": "def doppio(x): return x * 2\n"}, "main.py", stdin="riga letta")
    esito("un file importa l'altro, e input() legge lo stdin",
          r.get("uscita", "").splitlines()[:2] == ["42", "riga letta"], repr(r.get("uscita")))
    esito("la chiave dell'hub NON arriva al codice", r.get("uscita", "").splitlines()[2:3] == ["None"])
    esito("   e il codice di uscita è 0", r.get("codice") == 0)
    r = E.esegui({"a.py": "raise ValueError('boom')\n"}, "a.py")
    esito("un'eccezione: codice 1 e il traceback negli errori",
          r["codice"] == 1 and "ValueError: boom" in r["errori"])
    figlio = ("import subprocess, sys\nsubprocess.Popen([sys.executable, '-c', "
              "'import time; time.sleep(60)  # figlio-prova-hub'])\nwhile True: pass\n")
    r = E.esegui({"loop.py": figlio}, "loop.py", tempo=3)
    esito("un ciclo infinito si ferma al tempo massimo", r["scaduto"] and r["secondi"] < 10, str(r["secondi"]))
    if os.name == "nt":
        vivi = subprocess.run(["powershell", "-NoProfile", "-Command",
                               "(Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
                               "Where-Object { $_.CommandLine -like '*figlio-prova-hub*' }).Count"],
                              capture_output=True, text=True).stdout.strip()
        esito("   e il processo figlio che aveva lanciato non resta vivo", vivi in ("", "0"), f"vivi: {vivi or 0}")
    r = E.esegui({"tanto.py": "while True: print('x' * 1000)\n"}, "tanto.py", tempo=2)
    esito("un output senza fine è tagliato", r["troncato"] and len(r["uscita"]) <= E.USCITA_MASSIMA)
    r = E.esegui({"calc.py": "def f(x): return x * 2\n",
                  "test_calc.py": "import unittest\nfrom calc import f\n"
                                  "class T(unittest.TestCase):\n"
                                  "    def test_giusto(self): self.assertEqual(f(2), 4)\n"
                                  "    def test_sbagliato(self): self.assertEqual(f(2), 5)\n"}, None, test=True)
    esito("i test: uno passa, uno no, e il codice è 1",
          r["codice"] == 1 and "test_giusto" in r["errori"] and "FAILED (failures=1)" in r["errori"])
    fuori = os.path.join(tempfile.gettempdir(), "hub_prova_fuori.py")
    if os.path.exists(fuori):
        os.remove(fuori)
    r = E.esegui({"../hub_prova_fuori.py": "print(1)"}, "../hub_prova_fuori.py")
    esito("un nome con `..` è rifiutato, e fuori non si scrive niente",
          "non validi" in (r.get("errore") or "") and not os.path.exists(fuori))
    os.environ["HUB_ESEGUI_CODICE"] = "0"
    r = E.esegui({"a.py": "print(1)"}, "a.py")
    esito("HUB_ESEGUI_CODICE=0 spegne l'esecuzione, e lo dice", "spenta" in (r.get("errore") or ""))
    del os.environ["HUB_ESEGUI_CODICE"]


def prove_sorgenti():
    import python_sorgenti as S
    print("\n== 2. i file: zip, caricamenti, GitHub ==")
    esito("link GitHub: proprietario e repo", S.github_valido("https://github.com/octocat/Hello-World.git")
          == ("octocat", "Hello-World"))
    esito("   un sito che finge GitHub no", S.github_valido("https://github.com.truffa.it/a/b") is None)
    esito("   `javascript:` no", S.github_valido("javascript:alert(1)") is None)
    z = zip_di({"main.py": "print(1)", "pkg/mod.py": "x = 1", "venv/lib/x.py": "no",
                "__pycache__/a.pyc": "no", "logo.png": "no", "dati.csv": "a,b"}, radice="utente-repo-abc123/")
    file, saltati = S.da_zip(z, togli_radice=True)
    esito("zip di GitHub: la cartella in cima si toglie", sorted(file) == ["dati.csv", "main.py", "pkg/mod.py"],
          str(sorted(file)))
    esito("   venv e __pycache__ si saltano in silenzio, il .png si dice",
          saltati == ["logo.png (tipo non ammesso)"], str(saltati))
    f, s = S.da_zip(zip_di({"a.py": "print(1)", "b.py": "x"}), togli_radice=True)
    esito("uno zip senza cartella in cima non perde il primo livello", sorted(f) == ["a.py", "b.py"])
    f, s = S.da_caricamento("rotto.py", "\xff\xfe".encode("latin-1"))
    esito("un file che non è UTF-8: saltato e detto", not f and "UTF-8" in s[0])
    f, s = S.da_caricamento("C:\\percorso\\script.py", b"print(2)")
    esito("un caricamento tiene solo il nome, non il percorso", f == {"script.py": "print(2)"})
    esito("a_zip e da_zip tornano gli stessi file",
          S.da_zip(S.a_zip({"x.py": "1", "d/y.py": "2"}))[0] == {"x.py": "1", "d/y.py": "2"})
    vero = S.scarica_github
    S.scarica_github = lambda o, r: zip_di({"main.py": f"# {o}/{r}"}, radice=f"{o}-{r}-sha/")
    esito("da_github con lo zip sostituito", S.da_github("https://github.com/tizio/progetto")[0]
          == {"main.py": "# tizio/progetto"})
    def non_esiste(o, r):
        raise LookupError("GitHub risponde 404: il repository non esiste o è privato")
    S.scarica_github = non_esiste
    try:
        S.da_github("https://github.com/tizio/privato"); preso = False
    except LookupError as e:
        preso = "privato" in str(e)
    esito("un 404 dice «non esiste o è privato»", preso)
    S.scarica_github = vero


def prove_web(dove):
    import extensions
    import python_sorgenti as S
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()
    db = extensions.get_db()
    print("\n== 3. schema e regole ==")
    esito("nessuna tabella con un proprietario senza regola", extensions.tabelle_senza_regola(db) == [],
          str(extensions.tabelle_senza_regola(db)))
    esito("nessuna figlia senza regola", extensions.figlie_senza_regola(db) == [],
          str(extensions.figlie_senza_regola(db)))
    for u, ruolo in (("tizio", "user"), ("caio", "user"), ("capo", "admin")):
        db.execute("INSERT INTO users(username,password,display_name,role) VALUES(?,?,?,?)",
                   (u, extensions.hash_password(PW), u.title(), ruolo))
    db.commit()
    uid = {r["username"]: r["id"] for r in db.execute("SELECT id, username FROM users")}
    db.close()

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    def entra(c, chi):
        c.post("/login", data={"username": chi, "password": PW})

    def q(sql, *p):
        d = extensions.get_db()
        r = [dict(x) for x in d.execute(sql, p)]
        d.close()
        return r

    print("\n== 4. un progetto ==")
    with app.test_client() as c:
        entra(c, "tizio")
        r = c.post("/python/progetto/nuovo", data={"nome": NOME})
        pid = q("SELECT id FROM python_progetti")[0]["id"]
        esito("nasce con un main.py", [f["nome"] for f in q("SELECT nome FROM python_file")] == ["main.py"])
        corpo = {"nome": NOME, "stato": "In corso", "principale": "main.py", "descrizione": "",
                 "github_url": "https://github.com/tizio/impiccato", "stdin": "",
                 "file": {"main.py": "from parole import scegli\nprint(scegli())\n",
                          "parole.py": "def scegli(): return 'python'\n"}}
        r = c.post(f"/python/progetto/{pid}/salva", json=corpo)
        esito("salvato, con due file e il link GitHub", r.get_json().get("ok")
              and len(q("SELECT * FROM python_file")) == 2
              and q("SELECT github_url FROM python_progetti")[0]["github_url"].endswith("/impiccato"))
        cattivo = dict(corpo, file=dict(corpo["file"], **{"../fuori.py": "x"}))
        r = c.post(f"/python/progetto/{pid}/salva", json=cattivo)
        esito("un nome cattivo: 400, e niente salvato a metà",
              r.status_code == 400 and len(q("SELECT * FROM python_file")) == 2)
        r = c.post(f"/python/progetto/{pid}/salva", json=dict(corpo, github_url="javascript:alert(1)"))
        esito("un link GitHub cattivo non si salva, e lo dice",
              "GitHub" in " ".join(r.get_json().get("avvisi", []))
              and q("SELECT github_url FROM python_progetti")[0]["github_url"] is None)
        c.post(f"/python/progetto/{pid}/salva", json=corpo)
        r = c.post(f"/python/progetto/{pid}/carica", data={"file": [
            (io.BytesIO(zip_di({"parole.py": "def scegli(): return 'hub'\n", "test_parole.py": "x=1",
                                "foto.jpg": "no"}, radice="cartella/")), "pacco.zip")]},
            content_type="multipart/form-data", follow_redirects=True)
        testo = r.get_data(as_text=True)
        nomi = sorted(f["nome"] for f in q("SELECT nome FROM python_file"))
        esito("uno zip caricato: aggiunge e sostituisce", nomi == ["main.py", "parole.py", "test_parole.py"],
              str(nomi))
        esito("   e dice cosa ha sostituito e cosa ha saltato", "sostituiti: parole.py" in testo and "foto.jpg" in testo)
        vero = S.scarica_github
        S.scarica_github = lambda o, r: zip_di({"README.md": "# ciao", "main.py": "print('da github')\n"},
                                                radice=f"{o}-{r}-sha/")
        c.post(f"/python/progetto/{pid}/github")
        S.scarica_github = vero
        esito("importa da GitHub (sostituito): main.py riscritto, README aggiunto",
              {f["nome"]: f["contenuto"] for f in q("SELECT * FROM python_file")}.get("main.py")
              == "print('da github')\n" and any(f["nome"] == "README.md" for f in q("SELECT nome FROM python_file")))
        r = c.get(f"/python/progetto/{pid}/zip")
        esito("lo zip del progetto contiene tutti i file",
              sorted(zipfile.ZipFile(io.BytesIO(r.data)).namelist()) ==
              sorted(f["nome"] for f in q("SELECT nome FROM python_file")))
        r.close()
        r = c.post("/python/esegui", json={"file": {"a.py": "print(1)"}, "principale": "a.py"})
        esito("un utente normale NON esegue sul PC, anche mandando la POST a mano", r.status_code == 403)

        print("\n== 5. le righe di un altro ==")
        with app.test_client() as altro:
            entra(altro, "caio")
            esito("caio non apre il progetto di tizio",
                  altro.get(f"/python/progetto/{pid}").status_code == 302)
            esito("   non lo scarica", altro.get(f"/python/progetto/{pid}/zip").status_code == 404)
            r = altro.post(f"/python/progetto/{pid}/salva", json=dict(corpo, nome="rubato"))
            esito("   non lo modifica", r.status_code == 404 and q("SELECT nome FROM python_progetti")[0]["nome"] == NOME)
            altro.post(f"/python/progetto/{pid}/carica", data={"file": [(io.BytesIO(b"x=1"), "intruso.py")]},
                       content_type="multipart/form-data")
            esito("   non ci carica file", not q("SELECT 1 FROM python_file WHERE nome='intruso.py'"))
            altro.post(f"/python/progetto/{pid}/elimina")
            esito("   non lo elimina", len(q("SELECT * FROM python_progetti")) == 1)

        print("\n== 6. note e frammenti ==")
        c.post("/python/nota/5", json={"testo": "le f-string", "codice": "print(f'{1+1}')"})
        c.post("/python/nota/5", json={"testo": "le f-string, riscritta", "codice": ""})
        note = q("SELECT * FROM python_note")
        esito("una nota per argomento: il secondo salvataggio aggiorna",
              len(note) == 1 and note[0]["testo"] == "le f-string, riscritta")
        with app.test_client() as altro:
            entra(altro, "caio")
            esito("caio non vede la nota di tizio", "le f-string" not in altro.get("/python/").get_data(as_text=True))
            altro.post("/python/nota/5", json={"testo": "la mia", "codice": ""})
        esito("   e la sua è una riga a parte", len(q("SELECT * FROM python_note")) == 2
              and len(q("SELECT * FROM python_note WHERE user_id=?", uid["tizio"])) == 1)
        c.post("/python/nota/5", json={"testo": "", "codice": "  "})
        esito("una nota svuotata si toglie", not q("SELECT * FROM python_note WHERE user_id=?", uid["tizio"]))
        esito("una nota su un argomento che non esiste: 404",
              c.post("/python/nota/99999", json={"testo": "x"}).status_code == 404)
        c.post("/python/frammento/salva", data={"titolo": "Leggi un CSV", "tag": "CSV, File, csv",
                                                 "codice": "import csv\n"})
        f = q("SELECT * FROM python_frammenti")[0]
        esito("un frammento: i tag minuscoli e senza doppioni", f["tag"] == "csv, file", f["tag"])
        with app.test_client() as altro:
            entra(altro, "caio")
            altro.post(f"/python/frammento/{f['id']}/elimina")
        esito("   caio non lo elimina", len(q("SELECT * FROM python_frammenti")) == 1)

        print("\n== 7. la pagina ==")
        c.post("/python/frammento/salva", data={"titolo": NOME, "tag": "l'apostrofo", "codice": "print('</script>')"})
        c.post("/python/nota/7", json={"testo": NOME, "codice": "print('</script>')"})
        try:
            import esprima
            from sweep_pagine import controlla
            for via in ("/python/", f"/python/progetto/{pid}"):
                errori = controlla(esprima, via, c.get(via).get_data(as_text=True))
                esito(f"{via}: script e handler compilano, con apostrofi e </script> nei dati",
                      errori == 0, f"{errori} errori")
        except ImportError:
            esito("manca esprima: pip install esprima", False)
        pagina = c.get("/python/").get_data(as_text=True)
        esito("il pulsante «Esegui sul PC» non c'è per un utente normale", 'data-esegui="pc"' not in pagina)

    print("\n== 8. l'amministratore ==")
    with app.test_client() as c:
        entra(c, "capo")
        r = c.post("/python/esegui", json={"file": {"a.py": "print(6 * 7)"}, "principale": "a.py"})
        esito("un amministratore esegue sul PC", r.status_code == 200 and r.get_json()["uscita"].strip() == "42")
        esito("   e il pulsante c'è", 'data-esegui="pc"' in c.get("/python/").get_data(as_text=True))
        c.post(f"/admin/utenti/{uid['tizio']}/copia", data={"da": str(uid["caio"])})
    esito("la copia fra utenti porta il progetto con i suoi file",
          len(q("SELECT * FROM python_progetti WHERE user_id=?", uid["caio"])) == 1
          and len(q("SELECT f.* FROM python_file f JOIN python_progetti p ON p.id=f.progetto_id "
                    "WHERE p.user_id=?", uid["caio"])) == len(q("SELECT f.* FROM python_file f JOIN "
                    "python_progetti p ON p.id=f.progetto_id WHERE p.user_id=?", uid["tizio"])))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true", help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_python_")
    try:
        prove_esecuzione()
        prove_sorgenti()
        prove_web(dove)
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
