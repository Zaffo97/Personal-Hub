import json
import math
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import get_db, login_required, _i, _f, t, tf
from data import GAME_STATUSES, GAME_PLATFORMS

bp = Blueprint("gaming", __name__, url_prefix="/gaming")

# Ordinamenti dell'elenco. Il frammento SQL sta qui e **non** arriva dalla richiesta:
# `sort` e' solo la chiave di questo dizionario, con fallback al default, quindi
# nessuna stringa dell'utente finisce in un ORDER BY.
# `NULLS LAST` non esiste in SQLite: `col IS NULL` prima dell'ordinamento vero tiene
# in fondo i giochi senza ore, che altrimenti aprirebbero l'elenco "per ore giocate".
ORDINAMENTI = {
    # `id DESC` come spareggio: l'import di massa da Steam scrive decine di righe nello
    # stesso secondo, e con `created_at` da solo l'ordine fra quelle e' arbitrario —
    # "aggiunti di recente" mostrava il piu' vecchio per primo.
    "":         "ORDER BY created_at DESC, id DESC",
    "recenti":  "ORDER BY created_at DESC, id DESC",
    "titolo":   "ORDER BY title COLLATE NOCASE ASC",
    "ore":      "ORDER BY hours_played IS NULL, hours_played DESC, title COLLATE NOCASE",
    "ore_asc":  "ORDER BY hours_played IS NULL, hours_played ASC, title COLLATE NOCASE",
    "durata":   "ORDER BY hours_hltb IS NULL, hours_hltb DESC, title COLLATE NOCASE",
}
ETICHETTE_ORDINE = [
    ("recenti", "Aggiunti di recente"),
    ("titolo",  "Titolo A→Z"),
    ("ore",     "Ore giocate ↓"),
    ("ore_asc", "Ore giocate ↑"),
    ("durata",  "Durata stimata ↓"),
]

# --- Steam ------------------------------------------------------------------
# Ricerca e dettagli usano endpoint pubblici: NON richiedono chiave.
# Solo la libreria posseduta con le ore (GetOwnedGames) richiede una chiave,
# letta da STEAM_API_KEY: mai su file, mai in git, mai chiesta in un form.
STEAM_UA      = "personal-hub/1.0"
STEAM_TIMEOUT = 8


def steam_key():
    """Chiave Steam Web API, solo da variabile d'ambiente. Mai su file, mai in git."""
    return os.environ.get("STEAM_API_KEY", "").strip()


def steam_cover(appid):
    """URL copertina 460x215 — deterministico, nessuna chiamata di rete."""
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"


def _steam_json(url):
    """GET su Steam. Ritorna (dati, None) oppure (None, messaggio_errore)."""
    req = urllib.request.Request(url, headers={"User-Agent": STEAM_UA})
    try:
        with urllib.request.urlopen(req, timeout=STEAM_TIMEOUT) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"Steam ha risposto {e.code}"
    except (urllib.error.URLError, socket.timeout):
        return None, "Steam non raggiungibile"
    except json.JSONDecodeError:
        return None, "Risposta di Steam non leggibile"


@bp.route("/api/steam/cerca")
@login_required
def steam_cerca():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"risultati": []})
    url = ("https://store.steampowered.com/api/storesearch/"
           f"?term={urllib.parse.quote(q)}&l=italian&cc=it")
    dati, errore = _steam_json(url)
    if errore:
        return jsonify({"errore": errore}), 502
    risultati = [
        {"appid": it.get("id"), "nome": it.get("name", ""),
         "miniatura": it.get("tiny_image", "")}
        for it in (dati or {}).get("items", [])[:12]
        if it.get("id")
    ]
    return jsonify({"risultati": risultati})


