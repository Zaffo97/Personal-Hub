#!/usr/bin/env python
"""Ridà a `Megasolar` il nome che Mega Meganium cita, e l'effetto che aveva.

    python scripts/ricollega_megasolar.py [--dry-run]

**Cosa era successo.** Prima dell'11/08/2026 c'erano tre voci in gioco:

- la chiave **`Mega Sol`**, con l'effetto «agisce come se ci fosse il Sole forte»
- la chiave **`Megasolar`**, inerte, il cui `nome_en` era **`Mega Sol`** — ed è
  questa la voce che il catalogo Pokémon cita su **Mega Meganium**, perché il
  catalogo scrive le abilità col nome **inglese**
- **`Terra Estrema`** (`Desolate Land`), ufficiale e inerte, di Primal Groudon

La fusione delle abilità doppie ha portato l'effetto da `Mega Sol` su `Terra
Estrema` e ha cancellato la chiave: per **Primal Groudon è giusto**, e infatti oggi
Desolate Land applica il sole. Poi il giro sui nomi ha cambiato il `nome_en` di
`Megasolar` da `Mega Sol` a `Megasolar`, e da quel momento il nome scritto su Mega
Meganium **non risolve più su nessuna voce**: nessuna descrizione, nessuna
traduzione, nessun effetto — e nessun errore, perché una tendina che non trova la
voce mostra il nome grezzo e tace.

**Cosa fa questo script**, decisioni di Davide del 10/09/2026:

1. rimette `nome_en: "Mega Sol"` su `Megasolar`, cioè il legame com'era prima del
   giro sui nomi. `nome_it` resta `Megasolar` e **la chiave non si tocca**
2. le ridà il blocco che la voce cancellata `Mega Sol` aveva — sole permanente,
   Fuoco ×1.5, Acqua ×0.5, Palla Clima di tipo Fuoco — copiato **alla lettera** da
   `data/archive/abilities_pre-fusione.json`, non riscritto a mano

⚠️ Il punto 2 **cambia i numeri del calcolatore**: da qui in poi Mega Meganium con
quell'abilità applica il sole. È una decisione di contenuto, non un dato dedotto.

Scrive con `_save_abilities()`, che tiene la copia di sicurezza automatica.
Rieseguibile: alla seconda esecuzione non trova più niente da fare e lo dice.
"""
import argparse
import io
import json
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

ARCHIVIO_PRE_FUSIONE = os.path.join(RADICE, "data", "archive", "abilities_pre-fusione.json")
FILE_POKEMON = os.path.join(RADICE, "data", "catalog", "pokemon.json")

CHIAVE = "Megasolar"
NOME_CITATO = "Mega Sol"          # come il catalogo Pokémon la chiama
VOCE_CANCELLATA = "Mega Sol"      # la chiave che aveva l'effetto, prima della fusione

# i campi da riportare: `effect` più i campi di calcolo che gli vivono accanto
CAMPI = ("desc", "category", "effect", "weather_override",
         "atk_boost", "atk_penalty", "weather_ball_type")


def carica(percorso):
    with io.open(percorso, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra cosa farebbe senza scrivere niente")
    args = ap.parse_args()

    from blueprints.pokemon import load_abilities, _save_abilities

    dati = load_abilities()
    ab = dati.get("abilities") or {}
    if CHIAVE not in ab:
        print(f"Mi fermo: la voce '{CHIAVE}' non è nel catalogo delle abilità.")
        return 1

    # la sorgente è l'archivio, non la memoria: il blocco si copia, non si riscrive
    try:
        vecchie = carica(ARCHIVIO_PRE_FUSIONE)
        vecchie = vecchie.get("abilities", vecchie)
        sorgente = vecchie[VOCE_CANCELLATA]
    except Exception as e:
        print(f"Mi fermo: non riesco a leggere '{VOCE_CANCELLATA}' "
              f"da {os.path.relpath(ARCHIVIO_PRE_FUSIONE, RADICE)} ({e})")
        return 1

    # e che quel nome sia davvero citato da un Pokémon va verificato, non creduto
    pokemon = carica(FILE_POKEMON)
    citano = []
    for chiave, voce in pokemon.items():
        for nome, elenco in ([(voce.get("name") or chiave, voce.get("abilities") or [])]
                             + [(nf, f.get("abilities") or [])
                                for nf, f in (voce.get("forms") or {}).items()]):
            if NOME_CITATO in elenco:
                citano.append(nome)
    if not citano:
        print(f"Mi fermo: nessun Pokémon cita '{NOME_CITATO}', quindi il legame "
              f"da ricucire non esiste più e questo script non serve.")
        return 1

    voce = ab[CHIAVE]
    da_fare = []
    if voce.get("nome_en") != NOME_CITATO:
        da_fare.append(f"nome_en: {voce.get('nome_en')!r} -> {NOME_CITATO!r}")
    for campo in CAMPI:
        if voce.get(campo) != sorgente.get(campo):
            da_fare.append(f"{campo}: {json.dumps(voce.get(campo), ensure_ascii=False)[:40]}"
                           f" -> {json.dumps(sorgente.get(campo), ensure_ascii=False)[:60]}")

    print(f"'{CHIAVE}' è citata come '{NOME_CITATO}' da: {', '.join(citano)}")
    if not da_fare:
        print("Niente da fare: la voce ha già il nome e l'effetto giusti.")
        return 0
    print(f"{len(da_fare)} campi da cambiare:")
    for riga in da_fare:
        print("   " + riga)

    if args.dry_run:
        print("\n--dry-run: nessuna modifica.")
        return 0

    voce["nome_en"] = NOME_CITATO
    for campo in CAMPI:
        if campo in sorgente:
            voce[campo] = sorgente[campo]
    # ⚠️ `nome_it` resta `Megasolar` e la chiave non si rinomina: le chiavi del
    # catalogo le usano i filtri delle regulation e i team salvati.
    voce["nome_it"] = CHIAVE

    dati["abilities"] = ab
    _save_abilities(dati)
    print(f"\nScritto. '{CHIAVE}' ora risponde al nome '{NOME_CITATO}' e applica "
          f"{sorgente['effect'].get('weather')}.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
