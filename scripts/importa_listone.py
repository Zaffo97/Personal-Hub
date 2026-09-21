#!/usr/bin/env python
"""Porta il listone di Serie A e le statistiche in `hub.db`. Rieseguibile.

    python scripts/importa_listone.py --dry-run
    python scripts/importa_listone.py
    python scripts/importa_listone.py --scarica      # il mercato: rilegge dalla rete

Sezione Fantacalcio (§4.2), 21/09/2026. La fonte è `fantacalcio.it` (l'ex
Fantagazzetta) e la legge `fantacalcio_it.py`, che non scrive niente.

⚠️ **Dal 21/09/2026 la logica non è più qui**: sta in `fanta_import.py`, perché
la stessa cosa la fa anche il pulsante «Aggiorna» della pagina. Questo file è il
rivestimento a riga di comando — legge gli argomenti e **stampa** il rapporto che
`aggiorna_listone()` restituisce. Scriverla due volte voleva dire lasciarne una
indietro, che è come questo progetto si è già fatto male una volta.

⚠️ **Va rilanciato a ogni mercato** — a luglio e a gennaio le rose cambiano — e
in quel caso con `--scarica`, altrimenti rilegge la copia in cache e dice il falso
senza dare errore.

COSA FA A UN GIOCATORE CHE NON È PIÙ NEL LISTONE, che è il punto di tutto:

**Lo spegne, non lo cancella.** `attivo` passa a 0 e la riga resta. Cancellarla
porterebbe via anche la voce di rosa che la nomina, cioè proprio il dato che è tuo
e che la fonte non sa ricostruire. Lo script dice **quanti degli spenti sono in una
rosa**, perché quelli sono gli unici che ti riguardano davvero.

E al contrario, un giocatore spento che **torna** nel listone si riaccende da sé.

⚠️ Si rifiuta di scrivere se il listone letto è **molto più corto** di quello che
c'è già nel DB (meno del 70%): una pagina tornata a metà, o cambiata di forma, darebbe
esattamente quel sintomo senza dare errore. La soglia si scavalca con `--forza`, che
va usato solo sapendo perché.
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
                    help="rilegge le pagine dalla rete invece che dalla cache")
    ap.add_argument("--forza", action="store_true",
                    help="scrive anche se il listone è molto più corto del solito")
    args = ap.parse_args()

    for nome in ("quotazioni", "statistiche"):
        ore = F.eta_cache(nome)
        if ore is None:
            print(f"  {nome}: non in cache, la scarico")
        elif args.scarica:
            print(f"  {nome}: in cache da {ore:.0f} ore, la riscarico (--scarica)")
        else:
            print(f"  {nome}: letta dalla cache, ferma da {ore:.0f} ore")
    print()

    db = get_db()
    r = I.aggiorna_listone(db, scarica=args.scarica, scrivi=not args.dry_run,
                           forza=args.forza)

    if r["letti"]:
        print(f"LETTI DALLA FONTE   {r['letti']} giocatori, {r['squadre']} squadre")
        print("  per ruolo: " + "  ".join(
            f"{F.RUOLI_CLASSIC.get(ruolo, ruolo)} {n}"
            for ruolo, n in sorted(r["per_ruolo"].items())))
    if r["problemi"]:
        print(f"\n  ⚠️  {len(r['problemi'])} problemi nella lettura:")
        for p in r["problemi"][:10]:
            print(f"     · {p}")

    if not r["ok"]:
        db.close()
        print(f"\n⚠️  {r['motivo']}")
        print("   INTERROTTO." + ("" if "forma" in (r["motivo"] or "")
                                  else "  Se è voluto: --forza"))
        return 1

    print(f"\nRISPETTO AL DB   {r['nel_db']} voci ({r['attivi_prima']} attive)")
    print(f"  nuovi          {len(r['nuovi'])}")
    print(f"  aggiornati     {len(r['cambiati'])}")
    print(f"  riaccesi       {len(r['riaccesi'])}")
    print(f"  spenti         {len(r['spenti'])}")

    if r["trasferiti"]:
        print(f"\n  cambi di squadra: {len(r['trasferiti'])}")
        for v, vecchia in r["trasferiti"][:15]:
            print(f"     · {v['nome']:22s} {vecchia['squadra']} -> {v['squadra']}")
        if len(r["trasferiti"]) > 15:
            print(f"     … e altri {len(r['trasferiti']) - 15}")

    if r["spenti"]:
        print(f"\n  ⚠️  {len(r['spenti'])} giocatori non sono più nel listone. "
              "Restano nel DB spenti, non cancellati.")
        for x in r["spenti"][:15]:
            quante = r["in_rosa"].get(x["id"], 0)
            nota = f"   ⚠️ è in {quante} rosa/e" if quante else ""
            print(f"     · {x['nome']:22s} ({x['squadra']}){nota}")
        if len(r["spenti"]) > 15:
            print(f"     … e altri {len(r['spenti']) - 15}")
        quanti = sum(1 for x in r["spenti"] if r["in_rosa"].get(x["id"]))
        if quanti:
            print(f"\n  ⚠️  {quanti} di questi sono in una tua rosa: sono i "
                  "giocatori che hai ancora in squadra e che la Serie A non ha più.")

    if not r["scritto"]:
        db.close()
        print("\n--dry-run: niente scritto.")
        return 0
    db.close()
    print(f"\nScritto in hub.db: {r['attivi_dopo']} giocatori attivi su "
          f"{r['nel_db'] + len(r['nuovi'])} voci.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
