#!/usr/bin/env python
"""Completa `nome_it`/`nome_en` con la wiki di Pokémon Central, dove PokéAPI non arriva.

    python scripts/importa_nomi_wiki.py [--dry-run] [--solo moves,items,abilities]

Il secondo giro dopo `importa_nomi_lingua.py`. Quello prende i nomi da PokéAPI, che
per l'italiano è **incompleto**: niente mosse Z, niente strumenti di nona generazione,
e un buon terzo delle abilità senza nome italiano. La wiki di Pokémon Central quelle
righe ce le ha, ed è la stessa fonte già usata da `importa_roster_champions.py`.

**Tocca solo le voci senza traduzione**, cioè quelle in cui `nome_it == nome_en`.
Una traduzione già presa da PokéAPI non viene mai sovrascritta: dove le due fonti non
concordano lo script lo **segnala** e basta, perché nessuna delle due è sempre giusta
(PokéAPI abbrevia — `Revitalizz. Max`, `Autodistruz.` sta invece sulla wiki — e la
wiki ha i suoi refusi: `Vasterngia`, `Morostretto`). La scelta è di Davide.

Due fonti, in quest'ordine:

1. le pagine **«… in altre lingue»** (mosse, strumenti, abilità), che sono tabelle con
   una riga *Italiano* e una *Inglese*: da lì esce l'indice completo delle due lingue
2. per ciò che quelle liste non coprono — gli strumenti di nona generazione non ci
   sono — la **pagina singola** dello strumento, trovata con la ricerca della wiki.
   Una pagina viene accettata **solo** se la sua riga *Inglese* combacia con la chiave
   del catalogo: così un risultato di ricerca sbagliato viene scartato invece di
   entrare nei dati

Le chiavi del catalogo non vengono toccate — sono referenziate dai filtri delle
regulation, dal motore degli effetti e dai team salvati nel DB.

Le pagine scaricate finiscono in `data/cache/wiki/` (ignorata da git): la seconda
esecuzione non ripassa dalla rete.
"""
import argparse
import io
import json
import os
import re
import sys
import unicodedata
import urllib.parse

import requests

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

# La console di Windows e' cp1252: senza questo il rapporto finale muore su
# UnicodeEncodeError dopo che il lavoro e' gia' stato fatto.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import voci_catalogo, salva_catalogo  # noqa: E402

WIKI = "https://wiki.pokemoncentral.it/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; personal-hub/1.0)"}
CACHE = os.path.join(RADICE, "data", "cache", "wiki")

ELENCHI = {
    "moves": "Elenco delle mosse in altre lingue",
    "items": "Elenco degli strumenti in altre lingue",
    "abilities": "Elenco delle abilità in altre lingue",
}

# Le chiavi di mosse e strumenti sono i nomi inglesi; quelle delle abilità sono
# italiane. Cambia solo l'ordine in cui si interroga l'indice.
PRIMA_INGLESE = {"moves", "items"}


