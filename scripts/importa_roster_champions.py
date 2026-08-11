#!/usr/bin/env python
"""Allinea il roster di una regulation all'elenco dei Pokémon di Pokémon Champions.

    python scripts/importa_roster_champions.py --dry-run
    python scripts/importa_roster_champions.py --reg ma

Fonte: https://wiki.pokemoncentral.it/Elenco_dei_Pokémon_di_Pokémon_Champions
(versione 0.9.0-1.0.2 del gioco). Lo script scarica e legge la pagina da solo.

La wiki NON scrive il nome della forma: la distingue solo per **tipi** e **codice
sprite** dell'immagine. Questo script traduce ogni riga in un nome del catalogo
usando entrambi, e si ferma segnalando tutto ciò che non riesce a mappare, invece
di indovinare.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from html.parser import HTMLParser

import requests

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RADICE, "data")
URL = ("https://wiki.pokemoncentral.it/"
       "Elenco_dei_Pok%C3%A9mon_di_Pok%C3%A9mon_Champions")
UA = {"User-Agent": "Mozilla/5.0 (compatible; personal-hub/1.0)"}
CACHE = os.environ.get("POKEAPI_CACHE") or os.path.join(tempfile.gettempdir(), "pokeapi_csv")


class TabellaWiki(HTMLParser):
    """Estrae dalle tabelle: numero dex, nome, tipi e file dello sprite."""

    def __init__(self):
        super().__init__()
        self.righe, self._riga, self._cella, self._testo, self._img = [], None, None, [], ""
        self._in_tabella = self._in_cella = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._in_tabella = True
        elif tag == "tr" and self._in_tabella:
            self._riga = []
        elif tag in ("td", "th") and self._riga is not None:
            self._in_cella, self._testo, self._img = True, [], ""
        elif tag == "img" and self._in_cella and not self._img:
            self._img = (a.get("src") or "").split("/")[-1]

    def handle_data(self, dato):
        if self._in_cella:
            self._testo.append(dato.strip())

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cella:
            self._riga.append((" ".join(t for t in self._testo if t).strip(), self._img))
            self._in_cella = False
        elif tag == "tr" and self._riga is not None:
            self.righe.append(self._riga)
            self._riga = None
        elif tag == "table":
            self._in_tabella = False


def scarica_elenco():
    r = requests.get(URL, headers=UA, timeout=60)
    r.raise_for_status()
    p = TabellaWiki()
    p.feed(r.text)
    fuori = []
    for celle in p.righe:
        testi = [t for t, _ in celle]
        if len(celle) < 4 or not re.match(r"^#\d{4}$", testi[1] if len(testi) > 1 else ""):
            continue
        sprite = next((img for _, img in celle if img), "")
        sprite = re.sub(r"^\d+px-", "", sprite).replace(".png", "")
        fuori.append({"dex": int(testi[1][1:]), "nome": testi[3],
                      "tipi": [t for t in testi[4:] if t], "sprite": sprite})
    return fuori

# Suffisso dello sprite della wiki -> pezzo di nome della forma nel catalogo.
# Il significato dipende dal Pokémon: 'G' è Galar per Slowbro ma Gelo per Rotom.
SUFFISSI = {
    26:  {"A": "Alolan Raichu"},
    38:  {"A": "Alolan Ninetales"},
    59:  {"":  None, "H": "Hisuian Arcanine"},
    80:  {"G": "Galarian Slowbro"},
    128: {"C": "Paldean Tauros (Combat Breed)", "I": "Paldean Tauros (Blaze Breed)",
          "A": "Paldean Tauros (Aqua Breed)"},
    157: {"H": "Hisuian Typhlosion"},
    199: {"G": "Galarian Slowking"},
    351: {"S": "Castform (Sunny Form)", "P": "Castform (Rainy Form)", "N": "Castform (Snowy Form)"},
    479: {"C": "Heat Rotom", "L": "Wash Rotom", "G": "Frost Rotom",
          "V": "Fan Rotom", "T": "Mow Rotom"},
    503: {"H": "Hisuian Samurott"},
    571: {"H": "Hisuian Zoroark"},
    618: {"G": "Galarian Stunfisk"},
    # In Champions il Floette presente è quello col Fiore Eterno (sprite ...0670E)
    670: {"E": "Eternal Flower Floette", "M": "Mega Floette"},
    # Lo sprite della Mega è "Minim0678M": Minim = maschio, quindi Mega maschile
    678: {"F": "Meowstic (Female)", "M": "Mega Meowstic (Male)"},
    681: {"S": "Aegislash (Blade Forme)"},
    706: {"H": "Hisuian Goodra"},
    711: {"S": "Gourgeist (Small)", "L": "Gourgeist (Large)", "XL": "Gourgeist (Super)"},
    713: {"H": "Hisuian Avalugg"},
    724: {"H": "Hisuian Decidueye"},
    745: {"N": "Lycanroc (Midnight Form)", "C": "Lycanroc (Dusk Form)"},
    877: {"V": "Morpeko (Hangry Mode)"},
    902: {"F": "Basculegion (Female)"},
    925: {"T": "Maushold (Family of Three)"},
    964: {"P": "Palafin (Hero Form)"},
}

# Forme puramente estetiche: stessi tipi e stesse stat, per il calcolatore sono
# la stessa voce. Le collassiamo sulla forma base invece di moltiplicare il roster.
SOLO_ESTETICHE = {666, 671, 676, 869}   # Vivillon, Florges, Furfrou, Alcremie


def leggi_csv(nome):
    with io.open(os.path.join(CACHE, nome), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def carica(percorso, default=None):
    try:
        with io.open(percorso, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reg", default="ma")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--elenco", action="store_true", help="stampa il roster risolto e basta")
    args = ap.parse_args()

    righe = scarica_elenco()
    if not righe:
        print("nessuna riga letta dalla wiki")
        return 1
    print(f"scaricate {len(righe)} righe da wiki.pokemoncentral.it")
    catalogo = carica(os.path.join(DATA, "catalog", "pokemon.json"), {})
    if not catalogo:
        print("manca data/catalog/pokemon.json — esegui prima build_catalog.py")
        return 1

    # Numero di Pokédex -> chiave di specie nel catalogo. Non basta l'identifier
    # della specie: per Meowstic, Aegislash, Lycanroc & co. il catalogo usa lo slug
    # del Pokémon *predefinito* (meowstic-male, aegislash-shield, ...).
    specie_per_dex = {int(r["id"]): r["identifier"] for r in leggi_csv("pokemon_species.csv")}
    default_per_dex = {}
    for r in leggi_csv("pokemon.csv"):
        if r["is_default"] == "1":
            default_per_dex[int(r["species_id"])] = r["identifier"]

    per_slug = {}
    for chiave, voce in catalogo.items():
        if voce.get("slug"):
            per_slug.setdefault(voce["slug"], chiave)
        per_slug.setdefault(chiave, chiave)
        if voce.get("name"):
            per_slug.setdefault(voce["name"].lower(), chiave)

    tutti_i_nomi = set()
    for voce in catalogo.values():
        if voce.get("name"):
            tutti_i_nomi.add(voce["name"])
        tutti_i_nomi.update(voce.get("forms") or {})

    risolti, irrisolti, estetiche_saltate = [], [], 0
    for r in righe:
        dex, nome, tipi = r["dex"], r["nome"], r["tipi"]
        pezzi = r["sprite"].split(str(dex).zfill(4))
        suffisso = pezzi[-1] if len(pezzi) > 1 else ""

        chiave_specie = None
        for slug in (default_per_dex.get(dex), specie_per_dex.get(dex)):
            if slug and per_slug.get(slug):
                chiave_specie = per_slug[slug]
                break
        if not chiave_specie or chiave_specie not in catalogo:
            irrisolti.append((nome, dex, suffisso, "specie assente dal catalogo"))
            continue
        voce_specie = catalogo[chiave_specie]
        forme = voce_specie.get("forms") or {}

        # 1) estetiche: tutte sulla forma base
        if dex in SOLO_ESTETICHE and suffisso:
            estetiche_saltate += 1
            continue

        # 2) forma nota per (dex, suffisso): ha la precedenza su tutto, perché
        #    copre anche i casi particolari come Mega Floette e Mega Meowstic
        atteso = SUFFISSI.get(dex, {}).get(suffisso)
        if atteso:
            # cerco fra TUTTI i nomi del catalogo: "Mega Floette" per esempio è una
            # forma di "Eternal Flower Floette", non della specie base Floette
            if atteso in tutti_i_nomi:
                risolti.append(atteso)
            else:
                irrisolti.append((nome, dex, suffisso, f"forma attesa non nel catalogo: {atteso}"))
            continue

        # 3) Mega — la wiki scrive "MegaVenusaur" attaccato. Non basta il prefisso
        #    del nome: "Meganium" è una specie vera e finiva qui dentro, risolta
        #    come "Mega Meganium". Il dato affidabile è il suffisso dello sprite,
        #    che per le Mega è M / MX / MY.
        if nome.startswith("Mega") and suffisso.startswith("M"):
            atteso_mega = "Mega " + nome[4:].strip()
            # nel catalogo esistono anche varianti tipo "Mega Absol Z": vince il nome esatto
            tutte = {**forme, **{n: v for n, v in
                                 ((k, v) for k, v in catalogo.items()) if n.startswith("Mega ")}}
            if atteso_mega in forme:
                risolti.append(atteso_mega)
                continue
            candidate = [f for f in forme if f.startswith("Mega ")]
            if nome.endswith((" X", " Y")):
                candidate = [f for f in candidate if f.endswith(" " + nome[-1])]
            if len(candidate) == 1:
                risolti.append(candidate[0])
            else:
                irrisolti.append((nome, dex, suffisso,
                                  f"cerco '{atteso_mega}', {len(candidate)} candidate: {candidate[:4]}"))
            continue

        # 4) niente suffisso -> specie base
        if not suffisso:
            risolti.append(voce_specie.get("name") or chiave_specie)
            continue

        # 5) ultimo tentativo: una sola forma con quei tipi
        candidate = [f for f, d in forme.items() if d.get("types") == tipi]
        if len(candidate) == 1:
            risolti.append(candidate[0])
        else:
            irrisolti.append((nome, dex, suffisso, f"tipi {tipi} -> {len(candidate)} candidate"))

    roster = sorted(set(risolti))
    print(f"righe wiki: {len(righe)}")
    print(f"  forme estetiche collassate sulla base: {estetiche_saltate}")
    print(f"  risolte: {len(risolti)}  ->  {len(roster)} nomi unici")
    print(f"  IRRISOLTE: {len(irrisolti)}")
    for n, d, s, motivo in irrisolti:
        print(f"    #{d:04d} {n:22s} suffisso={s!r:8s} {motivo}")
    if irrisolti:
        print("\nINTERROTTO: risolvi le voci sopra prima di scrivere il roster")
        return 1

    if args.elenco:
        for n in roster:
            print(n)
        return 0

    percorso_filtro = os.path.join(DATA, "regulations", f"{args.reg}.json")
    filtro = carica(percorso_filtro)
    if filtro is None:
        print(f"manca {percorso_filtro}")
        return 1

    prima = set(filtro.get("pokemon") or [])
    dopo = set(roster)
    print(f"\nregulation '{args.reg}': {len(prima)} -> {len(dopo)} Pokémon")
    print(f"  aggiunti ({len(dopo - prima)}): {sorted(dopo - prima)}")
    print(f"  rimossi  ({len(prima - dopo)}): {sorted(prima - dopo)}")

    if args.dry_run:
        print("\ndry-run: niente scritto")
        return 0

    filtro["pokemon"] = roster
    filtro["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    filtro["_fonte_roster"] = ("Elenco dei Pokémon di Pokémon Champions — "
                               "wiki.pokemoncentral.it, versione 0.9.0-1.0.2")
    with io.open(percorso_filtro, "w", encoding="utf-8") as f:
        json.dump(filtro, f, ensure_ascii=False, indent=2)
    print(f"\nscritto {percorso_filtro}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
