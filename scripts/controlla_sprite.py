#!/usr/bin/env python
"""Quali voci del catalogo mostrano uno sprite rotto, e quali no.

    python scripts/controlla_sprite.py [--solo-rotti] [--senza-cache] [--limite N]

Gli sprite non sono un dato del catalogo: sono **URL costruiti** da uno slug verso
`img.pokemondb.net`, con una tabella di eccezioni (`SPRITE_SLUG_OVERRIDES` in
`blueprints/api_pokemon.py`). Quindi «sprite mancante» vuol dire una cosa sola: quel
URL risponde 404.

⚠️ **E nessuno se ne accorge.** In nessun template c'è un `onerror` sulle `<img>`: un
404 diventa l'icona di immagine spezzata del browser, senza una riga che dica perché.
È il fallback silenzioso di sempre, con un'altra faccia.

⚠️ **Gli URL li costruisce la route vera**, chiamata col test client, non una copia
della sua logica qui dentro. Una copia proverebbe se stessa: è l'errore che in questo
progetto è già costato un giro di lavoro più di una volta.

**Come tratta la rete.** Una richiesta `HEAD` per URL, **in fila** e con una pausa,
perché pokemondb è un sito di qualcun altro e queste sono ~2700 richieste. Gli esiti
finiscono in una cache su disco (fuori dal repo), quindi una seconda esecuzione non
tocca la rete: si può rilanciare quanto si vuole mentre si sistemano le eccezioni.

**Le tre categorie**, e solo la terza è lavoro:

  * **ok**          — l'URL risponde, ed è l'immagine di quella forma
  * **ripiego**     — l'URL risponde, ma è l'immagine di **un'altra** voce, perché
                      quella giusta su pokemondb non esiste: i Totem di Alola, le
                      andature di Koraidon e Miraidon, le Mega **inventate**.
                      Sta in `SENZA_SPRITE_PDB`, cioè qualcuno l'ha deciso e scritto.
                      ⚠️ Si contano a parte apposta: «va bene così» e «nessuno ha
                      ancora guardato» devono restare due risposte diverse
  * **ROTTO**       — 404, e nessuno l'ha deciso

Esce con 1 se resta anche un solo sprite rotto.

**Dove eravamo** (22/09/2026, primo giro): **333 URL rotti su 2684**, cioè 178 voci
del catalogo che mostravano un'immagine spezzata. La causa più grossa non era una
tabella incompleta: `_costruisci_indice()` ricavava lo slug dal **nome visualizzato**
(«Venusaur (Gigantamax Form)» → `venusaur-gigantamax-form`) mentre nella stessa voce
il catalogo aveva già scritto `venusaur-gmax`.
"""
import argparse
import io
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)
CATALOGO = os.path.join(RADICE, "data", "catalog", "pokemon.json")
# ⚠️ La cache sta **fuori dal repo**: è un esito di rete, non un dato del progetto, e
# committarla vorrebbe dire far credere a chi clona che quei 404 li ha misurati lui.
CACHE = os.path.join(tempfile.gettempdir(), "hub_sprite_cache.json")
UA = "personal-hub/controlla_sprite (uso personale, una HEAD per sprite)"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def voci_del_catalogo():
    """`[(etichetta, nome per l'API, slug del catalogo)]`, specie e forme annidate.

    Lo **slug** serve a riconoscere i ripieghi dichiarati: `SENZA_SPRITE_PDB` è
    indicizzata su quello, non sul nome che si legge a schermo.
    """
    cat = json.load(io.open(CATALOGO, encoding="utf-8"))
    fuori = []
    for chiave, v in cat.items():
        fuori.append((chiave, v.get("name") or chiave, chiave))
        for forma, dati in (v.get("forms") or {}).items():
            fuori.append((f"{chiave} / {forma}", forma, dati.get("slug") or ""))
    return fuori


def carica_cache(usa):
    if not usa or not os.path.exists(CACHE):
        return {}
    try:
        return json.load(io.open(CACHE, encoding="utf-8"))
    except Exception:
        return {}


