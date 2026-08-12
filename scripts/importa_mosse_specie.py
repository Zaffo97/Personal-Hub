#!/usr/bin/env python
"""Costruisce `data/catalog/pokemon_moves.json` — le mosse che ogni voce può imparare.

    python scripts/importa_mosse_specie.py [--dry-run] [--solo main,champions]

Era il buco più grosso dei dati: **zero specie su 1026** avevano un elenco `moves`, e
non ce l'aveva nemmeno il vecchio `data/pokemon_catalog.json`. Senza questo elenco il
calcolatore accetta Fulmine su Magikarp e il team builder non può proporre le mosse
del Pokémon scelto.

FONTE — il dump CSV di PokéAPI (`data/v2/csv`), lo stesso di `build_catalog.py`.
Non la API REST: il moveset sta tutto in `pokemon_moves.csv`, quindi si scarica **un
file** invece di fare 1026 chiamate. La cache sta in `data/cache/pokeapi_csv/`
(ignorata da git), quindi la seconda esecuzione non ripassa dalla rete.

DUE ELENCHI PER VOCE, non uno, perché sono due cose diverse:

- **`main`** — le mosse dei giochi principali, prese dal **version group più recente in
  cui quella voce compare** (di norma Scarlatto/Violetto; chi non c'è ricade su
  Spada/Scudo e via indietro). È l'elenco giusto per la regulation `pokedex`, che non
  filtra nulla
- **`champions`** — il moveset di **Pokémon Champions**, che nel dump è un version
  group suo (`champions`, id 32, 19810 righe su 319 voci). È l'elenco giusto per `ma` e
  `mb`, che da Champions vengono. Non è la stessa lista: Incineroar in Champions **non
  ha Knock Off**, che nei giochi principali impara con una MT

Il valore di ogni mossa dice **come** si impara: `"level-up:32"`, `"machine"`,
`"egg"`, `"tutor"`, `"train"` (l'unico metodo di Champions), separati da virgola quando
sono più d'uno. Così l'interfaccia può filtrare per metodo senza un secondo import.

COSA NON FA, di proposito:

- **non inventa niente per le forme inventate.** Le voci senza `slug` — le tue Mega
  fan-made e le forme di Champions che PokéAPI non conosce — restano **fuori**
  dall'elenco, non ereditano il moveset della specie base. Sono elencate nel rapporto:
  quando ci sarà una fonte, si riaprono da lì
- **non tocca `data/catalog/pokemon.json`.** Il moveset sta in un file affiancato
  perché il catalogo è già 547 KB per 8 campi a riga, e finisce nel payload del browser:
  metterci dentro ~60 mosse per voce lo porterebbe oltre i 3 MB
"""
import argparse
import collections
import csv
import io
import json
import os
import sys
import time

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

# La console di Windows e' cp1252 e non sa scrivere "Nidoran♀": senza questo il
# rapporto finale muore su UnicodeEncodeError dopo che il lavoro e' gia' stato fatto.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DATA = os.path.join(RADICE, "data")
CATALOGO = os.path.join(DATA, "catalog")
CACHE = os.path.join(DATA, "cache", "pokeapi_csv")
USCITA = os.path.join(CATALOGO, "pokemon_moves.json")

BASE_CSV = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
UA = {"User-Agent": "personal-hub/1.0 (import moveset offline, uso personale)"}
EN = "9"

FILE_CSV = [
    "pokemon.csv", "pokemon_moves.csv", "pokemon_move_methods.csv",
    "move_names.csv", "version_groups.csv",
]

# Il version group di Pokémon Champions nel dump. Tenuto fuori da `main` perché non è
# un gioco principale: è la fonte separata delle regulation `ma`/`mb`.
VG_CHAMPIONS = "champions"


# ── cache CSV ────────────────────────────────────────────────────────────────
def scarica_cache():
    import requests
    os.makedirs(CACHE, exist_ok=True)
    mancanti = [f for f in FILE_CSV
                if not os.path.exists(os.path.join(CACHE, f))
                or os.path.getsize(os.path.join(CACHE, f)) == 0]
    if not mancanti:
        print(f"cache CSV già presente in {CACHE}")
        return
    print(f"scarico {len(mancanti)} file CSV in {CACHE}")
    for f in mancanti:
        r = requests.get(BASE_CSV + f, headers=UA, timeout=180)
        r.raise_for_status()
        io.open(os.path.join(CACHE, f), "wb").write(r.content)
        print(f"  {f}  {len(r.content) // 1024} KB")


