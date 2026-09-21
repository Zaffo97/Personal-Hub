#!/usr/bin/env python
"""Le liste e i dati mossa devono essere quelli di Champions 1.2.0, e restarci.

    python scripts/prova_champions_1_2_0.py

Non tocca nessun file: legge i dati veri e lavora in memoria su copie.

⚠️ Perché esiste. Il dump di PokéAPI è fermo prima della versione 1.2.0 (9 settembre
2026), e `pokemon_moves.json` lo **rigenerano** `importa_mosse_specie.py` e l'import
dal pannello: una mossa aggiunta o tolta a mano lì dentro tornerebbe al giro dopo
**senza nessun errore**. Per questo le correzioni stanno in `moveset_integrazioni.json`
sotto `toppe`, e la prova più importante è la numero 3: dopo una rigenerazione finta,
le toppe si riapplicano da sole.
"""
import copy
import json
import os
import sys

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
    from blueprints.pokemon import (load_catalog, load_moveset, mosse_legali,
                                    applica_toppe_moveset, file_integrazioni_moveset,
                                    _load_filtro, _list_regulation_files)

    voci, _ = load_moveset()
    regs = {r["id"]: r for r in _list_regulation_files()}
    ma = {"id": "ma", "moveset": "champions"}

    def lista(nome):
        return set(mosse_legali(nome, ma)[0] or [])

    print("\n== 1. il changelog ufficiale della 1.2.0 ==")
    esito("Politoed non ha più Pound", "Pound" not in lista("Politoed"),
          f"{len(lista('Politoed'))} mosse")
    arch = lista("Archaludon")
    esito("Archaludon non ha più Mirror Coat né Metal Burst",
          "Mirror Coat" not in arch and "Metal Burst" not in arch, f"{len(arch)} mosse")
    con_slash = [k for k, v in voci.items()
                 if "Slash" in (((v.get("champions") or {}).get("moves")) or {})]
    # ⚠️ Il numero era **29 secco** fino al 21/09/2026, e contarlo così nascondeva il
    # difetto: la toppa è scritta con la **chiave di una specie**, e si fermava lì. Le
    # forme delle specie toppate — Mega Absol, Mega Charizard X e Y, Aegislash (Blade
    # Forme), Mimikyu (Busted Form), … — restavano **senza** Slash pur essendo tutte in
    # MA e MB: a schermo Absol poteva sceglierlo e Mega Absol no. Quindi il conto si
    # spezza in due, e la seconda metà è quella che allora valeva zero.
    with open(file_integrazioni_moveset(), encoding="utf-8") as f:
        nomi_toppati = set((json.load(f) or {}).get("toppe") or {})
    specie_di = {nf: k for k, d in load_catalog("pokemon").items()
                 for nf in (d.get("forms") or {})}
    scelte = [k for k in con_slash if k in nomi_toppati]
    per_forma = sorted(k for k in con_slash if k not in nomi_toppati)
    esito("Slash è nelle liste delle 29 voci nominate dalla toppa",
          len(scelte) == 29, f"{len(scelte)} voci")
    esito("e in quelle delle forme di quelle specie, nessuna esclusa",
          per_forma and all(specie_di.get(k) in nomi_toppati for k in per_forma),
          f"{len(per_forma)} forme, fra cui {per_forma[:3]}")
    senza = sorted(nf for nf, sp in specie_di.items()
                   if sp in con_slash and nf not in con_slash
                   and (((voci.get(nf) or {}).get("champions") or {}).get("moves")))
    esito("nessuna forma di una specie con Slash ne è rimasta fuori",
          not senza, senza[:6] or "0 rimaste indietro")
    esito("fra queste Absol, Garchomp e Weavile",
          {"absol", "garchomp", "weavile"} <= set(con_slash))

    print("\n== 2. le correzioni prese da Bulbapedia ==")
    ari = lista("Ariados")
    esito("Ariados ha Psychic Fangs e non Psychic",
          "Psychic Fangs" in ari and "Psychic" not in ari, f"{len(ari)} mosse")
    maw = set((((voci.get("mawile") or {}).get("champions") or {}).get("moves")) or {})
    esito("Mawile ha Charm, Draining Kiss e Misty Terrain",
          {"Charm", "Draining Kiss", "Misty Terrain"} <= maw, f"{len(maw)} mosse")
    hou = set((((voci.get("houndstone") or {}).get("champions") or {}).get("moves")) or {})
    esito("Houndstone ha Bulldoze", "Bulldoze" in hou, f"{len(hou)} mosse")

    print("\n== 3. le lacune di Bulbapedia NON sono state applicate ==")
    gar = lista("Gardevoir")
    cinque = {"Alluring Voice", "Aura Sphere", "Body Slam", "Calm Mind", "Charge Beam"}
    esito("Gardevoir ha ancora le 5 mosse che la pagina troncata non elenca",
          cinque <= gar, f"{len(cinque & gar)} su 5")
    bla = set((((voci.get("blaziken") or {}).get("champions") or {}).get("moves")) or {})
    esito("Blaziken ha ancora U-turn", "U-turn" in bla)
    rot = set((((voci.get("rotom") or {}).get("champions") or {}).get("moves")) or {})
    esito("Rotom base non ha preso le mosse delle sue forme",
          not ({"Overheat", "Hydro Pump", "Leaf Storm", "Blizzard"} & rot))

    print("\n== 4. e sopravvivono a una rigenerazione del dump ==")
    # Il finto dump è la voce com'era **prima** della 1.2.0: con Pound, senza Slash.
    finto = {"politoed": {"champions": {"vg": "champions",
                                        "moves": {"Pound": "train", "Bubble Beam": "train"}}},
             "absol": {"champions": {"vg": "champions", "moves": {"Bite": "train"}}}}
    applicate, superate, _ = applica_toppe_moveset(finto)
    dopo_pol = finto["politoed"]["champions"]["moves"]
    dopo_abs = finto["absol"]["champions"]["moves"]
    esito("dopo la rigenerazione Politoed riperde Pound", "Pound" not in dopo_pol,
          f"{sorted(dopo_pol)}")
    esito("e Absol riprende Slash", "Slash" in dopo_abs, f"{sorted(dopo_abs)}")
    esito("le toppe applicate vengono contate", len(applicate) >= 2,
          f"applicate {len(applicate)}")

    print("\n== 5. una toppa non si applica a vuoto ==")
    # Il dump si è allineato da solo: la toppa è superata e va detta, non applicata.
    allineato = {"politoed": {"champions": {"vg": "champions",
                                            "moves": {"Bubble Beam": "train"}}}}
    _, sup, _ = applica_toppe_moveset(allineato)
    esito("un dump già allineato marca la toppa come superata",
          "politoed/champions" in sup, f"superate {len(sup)}")
    senza = {"politoed": {}}
    _, sup2, _ = applica_toppe_moveset(senza)
    esito("e su una voce senza lista non ne inventa una",
          "politoed/champions" in sup2 and not senza["politoed"].get("champions"))

    print("\n== 6. i dati mossa sono quelli di Champions ==")
    mosse = load_catalog("moves")
    attesi = [("Slash", "bp", 80), ("Grav Apple", "bp", 90), ("Meteor Assault", "bp", 170),
              ("Snipe Shot", "bp", 85), ("Crabhammer", "accuracy", 95),
              ("Syrup Bomb", "accuracy", 90), ("Make It Rain", "accuracy", 95),
              ("Snap Trap", "type", "steel"), ("Freeze-Dry", "effect_chance", 0)]
    sbagliati = [(m, c, mosse.get(m, {}).get(c), v) for m, c, v in attesi
                 if mosse.get(m, {}).get(c) != v]
    esito("i 9 valori numerici di Champions", not sbagliati, str(sbagliati[:3]))
    esito("Toxic Thread abbassa la Velocità di 2",
          (mosse.get("Toxic Thread", {}).get("stat_changes") or {}).get("spe") == -2)
    esito("Make It Rain abbassa l'Att. Sp. di chi la usa di 2",
          (mosse.get("Make It Rain", {}).get("stat_changes") or {}).get("spa") == -2)
    esito("Dire Claw è slicing e Double Shock è punch",
          "slicing" in (mosse.get("Dire Claw", {}).get("flags") or [])
          and "punch" in (mosse.get("Double Shock", {}).get("flags") or []))

    print("\n== 7. e le regulation lo sanno ==")
    for rid in ("ma", "mb"):
        elenco = set(_load_filtro(regs[rid])["moves"])
        esito(f"{rid}: Slash c'è, Pound no", "Slash" in elenco and "Pound" not in elenco,
              f"{len(elenco)} mosse")

    print("\n== 8. anche il Pokedex mostra le mosse di Champions ==")
    # Decisione di Davide del 18/09/2026: «voglio solo ciò che imparano in Champions».
    # `pokedex` usa la sorgente `champions`, quindi chi in Champions non c'è **non ha
    # elenco** — l'avviso giallo e tutte le mosse — invece di un elenco preso da un
    # gioco che non c'entra (Abra aveva **una** mossa, da Leggende Arceus).
    pokedex = regs["pokedex"]
    esito("pokedex usa la sorgente `champions`",
          pokedex.get("moveset") == "champions", str(pokedex.get("moveset")))
    catalogo = load_catalog("pokemon")
    tutte = []
    for k, v in catalogo.items():
        tutte.append(k)
        tutte.extend((v.get("forms") or {}).keys())
    con = sum(1 for n in tutte if mosse_legali(n, pokedex)[0])
    esito("333 voci del Pokedex hanno un elenco, le altre no",
          con == 333, f"{con} su {len(tutte)}")
    esito("Incineroar nel Pokedex mostra le sue 77 di Champions",
          len(mosse_legali("Incineroar", pokedex)[0] or []) == 77)
    esito("Abra non ha più l'elenco da una mossa sola",
          mosse_legali("Abra", pokedex)[0] is None,
          str(mosse_legali("Abra", pokedex)[0]))
    # ⚠️ Il caso della regola #8 gira su `pokedex` e usa Amoonguss, che in Champions
    # non c'è: l'avviso giallo su Amoonguss è **previsto**, non un guasto. Il danno si
    # calcola lo stesso perché la mossa si scrive a mano (Buio, fisica, BP 100).
    esito("e Amoonguss prende l'avviso, come deve",
          mosse_legali("Amoonguss", pokedex)[0] is None)

    print(f"\n{sum(esiti)} controlli su {len(esiti)}")
    return 0 if all(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
