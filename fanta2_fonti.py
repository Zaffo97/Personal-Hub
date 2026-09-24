"""Le fonti della Fantacalcio 2: **legge e basta**, come `fantacalcio_it.py`.

§4.6 del backlog, 24/09/2026. La Fantacalcio 2 esiste per provare delle fonti che
si possono usare **senza leggere le pagine di fantacalcio.it**, che i suoi termini
vietano (art. 3). Le fonti, e perché sono queste:

- **i due file Excel** di fantacalcio.it — quotazioni e statistiche — che Davide
  **scarica a mano col suo login** e carica nell'hub. Nessun programma li chiede al
  sito: il pulsante «Scarica» è `only-for-logged`, e qui arriva solo il file.
  Confrontati il 24/09/2026 col listone letto dalle pagine: stesso `Id` per tutti i
  597, quotazioni e statistiche identiche. ⚠️ I file **non vanno nel repository**:
  sono contenuti scaricati con un account, e metterli su GitHub vorrebbe dire
  ripubblicarli. Si leggono dalla memoria e non si salvano;
- **football-data.org** per calendario e classifica, un'API con chiave personale e
  un piano gratuito che copre la Serie A. ⚠️ La chiave **non va nel repository**
  (termini, §6.1): si legge da `FOOTBALL_DATA_API_KEY`. E la pagina che mostra i
  dati deve dire «Football data provided by the Football-Data.org API» (§7.1);
- le **probabili formazioni** non hanno una fonte: la Fantacalcio 2 mette un link
  che le apre nel browser di chi guarda (decisione di Davide, strada «a»).

Per leggere gli `.xlsx` basta la libreria standard: un `.xlsx` è uno zip di XML, e
questi due file hanno solo testo e numeri. `openpyxl` non è installato, e per due
tabelle piatte non serve una dipendenza in più.
"""
import io
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone

import requests

# ── Gli Excel ────────────────────────────────────────────────────────────────

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
_M = "{%s}" % _NS["m"]


def _colonna(ref):
    """`"C12"` → 2: l'indice della colonna dal riferimento della cella."""
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def leggi_xlsx(dati):
    """`{nome_foglio: [righe]}` da un `.xlsx`, dati come bytes o file aperto.

    Ogni riga è una lista di stringhe (o `None` per una cella vuota), nell'ordine
    delle colonne. ⚠️ I numeri restano **stringhe**, come il file li scrive: la
    conversione la fa chi sa che cosa sta leggendo, e una cella che non è un numero
    deve saltare fuori lì, non diventare zero qui.
    """
    if isinstance(dati, (bytes, bytearray)):
        dati = io.BytesIO(dati)
    z = zipfile.ZipFile(dati)
    condivise = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
            condivise.append("".join(t.text or "" for t in si.iter(_M + "t")))
    libro = ET.fromstring(z.read("xl/workbook.xml"))
    legami = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    dove = {r.get("Id"): r.get("Target") for r in legami}
    fogli = {}
    for foglio in libro.find("m:sheets", _NS):
        bersaglio = dove[foglio.get("{%s}id" % _NS["r"])].lstrip("/")
        if not bersaglio.startswith("xl/"):
            bersaglio = "xl/" + bersaglio
        righe = []
        for riga in ET.fromstring(z.read(bersaglio)).iter(_M + "row"):
            celle = {}
            for c in riga.findall("m:c", _NS):
                v = c.find("m:v", _NS)
                tipo = c.get("t")
                if tipo == "s" and v is not None:
                    valore = condivise[int(v.text)]
                elif tipo == "inlineStr":
                    valore = "".join(e.text or "" for e in c.iter(_M + "t"))
                else:
                    valore = v.text if v is not None else None
                celle[_colonna(c.get("r"))] = valore
            if celle:
                righe.append([celle.get(i) for i in range(max(celle) + 1)])
        fogli[foglio.get("name")] = righe
    return fogli


def _tabella(righe):
    """Le righe di un foglio come dizionari, dall'intestazione che comincia con `Id`.

    ⚠️ L'intestazione **si cerca**, non si dà per scontata alla seconda riga: sopra
    c'è un titolo («Quotazioni Fantacalcio Stagione 2026 27»), e un file dell'anno
    prossimo con una riga in più di titolo sposterebbe tutto di uno senza errore.
    """
    for i, r in enumerate(righe):
        if r and (r[0] or "").strip() == "Id":
            testa = [(x or "").strip() for x in r]
            fuori = []
            for riga in righe[i + 1:]:
                if not riga or not (riga[0] or "").strip():
                    continue
                fuori.append(dict(zip(testa, [(x.strip() if isinstance(x, str) else x)
                                              for x in riga])))
            return fuori
    return None


