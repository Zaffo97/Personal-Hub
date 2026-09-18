#!/usr/bin/env python
"""Riallinea l'elenco `moves` di una regulation al moveset che la regulation usa.

    python scripts/allinea_mosse_regulation.py [--reg ma,mb] [--dry-run] [--forza]

Decisione di Davide del 18/09/2026: «i cataloghi saranno sempre di Champions, quindi
la lista mosse sarà sempre quella in relazione alla regulation». L'elenco non è più
un dato da curare a mano: si **deriva** dall'unione delle mosse che il roster della
regulation può imparare, secondo la sorgente moveset dichiarata in `regulations.json`
(`champions` per MA e MB, `main` per le altre).

Perché serviva. Il `moves` di MA e MB erano le 460 chiavi di `data/moves_ma.json`
(04/05/2026, «PokeAPI + patch Champions Reg M-A»), diventate il filtro l'11/08 con la
costruzione del catalogo. Non erano l'elenco delle mosse legali in Champions, e si
vede da due parti opposte: mancavano **Endure** e **Substitute**, che 332 voci di
Champions su 333 imparano, e c'erano 126 mosse che **nessuna** voce di Champions
impara, comprese le esclusive di Pokémon che nel gioco non ci sono (Behemoth Bash,
Bolt Beak, Defend Order). La tendina mosse del calcolatore è l'intersezione fra questo
elenco e quello del singolo Pokémon, quindi il filtro nascondeva mosse legali **senza
dirlo**: 3239 su 17219 in MA (18,8%), su **278 specie su 278**.

Cosa fa, in ordine:

1. per ogni regulation con un `filter_file` e un roster non nullo, chiama la
   `mosse_legali()` vera dell'app su ogni nome del roster e ne fa l'unione;
2. **si ferma** se una mossa dell'unione non ha una voce in `data/catalog/moves.json`
   — comparirebbe nella tendina senza nessun dato — o se l'unione esce vuota;
3. **si ferma** se una mossa che uscirebbe dall'elenco è usata da un team salvato in
   `hub.db`, a meno di `--forza`. Un team non si rompe (le sue mosse restano scritte),
   ma è il segno che l'elenco derivato non copre un caso reale, e va guardato;
4. lascia la copia del filtro precedente in `data/archive/regulation_<id>_pre-mosse.json`
   e scrive con `_salva_filtro()`, la stessa funzione che usa l'editor.

È rieseguibile: se l'elenco è già quello derivato non tocca il file e lo dice. Le
regulation con `pokemon: null` (oggi `pokedex`) vengono saltate: lì il roster è tutto
il catalogo e `moves: null` è già la risposta giusta.

⚠️ Va rilanciato **ogni volta che cambia il roster di una regulation o il moveset**:
un Pokémon aggiunto porta con sé le sue mosse, e finché non si rilancia quelle mosse
restano fuori dalla tendina in silenzio — che è esattamente il baco che questo script
chiude.
"""
import argparse
import json
import os
import shutil
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import (  # noqa: E402
    DATA_DIR, _list_regulation_files, _load_filtro, _salva_filtro,
    load_catalog, mosse_legali,
)


def mosse_dei_team():
    """{mossa: [team…]} per le mosse scritte nei team salvati, per regulation."""
    import sqlite3
    percorso = os.path.join(RADICE, "hub.db")
    if not os.path.exists(percorso):
        return {}
    uso = {}
    con = sqlite3.connect(percorso)
    try:
        righe = con.execute(
            "SELECT t.regulation_id, t.name, m.move1, m.move2, m.move3, m.move4 "
            "FROM team_members m JOIN teams t ON t.id = m.team_id").fetchall()
    except sqlite3.Error:
        return {}
    finally:
        con.close()
    for reg_id, nome_team, *mosse in righe:
        for mossa in mosse:
            if mossa:
                uso.setdefault((reg_id, mossa), set()).add(nome_team)
    return uso


