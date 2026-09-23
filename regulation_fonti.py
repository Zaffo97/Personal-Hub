"""Il roster e gli oggetti di una regulation, confrontati con le fonti.

Chiesto da Davide il 22/09/2026 («un pulsante per creare una regulation nuova senza
inserire i dati a mano, con una fonte affidabile da cui confrontare i dati»); fonti
decise il 23/09/2026: **Serebii e Bulbapedia**, le stesse con cui era stato confermato
M-C. Misurato lo stesso giorno, prima di scrivere una riga:

- **Bulbapedia**, «Regulation Set M-C»: il roster **completo**, righe
  `{{CPCard|0026|Raichu|ig=-Alola|…}}` — numero di Pokédex più forma
- **Serebii**, `pokemonchampions/rankedbattle/regulationm-c.shtml`: solo le **aggiunte**
  rispetto alla regulation prima («Newly Useable Pokémon», icone `026-a.png`) e — la
  parte che nessun'altra fonte dava — **«Newly Added Items»**
- le due concordano **specie per specie** su M-A (186) e M-B (208); in M-C l'unica
  differenza è Kingambit

**Le regole**, che sono il punto di questo modulo:

1. una **specie** entra o esce solo se le due fonti **concordano**. Se non concordano
   resta com'è, e il disaccordo si mostra
2. le **forme** vengono da Bulbapedia, l'unica con l'elenco completo; Serebii le
   conferma dove ha l'icona
3. restano le **forme nostre**: voci del roster che le fonti non elencano ma la cui specie
   è ammessa — le forme di battaglia (Aegislash Spada, Castform, Morpeko, Palafin Eroe) e
   simili. È una convenzione di questo progetto, non un disaccordo
4. gli **oggetti si aggiungono e non si tolgono**: Serebii elenca le aggiunte, e da M-B in
   poi sono cumulative
5. un nome che non si risolve sul catalogo **ferma tutto**: niente si scrive a metà

Come `fanta_import.py`: le funzioni non stampano, tornano dizionari, e si rifiutano con
`ok=False` e il motivo. Le pagine scaricate stanno in `data/cache/fonti_regulation/`.
"""
import csv
import html
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime

import requests

RADICE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(RADICE, "data")
CACHE = os.path.join(DATA, "cache", "fonti_regulation")
ARCHIVIO = os.path.join(DATA, "archive")
UA = {"User-Agent": "Mozilla/5.0 (compatible; personal-hub/1.0)"}

BULBA = "https://bulbapedia.bulbagarden.net/w/index.php"
SEREBII = "https://www.serebii.net/pokemonchampions/rankedbattle/regulation{sigla}.shtml"

CPCARD = re.compile(r"\{\{CPCard\|(\d+)\|([^|}]+)((?:\|[^}]*)?)\}\}")
ICONA = re.compile(r"/pokedex-champions/icon/([0-9]+)(?:-([a-z]+))?\.png")
OGGETTO = re.compile(r'<a href="/itemdex/[^"]+">([^<]+)</a>')

# Suffisso dell'icona di Serebii -> forma come la scrive Bulbapedia (`ig=`).
SUFFISSI_SEREBII = {"": "", "a": "-Alola", "g": "-Galar", "h": "-Hisui", "m": "-Mega",
                    "mx": "-Mega X", "my": "-Mega Y", "mz": "-Mega Z", "f": "-Female",
                    "l": "-Low Key", "e": "-Eternal"}
# ⚠️ Tauros di Paldea usa le lettere a modo suo: `a` lì non è Alola
SUFFISSI_PER_NUMERO = {128: {"p": "-Paldea Combat", "b": "-Paldea Blaze", "a": "-Paldea Aqua"}}
# Forme che Bulbapedia chiama diversamente dallo slug del dump
FORME_BULBA = {"-Paldea Combat": "paldea-combat-breed", "-Paldea Blaze": "paldea-blaze-breed",
               "-Paldea Aqua": "paldea-aqua-breed", "-Jumbo": "super"}
