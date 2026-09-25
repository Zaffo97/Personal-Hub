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
         usato_prev="", usato_data="", amazon="", eprice="", bpm="", versus="", note=""):
    """I campi di una riga del form, nell'ordine di `CAMPI_RIGA`."""
    return {"comp_cat": cat, "comp_name": nome, "comp_price": prezzo, "comp_notes": note,
            "comp_stato": stato, "comp_obiettivo": obiettivo, "comp_usato": usato,
            "comp_price_prev": prev, "comp_price_date": data_p,
            "comp_usato_prev": usato_prev, "comp_usato_date": usato_data,
            "comp_link_amazon": amazon, "comp_link_eprice": eprice,
            "comp_link_bpm": bpm, "comp_link_versus": versus}


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
