#!/usr/bin/env python
"""Dà l'effetto alle abilità che il motore ignorava, ognuna con la sua fonte.

    python scripts/effetti_abilita.py [--dry-run]

Tutte avevano `effect: none`, quindi il calcolatore le mostrava nella tendina e non
faceva niente, senza nessun errore. Nato il 26/09/2026 come `effetti_abilita_mc.py`
per le due di Regulation M-C (BACKLOG §3, trovate il 23/09); lo stesso giorno ha preso
le tre sorelle di Affilama e il nome generico.

- **Affilama** (*Sharpness*, Mega Absol Z): le mosse **da taglio** ×1.5. Il numero è
  di Serebii («Increases the power of Slicing moves used by this Pokémon by 50%») e
  coincide con Bulbapedia. Quali mosse sono «da taglio» lo dice il flag `slicing` di
  `moves.json`, completato lo stesso giorno con
  `integra_flag_mosse.py --da-elenco slicing` (31 mosse, la lista di Bulbapedia
  aggiornata a Champions, che ha aggiunto le mosse «artiglio»). ⚠️ Serebii ha anche
  **Dual Chop**, Bulbapedia no: una fonte sola, resta fuori.
- **Aura Guard** (Mega Lucario Z): il danno delle mosse **da contatto** ×0.5. Fonti:
  gli account ufficiali di Nintendo of America e di Pokémon Champions, e Serebii.
  ⚠️ Il **nome italiano** non l'ha dato nessuna delle fonti lette: la voce resta
  senza `nome_it`, e a schermo si legge il nome inglese. Non si inventa.
- **Ferropugno** (*Iron Fist*): le mosse **pugno** ×1.2 (4915/4096) — Serebii e
  Bulbapedia, che aggiunge: si somma al Guantone, ×1.32 in tutto. È il motivo per cui
  il motore concatena la potenza di abilità e oggetto in un passo solo
- **Ferromascella** (*Strong Jaw*): i **morsi** ×1.5 — Serebii e Bulbapedia
- **Megalancio** (*Mega Launcher*): le mosse **pulsar e aura** ×1.5 — Serebii e
  Bulbapedia. Il +50% di cura di Ondasana non tocca il danno e non c'è. ⚠️ Muddy Water
  aveva il flag `pulse`, che nessuna delle due fonti le dà: tolto lo stesso giorno con
  `integra_flag_mosse.py --da-elenco pulse --togli`, prima di accendere questa

I flag delle tre (25 `punch`, 10 `bite`, 7 `pulse`) combaciano con le liste di
Bulbapedia, misurato il 26/09/2026.

Le descrizioni sono in italiano per scelta (13/08/2026). Dove la voce ne ha già una
italiana e giusta, `desc` qui manca e quella resta.

Scrive con `_save_abilities()`, che lascia la copia in `data/archive/`. Si **ferma**
se una delle due ha già un effetto diverso da `none` e da quello qui sotto: vorrebbe
dire che qualcuno l'ha scritto a mano, e va guardato prima. Rieseguibile.
"""
import argparse
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

VOCI = {
    "Affilama": {
        "effect": {"type": "flag_boost", "flag": "slicing", "value": 1.5},
        "desc": "Potenzia del 50% le mosse da taglio.",
    },
    "Aura Guard": {
        "effect": {"type": "contact_guard", "value": 0.5},
        "desc": "Dimezza il danno subito dalle mosse che comportano un contatto.",
    },
    "Ferropugno": {"effect": {"type": "flag_boost", "flag": "punch", "value": 1.2}},
    "Ferromascella": {"effect": {"type": "flag_boost", "flag": "bite", "value": 1.5}},
    "Megalancio": {"effect": {"type": "flag_boost", "flag": "pulse", "value": 1.5}},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra cosa farebbe senza scrivere niente")
    args = ap.parse_args()

    from blueprints.pokemon import load_abilities, _save_abilities

    dati = load_abilities()
    ab = dati.get("abilities") or {}
    da_fare = []
    for chiave, nuova in VOCI.items():
        voce = ab.get(chiave)
        if voce is None:
            print(f"Mi fermo: '{chiave}' non è nel catalogo delle abilità.")
            return 1
        attuale = voce.get("effect") or {"type": "none"}
        desc = nuova.get("desc", voce.get("desc"))
        if attuale == nuova["effect"] and voce.get("desc") == desc:
            print(f"= {chiave}: già a posto")
            continue
        if attuale.get("type") != "none" and attuale != nuova["effect"]:
            print(f"Mi fermo: '{chiave}' ha già un effetto diverso, {attuale}. "
                  "Va guardato a mano prima di sovrascriverlo.")
            return 1
        print(f"+ {chiave}: effect {attuale} -> {nuova['effect']}")
        if desc != voce.get("desc"):
            print(f"  {'':{len(chiave)}}  desc  {voce.get('desc')!r} -> {desc!r}")
        da_fare.append((voce, nuova))

    if not da_fare:
        print("Niente da fare.")
        return 0
    if args.dry_run:
        print("--dry-run: file non toccato.")
        return 0
    for voce, nuova in da_fare:
        voce["effect"] = dict(nuova["effect"])
        voce["desc"] = nuova.get("desc", voce.get("desc"))
    _save_abilities(dati)
    print("Scritto data/catalog/abilities.json (copia precedente in data/archive/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
