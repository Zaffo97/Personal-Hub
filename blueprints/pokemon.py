import json
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import get_db, login_required, _i, nome_vis
from data import (
    DATA_DIR,
    regulation_default,
    REG_MA_ROSTER,
    MEGA_EVOLUTIONS_MA,
    NATURES,
    NATURE_EFFECTS,
    CHAMPIONS_BST,
)

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
    449 KB di catalogo quando servono quattro campi per riga."""
    if db == "pokemon":
        bs = voce.get("base_stats") or {}
        return {"nome": voce.get("name") or nome, "chiave": nome,
                "info": " · ".join(voce.get("types") or []),
                "numero": sum(bs.values()) if bs else 0,
                "extra": f"{len(voce.get('forms') or {})} forme" if voce.get("forms") else ""}
    if db == "moves":
        return {"nome": nome, "chiave": nome,
                "info": f"{voce.get('type', '')} · {voce.get('category', '')}",
                "numero": voce.get("bp") or 0,
                "extra": ", ".join(voce.get("flags") or [])}
    if db == "abilities":
        fx = (voce.get("effect") or {}).get("type", "none")
        return {"nome": nome, "chiave": nome, "info": voce.get("category", ""),
                "numero": 0, "extra": "" if fx == "none" else f"● {fx}"}
    return {"nome": nome, "chiave": nome, "info": voce.get("category", ""),
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
        db.execute(
            "UPDATE teams SET name=?,format=?,record=?,description=?,notes=?,regulation_id=? WHERE id=?",
            vals + (tid,)
        )
    else:
        cur = db.execute(
            "INSERT INTO teams(name,format,record,description,notes,regulation_id) VALUES(?,?,?,?,?,?)",
            vals
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
    campi = payload.get("campi") or ["pokemon", "moves", "items", "abilities", "mega_map"]
    percorso = os.path.join(DATA_DIR, reg["filter_file"])
    with open(percorso, encoding="utf-8") as f:
        filtro = json.load(f)

    copiati = {}
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

    voci = voci_catalogo(db)
    if nome_originale and nome_originale != nome:
        voci.pop(nome_originale, None)      # rinomina
    elif not nome_originale and nome in voci:
        return jsonify({"ok": False, "error": f"'{nome}' esiste già"}), 400
    voci[nome] = voce
    salva_catalogo(db, voci)
    return jsonify({"ok": True, "totale": len(voci),
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
    }
    regs.append(new_reg)
    _save_regulations(regs)

    return jsonify({"ok": True, "regulation": new_reg, "partenza": partenza}), 201


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

    # Elimina i file JSON associati (roster, mosse, oggetti)
    deleted_files = []
    for key in ("roster_file", "moves_file", "items_file"):
        fpath = os.path.join(DATA_DIR, reg.get(key, ""))
        if os.path.isfile(fpath):
            try:
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
    teams = []
    for t in db.execute("SELECT * FROM teams ORDER BY created_at DESC").fetchall():
        members = db.execute(
            "SELECT * FROM team_members WHERE team_id=? ORDER BY slot",
            (t["id"],)
        ).fetchall()
        teams.append({"data": t, "members": list(members)})
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
    return render_template("pokemon.html", teams=teams, teams_json=teams_json)


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
    team = db.execute("SELECT * FROM teams WHERE id=?", (tid,)).fetchone()
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
        _team_upsert(tid)
        db.close()
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
    db.execute("DELETE FROM teams WHERE id=?", (tid,))
    db.commit()
    db.close()
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
        regulations=regs
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
        for key, fld, sub in [
            ("roster_count", "roster_file", "pokemon"),
            ("moves_count",  "moves_file",  "moves"),
            ("items_count",  "items_file",  "items"),
        ]:
            try:
                with open(os.path.join(DATA_DIR, reg[fld]), encoding="utf-8") as f:
                    reg[key] = len(json.load(f).get(sub, {}))
            except Exception:
                reg[key] = 0
    db.close()
    return render_template("regulations_list.html", regulations=regs)


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
        regulations=regs
    )
