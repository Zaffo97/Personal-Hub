#!/usr/bin/env python
"""Esporta il contenuto di `hub.db` in un JSON committabile, o in un backup completo.

    python scripts/esporta_dati.py [--dry-run]
    python scripts/esporta_dati.py --completo --uscita <percorso fuori dal repo>

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

── `--completo`, dal 18/09/2026 (§1.4 del backlog) ──────────────────────────────

Un backup che non contiene le password **non è un backup**: è proprio la parte che il
ripristino non sa rimettere. Quindi esistono **due export, non uno**, e la differenza
non è un'opzione fra le altre — è la ragione per cui questo file può stare in git.

`--completo` scrive **tutto**: gli hash delle password e la tabella `regulations`, che
l'export normale omette. Per questo **pretende `--uscita`** e si **rifiuta** di scrivere
in una cartella versionata: risale l'albero dalla destinazione cercando un `.git`, e se
lo trova non scrive niente. È l'unico modo perché la distinzione non salti per
distrazione — un percorso di default dentro al repo verrebbe committato la prima volta
che qualcuno fa `git add -A` senza guardare.

Cosa resta fuori anche dal completo, e perché:

- **`game_releases`**, la cache del calendario IGDB: 6007 righe rigenerabili col
  pulsante della sezione Gaming. Non è un dato tuo, è una copia di un servizio
- il **tema** (in `localStorage`) e la **lingua** (nel cookie `hub_lang`): non sono nel
  DB, quindi nessun export potrà prenderli finché non diventano colonne di `users`

Il ritorno è `scripts/importa_dati.py --file <quel percorso>`, che era già pronto a
rileggerlo: le password entrano **solo** per gli utenti nuovi e non sovrascrivono mai
quelle esistenti.
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
    # ⚠️ Fantacalcio, dal 21/09/2026. Le **leghe** e le **rose** sono dati tuoi e
    # non li ricostruisce nessuna fonte: le regole di una lega e il prezzo pagato per
    # ogni giocatore esistono solo qui. `fanta_players` invece **non** c'è, ed è
    # voluto: è il listone, cioè una copia di fantacalcio.it che si rifà in un minuto
    # con `scripts/importa_listone.py` — stessa ragione per cui resta fuori la cache
    # IGDB. ⚠️ La conseguenza da sapere: ripristinando su un DB vuoto, le rose
    # puntano a giocatori che ancora non ci sono, quindi il listone va reimportato
    # **prima**.
    "fanta_leagues", "fanta_roster",
]

# In più, solo con `--completo`. `regulations` è una **tabella morta** — la scrive solo
# `init_db()` e non la legge nessuno, le regulation vivono in `data/regulations/*.json`
# dal 10/08/2026 — ma un backup completo la porta lo stesso: dire «completo» e lasciare
# fuori una tabella per giudizio proprio è il modo di scoprire il buco quando serve.
TABELLE_SOLO_COMPLETO = ["regulations"]

# Escluse **sempre**, anche dal completo, e ognuna con la sua ragione (vedi il docstring).
FUORI_DAL_BACKUP = {"game_releases": "cache IGDB, si rifà col pulsante"}


def dentro_a_un_repo(percorso):
    """La cartella che conterrà `percorso` sta dentro un repo git? Torna la radice.

    ⚠️ È la rete che tiene in piedi la distinzione fra i due export. Il completo
    contiene gli **hash delle password**: se finisse in una cartella versionata
    basterebbe un `git add -A` distratto per pubblicarli, ed è esattamente il buco per
    cui `hub.db` non è in git. Si risale l'albero perché non conta solo *questo* repo:
    qualunque cartella versionata va bene per sbagliare.
    """
    cartella = os.path.dirname(os.path.abspath(percorso)) or os.getcwd()
    while True:
        if os.path.exists(os.path.join(cartella, ".git")):
            return cartella
        genitore = os.path.dirname(cartella)
        if genitore == cartella:
            return None
        cartella = genitore


def leggibile(percorso):
    """Il percorso relativo alla radice se ci sta dentro, altrimenti quello intero."""
    try:
        dentro = os.path.relpath(percorso, RADICE)
    except ValueError:                   # su Windows: unità diverse
        return percorso
    return dentro if not dentro.startswith("..") else percorso


def uguali_a_meno_del_meta(precedente, documento):
    """I dati sono gli stessi del file già sul disco, a parte il blocco `_meta`?"""
    try:
        prima = json.loads(precedente)
    except Exception:
        return False
    senza = {k: v for k, v in documento.items() if not k.startswith("_")}
    return {k: v for k, v in prima.items() if not k.startswith("_")} == senza


def righe(db, tabella, escluse=None):
    """Le righe di una tabella, in ordine stabile, senza le colonne escluse.

    `escluse` è `ESCLUSE` per l'export committabile e `{}` per `--completo`: la
    differenza fra i due file è **solo** questo dizionario e due tabelle in più.

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
    fuori = (ESCLUSE if escluse is None else escluse).get(tabella, set())
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
    ap.add_argument("--completo", action="store_true",
                    help="backup vero: password e `regulations` comprese. Pretende "
                         "--uscita, e rifiuta una cartella versionata")
    ap.add_argument("--uscita", help="dove scrivere il backup completo")
    # Simmetrico a `importa_dati.py --db`, e serve alle prove: senza, l'unico modo di
    # provare l'export sarebbe leggere `hub.db` vero.
    ap.add_argument("--db", default=DB, help="DB da leggere (default: hub.db)")
    args = ap.parse_args()

    if args.uscita and not args.completo:
        print("--uscita vale solo con --completo: l'export committabile ha un posto")
        print(f"    solo, {os.path.relpath(USCITA, RADICE)}, ed è quello che git segue.")
        return 1

    tabelle = TABELLE + (TABELLE_SOLO_COMPLETO if args.completo else [])
    destinazione = USCITA
    if args.completo:
        if not args.uscita:
            print("⚠️  --completo pretende --uscita: questo file contiene gli hash")
            print("    delle password e non deve finire in una cartella versionata.")
            print("\n    Esempio:  python scripts/esporta_dati.py --completo \\")
            print("                     --uscita D:/Backup/hub_completo.json")
            return 1
        destinazione = os.path.abspath(args.uscita)
        repo = dentro_a_un_repo(destinazione)
        if repo:
            print("⚠️  INTERROTTO: la destinazione sta dentro un repository git.")
            print(f"      destinazione: {destinazione}")
            print(f"      repo trovato: {repo}")
            print("\n    Il backup completo contiene gli **hash delle password**: è la")
            print("    stessa ragione per cui hub.db non è versionato. Scegli una")
            print("    cartella fuori da qualunque repo — una chiavetta, il disco di")
            print("    backup, una cartella sincronizzata che non sia un checkout.")
            return 1

    if not os.path.exists(args.db):
        print(f"DB non trovato in {args.db}: niente da esportare.")
        return 1

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    dati, mancanti = {}, []
    for t in tabelle:
        r = righe(db, t, {} if args.completo else ESCLUSE)
        if r is None:
            mancanti.append(t)
        else:
            dati[t] = r
    db.close()

    if not dati:
        print("Nessuna tabella leggibile: non sovrascrivo l'export esistente.")
        return 1

    documento = dati
    if args.completo:
        # Il timestamp qui si può: questo file **non** è committato, quindi non c'è
        # nessun diff da tenere leggibile — e di un backup la data è la prima cosa che
        # serve sapere. `importa_dati.py` salta le chiavi che cominciano per `_`.
        documento = {"_meta": {
            "generato": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
            "generato_da": "scripts/esporta_dati.py --completo",
            "db": args.db,
            "password_incluse": True,
            "fuori_dal_backup": FUORI_DAL_BACKUP,
        }, **dati}
    testo = json.dumps(documento, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    for t in tabelle:
        if t in dati:
            print(f"  {t:<18} {len(dati[t]):>5} righe")
    if mancanti:
        print(f"  (tabelle assenti nel DB: {', '.join(mancanti)})")
    if args.completo:
        print(f"  {'users.password':<18} {'':>5} inclusa")
        for t, perche in FUORI_DAL_BACKUP.items():
            print(f"  (fuori anche dal completo: {t} — {perche})")

    precedente = None
    if os.path.exists(destinazione):
        with io.open(destinazione, encoding="utf-8") as f:
            precedente = f.read()

    cali = cali_sospetti(dati, precedente)
    if cali and not args.anche_se_vuoto:
        print("\n⚠️  INTERROTTO: una tabella è passata da righe a ZERO.")
        for tabella, quante in cali:
            print(f"      {tabella}: {quante} righe nell'export, 0 nel DB")
        print("\n    L'export è la sola copia di hub.db, che git non segue:")
        print("    scriverlo ora cancellerebbe quei dati anche dal backup.")
        print(f"    La versione buona è ancora in {leggibile(destinazione)},")
        if not args.completo:
            print("    e le versioni precedenti si leggono con `git log` su quel file.")
        print("\n    Se il vuoto è voluto, rilancia con --anche-se-vuoto")
        return 1
    if cali:
        print(f"\n⚠️  Scrivo lo stesso ({', '.join(t for t, _ in cali)} a zero): --anche-se-vuoto")

    if args.dry_run:
        print(f"\n--dry-run: {len(testo)} byte non scritti in {leggibile(destinazione)}.")
        return 0

    if precedente == testo:
        print(f"\nNessuna differenza: {leggibile(destinazione)} è già aggiornato.")
        return 0
    if args.completo and precedente and uguali_a_meno_del_meta(precedente, documento):
        # Con `--completo` il confronto sopra non scatta mai, perché `_meta` porta
        # l'ora. Dirlo è meglio che lasciar credere che i dati siano cambiati.
        print("\n(dati identici al backup precedente: cambia solo la data in `_meta`)")

    cartella = os.path.dirname(destinazione)
    if cartella:
        os.makedirs(cartella, exist_ok=True)
    with io.open(destinazione, "w", encoding="utf-8") as f:
        f.write(testo)
    print(f"\nScritto {leggibile(destinazione)} — {len(testo)} byte.")
    if args.completo:
        print("⚠️  Contiene gli hash delle password: tienilo dove tieni le cose tue,")
        print("    non in una cartella che finisce su GitHub.")
        print(f"    Ritorno:  python scripts/importa_dati.py --file {destinazione}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
