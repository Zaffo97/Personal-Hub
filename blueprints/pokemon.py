import json
import os
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   jsonify, session)
from extensions import (get_db, login_required, _i, nome_vis, categorie,
                        ambito_utente, utente_id, e_admin)
from data import (
    DATA_DIR,
    applica_collegamenti,
    collega_mega,
    regulation_default,
    REG_MA_ROSTER,
    MEGA_EVOLUTIONS_MA,
    NATURES,
    NATURE_EFFECTS,
    CHAMPIONS_BST,
)
import log_hub

# Le abilità stanno nel catalogo, come gli altri tre database. Il vecchio
# data/abilities.json resta leggibile come fallback finché non è dismesso.
ABILITIES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "catalog", "abilities.json")
ABILITIES_FILE_LEGACY = os.path.join(os.path.dirname(__file__), "..", "data", "abilities.json")

def load_abilities():
    for percorso in (ABILITIES_FILE, ABILITIES_FILE_LEGACY):
        try:
            with open(percorso, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return {"abilities": {}}

ABILITIES_ARCHIVE_PREFIX = "abilities_"
ABILITIES_PRESAVE = "abilities_pre-salvataggio.json"


def _archive_dir():
    d = os.path.join(DATA_DIR, "archive")
    os.makedirs(d, exist_ok=True)
    return d


def _save_abilities(data):
    """Scrive data/abilities.json, tenendo da parte la versione precedente.

    Il file regge 408 abilità, 56 delle quali con il blocco `effect` da cui dipende
    il calcolatore danno: un salvataggio sbagliato dall'editor le azzerava senza
    lasciare nulla dietro. La copia è a scorrimento, sempre lo stesso nome, così
    non riempie la cartella a ogni salvataggio.
    """
    path = os.path.normpath(ABILITIES_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                precedente = f.read()
            with open(os.path.join(_archive_dir(), ABILITIES_PRESAVE), "w", encoding="utf-8") as f:
                f.write(precedente)
        except Exception:
            pass  # il backup non deve mai impedire il salvataggio

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# CATALOGO: il database di default, unico. Le regulation non contengono più dati,
# solo elenchi di nomi che puntano qui (data/regulations/<id>.json).
# `null` in un elenco significa "tutte le voci del catalogo".
# ---------------------------------------------------------------------------
CATALOG_DIR = os.path.join(DATA_DIR, "catalog")


DB_CATALOGO = ("pokemon", "moves", "abilities", "items")

# Le abilità sono avvolte in {"abilities": ...} perché è la forma che l'editor
# abilità, l'archivio e il ripristino usano da sempre. Gli altri tre sono piatti.
DB_AVVOLTI = {"abilities": "abilities"}


def load_catalog(nome):
    """Legge data/catalog/<nome>.json — pokemon | moves | abilities | items."""
    try:
        with open(os.path.join(CATALOG_DIR, f"{nome}.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def voci_catalogo(db):
    """Le voci di un database del catalogo, sempre come dizionario piatto."""
    dati = load_catalog(db)
    chiave = DB_AVVOLTI.get(db)
    return dati.get(chiave, {}) if chiave else dati


# ---------------------------------------------------------------------------
# MOVESET: quali mosse ogni voce può imparare (data/catalog/pokemon_moves.json,
# scritto da scripts/importa_mosse_specie.py). Sta fuori dal catalogo perché
# pesa 2,7 MB e il catalogo finisce nel payload del browser.
#
# Ogni voce ha DUE elenchi, e non coincidono: `main` sono i giochi principali,
# `champions` è il moveset di Pokémon Champions — Incineroar lì non ha Knock Off.
# Quale dei due usare lo dice la regulation, col campo `moveset` in regulations.json.
# ---------------------------------------------------------------------------
MOVESET_FILE = os.path.join(CATALOG_DIR, "pokemon_moves.json")
MOVESET_DEFAULT = "main"

# Cache in memoria con l'mtime del file: 2,7 MB riletti a ogni richiesta sarebbero
# sprecati, ma il file lo riscrive uno script fuori dal processo, quindi rileggerlo
# quando cambia evita di dover riavviare l'app dopo un import.
_MOVESET = {"mtime": None, "voci": {}, "indice": {}}


def load_moveset():
    """`(voci, indice)` del moveset. L'indice risolve i nomi visualizzati."""
    try:
        mtime = os.path.getmtime(MOVESET_FILE)
    except OSError:
        return {}, {}
    if _MOVESET["mtime"] != mtime:
        try:
            with open(MOVESET_FILE, encoding="utf-8") as f:
                voci = (json.load(f) or {}).get("voci") or {}
        except Exception:
            return {}, {}
        # Le chiavi del moveset sono quelle del catalogo (chiave per le specie, nome
        # della forma per le forme annidate): l'indice aggiunge i nomi visualizzati,
        # perché roster e team parlano di "Incineroar", non di "incineroar".
        indice = {}
        catalogo = load_catalog("pokemon")
        for chiave, voce in catalogo.items():
            if chiave in voci:
                for n in (chiave, voce.get("name"), voce.get("nome_it"), voce.get("nome_en")):
                    if n:
                        indice.setdefault(n.lower(), chiave)
            for nome_forma, forma in (voce.get("forms") or {}).items():
                if nome_forma in voci:
                    for n in (nome_forma, forma.get("nome_it"), forma.get("nome_en")):
                        if n:
                            indice.setdefault(n.lower(), nome_forma)
        _MOVESET.update(mtime=mtime, voci=voci, indice=indice)
    return _MOVESET["voci"], _MOVESET["indice"]


def sorgente_moveset(reg):
    """Quale dei due elenchi usa la regulation: `main` o `champions`."""
    return (reg or {}).get("moveset") or MOVESET_DEFAULT


def sorgenti_moveset():
    """Gli elenchi che il moveset contiene davvero, `main` per primo.

    Letti dal file invece che scritti a mano: il giorno che un import aggiunge un
    version group, la tendina della regulation lo offre senza toccare il codice.
    ⚠️ E una regulation che chiede una sorgente inesistente non darebbe errore —
    `mosse_legali()` troverebbe `None` e mostrerebbe **tutte** le mosse: e' per
    questo che la creazione e il salvataggio la validano contro questo elenco.
    """
    voci, _ = load_moveset()
    # ⚠️ Non «tutte le chiavi tranne `slug`»: le 32 forme Gigantamax hanno anche
    # `eredita_da`, che dice **da chi** copiano le mosse e non e' una sorgente. Una
    # sorgente e' un blocco con dentro `moves`, ed e' questa la forma che
    # `mosse_legali()` legge — cosi' l'elenco non si sporca al prossimo campo nuovo.
    trovate = {chiave for voce in voci.values() for chiave, valore in voce.items()
               if isinstance(valore, dict) and "moves" in valore}
    trovate.discard(MOVESET_DEFAULT)
    return [MOVESET_DEFAULT] + sorted(trovate)


def mosse_legali(nome, reg):
    """Mosse che `nome` può imparare nella regulation.

    Restituisce `(elenco, sorgente)`. **`elenco` è `None` quando non lo sappiamo** —
    le forme inventate non stanno su PokéAPI, e le specie arrivate in Champions con la
    versione 1.2.0 non stanno nel suo moveset (Pawmot ce l'ha dal 14/09/2026, integrato
    da Bulbapedia). `None` e lista vuota sono due cose diverse: chi chiama
    deve poter mostrare tutte le mosse invece di non mostrarne nessuna.
    """
    voci, indice = load_moveset()
    sorgente = sorgente_moveset(reg)
    chiave = indice.get((nome or "").lower())
    if not chiave:
        return None, sorgente
    elenco = (voci.get(chiave) or {}).get(sorgente)
    if not elenco:
        return None, sorgente
    return sorted(elenco.get("moves") or {}), sorgente


def salva_catalogo(db, voci):
    """Scrive un database del catalogo, tenendo da parte la versione precedente.

    Stessa rete di sicurezza delle abilità: una copia a scorrimento prima di ogni
    salvataggio, così un errore nell'editor non azzera 1032 Pokémon o 921 mosse.
    """
    percorso = os.path.join(CATALOG_DIR, f"{db}.json")
    os.makedirs(CATALOG_DIR, exist_ok=True)
    if os.path.exists(percorso):
        try:
            with open(percorso, encoding="utf-8") as f:
                precedente = f.read()
            copia = os.path.join(_archive_dir(), f"catalog_{db}_pre-salvataggio.json")
            with open(copia, "w", encoding="utf-8") as f:
                f.write(precedente)
        except Exception:
            pass  # il backup non deve mai impedire il salvataggio

    chiave = DB_AVVOLTI.get(db)
    dati = {chiave: voci} if chiave else voci
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)


def _riga_indice(db, nome, voce):
    """Riga compatta per la tabella dell'editor: evita di mandare al browser
    449 KB di catalogo quando servono quattro campi per riga.

    `nome` è quello che si **legge**, nella lingua attiva; `chiave` è l'identità
    della voce e non cambia mai — è quella che il template usa per aprire, salvare
    ed eliminare, ed è quella che si scrive nel JSON.
    """
    vis = nome_vis(voce, nome)
    if db == "pokemon":
        bs = voce.get("base_stats") or {}
        return {"nome": vis, "chiave": nome,
                "info": " · ".join(voce.get("types") or []),
                "numero": sum(bs.values()) if bs else 0,
                "extra": f"{len(voce.get('forms') or {})} forme" if voce.get("forms") else ""}
    if db == "moves":
        return {"nome": vis, "chiave": nome,
                "info": f"{voce.get('type', '')} · {voce.get('category', '')}",
                "numero": voce.get("bp") or 0,
                "extra": ", ".join(voce.get("flags") or [])}
    # La categoria si legge tradotta, ma il **valore** resta la chiave: `effect.type`
    # nella colonna extra invece no, e' un valore tecnico che si legge nel JSON.
    if db == "abilities":
        fx = (voce.get("effect") or {}).get("type", "none")
        cat = voce.get("category", "")
        return {"nome": vis, "chiave": nome,
                "info": categorie("abilities").get(cat, cat),
                "numero": 0, "extra": "" if fx == "none" else f"● {fx}"}
    cat = voce.get("category", "")
    return {"nome": vis, "chiave": nome, "info": categorie("items").get(cat, cat),
            "numero": voce.get("modifier") or 0,
            "extra": voce.get("categoria_pokeapi", "")}


def _load_filtro(reg):
    """Elenchi di nomi della regulation, o None se non è ancora migrata."""
    percorso = reg.get("filter_file")
    if not percorso:
        return None
    try:
        with open(os.path.join(DATA_DIR, percorso), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _filtra(catalogo, nomi, override=None):
    """Sottoinsieme del catalogo. `nomi` None = tutto. `override` sovrascrive campi."""
    fuori = dict(catalogo) if nomi is None else {n: catalogo[n] for n in nomi if n in catalogo}
    for chiave, valori in (override or {}).items():
        if chiave in fuori:
            fuori[chiave] = {**fuori[chiave], **valori}
    return fuori


def _nomi_catalogo_pokemon(catalogo):
    """Tutti i nomi visualizzabili: specie più forme annidate."""
    nomi = []
    for voce in catalogo.values():
        nomi.append(voce.get("name") or "")
        nomi.extend(voce.get("forms") or {})
    return sorted(n for n in nomi if n)


bp = Blueprint("pokemon", __name__, url_prefix="/pokemon")


# --- Chi può toccare i dati condivisi ---------------------------------------
# Il permesso di sezione decide **se** vedi Pokémon, non **cosa** puoi scriverci:
# catalogo, mosse, oggetti, abilità, roster e regulation sono un dato solo per
# tutti gli utenti, e finora chiunque avesse la sezione poteva riscriverlo.
#
# ⚠️ L'elenco qui sotto è quello del **permesso**, non del divieto, ed è la scelta
# che conta. Una lista di route vietate fallirebbe **aperta**: la prossima route di
# scrittura che qualcuno aggiunge nascerebbe libera per tutti, e la dimenticanza non
# darebbe nessun segnale. Così invece una route nuova nasce riservata agli
# amministratori, e chi la vuole aperta deve scriverlo qui — dove la dimenticanza si
# vede subito, perché la pagina non si apre.
#
# I nomi sono quelli delle viste (`request.endpoint` senza il prefisso `pokemon.`).
APERTE_A_TUTTI = {
    "pokemon",               # /pokemon — l'elenco dei team
    "calcolatori",           # /pokemon/calcolatori
    "team_new",              # creare, modificare ed eliminare i propri team
    "team_edit",
    "team_delete",
    # GET: la tendina delle regulation nel team builder (team_form.html) e in
    # regulation_editor. Legge e basta — il salvataggio è `api_regulations_save`.
    "api_regulations_list",
}

# Le viste che rispondono in JSON a una `fetch()`: a loro va detto 403, non un
# redirect a una pagina HTML, che nel browser diventerebbe un errore di parsing
# invece di un messaggio. Le altre stanno tutte sotto un path con `/api/`; queste
# tre no, e sono l'unico caso — stesso ragionamento del controllo in `app.py`.
RISPONDONO_JSON = {"abilities_archives", "catalog_archives", "roster_archives"}


@bp.before_request
def _solo_admin_sugli_editor():
    """Il controllo sta qui e non sulle singole viste: una route nuova nasce protetta."""
    if "username" not in session:
        return None                     # non loggato: ci pensa `login_required`
    if request.endpoint is None:
        return None                     # 404 dentro /pokemon/*: lascia fare a Flask
    vista = request.endpoint.split(".", 1)[-1]
    if vista in APERTE_A_TUTTI or session.get("role") == "admin":
        return None
    if vista in RISPONDONO_JSON or "/api/" in request.path:
        return jsonify({"ok": False, "error": "Serve un account amministratore."}), 403
    flash("Serve un account amministratore.", "error")
    return redirect(url_for("pokemon.pokemon"))


def _list_regulation_files():
    reg_path = os.path.join(DATA_DIR, "regulations.json")
    try:
        with open(reg_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return [
            {
                "id": "ma",
                "label": "Regulation MA",
                "roster_file": "roster_ma.json",
                "moves_file": "moves_ma.json",
                "items_file": "items_ma.json"
            }
        ]


def _save_regulations(regs):
    reg_path = os.path.join(DATA_DIR, "regulations.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(regs, f, ensure_ascii=False, indent=2)


def _load_roster(reg):
    """Nomi Pokémon della regulation: dal filtro se migrata, altrimenti dal file vecchio."""
    filtro = _load_filtro(reg)
    if filtro is not None:
        nomi = filtro.get("pokemon")
        if nomi is None:                      # nessun filtro: tutto il catalogo
            return _nomi_catalogo_pokemon(load_catalog("pokemon"))
        return sorted(nomi)
    try:
        with open(os.path.join(DATA_DIR, reg["roster_file"]), encoding="utf-8") as f:
            return sorted(json.load(f).get("pokemon", []))
    except Exception:
        return sorted(REG_MA_ROSTER)


def _load_mega_map(reg):
    """mega_map della regulation: dal filtro se migrata, altrimenti dal roster file."""
    filtro = _load_filtro(reg)
    if filtro is not None:
        return filtro.get("mega_map") or {}
    try:
        with open(os.path.join(DATA_DIR, reg["roster_file"]), encoding="utf-8") as f:
            return json.load(f).get("mega_map", {})
    except Exception:
        return {}


def _salva_filtro(reg, campo, nomi):
    """Aggiorna l'elenco di nomi di una regulation migrata. True se ha scritto."""
    percorso_rel = reg.get("filter_file")
    if not percorso_rel:
        return False
    percorso = os.path.join(DATA_DIR, percorso_rel)
    try:
        with open(percorso, encoding="utf-8") as f:
            filtro = json.load(f)
    except Exception:
        return False
    filtro[campo] = sorted(nomi) if nomi is not None else None
    filtro["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(filtro, f, ensure_ascii=False, indent=2)
    return True


def _pokemon_regulation(reg_id=None):
    """Catalogo Pokémon ristretto alla regulation, per CHAMPIONS_BST del calcolatore.

    Serve a non iniettare 449 KB di catalogo in ogni pagina: con Regulation MA la
    pagina resta piccola, con Pokedex è grande perché deve esserlo.
    """
    catalogo = load_catalog("pokemon")
    if not catalogo:
        return CHAMPIONS_BST
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == (reg_id or regulation_default())), regs[0])
    filtro = _load_filtro(reg)
    if filtro is None or filtro.get("pokemon") is None:
        return catalogo
    voluti = {n.lower() for n in filtro["pokemon"]}
    fuori = {}
    for chiave, voce in catalogo.items():
        etichette = {chiave.lower(), (voce.get("name") or "").lower(),
                     (voce.get("slug") or "").lower()}
        forme = {nf: vf for nf, vf in (voce.get("forms") or {}).items()
                 if voluti & {nf.lower(), (vf.get("slug") or "").lower()}}
        if etichette & voluti or forme:
            nuova = dict(voce)
            # tiene tutte le forme se la specie e' nel roster: mega e forme
            # alternative vanno comunque risolte dal calcolatore
            if forme and not (etichette & voluti):
                nuova["forms"] = forme
            fuori[chiave] = nuova
    return fuori or catalogo


def _nomi_visualizzati(catalogo):
    """{nome del catalogo: nome nella lingua attiva} per specie e forme annidate.

    Serve alle tendine renderizzate dal server: la casella deve mostrare (e ricevere)
    il nome tradotto, mentre a indicizzare i dati resta la chiave. `_INDICE` in
    api_pokemon.py conosce entrambe le lingue, quindi il nome tradotto risolve.
    """
    nomi = {}
    for chiave, voce in (catalogo or {}).items():
        etichetta = voce.get("name") or chiave
        visualizzato = nome_vis(voce, etichetta)
        nomi[etichetta] = visualizzato
        nomi[chiave] = visualizzato
        for nome_forma, forma in (voce.get("forms") or {}).items():
            nomi[nome_forma] = nome_vis(forma, nome_forma)
    return nomi


def _build_full_roster(roster, mega_map, catalogo=None):
    """
    Costruisce la lista completa per la combobox:
    roster base + tutte le mega da mega_map + tutte le forme dal catalogo.
    Deduplicata e ordinata.
    """
    all_names = set(roster)

    # Aggiungi tutte le mega dalla mega_map
    for mega_list in mega_map.values():
        for m in mega_list:
            all_names.add(m)

    # Aggiungi tutte le forme (forms) presenti nel catalogo della regulation
    for poke_data in (catalogo or CHAMPIONS_BST).values():
        for form_name in poke_data.get("forms", {}).keys():
            all_names.add(form_name)

    return sorted(all_names)


def _dal_catalogo(reg_id, tipo, chiave_uscita):
    """Catalogo filtrato dalla regulation, o None se la regulation non è migrata."""
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    filtro = _load_filtro(reg)
    if filtro is None:
        return None
    catalogo = load_catalog(tipo)
    if not catalogo:
        return None
    override = (filtro.get("overrides") or {}).get(tipo)
    return {
        chiave_uscita: _filtra(catalogo, filtro.get(chiave_uscita), override),
        "regulation": reg.get("label", reg_id),
        "last_updated": filtro.get("last_updated", ""),
    }


def load_moves(reg_id=None):
    reg_id = reg_id or regulation_default()
    dal_catalogo = _dal_catalogo(reg_id, "moves", "moves")
    if dal_catalogo is not None:
        return dal_catalogo
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    try:
        with open(os.path.join(DATA_DIR, reg["moves_file"]), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"moves": {}, "regulation": reg["label"], "last_updated": ""}


def load_items(reg_id=None):
    reg_id = reg_id or regulation_default()
    dal_catalogo = _dal_catalogo(reg_id, "items", "items")
    if dal_catalogo is not None:
        return dal_catalogo
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    try:
        with open(os.path.join(DATA_DIR, reg["items_file"]), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": {}, "regulation": reg["label"]}


def _team_upsert(tid=None):
    f = request.form
    db = get_db()
    vals = (
        f.get("team_name", "Nuovo Team"),
        f.get("team_format", "VGC Doubles"),
        f.get("team_record", ""),
        f.get("team_description", ""),
        f.get("team_notes", ""),
        f.get("regulation_id") or regulation_default(),
    )

    if tid:
        # ⚠️ Il proprietario **non** si riscrive in aggiornamento: un admin che
        # corregge il team di un altro non se lo intesta.
        cond, par = ambito_utente()
        cur = db.execute(
            "UPDATE teams SET name=?,format=?,record=?,description=?,notes=?,regulation_id=? "
            f"WHERE id=? AND {cond}",
            vals + (tid,) + tuple(par)
        )
        if cur.rowcount == 0:
            # Il team non è di chi sta salvando. Si esce **prima** di toccare i
            # membri: senza questo ritorno il DELETE qui sotto svuoterebbe la
            # squadra di un altro, e l'UPDATE a vuoto non avrebbe detto niente.
            db.close()
            return None
    else:
        cur = db.execute(
            "INSERT INTO teams(name,format,record,description,notes,regulation_id,user_id) "
            "VALUES(?,?,?,?,?,?,?)",
            vals + (utente_id(),)
        )
        tid = cur.lastrowid

    db.execute("DELETE FROM team_members WHERE team_id=?", (tid,))

    for i in range(6):
        pk = f.get(f"pk_{i}", "").strip()
        if not pk:
            continue

        db.execute("""
            INSERT INTO team_members
            (team_id,slot,pokemon,mechanic_type,mechanic_value,
             nature,ability,held_item,
             move1,move2,move3,move4,
             sp_hp,sp_atk,sp_def,sp_spatk,sp_spdef,sp_spe,
             sprite_url)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            tid, i, pk,
            f.get(f"mechanic_type_{i}", ""), f.get(f"mechanic_value_{i}", ""),
            f.get(f"nature_{i}", ""), f.get(f"ability_{i}", ""),
            f.get(f"item_{i}", ""),
            f.get(f"move1_{i}", ""), f.get(f"move2_{i}", ""),
            f.get(f"move3_{i}", ""), f.get(f"move4_{i}", ""),
            _i(f.get(f"sp_hp_{i}")), _i(f.get(f"sp_atk_{i}")),
            _i(f.get(f"sp_def_{i}")), _i(f.get(f"sp_spatk_{i}")),
            _i(f.get(f"sp_spdef_{i}")), _i(f.get(f"sp_spe_{i}")),
            f.get(f"sprite_url_{i}", "") or None
        ))

    db.commit()
    db.close()
    return tid


# ---------------------------------------------------------------------------
# ABILITIES: editor + API
# ---------------------------------------------------------------------------
@bp.route("/abilita", methods=["GET", "POST"])
@login_required
def abilities_editor():
    if request.method == "POST":
        try:
            raw = request.form.get("abilities_json", "")
            data = json.loads(raw)
            if "abilities" not in data:
                flash("JSON non valido: manca la chiave 'abilities'", "error")
                return redirect(url_for("pokemon.abilities_editor"))
            if not isinstance(data["abilities"], dict) or not data["abilities"]:
                # Un POST con 'abilities' vuoto o non-oggetto cancellerebbe tutto.
                flash("JSON non valido: 'abilities' deve essere un oggetto non vuoto", "error")
                return redirect(url_for("pokemon.abilities_editor"))

            prima = len(load_abilities().get("abilities", {}))
            dopo = len(data["abilities"])
            _save_abilities(data)
            delta = dopo - prima
            nota = f" ({delta:+d} rispetto a prima)" if delta else ""
            flash(f"✅ Abilità aggiornate: {dopo} voci{nota}", "success")
        except json.JSONDecodeError as e:
            flash(f"❌ Errore JSON: {e}", "error")
        return redirect(url_for("pokemon.abilities_editor"))

    ab_data = load_abilities()
    return render_template(
        "abilities_editor.html",
        abilities=ab_data.get("abilities", {}),
        abilities_json=json.dumps(ab_data, ensure_ascii=False, indent=2)
    )


@bp.route("/abilita/archive", methods=["POST"])
@login_required
def abilities_archive():
    try:
        data = load_abilities()
        nome = f"{ABILITIES_ARCHIVE_PREFIX}{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        with open(os.path.join(_archive_dir(), nome), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        flash(f"📦 Abilità archiviate come {nome} ({len(data.get('abilities', {}))} voci)", "success")
    except Exception as e:
        flash(f"❌ Errore archivio abilità: {e}", "error")
    return redirect(url_for("pokemon.abilities_editor"))


@bp.route("/abilita/archives")
@login_required
def abilities_archives():
    """Elenco degli archivi abilità, più recenti prima."""
    d = _archive_dir()
    archivi = []
    for fn in sorted(os.listdir(d), reverse=True):
        if not fn.startswith(ABILITIES_ARCHIVE_PREFIX) or not fn.endswith(".json"):
            continue
        percorso = os.path.join(d, fn)
        try:
            with open(percorso, encoding="utf-8") as f:
                contenuto = json.load(f)
            archivi.append({
                "filename": fn,
                "count": len(contenuto.get("abilities", {})),
                "modificato": datetime.fromtimestamp(
                    os.path.getmtime(percorso)).strftime("%d/%m/%Y %H:%M"),
                # la copia a scorrimento e' quella da cui recuperare dopo un salvataggio sbagliato
                "automatico": fn == ABILITIES_PRESAVE,
            })
        except Exception:
            pass
    return json.dumps(archivi), 200, {"Content-Type": "application/json"}


@bp.route("/abilita/restore/<path:filename>", methods=["POST"])
@login_required
def abilities_restore(filename):
    d = _archive_dir()
    # Solo file dell'archivio: senza questo, un filename come ../../app.py
    # farebbe leggere e copiare file fuori dalla cartella.
    nome = os.path.basename(filename)
    percorso = os.path.join(d, nome)
    if not nome.startswith(ABILITIES_ARCHIVE_PREFIX) or not os.path.isfile(percorso):
        flash(f"❌ Archivio non trovato: {nome}", "error")
        return redirect(url_for("pokemon.abilities_editor"))
    try:
        with open(percorso, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data.get("abilities"), dict) or not data["abilities"]:
            flash(f"❌ {nome} non contiene abilità valide", "error")
            return redirect(url_for("pokemon.abilities_editor"))
        # _save_abilities tiene da parte la versione corrente prima di sovrascrivere
        _save_abilities(data)
        flash(f"↩ Abilità ripristinate da {nome}: {len(data['abilities'])} voci", "success")
    except Exception as e:
        flash(f"❌ Errore ripristino: {e}", "error")
    return redirect(url_for("pokemon.abilities_editor"))


# ---------------------------------------------------------------------------
# CONTENUTI DI UNA REGULATION — si sceglie QUALI voci del catalogo ne fanno parte.
# I dati restano nel catalogo: qui si spuntano soltanto dei nomi.
# ---------------------------------------------------------------------------
CAMPO_FILTRO = {"pokemon": "pokemon", "moves": "moves", "items": "items", "abilities": "abilities"}


def _nomi_selezionabili(db):
    """Nomi del catalogo proponibili per una regulation, ordinati."""
    if db == "pokemon":
        return _nomi_catalogo_pokemon(load_catalog("pokemon"))
    return sorted(voci_catalogo(db))


@bp.route("/regulation/<reg_id>/contenuto")
@login_required
def regulation_content(reg_id):
    db = request.args.get("db", "pokemon")
    if db not in CAMPO_FILTRO:
        db = "pokemon"
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), None)
    if not reg:
        flash(f"Regulation '{reg_id}' non trovata", "error")
        return redirect(url_for("pokemon.regulations_list"))

    filtro = _load_filtro(reg)
    if filtro is None:
        flash("Questa regulation usa ancora i file vecchi: convertila con "
              "scripts/migra_regulation.py per poterne scegliere i contenuti.", "error")
        return redirect(url_for("pokemon.regulation_editor", reg_id=reg_id))

    selezionati = filtro.get(CAMPO_FILTRO[db])
    disponibili = _nomi_selezionabili(db)
    conteggi = {}
    for d in CAMPO_FILTRO:
        sel = filtro.get(CAMPO_FILTRO[d])
        conteggi[d] = {"scelti": len(_nomi_selezionabili(d)) if sel is None else len(sel),
                       "totale": len(_nomi_selezionabili(d)),
                       "tutto": sel is None}
    return render_template(
        "regulation_content.html",
        reg=reg, db=db, db_disponibili=list(CAMPO_FILTRO), conteggi=conteggi,
        tutto=selezionati is None,
        disponibili_json=json.dumps(disponibili, ensure_ascii=False),
        selezionati_json=json.dumps(sorted(selezionati) if selezionati else [], ensure_ascii=False),
    )


@bp.route("/api/regulation/<reg_id>/copia-da", methods=["POST"])
@login_required
def api_regulation_copia_da(reg_id):
    """Copia gli elenchi di un'altra regulation dentro questa.

    Serve a non ricostruire a mano una regulation simile a una esistente: si parte
    da una copia e si toglie quel che non serve dalla schermata contenuti.
    """
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), None)
    if not reg or _load_filtro(reg) is None:
        return jsonify({"ok": False, "error": "regulation non trovata o non convertita"}), 404

    payload = request.get_json(silent=True) or {}
    sorgente_id = (payload.get("sorgente") or "").strip()
    if sorgente_id == reg_id:
        return jsonify({"ok": False, "error": "sorgente e destinazione coincidono"}), 400
    sorgente = next((r for r in regs if r["id"] == sorgente_id), None)
    filtro_sorgente = _load_filtro(sorgente) if sorgente else None
    if filtro_sorgente is None:
        return jsonify({"ok": False, "error": f"regulation sorgente non valida: {sorgente_id}"}), 404

    # solo i campi scelti, così si può copiare per esempio le sole mosse
    campi = payload.get("campi") or ["pokemon", "moves", "items", "abilities", "mega_map",
                                     "moveset"]
    percorso = os.path.join(DATA_DIR, reg["filter_file"])
    with open(percorso, encoding="utf-8") as f:
        filtro = json.load(f)

    copiati = {}
    # ⚠️ `moveset` non sta nel filtro, sta nel registro: e' l'unico campo copiabile
    # che si scrive in `regulations.json`. Senza di lui una regulation copiata da MA
    # riceve i 460 nomi di Champions e poi legge gli elenchi di `main`.
    if "moveset" in campi:
        reg["moveset"] = sorgente_moveset(sorgente)
        _save_regulations(regs)
        copiati["moveset"] = reg["moveset"]

    for campo in campi:
        if campo not in ("pokemon", "moves", "items", "abilities", "mega_map"):
            continue
        valore = filtro_sorgente.get(campo)
        filtro[campo] = valore
        copiati[campo] = "tutte" if valore is None else len(valore)
    filtro["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(percorso, "w", encoding="utf-8") as f:
        json.dump(filtro, f, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "sorgente": sorgente.get("label", sorgente_id), "copiati": copiati})


# Roster e oggetti confrontati con Serebii e Bulbapedia (§4.3, deciso con Davide il
# 23/09/2026). Una route sola come la mega_map: `anteprima` non scrive niente. Le
# regole — una specie cambia solo se le due fonti concordano — stanno in
# `regulation_fonti.py`, e le usa anche `scripts/confronta_regulation.py`.
@bp.route("/api/regulation/<reg_id>/fonti", methods=["POST"])
@login_required
def api_regulation_fonti(reg_id):
    import regulation_fonti
    payload = request.get_json(silent=True) or {}
    if payload.get("anteprima", True):
        esito = regulation_fonti.confronto(reg_id, aggiorna=bool(payload.get("aggiorna")))
    else:
        esito = regulation_fonti.applica(reg_id)
    return jsonify(esito), (200 if esito.get("ok") else 409)


@bp.route("/api/regulation/<reg_id>/mega-map", methods=["POST"])
@login_required
def api_regulation_mega_map(reg_id):
    """Collega le Mega del roster alla loro specie base, dedotte dal nome.

    E' il pulsante che rende una regulation nata qui **usabile**: una Mega che sta
    nel roster ma che nessuna base punta e' irraggiungibile — il team builder non la
    offre e il calcolatore non ci arriva — e fino al 10/09/2026 l'unico modo di
    collegarla era `scripts/completa_mega_map.py` da riga di comando, o copiare la
    mega_map di un'altra regulation.

    Tre cose, di proposito:

    - **completa, non ricalcola**: i collegamenti gia' scritti restano, anche quelli
      messi a mano che nessuna regola dedurrebbe
    - `anteprima: true` non scrive niente e dice cosa farebbe, come il `--dry-run`
      degli script
    - le Mega la cui base **non e' nel roster** non si collegano da sole: aggiungere
      una specie e' una scelta di contenuto, e serve `aggiungi_basi: true`
    """
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), None)
    filtro = _load_filtro(reg) if reg else None
    if filtro is None:
        return jsonify({"ok": False, "error": "regulation non trovata o non convertita"}), 404

    payload = request.get_json(silent=True) or {}
    anteprima     = bool(payload.get("anteprima"))
    aggiungi_basi = bool(payload.get("aggiungi_basi"))

    nomi_catalogo = _nomi_catalogo_pokemon(load_catalog("pokemon"))
    roster = _load_roster(reg)          # risolve gia' `pokemon: null` = tutto il catalogo
    mega_map = filtro.get("mega_map") or {}
    collegamenti, senza_base, problemi = collega_mega(roster, nomi_catalogo, mega_map)

    # ⚠️ Su una regulation con `pokemon: null` il roster e' tutto il catalogo, quindi
    # `senza_base` e' vuoto per costruzione e nessuna specie va aggiunta: scrivere
    # l'elenco trasformerebbe «tutto, anche le voci future» in una lista chiusa.
    tutto_il_catalogo = filtro.get("pokemon") is None
    da_aggiungere = sorted({b for b, _ in senza_base}) if (aggiungi_basi and not tutto_il_catalogo) else []
    da_collegare = collegamenti + (senza_base if da_aggiungere else [])

    esito = {
        "ok": True,
        "anteprima": anteprima,
        "collegamenti": [{"base": b, "mega": m} for b, m in sorted(da_collegare)],
        "collegati": len(da_collegare),
        "senza_base": [{"base": b, "mega": m} for b, m in sorted(senza_base)],
        "aggiunte_al_roster": da_aggiungere,
        "problemi": [motivo for _, motivo in problemi],
    }

    if anteprima or not da_collegare:
        esito["scritto"] = False
        return jsonify(esito)

    copia = os.path.join(_archive_dir(), f"regulation_{reg_id}_pre-mega-map.json")
    try:
        with open(copia, "w", encoding="utf-8") as f:
            json.dump(filtro, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # come per il catalogo: il backup non deve impedire il salvataggio

    filtro["mega_map"] = applica_collegamenti(mega_map, da_collegare)
    if da_aggiungere:
        filtro["pokemon"] = sorted(set(roster) | set(da_aggiungere))
    filtro["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(os.path.join(DATA_DIR, reg["filter_file"]), "w", encoding="utf-8") as f:
        json.dump(filtro, f, ensure_ascii=False, indent=2)

    roster_finale = filtro["pokemon"] if filtro.get("pokemon") is not None else roster
    mappate = {m for v in filtro["mega_map"].values() for m in v}
    mega_nel_roster = {n for n in roster_finale if n.startswith("Mega ")}
    esito.update(scritto=True,
                 raggiungibili=len(mega_nel_roster & mappate),
                 mega_nel_roster=len(mega_nel_roster))
    return jsonify(esito)


@bp.route("/api/regulation/<reg_id>/contenuto/<db>", methods=["POST"])
@login_required
def api_regulation_content_save(reg_id, db):
    if db not in CAMPO_FILTRO:
        return jsonify({"ok": False, "error": "database sconosciuto"}), 404
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), None)
    if not reg or _load_filtro(reg) is None:
        return jsonify({"ok": False, "error": "regulation non trovata o non convertita"}), 404

    payload = request.get_json(silent=True) or {}
    if payload.get("tutto"):
        _salva_filtro(reg, CAMPO_FILTRO[db], None)   # null = tutte le voci
        return jsonify({"ok": True, "tutto": True, "scelti": len(_nomi_selezionabili(db))})

    nomi = payload.get("nomi")
    if not isinstance(nomi, list):
        return jsonify({"ok": False, "error": "serve un elenco di nomi"}), 400
    validi = set(_nomi_selezionabili(db))
    ignorati = [n for n in nomi if n not in validi]
    _salva_filtro(reg, CAMPO_FILTRO[db], [n for n in nomi if n in validi])
    return jsonify({"ok": True, "tutto": False,
                    "scelti": len([n for n in nomi if n in validi]),
                    "ignorati": ignorati[:20]})


# ---------------------------------------------------------------------------
# EDITOR DEL CATALOGO — schermata separata dagli editor di regulation.
# Qui si modificano i DATI (base stat, potenza, effetti); negli editor di
# regulation si sceglie soltanto QUALI nomi ne fanno parte.
# ---------------------------------------------------------------------------
@bp.route("/catalogo")
@login_required
def catalog_editor():
    db = request.args.get("db", "pokemon")
    if db not in DB_CATALOGO:
        db = "pokemon"
    voci = voci_catalogo(db)
    indice = sorted((_riga_indice(db, n, v) for n, v in voci.items()),
                    key=lambda r: r["nome"].lower())
    return render_template(
        "catalog_editor.html",
        db=db,
        db_disponibili=DB_CATALOGO,
        conteggi={d: len(voci_catalogo(d)) for d in DB_CATALOGO},
        indice_json=json.dumps(indice, ensure_ascii=False),
        totale=len(voci),
    )


@bp.route("/api/catalogo/<db>/voce")
@login_required
def api_catalogo_voce(db):
    """JSON completo di una singola voce: la tabella manda solo l'indice compatto."""
    if db not in DB_CATALOGO:
        return jsonify({"ok": False, "error": "database sconosciuto"}), 404
    nome = request.args.get("nome", "")
    voce = voci_catalogo(db).get(nome)
    if voce is None:
        return jsonify({"ok": False, "error": f"voce non trovata: {nome}"}), 404
    return jsonify({"ok": True, "nome": nome, "voce": voce})


# I campi che **tutte** le voci di un database hanno oggi: non è una lista di desideri,
# è il contratto vero, contato sul catalogo il 21/08/2026 — 1026 voci Pokémon, 919
# mosse, 397 oggetti, 386 abilità, e per ognuna questi campi sono al 100%.
# ⚠️ `bp` sulle mosse **non** è qui di proposito: ce l'hanno 760 su 919, perché le
# mosse di stato non hanno potenza. Chiederlo vorrebbe dire dichiarare incompleta una
# voce che è giusta.
CAMPI_ATTESI = {
    "pokemon": ("name", "types", "abilities", "base_stats", "nome_it", "nome_en"),
    "moves": ("category", "type", "desc", "nome_it", "nome_en"),
    "items": ("category", "desc", "nome_it", "nome_en"),
    "abilities": ("desc", "category", "effect", "nome_it", "nome_en"),
}

STAT_ATTESE = ("hp", "atk", "def", "spa", "spd", "spe")


def _valida_voce(db, voce):
    """`(errori, avvisi)` per una voce del catalogo.

    ⚠️ **Due elenchi e non uno**, perché sono due cose diverse — è la stessa distinzione
    per cui `moves: null` non vuol dire «nessuna mossa»:

    - un **errore** è un campo che c'è ma è del tipo sbagliato. Quello non si salva:
      `base_stats` con dentro una stringa non dà un errore a valle, dà **un numero
      sbagliato** nel calcolatore, che è il modo peggiore di sbagliare
    - un **avviso** è un campo che manca. Quello si salva e si **dichiara**: serve
      poter tenere una bozza, e le forme inventate di Davide sono nate così

    Fino al 21/08/2026 non c'era né l'uno né l'altro: il solo controllo era
    `isinstance(voce, dict)`, e una voce col solo campo `name` entrava con un `200 ok`.
    """
    errori, avvisi = [], []

    def tipo(campo, atteso, nome_atteso):
        valore = voce.get(campo)
        if valore is not None and not isinstance(valore, atteso):
            errori.append(f"«{campo}» dovrebbe essere {nome_atteso}, "
                          f"non {type(valore).__name__}")

    tipo("types", list, "un elenco")
    tipo("abilities", list, "un elenco")
    tipo("flags", list, "un elenco")
    tipo("base_stats", dict, "un oggetto")
    tipo("forms", dict, "un oggetto")
    tipo("effect", dict if db == "abilities" else (str, dict),
         "un oggetto" if db == "abilities" else "un testo o un oggetto")

    stats = voce.get("base_stats")
    if isinstance(stats, dict):
        for chiave, valore in stats.items():
            if isinstance(valore, bool) or not isinstance(valore, (int, float)):
                errori.append(f"base_stats.{chiave} non è un numero ({valore!r})")
            elif not 1 <= valore <= 255:
                # Non è un errore: le Mega di Davide possono uscire dai binari. Ma un
                # 2550 da uno zero di troppo va visto prima, non dopo tre calcoli.
                avvisi.append(f"base_stats.{chiave} = {valore}, fuori da 1-255")
        mancanti = [s for s in STAT_ATTESE if s not in stats]
        if mancanti:
            avvisi.append("base_stats senza " + ", ".join(mancanti)
                          + ": il calcolatore userà 0 per quelle")

    for campo in CAMPI_ATTESI.get(db, ()):
        if campo not in voce or voce.get(campo) in (None, "", [], {}):
            avvisi.append(f"manca «{campo}»")
    return errori, avvisi


@bp.route("/api/catalogo/<db>/salva", methods=["POST"])
@login_required
def api_catalogo_salva(db):
    """Crea o aggiorna una singola voce del catalogo."""
    if db not in DB_CATALOGO:
        return jsonify({"ok": False, "error": "database sconosciuto"}), 404
    payload = request.get_json(silent=True) or {}
    nome = (payload.get("nome") or "").strip()
    voce = payload.get("voce")
    nome_originale = (payload.get("nome_originale") or "").strip()
    if not nome:
        return jsonify({"ok": False, "error": "nome obbligatorio"}), 400
    if not isinstance(voce, dict):
        return jsonify({"ok": False, "error": "la voce deve essere un oggetto"}), 400
    errori, avvisi = _valida_voce(db, voce)
    if errori:
        return jsonify({"ok": False, "error": "; ".join(errori), "errori": errori}), 400

    voci = voci_catalogo(db)
    if nome_originale and nome_originale != nome:
        voci.pop(nome_originale, None)      # rinomina
    elif not nome_originale and nome in voci:
        return jsonify({"ok": False, "error": f"'{nome}' esiste già"}), 400
    voci[nome] = voce
    salva_catalogo(db, voci)
    return jsonify({"ok": True, "totale": len(voci), "avvisi": avvisi,
                    "riga": _riga_indice(db, nome, voce)})


@bp.route("/api/catalogo/<db>/elimina", methods=["POST"])
@login_required
def api_catalogo_elimina(db):
    if db not in DB_CATALOGO:
        return jsonify({"ok": False, "error": "database sconosciuto"}), 404
    nome = ((request.get_json(silent=True) or {}).get("nome") or "").strip()
    voci = voci_catalogo(db)
    if nome not in voci:
        return jsonify({"ok": False, "error": f"voce non trovata: {nome}"}), 404
    # Una voce del catalogo può essere referenziata da una regulation: avvisa.
    usata_da = []
    for reg in _list_regulation_files():
        filtro = _load_filtro(reg)
        if not filtro:
            continue
        elenco = filtro.get({"moves": "moves", "items": "items"}.get(db, "pokemon"))
        if elenco and nome in elenco:
            usata_da.append(reg.get("label", reg["id"]))
    del voci[nome]
    salva_catalogo(db, voci)
    return jsonify({"ok": True, "totale": len(voci), "usata_da": usata_da})


@bp.route("/catalogo/<db>/archive", methods=["POST"])
@login_required
def catalog_archive(db):
    if db not in DB_CATALOGO:
        flash("Database sconosciuto", "error")
        return redirect(url_for("pokemon.catalog_editor"))
    try:
        voci = voci_catalogo(db)
        nome = f"catalog_{db}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        with open(os.path.join(_archive_dir(), nome), "w", encoding="utf-8") as f:
            json.dump(voci, f, ensure_ascii=False, indent=2)
        flash(f"📦 Catalogo {db} archiviato come {nome} ({len(voci)} voci)", "success")
    except Exception as e:
        flash(f"❌ Errore archivio: {e}", "error")
    return redirect(url_for("pokemon.catalog_editor", db=db))


@bp.route("/catalogo/<db>/archives")
@login_required
def catalog_archives(db):
    d = _archive_dir()
    prefisso = f"catalog_{db}_"
    archivi = []
    for fn in sorted(os.listdir(d), reverse=True):
        if not fn.startswith(prefisso) or not fn.endswith(".json"):
            continue
        percorso = os.path.join(d, fn)
        try:
            with open(percorso, encoding="utf-8") as f:
                contenuto = json.load(f)
            chiave = DB_AVVOLTI.get(db)
            voci = contenuto.get(chiave, {}) if chiave else contenuto
            archivi.append({
                "filename": fn, "count": len(voci),
                "modificato": datetime.fromtimestamp(os.path.getmtime(percorso)).strftime("%d/%m/%Y %H:%M"),
                "automatico": fn == f"{prefisso}pre-salvataggio.json",
            })
        except Exception:
            pass
    return json.dumps(archivi), 200, {"Content-Type": "application/json"}


@bp.route("/catalogo/<db>/restore/<path:filename>", methods=["POST"])
@login_required
def catalog_restore(db, filename):
    if db not in DB_CATALOGO:
        flash("Database sconosciuto", "error")
        return redirect(url_for("pokemon.catalog_editor"))
    nome = os.path.basename(filename)          # niente path traversal
    percorso = os.path.join(_archive_dir(), nome)
    if not nome.startswith(f"catalog_{db}_") or not os.path.isfile(percorso):
        flash(f"❌ Archivio non trovato: {nome}", "error")
        return redirect(url_for("pokemon.catalog_editor", db=db))
    try:
        with open(percorso, encoding="utf-8") as f:
            contenuto = json.load(f)
        chiave = DB_AVVOLTI.get(db)
        voci = contenuto.get(chiave, {}) if chiave else contenuto
        if not isinstance(voci, dict) or not voci:
            flash(f"❌ {nome} non contiene voci valide", "error")
            return redirect(url_for("pokemon.catalog_editor", db=db))
        salva_catalogo(db, voci)             # tiene da parte la versione corrente
        flash(f"↩ Catalogo {db} ripristinato da {nome}: {len(voci)} voci", "success")
    except Exception as e:
        flash(f"❌ Errore ripristino: {e}", "error")
    return redirect(url_for("pokemon.catalog_editor", db=db))


# ── Import di specie nuove da PokéAPI (§1.3) ─────────────────────────────────
# La forma dell'import l'ha scelta Davide il 21/08/2026: si scrive un nome e i dati
# li pesca il programma, invece di incollare JSON a mano. La fonte è il dump CSV,
# la stessa da cui il catalogo è stato costruito — vedi `pokeapi.py`.
#
# ⚠️ Due route e non una: `pesca` fa **solo** l'anteprima e non scrive niente,
# `importa` scrive dopo che hai visto cosa entra. Un import che scrive al primo clic
# su dati curati è esattamente ciò che `salva_catalogo()` e gli archivi esistono per
# rimediare, e rimediare è peggio che chiedere.
def _voci_gia_presenti(voci):
    catalogo = voci_catalogo("pokemon")
    return {chiave: catalogo[chiave] for chiave in voci if chiave in catalogo}


def _stesso_slug_altrove(voci):
    """`{chiave pescata: chiave già in catalogo}` per chi ha lo **stesso slug**.

    ⚠️ Il confronto per chiave non basta, e questo è il caso vero, non teorico: delle
    specie di default del dump che non sono in catalogo ne restano **quattro**
    (`aegislash-shield`, `mimikyu-disguised`, `morpeko-full-belly`, `palafin-zero`), e
    tutte e quattro ci sono già sotto un'altra chiave (`aegislash-shield-forme`, …).
    Importarle creerebbe due voci per lo stesso Pokémon, con due verità sulle sue
    stat e nessun errore da nessuna parte.
    """
    catalogo = voci_catalogo("pokemon")
    per_slug = {}
    for chiave, voce in catalogo.items():
        if voce.get("slug"):
            per_slug.setdefault(voce["slug"], chiave)
    fuori = {}
    for chiave, voce in voci.items():
        altra = per_slug.get(voce.get("slug"))
        if altra and altra != chiave:
            fuori[chiave] = altra
    return fuori


def file_integrazioni_moveset():
    """Il file delle liste che il dump non ha, prese da un'altra fonte a mano.

    Letto a ogni chiamata e non fissato all'import del modulo: le prove spostano
    `CATALOG_DIR` su una copia, e questo file deve seguirlo.
    """
    return os.path.join(CATALOG_DIR, "moveset_integrazioni.json")


def applica_integrazioni_moveset(voci):
    """Aggiunge a `voci` (sul posto) le liste di `moveset_integrazioni.json`.

    Scritto il 14/09/2026 per Pawmot: è in Champions dalla versione 1.2.0, e PokéAPI
    quella versione non ce l'ha. `pokemon_moves.json` però lo **rigenerano** due strade,
    `importa_mosse_specie.py` e l'import dal pannello del catalogo, e una lista scritta
    a mano lì dentro sparirebbe al giro dopo **senza nessun errore**. Per questo le
    integrazioni stanno in un file loro, e tutte e due le strade passano da qui.

    ⚠️ **Il dump vince.** Una lista integrata si applica solo dove il dump non ne ha una
    sua: il giorno che PokéAPI aggiungerà Pawmot, la voce torna al dump e l'integrazione
    compare fra le `superate`, da togliere. Si riconosce dal campo `fonte`, che il dump
    non scrive mai.

    Torna `(applicate, superate)`, due elenchi di `"voce/sorgente"`.
    """
    try:
        with open(file_integrazioni_moveset(), encoding="utf-8") as f:
            integrazioni = (json.load(f) or {}).get("voci") or {}
    except (OSError, ValueError):
        return [], []
    applicate, superate = [], []
    for chiave, sorgenti in integrazioni.items():
        for sorgente, blocco in sorgenti.items():
            voce = voci.setdefault(chiave, {})
            presente = voce.get(sorgente)
            if presente and not presente.get("fonte"):
                superate.append(f"{chiave}/{sorgente}")
                continue
            voce[sorgente] = blocco
            applicate.append(f"{chiave}/{sorgente}")
    return applicate, superate


def applica_eredita_dichiarata(voci):
    """Dà a una forma la lista della sua specie, dove una fonte dice che è la stessa.

    Scritto il 21/09/2026 per le **6 Mega di Regulation M-C** — Mega Salamence, Mega
    Absol Z, Mega Garchomp Z, Mega Lucario Z, Mega Golisopod, Mega Baxcalibur. Sono in
    Champions, ma il dump di PokéAPI non ha righe di mosse per loro (i loro giochi,
    `legends-za` e `mega-dimension`, nel dump sono vuoti) e Bulbapedia **non dà un
    blocco alle Mega**: le tratta come la specie, quindi
    `integra_moveset_bulbapedia.py` si rifiuta — giustamente — di integrarle.

    Non è una deduzione: la fonte è **Pokémon Zone**, che ha una pagina **per ogni
    Mega** con la sua tabella «Learnable Moves». Confrontate tutte e sei con la lista
    della loro specie il 21/09/2026: **6 su 6 identiche**, stesso conteggio
    (Golisopod 67, Absol 72, Salamence 62, Garchomp 59, Lucario 83, Baxcalibur 51).
    L'unica differenza di testo era `Mud-Slap` contro `Mud Slap`, che è l'alias di nome
    già noto. Serebii dice la stessa cosa dall'altro verso: una **lista sola** per
    Absol, Mega Absol e Mega Absol Z.

    ⚠️ **Il dump vince**, come per le integrazioni: se un domani PokéAPI riempirà
    `mega-dimension`, la forma avrà una lista sua e questa eredità verrà detta
    **superata**, da togliere. E se la specie non ha la lista, non se ne inventa una.

    ⚠️ La derivazione è **dichiarata dentro il blocco** (`eredita_da`), non a livello
    di voce: a livello di voce vorrebbe dire «tutti i blocchi», e a queste Mega la
    lista `main` della specie non spetta — nei giochi principali non esistono.

    Torna `(applicate, superate)`.
    """
    try:
        with open(file_integrazioni_moveset(), encoding="utf-8") as f:
            eredita = (json.load(f) or {}).get("eredita") or {}
    except (OSError, ValueError):
        return [], []
    # ⚠️ Cinque delle sei Mega **non hanno nessuna voce** nel moveset: il dump non ha
    # righe per loro, quindi `costruisci_moveset()` le lascia fuori del tutto. Qui la
    # voce si crea, con il suo slug preso dal catalogo — senza questo la funzione
    # applicava una sola eredità su sei e non lo diceva a nessuno.
    slug_forme = {nome_forma: (forma or {}).get("slug")
                  for dati in load_catalog("pokemon").values()
                  for nome_forma, forma in (dati.get("forms") or {}).items()}
    applicate, superate = [], []
    for nome_forma, sorgenti in eredita.items():
        voce = voci.get(nome_forma)
        if voce is None:
            if nome_forma not in slug_forme:
                continue          # non è nemmeno nel catalogo: non si inventa
            voce = voci[nome_forma] = {}
            if slug_forme[nome_forma]:
                voce["slug"] = slug_forme[nome_forma]
        for sorgente, blocco in sorgenti.items():
            if (voce.get(sorgente) or {}).get("moves"):
                superate.append(f"{nome_forma}/{sorgente}")
                continue
            base = voci.get(blocco.get("da")) or {}
            lista = (base.get(sorgente) or {}).get("moves")
            if not lista:
                continue          # la specie non ce l'ha: non si inventa
            voce[sorgente] = {"moves": dict(lista),
                              "fonte": blocco.get("fonte"),
                              "eredita_da": blocco.get("da")}
            applicate.append(f"{nome_forma}/{sorgente}")
    return applicate, superate


def applica_toppe_moveset(voci):
    """Aggiunge e toglie **singole mosse** su liste che il dump ha già.

    Scritto il 18/09/2026 per la versione 1.2.0 di Champions. È il caso opposto a
    `applica_integrazioni_moveset()`, che sostituisce una lista intera e **solo**
    dove il dump non ne ha una: qui la lista del dump c'è ed è giusta quasi tutta,
    e va corretta di una mossa. Il changelog ufficiale della 1.2.0 dice che Politoed
    non può più usare Pound, Archaludon né Mirror Coat né Metal Burst, e che Slash
    ora si può usare; il dump di PokéAPI è fermo prima di quella versione.

    ⚠️ Vale la stessa ragione per cui esistono le integrazioni: `pokemon_moves.json`
    lo **rigenerano** `importa_mosse_specie.py` e l'import dal pannello, e una mossa
    tolta a mano lì dentro tornerebbe al giro dopo **senza nessun errore**.

    ⚠️ Una toppa non inventa: se la mossa da togliere non c'è più, o quella da
    aggiungere c'è già, la toppa è **superata** — il dump ha recuperato il ritardo —
    e va tolta dal file. Non si applica silenziosamente a vuoto.

    ⚠️ **Dal 21/09/2026 arriva anche alle forme della specie**, che una toppa scritta
    per chiave non raggiungeva: e solo a quelle la cui lista, tolte le mosse che la
    toppa nomina, è **identica** a quella della specie. Una forma con una lista sua
    finisce nel terzo elenco invece di essere toccata.

    Torna `(applicate, superate, con_lista_propria)`, tre elenchi di `"voce/sorgente"`.
    """
    try:
        with open(file_integrazioni_moveset(), encoding="utf-8") as f:
            toppe = (json.load(f) or {}).get("toppe") or {}
    except (OSError, ValueError):
        return [], [], []
    catalogo = load_catalog("pokemon")
    applicate, superate, con_lista_propria = [], [], []

    def tocca(elenco, aggiunte, rimosse):
        """Applica una toppa a una lista. Torna `True` se serviva davvero."""
        serviva = (any(m not in elenco for m in aggiunte)
                   or any(m in elenco for m in rimosse))
        for mossa, metodo in aggiunte.items():
            elenco.setdefault(mossa, metodo)
        for mossa in rimosse:
            elenco.pop(mossa, None)
        return serviva

    for chiave, sorgenti in toppe.items():
        for sorgente, blocco in sorgenti.items():
            blocco_voce = (voci.get(chiave) or {}).get(sorgente) or {}
            elenco = blocco_voce.get("moves")
            if elenco is None:
                # Nessuna lista da toppare: senza questo la toppa **creerebbe** una
                # lista di una mossa sola, che è peggio di non averne nessuna.
                superate.append(f"{chiave}/{sorgente}")
                continue
            aggiunte = blocco.get("aggiunte") or {}
            rimosse = blocco.get("rimosse") or []
            serviva = tocca(elenco, aggiunte, rimosse)
            # ⚠️ Riordinata: una mossa aggiunta finirebbe **in fondo** al dizionario, e
            # il file scritto dopo avrebbe un ordine diverso da quello del dump, che è
            # alfabetico. Non cambia il contenuto, ma rende il diff illeggibile e fa
            # sembrare non idempotente uno script che lo è.
            blocco_voce["moves"] = dict(sorted(elenco.items()))
            (applicate if serviva else superate).append(f"{chiave}/{sorgente}")

            # ⚠️ **E le forme della specie.** Una toppa è scritta con la **chiave** di
            # una specie, e fino al 21/09/2026 si fermava lì: le 19 forme delle specie
            # toppate — Mega Absol, Mega Charizard X e Y, Aegislash (Blade Forme),
            # Mimikyu (Busted Form), … — sono rimaste **senza** lo `Slash` della 1.2.0
            # che la loro specie aveva preso, e sono tutte in MA e MB. A schermo voleva
            # dire che Absol poteva scegliere Slash e Mega Absol no, che è lo stesso
            # Pokémon a metà partita. Nessun errore, solo la tendina più corta.
            #
            # Il criterio non indovina: si tocca una forma **solo** se la sua lista,
            # ignorando le mosse che la toppa nomina, è **identica** a quella della
            # specie — cioè se la fonte non sa niente di specifico su quella forma.
            # Ignorare le mosse nominate è ciò che rende il confronto stabile: regge
            # sia sul file appena rigenerato dal dump (dove nessuna delle due ce l'ha)
            # sia su quello già toppato a metà (dove la specie sì e la forma no).
            toccate = set(aggiunte) | set(rimosse)
            resto_specie = set(elenco) - toccate
            for nome_forma in (catalogo.get(chiave) or {}).get("forms") or {}:
                if nome_forma in toppe:
                    continue      # ha una toppa sua: la applica il suo giro
                blocco_forma = (voci.get(nome_forma) or {}).get(sorgente) or {}
                lista = blocco_forma.get("moves")
                if lista is None:
                    continue      # niente lista: una toppa non ne inventa una
                if (set(lista) - toccate) != resto_specie:
                    # Una lista sua vuol dire che la fonte **distingue** le due forme
                    # (le Rotom, Hisuian Samurott): applicarle la toppa della specie
                    # sarebbe inventare. Si dichiara e si lascia stare.
                    con_lista_propria.append(f"{nome_forma}/{sorgente}")
                    continue
                if tocca(lista, aggiunte, rimosse):
                    applicate.append(f"{nome_forma}/{sorgente}")
                blocco_forma["moves"] = dict(sorted(lista.items()))
    return applicate, superate, con_lista_propria


def riallinea_forme_eredi(voci):
    """Rimette alle forme che dichiarano `eredita_da` i blocchi della loro base.

    ⚠️ Serve perché l'eredità viene costruita **prima** che integrazioni e toppe
    entrino, e non le vede arrivare. In `costruisci_moveset()` la forma Gigantamax copia
    il dizionario della specie: mutare una lista condivisa si propaga, ma **aggiungere
    un blocco nuovo alla specie no**. Trovato il 21/09/2026 integrando le 25 voci di
    Regulation M-C: Cinderace, Inteleon, Rillaboom e Toxtricity hanno preso la loro
    lista `champions` da Bulbapedia, e le loro quattro forme Gigantamax — che
    dichiarano di ereditarla — sono rimaste senza, con l'avviso giallo «nessun elenco
    mosse». Nessun errore.

    `eredita_da` non è un'indicazione di massima: dice che la lista **è** quella della
    base, quindi qui si copia, non si fonde. Torna l'elenco dei `"voce/sorgente"`
    rimessi a posto.
    """
    catalogo = load_catalog("pokemon")
    # `eredita_da` nomina la base col nome visualizzato (`Charizard`), le specie stanno
    # sotto la chiave del catalogo (`charizard`): senza il ponte non si trova niente.
    per_nome = {}
    for chiave, dati in catalogo.items():
        for n in (dati.get("name"), chiave):
            if n:
                per_nome.setdefault(n, chiave)
    rimessi = []
    for nome_forma, voce in voci.items():
        base = voce.get("eredita_da")
        if not base:
            continue
        sorgente = voci.get(per_nome.get(base, base)) or {}
        for quale, blocco in sorgente.items():
            if not isinstance(blocco, dict) or "moves" not in blocco:
                continue
            if (voce.get(quale) or {}).get("moves") != blocco.get("moves"):
                voce[quale] = {k: (dict(v) if isinstance(v, dict) else v)
                               for k, v in blocco.items()}
                rimessi.append(f"{nome_forma}/{quale}")
    return rimessi


def salva_moveset(nuove):
    """Aggiunge o aggiorna voci in `pokemon_moves.json`, tenendo `_meta`.

    ⚠️ Niente copia in `data/archive/`, e la ragione è la stessa scritta in
    `scripts/importa_mosse_specie.py`: il file pesa 3 MB e si **rigenera** con uno
    script rieseguibile. La rete qui è quella, non una copia che gonfierebbe una
    cartella versionata a ogni import.
    """
    try:
        with open(MOVESET_FILE, encoding="utf-8") as f:
            dati = json.load(f) or {}
    except Exception:
        dati = {}
    voci = dati.get("voci") or {}
    voci.update(nuove)
    # una voce reimportata dal dump non deve perdere la lista integrata, né le
    # mosse che la 1.2.0 ha aggiunto o tolto e che nel dump non si vedono
    applica_integrazioni_moveset(voci)
    applica_toppe_moveset(voci)
    # l'eredità dichiarata va **dopo** le toppe, così copia la lista finale
    applica_eredita_dichiarata(voci)
    # e le forme che ereditano: l'eredità è costruita prima che le tre passino
    riallinea_forme_eredi(voci)
    dati["voci"] = voci
    meta = dati.get("_meta") or {}
    # La provenienza si scrive **accanto** a quella del dump, non al posto: il grosso
    # del file resta di `importa_mosse_specie.py`, e chi legge deve poterlo sapere.
    meta["aggiornato_da_interfaccia"] = datetime.now().strftime("%Y-%m-%d")
    dati["_meta"] = meta
    os.makedirs(os.path.dirname(MOVESET_FILE), exist_ok=True)
    # ⚠️ `indent=1`, come `importa_mosse_specie.py` che genera il file. Fino al
    # 23/09/2026 qui c'era `indent=2`: ogni salvataggio dall'interfaccia riscriveva
    # tutte le ~200.000 righe per cambiarne poche, e il diff non diceva più cosa era
    # cambiato davvero.
    with open(MOVESET_FILE, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=1)
    _MOVESET["mtime"] = None                  # la cache si rilegge al prossimo giro


@bp.route("/api/catalogo/pokemon/pesca", methods=["POST"])
@login_required
def api_catalogo_pesca():
    """Anteprima dell'import: cosa entrerebbe, cosa sovrascriverebbe, cosa non torna."""
    import pokeapi
    payload = request.get_json(silent=True) or {}
    nomi = [n.strip() for n in (payload.get("nomi") or []) if (n or "").strip()]
    if not nomi:
        return jsonify({"ok": False, "error": "nessun nome da cercare"}), 400
    mancanti = pokeapi.file_mancanti()
    if mancanti:
        return jsonify({"ok": False, "fonte_incompleta": mancanti,
                        "error": "la fonte non è ancora scaricata"}), 200

    voci, mosse, problemi = pokeapi.pesca(nomi)
    # L'anteprima mostra quello che l'import scriverà davvero, integrazioni comprese:
    # dire «non è in Champions» di Pawmot sarebbe falso, e lo è dalla 1.2.0.
    applicate, _ = applica_integrazioni_moveset(mosse)
    # Le toppe si applicano anche qui — l'anteprima deve dire il vero — ma **non**
    # entrano in `integrate`: quella nota dice «PokéAPI non ce l'ha», e per una voce
    # toppata sarebbe falsa, la lista ce l'ha e le manca una mossa.
    applica_toppe_moveset(mosse)
    integrate = {a.split("/")[0] for a in applicate}
    mosse = {k: v for k, v in mosse.items() if k in voci}
    problemi = [p for p in problemi
                if not (p.get("nome") in integrate and p.get("problema") == pokeapi.NON_IN_CHAMPIONS)]
    for chiave in sorted(integrate & set(voci)):
        fonte = ((mosse.get(chiave) or {}).get("champions") or {}).get("fonte", "")
        problemi.append({"nome": chiave, "problema": "lista Champions integrata",
                         "dettaglio": f"PokéAPI non ce l'ha: viene da {fonte}, "
                                      "in data/catalog/moveset_integrazioni.json"})
    presenti = _voci_gia_presenti(voci)
    doppioni = _stesso_slug_altrove(voci)
    for chiave, altra in doppioni.items():
        problemi.append({"nome": chiave, "problema": "esiste già sotto un'altra chiave",
                         "dettaglio": f"«{altra}» ha lo stesso slug: importarla farebbe "
                                      f"due voci per lo stesso Pokémon"})
    anteprima = []
    for chiave, voce in voci.items():
        m = mosse.get(chiave) or {}
        anteprima.append({
            "chiave": chiave,
            "nome": voce.get("nome_it") or voce.get("name"),
            "types": voce.get("types"),
            "abilities": voce.get("abilities"),
            "base_stats": voce.get("base_stats"),
            "mosse_main": len((m.get("main") or {}).get("moves") or {}),
            "mosse_champions": len((m.get("champions") or {}).get("moves") or {}),
            # ⚠️ Va detto **prima**: sovrascrivere una voce curata a mano senza
            # dirlo sarebbe il modo più veloce di perdere una correzione.
            "gia_presente": chiave in presenti,
            "doppione_di": doppioni.get(chiave),
        })
    return jsonify({"ok": True, "voci": anteprima, "problemi": problemi,
                    "regulation": [{"id": r["id"], "label": r.get("label", r["id"])}
                                   for r in _list_regulation_files()]})


@bp.route("/api/catalogo/pokemon/prepara-fonte", methods=["POST"])
@login_required
def api_catalogo_prepara_fonte():
    """Scarica i file del dump che mancano. È lento la prima volta: sono ~11 MB."""
    import pokeapi
    mancanti = pokeapi.file_mancanti()
    if not mancanti:
        return jsonify({"ok": True, "scaricati": [], "messaggio": "la fonte c'era già"})
    try:
        scaricati, byte = pokeapi.scarica_mancanti(mancanti)
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 502
    return jsonify({"ok": True, "scaricati": scaricati, "kb": byte // 1024})


@bp.route("/api/catalogo/pokemon/importa", methods=["POST"])
@login_required
def api_catalogo_importa():
    """Scrive le voci pescate: catalogo, moveset e — se chiesto — le regulation."""
    import pokeapi
    payload = request.get_json(silent=True) or {}
    nomi = [n.strip() for n in (payload.get("nomi") or []) if (n or "").strip()]
    regulation = payload.get("regulation") or []
    sovrascrivi = bool(payload.get("sovrascrivi"))
    if not nomi:
        return jsonify({"ok": False, "error": "nessun nome da importare"}), 400

    voci, mosse, problemi = pokeapi.pesca(nomi)
    if not voci:
        return jsonify({"ok": False, "error": "niente da importare", "problemi": problemi}), 400

    doppioni = _stesso_slug_altrove(voci)
    if doppioni:
        # ⚠️ Qui non c'è un `--sovrascrivi` che tenga: la voce esiste già con un altro
        # nome, e scriverla comunque vorrebbe dire creare il doppione, non sostituirlo.
        # Chi vuole davvero rimpiazzarla passa dall'editor, dove rinominare è previsto.
        return jsonify({"ok": False, "error": "esistono già sotto un'altra chiave",
                        "doppioni": doppioni, "problemi": problemi}), 409
    presenti = _voci_gia_presenti(voci)
    if presenti and not sovrascrivi:
        return jsonify({"ok": False, "error": "voci già in catalogo",
                        "gia_presenti": sorted(presenti),
                        "problemi": problemi}), 409

    catalogo = voci_catalogo("pokemon")
    for chiave, voce in voci.items():
        # ⚠️ Le `forms` annidate di una voce che esisteva **non si perdono**: sono le
        # Mega e le Gigantamax, che il dump non ha e che nessun import può ricostruire.
        # Sovrascrivere la voce intera le cancellerebbe in silenzio.
        vecchia = catalogo.get(chiave) or {}
        if vecchia.get("forms"):
            voce = dict(voce, forms=vecchia["forms"])
        catalogo[chiave] = voce
    salva_catalogo("pokemon", catalogo)
    if mosse:
        salva_moveset(mosse)

    # Le regulation con l'elenco esplicito: `pokedex` non serve, i suoi filtri sono
    # `null` cioè "tutto il catalogo", e una voce nuova ci compare da sola.
    aggiunte_a = {}
    for reg in _list_regulation_files():
        if reg["id"] not in regulation:
            continue
        filtro = _load_filtro(reg)
        if filtro is None or filtro.get("pokemon") is None:
            aggiunte_a[reg["id"]] = "già tutto il catalogo: non serve aggiungerla"
            continue
        elenco = set(filtro["pokemon"])
        prima = len(elenco)
        for voce in voci.values():
            elenco.add(voce.get("name") or voce.get("nome_en"))
        if _salva_filtro(reg, "pokemon", elenco):
            aggiunte_a[reg["id"]] = f"{len(elenco) - prima} aggiunte, {len(elenco)} in tutto"
        else:
            aggiunte_a[reg["id"]] = "non migrata al filtro: elenco non scritto"

    log_hub.registra("import", f"Pokémon da PokéAPI: {len(voci)} voci scritte"
                               + (f", {len(presenti)} sovrascritte" if presenti else ""),
                     voci=sorted(voci), regulation=aggiunte_a or None)
    return jsonify({"ok": True, "scritte": sorted(voci), "totale": len(catalogo),
                    "sovrascritte": sorted(presenti), "problemi": problemi,
                    "regulation": aggiunte_a,
                    "con_mosse": sorted(mosse),
                    "senza_champions": sorted(c for c, m in mosse.items()
                                              if "champions" not in m)})


# Aggiornare tutto il Pokédex dalla fonte (§4.3, deciso con Davide il 23/09/2026):
# entra solo il **nuovo**, e le differenze sulle voci esistenti si mostrano senza
# applicarle. Due route come per `pesca`/`importa`: la prima non scrive niente.
@bp.route("/api/catalogo/aggiorna/anteprima", methods=["POST"])
@login_required
def api_catalogo_aggiorna_anteprima():
    import pokedex_aggiorna
    a = pokedex_aggiorna.anteprima(aggiorna_fonte=True)
    a.pop("_costruiti", None)
    return jsonify(a), (200 if a.get("ok") else 409)


@bp.route("/api/catalogo/aggiorna/applica", methods=["POST"])
@login_required
def api_catalogo_aggiorna_applica():
    import pokedex_aggiorna
    esito = pokedex_aggiorna.applica()
    esito.pop("_costruiti", None)
    if esito.get("ok"):
        log_hub.registra("import", f"Pokédex aggiornato dalla fonte: "
                                   f"{esito.get('scritte', 0)} voci nuove scritte")
    else:
        log_hub.registra("import", f"Pokédex non aggiornato: {esito.get('errore')}",
                         livello="avviso")
    return jsonify(esito), (200 if esito.get("ok") else 409)


@bp.route("/api/abilities/update", methods=["POST"])
@login_required
def api_abilities_update():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "nome obbligatorio"}), 400
    ab_data = load_abilities()
    ab_data["abilities"][name] = {
        "desc": payload.get("desc", ""),
        "category": payload.get("category", "other"),
        "effect": payload.get("effect", {"type": "none"})
    }
    _save_abilities(ab_data)
    return jsonify({"ok": True, "name": name})


@bp.route("/api/abilities/delete", methods=["POST"])
@login_required
def api_abilities_delete():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "nome obbligatorio"}), 400
    ab_data = load_abilities()
    if name not in ab_data["abilities"]:
        return jsonify({"ok": False, "error": "abilità non trovata"}), 404
    del ab_data["abilities"][name]
    _save_abilities(ab_data)
    return jsonify({"ok": True})


@bp.route("/api/abilities", methods=["GET"])
@login_required
def api_abilities_list():
    """Restituisce il JSON delle abilità — usato dal calcolatore."""
    return jsonify(load_abilities())


# ---------------------------------------------------------------------------
# API: elenco e salvataggio del registro delle regulation
#
# Le chiamava già il JS di regulation_editor.html (Salva Metadati) e la tendina
# Regulation di team_form.html, ma le due rotte non esistevano: la prima dava
# 404 e finiva nel catch, la seconda lasciava la tendina con la sola opzione
# stampata dal template. Trovate verificando le quattro voci dell'11/08/2026.
# ---------------------------------------------------------------------------
@bp.route("/api/regulations", methods=["GET"])
@login_required
def api_regulations_list():
    return jsonify({"ok": True, "regulations": _list_regulation_files()})


@bp.route("/api/regulations/save", methods=["POST"])
@login_required
def api_regulations_save():
    """Riscrive data/regulations.json. Rifiuta un registro vuoto o malformato.

    Il file dice anche **qual è la regulation di partenza** (la prima), quindi un
    salvataggio sbagliato non toglierebbe solo un'etichetta: cambierebbe il default
    del sito. Per questo i controlli sono prima della scrittura, non dopo.
    """
    data = request.get_json(silent=True) or {}
    regs = data.get("regulations")

    if not isinstance(regs, list) or not regs:
        return jsonify({"ok": False, "error": "Elenco regulation vuoto o non valido"}), 400
    for r in regs:
        if not isinstance(r, dict) or not (r.get("id") or "").strip() \
                or not (r.get("label") or "").strip():
            return jsonify({"ok": False, "error": "Ogni regulation deve avere id e label"}), 400
    ids = [r["id"] for r in regs]
    if len(ids) != len(set(ids)):
        return jsonify({"ok": False, "error": "Ci sono id duplicati"}), 400

    # Una sorgente mosse inesistente non darebbe errore a valle: `mosse_legali()`
    # troverebbe `None` e il team builder mostrerebbe **tutte** le mosse, con
    # l'avviso giallo delle forme inventate. Sarebbe un permesso, non un guasto.
    sorgenti = sorgenti_moveset()
    for r in regs:
        if r.get("moveset") and r["moveset"] not in sorgenti:
            return jsonify({"ok": False,
                            "error": f"'{r['id']}': sorgente mosse sconosciuta "
                                     f"'{r['moveset']}'. Disponibili: "
                                     + ", ".join(sorgenti)}), 400

    precedenti = {r["id"] for r in _list_regulation_files()}
    perse = precedenti - set(ids)
    if perse:
        return jsonify({"ok": False,
                        "error": "Il salvataggio perderebbe: " + ", ".join(sorted(perse))
                                 + ". Per rimuoverne una usa l'eliminazione."}), 409

    _save_regulations(regs)
    return jsonify({"ok": True, "regulations": regs, "default": regs[0]["id"]})


# ---------------------------------------------------------------------------
# API: crea una nuova regulation
# ---------------------------------------------------------------------------
@bp.route("/api/regulations/create", methods=["POST"])
@login_required
def api_regulations_create():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "Dati JSON mancanti"}), 400

    reg_id    = (data.get("id") or "").strip().lower().replace(" ", "_")
    reg_label = (data.get("label") or "").strip()

    if not reg_id or not reg_label:
        return jsonify({"ok": False, "error": "id e label sono obbligatori"}), 400

    regs = _list_regulation_files()
    if any(r["id"] == reg_id for r in regs):
        return jsonify({"ok": False, "error": f"Regulation '{reg_id}' già esistente"}), 409

    # ⚠️ La sorgente delle mosse va decisa **qui**, perche' l'assenza non da' errore:
    # `sorgente_moveset()` ricade su `main`, e una regulation nata da una copia di MA
    # servirebbe in silenzio gli elenchi dei giochi principali invece di quelli di
    # Champions — Incineroar con 80 mosse invece di 77, Knock Off compresa.
    sorgenti = sorgenti_moveset()
    moveset = (data.get("moveset") or "").strip().lower()
    if moveset and moveset not in sorgenti:
        return jsonify({"ok": False,
                        "error": f"Sorgente mosse sconosciuta: '{moveset}'. "
                                 f"Disponibili: {', '.join(sorgenti)}"}), 400

    # Una regulation nuova nasce nel modello a filtro: elenchi di nomi che puntano
    # al catalogo, mai una copia dei dati.
    #   partenza = "vuota"  -> non contiene nulla, si popola dalla schermata contenuti
    #              "tutto"  -> null ovunque, vede tutto il catalogo
    #              "<id>"   -> copia gli elenchi da una regulation esistente
    partenza = (data.get("partenza") or "vuota").strip().lower()
    if partenza == "tutto":
        elenchi = {"pokemon": None, "moves": None, "items": None, "abilities": None}
        mega_map = {}
    elif partenza in {r["id"] for r in regs}:
        sorgente = next(r for r in regs if r["id"] == partenza)
        filtro_sorgente = _load_filtro(sorgente) or {}
        elenchi = {k: filtro_sorgente.get(k) for k in ("pokemon", "moves", "items", "abilities")}
        mega_map = filtro_sorgente.get("mega_map") or {}
        # Copiando gli elenchi si copia anche la sorgente delle mosse, se non e' stata
        # chiesta esplicitamente: e' l'altra meta' di «parti da questa».
        moveset = moveset or sorgente_moveset(sorgente)
    else:
        partenza = "vuota"
        elenchi = {"pokemon": [], "moves": [], "items": [], "abilities": None}
        mega_map = {}

    filtro = {
        "id": reg_id,
        "label": reg_label,
        "_commento": ("Solo elenchi di nomi: i dati stanno in data/catalog/. "
                      "null significa 'tutte le voci del catalogo'."),
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        **elenchi,
        "mega_map": mega_map,
        "overrides": {},
    }
    percorso_filtro = os.path.join("regulations", f"{reg_id}.json")
    os.makedirs(os.path.join(DATA_DIR, "regulations"), exist_ok=True)
    with open(os.path.join(DATA_DIR, percorso_filtro), "w", encoding="utf-8") as fh:
        json.dump(filtro, fh, ensure_ascii=False, indent=2)

    new_reg = {
        "id":          reg_id,
        "label":       reg_label,
        "filter_file": percorso_filtro.replace(os.sep, "/"),
        "mechanics":   data.get("mechanics") or ["mega"],
        # Scritta sempre, anche quando vale il default: implicita non si vede, e una
        # sorgente che non si vede e' la stessa cosa di una sorgente sbagliata.
        "moveset":     moveset or MOVESET_DEFAULT,
    }
    regs.append(new_reg)
    _save_regulations(regs)

    return jsonify({"ok": True, "regulation": new_reg, "partenza": partenza,
                    "moveset": new_reg["moveset"]}), 201


# ---------------------------------------------------------------------------
# API: elimina una regulation (solo se senza team attivi)
# ---------------------------------------------------------------------------
@bp.route("/api/regulations/<reg_id>/delete", methods=["POST"])
@login_required
def api_regulations_delete(reg_id):
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), None)

    if not reg:
        return jsonify({"ok": False, "error": f"Regulation '{reg_id}' non trovata"}), 404

    # Sicurezza extra lato server: verifica che non ci siano team associati
    db = get_db()
    count = db.execute(
        "SELECT COUNT(*) FROM teams WHERE regulation_id=?", (reg_id,)
    ).fetchone()[0]
    db.close()

    if count > 0:
        return jsonify({"ok": False, "error": f"Impossibile eliminare: {count} team attivi"}), 409

    # Elimina i file JSON associati: i tre del vecchio modello e — dall'11/08/2026 —
    # anche il filtro. Prima restava lì: le regulation nuove hanno solo quello, quindi
    # eliminarne una lasciava `data/regulations/<id>.json` orfano sul disco mentre la
    # modale prometteva di averlo cancellato.
    deleted_files = []
    for key in ("roster_file", "moves_file", "items_file", "filter_file"):
        fpath = os.path.join(DATA_DIR, reg.get(key, ""))
        if os.path.isfile(fpath):
            try:
                # Il filtro è l'elenco di nomi scelto a mano: prima di toglierlo se ne
                # tiene una copia, come per catalogo e abilità. Ricostruire 279 nomi a
                # mano è esattamente la perdita che l'archivio esiste per evitare.
                if key == "filter_file":
                    with open(fpath, encoding="utf-8") as f:
                        contenuto = f.read()
                    copia = os.path.join(_archive_dir(), f"regulation_{reg_id}_pre-eliminazione.json")
                    with open(copia, "w", encoding="utf-8") as f:
                        f.write(contenuto)
                os.remove(fpath)
                deleted_files.append(reg[key])
            except Exception as e:
                return jsonify({"ok": False, "error": f"Errore eliminazione file '{reg[key]}': {e}"}), 500

    # Rimuovi dal registro e salva
    regs = [r for r in regs if r["id"] != reg_id]
    _save_regulations(regs)

    return jsonify({"ok": True, "deleted_files": deleted_files}), 200


@bp.route("/")
@login_required
def pokemon():
    db = get_db()
    # Chi guarda vede i **suoi** team. L'amministratore li vede tutti, con scritto
    # di chi sono, e con `?utente=<id>` ne isola uno solo: la tendina qui sotto.
    di = _i(request.args.get("utente")) or None
    cond, par = ambito_utente("t.user_id", di=di)
    teams = []
    for t in db.execute(
            "SELECT t.*, u.username AS proprietario FROM teams t "
            f"LEFT JOIN users u ON u.id=t.user_id WHERE {cond} ORDER BY t.created_at DESC",
            par).fetchall():
        # I membri non hanno un proprietario loro: lo ereditano dal team, che qui
        # è già stato filtrato. Ripeterlo sulla riga figlia vorrebbe dire poterlo
        # far divergere da quello del padre.
        members = db.execute(
            "SELECT * FROM team_members WHERE team_id=? ORDER BY slot",
            (t["id"],)
        ).fetchall()
        teams.append({"data": t, "members": list(members)})
    # La tendina del filtro esiste solo per l'admin, e nomina solo chi ha davvero
    # dei team: un elenco di utenti senza niente dentro sarebbe rumore.
    proprietari = []
    if e_admin():
        proprietari = [dict(r) for r in db.execute(
            "SELECT u.id, u.username, COUNT(t.id) AS quanti FROM users u "
            "JOIN teams t ON t.user_id=u.id GROUP BY u.id, u.username "
            "ORDER BY u.username").fetchall()]
    db.close()

    teams_json = json.dumps(
        [
            {
                "data": dict(t["data"]),
                "members": [dict(m) if m else None for m in t["members"]]
            }
            for t in teams
        ],
        ensure_ascii=False,
        default=str
    )
    return render_template("pokemon.html", teams=teams, teams_json=teams_json,
                           proprietari=proprietari, filtro_utente=di)


@bp.route("/team/new", methods=["GET", "POST"])
@login_required
def team_new():
    if request.method == "POST":
        tid = _team_upsert()
        flash("Team creato!", "success")
        return redirect(url_for("pokemon.team_edit", tid=tid))

    reg_id = request.args.get("regulation_id") or regulation_default()
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])

    roster = _load_roster(reg)
    mega_map = _load_mega_map(reg)
    mega_list = sorted(set(m for v in mega_map.values() for m in v))

    return render_template(
        "team_form.html",
        team=None,
        members=[None] * 6,
        roster=roster,
        mega_map=mega_map,
        natures=NATURES,
        nature_effects=NATURE_EFFECTS,
        mega_list=mega_list,
        items_data=load_items(reg_id),
        regulations=regs,
        current_reg=reg
    )