# Forme che nel catalogo non sono voci a sé: si prende la specie (i disegni di
# Vivillon sono solo estetici, e nel dump non sono `pokemon` separati)
FORME_ESTETICHE = {(666, "-Fancy")}


def sigla(reg_id):
    """`mc` -> `M-C`; `None` per chi non segue lo schema di Champions (es. `pokedex`)."""
    return f"{reg_id[0]}-{reg_id[1]}".upper() if re.fullmatch(r"[a-z]{2}", reg_id or "") else None


def catena(reg_id):
    """Le regulation da leggere su Serebii, dalla prima a questa: `mc` -> ma, mb, mc."""
    return [f"{reg_id[0]}{chr(c)}" for c in range(ord("a"), ord(reg_id[1]) + 1)]


def normalizza(nome):
    return re.sub(r"[^a-z0-9]", "", html.unescape(nome or "").lower().replace("’", "'"))


# ── scaricare, con la cache ──────────────────────────────────────────────────
def _pagina(url, params, nome, aggiorna, codifica="utf-8"):
    percorso = os.path.join(CACHE, nome)
    if os.path.exists(percorso) and os.path.getsize(percorso) and not aggiorna:
        return io.open(percorso, encoding="utf-8").read()
    r = requests.get(url, params=params, headers=UA, timeout=60)
    time.sleep(1)
    if r.status_code != 200 or not r.content:
        return None
    testo = r.content.decode(codifica, errors="replace")
    os.makedirs(CACHE, exist_ok=True)
    io.open(percorso, "w", encoding="utf-8").write(testo)
    return testo


def bulbapedia(sig, aggiorna=False):
    """`[(numero, nome, forma)]` dal roster completo di Bulbapedia, o `None`."""
    titolo = f"Regulation Set {sig}"
    testo = _pagina(BULBA, {"title": titolo, "action": "raw"},
                    urllib.parse.quote(titolo, safe="") + ".txt", aggiorna)
    if not testo:
        return None
    fuori = []
    for num, nome, resto in CPCARD.findall(testo):
        ig = re.search(r"ig=([^|}]*)", resto)
        fuori.append((int(num), nome.strip(), ig.group(1).strip() if ig else ""))
    return fuori or None


def serebii(sig, aggiorna=False):
    """`([(numero, forma)], [oggetti])` aggiunti da questa regulation, o `None`."""
    testo = _pagina(SEREBII.format(sigla=sig.lower()), None, f"serebii_{sig.lower()}.html",
                    aggiorna, codifica="latin-1")
    if not testo or "Newly Useable" not in testo:
        return None
    blocco = testo[testo.index("Newly Useable"):]
    oggetti_da = blocco.find("Newly Added Items")
    pokemon = blocco[:oggetti_da] if oggetti_da >= 0 else blocco
    fuori = []
    for num, suf in ICONA.findall(pokemon):
        n = int(num)
        forma = SUFFISSI_PER_NUMERO.get(n, {}).get(suf or "", SUFFISSI_SEREBII.get(suf or ""))
        fuori.append((n, forma if forma is not None else f"?{suf}"))
    oggetti = []
    if oggetti_da >= 0:
        sezione = blocco[oggetti_da:]
        sezione = sezione[:sezione.find("Game Names")] if "Game Names" in sezione else sezione
        oggetti = list(dict.fromkeys(html.unescape(o).strip()
                                     for o in OGGETTO.findall(sezione) if o.strip()))
    return fuori, oggetti


