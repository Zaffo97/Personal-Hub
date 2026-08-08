#!/usr/bin/env python
"""Costruisce data/catalog/ — il database di default con TUTTE le voci.

    python scripts/build_catalog.py            # costruisce
    python scripts/build_catalog.py --dry-run  # mostra cosa farebbe, senza scrivere

REGOLA D'ORO: i dati curati esistenti vincono sempre.
L'import aggiunge solo ciò che manca e non sovrascrive mai una voce già presente.
Questo perché PokéAPI non ha i campi che il calcolatore usa davvero — `modifier` e
`effect` sugli oggetti, il blocco `effect` sulle abilità — e perché parte del
catalogo è deliberatamente personalizzata (vedi le Mega qui sotto).

Convenzioni rispettate, le stesse dei file attuali:
  - chiavi Pokémon, mosse e oggetti in inglese; abilità con nome italiano ufficiale
    quando esiste, altrimenti inglese (è la convenzione di data/abilities.json)
  - tipi in italiano, descrizioni in italiano
  - Pokémon: base stat ufficiali. Le forme **Mega** ricevono il potenziamento del
    formato Champions: HP +75, tutte le altre stat +20. Verificato sul catalogo
    esistente: 53 Mega su 55 seguono questa regola, mentre le 166 specie base e le
    20 forme non-Mega sono identiche ai dati ufficiali.

Le regulation NON contengono più dati: contengono elenchi di nomi che puntano qui.
"""
import argparse
import csv
import io
import json
import os
import sys
import tempfile

import requests

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RADICE, "data")
CATALOGO = os.path.join(DATA, "catalog")
CACHE = os.environ.get("POKEAPI_CACHE") or os.path.join(tempfile.gettempdir(), "pokeapi_csv")
BASE_CSV = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
UA = {"User-Agent": "personal-hub/1.0 (build catalogo offline, uso personale)"}

IT, EN = "8", "9"
STAT_ID = {"1": "hp", "2": "atk", "3": "def", "4": "spa", "5": "spd", "6": "spe"}
ORDINE_STAT = ["hp", "atk", "def", "spa", "spd", "spe"]

# Potenziamento Mega del formato Champions, ricavato dal catalogo esistente.
MEGA_BONUS = {"hp": 75, "atk": 20, "def": 20, "spa": 20, "spd": 20, "spe": 20}

# PokéAPI chiama 'ballistics' quello che i file dell'app chiamano 'bullet'.
FLAG_RINOMINATI = {"ballistics": "bullet"}

# Oggetti che ha senso vedere in un calcolatore: quelli che si tengono in battaglia.
# Fuori restano MT, caramelle, ingredienti da picnic, oggetti di trama e simili.
CATEGORIE_OGGETTI = {
    "held-items", "choice", "bad-held-items", "plates", "species-specific",
    "type-enhancement", "jewels", "memories", "z-crystals", "effort-training",
    "training", "in-a-pinch", "picky-healing", "type-protection", "scarves",
    "mega-stones", "healing", "status-cures", "revival", "vitamins",
}

FILE_CSV = [
    "languages.csv", "pokemon.csv", "pokemon_species.csv", "pokemon_species_names.csv",
    "pokemon_stats.csv", "pokemon_types.csv", "pokemon_abilities.csv",
    "pokemon_forms.csv", "pokemon_form_names.csv",
    "types.csv", "type_names.csv",
    "abilities.csv", "ability_names.csv", "ability_flavor_text.csv",
    "moves.csv", "move_names.csv", "move_flavor_text.csv",
    "move_flags.csv", "move_flag_map.csv", "move_damage_classes.csv",
    "items.csv", "item_names.csv", "item_flavor_text.csv", "item_categories.csv",
]


# ── lettura CSV ──────────────────────────────────────────────────────────────
def scarica_cache():
    os.makedirs(CACHE, exist_ok=True)
    mancanti = [f for f in FILE_CSV
                if not os.path.exists(os.path.join(CACHE, f))
                or os.path.getsize(os.path.join(CACHE, f)) == 0]
    if not mancanti:
        print(f"cache CSV già presente in {CACHE}")
        return
    print(f"scarico {len(mancanti)} file CSV in {CACHE}")
    for f in mancanti:
        r = requests.get(BASE_CSV + f, headers=UA, timeout=90)
        r.raise_for_status()
        io.open(os.path.join(CACHE, f), "wb").write(r.content)


