import datetime
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


# --- IGDB -------------------------------------------------------------------
# La fonte delle date d'uscita **multi-piattaforma**. Steam da' solo Steam, e la
# richiesta era esplicitamente "tutte le piattaforme"; RAWG il 16/08/2026 rispondeva
# 522 su API e sito, quindi scriverne il client sarebbe stato scrivere codice non
# provabile.
#
# IGDB e' di Twitch, e l'autenticazione e' quella di Twitch: un'app registrata da'
# Client ID + Secret, con cui si chiede un **token applicativo** (client_credentials)
# che vale settimane. Le credenziali stanno **solo** in variabili d'ambiente, come
# STEAM_API_KEY: mai su file, mai in git, mai chieste in un form.
IGDB_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_URL = "https://api.igdb.com/v4/{}"
IGDB_TIMEOUT = 15
# Margine sulla scadenza: un token che scade fra dieci secondi e' gia' scaduto per
# una richiesta che deve ancora partire.
IGDB_MARGINE = 300

# Cache del token in memoria: `(token, scade_a_epoch)`. Non va su disco — e' una
# credenziale, e su disco finirebbe in un backup o in un commit.
_igdb_token_cache = (None, 0)


def igdb_credenziali():
    """`(client_id, client_secret)` dall'ambiente. Stringhe vuote se non impostate."""
    return (os.environ.get("IGDB_CLIENT_ID", "").strip(),
            os.environ.get("IGDB_CLIENT_SECRET", "").strip())


def igdb_token():
    """Token applicativo, preso una volta e riusato. Ritorna (token, errore)."""
    global _igdb_token_cache
    token, scade = _igdb_token_cache
    if token and time.time() < scade - IGDB_MARGINE:
        return token, None

    cid, seg = igdb_credenziali()
    if not cid or not seg:
        return None, "IGDB_CLIENT_ID / IGDB_CLIENT_SECRET non impostate"

    dati = urllib.parse.urlencode({
        "client_id": cid, "client_secret": seg,
        "grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(IGDB_TOKEN_URL, data=dati,
                                 headers={"User-Agent": STEAM_UA})
    try:
        with urllib.request.urlopen(req, timeout=IGDB_TIMEOUT) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        # 401/403 qui vuol dire credenziali sbagliate, non un guasto di rete: va
        # detto con parole diverse, o si cerca il problema dalla parte sbagliata.
        if e.code in (400, 401, 403):
            return None, "Twitch rifiuta le credenziali IGDB: Client ID o Secret errati"
        return None, f"Twitch ha risposto {e.code}"
    except (urllib.error.URLError, socket.timeout):
        return None, "Twitch non raggiungibile"
    except json.JSONDecodeError:
        return None, "Risposta di Twitch non leggibile"

    token = d.get("access_token")
    if not token:
        return None, "Twitch non ha restituito un token"
    _igdb_token_cache = (token, time.time() + (d.get("expires_in") or 0))
    return token, None


def igdb_query(endpoint, query):
    """POST Apicalypse su IGDB. Ritorna (dati, errore).

    ⚠️ IGDB **non** usa la querystring: la richiesta e' un POST col corpo in
    Apicalypse (`fields …; where …; limit …;`), e senza gli header `Client-ID` e
    `Authorization: Bearer` risponde 401 con un messaggio che spiega quale manca.
    """
    token, errore = igdb_token()
    if errore:
        return None, errore
    req = urllib.request.Request(
        IGDB_URL.format(endpoint), data=query.encode(),
        headers={"Client-ID": igdb_credenziali()[0],
                 "Authorization": f"Bearer {token}",
                 "User-Agent": STEAM_UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=IGDB_TIMEOUT) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return None, "IGDB ha risposto 429: troppe richieste, riprova fra poco"
        return None, f"IGDB ha risposto {e.code}"
    except (urllib.error.URLError, socket.timeout):
        return None, "IGDB non raggiungibile"
    except json.JSONDecodeError:
        return None, "Risposta di IGDB non leggibile"


# --- Calendario uscite ------------------------------------------------------
# Le uscite future stanno in `game_releases`, che e' una **cache** e non la libreria:
# il perche' sta nel commento della tabella in `extensions.py`.
#
# Finestre offerte dal filtro. La chiave e' quella che viaggia nell'URL, il valore e'
# quanti giorni in avanti guardare. `None` = tutto quello che c'e' in cache.
FINESTRE = [("30", 30), ("90", 90), ("365", 365), ("tutto", None)]
ETICHETTE_FINESTRA = {"30": "Prossimi 30 giorni", "90": "Prossimi 3 mesi",
                      "365": "Prossimo anno", "tutto": "Tutto quello che c'è"}
FINESTRA_DEFAULT = "90"

# Quante uscite mostrare nella striscia in cima a /gaming: e' un assaggio, non l'elenco.
STRISCIA = 6

# ⚠️ Tetto alle righe della pagina, **misurato e non prudenziale**. Senza, con la cache
# vera (6827 uscite, 4343 righe dopo la fusione) la pagina pesava **3,3 MB con 4224
# immagini** su "tutto", e **994 KB con 1291 immagini** gia' sulla finestra di default.
# Stesso rimedio dello Speed Tier, che dalle 1343 righe / 714 KB e' sceso a 300 / 159 KB.
# Si tengono le **piu' vicine**: in un calendario delle uscite quello che si guarda e'
# cosa esce adesso, non cosa esce fra due anni. Il conto pieno resta scritto sopra la
# tabella, perche' un elenco tagliato che non dichiara di esserlo mente.
TETTO_RIGHE = 300

MESI_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
           "agosto", "settembre", "ottobre", "novembre", "dicembre"]
# ⚠️ **I mesi NON si abbreviano, e non e' una scelta estetica.** La chiave del
# dizionario e' la frase italiana, quindi `mar` puo' avere **una** traduzione sola —
# ma in italiano `mar` e' sia *marzo* (`Mar`) sia *martedi'* (`Tue`). Abbreviando
# entrambi, uno dei due riceverebbe la parola inglese dell'altro **senza nessun
# errore**: e' la trappola "una parola italiana, due inglesi" gia' descritta in
# CLAUDE.md. Si rompe il pareggio dove costa meno: "16 agosto" per esteso e' italiano
# normale, mentre i giorni della settimana in italiano si abbreviano proprio cosi'.
# ⚠️ Indicizzati come `datetime.weekday()`: 0 = lunedì. `time.strftime('%A')` darebbe
# il nome nella lingua del **sistema operativo**, che qui non c'entra niente: la
# lingua della pagina sta nel cookie `hub_lang`, e il giorno deve seguire quella.
GIORNI_IT = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]


