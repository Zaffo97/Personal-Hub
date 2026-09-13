#!/usr/bin/env python
"""Fonde le due voci di Floette Fiore Eterno, che nel catalogo stava due volte.

    python scripts/fondi_floette_doppione.py [--dry-run]

Trovato il 13/09/2026 sistemando gli slug. Lo stesso Pokémon stava nel catalogo in due
posti, con le **stesse sei base stat** e lo **stesso slug** `floette-eternal`:

- `eternal-flower-floette`, chiave di **primo livello** (`name`: «Eternal Flower
  Floette»), con `abilities: []` — e con **Mega Floette** annidata fra le sue `forms`
- `floette` → `Floette (Eternal Flower)`, forma **annidata**, con le sue abilità

⚠️ **Non è un'ambiguità di nome**: i due nomi sono diversi, quindi `indiceNomi()` non ha
niente da dirimere e `controlla_abilita.py` non lo vede. È una voce di troppo, che in
`pokedex` si vedeva due volte nel roster.

QUALE DELLE DUE RESTA, e perché non è una scelta di gusto: resta la **forma annidata**.
La voce di primo livello è un residuo di `data/pokemon_catalog.json`, il catalogo
vecchio; la forma annidata è quella che **`build_catalog.py` produce dal dump**. Tenere
il primo livello vorrebbe dire che alla prossima esecuzione di `build_catalog.py` il
doppione **rinasce**, perché quello script la forma la rigenera comunque.

COSA SPOSTA:

1. **Mega Floette** trasloca sotto `floette`, identica a com'era: le sue `base_stats`
   se le porta dietro, quindi il calcolatore non cambia di un punto — una Mega non
   eredita i numeri dalla voce che la ospita
2. la chiave `eternal-flower-floette` sparisce dal catalogo
3. in **`ma`** e **`mb`** il nome `Eternal Flower Floette` diventa
   `Floette (Eternal Flower)`, sia nell'elenco `pokemon` sia come chiave della
   `mega_map`. ⚠️ **Senza questo passo la fusione romperebbe due regulation**: quelle
   liste sono elenchi di **nomi**, e un nome che nel catalogo non esiste più non dà
   errore — sparisce e basta. In `pokedex` non c'è niente da cambiare: la sua `mega_map`
   dice già `Floette → Mega Floette`, che dopo la fusione è esattamente il verso giusto

⚠️ **Si rifiuta di lavorare alla cieca.** Le due voci devono avere le stesse sei base
stat e lo stesso slug — è la prova che sono lo stesso Pokémon e non due voci simili — e
nessun membro di team salvato deve citare la voce che sparisce. Se un controllo non
passa non si scrive niente e si esce con 1.

Rieseguibile: a fusione già fatta dice «niente da fare». Le copie di sicurezza le
lasciano `salva_catalogo()` per il catalogo e questo script per i due filtri, tutte in
`data/archive/`.

Dopo va rifatto il moveset, che ha ancora una voce intestata alla chiave sparita:

    python scripts/importa_mosse_specie.py
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import load_catalog, salva_catalogo

DATA = os.path.join(RADICE, "data")
ARCHIVIO = os.path.join(DATA, "archive")

# La voce che sparisce e quella che resta. `VECCHIO_NOME` e' il testo con cui le
# regulation la citano: gli elenchi sono di **nomi**, non di chiavi.
CHIAVE_DA_TOGLIERE = "eternal-flower-floette"
VECCHIO_NOME = "Eternal Flower Floette"
SPECIE_CHE_OSPITA = "floette"
NUOVO_NOME = "Floette (Eternal Flower)"
FORMA_DA_SPOSTARE = "Mega Floette"

REGULATION_DA_SISTEMARE = ("ma", "mb")
ORDINE_STAT = ("hp", "atk", "def", "spa", "spd", "spe")


def filtro_percorso(reg_id):
    return os.path.join(DATA, "regulations", f"{reg_id}.json")


def team_che_citano(nomi):
    """I membri di team salvati che citano uno di questi nomi. Vuoto = si puo'."""
    percorso = os.path.join(RADICE, "hub.db")
    if not os.path.exists(percorso):
        return []
    db = sqlite3.connect(percorso)
    try:
        righe = db.execute("SELECT id, team_id, pokemon FROM team_members").fetchall()
    finally:
        db.close()
    return [r for r in righe if r[2] in nomi]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    catalogo = load_catalog("pokemon")
    if not catalogo:
        print("Catalogo vuoto o illeggibile: non tocco niente.")
        return 1

    vecchia = catalogo.get(CHIAVE_DA_TOGLIERE)
    ospite = catalogo.get(SPECIE_CHE_OSPITA)
    if ospite is None:
        print(f"X la specie «{SPECIE_CHE_OSPITA}» non esiste nel catalogo.")
        return 1
    forme_ospite = ospite.get("forms") or {}

    # --- gia' fatto? ---------------------------------------------------------
    if vecchia is None:
        if FORMA_DA_SPOSTARE in forme_ospite:
            print(f"= «{CHIAVE_DA_TOGLIERE}» non c'e' piu' e «{FORMA_DA_SPOSTARE}» e' "
                  f"gia' sotto «{SPECIE_CHE_OSPITA}»: niente da fare sul catalogo.")
        else:
            print(f"X «{CHIAVE_DA_TOGLIERE}» non c'e' piu' ma «{FORMA_DA_SPOSTARE}» non "
                  f"e' sotto «{SPECIE_CHE_OSPITA}»: la fusione e' a meta', non proseguo.")
            return 1
    else:
        # --- le due voci sono davvero lo stesso Pokemon? ----------------------
        resta = forme_ospite.get(NUOVO_NOME)
        if resta is None:
            print(f"X la forma «{NUOVO_NOME}» non esiste sotto «{SPECIE_CHE_OSPITA}»: "
                  "non c'e' nessun doppione da fondere.")
            return 1

        sa, sb = vecchia.get("base_stats") or {}, resta.get("base_stats") or {}
        diverse = [k for k in ORDINE_STAT if sa.get(k) != sb.get(k)]
        if diverse:
            print("X le due voci NON hanno le stesse base stat: " + ", ".join(
                f"{k}: {VECCHIO_NOME} {sa.get(k)} / {NUOVO_NOME} {sb.get(k)}" for k in diverse))
            print("  Non sono lo stesso Pokemon, o una delle due e' sbagliata: non fondo niente.")
            return 1
        if vecchia.get("slug") != resta.get("slug"):
            print(f"X slug diversi: «{vecchia.get('slug')}» contro «{resta.get('slug')}». "
                  "Non fondo niente.")
            return 1

        if FORMA_DA_SPOSTARE in forme_ospite:
            print(f"X «{FORMA_DA_SPOSTARE}» e' gia' sotto «{SPECIE_CHE_OSPITA}» e la "
                  f"vecchia voce esiste ancora: stato incoerente, non proseguo.")
            return 1
        if FORMA_DA_SPOSTARE not in (vecchia.get("forms") or {}):
            print(f"X «{FORMA_DA_SPOSTARE}» non e' fra le forme di «{CHIAVE_DA_TOGLIERE}»: "
                  "non so cosa spostare.")
            return 1

        citanti = team_che_citano({VECCHIO_NOME, CHIAVE_DA_TOGLIERE})
        if citanti:
            print(f"X {len(citanti)} membri di team salvati citano la voce che sparirebbe:")
            for i, tid, nome in citanti:
                print(f"    membro {i} (team {tid}): «{nome}»")
            print("  Vanno rinominati prima, altrimenti la squadra perde un Pokemon in silenzio.")
            return 1

        print(f"+ base stat identiche 6 su 6 e stesso slug «{resta.get('slug')}»: "
              "sono lo stesso Pokemon")
        print(f"+ «{FORMA_DA_SPOSTARE}» trasloca sotto «{SPECIE_CHE_OSPITA}»")
        print(f"+ la chiave «{CHIAVE_DA_TOGLIERE}» sparisce dal catalogo")
        print(f"+ 0 membri di team salvati la citano")

    # --- le regulation che citano il vecchio nome ----------------------------
    da_sistemare = []
    for reg_id in REGULATION_DA_SISTEMARE:
        percorso = filtro_percorso(reg_id)
        if not os.path.exists(percorso):
            print(f"X il filtro di «{reg_id}» non esiste: {percorso}")
            return 1
        with open(percorso, encoding="utf-8") as f:
            filtro = json.load(f)
        elenco = filtro.get("pokemon")
        mega_map = filtro.get("mega_map") or {}
        nel_elenco = isinstance(elenco, list) and VECCHIO_NOME in elenco
        nella_mappa = VECCHIO_NOME in mega_map
        if not nel_elenco and not nella_mappa:
            print(f"= «{reg_id}» non cita «{VECCHIO_NOME}»: niente da cambiare")
            continue
        if isinstance(elenco, list) and NUOVO_NOME in elenco and nel_elenco:
            print(f"X «{reg_id}» cita **tutti e due** i nomi: la fusione creerebbe un "
                  "doppione nell'elenco. Va guardato a mano.")
            return 1
        da_sistemare.append((reg_id, percorso, filtro, nel_elenco, nella_mappa))
        print(f"+ «{reg_id}»: elenco={'si' if nel_elenco else 'no'} "
              f"mega_map={'si' if nella_mappa else 'no'} -> «{NUOVO_NOME}»")

    if vecchia is None and not da_sistemare:
        print("\nNiente da fare: la fusione e' gia' stata fatta.")
        return 0

    if args.dry_run:
        print("\n--dry-run: niente scritto.")
        return 0

    os.makedirs(ARCHIVIO, exist_ok=True)

    # --- catalogo ------------------------------------------------------------
    if vecchia is not None:
        forme_ospite[FORMA_DA_SPOSTARE] = (vecchia.get("forms") or {})[FORMA_DA_SPOSTARE]
        ospite["forms"] = forme_ospite
        del catalogo[CHIAVE_DA_TOGLIERE]
        salva_catalogo("pokemon", catalogo)
        print(f"\nCatalogo scritto: {len(catalogo)} specie "
              "(copia precedente in data/archive/).")

    # --- filtri delle regulation --------------------------------------------
    for reg_id, percorso, filtro, nel_elenco, nella_mappa in da_sistemare:
        copia = os.path.join(ARCHIVIO, f"regulation_{reg_id}_pre-fusione-floette.json")
        shutil.copy(percorso, copia)

        prima = len(filtro.get("pokemon") or [])
        if nel_elenco:
            filtro["pokemon"] = sorted(NUOVO_NOME if n == VECCHIO_NOME else n
                                       for n in filtro["pokemon"])
            dopo = len(filtro["pokemon"])
            if dopo != prima:
                print(f"X «{reg_id}»: l'elenco e' passato da {prima} a {dopo} nomi. "
                      "Rimetti la copia da data/archive/ e guarda a mano.")
                return 1
        if nella_mappa:
            mm = filtro["mega_map"]
            mm[NUOVO_NOME] = mm.pop(VECCHIO_NOME)
            filtro["mega_map"] = {k: mm[k] for k in sorted(mm)}
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(filtro, f, ensure_ascii=False, indent=2)
        print(f"«{reg_id}» aggiornata: {prima} nomi prima e dopo "
              f"(copia in data/archive/regulation_{reg_id}_pre-fusione-floette.json).")

    print("\nOra il moveset: python scripts/importa_mosse_specie.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
