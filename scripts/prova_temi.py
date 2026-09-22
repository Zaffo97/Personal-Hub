#!/usr/bin/env python
"""Le prove dei temi: gli elenchi allineati, e i contrasti misurati.

    python scripts/prova_temi.py [--tutto]

Un tema è **una lista di variabili**, e vive in cinque posti: i colori in
`templates/_temi.html` (un file solo, incluso da `base.html` **e** da `login.html`),
la lista `temi` del menu e i due elenchi JavaScript `TEMI` e `TEMI_CHIARI` in
`base.html`, e l'elenco nel `<head>` di `login.html`. Sono vicini di proposito, ma
«vicini» non è un controllo: questo script lo è.

⚠️ **Perché serve, e non è pignoleria.** Ognuno dei disallineamenti rompe in
silenzio, e in modo diverso:

- una **variabile che manca** in un blocco eredita il valore di `:root`, cioè del tema
  scuro: un colore giusto su tre temi e sbagliato sul quarto. Nessun errore, e lo vede
  solo chi usa quel tema
- un tema **nel CSS ma non nella lista del menu** esiste e non si può scegliere
- un tema **nel menu ma non in `TEMI`** viene rifiutato da `scegliTema()` e il clic non
  fa niente — un pulsante morto e muto
- un tema chiaro **non elencato in `TEMI_CHIARI`** tiene l'icona della luna
- un tema che il `<head>` del **login** non conosce fa aprire quella pagina in scuro,
  qualunque cosa tu abbia scelto — ed è la pagina che si vede per prima
- e se `login.html` tornasse ad avere una **copia** dei colori, le due liste
  divergerebbero: è la deriva tolta il 22/09/2026, quando il login aveva i suoi due
  temi scritti a parte e i due nuovi non sarebbero mai arrivati fin lì

E i **contrasti**: il 22/09/2026 il ciano scelto a occhio per «Oceano» dava **2.43**
fra il bianco e il fondo dei pulsanti — sotto 3.0, illeggibile anche per un testo
grande, mentre gli altri tre temi stavano fra 3.99 e 6.11. A occhio, su uno schermo
buono, sembrava a posto. Le soglie qui sotto sono quelle di WCAG 2.1; il minimo
accettato è **3.0**, che è il pavimento sotto cui non si scende, non un buon voto.
"""
import argparse
import io
import os
import re
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RADICE, "templates", "base.html")
TEMI = os.path.join(RADICE, "templates", "_temi.html")
LOGIN = os.path.join(RADICE, "templates", "login.html")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []
MINIMO = 3.0


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def luminanza(colore):
    c = colore.lstrip("#")
    if len(c) == 3:
        c = "".join(x * 2 for x in c)
    canali = []
    for i in (0, 2, 4):
        x = int(c[i:i + 2], 16) / 255
        canali.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canali[0] + 0.7152 * canali[1] + 0.0722 * canali[2]


def contrasto(a, b):
    la, lb = luminanza(a), luminanza(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Le coppie che finiscono davvero una sopra l'altra a schermo. Non sono tutte le
# combinazioni possibili: sono quelle che `base.html` mette davvero in contatto.
COPPIE = [
    ("testo sul fondo", "text", "bg"),
    ("testo su una card", "text", "surface"),
    ("testo tenue su una card", "text-muted", "surface"),
    ("bianco su primary (.btn-primary, .calc-tab.active)", "#ffffff", "primary"),
    ("bianco su primary-h (hover)", "#ffffff", "primary-h"),
    ("primary su primary-dim (.badge-primary, .nav-item.active)", "primary", "primary-dim"),
    ("bianco su error", "#ffffff", "error"),
    ("success su success-dim", "success", "success-dim"),
    ("--fanta su una card (sezione Fantacalcio)", "fanta", "surface"),
]


def leggi():
    colori = io.open(TEMI, encoding="utf-8").read()
    testo = io.open(BASE, encoding="utf-8").read()
    login = io.open(LOGIN, encoding="utf-8").read()
    blocchi = re.findall(
        r'(?::root,\[data-theme="dark"\]|\[data-theme="(\w+)"\])\s*\{(.*?)\}',
        colori, re.S)
    temi = {}
    for nome, corpo in blocchi:
        # ⚠️ I commenti vanno tolti prima di cercare le variabili: dentro ce ne sono
        # di citate a titolo di spiegazione (#2fb6c9), e contarle come dichiarazioni
        # farebbe dire a questo script che un tema ha un colore che non ha.
        corpo = re.sub(r"/\*.*?\*/", "", corpo, flags=re.S)
        temi[nome or "dark"] = dict(
            re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})", corpo))
    menu = re.search(r"\{%\s*set\s+temi\s*=\s*\[(.*?)\]\s*%\}", testo, re.S)
    nel_menu = re.findall(r"\('([\w-]+)'\s*,", menu.group(1)) if menu else []
    js = re.search(r"const\s+TEMI\s*=\s*\[(.*?)\]", testo)
    nel_js = re.findall(r"'([\w-]+)'", js.group(1)) if js else []
    jsc = re.search(r"const\s+TEMI_CHIARI\s*=\s*\[(.*?)\]", testo)
    chiari = re.findall(r"'([\w-]+)'", jsc.group(1)) if jsc else []
    # ⚠️ Il login e' una pagina a se': non estende `base.html` e ha un suo elenco di
    # temi validi, perche' applica il tema **nel `<head>`** per non far lampeggiare
    # lo scuro a chi ne usa un altro. Quindi va guardato anche lui.
    jsl = re.search(r"var\s+temi\s*=\s*\[(.*?)\]", login)
    nel_login = re.findall(r"'([\w-]+)'", jsl.group(1)) if jsl else []
    # E non deve tornare ad avere una **copia** dei colori: e' la deriva tolta il
    # 22/09/2026, ed e' l'unica che questo script puo' vedere prima che faccia danno.
    senza_commenti = re.sub(r"\{#.*?#\}", "", login, flags=re.S)
    copia = bool(re.search(r"\[data-theme=\"\w+\"\]\s*\{", senza_commenti))
    return temi, nel_menu, nel_js, chiari, nel_login, copia


