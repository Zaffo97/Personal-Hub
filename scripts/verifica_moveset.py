#!/usr/bin/env python
"""Confronta la lista `champions` del moveset con Bulbapedia. **Segnala, non corregge.**

    python scripts/verifica_moveset.py [--scarica] [--aggiorna]

§5.2 del backlog, 14/09/2026. Il moveset (`data/catalog/pokemon_moves.json`) viene tutto
dal dump di PokéAPI, e fino a oggi l'unica verifica era **interna**: i nomi risolvono,
i conti tornano, Incineroar perde Knock Off. Questo dice che il meccanismo funziona,
non che gli elenchi siano giusti. La seconda fonte è **Bulbapedia**, indicata da Davide:
per ogni specie c'è una pagina «/Champions learnset» con le mosse **accessibili** e,
a parte, quelle **inaccessibili**. Qui si confrontano solo le accessibili.

Cosa dice il rapporto, in ordine di rischio:

1. **Bulbapedia ha la lista, il dump no.** Su MA e MB una specie così ha l'avviso giallo
   «nessun elenco mosse» invece delle sue mosse. È il caso di Pawmot, che il backlog dava
   per «buco del dump»: Bulbapedia scrive che è in Champions dalla versione 1.2.0
2. **Mosse diverse** fra le due fonti, voce per voce: solo nel dump / solo su Bulbapedia
3. **Forme confrontate con la lista della specie** (Mega, Rotom, Castform, …): Bulbapedia
   non ha un blocco loro, quindi una differenza lì può essere una mossa propria della
   forma e va letta, non contata come errore
4. **Voci col dump e senza pagina** su Bulbapedia

⚠️ **Non si sovrascrive PokéAPI con Bulbapedia alla cieca**: nessuna delle due è sempre
giusta, e la lezione è già stata pagata. Lo script non scrive nel catalogo, e non ha
un modo per farlo.

⚠️ **Si ferma su ciò che non risolve.** Ogni blocco di Bulbapedia deve corrispondere a
**una sola** voce del catalogo (la pagina dà la specie, la sezione `===…===` la forma).
Un blocco ambiguo o senza voce viene elencato ed esce con 1: un confronto fatto con la
voce sbagliata darebbe differenze false, che è peggio di nessun confronto.

Le pagine stanno in `data/cache/bulbapedia/champions/` (ignorata da git). Senza cache le
scarica, una richiesta al secondo; `--aggiorna` le riscarica tutte, e va fatto dopo un
aggiornamento del gioco, perché Bulbapedia cambia e la cache no. Il rapporto completo
finisce in `data/cache/bulbapedia/rapporto_champions.json`.
"""
import argparse
import collections
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse

import requests

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import load_catalog, MOVESET_FILE  # noqa: E402

API = "https://bulbapedia.bulbagarden.net/w/api.php"
INDEX = "https://bulbapedia.bulbagarden.net/w/index.php"
UA = {"User-Agent": "Mozilla/5.0 (compatible; personal-hub/1.0)"}
CATEGORIA = "Category:Pokémon learnsets (Champions)"
CACHE = os.path.join(RADICE, "data", "cache", "bulbapedia", "champions")
RAPPORTO = os.path.join(RADICE, "data", "cache", "bulbapedia", "rapporto_champions.json")

# Parole che nei nomi delle forme non distinguono niente
PAROLE_VUOTE = {"form", "forme", "pokemon"}


