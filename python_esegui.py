"""Eseguire del codice Python **sul PC dell'hub**: la metà «server» di «Esegui».

⚠️ Qui gira codice scritto da una persona, col Python e i permessi dell'hub. Può leggere
`hub.db`, la chiave di sessione, qualunque file del disco: **non c'è un modo di impedirlo**
restando Python vero, ed è il motivo per cui lo può fare **solo un amministratore** (la
route controlla) e si spegne con `HUB_ESEGUI_CODICE=0`. Il giorno che l'hub esce di casa
(§1.5) va spento o ripensato: è scritto nel backlog. L'altra metà, nel browser con
Pyodide, non ha questo problema — gira isolata nel browser di chi guarda.

Quello che si fa per limitare i danni **involontari** (un ciclo infinito, un print senza
fine), non quelli voluti:
- una cartella temporanea per ogni esecuzione, cancellata dopo
- **niente variabili d'ambiente dell'hub**: il figlio non eredita `STEAM_API_KEY`,
  `FOOTBALL_DATA_API_KEY`, `SECRET_KEY`, … — solo quelle che servono a Windows per partire
- un tempo massimo, e allo scadere si chiude **tutto l'albero** dei processi: un
  `subprocess` lanciato dal codice sopravviverebbe a un `kill` del solo figlio
- l'output va su file e se ne legge solo l'inizio: un print in un ciclo può fare GB
"""
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

TEMPO_MASSIMO = 30               # secondi; scelta, non misurata
USCITA_MASSIMA = 200_000         # caratteri per flusso; scelta, non misurata
FILE_MASSIMI = 50

# Le sole variabili d'ambiente che passano: senza SYSTEMROOT Python su Windows non parte,
# TEMP/TMP servono a `tempfile`, PATH a trovare le DLL. Tutto il resto resta nell'hub.
AMBIENTE_PASSA = ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "HOME", "USERPROFILE",
                  "LANG", "LC_ALL")


def attivo():
    return os.environ.get("HUB_ESEGUI_CODICE", "1") != "0"


def interprete():
    """Il Python con cui gira il codice: `HUB_PYTHON`, altrimenti quello dell'hub."""
    return os.environ.get("HUB_PYTHON") or sys.executable


def nome_valido(nome):
    """Un nome di file relativo, senza `..` né percorsi assoluti: `pkg/mod.py` sì."""
    if not nome or len(nome) > 200 or nome.startswith(("/", "\\")) or ":" in nome:
        return False
    parti = re.split(r"[\\/]", nome)
    return all(p and p not in (".", "..") and re.fullmatch(r"[\w.\- ]+", p) for p in parti)


def _chiudi_albero(proc):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                           capture_output=True, timeout=10)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def _leggi(percorso):
    with open(percorso, "rb") as f:
        dati = f.read(USCITA_MASSIMA * 4 + 1)
    testo = dati.decode("utf-8", errors="replace").replace("\r\n", "\n")
    troncato = len(testo) > USCITA_MASSIMA or os.path.getsize(percorso) > len(dati)
    return testo[:USCITA_MASSIMA], troncato


def esegui(file, principale=None, stdin="", test=False, tempo=TEMPO_MASSIMO):
    """Esegue `principale` (o i test) con i `file` {nome: contenuto}.

    Torna `{uscita, errori, codice, secondi, scaduto, troncato, comando}`; `errore` se
    non è partito niente (e allora dice perché)."""
    if not attivo():
        return {"errore": "l'esecuzione sul PC è spenta (HUB_ESEGUI_CODICE=0)"}
    if not file:
        return {"errore": "nessun file da eseguire"}
    if len(file) > FILE_MASSIMI:
        return {"errore": f"troppi file ({len(file)}, massimo {FILE_MASSIMI})"}
    cattivi = [n for n in file if not nome_valido(n)]
    if cattivi:
        return {"errore": "nomi di file non validi: " + ", ".join(cattivi[:5])}
    if not test and principale not in file:
        return {"errore": f"il file da eseguire «{principale}» non c'è"}
    cartella = tempfile.mkdtemp(prefix="hub_esegui_")
    try:
        for nome, contenuto in file.items():
            percorso = os.path.join(cartella, *re.split(r"[\\/]", nome))
            os.makedirs(os.path.dirname(percorso), exist_ok=True)
            with open(percorso, "w", encoding="utf-8", newline="") as f:
                f.write(contenuto or "")
        # -E: ignora le PYTHON* dell'ambiente; -s: niente site-packages dell'utente.
        # Non -I: toglierebbe la cartella dello script da sys.path, e un progetto con
        # due file non potrebbe importare l'uno dall'altro.
        base = [interprete(), "-E", "-s", "-X", "utf8"]
        comando = base + (["-m", "unittest", "discover", "-v"] if test else [principale])
        env = {k: os.environ[k] for k in AMBIENTE_PASSA if k in os.environ}
        env["PYTHONIOENCODING"] = "utf-8"
        out_p, err_p = os.path.join(cartella, ".uscita"), os.path.join(cartella, ".errori")
        opzioni = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" \
            else {"start_new_session": True}
        inizio = time.monotonic()
        with open(out_p, "wb") as fo, open(err_p, "wb") as fe:
            proc = subprocess.Popen(comando, cwd=cartella, env=env, stdin=subprocess.PIPE,
                                    stdout=fo, stderr=fe, **opzioni)
            scaduto = False
            try:
                proc.communicate(input=(stdin or "").encode("utf-8"), timeout=tempo)
            except subprocess.TimeoutExpired:
                scaduto = True
                _chiudi_albero(proc)
                proc.wait(timeout=10)
        secondi = round(time.monotonic() - inizio, 2)
        uscita, t1 = _leggi(out_p)
        errori, t2 = _leggi(err_p)
        return {"uscita": uscita, "errori": errori, "codice": proc.returncode,
                "secondi": secondi, "scaduto": scaduto, "troncato": t1 or t2,
                "comando": " ".join(["python"] + comando[5:] if not test else
                                    ["python", "-m", "unittest", "discover", "-v"])}
    except OSError as e:
        return {"errore": f"non sono riuscito a lanciare Python: {e}"}
    finally:
        shutil.rmtree(cartella, ignore_errors=True)
