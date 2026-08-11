#!/usr/bin/env python
"""Fonde le coppie di abilità doppie: l'effetto passa sulla voce ufficiale.

    python scripts/fondi_abilita_doppie.py [--dry-run]

**Il problema.** `data/catalog/abilities.json` conteneva due famiglie di voci per
la stessa abilità:

- **307 voci ufficiali**, con `nome_it`/`nome_en` presi da PokéAPI e dalla wiki.
  Sono quelle a cui i Pokémon sono collegati — il catalogo Pokémon cita le abilità
  col **nome inglese** (`Swift Swim`), che è il `nome_en` di queste voci
- **108 voci vecchie**, con `nome_it == nome_en == chiave`, senza traduzione — ma
  con il blocco `effect` che il calcolatore usa davvero

Gli effetti stavano quindi **dalla parte sbagliata**: dei 307 nomi di abilità
posseduti dai Pokémon, **zero** risolvevano su un effetto attivo, e tutti e 56 gli
effetti del file erano irraggiungibili partendo da un Pokémon. Misurato prima della
fusione: Kingdra sotto pioggia con **Swift Swim** restava a 105 di Velocità invece
di 210, perché `Nuotovelox` (la voce con `nome_en: Swift Swim`) era inerte e
l'effetto stava su `Nuoto Veloce`, che nessuna tendina offre.

**Cosa fa lo script.** Per ognuna delle coppie qui sotto:

1. copia sulla voce **ufficiale** il blocco `effect`, la `category` e i campi extra
   di calcolo (`weather_ball_type`, `atk_stat_mult`, …) presi dalla **vecchia**
2. porta anche la `desc` della vecchia, che descrive l'effetto applicato davvero
   («La Speed è raddoppiata sotto la Pioggia») invece della formula generica
   dell'ufficiale («Se piove, la statistica Velocità aumenta»)
3. **elimina** la voce vecchia: 415 → 391 voci, una sola per abilità

`nome_it`, `nome_en` e la chiave restano quelli **ufficiali**: la chiave è
l'identità della voce e non si rinomina.

**Le coppie non sono indovinate.** L'accoppiamento automatico per somiglianza di
testo è stato provato e sbagliava (proponeva `Combattività` → `Bruciaimpeto`,
`Nuoto Veloce` → `Clorofilla`): qui ogni voce vecchia è mappata a mano
sull'**abilità reale che il suo `effect` descrive**, e lo script risolve quel nome
inglese contro i dati. Se un nome non trova esattamente una voce, si ferma senza
scrivere niente.

**Cosa NON tocca.** Le 10 voci il cui effetto non corrisponde a nessuna abilità
reale (`Nervosismo` e `Polifagia`, SpA +50% fisso; `Tiratore`, +30% sulle mosse ad
area; `Manto Neve`, Difesa +50% con la neve, che è la meccanica della neve e non
Snow Cloak; `Sforzo`, `Tempra`, `Vento Misterioso`, `Assorbifuoco`, `Colpo Secco`,
`Compressione`). Sono probabilmente abilità di Champions: accoppiarle vorrebbe dire
decidere che l'effetto attuale è sbagliato. Decisione di Davide dell'11/08/2026:
restano come sono. Idem per le 7 voci senza traduzione ma **appese a un Pokémon**
(`Download`, `Eelevate`, `Fire Mane`, `Libero`, `Punk Rock`, `Teravolt`,
`Transistor`), che non sono doppioni di nessuno.

Copia di sicurezza in `data/archive/abilities_pre-fusione.json` prima di scrivere.
Rieseguibile: alla seconda esecuzione non trova più niente da fare e lo dice.
"""
import argparse
import io
import json
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

FILE_ABILITA = os.path.join(RADICE, "data", "catalog", "abilities.json")
FILE_POKEMON = os.path.join(RADICE, "data", "catalog", "pokemon.json")
ARCHIVIO = os.path.join(RADICE, "data", "archive", "abilities_pre-fusione.json")

# voce vecchia (con l'effetto) -> nome inglese dell'abilità che quell'effetto descrive
COPPIE = {
    "Assorbiacqua":       "Water Absorb",
    "Voltassorbi":        "Volt Absorb",
    "Combattività":       "Guts",
    "Erboristeria":       "Overgrow",
    "Torrente":           "Torrent",
    "Torrentismo":        "Torrent",      # seconda vecchia sulla stessa ufficiale
    "Vampirico":          "Blaze",
    "Filtraggio":         "Filter",
    "Prisma Armatura":    "Prism Armor",
    "Schermosaldo":       "Solid Rock",
    "Multiscaglia":       "Multiscale",
    "Ombra Fantasma":     "Shadow Shield",
    "Scudo Peluria":      "Fur Coat",
    "Spessore":           "Thick Fat",
    "Squame Miracolo":    "Marvel Scale",
    "Passo Veloce":       "Quick Feet",
    "Nuoto Veloce":       "Swift Swim",
    "Fuga":               "Sand Rush",
    "Manto Slaccio":      "Slush Rush",
    "Pioggerella":        "Drizzle",
    "Nevischio":          "Snow Warning",
    "Tempesta di Sabbia": "Sand Stream",
    "Mega Sol":           "Desolate Land",
    "Pioggia Perpetua":   "Primordial Sea",
}

