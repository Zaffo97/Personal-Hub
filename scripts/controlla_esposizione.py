#!/usr/bin/env python
"""La lista di controllo da passare **prima** di far vedere l'hub fuori da qui.

    python scripts/controlla_esposizione.py

Esce con **1** se resta anche una voce aperta, così può stare davanti a un deploy.
Sul modello di `controlla_traduzioni.py` e `controlla_proprietario.py`: risponde con
dei fatti misurati sull'installazione che hai adesso, non con delle raccomandazioni.

⚠️ Cosa **non** dice, e va saputo: che l'app sia pronta per stare online. Restano
aperti i 20 punti che scrivono file su disco mentre l'app gira (§1.5) e il collaudo
del vincolo 1 — salvare, riavviare, ricontrollare — che nessuno script può fare al
posto tuo perché richiede di riavviare il servizio vero.

Le voci, e perché ognuna è qui:

1. **la chiave di sessione** — con una chiave nota chiunque si firma un cookie da
   amministratore, senza sapere nessuna password. È il buco che vale tutti gli altri
2. **la password dell'amministratore** — `admin123` è il seme di `init_db()`, sta nel
   repo, e finché non la cambi è pubblica
3. **il debugger** — `debug=True` su una porta raggiungibile è esecuzione di codice
   da remoto, non un fastidio
4. **le dipendenze** — un `requirements.txt` che mente si scopre sul server, cioè nel
   momento peggiore
5. **il punto d'ingresso WSGI** — il server di sviluppo di Flask non va esposto
6. **cosa git si porta dietro** — il DB, le sue copie e la chiave non devono essere
   versionati: sarebbe pubblicare ciò che i punti 1 e 2 proteggono
"""
import io
import os
import subprocess
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CHIAVE_VECCHIA = "dev-secret-change-me"
voci = []


def voce(nome, ok, dettaglio=""):
    voci.append((nome, ok, dettaglio))


def chiave_di_sessione():
    import extensions
    aperte = []
    sorgente = io.open(os.path.join(RADICE, "app.py"), encoding="utf-8").read()
    # ⚠️ Si cerca l'**assegnazione**, non la parola: la stringa vecchia compare anche
    # nel commento che spiega perché non c'è più, e un controllo che inciampa lì
    # griderebbe per sempre.
    if f'"{CHIAVE_VECCHIA}")' in sorgente or f"'{CHIAVE_VECCHIA}')" in sorgente:
        aperte.append("app.py usa ancora la costante come valore di riserva")
    dall_ambiente = os.environ.get("SECRET_KEY")
    if dall_ambiente == CHIAVE_VECCHIA:
        aperte.append("la variabile d'ambiente SECRET_KEY è la costante pubblica")
    if not dall_ambiente:
        if not os.path.exists(extensions.CHIAVE):
            return (True, "nasce al primo avvio, in data/secret_key.txt")
        salvata = io.open(extensions.CHIAVE, encoding="utf-8").read().strip()
        if len(salvata) < 32:
            aperte.append(f"la chiave in data/secret_key.txt è corta ({len(salvata)})")
        elif salvata == CHIAVE_VECCHIA:
            aperte.append("la chiave salvata è la costante pubblica")
    return (not aperte, "; ".join(aperte) or
            ("dall'ambiente" if dall_ambiente else "da data/secret_key.txt"))


def password_admin():
    import extensions
    if not os.path.exists(extensions.DB):
        return (True, "nessun hub.db qui: il controllo vale sulla macchina che lo ha")
    if extensions.password_di_default():
        return (False, "l'amministratore entra ancora con la password del primo avvio")
    return (True, "cambiata")


def debugger():
    sorgente = io.open(os.path.join(RADICE, "app.py"), encoding="utf-8").read()
    if "debug=True" in sorgente.replace("`debug=True`", ""):
        return (False, "app.py accende il debugger da sé")
    if os.environ.get("HUB_DEBUG") == "1":
        return (False, "HUB_DEBUG=1 nell'ambiente: il debugger si accenderà")
    return (True, "acceso solo con HUB_DEBUG=1")


def dipendenze():
    import importlib.metadata as meta
    mancanti = []
    for pacchetto in ("flask", "requests", "werkzeug"):
        try:
            meta.version(pacchetto)
        except meta.PackageNotFoundError:
            mancanti.append(pacchetto)
    # Il server WSGI dipende dal sistema operativo, come in requirements.txt.
    server = "waitress" if sys.platform == "win32" else "gunicorn"
    try:
        meta.version(server)
        con_server = f"{server} c'è"
    except meta.PackageNotFoundError:
        con_server = f"⚠️ {server} non installato: serve solo per mettere l'app online"
    return (not mancanti,
            f"mancano: {', '.join(mancanti)}" if mancanti else con_server)


def punto_wsgi():
    percorso = os.path.join(RADICE, "wsgi.py")
    if not os.path.exists(percorso):
        return (False, "wsgi.py non c'è")
    # In un processo a parte: importare l'app qui dentro farebbe girare `init_db()`
    # sul DB vero solo per rispondere a una domanda sul filesystem.
    r = subprocess.run([sys.executable, "-c",
                        "import wsgi; assert callable(wsgi.application)"],
                       capture_output=True, text=True, cwd=RADICE)
    return (r.returncode == 0, "wsgi:application si carica" if r.returncode == 0
            else (r.stderr or "").strip().split("\n")[-1])


def cosa_segue_git():
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=RADICE)
    if r.returncode != 0:
        return (True, "non è un repo git: niente da controllare")
    tracciati = set(r.stdout.split("\n"))
    brutti = [f for f in tracciati
              if f.endswith(".db") or f.endswith("secret_key.txt")]
    return (not brutti, "versionati: " + ", ".join(brutti) if brutti
            else "né il DB né la chiave sono versionati")


def main():
    voce("la chiave di sessione", *chiave_di_sessione())
    voce("la password dell'amministratore", *password_admin())
    voce("il debugger di Werkzeug", *debugger())
    voce("le dipendenze dichiarate", *dipendenze())
    voce("il punto d'ingresso WSGI", *punto_wsgi())
    voce("cosa git si porta dietro", *cosa_segue_git())

    larghezza = max(len(n) for n, _, _ in voci)
    for nome, ok, dettaglio in voci:
        print(f"  {'✅' if ok else '⚠️ '} {nome:<{larghezza}}   {dettaglio}")

    aperte = [n for n, ok, _ in voci if not ok]
    print()
    if aperte:
        quante = "1 voce aperta" if len(aperte) == 1 else f"{len(aperte)} voci aperte"
        print(f"⚠️  {quante}: {', '.join(aperte)}.")
        print("    L'app non è pronta a essere raggiunta da fuori.")
        return 1
    print(f"{len(voci)} voci su {len(voci)}: nessuna aperta.")
    print("⚠️  Restano fuori da questo controllo i 20 punti che scrivono file su disco")
    print("    e il collaudo «salva, riavvia, ricontrolla» del vincolo 1 (§1.5).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
