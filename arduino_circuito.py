"""Arduino: i link a Tinkercad e Wokwi, e la tabella dei piedini dal `diagram.json`.

Come per il PC Builder e la Stampa 3D, l'hub **non legge i siti**: il circuito lo incolla
Davide (la linguetta `diagram.json` dell'editor di Wokwi), e i dati dei piedini sono in
`data/arduino_piedini.json`, scritto da `scripts/importa_piedini_wokwi.py` dalle fonti
(sorgente di Wokwi, documentazione di Espressif). Qui niente è scritto a memoria.

Verificato il 25/09/2026:
- Tinkercad si incorpora **solo** da `/embed/<id>` (le altre pagine hanno
  `X-Frame-Options: SAMEORIGIN`), e solo se il circuito è **pubblico**
- i modelli «nuovo progetto» di Wokwi, aperti uno per uno: ⚠️ un nome che non esiste
  apre **in silenzio** un progetto Uno, quindi l'elenco qui sotto non si allunga a occhio
- il `diagram.json` del modello ESP32 ha due collegamenti a `$serialMonitor`: le parti
  che cominciano con `$` non sono componenti e si saltano
"""
import io
import json
import os
import re
from urllib.parse import urlparse

DATI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "arduino_piedini.json")

LINK = {
    "tinkercad_url": ("Tinkercad", ("tinkercad.com",)),
    "wokwi_url": ("Wokwi", ("wokwi.com",)),
}

TINKERCAD_NUOVO = ("Tinkercad", "https://www.tinkercad.com/circuits")
# Scheda del progetto (ARDUINO_BOARDS in data.py) -> modello Wokwi. Aperti il 25/09/2026:
# il titolo e il diagram.json di ognuno dicono la scheda giusta.
WOKWI_NUOVO = {
    "Arduino Uno": "https://wokwi.com/projects/new/arduino-uno",
    "Arduino Nano": "https://wokwi.com/projects/new/arduino-nano",
    "Arduino Mega": "https://wokwi.com/projects/new/arduino-mega",
    "ESP32": "https://wokwi.com/projects/new/esp32",
}
# Scheda del progetto -> tipi Wokwi che le corrispondono, per dire se sono la stessa.
TIPI_DI = {
    "Arduino Uno": {"wokwi-arduino-uno"},
    "Arduino Nano": {"wokwi-arduino-nano"},
    "Arduino Mega": {"wokwi-arduino-mega"},
    "ESP32": {"board-esp32-devkit-c-v4", "wokwi-esp32-devkit-v1"},
}
MAX_DIAGRAMMA = 500_000          # un diagram.json vero è di pochi KB; scelta, non misurata

# ESP-IDF: «GPIO6-11 and GPIO16-17 are **usually** connected to the SPI flash and PSRAM».
# Sulla DevKitC i 6-11 sono i piedini CLK/D0-D3/CMD, cioè il flash: errore. I 16-17
# dipendono dal modulo (la PSRAM c'è su alcuni e non su altri): avviso, non errore —
# dire ✗ a un piedino che sul modulo di Davide può essere libero sarebbe un dato inventato.
FLASH_DIPENDE = {"16", "17"}

OK, AVVISO, ERRORE = "ok", "avviso", "errore"
_PESO = {OK: 0, AVVISO: 1, ERRORE: 2}

_cache = {"mtime": None, "dati": None}


def dati():
    """Il file dei piedini, riletto se cambia (la regola delle copie in memoria)."""
    try:
        m = os.path.getmtime(DATI)
    except OSError:
        return None
    if _cache["mtime"] != m:
        _cache["dati"] = json.load(io.open(DATI, encoding="utf-8"))
        _cache["mtime"] = m
    return _cache["dati"]


def link_valido(campo, url):
    """L'indirizzo se è http(s) di un sito ammesso per quel campo, altrimenti None."""
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


def incorpora(campo, url):
    """L'indirizzo da mettere nell'iframe, o None se dal link non si ricava."""
    url = link_valido(campo, url)
    if not url:
        return None
    percorso = urlparse(url).path
    if campo == "tinkercad_url":
        m = re.search(r"/(?:things|embed)/([A-Za-z0-9]+)", percorso)
        return f"https://www.tinkercad.com/embed/{m.group(1)}?editbtn=1" if m else None
    m = re.search(r"/projects/(\d+)", percorso)
    return f"https://wokwi.com/projects/{m.group(1)}" if m else None


