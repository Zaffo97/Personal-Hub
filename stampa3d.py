"""La logica della sezione Stampa 3D: link, file allegati, bobine.

Come per il PC Builder, l'hub **costruisce link e non legge i siti**. Le fonti, lette
il 25/09/2026:

- **MakerWorld** (il sito di modelli di Bambu Lab) vieta nelle condizioni d'uso
  «robot, spider» e ogni strumento automatico per accedere o copiare i contenuti, e
  non ha un'API pubblica: solo link
- **`bambustudio://open?file=`**, il link «apri in Bambu Studio», carica solo file
  che stanno sui domini di Bambu (c'è un elenco dentro lo slicer): un file allegato
  qui si **scarica** e si apre col doppio clic, che è la strada che funziona
- **la stampante in rete** (stato, AMS) si legge solo in «LAN Mode» con la
  «Developer Mode» accesa, dal firmware di inizio 2025: si guarda quando la
  stampante c'è, non prima

⚠️ Ogni indirizzo costruito qui è stato **aperto e guardato** il 25/09/2026 (la
trappola di Versus, §4.7): la ricerca di MakerWorld tiene la query, MakerLab e la
pagina di Bambu Studio si aprono. Printables mostra un controllo di Cloudflare, quindi
di Printables si accetta un link incollato ma non se ne costruisce nessuno.
"""
import hashlib
import os
from urllib.parse import quote, urlparse

CARTELLA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stampa3d")

STATI = ["Idea", "Da stampare", "In stampa", "Stampato", "Fallito"]
MATERIALI = ["PLA", "PETG", "ABS", "ASA", "TPU", "PLA-CF", "PETG-CF", "PA", "PC", "Altro"]

# I due campi link di un progetto, e i siti che ognuno accetta. Un link di un altro
# sito **non passa, e lo si dice**: sotto l'etichetta «Modello» un indirizzo qualunque
# sarebbe un'etichetta falsa, e un `javascript:` sarebbe codice che gira al clic.
LINK = {
    "link_modello": ("Modello", ("makerworld.com", "printables.com", "thingiverse.com",
                                 "thangs.com", "cults3d.com")),
    "link_disegno": ("Disegno", ("tinkercad.com", "onshape.com", "makerworld.com",
                                 "autodesk360.com")),
}

# Dove si comincia un disegno nuovo. Verificati a mano il 25/09/2026.
PARTENZE = [
    ("MakerWorld", "https://makerworld.com/it"),
    ("MakerLab", "https://makerworld.com/it/makerlab"),
    ("Tinkercad", "https://www.tinkercad.com/dashboard"),
    ("Onshape", "https://cad.onshape.com/"),
    ("Bambu Studio", "https://bambulab.com/it/download/studio"),
]

# I formati che Bambu Studio apre. Un file di un altro tipo si rifiuta **dicendolo**.
ESTENSIONI = (".3mf", ".stl", ".step", ".stp", ".obj")
# ⚠️ Una soglia **scelta**, non misurata: un .3mf di MakerWorld con più piatti sta
# di solito sotto qualche decina di MB. Si cambia qui.
MAX_BYTE = 200 * 1024 * 1024
# Sotto questi grammi una bobina è «quasi finita». Scelta, non misurata.
SOGLIA_BOBINA_G = 150


def link_valido(campo, url):
    """Torna l'indirizzo se è http(s) e di un sito ammesso per quel campo, altrimenti None."""
    url = (url or "").strip()
    if not url:
        return None
    try:
        p = urlparse(url)
    except ValueError:
        return None
    host = (p.hostname or "").lower()
    if p.scheme not in ("http", "https"):
        return None
    if not any(host == d or host.endswith("." + d) for d in LINK[campo][1]):
        return None
    return url


def cerca_makerworld(nome):
    """La ricerca di MakerWorld col nome del progetto (formato aperto il 25/09/2026)."""
    nome = (nome or "").strip()
    if not nome:
        return None
    return "https://makerworld.com/it/search/models?keyword=" + quote(nome)


def estensione_ammessa(nome):
    return os.path.splitext(nome or "")[1].lower() in ESTENSIONI


def percorso(impronta):
    """Il file su disco. L'impronta è esadecimale: niente `..`, niente separatori."""
    if not impronta or any(c not in "0123456789abcdef" for c in impronta):
        raise ValueError("impronta non valida")
    return os.path.join(CARTELLA, impronta)


def salva_file(flusso):
    """Scrive il file caricato in `CARTELLA` col nome della sua impronta.

    Torna `(impronta, byte)`, o `(None, byte)` se supera `MAX_BYTE` — in quel caso
    su disco non resta niente. Si legge a pezzi: un file da 200 MB non passa in
    memoria tutto insieme.
    """
    os.makedirs(CARTELLA, exist_ok=True)
    h = hashlib.sha256()
    temporaneo = os.path.join(CARTELLA, f".caricamento-{os.getpid()}-{id(flusso)}")
    byte = 0
    try:
        with open(temporaneo, "wb") as uscita:
            while True:
                pezzo = flusso.read(1024 * 1024)
                if not pezzo:
                    break
                byte += len(pezzo)
                if byte > MAX_BYTE:
                    raise OverflowError
                h.update(pezzo)
                uscita.write(pezzo)
    except OverflowError:
        os.remove(temporaneo)
        return None, byte
    impronta = h.hexdigest()
    finale = percorso(impronta)
    if os.path.exists(finale):
        os.remove(temporaneo)           # lo stesso file c'è già: una copia sola
    else:
        os.replace(temporaneo, finale)
    return impronta, byte


def togli_orfani(db, impronte):
    """Cancella dal disco i file che nessuna riga di `stampa_file` nomina più.

    Si chiama **dopo** aver cancellato le righe, con le impronte che avevano: un
    file che un'altra riga nomina ancora (una copia, lo stesso .3mf in due progetti)
    resta. Torna quanti file ha tolto.
    """
    tolti = 0
    for imp in set(impronte):
        if db.execute("SELECT 1 FROM stampa_file WHERE impronta=?", (imp,)).fetchone():
            continue
        try:
            os.remove(percorso(imp))
            tolti += 1
        except (FileNotFoundError, ValueError):
            pass
    return tolti


def esiste(impronta):
    try:
        return os.path.isfile(percorso(impronta))
    except ValueError:
        return False


def misura(byte):
    """La dimensione leggibile: 1,2 MB, 340 KB."""
    byte = byte or 0
    if byte >= 1024 * 1024:
        return f"{byte / 1024 / 1024:.1f} MB".replace(".", ",")
    if byte >= 1024:
        return f"{byte // 1024} KB"
    return f"{byte} B"


def quasi_finita(bobina):
    rimasto = bobina.get("peso_rimasto")
    return rimasto is not None and rimasto < SOGLIA_BOBINA_G
