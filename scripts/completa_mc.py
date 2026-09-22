#!/usr/bin/env python
"""Mette nel roster di Regulation M-C le voci che M-C aggiunge a M-B.

    python scripts/completa_mc.py [--dry-run]

⚠️ **Da dove viene il dato, perché è la sola cosa che conta qui.** Non da questo
script: le voci di M-C sono nel repo dal 21/09/2026, in
`data/catalog/moveset_integrazioni.json` — le **26 specie** sotto `voci` e le **6
Mega** sotto `eredita` — e il roster è confermato **due volte**, da Serebii e da
Game8. Qui non si decide niente e non si inventa niente: si prendono quei nomi, si
risolvono sul catalogo e si aggiungono a quelli di M-B.

⚠️ **Perché «a quelli di M-B».** Le regulation di Champions sono **cumulative**, e non
è un'assunzione: misurato: il roster di MA è contenuto in quello di MB (MB = MA + 29
voci, MA − MB = 0). M-C aggiunge, non sostituisce. Il file `mc.json` nasce infatti
come copia di `mb.json` dal pulsante «crea regulation», ed è la base giusta: gli
manca solo l'aggiunta.

**Cosa NON fa, di proposito:**

- **le mosse** non le scrive: le deriva `scripts/allinea_mosse_regulation.py --reg mc`
  dall'unione di quelle che il roster può imparare. Decisione di Davide del
  18/09/2026, e va lanciato **dopo** questo script perché il roster è cambiato
- **la mega_map** non la tocca: la completa `scripts/completa_mega_map.py`, che
  collega ogni Mega del roster alla sua specie base. ⚠️ Su `mc` si limita a
  **collegare**: aggiungere specie base è permesso solo dove `AGGIUNGI_BASI` lo dice,
  e lì non c'è — tutte e sei le basi delle Mega di M-C stanno già nel roster dopo
  questo passo
- **gli oggetti** restano i 58 di MA/MB, ed è un **buco dichiarato**: nessuna fonte
  dice quali oggetti M-C aggiunga. Meglio una lacuna scritta di un numero inventato

Copia di sicurezza in `data/archive/regulation_mc_pre-completamento.json`.
Rieseguibile: se le voci ci sono già non tocca il file e lo dice.
"""
import argparse
import io
import json
import os
import shutil
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)
DATA = os.path.join(RADICE, "data")
ARCHIVIO = os.path.join(DATA, "archive")
CATALOGO = os.path.join(DATA, "catalog", "pokemon.json")
INTEGRAZIONI = os.path.join(DATA, "catalog", "moveset_integrazioni.json")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def indice_nomi(cat):
    """Ogni modo di nominare una voce -> il nome con cui il roster la scrive.

    ⚠️ Le chiavi di `moveset_integrazioni.json` sono un misto: alcune sono slug
    (`pawmot`, `arboliva`), altre nomi di forma (`Alolan Persian`). Il roster invece
    usa **un solo** modo: il `name` della specie o il nome della forma. Senza questa
    risoluzione si scriverebbero nel roster dei nomi che il catalogo non conosce, e
    un nome inesistente lì dentro **non dà errore: sparisce e basta** (è successo con
    Floette il 13/09/2026).
    """
    fuori = {}
    for chiave, voce in cat.items():
        nome = voce.get("name") or chiave
        for modo in (chiave, nome, voce.get("nome_en"), voce.get("nome_it")):
            if modo:
                fuori.setdefault(modo, nome)
                fuori.setdefault(modo.lower(), nome)
        for forma, dati in (voce.get("forms") or {}).items():
            for modo in (forma, dati.get("slug"), dati.get("nome_en"),
                         dati.get("nome_it")):
                if modo:
                    fuori.setdefault(modo, forma)
                    fuori.setdefault(modo.lower(), forma)
    return fuori


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="dice cosa farebbe e non scrive niente")
    args = ap.parse_args()

    from blueprints.pokemon import _list_regulation_files, _salva_filtro

    cat = json.load(io.open(CATALOGO, encoding="utf-8"))
    integ = json.load(io.open(INTEGRAZIONI, encoding="utf-8"))
    reg = next((r for r in _list_regulation_files() if r.get("id") == "mc"), None)
    if not reg:
        print("Regulation `mc` non è nel registro: niente da completare.")
        return 1
    percorso = os.path.join(DATA, reg["filter_file"])
    filtro = json.load(io.open(percorso, encoding="utf-8"))
    mb = json.load(io.open(os.path.join(DATA, "regulations", "mb.json"),
                           encoding="utf-8"))

    # ⚠️ Si parte da **MB**, non da quello che c'è ora in `mc.json`: se qualcuno ha
    # già fatto un giro a mano, ripartire dal file lo raddoppierebbe. Le regulation
    # sono cumulative, quindi MB è il punto di partenza per costruzione.
    if not mb.get("pokemon"):
        print("MB non ha un roster: mi fermo invece di indovinare.")
        return 1

    nomi = indice_nomi(cat)
    voci = list(integ.get("voci") or {}) + list(integ.get("eredita") or {})
    risolte, perse = [], []
    for v in voci:
        n = nomi.get(v) or nomi.get(v.lower())
        (risolte.append(n) if n else perse.append(v))
    if perse:
        # ⚠️ Fermarsi, non saltare: un nome che il catalogo non conosce scritto nel
        # roster non dà errore, sparisce — e si scoprirebbe mesi dopo contando.
        print(f"INTERROTTO: {len(perse)} voci di M-C non esistono nel catalogo:")
        for v in perse:
            print(f"    {v}")
        return 1

    prima = list(filtro.get("pokemon") or [])
    nuovo = sorted(set(mb["pokemon"]) | set(risolte))
    aggiunte = sorted(set(nuovo) - set(mb["pokemon"]))
    gia_in_mb = sorted(set(risolte) & set(mb["pokemon"]))

    print(f"Voci di M-C nel repo    : {len(voci)}  (26 specie + 6 Mega)")
    print(f"gia' presenti in MB     : {len(gia_in_mb)}"
          + (f"  ({', '.join(gia_in_mb)})" if gia_in_mb else ""))
    print(f"da aggiungere           : {len(aggiunte)}")
    print(f"roster: MB {len(mb['pokemon'])}  ->  MC {len(nuovo)}"
          f"   (adesso mc.json ne ha {len(prima)})")
    print("\nLe voci aggiunte:")
    for n in aggiunte:
        print(f"    {n}")

    if prima == nuovo:
        print("\nNiente da fare: il roster di MC e' gia' quello giusto.")
        return 0
    if args.dry_run:
        print(f"\n--dry-run: scriverei {len(nuovo)} nomi. Non ho toccato niente.")
        return 0

    os.makedirs(ARCHIVIO, exist_ok=True)
    copia = os.path.join(ARCHIVIO, "regulation_mc_pre-completamento.json")
    shutil.copy2(percorso, copia)
    print(f"\nCopia di sicurezza: {os.path.relpath(copia, RADICE)}")

    if not _salva_filtro(reg, "pokemon", nuovo):
        print("INTERROTTO: `_salva_filtro()` non ha scritto.")
        return 1
    print(f"Scritto: roster di MC a {len(nuovo)} voci.")
    print("\nOra, in quest'ordine:")
    print("    python scripts/completa_mega_map.py     # collega le 6 Mega nuove")
    print("    python scripts/allinea_mosse_regulation.py --reg mc")
    return 0


if __name__ == "__main__":
    sys.exit(main())