def leggi_diagramma(testo):
    """`(diagramma, errore)`. Controlla la **forma**, non il contenuto."""
    testo = (testo or "").strip()
    if not testo:
        return None, None
    if len(testo) > MAX_DIAGRAMMA:
        return None, f"troppo lungo ({len(testo)} caratteri)"
    try:
        d = json.loads(testo)
    except ValueError as e:
        return None, f"non è un JSON valido ({e})"
    if not isinstance(d, dict) or not isinstance(d.get("parts"), list) \
            or not isinstance(d.get("connections"), list):
        return None, "non ha «parts» e «connections»: è il diagram.json di Wokwi?"
    return d, None


def _base(nome, piedini):
    """`A4.2` e `11.2` sono lo stesso segnale di `A4` e `11` su un altro connettore.

    ⚠️ Solo un suffisso **numerico**: tagliando al primo punto `3.3V` diventava `3`, e un
    sensore sui 3,3 V risultava collegato al piedino digitale 3 — nessun errore, la riga
    sbagliata e basta. L'ha preso `prova_arduino.py` al primo giro (25/09/2026)."""
    m = re.fullmatch(r"(.+)\.(\d+)", nome)
    return m.group(1) if m and m.group(1) in piedini else nome


def leggibile(segnale):
    """Il nome a schermo di un segnale: `usart1:TX` → «Serial1 TX», `vcc:5` → «5 V»."""
    if segnale == "pwm":
        return "PWM"
    if segnale == "analog":
        return "analogico"
    if segnale == "gnd":
        return "massa"
    if segnale.startswith("vcc"):
        return (segnale[4:].replace(".", ",") + " V") if ":" in segnale else "alimentazione"
    m = re.fullmatch(r"usart(\d*):(\w+)", segnale)
    if m:
        return ("seriale " if not m.group(1) else f"Serial{m.group(1)} ") + m.group(2)
    bus, _, ruolo = segnale.partition(":")
    return f"{bus.upper()} {ruolo}".strip()


def _pin_num(p):
    m = re.match(r"([A-Za-z]*)(\d+)", p)
    return (m.group(1), int(m.group(2))) if m else (p, 0)


