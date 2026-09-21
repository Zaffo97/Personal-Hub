"""Leggere il listone e le statistiche di Serie A da fantacalcio.it.

È la fonte della sezione Fantacalcio (§4.2), e sta qui accanto a `pokeapi.py` per la
stessa ragione: **legge e basta**. Non scrive niente nel DB — la scrittura resta a
`scripts/importa_listone.py`, che è l'unico che sa cosa fare di una voce che sparisce.

⚠️ **Perché le pagine e non il file Excel.** `fantacalcio.it` (che è l'ex
Fantagazzetta) offre l'export del listone su `/api/v1/Excel/prices/21/1`, ma quella
strada **pretende un account**: provata il 21/09/2026, risponde **401**. Le tre pagine
pubbliche invece sono **renderizzate dal server** — il loro HTML contiene già tutto,
niente JavaScript da eseguire — quindi si leggono con `requests` e `HTMLParser` come
già fa `importa_roster_champions.py` sulla wiki, e **senza mettere credenziali nel
progetto**.

⚠️ **La chiave è l'id, non il nome.** Ogni giocatore porta il suo id numerico
nell'URL della sua pagina (`/serie-a/squadre/inter/martinez-l/2764`), **uguale in
tutte e tre le pagine**. Le liste si incrociano per quello: il nome è abbreviato
(`Martinez L.`), due squadre possono avere due `Martinez`, e legare per nome è
esattamente la classe di baco che questo progetto ha già pagato sul catalogo Pokémon.

Le tre pagine, misurate il 21/09/2026:

- **quotazioni** — 597 giocatori: ruolo Classic *e* Mantra, squadra, partite a voto,
  quotazione iniziale (QI), attuale (QA) e valore di mercato (FVM), per tutti e due i
  sistemi
- **statistiche** — gli stessi 597: media voto, fantamedia, gol, gol subiti, rigori,
  assist, ammonizioni, espulsioni. I nomi delle colonne li dichiara il sito nei
  `title` delle intestazioni, non sono indovinati: `pg` è «partite a **voto**», non
  le presenze, e `rig` è «segnati / tirati», quindi una frazione
- **probabili formazioni** — la giornata, il modulo di ogni squadra e l'undici

La cache sta in `data/cache/fantacalcio/` (ignorata da git come le altre): una
seconda lettura nello stesso giorno non ripassa dalla rete. Il mercato di gennaio si
prende con `--scarica`.
"""
import io
import os
import re
import time
from html.parser import HTMLParser

RADICE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(RADICE, "data", "cache", "fantacalcio")

BASE = "https://www.fantacalcio.it"
PAGINE = {
    "quotazioni": BASE + "/quotazioni-fantacalcio",
    "statistiche": BASE + "/statistiche-serie-a",
    "probabili": BASE + "/probabili-formazioni-serie-a",
}
UA = {"User-Agent": "Mozilla/5.0 (compatible; personal-hub/1.0; uso personale)"}

# I ruoli del sistema Classic, che è quello che usano tutte e due le leghe di Davide.
# La chiave è il valore del sito (`data-filter-role-classic`), e **non si traduce**:
# è il dato che finisce nel DB. L'etichetta è solo per lo schermo.
RUOLI_CLASSIC = {"p": "Portiere", "d": "Difensore", "c": "Centrocampista",
                 "a": "Attaccante"}

# L'id della pagina di un giocatore: .../serie-a/squadre/<squadra>/<nome>/<id>
_ID_NELL_URL = re.compile(r"/serie-a/squadre/([^/]+)/([^/]+)/(\d+)")


def percorso_cache(nome):
    return os.path.join(CACHE, nome + ".html")


def eta_cache(nome):
    """Da quante ore è ferma la copia in cache, o `None` se non c'è."""
    p = percorso_cache(nome)
    if not os.path.exists(p):
        return None
    return (time.time() - os.path.getmtime(p)) / 3600.0


