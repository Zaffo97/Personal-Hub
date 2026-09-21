#!/usr/bin/env python
"""Porta le probabili formazioni della giornata in `hub.db`. Rieseguibile.

    python scripts/importa_probabili.py --dry-run
    python scripts/importa_probabili.py --scarica     # quasi sempre questo
    python scripts/importa_probabili.py --giornata 7  # solo se la pagina sbaglia

Sezione Fantacalcio (§4.2), 21/09/2026. La fonte è la pagina
`/probabili-formazioni-serie-a` di fantacalcio.it e la legge `fantacalcio_it.py`.

⚠️ **Dal 21/09/2026 la logica non è più qui**: sta in `fanta_import.py`, perché la
stessa cosa la fa anche il pulsante «Aggiorna» della pagina, e l'aggiornamento
automatico quando entri nella sezione. Questo file legge gli argomenti e **stampa**
il rapporto che `aggiorna_probabili()` restituisce.

⚠️ **Qui la cache invecchia in ore, non in mesi.** Il listone cambia a ogni
mercato, le probabili cambiano **fino al fischio d'inizio**: un titolare diventa
panchinaro il sabato mattina. Senza `--scarica` lo script rilegge la copia in cache
e scrive un dato vecchio **senza dare errore**, ed è per questo che l'età della
copia viene detta a voce ogni volta, in ore.

COSA FA A UNA GIORNATA CHE RILEGGE:

**La sovrascrive tutta.** Le altre giornate non le tocca. Se un giocatore sparisce
dai convocati, la sua riga di quella giornata **deve** sparire, altrimenti resta lì
a dire che è in panchina quando la fonte non lo nomina più.

⚠️ Si rifiuta di scrivere se legge **meno di 20 squadre** o se la pagina non ha
detto che giornata è. La soglia si scavalca con `--forza`, che va usato sapendo
perché — per esempio a campionato fermo, quando giocano in poche.
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

import fantacalcio_it as F                                   # noqa: E402
import fanta_import as I                                     # noqa: E402
from extensions import get_db                                # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    ap.add_argument("--scarica", action="store_true",
                    help="rilegge la pagina dalla rete invece che dalla cache")
    ap.add_argument("--giornata", type=int,
                    help="la giornata sotto cui salvare, se la pagina non la dice")
    ap.add_argument("--forza", action="store_true",
                    help="scrive anche con meno di 20 squadre")
    args = ap.parse_args()

    ore = F.eta_cache("probabili")
    if ore is None:
        print("  probabili: non in cache, la scarico")
    elif args.scarica:
        print(f"  probabili: in cache da {ore:.1f} ore, la riscarico (--scarica)")
    else:
        print(f"  ⚠️  probabili: letta dalla CACHE, ferma da {ore:.1f} ore. "
              "Le formazioni cambiano fino al fischio d'inizio: --scarica")
    print()

    db = get_db()
    r = I.aggiorna_probabili(db, scarica=args.scarica, scrivi=not args.dry_run,
                             giornata=args.giornata, forza=args.forza)

    print(f"LETTO DALLA FONTE   giornata {r['giornata'] or '?'}"
          f"{' — Serie A ' + r['stagione'] if r['stagione'] else ''}")
    print(f"  squadre        {r['squadre']}")
    print(f"  convocati      {r['voci']}  ({r['titolari']} titolari, "
          f"{r['voci'] - r['titolari']} in panchina)")
    if r["problemi"]:
        print(f"\n  ⚠️  {len(r['problemi'])} problemi nella lettura:")
        for p in r["problemi"][:10]:
            print(f"     · {p}")
        if len(r["problemi"]) > 10:
            print(f"     … e altri {len(r['problemi']) - 10}")

    if not r["ok"]:
        db.close()
        print(f"\n⚠️  {r['motivo']}")
        if "giornata è" in (r["motivo"] or ""):
            print("   INTERROTTO. Se la sai: --giornata N")
        else:
            print("   INTERROTTO. Se è voluto (campionato fermo, recuperi): --forza")
        return 1

    print(f"\nRISPETTO AL DB   giornata {r['giornata']}: {r['gia_scritte']} righe "
          "già scritte")
    print(f"  entrano        {r['entrano']}")
    print(f"  riscritte      {r['riscritte']}")
    print(f"  tolte          {len(r['tolti'])}")
    for x in r["tolti"][:10]:
        print(f"     · {x['nome']} ({x['squadra_slug']}) non è più fra i convocati")
    if len(r["tolti"]) > 10:
        print(f"     … e altri {len(r['tolti']) - 10}")
    if r["ignoti"]:
        print(f"\n  {len(r['ignoti'])} convocati non sono nel listone: entrano lo "
              "stesso, senza quotazioni.")
        for v in r["ignoti"][:10]:
            print(f"     · {v['nome']} ({v['squadra_slug']}, {v['ruolo']})")
        if len(r["ignoti"]) > 10:
            print(f"     … e altri {len(r['ignoti']) - 10}")
    if r["miei"]:
        print(f"\n  nelle tue rose: {r['miei']} convocati, di cui "
              f"{r['miei_titolari']} titolari e {r['miei'] - r['miei_titolari']} "
              "in panchina")

    if not r["scritto"]:
        db.close()
        print("\n--dry-run: niente scritto.")
        return 0
    db.close()
    print(f"\nScritto in hub.db: {r['voci']} convocati della giornata "
          f"{r['giornata']}, {r['squadre']} squadre. Giornate in archivio: "
          f"{r['giornate_in_archivio']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
