#!/usr/bin/env python
"""Controlla che i Pokémon e il catalogo delle abilità si parlino ancora.

    python scripts/controlla_abilita.py

Esce con 1 se trova qualcosa. Tre domande, e nessuna delle tre da' errore a schermo
quando la risposta e' sbagliata — e' per questo che serve uno script:

1. **ogni nome di abilita' citato da un Pokémon risolve su una voce?** Il catalogo
   Pokémon cita le abilita' col nome **inglese**, le chiavi sono italiane, e il
   legame passa da `nome_en`. Il 10/09/2026 era rotto per **una** voce: Mega
   Meganium citava `Mega Sol`, che era il `nome_en` di `Megasolar` finche' il giro
   sui nomi dell'11/08 non l'ha cambiato. Nella tendina restava il nome grezzo,
   senza descrizione ne' effetto, e nessuno se n'e' accorto per un mese
2. **due chiavi si chiamano uguale?** E' il caso `Sheer Force` = `Forza Bruta` +
   `Forzabruta` dell'11/08: `indiceNomi()` a parita' di nome tiene quella che ha un
   effetto, ma e' una rete, non una cura — con due voci **entrambe** attive vince
   l'ultima, e nessuno lo dice
3. **quante voci attive sono irraggiungibili da un Pokémon?** Non e' un errore (le
   abilita' inventate di Champions stanno li' apposta), ma il numero va guardato:
   se cresce, un effetto e' finito di nuovo dalla parte sbagliata

Legge e basta: non scrive niente, mai.
"""
import io
import json
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGO = os.path.join(RADICE, "data", "catalog")


def carica(nome):
    with io.open(os.path.join(CATALOGO, nome + ".json"), encoding="utf-8") as f:
        return json.load(f)


def attivo(voce):
    return (voce.get("effect") or {}).get("type") not in (None, "none")


def main():
    ab = carica("abilities")["abilities"]
    pokemon = carica("pokemon")

    # chi cita cosa: nome citato -> Pokémon che lo scrivono
    citati = {}
    for chiave, voce in pokemon.items():
        elenchi = [(voce.get("name") or chiave, voce.get("abilities") or [])]
        elenchi += [(nf, f.get("abilities") or [])
                    for nf, f in (voce.get("forms") or {}).items()]
        for nome, elenco in elenchi:
            for a in elenco:
                citati.setdefault(a, []).append(nome)

    # l'indice dei nomi, come lo costruisce `indiceNomi()` nel browser
    indice = {}
    for chiave, voce in ab.items():
        for n in (chiave, voce.get("nome_it"), voce.get("nome_en")):
            if n:
                indice.setdefault(n.lower(), []).append(chiave)

    problemi = 0

    orfani = {a: p for a, p in citati.items() if a.lower() not in indice}
    print(f"nomi di abilita' citati dai Pokémon : {len(citati)}")
    print(f"  senza nessuna voce che risponda   : {len(orfani)}")
    for a, p in sorted(orfani.items()):
        problemi += 1
        print(f"    ⚠️ '{a}' — citata da {', '.join(sorted(set(p))[:4])}")

    doppi = {n: ks for n, ks in indice.items() if len(set(ks)) > 1}
    print(f"nomi condivisi da piu' chiavi        : {len(doppi)}")
    for n, ks in sorted(doppi.items()):
        chiavi = sorted(set(ks))
        attive = [k for k in chiavi if attivo(ab[k])]
        problemi += 1
        print(f"    ⚠️ '{n}' -> {chiavi}" +
              (f"  ⛔ {len(attive)} attive: vince l'ultima" if len(attive) > 1 else ""))

    attive = [k for k, v in ab.items() if attivo(v)]
    raggiungibili = [k for k in attive
                     if any(n and n.lower() in {c.lower() for c in citati}
                            for n in (k, ab[k].get("nome_it"), ab[k].get("nome_en")))]
    print(f"voci con un effetto                  : {len(attive)}")
    print(f"  di cui raggiungibili da un Pokémon : {len(raggiungibili)}")
    print(f"  irraggiungibili (Champions & co.)  : {len(attive) - len(raggiungibili)}")
    print(f"voci totali                          : {len(ab)}")

    if problemi:
        print(f"\n{problemi} cose da guardare.")
        return 1
    print("\nTutto a posto.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
