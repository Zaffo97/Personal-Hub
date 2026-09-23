#!/usr/bin/env python
"""Confronta roster e oggetti di una regulation con Serebii e Bulbapedia.

    python scripts/confronta_regulation.py mc               # solo il confronto
    python scripts/confronta_regulation.py ma mb mc --applica
    python scripts/confronta_regulation.py mc --aggiorna    # riscarica le pagine

Il rivestimento a riga di comando di `regulation_fonti.py`, dove stanno le regole
(una specie cambia solo se le due fonti concordano, le forme nostre restano, gli
oggetti si aggiungono e non si tolgono). Lo stesso confronto c'è come pulsante nella
pagina della regulation. Senza `--applica` non scrive niente.
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

import regulation_fonti  # noqa: E402


def stampa(c):
    if not c.get("ok"):
        print(f"  X {c.get('errore')}")
        for p in c.get("problemi") or []:
            print(f"    - {p}")
        return
    k = c["conti"]
    print(f"  Bulbapedia {k['bulbapedia']} voci, Serebii {k['serebii']}, roster {k['roster']}, "
          f"specie concordi {k['specie_concordi']}")
    print(f"  + da aggiungere ({len(c['da_aggiungere'])}): {', '.join(c['da_aggiungere']) or '—'}")
    print(f"  - da togliere   ({len(c['da_togliere'])}): {', '.join(c['da_togliere']) or '—'}")
    print(f"  = forme nostre che restano ({len(c['forme_nostre'])}): {', '.join(c['forme_nostre']) or '—'}")
    for d in c["disaccordi"]:
        print(f"  ≠ {d['specie']}: {d['fonte']}, {'nel roster' if d['nel_roster'] else 'fuori'} "
              f"— resta com'è ({', '.join(d['voci'])})")
    print(f"  + oggetti nuovi ({len(c['oggetti_nuovi'])}): {', '.join(c['oggetti_nuovi']) or '—'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reg", nargs="+", help="id delle regulation, es. ma mb mc")
    ap.add_argument("--applica", action="store_true", help="scrive roster, oggetti, mega_map e mosse")
    ap.add_argument("--aggiorna", action="store_true", help="riscarica le pagine delle fonti")
    args = ap.parse_args()

    esito = 0
    for reg in args.reg:
        print(f"== {reg}")
        c = regulation_fonti.confronto(reg, aggiorna=args.aggiorna)
        stampa(c)
        if not c.get("ok"):
            esito = 1
            continue
        if args.applica:
            a = regulation_fonti.applica(reg)
            if a.get("scritto"):
                print(f"  scritto: roster {a['roster_dopo']}, Mega collegate {a['mega_collegate']}, "
                      f"mosse {'ok' if a['mosse_ok'] else 'NON riallineate'}")
                for riga in a["mosse_esito"]:
                    print(f"    {riga}")
                esito |= 0 if a["mosse_ok"] else 1
            else:
                print(f"  {a.get('messaggio') or a.get('errore')}")
    return esito


if __name__ == "__main__":
    sys.exit(main())