@bp.route("/team/<int:tid>/edit", methods=["GET", "POST"])
@login_required
def team_edit(tid):
    db = get_db()
    cond, par = ambito_utente()
    team = db.execute(f"SELECT * FROM teams WHERE id=? AND {cond}",
                      (tid,) + tuple(par)).fetchone()
    # Un team che non è tuo risponde «non trovato», non «vietato»: chi prova un id
    # a caso non deve poter capire quali esistono.
    if not team:
        flash("Non trovato", "error")
        db.close()
        return redirect(url_for("pokemon.pokemon"))

    members = list(db.execute(
        "SELECT * FROM team_members WHERE team_id=? ORDER BY slot",
        (tid,)
    ).fetchall())
    members = members + [None] * (6 - len(members))

    if request.method == "POST":
        db.close()
        if _team_upsert(tid) is None:
            flash("Non trovato", "error")
            return redirect(url_for("pokemon.pokemon"))
        flash("Aggiornato!", "success")
        return redirect(url_for("pokemon.team_edit", tid=tid))

    reg_id = dict(team).get("regulation_id") or regulation_default()
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    roster = _load_roster(reg)
    mega_map = _load_mega_map(reg)
    mega_list = sorted(set(m for v in mega_map.values() for m in v))
    db.close()

    return render_template(
        "team_form.html",
        team=team,
        members=members,
        roster=roster,
        mega_map=mega_map,
        natures=NATURES,
        nature_effects=NATURE_EFFECTS,
        mega_list=mega_list,
        items_data=load_items(reg_id),
        moves_data=load_moves(reg_id),
        regulations=regs,
        current_reg=reg
    )