def _oggi():
    return time.strftime("%Y-%m-%d")


def _fra_giorni(n):
    return time.strftime("%Y-%m-%d", time.localtime(time.time() + n * 86400))


def leggi_uscite(piattaforma="", entro=FINESTRA_DEFAULT, limite=None):
    """Le uscite in cache da oggi in avanti, gia' ordinate per data.

    ⚠️ Il confine e' **oggi compreso**, non "da domani": un gioco che esce oggi e'
    esattamente quello che uno vuole vedere in un calendario delle uscite.

    Le date sono stringhe `YYYY-MM-DD`, quindi il confronto lessicografico di SQLite
    e' anche quello cronologico: non serve nessuna conversione. Le righe **senza**
    data restano fuori — una riga in un calendario senza sapere quando e' rumore.
    """
    giorni = dict(FINESTRE).get(entro, dict(FINESTRE)[FINESTRA_DEFAULT])
    sql = ("SELECT * FROM game_releases WHERE release_date IS NOT NULL"
           " AND release_date >= ?")
    params = [_oggi()]
    if giorni is not None:
        sql += " AND release_date <= ?"
        params.append(_fra_giorni(giorni))
    if piattaforma:
        sql += " AND platform = ?"
        params.append(piattaforma)
    sql += " ORDER BY release_date ASC, title COLLATE NOCASE ASC"
    if limite:
        sql += " LIMIT ?"
        params.append(limite)
    db = get_db()
    righe = db.execute(sql, params).fetchall()
    db.close()
    return righe


