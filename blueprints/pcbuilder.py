import re
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import (get_db, login_required, _i, _f,
                        ambito_utente, utente_id, e_admin)
from data import PC_CATEGORIES
import pc_catalogo
import pc_negozi

bp = Blueprint("pcbuilder", __name__, url_prefix="/pcbuilder")


def _numero(v):
    """Un prezzo facoltativo: `None` se il campo è vuoto o non è un numero.

    Non `_f()`, che ripiega su 0: una soglia a 0 vorrebbe dire «avvisami quando è
    gratis», e un valore da usato a 0 «non vale niente» — tutti e due falsi."""
    try:
        n = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


@bp.route("/")
@login_required
def pcbuilder():
    db = get_db(); builds = []; mie = []
    # L'admin vede le build di tutti, con scritto di chi sono e la tendina
    # `?utente=` per isolarne una; gli altri vedono le proprie.
    di = _i(request.args.get("utente")) or None
    cond, par = ambito_utente(di=di)
    for b in db.execute(
            f"SELECT * FROM pc_builds WHERE {cond} ORDER BY created_at DESC", par).fetchall():
        comps = db.execute("SELECT * FROM pc_components WHERE build_id=? ORDER BY category",
                           (b["id"],)).fetchall()
        # dict(b), non la Row: il template la passa a |tojson nell'onclick di
        # "Modifica", e una sqlite3.Row non è serializzabile — con una build
        # salvata la pagina rispondeva 500. Stesso motivo per cui pokemon()
        # costruisce teams_json con dict().
        componenti = [dict(c) for c in comps]
        for c in componenti:
            # Il nome del pezzo di catalogo, per vederlo in tabella e nel modulo. Se il
            # catalogo non c'è (mai scaricato, o cache cancellata) il collegamento resta:
            # si ritrova al prossimo «Aggiorna catalogo».
            v = pc_catalogo.pezzo(c.get("opendb_id"))
            c["opendb_nome"] = v["nome"] if v else None
        link = {c["id"]: pc_negozi.link(c) for c in componenti}
        # Il totale è quello che la build costa o è costata: un pezzo venduto non c'è più.
        # Stessa regola della Dashboard.
        attivi = [c for c in componenti if c.get("stato") != "venduto"]
        builds.append({"data": dict(b), "components": componenti, "link": link,
                        "confronti": pc_negozi.confronti(componenti),
                        "total": sum(c["price"] or 0 for c in attivi),
                        "da_comprare": sum(c["price"] or 0 for c in attivi
                                           if c.get("stato") == "desiderato"),
                        "compatibilita": pc_catalogo.controlli(componenti)})
        # Gli avvisi sono di chi guarda: l'admin che vede tutte le build non deve
        # sentirsi dire che la wishlist di un altro è da ricontrollare.
        if b["user_id"] == utente_id():
            mie += [{**c, "build": b["name"], "link_negozi": link[c["id"]]}
                    for c in componenti]
    nomi_utenti = {r["id"]: r["username"] for r in
                   db.execute("SELECT id, username FROM users")} if e_admin() else {}
    proprietari = []
    if e_admin():
        proprietari = [dict(r) for r in db.execute(
            "SELECT u.id, u.username, COUNT(b.id) AS quanti FROM users u "
            "JOIN pc_builds b ON b.user_id=u.id GROUP BY u.id, u.username "
            "ORDER BY u.username").fetchall()]
    db.close()
    return render_template("pcbuilder.html", builds=builds, categories=PC_CATEGORIES,
                           proprietari=proprietari, filtro_utente=di,
                           nomi_utenti=nomi_utenti, avvisi=pc_negozi.avvisi(mie),
                           stati=pc_negozi.STATI,
                           giorni_promemoria=pc_negozi.GIORNI_PROMEMORIA,
                           catalogo=(pc_catalogo.carica() or {}).get("_meta"),
                           cat_catalogo=sorted(set(pc_catalogo.CATEGORIE.values())),
                           fonte={"nome": pc_catalogo.FONTE, "url": pc_catalogo.FONTE_URL,
                                  "licenza": pc_catalogo.LICENZA,
                                  "licenza_url": pc_catalogo.LICENZA_URL},
                           margine=round((pc_catalogo.MARGINE_ALIMENTATORE - 1) * 100))


