# -*- coding: utf-8 -*-
"""Confronta le stringhe che il codice chiede con quelle che il dizionario ha.

Serve perché la chiave del dizionario **è la frase italiana**: cambiare una parola
in un template stacca la traduzione senza che nulla dia errore — a schermo torna
l'italiano, che è il fallback giusto ma silenzioso. Questo script rende il silenzio
rumoroso.

    python scripts/controlla_traduzioni.py                # controlla e basta
    python scripts/controlla_traduzioni.py --scrivi       # aggiunge le mancanti, vuote

Non traduce niente da solo: le voci nuove le scrive con valore "" e vanno riempite
a mano. Una traduzione inventata dallo script sarebbe indistinguibile da una buona.

Esce con 1 se manca qualcosa, così si può usare come controllo prima di un commit.
"""
import argparse
import collections
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(BASE, "templates")
STATIC_JS = os.path.join(BASE, "static", "js")
I18N = os.path.join(BASE, "data", "i18n")

# t('...') e tf('...', {...}) — sia in Jinja che in JavaScript. Le due forme di
# apici vanno prese entrambe: nei template si scrive t('...'), nel JS capita "...".
CHIAMATA = re.compile(r"\bt f?\(|\btf?\(\s*(?P<q>['\"])(?P<testo>(?:\\.|(?!(?P=q)).)*)(?P=q)")


def chiavi_nel_codice():
    """Ogni frase passata a t() o tf(), con i file in cui compare."""
    trovate = {}
    cartelle = [(TEMPLATES, ".html"), (STATIC_JS, ".js")]
    for cartella, est in cartelle:
        if not os.path.isdir(cartella):
            continue
        for nome in sorted(os.listdir(cartella)):
            if not nome.endswith(est):
                continue
            testo = io.open(os.path.join(cartella, nome), encoding="utf-8").read()
            for m in CHIAMATA.finditer(testo):
                frase = m.group("testo")
                if not frase:
                    continue
                # nel JS le frasi lunghe sono spezzate con +: si ricompone qui,
                # perché nel dizionario la chiave è la frase intera.
                coda = testo[m.end():]
                agg = re.match(r"\s*\+\s*(['\"])((?:\\.|(?!\1).)*)\1", coda)
                while agg:
                    frase += agg.group(2)
                    coda = coda[agg.end():]
                    agg = re.match(r"\s*\+\s*(['\"])((?:\\.|(?!\1).)*)\1", coda)
                frase = frase.replace("\\'", "'").replace('\\"', '"')
                trovate.setdefault(frase, set()).add(nome)
    return trovate


def chiavi_doppie(percorso):
    """Le chiavi ripetute nel file, che `json.load()` non può vedere.

    Il dizionario si scrive a mano ed è lungo: la stessa frase può finire in due
    sezioni diverse. `json.load()` **tiene l'ultima e butta la prima in silenzio**,
    quindi correggere la traduzione sbagliata non cambia niente a schermo e non si
    capisce perché. Qui si legge il file grezzo, che è l'unico modo di accorgersene.
    """
    testo = io.open(percorso, encoding="utf-8").read()
    chiavi = re.findall(r'^\s*"((?:[^"\\]|\\.)*)"\s*:', testo, re.M)
    return sorted(k for k, n in collections.Counter(chiavi).items() if n > 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lingua", default="en", help="il dizionario da controllare (default: en)")
    ap.add_argument("--scrivi", action="store_true",
                    help="aggiunge le chiavi mancanti con valore vuoto")
    args = ap.parse_args()

    percorso = os.path.join(I18N, f"{args.lingua}.json")
    if not os.path.exists(percorso):
        print(f"manca {percorso}")
        return 1
    dizionario = json.load(io.open(percorso, encoding="utf-8"))

    nel_codice = chiavi_nel_codice()
    tradotte = {k for k in dizionario if not k.startswith("_")}
    # Le frasi passate a t() da una variabile — t({...}[d]) nelle tendine del
    # catalogo — non sono scritte dentro la chiamata, quindi qui non si vedono.
    # Il dizionario le dichiara in "_dinamiche" per non farle sembrare orfane.
    nel_codice.update({k: {"(dichiarata in _dinamiche)"}
                       for k in dizionario.get("_dinamiche", [])})

    mancanti = {k: v for k, v in nel_codice.items() if k not in tradotte}
    vuote = sorted(k for k in tradotte if not dizionario[k])
    orfane = sorted(tradotte - set(nel_codice))
    doppie = chiavi_doppie(percorso)

    print(f"chieste dal codice : {len(nel_codice)}")
    print(f"nel dizionario {args.lingua}  : {len(tradotte)}")
    print(f"mancanti           : {len(mancanti)}")
    print(f"presenti ma vuote  : {len(vuote)}")
    print(f"orfane (non più usate): {len(orfane)}")
    print(f"chiavi doppie      : {len(doppie)}")

    if mancanti:
        print("\n-- mancanti --")
        for k in sorted(mancanti):
            print(f"  [{', '.join(sorted(mancanti[k]))}] {k}")
    if vuote:
        print("\n-- da riempire --")
        for k in vuote:
            print(f"  {k}")
    if orfane:
        print("\n-- orfane: la frase nel codice è cambiata, o la voce non serve più --")
        for k in orfane:
            print(f"  {k}")
    if doppie:
        print("\n-- doppie: scritte due volte nel file. json.load() tiene l'ultima e")
        print("   butta la prima in silenzio, quindi correggere quella sbagliata")
        print("   non cambierebbe niente a schermo --")
        for k in doppie:
            print(f"  {k}")

    if args.scrivi and mancanti:
        for k in mancanti:
            dizionario[k] = ""
        with io.open(percorso, "w", encoding="utf-8") as f:
            json.dump(dizionario, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\nscritte {len(mancanti)} voci vuote in {percorso}: vanno riempite a mano.")

    return 1 if (mancanti or vuote or doppie) else 0


if __name__ == "__main__":
    sys.exit(main())
