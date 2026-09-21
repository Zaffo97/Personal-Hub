#!/usr/bin/env python
"""Le prove della regola che sceglie il version group di `main`. Non scrive niente.

    python scripts/prova_moveset_main.py

Fino al 21/09/2026 `main` prendeva il gioco **più recente** in cui la voce compare, e
basta. Il difetto non era «Leggende Arceus dà poche mosse»: era che un gioco col
sistema di mosse ridotto **vince perché è più recente**, e il risultato non dava
nessun errore — dava il numero sbagliato. Abra aveva **una** mossa invece di 49, e 77
voci su 1293 stavano così.

Cosa dimostra, in ordine:

- che la regola **esclude** i giochi fuori serie ma non li butta: una voce che compare
  **solo** lì la si prende lo stesso, dichiarando che è un ripiego. È il caso di
  Partner Pikachu e Partner Eevee, che in nessun altro gioco esistono
- che `legends-za` e `mega-dimension` sono nell'elenco **pur essendo vuoti oggi**.
  Hanno order 30 e 31, cioè stanno **sopra** Scarlatto/Violetto: il giorno che PokéAPI
  li riempie diventerebbero da soli la sorgente di centinaia di voci senza che nessuno
  abbia toccato niente. Questa prova esiste perché togliergli l'esclusione non sia
  silenzioso
- che i **due scrittori usano la stessa funzione**, non due copie. `pokeapi.moveset()`
  (l'import dal pannello) e `importa_mosse_specie.py` (l'import in blocco) applicavano
  la stessa regola in due punti, ed è così che il difetto è sopravvissuto
- che il **file sul disco** sia d'accordo con la regola: se qualcuno cambia l'elenco
  degli esclusi e non rilancia l'import, il file resta indietro senza dirlo
- che il blocco **`champions` non sia toccato** da tutto questo: è quello che leggono
  tutte e tre le regulation, e una modifica lì si vedrebbe a schermo
"""
import io
import json
import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import pokeapi
import importa_mosse_specie as blocco

MOVESET = os.path.join(RADICE, "data", "catalog", "pokemon_moves.json")

esiti = []


