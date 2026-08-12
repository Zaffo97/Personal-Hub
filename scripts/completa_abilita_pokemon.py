#!/usr/bin/env python
"""Completa le abilità di ogni Pokémon del catalogo, dal dump CSV di PokéAPI.

    python scripts/completa_abilita_pokemon.py [--dry-run]

È il **prerequisito** della voce «ogni Pokémon deve mostrare solo le sue abilità»:
finché il catalogo è incompleto, stringere le tendine toglierebbe scelte legittime
invece di togliere rumore.

FONTE — `pokemon_abilities.csv` del dump, che include anche le **abilità nascoste**
(`is_hidden`). È lì che sta quasi tutto il buco: al catalogo manca Chlorophyll su
Venusaur, Solar Power su Charizard, Lightning Rod su Pikachu.

SOLO IN AGGIUNTA, MAI IN RIMOZIONE. Le abilità già presenti non vengono toccate né
riordinate, e quelle che PokéAPI non conosce **restano dove sono**: sono le abilità
inventate di Champions, e toglierle vorrebbe dire decidere che sono sbagliate. Le
nuove si accodano in ordine di slot ufficiale.

⚠️ Il backlog diceva che «le 238 specie con una sola abilità sono quasi certamente
incomplete». **È vero solo in parte**, e questo script lo dimostra invece di
presumerlo: dopo l'import restano 325 voci con una sola abilità, e 323 di quelle ce
l'hanno per davvero anche secondo PokéAPI — sono Mega e forme regionali, che di
abilità ne hanno una sola (Mega Venusaur ha solo Thick Fat). Il rapporto finale
stampa il conto, così la differenza è misurata e non dedotta.
"""
import argparse
import collections
import csv
import io
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import voci_catalogo, salva_catalogo  # noqa: E402

CACHE = os.path.join(RADICE, "data", "cache", "pokeapi_csv")
BASE_CSV = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
UA = {"User-Agent": "personal-hub/1.0 (completamento abilità, uso personale)"}
EN = "9"

FILE_CSV = ["pokemon.csv", "pokemon_abilities.csv", "ability_names.csv"]


def scarica_cache():
    import requests
    os.makedirs(CACHE, exist_ok=True)
    for f in FILE_CSV:
        p = os.path.join(CACHE, f)
        if os.path.exists(p) and os.path.getsize(p):
            continue
        r = requests.get(BASE_CSV + f, headers=UA, timeout=90)
        r.raise_for_status()
        io.open(p, "wb").write(r.content)
        print(f"scaricato {f}  {len(r.content) // 1024} KB")


def leggi(nome):
    with io.open(os.path.join(CACHE, nome), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def abilita_ufficiali():
    """slug -> elenco di abilità in ordine di slot, le nascoste comprese."""
    pokemon = {r["id"]: r["identifier"] for r in leggi("pokemon.csv")}
    nomi = {r["ability_id"]: r["name"] for r in leggi("ability_names.csv")
            if r["local_language_id"] == EN}
    per_slug = collections.defaultdict(list)
    for r in leggi("pokemon_abilities.csv"):
        slug, nome = pokemon.get(r["pokemon_id"]), nomi.get(r["ability_id"])
        if slug and nome:
            per_slug[slug].append((int(r["slot"]), nome))
    return {s: [n for _, n in sorted(v)] for s, v in per_slug.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="non scrive niente")
    args = ap.parse_args()

    scarica_cache()
    ufficiali = abilita_ufficiali()
    catalogo = voci_catalogo("pokemon")

    # Ogni voce del catalogo, specie e forme annidate, con la sua lista da modificare
    # sul posto: il dizionario e' lo stesso che finisce in salva_catalogo().
    voci = []
    for chiave, dati in catalogo.items():
        voci.append((dati.get("name") or chiave, dati))
        for nome_forma, forma in (dati.get("forms") or {}).items():
            voci.append((nome_forma, forma))

    # Ripara i doppioni di sola maiuscola, che una prima versione di questo script
    # ha creato prima che il confronto diventasse insensibile alle maiuscole. Tiene
    # sempre la **prima** occorrenza, cioe' quella che c'era gia' nel catalogo.
    ripuliti = []
    for nome, voce in voci:
        attuali = voce.get("abilities") or []
        viste, tenute = set(), []
        for a in attuali:
            if a.lower() in viste:
                ripuliti.append((nome, a))
                continue
            viste.add(a.lower())
            tenute.append(a)
        if len(tenute) != len(attuali):
            voce["abilities"] = tenute

    toccate, aggiunte, senza_fonte = 0, 0, []
    nascoste_note = []
    prima = collections.Counter()
    dopo = collections.Counter()
    for nome, voce in voci:
        attuali = list(voce.get("abilities") or [])
        prima[len(attuali)] += 1
        uff = ufficiali.get(voce.get("slug") or "")
        if not uff:
            senza_fonte.append(nome)
            dopo[len(attuali)] += 1
            continue
        # Confronto senza maiuscole: il catalogo scrive `Zero To Hero`, PokéAPI
        # `Zero to Hero`, e alla lettera sono due abilità diverse. Su Palafin la prima
        # esecuzione le ha aggiunte entrambe — un doppione creato dall'import.
        gia = {a.lower() for a in attuali}
        nuove = [a for a in uff if a.lower() not in gia]
        if nuove:
            voce["abilities"] = attuali + nuove
            toccate += 1
            aggiunte += len(nuove)
            if len(nascoste_note) < 8:
                nascoste_note.append((nome, attuali, nuove))
        dopo[len(voce.get("abilities") or [])] += 1

    # Quante voci restano con una sola abilita', e quante di quelle ce l'hanno davvero
    # anche secondo PokeAPI: e' la misura che dice se il prerequisito e' chiuso.
    una_sola = [(n, v) for n, v in voci if len(v.get("abilities") or []) == 1]
    una_sola_vera = [n for n, v in una_sola
                     if len(ufficiali.get(v.get("slug") or "", [])) == 1]

    print(f"\nVOCI DEL CATALOGO           {len(voci)} (specie + forme)")
    print(f"  completate ora            {toccate}  ->  +{aggiunte} abilità")
    print(f"  senza fonte ufficiale     {len(senza_fonte)}  (forme inventate: {', '.join(senza_fonte[:4])}…)")
    print("\n  esempi di completamento (quasi sempre l'abilità nascosta):")
    for nome, attuali, nuove in nascoste_note:
        print(f"    {nome:28s} {attuali}  +{nuove}")

    print(f"\n  abilità per voce   prima: {dict(sorted(prima.items()))}")
    print(f"                      dopo: {dict(sorted(dopo.items()))}")
    print(f"\n  restano con UNA sola abilità: {len(una_sola)}")
    print(f"    di cui ne hanno davvero una sola anche per PokéAPI: {len(una_sola_vera)}")
    print(f"    (sono Mega e forme regionali — Mega Venusaur ha solo Thick Fat)")
    print(f"    quindi i casi ancora dubbi sono {len(una_sola) - len(una_sola_vera)}")

    if ripuliti:
        print(f"\n  doppioni di sola maiuscola rimossi: {len(ripuliti)}")
        for nome, a in ripuliti:
            print(f"    {nome}: tolto «{a}»")

    if args.dry_run:
        print("\ndry-run: niente scritto")
        return 0
    if not toccate and not ripuliti:
        print("\nniente da aggiungere: il catalogo è già completo")
        return 0
    salva_catalogo("pokemon", catalogo)
    print(f"\nscritto data/catalog/pokemon.json  ({toccate} voci completate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
