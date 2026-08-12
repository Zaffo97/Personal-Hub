#!/usr/bin/env python
"""Rende raggiungibile ogni Mega presente nel roster di una regulation.

    python scripts/completa_mega_map.py [--dry-run]

Una Mega finisce nel roster ma resta **irraggiungibile** se nessuna specie base la
punta nel `mega_map`: il team builder non la offre e il calcolatore non ci arriva.
Prima di questo script erano **1 in MA** e **17 in MB**.

Cosa fa, per ogni Mega del roster non ancora mappata:

1. deduce la specie base dal nome (`Mega Barbaracle` → `Barbaracle`, `Mega Raichu X`
   → `Raichu`) e **verifica che esista nel catalogo**: se non c'è, si ferma
2. se la base è già nel roster, aggiunge la voce al `mega_map` — nessun dato nuovo,
   solo il collegamento fra due nomi già verificati
3. se la base **non** è nel roster, la aggiunge **solo** per le regulation elencate in
   `AGGIUNGI_BASI`, cioè dove Davide ha deciso che ci deve stare

Il punto 3 è l'unico che cambia *cosa contiene* una regulation, e per questo non è
automatico: aggiungere una specie a un roster è una scelta di contenuto, non un dato
deducibile. L'11/08/2026 Davide ha deciso di popolare **MB**, che era rimasta un
segnaposto (MA più 16 Mega, con mosse, oggetti e `mega_map` identici a MA); il roster
di **MA** invece viene dalla wiki di Pokémon Central e non si tocca — lì lo script si
limita a collegare `Meowstic (Male)`, che era già dentro insieme alla sua Mega.

Copia di sicurezza in `data/archive/regulation_<id>_pre-mega-map.json`.
Rieseguibile: alla seconda esecuzione non trova più niente da fare.
"""
import argparse
import io
import json
import os
import re
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILTRI = os.path.join(RADICE, "data", "regulations")
CATALOGO = os.path.join(RADICE, "data", "catalog", "pokemon.json")
ARCHIVIO = os.path.join(RADICE, "data", "archive")

# regulation dove è consentito **aggiungere al roster** la specie base mancante
AGGIUNGI_BASI = {"mb"}
REGULATION = ("ma", "mb", "pokedex")


def nomi_catalogo():
    with open(CATALOGO, encoding="utf-8") as f:
        catalogo = json.load(f)
    nomi = set()
    for chiave, voce in catalogo.items():
        nomi.add(voce.get("name") or chiave)
        nomi.update((voce.get("forms") or {}).keys())
    return nomi


# Le Mega inventate che non seguono la regola del nome. Il catalogo scrive la forma
# come `<Specie> (<Forma> Form)`, queste come `Mega <Forma> <Specie>`: nessuna regola
# generale le lega, quindi stanno qui una per una invece di essere indovinate.
# Verificate contro i nomi veri del catalogo il 12/08/2026.
BASE_A_MANO = {
    # Curly e' la forma predefinita di Tatsugiri: nel catalogo e' la voce nuda.
    "Mega Curly Tatsugiri":    "Tatsugiri",
    "Mega Droopy Tatsugiri":   "Tatsugiri (Droopy Form)",
    "Mega Stretchy Tatsugiri": "Tatsugiri (Stretchy Form)",
    "Mega Original Magearna":  "Magearna (Original Color)",
}