def stato(url, cache, pausa):
    """Il codice HTTP dell'URL. Dalla cache se c'è, altrimenti una HEAD."""
    if url in cache:
        return cache[url]
    richiesta = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(richiesta, timeout=20) as r:
            cache[url] = r.status
    except urllib.error.HTTPError as e:
        cache[url] = e.code
    except Exception as e:
        # ⚠️ Un guasto di rete **non è** uno sprite rotto, e confonderli farebbe
        # scrivere nel backlog delle correzioni per sprite che stanno benissimo.
        cache[url] = f"rete: {type(e).__name__}"
    time.sleep(pausa)
    return cache[url]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solo-rotti", action="store_true",
                    help="stampa solo i 404, non il riassunto per categoria")
    ap.add_argument("--senza-cache", action="store_true",
                    help="ricontrolla tutto in rete, ignorando la cache")
    ap.add_argument("--limite", type=int, default=0,
                    help="ferma dopo N voci: per provare lo script senza il giro intero")
    ap.add_argument("--pausa", type=float, default=0.05,
                    help="secondi fra una richiesta e l'altra (default 0.05)")
    args = ap.parse_args()

    from blueprints.api_pokemon import SPRITE_SLUG_OVERRIDES, SENZA_SPRITE_PDB
    import app as modulo
    flask_app = modulo.create_app()
    flask_app.config["TESTING"] = True

    voci = voci_del_catalogo()
    if args.limite:
        voci = voci[:args.limite]
    cache = carica_cache(not args.senza_cache)
    print(f"Voci del catalogo: {len(voci)}")
    print(f"Cache: {CACHE} ({len(cache)} URL gia' noti)\n")

    # ⚠️ «Dichiarato» vuol dire **una riga in `SENZA_SPRITE_PDB`**, non un indovinello
    # su quanto si somigliano due slug. Il primo giro di questo script lo deduceva
    # confrontando le stringhe, ed era la stessa pigrizia che qui si paga sempre:
    # avrebbe chiamato «voluto» un ripiego che nessuno aveva deciso.
    dichiarati = set(SENZA_SPRITE_PDB)

    rotti, ok, dichiarati_visti, guasti = [], 0, [], []
    with flask_app.test_client() as c:
        with c.session_transaction() as s:
            s["username"], s["role"], s["user_id"] = "admin", "admin", 1
        for i, (etichetta, nome, slug) in enumerate(voci, 1):
            r = c.get("/api/pokemon/" + nome)
            d = r.get_json() or {}
            if not d.get("ok"):
                rotti.append((etichetta, "(l'API non la trova)", r.status_code))
                continue
            for quale in ("sprite", "sprite_hd"):
                url = d.get(quale)
                if not url:
                    continue
                st = stato(url, cache, args.pausa)
                if isinstance(st, str):
                    guasti.append((etichetta, url, st))
                elif st == 200:
                    # ⚠️ Un ripiego dichiarato **risponde 200**, perché punta alla
                    # voce base: contarlo fra gli «ok» e basta lo farebbe sparire.
                    # Sta bene, ma resta un'immagine che non è quella della forma.
                    if slug in dichiarati:
                        dichiarati_visti.append((etichetta, url))
                    else:
                        ok += 1
                else:
                    rotti.append((etichetta, url, st))
            if i % 100 == 0:
                json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))
                print(f"  … {i}/{len(voci)}", flush=True)
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

    print(f"\nURL che rispondono : {ok}")
    print(f"ROTTI (404)        : {len(rotti)}")
    print(f"guasti di rete     : {len(guasti)}")
    if not args.solo_rotti:
        print(f"ripieghi dichiarati : {len(dichiarati_visti)} "
              f"({len(dichiarati)} voci in SENZA_SPRITE_PDB)")

    if rotti:
        print("\n-- ROTTI: l'URL non esiste, e nessuno l'ha deciso --")
        for etichetta, url, st in rotti:
            print(f"  {etichetta:<46} {st}  {url.split('/')[-1] if '/' in url else url}")
    if guasti:
        print("\n-- non misurati: la rete non ha risposto, NON vuol dire rotti --")
        for etichetta, url, perche in guasti[:10]:
            print(f"  {etichetta:<46} {perche}")

    return 1 if rotti else 0


if __name__ == "__main__":
    sys.exit(main())
