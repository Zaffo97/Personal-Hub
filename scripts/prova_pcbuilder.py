#!/usr/bin/env python
"""Le prove del PC Builder con stato, prezzi datati, link e avvisi. Non tocca `hub.db`
e non va in rete: l'hub **costruisce** indirizzi, non li apre.

    python scripts/prova_pcbuilder.py [--tieni]

Quello che queste prove devono tenere fermo sono i difetti che non darebbero errore:

- la **data del prezzo** che si perde: `pcbuilder_save()` cancella e ricrea i pezzi a ogni
  salvataggio, quindi se la data non passa dal form ogni salvataggio la rifà oggi e il
  promemoria non scatta mai
- un **link incollato** che finisce in un `href`: `javascript:` lì è codice che gira al
  clic, e un link di un altro sito sotto l'etichetta «Amazon» è un'etichetta falsa
- le **liste del form sfasate**: `zip()` taglia alla più corta, e un pezzo prenderebbe il
  prezzo di un altro
- il pezzo **di un altro utente** segnato come ricontrollato
- il **venduto** contato nel totale, qui e in Dashboard
- la ricerca di **Versus** (`/it/search?q=`), che la pagina dichiara e che non funziona:
  nessun link deve usarla
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date, timedelta

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []
PW = "password-di-prova"
OGGI = date.today()
VECCHIO = (OGGI - timedelta(days=30)).isoformat()


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def riga(cat, nome, prezzo="", stato="", obiettivo="", usato="", prev="", data_p="",
         usato_prev="", usato_data="", amazon="", eprice="", bpm="", versus="", note="",
         opendb=""):
    """I campi di una riga del form, nell'ordine di `CAMPI_RIGA`."""
    return {"comp_cat": cat, "comp_name": nome, "comp_price": prezzo, "comp_notes": note,
            "comp_stato": stato, "comp_obiettivo": obiettivo, "comp_usato": usato,
            "comp_price_prev": prev, "comp_price_date": data_p,
            "comp_usato_prev": usato_prev, "comp_usato_date": usato_data,
            "comp_link_amazon": amazon, "comp_link_eprice": eprice,
            "comp_link_bpm": bpm, "comp_link_versus": versus, "comp_opendb": opendb}


def form(nome_build, righe, bid=""):
    dati = {"build_id": bid, "build_name": nome_build, "build_notes": ""}
    for k in righe[0]:
        dati[k] = [r[k] for r in righe]
    return dati


def prove_modulo():
    import pc_negozi as N
    print("\n== 1. pc_negozi, senza DB ==")
    esito("un link `javascript:` non passa",
          N.link_valido("link_amazon", "javascript:alert(1)") is None)
    esito("un link di un altro sito sotto «Amazon» non passa",
          N.link_valido("link_amazon", "https://www.amazon.it.truffa.com/dp/B0D6W8L5YM") is None)
    esito("un link amazon.it vero passa",
          N.link_valido("link_amazon", "https://www.amazon.it/x/dp/B0D6W8L5YM/ref=sr_1_1"))
    esito("l'ASIN si legge da /dp/", N.asin("https://www.amazon.it/x/dp/B0D6W8L5YM/ref=1") == "B0D6W8L5YM")
    esito("   e un link corto non ne ha uno (niente Keepa inventato)",
          N.asin("https://amzn.eu/d/abc123") is None)
    esito("lo slug di Versus da un nome pulito",
          N.slug_versus("Nvidia GeForce RTX 3070") == "nvidia-geforce-rtx-3070")

    senza = N.link({"name": "RTX 3070"})
    etich = [l["etichetta"] for l in senza]
    esito("senza link incollati: niente Keepa", "Keepa" not in etich, ", ".join(etich))
    esito("   eBay venduti ha i due filtri",
          any("LH_Sold=1&LH_Complete=1" in l["url"] for l in senza))
    esito("   BPM apre la home e lo dice", any(l["etichetta"] == "BPM" and
          l["url"] == "https://www.bpm-power.com/" and "home" in l["nota"] for l in senza))
    esito("   nessun link usa la ricerca di Versus che non funziona",
          not any("versus.com/it/search" in l["url"] for l in senza))
    con = N.link({"name": "RTX 3070", "link_amazon": "https://www.amazon.it/x/dp/B0D6W8L5YM"})
    esito("con la pagina Amazon: Keepa sul dominio 8 (amazon.it)",
          any(l["url"] == "https://keepa.com/#!product/8-B0D6W8L5YM" for l in con))

    print("\n== 2. la data di un prezzo scritto a mano ==")
    esito("valore uguale: resta la data di prima",
          N.data_valore(100.0, 100.0, VECCHIO, OGGI) == VECCHIO)
    esito("valore cambiato: diventa oggi", N.data_valore(90.0, 100.0, VECCHIO, OGGI) == OGGI.isoformat())
    esito("valore tolto: nessuna data", N.data_valore(0, 100.0, VECCHIO, OGGI) is None)
    esito("data di prima illeggibile: diventa oggi, non resta spazzatura",
          N.data_valore(100.0, 100.0, "ieri", OGGI) == OGGI.isoformat())

    print("\n== 3. gli avvisi ==")
    a = N.avvisi([
        {"name": "sotto soglia", "stato": "desiderato", "price": 450, "obiettivo": 500, "prezzo_data": OGGI.isoformat()},
        {"name": "sopra soglia", "stato": "desiderato", "price": 550, "obiettivo": 500, "prezzo_data": OGGI.isoformat()},
        {"name": "vecchio", "stato": "desiderato", "price": 550, "prezzo_data": VECCHIO},
        {"name": "mai scritto", "stato": "desiderato", "price": 0},
        {"name": "da vendere", "stato": "posseduto", "price": 300, "obiettivo": 200, "valore_usato": 220, "valore_usato_data": OGGI.isoformat()},
        {"name": "tengo", "stato": "posseduto", "price": 300},
        {"name": "venduto", "stato": "venduto", "price": 1, "obiettivo": 500},
        {"name": "senza stato", "stato": None, "price": 1, "obiettivo": 500},
    ], OGGI)
    ob = sorted(c["name"] for c in a["obiettivo"])
    ri = sorted(c["name"] for c in a["ricontrollare"])
    esito("soglia raggiunta: il desiderato sotto soglia e il posseduto che vale abbastanza",
          ob == ["da vendere", "sotto soglia"], str(ob))
    esito("da ricontrollare: il prezzo vecchio e quello mai scritto, nient'altro",
          ri == ["mai scritto", "vecchio"], str(ri))


