#!/usr/bin/env python
"""Scrive `data/arduino_piedini.json`: i piedini delle schede e dei componenti di Wokwi.

    python scripts/importa_piedini_wokwi.py [--dry-run] [--rileggi]

Serve ai controlli della tabella dei piedini di Arduino (`arduino_circuito.py`). I dati
**non si scrivono a mano**: vengono da tre fonti, lette il 25/09/2026.

- **wokwi-elements** (MIT, github.com/wokwi/wokwi-elements): il sorgente dei componenti
  del simulatore. Ogni piedino ha i suoi `signals` — `pwm`, `analog(n)`, `i2c('SDA')`,
  `spi(…)`, `usart(…)`, alimentazione — ed è quello che usa Wokwi stesso. Da qui le
  schede Arduino (Uno, Nano, Mega) e tutti i componenti
- **wokwi-boards** (github.com/wokwi/wokwi-boards): `board.json` dell'ESP32 DevKitC V4,
  la scheda del modello ESP32 di Wokwi. Dice solo **quale GPIO** c'è dietro ogni piedino
- **ESP-IDF, «GPIO Summary»** (docs.espressif.com): per ogni GPIO dell'ESP32 l'ADC, e i
  limiti — solo ingresso, collegato al flash, piedino di avvio. Più `pins_arduino.h` del
  core Arduino-ESP32 per la coppia I2C predefinita (21/22)

⚠️ Tre controlli incrociati, e lo script si **ferma** se non tornano, invece di scrivere
un dato che non si sa più da dove venga:
- i PWM di Uno e Mega letti dal sorgente devono essere quelli che la **documentazione**
  di Wokwi scrive a parole (3,5,6,9,10,11 · 2…13,44,45,46)
- la frase della documentazione della Nano su A6/A7 («can only be used for Analog
  input») dev'esserci ancora: è l'unico dato preso dal testo e non dal sorgente
- la tabella di Espressif deve avere i 34 GPIO che la sua stessa pagina dichiara

⚠️ Dai componenti si prendono **solo** i requisiti di segnale (`pwm`, `analog`, `i2c`) e
la tensione, non il resto dell'alimentazione: nel sorgente del NeoPixel il piedino `DIN`
è marcato `GND()` (25/09/2026), e fidarsene direbbe «massa» a un piedino di dati.
"""
import argparse
import html
import io
import json
import os
import re
import sys
from datetime import date

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USCITA = os.path.join(RADICE, "data", "arduino_piedini.json")
CACHE = os.path.join(RADICE, "data", "cache", "wokwi")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

GREZZO = "https://raw.githubusercontent.com"
ELEMENTI = GREZZO + "/wokwi/wokwi-elements/main/src/"
ALBERO_ELEMENTI = "https://api.github.com/repos/wokwi/wokwi-elements/git/trees/main?recursive=1"
DOCS = GREZZO + "/wokwi/wokwi-docs/main/docs/parts/"
SCHEDE_ESP32 = GREZZO + "/wokwi/wokwi-boards/main/boards/{}/board.json"
GPIO_ESP32 = "https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/gpio.html"
PINS_ARDUINO_ESP32 = GREZZO + "/espressif/arduino-esp32/master/variants/esp32/pins_arduino.h"

# Le schede: tipo Wokwi (quello del `diagram.json`) -> nome a schermo e voce di
# ARDUINO_BOARDS in `data.py`, per dire se la scheda del progetto e quella del circuito
# sono la stessa. I tipi sono quelli dei modelli di Wokwi, aperti il 25/09/2026.
SCHEDE_ARDUINO = {
    "wokwi-arduino-uno": ("Arduino Uno", "arduino-uno-element.ts"),
    "wokwi-arduino-nano": ("Arduino Nano", "arduino-nano-element.ts"),
    "wokwi-arduino-mega": ("Arduino Mega", "arduino-mega-element.ts"),
}
# Le ESP32: tipo Wokwi -> cartella in wokwi-boards. La DevKitC V4 è quella del modello
# «nuovo progetto ESP32» (aperto il 25/09/2026); la DevKit V1 è quella dei progetti
# Wokwi più vecchi, e un circuito incollato può essere l'una o l'altra.
SCHEDE_ESP32_TIPI = {
    "board-esp32-devkit-c-v4": ("ESP32 DevKitC V4", "esp32-devkit-c-v4"),
    "wokwi-esp32-devkit-v1": ("ESP32 DevKit V1", "esp32-devkit-v1"),
}


