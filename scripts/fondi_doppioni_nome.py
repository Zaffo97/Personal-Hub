#!/usr/bin/env python
"""Fonde le coppie di chiavi diverse che portano lo **stesso nome**.

    python scripts/fondi_doppioni_nome.py [--dry-run]

Le 24 coppie chiuse da `fondi_abilita_doppie.py` avevano una firma precisa: una voce
con la traduzione ufficiale e una senza. Restavano fuori le coppie in cui **le due
chiavi hanno gli stessi `nome_it` e `nome_en`**, che sono un doppione altrettanto
vero ma invisibile a quel criterio.

Non è un problema estetico. `risolviChiave()` accetta chiave, nome italiano e nome
inglese: con due chiavi che si chiamano allo stesso modo **ne vince una sola**, e per
`Sheer Force` vinceva `Forzabruta`, che è inerte, invece di `Forza Bruta`, che ha
l'effetto — misurato: un Pokémon con Sheer Force non applicava niente. Il tampone
(`indiceNomi()` a parità di nome tiene la voce con un `effect`) fa sì che l'effetto si
applichi; questo script toglie la causa.

**Quale delle due sopravvive.** Non «quella col nome ufficiale»: su `King's Rock`
darebbe la voce sbagliata, perché la variante con l'apostrofo curvo è quella importata
e inerte mentre quella con l'apostrofo dritto è curata, ha `effect: flinch_chance` ed è
nei filtri di MA e MB.

A restare è la **chiave giusta** — quella che segue la convenzione del file e che i
filtri già nominano — e i campi che le mancano **le arrivano dall'altra** prima che
venga rimossa: un buco viene colmato, e un `effect` vuoto viene sostituito da quello
vero. Così su `Forzabruta` resta la chiave che coincide con `nome_it` e ci arriva
comunque l'`effect` di `Forza Bruta`, che è l'unica cosa per cui quella voce esisteva.

| Coppia | Resta | Perché |
|---|---|---|
| `Forza Bruta` / `Forzabruta` | **`Forzabruta`** | è la chiave che coincide con `nome_it`, la convenzione del file; riceve l'`effect` `sheer_force` dall'altra |
| `Dragonize` / `Pelledrago` | **`Pelledrago`** | stessa abilità inventata scritta in due lingue: resta il nome italiano, come per le altre «Pelle…» |
| `Piercing Drill` / `Punta Perforante` | **`Punta Perforante`** | idem |
| `Spicy Spray` / `Spargipiccante` | **`Spargipiccante`** | idem |
| `Occhio Interiore ` / `Occhio Interiore` | **`Occhio Interiore`** | la chiave gemella ha **uno spazio in fondo**; la sua `desc` (l'altra ce l'ha vuota) viene portata sulla superstite |
| `Freeze Dry` / `Freeze-Dry` | **`Freeze-Dry`** | identiche campo per campo, resta quella che coincide col nome inglese ufficiale |
| `Mud Slap` / `Mud-Slap` | **`Mud Slap`** | è la più completa (`effect_chance: 100`, che l'altra non ha) ed è quella nei filtri |
| `King's Rock` / `King’s Rock` | **`King's Rock`** | curata, con `effect: flinch_chance`, ed è quella nei filtri |

**I filtri delle regulation vengono aggiornati di conseguenza**: dove compare la chiave
rimossa ci va la superstite, senza duplicarla. MA e MB contengono **entrambe** le
varianti di `Freeze Dry`, quindi il loro conteggio mosse scende di uno — è la stessa
mossa contata due volte, non una mossa persa.

Copie di sicurezza in `data/archive/` prima di scrivere, sia dei file del catalogo sia
dei filtri toccati. Rieseguibile: alla seconda esecuzione non trova più niente.
"""
import argparse
import io
import json
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGO = os.path.join(RADICE, "data", "catalog")
FILTRI = os.path.join(RADICE, "data", "regulations")
ARCHIVIO = os.path.join(RADICE, "data", "archive")

# db -> [(chiave che resta, chiave che sparisce), …]
COPPIE = {
    "abilities": [
        ("Forzabruta",        "Forza Bruta"),
        ("Pelledrago",        "Dragonize"),
        ("Punta Perforante",  "Piercing Drill"),
        ("Spargipiccante",    "Spicy Spray"),
        ("Occhio Interiore",  "Occhio Interiore "),
    ],
    "moves": [
        ("Freeze-Dry", "Freeze Dry"),
        ("Mud Slap",   "Mud-Slap"),
    ],
    "items": [
        ("King's Rock", "King’s Rock"),
    ],
}
AVVOLTI = {"abilities": "abilities"}
CAMPO_FILTRO = {"abilities": "abilities", "moves": "moves", "items": "items"}