# Uno zip finto con la forma di quello di OpenDB: <radice>/open-db/<Categoria>/<id>.json.
# Pochi pezzi scelti per far scattare ogni controllo; i valori sono presi dal dump vero
# del 25/09/2026 (7800X3D 120 W AM5, RTX 4070 Ti 285 W, Fractal North 355/170 mm, ...).
PEZZI_FINTI = {
    ("CPU", "cpu-7800"): {"socket": "AM5", "specifications": {"tdp": 120, "memory": {"types": ["DDR5"]}},
                          "metadata": {"name": "AMD Ryzen 7 7800X3D"}},
    ("CPU", "cpu-9700k"): {"socket": "LGA 1151", "specifications": {"tdp": 95, "memory": {"types": ["DDR4"]}},
                           "metadata": {"name": "Intel Core i7-9700K"}},
    # Uno slot M.2 per SSD e uno con chiave E (il Wi-Fi), che non deve contare.
    ("Motherboard", "mb-b650"): {"socket": "AM5", "form_factor": "Micro ATX",
                                 "memory": {"ram_type": "DDR5", "slots": 4, "max": 192},
                                 "m2_slots": [{"size": "2280", "key": "M", "interface": "PCIe 4.0 x4"},
                                              {"size": "2230", "key": "E", "interface": "PCIe"}],
                                 "metadata": {"name": "ASUS TUF GAMING B650M-E WIFI", "releaseYear": 2023}},
    ("Motherboard", "mb-h270"): {"socket": "LGA 1151", "form_factor": "Thin Mini-ITX",
                                 "memory": {"ram_type": "DDR4", "slots": 2, "max": 32},
                                 "m2_slots": [], "metadata": {"name": "Scheda H270 Thin"}},
    ("Motherboard", "mb-sata"): {"socket": "AM4", "form_factor": "ATX",
                                 "m2_slots": [{"size": "2242/2260/2280", "key": "M", "interface": "SATA3 6.0 Gb/s"}],
                                 "metadata": {"name": "Scheda con M.2 solo SATA"}},
    ("RAM", "ram-ddr5"): {"ram_type": "DDR5", "modules": {"quantity": 2}, "capacity": 32,
                          "metadata": {"name": "Kit DDR5 32GB (2x16GB)"}},
    ("RAM", "ram-ddr4"): {"ram_type": "DDR4", "modules": {"quantity": 4}, "capacity": 64,
                          "metadata": {"name": "Kit DDR4 64GB (4x16GB)"}},
    ("GPU", "gpu-4070ti"): {"length": 308, "tdp": 285,
                            "power_connectors": {"pcie_6_pin": 0, "pcie_8_pin": 0,
                                                 "pcie_12VHPWR": 1, "pcie_12V_2x6": 0},
                            "metadata": {"name": "MSI GeForce RTX 4070 Ti VENTUS 3X", "releaseYear": 2023}},
    ("GPU", "gpu-lunga"): {"length": 360, "tdp": 285,
                           "metadata": {"name": "ZOTAC GeForce RTX 4070 Ti lunghissima"}},
    ("GPU", "gpu-3x8"): {"length": 300, "tdp": 320,
                         "power_connectors": {"pcie_6_pin": 0, "pcie_8_pin": 3,
                                              "pcie_12VHPWR": 0, "pcie_12V_2x6": 0},
                         "metadata": {"name": "Radeon con tre 8 pin"}},
    ("GPU", "gpu-zero-70w"): {"length": 170, "tdp": 70,
                              "power_connectors": {"pcie_6_pin": 0, "pcie_8_pin": 0,
                                                   "pcie_12VHPWR": 0, "pcie_12V_2x6": 0},
                              "metadata": {"name": "GPU piccola da 70 W"}},
    ("PCCase", "case-north"): {"supported_motherboard_form_factors": ["ATX", "Micro ATX", "Mini-ITX"],
                               "max_video_card_length": 355, "max_cpu_cooler_height": 170,
                               "metadata": {"name": "Fractal Design North"}},
    ("PCCase", "case-ignoto"): {"supported_motherboard_form_factors": ["ATX"],
                                "max_video_card_length": 400, "max_cpu_cooler_height": None,
                                "metadata": {"name": "Case senza altezza"}},
    ("PSU", "psu-750"): {"wattage": 750, "connectors": {"pcie_6_plus_2_pin": 4, "pcie_12vhpwr": 1},
                         "metadata": {"name": "Alimentatore 750W"}},
    ("PSU", "psu-500"): {"wattage": 500, "connectors": {"pcie_6_plus_2_pin": 2, "pcie_12vhpwr": 0},
                         "metadata": {"name": "Alimentatore 500W"}},
    # 855 alimentatori veri sono così, anche da 750 W: lo zero è un dato che manca.
    ("PSU", "psu-zero"): {"wattage": 850, "connectors": {"pcie_6_plus_2_pin": 0, "pcie_12vhpwr": 0},
                          "metadata": {"name": "Alimentatore senza connettori nel catalogo"}},
    ("CPUCooler", "dis-ak400"): {"height": 155, "cpu_sockets": ["AM4", "AM5", "LGA 1700"],
                                 "metadata": {"name": "Deepcool AK400"}},
    ("Storage", "ssd-nvme"): {"form_factor": "M.2-2280", "interface": "M.2 PCIe 4.0 x4",
                              "metadata": {"name": "SSD NVMe 2280"}},
    ("Storage", "ssd-nvme-2"): {"form_factor": "M.2-2280", "interface": "M.2 PCIe 5.0 x4",
                                "metadata": {"name": "Secondo SSD NVMe 2280"}},
    ("Storage", "ssd-sata-m2"): {"form_factor": "M.2-2280", "interface": "M.2 SATA",
                                 "metadata": {"name": "SSD M.2 SATA"}},
    ("Storage", "ssd-2242"): {"form_factor": "M.2-2242", "interface": "M.2 PCIe 3.0 x4",
                              "metadata": {"name": "SSD corto 2242"}},
    ("Storage", "ssd-22110"): {"form_factor": "M.2-22110", "interface": "M.2 PCIe 4.0 x4",
                               "metadata": {"name": "SSD lungo 22110"}},
    ("Storage", "hdd"): {"form_factor": "3.5\"", "interface": "SATA 6.0 Gb/s",
                         "metadata": {"name": "Disco 4TB"}},
    ("RAM", "ram-ddr5-b"): {"ram_type": "DDR5", "modules": {"quantity": 2}, "capacity": 64,
                            "metadata": {"name": "Secondo kit DDR5 64GB (2x32GB)"}},
}


