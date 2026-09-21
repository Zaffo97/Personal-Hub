#!/usr/bin/env python
"""Porta le probabili formazioni della giornata in `hub.db`. Rieseguibile.

    python scripts/importa_probabili.py --dry-run
    python scripts/importa_probabili.py --scarica     # quasi sempre questo
    python scripts/importa_probabili.py --giornata 7  # solo se la pagina sbaglia

Sezione Fantacalcio (§4.2), 21/09/2026. La fonte è la pagina
`/probabili-formazioni-serie-a` di fantacalcio.it e la legge `fantacalcio_it.py`,
che non scrive niente: qui c'è l'unica parte che tocca il DB.

⚠️ **Qui la cache invecchia in ore, non in mesi.** Il listone cambia a ogni
mercato, le probabili cambiano **fino al fischio d'inizio**: un titolare diventa
panchinaro il sabato mattina. Senza `--scarica` lo script rilegge la copia in
cache e scrive un dato vecchio **senza dare errore**, ed è per questo che lo dice
a voce ogni volta, con l'età della copia in ore.

COSA FA A UNA GIORNATA CHE RILEGGE:

**La sovrascrive tutta.** Le altre giornate non le tocca. Una formazione non è un
dato che si aggiorna campo per campo: se un giocatore sparisce dai convocati, la
sua riga di quella giornata **deve** sparire, altrimenti resta lì a dire che è in
panchina quando la fonte non lo nomina più. Le righe tolte vengono contate e dette.

⚠️ Si rifiuta di scrivere se legge **meno di 20 squadre** o se la pagina non ha
detto che giornata è: sono i due sintomi di una pagina cambiata di forma o letta a
metà, e tutti e due, senza questo controllo, darebbero un DB a posto con dentro
mezza giornata. La soglia si scavalca con `--forza`, che va usato sapendo perché —
per esempio a campionato fermo, quando giocano in poche.
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
from extensions import get_db                                # noqa: E402

# Venti squadre giocano ogni giornata di Serie A: leggerne meno è un sintomo.
SQUADRE_ATTESE = 20


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

    dati, problemi = F.probabili(forza=args.scarica)
    giornata = args.giornata or dati["giornata"]
    squadre, voci = dati["squadre"], dati["voci"]

    print(f"LETTO DALLA FONTE   giornata {giornata or '?'}"
          f"{' — Serie A ' + dati['stagione'] if dati['stagione'] else ''}")
    print(f"  squadre        {len(squadre)}")
    titolari = sum(v["titolare"] for v in voci)
    print(f"  convocati      {len(voci)}  ({titolari} titolari, "
          f"{len(voci) - titolari} in panchina)")
    if problemi:
        print(f"\n  ⚠️  {len(problemi)} problemi nella lettura:")
        for p in problemi[:10]:
            print(f"     · {p}")
        if len(problemi) > 10:
            print(f"     … e altri {len(problemi) - 10}")

    if giornata is None:
        print("\n⚠️  La pagina non dice che giornata è, e senza quella il dato non ha "
              "una chiave.\n   INTERROTTO. Se la sai: --giornata N")
        return 1
    if len(squadre) < SQUADRE_ATTESE and not args.forza:
        print(f"\n⚠️  Ho letto {len(squadre)} squadre invece di {SQUADRE_ATTESE}.")
        print("   INTERROTTO: mezza giornata scritta sembra una giornata intera.")
        print("   Se è voluto (campionato fermo, recuperi): --forza")
        return 1

    db = get_db()
    # Lo schema lo porta avanti `init_db()`, non questo script: è la convenzione
    # del progetto, e detta così invece che con un traceback si capisce cosa fare.
    if not db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                      "AND name='fanta_probabili'").fetchone():
        db.close()
        print("\n⚠️  In hub.db non c'è la tabella `fanta_probabili`.")
        print("   Lo schema lo crea `init_db()`: avvia l'app una volta e riprova.")
        return 1
    prima = {r["player_id"]: dict(r) for r in db.execute(
        "SELECT * FROM fanta_probabili WHERE giornata=?", (giornata,)).fetchall()}
    letti = {v["id"] for v in voci}
    tolti = [r for pid, r in prima.items() if pid not in letti]

    # Quali di questi convocati sono in una tua rosa: è l'unica parte del dato
    # che ti riguarda davvero, ed è il motivo per cui la giornata si importa.
    in_rosa = {}
    if letti:
        segni = ",".join("?" * len(letti))
        for r in db.execute(
                f"SELECT r.player_id, COUNT(*) AS quante FROM fanta_roster r "
                f"WHERE r.player_id IN ({segni}) GROUP BY r.player_id",
                list(letti)).fetchall():
            in_rosa[r["player_id"]] = r["quante"]
    # ⚠️ LEFT JOIN mentale: un convocato può non essere nel listone. Non è un
    # errore da nascondere, è un giocatore che la fonte non quota.
    noti = {r["id"] for r in db.execute("SELECT id FROM fanta_players")}
    ignoti = [v for v in voci if v["id"] not in noti]

    print(f"\nRISPETTO AL DB   giornata {giornata}: {len(prima)} righe già scritte")
    print(f"  entrano        {len(letti - set(prima))}")
    print(f"  riscritte      {len(letti & set(prima))}")
    print(f"  tolte          {len(tolti)}")
    if tolti:
        for r in tolti[:10]:
            print(f"     · {r['nome']} ({r['squadra_slug']}) non è più fra i convocati")
        if len(tolti) > 10:
            print(f"     … e altri {len(tolti) - 10}")
    if ignoti:
        print(f"\n  {len(ignoti)} convocati non sono nel listone: entrano lo stesso, "
              "senza quotazioni.")
        for v in ignoti[:10]:
            print(f"     · {v['nome']} ({v['squadra_slug']}, {v['ruolo']})")
        if len(ignoti) > 10:
            print(f"     … e altri {len(ignoti) - 10}")
    if in_rosa:
        miei = [v for v in voci if v["id"] in in_rosa]
        titolari_miei = sum(1 for v in miei if v["titolare"])
        print(f"\n  nelle tue rose: {len(miei)} convocati, di cui {titolari_miei} "
              f"titolari e {len(miei) - titolari_miei} in panchina")

    if args.dry_run:
        db.close()
        print("\n--dry-run: niente scritto.")
        return 0

    db.execute("DELETE FROM fanta_probabili WHERE giornata=?", (giornata,))
    db.execute("DELETE FROM fanta_probabili_squadre WHERE giornata=?", (giornata,))
    db.executemany(
        "INSERT INTO fanta_probabili_squadre(giornata, squadra_slug, squadra, modulo,"
        " avversario, avversario_slug, in_casa, match_id, aggiornato_il)"
        " VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
        [(giornata, s["squadra_slug"], s["squadra"], s["modulo"], s["avversario"],
          s["avversario_slug"], s["in_casa"], s["match_id"])
         for s in squadre.values()])
    db.executemany(
        "INSERT INTO fanta_probabili(giornata, player_id, nome, squadra_slug, ruolo,"
        " titolare, percentuale, aggiornato_il)"
        " VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
        [(giornata, v["id"], v["nome"], v["squadra_slug"], v["ruolo"],
          v["titolare"], v["percentuale"]) for v in voci])
    db.commit()
    quante = db.execute("SELECT COUNT(*) FROM fanta_probabili WHERE giornata=?",
                        (giornata,)).fetchone()[0]
    giornate = db.execute("SELECT COUNT(DISTINCT giornata) FROM fanta_probabili"
                          ).fetchone()[0]
    db.close()
    print(f"\nScritto in hub.db: {quante} convocati della giornata {giornata}, "
          f"{len(squadre)} squadre. Giornate in archivio: {giornate}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