def raggruppa_per_mese(righe):
    """`[(etichetta_mese, [voce, …]), …]`, nell'ordine in cui arrivano.

    Il raggruppamento si fa qui e non nel template: Jinja sa fare `groupby`, ma
    l'etichetta del mese va tradotta e composta, e farlo nel template significherebbe
    spezzarla in pezzi che l'inglese rimetterebbe in un altro ordine.

    Le righe diventano **dizionari** perche' ci si aggiunge `dow`, il giorno della
    settimana: una `sqlite3.Row` non si puo' arricchire.
    """
    gruppi = []
    for r in righe:
        voce = dict(r)
        anno, mese, giorno = (int(voce["release_date"][:4]),
                              int(voce["release_date"][5:7]),
                              int(voce["release_date"][8:10]))
        # Frase intera in una chiamata sola, non "mese" + " " + "anno": cosi' l'inglese
        # puo' metterne le parole in un altro ordine se serve.
        etichetta = tf("{mese} {anno}", {"mese": t(MESI_IT[mese - 1]), "anno": anno})
        voce["dow"] = t(GIORNI_IT[datetime.date(anno, mese, giorno).weekday()])
        if not gruppi or gruppi[-1][0] != etichetta:
            gruppi.append((etichetta, []))
        gruppi[-1][1].append(voce)
    return gruppi


# Quanto e' precisa una data, dalla piu' alla meno precisa. Serve a fondere due righe
# della stessa uscita che non concordano: se una fonte sa il giorno esatto e l'altra
# solo il mese, il giorno esatto e' quello buono — non il contrario.
ORDINE_PRECISIONE = ["giorno", "mese", "trimestre", "anno", "ignota"]


def _quanto_precisa(valore):
    """Posizione in `ORDINE_PRECISIONE`, e in fondo se e' un valore che non conosco.

    `.index()` nudo solleverebbe `ValueError` su una precisione inattesa, e una
    pagina che risponde 500 perche' in cache c'e' una parola che non mi aspettavo e'
    un prezzo assurdo: una precisione sconosciuta va trattata come la meno affidabile,
    non come un guasto.
    """
    try:
        return ORDINE_PRECISIONE.index(valore or "ignota")
    except ValueError:
        return len(ORDINE_PRECISIONE)


def unisci_multipiattaforma(righe):
    """Una riga per **gioco e giorno**, con tutte le sue piattaforme dentro.

    Su IGDB l'unita' del dato e' l'uscita **per piattaforma**: un gioco che esce lo
    stesso giorno su PC, PS5 e Xbox sono **tre righe**. In un calendario diventano tre
    voci identiche una sotto l'altra, che e' rumore: quello che si vuole leggere e'
    «GTA VI — PlayStation 5, Xbox Series X|S».

    ⚠️ Si fonde in **lettura**, non in scrittura. In cache le righe restano separate,
    ed e' cio' che permette al filtro per piattaforma di funzionare e all'import di
    restare rieseguibile sulla chiave `igdb_release_id`.

    ⚠️ E si fonde **dopo** il filtro, non prima: cosi' quello che si vede corrisponde
    sempre a quello che si e' chiesto. Filtrando su PS5 la riga elenca PS5 e basta,
    anche se quel gioco esce anche altrove — mostrare piattaforme escluse dal filtro
    farebbe sembrare che il filtro non funzioni.

    La chiave e' `igdb_game_id`, non il titolo: due giochi diversi possono chiamarsi
    uguale, e fonderli sarebbe inventare un'uscita che non esiste. Il titolo resta solo
    come ripiego per le righe che un id non ce l'hanno.
    """
    fuse = {}
    ordine = []
    for r in righe:
        v = dict(r)
        chiave = (v["igdb_game_id"] or f"t:{v['title'].lower()}", v["release_date"])
        if chiave not in fuse:
            v["piattaforme"] = []
            fuse[chiave] = v
            ordine.append(chiave)
        voce = fuse[chiave]
        if v["platform"] and v["platform"] not in voce["piattaforme"]:
            voce["piattaforme"].append(v["platform"])
        # I campi che possono mancare su una riga e esserci su un'altra: si tiene il
        # primo valorizzato invece di lasciare il buco della riga capofila.
        for campo in ("cover_url", "igdb_url", "human"):
            if not voce.get(campo) and v.get(campo):
                voce[campo] = v[campo]
        if _quanto_precisa(v.get("precisione")) < _quanto_precisa(voce.get("precisione")):
            voce["precisione"] = v["precisione"]
            voce["human"] = v["human"]
    for chiave in ordine:
        fuse[chiave]["piattaforme"].sort()
    return [fuse[c] for c in ordine]


