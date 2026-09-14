#!/usr/bin/env python
"""Scrive su ogni voce del catalogo se il Pokémon **può ancora evolversi**.

    python scripts/importa_evoluzioni.py [--dry-run]

Serve all'Evolcondensa (14/09/2026). Alza Difesa e Difesa Speciale del 50%, **solo** a
chi non è completamente evoluto (Bulbapedia), e il catalogo non aveva nessun dato sulle
evoluzioni. Applicarla sempre avrebbe dato un numero sbagliato su Incineroar, senza
nessun avviso.

Il campo è `puo_evolversi`, e ha **tre** valori, non due:

- `true` / `false` — lo dice il dump di PokéAPI
- **assente** — non lo sappiamo: voce senza `slug` (le Mega inventate) o slug che il
  dump non ha. Il calcolatore la tratta come «non si attiva», **non** come `false`
  scritto: è la stessa regola di `moves: null`

⚠️ **Si decide per forma, non per specie.** Corsola di Kanto non si evolve e Corsola di
Galar sì (in Cursola); Pikachu sì e Pikachu Cosplay no; una Mega mai.
La regola sta in `pokeapi.evoluzioni()`, che usa anche l'import dal pannello del
catalogo: una specie importata da lì nasce già col campo.

Le forme **non ereditano** il valore dalla specie, al contrario di tipi e stat in
`api_pokemon.py`: ereditarlo darebbe `true` a tutte le Mega.

È rieseguibile: riscrive il campo quando il dump dice altro, e **dice cosa cambia**. La
copia di sicurezza la lascia `salva_catalogo()`, in `data/archive/`. Scarica
`pokemon_evolution.csv` nella cache del dump se manca.
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

import pokeapi
from blueprints.pokemon import load_catalog, salva_catalogo

FILE_EVOLUZIONI = "pokemon_evolution.csv"
FILE_SPECIE = "pokemon_species.csv"

# Casi noti, controllati a ogni giro: se uno sbaglia, il dump o la regola sono cambiati
# e non si scrive niente. Il valore atteso viene da Bulbapedia, non dal dump.
CANARINI = {
    "corsola": False, "corsola-galar": True,
    "pikachu": True, "pikachu-cosplay": False,
    "incineroar": False, "amoonguss": False, "foongus": True,
    "venusaur-mega": False, "porygon2": True, "dusclops": True, "chansey": True,
    "farfetchd": False, "farfetchd-galar": True,
    "qwilfish": False, "qwilfish-hisui": True,
    "pumpkaboo-average": True, "gourgeist-average": False,
    "eevee": True, "sneasel": True, "sneasel-hisui": True,
    "meltan": True, "melmetal": False,
}


def voci_con_slug(catalogo):
    """`(nome, voce, slug)` per specie e forme annidate, slug compreso quando manca."""
    for chiave, dati in catalogo.items():
        yield chiave, dati, dati.get("slug")
        for nome_forma, forma in (dati.get("forms") or {}).items():
            yield nome_forma, forma, forma.get("slug")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    mancanti = [f for f in ("pokemon.csv", FILE_SPECIE, FILE_EVOLUZIONI)
                if not os.path.exists(pokeapi.percorso(f))
                or os.path.getsize(pokeapi.percorso(f)) == 0]
    if mancanti:
        print("Scarico dal dump: " + ", ".join(mancanti))
        pokeapi.scarica_mancanti(mancanti)

    catalogo = load_catalog("pokemon")
    if not catalogo:
        print("Catalogo vuoto o illeggibile: non tocco niente.")
        return 1

    esito, senza_righe = pokeapi.evoluzioni()

    problemi = []
    for slug, atteso in CANARINI.items():
        if slug not in esito:
            problemi.append(f"canarino «{slug}»: il dump non ha questo slug")
        elif esito[slug] is not atteso:
            problemi.append(f"canarino «{slug}»: il dump dice {esito[slug]}, atteso {atteso}")
    if senza_righe:
        problemi.append(f"{len(senza_righe)} specie (id {', '.join(senza_righe)}) hanno "
                        f"un'evoluzione in {FILE_SPECIE} ma nessuna riga in "
                        f"{FILE_EVOLUZIONI}: vanno guardate e scritte in "
                        "EVOLUZIONI_FUORI_DAL_DUMP, in pokeapi.py")

    conta = collections.Counter()
    cambi, ignote = [], []
    for nome, voce, slug in voci_con_slug(catalogo):
        if not slug or slug not in esito:
            ignote.append(f"{nome} ({'senza slug' if not slug else 'slug ' + slug + ' non nel dump'})")
            if "puo_evolversi" in voce:
                problemi.append(f"{nome}: ha puo_evolversi={voce['puo_evolversi']} ma il "
                                "dump non lo conferma. Non lo tolgo alla cieca.")
            continue
        nuovo = esito[slug]
        conta[nuovo] += 1
        vecchio = voce.get("puo_evolversi")
        if vecchio is None:
            conta["nuovi"] += 1
        elif vecchio is not nuovo:
            cambi.append(f"{nome}: {vecchio} -> {nuovo}")
        voce["_nuovo_puo_evolversi"] = nuovo

    print(f"voci con esito dal dump: {conta[True] + conta[False]} "
          f"(si evolvono {conta[True]}, no {conta[False]}), di cui nuove {conta['nuovi']}")
    print(f"voci senza esito (campo lasciato assente): {len(ignote)}")
    for riga in ignote:
        print("  ? " + riga)
    for riga in cambi:
        print("  ~ " + riga)
    for riga in problemi:
        print("X " + riga)

    da_scrivere = conta["nuovi"] + len(cambi)
    for _, voce, _ in voci_con_slug(catalogo):
        nuovo = voce.pop("_nuovo_puo_evolversi", None)
        if nuovo is not None and not problemi and not args.dry_run:
            voce["puo_evolversi"] = nuovo

    if problemi:
        print(f"\n{len(problemi)} problemi: non scrivo niente.")
        return 1
    if not da_scrivere:
        print("\nNiente da fare: il catalogo e' gia' allineato al dump.")
        return 0
    if args.dry_run:
        print(f"\n--dry-run: {da_scrivere} voci da scrivere, file non toccato.")
        return 0

    salva_catalogo("pokemon", catalogo)
    print(f"\nScritte {da_scrivere} voci in data/catalog/pokemon.json "
          "(copia precedente in data/archive/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
