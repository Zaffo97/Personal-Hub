#!/usr/bin/env python
"""Le prove di `scripts/esporta_dati.py --completo`. Non tocca `hub.db` né l'export vero.

    python scripts/prova_esporta_completo.py [--tieni]

Ogni prova gira su un DB **suo**, creato da `init_db()` in una cartella temporanea, e
scrive solo lì dentro. ⚠️ Non è pignoleria: il 16/08/2026 uno script di prova che
cancellava «il mio intervallo» di id si è portato via 497 righe vere.

Cosa dimostra, in ordine:

- la **rete che tiene in piedi la distinzione fra i due export**: `--completo` senza
  `--uscita` non scrive, e con una destinazione **dentro un repo git** non scrive. È la
  prova più importante di tutte: quel file contiene gli hash delle password, ed è la
  stessa ragione per cui `hub.db` non è versionato. La ricerca del `.git` **risale
  l'albero**, quindi non basta scegliere una sottocartella qualsiasi
- che i **due file siano davvero diversi**: il completo ha le password e `regulations`,
  quello committabile non ha né l'una né l'altra cosa
- il **giro vero**: export completo da un DB, import in un DB nuovo, e l'utente rientra
  **con la sua password**, cioè proprio la cosa che l'export committabile non sa fare
- che una password **già nel DB** non venga sovrascritta nemmeno da un backup completo
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESPORTA = os.path.join(RADICE, "scripts", "esporta_dati.py")
IMPORTA = os.path.join(RADICE, "scripts", "importa_dati.py")
EXPORT_VERO = os.path.join(RADICE, "data", "backup", "hub_export.json")
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []


def esito(nome, ok, dettaglio=""):
    esiti.append((nome, ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def esporta(*extra):
    r = subprocess.run([sys.executable, ESPORTA, *extra], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=RADICE)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def importa(*extra):
    r = subprocess.run([sys.executable, IMPORTA, *extra], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=RADICE)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def db_vergine(dove, nome):
    """Un DB come lo crea `init_db()` su un PC nuovo: schema, `admin`, i 53 argomenti."""
    import extensions
    percorso = os.path.join(dove, nome)
    vecchio, extensions.DB = extensions.DB, percorso
    try:
        extensions.init_db()
    finally:
        extensions.DB = vecchio
    return percorso


def valore(db, query):
    c = sqlite3.connect(db)
    try:
        r = c.execute(query).fetchone()
        return r[0] if r else None
    finally:
        c.close()


def prove(dove):
    sorgente = db_vergine(dove, "sorgente.db")
    c = sqlite3.connect(sorgente)
    from extensions import hash_password
    c.execute("INSERT INTO users(username, password, display_name, role) VALUES(?,?,?,?)",
              ("davide", hash_password("segreto-di-prova"), "Davide", "user"))
    c.commit()
    c.close()

    print("\n== 1. la rete: dove NON deve scrivere ==")
    dentro_repo = os.path.join(RADICE, "data", "backup", "prova_completo.json")
    rc, out = esporta("--completo", "--db", sorgente)
    esito("--completo senza --uscita si ferma", rc == 1 and "pretende --uscita" in out)
    rc, out = esporta("--completo", "--db", sorgente, "--uscita", dentro_repo)
    esito("una destinazione dentro il repo si ferma",
          rc == 1 and "repository git" in out)
    esito("e non ha lasciato il file", not os.path.exists(dentro_repo))
    # ⚠️ La ricerca risale: una sottocartella profonda del repo deve essere rifiutata
    # lo stesso, altrimenti la rete si aggira scegliendo `data/archive/qualcosa/`.
    profondo = os.path.join(RADICE, "data", "archive", "giu", "ancora", "x.json")
    rc, out = esporta("--completo", "--db", sorgente, "--uscita", profondo)
    esito("anche una sottocartella profonda del repo", rc == 1 and "repository git" in out)
    rc, out = esporta("--uscita", os.path.join(dove, "x.json"), "--db", sorgente)
    esito("--uscita senza --completo si ferma", rc == 1 and "vale solo con --completo" in out)

    print("\n== 2. i due export sono diversi, e nel verso giusto ==")
    completo = os.path.join(dove, "hub_completo.json")
    rc, out = esporta("--completo", "--db", sorgente, "--uscita", completo)
    esito("fuori dal repo scrive", rc == 0 and os.path.exists(completo), out.strip()[-60:])
    doc = json.load(open(completo, encoding="utf-8"))
    esito("il completo ha la password di ogni utente",
          all("password" in u and len(str(u["password"])) > 20 for u in doc["users"]),
          f"{len(doc['users'])} utenti")
    esito("il completo ha la tabella `regulations`", "regulations" in doc,
          f"{len(doc.get('regulations', []))} righe")
    esito("e un `_meta` che dice quando e da dove",
          doc.get("_meta", {}).get("password_incluse") is True
          and "generato" in doc.get("_meta", {}))
    esito("`game_releases` resta fuori anche dal completo", "game_releases" not in doc)
    committabile = json.load(open(EXPORT_VERO, encoding="utf-8"))
    esito("l'export committabile NON ha password né `regulations`",
          not any("password" in u for u in committabile["users"])
          and "regulations" not in committabile)

    print("\n== 3. il giro vero: si rimette dentro, password comprese ==")
    nuovo = db_vergine(dove, "nuovo.db")
    prima = valore(nuovo, "SELECT password FROM users WHERE username='admin'")
    # ⚠️ Forzato, non lasciato al caso: `regulations.created_at` lo scrive `init_db()`
    # al momento, quindi i due DB lo hanno uguale **solo se** sono nati nello stesso
    # secondo. Con la data diversa il ripristino si fermava su un conflitto — su una
    # tabella morta — e l'unica uscita era `--sovrascrivi`. Qui la differenza si crea
    # apposta, così la prova misura la regola e non l'orologio.
    c = sqlite3.connect(nuovo)
    c.execute("UPDATE regulations SET created_at='2001-01-01 00:00:00'")
    c.commit()
    c.close()
    rc, out = importa("--db", nuovo, "--file", completo)
    esito("l'import legge il backup completo", rc == 0, out.strip().splitlines()[-1][:70])
    esito("l'utente nuovo è rientrato",
          valore(nuovo, "SELECT COUNT(*) FROM users WHERE username='davide'") == 1)
    esito("e con la SUA password, non una casuale",
          valore(nuovo, "SELECT password FROM users WHERE username='davide'")
          == valore(sorgente, "SELECT password FROM users WHERE username='davide'"))
    esito("lo dice a schermo, e non dice il contrario",
          "con la loro password" in out and "senza password" not in out)
    esito("la password di `admin`, già nel DB, non è stata toccata",
          valore(nuovo, "SELECT password FROM users WHERE username='admin'") == prima)
    esito("e `regulations` è rientrata",
          valore(nuovo, "SELECT COUNT(*) FROM regulations") >= 1)
    # `rc == 0` dice che non si è fermato; la data ancora al 2001 dice che non l'ha
    # nemmeno riscritta. «conflitto» nel testo non si può cercare: è anche il titolo
    # di una colonna della tabella che lo script stampa sempre.
    esito("un `created_at` diverso su `regulations` non ferma il ripristino",
          rc == 0 and "INTERROTTO" not in out
          and valore(nuovo, "SELECT created_at FROM regulations LIMIT 1")
          == "2001-01-01 00:00:00",
          valore(nuovo, "SELECT created_at FROM regulations LIMIT 1"))

    print("\n== 4. e rieseguirlo non cambia niente ==")
    rc, out = importa("--db", nuovo, "--file", completo)
    esito("il secondo import non scrive", rc == 0 and "Niente da fare" in out,
          out.strip().splitlines()[-1][:70])

    print("\n== 5. niente di vero è stato toccato ==")
    esito("l'export committabile vero è intatto",
          not any("password" in u for u in
                  json.load(open(EXPORT_VERO, encoding="utf-8"))["users"]))
    esito("hub.db vero non è stato scritto da nessuna prova",
          os.path.exists(os.path.join(RADICE, "hub.db")))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true",
                    help="non cancella la cartella temporanea, per guardarci dentro")
    args = ap.parse_args()

    dove = tempfile.mkdtemp(prefix="prova_esporta_")
    try:
        prove(dove)
    finally:
        if args.tieni:
            print(f"\ncartella tenuta: {dove}")
        else:
            shutil.rmtree(dove, ignore_errors=True)

    passate = sum(1 for _, ok in esiti if ok)
    print(f"\n{passate} prove su {len(esiti)}." +
          ("  Tutte passate." if passate == len(esiti) else "  FALLITE."))
    return 0 if passate == len(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