# I campi di una riga componente, nell'ordine in cui il form li manda. Tutti devono
# arrivare lo stesso numero di volte: `zip()` taglierebbe in silenzio alla lista più
# corta, e i pezzi in fondo sparirebbero senza errore.
CAMPI_RIGA = ("comp_cat", "comp_name", "comp_price", "comp_notes", "comp_stato",
              "comp_obiettivo", "comp_usato", "comp_price_prev", "comp_price_date",
              "comp_usato_prev", "comp_usato_date", "comp_link_amazon",
              "comp_link_eprice", "comp_link_bpm", "comp_link_versus", "comp_opendb")


@bp.route("/save", methods=["POST"])
@login_required
def pcbuilder_save():
    f = request.form; bid = _i(f.get("build_id", 0))
    colonne = {k: f.getlist(k) for k in CAMPI_RIGA}
    if len({len(v) for v in colonne.values()}) > 1:
        # Si esce **prima** di toccare il DB: con le liste sfasate un pezzo prenderebbe
        # il prezzo o il link di un altro.
        flash("Componenti non salvati: il modulo è arrivato incompleto. Ricarica la pagina.",
              "error")
        return redirect(url_for("pcbuilder.pcbuilder"))
    db = get_db()
    if bid:
        cond, par = ambito_utente()
        cur = db.execute(f"UPDATE pc_builds SET name=?,notes=? WHERE id=? AND {cond}",
                         (f.get("build_name", ""), f.get("build_notes", ""), bid) + tuple(par))
        if cur.rowcount == 0:
            # ⚠️ Si esce **prima** del DELETE qui sotto: la build non e' di chi salva,
            # e senza questo ritorno le si svuoterebbero i componenti lo stesso.
            db.close(); flash("Non trovata", "error")
            return redirect(url_for("pcbuilder.pcbuilder"))
    else:
        cur = db.execute("INSERT INTO pc_builds(name,notes,user_id) VALUES(?,?,?)",
                         (f.get("build_name", "Nuova Build"), f.get("build_notes", ""),
                          utente_id()))
        bid = cur.lastrowid
    db.execute("DELETE FROM pc_components WHERE build_id=?", (bid,))
    oggi = date.today(); scartati = []; scartati_cat = []
    for riga in zip(*(colonne[k] for k in CAMPI_RIGA)):
        r = dict(zip(CAMPI_RIGA, riga))
        name = r["comp_name"]
        if not name.strip():
            continue
        prezzo, usato = _f(r["comp_price"]), _numero(r["comp_usato"])
        stato = r["comp_stato"] if r["comp_stato"] in pc_negozi.STATI else None
        link = {}
        for campo in pc_negozi.NEGOZI:
            grezzo = r["comp_" + campo].strip()
            link[campo] = pc_negozi.link_valido(campo, grezzo)
            if grezzo and not link[campo]:
                scartati.append(f"{name.strip()} ({pc_negozi.NEGOZI[campo][0]})")
        # Il collegamento al catalogo si tiene solo se il pezzo esiste ed è della stessa
        # categoria: una RAM collegata a una scheda madre darebbe controlli senza senso.
        # Senza catalogo non si può verificare, e il collegamento di prima si lascia com'è.
        opendb = r["comp_opendb"].strip() or None
        if opendb and pc_catalogo.carica():
            v = pc_catalogo.pezzo(opendb)
            if not v or v["cat"] != r["comp_cat"]:
                scartati_cat.append(name.strip())
                opendb = None
        # ⚠️ Le date dei prezzi passano dal form: questa funzione ricrea i pezzi a ogni
        # salvataggio, e senza la data di prima il promemoria non scatterebbe mai.
        db.execute(
            "INSERT INTO pc_components(build_id,category,name,price,notes,stato,prezzo_data,"
            "obiettivo,valore_usato,valore_usato_data,link_amazon,link_eprice,link_bpm,"
            "link_versus,opendb_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (bid, r["comp_cat"], name, prezzo, r["comp_notes"], stato,
             pc_negozi.data_valore(prezzo, _numero(r["comp_price_prev"]),
                                   r["comp_price_date"], oggi),
             _numero(r["comp_obiettivo"]), usato,
             pc_negozi.data_valore(usato, _numero(r["comp_usato_prev"]),
                                   r["comp_usato_date"], oggi),
             link["link_amazon"], link["link_eprice"], link["link_bpm"],
             link["link_versus"], opendb))
    db.commit(); db.close()
    flash("Build salvata", "success")
    if scartati:
        # Detto, non taciuto: un link che sparisce senza spiegazione sembra un baco.
        flash("Link non salvati perché non sono del negozio giusto o non cominciano per "
              "http(s): " + ", ".join(scartati), "error")
    if scartati_cat:
        flash("Collegamento al catalogo tolto perché il pezzo non è della stessa categoria: "
              + ", ".join(scartati_cat), "error")
    return redirect(url_for("pcbuilder.pcbuilder"))


