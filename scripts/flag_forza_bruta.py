#!/usr/bin/env python
"""Il flag `sheer_force`: le mosse che Forza Bruta potenzia, dove due fonti concordano.

    python scripts/flag_forza_bruta.py [--dry-run] [--aggiorna]

Dal 26/09/2026. Fino a quel giorno il motore dava il ×1.3 di Forza Bruta a **ogni**
mossa, Terremoto e Zuffa compresi, senza nessun errore. Nel gioco vale solo sulle mosse
con un **effetto aggiuntivo** (Bulbapedia: calo delle stat del bersaglio, aumento delle
proprie, stato, tentennamento — non il contraccolpo né il calo delle **proprie** stat), e
nessun campo del catalogo lo dice: `effect_chance` no, perché Zuffa ha 100 (il suo calo
di difese) e Forza Bruta non la tocca.

**Le fonti**, e la regola è quella di sempre: si scrive dove **concordano**.

- **Bulbapedia**, «Sheer Force (Ability)», sezione *Affected moves*: righe `{{movelist}}`,
  in cache con le altre pagine in `data/cache/bulbapedia/mosse/`
- **Pokémon Showdown**, `data/moves.ts`: una mossa ha l'effetto se dichiara `secondary`
  o `secondaries` (o `hasSheerForce`) e non è di stato. È il simulatore che il VGC usa,
  e il campo è esattamente quello che la sua Forza Bruta legge. In cache in
  `data/cache/showdown/moves.ts`

⚠️ **Serebii** non è una delle due: la sua pagina elenca solo le mosse di Champions (144
link), e fra queste mancano Fake Out, Rock Tomb e Snarl, che le altre due danno. Letta il
26/09/2026 e lasciata come nota.

Misurato il 26/09/2026: Bulbapedia 209, Showdown 208 sulle mosse del catalogo, **207 in
comune**. In disaccordo, e quindi **senza** flag: Electro Shot e Order Up (solo
Bulbapedia), Zippy Zap (solo Showdown). Lo script li stampa a ogni giro.

Aggiunge e toglie: un `sheer_force` fuori dall'intersezione si toglie, perché il flag
nasce qui e non ha altri scrittori. Si ferma se una delle due fonti non si legge.
Scrive con `salva_catalogo()`. Rieseguibile.
"""
import argparse
import os
import re
import sys

import requests

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import voci_catalogo, salva_catalogo  # noqa: E402
from integra_flag_mosse import pagina, MOVELIST  # noqa: E402

FLAG = "sheer_force"
PAGINA = "Sheer Force (Ability)"
SHOWDOWN = "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/moves.ts"
CACHE_SHOWDOWN = os.path.join(RADICE, "data", "cache", "showdown", "moves.ts")


def da_bulbapedia(aggiorna):
    testo = pagina(PAGINA, aggiorna) or ""
    i = testo.find("====Affected moves====")
    if i < 0:
        return set()
    fine = testo.find("\n==", i + len("====Affected moves===="))
    blocco = testo[i:fine if fine > 0 else None]
    return {n.strip() for n in re.findall(r"\{\{[Mm]ovelist\|([^|}]+)", blocco)}


def da_showdown(aggiorna):
    if aggiorna or not os.path.exists(CACHE_SHOWDOWN):
        r = requests.get(SHOWDOWN, timeout=60)
        r.raise_for_status()
        os.makedirs(os.path.dirname(CACHE_SHOWDOWN), exist_ok=True)
        with open(CACHE_SHOWDOWN, "w", encoding="utf-8") as f:
            f.write(r.text)
    with open(CACHE_SHOWDOWN, encoding="utf-8") as f:
        testo = f.read()
    fuori = set()
    for blocco in re.split(r"\n\t(?=[a-z0-9]+: \{\n)", testo):
        nome = re.search(r'\n\t\tname: "([^"]+)"', blocco)
        categoria = re.search(r'\n\t\tcategory: "(\w+)"', blocco)
        if not nome or (categoria and categoria.group(1) == "Status"):
            continue
        if (re.search(r"\n\t\tsecondary: \{", blocco) or re.search(r"\n\t\tsecondaries: \[", blocco)
                or "hasSheerForce: true" in blocco):
            fuori.add(nome.group(1))
    return fuori


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="dice cosa farebbe e non scrive niente")
    ap.add_argument("--aggiorna", action="store_true", help="riscarica le due fonti")
    args = ap.parse_args()

    voci = voci_catalogo("moves")
    if not voci:
        print("Catalogo mosse vuoto o illeggibile: non tocco niente.")
        return 1
    bulba, showdown = da_bulbapedia(args.aggiorna), da_showdown(args.aggiorna)
    if not bulba or not showdown:
        print(f"Una fonte non si legge (Bulbapedia {len(bulba)}, Showdown {len(showdown)}): "
              "non scrivo niente.")
        return 1

    per_nome_en = {(v.get("nome_en") or k): k for k, v in voci.items()}
    nel_catalogo = set(per_nome_en)
    b, s = bulba & nel_catalogo, showdown & nel_catalogo
    comuni = b & s
    print(f"Bulbapedia {len(b)}, Showdown {len(s)} sulle mosse del catalogo: "
          f"{len(comuni)} in comune")
    for n in sorted(b - s):
        print(f"≠ {n}: solo Bulbapedia (senza flag)")
    for n in sorted(s - b):
        print(f"≠ {n}: solo Showdown (senza flag)")

    aggiungi = sorted(per_nome_en[n] for n in comuni
                      if FLAG not in (voci[per_nome_en[n]].get("flags") or []))
    togli = sorted(k for k, v in voci.items() if FLAG in (v.get("flags") or [])
                   and (v.get("nome_en") or k) not in comuni)
    for k in aggiungi:
        print(f"+ {k}")
    for k in togli:
        print(f"- {k}")
    if not aggiungi and not togli:
        print("Niente da fare.")
        return 0
    print(f"{len(aggiungi)} da aggiungere, {len(togli)} da togliere")
    if args.dry_run:
        print("--dry-run: file non toccato.")
        return 0
    for k in aggiungi:
        voci[k]["flags"] = sorted(set(voci[k].get("flags") or []) | {FLAG})
    for k in togli:
        voci[k]["flags"] = sorted(set(voci[k].get("flags") or []) - {FLAG})
    salva_catalogo("moves", voci)
    print("Scritto data/catalog/moves.json (copia precedente in data/archive/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
