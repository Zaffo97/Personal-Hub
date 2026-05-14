#!/usr/bin/env python3
"""
patch_catalog_abilities.py

Aggiunge le abilità mancanti alle forme (Mega, Alolan, Galarian, Hisuian, ecc.)
nel file data/pokemon_catalog.json.

Uso:
    python scripts/patch_catalog_abilities.py

Non sovrascrive abilità già presenti.
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "data", "pokemon_catalog.json")

# ---------------------------------------------------------------------------
# Mappa: nome_forma_esatto (come nel JSON) → lista abilità
# ---------------------------------------------------------------------------
FORM_ABILITIES = {
    # ── MEGA ────────────────────────────────────────────────────────────────
    "Mega Venusaur":        ["Thick Fat"],
    "Mega Charizard X":     ["Tough Claws"],
    "Mega Charizard Y":     ["Drought"],
    "Mega Blastoise":       ["Mega Launcher"],
    "Mega Beedrill":        ["Adaptability"],
    "Mega Pidgeot":         ["No Guard"],
    "Mega Alakazam":        ["Trace"],
    "Mega Slowbro":         ["Shell Armor"],
    "Mega Gengar":          ["Shadow Tag"],
    "Mega Kangaskhan":      ["Parental Bond"],
    "Mega Pinsir":          ["Aerilate"],
    "Mega Gyarados":        ["Mold Breaker"],
    "Mega Aerodactyl":      ["Tough Claws"],
    "Mega Meganium":        ["Thick Fat"],
    "Mega Feraligatr":      ["Sheer Force"],
    "Mega Ampharos":        ["Mold Breaker"],
    "Mega Scizor":          ["Technician"],
    "Mega Heracross":       ["Skill Link"],
    "Mega Houndoom":        ["Solar Power"],
    "Mega Tyranitar":       ["Sand Stream"],
    "Mega Gardevoir":       ["Pixilate"],
    "Mega Sableye":         ["Magic Bounce"],
    "Mega Aggron":          ["Filter"],
    "Mega Medicham":        ["Pure Power"],
    "Mega Manectric":       ["Intimidate"],
    "Mega Sharpedo":        ["Strong Jaw"],
    "Mega Camerupt":        ["Sheer Force"],
    "Mega Altaria":         ["Pixilate"],
    "Mega Absol":           ["Magic Bounce"],
    "Mega Glalie":          ["Refrigerate"],
    "Mega Salamence":       ["Aerilate"],
    "Mega Metagross":       ["Tough Claws"],
    "Mega Latias":          ["Levitate"],
    "Mega Latios":          ["Levitate"],
    "Mega Lucario":         ["Adaptability"],
    "Mega Abomasnow":       ["Snow Warning"],
    "Mega Lopunny":         ["Scrappy"],
    "Mega Garchomp":        ["Sand Force"],
    "Mega Gallade":         ["Inner Focus"],
    "Mega Audino":          ["Healer"],
    "Mega Steelix":         ["Sand Force"],
    "Mega Sceptile":        ["Lightning Rod"],
    "Mega Blaziken":        ["Speed Boost"],
    "Mega Swampert":        ["Swift Swim"],
    "Mega Mawile":          ["Huge Power"],
    "Mega Banette":         ["Prankster"],
    "Mega Diancie":         ["Magic Bounce"],
    "Mega Rayquaza":        ["Delta Stream"],
    "Mega Mewtwo X":        ["Steadfast"],
    "Mega Mewtwo Y":        ["Insomnia"],
    "Mega Skarmory":        ["Sturdy"],
    "Mega Dragonite":       ["Multiscale"],
    "Mega Emboar":          ["Reckless"],
    "Mega Excadrill":       ["Sand Rush"],
    "Mega Golurk":          ["No Guard"],
    "Mega Chandelure":      ["Infiltrator"],
    "Mega Froslass":        ["Cursed Body"],
    "Mega Chesnaught":      ["Bulletproof"],
    "Mega Delphox":         ["Magician"],
    "Mega Greninja":        ["Protean"],
    "Mega Hawlucha":        ["Unburden"],
    "Mega Drampa":          ["Cloud Nine"],
    "Mega Glimmora":        ["Corrosion"],
    "Mega Scovillain":      ["Drought"],
    "Mega Starmie":         ["Natural Cure"],
    "Mega Victreebel":      ["Chlorophyll"],
    "Mega Clefable":        ["Friend Guard"],
    "Mega Machamp":         ["No Guard"],
    "Mega Meganium":        ["Thick Fat"],
    "Mega Steelix":         ["Sand Force"],
    "Mega Heracross":       ["Skill Link"],
    "Mega Lopunny":         ["Scrappy"],
    "Mega Houndoom":        ["Solar Power"],
    "Mega Meowstic (Male)": ["Prankster"],
    "Mega Meowstic (Female)": ["Competitive"],
    "Mega Floette":         ["Flower Veil"],
    "Mega Chimecho":        ["Levitate"],
    "Mega Crabominable":    ["Iron Fist"],
    # ── ALOLAN ──────────────────────────────────────────────────────────────
    "Alolan Raichu":        ["Surge Surfer"],
    "Alolan Ninetales":     ["Snow Cloak", "Snow Warning"],
    "Alolan Sandshrew":     ["Snow Cloak"],
    "Alolan Sandslash":     ["Snow Cloak"],
    "Alolan Vulpix":        ["Snow Cloak"],
    "Alolan Exeggutor":     ["Frisk"],
    "Alolan Marowak":       ["Cursed Body", "Lightning Rod"],
    "Alolan Grimer":        ["Poison Touch", "Gluttony"],
    "Alolan Muk":           ["Poison Touch", "Gluttony"],
    "Alolan Geodude":       ["Magnet Pull", "Sturdy"],
    "Alolan Graveler":      ["Magnet Pull", "Sturdy"],
    "Alolan Golem":         ["Magnet Pull", "Sturdy"],
    "Alolan Meowth":        ["Pickup", "Technician"],
    "Alolan Persian":       ["Fur Coat", "Technician"],
    # ── GALARIAN ────────────────────────────────────────────────────────────
    "Galarian Slowbro":     ["Quick Draw", "Own Tempo"],
    "Galarian Slowking":    ["Curious Medicine", "Own Tempo"],
    "Galarian Weezing":     ["Levitate", "Neutralizing Gas"],
    "Galarian Mr. Mime":    ["Ice Body", "Screen Cleaner"],
    "Galarian Ponyta":      ["Run Away", "Pastel Veil"],
    "Galarian Rapidash":    ["Run Away", "Pastel Veil"],
    "Galarian Corsola":     ["Weak Armor"],
    "Galarian Linoone":     ["Pickup", "Gluttony"],
    "Galarian Meowth":      ["Pickup", "Tough Claws"],
    "Galarian Farfetch'd":  ["Steadfast"],
    "Galarian Zigzagoon":   ["Pickup", "Gluttony"],
    "Galarian Articuno":    ["Competitive"],
    "Galarian Zapdos":      ["Defiant"],
    "Galarian Moltres":     ["Berserk"],
    # ── HISUIAN ─────────────────────────────────────────────────────────────
    "Hisuian Arcanine":     ["Intimidate", "Flash Fire", "Rock Head"],
    "Hisuian Typhlosion":   ["Blaze", "Frisk"],
    "Hisuian Samurott":     ["Torrent", "Shell Armor"],
    "Hisuian Decidueye":    ["Overgrow", "Long Reach"],
    "Hisuian Zorua":        ["Illusion"],
    "Hisuian Zoroark":      ["Illusion"],
    "Hisuian Goodra":       ["Sap Sipper", "Hydration", "Gooey"],
    "Hisuian Avalugg":      ["Own Tempo", "Ice Body", "Sturdy"],
    "Hisuian Lilligant":    ["Chlorophyll", "Hustle"],
    "Hisuian Braviary":     ["Keen Eye", "Sheer Force"],
    "Hisuian Electrode":    ["Soundproof", "Static"],
    "Hisuian Sliggoo":      ["Sap Sipper", "Hydration"],
    # ── ALTRE FORME ─────────────────────────────────────────────────────────
    "Aegislash (Blade Forme)": ["Stance Change"],
    "Palafin (Hero Form)":  ["Zero to Hero"],
    "Basculegion (Female)": ["Swift Swim", "Adaptability"],
    "Meowstic (Female)":    ["Keen Eye", "Infiltrator", "Competitive"],
    "Indeedee (Female)":    ["Inner Focus", "Synchronize", "Psychic Surge"],
    "Gourgeist (Small)":    ["Pickup", "Frisk", "Insomnia"],
    "Gourgeist (Large)":    ["Pickup", "Frisk", "Insomnia"],
    "Gourgeist (Super)":    ["Pickup", "Frisk", "Insomnia"],
    "Tauros (Combat Breed)": ["Intimidate", "Anger Point", "Cud Chew"],
    "Tauros (Blaze Breed)":  ["Intimidate", "Anger Point", "Cud Chew"],
    "Tauros (Aqua Breed)":   ["Intimidate", "Anger Point", "Cud Chew"],
    "Heat Rotom":           ["Levitate"],
    "Wash Rotom":           ["Levitate"],
    "Frost Rotom":          ["Levitate"],
    "Fan Rotom":            ["Levitate"],
    "Mow Rotom":            ["Levitate"],
}


def patch_catalog(catalog: dict) -> tuple[dict, int, int]:
    """
    Itera il catalogo e aggiunge le abilità alle forme che le mancano.
    Restituisce (catalogo_patchato, n_aggiornati, n_skippati_già_presenti).
    """
    updated = 0
    skipped = 0

    for poke_key, poke_data in catalog.items():
        forms = poke_data.get("forms", {})
        for form_name, form_data in forms.items():
            if form_name in FORM_ABILITIES:
                existing = form_data.get("abilities", [])
                if not existing:  # aggiungi solo se vuota
                    form_data["abilities"] = FORM_ABILITIES[form_name]
                    updated += 1
                    print(f"  ✅ {form_name}")
                else:
                    skipped += 1
                    print(f"  ⏭  {form_name} (già presente: {existing})")

        # Gestisci anche le entry top-level che sono già una forma
        # (es. mega-banette, eternal-flower-floette, ecc.)
        top_name = poke_data.get("name", "")
        if top_name in FORM_ABILITIES:
            existing = poke_data.get("abilities", [])
            if not existing:
                poke_data["abilities"] = FORM_ABILITIES[top_name]
                updated += 1
                print(f"  ✅ [top-level] {top_name}")
            else:
                skipped += 1

    return catalog, updated, skipped


def main():
    print(f"📂 Catalogo: {CATALOG_PATH}")
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"📊 Pokémon nel catalogo: {len(catalog)}")
    print("\n🔧 Patching...")

    patched, updated, skipped = patch_catalog(catalog)

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(patched, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Completato!")
    print(f"   Aggiornati : {updated}")
    print(f"   Già presenti (skip): {skipped}")
    print(f"   Salvato in: {CATALOG_PATH}")


if __name__ == "__main__":
    main()
