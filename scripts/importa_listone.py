#!/usr/bin/env python
"""Porta i due Excel di fantacalcio.it nel listone del Fantacalcio. Rieseguibile.

    python scripts/importa_listone.py FILE FILE --dry-run
    python scripts/importa_listone.py FILE FILE
    python scripts/importa_listone.py FILE FILE --calendario   # anche football-data

§4.6, 24/09/2026. I due file sono quelli che il pulsante «Scarica» di fantacalcio.it
dà **dopo il login** (quotazioni e statistiche): li scarica Davide a mano, e questo
script li legge e basta. L'ordine non conta — quale sia quale lo dicono le colonne.

⚠️ La logica non è qui: sta in `fanta.py`, perché la stessa cosa la fa il form della
pagina. Questo file è il rivestimento a riga di comando che stampa il rapporto.
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

import fanta as G                                           # noqa: E402
from extensions import get_db, init_db                       # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", nargs=2, help="i due .xlsx, in qualunque ordine")
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    ap.add_argument("--forza", action="store_true",
                    help="scrive anche se il listone è molto più corto del solito")
    ap.add_argument("--calendario", action="store_true",
                    help="dopo il listone, rilegge calendario e classifica")
    args = ap.parse_args()

    dati = []
    for percorso in args.file:
        with open(percorso, "rb") as f:
            dati.append(f.read())
    fq, fs, problemi = G.leggi_i_due_file(*dati)
    for p in problemi:
        print("⚠️ ", p)
    if problemi:
        return 1

    init_db()
    db = get_db()
    r = G.importa_listone(db, fq, fs, scrivi=not args.dry_run, forza=args.forza)
    if not r["ok"]:
        print("✗ Non scritto:", r["motivo"])
        db.close()
        return 1
    print(f"Letti {r['letti']} giocatori: {r['letti'] - r['ceduti']} in Serie A, "
          f"{r['ceduti']} ceduti.")
    print(f"  nuovi {len(r['nuovi'])}, cambiati {r['cambiati']}, "
          f"riaccesi {len(r['riaccesi'])}, non più nel file {len(r['spenti'])}")
    if r["in_rosa"]:
        print(f"  ⚠️ {len(r['in_rosa'])} dei ceduti o usciti sono in una rosa")
    if r["senza_statistiche"] or r["solo_statistiche"]:
        print(f"  ⚠️ {r['senza_statistiche']} senza statistiche, "
              f"{len(r['solo_statistiche'])} solo nelle statistiche (non entrano)")
    for p in r["problemi"]:
        print("  ⚠️", p)
    print("(dry-run: niente scritto)" if args.dry_run else "Scritto.")

    if args.calendario:
        c = G.aggiorna_calendario(db, scrivi=not args.dry_run)
        if not c["ok"]:
            print("✗ Calendario:", c["motivo"])
        else:
            print(f"Calendario: {c['partite']} partite, {c['con_ora']} con l'ora "
                  f"esatta, {c['squadre']} squadre"
                  + (f", ⚠️ non abbinate: {', '.join(c['non_abbinate'])}"
                     if c["non_abbinate"] else ""))
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
