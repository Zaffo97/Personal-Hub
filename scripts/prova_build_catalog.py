#!/usr/bin/env python
"""Le prove delle due reti di `build_catalog.py` (§3, baco 1). Niente rete, niente CSV.

    python scripts/prova_build_catalog.py

`build_catalog.py` intero non si può provare qui: scarica 24 CSV da PokéAPI e
ricostruisce 1029 voci. Ma le due cose che il 10/09/2026 lo rendevano pericoloso non
stanno nell'import, stanno in due funzioni — **da dove prende la base** e **cosa
accetta di scrivere** — e quelle si provano in una cartella temporanea.

Cosa dimostra:

- `base_curata()` legge `data/catalog/` quando c'è, e **dice da quale file**: era il
  guasto, perché leggeva sempre i file storici, fermi a 174 voci contro 1026
- e ricade sul file storico **solo** quando il catalogo non esiste, cioè al primo giro
- `scrivi_json()` **rifiuta** un file più povero di quello sul disco, e non lo tocca
- accetta invece un file con lo stesso numero di voci o con più
- la rete vale anche per le abilità, che sono avvolte in `{"abilities": …}`
- `MEGA_BONUS` **non esiste più** nel modulo: il +75 HP che la deconversione dell'11/08
  ha tolto non può rientrare da qui senza che questa prova se ne accorga
"""
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

