#!/usr/bin/env python
"""Dà uno `slug` alle forme **vere** del catalogo che ne sono rimaste senza.

    python scripts/aggiungi_slug_forme.py [--dry-run]

Trovato il 13/09/2026. Le voci del catalogo senza elenco mosse sono **20 su 1343**
(specie più forme annidate), e `BACKLOG.md` le chiamava tutte «le 20 forme inventate,
che PokéAPI non conosce». Per **quattro non è vero**: il dump le conosce benissimo, ma
nel catalogo non hanno il campo `slug`, e `indice_catalogo()` in
`importa_mosse_specie.py` prende **solo** le voci che ce l'hanno. Quindi restavano
fuori dal moveset insieme alle Mega fan-made, e il sintomo era quello silenzioso di
sempre: `mosse_legali()` torna `None`, e a schermo compare l'avviso giallo «nessun
elenco mosse» invece delle 397 righe che il dump ha.

Le altre 16 sono Mega inventate da Davide e restano fuori: è giusto così, per loro una
fonte non esiste.

⚠️ **Non scrive uno slug alla cieca.** Per ogni voce il legame va **dimostrato**, non
supposto: le sei base stat del catalogo devono combaciare **esatte** con quelle che il
dump dà per quello slug. Uno slug plausibile ma sbagliato non darebbe un errore, darebbe
l'elenco mosse di un altro Pokémon — è esattamente la classe di baco che questo progetto
ha già pagato più volte. Se **una sola** voce non supera i controlli, non si scrive
**niente** e si esce con 1.

È rieseguibile: una voce che ha già lo slug atteso viene contata e saltata. La copia di
sicurezza la lascia `salva_catalogo()`, in `data/archive/`.

Dopo averlo eseguito va rifatto il moveset, che è il file che legge gli slug:

    python scripts/importa_mosse_specie.py
"""
import argparse
import collections
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

# La console di Windows e' cp1252 e non sa scrivere "Nidoran♀": senza questo il
# rapporto muore su UnicodeEncodeError dopo che il lavoro e' gia' stato fatto.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import pokeapi
from blueprints.pokemon import load_catalog, salva_catalogo

# Il nome della voce nel catalogo -> lo slug del dump. Le chiavi sono quelle con cui
# la voce e' gia' nominata altrove: la chiave del catalogo per le specie, il **nome
# della forma** per le forme annidate, che e' quello che `indice_catalogo()` usa.
SLUG_ATTESI = {
    "Gourgeist (Small)": "gourgeist-small",
    "Gourgeist (Large)": "gourgeist-large",
    "Gourgeist (Super)": "gourgeist-super",
    "eternal-flower-floette": "floette-eternal",
}

ORDINE_STAT = ("hp", "atk", "def", "spa", "spd", "spe")


def trova(catalogo, nome):
    """Dove sta `nome`: `(dizionario_della_voce, dove_lo_dico)`, o `(None, motivo)`.

    Cerca prima fra le chiavi di primo livello, poi fra i nomi delle forme annidate.
    Se lo stesso nome comparisse in **due** posti si ferma invece di sceglierne uno:
    con un doppione la voce giusta non la sa nessuno.
    """
    trovate = []
    if nome in catalogo:
        trovate.append((catalogo[nome], f"specie «{nome}»"))
    for chiave, dati in catalogo.items():
        forma = (dati.get("forms") or {}).get(nome)
        if forma is not None:
            trovate.append((forma, f"forma «{nome}» sotto «{chiave}»"))
    if not trovate:
        return None, "non esiste nel catalogo"
    if len(trovate) > 1:
        return None, f"compare in {len(trovate)} posti: " + " / ".join(d for _, d in trovate)
    return trovate[0]


def stat_del_dump():
    """`pokemon_id` -> le sei base stat con le chiavi del catalogo."""
    ordine = {r["id"]: r["identifier"] for r in pokeapi.leggi("stats.csv")}
    fuori = collections.defaultdict(dict)
    for r in pokeapi.leggi("pokemon_stats.csv"):
        chiave = pokeapi.STAT_CATALOGO.get(ordine.get(r["stat_id"]))
        if chiave:
            fuori[r["pokemon_id"]][chiave] = int(r["base_stat"])
    return dict(fuori)


