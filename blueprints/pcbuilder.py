import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import get_db, login_required, _i, _f
from data import PC_CATEGORIES

bp = Blueprint("pcbuilder", __name__, url_prefix="/pcbuilder")


@bp.route("/")
@login_required
def pcbuilder():
    db = get_db(); builds = []
    for b in db.execute("SELECT * FROM pc_builds ORDER BY created_at DESC").fetchall():
        comps = db.execute("SELECT * FROM pc_components WHERE build_id=? ORDER BY category",
                           (b["id"],)).fetchall()
        builds.append({"data": b, "components": [dict(c) for c in comps],
                        "total": sum(c["price"] for c in comps)})
    db.close()
    return render_template("pcbuilder.html", builds=builds, categories=PC_CATEGORIES)


@bp.route("/save", methods=["POST"])
@login_required
def pcbuilder_save():
    f = request.form; bid = _i(f.get("build_id", 0)); db = get_db()
    if bid:
        db.execute("UPDATE pc_builds SET name=?,notes=? WHERE id=?",
                   (f.get("build_name", ""), f.get("build_notes", ""), bid))
    else:
        cur = db.execute("INSERT INTO pc_builds(name,notes) VALUES(?,?)",
                         (f.get("build_name", "Nuova Build"), f.get("build_notes", "")))
        bid = cur.lastrowid
    db.execute("DELETE FROM pc_components WHERE build_id=?", (bid,))
    for cat, name, price, note in zip(
        f.getlist("comp_cat"), f.getlist("comp_name"),
        f.getlist("comp_price"), f.getlist("comp_notes")
    ):
        if name.strip():
            db.execute("INSERT INTO pc_components(build_id,category,name,price,notes)"
                       " VALUES(?,?,?,?,?)", (bid, cat, name, _f(price), note))
    db.commit(); db.close()
    flash("Build salvata", "success"); return redirect(url_for("pcbuilder.pcbuilder"))


@bp.route("/<int:bid>/delete", methods=["POST"])
@login_required
def pcbuilder_delete(bid):
    db = get_db(); db.execute("DELETE FROM pc_builds WHERE id=?", (bid,))
    db.commit(); db.close()
    flash("Eliminata", "success"); return redirect(url_for("pcbuilder.pcbuilder"))


@bp.route("/import_dxdiag", methods=["POST"])
@login_required
def import_dxdiag():
    content = request.form.get("dxdiag_text", "")
    if not content:
        return jsonify({"ok": False, "error": "Nessun contenuto"})
    return jsonify({"ok": True, "components": _parse_dxdiag(content)})


def _parse_dxdiag(text):
    results = []; lines = text.splitlines()

    def find(pats):
        for p in pats:
            for line in lines:
                m = re.search(p, line, re.I)
                if m:
                    v = m.group(1).strip() if m.lastindex else line.split(":", 1)[-1].strip()
                    if v and v.lower() not in ("", "n/a", "not available", "unknown"):
                        return v
        return None

    cpu = find([r"Processor[^:]*:\s*(.+)", r"CPU[^:]*:\s*(.+)"])
    if cpu: results.append({"category": "CPU", "name": cpu[:120], "price": 0, "notes": ""})
    ram = find([r"Memory:\s*(.+)", r"Available OS RAM[^:]*:\s*(.+)"])
    if ram: results.append({"category": "RAM", "name": ram[:80], "price": 0, "notes": ""})
    seen_gpu = set()
    for line in lines:
        m = re.match(r"\s*Card name[^:]*:\s*(.+)", line, re.I)
        if m:
            g = m.group(1).strip()
            if any(x in g.lower() for x in ["n/a", "not available", "unknown", "microsoft", "basic"]):
                continue
            if g not in seen_gpu and len(g) > 4:
                seen_gpu.add(g)
                results.append({"category": "GPU", "name": g[:120], "price": 0, "notes": ""})
            if len(seen_gpu) >= 2:
                break
    mb = find([r"Motherboard[^:]*:\s*(.+)", r"System Model[^:]*:\s*(.+)"])
    if mb: results.append({"category": "Motherboard", "name": mb[:120], "price": 0, "notes": ""})
    return results