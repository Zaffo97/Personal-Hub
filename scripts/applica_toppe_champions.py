#!/usr/bin/env python
"""Porta le liste `champions` alla versione **1.2.0**, una mossa alla volta.

    python scripts/applica_toppe_champions.py [--dry-run]

§5.2 del backlog, decisioni di Davide del 18/09/2026. Il dump di PokéAPI è fermo prima
della 1.2.0 (uscita il **9 settembre 2026**), quindi le liste `champions` sono quelle di
prima. Le differenze non si indovinano: la **nota ufficiale di aggiornamento**, citata
su Bulbapedia alla voce «Pokémon Champions#Version history», dice esattamente questo:

> * The following Pokémon can no longer use the moves listed here.
>   ** Politoed: Pound
>   ** Archaludon: Mirror Coat, Metal Burst
> * The following move can now be used. **Slash**
> * PP adjustments: Wish 12 → 8, Strength Sap 12 → 8

I PP non hanno dove andare: il catalogo mosse **non ha il campo** (0 voci su 919).

Come funziona, e perché non è un elenco di nomi scritto a mano:

1. lo script ricostruisce da sé il confronto fra le pagine Champions di Bulbapedia (in
   cache, le stesse di `verifica_moveset.py`) e le liste del dump;
2. ogni differenza trovata viene cercata in `DECISIONI`, la tabella qui sotto, dove ogni
   riga porta **il motivo e la fonte**;
3. una differenza che non è in `DECISIONI` **ferma tutto** ed esce con 1. Chi prende
   `Slash` non è scritto qui: lo dicono le pagine, e sono 29 voci.

Dove scrive, e perché in due posti (la stessa ragione delle integrazioni):

- `data/catalog/moveset_integrazioni.json`, sezione **`toppe`** — il dato curato. È lui
  la verità: `pokemon_moves.json` lo **rigenerano** `importa_mosse_specie.py` e l'import
  dal pannello, e una mossa tolta a mano lì dentro tornerebbe al giro dopo **senza
  nessun errore**. Le riapplica `applica_toppe_moveset()` in `blueprints/pokemon.py`
- `data/catalog/pokemon_moves.json` — subito, così l'app la vede senza rigenerare niente

⚠️ **Dopo questo script va rilanciato `scripts/allinea_mosse_regulation.py`**: `Slash`
entra in 29 liste, e l'elenco mosse della regulation è derivato da quelle.

⚠️ Si rifiuta di scrivere se una mossa non esiste nel catalogo, se una voce non si
risolve, o se compare una differenza non decisa.
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import verifica_moveset as V  # noqa: E402
from blueprints.pokemon import (load_catalog, MOVESET_FILE, _archive_dir,  # noqa: E402
                                file_integrazioni_moveset, applica_toppe_moveset)

CHANGELOG = ("nota ufficiale di aggiornamento 1.2.0 (9 settembre 2026), citata in "
             "«Pokémon Champions#Version history» su Bulbapedia")
PAGINA = "pagina «<specie> (Pokémon)/Champions learnset» su Bulbapedia"

# ── Le decisioni ─────────────────────────────────────────────────────────────
# `(voce o None, mossa, direzione)` -> motivo. `None` come voce vuol dire «su
# qualunque voce»: è il caso di Slash, che il changelog dà al gioco intero.
# direzione: "+" la mossa entra (Bulbapedia ce l'ha, il dump no), "-" esce.
DECISIONI = {
    (None, "Slash", "+"): CHANGELOG + ": «The following move can now be used: Slash»",

    ("politoed", "Pound", "-"): CHANGELOG + ": «Politoed can no longer use Pound»",
    ("archaludon", "Mirror Coat", "-"): CHANGELOG + ": «Archaludon can no longer use…»",
    ("archaludon", "Metal Burst", "-"): CHANGELOG + ": «Archaludon can no longer use…»",

    # Non nel changelog: qui Bulbapedia è **affermativa da tutte e due le parti** —
    # Psychic Fangs fra le accessibili, Psychic fra le perse con una lista di giochi
    # che non comprende Champions. Decisione di Davide del 18/09/2026.
    ("ariados", "Psychic Fangs", "+"): PAGINA + ": fra le accessibili",
    ("ariados", "Psychic", "-"): PAGINA + ": fra le perse, e la lista giochi non ha Champions",

    # Non nel changelog, e non è un cambio di versione: Mawile e Houndstone sono in
    # Champions dalla 1.1.0 e il dump arriva fin lì. È un buco del dump. Nessuna delle
    # due è in un roster, quindi oggi non si vede niente.
    ("mawile", "Charm", "+"): PAGINA + " (in Champions dalla 1.1.0: buco del dump)",
    ("mawile", "Draining Kiss", "+"): PAGINA + " (in Champions dalla 1.1.0: buco del dump)",
    ("mawile", "Misty Terrain", "+"): PAGINA + " (in Champions dalla 1.1.0: buco del dump)",
    ("houndstone", "Bulldoze", "+"): PAGINA + " (in Champions dalla 1.1.0: buco del dump)",
}

# Differenze **decise e lasciate stare**: si riconoscono, non si applicano, e il
# motivo resta scritto qui perché al giro dopo nessuno le riapra.
IGNORATE = {
    # La lista della pagina è alfabetica e comincia da «Charm»: le cinque mosse che il
    # dump ha in più sono **esattamente** le cinque che vengono prima di Charm. È la
    # testa della lista tagliata via, non una smentita. Verificato il 18/09/2026.
    ("gardevoir", "Alluring Voice", "-"): "pagina troncata in testa (parte da «Charm»)",
    ("gardevoir", "Aura Sphere", "-"): "pagina troncata in testa (parte da «Charm»)",
    ("gardevoir", "Body Slam", "-"): "pagina troncata in testa (parte da «Charm»)",
    ("gardevoir", "Calm Mind", "-"): "pagina troncata in testa (parte da «Charm»)",
    ("gardevoir", "Charge Beam", "-"): "pagina troncata in testa (parte da «Charm»)",
    # Omissione isolata: la lista va da Acrobatics a Will-O-Wisp senza buchi, U-turn
    # non è nemmeno fra le perse, e compare normalmente su 48 delle 232 pagine.
    ("blaziken", "U-turn", "-"): "omissione isolata della pagina; non è nel changelog 1.2.0",
    # Bulbapedia mette le mosse proprie delle forme di Rotom sulla pagina unica della
    # specie; il dump le tiene separate, ed è il verso giusto.
    ("rotom", "Air Slash", "+"): "mossa di una forma, sulla pagina unica di Rotom",
    ("rotom", "Blizzard", "+"): "mossa di una forma, sulla pagina unica di Rotom",
    ("rotom", "Hydro Pump", "+"): "mossa di una forma, sulla pagina unica di Rotom",
    ("rotom", "Leaf Storm", "+"): "mossa di una forma, sulla pagina unica di Rotom",
    ("rotom", "Overheat", "+"): "mossa di una forma, sulla pagina unica di Rotom",
}

METODO = "train"          # l'unico metodo di Champions, come nel dump


def disfa_toppe(voci):
    """Riporta `voci` allo stato del dump, togliendo le toppe di un giro precedente.

    Serve a rendere lo script **rieseguibile senza distruggersi**: il confronto deve
    misurare il dump contro Bulbapedia, e `pokemon_moves.json` le toppe ce le ha già.
    Torna quante voci ha toccato.
    """
    try:
        with open(file_integrazioni_moveset(), encoding="utf-8") as f:
            toppe = (json.load(f) or {}).get("toppe") or {}
    except (OSError, ValueError):
        return 0
    quante = 0
    for chiave, sorgenti in toppe.items():
        for sorgente, blocco in sorgenti.items():
            blocco_voce = (voci.get(chiave) or {}).get(sorgente) or {}
            elenco = blocco_voce.get("moves")
            if elenco is None:
                continue
            for mossa in blocco.get("aggiunte") or {}:
                elenco.pop(mossa, None)
            for mossa in blocco.get("rimosse") or []:
                elenco.setdefault(mossa, METODO)
            blocco_voce["moves"] = dict(sorted(elenco.items()))
            quante += 1
    return quante


def mappa_bulbapedia(catalogo, titoli):
    """`{voce: (titolo, sezione, versione, mosse)}`. Si ferma sui blocchi ambigui."""
    specie = V.indice_specie(catalogo)
    fuori, non_risolti = {}, []
    for titolo in titoli:
        nome_specie = titolo.split(" (Pokémon)")[0]
        chiavi = specie.get(V.chiave_confronto(nome_specie), [])
        if len(chiavi) != 1:
            non_risolti.append(f"{titolo}: {len(chiavi)} voci di catalogo")
            continue
        testo = V.testo_pagina(titolo, False)
        if testo is None:
            non_risolti.append(f"{titolo}: pagina non leggibile")
            continue
        versione = (V.VERSIONE.search(testo) or [None, None])[1]
        cand = V.candidati(catalogo, chiavi[0])
        for sezione, mosse in V.blocchi(testo):
            voce, motivo = V.risolvi_blocco(nome_specie, sezione, cand)
            if voce is None:
                non_risolti.append(f"{titolo} [{sezione}]: {motivo}")
                continue
            fuori[voce] = (titolo, sezione, versione, mosse)
    return fuori, non_risolti


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    catalogo = load_catalog("pokemon")
    mosse_cat = load_catalog("moves")
    if not catalogo or not mosse_cat:
        print("Catalogo vuoto o illeggibile: non tocco niente.")
        return 1
    # I nomi di Bulbapedia non sono sempre le chiavi del catalogo: «King's Shield» ha
    # l'apostrofo dritto e «Mud-Slap» il trattino. Si risolve come ovunque qui.
    nomi = {V.chiave_confronto(k): k for k in mosse_cat}
    for k, v in mosse_cat.items():
        if v.get("nome_en"):
            nomi.setdefault(V.chiave_confronto(v["nome_en"]), k)

    moveset_doc = json.load(open(MOVESET_FILE, encoding="utf-8"))
    moveset = moveset_doc.get("voci") or {}
    # ⚠️ Il confronto va fatto sul **dump**, non su ciò che si vede: `pokemon_moves.json`
    # contiene già le toppe di un giro precedente, e confrontando quello la differenza
    # sparirebbe — il secondo giro scriverebbe `toppe: {}` cancellando il proprio
    # lavoro, in silenzio. Quindi le toppe presenti si disfano prima di misurare.
    # È lossless: nelle liste `champions` il metodo è `train` su tutte le 20 699 righe.
    disfatte = disfa_toppe(moveset)
    if disfatte:
        print(f"Toppe già presenti, disfatte per misurare: {disfatte} voci\n")
    pagine, non_risolti = mappa_bulbapedia(catalogo, V.elenco_pagine(False))
    if non_risolti:
        for r in non_risolti:
            print("X " + r)
        print(f"\n{len(non_risolti)} blocchi non risolti: non scrivo niente.")
        return 1

    toppe, ignorate, indecise, ignote = {}, [], [], []
    for voce, (titolo, _sezione, _versione, mosse_b) in pagine.items():
        blocco = (moveset.get(voce) or {}).get("champions") or {}
        mosse_d = blocco.get("moves")
        if not mosse_d:
            continue                     # niente lista nel dump: è un caso da integrare
        risolte = {}
        # ⚠️ `sorted`: `V.blocchi()` torna un **set**, e l'ordine di un set di stringhe
        # cambia da un processo all'altro (l'hash delle stringhe è randomizzato). Senza
        # questo, due giri scrivono lo stesso contenuto in ordine diverso e lo script
        # sembra non idempotente — misurato, l'md5 cambiava.
        for m in sorted(mosse_b):
            k = nomi.get(V.chiave_confronto(m))
            if k is None:
                ignote.append(f"{voce}: «{m}» non è una mossa del catalogo")
            else:
                risolte[k] = m
        differenze = (sorted((m, "+") for m in risolte if m not in mosse_d)
                      + sorted((m, "-") for m in mosse_d if m not in risolte))
        for mossa, verso in differenze:
            motivo = (DECISIONI.get((voce, mossa, verso))
                      or DECISIONI.get((None, mossa, verso)))
            if motivo:
                blocco_t = toppe.setdefault(voce, {"aggiunte": {}, "rimosse": [],
                                                   "motivi": {}})
                if verso == "+":
                    blocco_t["aggiunte"][mossa] = METODO
                else:
                    blocco_t["rimosse"].append(mossa)
                blocco_t["motivi"][mossa] = motivo
                continue
            if (voce, mossa, verso) in IGNORATE:
                ignorate.append((voce, mossa, verso))
                continue
            indecise.append(f"{voce}: «{mossa}» {'entra' if verso == '+' else 'esce'} "
                            f"(pagina {titolo})")

    for r in ignote:
        print("X " + r)
    for r in indecise:
        print("X differenza non decisa — " + r)
    if ignote or indecise:
        print(f"\n{len(ignote) + len(indecise)} problemi: non scrivo niente. "
              "Ogni differenza va decisa e scritta in DECISIONI o in IGNORATE.")
        return 1

    per_mossa = {}
    for voce, b in toppe.items():
        for m in list(b["aggiunte"]) + b["rimosse"]:
            per_mossa.setdefault(m, []).append(voce)
    print("Toppe da scrivere: %d voci" % len(toppe))
    for mossa, voci in sorted(per_mossa.items(), key=lambda x: (-len(x[1]), x[0])):
        verso = "+" if any(mossa in toppe[v]["aggiunte"] for v in voci) else "−"
        print("  %s %-16s %3d voci: %s%s" % (
            verso, mossa, len(voci), ", ".join(sorted(voci)[:6]),
            " …" if len(voci) > 6 else ""))
    print("\nDifferenze riconosciute e lasciate stare: %d" % len(ignorate))
    for voce, mossa, verso in sorted(ignorate):
        print("  = %-10s %-16s %s" % (voce, mossa, IGNORATE[(voce, mossa, verso)]))

    if args.dry_run:
        print("\n--dry-run: nessun file toccato.")
        return 0

    # ── 1. il dato curato ────────────────────────────────────────────────────
    percorso = file_integrazioni_moveset()
    documento = json.load(open(percorso, encoding="utf-8"))
    os.makedirs(_archive_dir(), exist_ok=True)
    shutil.copyfile(percorso, os.path.join(_archive_dir(),
                                           "moveset_integrazioni_pre-toppe.json"))
    oggi = datetime.now().strftime("%Y-%m-%d")
    documento.setdefault("_meta", {})["toppe_spiegazione"] = (
        "Singole mosse aggiunte o tolte sopra una lista che il dump HA già: il dump di "
        "PokéAPI è fermo prima della versione 1.2.0 di Champions. Le applica "
        "applica_toppe_moveset() in blueprints/pokemon.py. Scritte da "
        "scripts/applica_toppe_champions.py.")
    documento["toppe"] = {
        voce: {"champions": {"fonte": "bulbapedia + changelog ufficiale 1.2.0",
                             "versione": "1.2.0", "scritta_il": oggi,
                             "aggiunte": b["aggiunte"], "rimosse": sorted(b["rimosse"]),
                             "motivi": b["motivi"]}}
        for voce, b in sorted(toppe.items())
    }
    with open(percorso, "w", encoding="utf-8") as f:
        # indent=1 come gli altri due scrittori di questi file: `indent=2` li
        # reindenta tutti e fa un diff da 100 000 righe per 33 voci cambiate.
        json.dump(documento, f, ensure_ascii=False, indent=1)
    print(f"\nScritto {os.path.relpath(percorso, RADICE)} "
          "(copia in data/archive/moveset_integrazioni_pre-toppe.json)")

    # ── 2. e il file che l'app legge ─────────────────────────────────────────
    applicate, superate, forme_proprie = applica_toppe_moveset(moveset)
    moveset_doc["voci"] = moveset
    with open(MOVESET_FILE, "w", encoding="utf-8") as f:
        json.dump(moveset_doc, f, ensure_ascii=False, indent=1)
    print(f"Applicate a data/catalog/pokemon_moves.json: {len(applicate)} voci"
          + (f", superate {superate}" if superate else ""))
    if forme_proprie:
        # Dal 21/09/2026 una toppa raggiunge anche le forme della specie. Queste no:
        # hanno una lista **loro**, quindi la fonte le distingue e applicargliela
        # sarebbe inventare. Va letto, non ignorato: l'altra spiegazione possibile e'
        # che sia la lista della forma a essere rimasta indietro.
        print(f"Forme con una lista propria, non toccate: {forme_proprie}")
    print("\n⚠️  Ora rilancia `python scripts/allinea_mosse_regulation.py`: "
          "l'elenco mosse delle regulation è derivato dalle liste appena cambiate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
