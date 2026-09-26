#!/usr/bin/env python
"""Dà i flag alle mosse di Gen 8-9, che il dump di PokéAPI non ha, leggendoli da Bulbapedia.

    python scripts/integra_flag_mosse.py [--dry-run] [--aggiorna]

Decisione di Davide del 23/09/2026. `move_flag_map.csv` ha i flag di **748 mosse**, ma
nessuna riga per le mosse di Gen 8-9: Rage Fist, Jet Punch, Wave Crash… Nel catalogo
avevano quindi `flags: None`, cioè né `contact` né `punch`, e il calcolatore — che legge
proprio quei due — non le vedeva: Unghiedure, Lanugine e il Guantone ci passavano sopra
**senza nessun errore**.

**Quali mosse**: quelle del catalogo con id del dump ≥ 743 (Gen 8 in poi) e **zero** righe
in `move_flag_map.csv`, tranne le mosse Max e G-Max, che in Champions non ci sono. Il
conto del 23/09/2026: **95**. Si decide dal dump e non a mano, così una mossa che PokéAPI
un giorno coprirà esce da sola dall'elenco.

**Da dove vengono i flag**, tutto da Bulbapedia (wikitext grezzo, in cache in
`data/cache/bulbapedia/mosse/`):

- l'infobox della pagina «<mossa> (move)»: `touches` → `contact`, `protect` → `protect`,
  `magiccoat` → `reflectable`, `snatch` → `snatch`, `mirrormove` → `mirror`,
  `sound` → `sound` (i nomi sono quelli che il catalogo usa già)
- le pagine-elenco, righe `{{movelist|…}}`: *Punching move* → `punch`, *Biting move* →
  `bite`, *Slicing move* → `slicing`, *Sound-based move* → `sound`, *Ball and bomb move*
  → `bullet`, *Pulse move* → `pulse`, *Dance move* → `dance`, *Powder and spore move* →
  `powder`.
  *Punching move* dice già «Double Shock — From Pokémon Champions onwards»: è la 1.2.0

Gli altri flag del catalogo (`authentic`, `heal`, `charge`, `recharge`, `gravity`,
`defrost`, `distance`, `mental`, `non-sky-battle`) Bulbapedia non li dà in una forma
leggibile così, e **restano come sono**: il calcolatore non li legge.

⚠️ **Aggiunge, non toglie.** Un flag già nel catalogo resta anche se Bulbapedia non lo
conferma: sono i flag scritti a mano, e fra loro quelli della 1.2.0 di Champions
(`allinea_dati_mosse_champions.py`). Dove le due fonti non concordano **lo dice e basta**,
come vuole il metodo di §5.2.

⚠️ **Si ferma su ciò che non risolve.** Se una pagina non esiste, o non ha l'infobox, o
un elenco non ha righe `{{movelist}}`, non scrive **niente** ed esce con 1. Rieseguibile:
una mossa che ha già tutti i suoi flag viene contata e saltata. La copia di sicurezza la
lascia `salva_catalogo()`, in `data/archive/`. `--aggiorna` riscarica le pagine invece
di leggerle dalla cache.
"""
import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse

import requests

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from blueprints.pokemon import voci_catalogo, salva_catalogo  # noqa: E402

INDEX = "https://bulbapedia.bulbagarden.net/w/index.php"
UA = {"User-Agent": "Mozilla/5.0 (compatible; personal-hub/1.0)"}
CACHE = os.path.join(RADICE, "data", "cache", "bulbapedia", "mosse")
# Lo stesso dump e la stessa cartella di `build_catalog.py`
CSV_DUMP = os.environ.get("POKEAPI_CACHE") or os.path.join(tempfile.gettempdir(), "pokeapi_csv")
BASE_CSV = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"

PRIMO_ID_GEN8 = 743

INFOBOX = {"touches": "contact", "protect": "protect", "magiccoat": "reflectable",
           "snatch": "snatch", "mirrormove": "mirror", "sound": "sound"}
ELENCHI = {"Punching move": "punch", "Biting move": "bite", "Slicing move": "slicing",
           "Sound-based move": "sound", "Ball and bomb move": "bullet", "Pulse move": "pulse",
           "Dance move": "dance", "Powder and spore move": "powder"}