def piu_ricca(voce):
    """Quanto è completa una voce: campi non vuoti, con peso a `effect`."""
    punti = sum(1 for v in voce.values() if v not in (None, "", [], {}))
    eff = voce.get("effect")
    if eff and (eff if isinstance(eff, str) else eff.get("type")) not in (None, "none"):
        punti += 10
    return punti


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra cosa farebbe senza scrivere niente")
    args = ap.parse_args()

    problemi, piano, gia_fatte = [], [], []
    dati_db = {}
    for db, coppie in COPPIE.items():
        percorso = os.path.join(CATALOGO, f"{db}.json")
        with open(percorso, encoding="utf-8") as f:
            dati = json.load(f)
        voci = dati[AVVOLTI[db]] if db in AVVOLTI else dati
        dati_db[db] = (percorso, dati, voci)
        for resta, sparisce in coppie:
            if sparisce not in voci and resta in voci:
                gia_fatte.append(f"{db}/{sparisce}")
                continue
            if resta not in voci or sparisce not in voci:
                problemi.append(f"{db}: manca una delle due — {resta!r} / {sparisce!r}")
                continue
            piano.append((db, resta, sparisce))

    if problemi:
        print("Mi fermo senza scrivere niente:")
        for p in problemi:
            print("  ⚠️ " + p)
        return 1
    if not piano:
        print(f"Niente da fare: le {len(gia_fatte)} coppie sono già fuse.")
        return 0

    # cosa cambia nei filtri delle regulation
    tocchi_filtri = {}
    for nome in sorted(os.listdir(FILTRI)):
        if not nome.endswith(".json"):
            continue
        with open(os.path.join(FILTRI, nome), encoding="utf-8") as f:
            filtro = json.load(f)
        cambi = []
        for db, resta, sparisce in piano:
            campo = CAMPO_FILTRO[db]
            elenco = filtro.get(campo)
            if elenco and sparisce in elenco:
                cambi.append((campo, resta, sparisce, resta in elenco))
        if cambi:
            tocchi_filtri[nome] = (filtro, cambi)

    print(f"{len(piano)} coppie da fondere"
          + (f" ({len(gia_fatte)} già fatte)" if gia_fatte else ""))
    for db, resta, sparisce in piano:
        _, _, voci = dati_db[db]
        print(f"  {db:10s} resta {resta!r:22s} (completezza {piu_ricca(voci[resta]):3d})"
              f"  sparisce {sparisce!r:20s} ({piu_ricca(voci[sparisce])})")
    for nome, (_, cambi) in tocchi_filtri.items():
        for campo, resta, sparisce, gia in cambi:
            print(f"  filtro {nome:12s} {campo}: {sparisce!r} → "
                  + (f"tolto, {resta!r} c'è già" if gia else f"{resta!r}"))

    if args.dry_run:
        print("\n--dry-run: nessuna modifica.")
        return 0

    os.makedirs(ARCHIVIO, exist_ok=True)
    toccati = {db for db, _, _ in piano}
    for db in toccati:
        percorso, dati, _ = dati_db[db]
        with open(os.path.join(ARCHIVIO, f"catalog_{db}_pre-doppioni-nome.json"),
                  "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)

    for db, resta, sparisce in piano:
        _, _, voci = dati_db[db]
        vincente, perdente = voci[resta], voci[sparisce]
        for campo, valore in perdente.items():
            if valore in (None, "", [], {}):
                continue
            attuale = vincente.get(campo)
            if attuale in (None, "", [], {}):
                vincente[campo] = valore          # colma un buco
            elif campo == "effect" and attuale in ({"type": "none"}, "none"):
                vincente[campo] = valore          # l'effetto vero batte quello vuoto
        del voci[sparisce]

    for db in toccati:
        percorso, dati, _ = dati_db[db]
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
        print(f"Scritto {os.path.relpath(percorso, RADICE)}")

    for nome, (filtro, cambi) in tocchi_filtri.items():
        with open(os.path.join(ARCHIVIO, f"regulation_{nome[:-5]}_pre-doppioni-nome.json"),
                  "w", encoding="utf-8") as f:
            json.dump(filtro, f, ensure_ascii=False, indent=2)
        for campo, resta, sparisce, _ in cambi:
            elenco = [x for x in filtro[campo] if x != sparisce]
            if resta not in elenco:
                elenco.append(resta)
            filtro[campo] = sorted(elenco)
        filtro["last_updated"] = "2026-08-11"
        with open(os.path.join(FILTRI, nome), "w", encoding="utf-8") as f:
            json.dump(filtro, f, ensure_ascii=False, indent=2)
        print(f"Aggiornato filtro {nome}: "
              + ", ".join(f"{c[0]} → {len(filtro[c[0]])} voci" for c in cambi))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
