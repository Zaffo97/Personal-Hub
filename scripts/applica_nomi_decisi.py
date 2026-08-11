#!/usr/bin/env python
"""Applica le scelte fatte a mano sui nomi in disaccordo fra PokéAPI e wiki.

    python scripts/applica_nomi_decisi.py [--dry-run]

`importa_nomi_wiki.py` **non sovrascrive** una traduzione già presa da PokéAPI:
dove le due fonti non concordano si limita a segnalarlo, perché nessuna delle due
è sempre giusta — PokéAPI abbrevia, la wiki ha refusi. Le voci segnalate sono state
guardate una per una; questo script scrive **solo** quelle che Davide ha deciso
l'11/08/2026, e nient'altro.

**Cosa cambia e perché:**

| Voce | Da | A | Motivo |
|---|---|---|---|
| `Aura Sphere` | Forzasfera | Sferapulsar | nome ufficiale italiano secondo la wiki |
| `Heal Pulse` | Ondasana | Curapulsar | idem |
| `Max Revive` | Revitalizz. Max | Revitalizzante Max | l'abbreviazione serve alla casella di testo del gioco, qui lo spazio non manca |
| `Exp. Share` | Condividi esp. | Condividi Esperienza | idem |
| `Megasolar` | `nome_en: Mega Sol` | `nome_en: Megasolar` | «Mega Sol» non è un nome inglese: era un aggancio sbagliato dell'import |

**Cosa NON cambia**, per decisione esplicita:

- i **6 refusi della wiki** (`Vasterngia`, `Morostretto`, `Psicotrasfer`,
  `Intoenergia`, `Ondaoscura`, `Ombropanico`): le forme in uso sono quelle corrette
- `Self-Destruct`, che è **già** «Autodistruzione», la forma estesa
- `Mirror Herb` → «Foglia carbone»: è quello che la wiki scrive in scheda e infobox,
  ed è l'unico dei 20 che non somiglia né all'inglese né al giapponese (*Mimic Herb*).
  Resta, dichiarato sospetto nel backlog: meglio una lacuna nota di un nome inventato

Le **chiavi non si toccano**: cambia solo `nome_it` (o `nome_en` per Megasolar), cioè
ciò che si legge a schermo. Lo script verifica il valore di partenza di ogni voce e si
ferma senza scrivere se non è quello atteso, così non può lavorare alla cieca né
rifare il giro due volte. Copia in `data/archive/` prima di scrivere.
"""
import argparse
import io
import json
import os
import shutil
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGO = os.path.join(RADICE, "data", "catalog")
ARCHIVIO = os.path.join(RADICE, "data", "archive")

# file -> chiave della voce -> (campo, valore atteso, valore nuovo)
DECISIONI = {
    "moves": {
        "Aura Sphere": ("nome_it", "Forzasfera", "Sferapulsar"),
        "Heal Pulse":  ("nome_it", "Ondasana",   "Curapulsar"),
    },
    "items": {
        "Max Revive": ("nome_it", "Revitalizz. Max", "Revitalizzante Max"),
        "Exp. Share": ("nome_it", "Condividi esp.",  "Condividi Esperienza"),
    },
    "abilities": {
        "Megasolar": ("nome_en", "Mega Sol", "Megasolar"),
    },
}
# Solo le abilità sono avvolte in {"abilities": …}; mosse e oggetti sono piatti,
# come già documentato per `voci_catalogo()` in blueprints/pokemon.py.
AVVOLTI = {"abilities": "abilities"}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra cosa farebbe senza scrivere niente")
    args = ap.parse_args()

    piano, problemi, gia_fatte = [], [], []
    for db, voci in DECISIONI.items():
        percorso = os.path.join(CATALOGO, f"{db}.json")
        with open(percorso, encoding="utf-8") as f:
            dati = json.load(f)
        contenuto = dati[AVVOLTI[db]] if db in AVVOLTI else dati
        for chiave, (campo, atteso, nuovo) in voci.items():
            if chiave not in contenuto:
                problemi.append(f"{db}: la voce '{chiave}' non esiste")
                continue
            attuale = contenuto[chiave].get(campo)
            if attuale == nuovo:
                gia_fatte.append(f"{db}/{chiave}")
            elif attuale != atteso:
                problemi.append(
                    f"{db}/{chiave}.{campo}: mi aspettavo {atteso!r}, trovato {attuale!r}")
            else:
                piano.append((db, percorso, dati, contenuto, chiave, campo, atteso, nuovo))

    if problemi:
        print("Mi fermo senza scrivere niente:")
        for p in problemi:
            print("  ⚠️ " + p)
        return 1
    if not piano:
        print(f"Niente da fare: le {len(gia_fatte)} decisioni sono già applicate.")
        return 0

    print(f"{len(piano)} nomi da cambiare"
          + (f" ({len(gia_fatte)} già a posto)" if gia_fatte else ""))
    for db, _, _, _, chiave, campo, atteso, nuovo in piano:
        print(f"  {db:10s} {chiave:14s} {campo}: {atteso!r} → {nuovo!r}")

    if args.dry_run:
        print("\n--dry-run: nessuna modifica.")
        return 0

    os.makedirs(ARCHIVIO, exist_ok=True)
    scritti = set()
    for db, percorso, dati, contenuto, chiave, campo, _, nuovo in piano:
        if percorso not in scritti:
            copia = os.path.join(ARCHIVIO, f"catalog_{db}_pre-nomi-decisi.json")
            shutil.copy2(percorso, copia)
            print(f"Copia di sicurezza: {os.path.relpath(copia, RADICE)}")
            scritti.add(percorso)
        contenuto[chiave][campo] = nuovo

    for db, percorso, dati, _, _, _, _, _ in piano:
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)

    print(f"Scritti {len(scritti)} file del catalogo.")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