def unione_roster(reg, filtro):
    """(unione, senza_lista, irrisolti) per il roster della regulation."""
    unione, senza_lista, irrisolti = set(), [], []
    catalogo = load_catalog("pokemon")
    for nome in filtro.get("pokemon") or []:
        elenco, _ = mosse_legali(nome, reg)
        if elenco is None:
            # Due casi diversi: il nome non esiste proprio nel catalogo (errore), o
            # esiste e non ha una lista per quella sorgente (forme inventate, voci
            # arrivate con la 1.2.0). Solo il primo è un problema.
            if nome not in catalogo and not any(
                    nome in (v.get("forms") or {}) for v in catalogo.values()):
                irrisolti.append(nome)
            else:
                senza_lista.append(nome)
            continue
        unione |= set(elenco)
    return unione, senza_lista, irrisolti


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reg", default="",
                    help="quali regulation, separate da virgola (default: tutte "
                         "quelle con un roster)")
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    ap.add_argument("--forza", action="store_true",
                    help="scrive anche se una mossa in uso in un team uscirebbe")
    args = ap.parse_args()

    volute = {r.strip() for r in args.reg.split(",") if r.strip()}
    uso_team = mosse_dei_team()
    catalogo_mosse = load_catalog("moves")
    if not catalogo_mosse:
        print("Catalogo mosse vuoto o illeggibile: non tocco niente.")
        return 1

    da_scrivere, problemi, scritte = [], [], 0
    for reg in _list_regulation_files():
        reg_id = reg["id"]
        if volute and reg_id not in volute:
            continue
        filtro = _load_filtro(reg)
        if filtro is None:
            if volute:
                problemi.append(f"{reg_id}: non ha un filter_file da aggiornare")
            continue
        if filtro.get("pokemon") is None:
            print(f"= {reg_id:8s} roster nullo (tutto il catalogo): salto, "
                  "`moves: null` è già giusto")
            continue

        sorgente = reg.get("moveset") or "main"
        unione, senza_lista, irrisolti = unione_roster(reg, filtro)
        if irrisolti:
            problemi.append(f"{reg_id}: {len(irrisolti)} nomi del roster non esistono "
                            f"nel catalogo: {', '.join(sorted(irrisolti)[:5])}")
            continue
        if not unione:
            problemi.append(f"{reg_id}: l'unione esce vuota (sorgente «{sorgente}»). "
                            "Non svuoto l'elenco.")
            continue
        senza_dato = sorted(unione - set(catalogo_mosse))
        if senza_dato:
            problemi.append(f"{reg_id}: {len(senza_dato)} mosse dell'unione non hanno "
                            f"una voce in catalog/moves.json: {', '.join(senza_dato[:5])}")
            continue

        attuale = set(filtro.get("moves") or [])
        entrano, escono = sorted(unione - attuale), sorted(attuale - unione)
        in_uso = [(m, sorted(uso_team[(reg_id, m)])) for m in escono
                  if (reg_id, m) in uso_team]

        print(f"\n== {reg_id} — sorgente moveset «{sorgente}», roster "
              f"{len(filtro['pokemon'])}")
        if senza_lista:
            print(f"   {len(senza_lista)} senza lista (mostrano tutto l'elenco): "
                  + ", ".join(sorted(senza_lista)))
        print(f"   elenco: {len(attuale)} -> {len(unione)}  "
              f"(+{len(entrano)} / -{len(escono)})")
        if entrano:
            print("   + " + ", ".join(entrano[:12])
                  + (f" … e altre {len(entrano) - 12}" if len(entrano) > 12 else ""))
        if escono:
            print("   - " + ", ".join(escono[:12])
                  + (f" … e altre {len(escono) - 12}" if len(escono) > 12 else ""))
        for mossa, team in in_uso:
            print(f"   ⚠️ «{mossa}» uscirebbe ed è in un team: {', '.join(team)}")
        if in_uso and not args.forza:
            problemi.append(f"{reg_id}: {len(in_uso)} mosse in uso in un team "
                            "uscirebbero dall'elenco. Guardale, poi --forza.")
            continue
        if not entrano and not escono:
            print("   = già allineato, non tocco il file")
            continue
        da_scrivere.append((reg, filtro, unione))

    for riga in problemi:
        print("X " + riga)
    if problemi:
        print(f"\n{len(problemi)} problemi: non scrivo niente.")
        return 1
    if not da_scrivere:
        print("\nNiente da fare: gli elenchi sono già derivati dal moveset.")
        return 0
    if args.dry_run:
        print(f"\n--dry-run: {len(da_scrivere)} regulation da aggiornare, "
              "nessun file toccato.")
        return 0

    archivio = os.path.join(DATA_DIR, "archive")
    os.makedirs(archivio, exist_ok=True)
    for reg, _filtro, unione in da_scrivere:
        origine = os.path.join(DATA_DIR, reg["filter_file"])
        copia = os.path.join(archivio, f"regulation_{reg['id']}_pre-mosse.json")
        shutil.copyfile(origine, copia)
        if not _salva_filtro(reg, "moves", unione):
            print(f"X {reg['id']}: _salva_filtro() non ha scritto.")
            return 1
        scritte += 1
        print(f"Scritto {reg['filter_file']}: {len(unione)} mosse "
              f"(copia precedente in data/archive/{os.path.basename(copia)})")
    print(f"\n{scritte} regulation aggiornate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