def chiave_confronto(s):
    """Per confrontare nomi tra fonti diverse: senza accenti, spazi né punteggiatura."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def pulisci(frammento):
    """Il nome dentro una cella: prima di <sup> (marcatori di generazione), <i> e <div>.

    La wiki mette nella stessa cella il nome attuale e quelli delle generazioni
    passate (`Metal Liviano<sup>VI+</sup><div>Met. Liviano<sup>V</sup></div>`):
    quello buono è il primo.
    """
    frammento = re.split(r"<sup|<i>|<div", frammento)[0]
    frammento = re.sub(r"<[^>]+>", "", frammento)
    return re.sub(r"\s+", " ", frammento).replace("&amp;", "&").strip()


def scarica(titolo, prefisso=""):
    """L'HTML di una pagina della wiki, dalla cache se c'è. Stringa vuota se non esiste."""
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, prefisso + urllib.parse.quote(titolo, safe="")[:150] + ".html")
    if os.path.exists(f):
        with io.open(f, encoding="utf-8") as fh:
            return fh.read()
    r = requests.get(WIKI + urllib.parse.quote(titolo.replace(" ", "_")), headers=UA, timeout=120)
    if r.status_code != 200:
        return ""
    with io.open(f, "w", encoding="utf-8") as fh:
        fh.write(r.text)
    return r.text


def cerca(query):
    """I titoli che la ricerca della wiki restituisce per una frase esatta."""
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, "ricerca_" + urllib.parse.quote(query, safe="") + ".json")
    if os.path.exists(f):
        with io.open(f, encoding="utf-8") as fh:
            return json.load(fh)
    r = requests.get(WIKI + "api.php", timeout=60, headers=UA,
                     params={"action": "query", "list": "search", "srsearch": '"%s"' % query,
                             "srlimit": "6", "srnamespace": "0", "format": "json"})
    titoli = [s["title"] for s in r.json().get("query", {}).get("search", [])]
    with io.open(f, "w", encoding="utf-8") as fh:
        json.dump(titoli, fh, ensure_ascii=False)
    return titoli


# ── fonte 1: le pagine «… in altre lingue» ───────────────────────────────────

CELLA_LINGUA = re.compile(r"<b>(Italiano|Inglese)</b>:</div>(.*?)</td>", re.S)


def indice_elenco(titolo):
    """(per_italiano, per_inglese) dalla tabella di una pagina «… in altre lingue»."""
    html = scarica(titolo)
    per_it, per_en = {}, {}
    for riga in re.split(r"<tr[ >]", html):
        celle = dict((lingua, pulisci(testo)) for lingua, testo in CELLA_LINGUA.findall(riga))
        it, en = celle.get("Italiano"), celle.get("Inglese")
        if it and en:
            per_it.setdefault(chiave_confronto(it), (it, en))
            per_en.setdefault(chiave_confronto(en), (it, en))
    return per_it, per_en


# ── fonte 2: la pagina singola ───────────────────────────────────────────────

def nome_pagina(html):
    """(italiano, inglese) di un articolo: il titolo e la riga Inglese di «In altre lingue»."""
    i = html.find('id="In_altre_lingue"')
    if i < 0:
        return None, None
    m = re.search(r"<b>Inglese</b>\s*</td>\s*<td[^>]*>(.*?)</td>", html[i:i + 20000], re.S)
    t = re.search(r'<span class="mw-page-title-main">(.*?)</span>', html, re.S)
    if not m or not t:
        return None, None
    return pulisci(t.group(1)), pulisci(m.group(1))


def cerca_articolo(nome_en):
    """Cerca l'articolo di una voce e lo accetta solo se dichiara quel nome inglese."""
    for titolo in cerca(nome_en):
        it, en = nome_pagina(scarica(titolo, "pag_"))
        if en and chiave_confronto(en) == chiave_confronto(nome_en):
            return it, en
    return None


# ── il lavoro ────────────────────────────────────────────────────────────────

