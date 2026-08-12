#!/usr/bin/env python
"""Aggiunge `stat_changes` alle mosse del catalogo, dal dump CSV di PokéAPI.

    python scripts/importa_variazioni_stat.py [--dry-run]

Di quante unità una mossa alza o abbassa una stat di chi la usa o di chi la subisce:
`{"spe": 2}` per Agilità, `{"atk": 1, "spe": 1}` per Dragodanza. Nel catalogo non
c'era: `data/catalog/moves.json` ha `bp`, `category`, `type`, `flags` e `desc`, e
delle 919 mosse **zero** dicevano quanti stage muovono.

Serve allo **Speed Tier**, che finora sapeva solo raddoppiare con Tailwind e dimezzare
con la paralisi: senza questo dato non si può rispondere a «dopo una Danza Draco chi
supero?» senza che sia l'utente a ricordarsi il numero.

FONTE — `move_meta_stat_changes.csv` del dump, 245 righe. È una **proprietà oggettiva
della mossa**, non una scelta di bilanciamento: vale qui la stessa eccezione che
`build_catalog.py` documenta per il flag `contact`, cioè si può aggiungere a una voce
curata perché non c'è niente da decidere. Verificato a campione contro il gioco:
Agilità +2, Danza Spada +2, Rock Polish +2, Dragodanza +1/+1, Shell Smash +2 su
atk/spa/spe e −1 su def/spd.

**Solo in aggiunta, mai in sovrascrittura**: una voce che ha già `stat_changes` non
viene toccata, così una correzione fatta a mano non viene cancellata al giro dopo.
Il catalogo si scrive con `salva_catalogo()`, che tiene la copia di sicurezza.
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
UA = {"User-Agent": "personal-hub/1.0 (import variazioni stat, uso personale)"}
EN = "9"

FILE_CSV = ["move_meta_stat_changes.csv", "move_names.csv"]

# Gli id stat del dump, con i nomi corti già usati da `base_stats` nel catalogo.
STAT_ID = {"1": "hp", "2": "atk", "3": "def", "4": "spa", "5": "spd", "6": "spe",
           "7": "accuracy", "8": "evasion"}


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="non scrive niente")
    args = ap.parse_args()

    scarica_cache()
    nomi_en = {r["move_id"]: r["name"] for r in leggi("move_names.csv")
               if r["local_language_id"] == EN}

    per_mossa = collections.defaultdict(dict)
    for r in leggi("move_meta_stat_changes.csv"):
        stat = STAT_ID.get(r["stat_id"])
        nome = nomi_en.get(r["move_id"])
        if stat and nome and int(r["change"]):
            per_mossa[nome][stat] = int(r["change"])

    mosse = voci_catalogo("moves")
    # Il catalogo scrive `Mud Slap` dove PokéAPI scrive `Mud-Slap`: stesso
    # riallineamento dell'import dei moveset, con lo stesso criterio — si accetta solo
    # quando, ignorando trattini e spazi, corrisponde a una sola chiave del catalogo.
    def piatto(s):
        return s.replace("-", " ").replace("  ", " ").strip().lower()

    per_forma = collections.defaultdict(list)
    for chiave in mosse:
        per_forma[piatto(chiave)].append(chiave)

    aggiunte, gia_presenti, riallineate, fuori_catalogo = 0, 0, [], []
    for nome, cambi in sorted(per_mossa.items()):
        chiave = nome
        if chiave not in mosse:
            candidati = per_forma.get(piatto(nome)) or []
            if len(candidati) != 1:
                fuori_catalogo.append(nome)
                continue
            chiave = candidati[0]
            riallineate.append((nome, chiave))
        if "stat_changes" in mosse[chiave]:
            gia_presenti += 1
            continue
        mosse[chiave]["stat_changes"] = cambi
        aggiunte += 1

    con_spe = {k: v["stat_changes"]["spe"] for k, v in mosse.items()
               if v.get("stat_changes", {}).get("spe", 0) > 0}

    print(f"\nMOSSE nel catalogo            {len(mosse)}")
    print(f"  con variazioni nel dump     {len(per_mossa)}")
    print(f"  aggiunte ora                {aggiunte}")
    print(f"  già presenti, non toccate   {gia_presenti}")
    if riallineate:
        print(f"  nomi riallineati            {len(riallineate)}: "
              + ", ".join(f"{a} -> {b}" for a, b in riallineate))
    if fuori_catalogo:
        print(f"  ⚠️ non risolte nel catalogo  {len(fuori_catalogo)}: {fuori_catalogo}")

    print(f"\nCHE ALZANO LA VELOCITÀ — {len(con_spe)}, quelle che servono allo Speed Tier:")
    for nome, stage in sorted(con_spe.items(), key=lambda x: (-x[1], x[0])):
        print(f"  +{stage}  {nome}")

    if args.dry_run:
        print("\ndry-run: niente scritto")
        return 0
    if not aggiunte:
        print("\nniente da aggiungere: il catalogo è già a posto")
        return 0
    salva_catalogo("moves", mosse)
    print(f"\nscritto data/catalog/moves.json  ({aggiunte} voci arricchite)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
