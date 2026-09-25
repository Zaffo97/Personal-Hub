"""Il catalogo dei componenti e i controlli di compatibilità del PC Builder.

**Fonte: BuildCores OpenDB** (https://github.com/buildcores/buildcores-open-db), licenza
**ODC-By 1.0**: si può copiare, usare e adattare, e chi la usa in pubblico la cita — la
pagina lo fa sotto i controlli. Scelta il 25/09/2026 dopo aver scartato UserBenchmark (ne
vieta ogni uso senza permesso) e PCPartPicker (nessuna API: quella che circola è scraping).

Si scarica lo zip del repository (46 MB il 25/09/2026) **solo quando lo chiede Davide**, col
pulsante «Aggiorna catalogo», e se ne tiene un indice con i soli campi dei controlli in
`data/cache/`, che non è versionata: si rifà dal pulsante.

⚠️ Quanto sono pieni i campi, misurato il 25/09/2026 su tutto il dump: socket, tipo di RAM,
slot, formato, wattaggio e lunghezza GPU fra il 96 e il 100%; il tipo di RAM supportato dalla
CPU all'89%; **l'altezza del dissipatore al 70% e l'altezza massima nel case al 36%**. Un
campo vuoto dà «non noto», mai «compatibile»: è la stessa regola di `moves: null`.

⚠️ E il pezzo va **scelto**, non indovinato dal nome: di «RTX 4070 Ti» ce ne sono 72 modelli,
lunghi da 242 a 356 mm. Il controllo col case vale per il modello collegato.
"""
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime

RADICE = os.path.dirname(os.path.abspath(__file__))
INDICE = os.path.join(RADICE, "data", "cache", "opendb_pezzi.json")
ZIP_URL = "https://codeload.github.com/buildcores/buildcores-open-db/zip/refs/heads/main"
FONTE = "BuildCores OpenDB"
FONTE_URL = "https://github.com/buildcores/buildcores-open-db"
LICENZA = "ODC-By 1.0"
LICENZA_URL = "https://opendatacommons.org/licenses/by/1-0/"

# Categoria di OpenDB → categoria del PC Builder (`data.PC_CATEGORIES`). Le altre categorie
# del PC Builder (Storage, Monitor, …) non entrano in nessun controllo, quindi non si cercano.
CATEGORIE = {"CPU": "CPU", "Motherboard": "Motherboard", "RAM": "RAM", "GPU": "GPU",
             "PCCase": "Case", "PSU": "PSU", "CPUCooler": "CPU Cooler"}

# ⚠️ Scelta di Davide del 25/09/2026, non un dato: l'alimentatore deve dare almeno il 30% in
# più della somma dei TDP di CPU e GPU (il resto del sistema e i picchi).
MARGINE_ALIMENTATORE = 1.30

# Sotto questi numeri lo zip è stato letto male (una cartella rinominata, un formato
# cambiato): meglio rifiutare dicendolo che scrivere un catalogo mezzo vuoto che
# risponderebbe «nessun risultato» a ogni ricerca. Il 25/09/2026 erano 789 CPU, 3701
# schede madri, 4876 RAM, 3862 GPU, 3783 case, 3297 alimentatori, 2405 dissipatori.
MINIMI = {"CPU": 300, "Motherboard": 1000, "RAM": 1000, "GPU": 1000, "Case": 1000,
          "PSU": 1000, "CPU Cooler": 500}


def _prendi(d, percorso):
    for k in percorso.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _pieno(v):
    return None if v in (None, "", [], 0) else v


def _compatta(cat, d):
    """I soli campi che servono ai controlli, con nomi nostri e stabili."""
    c = {"cat": cat, "nome": (_prendi(d, "metadata.name") or "").strip()}
    if cat == "CPU":
        c.update(socket=d.get("socket"), tdp=_prendi(d, "specifications.tdp"),
                 ram=_prendi(d, "specifications.memory.types"))
    elif cat == "Motherboard":
        c.update(socket=d.get("socket"), formato=d.get("form_factor"),
                 ram=_prendi(d, "memory.ram_type"), slot=_prendi(d, "memory.slots"),
                 ram_max=_prendi(d, "memory.max"))
    elif cat == "RAM":
        c.update(ram=d.get("ram_type"), moduli=_prendi(d, "modules.quantity"),
                 capacita=d.get("capacity"))
    elif cat == "GPU":
        c.update(lunghezza=d.get("length"), tdp=d.get("tdp"))
    elif cat == "Case":
        c.update(formati=d.get("supported_motherboard_form_factors"),
                 gpu_max=d.get("max_video_card_length"),
                 dissipatore_max=d.get("max_cpu_cooler_height"))
    elif cat == "PSU":
        c.update(watt=d.get("wattage"))
    elif cat == "CPU Cooler":
        c.update(altezza=d.get("height"), socket=d.get("cpu_sockets"))
    return {k: v for k, v in c.items() if _pieno(v) is not None or k in ("cat", "nome")}