def scarica(nome, forza=False):
    """L'HTML di una delle tre pagine, dalla cache o dalla rete.

    ⚠️ `forza=True` è la strada del **mercato**: a gennaio le squadre cambiano e la
    copia in cache direbbe il falso senza dare errore.
    """
    if nome not in PAGINE:
        raise ValueError(f"pagina sconosciuta: {nome}")
    p = percorso_cache(nome)
    if not forza and os.path.exists(p) and os.path.getsize(p) > 0:
        return io.open(p, encoding="utf-8").read()
    import requests
    r = requests.get(PAGINE[nome], headers=UA, timeout=90)
    r.raise_for_status()
    os.makedirs(CACHE, exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(r.text)
    return r.text


class _RigheGiocatori(HTMLParser):
    """Le righe `tr.player-row`: attributi di filtro, id dall'URL, celle per chiave.

    Tiene le celle **per `data-col-key`** e non per posizione: le due pagine hanno
    colonne diverse e nello stesso ordine non ci sono. Una colonna nuova domani
    compare da sola invece di spostare tutte le altre di uno.
    """

    def __init__(self):
        super().__init__()
        self.righe = []
        self._riga = None
        self._chiave = None
        self._testo = []
        self._in_nome = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classi = (a.get("class") or "").split()
        if tag == "tr" and "player-row" in classi:
            self._riga = {
                "nome": (a.get("data-filter-keywords") or "").strip(),
                "team_id": a.get("data-filter-team-id"),
                "ruolo_classic": (a.get("data-filter-role-classic") or "").strip(),
                "ruolo_mantra": (a.get("data-filter-role-mantra") or "").strip(),
                "celle": {},
            }
            return
        if self._riga is None:
            return
        if tag == "a" and "player-link" in classi:
            m = _ID_NELL_URL.search(a.get("href") or "")
            if m:
                self._riga.setdefault("squadra_slug", m.group(1))
                self._riga.setdefault("slug", m.group(2))
                self._riga.setdefault("id", int(m.group(3)))
            self._in_nome = True
            self._testo = []
        elif tag in ("td", "th") and a.get("data-col-key"):
            self._chiave = a["data-col-key"]
            self._testo = []
        # ⚠️ Il ruolo Mantra esteso sta nel `title` dello span, non nel testo: il
        # `data-value` da' la sigla (`pc`), il title da' «Punta centrale».
        elif tag == "span" and "role-mantra" in classi and a.get("title"):
            self._riga["ruolo_mantra_esteso"] = a["title"]

    def handle_data(self, dato):
        if self._riga is not None and (self._chiave or self._in_nome):
            self._testo.append(dato)

    def handle_endtag(self, tag):
        if self._riga is None:
            return
        if tag == "a" and self._in_nome:
            testo = " ".join("".join(self._testo).split())
            if testo and not self._riga.get("nome"):
                self._riga["nome"] = testo
            self._in_nome = False
        elif tag in ("td", "th") and self._chiave:
            self._riga["celle"][self._chiave] = " ".join("".join(self._testo).split())
            self._chiave = None
        elif tag == "tr":
            if self._riga.get("id"):
                self.righe.append(self._riga)
            self._riga = None


def _intero(testo):
    """Il numero intero in `testo`, o `None`. `''` e `'-'` valgono «non lo sappiamo»."""
    testo = (testo or "").strip()
    if not testo or testo in ("-", "—"):
        return None
    m = re.search(r"-?\d+", testo.replace(".", ""))
    return int(m.group(0)) if m else None


def _decimale(testo):
    """Il numero con la virgola in `testo`, o `None`.

    ⚠️ Il sito scrive `6,5` con la **virgola**: `float('6,5')` solleva, e un `try`
    muto qui trasformerebbe una media vera in «non lo sappiamo».
    """
    testo = (testo or "").strip().replace(",", ".")
    if not testo or testo in ("-", "—"):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", testo)
    return float(m.group(0)) if m else None


def quotazioni(forza=False):
    """`{id: {...}}` dal listone: ruoli, squadra, QI, QA, FVM."""
    p = _RigheGiocatori()
    p.feed(scarica("quotazioni", forza))
    fuori = {}
    for r in p.righe:
        fuori[r["id"]] = {
            "id": r["id"],
            "nome": r["nome"],
            "slug": r.get("slug"),
            "squadra": (r["celle"].get("sq") or "").upper() or None,
            "squadra_slug": r.get("squadra_slug"),
            "ruolo_classic": r["ruolo_classic"] or None,
            "ruolo_mantra": r["ruolo_mantra"] or None,
            "ruolo_mantra_esteso": r.get("ruolo_mantra_esteso"),
            "qi": _intero(r["celle"].get("c_qi")),
            "qa": _intero(r["celle"].get("c_qa")),
            "fvm": _intero(r["celle"].get("c_fvm")),
        }
    return fuori


def statistiche(forza=False):
    """`{id: {...}}` dalle statistiche: media voto, fantamedia, gol, cartellini.

    I nomi delle colonne sono quelli che il sito dichiara nei `title`: `pg` è
    «partite a **voto**», `rig` è «rigori segnati / tirati» e quindi una frazione,
    che si tiene **com'è** invece di sceglierne una metà.
    """
    p = _RigheGiocatori()
    p.feed(scarica("statistiche", forza))
    fuori = {}
    for r in p.righe:
        c = r["celle"]
        fuori[r["id"]] = {
            "id": r["id"],
            "nome": r["nome"],
            "squadra": (c.get("sq") or "").upper() or None,
            "partite_a_voto": _intero(c.get("pg")),
            "media_voto": _decimale(c.get("mv")),
            "fantamedia": _decimale(c.get("mfv")),
            "gol": _intero(c.get("gol")),
            "gol_subiti": _intero(c.get("gs")),
            "rigori": (c.get("rig") or "").strip() or None,
            "rigori_parati": _intero(c.get("rp")),
            "assist": _intero(c.get("ass")),
            "ammonizioni": _intero(c.get("amm")),
            "espulsioni": _intero(c.get("esp")),
        }
    return fuori


def giocatori(forza=False):
    """Listone e statistiche uniti **per id**. Torna `(voci, problemi)`.

    ⚠️ Il listone comanda: una voce che sta solo nelle statistiche **non entra**, e
    viene detta nei problemi. Le statistiche aggiungono campi, non giocatori.
    """
    q = quotazioni(forza)
    s = statistiche(forza)
    problemi = []
    for pid, voce in s.items():
        if pid not in q:
            problemi.append(f"{voce['nome']} ({pid}) è nelle statistiche ma non nel listone")
    voci = {}
    for pid, voce in q.items():
        unita = dict(voce)
        st = s.get(pid)
        if st:
            unita.update({k: v for k, v in st.items()
                          if k not in ("id", "nome", "squadra")})
            # ⚠️ Un disaccordo sulla squadra fra le due pagine è il sintomo di una
            # lettura sbagliata, non un dettaglio: va detto, non appianato.
            if st.get("squadra") and voce.get("squadra") and st["squadra"] != voce["squadra"]:
                problemi.append(f"{voce['nome']} ({pid}): squadra {voce['squadra']} nel "
                                f"listone e {st['squadra']} nelle statistiche")
        else:
            unita["senza_statistiche"] = True
        voci[pid] = unita
    return voci, problemi
