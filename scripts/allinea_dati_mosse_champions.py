#!/usr/bin/env python
"""Porta i dati delle mosse ai valori di **Champions**, non a quelli di Scarlatto/Violetto.

    python scripts/allinea_dati_mosse_champions.py [--dry-run]

Decisione di Davide del 18/09/2026: «devi considerare tutte le modifiche fatte in
Champions, non mi interessa come erano prima».

Champions ribilancia le mosse rispetto ai giochi principali, e il catalogo viene da
PokéAPI, cioè da Scarlatto/Violetto. La fonte è la sezione **«Changes from Scarlet and
Violet and Generation VIII»** della pagina «Pokémon Champions» su Bulbapedia, più la
nota ufficiale della versione 1.2.0. Il conto, misurato il 18/09/2026: delle 23 voci
qui sotto il catalogo ne aveva **14 già giuste** — qualcuna era già di Champions — e 9 no.

⚠️ La sezione contiene anche un blocco **commentato** di mosse «that aren't in the game
yet» (Gear Grind, Anchor Shot, Hyper Drill, …). Quelle **non** sono qui: nel gioco non
ci sono, e scriverle vorrebbe dire inventare.

Non si applicano, perché il modello non ha il campo:

- i **PP**: nessuna delle 919 mosse ha un campo `pp`, quindi Wish e Strength Sap 12→8
  e tutte le altre correzioni di PP non hanno dove andare
- `Salt Cure` dimezzata, `Rage Fist` che si azzera al cambio, `Milk Drink` sull'alleato,
  `Fake Out` e `First Impression` dopo il primo turno, la priorità con Encore,
  l'Eject Button: sono comportamenti del motore, non campi di una mossa
- le tre abilità cambiate (`Healer` 30→50%, `Unseen Fist`, `Run Away`): nel catalogo
  hanno `effect: {"type": "none"}` e non toccano il danno
- gli stati indeboliti (gelo, paralisi, sonno) e le etichette «extremely effective»:
  non sono dati di mossa

È rieseguibile: una voce già al valore di Champions viene contata e saltata. La copia
di sicurezza la lascia `salva_catalogo()`, in `data/archive/`.

⚠️ Si **rifiuta** di scrivere se una mossa dell'elenco non esiste nel catalogo.
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

from blueprints.pokemon import voci_catalogo, salva_catalogo  # noqa: E402

# ── I valori di Champions ────────────────────────────────────────────────────
# Ogni riga è una frase della sezione «Changes from Scarlet and Violet». Il campo
# `flags` si **aggiunge**, non si sostituisce: gli altri flag della mossa restano.
VALORI = {
    # «Snap Trap had its type changed from Grass to Steel»
    "Snap Trap":       {"type": "steel"},

    # «Slash, Trop Kick, and Psyshield Bash had their base power increased from 70 to
    #  80, 85, and 90, respectively»  (Slash: anche «now be used», changelog 1.2.0)
    "Slash":           {"bp": 80},
    "Trop Kick":       {"bp": 85},
    "Psyshield Bash":  {"bp": 90},
    # «Snipe Shot had its base power increased from 80 to 85»
    "Snipe Shot":      {"bp": 85},
    # «Apple Acid, Fire Lash, Grav Apple, and Spirit Shackle … from 80 to 90»
    "Apple Acid":      {"bp": 90},
    "Fire Lash":       {"bp": 90},
    "Grav Apple":      {"bp": 90},
    "Spirit Shackle":  {"bp": 90},
    # «First Impression had its base power increased from 90 to 100»
    "First Impression": {"bp": 100},
    # «Beak Blast and Mountain Gale … from 100 to 120»
    "Beak Blast":      {"bp": 120},
    "Mountain Gale":   {"bp": 120},
    # «Meteor Assault had its base power increased from 150 to 170»
    "Meteor Assault":  {"bp": 170},
    # «Bone Rush, Infernal Parade, and Night Daze … by 5 each, totaling 30, 65 and 90»
    "Bone Rush":       {"bp": 30},
    "Infernal Parade": {"bp": 65},
    "Night Daze":      {"bp": 90},

    # «Crabhammer and Syrup Bomb had their accuracy increased by 5 each, totaling 95%
    #  and 90%»
    "Crabhammer":      {"accuracy": 95},
    "Syrup Bomb":      {"accuracy": 90},
    # «Make It Rain had its accuracy reduced from 100% to 95%. It now reduces the
    #  user's Sp. Atk by two stages, instead of one»
    "Make It Rain":    {"accuracy": 95, "stat_changes": {"spa": -2}},

    # «Toxic Thread now lowers Speed by two stages rather than one»
    "Toxic Thread":    {"stat_changes": {"spe": -2}},

    # «Iron Head and Moonblast's secondary effect chances were lowered from 30% to 20%
    #  and 10%» · «Dire Claw's … from 50% to 30%. It is also now considered a slicing move»
    "Iron Head":       {"effect_chance": 20},
    "Moonblast":       {"effect_chance": 10},
    "Dire Claw":       {"effect_chance": 30, "flags+": ["slicing"]},
    # «Crush Claw, Dragon Claw, and Shadow Claw are now considered to be slicing moves»
    "Crush Claw":      {"flags+": ["slicing"]},
    "Dragon Claw":     {"flags+": ["slicing"]},
    "Shadow Claw":     {"flags+": ["slicing"]},
    # «Dragon Cheer is now considered a sound-based move»
    "Dragon Cheer":    {"flags+": ["sound"]},
    # «Double Shock is now considered a punching move»
    "Double Shock":    {"flags+": ["punch"]},
    # «Freeze-Dry can no longer inflict freeze»
    "Freeze-Dry":      {"effect_chance": 0},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    voci = voci_catalogo("moves")
    if not voci:
        print("Catalogo mosse vuoto o illeggibile: non tocco niente.")
        return 1

    da_scrivere, gia_fatte, problemi = [], [], []
    for mossa, atteso in sorted(VALORI.items()):
        voce = voci.get(mossa)
        if voce is None:
            problemi.append(f"{mossa}: non esiste nel catalogo")
            continue
        cambi = {}
        for campo, valore in atteso.items():
            if campo == "flags+":
                mancanti = [f for f in valore if f not in (voce.get("flags") or [])]
                if mancanti:
                    cambi["flags"] = sorted(set((voce.get("flags") or []) + valore))
            elif campo == "stat_changes":
                unione = dict(voce.get("stat_changes") or {})
                if any(unione.get(k) != v for k, v in valore.items()):
                    unione.update(valore)
                    cambi["stat_changes"] = unione
            elif voce.get(campo) != valore:
                cambi[campo] = valore
        if cambi:
            da_scrivere.append((mossa, voce, cambi))
        else:
            gia_fatte.append(mossa)

    for mossa, voce, cambi in da_scrivere:
        for campo, nuovo in cambi.items():
            print("  %-18s %-14s %-24s -> %s" % (mossa, campo, voce.get(campo), nuovo))
    print(f"\n= già ai valori di Champions: {len(gia_fatte)}")
    for riga in problemi:
        print("X " + riga)

    if problemi:
        print(f"\n{len(problemi)} problemi: non scrivo niente.")
        return 1
    if not da_scrivere:
        print("Niente da fare: il catalogo è già allineato a Champions.")
        return 0
    if args.dry_run:
        print(f"--dry-run: {len(da_scrivere)} mosse da correggere, file non toccato.")
        return 0

    for _mossa, voce, cambi in da_scrivere:
        voce.update(cambi)
    salva_catalogo("moves", voci)
    print(f"Scritte {len(da_scrivere)} mosse in data/catalog/moves.json "
          "(copia precedente in data/archive/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