def indice_da_zip(dati_zip):
    """Dallo zip del repository all'indice `{opendb_id: {…}}`. Solleva se i conti non
    tornano, senza scrivere niente."""
    pezzi = {}
    with zipfile.ZipFile(io.BytesIO(dati_zip) if isinstance(dati_zip, bytes) else dati_zip) as z:
        for nome in z.namelist():
            p = nome.split("/")
            # <radice>/open-db/<Categoria>/<uuid>.json
            if len(p) != 4 or p[1] != "open-db" or p[2] not in CATEGORIE or not p[3].endswith(".json"):
                continue
            try:
                d = json.loads(z.read(nome))
            except ValueError:
                continue
            voce = _compatta(CATEGORIE[p[2]], d)
            if voce["nome"]:
                pezzi[d.get("opendb_id") or p[3][:-5]] = voce
    conti = {c: 0 for c in MINIMI}
    for v in pezzi.values():
        conti[v["cat"]] += 1
    corti = {c: n for c, n in conti.items() if n < MINIMI[c]}
    if corti:
        raise ValueError(f"catalogo letto male, troppo pochi pezzi: {corti} (minimi {MINIMI})")
    return pezzi, conti


def scarica():
    """Lo zip, in memoria. A parte perché le prove lo sostituiscono: non vanno in rete."""
    import requests
    r = requests.get(ZIP_URL, timeout=180)
    r.raise_for_status()
    return r.content


def aggiorna():
    """Scarica, indicizza e scrive il catalogo. Torna i conti per categoria."""
    pezzi, conti = indice_da_zip(scarica())
    documento = {"_meta": {"fonte": FONTE, "url": FONTE_URL, "licenza": LICENZA,
                           "aggiornato": datetime.now().strftime("%Y-%m-%d %H:%M"),
                           "conti": conti},
                 "pezzi": pezzi}
    os.makedirs(os.path.dirname(INDICE), exist_ok=True)
    # Scrittura atomica: un salvataggio interrotto non lascia un indice troncato.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(INDICE), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(documento, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, INDICE)
    return conti


_CACHE = {"mtime": None, "doc": None}


def carica():
    """L'indice, seguendo l'mtime del file (trappola «una copia in memoria che non guarda
    più il file»). `None` se non è mai stato scaricato."""
    try:
        mtime = os.path.getmtime(INDICE)
    except OSError:
        _CACHE.update(mtime=None, doc=None)
        return None
    if _CACHE["mtime"] != mtime:
        with open(INDICE, encoding="utf-8") as f:
            _CACHE.update(mtime=mtime, doc=json.load(f))
    return _CACHE["doc"]


def pezzo(opendb_id):
    doc = carica()
    return (doc or {}).get("pezzi", {}).get(opendb_id) if opendb_id else None


def cerca(categoria, q, limite=25):
    """I pezzi di una categoria il cui nome contiene **tutte** le parole cercate."""
    doc = carica()
    parole = [p for p in (q or "").lower().split() if p]
    if not doc or not parole:
        return []
    fuori = []
    for pid, v in doc["pezzi"].items():
        if v["cat"] == categoria and all(p in v["nome"].lower() for p in parole):
            fuori.append({"id": pid, "nome": v["nome"]})
    fuori.sort(key=lambda x: (len(x["nome"]), x["nome"]))
    return fuori[:limite]


def configurazione(componenti):
    """La macchina su cui si fanno i controlli: **quella dopo gli acquisti**.

    Per ogni categoria il pezzo desiderato prende il posto del posseduto; i venduti non ci
    sono. Solo i pezzi collegati al catalogo. Se in una categoria ne restano più d'uno si
    prende il primo e lo si dice (`doppi`)."""
    per_cat, doppi = {}, []
    for stato in ("desiderato", "posseduto", None):
        for c in componenti:
            if c.get("stato") != stato or not c.get("opendb_id"):
                continue
            v = pezzo(c["opendb_id"])
            if not v:
                continue
            if v["cat"] in per_cat:
                if per_cat[v["cat"]]["_stato"] == stato:
                    doppi.append(v["cat"])
                continue
            per_cat[v["cat"]] = {**v, "_stato": stato, "_nome_hub": c.get("name")}
    return per_cat, sorted(set(doppi))


def _esito(nome, esito, dettaglio):
    return {"controllo": nome, "esito": esito, "dettaglio": dettaglio}


