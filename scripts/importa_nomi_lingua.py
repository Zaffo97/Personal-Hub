#!/usr/bin/env python
"""Riempie `nome_it` e `nome_en` sulle quattro basi del catalogo, da PokéAPI.

    python scripts/importa_nomi_lingua.py [--dry-run] [--solo moves,abilities,...]

Le **chiavi del catalogo non vengono toccate**: sono referenziate dai filtri delle
regulation, dal motore degli effetti e dai team salvati nel DB. Ogni voce riceve solo
i due nomi da mostrare a schermo.

Come aggancia ogni base:

- **mosse** e **oggetti** — la chiave è già il nome inglese: si passa allo slug e si
  chiede la voce a PokéAPI. Qualche slug non combacia (`Vise Grip` lì è `vice-grip`,
  le `… Feather` sono `…-wing`), e per quelli c'è `SLUG_A_MANO`
- **abilità** — la chiave è il nome **italiano**: si scarica l'elenco completo delle
  373 abilità e si costruisce l'indice inverso italiano → inglese
- **Pokémon** — i nomi italiani coincidono quasi sempre con gli inglesi (l'Italia usa
  i nomi inglesi); fanno eccezione i Paradosso e pochi altri. Si traduce **solo** la
  voce il cui nome è esattamente il nome inglese della specie: per tutto il resto —
  forme, Mega, regionali — `nome_it` resta uguale a `nome_en`, perché il nome italiano
  di una forma non è deducibile e non va inventato

Chi non si aggancia non viene lasciato a metà: prende `nome_it == nome_en == chiave`,
così il commutatore di lingua ha sempre qualcosa da mostrare, e finisce nel rapporto
finale. Le tue forme e abilità inventate stanno tutte lì, ed è corretto così.

Le risposte finiscono in `data/cache/pokeapi/` (ignorata da git): la seconda esecuzione
non ripassa dalla rete. PokéAPI risponde **403** senza `User-Agent`.
"""
import argparse
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

# La console di Windows e' cp1252 e non sa scrivere "Nidoran♀": senza questo il
# rapporto finale muore su UnicodeEncodeError dopo che il lavoro e' gia' stato fatto.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import voci_catalogo, salva_catalogo  # noqa: E402

API = "https://pokeapi.co/api/v2"
UA = {"User-Agent": "personal-hub/1.0 (import nomi IT/EN)"}
CACHE = os.path.join(RADICE, "data", "cache", "pokeapi")

# Slug che non si ricavano dal nome. Verificati uno per uno contro PokéAPI.
SLUG_A_MANO = {
    "moves": {"Vise Grip": "vice-grip"},
    "items": {
        "Health Feather": "health-wing", "Muscle Feather": "muscle-wing",
        "Resist Feather": "resist-wing", "Genius Feather": "genius-wing",
        "Clever Feather": "clever-wing", "Swift Feather": "swift-wing",
        "Pretty Feather": "pretty-wing",
        "Leek": "large-leek",
    },
}

# PokéAPI tiene i cristalli Z sdoppiati in "…-z--held" e "…-z--bag": lo slug nudo
# ("normalium-z") non esiste. Se il primo tentativo va a vuoto si prova questa coda.
CODE_ALTERNATIVE = ("--held",)


