#!/usr/bin/env python
"""Assegna le 7 categorie di oggetti che erano vuote, con l'effetto per il calcolatore.

    python scripts/assegna_categorie_oggetti.py [--dry-run]

Decisione di Davide del 14/09/2026. `conditional`, `damage`, `defensive`, `orb`,
`support`, `terrain` e `weather` esistevano in `CATEGORIE_OGGETTI` senza nessuna voce,
e sono i gruppi da cui si riempiono le due tendine «Item» del calcolatore. `other`
erano **esattamente** i 339 oggetti senza `effect`: dare una categoria vuol dire quindi
dare un effetto, e l'effetto va scritto anche in `calcDamage()`.

Ogni valore viene da **Bulbapedia**, pagina per pagina, non da memoria. Le frazioni
ufficiali si scrivono arrotondate come i 58 oggetti già curati (4915/4096 -> 1.2,
4505/4096 -> 1.1, 5324/4096 -> 1.3).

Gli effetti, e cosa vuol dire ciascuno nel calcolatore:

- `boost_<tipo>` — potenza × modifier sulle mosse di quel tipo (c'era già)
- `boost_atk` / `boost_spa` — Attacco o Attacco Speciale × modifier (Bendascelta, Lentiscelta)
- `boost_physical` / `boost_special` — potenza × modifier sulle fisiche o sulle speciali
- `boost_punch` — potenza × modifier sulle mosse col flag `punch`
- `life_orb` — danno × modifier, sempre
- `expert_belt` — danno × modifier se la mossa è super efficace
- `boost_specie` — potenza × modifier se chi attacca è in `specie` e la mossa è di un
  tipo in `tipi` (`tipi` assente = tutte le mosse, le maschere di Ogerpon)
- `stat_specie` — la stat `stat` × modifier se il Pokémon è in `specie`
- `boost_spd` — Difesa Speciale × modifier (Corpetto assalto)
- `eviolite` — Difesa e Difesa Speciale × modifier se `puo_evolversi` è `true`
- `air_balloon` — immunità alle mosse Terra (modifier 0)

Le voci con `effect: null` prendono solo la categoria: non cambiano il danno, quindi non
entrano nelle tendine del calcolatore, che mostrano solo le voci con un `modifier`.

⚠️ **Non sovrascrive un oggetto già curato.** Tocca solo voci in `other` e senza
`effect`: se una di quelle elencate qui ha già una categoria diversa o un effetto,
non scrive **niente** ed esce con 1. È rieseguibile: una voce già uguale viene contata
e saltata. La copia di sicurezza la lascia `salva_catalogo()`, in `data/archive/`.
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


def solo_etichetta(categoria):
    return {"category": categoria, "effect": None, "modifier": None}


def tipo(categoria, t, mod):
    return {"category": categoria, "effect": f"boost_{t}", "modifier": mod}


ASSEGNAZIONI = {
    # ── choice ───────────────────────────────────────────────────────────────
    "Choice Band":  {"category": "choice", "effect": "boost_atk", "modifier": 1.5},
    "Choice Specs": {"category": "choice", "effect": "boost_spa", "modifier": 1.5},

    # ── damage ───────────────────────────────────────────────────────────────
    "Muscle Band":  {"category": "damage", "effect": "boost_physical", "modifier": 1.1},
    "Wise Glasses": {"category": "damage", "effect": "boost_special", "modifier": 1.1},

    # ── orb: Assorbisfera e le due sfere di stato (decisione di Davide) ──────
    "Life Orb":   {"category": "orb", "effect": "life_orb", "modifier": 1.3},
    "Flame Orb":  solo_etichetta("orb"),
    "Toxic Orb":  solo_etichetta("orb"),

    # ── conditional ──────────────────────────────────────────────────────────
    "Expert Belt":    {"category": "conditional", "effect": "expert_belt", "modifier": 1.2},
    "Punching Glove": {"category": "conditional", "effect": "boost_punch", "modifier": 1.1},
    # Gli oggetti delle leggende: la condizione e' la specie. In `conditional` e non in
    # `orb` perche' `orb` Davide l'ha data all'Assorbisfera.
    "Adamant Orb":  {"category": "conditional", "effect": "boost_specie", "modifier": 1.2,
                     "specie": ["Dialga"], "tipi": ["dragon", "steel"]},
    "Lustrous Orb": {"category": "conditional", "effect": "boost_specie", "modifier": 1.2,
                     "specie": ["Palkia"], "tipi": ["dragon", "water"]},
    "Griseous Orb": {"category": "conditional", "effect": "boost_specie", "modifier": 1.2,
                     "specie": ["Giratina"], "tipi": ["dragon", "ghost"]},
    "Soul Dew":     {"category": "conditional", "effect": "boost_specie", "modifier": 1.2,
                     "specie": ["Latios", "Latias"], "tipi": ["psychic", "dragon"]},
    "Hearthflame Mask":  {"category": "conditional", "effect": "boost_specie",
                          "modifier": 1.2, "specie": ["Ogerpon"]},
    "Wellspring Mask":   {"category": "conditional", "effect": "boost_specie",
                          "modifier": 1.2, "specie": ["Ogerpon"]},
    "Cornerstone Mask":  {"category": "conditional", "effect": "boost_specie",
                          "modifier": 1.2, "specie": ["Ogerpon"]},

    # ── utility: raddoppiano una stat a una specie, come l'Elettropalla ──────
    "Thick Club":     {"category": "utility", "effect": "stat_specie", "modifier": 2.0,
                       "stat": "atk", "specie": ["Cubone", "Marowak"]},
    "Deep Sea Tooth": {"category": "utility", "effect": "stat_specie", "modifier": 2.0,
                       "stat": "spa", "specie": ["Clamperl"]},

    # ── type_boost: aromi (+20%), lastre (+20%), gemme (+30%, consumate) ─────
    "Odd Incense":  tipo("type_boost", "psychic", 1.2),
    "Rock Incense": tipo("type_boost", "rock", 1.2),
    "Rose Incense": tipo("type_boost", "grass", 1.2),
    "Sea Incense":  tipo("type_boost", "water", 1.2),
    "Wave Incense": tipo("type_boost", "water", 1.2),
    # Lastraleggenda esclusa: non ha un tipo, cambia quello di Giudizio
    **{f"{nome} Plate": tipo("type_boost", t, 1.2) for nome, t in {
        "Blank": "normal", "Fist": "fighting", "Sky": "flying", "Toxic": "poison",
        "Earth": "ground", "Stone": "rock", "Insect": "bug", "Spooky": "ghost",
        "Iron": "steel", "Flame": "fire", "Splash": "water", "Meadow": "grass",
        "Zap": "electric", "Mind": "psychic", "Icicle": "ice", "Draco": "dragon",
        "Dread": "dark", "Pixie": "fairy"}.items()},
    **{f"{t.capitalize()} Gem": tipo("type_boost", t, 1.3) for t in (
        "normal", "fighting", "flying", "poison", "ground", "rock", "bug", "ghost",
        "steel", "fire", "water", "grass", "electric", "psychic", "ice", "dragon",
        "dark", "fairy")},

    # ── defensive ────────────────────────────────────────────────────────────
    "Assault Vest":   {"category": "defensive", "effect": "boost_spd", "modifier": 1.5},
    "Eviolite":       {"category": "defensive", "effect": "eviolite", "modifier": 1.5},
    "Deep Sea Scale": {"category": "defensive", "effect": "stat_specie", "modifier": 2.0,
                       "stat": "spd", "specie": ["Clamperl"]},
    "Metal Powder":   {"category": "defensive", "effect": "stat_specie", "modifier": 2.0,
                       "stat": "def", "specie": ["Ditto"]},
    "Air Balloon":    {"category": "defensive", "effect": "air_balloon", "modifier": 0},

    # ── solo etichette ───────────────────────────────────────────────────────
    **{n: solo_etichetta("weather") for n in
       ("Heat Rock", "Damp Rock", "Smooth Rock", "Icy Rock")},
    **{n: solo_etichetta("terrain") for n in
       ("Terrain Extender", "Electric Seed", "Grassy Seed", "Misty Seed", "Psychic Seed")},
    "Light Clay": solo_etichetta("support"),
    **{f"{n} Berry": solo_etichetta("berry") for n in
       ("Apicot", "Custap", "Ganlon", "Lansat", "Liechi", "Micle", "Petaya", "Salac",
        "Starf", "Aguav", "Figy", "Iapapa", "Mago", "Wiki")},
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
        if voce.get("category") != "other" or voce.get("effect"):
            problemi.append(f"{nome}: e' gia' curato (category={voce.get('category')}, "
                            f"effect={voce.get('effect')}). Non lo sovrascrivo.")
            continue
        da_scrivere.append((nome, voce, nuovo))

    per_categoria = {}
    for nome, _, nuovo in da_scrivere:
        per_categoria.setdefault(nuovo["category"], []).append(nome)
    for cat, nomi in sorted(per_categoria.items()):
        print(f"+ {cat:12s} {len(nomi):3d}: " + ", ".join(nomi))
    if gia_fatte:
        print(f"= gia' assegnate: {len(gia_fatte)}")
    for riga in problemi:
        print("X " + riga)

    if problemi:
        print(f"\n{len(problemi)} problemi: non scrivo niente.")
        return 1
    if not da_scrivere:
        print("\nNiente da fare: tutte le assegnazioni sono gia' nel catalogo.")
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
