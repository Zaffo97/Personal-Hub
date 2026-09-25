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

⚠️ Nei connettori **uno zero non è un dato**, misurato sullo stesso dump: 855 alimentatori su
3297 hanno zero connettori PCIe, e 275 di loro sono da 750 W in su; 1005 GPU su 3862 non ne
hanno nessuno, e 697 di queste consumano più dei 75 W dello slot. Tutto zero dà «non noto».
"""
import io
import json
import os
import re
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
# `Storage` di OpenDB ha SSD e dischi insieme: va sotto «Storage SSD» perché l'unico controllo
# che lo usa è quello degli slot M.2, e un disco M.2 è sempre un SSD. Un HDD collegato lì non
# entra in nessun controllo.
CATEGORIE = {"CPU": "CPU", "Motherboard": "Motherboard", "RAM": "RAM", "GPU": "GPU",
             "PCCase": "Case", "PSU": "PSU", "CPUCooler": "CPU Cooler", "Storage": "Storage SSD"}

# Le categorie in cui si hanno **più pezzi insieme**, e come si sommano (scelta di Davide del
# 25/09/2026): gli SSD si aggiungono agli altri, desiderati e posseduti; i kit di RAM si
# sommano fra quelli dello stesso stato, e il desiderato prende il posto del posseduto come
# nelle altre categorie. Nelle categorie non elencate si controlla il primo e lo si dice.
SOMMATI = {"Storage SSD": "si_aggiunge", "RAM": "sostituisce"}

# ⚠️ Scelta di Davide del 25/09/2026, non un dato: l'alimentatore deve dare almeno il 30% in
# più della somma dei TDP di CPU e GPU (il resto del sistema e i picchi).
MARGINE_ALIMENTATORE = 1.30

# Sotto questi numeri lo zip è stato letto male (una cartella rinominata, un formato
# cambiato): meglio rifiutare dicendolo che scrivere un catalogo mezzo vuoto che
# risponderebbe «nessun risultato» a ogni ricerca. Il 25/09/2026 erano 789 CPU, 3701
# schede madri, 4876 RAM, 3862 GPU, 3783 case, 3297 alimentatori, 2405 dissipatori, 3495
# unità di memoria.
MINIMI = {"CPU": 300, "Motherboard": 1000, "RAM": 1000, "GPU": 1000, "Case": 1000,
          "PSU": 1000, "CPU Cooler": 500, "Storage SSD": 1000}


def _prendi(d, percorso):
    for k in percorso.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _pieno(v):
    return None if v in (None, "", [], 0) else v


def _intero(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else 0


def _anno(d):
    """L'anno di uscita, se c'è e ha senso: nel dump ci sono anche «20117» e «20225»."""
    a = _prendi(d, "metadata.releaseYear")
    return a if isinstance(a, int) and 1990 <= a <= 2100 else None


def _asin(d):
    """L'ASIN di amazon.it, per il link ad Amazon e a Keepa senza incollare niente.

    ⚠️ Nel dump ogni pezzo che ha un ASIN lo ha **su tutti i 15 canali Amazon** (12 118 per
    ognuno, tutti `verified`): sembra copiato per paese, non controllato. Aperti a mano su
    amazon.it il 25/09/2026 nove presi a caso da sei categorie, più la 4070 Ti di Davide:
    **dieci su dieci** il prodotto giusto. Per questo si usa, ma il link dice da dove viene."""
    for r in _prendi(d, "identifiers.retailer_listings") or []:
        if isinstance(r, dict) and r.get("source") == "amazon" and r.get("channel") == "it" \
                and re.fullmatch(r"[A-Z0-9]{10}", r.get("source_product_id") or ""):
            return r["source_product_id"]
    return None


def _compatta(cat, d):
    """I soli campi che servono ai controlli, con nomi nostri e stabili."""
    c = {"cat": cat, "nome": (_prendi(d, "metadata.name") or "").strip(), "anno": _anno(d),
         "asin": _asin(d)}
    if cat == "CPU":
        c.update(socket=d.get("socket"), tdp=_prendi(d, "specifications.tdp"),
                 ram=_prendi(d, "specifications.memory.types"))
    elif cat == "Motherboard":
        # Solo gli slot con chiave M (o senza chiave): quelli con chiave E sono per il Wi-Fi,
        # 602 nel dump, e contati come slot per SSD darebbero un posto che non c'è.
        m2 = [{"misura": s.get("size"), "iface": s.get("interface")}
              for s in (d.get("m2_slots") or []) if isinstance(s, dict) and s.get("key") in ("M", None)]
        c.update(socket=d.get("socket"), formato=d.get("form_factor"),
                 ram=_prendi(d, "memory.ram_type"), slot=_prendi(d, "memory.slots"),
                 ram_max=_prendi(d, "memory.max"), m2=m2)
    elif cat == "RAM":
        c.update(ram=d.get("ram_type"), moduli=_prendi(d, "modules.quantity"),
                 capacita=d.get("capacity"))
    elif cat == "GPU":
        pc = d.get("power_connectors")
        # 12V-2x6 è la revisione del 12VHPWR, con la stessa spina: si contano insieme.
        conn = {"6": _intero(pc.get("pcie_6_pin")), "8": _intero(pc.get("pcie_8_pin")),
                "12": _intero(pc.get("pcie_12VHPWR")) + _intero(pc.get("pcie_12V_2x6"))} \
            if isinstance(pc, dict) else None
        c.update(lunghezza=d.get("length"), tdp=d.get("tdp"), connettori=conn)
    elif cat == "Case":
        c.update(formati=d.get("supported_motherboard_form_factors"),
                 gpu_max=d.get("max_video_card_length"),
                 dissipatore_max=d.get("max_cpu_cooler_height"))
    elif cat == "PSU":
        pc = d.get("connectors")
        conn = {"62": _intero(pc.get("pcie_6_plus_2_pin")), "12": _intero(pc.get("pcie_12vhpwr"))} \
            if isinstance(pc, dict) else None
        c.update(watt=d.get("wattage"), connettori=conn)
    elif cat == "CPU Cooler":
        c.update(altezza=d.get("height"), socket=d.get("cpu_sockets"))
    elif cat == "Storage SSD":
        c.update(formato=d.get("form_factor"), iface=d.get("interface"))
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


def differenze(vecchio, pezzi):
    """Cosa è entrato e cosa è uscito rispetto all'indice di prima.

    Solo nelle categorie che l'indice di prima **aveva già**: quando se ne aggiunge una (gli
    SSD, il 25/09/2026) i suoi 3495 pezzi non sono «usciti oggi», c'erano anche prima e
    l'hub non li guardava. Un pezzo uscito si tiene col nome, perché nell'indice nuovo non
    c'è più; uno entrato basta l'id."""
    if not vecchio:
        return None
    prima = vecchio.get("pezzi", {})
    categorie = set((vecchio.get("_meta") or {}).get("conti", {}))
    return {"da": (vecchio.get("_meta") or {}).get("aggiornato"),
            "nuovi": sorted(pid for pid, v in pezzi.items()
                            if v["cat"] in categorie and pid not in prima),
            "tolti": {pid: {"cat": v["cat"], "nome": v["nome"]} for pid, v in prima.items()
                      if pid not in pezzi}}


def aggiorna():
    """Scarica, indicizza e scrive il catalogo. Torna i conti per categoria."""
    pezzi, conti = indice_da_zip(scarica())
    documento = {"_meta": {"fonte": FONTE, "url": FONTE_URL, "licenza": LICENZA,
                           "aggiornato": datetime.now().strftime("%Y-%m-%d %H:%M"),
                           "conti": conti,
                           # ⚠️ Rispetto all'aggiornamento **precedente**: due pressioni di
                           # fila e la seconda dice «niente di nuovo».
                           "differenze": differenze(carica(), pezzi)},
                 "pezzi": pezzi}
    os.makedirs(os.path.dirname(INDICE), exist_ok=True)
    # Scrittura atomica: un salvataggio interrotto non lascia un indice troncato.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(INDICE), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(documento, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, INDICE)
    _CACHE.update(mtime=_firma(), doc=documento)
    return conti


_CACHE = {"mtime": None, "doc": None}


def _firma():
    """mtime **e** dimensione: su Windows due scritture a pochi millisecondi di distanza
    possono avere lo stesso mtime (l'orologio dei file va a scatti), e con la sola data la
    cache restituiva l'indice di prima."""
    st = os.stat(INDICE)
    return (st.st_mtime_ns, st.st_size)


def carica():
    """L'indice, seguendo mtime e dimensione del file (trappola «una copia in memoria che
    non guarda più il file»). `None` se non è mai stato scaricato."""
    try:
        firma = _firma()
    except OSError:
        _CACHE.update(mtime=None, doc=None)
        return None
    if _CACHE["mtime"] != firma:
        with open(INDICE, encoding="utf-8") as f:
            _CACHE.update(mtime=firma, doc=json.load(f))
    return _CACHE["doc"]


def pezzo(opendb_id):
    doc = carica()
    return (doc or {}).get("pezzi", {}).get(opendb_id) if opendb_id else None


def novita(per_categoria=100):
    """Le differenze dell'ultimo aggiornamento, pronte per la pagina: per categoria, i nuovi
    dal più recente (quelli senza anno in fondo) e i tolti. `None` se non c'è un
    aggiornamento precedente con cui confrontare.

    ⚠️ «Nuovo» vuol dire **entrato nel catalogo**, non uscito sul mercato: OpenDB aggiunge
    anche pezzi vecchi. L'anno, quando c'è, è quello che distingue — e c'è per l'88% delle
    CPU ma per il 31% delle GPU e il 4% degli alimentatori."""
    doc = carica()
    diff = ((doc or {}).get("_meta") or {}).get("differenze")
    if not diff:
        return None
    nuovi, tolti = {}, {}
    for pid in diff.get("nuovi", []):
        v = doc["pezzi"].get(pid)
        if v:
            nuovi.setdefault(v["cat"], []).append({"nome": v["nome"], "anno": v.get("anno")})
    for v in diff.get("tolti", {}).values():
        tolti.setdefault(v["cat"], []).append(v["nome"])
    for cat, lista in nuovi.items():
        lista.sort(key=lambda x: (-(x["anno"] or 0), x["nome"]))
    fuori = {"da": diff.get("da"),
             "n_nuovi": sum(len(x) for x in nuovi.values()),
             "n_tolti": sum(len(x) for x in tolti.values()),
             "nuovi": [], "tolti": {c: sorted(n) for c, n in sorted(tolti.items())}}
    for cat in sorted(nuovi):
        lista = nuovi[cat]
        fuori["nuovi"].append({"cat": cat, "quanti": len(lista), "pezzi": lista[:per_categoria],
                               "altri": max(0, len(lista) - per_categoria)})
    return fuori


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
    prende il primo e lo si dice (`doppi`) — tranne nelle categorie di `SOMMATI`, dove il
    valore è la **lista** dei pezzi."""
    per_cat, doppi = {}, []
    for stato in ("desiderato", "posseduto", None):
        for c in componenti:
            if c.get("stato") != stato or not c.get("opendb_id"):
                continue
            v = pezzo(c["opendb_id"])
            if not v:
                continue
            voce = {**v, "_stato": stato, "_nome_hub": c.get("name")}
            modo = SOMMATI.get(v["cat"])
            if modo == "si_aggiunge":
                per_cat.setdefault(v["cat"], []).append(voce)
            elif modo == "sostituisce":
                lista = per_cat.setdefault(v["cat"], [])
                if not lista or lista[0]["_stato"] == stato:
                    lista.append(voce)
            elif v["cat"] in per_cat:
                if per_cat[v["cat"]]["_stato"] == stato:
                    doppi.append(v["cat"])
            else:
                per_cat[v["cat"]] = voce
    return per_cat, sorted(set(doppi))


# Le lunghezze standard degli SSD M.2, in mm: servono a leggere «2242-2280» come «2242, 2260
# e 2280». 25110 e 2580 sono gli slot larghi 25 mm.
_LUNGHEZZE_M2 = (30, 42, 60, 80, 110)


def misure_m2(testo):
    """`2242/2260/2280` o `2242-2280` o `2280-22110` → `{"2242", "2260", "2280"}`…

    Il dump scrive le misure in una ventina di modi («2260/ 2280», «22110/2280»). Un
    intervallo vale fra due misure della stessa larghezza. Insieme vuoto se non si legge."""
    fuori = set()
    for parte in re.split(r"[/,]", testo or ""):
        m = re.fullmatch(r"\s*(\d{2})(\d{2,3})\s*-\s*(\d{2})(\d{2,3})\s*", parte)
        if m and m.group(1) == m.group(3):
            lo, hi = int(m.group(2)), int(m.group(4))
            fuori |= {m.group(1) + str(n) for n in _LUNGHEZZE_M2 if lo <= n <= hi}
            continue
        fuori |= set(re.findall(r"\d{4,5}", parte))
    return fuori


def _tipo_m2(iface):
    """Cosa porta un'interfaccia: {"pcie"}, {"sata"}, tutte e due, o vuoto se non si legge."""
    t = (iface or "").upper()
    return ({"pcie"} if "PCIE" in t or "GEN" in t else set()) | ({"sata"} if "SATA" in t else set())


# Quanto è sicuro che un SSD entri in uno slot, dal peggio al meglio.
NO, IGNOTO, DUBBIO, SI = 0, 1, 2, 3
CORTO = ("l'SSD è più corto della misura dichiarata dello slot: di solito c'è il foro per "
         "fissarlo")
SATA = ("lo slot risulta solo PCIe e l'SSD è SATA: molti slot non lo accettano, ma su questo il "
        "catalogo non è affidabile")


def _entra(s, sl):
    """Un SSD in uno slot: `(voto, motivo del dubbio)`.

    ⚠️ Il dump è **avaro** su misure e interfacce, e un «no» costruito su quello che non dice
    sarebbe quasi sempre falso. Misurato il 25/09/2026: la MSI X570 Gaming Pro Carbon vi
    risulta con i soli 2242 e 2260; la Asus B450 Prime Plus con «PCIe 4.0 x4» e niente SATA,
    ed è PCIe 3.0 con SATA. Quindi un SSD più corto della misura più lunga dello slot, o SATA
    in uno slot che non nomina SATA, è `DUBBIO`; `NO` solo per un SSD più lungo di ogni misura
    o NVMe in uno slot dichiarato solo SATA."""
    misure, tipi = misure_m2(sl.get("misura")), _tipo_m2(sl.get("iface"))
    motivi = []
    if tipi and s["tipo"] and not s["tipo"] & tipi:
        if s["tipo"] != {"sata"}:
            return NO, []
        motivi.append(SATA)
    if not misure or not s["misura"]:
        return IGNOTO, []
    if s["misura"] not in misure:
        larghezza, lunghezza = s["misura"][:2], int(s["misura"][2:])
        stesse = [int(m[2:]) for m in misure if m[:2] == larghezza]
        if not stesse:
            return IGNOTO, []     # uno slot largo 25 mm: se accetti un 22 il dump non lo dice
        if lunghezza > max(stesse):
            return NO, []
        motivi.append(CORTO)
    if not tipi or not s["tipo"]:
        return IGNOTO, []
    return (DUBBIO if motivi else SI), motivi


def _abbina(ssd, slot):
    """Ogni SSD in uno slot diverso, col voto più alto possibile per l'abbinamento peggiore:
    `(SI | DUBBIO | IGNOTO | NO, motivi dei dubbi)`. Pochi pezzi: basta provare."""
    voti = [[_entra(s, sl) for sl in slot] for s in ssd]

    def prova(i, liberi, soglia):
        """I motivi raccolti lungo un abbinamento riuscito, o `None`."""
        if i == len(ssd):
            return []
        for j in liberi:
            voto, motivi = voti[i][j]
            if voto >= soglia:
                resto = prova(i + 1, liberi - {j}, soglia)
                if resto is not None:
                    return motivi + resto
        return None

    for soglia in (SI, DUBBIO, IGNOTO):
        motivi = prova(0, set(range(len(slot))), soglia)
        if motivi is not None:
            return soglia, list(dict.fromkeys(motivi))
    return NO, []


def _esito(nome, esito, dettaglio):
    return {"controllo": nome, "esito": esito, "dettaglio": dettaglio}


def _connettori_gpu(gpu, psu):
    """I connettori di alimentazione che la GPU chiede, contro quelli dell'alimentatore.

    Ogni 6 o 8 pin della GPU prende un «6+2 pin» dell'alimentatore; un 12VHPWR / 12V-2x6
    prende il suo. Senza il 12VHPWR nativo si usa l'adattatore della GPU, che chiede più 8
    pin: quanti dipende dal modello e il catalogo non lo dice, quindi «da verificare»
    (scelta di Davide del 25/09/2026)."""
    nome = "Connettori GPU / alimentatore"
    g, a = gpu.get("connettori"), psu.get("connettori")
    if g is None or a is None:
        return _esito(nome, "non_noto", "dato mancante")
    n68, n12 = g["6"] + g["8"], g["12"]
    if not n68 and not n12:
        # Vedi la nota in cima: tutto zero è quasi sempre un dato che manca.
        tdp = gpu.get("tdp")
        if tdp and tdp <= 75:
            return _esito(nome, "verifica", f"il catalogo non indica connettori e la GPU consuma "
                                            f"{tdp} W, entro i 75 W dello slot: probabilmente non ne servono")
        return _esito(nome, "non_noto", "il catalogo non indica i connettori della GPU")
    if not a["62"] and not a["12"]:
        return _esito(nome, "non_noto", "il catalogo non indica i connettori PCIe dell'alimentatore")
    vuole = " + ".join(f"{n}×{p}" for n, p in ((g["8"], "8 pin"), (g["6"], "6 pin"),
                                                 (n12, "12VHPWR")) if n)
    ha = f"l'alimentatore ha {a['62']}×6+2 pin" + (f" e {a['12']}×12VHPWR" if a["12"] else "")
    if n68 > a["62"]:
        return _esito(nome, "no", f"la GPU vuole {vuole}, {ha}")
    if n12 > a["12"]:
        return _esito(nome, "verifica",
                      f"la GPU vuole {vuole}, {ha}: serve l'adattatore (di solito nella scatola "
                      "della GPU), che chiede più connettori 8 pin — quanti dipende dal modello")
    return _esito(nome, "ok", f"la GPU vuole {vuole}, {ha}")


def _slot_m2(m2, mb):
    """Ogni SSD M.2 nel suo slot: quanti, di che misura (2280, 2242…) e se lo slot porta la
    sua interfaccia (NVMe su PCIe, o SATA). La velocità no: un SSD PCIe 5.0 in uno slot 4.0
    funziona, più lento."""
    nome = "SSD M.2 / slot della scheda madre"
    slot = mb.get("m2")
    if not slot:
        return _esito(nome, "non_noto", "il catalogo non indica slot M.2 per SSD su questa scheda")
    dischi = []
    for s in m2:
        m = re.fullmatch(r"M\.2-(\d{4,5})", s["formato"].strip())
        dischi.append({"misura": m.group(1) if m else None, "tipo": _tipo_m2(s.get("iface"))})
    conto = f"{len(m2)} SSD M.2, {len(slot)} slot"
    if len(m2) > len(slot):
        return _esito(nome, "no", conto)
    esito, motivi = _abbina(dischi, slot)
    if esito == SI:
        return _esito(nome, "ok", conto)
    if esito == DUBBIO:
        return _esito(nome, "verifica", conto + ": " + "; ".join(motivi) +
                      ". Controlla sul manuale della scheda")
    if esito == IGNOTO:
        return _esito(nome, "non_noto", conto + ": di qualche slot o SSD mancano misura o interfaccia")
    return _esito(nome, "no", conto + ": nessuna combinazione mette ogni SSD in uno slot della "
                                      "sua misura e interfaccia (" +
                  "; ".join(f"{sl.get('misura') or '?'} {sl.get('iface') or '?'}" for sl in slot) + ")")


def controlli(componenti):
    """Ogni controllo possibile fra i pezzi collegati: `ok`, `no`, `non_noto` (manca un
    dato) o `verifica` (i dati dicono sì, ma non bastano a dirlo). Più la percentuale sui
    soli controlli **verificabili** — un non noto non è né un sì né un no."""
    p, doppi = configurazione(componenti)
    cpu, mb, gpu = p.get("CPU"), p.get("Motherboard"), p.get("GPU")
    case, psu, dis = p.get("Case"), p.get("PSU"), p.get("CPU Cooler")
    kit, ssd = p.get("RAM") or [], p.get("Storage SSD") or []
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

    # I kit di RAM si sommano (`SOMMATI`): moduli e capacità sono il totale, il tipo deve
    # andare bene per ognuno.
    tipi_ram = [k.get("ram") for k in kit]
    if kit and mb:
        b = mb.get("ram")
        if not all(tipi_ram) or not b:
            fuori.append(_esito("Tipo di RAM / scheda madre", "non_noto", "tipo non indicato"))
        else:
            fuori.append(_esito("Tipo di RAM / scheda madre",
                                "ok" if all(a == b for a in tipi_ram) else "no",
                                f"{' + '.join(tipi_ram)} su {b}"))
        a, b = [k.get("moduli") for k in kit], mb.get("slot")
        if all(a) and b:
            fuori.append(_esito("Moduli di RAM / slot", "ok" if sum(a) <= b else "no",
                                f"{' + '.join(map(str, a)) + ' = ' if len(a) > 1 else ''}{sum(a)} moduli, {b} slot"))
        else:
            fuori.append(_esito("Moduli di RAM / slot", "non_noto", "dato mancante"))
        a, b = [k.get("capacita") for k in kit], mb.get("ram_max")
        if all(a) and b:
            fuori.append(_esito("Capacità RAM / massimo della scheda", "ok" if sum(a) <= b else "no",
                                f"{' + '.join(map(str, a)) + ' = ' if len(a) > 1 else ''}{sum(a)} GB su {b} GB"))
        else:
            fuori.append(_esito("Capacità RAM / massimo della scheda", "non_noto", "dato mancante"))
    if kit and cpu:
        tipi = cpu.get("ram") or []
        if all(tipi_ram) and tipi:
            fuori.append(_esito("Tipo di RAM / CPU", "ok" if all(a in tipi for a in tipi_ram) else "no",
                                f"{' + '.join(tipi_ram)}, la CPU supporta {', '.join(tipi)}"))
        else:
            fuori.append(_esito("Tipo di RAM / CPU", "non_noto", "dato mancante"))
    if len(kit) > 1:
        # Anche due kit identici comprati a parte: nessun dato del catalogo dice se insieme
        # tengono frequenza e timing.
        fuori.append(_esito("Più kit di RAM insieme", "verifica",
                            f"{len(kit)} kit: insieme non è garantito che tengano frequenza e "
                            "timing, possono scendere a quelli del più lento. Un solo kit con "
                            "tutti i moduli è la scelta sicura"))

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
    if psu and gpu:
        fuori.append(_connettori_gpu(gpu, psu))
    m2 = [s for s in ssd if str(s.get("formato") or "").startswith("M.2")]
    if m2 and mb:
        fuori.append(_slot_m2(m2, mb))

    verificabili = [e for e in fuori if e["esito"] in ("ok", "no")]
    ok = sum(1 for e in verificabili if e["esito"] == "ok")
    return {"controlli": fuori, "ok": ok, "verificabili": len(verificabili),
            "percentuale": round(100 * ok / len(verificabili)) if verificabili else None,
            "non_noti": sum(1 for e in fuori if e["esito"] == "non_noto"),
            "da_verificare": sum(1 for e in fuori if e["esito"] == "verifica"),
            "doppi": doppi, "collegati": len(p)}
