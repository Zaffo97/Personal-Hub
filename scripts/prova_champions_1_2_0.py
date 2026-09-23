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
    # ⚠️ Dal 21/09/2026 non sono più due soli modi di avere Slash, ma quattro, e vanno
    # tenuti distinti: la toppa lo dà alle 29 specie nominate e alle **forme** di
    # quelle; le 25 voci di Regulation M-C hanno una lista **integrata** da Bulbapedia
    # che è già alla 1.2.0 e Slash ce l'ha dentro da sé; e le Gigantamax lo prendono
    # perché **ereditano**. Una voce con Slash che non rientri in nessuno dei quattro è
    # la cosa che questa prova deve trovare.
    altre = [k for k in con_slash if k not in nomi_toppati]
    # ⚠️ Chi eredita si conta **per primo**, e si guarda `eredita_da` in tutti e due i
    # posti in cui può stare: a livello di voce (le Gigantamax, che copiano ogni blocco)
    # e **dentro il blocco** (le 6 Mega di M-C, a cui spetta solo `champions`). Senza
    # questo, Mega Absol Z e Mega Garchomp Z finirebbero fra le «forme toppate», che
    # non sono: lo Slash ce l'hanno perché è nella lista che ereditano.
    eredi = sorted(k for k in altre
                   if "eredita_da" in (voci.get(k) or {})
                   or ((voci.get(k) or {}).get("champions") or {}).get("eredita_da"))
    per_forma = sorted(k for k in altre
                       if k not in eredi and specie_di.get(k) in nomi_toppati)
    integrate = sorted(k for k in altre if k not in eredi
                       and ((voci.get(k) or {}).get("champions") or {}).get("fonte"))
    inspiegate = sorted(set(altre) - set(per_forma) - set(integrate) - set(eredi))
    esito("Slash è nelle liste delle 29 voci nominate dalla toppa",
          len(scelte) == 29, f"{len(scelte)} voci")
    # 18, non 19: la diciannovesima forma toccata dalla toppa è **Mega Mawile**, che
    # prende le tre mosse di Mawile e non Slash, quindi qui non compare. E Charizard
    # Gigantamax è fra chi **eredita**, non fra le forme propagate.
    esito("e in quelle delle forme di quelle specie",
          len(per_forma) == 18, f"{len(per_forma)} forme, fra cui {per_forma[:3]}")
    esito("nessuna voce ha Slash senza una ragione fra le quattro",
          not inspiegate,
          inspiegate[:5] or f"{len(integrate)} integrate, {len(eredi)} che ereditano")
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
    # 333 fino al 21/09/2026, poi 362: +25 sono le voci di Regulation M-C integrate da
    # Bulbapedia, +4 le loro forme Gigantamax che ereditano la lista nuova.
    # 373 dal 23/09/2026: i tre piumaggi di Squawkabilly entrati in M-C col confronto
    # delle fonti ereditano la lista della specie (scripts/dichiara_eredita.py).
    esito("373 voci del Pokedex hanno un elenco, le altre no",
          con == 373, f"{con} su {len(tutte)}")
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

    print("\n== 9. Regulation M-C, integrata il 21/09/2026 ==")
    # Le 25 voci arrivate con la 1.2.0 che PokéAPI non ha: le loro liste vengono da
    # Bulbapedia, e il roster è confermato da Serebii e da Game8.
    mc = ["Alolan Persian", "Indeedee (Female)", "Toxtricity (Low Key Form)", "arboliva",
          "baxcalibur", "cinderace", "farfetchd", "gogoat", "golisopod", "grapploct",
          "indeedee-male", "inteleon", "mabosstiff", "mr-mime", "perrserker", "persian",
          "pincurchin", "rillaboom", "salamence", "sirfetchd",
          "squawkabilly-green-plumage", "swalot", "thievul", "toxtricity-amped",
          "wigglytuff"]
    senza_lista = [k for k in mc
                   if not (((voci.get(k) or {}).get("champions") or {}).get("moves"))]
    esito("tutte e 25 le voci di M-C hanno la loro lista", not senza_lista,
          senza_lista[:5] or "25 su 25")
    non_integrate = [k for k in mc
                     if ((voci.get(k) or {}).get("champions") or {}).get("fonte")
                     != "bulbapedia"]
    esito("e dichiarano la fonte, invece di sembrare venute dal dump",
          not non_integrate, non_integrate[:5] or "fonte: bulbapedia")

    # ⚠️ Il controllo incrociato che conta: le **liste** vengono da Bulbapedia, questi
    # **cambi** li elenca Game8 («List of Changes», Regulation M-C). Due fonti che non
    # si copiano a vicenda.
    gol = set((((voci.get("golisopod") or {}).get("champions") or {}).get("moves")) or {})
    esito("Golisopod: Close Combat, U-turn e Gunk Shot sì, Knock Off no (Game8)",
          {"Close Combat", "U-turn", "Gunk Shot"} <= gol and "Knock Off" not in gol,
          f"{len(gol)} mosse")
    ind = set((((voci.get("Indeedee (Female)") or {}).get("champions") or {}).get("moves")) or {})
    wig = set((((voci.get("wigglytuff") or {}).get("champions") or {}).get("moves")) or {})
    gra = set((((voci.get("grapploct") or {}).get("champions") or {}).get("moves")) or {})
    esito("Indeedee Femmina ha Sing e Terrain Pulse, Wigglytuff Moonblast, "
          "Grapploct Mach Punch (Game8)",
          {"Sing", "Terrain Pulse"} <= ind and "Moonblast" in wig
          and "Mach Punch" in gra)

    # Le forme Gigantamax delle specie appena integrate: `eredita_da` dice che la loro
    # lista È quella della base, e l'eredità è costruita **prima** dell'integrazione.
    gmax = ["Cinderace (Gigantamax Form)", "Inteleon (Gigantamax Form)",
            "Rillaboom (Gigantamax Form)", "Toxtricity (Gigantamax Form)"]
    storte = [g for g in gmax
              if (((voci.get(g) or {}).get("champions") or {}).get("moves"))
              != (((voci.get(specie_di.get(g, "")) or {}).get("champions") or {}).get("moves"))]
    esito("le 4 Gigantamax delle specie integrate hanno la lista della loro base",
          not storte, storte or "4 su 4")

    print("\n== 10. Morpeko: le due forme hanno la stessa lista ==")
    # Deciso il 21/09/2026 dopo aver cercato una terza fonte, come chiesto da Davide:
    # Serebii e Game8 danno una **lista unica** per Full Belly e Hangry, con dentro le
    # cinque mosse che nel dump mancavano alla Hangry, e dicono che l'unica cosa che
    # dipende dalla forma è il **tipo di Aura Wheel**.
    piena = set((((voci.get("morpeko-full-belly-mode") or {}).get("champions") or {})
                 .get("moves")) or {})
    hangry = set((((voci.get("Morpeko (Hangry Mode)") or {}).get("champions") or {})
                  .get("moves")) or {})
    esito("Full Belly e Hangry hanno esattamente la stessa lista",
          piena == hangry and len(piena) == 65,
          f"{len(piena)} e {len(hangry)}, differenze {sorted(piena ^ hangry)}")
    esito("le cinque mosse che mancavano alla Hangry ci sono",
          {"Assurance", "Payback", "Rising Voltage", "Round", "Snore"} <= hangry)

    print("\n== 11. le 6 Mega di M-C prendono la lista della loro specie ==")
    # ⚠️ Non è una deduzione: **Pokémon Zone** ha una pagina per **ogni Mega**, con la
    # sua tabella «Learnable Moves», e confrontate il 21/09/2026 danno **6 su 6** la
    # lista identica a quella della specie (Golisopod 67, Absol 72, Salamence 62,
    # Garchomp 59, Lucario 83, Baxcalibur 51). Bulbapedia non dà un blocco alle Mega e
    # il dump non ha righe per loro: senza questa fonte restavano senza elenco.
    mega_mc = {"Mega Salamence": "salamence", "Mega Absol Z": "absol",
               "Mega Garchomp Z": "garchomp", "Mega Lucario Z": "lucario",
               "Mega Golisopod": "golisopod", "Mega Baxcalibur": "baxcalibur"}
    storte, senza_fonte = [], []
    for forma, specie in mega_mc.items():
        blocco = (voci.get(forma) or {}).get("champions") or {}
        if (blocco.get("moves") or {}) != (((voci.get(specie) or {})
                                            .get("champions") or {}).get("moves") or {}):
            storte.append(forma)
        if blocco.get("eredita_da") != specie or not blocco.get("fonte"):
            senza_fonte.append(forma)
    esito("tutte e 6 hanno esattamente la lista della loro specie",
          not storte, storte or "6 su 6")
    esito("e ognuna dichiara da chi eredita e da quale fonte",
          not senza_fonte, senza_fonte or "eredita_da + fonte su tutte e 6")
    # ⚠️ La derivazione è dichiarata **dentro il blocco**, non a livello di voce: a
    # livello di voce vorrebbe dire «tutti i blocchi», e a cinque di queste sei la lista
    # `main` della specie non spetta — nei giochi principali non esistono.
    con_main = [f for f in mega_mc if "main" in (voci.get(f) or {})]
    esito("e non si sono prese anche la lista `main` della specie",
          con_main == ["Mega Salamence"],
          f"{con_main} (Mega Salamence ce l'ha di suo: è una Mega di ORAS)")

    print("\n== 12. Growth è di tipo Erba in Champions ==")
    # ⚠️ Non viene da Bulbapedia: la sezione «Changes from Scarlet and Violet» **non lo
    # cita**, e per questo il 18/09 era rimasto Normale. Lo dicono Game8 e Serebii.
    esito("Growth: type erba", (mosse.get("Growth") or {}).get("type") == "grass",
          str((mosse.get("Growth") or {}).get("type")))

    print(f"\n{sum(esiti)} controlli su {len(esiti)}")
    return 0 if all(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
