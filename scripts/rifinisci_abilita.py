#!/usr/bin/env python
"""Due rifiniture sulle abilità, decise l'11/08/2026.

    python scripts/rifinisci_abilita.py [--dry-run]

**1. Le 10 abilità di Champions ricevono una nota nella descrizione.**
Sono le voci il cui blocco `effect` non corrisponde a nessuna abilità reale — SpA +50%
fisso, +30% sulle mosse ad area, Difesa +50% con la Neve (che è la meccanica della
Neve, non Snow Cloak) — e per questo la fusione dei doppioni le ha lasciate stare.
Restano dove sono, ma la loro `desc` lo dice: chi le trova nella tendina capisce
perché esistono e non le scambia per un errore. Nessun dato viene inventato: la nota
è un'aggiunta al testo, l'effetto non si tocca.

**2. Il fallback `data/abilities.json` viene riallineato al catalogo.**
È il file che `load_abilities()` legge **solo** se `data/catalog/abilities.json`
manca. Conteneva ancora le voci fuse: se quel giorno arrivasse, il fallback
riporterebbe indietro tutti i doppioni appena chiusi, e in silenzio. Non viene
dismesso — quello si fa al collaudo finale, con gli altri file storici — ma smette di
essere una macchina del tempo. Copia in `data/archive/abilities_legacy_pre-allineamento.json`.

Rieseguibile: alla seconda esecuzione non trova più niente da fare.
"""
import argparse
import io
import json
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGO = os.path.join(RADICE, "data", "catalog", "abilities.json")
LEGACY = os.path.join(RADICE, "data", "abilities.json")
ARCHIVIO = os.path.join(RADICE, "data", "archive")

NOTA = " — abilità di Champions, senza corrispondente ufficiale."

# Le 10 voci il cui effetto non corrisponde a nessuna abilità reale. L'elenco è
# esplicito di proposito: dedurlo automaticamente vorrebbe dire ricalcolare ogni
# volta un giudizio che è stato dato guardando le voci una per una.
CHAMPIONS = [
    "Assorbifuoco", "Colpo Secco", "Compressione", "Manto Neve", "Nervosismo",
    "Polifagia", "Sforzo", "Tempra", "Tiratore", "Vento Misterioso",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra cosa farebbe senza scrivere niente")
    args = ap.parse_args()

    with open(CATALOGO, encoding="utf-8") as f:
        dati = json.load(f)
    voci = dati["abilities"]

    mancanti = [k for k in CHAMPIONS if k not in voci]
    if mancanti:
        print("Mi fermo senza scrivere niente — voci non trovate: " + ", ".join(mancanti))
        return 1

    da_marcare = [k for k in CHAMPIONS if not (voci[k].get("desc") or "").endswith(NOTA)]
    with open(LEGACY, encoding="utf-8") as f:
        legacy = json.load(f)
    fallback_allineato = legacy.get("abilities") == voci

    if not da_marcare and fallback_allineato:
        print("Niente da fare: le 10 note ci sono già e il fallback è allineato.")
        return 0

    print(f"{len(da_marcare)} descrizioni da annotare"
          + ("" if fallback_allineato else
             f" · fallback da riallineare ({len(legacy.get('abilities', {}))} → {len(voci)} voci)"))
    for k in da_marcare:
        print(f"  {k:20s} {(voci[k].get('desc') or '')[:58]}")

    if args.dry_run:
        print("\n--dry-run: nessuna modifica.")
        return 0

    os.makedirs(ARCHIVIO, exist_ok=True)
    if da_marcare:
        with open(os.path.join(ARCHIVIO, "catalog_abilities_pre-nota-champions.json"),
                  "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        for k in da_marcare:
            voci[k]["desc"] = (voci[k].get("desc") or "").rstrip() + NOTA
        with open(CATALOGO, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        print(f"Annotate {len(da_marcare)} voci in {os.path.relpath(CATALOGO, RADICE)}")

    if not fallback_allineato:
        with open(os.path.join(ARCHIVIO, "abilities_legacy_pre-allineamento.json"),
                  "w", encoding="utf-8") as f:
            json.dump(legacy, f, ensure_ascii=False, indent=2)
        prima = len(legacy.get("abilities", {}))
        legacy["abilities"] = voci
        with open(LEGACY, "w", encoding="utf-8") as f:
            json.dump(legacy, f, ensure_ascii=False, indent=2)
        print(f"Fallback riallineato: {prima} → {len(voci)} voci "
              f"({os.path.relpath(LEGACY, RADICE)})")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