@bp.route("/team/<int:tid>/delete", methods=["POST"])
@login_required
def team_delete(tid):
    db = get_db()
    cond, par = ambito_utente()
    cur = db.execute(f"DELETE FROM teams WHERE id=? AND {cond}", (tid,) + tuple(par))
    db.commit()
    db.close()
    # I membri se ne vanno con la cascata della chiave esterna, che `get_db()`
    # accende con PRAGMA foreign_keys.
    if cur.rowcount == 0:
        flash("Non trovato", "error")
    else:
        flash("Eliminato", "success")
    return redirect(url_for("pokemon.pokemon"))


@bp.route("/calcolatori")
@login_required
def calcolatori():
    reg_id = request.args.get("reg") or regulation_default()
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])

    roster = _load_roster(reg)
    mega_map = _load_mega_map(reg)
    mega_list = sorted(set(m for v in mega_map.values() for m in v))

    # Lista completa per la combobox: roster + mega + tutte le forme del catalogo
    catalogo_reg = _pokemon_regulation(reg_id)
    roster_calc = _build_full_roster(roster, mega_map, catalogo_reg)

    ab_data = load_abilities()

    return render_template(
        "calcolatori.html",
        roster=roster_calc,
        roster_calc=roster_calc,
        # nome da mostrare nelle tendine, nella lingua attiva
        nomi_vis=_nomi_visualizzati(catalogo_reg),
        natures=NATURES,
        nature_effects=NATURE_EFFECTS,
        # Catalogo ristretto alla regulation attiva: con MA la pagina resta piccola,
        # con Pokedex è grande perché contiene tutto.
        champions_bst=json.dumps(catalogo_reg or {}, ensure_ascii=False),
        mega_list=mega_list,
        items_data=load_items(reg_id),
        moves_data=load_moves(reg_id),
        current_reg=reg,
        regulations=regs,
        # Le tendine abilità sono popolate lato JS da ABILITIES_DATA
        abilities_data=json.dumps(ab_data.get("abilities", {}), ensure_ascii=False),
    )

