"""Pescare una specie dal dump di PokéAPI, pronta da mettere nel catalogo.

È la fonte dell'import da interfaccia (§1.3): si scrive un nome, questo modulo
risponde con una voce **nella stessa forma delle 1026 già in catalogo**, più il suo
moveset. Non scrive niente: la scrittura resta a chi ha già la rete di sicurezza,
cioè `salva_catalogo()`.

**Il dump CSV e non la API REST**, per la stessa ragione di `importa_mosse_specie.py`
e `build_catalog.py`: è la fonte da cui il catalogo è stato costruito, quindi i valori
combaciano invece di divergere per una versione diversa. E il moveset sta tutto in un
file, quindi una specie costa una lettura e non una chiamata di rete.

⚠️ **Le regole di Pokémon Champions, decise da Davide il 21/08/2026**: la voce nuova
porta **tutti e due** gli elenchi di mosse quando il dump li ha — `main` per `pokedex`
e `champions` per `ma`/`mb`. Delle 1323 voci col moveset oggi solo **329** hanno
l'elenco `champions`: dove Champions non conosce la specie l'elenco **non si inventa**,
resta assente, e a schermo compare l'avviso giallo «sono mostrate tutte» che già
esiste. Le IV non c'entrano con questo file: il calcolatore le usa fisse a 31
dappertutto, verificato.

⚠️ **Non inventa mai un campo.** Se il dump non ha il nome italiano di una specie, la
voce esce con quel campo mancante e il chiamante lo vede in `problemi`. Meglio una
lacuna dichiarata di un valore plausibile e falso.
"""
import collections
import csv
import io
import os

RADICE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(RADICE, "data", "cache", "pokeapi_csv")
BASE_CSV = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
UA = {"User-Agent": "personal-hub/1.0 (import specie da interfaccia, uso personale)"}

IT, EN = "8", "9"
VG_CHAMPIONS = "champions"

# I file del dump che servono a costruire una voce completa. `pokemon_moves.csv` è il
# grosso (10 MB): sta in fondo perché è l'unico che si legge filtrando.
FILE_CSV = [
    "pokemon.csv", "pokemon_stats.csv", "stats.csv",
    "pokemon_types.csv", "type_names.csv",
    "pokemon_species_names.csv", "pokemon_abilities.csv", "ability_names.csv",
    "version_groups.csv", "pokemon_move_methods.csv", "move_names.csv",
    "pokemon_forms.csv",
    "pokemon_moves.csv",
]

# Le chiavi delle stat nel catalogo non sono quelle del dump: `spa`/`spd`, non
# `special-attack`/`special-defense`. Cambiarle vorrebbe dire toccare il calcolatore.
STAT_CATALOGO = {
    "hp": "hp", "attack": "atk", "defense": "def",
    "special-attack": "spa", "special-defense": "spd", "speed": "spe",
}

# Cache in memoria delle tabelline piccole, con la firma del file — stesso patto di
# `_MOVESET` e del catalogo in `api_pokemon.py`: un file che può cambiare mentre
# l'app gira non si legge una volta sola.
_TABELLE = {}


def percorso(nome):
    return os.path.join(CACHE, nome)


def file_mancanti():
    """Quali file del dump non ci sono (o sono vuoti). Lista vuota = si può pescare."""
    return [f for f in FILE_CSV
            if not os.path.exists(percorso(f)) or os.path.getsize(percorso(f)) == 0]


def scarica_mancanti(quali=None):
    """Scarica i file del dump che mancano. Torna `(scaricati, byte)`."""
    import requests
    os.makedirs(CACHE, exist_ok=True)
    da_prendere = quali if quali is not None else file_mancanti()
    scaricati, byte = [], 0
    for f in da_prendere:
        r = requests.get(BASE_CSV + f, headers=UA, timeout=180)
        r.raise_for_status()
        with io.open(percorso(f), "wb") as fh:
            fh.write(r.content)
        scaricati.append(f)
        byte += len(r.content)
    return scaricati, byte


def _firma(nome):
    try:
        s = os.stat(percorso(nome))
    except OSError:
        return None
    return (s.st_mtime_ns, s.st_size)


