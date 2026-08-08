#!/usr/bin/env python3
"""
patch_abilities_effects.py

Completa i blocchi `effect` mancanti in data/abilities.json per le abilita' che
il calcolatore danno sa gestire ma che erano rimaste con {"type": "none"}.

Le voci sono state individuate per DESCRIZIONE, non per nome, perche' alcuni nomi
nel file non corrispondono all'abilita' che descrivono.

Uso:
    python scripts/patch_abilities_effects.py            # applica
    python scripts/patch_abilities_effects.py --dry-run  # mostra e basta

Non sovrascrive un effect gia' diverso da "none" se non con --force.
"""
import argparse
import json
import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(BASE_DIR, "data", "abilities.json")

# nome_nel_json -> nuovo blocco effect
PATCH = {
    # ── Abilita' "-ate": convertono le mosse Normale e le potenziano x1.2 ──────
    "Pellecielo":    {"type": "ate", "move_type": "Volante",  "value": 1.2},
    "Pellefolletto": {"type": "ate", "move_type": "Folletto", "value": 1.2},
    "Pellegelo":     {"type": "ate", "move_type": "Ghiaccio", "value": 1.2},
    "Pellelettro":   {"type": "ate", "move_type": "Elettro",  "value": 1.2},
    # Normalize converte QUALSIASI tipo, non solo Normale
    "Normalità":     {"type": "ate", "move_type": "Normale",  "value": 1.2, "any_source": True},

    # ── Contatto ──────────────────────────────────────────────────────────────
    "Unghiedure":    {"type": "tough_claws", "value": 1.3},

    # ── Wonder Guard: "Rende vulnerabili solo alle mosse superefficaci" ───────
    "Magidifesa":    {"type": "wonder_guard"},

    # ── Pinch (sotto 1/3 PS) — nomi ufficiali IT, erano rimasti a none ────────
    "Erbaiuto":      {"type": "overgrow", "move_type": "Erba"},
    "Acquaiuto":     {"type": "overgrow", "move_type": "Acqua"},
    "Aiutofuoco":    {"type": "overgrow", "move_type": "Fuoco"},
    "Aiutinsetto":   {"type": "overgrow", "move_type": "Coleottero"},

    # ── Filter/Solid Rock: stessa desc di Filtraggio, che gia' aveva l'effect ──
    "Filtro":        {"type": "filter", "value": 0.75},
    "Solidroccia":   {"type": "filter", "value": 0.75},
    "Scudoprisma":   {"type": "filter", "value": 0.75},
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true",
                   help="sovrascrive anche effect gia' valorizzati")
    args = p.parse_args()

    with open(PATH, encoding="utf-8") as f:
        root = json.load(f)
    abilities = root.get("abilities", root)

    applicati, saltati, assenti = [], [], []
    for nome, eff in PATCH.items():
        voce = abilities.get(nome)
        if voce is None:
            assenti.append(nome)
            continue
        attuale = (voce.get("effect") or {}).get("type", "none")
        if attuale != "none" and not args.force:
            saltati.append(f"{nome} (ha gia' '{attuale}')")
            continue
        voce["effect"] = eff
        applicati.append(f"{nome} -> {eff['type']}")

    for r in applicati:
        print(f"  [OK]      {r}")
    for r in saltati:
        print(f"  [SALTATO] {r}")
    for r in assenti:
        print(f"  [ASSENTE] {r}")
    print(f"\n{len(applicati)} applicati, {len(saltati)} saltati, {len(assenti)} assenti")

    if args.dry_run:
        print("\n--dry-run: nessuna modifica scritta.")
        return
    if not applicati:
        print("\nNiente da fare.")
        return

    backup = PATH + "." + datetime.now().strftime("%Y%m%d_%H%M%S") + ".bak"
    shutil.copy2(PATH, backup)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(root, f, ensure_ascii=False, indent=2)
    print(f"\nBackup: {os.path.basename(backup)}")
    print(f"Scritto: {os.path.relpath(PATH, BASE_DIR)}")


if __name__ == "__main__":
    main()