@bp.route("/api/steam/gioco/<int:appid>")
@login_required
def steam_gioco(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=italian&cc=it"
    dati, errore = _steam_json(url)
    if errore:
        return jsonify({"errore": errore}), 502
    voce = (dati or {}).get(str(appid)) or {}
    if not voce.get("success"):
        return jsonify({"errore": "Gioco non trovato su Steam"}), 404
    d = voce.get("data") or {}
    return jsonify({
        "appid":   appid,
        "titolo":  d.get("name", ""),
        "genere":  ", ".join(g["description"] for g in (d.get("genres") or [])),
        "cover":   d.get("header_image") or steam_cover(appid),
        "uscita":  (d.get("release_date") or {}).get("date", ""),
        "tipo":    d.get("type", ""),
    })


def _game_upsert(gid=None):
    f  = request.form
    db = get_db()
    vals = (
        f.get("title", ""), f.get("platform", ""), f.get("genre", ""),
        f.get("status", "Wishlist"),
        _f(f.get("hours_hltb")), f.get("cover_url", "") or None,
        _i(f.get("prog_story")), _i(f.get("prog_side")), _i(f.get("prog_collect")),
        f.get("date_start") or None, f.get("date_end") or None,
        f.get("notes", ""),
        _i(f.get("steam_appid")) or None,
        _f(f.get("hours_played")) or None,
    )
    if gid:
        db.execute(
            "UPDATE games SET title=?,platform=?,genre=?,status=?,"
            "hours_hltb=?,cover_url=?,prog_story=?,prog_side=?,prog_collect=?,"
            "date_start=?,date_end=?,notes=?,steam_appid=?,hours_played=? WHERE id=?",
            vals + (gid,),
        )
    else:
        db.execute(
            "INSERT INTO games(title,platform,genre,status,hours_hltb,cover_url,"
            "prog_story,prog_side,prog_collect,date_start,date_end,notes,steam_appid,"
            "hours_played) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            vals,
        )
    db.commit(); db.close()


def risolvi_profilo(testo):
    """Da quello che l'utente incolla ricava uno steamID64.

    Accetta: 17 cifre, /profiles/<id64>, /id/<nome>, o il nome vanity nudo.
    Ritorna (steamid, None) oppure (None, messaggio_errore).
    """
    t = (testo or "").strip().rstrip("/")
    if not t:
        return None, "Indica il tuo profilo Steam"
    if re.fullmatch(r"\d{17}", t):
        return t, None
    m = re.search(r"/profiles/(\d{17})", t)
    if m:
        return m.group(1), None
    m = re.search(r"/id/([^/?#]+)", t)
    vanity = m.group(1) if m else t
    if not re.fullmatch(r"[A-Za-z0-9_.-]{2,64}", vanity):
        return None, "Profilo non riconosciuto"
    chiave = steam_key()
    if not chiave:
        return None, "Serve STEAM_API_KEY per risolvere un nome profilo"
    dati, errore = _steam_json(
        "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
        f"?key={urllib.parse.quote(chiave)}&vanityurl={urllib.parse.quote(vanity)}")
    if errore:
        return None, errore
    r = (dati or {}).get("response") or {}
    if r.get("success") != 1 or not r.get("steamid"):
        return None, (
            f"'{vanity}' non e' un indirizzo personalizzato Steam. Attenzione: NON e' il "
            "nome che vedi sul profilo, ma la parte finale di steamcommunity.com/id/<...>, "
            "e molti profili non ce l'hanno affatto. Su Steam apri il tuo profilo, tasto "
            "destro sulla pagina, 'Copia URL pagina' e incolla qui l'indirizzo completo: "
            "se contiene /profiles/ funziona subito, non serve nessun nome.")
    return r["steamid"], None


@bp.route("/steam")
@login_required
def steam_pagina():
    return render_template("steam_import.html",
                           chiave_presente=bool(steam_key()),
                           profilo_default=os.environ.get("STEAM_ID", ""))


@bp.route("/api/steam/libreria")
@login_required
def steam_libreria():
    """Giochi posseduti + ore giocate. Unico endpoint che richiede la chiave."""
    if not steam_key():
        return jsonify({"errore": "STEAM_API_KEY non impostata",
                        "manca_chiave": True}), 400
    steamid, errore = risolvi_profilo(request.args.get("profilo", ""))
    if errore:
        return jsonify({"errore": errore}), 400

    dati, errore = _steam_json(
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        f"?key={urllib.parse.quote(steam_key())}&steamid={steamid}"
        "&include_appinfo=1&include_played_free_games=1&format=json")
    if errore:
        return jsonify({"errore": errore}), 502
    risposta = (dati or {}).get("response") or {}
    if "games" not in risposta:
        return jsonify({"errore": "Steam non restituisce la libreria: il profilo e' "
                                  "privato oppure 'Dettagli sui giochi' non e' Pubblico",
                        "profilo_privato": True}), 403

    db = get_db()
    gia = {r["steam_appid"]: r["id"] for r in
           db.execute("SELECT id, steam_appid FROM games WHERE steam_appid IS NOT NULL")}
    db.close()

    giochi = [{
        "appid":     g["appid"],
        "titolo":    g.get("name", ""),
        "ore":       round((g.get("playtime_forever") or 0) / 60, 1),
        "cover":     steam_cover(g["appid"]),
        "gia_in_db": g["appid"] in gia,
    } for g in risposta["games"] if g.get("appid")]
    giochi.sort(key=lambda g: (-g["ore"], g["titolo"].lower()))
    return jsonify({"steamid": steamid, "totale": len(giochi), "giochi": giochi})


@bp.route("/steam/importa", methods=["POST"])
@login_required
def steam_importa():
    """Importa gli appid scelti. Aggiorna le ore se il gioco c'e' gia', non duplica."""
    payload = request.get_json(silent=True) or {}
    scelti  = payload.get("giochi") or []
    if not scelti:
        return jsonify({"errore": "Nessun gioco selezionato"}), 400

    db = get_db()
    esistenti = {r["steam_appid"]: r["id"] for r in
                 db.execute("SELECT id, steam_appid FROM games WHERE steam_appid IS NOT NULL")}
    nuovi = aggiornati = 0
    for g in scelti:
        appid = _i(g.get("appid"))
        if not appid:
            continue
        ore = _f(g.get("ore"))
        # Importare significa "ce l'ho in libreria", non "ci sto giocando": mettere
        # tutto su "In corso" rende inutile il filtro per stato. Sta all'utente
        # promuovere i pochi che sta davvero giocando.
        stato = "Pausa"
        if appid in esistenti:
            db.execute("UPDATE games SET hours_played=? WHERE id=?", (ore, esistenti[appid]))
            aggiornati += 1
        else:
            db.execute(
                "INSERT INTO games(title,platform,status,cover_url,steam_appid,hours_played)"
                " VALUES(?,?,?,?,?,?)",
                (g.get("titolo", "")[:200], "PC", stato, steam_cover(appid), appid, ore))
            nuovi += 1
    db.commit(); db.close()
    return jsonify({"nuovi": nuovi, "aggiornati": aggiornati})


@bp.route("/api/steam/da-arricchire")
@login_required
def steam_da_arricchire():
    """Quanti giochi Steam sono senza genere. Nessuna chiave richiesta."""
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM games WHERE steam_appid IS NOT NULL"
                   " AND (genre IS NULL OR genre='')").fetchone()[0]
    db.close()
    return jsonify({"rimasti": n})