@bp.route("/api/catalogo")
@login_required
def api_catalogo():
    """La ricerca nel catalogo dei pezzi, per collegare un componente al suo modello."""
    cat = request.args.get("cat", "")
    if cat not in pc_catalogo.CATEGORIE.values():
        return jsonify({"ok": False, "errore": "categoria senza catalogo", "risultati": []})
    if not pc_catalogo.carica():
        return jsonify({"ok": False, "errore": "catalogo non scaricato: premi «Aggiorna catalogo»",
                        "risultati": []})
    return jsonify({"ok": True, "risultati": pc_catalogo.cerca(cat, request.args.get("q", ""))})


@bp.route("/catalogo/aggiorna", methods=["POST"])
@login_required
def catalogo_aggiorna():
    """Scarica OpenDB (~46 MB) e riscrive l'indice. Come la cache IGDB del Gaming: lo
    preme chi usa la sezione, quando vuole, e il catalogo è di tutti."""
    try:
        conti = pc_catalogo.aggiorna()
    except Exception as e:                      # rete, zip, o conti che non tornano
        flash(f"Catalogo non aggiornato: {e}. Quello di prima resta com'era.", "error")
    else:
        flash("Catalogo aggiornato: " + ", ".join(f"{n} {c}" for c, n in conti.items()),
              "success")
    return redirect(url_for("pcbuilder.pcbuilder"))


@bp.route("/componente/<int:cid>/ricontrollato", methods=["POST"])
@login_required
def pcbuilder_ricontrollato(cid):
    """«L'ho ricontrollato, il prezzo è ancora quello»: sposta la data a oggi senza
    cambiare il valore. Senza questo, un prezzo stabile resterebbe nel promemoria finché
    non lo si riscrive diverso."""
    db = get_db()
    cond, par = ambito_utente()
    oggi = date.today().isoformat()
    cur = db.execute(
        "UPDATE pc_components SET "
        "prezzo_data = CASE WHEN stato='desiderato' AND price>0 THEN ? ELSE prezzo_data END, "
        "valore_usato_data = CASE WHEN stato='posseduto' AND valore_usato>0 THEN ? "
        "ELSE valore_usato_data END "
        f"WHERE id=? AND build_id IN (SELECT id FROM pc_builds WHERE {cond})",
        (oggi, oggi, cid) + tuple(par))
    db.commit(); db.close()
    flash("Segnato come ricontrollato oggi" if cur.rowcount else "Non trovato",
          "success" if cur.rowcount else "error")
    return redirect(url_for("pcbuilder.pcbuilder"))


@bp.route("/<int:bid>/delete", methods=["POST"])
@login_required
def pcbuilder_delete(bid):
    db = get_db()
    cond, par = ambito_utente()
    cur = db.execute(f"DELETE FROM pc_builds WHERE id=? AND {cond}", (bid,) + tuple(par))
    db.commit(); db.close()
    flash("Eliminata" if cur.rowcount else "Non trovata",
          "success" if cur.rowcount else "error")
    return redirect(url_for("pcbuilder.pcbuilder"))


@bp.route("/import_dxdiag", methods=["POST"])
@login_required
def import_dxdiag():
    content = request.form.get("dxdiag_text", "")
    if not content:
        return jsonify({"ok": False, "error": "Nessun contenuto"})
    componenti, note = _parse_dxdiag(content)
    return jsonify({"ok": True, "components": componenti, "note": note})


