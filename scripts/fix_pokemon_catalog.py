#!/usr/bin/env python3
"""
fix_pokemon_catalog.py
Corregge le base_stats errate (stat Lv.50 invece di vere base stats)
nel file data/pokemon_catalog.json.
Esegui dalla root del progetto: python scripts/fix_pokemon_catalog.py
"""
import json, os

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pokemon_catalog.json")

# Entry principali con base_stats già calcolate (stat Lv.50 31IV invece di vere base stats)
ENTRY_FIXES = {
    "palafin-zero-form":       {"hp": 100, "atk": 70,  "def": 72,  "spa": 53,  "spd": 62,  "spe": 100},
    "gourgeist-average":       {"hp": 65,  "atk": 90,  "def": 122, "spa": 58,  "spd": 75,  "spe": 84},
    "morpeko-full-belly-mode": {"hp": 58,  "atk": 95,  "def": 58,  "spa": 70,  "spd": 58,  "spe": 97},
    "basculegion-male":        {"hp": 120, "atk": 112, "def": 65,  "spa": 80,  "spd": 75,  "spe": 78},
    "aegislash-shield-forme":  {"hp": 60,  "atk": 50,  "def": 140, "spa": 50,  "spd": 140, "spe": 60},
    "meowstic-male":           {"hp": 74,  "atk": 48,  "def": 76,  "spa": 83,  "spd": 81,  "spe": 104},
    "mega-banette":            {"hp": 64,  "atk": 165, "def": 75,  "spa": 93,  "spd": 83,  "spe": 75},
    "mega-chimecho":           {"hp": 75,  "atk": 50,  "def": 80,  "spa": 95,  "spd": 90,  "spe": 65},
    "mega-crabominable":       {"hp": 97,  "atk": 132, "def": 85,  "spa": 55,  "spd": 85,  "spe": 43},
    "eternal-flower-floette":  {"hp": 74,  "atk": 65,  "def": 67,  "spa": 125, "spd": 128, "spe": 92},
}

# Forme dentro "forms" con base_stats già calcolate
FORM_FIXES = {
    "Alolan Raichu":           {"hp": 60,  "atk": 85,  "def": 50,  "spa": 95,  "spd": 85,  "spe": 110},
    "Alolan Ninetales":        {"hp": 73,  "atk": 67,  "def": 75,  "spa": 81,  "spd": 100, "spe": 109},
    "Hisuian Arcanine":        {"hp": 95,  "atk": 115, "def": 80,  "spa": 95,  "spd": 80,  "spe": 90},
    "Galarian Slowbro":        {"hp": 95,  "atk": 100, "def": 95,  "spa": 100, "spd": 70,  "spe": 30},
    "Galarian Slowking":       {"hp": 95,  "atk": 65,  "def": 80,  "spa": 110, "spd": 110, "spe": 30},
    "Hisuian Typhlosion":      {"hp": 73,  "atk": 84,  "def": 78,  "spa": 119, "spd": 85,  "spe": 95},
    "Hisuian Samurott":        {"hp": 90,  "atk": 108, "def": 80,  "spa": 100, "spd": 65,  "spe": 85},
    "Hisuian Zoroark":         {"hp": 55,  "atk": 100, "def": 60,  "spa": 125, "spd": 60,  "spe": 110},
    "Hisuian Goodra":          {"hp": 80,  "atk": 100, "def": 100, "spa": 110, "spd": 150, "spe": 60},
    "Hisuian Decidueye":       {"hp": 88,  "atk": 112, "def": 80,  "spa": 95,  "spd": 95,  "spe": 60},
    "Hisuian Avalugg":         {"hp": 95,  "atk": 127, "def": 184, "spa": 34,  "spd": 36,  "spe": 38},
    "Heat Rotom":              {"hp": 50,  "atk": 65,  "def": 107, "spa": 105, "spd": 107, "spe": 86},
    "Wash Rotom":              {"hp": 50,  "atk": 65,  "def": 107, "spa": 105, "spd": 107, "spe": 86},
    "Frost Rotom":             {"hp": 50,  "atk": 65,  "def": 107, "spa": 105, "spd": 107, "spe": 86},
    "Fan Rotom":               {"hp": 50,  "atk": 65,  "def": 107, "spa": 105, "spd": 107, "spe": 86},
    "Mow Rotom":               {"hp": 50,  "atk": 65,  "def": 107, "spa": 105, "spd": 107, "spe": 86},
    "Palafin (Hero Form)":     {"hp": 100, "atk": 160, "def": 97,  "spa": 106, "spd": 87,  "spe": 100},
    "Gourgeist (Small)":       {"hp": 55,  "atk": 85,  "def": 122, "spa": 58,  "spd": 75,  "spe": 99},
    "Gourgeist (Large)":       {"hp": 75,  "atk": 95,  "def": 122, "spa": 58,  "spd": 75,  "spe": 69},
    "Gourgeist (Super)":       {"hp": 85,  "atk": 100, "def": 122, "spa": 58,  "spd": 75,  "spe": 54},
    "Basculegion (Female)":    {"hp": 120, "atk": 92,  "def": 65,  "spa": 100, "spd": 75,  "spe": 78},
    "Aegislash (Blade Forme)": {"hp": 60,  "atk": 140, "def": 50,  "spa": 140, "spd": 50,  "spe": 60},
    "Meowstic (Female)":       {"hp": 74,  "atk": 48,  "def": 76,  "spa": 83,  "spd": 81,  "spe": 104},
    "Mega Floette":            {"hp": 74,  "atk": 85,  "def": 87,  "spa": 145, "spd": 148, "spe": 92},
}


def main():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    fixed_entries = []
    fixed_forms = []

    # Fix entry principali
    for key, new_stats in ENTRY_FIXES.items():
        if key in catalog:
            old = catalog[key]["base_stats"].copy()
            catalog[key]["base_stats"] = new_stats
            fixed_entries.append(f"  {catalog[key]['name']}: BST {sum(old.values())} → {sum(new_stats.values())}")

    # Fix forme
    for key, mon in catalog.items():
        for form_name, form_data in mon.get("forms", {}).items():
            if form_name in FORM_FIXES:
                old = form_data["base_stats"].copy()
                form_data["base_stats"] = FORM_FIXES[form_name]
                fixed_forms.append(f"  {form_name}: BST {sum(old.values())} → {sum(FORM_FIXES[form_name].values())}")

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"✅ Fix completato!")
    print(f"\n📋 Entry principali fixate ({len(fixed_entries)}):")
    for line in fixed_entries:
        print(line)
    print(f"\n🔧 Forme fixate ({len(fixed_forms)}):")
    for line in fixed_forms:
        print(line)


if __name__ == "__main__":
    main()
