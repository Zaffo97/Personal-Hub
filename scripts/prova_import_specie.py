#!/usr/bin/env python
"""Le prove dell'import di specie da PokéAPI (§1.3). Non tocca i file veri.

    python scripts/prova_import_specie.py

Gira su una **copia** di `data/catalog/` e di `data/regulations/`, con anche
`_archive_dir()` deviato — la lezione del 21/08: non bastano i file che il test
legge, vanno deviati anche quelli che il codice sotto prova **scrive**.

Cosa dimostra:

- l'anteprima non scrive niente, e dice **prima** cosa sovrascriverebbe
- la voce importata ha la forma delle 1026 già in catalogo, e si carica subito
  nel calcolatore (che è ciò che la correzione dell'mtime ha reso possibile)
- il moveset entra con **tutti e due** gli elenchi quando il dump li ha, e quando
  Champions non conosce la specie l'elenco **non si inventa**
- le `forms` annidate di una voce che esisteva non si perdono
- i tre casi che devono fermarlo: doppione con un'altra chiave, voce già presente
  senza conferma, forma invece di specie base
- la spunta «aggiungi anche a ma/mb» scrive davvero negli elenchi
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


# Una specie vera, presente in catalogo: la tolgo dalla copia per avere un caso
# «nuovo» realistico. ⚠️ Contato il 21/08: delle specie di default del dump ne
# mancano **quattro** al catalogo, e sono tutte già presenti sotto un'altra chiave —
# cioè oggi non c'è niente di davvero nuovo da importare, e questo import serve al
# giorno in cui il dump avrà specie che qui non ci sono.
CAVIA = "pawmot"


def prove(dove):
    # ⚠️ Si copia **anche `regulations/` e `regulations.json`**, e la prima volta me
    # n'ero dimenticato: la spunta «aggiungi anche a ma» passa da `_salva_filtro()`,
    # che scrive sotto `DATA_DIR` — cioè aveva riscritto il file **vero** di MA,
    # cambiandogli la data. Nessun nome perso, ma è la terza volta in due giorni che
    # un test tocca qualcosa di vero: quello che il codice sotto prova **scrive** va
    # cercato, non dedotto.
    dati = os.path.join(dove, "data")
    os.makedirs(dati, exist_ok=True)
    catalogo_dir = os.path.join(dati, "catalog")
    shutil.copytree(os.path.join(RADICE, "data", "catalog"), catalogo_dir)
    shutil.copytree(os.path.join(RADICE, "data", "regulations"),
                    os.path.join(dati, "regulations"))
    shutil.copy2(os.path.join(RADICE, "data", "regulations.json"),
                 os.path.join(dati, "regulations.json"))
    archivio = os.path.join(dove, "archive")
    os.makedirs(archivio, exist_ok=True)

    import extensions
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()

    import blueprints.pokemon as P
    import blueprints.api_pokemon as A
    P.DATA_DIR = dati
    P.CATALOG_DIR = catalogo_dir
    P.MOVESET_FILE = os.path.join(catalogo_dir, "pokemon_moves.json")
    P._MOVESET["mtime"] = None
    P._archive_dir = lambda: archivio
    A.PERCORSI_CATALOGO = (os.path.join(catalogo_dir, "pokemon.json"),)
    A.aggiorna_catalogo(forza=True)

    percorso_catalogo = os.path.join(catalogo_dir, "pokemon.json")

    def catalogo():
        with open(percorso_catalogo, encoding="utf-8") as f:
            return json.load(f)

    # tolgo la cavia dalla copia, così l'import ha qualcosa di nuovo da fare
    voci = catalogo()
    originale = voci.pop(CAVIA)
    with open(percorso_catalogo, "w", encoding="utf-8") as f:
        json.dump(voci, f, ensure_ascii=False, indent=2)
    A.aggiorna_catalogo(forza=True)

    # ...e la tolgo anche dal roster di MA, altrimenti la prova sulla spunta direbbe
    # «0 aggiunte» e passerebbe senza aver dimostrato niente.
    percorso_ma = os.path.join(dati, "regulations", "ma.json")
    with open(percorso_ma, encoding="utf-8") as f:
        filtro_ma = json.load(f)
    nome_visibile = originale.get("name")
    filtro_ma["pokemon"] = [n for n in filtro_ma["pokemon"] if n != nome_visibile]
    quanti_in_ma = len(filtro_ma["pokemon"])
    with open(percorso_ma, "w", encoding="utf-8") as f:
        json.dump(filtro_ma, f, ensure_ascii=False, indent=2)

    import app as m
    m.app.config["TESTING"] = True
    with m.app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "admin"
            s["role"] = "admin"

        esito("prima dell'import la cavia non si carica",
              c.get(f"/api/pokemon/{CAVIA}?reg=pokedex").status_code == 404)

        # --- 1. anteprima -----------------------------------------------------
        r = c.post("/pokemon/api/catalogo/pokemon/pesca", json={"nomi": ["Pawmot"]})
        j = r.get_json() or {}
        voce = (j.get("voci") or [{}])[0]
        esito("l'anteprima risponde con la voce",
              r.status_code == 200 and j.get("ok") and voce.get("chiave") == CAVIA)
        esito("l'anteprima porta stat, tipi e conteggio mosse",
              voce.get("base_stats", {}).get("atk") == 115
              and voce.get("types") == ["Elettro", "Lotta"]
              and voce.get("mosse_main") > 0,
              f"atk={voce.get('base_stats', {}).get('atk')} "
              f"main={voce.get('mosse_main')} champions={voce.get('mosse_champions')}")
        esito("Pawmot non è in Champions, e l'anteprima lo dichiara",
              voce.get("mosse_champions") == 0
              and any("Champions" in p["problema"] for p in j.get("problemi") or []))
        esito("l'anteprima NON ha scritto niente", CAVIA not in catalogo())

        # --- 2. import vero ---------------------------------------------------
        r = c.post("/pokemon/api/catalogo/pokemon/importa",
                   json={"nomi": ["Pawmot"], "regulation": ["ma"]})
        j = r.get_json() or {}
        esito("l'import scrive", r.status_code == 200 and j.get("ok")
              and j.get("scritte") == [CAVIA], str(j.get("scritte")))
        scritta = catalogo().get(CAVIA) or {}
        esito("la voce scritta è identica a quella che c'era",
              scritta == originale,
              "identica" if scritta == originale else
              f"differenze: {[k for k in set(scritta) | set(originale) if scritta.get(k) != originale.get(k)]}")
        r = c.get(f"/api/pokemon/{CAVIA}?reg=pokedex")
        esito("e si carica subito nel calcolatore, senza riavviare",
              r.status_code == 200 and (r.get_json() or {}).get("stats", {}).get("atk") == 115)

        with open(os.path.join(catalogo_dir, "pokemon_moves.json"), encoding="utf-8") as f:
            moveset = json.load(f)
        voce_mosse = (moveset.get("voci") or {}).get(CAVIA) or {}
        esito("il moveset è entrato con l'elenco `main`",
              len((voce_mosse.get("main") or {}).get("moves") or {}) > 0,
              f"{len((voce_mosse.get('main') or {}).get('moves') or {})} mosse")
        esito("e l'elenco `champions` NON è stato inventato",
              "champions" not in voce_mosse)
        esito("`_meta` del moveset non è stato buttato via",
              bool(moveset.get("_meta", {}).get("fonte")))

        # --- 3. la regulation -------------------------------------------------
        esito("la spunta «aggiungi a ma» ha aggiunto davvero una voce",
              (j.get("regulation") or {}).get("ma", "").startswith("1 aggiunte"),
              f"{quanti_in_ma} prima → {j.get('regulation', {}).get('ma')}")
        roster = (c.get("/api/regulation/ma/data").get_json() or {}).get("roster") or []
        esito("e in MA il Pokémon ora c'è", (originale.get("name") or "") in roster)

        # --- 4. le tre porte chiuse ------------------------------------------
        r = c.post("/pokemon/api/catalogo/pokemon/importa", json={"nomi": ["Pawmot"]})
        esito("reimportare una voce presente si ferma con 409",
              r.status_code == 409 and (r.get_json() or {}).get("gia_presenti") == [CAVIA])
        r = c.post("/pokemon/api/catalogo/pokemon/importa",
                   json={"nomi": ["Pawmot"], "sovrascrivi": True})
        esito("...e con `sovrascrivi` passa", r.status_code == 200)

        r = c.post("/pokemon/api/catalogo/pokemon/importa", json={"nomi": ["aegislash-shield"]})
        j = r.get_json() or {}
        esito("una voce già presente sotto un'altra chiave si ferma (doppione)",
              r.status_code == 409 and "aegislash-shield-forme"
              in (j.get("doppioni") or {}).values())

        r = c.post("/pokemon/api/catalogo/pokemon/pesca", json={"nomi": ["deoxys-attack"]})
        j = r.get_json() or {}
        esito("una forma non passa per l'import, e dice perché",
              not j.get("voci") and any("forma" in p["problema"]
                                        for p in j.get("problemi") or []))

        # --- 5. le forms annidate non si perdono ------------------------------
        voci = catalogo()
        chiave_con_forme = next(k for k, v in voci.items() if v.get("forms"))
        quante = len(voci[chiave_con_forme]["forms"])
        r = c.post("/pokemon/api/catalogo/pokemon/importa",
                   json={"nomi": [chiave_con_forme], "sovrascrivi": True})
        dopo = (catalogo().get(chiave_con_forme) or {}).get("forms") or {}
        esito("reimportare una specie NON cancella le sue Mega e Gigantamax",
              r.status_code == 200 and len(dopo) == quante,
              f"{chiave_con_forme}: {quante} forme prima, {len(dopo)} dopo")

        # --- 5b. il pannello è nella pagina, e solo dove ha senso -------------
        pagina = c.get("/pokemon/catalogo?db=pokemon").get_data(as_text=True)
        esito("il pannello di import è nella pagina del catalogo Pokémon",
              'id="imp_nomi"' in pagina and "Importa da Pok" in pagina)
        altra = c.get("/pokemon/catalogo?db=moves").get_data(as_text=True)
        # ⚠️ Non basta cercare l'id: la prima volta il pannello era condizionato e le
        # sue funzioni JS no, quindi «imp_nomi» compariva lo stesso — dentro codice
        # che su quella pagina non serviva a niente.
        esito("e NON compare sugli altri tre database, né il pannello né il suo JS",
              "imp_nomi" not in altra and "impCerca" not in altra)
        c.set_cookie("hub_lang", "en")
        inglese = c.get("/pokemon/catalogo?db=pokemon").get_data(as_text=True)
        esito("in inglese il pannello è tradotto",
              "Import from Pok" in inglese and "See what enters" in inglese)
        c.set_cookie("hub_lang", "it")

        # --- 6. un utente normale non entra -----------------------------------
        with c.session_transaction() as s:
            s["role"] = "user"
        r = c.post("/pokemon/api/catalogo/pokemon/importa", json={"nomi": ["Pawmot"]})
        esito("un utente non amministratore prende 403", r.status_code == 403)

    # --- 7. niente di vero è stato toccato -----------------------------------
    vero = json.load(open(os.path.join(RADICE, "data", "catalog", "pokemon.json"),
                          encoding="utf-8"))
    esito("il catalogo vero è intatto", len(vero) == 1026 and CAVIA in vero,
          f"{len(vero)} voci")


def main():
    dove = tempfile.mkdtemp(prefix="prova_import_")
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
