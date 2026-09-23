"""Aggiornare il Pokédex dalla fonte: **aggiunge il nuovo, mostra il diverso.**

Chiesto da Davide il 22/09/2026 («un pulsante che aggiorni da solo tutto il Pokédex
quando la fonte cambia»), deciso il 23/09/2026 dopo averlo misurato:

- il catalogo e il dump di PokéAPI coincidono su **1318 voci su 1342**; le 24 che
  differiscono sono quelle **curate a mano** (quasi tutte Mega di Champions). Un
  aggiornamento che «riallinea» toccherebbe solo quelle, cioè il lavoro da non perdere
- quindi le voci **nuove** entrano, e le **differenze** su quelle esistenti si
  **mostrano** per una decisione, e non si applicano mai da qui

⚠️ La logica dell'import non è qui: sta in `scripts/build_catalog.py`, che questo
modulo carica e chiama. È la lezione di `fanta_import.py` — due copie della stessa
logica sono due copie che divergono — e lo script resta il rivestimento a riga di
comando. Da qui arrivano solo due cose in più: la scrittura passa da
`salva_catalogo()` e `_save_abilities()` (la copia di sicurezza), e le liste mosse
delle specie nuove, da `pokeapi.moveset()`, come fa il pannello `/pesca`.

Ogni funzione **non stampa**, torna un dizionario, e si rifiuta con `ok=False` e il
motivo scritto: se l'import avesse cambiato anche una sola voce curata
(`build_catalog.intatte()`), non si scrive niente.
"""
import contextlib
import importlib.util
import io
import os

RADICE = os.path.dirname(os.path.abspath(__file__))
_BC = None

ORDINE_STAT = ["hp", "atk", "def", "spa", "spd", "spe"]


def _bc():
    """`scripts/build_catalog.py` come modulo: `scripts/` non è un pacchetto."""
    global _BC
    if _BC is None:
        percorso = os.path.join(RADICE, "scripts", "build_catalog.py")
        spec = importlib.util.spec_from_file_location("build_catalog", percorso)
        _BC = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_BC)
    return _BC


def _nuove_chiavi(prima, dopo):
    return sorted(set(dopo) - set(prima))


def _nuove_forme(prima, dopo):
    fuori = []
    for k, v in dopo.items():
        vecchie = set(((prima.get(k) or {}).get("forms") or {}))
        fuori += [nf for nf in (v.get("forms") or {}) if nf not in vecchie]
    return sorted(fuori)


def _differenze_pokemon(bc, catalogo):
    """Le voci esistenti su cui catalogo e dump non dicono la stessa cosa.

    Base stat, tipi e abilità, confrontati per **slug**. Sono quasi sempre scelte
    curate (le Mega di Champions): si mostrano, non si correggono.
    """
    per_slug = {r["identifier"]: r["id"] for r in bc.leggi("pokemon.csv")}
    stat, tipi, abil = {}, {}, {}
    for r in bc.leggi("pokemon_stats.csv"):
        if r["stat_id"] in bc.STAT_ID:
            stat.setdefault(r["pokemon_id"], {})[bc.STAT_ID[r["stat_id"]]] = int(r["base_stat"])
    tipo_it = {r["type_id"]: r["name"] for r in bc.leggi("type_names.csv")
               if r["local_language_id"] == bc.IT}
    for r in sorted(bc.leggi("pokemon_types.csv"), key=lambda r: int(r["slot"])):
        tipi.setdefault(r["pokemon_id"], []).append(tipo_it.get(r["type_id"], "?"))
    ab_en = {r["ability_id"]: r["name"] for r in bc.leggi("ability_names.csv")
             if r["local_language_id"] == bc.EN}
    for r in bc.leggi("pokemon_abilities.csv"):
        abil.setdefault(r["pokemon_id"], []).append(ab_en.get(r["ability_id"], "?"))

    voci = []
    for chiave, v in catalogo.items():
        voci.append((v.get("name") or chiave, v.get("slug") or chiave, v))
        for nf, f in (v.get("forms") or {}).items():
            voci.append((nf, f.get("slug"), f))

    fuori = []
    for nome, slug, v in voci:
        pid = per_slug.get(slug or "")
        if not pid:
            continue
        if v.get("base_stats") and pid in stat and v["base_stats"] != stat[pid]:
            fuori.append({"voce": nome, "campo": "base stat",
                          "catalogo": "/".join(str(v["base_stats"].get(k, "–")) for k in ORDINE_STAT),
                          "fonte": "/".join(str(stat[pid].get(k, "–")) for k in ORDINE_STAT)})
        if v.get("types") and pid in tipi and v["types"] != tipi[pid]:
            fuori.append({"voce": nome, "campo": "tipi", "catalogo": " · ".join(v["types"]),
                          "fonte": " · ".join(tipi[pid])})
        if v.get("abilities") is not None and pid in abil \
                and sorted(v["abilities"]) != sorted(abil[pid]):
            fuori.append({"voce": nome, "campo": "abilità", "catalogo": ", ".join(v["abilities"]),
                          "fonte": ", ".join(abil[pid])})
    return fuori


