#!/usr/bin/env python
"""Il catalogo modificato dall'editor deve vedersi **subito**, senza riavviare l'app.

    python scripts/prova_catalogo_vivo.py

Gira su una **copia** di `data/catalog/`, mai sui file veri.

⚠️ Perché esiste. Fino al 21/08/2026 `POKEMON_CATALOG` e `_INDICE` in
`blueprints/api_pokemon.py` erano caricati **una volta sola all'avvio**. Misurato:

- un Pokémon aggiunto dall'editor **compariva nel roster** della regulation, che
  rilegge il file ogni volta, e `/api/pokemon/<nome>` rispondeva **404**: nell'elenco
  c'era, e aprendolo non esisteva
- cambiando una base stat, il file diceva 999 e l'API continuava a rispondere 115
  **senza nessun errore** — il calcolatore faceva i conti col valore vecchio. È la
  classe di baco che questo progetto paga di più: non un errore, un numero sbagliato

La cura è il pattern che il progetto già usa per `_MOVESET` e `_TRADUZIONI`: la copia
in memoria segue l'mtime del file. Queste prove servono a non tornare indietro.
"""
import json
import os
import shutil
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


NUOVO = "Provamon"
VOCE = {"name": NUOVO, "nome_it": "Provamon", "nome_en": "Provamon", "types": ["fire"],
        "base_stats": {"hp": 80, "atk": 100, "def": 70, "spatk": 90, "spdef": 70, "spe": 110},
        "abilities": ["Blaze"]}


def prove(dove):
    catalogo = os.path.join(dove, "catalog")
    shutil.copytree(os.path.join(RADICE, "data", "catalog"), catalogo)

    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()

    import blueprints.pokemon as P
    import blueprints.api_pokemon as A
    # ⚠️ Tutti e due i moduli devono guardare la copia: se uno dei due leggesse i
    # file veri, il risultato di questa prova non direbbe niente.
    P.CATALOG_DIR = catalogo
    P.MOVESET_FILE = os.path.join(catalogo, "pokemon_moves.json")
    P._MOVESET["mtime"] = None
    # ⚠️ **Anche l'archivio**, e la prima volta me ne sono dimenticato: `salva_catalogo()`
    # tiene da parte la versione precedente in `data/archive/`, e senza questa riga una
    # prova che salva voci finte **sovrascrive la copia di sicurezza vera** —
    # `catalog_pokemon_pre-salvataggio.json` si è ritrovato dentro `Provamon` e un
    # Incineroar da 999 di attacco. Il catalogo non era stato toccato, ma la rete sì.
    # Stessa lezione del 16/08, un piano più in là: non basta deviare i file che il test
    # legge, vanno deviati anche quelli che il **codice sotto prova** scrive.
    archivio = os.path.join(dove, "archive")
    os.makedirs(archivio, exist_ok=True)
    P._archive_dir = lambda: archivio
    A.PERCORSI_CATALOGO = (os.path.join(catalogo, "pokemon.json"),)
    A.aggiorna_catalogo(forza=True)

    import app as m
    m.app.config["TESTING"] = True
    with m.app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "admin"
            s["role"] = "admin"

        esito("controllo: un Pokémon che c'è già si carica",
              c.get("/api/pokemon/Incineroar?reg=pokedex").status_code == 200)

        # --- 1. una voce nuova si vede subito -------------------------------
        r = c.post("/pokemon/api/catalogo/pokemon/salva",
                   json={"nome": NUOVO, "voce": VOCE})
        esito("l'editor salva la voce nuova", r.status_code == 200)
        r = c.get(f"/api/pokemon/{NUOVO}?reg=pokedex")
        j = r.get_json() or {}
        esito("la voce nuova si carica SENZA riavviare l'app",
              r.status_code == 200 and j.get("stats", {}).get("atk") == 100,
              f"{r.status_code}, atk={j.get('stats', {}).get('atk')}")

        # ⚠️ Il roster la mostrava già prima della correzione: è il confronto che
        # rendeva il baco visibile — nell'elenco sì, aprendola no.
        roster = (c.get("/api/regulation/pokedex/data").get_json() or {}).get("roster") or []
        esito("e compare nel roster, come già faceva", NUOVO in roster)

        # --- 2. una stat modificata si vede subito --------------------------
        su_disco = json.load(open(os.path.join(catalogo, "pokemon.json"), encoding="utf-8"))
        chiave = next(k for k in su_disco if k.lower() == "incineroar")
        prima = c.get(f"/api/pokemon/{chiave}?reg=pokedex").get_json()["stats"]["atk"]
        voce = dict(su_disco[chiave])
        voce["base_stats"] = dict(voce["base_stats"], atk=999)
        c.post("/pokemon/api/catalogo/pokemon/salva",
               json={"nome": chiave, "voce": voce, "nome_originale": chiave})
        dopo = c.get(f"/api/pokemon/{chiave}?reg=pokedex").get_json()["stats"]["atk"]
        esito("una base stat modificata arriva al calcolatore subito",
              prima == 115 and dopo == 999, f"{prima} → {dopo}")

        # --- 3. una voce eliminata sparisce ---------------------------------
        c.post("/pokemon/api/catalogo/pokemon/elimina", json={"nome": NUOVO})
        esito("una voce eliminata torna a dare 404",
              c.get(f"/api/pokemon/{NUOVO}?reg=pokedex").status_code == 404)

        # --- 4. il costo: senza modifiche non si rilegge niente -------------
        esito("a file fermo non ricarica (è una stat(), non una rilettura)",
              A.aggiorna_catalogo() is False)

        # --- 5. un file rotto non svuota la copia buona ---------------------
        # ⚠️ Il verso giusto: meglio il catalogo di un minuto fa che un catalogo
        # vuoto, che qui vorrebbe dire 404 su **ogni** Pokémon.
        quante = len(A.POKEMON_CATALOG)
        with open(os.path.join(catalogo, "pokemon.json"), "w", encoding="utf-8") as f:
            f.write("{ questo non è JSON")
        A.aggiorna_catalogo()
        esito("un file illeggibile NON svuota la copia in memoria",
              len(A.POKEMON_CATALOG) == quante, f"{len(A.POKEMON_CATALOG)} voci ancora in mano")
        esito("e i Pokémon continuano a rispondere",
              c.get("/api/pokemon/Amoonguss?reg=pokedex").status_code == 200)

        # --- 6. e queste prove non hanno toccato niente di vero -------------
        vero = os.path.join(RADICE, "data", "catalog", "pokemon.json")
        copia_vera = os.path.join(RADICE, "data", "archive",
                                  "catalog_pokemon_pre-salvataggio.json")
        catalogo_vero = json.load(open(vero, encoding="utf-8"))
        archivio_vero = json.load(open(copia_vera, encoding="utf-8"))
        esito("il catalogo vero non è stato toccato",
              NUOVO not in catalogo_vero, f"{len(catalogo_vero)} voci")
        esito("e nemmeno la sua copia di sicurezza vera",
              NUOVO not in archivio_vero, f"{len(archivio_vero)} voci")


def main():
    dove = tempfile.mkdtemp(prefix="prova_catalogo_")
    print(f"Prove in {dove}\n")
    try:
        prove(dove)
    finally:
        shutil.rmtree(dove, ignore_errors=True)
    print()
    quante = sum(esiti)
    print(f"{quante} prove su {len(esiti)}." +
          ("  Tutte passate." if quante == len(esiti) else "  FALLITE."))
    return 0 if quante == len(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
