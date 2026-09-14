#!/usr/bin/env python
"""Integra da Bulbapedia la lista `champions` di voci che il dump di PokéAPI non ha.

    python scripts/integra_moveset_bulbapedia.py --voci pawmot [--dry-run]

Decisione di Davide del 14/09/2026, **per Pawmot**. Il moveset di Champions di PokéAPI
arriva a Regulation M-B e non ha la versione 1.2.0: Pawmot è nei roster di MA e MB, ed è
in Champions dalla 1.2.0, ma a schermo aveva l'avviso giallo «nessun elenco mosse».
`scripts/verifica_moveset.py` ne ha trovate 26 così; si integrano **solo le voci
nominate**, una decisione alla volta, non tutte in blocco.

Dove scrive, e perché in due posti:

- `data/catalog/moveset_integrazioni.json` — **il dato curato**, con la fonte, la pagina
  e la versione. È lui la verità: `pokemon_moves.json` lo rigenerano
  `importa_mosse_specie.py` e l'import dal pannello, e tutti e due riapplicano le
  integrazioni con `applica_integrazioni_moveset()`. Copia di sicurezza in `data/archive/`
- `data/catalog/pokemon_moves.json` — subito, così l'app la vede senza rigenerare niente

Si **rifiuta** di scrivere, e non scrive niente, se:

- la voce non è nel catalogo, o nessun blocco di Bulbapedia le corrisponde
- il dump ha **già** una lista `champions` per quella voce: lì vince il dump
- anche **una sola** mossa di Bulbapedia non corrisponde a una mossa del catalogo. Una
  mossa sconosciuta non darebbe errore, sparirebbe dalla tendina

Il metodo di ogni mossa è `train`, l'unico di Champions, come nel dump. Legge le pagine
dalla cache di `verifica_moveset.py` (le scarica se mancano).
"""
import argparse
import json
import os
import shutil
import sys
import time

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import verifica_moveset as V  # noqa: E402
from blueprints.pokemon import (load_catalog, MOVESET_FILE,  # noqa: E402
                                file_integrazioni_moveset, applica_integrazioni_moveset,
                                _archive_dir)


def trova_blocco(catalogo, titoli, voce_cercata):
    """`(titolo, sezione, versione, mosse)` del blocco che appartiene alla voce, o `None`."""
    specie = V.indice_specie(catalogo)
    trovati = []
    for titolo in titoli:
        nome_specie = titolo.split(" (Pokémon)")[0]
        chiavi = specie.get(V.chiave_confronto(nome_specie), [])
        if len(chiavi) != 1:
            continue
        cand = V.candidati(catalogo, chiavi[0])
        if voce_cercata not in {n for n, _, _ in cand}:
            continue
        testo = V.testo_pagina(titolo, False)
        if testo is None:
            continue
        versione = (V.VERSIONE.search(testo) or [None, None])[1]
        for sezione, mosse in V.blocchi(testo):
            voce, _ = V.risolvi_blocco(nome_specie, sezione, cand)
            if voce == voce_cercata:
                trovati.append((titolo, sezione, versione, mosse))
    return trovati


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--voci", required=True,
                    help="chiavi del catalogo (o nomi di forma) separate da virgola")
    ap.add_argument("--dry-run", action="store_true", help="dice cosa farebbe e non scrive")
    args = ap.parse_args()
    richieste = [v.strip() for v in args.voci.split(",") if v.strip()]

    catalogo = load_catalog("pokemon")
    moveset_doc = json.load(open(MOVESET_FILE, encoding="utf-8"))
    moveset = moveset_doc.get("voci") or {}
    mosse_cat = load_catalog("moves")
    nomi_mosse = {V.chiave_confronto(k): k for k in mosse_cat}
    for k, v in mosse_cat.items():
        if v.get("nome_en"):
            nomi_mosse.setdefault(V.chiave_confronto(v["nome_en"]), k)
    titoli = V.elenco_pagine(False)

    percorso = file_integrazioni_moveset()
    try:
        documento = json.load(open(percorso, encoding="utf-8"))
    except (OSError, ValueError):
        documento = {"_meta": {
            "spiegazione": ("Liste di mosse che il dump di PokéAPI non ha, integrate a mano "
                            "da un'altra fonte. Le applica applica_integrazioni_moveset() in "
                            "blueprints/pokemon.py; dove il dump ha una lista sua, vince il dump."),
            "scritto_da": "scripts/integra_moveset_bulbapedia.py"}, "voci": {}}

    problemi, nuove = [], {}
    for voce in richieste:
        in_catalogo = voce in catalogo or any(voce in (d.get("forms") or {}) for d in catalogo.values())
        if not in_catalogo:
            problemi.append(f"{voce}: non è nel catalogo")
            continue
        lista_dump = (moveset.get(voce) or {}).get("champions")
        if lista_dump and not lista_dump.get("fonte"):
            problemi.append(f"{voce}: il dump ha già la sua lista champions "
                            f"({len(lista_dump.get('moves') or {})} mosse). Vince il dump.")
            continue
        blocchi = trova_blocco(catalogo, titoli, voce)
        if len(blocchi) != 1:
            problemi.append(f"{voce}: {len(blocchi)} blocchi di Bulbapedia le corrispondono, ne serve uno")
            continue
        titolo, sezione, versione, mosse = blocchi[0]
        ignote = sorted(m for m in mosse if V.chiave_confronto(m) not in nomi_mosse)
        if ignote:
            problemi.append(f"{voce}: mosse di Bulbapedia che il catalogo non conosce: {ignote}")
            continue
        scaricata = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(V.file_pagina(titolo))))
        nuove[voce] = {"champions": {
            "fonte": "bulbapedia",
            "pagina": titolo + (f" / {sezione}" if sezione else ""),
            "versione": versione,
            "scaricata_il": scaricata,
            "moves": {nomi_mosse[V.chiave_confronto(m)]: "train" for m in sorted(mosse)},
        }}
        print(f"+ {voce}: {len(mosse)} mosse da «{titolo}»"
              f"{' / ' + sezione if sezione else ''}, in Champions dalla versione {versione}")

    for riga in problemi:
        print("X " + riga)
    if problemi:
        print(f"\n{len(problemi)} problemi: non scrivo niente.")
        return 1
    if args.dry_run:
        print(f"\n--dry-run: {len(nuove)} voci da integrare, nessun file toccato.")
        return 0

    if os.path.exists(percorso):
        shutil.copy(percorso, os.path.join(_archive_dir(), "moveset_integrazioni_pre-salvataggio.json"))
    documento["voci"].update(nuove)
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(documento, f, ensure_ascii=False, indent=1)

    applicate, superate = applica_integrazioni_moveset(moveset)
    moveset_doc["voci"] = moveset
    moveset_doc.setdefault("_meta", {})["integrazioni"] = os.path.relpath(percorso, RADICE).replace("\\", "/")
    with open(MOVESET_FILE, "w", encoding="utf-8") as f:
        json.dump(moveset_doc, f, ensure_ascii=False, indent=1)
    print(f"\nScritte {len(nuove)} integrazioni in {os.path.relpath(percorso, RADICE)} "
          f"e applicate al moveset: {applicate}")
    if superate:
        print(f"⚠️  superate dal dump, da togliere: {superate}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