def analizza(testo, scheda_progetto=None):
    """La tabella dei piedini e i controlli, da un diagram.json."""
    d, errore = leggi_diagramma(testo)
    if errore or d is None:
        return {"errore": errore} if errore else None
    D = dati()
    if not D:
        return {"errore": "manca data/arduino_piedini.json: python scripts/importa_piedini_wokwi.py"}

    tipi = {}
    for p in d["parts"]:
        if isinstance(p, dict) and isinstance(p.get("id"), str):
            tipi[p["id"]] = str(p.get("type") or "")
    schede = [i for i, t in tipi.items() if t in D["schede"]]
    esito = {"errore": None, "controlli": [], "righe": [], "sconosciuti": []}
    if not schede:
        # Si nomina tutto quello che non è un componente noto: un filtro sul nome
        # («arduino», «esp32») lasciava fuori `wokwi-pi-pico` e diceva solo «nessuna».
        trovate = sorted({t for t in tipi.values() if t and t not in D["componenti"]})
        esito["errore"] = ("nessuna scheda che so controllare (Uno, Nano, Mega, ESP32 DevKitC V4 "
                           "o DevKit V1)" + (f": nel circuito c'è {', '.join(trovate)}" if trovate else ""))
        return esito
    sid = schede[0]
    stipo = tipi[sid]
    S = D["schede"][stipo]
    piedini = S["piedini"]
    esp32 = "gpio" in S
    esito["scheda"] = {"id": sid, "tipo": stipo, "nome": S["nome"]}

    def controllo(livello, testo_):
        esito["controlli"].append({"esito": livello, "testo": testo_})

    if len(schede) > 1:
        controllo(AVVISO, f"nel circuito ci sono {len(schede)} schede: controllo solo «{sid}»")
    if scheda_progetto in TIPI_DI and stipo not in TIPI_DI[scheda_progetto]:
        controllo(AVVISO, f"il progetto dice {scheda_progetto}, il circuito è {S['nome']}")

    # --- Le reti: chi è collegato a chi ---------------------------------------
    # I fili uniscono i capi; un componente **no** (i due capi di una resistenza sono
    # due reti diverse). Così `led1:A — r1:1` e `r1:2 — uno:13` dicono che al 13 c'è la
    # resistenza, non il LED: è quello che il piedino vede davvero.
    padre = {}

    def trova(x):
        padre.setdefault(x, x)
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for c in d["connections"]:
        if not isinstance(c, list) or len(c) < 2:
            continue
        a, b = c[0], c[1]
        if not (isinstance(a, str) and isinstance(b, str) and ":" in a and ":" in b):
            continue
        if a.startswith("$") or b.startswith("$"):
            continue                   # $serialMonitor & co.: non sono componenti
        padre[trova(a)] = trova(b)
    reti = {}
    for capo in list(padre):
        reti.setdefault(trova(capo), []).append(capo)

    comp = D["componenti"]
    sconosciuti = set()
    righe = {}
    for capi in reti.values():
        della_scheda = sorted({_base(c.split(":", 1)[1], piedini) for c in capi
                               if c.split(":", 1)[0] == sid})
        altri = [c for c in capi if c.split(":", 1)[0] != sid]
        if not della_scheda:
            continue
        # Alimentazione e massa della scheda nella stessa rete: un corto.
        tipi_alim = {("gnd" if "gnd" in piedini.get(p, []) else "vcc")
                     for p in della_scheda
                     if any(s == "gnd" or s.startswith("vcc") for s in piedini.get(p, []))}
        if tipi_alim == {"gnd", "vcc"}:
            controllo(ERRORE, "alimentazione e massa collegate fra loro: " + ", ".join(della_scheda))
        segnale = [p for p in della_scheda
                   if not any(s == "gnd" or s.startswith("vcc") for s in piedini.get(p, []))]
        if len(segnale) > 1:
            controllo(AVVISO, "piedini della scheda collegati fra loro: " + ", ".join(segnale))
        for p in della_scheda:
            riga = righe.setdefault(p, {"piedino": p, "collegati": [], "richiesto": set(),
                                        "esiti": []})
            for capo in altri:
                pid, pin = capo.split(":", 1)
                tipo = tipi.get(pid, "")
                if tipo in comp:
                    req = comp[tipo].get(pin)
                    if req is None:
                        riga["esiti"].append((AVVISO, f"{pid} ({tipo}) non ha un piedino «{pin}»"))
                        req = []
                else:
                    sconosciuti.add(tipo or pid)
                    req = []
                riga["collegati"].append({"capo": capo, "tipo": tipo, "requisiti": req})
                riga["richiesto"].update(req)

    # --- I controlli, piedino per piedino --------------------------------------
    # I PWM da suggerire: non i piedini del flash dell'ESP32, che il PWM tecnicamente ce
    # l'hanno ma che lo stesso controllo, due righe sotto, dice di non usare.
    def _sul_flash(p):
        g = next((x[5:] for x in piedini[p] if x.startswith("gpio:")), None)
        return (esp32 and g is not None and g not in FLASH_DIPENDE
                and S["gpio"].get(g, {}).get("flash"))
    pwm_scheda = sorted((p for p, s in piedini.items()
                         if "pwm" in s and _base(p, piedini) == p and not _sul_flash(p)), key=_pin_num)
    i2c_scheda = {r: [p for p, s in piedini.items() if f"i2c:{r}" in s and "." not in p]
                  for r in ("SDA", "SCL")}
    for p, riga in righe.items():
        s = piedini.get(p)
        es = riga["esiti"]
        if s is None:
            es.append((ERRORE, "la scheda non ha questo piedino"))
            s = []
        alim = any(x == "gnd" or x.startswith("vcc") for x in s)
        riga["gpio"] = next((x[5:] for x in s if x.startswith("gpio:")), None)
        riga["segnali"] = [x for x in s if not x.startswith("gpio:")]
        if p in S.get("non_simulati", []) or (p.startswith("RESET") and "RESET" in S.get("non_simulati", [])):
            es.append((AVVISO, "Wokwi non simula questo piedino: collegato, non fa niente"))
        # Tensione: un componente che dichiara la sua.
        tensione = next((x[4:] for x in s if x.startswith("vcc:")), None)
        for c in riga["collegati"]:
            for r in c["requisiti"]:
                if r.startswith("vcc:") and tensione and float(r[4:]) != float(tensione):
                    es.append((AVVISO, f"{c['capo']} vuole {r[4:]} V, qui ci sono {tensione} V"))
        if alim:
            continue
        req = riga["richiesto"]
        if "pwm" in req and "pwm" not in s:
            es.append((ERRORE, "serve un PWM e questo piedino non ce l'ha. PWM su questa scheda: "
                       + ", ".join(pwm_scheda)))
        if "analog" in req and "analog" not in s:
            es.append((ERRORE, "serve un ingresso analogico e questo piedino non lo è"))
        for ruolo in ("SDA", "SCL"):
            if f"i2c:{ruolo}" in req and f"i2c:{ruolo}" not in s:
                if esp32:
                    es.append((AVVISO, f"non è l'{ruolo} predefinito ({', '.join(i2c_scheda[ruolo])}): "
                               "nel codice serve Wire.begin(sda, scl)"))
                else:
                    es.append((ERRORE, f"l'I2C {ruolo} di questa scheda è su "
                               f"{', '.join(i2c_scheda[ruolo])}"))
        if any(x in ("usart:TX", "usart:RX") for x in s):
            es.append((AVVISO, "è la seriale della USB: la condivide col caricamento e col Serial Monitor"))
        if p in S.get("solo_analogici", []) and req != {"analog"}:
            es.append((AVVISO, f"{p} è solo ingresso analogico: non fa da digitale"))
        altri_veri = [c for c in riga["collegati"]
                      if c["tipo"] != "wokwi-resistor" and not any(r.startswith("i2c:") for r in c["requisiti"])]
        if len(altri_veri) > 1:
            es.append((AVVISO, f"{len(altri_veri)} componenti sullo stesso piedino"))
        if esp32 and riga["gpio"] is not None:
            g = S["gpio"].get(riga["gpio"], {})
            if g.get("flash") and riga["gpio"] in FLASH_DIPENDE:
                es.append((AVVISO, f"GPIO{riga['gpio']} di solito è collegato al flash o alla PSRAM "
                           "del modulo (ESP-IDF): controlla il tuo modulo"))
            elif g.get("flash"):
                es.append((ERRORE, f"GPIO{riga['gpio']} è collegato al flash del modulo: non va usato"))
            if g.get("solo_ingresso") and "pwm" not in req and not any(r.startswith("i2c") for r in req):
                es.append((AVVISO, f"GPIO{riga['gpio']} è solo ingresso: come uscita non funziona"))
            if g.get("avvio"):
                es.append((AVVISO, f"GPIO{riga['gpio']} è un piedino di avvio: se all'accensione è "
                           "tirato su o giù, la scheda può non partire"))
            if g.get("seriale"):
                es.append((AVVISO, "è la seriale della USB: la condivide col caricamento e col Serial Monitor"))
            if "analog" in req and (g.get("adc") or "").startswith("ADC2"):
                es.append((AVVISO, "ADC2: non legge col Wi-Fi acceso"))

    for p in sorted(righe, key=_pin_num):
        riga = righe[p]
        riga["richiesto"] = sorted(riga["richiesto"])
        riga["segnali_vis"] = [leggibile(x) for x in riga["segnali"]]
        for c in riga["collegati"]:
            c["requisiti_vis"] = [leggibile(x) for x in c["requisiti"]]
        riga["esito"] = max((e for e, _ in riga["esiti"]), key=_PESO.get, default=OK)
        riga["esiti"] = [{"esito": e, "testo": t} for e, t in dict.fromkeys(riga["esiti"])]
        esito["righe"].append(riga)
    esito["sconosciuti"] = sorted(sconosciuti)
    tutti = [r["esito"] for r in esito["righe"]] + [c["esito"] for c in esito["controlli"]]
    esito["conti"] = {k: tutti.count(k) for k in (OK, AVVISO, ERRORE)}
    return esito