def scarica(url, nome, rileggi):
    """Una fonte, con una copia in `data/cache/wokwi/` (fuori da git)."""
    os.makedirs(CACHE, exist_ok=True)
    percorso = os.path.join(CACHE, nome)
    if not rileggi and os.path.exists(percorso):
        return io.open(percorso, encoding="utf-8").read()
    import requests
    r = requests.get(url, timeout=60, headers={"User-Agent": "personal-hub"})
    r.raise_for_status()
    io.open(percorso, "w", encoding="utf-8").write(r.text)
    return r.text


def segnali(testo):
    """I segnali di un piedino dal pezzo di sorgente che lo descrive."""
    s = []
    if "type: 'pwm'" in testo:
        s.append("pwm")
    if "analog(" in testo:
        s.append("analog")
    for bus, ruolo in re.findall(r"\b(i2c|spi)\('([A-Z]+)'", testo):
        s.append(f"{bus}:{ruolo}")
    for ruolo, n in re.findall(r"usart\('([A-Z]+)'(?:,\s*(\d+))?\)", testo):
        s.append(f"usart{n or ''}:{ruolo}")
    if "signal: 'GND'" in testo or "GND()" in testo:
        s.append("gnd")
    if "signal: 'VCC'" in testo or "VCC()" in testo:
        v = re.search(r"voltage:\s*([\d.]+)", testo)
        s.append("vcc" + (f":{v.group(1)}" if v else ""))
    return s


def piedini_ts(sorgente):
    """`{nome: [segnali]}` dal `pinInfo` di un elemento di wokwi-elements.

    Si taglia il sorgente a ogni `name: '…'` e si guarda il pezzo fino al successivo: i
    piedini stanno anche su più righe, e dentro `signals` ci sono graffe annidate che una
    regex «dalla graffa alla graffa» spezzerebbe a metà."""
    i = sorgente.find("pinInfo")
    if i < 0:
        return {}
    corpo = sorgente[i:]
    pezzi = list(re.finditer(r"\bname:\s*'([^']+)'", corpo))
    out = {}
    for k, m in enumerate(pezzi):
        fine = pezzi[k + 1].start() if k + 1 < len(pezzi) else len(corpo)
        blocco = corpo[m.end():fine]
        if "signals" not in blocco:
            continue
        nome = m.group(1)
        out.setdefault(nome, [])
        for s in segnali(blocco[:blocco.find("]") + 1] if "]" in blocco else blocco):
            if s not in out[nome]:
                out[nome].append(s)
    return out


def tabella_gpio(pagina):
    """`{numero: {adc, avvio, flash, solo_ingresso, jtag, seriale}}` dalla tabella di ESP-IDF."""
    righe = re.findall(r"<tr[^>]*>\s*<td><p>GPIO(\d+)</p></td>(.*?)</tr>", pagina, re.S)
    out = {}
    for num, resto in righe:
        celle = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td>(.*?)</td>", resto, re.S)]
        adc, _rtc, note = (celle + ["", "", ""])[:3]
        voce = {}
        if adc.startswith("ADC"):
            voce["adc"] = adc
        if "Strapping" in note:
            voce["avvio"] = True
        if "SPI0/1" in note:
            voce["flash"] = True
        if "GPI" == note.strip() or note.startswith("GPI "):
            voce["solo_ingresso"] = True
        if "JTAG" in note:
            voce["jtag"] = True
        if note in ("TXD", "RXD"):
            voce["seriale"] = note
        out[num] = voce
    return out