# Le coppie sotto il pavimento che **restano com'erano**, con scritto perché. Come le
# `ECCEZIONI` di `controlla_proprietario.py`: una misura fuori soglia o si corregge o
# si dichiara, e la terza strada — abbassare la soglia — le nasconderebbe tutte.
DICHIARATE = {
    ("dark", "bianco su primary-h (hover)"):
        "2.95, e il tema scuro è così da sempre: il viola dell'hover schiarisce "
        "invece di scurire, che è la scelta di disegno di tutto il tema. Trovata "
        "il 22/09/2026 scrivendo questo script, **non corretta**: cambiarla vuol "
        "dire cambiare il colore principale dell'hub, e non è una cosa da fare di "
        "propria iniziativa dentro un lavoro sui temi nuovi. È uno **stato "
        "transitorio** su un pulsante già leggibile da fermo (3.99), quindi non "
        "rende niente inservibile — ma va deciso, non dimenticato: sta in §3 del "
        "backlog",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tutto", action="store_true",
                    help="stampa la tabella dei contrasti, non solo i guai")
    args = ap.parse_args()

    temi, nel_menu, nel_js, chiari, nel_login, copia_nel_login = leggi()
    base = temi.get("dark", {})

    print("\n== 1. i quattro elenchi dicono gli stessi temi ==")
    esito("il CSS dichiara dei temi", len(temi) >= 2, ", ".join(temi))
    esito("la lista del menu combacia col CSS", set(nel_menu) == set(temi),
          f"menu: {nel_menu}  css: {sorted(temi)}")
    esito("e `TEMI` in JavaScript pure", set(nel_js) == set(temi),
          f"js: {nel_js}")
    esito("`TEMI_CHIARI` non nomina temi che non esistono",
          set(chiari) <= set(temi), f"chiari: {chiari}")
    esito("e l'elenco nel <head> del login pure", set(nel_login) == set(temi),
          f"login: {nel_login}")
    esito("il login NON ha una copia sua dei colori", not copia_nel_login,
          "ne ha una: due liste di colori divergono, e in silenzio"
          if copia_nel_login else "usa `_temi.html` come base.html")

    print("\n== 2. ogni tema dichiara le stesse variabili ==")
    # ⚠️ `:root` porta anche le misure (`--radius-*`, `--sidebar`, `--topbar`), che
    # un tema non deve ridichiarare: il confronto è sui **colori**, cioè su ciò che
    # il tema chiaro — il primo che è stato scritto — ha ritenuto di dover cambiare.
    attese = set(temi.get("light", {}))
    esito("il tema chiaro è il metro, e ha delle variabili", bool(attese),
          f"{len(attese)} colori")
    for nome, v in temi.items():
        if nome == "dark":
            continue
        mancano = sorted(attese - set(v))
        esito(f"{nome}: non ne manca nessuna", not mancano,
              "mancano: " + ", ".join(mancano) if mancano else "")

    print("\n== 3. i contrasti stanno sopra il pavimento ==")
    if args.tutto:
        print(f"    {'':<56}" + "".join(f"{t:>9}" for t in temi))
    guai = []
    for etichetta, a, b in COPPIE:
        riga = f"    {etichetta:<56}"
        for nome in temi:
            v = {**base, **temi[nome]}
            ca = a if a.startswith("#") else v.get(a)
            cb = b if b.startswith("#") else v.get(b)
            if not ca or not cb:
                riga += f"{'--':>9}"
                continue
            r = contrasto(ca, cb)
            dichiarata = (nome, etichetta) in DICHIARATE
            riga += f"{r:>8.2f}" + ("!" if r < MINIMO and not dichiarata
                                    else "*" if dichiarata else " ")
            if r < MINIMO and not dichiarata:
                guai.append((nome, etichetta, round(r, 2)))
        if args.tutto:
            print(riga)
    esito(f"nessuna coppia sotto {MINIMO}", not guai,
          "; ".join(f"{t}: {e} = {r}" for t, e, r in guai) if guai
          else f"{len(COPPIE)} coppie x {len(temi)} temi")
    # ⚠️ Le dichiarate si **stampano sempre**, anche quando tutto passa: una misura
    # fuori soglia che smette di comparire smette anche di essere una decisione, e
    # diventa una cosa che nessuno guarda più.
    if DICHIARATE:
        print("\n-- sotto il pavimento, e dichiarate (vedi DICHIARATE) --")
        for (nome, etichetta), perche in DICHIARATE.items():
            v = {**base, **temi.get(nome, {})}
            trovata = next((c for e, a, b in COPPIE if e == etichetta
                            for c in [contrasto(a if a.startswith("#") else v.get(a),
                                                b if b.startswith("#") else v.get(b))]),
                           None)
            print(f"  {nome} — {etichetta}: {trovata:.2f}" if trovata
                  else f"  {nome} — {etichetta}")
            print(f"      {perche}")

    passate = sum(esiti)
    print(f"\n{passate} prove su {len(esiti)}." +
          ("  Tutte passate." if passate == len(esiti) else "  FALLITE."))
    return 0 if passate == len(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
