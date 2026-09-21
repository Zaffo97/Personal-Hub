#!/usr/bin/env python
"""Porta il listone di Serie A e le statistiche in `hub.db`. Rieseguibile.

    python scripts/importa_listone.py --dry-run
    python scripts/importa_listone.py
    python scripts/importa_listone.py --scarica      # il mercato: rilegge dalla rete

Sezione Fantacalcio (§4.2), 21/09/2026. La fonte è `fantacalcio.it` (l'ex
Fantagazzetta) e la legge `fantacalcio_it.py`, che non scrive niente: qui c'è
l'unica parte che tocca il DB, ed è quella che deve sapere cosa fare di un
giocatore che **sparisce**.

⚠️ **Va rilanciato a ogni mercato** — a luglio e a gennaio le rose cambiano — e
in quel caso con `--scarica`, altrimenti rilegge la copia in cache e dice il falso
senza dare errore. Senza `--scarica` la cache vale finché non la si cancella.

COSA FA A UN GIOCATORE CHE NON È PIÙ NEL LISTONE, che è il punto di tutto:

**Lo spegne, non lo cancella.** `attivo` passa a 0 e la riga resta. Cancellarla
porterebbe via anche la voce di rosa che la nomina, cioè proprio il dato che è tuo
e che la fonte non sa ricostruire. Lo script dice **quanti degli spenti sono in una
rosa**, perché quelli sono gli unici che ti riguardano davvero: sono i giocatori
che a gennaio hai ancora in squadra e che dalla Serie A se ne sono andati.

E al contrario, un giocatore spento che **torna** nel listone si riaccende da sé.

⚠️ Si rifiuta di scrivere se il listone letto è **molto più corto** di quello che
c'è già nel DB (meno del 70%): una pagina tornata a metà, o cambiata di forma, darebbe
esattamente quel sintomo senza dare errore. La soglia si scavalca con `--forza`, che
va usato solo sapendo perché.
"""
import argparse
import os
import sys
from datetime import datetime

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import fantacalcio_it as F                                   # noqa: E402
from extensions import get_db                                # noqa: E402

CAMPI = ("nome", "slug", "squadra", "squadra_slug", "ruolo_classic",
         "ruolo_mantra", "ruolo_mantra_esteso", "qi", "qa", "fvm",
         "partite_a_voto", "media_voto", "fantamedia", "gol", "gol_subiti",
         "rigori", "rigori_parati", "assist", "ammonizioni", "espulsioni")

