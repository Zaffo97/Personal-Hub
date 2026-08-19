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

# La console di Windows e' cp1252 e non sa scrivere le emoji, come gia' per gli script
# di import. Qui non e' cosmetico: senza questa riga l'avviso di INTERRUZIONE muore su
# UnicodeEncodeError, cioe' proprio il messaggio che deve spiegare perche' ci si e'
# fermati non arriverebbe mai a schermo.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RADICE, "hub.db")
USCITA = os.path.join(RADICE, "data", "backup", "hub_export.json")

# tabella -> colonne da NON esportare
ESCLUSE = {"users": {"password"}}

TABELLE = [
    "users", "games", "teams", "team_members",
    "arduino_projects", "python_topics", "pc_builds", "pc_components",
    # ⚠️ Dal 19/08/2026 la spunta degli argomenti Python **non è più** su
    # `python_topics`, è qui, una riga per utente e argomento. Senza questa tabella
    # nell'elenco il backup perderebbe il progresso di tutti senza dire niente:
    # `python_topics` verrebbe esportata comunque, ma con la sua colonna `done`
    # ferma alla fotografia del giorno della migrazione.
    "python_progress",
]


def righe(db, tabella):
    """Le righe di una tabella, in ordine stabile, senza le colonne escluse.

    ⚠️ L'ordinamento **non può essere `id` e basta**: `python_progress` non ha un `id`,
    ha una chiave doppia `(user_id, topic_id)`. Con `ORDER BY id` fisso la query
    sollevava, l'errore finiva nello stesso ramo di «tabella non ancora creata», e
    l'export dichiarava **assente** una tabella che c'era — perdendo in silenzio il
    progresso Python di tutti. L'ordine si chiede allo schema, non lo si indovina.
    """
    try:
        schema = [(r[1], r[5]) for r in db.execute(f"PRAGMA table_info({tabella})")]
    except sqlite3.Error:
        return None
    if not schema:
        return None                      # tabella non ancora creata: non è un errore
    nomi = [nome for nome, _ in schema]
    if "id" in nomi:
        ordine = "id"
    else:
        chiave = [nome for nome, pk in sorted(schema, key=lambda x: x[1]) if pk]
        ordine = ", ".join(chiave) if chiave else nomi[0]
    try:
        cur = db.execute(f"SELECT * FROM {tabella} ORDER BY {ordine}")
    except sqlite3.Error:
        return None
    fuori = ESCLUSE.get(tabella, set())
    return [{k: r[k] for k in r.keys() if k not in fuori} for r in cur.fetchall()]


def cali_sospetti(dati, precedente):
    """Tabelle che nell'export precedente avevano righe e ora sono **vuote**.

    Serve perché questo script è la sola copia su GitHub di `hub.db`, ed esportare
    fedelmente il vuoto significa **sovrascrivere l'unica copia buona**. È già
    successo: l'11/08/2026, fra le 10:09 e le 10:43, i 33 giochi importati da Steam
    sono spariti dal DB e l'export li ha cancellati anche dal backup, in silenzio.

    Un calo parziale non viene toccato — cancellare un gioco è una cosa normale.
    Solo il crollo a zero è sospetto, perché è la firma di un DB perso o ricreato.
    """
    if not precedente:
        return []
    try:
        prima = json.loads(precedente)
    except Exception:
        return []
    fuori = []
    for tabella, righe_nuove in dati.items():
        vecchie = prima.get(tabella)
        if isinstance(vecchie, list) and vecchie and not righe_nuove:
            fuori.append((tabella, len(vecchie)))
    return fuori


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--anche-se-vuoto", action="store_true",
                    help="scrive anche se una tabella è passata da N righe a zero")
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

    precedente = None
    if os.path.exists(USCITA):
        with io.open(USCITA, encoding="utf-8") as f:
            precedente = f.read()

    cali = cali_sospetti(dati, precedente)
    if cali and not args.anche_se_vuoto:
        print("\n⚠️  INTERROTTO: una tabella è passata da righe a ZERO.")
        for tabella, quante in cali:
            print(f"      {tabella}: {quante} righe nell'export, 0 nel DB")
        print("\n    L'export è la sola copia su GitHub di hub.db, che git non segue:")
        print("    scriverlo ora cancellerebbe quei dati anche dal backup.")
        print(f"    La versione buona è ancora in {os.path.relpath(USCITA, RADICE)},")
        print("    e le versioni precedenti si leggono con `git log` su quel file.")
        print("\n    Se il vuoto è voluto:  python scripts/esporta_dati.py --anche-se-vuoto")
        return 1
    if cali:
        print(f"\n⚠️  Scrivo lo stesso ({', '.join(t for t, _ in cali)} a zero): --anche-se-vuoto")

    if args.dry_run:
        print(f"\n--dry-run: {len(testo)} byte non scritti.")
        return 0

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