# ── risolvere sul catalogo ───────────────────────────────────────────────────
class Risolutore:
    """Numero di Pokédex + forma -> il nome con cui il roster scrive la voce."""

    def __init__(self):
        import pokeapi
        if pokeapi.file_mancanti():
            pokeapi.scarica_mancanti()
        leggi = lambda n: list(csv.DictReader(io.open(pokeapi.percorso(n), encoding="utf-8")))
        pokemon = leggi("pokemon.csv")
        self.specie = {int(r["id"]): r["identifier"] for r in leggi("pokemon_species.csv")}
        self.default = {int(r["species_id"]): r["identifier"] for r in pokemon if r["is_default"] == "1"}
        numero_slug = {r["identifier"]: int(r["species_id"]) for r in pokemon}

        with io.open(os.path.join(DATA, "catalog", "pokemon.json"), encoding="utf-8") as f:
            catalogo = json.load(f)
        self.per_slug, self.numero = {}, {}
        for k, v in catalogo.items():
            nome = v.get("name") or k
            slug = v.get("slug") or k
            self.per_slug[slug] = nome
            self.numero[nome] = numero_slug.get(slug)
            for nf, f in (v.get("forms") or {}).items():
                if f.get("slug"):
                    self.per_slug[f["slug"]] = nf
                # una forma senza slug è della specie della sua voce
                self.numero[nf] = numero_slug.get(f.get("slug")) or numero_slug.get(slug)

    def nome(self, num, forma):
        base = self.specie.get(num)
        if not forma or (num, forma) in FORME_ESTETICHE:
            return self.per_slug.get(self.default.get(num)) or self.per_slug.get(base)
        suf = FORME_BULBA.get(forma) or forma.strip("-").lower().replace(" ", "-")
        for cand in (f"{base}-{suf}", f"{self.default.get(num)}-{suf}"):
            if cand in self.per_slug:
                return self.per_slug[cand]
        vicini = [s for s in self.per_slug if s.startswith(f"{base}-{suf}")]
        return self.per_slug[vicini[0]] if len(vicini) == 1 else None


def _oggetti_catalogo():
    with io.open(os.path.join(DATA, "catalog", "items.json"), encoding="utf-8") as f:
        voci = json.load(f)
    indice = {}
    for k, v in voci.items():
        indice[normalizza(k)] = k
        if v.get("nome_en"):
            indice[normalizza(v["nome_en"])] = k
    return indice


# ── il confronto ─────────────────────────────────────────────────────────────
def _filtro(reg_id):
    percorso = os.path.join(DATA, "regulations", f"{reg_id}.json")
    if not os.path.exists(percorso):
        return None, percorso
    with io.open(percorso, encoding="utf-8") as f:
        return json.load(f), percorso


def confronto(reg_id, aggiorna=False):
    """Cosa dicono le fonti di questa regulation, e cosa cambierebbe. Non scrive."""
    sig = sigla(reg_id)
    if not sig:
        return {"ok": False, "errore": f"«{reg_id}» non è una regulation di Champions (es. mc)"}
    filtro, _ = _filtro(reg_id)
    if not filtro or filtro.get("pokemon") is None:
        return {"ok": False, "errore": "la regulation non ha un roster esplicito da confrontare"}

    try:
        b = bulbapedia(sig, aggiorna)
        s_catena = [(r, serebii(sigla(r), aggiorna)) for r in catena(reg_id)]
    except requests.RequestException as e:
        return {"ok": False, "errore": f"fonte non raggiungibile: {e}"}
    if not b:
        return {"ok": False, "errore": f"Bulbapedia non ha la pagina «Regulation Set {sig}»"}
    mancanti = [sigla(r) for r, s in s_catena if s is None]
    if mancanti:
        return {"ok": False, "errore": f"Serebii non ha la pagina di {', '.join(mancanti)}"}

    R = Risolutore()
    problemi = []

    fonte_b = set()
    for num, nome, forma in b:
        n = R.nome(num, forma)
        (fonte_b.add(n) if n else problemi.append(f"Bulbapedia: {num} {nome} {forma} non risolto"))
    fonte_s, oggetti_s = set(), []
    for _, (voci, oggetti) in s_catena:
        oggetti_s += oggetti
        for num, forma in voci:
            n = R.nome(num, forma)
            (fonte_s.add(n) if n else problemi.append(f"Serebii: {num} {forma} non risolto"))

    specie_b = {R.numero.get(n) for n in fonte_b}
    specie_s = {R.numero.get(n) for n in fonte_s}
    concordi = specie_b & specie_s
    attuale = set(filtro["pokemon"])

    dalle_fonti = {n for n in fonte_b | fonte_s if R.numero.get(n) in concordi}
    da_aggiungere = sorted(dalle_fonti - attuale)
    da_togliere = sorted(n for n in attuale if R.numero.get(n) not in specie_b | specie_s)
    forme_nostre = sorted(n for n in attuale - dalle_fonti if R.numero.get(n) in concordi)
    # una specie che una fonte sola dà: non si aggiunge e non si toglie
    disaccordi = []
    for num in sorted(x for x in specie_b ^ specie_s if x):
        chi = "solo Bulbapedia" if num in specie_b else "solo Serebii"
        voci = sorted(n for n in (fonte_b | fonte_s) if R.numero.get(n) == num)
        disaccordi.append({"specie": R.specie.get(num), "fonte": chi,
                           "nel_roster": bool(set(voci) & attuale), "voci": voci})

    indice = _oggetti_catalogo()
    oggetti, oggetti_irrisolti = [], []
    for o in oggetti_s:
        k = indice.get(normalizza(o))
        (oggetti.append(k) if k else oggetti_irrisolti.append(o))
    problemi += [f"Serebii: l'oggetto «{o}» non è nel catalogo" for o in oggetti_irrisolti]
    oggetti_nuovi = sorted(set(oggetti) - set(filtro.get("items") or []))

    return {
        "ok": not problemi, "errore": "nomi che il catalogo non risolve: non si scrive" if problemi else "",
        "problemi": problemi, "reg": reg_id, "sigla": sig,
        "conti": {"bulbapedia": len(fonte_b), "serebii": len(fonte_s), "roster": len(attuale),
                  "specie_concordi": len(concordi)},
        "da_aggiungere": da_aggiungere, "da_togliere": da_togliere,
        "forme_nostre": forme_nostre, "disaccordi": disaccordi,
        "oggetti_nuovi": oggetti_nuovi, "oggetti_fonte": len(oggetti),
    }


