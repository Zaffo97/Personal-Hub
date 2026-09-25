#!/usr/bin/env python
"""Le prove di Arduino: link, anteprime e tabella dei piedini. Non tocca `hub.db` né la rete.

    python scripts/prova_arduino.py [--tieni]

Quello che queste prove devono tenere fermo sono i difetti che non darebbero errore:

- un **link** che finisce in un `href`: fino al 25/09/2026 il campo Tinkercad ci andava
  così com'era, e un `javascript:` lì è codice che gira al clic. Anche i link **già
  salvati** prima del controllo non devono comparire
- un **diagram.json incollato male** che cancella quello buono salvato prima
- un controllo che dice ✓ dove dovrebbe dire ✗: ogni circuito sbagliato qui sotto è
  costruito a mano, e l'esito atteso di ogni piedino è scritto **prima** di guardare
  cosa risponde il codice
- il **nome con l'apostrofo** negli handler inline
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile

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
NOME = "Semaforo dell'incrocio \"nord\""


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def circuito(scheda_tipo, parti, fili, sid=None):
    sid = sid or scheda_tipo.split("-")[-1]
    return json.dumps({"version": 1, "parts": [{"id": sid, "type": scheda_tipo}] +
                       [{"id": i, "type": t} for i, t in parti],
                       "connections": [[a, b, "", []] for a, b in fili]})


def riga(e, pin):
    return next((r for r in e["righe"] if r["piedino"] == pin), None)


def testi(e, pin):
    r = riga(e, pin)
    return " | ".join(x["testo"] for x in r["esiti"]) if r else "(riga assente)"


def prove_modulo():
    import arduino_circuito as C
    print("\n== 1. i link e le anteprime ==")
    esito("un `javascript:` non passa", C.link_valido("tinkercad_url", "javascript:alert(1)") is None)
    esito("un sito che finge Tinkercad non passa",
          C.link_valido("tinkercad_url", "https://tinkercad.com.truffa.it/things/abc") is None)
    esito("Wokwi nel campo Tinkercad non passa",
          C.link_valido("tinkercad_url", "https://wokwi.com/projects/1") is None)
    esito("Tinkercad: dalla pagina del progetto all'indirizzo /embed/",
          C.incorpora("tinkercad_url", "https://www.tinkercad.com/things/a4p5kroqdCl-semaforo/editel")
          == "https://www.tinkercad.com/embed/a4p5kroqdCl?editbtn=1")
    esito("Wokwi: il progetto per numero",
          C.incorpora("wokwi_url", "https://wokwi.com/projects/322062421191557714?x=1")
          == "https://wokwi.com/projects/322062421191557714")
    esito("   un link Wokwi senza progetto non dà un'anteprima inventata",
          C.incorpora("wokwi_url", "https://wokwi.com/") is None)

    print("\n== 2. i dati dei piedini ==")
    D = C.dati()
    esito("le cinque schede ci sono",
          set(D["schede"]) == {"wokwi-arduino-uno", "wokwi-arduino-nano", "wokwi-arduino-mega",
                               "board-esp32-devkit-c-v4", "wokwi-esp32-devkit-v1"})
    uno = D["schede"]["wokwi-arduino-uno"]["piedini"]
    esito("i PWM dell'Uno sono i sei della documentazione",
          {p for p, s in uno.items() if "pwm" in s and "." not in p} == {"3", "5", "6", "9", "10", "11"})
    esito("ESP32: GPIO34 solo ingresso, GPIO6 flash, GPIO0 di avvio",
          D["schede"]["board-esp32-devkit-c-v4"]["gpio"]["34"].get("solo_ingresso")
          and D["schede"]["board-esp32-devkit-c-v4"]["gpio"]["6"].get("flash")
          and D["schede"]["board-esp32-devkit-c-v4"]["gpio"]["0"].get("avvio"))

    print("\n== 3. un circuito giusto sull'Uno: nessun avviso ==")
    buono = circuito("wokwi-arduino-uno",
                     [("r1", "wokwi-resistor"), ("led1", "wokwi-led"), ("sv", "wokwi-servo"),
                      ("pot", "wokwi-potentiometer"), ("lcd", "wokwi-lcd1602")],
                     [("led1:A", "r1:1"), ("r1:2", "uno:13"), ("led1:C", "uno:GND.1"),
                      ("sv:PWM", "uno:9"), ("sv:V+", "uno:5V"), ("sv:GND", "uno:GND.2"),
                      ("pot:SIG", "uno:A0"), ("lcd:SDA", "uno:A4"), ("lcd:SCL", "uno:A5")])
    e = C.analizza(buono, "Arduino Uno")
    esito("zero avvisi e zero errori", e["conti"]["avviso"] == 0 and e["conti"]["errore"] == 0, str(e["conti"]))
    esito("   al 13 c'è la resistenza, non il LED (il componente non unisce le reti)",
          [c["capo"] for c in riga(e, "13")["collegati"]] == ["r1:2"])
    esito("   il servo vuole il PWM e il 9 ce l'ha", riga(e, "9")["richiesto"] == ["pwm"]
          and riga(e, "9")["esito"] == "ok")

    print("\n== 4. un circuito sbagliato sull'Uno ==")
    male = circuito("wokwi-arduino-uno",
                    [("sv", "wokwi-servo"), ("pot", "wokwi-potentiometer"), ("lcd", "wokwi-lcd1602"),
                     ("r1", "wokwi-resistor"), ("us", "wokwi-hc-sr04"), ("x", "tipo-inventato")],
                    [("sv:PWM", "uno:7"), ("pot:SIG", "uno:8"), ("lcd:SDA", "uno:2"),
                     ("r1:1", "uno:0"), ("us:VCC", "uno:3.3V"), ("x:1", "uno:99"),
                     ("uno:5V", "uno:GND.1")])
    e = C.analizza(male, "Arduino Uno")
    esito("servo sul 7: ✗, e dice dove sono i PWM",
          riga(e, "7")["esito"] == "errore" and "3, 5, 6, 9, 10, 11" in testi(e, "7"), testi(e, "7"))
    esito("potenziometro sull'8: ✗ non analogico", riga(e, "8")["esito"] == "errore"
          and "analogico" in testi(e, "8"))
    esito("SDA del display sul 2: ✗, l'I2C dell'Uno è su A4", riga(e, "2")["esito"] == "errore"
          and "A4" in testi(e, "2"), testi(e, "2"))
    esito("qualcosa sullo 0: ⚠ è la seriale", riga(e, "0")["esito"] == "avviso"
          and "seriale" in testi(e, "0"))
    esito("sensore a 5 V sul 3.3V: ⚠ la tensione, e ⚠ Wokwi non lo simula",
          "vuole 5 V" in testi(e, "3.3V") and "non simula" in testi(e, "3.3V"), testi(e, "3.3V"))
    esito("un piedino che non esiste: ✗", riga(e, "99")["esito"] == "errore")
    esito("5V e GND collegati: ✗ nei controlli generali",
          any(k["esito"] == "errore" and "massa" in k["testo"] for k in e["controlli"]))
    esito("il componente sconosciuto è dichiarato, non ignorato", e["sconosciuti"] == ["tipo-inventato"])

    print("\n== 5. ESP32 DevKitC V4 (il modello di Wokwi) ==")
    esp = circuito("board-esp32-devkit-c-v4",
                   [("sv", "wokwi-servo"), ("pot", "wokwi-potentiometer"), ("r1", "wokwi-resistor"),
                    ("bt", "wokwi-pushbutton"), ("lcd", "wokwi-lcd1602"), ("us", "wokwi-hc-sr04")],
                   [("sv:PWM", "esp:34"), ("pot:SIG", "esp:25"), ("r1:1", "esp:D2"),
                    ("bt:1.l", "esp:0"), ("lcd:SDA", "esp:18"), ("lcd:SCL", "esp:22"),
                    ("us:VCC", "esp:3V3"), ("esp:TX", "$serialMonitor:RX"), ("esp:RX", "$serialMonitor:TX")],
                   sid="esp")
    e = C.analizza(esp, "ESP32")
    esito("servo sul 34: ✗ niente PWM (solo ingresso)", riga(e, "34")["esito"] == "errore", testi(e, "34"))
    esito("potenziometro sul 25: ⚠ ADC2 col Wi-Fi", riga(e, "25")["esito"] == "avviso"
          and "ADC2" in testi(e, "25"))
    esito("qualcosa su D2 (GPIO9): ✗ è il flash", riga(e, "D2")["esito"] == "errore"
          and "flash" in testi(e, "D2"))
    esito("pulsante sul GPIO0: ⚠ piedino di avvio", "avvio" in testi(e, "0"))
    e16 = C.analizza(circuito("board-esp32-devkit-c-v4", [("r1", "wokwi-resistor")],
                              [("r1:1", "esp:16")], sid="esp"), "ESP32")
    esito("GPIO16: ⚠ e non ✗ — flash o PSRAM «di solito», dipende dal modulo",
          riga(e16, "16")["esito"] == "avviso" and "PSRAM" in testi(e16, "16"))
    esito("SDA sul 18: ⚠ non predefinito, Wire.begin — non ✗: sull'ESP32 l'I2C va ovunque",
          riga(e, "18")["esito"] == "avviso" and "Wire.begin" in testi(e, "18"))
    esito("   e SCL sul 22, quello predefinito: ✓", riga(e, "22")["esito"] == "ok")
    esito("sensore a 5 V sul 3V3: ⚠", "vuole 5 V" in testi(e, "3V3"))
    esito("i fili verso $serialMonitor non sono componenti: TX e RX non compaiono",
          riga(e, "TX") is None and riga(e, "RX") is None and "$serialMonitor" not in e["sconosciuti"])
    esito("la scheda del progetto è la stessa: nessun avviso di scheda",
          not any("il progetto dice" in k["testo"] for k in e["controlli"]))

    print("\n== 6. ESP32 DevKit V1, Nano, e la scheda sbagliata ==")
    v1 = circuito("wokwi-esp32-devkit-v1", [("r1", "wokwi-resistor")], [("r1:1", "esp:D34")], sid="esp")
    e = C.analizza(v1, "ESP32")
    esito("DevKit V1: una resistenza sul D34 → ⚠ solo ingresso", "solo ingresso" in testi(e, "D34"))
    nano = circuito("wokwi-arduino-nano", [("bt", "wokwi-pushbutton"), ("pot", "wokwi-potentiometer")],
                    [("bt:1.l", "nano:A6"), ("pot:SIG", "nano:A7")])
    e = C.analizza(nano, "Arduino Nano")
    esito("Nano: pulsante su A6 → ⚠ solo analogico", "solo ingresso analogico" in testi(e, "A6"))
    esito("   potenziometro su A7 → ✓", riga(e, "A7")["esito"] == "ok")
    e = C.analizza(nano, "Arduino Uno")
    esito("il progetto dice Uno e il circuito è una Nano: ⚠",
          any("il progetto dice Arduino Uno" in k["testo"] for k in e["controlli"]))

    print("\n== 7. quello che non si può leggere ==")
    esito("JSON rotto: lo dice", "JSON" in (C.analizza("{rotto", None) or {}).get("errore", ""))
    esito("JSON senza parts/connections: lo dice",
          "parts" in (C.analizza('{"a": 1}', None) or {}).get("errore", ""))
    e = C.analizza(circuito("wokwi-pi-pico", [], []), None)
    esito("nessuna scheda che conosco: lo dice e nomina quella che c'è",
          "wokwi-pi-pico" in (e.get("errore") or ""), e.get("errore"))
    esito("vuoto: nessuna analisi, nessun errore", C.analizza("", None) is None)
    return buono


def prove_web(dove, buono):
    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()
    db = extensions.get_db()
    colonne = {r["name"] for r in db.execute("PRAGMA table_info(arduino_projects)")}
    print("\n== 8. schema ==")
    esito("le colonne nuove ci sono", {"wokwi_url", "wokwi_diagramma"} <= colonne)
    for u in ("tizio", "caio"):
        db.execute("INSERT INTO users(username,password,display_name,role) VALUES(?,?,?,?)",
                   (u, extensions.hash_password(PW), u.title(), "user"))
    db.commit(); db.close()

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    def righe():
        d = extensions.get_db()
        r = [dict(x) for x in d.execute("SELECT * FROM arduino_projects ORDER BY id")]
        d.close()
        return r

    print("\n== 9. il salvataggio ==")
    with app.test_client() as c:
        c.post("/login", data={"username": "tizio", "password": PW})
        r = c.post("/arduino/save", data={
            "name": NOME, "board": "Arduino Uno", "status": "Idea",
            "tinkercad_url": "javascript:alert(1)",
            "wokwi_url": "https://wokwi.com/projects/322062421191557714",
            "wokwi_diagramma": buono}, follow_redirects=True)
        testo = r.get_data(as_text=True)
        p = righe()[0]
        esito("il `javascript:` non è salvato, e la pagina lo dice",
              p["tinkercad_url"] is None and "non salvato" in testo)
        esito("il link Wokwi e il diagram.json sì", p["wokwi_url"].startswith("https://wokwi.com/")
              and p["wokwi_diagramma"] == buono)
        c.post("/arduino/save", data={"proj_id": p["id"], "name": NOME, "board": "Arduino Uno",
                                      "status": "Idea", "wokwi_diagramma": "{incollato male"})
        esito("un diagram.json rotto non cancella quello buono", righe()[0]["wokwi_diagramma"] == buono)
        c.post("/arduino/save", data={"proj_id": p["id"], "name": NOME, "board": "Arduino Uno",
                                      "status": "Idea", "wokwi_diagramma": ""})
        esito("   svuotarlo invece lo toglie", righe()[0]["wokwi_diagramma"] is None)
        c.post("/arduino/save", data={"proj_id": p["id"], "name": NOME, "board": "Arduino Uno",
                                      "status": "Idea", "wokwi_diagramma": buono,
                                      "wokwi_url": "https://wokwi.com/projects/322062421191557714"})

        print("\n== 10. la pagina ==")
        # Un link cattivo salvato **prima** del controllo, scritto dritto nel DB.
        d = extensions.get_db()
        d.execute("UPDATE arduino_projects SET tinkercad_url='javascript:alert(2)'")
        d.commit(); d.close()
        pagina = c.get("/arduino/").get_data(as_text=True)
        esito("un link cattivo già nel DB non diventa un href", 'href="javascript:' not in pagina)
        esito("la tabella dei piedini c'è", 'id="piedini-' in pagina and "wokwi-arduino-uno" in pagina)
        esito("l'anteprima di Wokwi c'è", "https://wokwi.com/projects/322062421191557714" in pagina
              and "apriAnteprima(" in pagina)
        esito("i pulsanti «nuovo circuito» per le quattro schede e Tinkercad",
              all(u in pagina for u in ("projects/new/arduino-uno", "projects/new/arduino-nano",
                                        "projects/new/arduino-mega", "projects/new/esp32",
                                        "tinkercad.com/circuits")))
        try:
            import esprima
            from sweep_pagine import controlla
            errori = controlla(esprima, "/arduino/", pagina)
            esito("script e handler compilano, col nome che ha apostrofo e virgolette",
                  errori == 0, f"{errori} errori")
        except ImportError:
            esito("manca esprima: pip install esprima", False)
        with app.test_client() as altro:
            altro.post("/login", data={"username": "caio", "password": PW})
            esito("caio non vede il progetto di tizio",
                  "Semaforo" not in altro.get("/arduino/").get_data(as_text=True))
            altro.post("/arduino/save", data={"proj_id": p["id"], "name": "rubato", "board": "ESP32",
                                              "status": "Idea"})
            esito("   e non lo modifica", righe()[0]["name"] == NOME)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true", help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_arduino_")
    try:
        buono = prove_modulo()
        prove_web(dove, buono)
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