def zip_finto(togli=(), aggiungi=None):
    """Lo zip finto; `togli` e `aggiungi` simulano un aggiornamento di OpenDB."""
    import zipfile
    buf = io.BytesIO()
    pezzi = {k: v for k, v in PEZZI_FINTI.items() if k[1] not in togli}
    pezzi.update(aggiungi or {})
    with zipfile.ZipFile(buf, "w") as z:
        for (cat, pid), d in pezzi.items():
            z.writestr(f"buildcores-open-db-main/open-db/{cat}/{pid}.json",
                       json.dumps({"opendb_id": pid, **d}))
        z.writestr("buildcores-open-db-main/open-db/Chair/sedia.json",
                   json.dumps({"opendb_id": "sedia", "metadata": {"name": "Una sedia"}}))
    return buf.getvalue()


def prove_catalogo(dove):
    import pc_catalogo as C
    C.INDICE = os.path.join(dove, "cache", "opendb_pezzi.json")   # mai data/cache vera
    print("\n== 10. il catalogo: rifiuto, indice, ricerca ==")
    C.scarica = zip_finto
    try:
        C.aggiorna()
        rifiutato = False
    except ValueError as e:
        rifiutato = "troppo pochi" in str(e)
    esito("uno zip con pochi pezzi si RIFIUTA (i minimi veri sono centinaia)", rifiutato)
    esito("   e l'indice non viene scritto", not os.path.exists(C.INDICE))
    C.MINIMI = {c: 1 for c in C.MINIMI}
    conti = C.aggiorna()
    esito("coi minimi abbassati l'indice si scrive, e la sedia resta fuori",
          os.path.exists(C.INDICE) and conti == {"CPU": 2, "Motherboard": 3, "RAM": 3, "GPU": 4,
                                                   "Case": 2, "PSU": 3, "CPU Cooler": 1,
                                                   "Storage SSD": 6}, str(conti))
    esito("   primo scaricamento: nessuna novità, non «tutto nuovo»", C.novita() is None)
    esito("lo slot M.2 con chiave E (Wi-Fi) non entra fra quelli per SSD",
          len(C.pezzo("mb-b650")["m2"]) == 1)
    esito("la ricerca vuole tutte le parole", [x["id"] for x in C.cerca("GPU", "4070 ventus")] == ["gpu-4070ti"])
    esito("   e resta nella categoria", C.cerca("CPU", "4070") == [])

    print("\n== 11. i controlli ==")

    def conf(*ids, stato="posseduto"):
        return [{"name": i, "stato": stato, "opendb_id": i} for i in ids]

    def per(k):
        return {e["controllo"]: e for e in k["controlli"]}

    k = C.controlli(conf("cpu-7800", "mb-b650", "ram-ddr5", "gpu-4070ti", "case-north", "psu-750",
                         "dis-ak400", "ssd-nvme"))
    esito("la configurazione buona: 12 su 12, 100%",
          (k["ok"], k["verificabili"], k["percentuale"], k["non_noti"], k["da_verificare"]) == (12, 12, 100, 0, 0),
          str([(e["controllo"], e["esito"]) for e in k["controlli"] if e["esito"] != "ok"]))
    k = per(C.controlli(conf("cpu-7800", "mb-b650", "ram-ddr4")))
    esito("RAM DDR4 su scheda e CPU DDR5: due «no»",
          k["Tipo di RAM / scheda madre"]["esito"] == "no" and k["Tipo di RAM / CPU"]["esito"] == "no")
    k = per(C.controlli(conf("cpu-9700k", "mb-h270")))
    esito("LGA 1151 con LGA 1151: «da verificare», non «ok»",
          k["Socket CPU / scheda madre"]["esito"] == "verifica")
    k = per(C.controlli(conf("mb-h270", "case-north")))
    esito("Thin Mini-ITX in un case Mini-ITX: ok", k["Formato scheda madre / case"]["esito"] == "ok")
    k = per(C.controlli(conf("cpu-7800", "gpu-lunga", "case-ignoto", "dis-ak400", "psu-500")))
    esito("dissipatore in un case senza altezza massima: «non noto», mai «ok»",
          k["Altezza dissipatore / case"]["esito"] == "non_noto")
    esito("alimentatore: 500 W < (120+285)x1,3 = 526 W: no",
          k["Alimentatore / consumi"]["esito"] == "no" and "526" in k["Alimentatore / consumi"]["dettaglio"],
          k["Alimentatore / consumi"]["dettaglio"])
    k = C.controlli(conf("gpu-lunga", "case-north"))
    esito("GPU da 360 mm in un case da 355: no, e la percentuale è 0",
          per(k)["Lunghezza GPU / case"]["esito"] == "no" and k["percentuale"] == 0)
    esito("un solo pezzo collegato: nessun controllo", C.controlli(conf("cpu-7800"))["controlli"] == [])
    k = C.controlli(conf("gpu-lunga", "case-north") + conf("gpu-4070ti", stato="desiderato"))
    esito("la GPU desiderata prende il posto della posseduta: 308 mm, ok",
          per(k)["Lunghezza GPU / case"]["esito"] == "ok")
    k = C.controlli(conf("case-north") + conf("gpu-4070ti", stato="venduto"))
    esito("un pezzo venduto non entra nella configurazione", k["collegati"] == 1)
    k = C.controlli(conf("gpu-lunga", "gpu-4070ti", "case-north"))
    esito("due GPU possedute: si dice, e si controlla la prima", k["doppi"] == ["GPU"])

    print("\n== 14. i connettori della GPU ==")
    G = "Connettori GPU / alimentatore"
    e = per(C.controlli(conf("gpu-4070ti", "psu-750")))[G]
    esito("12VHPWR contro un alimentatore che ce l'ha: ok", e["esito"] == "ok", e["dettaglio"])
    e = per(C.controlli(conf("gpu-4070ti", "psu-500")))[G]
    esito("12VHPWR senza il nativo: «da verificare», con l'adattatore nel dettaglio",
          e["esito"] == "verifica" and "adattatore" in e["dettaglio"], e["dettaglio"])
    e = per(C.controlli(conf("gpu-3x8", "psu-500")))[G]
    esito("tre 8 pin contro due 6+2: no", e["esito"] == "no", e["dettaglio"])
    e = per(C.controlli(conf("gpu-3x8", "psu-750")))[G]
    esito("tre 8 pin contro quattro 6+2: ok", e["esito"] == "ok", e["dettaglio"])
    e = per(C.controlli(conf("gpu-4070ti", "psu-zero")))[G]
    esito("alimentatore con zero connettori nel catalogo: «non noto», mai «no»", e["esito"] == "non_noto")
    e = per(C.controlli(conf("gpu-zero-70w", "psu-500")))[G]
    esito("GPU da 70 W senza connettori: «da verificare», non «ok»", e["esito"] == "verifica", e["dettaglio"])
    e = per(C.controlli(conf("gpu-lunga", "psu-750")))[G]
    esito("GPU senza il campo: «non noto»", e["esito"] == "non_noto")

    print("\n== 15. gli SSD M.2 ==")
    esito("le misure scritte in modi diversi si leggono",
          C.misure_m2("2242-2280") == {"2242", "2260", "2280"}
          and C.misure_m2("2260/ 2280") == {"2260", "2280"}
          and C.misure_m2("2280-22110") == {"2280", "22110"}
          and C.misure_m2("2580-25110") == {"2580", "25110"} and C.misure_m2(None) == set())
    M = "SSD M.2 / slot della scheda madre"
    esito("un NVMe 2280 in uno slot 2280 PCIe: ok",
          per(C.controlli(conf("mb-b650", "ssd-nvme")))[M]["esito"] == "ok")
    e = per(C.controlli(conf("mb-b650", "ssd-nvme", "ssd-nvme-2")))[M]
    esito("due SSD e un solo slot per SSD (quello del Wi-Fi non conta): no",
          e["esito"] == "no" and "2 SSD M.2, 1 slot" in e["dettaglio"], e["dettaglio"])
    e = per(C.controlli(conf("mb-b650", "ssd-sata-m2")))[M]
    esito("SSD SATA in uno slot che dice solo PCIe: «da verificare» (il catalogo è avaro sul SATA)",
          e["esito"] == "verifica" and "SATA" in e["dettaglio"], e["dettaglio"])
    e = per(C.controlli(conf("mb-sata", "ssd-nvme")))[M]
    esito("NVMe in uno slot dichiarato solo SATA: no", e["esito"] == "no", e["dettaglio"])
    e = per(C.controlli(conf("mb-sata", "ssd-sata-m2")))[M]
    esito("   e lì un SSD SATA: ok", e["esito"] == "ok", e["dettaglio"])
    e = per(C.controlli(conf("mb-b650", "ssd-22110")))[M]
    esito("SSD 22110 in uno slot 2280: no", e["esito"] == "no")
    e = per(C.controlli(conf("mb-b650", "ssd-2242")))[M]
    esito("SSD 2242 in uno slot che dichiara solo 2280: «da verificare», non «no»",
          e["esito"] == "verifica" and "più corto" in e["dettaglio"], e["dettaglio"])
    e = per(C.controlli(conf("mb-h270", "ssd-nvme")))[M]
    esito("scheda senza slot M.2 nel catalogo: «non noto»", e["esito"] == "non_noto")
    esito("un disco da 3,5\" non entra nel controllo M.2",
          M not in per(C.controlli(conf("mb-b650", "hdd"))))

    print("\n== 16. più pezzi della stessa categoria ==")
    k = C.controlli(conf("mb-b650", "ssd-nvme") + conf("ssd-nvme-2", stato="desiderato"))
    esito("un SSD posseduto e uno desiderato si SOMMANO: 2 su 1 slot, no",
          per(k)[M]["esito"] == "no" and not k["doppi"], per(k)[M]["dettaglio"])
    k = per(C.controlli(conf("mb-b650", "ram-ddr5", "ram-ddr5-b")))
    esito("due kit posseduti si sommano: 2 + 2 = 4 moduli, 32 + 64 = 96 GB",
          k["Moduli di RAM / slot"]["dettaglio"] == "2 + 2 = 4 moduli, 4 slot"
          and k["Capacità RAM / massimo della scheda"]["dettaglio"] == "32 + 64 = 96 GB su 192 GB",
          k["Moduli di RAM / slot"]["dettaglio"] + " | " + k["Capacità RAM / massimo della scheda"]["dettaglio"])
    esito("   e due kit insieme sono «da verificare»", k["Più kit di RAM insieme"]["esito"] == "verifica")
    k = per(C.controlli(conf("mb-b650", "ram-ddr4") + conf("ram-ddr5", stato="desiderato")))
    esito("un kit desiderato prende il posto del posseduto: DDR5 su DDR5, un kit solo",
          k["Tipo di RAM / scheda madre"]["esito"] == "ok" and "Più kit di RAM insieme" not in k,
          k["Tipo di RAM / scheda madre"]["dettaglio"])
    k = per(C.controlli(conf("mb-b650", "ram-ddr5", "ram-ddr4")))
    esito("due kit, uno DDR4: il tipo è «no»", k["Tipo di RAM / scheda madre"]["esito"] == "no",
          k["Tipo di RAM / scheda madre"]["dettaglio"])

    print("\n== 17. le novità del catalogo ==")
    nuovo = {("GPU", "gpu-nuova"): {"length": 330, "tdp": 360,
                                    "metadata": {"name": "GPU uscita adesso", "releaseYear": 2026}},
             ("GPU", "gpu-vecchia-aggiunta"): {"length": 200, "tdp": 120,
                                               "metadata": {"name": "GPU vecchia appena aggiunta", "releaseYear": 2016}}}
    C.scarica = lambda: zip_finto(togli=("dis-ak400",), aggiungi=nuovo)
    C.MINIMI["CPU Cooler"] = 0
    C.aggiorna()
    n = C.novita()
    esito("un aggiornamento dice cosa è entrato e cosa è uscito",
          n and n["n_nuovi"] == 2 and n["n_tolti"] == 1
          and n["tolti"] == {"CPU Cooler": ["Deepcool AK400"]}, str(n and (n["n_nuovi"], n["n_tolti"], n["tolti"])))
    esito("   i nuovi dal più recente", n and [x["nome"] for x in n["nuovi"][0]["pezzi"]]
          == ["GPU uscita adesso", "GPU vecchia appena aggiunta"])
    # Un indice di prima **senza** una categoria: quella non è «tutta nuova».
    doc = json.load(open(C.INDICE, encoding="utf-8"))
    del doc["_meta"]["conti"]["Storage SSD"]
    doc["pezzi"] = {k: v for k, v in doc["pezzi"].items() if v["cat"] != "Storage SSD"}
    json.dump(doc, open(C.INDICE, "w", encoding="utf-8"))
    C.aggiorna()
    n = C.novita()
    esito("una categoria che l'indice di prima non aveva non conta fra i nuovi",
          n is not None and n["n_nuovi"] == 0, str(n and n["nuovi"]))
    C.scarica = zip_finto
    C.MINIMI["CPU Cooler"] = 1
    C.aggiorna()