# campi di calcolo che vivono accanto a `effect`, non dentro
CAMPI_EXTRA = (
    "stab_multiplier", "immunity", "speed_multiplier", "guts", "bp_multiplier",
    "super_effective_reduction", "sheer_force", "contact_reduction", "fire_weakness",
    "weather_override", "atk_boost", "atk_penalty", "weather_ball_type", "multiscale",
    "atk_stat_mult", "fire_blocked", "def_multiplier", "technician", "spread_boost",
)


def carica(percorso):
    with open(percorso, encoding="utf-8") as f:
        return json.load(f)


def attivo(voce):
    return (voce.get("effect") or {}).get("type") not in (None, "none")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra cosa farebbe senza scrivere niente")
    args = ap.parse_args()

    dati = carica(FILE_ABILITA)
    ab = dati["abilities"]
    pokemon = carica(FILE_POKEMON)

    # nomi inglesi realmente posseduti da un Pokémon: servono a provare che la
    # voce che riceve l'effetto è quella a cui i Pokémon sono collegati
    posseduti = set()
    for voce in pokemon.values():
        posseduti.update(voce.get("abilities") or [])
        for forma in (voce.get("forms") or {}).values():
            posseduti.update(forma.get("abilities") or [])

    per_en = {}
    for chiave, voce in ab.items():
        per_en.setdefault(voce.get("nome_en"), []).append(chiave)

    piano, problemi, gia_fatte = [], [], []
    for vecchia, nome_en in COPPIE.items():
        if vecchia not in ab:
            gia_fatte.append(vecchia)
            continue
        candidate = [k for k in per_en.get(nome_en, []) if k != vecchia]
        if len(candidate) != 1:
            problemi.append(f"{vecchia}: '{nome_en}' risolve su {len(candidate)} voci {candidate}")
            continue
        ufficiale = candidate[0]
        if not attivo(ab[vecchia]):
            problemi.append(f"{vecchia}: non ha nessun effetto da spostare")
            continue
        piano.append((vecchia, ufficiale, nome_en, nome_en in posseduti))

    if gia_fatte and not piano:
        print(f"Niente da fare: le {len(gia_fatte)} coppie sono già fuse.")
        return 0
    if problemi:
        print("Mi fermo senza scrivere niente — queste righe non sono verificabili:")
        for p in problemi:
            print("  ⚠️ " + p)
        return 1

    print(f"{len(piano)} coppie da fondere"
          + (f" ({len(gia_fatte)} già fatte in una esecuzione precedente)" if gia_fatte else ""))
    print(f"{'VECCHIA':20s} -> {'UFFICIALE':18s} {'(inglese)':17s} effetto")
    print("-" * 96)
    senza_pokemon = []
    for vecchia, ufficiale, nome_en, posseduta in piano:
        tipo = (ab[vecchia].get("effect") or {}).get("type")
        print(f"{vecchia:20s} -> {ufficiale:18s} {nome_en:17s} {tipo}"
              + ("" if posseduta else "   ⚠️ nessun Pokémon la possiede"))
        if not posseduta:
            senza_pokemon.append(nome_en)

    if args.dry_run:
        print(f"\n--dry-run: nessuna modifica. Voci ora: {len(ab)}, dopo: {len(ab) - len(piano)}.")
        return 0

    os.makedirs(os.path.dirname(ARCHIVIO), exist_ok=True)
    with open(ARCHIVIO, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)
    print(f"\nCopia di sicurezza: {os.path.relpath(ARCHIVIO, RADICE)}")

    prima = len(ab)
    for vecchia, ufficiale, _, _ in piano:
        v, u = ab[vecchia], ab[ufficiale]
        u["effect"] = v["effect"]
        u["category"] = v.get("category", u.get("category"))
        u["desc"] = v.get("desc", u.get("desc"))
        for campo in CAMPI_EXTRA:
            if campo in v:
                u[campo] = v[campo]
        del ab[vecchia]

    with open(FILE_ABILITA, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)

    attive = sum(1 for v in ab.values() if attivo(v))
    raggiungibili = sum(1 for k, v in ab.items() if attivo(v) and v.get("nome_en") in posseduti)
    print(f"Scritto {os.path.relpath(FILE_ABILITA, RADICE)}: {prima} → {len(ab)} voci.")
    print(f"Effetti attivi: {attive}, di cui raggiungibili da un Pokémon: {raggiungibili}"
          f" (prima erano 0).")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
