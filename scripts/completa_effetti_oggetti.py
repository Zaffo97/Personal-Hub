#!/usr/bin/env python
"""Dà un effetto al Plessimetro e ai quattro semi del terreno, che non ne avevano.

    python scripts/completa_effetti_oggetti.py [--dry-run]

Sono due dei «limiti dichiarati» del 14/09/2026 (BACKLOG §3), lasciati fuori da
`assegna_categorie_oggetti.py` perché il calcolatore non aveva dove metterli: il
Plessimetro voleva un campo «usi consecutivi», i semi un legame con la tendina del
terreno. Dal 23/09/2026 ci sono entrambi, quindi le voci possono avere un effetto.

Valori da Bulbapedia, una pagina per oggetto:

- **Plessimetro** (`Metronome`): «+819/4096 per ogni uso consecutivo precedente,
  fino a +100%», e nella pagina *Damage* sta fra i moltiplicatori *other*, cioè sul
  danno finale e non sulla potenza. `modifier` è il passo per uso, arrotondato come
  gli altri (819/4096 -> 0.2, quindi 1.2); il tetto ×2 sta nel motore.
- **Semi** (`Electric/Grassy/Misty/Psychic Seed`): col terreno giusto in campo, +1
  grado alla Difesa (Elettrico, Erboso) o alla Difesa Speciale (Psichico, Nebbioso).
  Qui `modifier` **non è un moltiplicatore**: è il numero di gradi, 1. Il terreno
  sta nel nome dell'effetto (`seed_<terreno>`), come il tipo in `boost_<tipo>`.

⚠️ **Non sovrascrive un oggetto curato.** Ogni voce deve trovarsi esattamente nello
stato di partenza scritto in `PARTENZA` (categoria, e nessun effetto): se ne trova
una diversa non scrive **niente** ed esce con 1. Rieseguibile: una voce già uguale
viene contata e saltata. La copia di sicurezza la lascia `salva_catalogo()`.

Riguarda solo `pokedex`: MA, MB e MC hanno i loro 58 oggetti e nessuno di questi.
"""
import argparse
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import voci_catalogo, salva_catalogo
from data import CATEGORIE_OGGETTI


def seme(terreno, stat):
    return {"category": "terrain", "effect": f"seed_{terreno}", "modifier": 1, "stat": stat}


ASSEGNAZIONI = {
    "Metronome":     {"category": "conditional", "effect": "metronome", "modifier": 1.2},
    "Electric Seed": seme("electric", "def"),
    "Grassy Seed":   seme("grassy", "def"),
    "Psychic Seed":  seme("psychic", "spd"),
    "Misty Seed":    seme("misty", "spd"),
}

# Lo stato in cui le voci sono state lasciate il 14/09/2026: solo la categoria.
PARTENZA = {
    "Metronome":     "other",
    "Electric Seed": "terrain",
    "Grassy Seed":   "terrain",
    "Psychic Seed":  "terrain",
    "Misty Seed":    "terrain",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    voci = voci_catalogo("items")
    if not voci:
        print("Catalogo oggetti vuoto o illeggibile: non tocco niente.")
        return 1

    da_scrivere, gia_fatte, problemi = [], [], []
    for nome, nuovo in ASSEGNAZIONI.items():
        voce = voci.get(nome)
        if voce is None:
            problemi.append(f"{nome}: non esiste nel catalogo")
            continue
        if nuovo["category"] not in CATEGORIE_OGGETTI:
            problemi.append(f"{nome}: la categoria «{nuovo['category']}» non esiste")
            continue
        if all(voce.get(k) == v for k, v in nuovo.items()):
            gia_fatte.append(nome)
            continue
        if voce.get("category") != PARTENZA[nome] or voce.get("effect"):
            problemi.append(f"{nome}: non e' nello stato atteso (category={voce.get('category')}, "
                            f"effect={voce.get('effect')}). Non lo sovrascrivo.")
            continue
        da_scrivere.append((nome, voce, nuovo))

    for nome, voce, nuovo in da_scrivere:
        prima = {k: voce.get(k) for k in nuovo}
        print(f"+ {nome:14s} {prima} -> {nuovo}")
    if gia_fatte:
        print(f"= gia' assegnate: {len(gia_fatte)}")
    for riga in problemi:
        print("X " + riga)

    if problemi:
        print(f"\n{len(problemi)} problemi: non scrivo niente.")
        return 1
    if not da_scrivere:
        print("\nNiente da fare: tutti gli effetti sono gia' nel catalogo.")
        return 0
    if args.dry_run:
        print(f"\n--dry-run: {len(da_scrivere)} oggetti da scrivere, file non toccato.")
        return 0

    for _, voce, nuovo in da_scrivere:
        voce.update(nuovo)
    salva_catalogo("items", voci)
    print(f"\nScritti {len(da_scrivere)} oggetti in data/catalog/items.json "
          "(copia precedente in data/archive/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
