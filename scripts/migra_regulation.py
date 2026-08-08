#!/usr/bin/env python
"""Converte le regulation da "file con i dati" a "elenchi di nomi sul catalogo".

    python scripts/migra_regulation.py [--dry-run]

Prima: data/roster_ma.json + moves_ma.json + items_ma.json contenevano i dati.
Dopo:  data/regulations/ma.json contiene solo NOMI che puntano a data/catalog/.

I file vecchi NON vengono cancellati: restano come fallback finché non sei sicuro.
Crea anche la regulation `pokedex`, che non filtra niente e quindi vede tutto.
"""
import argparse
import io
import json
import os
import sys
from datetime import datetime

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RADICE, "data")
DIR_REG = os.path.join(DATA, "regulations")


def carica(percorso, default=None):
    try:
        with io.open(percorso, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def scrivi(percorso, dati, dry):
    if dry:
        return
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with io.open(percorso, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    catalogo = {n: carica(os.path.join(DATA, "catalog", f"{n}.json"))
                for n in ("pokemon", "moves", "abilities", "items")}
    if not catalogo["pokemon"]:
        print("data/catalog/ mancante: esegui prima scripts/build_catalog.py")
        return 1

    # Nomi validi: chiavi top-level, campo `name`, nomi delle forme e gli slug.
    # Gli slug servono perché il roster usa nomi in stile "Arcanine-Hisui", che nel
    # catalogo sta come "Hisuian Arcanine" ma con slug `arcanine-hisui`.
    nomi_pokemon = set()

    def registra(v):
        for x in (v.get("name"), v.get("slug")):
            if x:
                nomi_pokemon.add(x.lower())

    for chiave, voce in catalogo["pokemon"].items():
        nomi_pokemon.add(chiave.lower())
        registra(voce)
        for forma, dati in (voce.get("forms") or {}).items():
            nomi_pokemon.add(forma.lower())
            registra(dati)

    registro = carica(os.path.join(DATA, "regulations.json"), [])
    aggiornato = []
    for reg in registro:
        rid = reg["id"]
        roster = carica(os.path.join(DATA, reg.get("roster_file", "")), {})
        mosse = carica(os.path.join(DATA, reg.get("moves_file", "")), {}).get("moves", {})
        oggetti = carica(os.path.join(DATA, reg.get("items_file", "")), {}).get("items", {})

        filtro = {
            "id": rid,
            "label": reg.get("label", rid),
            "_commento": ("Solo elenchi di nomi: i dati stanno in data/catalog/. "
                          "null significa 'tutte le voci del catalogo'."),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "pokemon": sorted(roster.get("pokemon", [])),
            "moves": sorted(mosse),
            "items": sorted(oggetti),
            "abilities": None,          # globali, come oggi
            "mega_map": roster.get("mega_map", {}),
            "overrides": {},            # per differenze future rispetto al catalogo
        }
        percorso = os.path.join(DIR_REG, f"{rid}.json")
        scrivi(percorso, filtro, args.dry_run)

        mancanti = [n for n in filtro["pokemon"] if n.lower() not in nomi_pokemon]
        fuori_m = [n for n in filtro["moves"] if n not in catalogo["moves"]]
        fuori_o = [n for n in filtro["items"] if n not in catalogo["items"]]
        print(f"{rid}: {len(filtro['pokemon'])} pokemon, {len(filtro['moves'])} mosse, "
              f"{len(filtro['items'])} oggetti  -> regulations/{rid}.json")
        for etichetta, lista in (("pokemon", mancanti), ("mosse", fuori_m), ("oggetti", fuori_o)):
            if lista:
                print(f"    ATTENZIONE {len(lista)} {etichetta} non presenti nel catalogo: {lista[:8]}")

        reg = dict(reg)
        reg["filter_file"] = f"regulations/{rid}.json"
        aggiornato.append(reg)

    # regulation Pokedex: nessun filtro
    pokedex = {
        "id": "pokedex",
        "label": "Pokedex — tutto il catalogo",
        "_commento": "Nessun filtro: null ovunque significa tutte le voci del catalogo.",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "pokemon": None, "moves": None, "items": None, "abilities": None,
        "mega_map": {}, "overrides": {},
    }
    scrivi(os.path.join(DIR_REG, "pokedex.json"), pokedex, args.dry_run)
    if not any(r["id"] == "pokedex" for r in aggiornato):
        aggiornato.append({
            "id": "pokedex",
            "label": pokedex["label"],
            "filter_file": "regulations/pokedex.json",
            "mechanics": ["mega"],
        })
    forme = sum(len(v.get("forms") or {}) for v in catalogo["pokemon"].values())
    print(f"pokedex: {len(catalogo['pokemon'])} specie + {forme} forme, "
          f"{len(catalogo['moves'])} mosse, {len(catalogo['items'])} oggetti, "
          f"{len(catalogo['abilities'])} abilità  -> regulations/pokedex.json")

    scrivi(os.path.join(DATA, "regulations.json"), aggiornato, args.dry_run)
    print("\n" + ("dry-run: niente scritto" if args.dry_run
                  else "registro aggiornato; i file roster_/moves_/items_ restano come fallback"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