def leggi(nome):
    with io.open(os.path.join(CACHE, nome), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def carica_json(percorso, default=None):
    try:
        with io.open(percorso, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ── indice del catalogo: chiave visibile -> slug ─────────────────────────────
def indice_catalogo():
    """Ogni voce del catalogo che ha uno `slug`, specie e forme annidate.

    La chiave dell'elenco è quella con cui la voce è già nominata altrove: la chiave
    del catalogo per le specie, il **nome della forma** per le forme annidate — lo
    stesso testo che i filtri delle regulation e i team salvati usano.
    """
    catalogo = carica_json(os.path.join(CATALOGO, "pokemon.json"), {}) or {}
    voci, senza_slug = {}, []
    for chiave, dati in catalogo.items():
        if dati.get("slug"):
            voci[chiave] = dati["slug"]
        else:
            senza_slug.append(chiave)
        for nome_forma, forma in (dati.get("forms") or {}).items():
            if forma.get("slug"):
                voci[nome_forma] = forma["slug"]
            else:
                senza_slug.append(nome_forma)
    return voci, sorted(senza_slug)


# ── moveset ──────────────────────────────────────────────────────────────────
def costruisci_moveset(quali):
    pokemon = {r["id"]: r["identifier"] for r in leggi("pokemon.csv")}
    metodi = {r["id"]: r["identifier"] for r in leggi("pokemon_move_methods.csv")}
    mosse_en = {r["move_id"]: r["name"] for r in leggi("move_names.csv")
                if r["local_language_id"] == EN}
    gruppi = {r["id"]: (r["identifier"], int(r["order"])) for r in leggi("version_groups.csv")}
    id_champions = next((i for i, (nome, _) in gruppi.items() if nome == VG_CHAMPIONS), None)

    # slug -> version group -> {nome mossa: [metodi]}
    per_slug = collections.defaultdict(lambda: collections.defaultdict(dict))
    righe_ignorate = 0
    for r in leggi("pokemon_moves.csv"):
        slug = pokemon.get(r["pokemon_id"])
        nome = mosse_en.get(r["move_id"])
        metodo = metodi.get(r["pokemon_move_method_id"])
        if not slug or not nome or not metodo:
            righe_ignorate += 1
            continue
        # Il livello si scrive sempre, `0` compreso: nel dump vuol dire "all'evoluzione
        # o dal ricordamosse", che è un'informazione, non un buco. Scrivere `level-up`
        # nudo per quei casi li renderebbe indistinguibili da un livello mancante.
        if metodo == "level-up" and r["level"].isdigit():
            metodo = f"level-up:{r['level']}"
        per_slug[slug][r["version_group_id"]].setdefault(nome, [])
        if metodo not in per_slug[slug][r["version_group_id"]][nome]:
            per_slug[slug][r["version_group_id"]][nome].append(metodo)

    voci_catalogo, senza_slug = indice_catalogo()
    fuori, usati_vg, senza_righe = {}, collections.Counter(), []

    for chiave, slug in sorted(voci_catalogo.items()):
        per_vg = per_slug.get(slug)
        if not per_vg:
            senza_righe.append(chiave)
            continue
        voce = {"slug": slug}

        if "main" in quali:
            # il version group più recente in cui la voce compare, Champions escluso
            candidati = [(gruppi[v][1], v) for v in per_vg
                         if v in gruppi and v != id_champions]
            if candidati:
                _, vg = max(candidati)
                voce["main"] = {
                    "vg": gruppi[vg][0],
                    "moves": {n: ",".join(m) for n, m in sorted(per_vg[vg].items())},
                }
                usati_vg[gruppi[vg][0]] += 1

        if "champions" in quali and id_champions in per_vg:
            voce["champions"] = {
                "moves": {n: ",".join(m) for n, m in sorted(per_vg[id_champions].items())},
            }

        if len(voce) > 1:
            fuori[chiave] = voce
        else:
            senza_righe.append(chiave)

    return fuori, dict(senza_slug=senza_slug, senza_righe=sorted(senza_righe),
                       usati_vg=usati_vg, righe_ignorate=righe_ignorate,
                       voci_catalogo=len(voci_catalogo))


# ── scrittura ────────────────────────────────────────────────────────────────
def scrivi(voci, dry):
    """Scrive il file, tenendo da parte la versione precedente come fa il catalogo."""
    documento = {
        "_meta": {
            "fonte": "dump CSV di PokéAPI — https://github.com/PokeAPI/pokeapi/tree/master/data/v2/csv",
            "generato": time.strftime("%Y-%m-%d"),
            "generato_da": "scripts/importa_mosse_specie.py",
            "spiegazione": (
                "`main` = mosse dei giochi principali, dal version group più recente in cui "
                "la voce compare. `champions` = moveset di Pokémon Champions, la fonte di "
                "ma/mb. Il valore dice come si impara la mossa: level-up:<livello>, machine, "
                "egg, tutor, train."
            ),
        },
        "voci": voci,
    }
    if dry:
        return len(json.dumps(documento, ensure_ascii=False, indent=1))
    # Nessuna copia in data/archive/, a differenza degli altri file del catalogo: questo
    # non è un dato curato a mano ma 2,7 MB rigenerabili da un dump pubblico in un
    # minuto, e `data/archive/` è tracciata da git. La rete di sicurezza qui è il
    # controllo che le voci non calino, sopra in main().
    os.makedirs(CATALOGO, exist_ok=True)
    with io.open(USCITA, "w", encoding="utf-8") as f:
        json.dump(documento, f, ensure_ascii=False, indent=1)
    return os.path.getsize(USCITA)


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="non scrive niente")
    ap.add_argument("--solo", default="main,champions",
                    help="quali elenchi costruire: main, champions, o entrambi")
    args = ap.parse_args()
    quali = {p.strip() for p in args.solo.split(",") if p.strip()}
    if not quali <= {"main", "champions"}:
        print(f"--solo accetta solo 'main' e 'champions', ricevuto: {sorted(quali)}")
        return 1

    scarica_cache()
    print()

    voci, s = costruisci_moveset(quali)

    precedente = carica_json(USCITA, {}) or {}
    prima = precedente.get("voci") or {}

    con_main = sum(1 for v in voci.values() if "main" in v)
    con_ch = sum(1 for v in voci.values() if "champions" in v)
    tot_main = sum(len(v["main"]["moves"]) for v in voci.values() if "main" in v)
    tot_ch = sum(len(v["champions"]["moves"]) for v in voci.values() if "champions" in v)

    print(f"VOCI DEL CATALOGO CON SLUG   {s['voci_catalogo']}")
    print(f"  con moveset               {len(voci)}")
    print(f"    di cui `main`           {con_main:5d}   {tot_main} mosse in tutto"
          f"   ({tot_main // max(con_main, 1)} in media)")
    print(f"    di cui `champions`      {con_ch:5d}   {tot_ch} mosse in tutto"
          f"   ({tot_ch // max(con_ch, 1)} in media)")

    if s["usati_vg"]:
        print("\n  version group usati per `main`:")
        for nome, n in s["usati_vg"].most_common():
            print(f"    {nome:20s} {n:5d} voci")

    # Chi resta fuori non è un blocco solo, e confonderli nasconderebbe la differenza
    # fra un dato che non esiste e un dato che esiste altrove.
    gmax = [n for n in s["senza_righe"] if "Gigantamax" in n]
    inventate = s["senza_slug"] + [n for n in s["senza_righe"] if "Gigantamax" not in n]
    print(f"\nRESTANO FUORI  {len(s['senza_slug']) + len(s['senza_righe'])}")
    print(f"  forme inventate — PokéAPI non le conosce     {len(inventate)}")
    for n in sorted(inventate):
        print(f"    · {n}")
    print(f"  forme Gigantamax — nel dump non hanno un      {len(gmax)}")
    print("    moveset proprio: condividono quello della forma base")
    for n in gmax[:6]:
        print(f"    · {n}")
    if len(gmax) > 6:
        print(f"    … e altre {len(gmax) - 6}")

    if prima:
        perse = sorted(set(prima) - set(voci))
        print(f"\nRISPETTO AL FILE ESISTENTE   {len(prima)} -> {len(voci)} voci")
        if perse:
            print(f"  ⚠️  {len(perse)} voci sparirebbero: {perse[:10]}")
            print("  INTERROTTO: un import non deve far calare i dati. Controlla la cache CSV.")
            return 1

    peso = scrivi(voci, args.dry_run)
    print(f"\n{'dry-run: niente scritto' if args.dry_run else 'scritto in ' + USCITA}"
          f"   ({peso // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