esiti = []


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def carica_modulo():
    """`build_catalog` importato senza eseguirlo: `requests` c'è, la rete non serve."""
    percorso = os.path.join(RADICE, "scripts", "build_catalog.py")
    spec = importlib.util.spec_from_file_location("build_catalog_sotto_prova", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def scrivi(percorso, dati):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with io.open(percorso, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)


def prove(dove):
    B = carica_modulo()

    esito("`MEGA_BONUS` non esiste più nel modulo", not hasattr(B, "MEGA_BONUS"))

    dati = os.path.join(dove, "data")
    catalogo = os.path.join(dati, "catalog")
    B.DATA, B.CATALOGO = dati, catalogo

    # --- 1. la base arriva dal catalogo, quando c'è -------------------------
    scrivi(os.path.join(dati, "pokemon_catalog.json"), {"storico1": {}, "storico2": {}})
    scrivi(os.path.join(catalogo, "pokemon.json"), {"a": {}, "b": {}, "c": {}})
    voci, percorso = B.base_curata("pokemon", "pokemon_catalog.json")
    esito("con `data/catalog/` presente, la base è quella — e il percorso lo dice",
          len(voci) == 3 and percorso.endswith(os.path.join("catalog", "pokemon.json")),
          f"{len(voci)} voci da {os.path.basename(percorso)}")

    # --- 2. e dal file storico solo se il catalogo non c'è -------------------
    os.remove(os.path.join(catalogo, "pokemon.json"))
    voci, percorso = B.base_curata("pokemon", "pokemon_catalog.json")
    esito("senza catalogo ricade sul file storico, come al primo giro",
          len(voci) == 2 and percorso.endswith("pokemon_catalog.json"),
          f"{len(voci)} voci da {os.path.basename(percorso)}")

    # --- 3. le abilità sono avvolte in entrambi i file -----------------------
    scrivi(os.path.join(catalogo, "abilities.json"), {"abilities": {"x": {}, "y": {}}})
    voci, _ = B.base_curata("abilities", "abilities.json", "abilities",
                            avvolto_anche_nel_catalogo=True)
    esito("le abilità si srotolano da `{\"abilities\": …}` anche nel catalogo",
          len(voci) == 2 and "x" in voci, str(sorted(voci)))

    # --- 4. non si scrive un file più povero ---------------------------------
    percorso = os.path.join(catalogo, "moves.json")
    scrivi(percorso, {f"m{i}": {} for i in range(919)})
    ok = B.scrivi_json(percorso, {"m0": {}}, dry=False)
    with io.open(percorso, encoding="utf-8") as f:
        dopo = json.load(f)
    esito("un file con 1 voce contro 919 sul disco viene RIFIUTATO",
          ok is False and len(dopo) == 919, f"sul disco restano {len(dopo)}")

    # --- 5. e uno completo passa --------------------------------------------
    ok = B.scrivi_json(percorso, {f"m{i}": {} for i in range(920)}, dry=False)
    with io.open(percorso, encoding="utf-8") as f:
        dopo = json.load(f)
    esito("uno con una voce in più passa", ok is True and len(dopo) == 920,
          f"{len(dopo)} voci")

    # --- 6. il --dry-run non scrive comunque niente -------------------------
    ok = B.scrivi_json(percorso, {f"m{i}": {} for i in range(999)}, dry=True)
    with io.open(percorso, encoding="utf-8") as f:
        dopo = json.load(f)
    esito("con --dry-run il file non si muove", ok is True and len(dopo) == 920)

    # --- 7. la rete conta le voci dentro l'involucro ------------------------
    percorso = os.path.join(catalogo, "abilities.json")
    scrivi(percorso, {"abilities": {f"a{i}": {} for i in range(386)}})
    ok = B.scrivi_json(percorso, {"abilities": {"a0": {}}}, dry=False, chiave="abilities")
    with io.open(percorso, encoding="utf-8") as f:
        dopo = json.load(f)["abilities"]
    esito("⚠️ e sulle abilità guarda dentro l'involucro, non l'involucro",
          ok is False and len(dopo) == 386, f"sul disco restano {len(dopo)}")

    # --- 9. una specie già presente sotto un'altra chiave non rientra --------
    # Il caso vero del 23/09/2026: `aegislash-shield` nel dump, `aegislash-shield-forme`
    # nel catalogo. Il confronto era su chiave e nome, e lo script la dava per nuova.
    # `leggi()` finto: nessun CSV, solo le righe che servono.
    tabelle = {
        "pokemon.csv": [{"id": "681", "identifier": "aegislash-shield", "species_id": "681",
                         "is_default": "1"}],
        "pokemon_species_names.csv": [{"pokemon_species_id": "681", "local_language_id": "9",
                                       "name": "Aegislash"}],
        "type_names.csv": [], "pokemon_types.csv": [], "ability_names.csv": [],
        "pokemon_abilities.csv": [], "pokemon_forms.csv": [], "pokemon_form_names.csv": [],
        "pokemon_stats.csv": [{"pokemon_id": "681", "stat_id": str(i), "base_stat": "50"}
                              for i in range(1, 7)],
        "items.csv": [{"id": "1", "category_id": "12"}],
        "item_categories.csv": [{"id": "12", "identifier": "held-items"}],
        "item_names.csv": [{"item_id": "1", "local_language_id": "9", "name": "King’s Rock"}],
        "item_flavor_text.csv": [],
    }
    leggi_vero = B.leggi
    B.leggi = lambda nome: tabelle[nome]
    try:
        esistente = {"aegislash-shield-forme": {"name": "Aegislash (Shield Forme)",
                                                "slug": "aegislash-shield"}}
        _, conti = B.costruisci_pokemon(esistente)
        esito("una specie col suo slug già in catalogo non è «nuova»",
              conti["nuove_specie"] == 0, f"nuove specie: {conti['nuove_specie']}")

        # --- 10. né un oggetto scritto con un altro apostrofo ----------------
        _, conti = B.costruisci_oggetti({"King's Rock": {"category": "other"}})
        esito("«King’s Rock» del dump è il «King's Rock» del catalogo",
              conti["aggiunti"] == 0, f"aggiunti: {conti['aggiunti']}")
    finally:
        B.leggi = leggi_vero

    # --- 8. niente di vero è stato toccato -----------------------------------
    with io.open(os.path.join(RADICE, "data", "catalog", "pokemon.json"), encoding="utf-8") as f:
        vero = json.load(f)
    # 1025 dal 13/09/2026: la fusione del doppione di Floette ha tolto
    # `eternal-flower-floette`. Vedi la stessa nota in `prova_import_specie.py`.
    esito("il catalogo vero è intatto", len(vero) == 1025, f"{len(vero)} voci")


def main():
    dove = tempfile.mkdtemp(prefix="prova_build_")
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
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
