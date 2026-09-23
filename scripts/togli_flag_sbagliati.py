#!/usr/bin/env python
"""Toglie 23 flag di mossa che non hanno nessuna fonte, arrivati dal file storico di MA.

    python scripts/togli_flag_sbagliati.py [--dry-run]

Decisione di Davide del 23/09/2026. Trovati integrando i flag di Gen 8-9
(`integra_flag_mosse.py`, che aggiunge soltanto e quindi non poteva toglierli): il file
storico `data/moves_ma.json` aveva messo `contact` su mosse che non lo fanno — Stone
Edge, Rock Tomb, Seed Bomb, perfino Bulk Up, che è di stato — e `punch` su Storm Throw.
Nel calcolatore Unghiedure dava ×1.3 e Lanugine ×0.5 dove non dovevano, **senza errore**.

**La prova non è scritta qui, viene ricontrollata a ogni giro**, così uno sbaglio in
questo elenco non toglie un flag vero:

- per le mosse vecchie, il dump di PokéAPI (`move_flag_map.csv`) deve avere righe per
  quella mossa **e** non avere il flag. Se il dump non ha righe per la mossa, non prova
  niente, e lo script si ferma
- per le tre di Gen 9, che il dump non copre, l'infobox di Bulbapedia deve dire
  `touches=no` (la pagina in cache di `integra_flag_mosse.py`)
- per Storm Throw anche la pagina *Punching move* di Bulbapedia non deve elencarla

Le note di Champions (§5.2, `allinea_dati_mosse_champions.py`) non cambiano il contatto
di nessuna di queste. Se anche una sola prova manca non scrive **niente** ed esce con 1.
Rieseguibile; copia di sicurezza da `salva_catalogo()`.
"""
import argparse
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import voci_catalogo, salva_catalogo  # noqa: E402
from integra_flag_mosse import csv_dump, pagina, identificatore, flag_infobox, MOVELIST  # noqa: E402

DAL_DUMP = {
    "contact": ["Absorb", "Beak Blast", "Beat Up", "Bone Club", "Bulk Up", "Glacial Lance",
                "Grass Pledge", "Icicle Crash", "Metal Burst", "Mud Slap", "Pin Missile",
                "Rock Tomb", "Sacred Fire", "Seed Bomb", "Sky Attack", "Snarl",
                "Spirit Shackle", "Stone Edge", "Twineedle"],
    "punch": ["Storm Throw"],
}
DA_BULBAPEDIA = {"contact": ["Aqua Cutter", "Gigaton Hammer", "Mountain Gale"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    voci = voci_catalogo("moves")
    ids = {r["identifier"]: r["id"] for r in csv_dump("moves.csv")}
    nomi_flag = {r["id"]: r["identifier"] for r in csv_dump("move_flags.csv")}
    dump = {}
    for r in csv_dump("move_flag_map.csv"):
        dump.setdefault(r["move_id"], set()).add(nomi_flag[r["move_flag_id"]])
    pugni = {n.strip() for n in MOVELIST.findall(pagina("Punching move", False) or "")}

    da_togliere, gia, problemi = [], [], []
    for flag, mosse in DAL_DUMP.items():
        for m in mosse:
            i = ids.get(identificatore(m))
            if m not in voci:
                problemi.append(f"{m}: non e' nel catalogo")
            elif i not in dump:
                problemi.append(f"{m}: il dump non ha righe di flag, non prova niente")
            elif flag in dump[i]:
                problemi.append(f"{m}: il dump HA `{flag}`, non lo tolgo")
            elif flag == "punch" and m in pugni:
                problemi.append(f"{m}: Bulbapedia la elenca fra i pugni, non lo tolgo")
            elif flag in (voci[m].get("flags") or []):
                da_togliere.append((m, flag, "dump"))
            else:
                gia.append(m)
    for flag, mosse in DA_BULBAPEDIA.items():
        for m in mosse:
            infobox = flag_infobox(pagina(f"{m} (move)", False))
            if m not in voci:
                problemi.append(f"{m}: non e' nel catalogo")
            elif infobox is None:
                problemi.append(f"{m}: pagina Bulbapedia assente o senza infobox")
            elif flag in infobox:
                problemi.append(f"{m}: Bulbapedia dice `{flag}`, non lo tolgo")
            elif flag in (voci[m].get("flags") or []):
                da_togliere.append((m, flag, "Bulbapedia"))
            else:
                gia.append(m)

    for m, flag, fonte in da_togliere:
        print(f"- {m:16s} toglie `{flag}` (prova: {fonte})")
    if gia:
        print(f"= gia' senza: {len(gia)}")
    for p in problemi:
        print("X " + p)
    if problemi:
        print(f"\n{len(problemi)} problemi: non scrivo niente.")
        return 1
    if not da_togliere:
        print("\nNiente da fare.")
        return 0
    if args.dry_run:
        print(f"\n--dry-run: {len(da_togliere)} flag da togliere, file non toccato.")
        return 0
    for m, flag, _ in da_togliere:
        voci[m]["flags"] = [f for f in voci[m]["flags"] if f != flag]
    salva_catalogo("moves", voci)
    print(f"\nTolti {len(da_togliere)} flag da data/catalog/moves.json (copia in data/archive/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