def _intero(x):
    try:
        return int(float(str(x).replace(",", ".")))
    except (TypeError, ValueError):
        return None


def _decimale(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def slug_squadra(nome):
    """`"Hellas Verona"` → `"hellas-verona"`: la chiave con cui si incrociano le fonti.

    È la stessa forma degli slug di fantacalcio.it (`atalanta`, `inter`), che il
    24/09/2026 coincidevano con il nome minuscolo su tutte e 20 le squadre.
    """
    testo = unicodedata.normalize("NFKD", nome or "")
    testo = "".join(c for c in testo if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", testo).strip("-") or None


def _mantra(testo):
    """`"M;C"` → `"m|c"`: la forma che il listone della prima sezione usa già."""
    pezzi = [p.strip().lower() for p in (testo or "").split(";") if p.strip()]
    return "|".join(pezzi) or None


def che_file_e(fogli):
    """`"quotazioni"`, `"statistiche"` o `None`, **dal contenuto** e non dal nome.

    Il nome del file lo decide il browser di chi scarica (un secondo download
    diventa `… (1).xlsx`), quindi si guarda l'intestazione: le statistiche hanno
    `Pv` e `Fm`, le quotazioni `Qt.A` e `FVM`.
    """
    for righe in fogli.values():
        tab = _tabella(righe)
        if not tab:
            continue
        chiavi = set(tab[0])
        if {"Qt.A", "Qt.I", "FVM"} <= chiavi:
            return "quotazioni"
        if {"Pv", "Mv", "Fm"} <= chiavi:
            return "statistiche"
    return None


def quotazioni(fogli):
    """`({id: voce}, problemi)` dal file delle quotazioni.

    ⚠️ **Il foglio `Ceduti` conta**: sono i giocatori che hanno lasciato la Serie A
    (63 il 24/09/2026), e il file li tiene **separati** da quelli in rosa. La prima
    sezione non lo sa — la pagina li elenca insieme agli altri, e nel suo listone
    risultano tutti attivi. Qui entrano con `ceduto=1`, cioè spenti ma presenti:
    possono essere nella rosa di qualcuno, e cancellarli porterebbe via quella riga.
    """
    tutti = _tabella(fogli.get("Tutti") or [])
    if tutti is None:
        return {}, ["Nel file delle quotazioni manca il foglio «Tutti» con "
                    "l'intestazione «Id»: non ha la forma che mi aspetto."]
    ceduti = _tabella(fogli.get("Ceduti") or []) or []
    voci, problemi = {}, []
    for riga, ceduto in [(r, 0) for r in tutti] + [(r, 1) for r in ceduti]:
        pid = _intero(riga.get("Id"))
        if pid is None:
            problemi.append(f"Una riga senza un Id leggibile: {riga.get('Nome')!r}")
            continue
        if pid in voci:
            problemi.append(f"{riga.get('Nome')} ({pid}) compare due volte")
            continue
        voci[pid] = {
            "id": pid,
            # ⚠️ `strip()`: nel file del 24/09/2026 un nome ha uno spazio in fondo
            # (`'Fini '`), e due nomi che differiscono per uno spazio non si
            # trovano con una ricerca.
            "nome": (riga.get("Nome") or "").strip(),
            "squadra": (riga.get("Squadra") or "").strip() or None,
            "squadra_slug": slug_squadra(riga.get("Squadra")),
            "ruolo_classic": (riga.get("R") or "").strip().lower() or None,
            "ruolo_mantra": _mantra(riga.get("RM")),
            "qa": _intero(riga.get("Qt.A")),
            "qi": _intero(riga.get("Qt.I")),
            "fvm": _intero(riga.get("FVM")),
            "ceduto": ceduto,
        }
    return voci, problemi


def statistiche(fogli):
    """`({id: voce}, problemi)` dal file delle statistiche.

    I nomi delle colonne sono quelli del file: `Pv` partite a voto, `Mv` media voto,
    `Fm` fantamedia, `Gf`/`Gs` gol fatti e subiti, `Rp` rigori parati, `Rc` rigori
    calciati, `R+`/`R-` segnati e sbagliati, `Ass`, `Amm`, `Esp`, `Au` autogol.
    ⚠️ I rigori si scrivono anche come `"R+ / Rc"`, la frazione della prima sezione:
    è quello che `fantamedia_regole()` sa leggere, e rifarla da capo sarebbe una
    seconda copia della stessa regola.
    """
    tutti = _tabella(fogli.get("Tutti") or [])
    if tutti is None:
        return {}, ["Nel file delle statistiche manca il foglio «Tutti» con "
                    "l'intestazione «Id»: non ha la forma che mi aspetto."]
    voci, problemi = {}, []
    for riga in tutti:
        pid = _intero(riga.get("Id"))
        if pid is None:
            problemi.append(f"Una riga senza un Id leggibile: {riga.get('Nome')!r}")
            continue
        segnati, tirati = _intero(riga.get("R+")), _intero(riga.get("Rc"))
        voci[pid] = {
            "id": pid,
            "nome": (riga.get("Nome") or "").strip(),
            "partite_a_voto": _intero(riga.get("Pv")),
            "media_voto": _decimale(riga.get("Mv")),
            "fantamedia": _decimale(riga.get("Fm")),
            "gol": _intero(riga.get("Gf")),
            "gol_subiti": _intero(riga.get("Gs")),
            "rigori": (f"{segnati} / {tirati}"
                       if segnati is not None and tirati is not None else None),
            "rigori_parati": _intero(riga.get("Rp")),
            "assist": _intero(riga.get("Ass")),
            "ammonizioni": _intero(riga.get("Amm")),
            "espulsioni": _intero(riga.get("Esp")),
            "autogol": _intero(riga.get("Au")),
        }
    return voci, problemi


# ── football-data.org ────────────────────────────────────────────────────────

API = "https://api.football-data.org/v4"
SERIE_A = "SA"
# La frase che i termini (§7.1) chiedono di mostrare dove i dati si vedono.
ATTRIBUZIONE = "Football data provided by the Football-Data.org API"
VARIABILE_CHIAVE = "FOOTBALL_DATA_API_KEY"

# Gli stati di una partita, come li scrive la documentazione (letta il 24/09/2026).
# ⚠️ `SCHEDULED` vuol dire data **approssimativa**: l'ora esatta c'è solo con
# `TIMED`. Il timer si fida solo di quello.
CON_ORA = {"TIMED", "IN_PLAY", "PAUSED", "FINISHED", "AWARDED"}
NON_SI_GIOCA = {"POSTPONED", "CANCELLED", "SUSPENDED"}
DA_GIOCARE = {"SCHEDULED", "TIMED", "IN_PLAY", "PAUSED"}


def chiave_api():
    """La chiave di football-data.org, o `None`. **Non si stampa mai.**

    Si legge dall'ambiente, come `STEAM_API_KEY`. ⚠️ Su Windows c'è un secondo
    posto, ed è voluto: `setx` scrive la variabile **nel registro dell'utente**, ma
    un processo partito prima la vede solo se lo si riavvia da un terminale nuovo —
    è la trappola già scritta in PROJECT_CONTEXT per Steam. Rileggerla dal registro
    toglie la trappola senza metterla in un file del progetto.
    ⚠️ Su Debian il registro non c'è: dove tenerla lì è aperto (§1.5 del backlog).
    """
    valore = (os.environ.get(VARIABILE_CHIAVE) or "").strip()
    if valore:
        return valore
    if sys.platform.startswith("win"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                valore = str(winreg.QueryValueEx(k, VARIABILE_CHIAVE)[0]).strip()
        except OSError:
            valore = ""
    return valore or None


def _get(percorso, chiave):
    risposta = requests.get(API + percorso, headers={"X-Auth-Token": chiave},
                            timeout=20)
    risposta.raise_for_status()
    return risposta.json()


# ⚠️ L'ora italiana. `zoneinfo` su Windows **non trova `Europe/Rome`** senza il
# pacchetto `tzdata` (provato il 24/09/2026: `ZoneInfoNotFoundError`), quindi se
# manca si usa la regola dell'ora legale europea, che è una regola scritta e non una
# stima: dall'ultima domenica di marzo all'ultima di ottobre, alle 01:00 UTC.
try:
    from zoneinfo import ZoneInfo
    _ROMA = ZoneInfo("Europe/Rome")
except Exception:
    _ROMA = None


def _ultima_domenica(anno, mese):
    giorno = datetime(anno, mese + 1, 1) - timedelta(days=1)
    return giorno - timedelta(days=(giorno.weekday() + 1) % 7)


def ora_italiana(utc):
    """`"2026-10-10T13:00:00Z"` → `"2026-10-10 15:00"`, l'ora della Serie A.

    Il formato è quello di `fanta_calendario.inizio`: niente fuso, perché il
    browser che fa il conto alla rovescia sta nello stesso fuso della partita.
    """
    quando = datetime.fromisoformat(utc.replace("Z", "+00:00"))
    if _ROMA is not None:
        return quando.astimezone(_ROMA).strftime("%Y-%m-%d %H:%M")
    inizio = _ultima_domenica(quando.year, 3).replace(hour=1, tzinfo=timezone.utc)
    fine = _ultima_domenica(quando.year, 10).replace(hour=1, tzinfo=timezone.utc)
    scarto = 2 if inizio <= quando < fine else 1
    return (quando + timedelta(hours=scarto)).strftime("%Y-%m-%d %H:%M")


def partite(chiave):
    """Tutte le partite della stagione di Serie A, **una chiamata**. Lista di voci.

    Una chiamata sola e non una per giornata: il piano gratuito ne dà 10 al minuto,
    e 380 partite stanno in una risposta.
    """
    dati = _get(f"/competitions/{SERIE_A}/matches", chiave)
    fuori = []
    for m in dati.get("matches", []):
        fuori.append({
            "match_id": m["id"],
            "giornata": m.get("matchday"),
            "stato": m.get("status"),
            "utc": m.get("utcDate"),
            "inizio": ora_italiana(m["utcDate"]) if m.get("utcDate") else None,
            "casa": (m.get("homeTeam") or {}).get("shortName"),
            "casa_id": (m.get("homeTeam") or {}).get("id"),
            "fuori": (m.get("awayTeam") or {}).get("shortName"),
            "fuori_id": (m.get("awayTeam") or {}).get("id"),
            "gol_casa": ((m.get("score") or {}).get("fullTime") or {}).get("home"),
            "gol_fuori": ((m.get("score") or {}).get("fullTime") or {}).get("away"),
            "aggiornata": m.get("lastUpdated"),
        })
    return fuori


def classifica(chiave):
    """La classifica totale. ⚠️ Solo quella: nel piano gratuito non ci sono le
    classifiche casa/trasferta, e il campo `form` arriva vuoto (provato il
    24/09/2026)."""
    dati = _get(f"/competitions/{SERIE_A}/standings", chiave)
    tabella = next((s["table"] for s in dati.get("standings", [])
                    if s.get("type") == "TOTAL"), [])
    return [{"squadra": t["team"].get("shortName"), "squadra_id": t["team"].get("id"),
             "posizione": t.get("position"), "punti": t.get("points"),
             "giocate": t.get("playedGames"), "gol_fatti": t.get("goalsFor"),
             "gol_subiti": t.get("goalsAgainst")} for t in tabella]


def abbina_squadre(nomi_api, squadre_listone):
    """`({nome_api: slug}, non_abbinate)`: le squadre di football-data sul listone.

    I nomi non sono uguali (`Como 1907` e `Como`, `Venezia FC` e `Venezia`), e un
    abbinamento sbagliato darebbe a un giocatore la partita di un'altra squadra
    senza nessun errore. Quindi la regola è stretta: le parole del nome del listone
    devono stare **tutte** nel nome dell'API, e il candidato dev'essere **uno
    solo**. Due candidati o nessuno → non abbinata, e la pagina lo dice.
    """
    parole = {slug: set(slug.split("-")) for slug in squadre_listone if slug}
    abbinate, sole = {}, []
    for nome in nomi_api:
        mie = set((slug_squadra(nome) or "").split("-"))
        esatte = [s for s, p in parole.items() if p == mie]
        candidati = esatte or [s for s, p in parole.items() if p <= mie]
        if len(candidati) == 1:
            abbinate[nome] = candidati[0]
        else:
            sole.append(nome)
    return abbinate, sole
