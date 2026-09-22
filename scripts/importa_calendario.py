#!/usr/bin/env python
"""Porta il calendario di Serie A in `hub.db`: **quando** si gioca. Rieseguibile.

    python scripts/importa_calendario.py --dry-run
    python scripts/importa_calendario.py --scarica         # quasi sempre questo
    python scripts/importa_calendario.py --scarica --giornata 7

Sezione Fantacalcio (§4.2), 22/09/2026. Serve a una cosa sola: l'ora della
**prima partita** di una giornata, cioè la scadenza entro cui schierare la
formazione. È il dato del timer che si vede in Dashboard, nell'elenco delle leghe,
nella scheda della lega e sul campo.

⚠️ **L'orario non sta nelle probabili formazioni**, e sembra di sì: quella pagina
ha lo stesso riquadro con data e ora, ma i valori sono segnaposto — `1970-01-01` e
`01:00` su tutte e dieci le partite, misurato il 22/09/2026. Leggerli darebbe un
orario invece di un errore, ed è il motivo per cui il lettore butta via una data
prima del 2000 invece di salvarla.

⚠️ **Senza `--giornata` si legge la pagina generica**, che è la giornata in corso.
Quando le probabili sono già passate alla successiva serve la sua:
`/serie-a/calendario/7`. Dalle pagine web questo lo fa da sé — la giornata la
prende dalle probabili importate.

⚠️ Si rifiuta di scrivere una giornata con **meno di 10 partite**: la scadenza è il
*minimo* degli orari, quindi basta che manchi l'anticipo del venerdì perché il
timer dica «hai ancora un giorno» a giornata già cominciata. Meglio nessun timer di
un timer in ritardo. La soglia si scavalca con `--forza`, sapendo perché (recuperi,
giornate spezzate).
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
                    help="quale giornata leggere (senza, quella in corso)")
    ap.add_argument("--forza", action="store_true",
                    help="scrive anche una giornata con meno di 10 partite")
    args = ap.parse_args()

    nome = F.nome_calendario(args.giornata)
    ore = F.eta_cache(nome)
    if ore is None:
        print(f"  {nome}: non in cache, la scarico")
    elif args.scarica:
        print(f"  {nome}: in cache da {ore:.1f} ore, la riscarico (--scarica)")
    else:
        print(f"  ⚠️  {nome}: letto dalla CACHE, fermo da {ore:.1f} ore. "
              "Un rinvio sposta l'orario: --scarica")
    print()

    db = get_db()
    r = I.aggiorna_calendario(db, scarica=args.scarica, scrivi=not args.dry_run,
                              forza=args.forza, giornata=args.giornata)

    print(f"LETTO DALLA FONTE   {r['partite']} partite")
    for g, quante in sorted(r["giornate"].items()):
        print(f"  giornata {g}   {quante} partite")
    if r["senza_ora"]:
        print(f"  ⚠️  {r['senza_ora']} senza data e ora: entrano, ma non contano "
              "per la scadenza")
    if r["problemi"]:
        print(f"\n  ⚠️  {len(r['problemi'])} problemi nella lettura:")
        for p in r["problemi"][:10]:
            print(f"     · {p}")
        if len(r["problemi"]) > 10:
            print(f"     … e altri {len(r['problemi']) - 10}")

    if not r["ok"]:
        db.close()
        print(f"\n⚠️  {r['motivo']}")
        print("   INTERROTTO. Se è voluto (recuperi, giornata spezzata): --forza")
        return 1
    if r["saltate"]:
        print("\n  giornate saltate perché incomplete: " +
              ", ".join(f"{g} ({n} partite)" for g, n in sorted(r["saltate"].items())))

    if not r["scritto"]:
        db.close()
        print("\n--dry-run: niente scritto.")
        return 0

    print(f"\nScritto in hub.db: {r['scritte']} partite.")
    for g in sorted(r["giornate"]):
        riga = db.execute("SELECT inizio, squadra_casa, squadra_fuori FROM "
                          "fanta_calendario WHERE giornata=? AND inizio IS NOT NULL "
                          "ORDER BY inizio LIMIT 1", (g,)).fetchone()
        if riga:
            print(f"  giornata {g}: si schiera entro il {riga['inizio']} "
                  f"({riga['squadra_casa']}–{riga['squadra_fuori']})")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