def anteprima(aggiorna_fonte=True):
    """Cosa entrerebbe e cosa è diverso. **Non scrive niente.**

    `aggiorna_fonte=True` riscarica i CSV del dump invece di rileggere la copia
    già scaricata: senza, «aggiorna» leggerebbe per sempre la fonte di mesi prima.
    """
    bc = _bc()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            bc.scarica_cache(aggiorna=aggiorna_fonte)
    except Exception as e:
        return {"ok": False, "errore": f"fonte non raggiungibile: {e}"}

    pk_es, _ = bc.base_curata("pokemon", "pokemon_catalog.json")
    mv_es, _ = bc.base_curata("moves", "moves_ma.json", "moves")
    it_es, _ = bc.base_curata("items", "items_ma.json", "items")
    ab_es, _ = bc.base_curata("abilities", "abilities.json", "abilities",
                              avvolto_anche_nel_catalogo=True)
    pk, s_pk = bc.costruisci_pokemon(pk_es)
    mv, s_mv = bc.costruisci_mosse(mv_es)
    ab, _ = bc.costruisci_abilita(ab_es)
    og, _ = bc.costruisci_oggetti(it_es)

    problemi = (bc.intatte("pokemon", pk_es, pk) + bc.intatte("mosse", mv_es, mv)
                + bc.intatte("abilità", ab_es, ab) + bc.intatte("oggetti", it_es, og))
    nuove = {
        "specie": _nuove_chiavi(pk_es, pk),
        "forme": _nuove_forme(pk_es, pk),
        "mosse": _nuove_chiavi(mv_es, mv),
        "abilita": _nuove_chiavi(ab_es, ab),
        "oggetti": _nuove_chiavi(it_es, og),
    }
    return {
        "ok": not problemi,
        "errore": "l'import cambierebbe delle voci curate: non si scrive" if problemi else "",
        "problemi": problemi[:20],
        "nuove": nuove,
        "quante_nuove": sum(len(v) for v in nuove.values()),
        # campi aggiunti a voci esistenti, ammessi da `intatte()`: si dicono
        "slug_aggiunti": s_pk.get("slug_aggiunti", 0),
        "contact_integrati": s_mv.get("contact_integrati", []),
        "differenze": _differenze_pokemon(bc, pk_es),
        "_costruiti": {"pokemon": pk, "moves": mv, "abilities": ab, "items": og},
    }


def applica():
    """Scrive le voci nuove. Rifà l'anteprima sulla fonte appena scaricata.

    ⚠️ Non si fida di un'anteprima arrivata dal browser: la ricalcola, e se nel
    frattempo è cambiato qualcosa vale quella nuova. Le differenze sulle voci
    esistenti non si toccano, per costruzione: `intatte()` lo garantisce.
    """
    from blueprints.pokemon import salva_catalogo, _save_abilities, salva_moveset
    import pokeapi

    a = anteprima(aggiorna_fonte=False)
    if not a["ok"]:
        return {k: v for k, v in a.items() if k != "_costruiti"}
    costruiti = a.pop("_costruiti")
    n = a["nuove"]
    toccati = bool(a["slug_aggiunti"] or a["contact_integrati"])
    if not a["quante_nuove"] and not toccati:
        return dict(a, scritte=0, messaggio="niente di nuovo nella fonte")

    if n["specie"] or n["forme"] or a["slug_aggiunti"]:
        salva_catalogo("pokemon", costruiti["pokemon"])
    if n["mosse"] or a["contact_integrati"]:
        salva_catalogo("moves", costruiti["moves"])
    if n["oggetti"]:
        salva_catalogo("items", costruiti["items"])
    if n["abilita"]:
        _save_abilities({"abilities": costruiti["abilities"]})

    # Le liste mosse delle specie nuove, come il pannello `/pesca`: la chiave del
    # catalogo è lo slug. Le forme no: lì chiave e slug non coincidono, e senza
    # lista la voce dice «nessun elenco mosse», che è vero.
    senza_mosse = list(n["forme"])
    if n["specie"]:
        if pokeapi.file_mancanti():
            senza_mosse += n["specie"]
        else:
            mosse = pokeapi.moveset(n["specie"])
            if mosse:
                salva_moveset(mosse)
            senza_mosse += [s for s in n["specie"] if s not in mosse]
    return dict(a, scritte=a["quante_nuove"], senza_mosse=sorted(senza_mosse))