def leggi(nome):
    """Le righe di un CSV del dump, come lista di dizionari. Senza cache."""
    with io.open(percorso(nome), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tabella(nome, costruisci, come=None):
    """Come `leggi()`, ma tiene il risultato di `costruisci` finché il file non cambia.

    ⚠️ `come` distingue **due letture diverse dello stesso file**, e non è un vezzo:
    senza, `_indice_specie()` e `_nomi_specie()` — che leggono tutte e due
    `pokemon_species_names.csv` costruendo strutture opposte — si rubavano la voce di
    cache a vicenda. Il sintomo era muto e sbagliato nel verso peggiore: `Deoxys`
    rispondeva **«nome non trovato nel dump»**, cioè una specie vera dichiarata
    inesistente, e solo per l'ordine delle chiamate.
    """
    chiave = (nome, come)
    firma = _firma(nome)
    voce = _TABELLE.get(chiave)
    if voce and voce["firma"] == firma:
        return voce["dati"]
    dati = costruisci(leggi(nome))
    _TABELLE[chiave] = {"firma": firma, "dati": dati}
    return dati


# ── risoluzione del nome ─────────────────────────────────────────────────────
def _indice_specie():
    """`{nome minuscolo: species_id}` in italiano e in inglese."""
    def costruisci(righe):
        fuori = {}
        for r in righe:
            if r["local_language_id"] in (IT, EN):
                fuori.setdefault(r["name"].lower(), r["pokemon_species_id"])
        return fuori
    return tabella("pokemon_species_names.csv", costruisci, come="nome→specie")


def _indice_pokemon():
    """`{slug: riga}` e `{species_id: [righe]}` da pokemon.csv."""
    def costruisci(righe):
        per_slug = {r["identifier"]: r for r in righe}
        per_specie = collections.defaultdict(list)
        for r in righe:
            per_specie[r["species_id"]].append(r)
        return {"per_slug": per_slug, "per_specie": dict(per_specie)}
    return tabella("pokemon.csv", costruisci)


def risolvi(nome):
    """Da un nome qualunque allo slug del dump, o `None`.

    Accetta lo slug (`incineroar`), il nome inglese e il nome italiano. ⚠️ Quando un
    nome di specie ha più righe in `pokemon.csv` — le forme — si prende quella
    **di default** (`is_default`), che è la specie base: importare `Deoxys` deve dare
    Deoxys, non una delle sue forme a caso.
    """
    testo = (nome or "").strip().lower()
    if not testo:
        return None
    indice = _indice_pokemon()
    if testo in indice["per_slug"]:
        return testo
    slug_possibile = testo.replace(" ", "-")
    if slug_possibile in indice["per_slug"]:
        return slug_possibile
    specie = _indice_specie().get(testo)
    if not specie:
        return None
    righe = indice["per_specie"].get(specie) or []
    predefinita = next((r for r in righe if r.get("is_default") == "1"), None)
    return (predefinita or (righe[0] if righe else {})).get("identifier")


def _forme_per_pokemon():
    """`{pokemon_id: form_identifier}` — vuoto quando la voce non è una forma."""
    return tabella("pokemon_forms.csv", lambda righe: {
        r["pokemon_id"]: r.get("form_identifier") or "" for r in righe})


# ── i pezzi di una voce ──────────────────────────────────────────────────────
def _stat_per_pokemon():
    ordine = tabella("stats.csv", lambda righe: {r["id"]: r["identifier"] for r in righe})

    def costruisci(righe):
        fuori = collections.defaultdict(dict)
        for r in righe:
            chiave = STAT_CATALOGO.get(ordine.get(r["stat_id"]))
            if chiave:
                fuori[r["pokemon_id"]][chiave] = int(r["base_stat"])
        return dict(fuori)
    return tabella("pokemon_stats.csv", costruisci)


def _tipi_per_pokemon():
    nomi = tabella("type_names.csv", lambda righe: {
        r["type_id"]: r["name"] for r in righe if r["local_language_id"] == IT})

    def costruisci(righe):
        fuori = collections.defaultdict(list)
        for r in sorted(righe, key=lambda x: int(x["slot"])):
            nome = nomi.get(r["type_id"])
            if nome:
                fuori[r["pokemon_id"]].append(nome)
        return dict(fuori)
    return tabella("pokemon_types.csv", costruisci)


def _abilita_per_pokemon():
    # ⚠️ In **inglese**, ed è voluto: il catalogo cita le abilità col nome inglese
    # mentre le chiavi di `abilities.json` sono italiane. Scriverle in italiano qui
    # romperebbe `risolviChiave()` a valle — è la trappola per cui Kingdra sotto
    # pioggia restava a 105 invece di 210.
    nomi = tabella("ability_names.csv", lambda righe: {
        r["ability_id"]: r["name"] for r in righe if r["local_language_id"] == EN})

    def costruisci(righe):
        fuori = collections.defaultdict(list)
        for r in sorted(righe, key=lambda x: int(x["slot"])):
            nome = nomi.get(r["ability_id"])
            if nome and nome not in fuori[r["pokemon_id"]]:
                fuori[r["pokemon_id"]].append(nome)
        return dict(fuori)
    return tabella("pokemon_abilities.csv", costruisci)


def _nomi_specie(species_id):
    def costruisci(righe):
        fuori = collections.defaultdict(dict)
        for r in righe:
            if r["local_language_id"] in (IT, EN):
                fuori[r["pokemon_species_id"]][r["local_language_id"]] = r["name"]
        return dict(fuori)
    voce = tabella("pokemon_species_names.csv", costruisci,
                   come="specie→nomi").get(species_id) or {}
    return voce.get(IT), voce.get(EN)


def _nomi_mosse():
    """`{move_id: nome}` in inglese, **riallineato ai nomi del catalogo**.

    ⚠️ Senza questo riallineamento una mossa che il catalogo non riconosce sparirebbe
    dalla tendina **in silenzio**: è la stessa riconciliazione di
    `importa_mosse_specie.py`, e vale lo stesso criterio — si accetta solo quando,
    ignorando trattini e spazi, il nome corrisponde a **una sola** chiave del catalogo.
    """
    import json
    grezzi = tabella("move_names.csv", lambda righe: {
        r["move_id"]: r["name"] for r in righe if r["local_language_id"] == EN})
    try:
        with io.open(os.path.join(RADICE, "data", "catalog", "moves.json"),
                     encoding="utf-8") as f:
            catalogo = json.load(f) or {}
    except Exception:
        return grezzi
    if not catalogo:
        return grezzi

    def piatto(s):
        return s.replace("-", " ").replace("  ", " ").strip().lower()

    per_forma = collections.defaultdict(list)
    for chiave in catalogo:
        per_forma[piatto(chiave)].append(chiave)
    fuori = {}
    for mid, nome in grezzi.items():
        if nome in catalogo:
            fuori[mid] = nome
            continue
        candidati = per_forma.get(piatto(nome)) or []
        fuori[mid] = candidati[0] if len(candidati) == 1 else nome
    return fuori


def moveset(slug_voluti):
    """`{slug: {"main": {...}, "champions": {...}}}` per gli slug chiesti.

    Un solo passaggio su `pokemon_moves.csv` (10 MB) **per quanti slug si vogliono**:
    è la ragione per cui l'import in blocco prende una lista e non un nome alla volta.
    """
    indice = _indice_pokemon()["per_slug"]
    voluti = {}
    for slug in slug_voluti:
        riga = indice.get(slug)
        if riga:
            voluti[riga["id"]] = slug
    if not voluti:
        return {}

    metodi = tabella("pokemon_move_methods.csv",
                     lambda righe: {r["id"]: r["identifier"] for r in righe})
    gruppi = tabella("version_groups.csv", lambda righe: {
        r["id"]: (r["identifier"], int(r["order"])) for r in righe})
    id_champions = next((i for i, (nome, _) in gruppi.items()
                         if nome == VG_CHAMPIONS), None)
    nomi = _nomi_mosse()

    per_slug = collections.defaultdict(lambda: collections.defaultdict(dict))
    with io.open(percorso("pokemon_moves.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            slug = voluti.get(r["pokemon_id"])
            if not slug:
                continue
            nome = nomi.get(r["move_id"])
            metodo = metodi.get(r["pokemon_move_method_id"])
            if not nome or not metodo:
                continue
            # Il livello si scrive sempre, `0` compreso: nel dump vuol dire
            # "all'evoluzione o dal ricordamosse", che è un'informazione, non un buco.
            if metodo == "level-up" and r["level"].isdigit():
                metodo = f"level-up:{r['level']}"
            elenco = per_slug[slug][r["version_group_id"]].setdefault(nome, [])
            if metodo not in elenco:
                elenco.append(metodo)

    fuori = {}
    for slug, per_vg in per_slug.items():
        voce = {"slug": slug}
        candidati = [(gruppi[v][1], v) for v in per_vg
                     if v in gruppi and v != id_champions]
        if candidati:
            _, vg = max(candidati)          # il version group più recente
            voce["main"] = {"vg": gruppi[vg][0],
                            "moves": {n: ",".join(m) for n, m in sorted(per_vg[vg].items())}}
        if id_champions in per_vg:
            voce["champions"] = {
                "moves": {n: ",".join(m)
                          for n, m in sorted(per_vg[id_champions].items())}}
        if len(voce) > 1:
            fuori[slug] = voce
    return fuori


def pesca(nomi, con_mosse=True):
    """`(voci, mosse, problemi)` per i nomi chiesti. **Non scrive niente.**

    `voci` è `{chiave_catalogo: voce}` nella forma delle 1026 già in catalogo;
    `mosse` è `{chiave_catalogo: {...}}` pronto per `pokemon_moves.json`;
    `problemi` è la lista di ciò che non si è potuto fare, con il perché — e va
    mostrata a schermo, non ingoiata.
    """
    mancanti = file_mancanti()
    if mancanti:
        return {}, {}, [{"nome": None, "problema": "fonte incompleta",
                         "dettaglio": ", ".join(mancanti)}]

    indice = _indice_pokemon()["per_slug"]
    stat = _stat_per_pokemon()
    tipi = _tipi_per_pokemon()
    abilita = _abilita_per_pokemon()

    voci, problemi, slug_per_chiave = {}, [], {}
    for nome in nomi:
        slug = risolvi(nome)
        if not slug:
            problemi.append({"nome": nome, "problema": "nome non trovato nel dump",
                             "dettaglio": "né come slug, né come nome italiano o inglese"})
            continue
        riga = indice[slug]
        pid = riga["id"]
        # ⚠️ **Solo le specie di default.** Non è una restrizione prudenziale: le 1025
        # voci di primo livello del catalogo hanno **tutte** `is_default=1`, e le 317
        # forme — Mega, Gigantamax, regionali — stanno **annidate** dentro `forms`.
        # Importare una forma al primo livello creerebbe un doppione che nessuno
        # noterebbe, con due voci per lo stesso Pokémon e due verità sulle sue stat.
        if riga.get("is_default") != "1":
            problemi.append({
                "nome": nome, "problema": "è una forma, non una specie base",
                "dettaglio": f"nel catalogo le forme stanno annidate in `forms` della "
                             f"specie: `{slug}` va aggiunta dall'editor, non da qui"})
            continue
        nome_it, nome_en = _nomi_specie(riga["species_id"])
        voce = {
            "name": nome_en or slug,
            "types": tipi.get(pid) or [],
            "abilities": abilita.get(pid) or [],
            "base_stats": stat.get(pid) or {},
            "slug": slug,
        }
        # ⚠️ I nomi si scrivono solo se ci sono: `nome_it` mancante è una lacuna da
        # dichiarare, non un buco da riempire col nome inglese fingendo sia italiano.
        if nome_it:
            voce["nome_it"] = nome_it
        if nome_en:
            voce["nome_en"] = nome_en
        # ⚠️ Il dump chiama queste voci col nome della **specie** («Basculegion»),
        # il catalogo con la convenzione sua («Basculegion (Male)»). Sono 6 casi su
        # 1025, e il nome non lo aggiusto io: comporlo vorrebbe dire inventare una
        # regola di scrittura che il dump non ha. Si dichiara e lo si corregge
        # dall'editor, dove rinominare è un'operazione prevista.
        forma = _forme_per_pokemon().get(pid) or ""
        if forma:
            problemi.append({
                "nome": nome, "problema": "il nome potrebbe volere la forma fra parentesi",
                "dettaglio": f"il dump la chiama «{voce['name']}» e la marca come forma "
                             f"«{forma}»; per casi simili il catalogo scrive "
                             f"«{voce['name']} ({forma.title()})». Da correggere a mano "
                             f"se serve — la voce entra col nome del dump"})
        vuoti = [c for c in ("types", "abilities", "base_stats") if not voce[c]]
        if not nome_it:
            vuoti.append("nome_it")
        if not nome_en:
            vuoti.append("nome_en")
        if vuoti:
            problemi.append({"nome": nome, "problema": "campi che il dump non ha",
                             "dettaglio": ", ".join(vuoti)})
        # La chiave del catalogo è lo slug: è così per 1021 voci su 1026, ed è
        # l'identità della voce — quella che i filtri delle regulation e i team
        # salvati citano, e che non si rinomina più.
        voci[slug] = voce
        slug_per_chiave[slug] = slug

    mosse = {}
    if con_mosse and slug_per_chiave:
        per_slug = moveset(list(slug_per_chiave.values()))
        for chiave, slug in slug_per_chiave.items():
            voce = per_slug.get(slug)
            if voce:
                mosse[chiave] = voce
            else:
                problemi.append({
                    "nome": chiave, "problema": "nessuna mossa nel dump",
                    "dettaglio": "la voce entra lo stesso: a schermo comparirà "
                                 "l'avviso «sono mostrate tutte»"})
        for chiave, voce in mosse.items():
            if "champions" not in voce:
                problemi.append({
                    "nome": chiave, "problema": "non è in Pokémon Champions",
                    "dettaglio": "ha solo l'elenco `main`: in ma/mb comparirà "
                                 "l'avviso giallo invece di un elenco inventato"})
    return voci, mosse, problemi
