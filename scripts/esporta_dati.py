#!/usr/bin/env python
"""Esporta il contenuto di `hub.db` in un JSON committabile.

    python scripts/esporta_dati.py [--dry-run]

`hub.db` è escluso da git (è un binario, e dentro c'è l'hash della password), quindi
i dati che vivono solo lì — la libreria giochi importata da Steam, i team, i progetti
Arduino, le build del PC — **non hanno nessuna copia su GitHub**. Questo script ne
scrive una leggibile in `data/backup/hub_export.json`, che invece viene committata.

Due scelte che rendono il file utile in un repo:

- **niente data di esportazione dentro il file.** Un timestamp farebbe risultare una
  modifica a ogni esecuzione, e il diff non direbbe più niente. Quando è stato fatto
  lo dice già il commit
- **righe ordinate per `id`**, così il diff mostra solo i dati cambiati davvero

Le **password non vengono esportate**: degli utenti restano username, nome
visualizzato e ruolo. Un ripristino ricrea `admin` con la password di default via
`init_db()`, e le altre vanno reimpostate a mano — è il prezzo giusto per non tenere
hash di password dentro un repo.
"""
import argparse
import io
import json
import os
import sqlite3
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RADICE, "hub.db")
USCITA = os.path.join(RADICE, "data", "backup", "hub_export.json")

# tabella -> colonne da NON esportare
ESCLUSE = {"users": {"password"}}

TABELLE = [
    "users", "games", "teams", "team_members",
    "arduino_projects", "python_topics", "pc_builds", "pc_components",
]


def righe(db, tabella):
    try:
        cur = db.execute(f"SELECT * FROM {tabella} ORDER BY id")
    except sqlite3.Error:
        return None                      # tabella non ancora creata: non è un errore
    fuori = ESCLUSE.get(tabella, set())
    return [{k: r[k] for k in r.keys() if k not in fuori} for r in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(DB):
        print(f"hub.db non trovato in {DB}: niente da esportare.")
        return 1

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    dati, mancanti = {}, []
    for t in TABELLE:
        r = righe(db, t)
        if r is None:
            mancanti.append(t)
        else:
            dati[t] = r
    db.close()

    if not dati:
        print("Nessuna tabella leggibile: non sovrascrivo l'export esistente.")
        return 1

    testo = json.dumps(dati, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    for t in TABELLE:
        if t in dati:
            print(f"  {t:<18} {len(dati[t]):>5} righe")
    if mancanti:
        print(f"  (tabelle assenti nel DB: {', '.join(mancanti)})")

    if args.dry_run:
        print(f"\n--dry-run: {len(testo)} byte non scritti.")
        return 0

    precedente = None
    if os.path.exists(USCITA):
        with io.open(USCITA, encoding="utf-8") as f:
            precedente = f.read()
    if precedente == testo:
        print(f"\nNessuna differenza: {os.path.relpath(USCITA, RADICE)} è già aggiornato.")
        return 0

    os.makedirs(os.path.dirname(USCITA), exist_ok=True)
    with io.open(USCITA, "w", encoding="utf-8") as f:
        f.write(testo)
    print(f"\nScritto {os.path.relpath(USCITA, RADICE)} — {len(testo)} byte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