def striscia_uscite():
    """Le prossime `STRISCIA` uscite per la striscia in cima a /gaming.

    Torna dizionari con un `quando` gia' composto ("16 ago"): nella striscia non c'e'
    l'intestazione del mese a fare da contesto, quindi la data se lo porta dietro.
    """
    # ⚠️ Il limite si applica **dopo** la fusione, quindi qui se ne chiedono di piu':
    # le righe grezze sono una per piattaforma, e tagliare a STRISCIA prima di fondere
    # riempirebbe la striscia con lo stesso gioco ripetuto. Il margine copre un gioco
    # che esce su tutte le piattaforme immaginabili lo stesso giorno; nel caso
    # patologico si mostrerebbe qualche voce in meno, mai una sbagliata.
    voci = unisci_multipiattaforma(leggi_uscite(entro="tutto", limite=STRISCIA * 12))
    for v in voci[:STRISCIA]:
        v["quando"] = tf("{giorno} {mese}", {
            "giorno": int(v["release_date"][8:10]),
            "mese": t(MESI_IT[int(v["release_date"][5:7]) - 1])})
    return voci[:STRISCIA]


def piattaforme_in_cache():
    """Solo le piattaforme che hanno almeno un'uscita: una lista fissa offrirebbe
    filtri che non danno mai risultati, come gia' per i generi della libreria."""
    db = get_db()
    righe = sorted({r[0] for r in db.execute(
        "SELECT DISTINCT platform FROM game_releases"
        " WHERE platform IS NOT NULL AND platform <> ''")})
    db.close()
    return righe


def stato_cache():
    """`(quante_uscite_future, quando_e_stata_aggiornata)`. Serve a dire a schermo se
    quello che si sta guardando e' fresco: una cache che non dichiara la propria eta'
    e' indistinguibile da un dato vero, ed e' la stessa trappola del grafo."""
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM game_releases WHERE release_date >= ?",
                   (_oggi(),)).fetchone()[0]
    quando = db.execute("SELECT MAX(updated_at) FROM game_releases").fetchone()[0]
    db.close()
    return n, quando


# Quante uscite chiedere per giro. IGDB accetta al massimo 500 per richiesta, ed e'
# anche un buon lotto per una richiesta HTTP: il client richiama finche' non ha finito.
IGDB_LOTTO = 500
# Fin dove guardare in avanti. Oltre l'anno e mezzo le date su IGDB sono quasi tutte
# "2028" o "TBD", cioe' righe che il calendario mostrerebbe senza dire niente di utile.
IGDB_ORIZZONTE = 540

# `category` di IGDB dice **quanto e' precisa** la data. Questa e' la tabella
# dell'enum; il nome del campo va confermato dalla sonda, e per questo il codice
# accetta sia `category` sia `date_format` e non da' per scontato nessuno dei due.
# ⚠️ La riga con precisione diversa da "giorno" ha comunque un `date` valorizzato: e'
# l'**inizio** del periodo. Ordinare va bene, mostrarlo come data d'uscita no — a
# schermo si mostra allora `human`, che e' come IGDB stessa la scrive.
IGDB_PRECISIONE = {
    0: "giorno", 1: "mese", 2: "anno", 3: "trimestre", 4: "trimestre",
    5: "trimestre", 6: "trimestre", 7: "ignota",
}