def tratta(base, voci, avanzamento):
    per_it, per_en = indice_elenco(ELENCHI[base])
    print(f"    elenco wiki: {len(per_it)} voci con nome italiano e inglese", flush=True)
    indici = (per_en, per_it) if base in PRIMA_INGLESE else (per_it, per_en)

    riempite, da_articolo, fuori, disaccordi = [], [], [], []
    da_fare = [k for k, v in voci.items() if v.get("nome_it") == v.get("nome_en")]

    # controllo: sulle voci gia' tradotte da PokeAPI, la wiki dice lo stesso?
    for chiave, voce in voci.items():
        if voce.get("nome_it") == voce.get("nome_en"):
            continue
        w = (per_en.get(chiave_confronto(voce.get("nome_en", "")))
             or per_it.get(chiave_confronto(voce.get("nome_it", ""))))
        if w and chiave_confronto(w[0]) != chiave_confronto(voce["nome_it"]):
            disaccordi.append((chiave, voce["nome_it"], w[0]))

    for i, chiave in enumerate(da_fare, 1):
        trovata = indici[0].get(chiave_confronto(chiave)) or indici[1].get(chiave_confronto(chiave))
        if trovata:
            riempite.append((chiave, trovata))
        elif base in PRIMA_INGLESE:
            # gli elenchi non arrivano alla nona generazione: si prova l'articolo
            trovata = cerca_articolo(chiave)
            (da_articolo if trovata else fuori).append(chiave)
            if trovata:
                riempite.append((chiave, trovata))
        else:
            fuori.append(chiave)
        avanzamento(i, len(da_fare))

    cambiate = 0
    for chiave, (it, en) in riempite:
        voce = voci[chiave]
        if (voce.get("nome_it"), voce.get("nome_en")) != (it, en):
            cambiate += 1
        voce["nome_it"], voce["nome_en"] = it, en
    return {"da_fare": da_fare, "riempite": riempite, "da_articolo": da_articolo,
            "fuori": fuori, "disaccordi": disaccordi, "cambiate": cambiate}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--solo", default="moves,items,abilities",
                    help="basi da trattare, separate da virgola")
    args = ap.parse_args()

    def avanzamento(fatto, totale):
        if fatto % 20 == 0 or fatto == totale:
            print(f"    {fatto}/{totale}", flush=True)

    rapporto = {}
    for base in [b.strip() for b in args.solo.split(",") if b.strip()]:
        if base not in ELENCHI:
            print(f"base sconosciuta: {base} (le liste della wiki coprono "
                  f"{', '.join(ELENCHI)}; i Pokémon non hanno una pagina equivalente)")
            continue
        voci = voci_catalogo(base)
        if not voci:
            print(f"[{base}] catalogo vuoto, salto")
            continue
        print(f"[{base}] {len(voci)} voci", flush=True)
        esito = tratta(base, voci, avanzamento)
        rapporto[base] = esito
        # Si scrive solo se qualcosa cambia davvero: un salvataggio a vuoto
        # sovrascriverebbe la copia di sicurezza pre-salvataggio con lo stato
        # gia' aggiornato, buttando via l'unica versione precedente.
        if args.dry_run or not esito["cambiate"]:
            print(f"    niente da cambiare in data/catalog/{base}.json")
        else:
            salva_catalogo(base, voci)
            print(f"    scritto data/catalog/{base}.json ({esito['cambiate']} voci aggiornate)")

    print("\n=== RAPPORTO ===")
    for base, e in rapporto.items():
        identiche = [c for c, (it, en) in e["riempite"] if chiave_confronto(it) == chiave_confronto(en)]
        print(f"\n{base}: senza traduzione {len(e['da_fare'])} -> riempite {len(e['riempite'])} "
              f"| ancora fuori {len(e['fuori'])}")
        print(f"   di cui davvero diverse in italiano: {len(e['riempite']) - len(identiche)} "
              f"| confermate identiche nelle due lingue: {len(identiche)}")
        if e["da_articolo"]:
            print(f"   prese dall'articolo singolo (non erano nell'elenco): {len(e['da_articolo'])}")
        for chiave, (it, en) in e["riempite"]:
            if chiave_confronto(it) != chiave_confronto(en):
                print(f"      {chiave:<26} -> {it}")
        if e["fuori"]:
            print(f"   ancora senza traduzione ({len(e['fuori'])}): " + " | ".join(e["fuori"]))
        if e["disaccordi"]:
            print(f"   ⚠ la wiki non concorda con PokéAPI su {len(e['disaccordi'])} voci "
                  f"già tradotte (non toccate):")
            for chiave, pokeapi, wiki in e["disaccordi"]:
                print(f"      {chiave:<26} PokéAPI: {pokeapi:<22} wiki: {wiki}")

    if args.dry_run:
        print("\n--dry-run: niente scritto su disco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