def senza_commenti(testo):
    """Il `board.json` di wokwi-boards ha commenti `/* */` **e** `//`: si tolgono solo
    fuori dalle stringhe, perché dentro una stringa `//` può essere un `https://`."""
    out, i, n, in_str = [], 0, len(testo), False
    while i < n:
        c = testo[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(testo[i + 1]); i += 2; continue
            if c == '"':
                in_str = False
            i += 1
        elif c == '"':
            in_str = True; out.append(c); i += 1
        elif testo.startswith("/*", i):
            i = testo.index("*/", i) + 2
        elif testo.startswith("//", i):
            i = testo.find("\n", i) if testo.find("\n", i) >= 0 else n
        else:
            out.append(c); i += 1
    return "".join(out)


def piedini_esp32(scheda, gpio, predef):
    """I piedini di una scheda ESP32 da `board.json` + la tabella dei GPIO di ESP-IDF."""
    piedini = {}
    for nome, p in scheda["pins"].items():
        bersaglio = p["target"]
        if bersaglio == "GND":
            piedini[nome] = ["gnd"]
            continue
        m = re.fullmatch(r"power\(([\d.]+)\)", bersaglio)
        if m:
            piedini[nome] = [f"vcc:{m.group(1)}"]
            continue
        # ⚠️ `GPIO15` **o** `15`: nel board.json della DevKit V1 il solo D15 è scritto
        # nudo (25/09/2026). Trattarlo come «non è un GPIO» lo lasciava senza segnali in
        # silenzio — l'ha preso il confronto col sorgente dell'elemento, che il PWM su
        # D15 ce l'ha. Un bersaglio che non si riconosce ferma lo script.
        m = re.fullmatch(r"(?:GPIO)?(\d+)", bersaglio)
        if not m:
            if bersaglio != "CHIP_PU":
                raise SystemExit(f"FERMO: bersaglio sconosciuto nel board.json: {nome} -> {bersaglio}")
            piedini[nome] = []           # EN: il reset, non un GPIO
            continue
        n = m.group(1)
        voce = gpio.get(n, {})
        s = ["gpio:" + n]
        # Dal GPIO matrix «peripheral output signals can be routed to any IO pins» (ESP-IDF):
        # il PWM (LEDC) va su ogni GPIO che può essere un'uscita, cioè non su 34-39.
        if not voce.get("solo_ingresso"):
            s.append("pwm")
        if voce.get("adc"):
            s.append("analog")
        if int(n) == predef["SDA"]:
            s.append("i2c:SDA")
        if int(n) == predef["SCL"]:
            s.append("i2c:SCL")
        piedini[nome] = s
    return piedini


def costruisci(rileggi):
    documento = {"_fonte": {
        "letto_il": date.today().isoformat(),
        "wokwi_elements": "https://github.com/wokwi/wokwi-elements (MIT)",
        "wokwi_boards": "https://github.com/wokwi/wokwi-boards",
        "esp_idf_gpio": GPIO_ESP32,
        "arduino_esp32": PINS_ARDUINO_ESP32,
    }, "schede": {}, "componenti": {}}

    # --- Le schede Arduino --------------------------------------------------
    for tipo, (nome, file) in SCHEDE_ARDUINO.items():
        piedini = piedini_ts(scarica(ELEMENTI + file, file, rileggi))
        documento["schede"][tipo] = {"nome": nome, "piedini": piedini}

    def pwm(tipo):
        return {p for p, s in documento["schede"][tipo]["piedini"].items()
                if "pwm" in s and "." not in p}

    attesi = {"wokwi-arduino-uno": {"3", "5", "6", "9", "10", "11"},
              "wokwi-arduino-mega": {str(n) for n in list(range(2, 14)) + [44, 45, 46]}}
    for tipo, pin in attesi.items():
        if pwm(tipo) != pin:
            raise SystemExit(f"FERMO: i PWM di {tipo} letti dal sorgente ({sorted(pwm(tipo), key=int)}) "
                             f"non sono quelli della documentazione ({sorted(pin, key=int)})")
    # Uno e Mega: le due frasi della documentazione devono esserci ancora, o il confronto
    # qui sopra confronta con un ricordo.
    doc_uno = scarica(DOCS + "wokwi-arduino-uno.md", "doc-uno.md", rileggi)
    doc_mega = scarica(DOCS + "wokwi-arduino-mega.md", "doc-mega.md", rileggi)
    if "Digital pins 3, 5, 6, 9, 10, and 11 have hardware PWM support" not in doc_uno or \
            "Digital pins 2 … 13, 44, 45, and 46 have hardware PWM support" not in doc_mega:
        raise SystemExit("FERMO: la documentazione di Wokwi non dice più i PWM come il 25/09/2026")

    # La Nano: A6 e A7 solo analogici. È l'unico dato preso dal **testo** della
    # documentazione e non dal sorgente, quindi si controlla che la frase ci sia.
    doc_nano = scarica(DOCS + "wokwi-arduino-nano.md", "doc-nano.md", rileggi)
    if "can only be used for Analog input" not in doc_nano:
        raise SystemExit("FERMO: la documentazione della Nano non dice più «A6/A7 solo analogici»")
    documento["schede"]["wokwi-arduino-nano"]["solo_analogici"] = ["A6", "A7"]

    # I piedini che il simulatore **non ha**: stessa frase nelle pagine di Uno e Mega, e
    # la Nano rimanda all'Uno. Collegarci qualcosa in Wokwi non dà errore, semplicemente
    # non succede niente.
    frase = "Pins 3.3V / IOREF / AREF / RESET are not available in the simulation."
    if frase not in doc_uno or frase not in doc_mega:
        raise SystemExit("FERMO: la documentazione non elenca più i piedini non simulati")
    for tipo in SCHEDE_ARDUINO:
        documento["schede"][tipo]["non_simulati"] = ["3.3V", "IOREF", "AREF", "RESET"]

    # --- L'ESP32 ------------------------------------------------------------
    gpio = tabella_gpio(scarica(GPIO_ESP32, "esp-idf-gpio.html", rileggi))
    if len(gpio) != 34:
        raise SystemExit(f"FERMO: la tabella di ESP-IDF ha {len(gpio)} GPIO, la pagina ne dichiara 34")
    h = scarica(PINS_ARDUINO_ESP32, "pins_arduino_esp32.h", rileggi)
    predef = {k: int(v) for k, v in re.findall(r"static const uint8_t (SDA|SCL|TX|RX|MOSI|MISO|SCK|SS) = (\d+);", h)}
    if predef.get("SDA") is None or predef.get("SCL") is None:
        raise SystemExit("FERMO: pins_arduino.h dell'ESP32 non dice più SDA/SCL")
    for tipo, (nome_scheda, cartella) in SCHEDE_ESP32_TIPI.items():
        scheda = json.loads(senza_commenti(scarica(SCHEDE_ESP32.format(cartella),
                                                   cartella + ".json", rileggi)))
        documento["schede"][tipo] = {"nome": nome_scheda, "gpio": gpio, "predefiniti": predef,
                                     "piedini": piedini_esp32(scheda, gpio, predef)}
    # La seconda strada per la DevKit V1: il suo elemento in wokwi-elements scrive i PWM e
    # l'I2C piedino per piedino. Devono combaciare con quelli ricavati qui sopra.
    el = piedini_ts(scarica(ELEMENTI + "esp32-devkit-v1-element.ts",
                            "esp32-devkit-v1-element.ts", rileggi))
    mio = documento["schede"]["wokwi-esp32-devkit-v1"]["piedini"]
    for segnale in ("pwm", "i2c:SDA", "i2c:SCL"):
        a = {p for p, s in el.items() if segnale in s}
        b = {p for p, s in mio.items() if segnale in s}
        if a != b:
            raise SystemExit(f"FERMO: DevKit V1, «{segnale}» non combacia col sorgente Wokwi: "
                             f"solo lì {sorted(a - b)}, solo qui {sorted(b - a)}")

    # --- I componenti -------------------------------------------------------
    # Il tipo è quello del decoratore `@customElement('…')`, non il nome del file: è la
    # stringa che finisce nel `diagram.json`. E una classe può **ereditare** i piedini
    # (`wokwi-lcd2004` estende il 1602 e non ha un `pinInfo` suo): senza seguire
    # `extends`, l'LCD 2004 risulterebbe un componente sconosciuto.
    albero = json.loads(scarica(ALBERO_ELEMENTI, "albero-elements.json", rileggi))
    file_el = sorted(t["path"][4:] for t in albero["tree"]
                     if re.fullmatch(r"src/[a-z0-9-]+-element\.ts", t["path"]))
    per_classe, eredi = {}, []
    for file in file_el:
        sorgente = scarica(ELEMENTI + file, file, rileggi)
        tipo = re.search(r"@customElement\('([^']+)'\)", sorgente)
        classe = re.search(r"class (\w+) extends (\w+)", sorgente)
        if not tipo or not classe:
            continue
        tipo = tipo.group(1)
        piedini = piedini_ts(sorgente)
        per_classe[classe.group(1)] = (tipo, piedini)
        if not piedini:
            eredi.append((tipo, classe.group(2)))
    for tipo, padre in eredi:
        if padre in per_classe and per_classe[padre][1]:
            per_classe[tipo + "#erede"] = (tipo, per_classe[padre][1])
    for tipo, piedini in per_classe.values():
        # Le schede non sono componenti: queste qui (Franzininho, Nano RP2040) non
        # hanno i controlli, e contarle fra i componenti le farebbe sembrare dei pezzi.
        if not piedini or tipo in SCHEDE_ARDUINO or tipo in SCHEDE_ESP32_TIPI or                 tipo in ("wokwi-franzininho", "wokwi-nano-rp2040-connect"):
            continue
        # Solo requisiti di segnale e tensione: vedi il docstring (il DIN del NeoPixel).
        documento["componenti"][tipo] = {
            p: [x for x in s if x == "pwm" or x == "analog" or x.startswith("i2c:")
                or re.fullmatch(r"vcc:[\d.]+", x)]
            for p, s in piedini.items()}
    if "wokwi-lcd2004" not in documento["componenti"]:
        raise SystemExit("FERMO: l'LCD 2004 non eredita più i piedini dal 1602 come il 25/09/2026")
    return documento


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="dice cosa scriverebbe, non scrive")
    ap.add_argument("--rileggi", action="store_true", help="riscarica le fonti invece della cache")
    args = ap.parse_args()
    nuovo = costruisci(args.rileggi)
    for tipo, s in nuovo["schede"].items():
        n = len(s["piedini"])
        print(f"  {tipo:<28} {n:>3} piedini, PWM {sum('pwm' in x for x in s['piedini'].values())}, "
              f"analogici {sum('analog' in x for x in s['piedini'].values())}")
    print(f"  componenti: {len(nuovo['componenti'])}")
    vecchio = None
    if os.path.exists(USCITA):
        vecchio = json.load(io.open(USCITA, encoding="utf-8"))
    uguale = vecchio is not None and {k: v for k, v in vecchio.items() if k != "_fonte"} == \
        {k: v for k, v in nuovo.items() if k != "_fonte"}
    if uguale:
        print("Niente di cambiato: il file resta com'è.")
        return 0
    if args.dry_run:
        print("--dry-run: non ho scritto niente.")
        return 0
    with io.open(USCITA, "w", encoding="utf-8", newline="\n") as f:
        json.dump(nuovo, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print(f"Scritto {os.path.relpath(USCITA, RADICE)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