# Le righe che contano di un DxDiag vero, quello del PC di Davide del 25/09/2026, senza
# nome e ID della macchina. Ci sono i tre casi che il parser di prima sbagliava: la scheda
# madre che non c'è (solo il segnaposto ASUS), la grafica integrata del 7800X3D, e il
# nome della CPU con i core e la frequenza attaccati.
DXDIAG_VERO = """------------------
System Information
------------------
         Operating System: Windows 11 Pro 64-bit (10.0, Build 26200)
      System Manufacturer: ASUS
             System Model: System Product Name
                     BIOS: 1616 (type: UEFI)
                Processor: AMD Ryzen 7 7800X3D 8-Core Processor            (16 CPUs), ~4.2GHz
                   Memory: 32768MB RAM
      Available OS Memory: 31888MB RAM
---------------
Display Devices
---------------
           Card name: Microsoft Remote Display Adapter
        Manufacturer: Microsoft
      Display Memory: 27937 MB
           Card name: NVIDIA GeForce RTX 4070 Ti
        Manufacturer: NVIDIA
      Display Memory: Unknown
           Card name: AMD Radeon(TM) Graphics
        Manufacturer: Advanced Micro Devices, Inc.
      Display Memory: 16429 MB
"""


def prove_dxdiag():
    from blueprints.pcbuilder import _parse_dxdiag, _pulisci_cpu
    print("\n== 13. l'import DxDiag ==")
    comp, note = _parse_dxdiag(DXDIAG_VERO)
    per = {c["category"]: [x["name"] for x in comp if x["category"] == c["category"]] for c in comp}
    esito("la CPU col nome pulito, che il catalogo trova", per.get("CPU") == ["AMD Ryzen 7 7800X3D"], str(per.get("CPU")))
    esito("la RAM in GB, non «32768MB RAM»", per.get("RAM") == ["32 GB"], str(per.get("RAM")))
    esito("una GPU sola: la 4070 Ti", per.get("GPU") == ["NVIDIA GeForce RTX 4070 Ti"], str(per.get("GPU")))
    esito("NESSUNA scheda madre inventata da «System Product Name»", "Motherboard" not in per)
    esito("   e le note dicono perché, e cosa è stato scartato",
          any("non la riporta" in n and "ASUS" in n for n in note)
          and any("AMD Radeon(TM) Graphics" in n for n in note), " | ".join(note))
    esito("la CPU Intel si pulisce allo stesso modo",
          _pulisci_cpu("Intel(R) Core(TM) i7-9700K CPU @ 3.60GHz (8 CPUs), ~3.6GHz") == "Intel Core i7-9700K")
    esito("una scheda video vera che si chiama «Radeon» NON è scartata",
          _parse_dxdiag("Card name: AMD Radeon RX 7900 XTX\n")[0][0]["name"] == "AMD Radeon RX 7900 XTX")