@bp.route("/steam/arricchisci", methods=["POST"])
@login_required
def steam_arricchisci():
    """Riempie il genere dei giochi importati leggendolo da appdetails.

    Endpoint pubblico, nessuna chiave. Lavora a lotti per non tenere impegnata
    la richiesta troppo a lungo: il client richiama finche' 'rimasti' non e' 0.
    """
    LOTTO = 15
    db = get_db()
    da_fare = db.execute(
        "SELECT id, steam_appid FROM games WHERE steam_appid IS NOT NULL"
        " AND (genre IS NULL OR genre='') ORDER BY id LIMIT ?", (LOTTO,)).fetchall()

    fatti = falliti = 0
    errore_rete = None
    for r in da_fare:
        dati, errore = _steam_json(
            "https://store.steampowered.com/api/appdetails"
            f"?appids={r['steam_appid']}&l=italian&cc=it&filters=basic,genres")
        if errore:
            # rete o rate limit: NON marcare il gioco, altrimenti un guasto
            # temporaneo lo escluderebbe per sempre dai tentativi successivi
            errore_rete = errore
            break
        voce   = (dati or {}).get(str(r["steam_appid"])) or {}
        generi = ", ".join(g["description"] for g in
                           ((voce.get("data") or {}).get("genres") or [])) if voce.get("success") else ""
        if generi:
            db.execute("UPDATE games SET genre=? WHERE id=?", (generi, r["id"]))
            fatti += 1
        else:
            # Steam ha risposto ma non ha generi (DLC, software, voce ritirata):
            # segno un trattino per non ripescarlo a ogni lotto
            db.execute("UPDATE games SET genre='—' WHERE id=?", (r["id"],))
            falliti += 1
        time.sleep(0.2)                      # riguardo per il rate limit di Steam
    db.commit()
    rimasti = db.execute("SELECT COUNT(*) FROM games WHERE steam_appid IS NOT NULL"
                         " AND (genre IS NULL OR genre='')").fetchone()[0]
    db.close()
    if errore_rete and not fatti:
        return jsonify({"errore": errore_rete, "rimasti": rimasti}), 502
    return jsonify({"fatti": fatti, "senza_genere": falliti,
                    "rimasti": rimasti, "interrotto": errore_rete})