@bp.route("/roster", methods=["GET", "POST"])
@login_required
def roster_editor():
    reg_id = request.args.get("reg") or regulation_default()
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    migrata = _load_filtro(reg) is not None
    path = os.path.join(DATA_DIR, reg.get("roster_file") or f"roster_{reg_id}.json")

    if request.method == "POST":
        try:
            data = json.loads(request.form.get("roster_json", ""))
            if "pokemon" not in data:
                flash("JSON non valido: manca la chiave 'pokemon'", "error")
                return redirect(url_for("pokemon.roster_editor", reg=reg_id))
            if migrata:
                # regulation migrata: il roster è l'elenco di nomi nel filtro
                _salva_filtro(reg, "pokemon", data["pokemon"])
                if "mega_map" in data:
                    _salva_filtro(reg, "mega_map", None)  # placeholder, riscritto sotto
                    percorso = os.path.join(DATA_DIR, reg["filter_file"])
                    with open(percorso, encoding="utf-8") as f:
                        filtro = json.load(f)
                    filtro["mega_map"] = data["mega_map"]
                    with open(percorso, "w", encoding="utf-8") as f:
                        json.dump(filtro, f, ensure_ascii=False, indent=2)
            else:
                data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False, indent=2)
            flash(f"Roster aggiornato: {len(data['pokemon'])} Pokémon", "success")
        except json.JSONDecodeError as e:
            flash(f"Errore JSON: {e}", "error")
        return redirect(url_for("pokemon.roster_editor", reg=reg_id))

    if migrata:
        roster_data = {
            "regulation": reg.get("label", reg_id),
            "pokemon": _load_roster(reg),
            "mega_map": _load_mega_map(reg),
        }
        roster_json = json.dumps(roster_data, ensure_ascii=False, indent=2)
    else:
        try:
            with open(path, encoding="utf-8") as fh:
                roster_json = fh.read()
                roster_data = json.loads(roster_json)
        except Exception:
            roster_json = "{}"
            roster_data = {}

    return render_template(
        "roster_editor.html",
        roster_json=roster_json,
        roster_data=roster_data,
        current_reg=reg,
        regulations=regs
    )

