#!/usr/bin/env python
"""Riporta le Mega del catalogo alle BASE STAT, e toglie i tre doppioni top-level.

    python scripts/deconverti_mega_catalogo.py [--dry-run]

Le Mega nel catalogo non avevano un bonus: avevano le **stat di Lv.50 già
calcolate** (IV 31, 0 SP) salvate dentro `base_stats`, mentre tutto il resto del
catalogo tiene le base vere. Con la formula del progetto

    (2·base + 31) · 50 // 100  =  base + 15

la conversione si traduce esattamente in **+75 HP e +20 su ogni altra stat**,
ed è per questo che 95 Mega su 101 avevano +75 HP rispetto alla propria specie
base — nel gioco una Mega non cambia mai gli HP.

Cosa fa lo script:

1. **deconverte** ogni forma Mega con `hp == hp_della_base + 75`: `hp − 75`,
   `− 20` sulle altre cinque. Aritmetica esatta e reversibile
2. **rimuove** le tre chiavi top-level `mega-banette`, `mega-chimecho` e
   `mega-crabominable`: ognuna è un doppione della forma annidata nella specie
   base, e due delle tre contengono pure valori sbagliati. La rimozione avviene
   solo dopo aver verificato che la forma annidata esista

Non tocca `Mega Floette` (l'unica già corretta), `Mega Zygarde` (rotta a sé) né il
vecchio `data/pokemon_catalog.json`, che resta come fallback.

⚠️ La firma `+75 HP` individua le voci convertite **specie per specie, non stat per
stat**: su `Mega Froslass` cinque valori su sei erano convertiti e la Velocità no,
quindi la regola in blocco le ha tolto 20 di troppo. Corretta a mano subito dopo
(base 120). Se rispunta un caso simile, il segnale è il confronto con la specie base.

Il salvataggio passa da `salva_catalogo()`, quindi lascia la copia a scorrimento
in `data/archive/catalog_pokemon_pre-salvataggio.json`; in più questo script
scrive una copia dedicata `catalog_pokemon_pre-mega-deconv.json`.
"""
import argparse
import io
import json
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from blueprints.pokemon import voci_catalogo, salva_catalogo, _archive_dir  # noqa: E402

STAT = ("hp", "atk", "def", "spa", "spd", "spe")
DELTA_HP = 75
DELTA_ALTRE = 20

# Doppioni: chiave top-level -> nome della forma annidata che la sostituisce.
DOPPIONI = {
    "mega-banette": "Mega Banette",
    "mega-chimecho": "Mega Chimecho",
    "mega-crabominable": "Mega Crabominable",
}


def e_mega(nome):
    """Vero solo per le Mega vere: "Meganium" non ha lo spazio, e non entra."""
    n = str(nome).lower()
    return n.startswith("mega ") or n.startswith("mega-")


def deconverti(bs):
    return {s: bs[s] - (DELTA_HP if s == "hp" else DELTA_ALTRE) for s in STAT}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    catalogo = voci_catalogo("pokemon")
    if not catalogo:
        print("Catalogo vuoto o illeggibile: non tocco niente.")
        return 1

    fatte, saltate = [], []
    for chiave, voce in catalogo.items():
        base = voce.get("base_stats") or {}
        for nome_forma, forma in (voce.get("forms") or {}).items():
            if not e_mega(nome_forma):
                continue
            bs = forma.get("base_stats") or {}
            if not all(s in bs for s in STAT) or "hp" not in base:
                saltate.append((nome_forma, "stat incomplete"))
                continue
            # La firma `+75 HP` va cercata contro **tutte le forme della specie**, non
            # solo contro la voce di testa. `Mega Zygarde` sembrava «rotta a sé» per
            # questo: ha 291 HP e Zygarde 50% ne ha 108, ma la `Zygarde (Complete
            # Forme)` ne ha **216**, e 216 + 75 = 291. Era convertita a partire da
            # quella, non dal 50% — nessuna anomalia, solo il confronto sbagliato.
            candidate = [base["hp"]] + [
                (f.get("base_stats") or {}).get("hp")
                for n, f in (voce.get("forms") or {}).items()
                if not e_mega(n) and (f.get("base_stats") or {}).get("hp") is not None
            ]
            if bs["hp"] - DELTA_HP not in candidate:
                saltate.append((nome_forma,
                                f"hp {bs['hp']} non è +{DELTA_HP} su nessuna forma "
                                f"della specie {sorted(set(candidate))}: non convertita"))
                continue
            nuovo = deconverti(bs)
            if any(v < 1 for v in nuovo.values()):
                saltate.append((nome_forma, "la deconversione darebbe stat < 1"))
                continue
            fatte.append((nome_forma, dict(bs), nuovo))
            if not args.dry_run:
                forma["base_stats"] = nuovo

    rimosse, tenute = [], []
    for chiave, nome_forma in DOPPIONI.items():
        if chiave not in catalogo:
            continue
        # rimuovo solo se la forma annidata che la sostituisce esiste davvero
        esiste = any(nome_forma in (v.get("forms") or {}) for v in catalogo.values())
        if esiste:
            rimosse.append((chiave, nome_forma))
            if not args.dry_run:
                del catalogo[chiave]
        else:
            tenute.append((chiave, f"la forma annidata «{nome_forma}» non esiste"))

    print(f"Mega deconvertite : {len(fatte)}")
    for nome, prima, dopo in fatte:
        a = "/".join(str(prima[s]) for s in STAT)
        b = "/".join(str(dopo[s]) for s in STAT)
        print(f"  {nome:<26} {a:>26}  ->  {b}")

    print(f"\nDoppioni top-level rimossi : {len(rimosse)}")
    for chiave, nome in rimosse:
        print(f"  {chiave:<20} sostituita dalla forma «{nome}»")

    if saltate or tenute:
        print(f"\nLasciate stare : {len(saltate) + len(tenute)}")
        for nome, perche in saltate + tenute:
            print(f"  {nome:<26} {perche}")

    if args.dry_run:
        print("\n--dry-run: niente scritto su disco.")
        return 0

    copia = os.path.join(_archive_dir(), "catalog_pokemon_pre-mega-deconv.json")
    if not os.path.exists(copia):
        with io.open(os.path.join(RADICE, "data", "catalog", "pokemon.json"), encoding="utf-8") as f:
            with io.open(copia, "w", encoding="utf-8") as g:
                g.write(f.read())
        print(f"\nCopia di sicurezza: {copia}")
    else:
        print(f"\nCopia di sicurezza già presente, non la sovrascrivo: {copia}")

    salva_catalogo("pokemon", catalogo)
    print(f"Scritto data/catalog/pokemon.json — {len(catalogo)} voci.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