# --- Tag della community ----------------------------------------------------
# I `genres` di Steam sono pochi e grossi ("Azione" ce l'hanno 23 giochi su 33 di
# questa libreria); i **tag** sono quelli che distinguono davvero — "Souls-like",
# "Open World", "Coop". Valve pero' non li espone in `appdetails`, e la pagina del
# negozio e' dietro il controllo dell'eta': su Elden Ring restituisce il solo
# "Violenza". La fonte che li da' in modo programmatico e' **SteamSpy**, pubblica e
# senza chiave, che li restituisce gia' con i voti.
#
# ⚠️ I tag sono **solo in inglese**: SteamSpy non ha una versione localizzata. I
# generi restano in italiano perche' vengono da Steam con `l=italian`.
STEAMSPY_URL = "https://steamspy.com/api.php?request=appdetails&appid={}"
STEAMSPY_PAUSA = 1.0        # SteamSpy chiede al massimo una richiesta al secondo
MAX_TAG = 12                # oltre i primi tag i voti crollano e diventano rumore


def _steamspy_tag(appid):
    """`(elenco_tag_ordinati_per_voti, errore)`. Elenco vuoto = risposta senza tag."""
    dati, errore = _steam_json(STEAMSPY_URL.format(appid))
    if errore:
        return [], errore
    tag = (dati or {}).get("tags") or {}
    if isinstance(tag, list):        # SteamSpy manda [] invece di {} quando non ne ha
        return [], None
    ordinati = sorted(tag.items(), key=lambda kv: kv[1], reverse=True)
    return [nome for nome, _ in ordinati[:MAX_TAG]], None


@bp.route("/api/steam/tag-da-arricchire")
@login_required
def steam_tag_da_arricchire():
    """Quanti giochi Steam sono ancora senza tag."""
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM games WHERE steam_appid IS NOT NULL"
                   " AND (steam_tags IS NULL OR steam_tags='')").fetchone()[0]
    db.close()
    return jsonify({"rimasti": n})