def slug(s):
    """"King's Rock" -> "kings-rock" ; "Mr. Mime" -> "mr-mime"."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "")).strip("-")


def chiave_confronto(s):
    """Per confrontare nomi tra fonti diverse: senza accenti, spazi né punteggiatura."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def scarica(percorso_api, cartella_cache):
    """Una risorsa PokéAPI, dalla cache se c'è. None se non esiste (404)."""
    dove = os.path.join(CACHE, cartella_cache)
    os.makedirs(dove, exist_ok=True)
    file_cache = os.path.join(dove, slug(percorso_api.rsplit("/", 1)[-1]) + ".json")
    if os.path.exists(file_cache):
        try:
            with io.open(file_cache, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    for tentativo in range(3):
        try:
            req = urllib.request.Request(f"{API}/{percorso_api}", headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                dati = json.load(r)
            with io.open(file_cache, "w", encoding="utf-8") as f:
                json.dump(dati, f, ensure_ascii=False)
            return dati
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + tentativo)
        except Exception:
            time.sleep(1 + tentativo)
    return None


def nomi_localizzati(dati):
    """(italiano, inglese) dal blocco `names`, con None se la lingua manca."""
    if not dati:
        return None, None
    m = {n["language"]["name"]: n["name"] for n in dati.get("names", [])}
    return m.get("it"), m.get("en")


def imposta(voce, it, en):
    voce["nome_it"] = it
    voce["nome_en"] = en


# ── una funzione per base ────────────────────────────────────────────────────

def per_nome_inglese(voci, tipo, cartella, a_mano, avanzamento):
    """Mosse e oggetti: la chiave È il nome inglese."""
    agganciate, fuori = 0, []
    for i, (chiave, voce) in enumerate(voci.items(), 1):
        s = a_mano.get(chiave) or slug(chiave)
        it, en = nomi_localizzati(scarica(f"{tipo}/{s}", cartella))
        for coda in CODE_ALTERNATIVE:
            if it and en:
                break
            it, en = nomi_localizzati(scarica(f"{tipo}/{s}{coda}", cartella))
        if it and en:
            imposta(voce, it, en)
            agganciate += 1
        else:
            imposta(voce, chiave, chiave)
            fuori.append(chiave)
        avanzamento(i, len(voci))
    return agganciate, fuori


def abilita_per_nome_italiano(voci, avanzamento):
    """Le chiavi sono in italiano: serve l'indice inverso di tutte le abilità."""
    elenco = scarica("ability?limit=1000", "liste") or {"results": []}
    indice = {}
    totale = len(elenco["results"])
    for i, riga in enumerate(elenco["results"], 1):
        it, en = nomi_localizzati(scarica(f"ability/{riga['name']}", "ability"))
        if it and en:
            indice[chiave_confronto(it)] = (it, en)
        avanzamento(i, totale)
    agganciate, fuori = 0, []
    for chiave, voce in voci.items():
        trovata = indice.get(chiave_confronto(chiave))
        if trovata:
            imposta(voce, trovata[0], trovata[1])
            agganciate += 1
        else:
            imposta(voce, chiave, chiave)
            fuori.append(chiave)
    return agganciate, fuori


def pokemon_per_specie(voci, avanzamento):
    """Traduce solo la voce che è esattamente la specie: le forme non si inventano."""
    tradotte, identiche, fuori = 0, 0, []
    for i, (chiave, voce) in enumerate(voci.items(), 1):
        nome = voce.get("name") or chiave
        # La specie si ricava dallo slug del catalogo togliendo i pezzi di forma da
        # destra: "venusaur-mega" -> "venusaur". Non basta prendere il primo pezzo:
        # le specie di due parole ("flutter-mane", "tapu-koko") ci morivano dentro.
        pezzi = (voce.get("slug") or chiave).split("-")
        it = en = None
        while pezzi and not en:
            it, en = nomi_localizzati(scarica("pokemon-species/" + "-".join(pezzi), "species"))
            pezzi = pezzi[:-1]
        if en and chiave_confronto(nome) == chiave_confronto(en):
            imposta(voce, it or nome, en)
            if (it or nome) != en:
                tradotte += 1
            else:
                identiche += 1
        else:
            # forma, Mega, regionale: nome non deducibile, resta uguale nelle due lingue
            imposta(voce, nome, nome)
            fuori.append(nome)
        for nome_forma, forma in (voce.get("forms") or {}).items():
            imposta(forma, nome_forma, nome_forma)
        avanzamento(i, len(voci))
    return tradotte, identiche, fuori


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--solo", default="moves,items,abilities,pokemon",
                    help="basi da trattare, separate da virgola")
    args = ap.parse_args()
    basi = [b.strip() for b in args.solo.split(",") if b.strip()]

    def avanzamento(fatto, totale):
        if fatto % 50 == 0 or fatto == totale:
            print(f"    {fatto}/{totale}", flush=True)

    rapporto = {}
    for base in basi:
        voci = voci_catalogo(base)
        if not voci:
            print(f"[{base}] catalogo vuoto, salto")
            continue
        print(f"[{base}] {len(voci)} voci", flush=True)

        if base in ("moves", "items"):
            tipo = "move" if base == "moves" else "item"
            ok, fuori = per_nome_inglese(voci, tipo, tipo, SLUG_A_MANO.get(base, {}), avanzamento)
            rapporto[base] = (ok, fuori)
        elif base == "abilities":
            ok, fuori = abilita_per_nome_italiano(voci, avanzamento)
            rapporto[base] = (ok, fuori)
        elif base == "pokemon":
            tradotte, identiche, fuori = pokemon_per_specie(voci, avanzamento)
            rapporto[base] = (tradotte + identiche, fuori)
            print(f"    specie con nome italiano diverso: {tradotte} | identiche: {identiche}")
        else:
            print(f"  base sconosciuta: {base}")
            continue

        if not args.dry_run:
            salva_catalogo(base, voci)
            print(f"    scritto data/catalog/{base}.json")

    print("\n=== RAPPORTO ===")
    for base, (ok, fuori) in rapporto.items():
        print(f"{base:<10} agganciate {ok:>5} | senza traduzione ufficiale {len(fuori):>4}")
        for n in fuori[:12]:
            print(f"             - {n}")
        if len(fuori) > 12:
            print(f"             … e altre {len(fuori) - 12}")
    if args.dry_run:
        print("\n--dry-run: niente scritto su disco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