# La grafica integrata nella CPU, riconosciuta dal nome: nel DxDiag non c'è un campo che
# la distingua con certezza (misurato il 25/09/2026 sul PC di Davide: la 4070 Ti e la
# Radeon del 7800X3D sono tutte e due «Full Device»). ⚠️ È un elenco di nomi, quindi una
# grafica integrata con un nome nuovo passa come GPU: per questo il modale **mostra** cosa
# è stato scartato, e una scartata a torto si rimette a mano.
GRAFICA_INTEGRATA = re.compile(
    r"^(AMD Radeon\(TM\)( Vega \d+)? Graphics|AMD Radeon Graphics"
    r"|Intel\(R\) (UHD|HD|Iris\(R\) Xe|Iris\(R\) Plus|Iris\(R\)) Graphics.*)$", re.I)


def _pulisci_cpu(nome):
    """`AMD Ryzen 7 7800X3D 8-Core Processor   (16 CPUs), ~4.2GHz` → `AMD Ryzen 7 7800X3D`.

    Il nome pulito è quello che la ricerca nel catalogo trova: con «8-Core Processor» e
    «(16 CPUs)» dentro, tutte le parole non le ha nessun pezzo."""
    n = re.sub(r"\(\d+ CPUs\).*$", "", nome)          # «(16 CPUs), ~4.2GHz»
    n = re.sub(r"\s+CPU\s*@.*$", "", n)                # Intel: «CPU @ 3.60GHz»
    n = re.sub(r"\s+\d+-Core Processor\s*$", "", n.strip(), flags=re.I)
    n = re.sub(r"\((R|TM)\)", "", n, flags=re.I)
    return re.sub(r"\s+", " ", n).strip()


def _parse_dxdiag(text):
    """I pezzi che un DxDiag.txt dice davvero, più le note su quello che non dice.

    ⚠️ **Il DxDiag non riporta la scheda madre.** Ha `System Manufacturer` e `System Model`,
    che sono il **sistema**: su un PC assemblato ASUS lascia il segnaposto «System Product
    Name», su un PC di marca c'è il modello del computer. Fino al 25/09/2026 quel campo
    diventava una «Motherboard», ed è così che la build di Davide aveva una scheda madre
    chiamata «System Product Name»."""
    results = []; note = []; lines = text.splitlines()

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
    if cpu:
        results.append({"category": "CPU", "name": _pulisci_cpu(cpu)[:120], "price": 0,
                        "notes": ""})
    # `^\s*Memory:` e non `Memory:`: «Available OS Memory» e «Display Memory» contengono
    # la stessa parola.
    ram = find([r"^\s*Memory:\s*(.+)"])
    if ram:
        m = re.match(r"(\d+)\s*MB RAM", ram, re.I)
        nome = f"{int(m.group(1)) // 1024} GB" if m else ram[:80]
        results.append({"category": "RAM", "name": nome, "price": 0,
                        "notes": "dal DxDiag: tipo e modello non indicati"})
    seen_gpu = set()
    for line in lines:
        m = re.match(r"\s*Card name[^:]*:\s*(.+)", line, re.I)
        if m:
            g = m.group(1).strip()
            if any(x in g.lower() for x in ["n/a", "not available", "unknown", "microsoft", "basic"]):
                continue
            if GRAFICA_INTEGRATA.match(g):
                if g not in seen_gpu:
                    seen_gpu.add(g)
                    note.append(f"Scartata «{g}»: è la grafica integrata nella CPU, non una "
                                "scheda video. Se è l'unica che hai, aggiungila a mano.")
                continue
            if g not in seen_gpu and len(g) > 4:
                seen_gpu.add(g)
                results.append({"category": "GPU", "name": g[:120], "price": 0, "notes": ""})
            if sum(1 for r in results if r["category"] == "GPU") >= 2:
                break
    produttore = find([r"System Manufacturer[^:]*:\s*(.+)"])
    note.append("Scheda madre: il DxDiag non la riporta" +
                (f" (dice solo il produttore del sistema, {produttore})" if produttore else "") +
                ". Aggiungila a mano, col modello scritto sulla scheda o nel BIOS.")
    return results, note