@bp.route("/steam/arricchisci-tag", methods=["POST"])
@login_required
def steam_arricchisci_tag():
    """Riempie i tag leggendoli da SteamSpy, a lotti come per i generi.

    Lotto piu' piccolo del giro dei generi perche' SteamSpy vuole una richiesta al
    secondo: 6 giochi sono ~6 secondi, che una richiesta HTTP regge senza problemi.
    """
    LOTTO = 6
    db = get_db()
    da_fare = db.execute(
        "SELECT id, steam_appid FROM games WHERE steam_appid IS NOT NULL"
        " AND (steam_tags IS NULL OR steam_tags='') ORDER BY id LIMIT ?", (LOTTO,)).fetchall()

    fatti = senza = 0
    errore_rete = None
    for r in da_fare:
        tag, errore = _steamspy_tag(r["steam_appid"])
        if errore:
            # Come per i generi: un guasto di rete NON deve marcare il gioco, o un
            # errore temporaneo lo escluderebbe per sempre dai tentativi successivi.
            errore_rete = errore
            break
        if tag:
            db.execute("UPDATE games SET steam_tags=? WHERE id=?", (", ".join(tag), r["id"]))
            fatti += 1
        else:
            db.execute("UPDATE games SET steam_tags='—' WHERE id=?", (r["id"],))
            senza += 1
        time.sleep(STEAMSPY_PAUSA)
    db.commit()
    rimasti = db.execute("SELECT COUNT(*) FROM games WHERE steam_appid IS NOT NULL"
                         " AND (steam_tags IS NULL OR steam_tags='')").fetchone()[0]
    db.close()
    if errore_rete and not fatti:
        return jsonify({"errore": errore_rete, "rimasti": rimasti}), 502
    return jsonify({"fatti": fatti, "senza_tag": senza,
                    "rimasti": rimasti, "interrotto": errore_rete})


def _campi(riga, colonna):
    return {v.strip() for v in ((riga[colonna] if colonna in riga.keys() else "") or "").split(",")
            if v.strip() and v.strip() != "—"}


def _segnali(riga):
    """Su cosa si misura la somiglianza: tag **e** generi, tenuti separati.

    I tag sono molto piu' fini dei generi — un gioco che per `genre` e' solo "Azione"
    puo' essere "Souls-like, Open World, Difficult" — ma non tutti ce l'hanno: le voci
    senza pagina SteamSpy prendono `—`.

    ⚠️ Usare **o** i tag **o** i generi, il migliore disponibile, sembra sensato ed e'
    sbagliato: un gioco con tag e uno senza non condividerebbero mai niente, e i
    secondi sparirebbero dai suggerimenti senza che nessuno se ne accorga. Si usano
    quindi entrambi, con un prefisso che tiene i due vocabolari **separati**, cosi'
    ogni termine pesa rispetto ai suoi simili e un tag non viene mai confrontato con
    un genere.
    """
    return ({"tag:" + t for t in _campi(riga, "steam_tags")}
            | {"gen:" + g for g in _campi(riga, "genre")})


def _etichetta(termine):
    """`tag:Souls-like` -> `Souls-like`: il prefisso è interno, non si mostra."""
    return termine.split(":", 1)[1] if ":" in termine else termine


# Un genere condiviso conta come segnale solo se **meno di metà libreria** ce l'ha:
# sotto quella soglia non distingue niente. `log(N/df) > log(2)` è esattamente questo.
SOGLIA_SEGNALE = math.log(2)


