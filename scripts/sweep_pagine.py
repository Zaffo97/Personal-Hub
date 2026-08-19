# -*- coding: utf-8 -*-
"""Rende ogni pagina e controlla la sintassi di ogni `<script>` e handler inline.

È lo «sweep» che il progetto fa a mano da mesi, e che ha già pagato due volte: un
apice di troppo in un `<script>` ha tenuto morto il PC Builder per settimane, e un
`SyntaxError` dentro un `onclick` ha tenuto morto il Ripristina del roster. Nessuno
dei due dava un errore visibile: la pagina si apriva, il pulsante non faceva niente.

    python scripts/sweep_pagine.py                 # tutte le pagine, IT ed EN
    python scripts/sweep_pagine.py --lingua it     # una lingua sola
    python scripts/sweep_pagine.py --pagina /pokemon/calcolatori

⚠️ **Dice che la sintassi è valida, non che il codice giri.** Il 13/08/2026 la tabella
dell'editor mosse è rimasta vuota con lo sweep a zero errori: `renderTable()` lanciava
`tf is not defined` **a runtime**. Ogni giro di verifica va chiuso caricando davvero le
pagine e contando le righe che compaiono.

Gira su una **copia** di `hub.db` (la lezione del 16/08/2026: un test che condivide lo
stato coi dati veri misura anche quelli, e lì si portò via 497 righe di cache).

Il parser è `esprima` (pip, puro Python) perché su questa macchina **node non c'è**.
Esce con 1 se trova anche un solo errore, così si può usare prima di un commit.
"""
import argparse
import os
import re
import shutil
import sys
import tempfile

# La console di Windows e' cp1252 e non sa scrivere gli accenti di questi messaggi.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)
TIPO = re.compile(r"""type\s*=\s*["']([^"']+)""", re.I)
HANDLER = re.compile(
    r"""\bon(?:click|change|submit|input|keyup|keydown|load|blur|focus)\s*=\s*("([^"]*)"|'([^']*)')""",
    re.I)

# Le pagine che si aprono con una GET e non chiedono un id che potrebbe non esserci.
# `/pokemon/team/1/edit` lo chiede: se il team 1 non c'è, la pagina redirige e lo
# sweep lo dice invece di fingere un ok.
PAGINE = [
    "/", "/pokemon/", "/pokemon/team/new", "/pokemon/team/1/edit",
    "/pokemon/calcolatori", "/pokemon/regulations", "/pokemon/catalogo",
    "/pokemon/mosse", "/pokemon/oggetti", "/pokemon/roster", "/pokemon/abilita",
    "/gaming/", "/gaming/new", "/gaming/1/edit", "/gaming/uscite", "/gaming/steam",
    "/arduino/", "/python/", "/pcbuilder/", "/admin/utenti",
]


def moderno(codice):
    """Smussa ciò che `esprima` 4.0.1 (2018) non sa leggere ma i browser sì.

    ⚠️ Serve perché `moves_editor.html` usa `d.damage_class?.name`: l'optional
    chaining è del 2020, e senza questo il parser lo segnalerebbe come errore di
    sintassi su una riga che nel browser gira benissimo. Un falso allarme dentro uno
    strumento di verifica è peggio di nessuno strumento: si impara a ignorarlo, e il
    giorno dell'errore vero non lo guarda più nessuno.
    """
    return codice.replace("?.", ".").replace("??", "||")


def controlla(esprima, pagina, testo):
    errori, blocchi, handler = [], 0, 0
    for attributi, corpo in SCRIPT.findall(testo):
        # I blocchi <script type="application/json"> sono isole di dati, non codice:
        # passarli a un parser JS è un falso allarme garantito.
        tipo = TIPO.search(attributi or "")
        if tipo and "javascript" not in tipo.group(1).lower():
            continue
        if not corpo.strip():
            continue
        blocchi += 1
        try:
            esprima.parseScript(moderno(corpo), {"tolerant": False})
        except Exception as e:
            errori.append(("<script>", str(e)[:120], corpo.strip()[:80]))
    # ⚠️ Gli handler si cercano **fuori** dagli `<script>`: dentro il JS ci sono
    # stringhe che costruiscono un `onclick` a pezzi, e raschiarle dall'HTML grezzo
    # vuol dire passare al parser mezza espressione — tre falsi allarmi sull'editor
    # del catalogo, tutti finti.
    for m in HANDLER.finditer(SCRIPT.sub("", testo)):
        codice = m.group(2) if m.group(2) is not None else m.group(3)
        codice = (codice.replace("&quot;", '"').replace("&#39;", "'")
                        .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
        if not codice.strip():
            continue
        handler += 1
        try:
            # Come `new Function(codice)`: è il **corpo di una funzione**, dove un
            # `return` in cima è legale. Parsare il codice nudo lo direbbe illegale.
            esprima.parseScript("(function(){" + moderno(codice) + "\n})")
        except Exception as e:
            errori.append(("handler", str(e)[:120], codice[:80]))
    stato = "ok" if not errori else f"{len(errori)} ERRORI"
    print(f"  {pagina:<26} script {blocchi:>2}  handler {handler:>4}  -> {stato}")
    for tipo_, messaggio, campione in errori:
        print(f"      {tipo_}: {messaggio}")
        print(f"        {campione}")
    return len(errori)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lingua", choices=["it", "en"], action="append",
                    help="una sola lingua (di default tutte e due)")
    ap.add_argument("--pagina", action="append", help="una pagina sola, ripetibile")
    ap.add_argument("--utente", default="admin")
    ap.add_argument("--password", default="admin123")
    args = ap.parse_args()

    try:
        import esprima
    except ImportError:
        print("Manca il parser: pip install esprima")
        return 1

    origine = os.path.join(RADICE, "hub.db")
    if not os.path.exists(origine):
        print(f"hub.db non trovato in {origine}.")
        return 1
    copia = os.path.join(tempfile.gettempdir(), "sweep_hub.db")
    shutil.copy(origine, copia)

    import extensions
    extensions.DB = copia                # ⚠️ prima di creare l'app, non dopo
    import app as modulo_app
    flask_app = modulo_app.create_app()
    flask_app.config.update(TESTING=True, SECRET_KEY="sweep")

    pagine = args.pagina or PAGINE
    lingue = args.lingua or ["it", "en"]
    totale = 0
    for lingua in lingue:
        print(f"\n== lingua {lingua} ==")
        with flask_app.test_client() as c:
            c.post("/login", data={"username": args.utente, "password": args.password},
                   follow_redirects=True)
            c.set_cookie("hub_lang", lingua)
            for pagina in pagine:
                r = c.get(pagina, follow_redirects=True)
                if r.status_code != 200:
                    print(f"  {pagina:<26} status {r.status_code}")
                    totale += 1
                    continue
                totale += controlla(esprima, pagina, r.get_data(as_text=True))

    print(f"\nerrori totali: {totale}")
    return 1 if totale else 0


if __name__ == "__main__":
    sys.exit(main())