CAMPO = re.compile(r"^\|\s*(\w+)\s*=\s*(.*?)\s*$", re.M)
MOVELIST = re.compile(r"\{\{movelist\|([^|}]+)")


# ── fonti ────────────────────────────────────────────────────────────────────
def csv_dump(nome):
    percorso = os.path.join(CSV_DUMP, nome)
    if not os.path.exists(percorso):
        os.makedirs(CSV_DUMP, exist_ok=True)
        r = requests.get(BASE_CSV + nome, headers=UA, timeout=60)
        r.raise_for_status()
        open(percorso, "w", encoding="utf-8", newline="").write(r.text)
    return list(csv.DictReader(open(percorso, encoding="utf-8")))


def pagina(titolo, aggiorna):
    """Il wikitext grezzo di una pagina, dalla cache se c'è. `None` se non esiste."""
    percorso = os.path.join(CACHE, urllib.parse.quote(titolo, safe="") + ".txt")
    if os.path.exists(percorso) and os.path.getsize(percorso) and not aggiorna:
        return open(percorso, encoding="utf-8").read()
    r = requests.get(INDEX, headers=UA, timeout=60, params={"title": titolo, "action": "raw"})
    time.sleep(1)
    if r.status_code != 200 or not r.text:
        return None
    os.makedirs(CACHE, exist_ok=True)
    open(percorso, "w", encoding="utf-8").write(r.text)
    return r.text


def identificatore(nome):
    """«Jet Punch» -> «jet-punch», come gli `identifier` del dump."""
    return re.sub(r"[^a-z0-9-]", "", nome.lower().replace(" ", "-"))


def mosse_senza_flag(voci):
    """Le mosse del catalogo che il dump non copre: Gen 8+, zero righe di flag."""
    ids = {r["identifier"]: int(r["id"]) for r in csv_dump("moves.csv")}
    con_flag = {int(r["move_id"]) for r in csv_dump("move_flag_map.csv")}
    fuori = []
    for nome in voci:
        if nome.startswith(("Max ", "G-Max ")):
            continue
        i = ids.get(identificatore(nome))
        if i and i >= PRIMO_ID_GEN8 and i not in con_flag:
            fuori.append(nome)
    return sorted(fuori)


def flag_infobox(testo):
    """I flag che l'infobox dice `yes`; `None` se l'infobox non c'è."""
    if not testo or "{{MoveInfobox" not in testo:
        return None
    blocco = testo[testo.index("{{MoveInfobox"):]
    blocco = blocco[:blocco.index("\n}}")] if "\n}}" in blocco else blocco
    campi = dict(CAMPO.findall(blocco))
    return {flag for campo, flag in INFOBOX.items() if campi.get(campo, "").lower() == "yes"}