def base_attesa(mega):
    """`Mega Raichu X` → `Raichu`; `Mega Meowstic (Male)` → `Meowstic (Male)`."""
    if mega in BASE_A_MANO:
        return BASE_A_MANO[mega]
    base = re.sub(r"^Mega ", "", mega)
    # `Z` insieme a X e Y: `Mega Absol Z` sta a `Absol` come `Mega Charizard X` sta a
    # `Charizard`. E' la stessa convenzione, non un caso nuovo.
    return re.sub(r" [XYZ]$", "", base)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra cosa farebbe senza scrivere niente")
    args = ap.parse_args()

    catalogo = nomi_catalogo()
    problemi, piano = [], {}

    for reg_id in REGULATION:
        percorso = os.path.join(FILTRI, f"{reg_id}.json")
        with open(percorso, encoding="utf-8") as f:
            filtro = json.load(f)
        # `pokemon: null` vuol dire "tutto il catalogo" — è la stessa convenzione che
        # `_load_roster()` usa nell'app. Senza questa riga `pokedex` risultava un
        # roster vuoto, quindi lo script non ci trovava nessuna Mega da collegare e
        # la sua `mega_map` restava a zero: il selettore Mega del team builder era
        # vuoto proprio sulla regulation di default del sito.
        roster = (list(filtro["pokemon"]) if filtro.get("pokemon") is not None
                  else sorted(catalogo))
        mega_map = filtro.get("mega_map") or {}
        mappate = {m for v in mega_map.values() for m in v}
        irraggiungibili = sorted(n for n in roster
                                 if n.startswith("Mega ") and n not in mappate)

        collega, aggiungi = [], []
        for mega in irraggiungibili:
            base = base_attesa(mega)
            if base not in catalogo:
                problemi.append(f"{reg_id}: '{mega}' → base '{base}' non è nel catalogo")
                continue
            if mega not in catalogo:
                problemi.append(f"{reg_id}: '{mega}' non è nel catalogo")
                continue
            if base in roster:
                collega.append((base, mega))
            elif reg_id in AGGIUNGI_BASI:
                aggiungi.append(base)
                collega.append((base, mega))
            else:
                problemi.append(
                    f"{reg_id}: '{mega}' → la base '{base}' non è nel roster e "
                    f"'{reg_id}' non è fra le regulation da popolare")
        if collega or aggiungi:
            piano[reg_id] = (percorso, filtro, roster, mega_map, collega, sorted(set(aggiungi)))

    if problemi:
        print("Mi fermo senza scrivere niente:")
        for p in problemi:
            print("  ⚠️ " + p)
        return 1
    if not piano:
        print("Niente da fare: ogni Mega nel roster è già raggiungibile.")
        return 0

    for reg_id, (_, _, roster, _, collega, aggiungi) in piano.items():
        print(f"--- {reg_id} ---")
        for base, mega in collega:
            nuova = " (specie aggiunta al roster)" if base in aggiungi else ""
            print(f"  {base:24s} → {mega}{nuova}")
        print(f"  totale: {len(collega)} collegamenti, {len(aggiungi)} specie aggiunte al roster")

    if args.dry_run:
        print("\n--dry-run: nessuna modifica.")
        return 0

    os.makedirs(ARCHIVIO, exist_ok=True)
    for reg_id, (percorso, filtro, roster, mega_map, collega, aggiungi) in piano.items():
        copia = os.path.join(ARCHIVIO, f"regulation_{reg_id}_pre-mega-map.json")
        with open(copia, "w", encoding="utf-8") as f:
            json.dump(filtro, f, ensure_ascii=False, indent=2)

        for base, mega in collega:
            mega_map.setdefault(base, [])
            if mega not in mega_map[base]:
                mega_map[base].append(mega)
            mega_map[base].sort()
        filtro["mega_map"] = dict(sorted(mega_map.items()))
        if aggiungi:
            filtro["pokemon"] = sorted(set(roster) | set(aggiungi))
        filtro["last_updated"] = "2026-08-11"

        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(filtro, f, ensure_ascii=False, indent=2)

        mappate = {m for v in filtro["mega_map"].values() for m in v}
        # Su `pokedex` il roster e' `null`, cioe' tutto il catalogo: qui va riusato
        # `roster`, che quel caso l'ha gia' risolto sopra. Leggere di nuovo
        # `filtro["pokemon"]` faceva `TypeError: 'NoneType' object is not iterable`
        # — e dopo che il file era gia' stato scritto, quindi il lavoro era fatto ma
        # la riga di riepilogo non arrivava mai.
        roster_finale = filtro["pokemon"] if filtro.get("pokemon") is not None else roster
        mega_roster = {n for n in roster_finale if n.startswith("Mega ")}
        print(f"{reg_id}: roster {len(roster_finale)} Pokémon, "
              f"Mega raggiungibili {len(mega_roster & mappate)}/{len(mega_roster)}, "
              f"copia in {os.path.relpath(copia, RADICE)}")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