def suggerimenti(giochi, quanti=4, id_ancora=None):
    """Cosa giocare dopo, **partendo dalla libreria stessa**.

    Steam non espone «giochi simili», e inventarsi una somiglianza sarebbe un dato
    finto: l'unica fonte onesta qui sei tu. Si parte da cosa stai giocando e si
    cercano nella tua libreria i giochi che gli somigliano di più per genere.

    ⚠️ **I generi non pesano uguale.** In questa libreria «Azione» ce l'hanno 23
    giochi su 33: condividerlo non dice quasi niente. «Corse», che ce l'hanno in 2, dice
    molto. Il punteggio di un genere condiviso è quindi `log(N / quanti_ce_l_hanno)`,
    cioè tanto più alto quanto più il genere è raro in libreria — senza questo, il
    suggeritore direbbe solo «ti piace l'azione» e proporrebbe i giochi a caso fra i 23.

    ⚠️ **Se il segnale è debole non si suggerisce lo stesso.** `Call of Duty®` ha un
    solo genere, «Azione», che in questa libreria hanno 23 giochi su 33: qualunque
    elenco basato su quello sarebbe rumore travestito da consiglio, e l'ordine lo
    deciderebbe lo spareggio. In quel caso torna una `nota` che dice perché, e nessun
    suggerimento.

    Restituisce `(ancora, motivo_ancora, [(gioco, punteggio, generi_in_comune), …], nota)`.
    `ancora` è `None` se la libreria è troppo piccola o senza generi.
    """
    if len(giochi) < 3:
        return None, "", [], ""

    # L'ancora è ciò che stai giocando, ma si può scegliere: con tutta la libreria in
    # "Pausa" il ripiego sul più giocato può capitare su un gioco poco caratterizzato,
    # e senza poterlo cambiare la funzione resterebbe muta.
    ancora = next((g for g in giochi if g["id"] == id_ancora), None)
    # Le frasi passano da t()/tf(): sono etichette, e la sezione Gaming è tradotta.
    # Restano **intere** nel dizionario invece di essere spezzate in pezzi da
    # concatenare, così l'inglese può metterne le parole in un altro ordine.
    motivo = t("scelto da te") if ancora else ""
    if ancora is None:
        in_corso = [g for g in giochi if g["status"] == "In corso"]
        if in_corso:
            ancora = max(in_corso, key=lambda g: g["hours_played"] or 0)
            motivo = t("perché lo stai giocando")
        else:
            con_ore = [g for g in giochi if (g["hours_played"] or 0) > 0]
            if not con_ore:
                return None, "", [], ""
            ancora = max(con_ore, key=lambda g: g["hours_played"] or 0)
            motivo = t("il più giocato — nessun gioco è «In corso»")

    generi_ancora = _segnali(ancora)
    if not generi_ancora:
        return ancora, motivo, [], tf(
            "{titolo} non ha generi in catalogo: non c'è su cosa confrontarlo.",
            {"titolo": ancora["title"]})

    # Quanti giochi hanno ciascun genere: è il denominatore della rarità.
    quanti_hanno = {}
    for g in giochi:
        for nome in _segnali(g):
            quanti_hanno[nome] = quanti_hanno.get(nome, 0) + 1
    totale = len(giochi)

    classifica = []
    for g in giochi:
        if g["id"] == ancora["id"] or g["status"] in ("Completato", "Abbandonato"):
            continue
        comuni = generi_ancora & _segnali(g)
        if not comuni:
            continue
        punti = sum(math.log(totale / quanti_hanno[nome]) for nome in comuni)
        if punti <= 0:      # solo generi che ha praticamente tutta la libreria
            continue
        # A parità di somiglianza vengono prima quelli su cui hai speso meno ore:
        # suggerire il gioco che hai già consumato non serve a niente.
        classifica.append((g, punti,
                           [_etichetta(n) for n in sorted(comuni, key=lambda n: quanti_hanno[n])]))
    classifica.sort(key=lambda r: (-r[1], r[0]["hours_played"] or 0))

    if not classifica:
        return ancora, motivo, [], tf(
            "Nessun altro gioco condivide un genere con {titolo}.",
            {"titolo": ancora["title"]})
    if classifica[0][1] < SOGLIA_SEGNALE:
        comuni_deboli = ", ".join(f"«{_etichetta(n)}»" for n in sorted(generi_ancora))
        # Singolare e plurale sono due frasi **intere** e non un pezzo cucito in mezzo:
        # in inglese il verbo non sta dove sta in italiano. E vanno scritte dentro la
        # chiamata a tf(), non passate da una variabile, altrimenti
        # controlla_traduzioni.py non le vede e le segnala come orfane.
        valori = {"titolo": ancora["title"], "generi": comuni_deboli,
                  "quanti": max(quanti_hanno[n] for n in generi_ancora),
                  "totale": totale}
        # ⚠️ Su UNA riga ciascuna, per quanto lunghe: `controlla_traduzioni.py` legge il
        # sorgente con una regex e la concatenazione implicita di Python ("a" "b") la
        # troncherebbe al primo pezzo, chiedendo una traduzione per mezza frase.
        nota = (tf("{titolo} ha solo {generi}, che in libreria hanno {quanti} giochi su {totale}: troppo comune per distinguere qualcosa. Scegli un altro gioco qui sopra.", valori)
                if len(generi_ancora) > 1 else
                tf("{titolo} ha solo {generi}, che in libreria ha {quanti} giochi su {totale}: troppo comune per distinguere qualcosa. Scegli un altro gioco qui sopra.", valori))
        return ancora, motivo, [], nota
    return ancora, motivo, classifica[:quanti], ""


