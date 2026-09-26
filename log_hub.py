"""Il log dell'hub: avvii, accessi, azioni sugli utenti, import, errori (§4, 26/09/2026).

Chiesto da Davide come «una funzione di salvataggio log»; il 26/09/2026 ha chiarito che
intende il **registro di quello che fa l'app**, non un diario e non la console su file.
Si legge da `/admin/log`, solo per gli amministratori.

Una riga per evento, in JSON (`{"quando", "livello", "categoria", "messaggio", "utente",
"ip", "dati"}`), in `logs/hub.log`. Le scelte, e perché:

⚠️ **Su file, non in una tabella di `hub.db`.** Il caso che un log deve reggere meglio è
l'errore, e l'errore più probabile qui è una richiesta morta a metà di una scrittura:
la sua connessione tiene il lucchetto di SQLite finché l'eccezione non viene raccolta,
quindi scrivere l'errore **nello stesso DB** aspetterebbe 5 secondi e poi fallirebbe
proprio sull'evento che serviva. E il log non è un dato da salvare: non entra nell'export
e non ha bisogno di un proprietario.

⚠️ **La cartella segue il DB** (`logs/` accanto a `extensions.DB`, letto a ogni
scrittura, non all'import). Le prove e lo sweep girano su un DB temporaneo spostando
proprio `extensions.DB`: così i loro login finti, gli errori provocati di proposito e
gli avvii finiscono nella loro cartella temporanea e non in quella vera — lo stesso
isolamento che la trappola «la suite di prove va isolata» ha chiesto al Fantacalcio,
ottenuto senza che ogni prova se ne debba ricordare.

⚠️ **Scrivere il log non deve mai rompere la richiesta**, ma non deve nemmeno tacere: se
la scrittura fallisce lo si dice in console (`stderr`) e la pagina va avanti. Un log che
solleva farebbe diventare un 500 un login riuscito.

**Cosa non ci finisce mai**: password (in chiaro o hash), token del «resta collegato»,
chiavi delle API. Chi aggiunge un evento passa in `dati` numeri e nomi, non il form.

La dimensione è tenuta a bada ruotando: a `MAX_BYTE` il file diventa `hub.1.log`, il
vecchio `hub.1.log` diventa `hub.2.log`, e così fino a `QUANTI_VECCHI`; il più vecchio
si butta. Cioè al massimo 5 MB, e nessuna pulizia da ricordarsi.
"""
import io
import json
import os
import sys
import threading
import time
import traceback

CATEGORIE = {
    "avvio": "Avvii",
    "accesso": "Accessi",
    "utenti": "Utenti",
    "import": "Import",
    "errore": "Errori",
}
LIVELLI = ("info", "avviso", "errore")
MAX_BYTE = 1_000_000
QUANTI_VECCHI = 4
NOME = "hub.log"

# Un lucchetto per processo: il server di sviluppo e waitress servono le richieste su
# più thread, e due righe scritte insieme si mescolerebbero. Fra **processi** diversi
# non c'è niente, ed è la stessa regola di `wsgi.py`: un worker solo.
_LUCCHETTO = threading.Lock()


def cartella():
    """`logs/` accanto al DB in uso. Letta ogni volta: vedi il docstring del modulo."""
    import extensions
    return os.path.join(os.path.dirname(os.path.abspath(extensions.DB)), "logs")


def _file(n=0):
    return os.path.join(cartella(), NOME if n == 0 else f"hub.{n}.log")


def _ruota():
    """hub.log → hub.1.log → … → hub.<QUANTI_VECCHI>.log, e il più vecchio via."""
    ultimo = _file(QUANTI_VECCHI)
    if os.path.exists(ultimo):
        os.remove(ultimo)
    for n in range(QUANTI_VECCHI - 1, -1, -1):
        if os.path.exists(_file(n)):
            os.replace(_file(n), _file(n + 1))