def _mappa_uscita(voce):
    """Da una voce IGDB alla riga da scrivere. Ritorna (riga, motivo_scarto).

    ⚠️ **Scarta invece di riempire.** Una riga senza data o senza titolo non e' una
    riga da salvare con dei NULL dentro: e' una riga che non sappiamo leggere, e in un
    calendario diventerebbe una voce muta. La si conta e la si dichiara a schermo.
    """
    rid = voce.get("id")
    quando = voce.get("date")
    gioco = voce.get("game") or {}
    titolo = (gioco.get("name") or "").strip() if isinstance(gioco, dict) else ""

    if not rid:
        return None, "senza id"
    if not quando:
        return None, "senza data"
    if not titolo:
        return None, "senza titolo"

    # `category` sul vecchio schema, `date_format` sul nuovo: si prende quello che
    # c'e'. Se non c'e' nessuno dei due la precisione resta **dichiarata ignota**,
    # che e' diverso da "giorno" — dare per esatta una data che non lo e' sarebbe
    # inventare un dato.
    codice = voce.get("category")
    if codice is None:
        codice = voce.get("date_format")
    precisione = IGDB_PRECISIONE.get(codice, "ignota")

    piattaforma = voce.get("platform") or {}
    if not isinstance(piattaforma, dict):
        piattaforma = {}

    copertina = ""
    cover = gioco.get("cover") if isinstance(gioco, dict) else None
    if isinstance(cover, dict) and cover.get("image_id"):
        # `t_cover_small` e' 90x128: qui la copertina sta in un riquadro da 92x43,
        # non serve di piu' e sono meno byte per riga.
        copertina = ("https://images.igdb.com/igdb/image/upload/"
                     f"t_cover_small/{cover['image_id']}.jpg")

    return {
        "igdb_release_id": rid,
        "igdb_game_id": gioco.get("id"),
        "title": titolo[:300],
        "platform": (piattaforma.get("name") or "").strip(),
        "platform_abbr": (piattaforma.get("abbreviation") or "").strip(),
        # IGDB da' un epoch UTC. La data si prende in UTC e **non** in ora locale:
        # `localtime()` su un timestamp di mezzanotte UTC sposterebbe l'uscita al
        # giorno prima o dopo a seconda del fuso, che e' un baco silenzioso.
        "release_date": time.strftime("%Y-%m-%d", time.gmtime(quando)),
        "precisione": precisione,
        "human": (voce.get("human") or "").strip(),
        "cover_url": copertina,
        "igdb_url": (gioco.get("url") or "") if isinstance(gioco, dict) else "",
        "region": str(voce.get("region") or ""),
    }, None


@bp.route("/uscite/aggiorna", methods=["POST"])
@login_required
def uscite_aggiorna():
    """Un lotto di uscite future da IGDB. Il client richiama finche' `finito`.

    Rieseguibile: l'UPSERT e' su `igdb_release_id`, quindi rilanciarlo aggiorna le
    righe che ci sono invece di duplicarle — una data che si sposta e' il caso normale
    per un'uscita futura, ed e' il motivo per cui questo pulsante esiste.
    """
    payload = request.get_json(silent=True) or {}
    offset = max(0, _i(payload.get("offset")))

    adesso = int(time.time())
    fino_a = adesso + IGDB_ORIZZONTE * 86400
    # Una richiesta sola per lotto: i campi espansi (`game.name`, `platform.name`)
    # evitano il giro supplementare per ogni gioco e ogni piattaforma.
    # ⚠️ `sort id asc` e non `sort date asc`: con l'offset che avanza serve un ordine
    # **stabile**, e le date cambiano proprio mentre si sta paginando. Ordinare per
    # data farebbe scivolare le righe fra un lotto e l'altro, saltandone alcune.
    query = ("fields id, date, human, category, date_format, region, "
             "game.id, game.name, game.url, game.cover.image_id, "
             "platform.name, platform.abbreviation; "
             f"where date > {adesso} & date < {fino_a}; "
             f"sort id asc; limit {IGDB_LOTTO}; offset {offset};")
    dati, errore = igdb_query("release_dates", query)
    if errore:
        return jsonify({"errore": errore, "offset": offset}), 502
    if not isinstance(dati, list):
        return jsonify({"errore": "IGDB non ha restituito un elenco",
                        "offset": offset}), 502

    db = get_db()
    nuovi = aggiornati = 0
    scarti = {}
    quando = time.strftime("%Y-%m-%d %H:%M:%S")     # ora locale, come la legge Davide
    for voce in dati:
        riga, motivo = _mappa_uscita(voce)
        if motivo:
            scarti[motivo] = scarti.get(motivo, 0) + 1
            continue
        gia = db.execute("SELECT id FROM game_releases WHERE igdb_release_id=?",
                         (riga["igdb_release_id"],)).fetchone()
        campi = list(riga) + ["updated_at"]
        valori = [riga[c] for c in riga] + [quando]
        if gia:
            db.execute("UPDATE game_releases SET "
                       + ", ".join(f"{c}=?" for c in campi)
                       + " WHERE igdb_release_id=?",
                       valori + [riga["igdb_release_id"]])
            aggiornati += 1
        else:
            db.execute(f"INSERT INTO game_releases({', '.join(campi)})"
                       f" VALUES({', '.join('?' * len(campi))})", valori)
            nuovi += 1
    db.commit()
    db.close()

    presi = len(dati)
    return jsonify({
        "presi": presi, "nuovi": nuovi, "aggiornati": aggiornati,
        "scarti": scarti,
        "offset": offset + presi,
        # Un lotto piu' corto del massimo vuol dire che IGDB ha finito le righe.
        "finito": presi < IGDB_LOTTO,
    })