@bp.route("/")
@login_required
def gaming():
    db    = get_db()
    filt  = request.args.get("status", "")
    q     = request.args.get("q", "")
    genere = request.args.get("genre", "")
    piattaforma = request.args.get("platform", "")
    ordine = request.args.get("sort", "")

    sql   = "SELECT * FROM games WHERE 1=1"; params = []
    if filt: sql += " AND status=?";     params.append(filt)
    if q:    sql += " AND title LIKE ?"; params.append(f"%{q}%")
    # `genre` e' un elenco separato da virgole ("Action, RPG"), non un valore singolo:
    # il confronto e' per sottostringa, con le virgole ai bordi per non far combaciare
    # "RPG" dentro un ipotetico "JRPG".
    if genere:
        sql += " AND (',' || REPLACE(genre, ', ', ',') || ',') LIKE ?"
        params.append(f"%,{genere},%")
    if piattaforma:
        sql += " AND platform=?"; params.append(piattaforma)
    sql += " " + ORDINAMENTI.get(ordine, ORDINAMENTI[""])
    games  = db.execute(sql, params).fetchall()

    counts = {s: db.execute("SELECT COUNT(*) FROM games WHERE status=?", (s,)).fetchone()[0]
              for s in GAME_STATUSES}
    counts["Tutti"] = db.execute("SELECT COUNT(*) FROM games").fetchone()[0]

    # Le tendine elencano solo i valori **presenti in libreria**: una lista fissa
    # offrirebbe filtri che non danno mai risultati.
    generi = sorted({g.strip() for (riga,) in db.execute(
        "SELECT genre FROM games WHERE genre IS NOT NULL AND genre <> ''")
        for g in riga.split(",") if g.strip()})
    piattaforme = sorted({r[0] for r in db.execute(
        "SELECT DISTINCT platform FROM games WHERE platform IS NOT NULL AND platform <> ''")})
    # I suggerimenti guardano **tutta** la libreria, non l'elenco filtrato: sono un
    # consiglio su cosa giocare, non un riassunto di quello che stai guardando.
    tutti = db.execute("SELECT * FROM games ORDER BY title COLLATE NOCASE").fetchall()
    ancora, motivo_ancora, suggeriti, nota_sugg = suggerimenti(
        tutti, id_ancora=_i(request.args.get("simile_a")) or None)
    db.close()
    return render_template("gaming.html", games=games, statuses=GAME_STATUSES,
                           platforms=GAME_PLATFORMS, current_filter=filt, q=q, counts=counts,
                           generi=generi, piattaforme=piattaforme, genre=genere,
                           platform=piattaforma, sort=ordine, ordinamenti=ETICHETTE_ORDINE,
                           ancora=ancora, motivo_ancora=motivo_ancora, suggeriti=suggeriti,
                           nota_sugg=nota_sugg, tutti=tutti)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def game_new():
    if request.method == "POST":
        _game_upsert(); flash("Gioco aggiunto!", "success")
        return redirect(url_for("gaming.gaming"))
    return render_template("game_form.html", game=None,
                           statuses=GAME_STATUSES, platforms=GAME_PLATFORMS)


@bp.route("/<int:gid>/edit", methods=["GET", "POST"])
@login_required
def game_edit(gid):
    db   = get_db()
    game = db.execute("SELECT * FROM games WHERE id=?", (gid,)).fetchone()
    db.close()
    if not game:
        flash("Non trovato", "error"); return redirect(url_for("gaming.gaming"))
    if request.method == "POST":
        _game_upsert(gid); flash("Aggiornato!", "success")
        return redirect(url_for("gaming.gaming"))
    return render_template("game_form.html", game=game,
                           statuses=GAME_STATUSES, platforms=GAME_PLATFORMS)


@bp.route("/<int:gid>/delete", methods=["POST"])
@login_required
def game_delete(gid):
    db = get_db(); db.execute("DELETE FROM games WHERE id=?", (gid,))
    db.commit(); db.close()
    flash("Eliminato", "success"); return redirect(url_for("gaming.gaming"))