def applica(reg_id):
    """Scrive roster, oggetti e mega_map, poi rideriva le mosse. Rifà il confronto.

    ⚠️ Non si fida di un confronto arrivato dal browser. Copia di sicurezza in
    `data/archive/regulation_<id>_pre-fonti.json`. Le mosse le deriva
    `scripts/allinea_mosse_regulation.py`, lanciato così com'è: la regola è sua.
    """
    from data import collega_mega, applica_collegamenti

    c = confronto(reg_id, aggiorna=False)
    if not c["ok"]:
        return c
    if not (c["da_aggiungere"] or c["da_togliere"] or c["oggetti_nuovi"]):
        return dict(c, scritto=False, messaggio="il roster e gli oggetti sono già allineati alle fonti")

    filtro, percorso = _filtro(reg_id)
    os.makedirs(ARCHIVIO, exist_ok=True)
    with io.open(os.path.join(ARCHIVIO, f"regulation_{reg_id}_pre-fonti.json"), "w", encoding="utf-8") as f:
        json.dump(filtro, f, ensure_ascii=False, indent=2)

    roster = (set(filtro["pokemon"]) | set(c["da_aggiungere"])) - set(c["da_togliere"])
    filtro["pokemon"] = sorted(roster)
    filtro["items"] = sorted(set(filtro.get("items") or []) | set(c["oggetti_nuovi"]))
    # la mega_map perde chi è uscito e collega le Mega entrate
    mm = {b: [m for m in v if m in roster] for b, v in (filtro.get("mega_map") or {}).items() if b in roster}
    mm = {b: v for b, v in mm.items() if v}
    R = Risolutore()
    collegamenti, _, _ = collega_mega(sorted(roster), set(R.per_slug.values()) | set(R.numero), mm)
    filtro["mega_map"] = applica_collegamenti(mm, collegamenti)
    filtro["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with io.open(percorso, "w", encoding="utf-8") as f:
        json.dump(filtro, f, ensure_ascii=False, indent=2)

    mosse = subprocess.run([sys.executable, os.path.join(RADICE, "scripts", "allinea_mosse_regulation.py"),
                            "--reg", reg_id], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=RADICE)
    return dict(c, scritto=True, roster_dopo=len(roster), mega_collegate=len(collegamenti),
                mosse_ok=mosse.returncode == 0,
                mosse_esito=(mosse.stdout.strip().splitlines() or [""])[-3:])
