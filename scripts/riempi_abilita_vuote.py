#!/usr/bin/env python
"""Dà le abilità alle voci del catalogo che le hanno **vuote**, prendendole dal dump.

    python scripts/riempi_abilita_vuote.py [--dry-run]

Decisione di Davide del 23/09/2026. Trovate dal pulsante «Aggiorna tutto dalla fonte» al
primo giro: 5 Mega di Regulation M-C — Absol Z, Garchomp Z, Lucario Z, Golisopod,
Baxcalibur — avevano `abilities: []`, e il dump aggiornato le ha. Confermate una per una
da Serebii («Mega Abilities» di Pokémon Champions): Sharpness, Levitate, Aura Guard, Tough
Claws, Thermal Exchange.

⚠️ **Tocca solo le liste vuote.** Una voce con abilità diverse dal dump non è un buco, è
quasi sempre una scelta curata (le Mega di Champions): quella la mostra il pulsante e non
la cambia nessuno script. Vuoto è diverso: non è una scelta, è un dato mancante.

⚠️ **Si ferma** se un'abilità del dump non ha una voce nel catalogo abilità con quel
`nome_en`: il legame fra Pokémon e abilità passa da lì, e un nome senza voce staccherebbe
il Pokémon dall'abilità **senza errore** (è successo a Mega Meganium). Rieseguibile; copia
di sicurezza da `salva_catalogo()`. Dopo, `controlla_abilita.py`.
"""
import argparse
import contextlib
import io
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import pokedex_aggiorna  # noqa: E402
from blueprints.pokemon import voci_catalogo, salva_catalogo, load_abilities  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    bc = pokedex_aggiorna._bc()          # lo stesso dump del pulsante, non una copia
    with contextlib.redirect_stdout(io.StringIO()):
        bc.scarica_cache()
    pid = {r["identifier"]: r["id"] for r in bc.leggi("pokemon.csv")}
    ab_en = {r["ability_id"]: r["name"] for r in bc.leggi("ability_names.csv")
             if r["local_language_id"] == bc.EN}
    dal_dump = {}
    for r in sorted(bc.leggi("pokemon_abilities.csv"), key=lambda r: int(r["slot"])):
        dal_dump.setdefault(r["pokemon_id"], []).append(ab_en.get(r["ability_id"], "?"))
    note = {(v.get("nome_en") or "").lower() for v in load_abilities()["abilities"].values()}

    catalogo = voci_catalogo("pokemon")
    voci = []
    for chiave, v in catalogo.items():
        voci.append((v.get("name") or chiave, v.get("slug") or chiave, v))
        voci += [(nf, f.get("slug"), f) for nf, f in (v.get("forms") or {}).items()]

    da_scrivere, problemi = [], []
    for nome, slug, voce in voci:
        if voce.get("abilities") != []:
            continue
        nuove = dal_dump.get(pid.get(slug or ""))
        if not nuove:
            problemi.append(f"{nome}: vuota anche nel dump, resta vuota")
            continue
        ignote = [a for a in nuove if a.lower() not in note]
        if ignote:
            problemi.append(f"{nome}: {', '.join(ignote)} non ha una voce nel catalogo abilità")
            continue
        da_scrivere.append((nome, voce, nuove))

    for nome, _, nuove in da_scrivere:
        print(f"+ {nome:22s} {', '.join(nuove)}")
    for p in problemi:
        print("X " + p)
    if any("non ha una voce" in p for p in problemi):
        print("\nAbilità senza voce: non scrivo niente.")
        return 1
    if not da_scrivere:
        print("\nNiente da fare: nessuna voce con le abilità vuote che il dump sappia riempire.")
        return 0
    if args.dry_run:
        print(f"\n--dry-run: {len(da_scrivere)} voci da riempire.")
        return 0
    for _, voce, nuove in da_scrivere:
        voce["abilities"] = nuove
    salva_catalogo("pokemon", catalogo)
    print(f"\nRiempite {len(da_scrivere)} voci (copia precedente in data/archive/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
