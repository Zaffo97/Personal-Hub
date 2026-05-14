import json
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import get_db, login_required, _i
from data import (
    DATA_DIR,
    REG_MA_ROSTER,
    MEGA_EVOLUTIONS_MA,
    NATURES,
    NATURE_EFFECTS,
    CHAMPIONS_BST
)

def load_items():
    return {}

TYPE_TABLE_HTML = ""
NATURE_TABLE_HTML = ""

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
    try:
        with open(os.path.join(DATA_DIR, reg["roster_file"]), encoding="utf-8") as f:
            return sorted(json.load(f).get("pokemon", []))
    except Exception:
        return sorted(REG_MA_ROSTER)


def _load_mega_map(reg):
    """Carica la mega_map dal roster file della regulation."""
    try:
        with open(os.path.join(DATA_DIR, reg["roster_file"]), encoding="utf-8") as f:
            return json.load(f).get("mega_map", {})
    except Exception:
        return {}


def _build_full_roster(roster, mega_map):
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

    # Aggiungi tutte le forme (forms) presenti nel catalogo
    for poke_data in CHAMPIONS_BST.values():
        for form_name in poke_data.get("forms", {}).keys():
            all_names.add(form_name)

    return sorted(all_names)


def load_moves(reg_id="ma"):
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    try:
        with open(os.path.join(DATA_DIR, reg["moves_file"]), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"moves": {}, "regulation": reg["label"], "last_updated": ""}


def load_items(reg_id="ma"):
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
        f.get("regulation_id", "ma"),
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

    reg_id = request.args.get("regulation_id", "ma")
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

    reg_id = dict(team).get("regulation_id", "ma") or "ma"
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
    reg_id = request.args.get("reg", "ma")
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])

    roster = _load_roster(reg)
    mega_map = _load_mega_map(reg)
    mega_list = sorted(set(m for v in mega_map.values() for m in v))

    # Lista completa per la combobox: roster + mega + tutte le forme del catalogo
    roster_calc = _build_full_roster(roster, mega_map)

    return render_template(
        "calcolatori.html",
        pkmn_db=CHAMPIONS_BST,
        roster=roster_calc,
        roster_calc=roster_calc,
        natures=NATURES,
        nature_effects=NATURE_EFFECTS,
        champions_bst=json.dumps(CHAMPIONS_BST or {}),
        mega_list=mega_list,
        speed_tier_data=[],
        type_table=TYPE_TABLE_HTML or "",
        nature_table=NATURE_TABLE_HTML or "",
        items_data=load_items(reg_id),
        moves_data=load_moves(reg_id),
        current_reg=reg,
        regulations=regs
    )

@bp.route("/roster", methods=["GET", "POST"])
@login_required
def roster_editor():
    reg_id = request.args.get("reg", "ma")
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    path = os.path.join(DATA_DIR, reg["roster_file"])

    if request.method == "POST":
        try:
            data = json.loads(request.form.get("roster_json", ""))
            if "pokemon" not in data:
                flash("JSON non valido: manca la chiave 'pokemon'", "error")
                return redirect(url_for("pokemon.roster_editor", reg=reg_id))
            data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            flash(f"Roster aggiornato: {len(data['pokemon'])} Pokémon", "success")
        except json.JSONDecodeError as e:
            flash(f"Errore JSON: {e}", "error")
        return redirect(url_for("pokemon.roster_editor", reg=reg_id))

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
    reg_id = request.args.get("reg", "ma")
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    path = os.path.join(DATA_DIR, reg["moves_file"])

    if request.method == "POST":
        try:
            data = json.loads(request.form.get("moves_json", ""))
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
    reg_id = request.args.get("reg", "ma")
    regs = _list_regulation_files()
    reg = next((r for r in regs if r["id"] == reg_id), regs[0])
    path = os.path.join(DATA_DIR, reg["items_file"])

    if request.method == "POST":
        try:
            data = json.loads(request.form.get("items_json", ""))
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

    def _count(fld, sub):
        try:
            with open(os.path.join(DATA_DIR, reg[fld]), encoding="utf-8") as f:
                return len(json.load(f).get(sub, {}))
        except Exception:
            return 0

    roster = []
    try:
        with open(os.path.join(DATA_DIR, reg["roster_file"]), encoding="utf-8") as f:
            roster = sorted(json.load(f).get("pokemon", []))
    except Exception:
        pass

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