@bp.route("/roster/archive", methods=["POST"])
@login_required
def roster_archive():
    path = os.path.join(DATA_DIR, "roster_ma.json")
    archive_dir = os.path.join(DATA_DIR, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        reg = data.get("regulation", "MA").replace(" ", "_")
        archive_name = f"roster_{reg}_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(os.path.join(archive_dir, archive_name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        flash(f"Roster archiviato come '{archive_name}'", "success")
    except Exception as e:
        flash(f"Errore archivio: {e}", "error")
    return redirect(url_for("pokemon.roster_editor"))


@bp.route("/roster/archives")
@login_required
def roster_archives():
    archive_dir = os.path.join(DATA_DIR, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    files = sorted(
        [f for f in os.listdir(archive_dir) if f.startswith("roster_")],
        reverse=True
    )
    archives = []
    for fn in files:
        try:
            with open(os.path.join(archive_dir, fn), encoding="utf-8") as f:
                d = json.load(f)
            archives.append({
                "filename": fn,
                "regulation": d.get("regulation", "?"),
                "last_updated": d.get("last_updated", "?"),
                "count": len(d.get("pokemon", []))
            })
        except Exception:
            pass
    return json.dumps(archives), 200, {"Content-Type": "application/json"}


@bp.route("/roster/restore/<path:filename>", methods=["POST"])
@login_required
def roster_restore(filename):
    archive_dir = os.path.join(DATA_DIR, "archive")
    path = os.path.join(DATA_DIR, "roster_ma.json")
    try:
        with open(path, encoding="utf-8") as f:
            current = json.load(f)
        reg = current.get("regulation", "MA").replace(" ", "_")
        backup_name = f"roster_{reg}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_backup.json"
        with open(os.path.join(archive_dir, backup_name), "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=False)
        with open(os.path.join(archive_dir, filename), encoding="utf-8") as f:
            data = json.load(f)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        flash(f"Roster ripristinato da '{filename}' (backup: {backup_name})", "success")
    except Exception as e:
        flash(f"Errore ripristino: {e}", "error")
    return redirect(url_for("pokemon.roster_editor"))


@bp.route("/mosse/archive", methods=["POST"])
@login_required
def moves_archive():
    archive_dir = os.path.join(DATA_DIR, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    try:
        moves_data = load_moves()
        reg = moves_data.get("regulation", "MA").replace(" ", "_")
        archive_name = f"moves_{reg}_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(os.path.join(archive_dir, archive_name), "w", encoding="utf-8") as f:
            json.dump(moves_data, f, ensure_ascii=False, indent=2)
        flash(f"Mosse archiviate come '{archive_name}'", "success")
    except Exception as e:
        flash(f"Errore archivio mosse: {e}", "error")
    return redirect(url_for("pokemon.moves_editor"))


@bp.route("/mosse", methods=["GET", "POST"])
@login_required
def moves_editor():
    reg_id = request.args.get("reg") or regulation_default()
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    migrata = _load_filtro(reg) is not None
    path = os.path.join(DATA_DIR, reg.get("moves_file") or f"moves_{reg_id}.json")

    if request.method == "POST":
        try:
            data = json.loads(request.form.get("moves_json", ""))
            if migrata:
                # Regulation migrata: qui si sceglie QUALI mosse ne fanno parte.
                # I dati (potenza, tipo, descrizione) stanno nel catalogo.
                nomi = list((data or {}).get("moves") or {})
                _salva_filtro(reg, "moves", nomi)
                flash(f"✅ Mosse della regulation: {len(nomi)}. "
                      "I dati delle mosse si modificano nel catalogo.", "success")
            else:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                flash("✅ Mosse aggiornate!", "success")
        except Exception as e:
            flash(f"❌ JSON non valido: {e}", "error")
        return redirect(url_for("pokemon.moves_editor", reg=reg_id))

    moves_data = load_moves(reg_id)
    return render_template(
        "moves_editor.html",
        moves_data=moves_data,
        moves_json=json.dumps(moves_data, ensure_ascii=False, indent=2),
        current_reg=reg,
        regulations=regs
    )


@bp.route("/oggetti/archive", methods=["POST"])
@login_required
def items_archive():
    archive_dir = os.path.join(DATA_DIR, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    try:
        idata = load_items()
        reg = idata.get("regulation", "MA").replace(" ", "_")
        archive_name = f"items_{reg}_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(os.path.join(archive_dir, archive_name), "w", encoding="utf-8") as f:
            json.dump(idata, f, ensure_ascii=False, indent=2)
        flash(f"📦 Oggetti archiviati come {archive_name}", "success")
    except Exception as e:
        flash(f"❌ Errore archivio: {e}", "error")
    return redirect(url_for("pokemon.items_editor"))


@bp.route("/oggetti", methods=["GET", "POST"])
@login_required
def items_editor():
    reg_id = request.args.get("reg") or regulation_default()
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    migrata = _load_filtro(reg) is not None
    path = os.path.join(DATA_DIR, reg.get("items_file") or f"items_{reg_id}.json")

    if request.method == "POST":
        try:
            data = json.loads(request.form.get("items_json", ""))
            if migrata:
                # Come per le mosse: qui si sceglie quali oggetti fanno parte della
                # regulation; `modifier` ed `effect` stanno nel catalogo.
                nomi = list((data or {}).get("items") or {})
                _salva_filtro(reg, "items", nomi)
                flash(f"✅ Oggetti della regulation: {len(nomi)}. "
                      "I dati degli oggetti si modificano nel catalogo.", "success")
            else:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                flash("✅ Oggetti aggiornati!", "success")
        except Exception as e:
            flash(f"❌ JSON non valido: {e}", "error")
        return redirect(url_for("pokemon.items_editor", reg=reg_id))

    idata = load_items(reg_id)
    return render_template(
        "items_editor.html",
        items=idata.get("items", {}),
        items_json=json.dumps(idata, ensure_ascii=False, indent=2),
        current_reg=reg,
        regulations=regs,
        # ⚠️ Le categorie che i dati usano **davvero**, contate qui e non scritte a
        # mano: la tendina dei filtri offriva tutte e 14 quelle di `CATEGORIE_OGGETTI`,
        # e **7 non hanno nemmeno una voce** (`conditional`, `damage`, `defensive`,
        # `orb`, `support`, `terrain`, `weather`). Sceglierle dava sempre zero
        # risultati, che a schermo somiglia a un guasto. La tendina del **modulo**
        # invece resta completa: e' da la' che una categoria vuota si riempie.
        categorie_presenti=sorted({(v.get("category") or "") for v in
                                   (idata.get("items") or {}).values()} - {""}),
    )

@bp.route("/regulations")
@login_required
def regulations_list():
    regs = _list_regulation_files()
    db = get_db()
    for reg in regs:
        reg["teams_count"] = db.execute(
            "SELECT COUNT(*) FROM teams WHERE regulation_id=?", (reg["id"],)
        ).fetchone()[0]
        # ⚠️ Dagli stessi loader dell'editor, non dai file vecchi. Fino al 10/09/2026
        # questa pagina leggeva `roster_file`/`moves_file`/`items_file`: su MA diceva
        # **208** Pokémon e **461** mosse invece di 279 e 460, e su MB, Pokedex e su
        # qualunque regulation creata da qui — che quei file non li ha mai avuti —
        # diceva **0 su tutto**, anche piena. Numeri sbagliati, nessun errore.
        reg["roster_count"] = len(_load_roster(reg))
        reg["moves_count"]  = len(load_moves(reg["id"]).get("moves", {}))
        reg["items_count"]  = len(load_items(reg["id"]).get("items", {}))
        reg["moveset"]      = sorgente_moveset(reg)
    db.close()
    return render_template("regulations_list.html", regulations=regs,
                           sorgenti_mosse=sorgenti_moveset())


@bp.route("/regulation/<reg_id>")
@login_required
def regulation_editor(reg_id):
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), None)
    if not reg:
        flash("Regulation non trovata", "error")
        return redirect(url_for("pokemon.regulations_list"))

    # Conteggi dai loader, così valgono sia per le regulation migrate
    # (elenchi di nomi sul catalogo) sia per quelle ancora sui file vecchi.
    def _count(fld, sub):
        if sub == "moves":
            return len(load_moves(reg_id).get("moves", {}))
        if sub == "items":
            return len(load_items(reg_id).get("items", {}))
        return len(_load_roster(reg))

    roster = _load_roster(reg)

    db = get_db()
    teams = db.execute(
        "SELECT id, name, format, record FROM teams WHERE regulation_id=? ORDER BY created_at DESC",
        (reg_id,)
    ).fetchall()
    db.close()

    return render_template(
        "regulation_editor.html",
        reg=reg,
        roster=roster,
        roster_count=_count("roster_file", "pokemon"),
        moves_count=_count("moves_file", "moves"),
        items_count=_count("items_file", "items"),
        teams_count=len(teams),
        teams=teams,
        regulations=regs,
        moveset=sorgente_moveset(reg),
        sorgenti_mosse=sorgenti_moveset(),
    )