def leggi(nome):
    with io.open(os.path.join(CACHE, nome), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pulisci(testo):
    """Il flavor text dei dump ha a capo e trattini morbidi in mezzo alle parole."""
    return " ".join(testo.replace("­\n", "").replace("­", "")
                    .replace("\n", " ").replace("\f", " ").split())


def testo_recente(righe, chiave_id, lingua=IT):
    """Ultimo flavor text disponibile nella lingua, per id."""
    fuori = {}
    for r in righe:
        if r.get("language_id") != lingua and r.get("local_language_id") != lingua:
            continue
        k = r[chiave_id]
        v = int(r.get("version_group_id") or 0)
        if k not in fuori or v >= fuori[k][0]:
            fuori[k] = (v, pulisci(r["flavor_text"]))
    return {k: v[1] for k, v in fuori.items()}


def carica_json(percorso, default):
    try:
        with io.open(percorso, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def scrivi_json(percorso, dati, dry):
    if dry:
        return
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with io.open(percorso, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)


# ── Pokémon ──────────────────────────────────────────────────────────────────
PREFISSI_FORMA = ("Mega ", "Alolan ", "Galarian ", "Hisuian ", "Paldean ", "Primal ")


def nome_forma(nome_specie, pokemon_name, form_name):
    """Nome visualizzato di una forma, nello stile del catalogo esistente.

    "Mega Venusaur" e "Alolan Raichu" arrivano già pronti da PokéAPI; le altre
    seguono lo schema "Specie (Forma)" usato dal catalogo, per esempio
    "Aegislash (Shield Forme)".
    """
    if pokemon_name and (pokemon_name.startswith(PREFISSI_FORMA)
                         or pokemon_name == form_name):
        return pokemon_name
    if form_name:
        return f"{nome_specie} ({form_name})"
    return pokemon_name or nome_specie


def costruisci_pokemon(esistente):
    pokemon = leggi("pokemon.csv")
    specie_nomi = {r["pokemon_species_id"]: r["name"]
                   for r in leggi("pokemon_species_names.csv") if r["local_language_id"] == EN}
    tipi_it = {r["type_id"]: r["name"] for r in leggi("type_names.csv") if r["local_language_id"] == IT}
    tipi_pk = {}
    for r in leggi("pokemon_types.csv"):
        tipi_pk.setdefault(r["pokemon_id"], []).append((int(r["slot"]), tipi_it.get(r["type_id"], "?")))
    ab_nomi_en = {r["ability_id"]: r["name"] for r in leggi("ability_names.csv") if r["local_language_id"] == EN}
    ab_pk = {}
    for r in leggi("pokemon_abilities.csv"):
        ab_pk.setdefault(r["pokemon_id"], []).append((int(r["slot"]), ab_nomi_en.get(r["ability_id"], "?")))
    stat_pk = {}
    for r in leggi("pokemon_stats.csv"):
        if r["stat_id"] in STAT_ID:
            stat_pk.setdefault(r["pokemon_id"], {})[STAT_ID[r["stat_id"]]] = int(r["base_stat"])

    forme = {r["pokemon_id"]: r for r in leggi("pokemon_forms.csv")}
    forme_nomi = {}
    for r in leggi("pokemon_form_names.csv"):
        if r["local_language_id"] == EN:
            forme_nomi[r["pokemon_form_id"]] = (r.get("pokemon_name", ""), r.get("form_name", ""))

    catalogo = json.loads(json.dumps(esistente))  # copia profonda: l'originale resta intatto
    chiavi_esistenti = set(catalogo)
    nomi_esistenti = {v.get("name", k).lower() for k, v in catalogo.items()}
    forme_esistenti = {n.lower() for v in catalogo.values() for n in (v.get("forms") or {})}

    nuove_specie = nuove_forme = mega_potenziate = 0
    for r in pokemon:
        pid, slug, sid = r["id"], r["identifier"], r["species_id"]
        stat = stat_pk.get(pid)
        if not stat or len(stat) != 6:
            continue
        tipi = [t for _, t in sorted(tipi_pk.get(pid, []))]
        abilita = [a for _, a in sorted(ab_pk.get(pid, []))]
        nome_sp = specie_nomi.get(sid, slug.title())

        if r["is_default"] == "1":
            chiave = slug
            if chiave in chiavi_esistenti or nome_sp.lower() in nomi_esistenti:
                continue
            catalogo[chiave] = {
                "name": nome_sp, "types": tipi, "abilities": abilita,
                "base_stats": {k: stat[k] for k in ORDINE_STAT}, "slug": slug,
            }
            chiavi_esistenti.add(chiave)
            nomi_esistenti.add(nome_sp.lower())
            nuove_specie += 1
            continue

        # forma alternativa
        f = forme.get(pid)
        pkn, fn = forme_nomi.get(f["id"], ("", "")) if f else ("", "")
        nome = nome_forma(nome_sp, pkn, fn)
        if nome.lower() in forme_esistenti:
            continue
        base = {k: stat[k] for k in ORDINE_STAT}
        e_mega = bool(f and f.get("is_mega") == "1") or nome.startswith("Mega ")
        if e_mega:
            base = {k: v + MEGA_BONUS[k] for k, v in base.items()}
            mega_potenziate += 1
        voce = {"types": tipi, "base_stats": base, "abilities": abilita, "slug": slug}

        # appende alla specie, creandola se serve
        chiave_specie = next((k for k, v in catalogo.items()
                              if v.get("name", "").lower() == nome_sp.lower()), None)
        if chiave_specie is None:
            continue  # la specie base non c'e': la forma senza base non serve a nulla
        catalogo[chiave_specie].setdefault("forms", {})[nome] = voce
        forme_esistenti.add(nome.lower())
        nuove_forme += 1

    # Slug ufficiale anche sulle voci che c'erano già: è un campo in più, non tocca
    # nulla di esistente, e rende la risoluzione dei nomi deterministica invece di
    # dipendere dalla mappa ALIAS scritta a mano (es. "Arcanine-Hisui").
    slug_per_nome = {}
    for r in pokemon:
        pid, slug, sid = r["id"], r["identifier"], r["species_id"]
        nome_sp = specie_nomi.get(sid, "")
        if r["is_default"] == "1":
            if nome_sp:
                slug_per_nome[nome_sp.lower()] = slug
        else:
            f = forme.get(pid)
            pkn, fn = forme_nomi.get(f["id"], ("", "")) if f else ("", "")
            slug_per_nome[nome_forma(nome_sp, pkn, fn).lower()] = slug
        slug_per_nome.setdefault(slug.lower(), slug)

    slug_aggiunti = 0
    for chiave, voce in catalogo.items():
        if "slug" not in voce:
            s = slug_per_nome.get(voce.get("name", "").lower()) or slug_per_nome.get(chiave.lower())
            if s:
                voce["slug"] = s
                slug_aggiunti += 1
        for nome_f, dati_f in (voce.get("forms") or {}).items():
            if "slug" not in dati_f:
                s = slug_per_nome.get(nome_f.lower())
                if s:
                    dati_f["slug"] = s
                    slug_aggiunti += 1

    return catalogo, dict(nuove_specie=nuove_specie, nuove_forme=nuove_forme,
                          mega_potenziate=mega_potenziate, slug_aggiunti=slug_aggiunti)


# ── mosse ────────────────────────────────────────────────────────────────────
def costruisci_mosse(esistenti):
    mosse = leggi("moves.csv")
    nomi_en = {r["move_id"]: r["name"] for r in leggi("move_names.csv") if r["local_language_id"] == EN}
    tipi_it = {r["type_id"]: r["name"] for r in leggi("type_names.csv") if r["local_language_id"] == IT}
    tipi_slug = {r["id"]: r["identifier"] for r in leggi("types.csv")}
    classi = {r["id"]: r["identifier"] for r in leggi("move_damage_classes.csv")}
    flag_nomi = {r["id"]: r["identifier"] for r in leggi("move_flags.csv")}
    flag_mossa = {}
    for r in leggi("move_flag_map.csv"):
        nome = flag_nomi.get(r["move_flag_id"], "")
        flag_mossa.setdefault(r["move_id"], []).append(FLAG_RINOMINATI.get(nome, nome))
    desc = testo_recente(leggi("move_flavor_text.csv"), "move_id")

    fuori = json.loads(json.dumps(esistenti))
    aggiunte = 0
    for r in mosse:
        nome = nomi_en.get(r["id"])
        if not nome or nome in fuori:
            continue
        voce = {
            "bp": int(r["power"]) if r["power"] else 0,
            "category": classi.get(r["damage_class_id"], "status"),
            "type": tipi_slug.get(r["type_id"], "normal"),
            "desc": desc.get(r["id"], ""),
        }
        if flag_mossa.get(r["id"]):
            voce["flags"] = sorted(flag_mossa[r["id"]])
        if r["accuracy"]:
            voce["accuracy"] = int(r["accuracy"])
        voce["type_it"] = tipi_it.get(r["type_id"], "")
        fuori[nome] = voce
        aggiunte += 1

    # Unica eccezione alla regola d'oro, e solo in aggiunta: il flag `contact`.
    # Non è una scelta di bilanciamento ma una proprietà oggettiva della mossa, e
    # il calcolatore lo legge per Tough Claws (×1.3) e Fluffy (×0.5). Nel file
    # curato mancava su 30 mosse — Liquidation, Play Rough, Leaf Blade... — che
    # quindi ignoravano entrambe le abilità. Nessun flag viene mai rimosso.
    contatto_ufficiale = {nomi_en[r["move_id"]] for r in leggi("move_flag_map.csv")
                          if flag_nomi.get(r["move_flag_id"]) == "contact" and r["move_id"] in nomi_en}
    integrate = []
    for nome in contatto_ufficiale & set(fuori):
        flags = fuori[nome].get("flags") or []
        if "contact" not in flags:
            fuori[nome]["flags"] = sorted(flags + ["contact"])
            integrate.append(nome)
    return fuori, dict(aggiunte=aggiunte, contact_integrati=sorted(integrate))


# ── abilità ──────────────────────────────────────────────────────────────────
def costruisci_abilita(esistenti):
    ab = leggi("abilities.csv")
    nomi = leggi("ability_names.csv")
    it = {r["ability_id"]: r["name"] for r in nomi if r["local_language_id"] == IT}
    en = {r["ability_id"]: r["name"] for r in nomi if r["local_language_id"] == EN}
    desc = testo_recente(leggi("ability_flavor_text.csv"), "ability_id")

    fuori = json.loads(json.dumps(esistenti))
    presenti = {k.lower() for k in fuori}
    aggiunte = senza_nome_it = 0
    for r in ab:
        nome = it.get(r["id"]) or en.get(r["id"])
        if not nome:
            continue
        if not it.get(r["id"]):
            senza_nome_it += 1
        if nome.lower() in presenti:
            continue
        fuori[nome] = {
            "desc": desc.get(r["id"], ""),
            "category": "other",
            # nessun effetto: il blocco `effect` va curato a mano, come le 56 esistenti
            "effect": {"type": "none"},
            "nome_en": en.get(r["id"], ""),
        }
        presenti.add(nome.lower())
        aggiunte += 1
    return fuori, dict(aggiunte=aggiunte, senza_nome_it=senza_nome_it)


# ── oggetti ──────────────────────────────────────────────────────────────────
def costruisci_oggetti(esistenti):
    items = leggi("items.csv")
    categorie = {r["id"]: r["identifier"] for r in leggi("item_categories.csv")}
    nomi_en = {r["item_id"]: r["name"] for r in leggi("item_names.csv") if r["local_language_id"] == EN}
    desc = testo_recente(leggi("item_flavor_text.csv"), "item_id")

    fuori = json.loads(json.dumps(esistenti))
    aggiunti = scartati = 0
    for r in items:
        cat = categorie.get(r["category_id"], "")
        if cat not in CATEGORIE_OGGETTI:
            scartati += 1
            continue
        nome = nomi_en.get(r["id"])
        if not nome or nome in fuori:
            continue
        fuori[nome] = {
            "category": "other",
            # niente `modifier`: il moltiplicatore va deciso a mano, come per i 58 curati
            "desc": desc.get(r["id"], ""),
            "categoria_pokeapi": cat,
        }
        aggiunti += 1
    return fuori, dict(aggiunti=aggiunti, scartati=scartati)


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="non scrive niente")
    args = ap.parse_args()

    scarica_cache()
    print()

    pk_esistente = carica_json(os.path.join(DATA, "pokemon_catalog.json"), {})
    mv_esistenti = carica_json(os.path.join(DATA, "moves_ma.json"), {}).get("moves", {})
    it_esistenti = carica_json(os.path.join(DATA, "items_ma.json"), {}).get("items", {})
    ab_esistenti = carica_json(os.path.join(DATA, "abilities.json"), {}).get("abilities", {})

    pk, s1 = costruisci_pokemon(pk_esistente)
    mv, s2 = costruisci_mosse(mv_esistenti)
    ab, s3 = costruisci_abilita(ab_esistenti)
    og, s4 = costruisci_oggetti(it_esistenti)

    forme_tot = sum(len(v.get("forms") or {}) for v in pk.values())
    print(f"POKÉMON  {len(pk_esistente):5d} -> {len(pk):5d} specie   (+{s1['nuove_specie']})")
    print(f"         forme: {forme_tot} totali   (+{s1['nuove_forme']}, di cui {s1['mega_potenziate']} Mega con bonus Champions)")
    print(f"MOSSE    {len(mv_esistenti):5d} -> {len(mv):5d}   (+{s2['aggiunte']})")
    ci = s2["contact_integrati"]
    if ci:
        print(f"         flag `contact` integrato su {len(ci)} mosse curate che ne erano prive:")
        print(f"           {', '.join(ci[:10])}{'...' if len(ci) > 10 else ''}")
    print(f"ABILITÀ  {len(ab_esistenti):5d} -> {len(ab):5d}   (+{s3['aggiunte']}, {s3['senza_nome_it']} senza nome IT ufficiale)")
    print(f"OGGETTI  {len(it_esistenti):5d} -> {len(og):5d}   (+{s4['aggiunti']}, {s4['scartati']} scartati perché non da battaglia)")

    # Nessuna voce curata deve essere cambiata. Aggiungere una forma nuova a una
    # specie esistente è lecito; alterare un campo o una forma già presenti no.
    def intatte(etichetta, orig, nuovo):
        fuori = []
        for k, v in orig.items():
            n = nuovo.get(k)
            if n is None:
                fuori.append(f"{etichetta}/{k} sparita")
                continue
            for campo, valore in v.items():
                if campo == "forms":
                    for nf, vf in valore.items():
                        nuova = (n.get("forms") or {}).get(nf)
                        if nuova is None:
                            fuori.append(f"{etichetta}/{k}.forms[{nf}] sparita")
                        # campi in più (es. `slug`) sono ammessi; quelli esistenti no
                        elif any(nuova.get(c) != v2 for c, v2 in vf.items()):
                            fuori.append(f"{etichetta}/{k}.forms[{nf}]")
                elif n.get(campo) != valore:
                    # unica differenza ammessa: il flag contact aggiunto sopra
                    if (etichetta == "mosse" and campo == "flags"
                            and set(n.get(campo) or []) - set(valore or []) == {"contact"}):
                        continue
                    fuori.append(f"{etichetta}/{k}.{campo}")
        return fuori

    problemi = (intatte("pokemon", pk_esistente, pk) + intatte("mosse", mv_esistenti, mv)
                + intatte("abilità", ab_esistenti, ab) + intatte("oggetti", it_esistenti, og))
    print(f"\nvoci curate modificate: {len(problemi)}" + (f"  {problemi[:5]}" if problemi else "  (nessuna, come deve essere)"))
    if problemi:
        print("INTERROTTO: l'import non deve toccare i dati curati")
        return 1

    scrivi_json(os.path.join(CATALOGO, "pokemon.json"), pk, args.dry_run)
    scrivi_json(os.path.join(CATALOGO, "moves.json"), mv, args.dry_run)
    # le abilità restano avvolte in {"abilities": ...}: è la forma che l'editor,
    # l'archivio e il ripristino già si aspettano
    scrivi_json(os.path.join(CATALOGO, "abilities.json"), {"abilities": ab}, args.dry_run)
    scrivi_json(os.path.join(CATALOGO, "items.json"), og, args.dry_run)
    print("\n" + ("dry-run: niente scritto" if args.dry_run else f"scritto in {CATALOGO}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