def da_elenco(voci, flag, args):
    """`--da-elenco <flag>`: il flag di **una** pagina-elenco su **tutto** il catalogo.

    Dal 26/09/2026, per Affilama. Il giro normale guarda solo le mosse di Gen 8+ senza
    righe nel dump, e per quasi tutti i flag basta: il dump li ha. Non per `slicing`,
    che nasce in Gen 9 — il dump non lo dà a nessuna mossa vecchia — e che Champions
    ha allargato alle mosse «artiglio»: così Aerial Ace, Sacred Sword, Razor Leaf e
    altre tre restavano fuori, e Affilama ci sarebbe passata sopra **senza errore**.
    Misurato quel giorno su tutte le liste: mancavano solo queste sei (e cinque di
    `bullet`, lasciate fuori perché nessuno l'aveva chiesto). Aggiunge e non toglie,
    come il giro normale; un nome della lista che il catalogo non ha si **dice**.
    """
    titolo = next((t for t, f in ELENCHI.items() if f == flag), None)
    if not titolo:
        print(f"`{flag}` non viene da nessuna pagina-elenco: {sorted(ELENCHI.values())}")
        return 1
    nomi = {n.strip() for n in MOVELIST.findall(pagina(titolo, args.aggiorna) or "")}
    if not nomi:
        print(f"elenco «{titolo}»: nessuna riga {{{{movelist}}}}, non scrivo niente.")
        return 1
    per_nome_en = {(v.get("nome_en") or k): k for k, v in voci.items()}
    fuori = sorted(n for n in nomi if n not in per_nome_en)
    da_scrivere = sorted(per_nome_en[n] for n in nomi if n in per_nome_en
                         and flag not in (voci[per_nome_en[n]].get("flags") or []))
    senza_lista = sorted(k for k, v in voci.items() if flag in (v.get("flags") or [])
                         and (v.get("nome_en") or k) not in nomi)
    print(f"elenco «{titolo}»: {len(nomi)} mosse, {len(da_scrivere)} senza `{flag}`")
    for chiave in da_scrivere:
        print(f"+ {chiave}")
    for n in fuori:
        print(f"? {n}: nella lista, non nel catalogo (non la invento)")
    for chiave in senza_lista:
        print(f"≠ {chiave}: ha `{flag}` ma non è nella lista (resta)")
    if not da_scrivere:
        print("Niente da fare.")
        return 0
    if args.dry_run:
        print("--dry-run: file non toccato.")
        return 0
    for chiave in da_scrivere:
        voci[chiave]["flags"] = sorted(set(voci[chiave].get("flags") or []) | {flag})
    salva_catalogo("moves", voci)
    print("Scritto data/catalog/moves.json (copia precedente in data/archive/).")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="dice cosa farebbe e non scrive niente")
    ap.add_argument("--aggiorna", action="store_true", help="riscarica le pagine di Bulbapedia")
    ap.add_argument("--da-elenco", metavar="FLAG",
                    help="porta il flag di una pagina-elenco su tutto il catalogo (es. slicing)")
    args = ap.parse_args()

    voci = voci_catalogo("moves")
    if not voci:
        print("Catalogo mosse vuoto o illeggibile: non tocco niente.")
        return 1
    if args.da_elenco:
        return da_elenco(voci, args.da_elenco, args)

    problemi = []
    per_elenco = {}
    for titolo, flag in ELENCHI.items():
        nomi = {n.strip() for n in MOVELIST.findall(pagina(titolo, args.aggiorna) or "")}
        print(f"elenco «{titolo}»: {len(nomi)} mosse -> `{flag}`")
        if not nomi:
            problemi.append(f"elenco «{titolo}»: nessuna riga {{{{movelist}}}}")
        for n in nomi:
            per_elenco.setdefault(n, set()).add(flag)

    bersagli = mosse_senza_flag(voci)
    print(f"mosse di Gen 8+ senza flag nel dump: {len(bersagli)}")

    da_scrivere, gia_fatte, disaccordi = [], [], []
    for nome in bersagli:
        voce = voci[nome]
        titolo_en = voce.get("nome_en") or nome
        dall_infobox = flag_infobox(pagina(f"{titolo_en} (move)", args.aggiorna))
        if dall_infobox is None:
            problemi.append(f"{nome}: pagina «{titolo_en} (move)» assente o senza infobox")
            continue
        bulba = dall_infobox | per_elenco.get(titolo_en, set())
        prima = set(voce.get("flags") or [])
        if prima - bulba:
            disaccordi.append(f"{nome}: il catalogo ha {sorted(prima - bulba)}, "
                              f"Bulbapedia no (restano)")
        dopo = prima | bulba
        if dopo == prima:
            gia_fatte.append(nome)
            continue
        da_scrivere.append((nome, voce, sorted(dopo), sorted(bulba - prima)))

    for nome, _, _, nuovi in da_scrivere:
        print(f"+ {nome:22s} {', '.join(nuovi)}")
    if gia_fatte:
        print(f"= gia' complete: {len(gia_fatte)}")
    for riga in disaccordi:
        print("≠ " + riga)
    for riga in problemi:
        print("X " + riga)

    contatto = sum(1 for _, _, _, n in da_scrivere if "contact" in n)
    pugno = sum(1 for _, _, _, n in da_scrivere if "punch" in n)
    print(f"\n{len(da_scrivere)} mosse da completare: {contatto} prendono `contact`, "
          f"{pugno} prendono `punch`. Disaccordi: {len(disaccordi)}.")

    if problemi:
        print(f"{len(problemi)} problemi: non scrivo niente.")
        return 1
    if not da_scrivere:
        print("Niente da fare: tutti i flag sono gia' nel catalogo.")
        return 0
    if args.dry_run:
        print("--dry-run: file non toccato.")
        return 0

    for _, voce, dopo, _ in da_scrivere:
        voce["flags"] = dopo
    salva_catalogo("moves", voci)
    print("Scritto data/catalog/moves.json (copia precedente in data/archive/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
