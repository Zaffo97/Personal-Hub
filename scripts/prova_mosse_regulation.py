#!/usr/bin/env python
"""L'elenco mosse della regulation non deve più nascondere mosse legali.

    python scripts/prova_mosse_regulation.py

Gira su una **copia** di `hub.db` e non tocca nessun file di dati.

⚠️ Perché esiste. Fino al 18/09/2026 il campo `moves` di MA e MB erano le 460 chiavi di
`data/moves_ma.json` (04/05/2026), non l'elenco delle mosse di Champions. La tendina del
calcolatore è l'**intersezione** fra quell'elenco e le mosse del singolo Pokémon
(`loadMovesDB()` in `static/js/calcolatori-danno.js`), quindi ogni mossa fuori dalle 460
spariva **senza nessun avviso**: Crunch da Incineroar, 13 mosse da Pawmot, 3239 righe su
17219 in MA. Nessun errore a schermo, solo una tendina più corta del vero.

Queste prove tengono ferme le due proprietà che lo rendono impossibile:

1. per ogni Pokémon del roster, l'intersezione è **tutta** la sua lista (0 perdite);
2. ogni mossa dell'elenco ha una voce in `catalog/moves.json`, cioè la tendina non può
   mostrare un nome senza dati dietro.

Più i casi concreti citati nel backlog, e la garanzia che `pokedex` è rimasta com'era.
"""
import os
import shutil
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f" — {dettaglio}" if dettaglio else ""))


def main():
    origine = os.path.join(RADICE, "hub.db")
    if os.path.exists(origine):
        copia = os.path.join(tempfile.gettempdir(), "prova_mosse_hub.db")
        shutil.copy(origine, copia)
        import extensions
        extensions.DB = copia            # ⚠️ prima di creare l'app, non dopo

    import json
    from blueprints.pokemon import _load_filtro, _list_regulation_files, load_catalog, mosse_legali

    catalogo_mosse = load_catalog("moves")
    regs = {r["id"]: r for r in _list_regulation_files()}

    print("\n== 1. nessuna mossa legale resta fuori dall'elenco ==")
    for rid in ("ma", "mb"):
        reg = regs[rid]
        filtro = _load_filtro(reg)
        permesse = set(filtro["moves"])
        totale = perse = con_lista = 0
        peggiore = (0, "")
        for nome in filtro["pokemon"]:
            elenco, _ = mosse_legali(nome, reg)
            if elenco is None:
                continue
            con_lista += 1
            fuori = [m for m in elenco if m not in permesse]
            totale += len(elenco)
            perse += len(fuori)
            if len(fuori) > peggiore[0]:
                peggiore = (len(fuori), nome)
        esito(f"{rid}: 0 mosse nascoste su {totale} ({con_lista} specie con lista)",
              perse == 0, f"nascoste {perse}" + (f", peggiore {peggiore[1]}" if perse else ""))

    print("\n== 2. ogni voce dell'elenco ha i suoi dati ==")
    for rid in ("ma", "mb"):
        senza = sorted(set(_load_filtro(regs[rid])["moves"]) - set(catalogo_mosse))
        esito(f"{rid}: nessuna mossa senza voce in catalog/moves.json",
              not senza, ", ".join(senza[:5]))

    print("\n== 3. e nessuna voce morta: ogni mossa la impara qualcuno del roster ==")
    for rid in ("ma", "mb"):
        reg = regs[rid]
        filtro = _load_filtro(reg)
        imparabili = set()
        for nome in filtro["pokemon"]:
            elenco, _ = mosse_legali(nome, reg)
            if elenco:
                imparabili |= set(elenco)
        orfane = sorted(set(filtro["moves"]) - imparabili)
        esito(f"{rid}: 0 mosse che nessuno del roster impara",
              not orfane, f"{len(orfane)} orfane: " + ", ".join(orfane[:5]) if orfane else "")

    print("\n== 4. i casi concreti del backlog ==")
    casi = [("ma", "Incineroar", "Crunch"), ("mb", "Incineroar", "Crunch"),
            ("ma", "Incineroar", "Endure"), ("ma", "Pawmot", "Substitute")]
    for rid, pkmn, mossa in casi:
        elenco, _ = mosse_legali(pkmn, regs[rid])
        permesse = set(_load_filtro(regs[rid])["moves"])
        visibile = elenco is not None and mossa in elenco and mossa in permesse
        esito(f"{rid}: «{mossa}» è nella tendina di {pkmn}", visibile,
              f"{len([m for m in (elenco or []) if m in permesse])} mosse visibili su "
              f"{len(elenco or [])}")

    print("\n== 5. MA e MB non sono più una copia l'una dell'altra ==")
    ma = set(_load_filtro(regs["ma"])["moves"])
    mb = set(_load_filtro(regs["mb"])["moves"])
    esito("gli elenchi differiscono, e la differenza viene dal roster",
          ma != mb, f"MA {len(ma)}, MB {len(mb)}, solo in MB: " + ", ".join(sorted(mb - ma)))

    print("\n== 6. pokedex non è stata toccata ==")
    filtro = _load_filtro(regs["pokedex"])
    esito("pokedex ha ancora `moves: null` (tutto il catalogo)",
          filtro.get("moves") is None, str(filtro.get("moves"))[:40])

    print("\n== 7. e questo è ciò che il calcolatore riceve davvero ==")
    # `MOVES_DB` nella pagina è esattamente `load_moves(reg)['moves']`: si controlla
    # quello, non il file, così il filtro e il loader non possono divergere.
    from blueprints.pokemon import load_moves
    attese = {"pokedex": len(catalogo_mosse), "ma": len(ma), "mb": len(mb)}
    for rid, quante in attese.items():
        dati = load_moves(rid).get("moves", {})
        esito(f"{rid}: MOVES_DB della pagina ha {quante} mosse",
              len(dati) == quante, f"ne ha {len(dati)}")
    esito("«Crunch» arriva alla pagina di MA", "Crunch" in load_moves("ma").get("moves", {}))

    print(f"\n{sum(esiti)} controlli su {len(esiti)}")
    return 0 if all(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
