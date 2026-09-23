#!/usr/bin/env python
"""Dichiara che una forma ha la stessa lista mosse della sua specie, con la fonte.

    python scripts/dichiara_eredita.py --forme "Squawkabilly (Blue Plumage)" ... \\
        --da squawkabilly-green-plumage --sorgente champions --fonte "..." [--dry-run]

Scrive nella sezione `eredita` di `data/catalog/moveset_integrazioni.json`, la stessa
delle 6 Mega di M-C del 21/09/2026, e poi fa riapplicare tutto da `salva_moveset()`.
Scritto il 23/09/2026 per i tre piumaggi di Squawkabilly entrati in M-C col confronto
delle fonti: il dump non ha righe `champions` per loro (Squawkabilly è della 1.2.0), e
senza lista il calcolatore mostrava «nessun elenco mosse».

⚠️ **Non è una deduzione, ed è per questo che `--fonte` è obbligatorio.** Una forma
eredita solo dove una fonte dice che la lista è la stessa: per i piumaggi, Bulbapedia dà
una lista unica senza sezioni per forma **e** il dump dà liste identiche in
Scarlatto/Violetto (47 mosse su 47, tutti e quattro). Una forma con mosse diverse —
Rotom, le Mega di Leggende Z-A — non passa di qui.

Si rifiuta se la forma non è nel catalogo, se la specie `--da` non ha la lista chiesta, o
se la forma ha già una lista sua (in quel caso vince quella, come per il dump).
Rieseguibile: una dichiarazione uguale viene contata e saltata.
"""
import argparse
import io
import json
import os
import sys
from datetime import datetime

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import (file_integrazioni_moveset, load_catalog, MOVESET_FILE,  # noqa: E402
                                salva_moveset)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--forme", nargs="+", required=True)
    ap.add_argument("--da", required=True, help="chiave della voce che ha la lista")
    ap.add_argument("--sorgente", default="champions")
    ap.add_argument("--fonte", required=True, help="chi dice che la lista è la stessa")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    forme_catalogo = {nf for v in load_catalog("pokemon").values() for nf in (v.get("forms") or {})}
    with io.open(MOVESET_FILE, encoding="utf-8") as f:
        voci = (json.load(f) or {}).get("voci") or {}
    percorso = file_integrazioni_moveset()
    with io.open(percorso, encoding="utf-8") as f:
        integrazioni = json.load(f)
    eredita = integrazioni.setdefault("eredita", {})

    problemi, nuove, gia = [], [], []
    lista = ((voci.get(args.da) or {}).get(args.sorgente) or {}).get("moves")
    if not lista:
        problemi.append(f"{args.da} non ha una lista `{args.sorgente}`: non si eredita niente")
    blocco = {"da": args.da, "fonte": args.fonte, "scritta_il": datetime.now().strftime("%Y-%m-%d")}
    for forma in args.forme:
        if forma not in forme_catalogo:
            problemi.append(f"{forma}: non è una forma del catalogo")
        elif ((voci.get(forma) or {}).get(args.sorgente) or {}).get("moves") and \
                (voci[forma][args.sorgente].get("eredita_da") != args.da):
            problemi.append(f"{forma}: ha già una lista `{args.sorgente}` sua, vince quella")
        elif (eredita.get(forma) or {}).get(args.sorgente, {}).get("da") == args.da:
            gia.append(forma)
        else:
            nuove.append(forma)

    for forma in nuove:
        print(f"+ {forma} eredita `{args.sorgente}` da {args.da} ({len(lista or {})} mosse)")
    if gia:
        print(f"= già dichiarate: {len(gia)}")
    for p in problemi:
        print("X " + p)
    if problemi:
        print(f"\n{len(problemi)} problemi: non scrivo niente.")
        return 1
    if not nuove:
        print("\nNiente da fare.")
        return 0
    if args.dry_run:
        print(f"\n--dry-run: {len(nuove)} dichiarazioni da scrivere.")
        return 0

    for forma in nuove:
        eredita.setdefault(forma, {})[args.sorgente] = dict(blocco)
    with io.open(percorso, "w", encoding="utf-8") as f:
        # indent=1 come `integra_moveset_bulbapedia.py`, che genera il file
        json.dump(integrazioni, f, ensure_ascii=False, indent=1)
    salva_moveset({})        # riapplica integrazioni, toppe ed eredità a tutto il file
    print(f"\nScritte {len(nuove)} dichiarazioni, moveset riapplicato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