def prove_web(dove):
    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()
    db = extensions.get_db()
    colonne = {r["name"] for r in db.execute("PRAGMA table_info(pc_components)")}
    print("\n== 4. schema ==")
    nuove = {"stato", "prezzo_data", "obiettivo", "valore_usato", "valore_usato_data",
             "link_amazon", "link_eprice", "link_bpm", "link_versus"}
    esito("le 9 colonne nuove esistono", nuove <= colonne, ", ".join(sorted(nuove - colonne)))
    for u in ("tizio", "caio"):
        db.execute("INSERT INTO users(username,password,display_name,role) VALUES(?,?,?,?)",
                   (u, extensions.hash_password(PW), u.title(), "user"))
    db.commit(); db.close()

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    def entra(c, chi):
        c.post("/login", data={"username": chi, "password": PW})

    def pezzi():
        d = extensions.get_db()
        r = {x["name"]: dict(x) for x in d.execute("SELECT * FROM pc_components")}
        d.close()
        return r

    print("\n== 5. il salvataggio ==")
    with app.test_client() as c:
        entra(c, "tizio")
        r = c.post("/pcbuilder/save", data=form("Il mio PC", [
            riga("GPU", "Nvidia GeForce RTX 3070", "499", "posseduto", obiettivo="250", usato="280"),
            riga("GPU", "Nvidia GeForce RTX 4070", "600", "desiderato", obiettivo="550",
                 amazon="https://www.amazon.it/x/dp/B0D6W8L5YM", eprice="javascript:alert(1)"),
            riga("Case", "Vecchio case", "40", "venduto"),
        ]), follow_redirects=True)
        p = pezzi()
        esito("tre pezzi salvati", len(p) == 3, str(list(p)))
        g70, g40 = p.get("Nvidia GeForce RTX 3070", {}), p.get("Nvidia GeForce RTX 4070", {})
        esito("stato, soglia e valore da usato entrano",
              (g70.get("stato"), g70.get("obiettivo"), g70.get("valore_usato")) == ("posseduto", 250.0, 280.0))
        esito("il prezzo nuovo prende la data di oggi", g40.get("prezzo_data") == OGGI.isoformat())
        esito("il link Amazon vero entra", g40.get("link_amazon", "").endswith("B0D6W8L5YM"))
        esito("il link `javascript:` NON entra", g40.get("link_eprice") is None)
        testo = r.get_data(as_text=True)
        esito("   e la pagina lo dice", "Link non salvati" in testo and "ePrice" in testo)
        esito("la pagina ha Keepa, eBay venduti e il confronto Versus",
              "keepa.com/#!product/8-B0D6W8L5YM" in testo and "LH_Sold=1" in testo
              and "versus.com/it/nvidia-geforce-rtx-3070-vs-nvidia-geforce-rtx-4070" in testo)
        esito("soglia raggiunta: il 3070 vale 280 da usato, la soglia è 250",
              "Soglia raggiunta" in testo and "da usato vale 280.00" in testo)
        esito("il totale non conta il venduto: 499 + 600 = 1099",
              "&euro; 1099</span>" in testo, "")
        esito("   e dice quanto resta da comprare (600)", "da comprare &euro; 600" in testo)

        bid = extensions.get_db().execute("SELECT id FROM pc_builds").fetchone()["id"]
        print("\n== 6. la data sopravvive al salvataggio ==")
        c.post("/pcbuilder/save", data=form("Il mio PC", [
            riga("GPU", "Nvidia GeForce RTX 3070", "499", "posseduto", "250", "280",
                 usato_prev="280", usato_data=VECCHIO),
            riga("GPU", "Nvidia GeForce RTX 4070", "600", "desiderato", "550",
                 prev="600", data_p=VECCHIO, amazon="https://www.amazon.it/x/dp/B0D6W8L5YM"),
        ], bid=bid))
        p = pezzi()
        esito("prezzo uguale: la data resta quella di 30 giorni fa",
              p["Nvidia GeForce RTX 4070"]["prezzo_data"] == VECCHIO)
        esito("valore da usato uguale: idem",
              p["Nvidia GeForce RTX 3070"]["valore_usato_data"] == VECCHIO)
        testo = c.get("/pcbuilder/").get_data(as_text=True)
        esito("e il promemoria compare", "Da ricontrollare" in testo and "prezzo di 30 giorni fa" in testo)

        cid = p["Nvidia GeForce RTX 4070"]["id"]
        print("\n== 7. ricontrollato, e di chi ==")
        with app.test_client() as altro:
            entra(altro, "caio")
            altro.post(f"/pcbuilder/componente/{cid}/ricontrollato")
        esito("un altro utente non sposta la data del mio pezzo",
              pezzi()["Nvidia GeForce RTX 4070"]["prezzo_data"] == VECCHIO)
        c.post(f"/pcbuilder/componente/{cid}/ricontrollato")
        esito("io sì: diventa oggi, e il prezzo resta 600",
              (pezzi()["Nvidia GeForce RTX 4070"]["prezzo_data"],
               pezzi()["Nvidia GeForce RTX 4070"]["price"]) == (OGGI.isoformat(), 600.0))

        print("\n== 8. liste sfasate ==")
        rotto = form("Il mio PC", [riga("GPU", "Uno", "1"), riga("GPU", "Due", "2")], bid=bid)
        rotto["comp_price"] = ["1"]          # un prezzo in meno dei nomi
        r = c.post("/pcbuilder/save", data=rotto, follow_redirects=True)
        esito("rifiutato, e lo dice", "arrivato incompleto" in r.get_data(as_text=True))
        esito("   e i pezzi di prima sono ancora tutti lì",
              set(pezzi()) == {"Nvidia GeForce RTX 3070", "Nvidia GeForce RTX 4070"}, str(list(pezzi())))

        print("\n== 12. il catalogo nella pagina ==")
        r = c.get("/pcbuilder/api/catalogo?cat=GPU&q=ventus").get_json()
        esito("l'API cerca", [x["id"] for x in r["risultati"]] == ["gpu-4070ti"])
        esito("   e rifiuta una categoria senza catalogo",
              c.get("/pcbuilder/api/catalogo?cat=Monitor&q=x").get_json()["ok"] is False)
        r = c.post("/pcbuilder/save", data=form("Il mio PC", [
            riga("GPU", "Nvidia GeForce RTX 4070", "600", "desiderato", opendb="gpu-4070ti"),
            riga("Case", "Il case", "90", "posseduto", opendb="case-north"),
            riga("RAM", "La RAM", "80", "posseduto", opendb="gpu-4070ti"),
        ], bid=bid), follow_redirects=True)
        testo = r.get_data(as_text=True)
        p = pezzi()
        esito("il collegamento giusto entra", p["Nvidia GeForce RTX 4070"]["opendb_id"] == "gpu-4070ti")
        esito("una RAM collegata a una GPU NO, e la pagina lo dice",
              p["La RAM"]["opendb_id"] is None and "non è della stessa categoria" in testo)
        esito("la pagina mostra i controlli, la percentuale e la fonte con la licenza",
              "Lunghezza GPU / case" in testo and "100%" in testo and "ODC-By" in testo
              and "github.com/buildcores/buildcores-open-db" in testo)
        esito("   e il nome del modello collegato", "MSI GeForce RTX 4070 Ti VENTUS 3X" in testo)
        esito("le novità dell'ultimo aggiornamento sono nella pagina, coi pezzi usciti",
              "Novità nel catalogo" in testo and "GPU uscita adesso" in testo and "Usciti" in testo)

        # Un pezzo collegato che OpenDB ha tolto: la pagina non deve dire «non scaricato».
        d = extensions.get_db()
        d.execute("UPDATE pc_components SET opendb_id='gpu-nuova' WHERE name='Nvidia GeForce RTX 4070'")
        d.commit(); d.close()
        testo = c.get("/pcbuilder/").get_data(as_text=True)
        esito("un modello uscito dal catalogo si dice così, non «catalogo non scaricato»",
              "non è più nel catalogo" in testo and "il catalogo non è scaricato" not in testo)
        r = c.post("/pcbuilder/save", data=form("Il mio PC", [
            riga("GPU", "Nvidia GeForce RTX 4070", "600", "desiderato", opendb="gpu-nuova"),
            riga("Case", "Il case", "90", "posseduto", opendb="case-north"),
        ], bid=bid), follow_redirects=True)
        testo = r.get_data(as_text=True)
        esito("   e al salvataggio si scollega col suo motivo, non «altra categoria»",
              pezzi()["Nvidia GeForce RTX 4070"]["opendb_id"] is None
              and "non è più in OpenDB" in testo and "non è della stessa categoria" not in testo)

        import pc_catalogo as C
        prima = open(C.INDICE, encoding="utf-8").read()

        def rotto():
            raise OSError("rete assente")
        C.scarica = rotto
        testo = c.post("/pcbuilder/catalogo/aggiorna", follow_redirects=True).get_data(as_text=True)
        esito("aggiornamento fallito: lo dice, e il catalogo di prima resta intatto",
              "Catalogo non aggiornato" in testo and open(C.INDICE, encoding="utf-8").read() == prima)
        C.scarica = zip_finto
        testo = c.post("/pcbuilder/catalogo/aggiorna", follow_redirects=True).get_data(as_text=True)
        esito("aggiornamento riuscito: lo dice coi numeri", "Catalogo aggiornato: 2 CPU" in testo)
        esito("   e rispetto a prima: niente di nuovo, detto",
              "0 nuovi, 0 usciti" in testo and "Nessun pezzo entrato o uscito" in testo)

        r = c.post("/pcbuilder/import_dxdiag", data={"dxdiag_text": DXDIAG_VERO}).get_json()
        esito("la route dell'import manda anche le note",
              r["ok"] and len(r["components"]) == 3 and len(r["note"]) == 2)

        print("\n== 9. la Dashboard ==")
        c.post("/pcbuilder/save", data=form("Il mio PC", [
            riga("GPU", "Nvidia GeForce RTX 3070", "499", "venduto"),
            riga("GPU", "Nvidia GeForce RTX 4070", "600", "desiderato"),
        ], bid=bid))
        d = extensions.get_db()
        tot = d.execute("""SELECT COALESCE(SUM(CASE WHEN c.stato='venduto' THEN 0 ELSE c.price END), 0) AS t
                           FROM pc_components c""").fetchone()["t"]
        d.close()
        testo = c.get("/").get_data(as_text=True)
        esito("il totale della build senza il venduto è 600", tot == 600.0)
        # Il totale della Dashboard si scrive «&#8364; N»: si cerca quello, non un 600
        # qualunque che la pagina potrebbe contenere per altri motivi.
        mostrati = re.findall(r"&#8364; (\d+)</span>", testo)
        esito("   e la Dashboard lo mostra così (600, non 1099)", mostrati == ["600"], str(mostrati))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true", help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_pcbuilder_")
    try:
        prove_modulo()
        prove_catalogo(dove)
        prove_dxdiag()
        prove_web(dove)
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