def esito(nome, ok, dettaglio=""):
    esiti.append((nome, ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def carica():
    with io.open(MOVESET, encoding="utf-8") as f:
        return json.load(f)


# ── la regola, su gruppi finti ──────────────────────────────────────────────
def prove_regola():
    print("\n== la regola di scelta ==")
    # id -> (nome, order), come nel dump
    gruppi = {
        "20": ("ultra-sun-ultra-moon", 20),
        "21": ("lets-go-pikachu-lets-go-eevee", 21),
        "25": ("brilliant-diamond-shining-pearl", 25),
        "26": ("legends-arceus", 26),
        "27": ("scarlet-violet", 27),
        "30": ("legends-za", 30),
        "32": ("champions", 32),
    }
    ID_CH = "32"

    vg, ripiego = pokeapi.scegli_vg_main({"27": {}, "26": {}}, gruppi, ID_CH)
    esito("fra Scarlatto/Violetto e Leggende Arceus vince S/V",
          gruppi[vg][0] == "scarlet-violet" and not ripiego, gruppi[vg][0])

    vg, ripiego = pokeapi.scegli_vg_main({"20": {}, "21": {}}, gruppi, ID_CH)
    esito("fra UltraSole/UltraLuna e Let's Go vince USUM",
          gruppi[vg][0] == "ultra-sun-ultra-moon" and not ripiego, gruppi[vg][0])

    vg, ripiego = pokeapi.scegli_vg_main({"25": {}, "26": {}, "30": {}}, gruppi, ID_CH)
    esito("Leggende Z-A non vince su Brillante Diamante, pur avendo order più alto",
          gruppi[vg][0] == "brilliant-diamond-shining-pearl" and not ripiego,
          gruppi[vg][0])

    vg, ripiego = pokeapi.scegli_vg_main({"21": {}}, gruppi, ID_CH)
    esito("una voce che sta SOLO in un gioco fuori serie la si prende lo stesso",
          gruppi[vg][0] == "lets-go-pikachu-lets-go-eevee" and ripiego,
          f"{gruppi[vg][0]}, ripiego={ripiego}")

    vg, ripiego = pokeapi.scegli_vg_main({"32": {}}, gruppi, ID_CH)
    esito("Champions non finisce MAI in `main`, nemmeno da solo", vg is None,
          "nessun version group scelto")

    vg, _ = pokeapi.scegli_vg_main({}, gruppi, ID_CH)
    esito("nessun version group: nessuna scelta, non un errore", vg is None)

    attesi = {"colosseum", "xd", "lets-go-pikachu-lets-go-eevee",
              "legends-arceus", "legends-za", "mega-dimension"}
    esito("l'elenco degli esclusi è quello deciso il 21/09/2026",
          pokeapi.VG_FUORI_SERIE == attesi,
          f"{len(pokeapi.VG_FUORI_SERIE)} giochi")
    esito("⚠️ legends-za e mega-dimension ci sono pur essendo vuoti nel dump di oggi",
          {"legends-za", "mega-dimension"} <= pokeapi.VG_FUORI_SERIE)


# ── i due scrittori ─────────────────────────────────────────────────────────
def prove_scrittori():
    print("\n== i due scrittori applicano la stessa regola ==")
    esito("l'import in blocco usa la funzione di pokeapi, non una copia",
          blocco.scegli_vg_main is pokeapi.scegli_vg_main)
    esito("e lo stesso elenco di esclusi",
          blocco.VG_FUORI_SERIE is pokeapi.VG_FUORI_SERIE)
    sorgente = io.open(os.path.join(RADICE, "pokeapi.py"), encoding="utf-8").read()
    esito("`pokeapi.moveset()` non ha più la sua copia della scelta",
          "il version group più recente" not in sorgente,
          "nessun `max(candidati)` scritto a mano")


# ── il file sul disco ───────────────────────────────────────────────────────
def prove_file():
    print("\n== il file sul disco ==")
    voci = carica()["voci"]
    con_main = {k: v["main"] for k, v in voci.items() if "main" in v}

    usati = {v["vg"] for v in con_main.values()}
    fuori_usati = usati & pokeapi.VG_FUORI_SERIE
    esito("nessuna voce resta su Leggende Arceus",
          "legends-arceus" not in usati,
          f"{sum(1 for v in con_main.values() if v['vg'] == 'legends-arceus')} voci")

    su_fuori = sorted(k for k, v in con_main.items()
                      if v["vg"] in pokeapi.VG_FUORI_SERIE)
    esito("le sole voci su un gioco fuori serie sono i due Partner",
          su_fuori == ["Partner Eevee", "Partner Pikachu"],
          f"{fuori_usati or 'nessuno'}: {su_fuori}")

    # Il sintomo concreto, quello che si vedeva a schermo.
    abra = len((con_main.get("abra") or {}).get("moves") or {})
    esito("Abra non ha più una mossa sola", abra > 1, f"{abra} mosse")

    magri = sorted((len(v["moves"]), k) for k, v in con_main.items())[:5]
    esito("le liste più corte restano poche e spiegabili",
          all(n >= 1 for n, _ in magri),
          ", ".join(f"{k}={n}" for n, k in magri))


# ── il file e la regola sono d'accordo ──────────────────────────────────────
def prove_coerenza():
    print("\n== il file è d'accordo con la regola (se no, va rilanciato l'import) ==")
    gruppi = blocco.leggi("version_groups.csv")
    gruppi = {r["id"]: (r["identifier"], int(r["order"])) for r in gruppi}
    id_ch = next((i for i, (n, _) in gruppi.items() if n == pokeapi.VG_CHAMPIONS), None)
    pokemon = {r["id"]: r["identifier"] for r in blocco.leggi("pokemon.csv")}

    presenti = {}
    for r in blocco.leggi("pokemon_moves.csv"):
        slug = pokemon.get(r["pokemon_id"])
        if slug:
            presenti.setdefault(slug, set()).add(r["version_group_id"])

    voci = carica()["voci"]
    sbagliate = []
    for chiave, voce in voci.items():
        if "main" not in voce or "eredita_da" in voce:
            continue          # le Gigantamax copiano dalla base, non scelgono
        per_vg = {v: {} for v in presenti.get(voce.get("slug") or "", ())}
        if not per_vg:
            continue
        atteso, _ = pokeapi.scegli_vg_main(per_vg, gruppi, id_ch)
        if atteso is not None and gruppi[atteso][0] != voce["main"]["vg"]:
            sbagliate.append((chiave, voce["main"]["vg"], gruppi[atteso][0]))
    esito("ogni voce ha il version group che la regola sceglierebbe oggi",
          not sbagliate, f"{len(sbagliate)} fuori posto" if sbagliate
          else f"{sum(1 for v in voci.values() if 'main' in v)} voci controllate")
    for c in sbagliate[:5]:
        print(f"      {c[0]}: ha {c[1]}, dovrebbe avere {c[2]}")


# ── champions non c'entra ───────────────────────────────────────────────────
def prove_champions():
    print("\n== il blocco `champions`, che è quello che si vede a schermo ==")
    voci = carica()["voci"]
    con_ch = {k: v for k, v in voci.items() if "champions" in v}
    tot = sum(len(v["champions"]["moves"]) for v in con_ch.values())
    esito("le voci di Champions sono ancora 333", len(con_ch) == 333, f"{len(con_ch)}")
    esito("nessun blocco `champions` porta un `vg`: non lo sceglie nessuna regola",
          all("vg" not in v["champions"] for v in con_ch.values()), f"{tot} mosse")

    # Una forma Gigantamax dichiara `eredita_da`: la sua lista DEVE essere quella
    # della base, e il 18/09/2026 su Charizard non lo era — la toppa della 1.2.0 era
    # arrivata alla specie e non alla forma.
    # ⚠️ `eredita_da` nomina la base col **nome visualizzato** (`Charizard`), non con la
    # chiave del catalogo (`charizard`): senza il ponte il confronto non trova niente e
    # la prova fallirebbe su tutte e 32 le forme, dando la colpa ai dati.
    _, _, per_nome = blocco.indice_catalogo()
    disallineate = []
    for chiave, voce in voci.items():
        base = voce.get("eredita_da")
        if not base:
            continue
        sorgente = voci.get(per_nome.get(base, base)) or {}
        for quale in ("main", "champions"):
            if (voce.get(quale) or {}).get("moves") != (sorgente.get(quale) or {}).get("moves"):
                disallineate.append(f"{chiave}/{quale}")
    esito("ogni forma che dichiara `eredita_da` ha davvero la lista della sua base",
          not disallineate, disallineate[:4] or "32 forme controllate")


def main():
    if not os.path.exists(MOVESET):
        print(f"manca {MOVESET}")
        return 1
    prove_regola()
    prove_scrittori()
    prove_file()
    prove_coerenza()
    prove_champions()
    passate = sum(1 for _, ok in esiti if ok)
    print(f"\n{passate} prove su {len(esiti)}." +
          ("  Tutte passate." if passate == len(esiti) else "  FALLITE."))
    return 0 if passate == len(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
