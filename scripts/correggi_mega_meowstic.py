#!/usr/bin/env python
"""Mega Meowstic (Female) aveva le base stat della forma **non** Mega.

    python scripts/correggi_mega_meowstic.py [--dry-run]

Trovato il 21/09/2026 andando a cercare perché le due Mega Meowstic fossero le uniche
due voci del catalogo senza `slug`. Lo slug nel dump c'è — `meowstic-female-mega` — ma
`aggiungi_slug_forme.py` si rifiuta di scriverlo finché le sei base stat non combaciano
**esatte**, ed è il verso giusto: uno slug plausibile ma sbagliato non darebbe un
errore, darebbe l'elenco mosse di un altro Pokémon. Non combaciavano perché la voce era
rimasta a **466**, cioè al totale di Meowstic femmina normale: la conversione a Mega non
le era mai stata applicata. Il maschio invece era già giusto, a 566.

**Tre fonti indipendenti**, cercate il 21/09/2026 su richiesta di Davide:

- il **dump di PokéAPI**: `meowstic-female-mega` ha 74/48/76/143/101/124, cioè gli
  stessi valori di `meowstic-male-mega`
- **Pokémon Database** (`pokemondb.net/pokedex/meowstic`): Meowstic maschio e femmina
  hanno le **stesse** base stat (466) e differiscono per abilità e aspetto, non per
  statistiche; e le due Mega condividono i valori potenziati, 566
- **RotomLabs**, che ha una pagina apposta per la Mega femmina
  (`rotomlabs.net/dex/legends-z-a/meowstic/mega-female`): 74/48/76/143/101/124, 566

⚠️ **Non scrive alla cieca.** Si rifiuta, e non tocca niente, se la voce non ha
esattamente i valori vecchi attesi (o già quelli nuovi, e allora lo dice e non fa
nulla), se i valori nuovi non combaciano con quelli che il dump dà per lo slug, o se non
combaciano con quelli della Mega maschio già nel catalogo. La copia di sicurezza la
lascia `salva_catalogo()`, in `data/archive/`.

Dopo questo script, nell'ordine:

    python scripts/aggiungi_slug_forme.py
    python scripts/importa_mosse_specie.py
    python scripts/allinea_mosse_regulation.py
"""
import argparse
import collections
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import pokeapi                                                      # noqa: E402
from blueprints.pokemon import load_catalog, salva_catalogo         # noqa: E402

SPECIE = "meowstic-male"
FEMMINA = "Mega Meowstic (Female)"
MASCHIO = "Mega Meowstic (Male)"
SLUG_FEMMINA = "meowstic-female-mega"

# I valori che la voce deve avere **prima**: sono quelli di Meowstic femmina normale.
VECCHI = {"hp": 74, "atk": 48, "def": 76, "spa": 83, "spd": 81, "spe": 104}
# E quelli che deve avere dopo, confermati dalle tre fonti del docstring.
NUOVI = {"hp": 74, "atk": 48, "def": 76, "spa": 143, "spd": 101, "spe": 124}


def stat_del_dump(slug):
    """Le sei base stat che il dump dà per uno slug, con le chiavi del catalogo."""
    ids = {r["identifier"]: r["id"] for r in pokeapi.leggi("pokemon.csv")}
    if slug not in ids:
        return None
    ordine = {r["id"]: r["identifier"] for r in pokeapi.leggi("stats.csv")}
    fuori = collections.defaultdict(dict)
    for r in pokeapi.leggi("pokemon_stats.csv"):
        chiave = pokeapi.STAT_CATALOGO.get(ordine.get(r["stat_id"]))
        if chiave:
            fuori[r["pokemon_id"]][chiave] = int(r["base_stat"])
    return fuori.get(ids[slug])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    mancanti = pokeapi.file_mancanti()
    if mancanti:
        print("Il dump non e' in cache: manca " + ", ".join(mancanti))
        return 1

    catalogo = load_catalog("pokemon")
    specie = catalogo.get(SPECIE)
    if not specie:
        print(f"La specie «{SPECIE}» non e' nel catalogo.")
        return 1
    forme = specie.get("forms") or {}
    femmina, maschio = forme.get(FEMMINA), forme.get(MASCHIO)
    if not femmina or not maschio:
        print(f"Manca una delle due forme sotto «{SPECIE}»: "
              f"{FEMMINA if not femmina else MASCHIO}")
        return 1

    attuali = dict(femmina.get("base_stats") or {})
    if attuali == NUOVI:
        print(f"= «{FEMMINA}» ha gia' i valori di Champions: {NUOVI} (tot {sum(NUOVI.values())})")
        print("  niente da fare.")
        return 0
    if attuali != VECCHI:
        print(f"⚠️  «{FEMMINA}» non ha i valori attesi e non si tocca.")
        print(f"    attesi prima: {VECCHI}")
        print(f"    trovati:      {attuali}")
        return 1

    # Le due reti: il dump e la Mega maschio devono dire la stessa cosa.
    dal_dump = stat_del_dump(SLUG_FEMMINA)
    if dal_dump != NUOVI:
        print(f"⚠️  Il dump non conferma: «{SLUG_FEMMINA}» ha {dal_dump}, non {NUOVI}.")
        return 1
    del_maschio = dict(maschio.get("base_stats") or {})
    if del_maschio != NUOVI:
        print(f"⚠️  La Mega maschio nel catalogo ha {del_maschio}, non {NUOVI}: "
              "prima va capito quale delle due sbaglia.")
        return 1

    print(f"«{FEMMINA}»")
    for k in ("hp", "atk", "def", "spa", "spd", "spe"):
        segno = "" if VECCHI[k] == NUOVI[k] else f"   <- {VECCHI[k]} -> {NUOVI[k]}"
        print(f"   {k:4s} {NUOVI[k]:4d}{segno}")
    print(f"   totale {sum(VECCHI.values())} -> {sum(NUOVI.values())}")
    print("   confermato dal dump (meowstic-female-mega), da Pokémon Database "
          "e da RotomLabs")

    if args.dry_run:
        print("\n--dry-run: niente scritto.")
        return 0

    femmina["base_stats"] = dict(NUOVI)
    salva_catalogo("pokemon", catalogo)
    print("\nScritto in data/catalog/pokemon.json (copia precedente in data/archive/).")
    print("Ora: aggiungi_slug_forme.py, poi importa_mosse_specie.py, poi "
          "allinea_mosse_regulation.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