def controlli(componenti):
    """Ogni controllo possibile fra i pezzi collegati: `ok`, `no`, `non_noto` (manca un
    dato) o `verifica` (i dati dicono sì, ma non bastano a dirlo). Più la percentuale sui
    soli controlli **verificabili** — un non noto non è né un sì né un no."""
    p, doppi = configurazione(componenti)
    cpu, mb, ram, gpu = p.get("CPU"), p.get("Motherboard"), p.get("RAM"), p.get("GPU")
    case, psu, dis = p.get("Case"), p.get("PSU"), p.get("CPU Cooler")
    fuori = []

    if cpu and mb:
        a, b = cpu.get("socket"), mb.get("socket")
        if not a or not b:
            fuori.append(_esito("Socket CPU / scheda madre", "non_noto", "socket non indicato"))
        elif a != b:
            fuori.append(_esito("Socket CPU / scheda madre", "no", f"{a} contro {b}"))
        elif a == "LGA 1151":
            # Due generazioni incompatibili sullo stesso socket (chipset serie 100/200 e 300):
            # il socket da solo direbbe sì anche quando è no.
            fuori.append(_esito("Socket CPU / scheda madre", "verifica",
                                "LGA 1151 è usato da due generazioni Intel incompatibili fra loro: "
                                "controlla il chipset sul sito del produttore"))
        else:
            nota = " (su AM4 una CPU recente può chiedere un BIOS aggiornato)" if a == "AM4" else ""
            fuori.append(_esito("Socket CPU / scheda madre", "ok", a + nota))

    if ram and mb:
        a, b = ram.get("ram"), mb.get("ram")
        if not a or not b:
            fuori.append(_esito("Tipo di RAM / scheda madre", "non_noto", "tipo non indicato"))
        else:
            fuori.append(_esito("Tipo di RAM / scheda madre", "ok" if a == b else "no", f"{a} su {b}"))
        a, b = ram.get("moduli"), mb.get("slot")
        if a and b:
            fuori.append(_esito("Moduli di RAM / slot", "ok" if a <= b else "no",
                                f"{a} moduli, {b} slot"))
        else:
            fuori.append(_esito("Moduli di RAM / slot", "non_noto", "dato mancante"))
        a, b = ram.get("capacita"), mb.get("ram_max")
        if a and b:
            fuori.append(_esito("Capacità RAM / massimo della scheda", "ok" if a <= b else "no",
                                f"{a} GB su {b} GB"))
        else:
            fuori.append(_esito("Capacità RAM / massimo della scheda", "non_noto", "dato mancante"))
    if ram and cpu:
        tipi = cpu.get("ram") or []
        if ram.get("ram") and tipi:
            fuori.append(_esito("Tipo di RAM / CPU", "ok" if ram["ram"] in tipi else "no",
                                f"{ram['ram']}, la CPU supporta {', '.join(tipi)}"))
        else:
            fuori.append(_esito("Tipo di RAM / CPU", "non_noto", "dato mancante"))

    if mb and case:
        a, b = mb.get("formato"), case.get("formati") or []
        # Thin Mini-ITX ha le misure della Mini-ITX (170×170 mm), ma nessun case del
        # catalogo la nomina: senza questo, una scheda che entra risulterebbe «no».
        if a == "Thin Mini-ITX" and "Mini-ITX" in b:
            a = "Mini-ITX"
        if a and b:
            fuori.append(_esito("Formato scheda madre / case", "ok" if a in b else "no",
                                f"{a}, il case accetta {', '.join(b)}"))
        else:
            fuori.append(_esito("Formato scheda madre / case", "non_noto", "dato mancante"))
    if gpu and case:
        a, b = gpu.get("lunghezza"), case.get("gpu_max")
        if a and b:
            fuori.append(_esito("Lunghezza GPU / case", "ok" if a <= b else "no", f"{a:g} mm su {b:g} mm"))
        else:
            fuori.append(_esito("Lunghezza GPU / case", "non_noto", "dato mancante"))
    if dis and cpu:
        a, b = cpu.get("socket"), dis.get("socket") or []
        if a and b:
            fuori.append(_esito("Dissipatore / socket CPU", "ok" if a in b else "no",
                                f"{a}{'' if a in b else ', il dissipatore non lo supporta'}"))
        else:
            fuori.append(_esito("Dissipatore / socket CPU", "non_noto", "dato mancante"))
    if dis and case:
        a, b = dis.get("altezza"), case.get("dissipatore_max")
        if a and b:
            fuori.append(_esito("Altezza dissipatore / case", "ok" if a <= b else "no", f"{a:g} mm su {b:g} mm"))
        else:
            fuori.append(_esito("Altezza dissipatore / case", "non_noto",
                                "dato mancante (nel catalogo l'altezza massima c'è solo per 1 case su 3)"))
    if psu and (cpu or gpu):
        tdp = [x.get("tdp") for x in (cpu, gpu) if x]
        if psu.get("watt") and all(tdp):
            serve = sum(tdp) * MARGINE_ALIMENTATORE
            fuori.append(_esito("Alimentatore / consumi", "ok" if psu["watt"] >= serve else "no",
                                f"{psu['watt']} W, servono almeno {serve:.0f} W "
                                f"(TDP {' + '.join(str(t) for t in tdp)} W, +30%)"))
        else:
            fuori.append(_esito("Alimentatore / consumi", "non_noto", "dato mancante"))

    verificabili = [e for e in fuori if e["esito"] in ("ok", "no")]
    ok = sum(1 for e in verificabili if e["esito"] == "ok")
    return {"controlli": fuori, "ok": ok, "verificabili": len(verificabili),
            "percentuale": round(100 * ok / len(verificabili)) if verificabili else None,
            "non_noti": sum(1 for e in fuori if e["esito"] == "non_noto"),
            "da_verificare": sum(1 for e in fuori if e["esito"] == "verifica"),
            "doppi": doppi, "collegati": len(p)}