def slug_gia_usati(catalogo):
    """Quale slug e' gia' scritto su quali voci. Serve a **dirlo**, non a vietarlo."""
    per_slug = collections.defaultdict(list)
    for chiave, dati in catalogo.items():
        if dati.get("slug"):
            per_slug[dati["slug"]].append(chiave)
        for nome_forma, forma in (dati.get("forms") or {}).items():
            if forma.get("slug"):
                per_slug[forma["slug"]].append(nome_forma)
    return per_slug


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    mancanti = pokeapi.file_mancanti()
    if mancanti:
        print("Il dump non e' in cache: manca " + ", ".join(mancanti))
        print("Si scarica con `python -c \"import pokeapi; pokeapi.scarica_mancanti()\"`")
        return 1

    catalogo = load_catalog("pokemon")
    if not catalogo:
        print("Catalogo vuoto o illeggibile: non tocco niente.")
        return 1

    per_slug_dump = {r["identifier"]: r["id"] for r in pokeapi.leggi("pokemon.csv")}
    stat = stat_del_dump()
    righe_mosse = collections.Counter(r["pokemon_id"]
                                      for r in pokeapi.leggi("pokemon_moves.csv"))
    usati = slug_gia_usati(catalogo)

    da_scrivere, gia_fatte, problemi, condivisi = [], [], [], []

    for nome, slug in SLUG_ATTESI.items():
        voce, dove = trova(catalogo, nome)
        if voce is None:
            problemi.append(f"{nome}: {dove}")
            continue

        presente = voce.get("slug")
        if presente == slug:
            gia_fatte.append(f"{nome} ({dove}) ha gia' slug «{slug}»")
            continue
        if presente:
            problemi.append(f"{nome}: ha gia' lo slug «{presente}», che non e' «{slug}». "
                            "Non lo sovrascrivo.")
            continue

        pid = per_slug_dump.get(slug)
        if not pid:
            problemi.append(f"{nome}: lo slug «{slug}» nel dump non esiste")
            continue

        atteso = stat.get(pid) or {}
        nostro = voce.get("base_stats") or {}
        diverse = [k for k in ORDINE_STAT if atteso.get(k) != nostro.get(k)]
        if diverse or len(atteso) != 6:
            dettaglio = ", ".join(f"{k}: catalogo {nostro.get(k)} / dump {atteso.get(k)}"
                                  for k in (diverse or ORDINE_STAT))
            problemi.append(f"{nome}: le base stat non combaciano con «{slug}» ({dettaglio})")
            continue

        n = righe_mosse.get(pid, 0)
        if not n:
            problemi.append(f"{nome}: «{slug}» nel dump non ha nessuna riga di mosse. "
                            "Scriverlo non servirebbe a niente.")
            continue

        altri = [x for x in usati.get(slug, []) if x != nome]
        if altri:
            condivisi.append(f"{nome} condivide lo slug «{slug}» con: " + ", ".join(altri))
        da_scrivere.append((nome, voce, slug, dove, n))

    for riga in gia_fatte:
        print("= " + riga)
    for nome, _, slug, dove, n in da_scrivere:
        print(f"+ {dove}: slug «{slug}» — {n} righe di mosse nel dump, base stat combaciate 6 su 6")
    for riga in condivisi:
        print("! " + riga)
    for riga in problemi:
        print("X " + riga)

    if problemi:
        print(f"\n{len(problemi)} voci non superano i controlli: non scrivo niente.")
        return 1

    if not da_scrivere:
        print("\nNiente da fare: tutte le voci hanno gia' il loro slug.")
        return 0

    if args.dry_run:
        print(f"\n--dry-run: {len(da_scrivere)} slug da scrivere, file non toccato.")
        return 0

    for _, voce, slug, _, _ in da_scrivere:
        voce["slug"] = slug
    salva_catalogo("pokemon", catalogo)
    print(f"\nScritti {len(da_scrivere)} slug in data/catalog/pokemon.json "
          "(copia precedente in data/archive/).")
    print("Ora il moveset: python scripts/importa_mosse_specie.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