def chiave_confronto(s):
    """Per confrontare nomi tra fonti diverse: senza accenti, spazi né punteggiatura."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def parole(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return frozenset(p for p in re.split(r"[^a-z0-9]+", s) if p and p not in PAROLE_VUOTE)


# ── cache di Bulbapedia ───────────────────────────────────────────────────────
def file_pagina(titolo):
    return os.path.join(CACHE, urllib.parse.quote(titolo, safe="") + ".txt")


def elenco_pagine(scarica):
    percorso = os.path.join(CACHE, "_elenco.json")
    if os.path.exists(percorso) and not scarica:
        return json.load(open(percorso, encoding="utf-8"))
    titoli, cont = [], {}
    while True:
        j = requests.get(API, headers=UA, timeout=60, params={
            "action": "query", "list": "categorymembers", "format": "json",
            "cmtitle": CATEGORIA, "cmlimit": "500", **cont}).json()
        titoli += [m["title"] for m in j["query"]["categorymembers"]]
        if "continue" not in j:
            break
        cont = j["continue"]
    os.makedirs(CACHE, exist_ok=True)
    json.dump(titoli, open(percorso, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return titoli


def testo_pagina(titolo, aggiorna):
    percorso = file_pagina(titolo)
    if os.path.exists(percorso) and os.path.getsize(percorso) and not aggiorna:
        return open(percorso, encoding="utf-8").read()
    r = requests.get(INDEX, headers=UA, timeout=60, params={"title": titolo, "action": "raw"})
    time.sleep(1)
    if r.status_code != 200 or not r.text:
        return None
    open(percorso, "w", encoding="utf-8").write(r.text)
    return r.text


# ── lettura del wikitext ──────────────────────────────────────────────────────
MOSSA = re.compile(r"\{\{learnlist/champ\|([^|}]+)\|")
SEZIONE = re.compile(r"^===\s*(.+?)\s*===\s*$", re.M)
VERSIONE = re.compile(r"available from Version ([\d.]+)", re.I)


def blocchi(testo):
    """`[(sezione o None, {mosse accessibili})]`.

    Le accessibili stanno fra `learnlist/champh|` e il primo `learnlist/champf|`; le
    inaccessibili hanno `champh/lost` e `champ/lost`, e restano fuori.
    """
    fuori = []
    confini = [(m.start(), m.group(1)) for m in SEZIONE.finditer(testo)] or [(0, None)]
    for i, (inizio, sezione) in enumerate(confini):
        fine = confini[i + 1][0] if i + 1 < len(confini) else len(testo)
        pezzo = testo[inizio:fine]
        a = pezzo.find("{{learnlist/champh|")
        if a < 0:
            continue
        b = pezzo.find("{{learnlist/champf|", a)
        accessibili = pezzo[a:b if b > 0 else len(pezzo)]
        fuori.append((sezione, {m.strip() for m in MOSSA.findall(accessibili)}))
    return fuori


# ── corrispondenza pagina/sezione -> voce del catalogo ───────────────────────
def indice_specie(catalogo):
    """`{chiave_confronto(nome della specie): [chiave_catalogo]}` sulle voci di primo livello."""
    fuori = collections.defaultdict(list)
    for chiave, voce in catalogo.items():
        for nome in {voce.get("name"), voce.get("nome_en")}:
            if nome:
                fuori[chiave_confronto(re.sub(r"\s*\(.*\)\s*$", "", nome))].append(chiave)
    return {k: sorted(set(v)) for k, v in fuori.items()}


def candidati(catalogo, chiave):
    """`[(nome_voce_nel_moveset, parole del nome, parole dello slug)]`: specie e forme."""
    voce = catalogo[chiave]
    fuori = [(chiave, parole(voce.get("name") or chiave), parole(voce.get("slug") or chiave))]
    for nome_forma, forma in (voce.get("forms") or {}).items():
        fuori.append((nome_forma, parole(nome_forma), parole(forma.get("slug") or "")))
    return fuori


def risolvi_blocco(specie_nome, sezione, cand):
    """La voce a cui appartiene un blocco, o `(None, motivo)`."""
    if sezione is None or chiave_confronto(sezione) == chiave_confronto(specie_nome):
        return cand[0][0], None
    cercate = parole(sezione) | parole(specie_nome)
    trovate = [n for n, p_nome, p_slug in cand if cercate in (p_nome, p_slug)]
    if len(trovate) == 1:
        return trovate[0], None
    return None, ("nessuna voce" if not trovate else "ambiguo: " + ", ".join(trovate))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scarica", action="store_true",
                    help="rilegge l'elenco delle pagine e scarica quelle mancanti")
    ap.add_argument("--aggiorna", action="store_true",
                    help="riscarica tutte le pagine (dopo un aggiornamento del gioco)")
    args = ap.parse_args()

    catalogo = load_catalog("pokemon")
    moveset = json.load(open(MOVESET_FILE, encoding="utf-8"))["voci"]
    mosse_catalogo = load_catalog("moves")
    nomi_mosse = {chiave_confronto(k): k for k in mosse_catalogo}
    for k, v in mosse_catalogo.items():
        if v.get("nome_en"):
            nomi_mosse.setdefault(chiave_confronto(v["nome_en"]), k)
    if not catalogo or not moveset:
        print("Catalogo o moveset illeggibile: non confronto niente.")
        return 1

    titoli = elenco_pagine(args.scarica or args.aggiorna)
    specie = indice_specie(catalogo)
    rosters = {r: set(json.load(open(os.path.join(RADICE, "data", "regulations", f"{r}.json"),
                                     encoding="utf-8")).get("pokemon") or [])
               for r in ("ma", "mb")}

    non_risolti, senza_pagina_scaricata = [], []
    confrontate = {}          # voce -> dati del confronto
    mosse_ignote = collections.Counter()
    pagine_viste = set()

    for titolo in titoli:
        testo = testo_pagina(titolo, args.aggiorna)
        if testo is None:
            senza_pagina_scaricata.append(titolo)
            continue
        nome_specie = titolo.split(" (Pokémon)")[0]
        chiavi = specie.get(chiave_confronto(nome_specie), [])
        if len(chiavi) != 1:
            non_risolti.append(f"{titolo}: specie {'assente' if not chiavi else 'ambigua ' + str(chiavi)}")
            continue
        cand = candidati(catalogo, chiavi[0])
        versione = (VERSIONE.search(testo) or [None, None])[1]
        lista = blocchi(testo)
        if not lista:
            non_risolti.append(f"{titolo}: nessun blocco di mosse accessibili")
            continue
        assegnate = set()
        for sezione, mosse in lista:
            voce, motivo = risolvi_blocco(nome_specie, sezione, cand)
            if voce is None:
                non_risolti.append(f"{titolo} / «{sezione}»: {motivo}")
                continue
            for m in mosse:
                if chiave_confronto(m) not in nomi_mosse:
                    mosse_ignote[m] += 1
            confrontate[voce] = {"pagina": titolo, "sezione": sezione, "versione": versione,
                                 "bulbapedia": mosse, "diretta": True}
            assegnate.add(voce)
        pagine_viste.add(chiavi[0])
        # Le forme senza un blocco loro, ma con una lista nel dump (Mega, Rotom, …), si
        # confrontano col blocco della specie — il primo — e si segnano a parte.
        principale = lista[0][1]
        for nome, _, _ in cand:
            if nome not in assegnate and "champions" in (moveset.get(nome) or {}):
                confrontate[nome] = {"pagina": titolo, "sezione": None, "versione": versione,
                                     "bulbapedia": principale, "diretta": False}

    manca_nel_dump, differenze, differenze_forme, uguali = [], [], [], 0
    for voce, dati in sorted(confrontate.items()):
        dump = set(((moveset.get(voce) or {}).get("champions") or {}).get("moves") or {})
        bulba = {nomi_mosse.get(chiave_confronto(m), m) for m in dati["bulbapedia"]}
        in_roster = sorted(r for r, nomi in rosters.items()
                           if voce in nomi or (catalogo.get(voce) or {}).get("name") in nomi)
        riga = {"voce": voce, "pagina": dati["pagina"], "sezione": dati["sezione"],
                "versione": dati["versione"], "roster": in_roster,
                "bulbapedia": len(bulba), "dump": len(dump)}
        if not dump:
            if dati["diretta"]:
                manca_nel_dump.append(riga)
            continue
        solo_dump, solo_bulba = sorted(dump - bulba), sorted(bulba - dump)
        if not solo_dump and not solo_bulba:
            uguali += 1
            continue
        riga.update(solo_dump=solo_dump, solo_bulbapedia=solo_bulba)
        (differenze if dati["diretta"] else differenze_forme).append(riga)

    con_champions = {v for v, d in moveset.items() if "champions" in d}
    senza_pagina = sorted(con_champions - set(confrontate))

    versioni = collections.Counter(r["versione"] for r in manca_nel_dump)
    print(f"pagine Bulbapedia: {len(titoli)}, voci confrontate: {len(confrontate)} "
          f"(dirette {sum(d['diretta'] for d in confrontate.values())})")
    print(f"voci con lista champions nel dump: {len(con_champions)}")
    print(f"\n= identiche: {uguali}")
    print(f"\n1) Bulbapedia ha la lista, il dump no: {len(manca_nel_dump)} "
          f"(per versione di arrivo: {dict(versioni)})")
    for r in manca_nel_dump:
        print(f"   {r['voce']:32s} {r['bulbapedia']:3d} mosse  dalla {r['versione']}  roster {r['roster']}")
    print(f"\n2) mosse diverse, voci con un blocco loro: {len(differenze)}")
    for r in differenze:
        print(f"   {r['voce']:32s} dump {r['dump']:3d} / bulba {r['bulbapedia']:3d}"
              f"  solo dump {r['solo_dump']}  solo bulba {r['solo_bulbapedia']}")
    print(f"\n3) forme confrontate con la lista della specie, con differenze: {len(differenze_forme)}")
    for r in differenze_forme:
        print(f"   {r['voce']:32s} solo dump {r['solo_dump']}  solo bulba {r['solo_bulbapedia']}")
    print(f"\n4) voci col dump ma senza pagina su Bulbapedia: {len(senza_pagina)}")
    if senza_pagina:
        print("   " + ", ".join(senza_pagina))
    if mosse_ignote:
        print(f"\n! nomi di mossa di Bulbapedia che il catalogo non conosce: {dict(mosse_ignote)}")
    for riga in senza_pagina_scaricata:
        print("X non scaricata: " + riga)
    for riga in non_risolti:
        print("X non risolto: " + riga)

    os.makedirs(os.path.dirname(RAPPORTO), exist_ok=True)
    json.dump({"generato": time.strftime("%Y-%m-%d"), "identiche": uguali,
               "manca_nel_dump": manca_nel_dump, "differenze": differenze,
               "differenze_forme": differenze_forme, "senza_pagina": senza_pagina,
               "mosse_ignote": dict(mosse_ignote), "non_risolti": non_risolti},
              open(RAPPORTO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nrapporto completo: {os.path.relpath(RAPPORTO, RADICE)}")

    if non_risolti or senza_pagina_scaricata:
        print(f"\n{len(non_risolti) + len(senza_pagina_scaricata)} blocchi non confrontati: "
              "il rapporto e' incompleto.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
