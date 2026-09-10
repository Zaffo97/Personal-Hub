#!/usr/bin/env python
"""Le prove della regulation creata dall'interfaccia (§1.3). Non tocca i file veri.

    python scripts/prova_regulation_nuova.py

Gira su una **copia** di `data/catalog/`, di `data/regulations/` e del registro, con
`_archive_dir()` deviato: la lezione del 21/08 vale anche qui, perche' il pulsante
della mega_map **scrive** una copia di sicurezza prima di toccare il filtro.

Cosa dimostra, tutto misurato:

- la **sorgente delle mosse** si sceglie alla creazione, si eredita copiando da
  un'altra regulation e si rifiuta se non esiste. E' il campo che cambia i numeri
  senza comparire: prima del 10/09/2026 una copia di MA leggeva `main` e su
  Incineroar dava **80 mosse invece di 77**, Knock Off compresa
- la pagina **Regulations dice i numeri veri**: prima leggeva i file vecchi e su MA
  scriveva 208 Pokémon e 461 mosse invece di 279 e 460, e 0 su tutto il resto
- il pulsante **completa la mega_map** collega le Mega del roster, non tocca i
  collegamenti gia' scritti, dichiara quelle che non puo' collegare e non trasforma
  mai `pokemon: null` in un elenco chiuso
- una regulation **vuota** non e' un errore: `/api/regulation/<id>/data` risponde 200
  e lo **dichiara**, invece del 404 che lo Speed Tier prendeva per «usa la lista
  statica» e il team builder per «tieni i dati di prima»
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


def prove(dove):
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

    def filtro(reg_id):
        with open(os.path.join(dati, "regulations", f"{reg_id}.json"), encoding="utf-8") as f:
            return json.load(f)

    def scrivi_filtro(reg_id, contenuto):
        with open(os.path.join(dati, "regulations", f"{reg_id}.json"), "w", encoding="utf-8") as f:
            json.dump(contenuto, f, ensure_ascii=False, indent=2)

    def registro(reg_id):
        with open(os.path.join(dati, "regulations.json"), encoding="utf-8") as f:
            return next(r for r in json.load(f) if r["id"] == reg_id)

    import app as m
    m.app.config["TESTING"] = True
    with m.app.test_client() as c:
        with c.session_transaction() as s:
            s["username"] = "admin"
            s["role"] = "admin"

        # --- 1. le sorgenti disponibili sono lette dal file -------------------
        esito("le sorgenti del moveset sono `main` e `champions`, lette dal file",
              P.sorgenti_moveset() == ["main", "champions"], str(P.sorgenti_moveset()))

        # --- 2. creazione vuota: la sorgente e' scritta, non implicita ---------
        r = c.post("/pokemon/api/regulations/create",
                   json={"id": "vuota1", "label": "Prova Vuota", "partenza": "vuota"})
        esito("la regulation vuota nasce con la sorgente scritta nel registro",
              r.status_code == 201 and registro("vuota1").get("moveset") == "main",
              str(registro("vuota1").get("moveset")))

        # --- 3. una sorgente che non esiste viene RIFIUTATA --------------------
        r = c.post("/pokemon/api/regulations/create",
                   json={"id": "rotta", "label": "Rotta", "moveset": "champions2"})
        esito("una sorgente mosse inesistente e' rifiutata con 400 alla creazione",
              r.status_code == 400 and not os.path.exists(
                  os.path.join(dati, "regulations", "rotta.json")))

        regs = json.load(open(os.path.join(dati, "regulations.json"), encoding="utf-8"))
        for reg in regs:
            if reg["id"] == "vuota1":
                reg["moveset"] = "champions2"
        r = c.post("/pokemon/api/regulations/save", json={"regulations": regs})
        esito("e anche il salvataggio dei metadati la rifiuta",
              r.status_code == 400 and registro("vuota1")["moveset"] == "main")

        # --- 4. copiando da MA si eredita Champions ---------------------------
        r = c.post("/pokemon/api/regulations/create",
                   json={"id": "copia1", "label": "Prova Copia", "partenza": "ma"})
        esito("copiando da MA la regulation nuova eredita `champions`",
              r.status_code == 201 and registro("copia1").get("moveset") == "champions",
              str(registro("copia1").get("moveset")))

        copia = next(r for r in P._list_regulation_files() if r["id"] == "copia1")
        ma = next(r for r in P._list_regulation_files() if r["id"] == "ma")
        mosse_copia, sorg_copia = P.mosse_legali("Incineroar", copia)
        mosse_ma, _ = P.mosse_legali("Incineroar", ma)
        esito("e Incineroar ha le stesse 77 mosse di MA, non le 80 di `main`",
              mosse_copia == mosse_ma and len(mosse_copia) == 77 and sorg_copia == "champions",
              f"copia={len(mosse_copia or [])} ma={len(mosse_ma or [])} sorgente={sorg_copia}")
        esito("Knock Off e' in `main` e non in `champions`: la differenza si vede",
              "Knock Off" not in mosse_copia
              and "Knock Off" in (P.mosse_legali("Incineroar",
                                                 {"id": "x", "moveset": "main"})[0] or []))

        # --- 5. la sorgente chiesta batte quella ereditata ---------------------
        r = c.post("/pokemon/api/regulations/create",
                   json={"id": "copia2", "label": "Copia con main", "partenza": "ma",
                         "moveset": "main"})
        esito("chiedere `main` copiando da MA vince sull'eredita'",
              r.status_code == 201 and registro("copia2").get("moveset") == "main")

        # --- 6. copia-da porta anche la sorgente ------------------------------
        r = c.post("/pokemon/api/regulation/vuota1/copia-da",
                   json={"sorgente": "ma", "campi": ["pokemon", "moveset"]})
        j = r.get_json() or {}
        esito("il copia contenuti sa copiare anche la sorgente delle mosse",
              r.status_code == 200 and j.get("copiati", {}).get("moveset") == "champions"
              and registro("vuota1")["moveset"] == "champions"
              and len(filtro("vuota1")["pokemon"]) == 279,
              str(j.get("copiati")))

        # --- 7. i conteggi della pagina Regulations ---------------------------
        r = c.get("/pokemon/regulations")
        esito("la pagina Regulations si apre", r.status_code == 200)
        # gli stessi numeri che la pagina mette nelle card, presi dai loader
        conteggi = {}
        for reg in P._list_regulation_files():
            conteggi[reg["id"]] = (len(P._load_roster(reg)),
                                   len(P.load_moves(reg["id"]).get("moves", {})),
                                   len(P.load_items(reg["id"]).get("items", {})))
        esito("MA dice 279 / 460 / 58, non i 208 / 461 / 58 dei file vecchi",
              conteggi["ma"] == (279, 460, 58), str(conteggi["ma"]))
        esito("Pokedex dice tutto il catalogo, non 0", conteggi["pokedex"] == (1343, 919, 397),
              str(conteggi["pokedex"]))
        html = r.get_data(as_text=True)
        esito("e i numeri veri sono scritti nella pagina",
              ">279<" in html and ">1343<" in html and ">919<" in html)

        # --- 8. una regulation vuota si dichiara, non da' 404 -----------------
        c.post("/pokemon/api/regulations/create",
               json={"id": "vuota2", "label": "Ancora Vuota", "partenza": "vuota"})
        r = c.get("/api/regulation/vuota2/data")
        j = r.get_json() or {}
        esito("il roster vuoto risponde 200 e lo dichiara, invece del 404 di prima",
              r.status_code == 200 and j.get("ok") and j.get("vuota") is True
              and j.get("roster") == [] and j.get("count") == 0,
              f"status={r.status_code} vuota={j.get('vuota')}")
        r = c.get("/api/regulation/ma/data")
        j = r.get_json() or {}
        esito("e una regulation piena non e' vuota", j.get("vuota") is False
              and j.get("count") == 279, str(j.get("count")))

        # --- 9. la mega_map: anteprima, collegamenti, dichiarazioni -----------
        c.post("/pokemon/api/regulations/create",
               json={"id": "mega1", "label": "Prova Mega", "partenza": "vuota"})
        c.post("/pokemon/api/regulation/mega1/contenuto/pokemon",
               json={"nomi": ["Charizard", "Mega Charizard X", "Mega Gengar"]})
        # una Mega che nel catalogo non esiste: si scrive a mano nel filtro, perche'
        # la schermata contenuti — giustamente — non la farebbe passare
        f = filtro("mega1")
        f["pokemon"] = sorted(f["pokemon"] + ["Mega Inventata"])
        scrivi_filtro("mega1", f)

        r = c.post("/pokemon/api/regulation/mega1/mega-map", json={"anteprima": True})
        j = r.get_json() or {}
        esito("l'anteprima trova il collegamento deducibile",
              j.get("collegati") == 1
              and j["collegamenti"][0] == {"base": "Charizard", "mega": "Mega Charizard X"},
              str(j.get("collegamenti")))
        esito("dichiara la Mega la cui base e' fuori dal roster, senza aggiungerla",
              [x["mega"] for x in j.get("senza_base", [])] == ["Mega Gengar"]
              and j.get("aggiunte_al_roster") == [])
        esito("e si ferma sul nome che nel catalogo non c'e'",
              any("Mega Inventata" in p for p in j.get("problemi") or []),
              str(j.get("problemi")))
        esito("l'anteprima NON ha scritto niente",
              j.get("scritto") is False and filtro("mega1").get("mega_map") == {})

        r = c.post("/pokemon/api/regulation/mega1/mega-map", json={})
        j = r.get_json() or {}
        esito("il collegamento viene scritto",
              j.get("scritto") is True
              and filtro("mega1")["mega_map"] == {"Charizard": ["Mega Charizard X"]},
              str(filtro("mega1")["mega_map"]))
        esito("senza la spunta, la specie base mancante NON entra nel roster",
              "Gengar" not in filtro("mega1")["pokemon"])
        esito("e la copia di sicurezza c'e'",
              os.path.exists(os.path.join(archivio, "regulation_mega1_pre-mega-map.json")))

        r = c.post("/pokemon/api/regulation/mega1/mega-map", json={"aggiungi_basi": True})
        j = r.get_json() or {}
        esito("con la spunta la base entra nel roster e la Mega diventa raggiungibile",
              j.get("aggiunte_al_roster") == ["Gengar"]
              and "Gengar" in filtro("mega1")["pokemon"]
              and filtro("mega1")["mega_map"].get("Gengar") == ["Mega Gengar"],
              str(j.get("aggiunte_al_roster")))
        esito("il collegamento gia' scritto non si tocca",
              filtro("mega1")["mega_map"].get("Charizard") == ["Mega Charizard X"])

        r = c.post("/pokemon/api/regulation/mega1/mega-map", json={})
        esito("rieseguibile: la seconda volta non c'e' piu' niente da collegare",
              (r.get_json() or {}).get("collegati") == 0)

        # --- 10. `pokemon: null` non diventa mai un elenco chiuso -------------
        c.post("/pokemon/api/regulations/create",
               json={"id": "tutto1", "label": "Tutto il catalogo", "partenza": "tutto"})
        esito("una regulation «tutto il catalogo» nasce senza mega_map",
              filtro("tutto1")["mega_map"] == {} and filtro("tutto1")["pokemon"] is None)
        r = c.post("/pokemon/api/regulation/tutto1/mega-map", json={"aggiungi_basi": True})
        j = r.get_json() or {}
        esito("il pulsante la riempie: 97 Mega del catalogo diventano raggiungibili",
              j.get("scritto") is True and j.get("collegati") >= 90
              and j.get("raggiungibili") == j.get("mega_nel_roster"),
              f"collegati={j.get('collegati')} "
              f"raggiungibili={j.get('raggiungibili')}/{j.get('mega_nel_roster')}")
        esito("⚠️ e `pokemon` resta null: «anche le voci future» non diventa una lista",
              filtro("tutto1")["pokemon"] is None and j.get("aggiunte_al_roster") == [])

        # --- 11. un utente normale non entra ----------------------------------
        with c.session_transaction() as s:
            s["role"] = "user"
        r = c.post("/pokemon/api/regulation/mega1/mega-map", json={})
        esito("un utente non amministratore prende 403 sulla mega_map", r.status_code == 403)
        r = c.post("/pokemon/api/regulations/create", json={"id": "x", "label": "X"})
        esito("e nemmeno puo' creare una regulation", r.status_code == 403)

    # --- 12. niente di vero e' stato toccato ---------------------------------
    veri = sorted(os.listdir(os.path.join(RADICE, "data", "regulations")))
    esito("la cartella vera delle regulation ha ancora i suoi tre file",
          veri == ["ma.json", "mb.json", "pokedex.json"], str(veri))
    with open(os.path.join(RADICE, "data", "regulations", "ma.json"), encoding="utf-8") as f:
        vero_ma = json.load(f)
    esito("e MA e' intatta: 279 Pokémon, 58 Mega mappate",
          len(vero_ma["pokemon"]) == 279 and len(vero_ma["mega_map"]) == 58)


def main():
    dove = tempfile.mkdtemp(prefix="prova_regulation_")
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