def _chi_e_da_dove():
    """Utente e indirizzo della richiesta in corso, se ce n'è una.

    ⚠️ L'indirizzo è `remote_addr`: in casa è il PC o il telefono che apre l'hub.
    Dietro un proxy (§1.5, l'app online) diventerebbe **l'indirizzo del proxy** per
    tutti, e andrà letto da `X-Forwarded-For` con `ProxyFix` — non prima, perché
    fidarsi di quell'intestazione senza un proxy vuol dire credere a chi la scrive.
    """
    try:
        from flask import has_request_context, request, session
        if not has_request_context():
            return None, None
        return session.get("username"), request.remote_addr
    except Exception:
        return None, None


def registra(categoria, messaggio, livello="info", **dati):
    """Scrive un evento. Non solleva mai: se non riesce, lo dice in console."""
    try:
        utente, ip = _chi_e_da_dove()
        riga = {"quando": time.strftime("%Y-%m-%d %H:%M:%S"),
                "livello": livello if livello in LIVELLI else "info",
                "categoria": categoria, "messaggio": str(messaggio),
                "utente": utente, "ip": ip}
        if dati:
            riga["dati"] = dati
        testo = json.dumps(riga, ensure_ascii=False, default=str) + "\n"
        with _LUCCHETTO:
            os.makedirs(cartella(), exist_ok=True)
            if os.path.exists(_file()) and os.path.getsize(_file()) >= MAX_BYTE:
                _ruota()
            with io.open(_file(), "a", encoding="utf-8") as f:
                f.write(testo)
    except Exception as e:
        print(f"⚠️  log non scritto ({type(e).__name__}: {e}): "
              f"[{categoria}] {messaggio}", file=sys.stderr)


def registra_eccezione(sender, exception, **_):
    """Per il segnale `got_request_exception` di Flask: ogni 500, con il traceback.

    È un segnale e non un `errorhandler` di proposito: un gestore cambierebbe la
    risposta (e con `debug` acceso nasconderebbe la pagina del debugger), il segnale
    si limita a guardare.
    """
    from flask import request
    registra("errore", f"{request.method} {request.path} — "
                       f"{type(exception).__name__}: {exception}",
             livello="errore",
             traceback="".join(traceback.format_exception(
                 type(exception), exception, exception.__traceback__)))


def leggi(categoria=None, livello=None, testo=None, limite=500):
    """Gli eventi dal più recente, filtrati.

    Torna `{"righe", "trovate", "illeggibili", "file_letti"}`: `trovate` sono tutte
    quelle che passano i filtri, `righe` le prime `limite` — così la pagina può dire
    «500 su 1834» invece di far credere che siano tutte.

    ⚠️ Una riga che non si legge **si conta**, non si salta in silenzio: un file
    troncato (un arresto a metà scrittura) o toccato a mano deve vedersi nella pagina,
    non sembrare un log più corto.

    La ricerca guarda i **valori** (messaggio, utente, indirizzo, dati), non la riga
    grezza: sulla riga grezza «info» troverebbe ogni evento, per via di `"livello"`.
    """
    cerca = (testo or "").strip().lower()
    righe, trovate, illeggibili, letti = [], 0, 0, 0
    for n in range(QUANTI_VECCHI + 1):
        percorso = _file(n)
        if not os.path.exists(percorso):
            continue
        letti += 1
        with io.open(percorso, encoding="utf-8", errors="replace") as f:
            contenuto = f.read().splitlines()
        for grezza in reversed(contenuto):
            if not grezza.strip():
                continue
            try:
                r = json.loads(grezza)
                if not isinstance(r, dict):
                    raise ValueError
            except ValueError:
                illeggibili += 1
                continue
            if categoria and r.get("categoria") != categoria:
                continue
            if livello and r.get("livello") != livello:
                continue
            if cerca:
                valori = " ".join([str(r.get("messaggio") or ""),
                                   str(r.get("utente") or ""), str(r.get("ip") or ""),
                                   json.dumps(r.get("dati") or {}, ensure_ascii=False)])
                if cerca not in valori.lower():
                    continue
            trovate += 1
            if len(righe) < limite:
                righe.append(r)
    return {"righe": righe, "trovate": trovate, "illeggibili": illeggibili,
            "file_letti": letti}