# Quanto può calare il listone prima che sia un sintomo invece di un mercato.
SOGLIA_CALO = 0.70


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

    voci, problemi = F.giocatori(forza=args.scarica)
    if not voci:
        print("Nessun giocatore letto: la pagina non ha la forma che mi aspetto.")
        return 1
    print(f"LETTI DALLA FONTE   {len(voci)} giocatori, {len({v['squadra'] for v in voci.values()})} squadre")
    per_ruolo = {}
    for v in voci.values():
        per_ruolo[v["ruolo_classic"]] = per_ruolo.get(v["ruolo_classic"], 0) + 1
    print("  per ruolo: " + "  ".join(f"{F.RUOLI_CLASSIC.get(r, r)} {n}"
                                      for r, n in sorted(per_ruolo.items())))
    if problemi:
        print(f"\n  ⚠️  {len(problemi)} problemi nella lettura:")
        for p in problemi[:10]:
            print(f"     · {p}")

    db = get_db()
    prima = {r["id"]: dict(r) for r in
             db.execute("SELECT * FROM fanta_players").fetchall()}
    attivi_prima = sum(1 for r in prima.values() if r["attivo"])

    if attivi_prima and len(voci) < attivi_prima * SOGLIA_CALO and not args.forza:
        print(f"\n⚠️  Il listone letto ha {len(voci)} giocatori, nel DB ce ne sono "
              f"{attivi_prima} attivi: sotto il {SOGLIA_CALO:.0%}.")
        print("   INTERROTTO: un calo così non è un mercato, è una pagina letta male.")
        print("   Se è voluto: --forza")
        db.close()
        return 1

    nuovi, cambiati, riaccesi = [], [], []
    for pid, v in voci.items():
        vecchia = prima.get(pid)
        if vecchia is None:
            nuovi.append(v)
        else:
            if not vecchia["attivo"]:
                riaccesi.append(v)
            diff = [c for c in CAMPI if (vecchia.get(c) or None) != (v.get(c) or None)]
            # La squadra cambiata è la notizia del mercato: si nomina a parte.
            if diff:
                cambiati.append((v, diff, vecchia))

    spenti = [r for pid, r in prima.items() if pid not in voci and r["attivo"]]
    # Degli spenti conta solo una cosa: quanti sono in una rosa.
    in_rosa = {}
    if spenti:
        segni = ",".join("?" * len(spenti))
        for r in db.execute(
                f"SELECT player_id, COUNT(*) AS quante FROM fanta_roster "
                f"WHERE player_id IN ({segni}) GROUP BY player_id",
                [r["id"] for r in spenti]).fetchall():
            in_rosa[r["player_id"]] = r["quante"]

    print(f"\nRISPETTO AL DB   {len(prima)} voci ({attivi_prima} attive)")
    print(f"  nuovi          {len(nuovi)}")
    print(f"  aggiornati     {len(cambiati)}")
    print(f"  riaccesi       {len(riaccesi)}")
    print(f"  spenti         {len(spenti)}")

    trasferiti = [(v, vecchia) for v, diff, vecchia in cambiati if "squadra" in diff]
    if trasferiti:
        print(f"\n  cambi di squadra: {len(trasferiti)}")
        for v, vecchia in trasferiti[:15]:
            print(f"     · {v['nome']:22s} {vecchia['squadra']} -> {v['squadra']}")
        if len(trasferiti) > 15:
            print(f"     … e altri {len(trasferiti) - 15}")

    if spenti:
        print(f"\n  ⚠️  {len(spenti)} giocatori non sono più nel listone. Restano nel DB "
              "spenti, non cancellati.")
        for r in spenti[:15]:
            quante = in_rosa.get(r["id"], 0)
            nota = f"   ⚠️ è in {quante} rosa/e" if quante else ""
            print(f"     · {r['nome']:22s} ({r['squadra']}){nota}")
        if len(spenti) > 15:
            print(f"     … e altri {len(spenti) - 15}")
        quanti_in_rosa = sum(1 for r in spenti if in_rosa.get(r["id"]))
        if quanti_in_rosa:
            print(f"\n  ⚠️  {quanti_in_rosa} di questi sono in una tua rosa: sono i "
                  "giocatori che hai ancora in squadra e che la Serie A non ha più.")

    if args.dry_run:
        db.close()
        print("\n--dry-run: niente scritto.")
        return 0

    oggi = datetime.now().strftime("%Y-%m-%d")
    colonne = ", ".join(CAMPI)
    segni = ", ".join("?" * len(CAMPI))
    aggiorna = ", ".join(f"{c}=excluded.{c}" for c in CAMPI)
    for pid, v in voci.items():
        db.execute(
            f"INSERT INTO fanta_players(id, {colonne}, attivo, visto_il, aggiornato_il) "
            f"VALUES(?, {segni}, 1, ?, CURRENT_TIMESTAMP) "
            f"ON CONFLICT(id) DO UPDATE SET {aggiorna}, attivo=1, visto_il=excluded.visto_il, "
            "aggiornato_il=CURRENT_TIMESTAMP",
            [pid] + [v.get(c) for c in CAMPI] + [oggi])
    if spenti:
        db.executemany("UPDATE fanta_players SET attivo=0, aggiornato_il=CURRENT_TIMESTAMP "
                       "WHERE id=?", [(r["id"],) for r in spenti])
    db.commit()
    quanti = db.execute("SELECT COUNT(*) FROM fanta_players WHERE attivo=1").fetchone()[0]
    db.close()
    print(f"\nScritto in hub.db: {quanti} giocatori attivi su {len(prima) + len(nuovi)} voci.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
