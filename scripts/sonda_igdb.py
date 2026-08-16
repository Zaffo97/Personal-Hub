#!/usr/bin/env python
"""Sonda l'API IGDB e stampa **quello che risponde davvero**.

    python scripts/sonda_igdb.py

Non scrive niente, da nessuna parte: serve a guardare, non a importare.

Perché esiste. Il mapping dei campi di una API non si scrive a memoria — su IGDB il
formato della data d'uscita è passato da `category` a `date_format` senza che i vecchi
esempi in giro smettessero di esistere, e mappare il campo sbagliato non darebbe un
errore: darebbe **la data sbagliata**, che è la classe di baco che qui si è già pagata
più volte. Quindi prima si guarda una risposta vera, poi si scrive il codice che la
legge.

Cosa serve, una volta sola (le crea Davide, io non posso creare account):

    1. https://dev.twitch.tv/console/apps -> Register Your Application
       OAuth Redirect URL: http://localhost   Categoria: Application Integration
    2. Copia Client ID, poi "New Secret" per il Client Secret
    3. In PowerShell:
       [Environment]::SetEnvironmentVariable("IGDB_CLIENT_ID","...","User")
       [Environment]::SetEnvironmentVariable("IGDB_CLIENT_SECRET","...","User")
       poi **riapri** il terminale, che le variabili le legge all'avvio

Le credenziali stanno **solo** in variabili d'ambiente: mai su file, mai in git, mai
chieste in un form. Stessa regola di STEAM_API_KEY.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_URL = "https://api.igdb.com/v4/{}"
UA = "personal-hub/1.0"
TIMEOUT = 15


def credenziali():
    cid = os.environ.get("IGDB_CLIENT_ID", "").strip()
    seg = os.environ.get("IGDB_CLIENT_SECRET", "").strip()
    return cid, seg


def prendi_token(cid, seg):
    """Token applicativo (client_credentials). Ritorna (token, scadenza_s, errore)."""
    dati = urllib.parse.urlencode({
        "client_id": cid, "client_secret": seg,
        "grant_type": "client_credentials",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=dati, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            d = json.loads(r.read())
        return d.get("access_token"), d.get("expires_in"), None
    except urllib.error.HTTPError as e:
        corpo = e.read()[:300].decode("utf-8", "replace")
        return None, None, f"Twitch ha risposto {e.code}: {corpo}"
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def interroga(endpoint, query, cid, token):
    """POST Apicalypse su IGDB. Ritorna (dati, errore)."""
    req = urllib.request.Request(
        IGDB_URL.format(endpoint), data=query.encode(),
        headers={"Client-ID": cid, "Authorization": f"Bearer {token}",
                 "User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        corpo = e.read()[:400].decode("utf-8", "replace")
        return None, f"IGDB ha risposto {e.code}: {corpo}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def mostra(titolo, dati):
    print(f"\n{'=' * 70}\n{titolo}\n{'=' * 70}")
    print(json.dumps(dati, indent=2, ensure_ascii=False)[:4000])


def main():
    cid, seg = credenziali()
    if not cid or not seg:
        manca = [n for n, v in [("IGDB_CLIENT_ID", cid), ("IGDB_CLIENT_SECRET", seg)] if not v]
        print("MANCA: " + ", ".join(manca))
        print("Le istruzioni per crearle stanno in cima a questo file.")
        return 1

    print(f"Client ID letto dall'ambiente: {cid[:6]}… ({len(cid)} caratteri)")
    token, scade, errore = prendi_token(cid, seg)
    if errore:
        print(f"Token NON ottenuto — {errore}")
        return 1
    print(f"Token ottenuto, scade fra {scade} secondi "
          f"(~{round((scade or 0) / 86400)} giorni)")

    adesso = int(time.time())

    # 1. Che campi ha davvero `release_dates`. `fields *;` li restituisce tutti:
    #    è questa risposta a decidere il mapping, non la memoria.
    dati, errore = interroga(
        "release_dates",
        f"fields *; where date > {adesso}; sort date asc; limit 3;", cid, token)
    if errore:
        print(f"\nrelease_dates: {errore}")
    else:
        mostra("release_dates — TUTTI i campi, 3 uscite future", dati)
        if dati:
            print("\nCampi presenti nella prima riga: " + ", ".join(sorted(dati[0].keys())))

    # 2. La stessa cosa espansa, che è la forma che servirà all'import: un solo giro
    #    di rete invece di tre (uscita -> gioco -> copertina -> piattaforma).
    dati, errore = interroga(
        "release_dates",
        "fields date, human, region, game.name, game.cover.image_id, game.url, "
        f"platform.name, platform.abbreviation; where date > {adesso}; "
        "sort date asc; limit 5;", cid, token)
    if errore:
        print(f"\nrelease_dates espanso: {errore}")
    else:
        mostra("release_dates — forma espansa (quella che userà l'import)", dati)

    # 3. L'elenco delle piattaforme, per capire su cosa si può filtrare davvero.
    dati, errore = interroga(
        "platforms", "fields id, name, abbreviation, category; limit 60; sort id asc;",
        cid, token)
    if errore:
        print(f"\nplatforms: {errore}")
    else:
        print(f"\n{'=' * 70}\nplatforms — prime 60\n{'=' * 70}")
        for p in dati or []:
            print(f"  {p.get('id'):>4}  {p.get('abbreviation', ''):<10} {p.get('name', '')}")

    # 4. Il conteggio: quante uscite future ci sono in tutto. Serve a sapere se
    #    l'import è un giro solo o un lavoro a lotti.
    dati, errore = interroga(
        "release_dates/count", f"where date > {adesso};", cid, token)
    if errore:
        print(f"\nconteggio: {errore}")
    else:
        print(f"\nUscite future totali su IGDB: {dati}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