@bp.route("/uscite/svuota", methods=["POST"])
@login_required
def uscite_svuota():
    """Butta la cache. E' rigenerabile per definizione, quindi non c'e' niente da
    archiviare prima: e' l'unica tabella di questo progetto per cui vale."""
    db = get_db()
    n = db.execute("DELETE FROM game_releases").rowcount
    db.commit()
    db.close()
    return jsonify({"tolte": n})


@bp.route("/uscite")
@login_required
def uscite():
    piattaforma = request.args.get("platform", "")
    entro = request.args.get("entro", FINESTRA_DEFAULT)
    if entro not in dict(FINESTRE):
        entro = FINESTRA_DEFAULT
    righe = unisci_multipiattaforma(leggi_uscite(piattaforma, entro))
    # Il taglio va **dopo** la fusione: tagliare prima riempirebbe il tetto con lo
    # stesso gioco ripetuto una volta per piattaforma.
    trovate = len(righe)
    righe = righe[:TETTO_RIGHE]
    totale, aggiornata = stato_cache()
    return render_template(
        "uscite.html",
        gruppi=raggruppa_per_mese(righe),
        # Tre numeri diversi, e a schermo si dice quale e' quale: `quante` sono le
        # righe **mostrate**, `trovate` quelle che passano i filtri (piu' grande se il
        # tetto ha tagliato), `totale` le uscite grezze in cache, una per piattaforma.
        quante=len(righe), trovate=trovate, tetto=TETTO_RIGHE,
        totale=totale, aggiornata=aggiornata,
        piattaforme=piattaforme_in_cache(), platform=piattaforma, entro=entro,
        finestre=[(k, ETICHETTE_FINESTRA[k]) for k, _ in FINESTRE],
        # Se il default cambia, il pulsante "azzera" lo segue da solo: ricopiare
        # `'90'` nel template lo lascerebbe indietro in silenzio.
        filtri_attivi=bool(piattaforma or entro != FINESTRA_DEFAULT),
        chiavi_presenti=all(igdb_credenziali()))


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
    # La striscia delle prossime uscite: un assaggio del calendario, non il calendario.
    # ⚠️ Non tocca `games` e non entra in nessuno dei conteggi qui sopra — sono giochi
    # che non possiedi, e mischiarli alla libreria era proprio la cosa da non fare.
    return render_template("gaming.html", games=games, statuses=GAME_STATUSES,
                           platforms=GAME_PLATFORMS, current_filter=filt, q=q, counts=counts,
                           generi=generi, piattaforme=piattaforme, genre=genere,
                           platform=piattaforma, sort=ordine, ordinamenti=ETICHETTE_ORDINE,
                           ancora=ancora, motivo_ancora=motivo_ancora, suggeriti=suggeriti,
                           nota_sugg=nota_sugg, tutti=tutti, prossime=striscia_uscite())


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