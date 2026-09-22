import os
import json
import re
import unicodedata

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Regulation di partenza del sito. Non è una costante scritta a mano: è **la prima**
# di data/regulations.json, cioè lo stesso criterio del fallback `regs[0]` che tutte
# le route usano già quando l'id richiesto non esiste. Per cambiare il default si
# sposta una voce in cima al file, e non si tocca il codice.
REGULATION_DEFAULT_EMERGENZA = "ma"   # se il registro non è leggibile esiste solo questa


def regulation_default():
    """Id della regulation di partenza: la prima del registro."""
    try:
        with open(os.path.join(DATA_DIR, "regulations.json"), encoding="utf-8") as f:
            return json.load(f)[0]["id"]
    except Exception:
        return REGULATION_DEFAULT_EMERGENZA


def _load_roster():
    """Carica roster e mega_map da data/roster_ma.json.
    Se il file non esiste, usa liste vuote come fallback."""
    path = os.path.join(DATA_DIR, "roster_ma.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d.get("pokemon", []), d.get("mega_map", {})
    except Exception as e:
        print(f"[WARN] Impossibile caricare roster_ma.json: {e}")
        return [], {}

REG_MA_ROSTER, POKEMON_TO_MEGA = _load_roster()
MEGA_EVOLUTIONS_MA = sorted(set(m for v in POKEMON_TO_MEGA.values() for m in v))

NATURES = [
    "Hardy","Lonely","Brave","Adamant","Naughty","Bold","Docile","Relaxed","Impish","Lax",
    "Timid","Hasty","Serious","Jolly","Naive","Modest","Mild","Quiet","Bashful","Rash",
    "Calm","Gentle","Sassy","Careful","Quirky",
]

NATURE_EFFECTS = {
    "Lonely":("+Atk","-Def"),"Brave":("+Atk","-Spe"),"Adamant":("+Atk","-SpA"),"Naughty":("+Atk","-SpD"),
    "Bold":("+Def","-Atk"),"Relaxed":("+Def","-Spe"),"Impish":("+Def","-SpA"),"Lax":("+Def","-SpD"),
    "Timid":("+Spe","-Atk"),"Hasty":("+Spe","-Def"),"Jolly":("+Spe","-SpA"),"Naive":("+Spe","-SpD"),
    "Modest":("+SpA","-Atk"),"Mild":("+SpA","-Def"),"Quiet":("+SpA","-Spe"),"Rash":("+SpA","-SpD"),
    "Calm":("+SpD","-Atk"),"Gentle":("+SpD","-Def"),"Sassy":("+SpD","-Spe"),"Careful":("+SpD","-SpA"),
}

PYTHON_TOPICS = {
    "Introduzione":["Python HOME","Python Intro","Python Get Started","Python Syntax","Python Comments","Python Variables","Python Data Types"],
    "Stringhe e I/O":["Python Strings","Python String Methods","Python String Formatting","Python User Input"],
    "Operatori e Controllo":["Python Operators","Python If...Else","Python Match","Python While Loops","Python For Loops"],
    "Strutture Dati":["Python Lists","Python Tuples","Python Sets","Python Dictionaries"],
    "Funzioni e Scope":["Python Functions","Python Lambda","Python Arrays","Python Scope"],
    "OOP":["Python Classes","Python Inheritance","Python Iterators","Python Polymorphism","Python Encapsulation"],
    "Moduli e File":["Python Modules","Python Dates","Python Math","Python JSON","Python RegEx","Python PIP","Python File Open","Python File Write","Python File Delete"],
    "Error Handling":["Python Try...Except","Python Exception Handling","Python User-Defined Exceptions"],
    "Avanzato":["Python Decorators","Python Generators","Python Context Managers","Python Threading","Python Multiprocessing"],
    "Standard Library":["Python os Module","Python sys Module","Python collections","Python itertools","Python functools","Python pathlib","Python argparse"],
}

PC_CATEGORIES    = ["CPU","GPU","Motherboard","RAM","Storage SSD","Storage HDD","PSU","Case","CPU Cooler","Case Fan","Monitor","Tastiera","Mouse","Cuffie","Webcam","Scheda Audio","Altro"]
# Le sezioni su cui si danno i permessi. `slug` è il nome del **blueprint** Flask:
# è così che il controllo in `app.py` sa a quale sezione appartiene una richiesta
# senza dover elencare le route una per una. Il Pokémon ne ha due, perché le API
# stanno in un blueprint separato ma sono la stessa sezione per chi guarda.
# La Dashboard non è qui di proposito: è la pagina di arrivo dopo il login e la
# vedono tutti, altrimenti chi entra si troverebbe davanti un errore.
SEZIONI = [
    ("gaming",     "🎮 Gaming",         "/gaming",    ["gaming"]),
    ("pokemon",    "🐉 Pokémon VGC",    "/pokemon",   ["pokemon", "api_pokemon"]),
    ("arduino",    "🔌 Arduino",        "/arduino",   ["arduino"]),
    ("python",     "🐍 Python Tracker", "/python",    ["python_tracker"]),
    ("pcbuilder",  "🖥️ PC Builder",     "/pcbuilder", ["pcbuilder"]),
    ("fantacalcio", "⚽ Fantacalcio",    "/fantacalcio", ["fantacalcio"]),
]
SEZIONI_SLUG = [s[0] for s in SEZIONI]
# blueprint -> sezione, ricavata da SEZIONI così le due non possono divergere
BLUEPRINT_SEZIONE = {bp: slug for slug, _, _, bps in SEZIONI for bp in bps}

# ── Fantacalcio ──────────────────────────────────────────────────────────────
# ⚠️ La **chiave** è il dato: è quello che fantacalcio.it scrive in
# `data-filter-role-classic` e che finisce in `fanta_players.ruolo_classic`. Non si
# traduce e non si rinomina; l'etichetta qui sotto è solo per lo schermo.
RUOLI_FANTA = {"p": "Portiere", "d": "Difensore", "c": "Centrocampista",
               "a": "Attaccante"}
# L'ordine in cui una rosa si legge, che non è quello alfabetico delle chiavi.
ORDINE_RUOLI_FANTA = ["p", "d", "c", "a"]

# Quanti giocatori per ruolo ha un modulo. La chiave è il modulo come lo scrive
# l'utente ("3-4-3"), e il portiere è sempre uno: un modulo dice i dieci di
# movimento. ⚠️ Non è un elenco di moduli **ammessi** — quello lo decide la lega,
# nella sua colonna `moduli` — è la traduzione da modulo a conto per ruolo.
def scomponi_modulo(modulo):
    """`{"p":1,"d":3,"c":4,"a":3}` da "3-4-3", o `None` se non è un modulo.

    ⚠️ Torna `None` invece di indovinare: un modulo scritto male deve fermare la
    validazione, non farla passare con un conto sbagliato.
    """
    pezzi = [p.strip() for p in str(modulo or "").split("-")]
    if len(pezzi) != 3 or not all(p.isdigit() for p in pezzi):
        return None
    d, c, a = (int(p) for p in pezzi)
    if d + c + a != 10:
        return None
    return {"p": 1, "d": d, "c": c, "a": a}


def nome_ruolo(ruolo, quanti=1):
    """«portiere» / «portieri». I quattro nomi vanno tutti al plurale in `-i`."""
    nome = RUOLI_FANTA.get(ruolo, ruolo or "?").lower()
    return nome if quanti == 1 else nome[:-1] + "i"


def controlla_formazione(modulo, titolari, panchinari, rosa, n_panchinari=None):
    """Cosa non va in una formazione. Lista di frasi, **vuota** se è a posto.

    `titolari` e `panchinari` sono liste di `player_id` **in ordine**; `rosa` è
    `{player_id: ruolo}` di chi è in quella rosa — il ruolo arriva da lì e non da
    quello che manda il form, che è la solita differenza fra un dato e un'opinione
    del browser.

    Davide ha scelto la validazione **severa** (21/09/2026): una formazione che
    non torna non si salva, come già succede a un modulo scritto male. Quindi
    questa funzione non decide niente da sé — elenca — ma chi la chiama si ferma
    se torna qualcosa.

    ⚠️ I controlli sono in quest'ordine di proposito: prima quelli che rendono
    tutti gli altri senza senso (modulo illeggibile, giocatori non in rosa,
    doppioni), poi i conti dei reparti. Dire «ti manca un difensore» quando il
    problema è che il modulo non esiste manda a cercare la cosa sbagliata.
    """
    guai = []
    serve = scomponi_modulo(modulo)
    if not serve:
        return [f"«{modulo or '—'}» non è un modulo: i dieci di movimento devono "
                "fare 10."]

    tutti = list(titolari) + list(panchinari)
    fuori_rosa = [p for p in tutti if p not in rosa]
    if fuori_rosa:
        guai.append(f"{len(fuori_rosa)} giocatore non è in questa rosa."
                    if len(fuori_rosa) == 1 else
                    f"{len(fuori_rosa)} giocatori non sono in questa rosa.")
    visti, doppi = set(), []
    for p in tutti:
        if p in visti:
            doppi.append(p)
        visti.add(p)
    if doppi:
        guai.append("Un giocatore è schierato due volte."
                    if len(doppi) == 1 else
                    f"{len(doppi)} giocatori sono schierati due volte.")
    if guai:
        return guai

    if len(titolari) != 11:
        guai.append(f"I titolari sono {len(titolari)}, devono essere 11.")
    per_ruolo = {}
    for p in titolari:
        r = rosa.get(p)
        per_ruolo[r] = per_ruolo.get(r, 0) + 1
    for ruolo in ORDINE_RUOLI_FANTA:
        ha, vuole = per_ruolo.get(ruolo, 0), serve[ruolo]
        if ha != vuole:
            guai.append(f"Hai {ha} {nome_ruolo(ruolo, ha)} in campo, il {modulo} "
                        f"ne vuole {vuole}.")
    if n_panchinari is not None and len(panchinari) > n_panchinari:
        guai.append(f"In panchina ce ne sono {len(panchinari)}, questa lega ne "
                    f"ammette {n_panchinari}.")
    return guai


def controlla_schierati(schierati, probabili, nomi=None, in_rosa=None):
    """Cosa **non torna più** fra la formazione salvata e le probabili di adesso.

    Torna quattro elenchi, e nessuno dei quattro è un errore: sono cose da sapere
    prima che la giornata cominci.

    - `fuori`: schierato titolare, ma le probabili non lo danno più in campo —
      panchina, non convocato, o la sua squadra non gioca affatto. È il caso per
      cui questa funzione esiste;
    - `incerti`: schierato titolare, dato titolare, ma con una percentuale sotto
      `SOGLIA_SCHIERABILE` — cioè un titolare che la fonte stessa metterebbe in
      dubbio;
    - `occasioni`: il rovescio, e serve a decidere **chi** mettere al posto di chi
      è nei primi due: uno che hai in panchina e che le probabili danno titolare;
    - `spariti`: schierato, ma **non più in rosa**. ⚠️ Dal 22/09/2026 togliere un
      giocatore dalla rosa lo toglie anche dal campo (`_scendi_dal_campo()`),
      quindi questo elenco dovrebbe restare vuoto: resta la **rete**, perché una
      formazione scritta prima di quella correzione può avere righe orfane e il
      campo smette di disegnarle senza dire niente — una formazione da 11 che
      diventa da 10 in silenzio.

    ⚠️ **Chi non ha una riga nelle probabili non viene dichiarato.** «Non lo
    sappiamo» non è «non gioca»: con l'archivio vuoto, o prima che la giornata sia
    pubblicata, questa funzione deve tornare quattro elenchi vuoti invece di
    accusare undici giocatori.

    ⚠️ E il confronto è sempre con **l'ultima giornata importata**, perché la
    formazione non ha una giornata sua: è la conseguenza della scelta «una
    formazione per lega, che si sovrascrive» (Davide, 21/09/2026). Chi la legge
    deve dire **quale** giornata sta guardando, o l'avviso non è verificabile.
    """
    nomi = nomi or {}
    fuori, incerti, occasioni, spariti = [], [], [], []
    for pid, riga in (schierati or {}).items():
        titolare = bool(riga.get("titolare")) if hasattr(riga, "get") else bool(riga)
        voce = {"id": pid, "nome": nomi.get(pid, "?"), "titolare": titolare,
                "stato": None, "percentuale": None}
        if in_rosa is not None and pid not in in_rosa:
            spariti.append(voce)
            continue
        p = (probabili or {}).get(pid)
        if not p:
            continue
        voce["stato"] = p.get("stato")
        voce["percentuale"] = p.get("percentuale")
        if titolare:
            if p.get("stato") != "titolare":
                fuori.append(voce)
            elif (p.get("percentuale") or 0) < SOGLIA_SCHIERABILE:
                incerti.append(voce)
        elif p.get("stato") == "titolare":
            occasioni.append(voce)
    # I «fuori» in ordine di gravità: chi non scende in campo per niente prima di
    # chi è solo in panchina. Un elenco alfabetico metterebbe in cima il caso meno
    # urgente, e il primo nome è quello che viene letto.
    peso = {"non_gioca": 0, "fuori": 1, "panchina": 2}
    fuori.sort(key=lambda v: (peso.get(v["stato"], 3), -(v["percentuale"] or 0),
                              v["nome"]))
    incerti.sort(key=lambda v: (v["percentuale"] or 0, v["nome"]))
    occasioni.sort(key=lambda v: (-(v["percentuale"] or 0), v["nome"]))
    spariti.sort(key=lambda v: v["nome"])
    return {"fuori": fuori, "incerti": incerti, "occasioni": occasioni,
            "spariti": spariti}


def quanti_guai(allerta):
    """Quante cose da guardare ci sono, **senza** le occasioni: quelle non sono un
    guaio, sono un suggerimento, e contarle farebbe dire «3 problemi» a una
    formazione che non ne ha nessuno."""
    if not allerta:
        return 0
    return sum(len(allerta.get(k, ())) for k in ("fuori", "incerti", "spariti"))


# ── Il modificatore di difesa ────────────────────────────────────────────────
# Due cose distinte, e le fonti le trattano diverse:
#
# **La struttura** viene dalla guida ufficiale di Leghe Fantacalcio, letta il
# 21/09/2026: la media è aritmetica sui voti del **portiere e dei migliori 3
# difensori** (o dei **migliori 4 difensori** se il portiere non viene incluso),
# **esclusi bonus e malus**, e il modificatore si applica solo se almeno **4
# difensori** portano voto. La guida dice anche, per esteso, che la struttura non
# si cambia: «puoi solo cambiare i valori nelle apposite caselle».
#
# **I valori** invece sono personalizzabili, e quelli qui sotto sono quelli
# storici di FantaGazzetta (vademecum del 30/08/2026 letto sul sito): +6 da 7 in
# su, +3 da 6.5, +1 da 6. Sotto il 6 non c'è bonus.
#
# ⚠️ Per questo stanno in una colonna della lega e non nel codice: sono il default,
# non la legge. Una lega che usa altri numeri li scrive nel suo regolamento.
MOD_DIFESA_SOGLIE = [(7.0, 6.0), (6.5, 3.0), (6.0, 1.0)]

# La seconda tabella che si usa davvero, chiesta da Davide il 22/09/2026: quella a
# **quarti di voto**, sei fasce invece di tre.
#
# ⚠️ **Da dove viene, e cosa non dice nessuno.** Il regolamento pubblico di
# fantacalcio.it (`/regolamenti/leghe-private`, §10.1, riletto il 22/09/2026) **non
# pubblica nessun valore**: dice che la piattaforma «vi propone la versione più
# diffusa per ogni reparto di gioco con possibilità di personalizzare l'output di
# bonus/malus, ma non la struttura logica», e la tabella vera sta dentro il pannello
# della lega, che vuole un account. I numeri qui sotto vengono quindi da
# **fantacalcio-online.com** (guida al modificatore di difesa), la stessa fonte
# secondaria da cui il progetto ha preso le fasce di titolarità il 21/09: 6,00 → +1,
# 6,01-6,25 → +2, 6,26-6,50 → +3, 6,51-6,75 → +4, 6,76-7,00 → +5, 7,01+ → +6.
#
# ⚠️ **La traduzione da «fasce chiuse» a «soglie» è esatta, non approssimata.** La
# fonte scrive gli intervalli con l'estremo alto incluso (`6,26-6,50`), qui le
# soglie sono «da X in su»: `6.26` come soglia produce la stessa identica fascia,
# perché i voti hanno due decimali e fra 6,25 e 6,26 non c'è niente. Una media di
# **6,25 prende +2** con tutte e due le letture — è il caso che Davide ha citato.
MOD_DIFESA_SOGLIE_QUARTI = [(7.01, 6.0), (6.76, 5.0), (6.51, 4.0),
                            (6.26, 3.0), (6.01, 2.0), (6.0, 1.0)]


def fasce_mod_difesa(soglie=None):
    """Le soglie lette **come intervalli**: `[{"da", "a", "punti"}, …]`.

    `a` è `None` sulla fascia più alta, che non ha un tetto. Serve solo a
    **mostrarle**: «da 6,26 a 6,50 → +3» è come le scrivono le piattaforme e come
    le ha scritte Davide chiedendole, mentre «da 6,26 → +3» costringe a leggere la
    riga dopo per sapere dove finisce. Il conto resta quello di
    `modificatore_difesa()`, che confronta con «maggiore o uguale».

    ⚠️ Il tetto è la soglia di sopra **meno un centesimo**, e i due decimali non
    sono una scelta estetica: i voti si danno a mezzi punti e le medie che escono
    hanno due decimali, quindi fra 6,25 e 6,26 non esiste nessuna media possibile.
    """
    ordinate = sorted(soglie or MOD_DIFESA_SOGLIE, key=lambda x: x[0], reverse=True)
    fuori = []
    for n, (media, punti) in enumerate(ordinate):
        sopra = ordinate[n - 1][0] if n else None
        fuori.append({"da": media, "punti": punti,
                      "a": None if sopra is None else round(sopra - 0.01, 2)})
    return fuori


_COPPIA = re.compile(r"(\d+(?:[.,]\d+)?)\s*:\s*(-?\d+(?:[.,]\d+)?)")


def soglie_mod_difesa(grezzo=None):
    """Le soglie di una lega, da `"7:6, 6.5:3, 6:1"`, o quelle standard.

    ⚠️ Le coppie si **cercano**, non si spezzano sulla virgola, e il motivo l'ha
    trovato la prova al primo giro: in italiano la virgola è anche il separatore
    decimale, quindi `"7,5:8, 6:2"` spezzato sulle virgole dà `7` e `5:8`, cioè
    una tabella diversa da quella scritta, **senza nessun errore**. Cercando le
    coppie `media:punti` l'ambiguità non si pone.

    ⚠️ E una riga scritta male non diventa una tabella **a metà**: se dopo aver
    tolto le coppie riconosciute resta qualcosa che non è un separatore, si torna
    allo standard — meglio un default dichiarato che tre righe su quattro.

    Le soglie tornano sempre **ordinate dalla più alta**, perché il conto si ferma
    alla prima che la media raggiunge: l'ordine è parte del significato.
    """
    testo = str(grezzo or "").strip()
    if not testo:
        return list(MOD_DIFESA_SOGLIE)
    fuori = []
    for media, punti in _COPPIA.findall(testo):
        fuori.append((float(media.replace(",", ".")), float(punti.replace(",", "."))))
    resto = _COPPIA.sub("", testo)
    if not fuori or resto.strip(" ,;\t\n"):
        return list(MOD_DIFESA_SOGLIE)
    return sorted(fuori, key=lambda x: x[0], reverse=True)


def scrivi_soglie(soglie):
    """L'inverso di `soglie_mod_difesa()`: la riga da salvare in colonna."""
    def num(x):
        return str(int(x)) if float(x) == int(x) else str(x)
    return ", ".join(f"{num(m)}:{num(p)}" for m, p in soglie)


def modificatore_difesa(media, soglie=None):
    """I punti che la tabella dà a quella media, o `0`.

    ⚠️ `None` vuol dire «non lo sappiamo» e torna `0`: un voto che non c'è non è
    un voto basso. E il confronto è **maggiore o uguale**, come lo scrive la fonte:
    con la tabella standard una media di esattamente 6 vale +1, non 0.
    """
    if media is None:
        return 0.0
    for minimo, punti in (soglie or MOD_DIFESA_SOGLIE):
        if media >= minimo:
            return punti
    return 0.0


# ── Il consiglio ─────────────────────────────────────────────────────────────
# ⚠️ **Il criterio non l'ho scelto io.** Davide, il 21/09/2026, alla domanda «quanto
# pesa la percentuale di titolarità contro la fantamedia» ha risposto: *quello che
# consigliano di più sulla piattaforma o altre fonti affidabili*. Quindi prima si è
# letto. Cosa si è trovato, quel giorno:
#
#   * **nessuna fonte pubblica una formula.** Il «Comparatore» di fantacalcio.it
#     («Scegli due calciatori da confrontare, ti diremo quale dei due potrebbe
#     rendere al meglio nel prossimo turno») confronta partite a voto, media voto,
#     fantamedia, gol, assist e gol subiti, **senza dichiarare come li combina**, ed
#     è premium; la pagina dell'algoritmo delle quotazioni dice per esteso di non
#     rivelare coefficienti; il FantaIndex è «un numero da 0 a 100» da «sette
#     macroaree» e basta. Un peso α «preso dalla fonte» non esiste: non c'era da
#     copiare, e inventarlo era la cosa da non fare;
#   * quello che le fonti **dichiarano davvero** è una **gerarchia con delle
#     soglie**. L'*Indice di Titolarità* di fantacalcio.it è «lo strumento
#     imprescindibile per poter schierare al meglio la propria fanta-squadra», su
#     scala 0–100; e le fasce, con il loro significato, le scrive
#     `fantacalcio-online.com`: **≥90** «titolare, nessun dubbio», **60–89**
#     «favorito in un ballottaggio», **40–59** «ballottaggio effettivo: è qui che si
#     decide una giornata», **<40** «parte dalla panchina». La stessa pagina dice
#     che titolarità e merito sono **due domande diverse** — «*se* gioca» e «*se
#     conviene* schierarlo» — e che si rispondono **in quest'ordine**;
#   * e dà una regola operativa, che qui si può eseguire perché la panchina è una
#     lista ordinata: sui ballottaggi, «schierare chi ha la percentuale più alta e
#     collocare l'altro **in cima alla panchina**», così la sostituzione automatica
#     lo fa subentrare.
#
# Da qui la struttura, che è una **porta e un ordinamento**, non una media pesata:
# la percentuale decide **chi può giocare** (soglia dichiarata), la fantamedia
# ricalcolata con le regole della lega decide **chi conviene** fra quelli che
# giocano. I «punti attesi» (`percentuale × fantamedia`) restano una **colonna**
# — sono la forma scritta di quello che le fonti dicono a parole, «a parità di
# fantamedia chi gioca il 90% vale più di chi gioca il 50%» — e servono a sommare
# un modulo intero, non a ordinare i giocatori.

# Le fasce, così come le dichiara la fonte. ⚠️ Sulla scala vera i 90 sono il
# **massimo osservato**, non un minimo raggiungibile da pochi: misurato sulla
# giornata 6 del 2026-27, i 482 convocati stanno in 134 a quota 90 (tutti e 134
# titolari nel campo disegnato), 145 fra 60 e 89 (di cui 86 titolari), 87 fra 40 e
# 59 e 116 sotto il 40 — e in quelle due fasce basse i titolari sono **zero**. La
# soglia del 40 quindi non è un numero scelto: è dove la fonte stessa smette di
# mettere gente in campo.
FASCE_TITOLARITA = [
    (90, "sicuro", "titolare, nessun dubbio"),
    (60, "favorito", "favorito in un ballottaggio"),
    (40, "ballottaggio", "ballottaggio effettivo"),
    (0, "panchina", "parte dalla panchina"),
]
# Sotto questa percentuale un giocatore **non entra** nell'undici consigliato, a
# meno che il suo reparto non si riesca a riempire altrimenti. È la fascia che la
# fonte chiama «parte dalla panchina».
SOGLIA_SCHIERABILE = 40

# ⚠️ Quante partite a voto servono perché la fantamedia voglia dire qualcosa. **5**
# non è scelto a occhio: è la soglia che fantacalcio.it dichiara per il **proprio**
# algoritmo delle quotazioni, dove la fantamedia «viene considerata dal quinto match
# in poi». Il 21/09/2026, alla giornata 6, questo vuol dire che su 597 giocatori
# attivi solo **151** hanno una fantamedia che la fonte stessa si fiderebbe di
# usare, e **183 non hanno nemmeno una partita a voto**. Non è un dettaglio da
# nascondere nel codice: è il motivo per cui a settembre il consiglio si regge più
# sulla titolarità che sul merito, e la pagina lo dice.
MINIMO_PARTITE_FIDATO = 5

# Le voci con cui si ricostruisce la fantamedia: (colonna delle statistiche,
# colonna della regola nella lega). ⚠️ **Porta inviolata e autogol non ci sono**, e
# non per dimenticanza: la fonte non pubblica né i clean sheet né gli autogol, e
# stimarli sarebbe il valore plausibile e falso della regola #3. Le due colonne
# della lega esistono, e restano inutilizzate **dichiaratamente**.
VOCI_FANTAMEDIA = [
    ("gol", "bonus_gol", "gol"),
    ("assist", "bonus_assist", "assist"),
    ("ammonizioni", "malus_amm", "ammonizioni"),
    ("espulsioni", "malus_esp", "espulsioni"),
    ("gol_subiti", "malus_gol_subito", "gol subiti"),
    ("rigori_parati", "bonus_rigore_parato", "rigori parati"),
    ("rigori_sbagliati", "malus_rigore_sbagliato", "rigori sbagliati"),
]


def rigori_segnati_tirati(testo):
    """`"1 / 2"` → `(1, 2)`. La fonte scrive i rigori come frazione, non come numero.

    ⚠️ Si tiene **com'è** invece di sceglierne una metà: i segnati sono già dentro
    `gol` (il regolamento dà +3 «rigori compresi», e la misura del 21/09/2026 lo
    conferma — contarli due volte avrebbe sfasato tutti i rigoristi), quello che
    serve è la **differenza**, cioè i rigori sbagliati.
    """
    pezzi = re.findall(r"\d+", str(testo or ""))
    if len(pezzi) < 2:
        return (int(pezzi[0]) if pezzi else 0), (int(pezzi[0]) if pezzi else 0)
    return int(pezzi[0]), int(pezzi[1])


def fascia_titolarita(percentuale):
    """La chiave della fascia (`sicuro`, `favorito`, `ballottaggio`, `panchina`).

    `None` quando la percentuale non c'è: un giocatore senza probabile **non ha
    fascia**, e dargli la più bassa vorrebbe dire dire una cosa che non si sa.
    """
    if percentuale is None:
        return None
    for minimo, chiave, _ in FASCE_TITOLARITA:
        if percentuale >= minimo:
            return chiave
    return "panchina"


def etichetta_fascia(chiave):
    """Come la fonte chiama quella fascia, parola per parola."""
    for _, k, testo in FASCE_TITOLARITA:
        if k == chiave:
            return testo
    return "—"


def fantamedia_regole(giocatore, regole):
    """La fantamedia **rifatta con le regole di questa lega**. `(valore, pezzi)`.

    Decisione di Davide del 21/09/2026: non la colonna `fantamedia` del sito, che è
    calcolata coi bonus standard di FantaGazzetta, ma il conto rifatto dai dati
    grezzi con le colonne della lega — se una lega dà +1 all'assist e l'altra +3, il
    consiglio deve cambiare, ed è tutto il motivo per cui le regole stanno in
    colonne.

    Torna `(None, [])` quando non c'è **nessuna partita a voto**: una media su zero
    partite non è zero, è assente, e trattarla come zero metterebbe in fondo
    all'elenco un acquisto appena arrivato come se avesse giocato male.

    ⚠️ **Che il conto sia giusto è misurato, non dedotto.** Il 21/09/2026, eseguito
    coi valori **standard** e confrontato con la colonna del sito: **407 giocatori
    su 414** tornano esatti entro 0.01 — tutti e 26 i portieri e tutti e 75 gli
    attaccanti. È la prova che le voci sono contate nel modo giusto (se `gol` non
    comprendesse i rigori, gli attaccanti sarebbero sfasati in blocco) e che la
    **porta inviolata non è dentro la fantamedia del sito**, altrimenti i 26
    portieri sarebbero tutti fuori.

    ⚠️ E i **7 che non tornano** hanno un nome: sei sono il **tetto dei cartellini**
    — ammonizione più espulsione nella stessa partita si fermano a −1, mentre qui si
    sommano a −1,5, perché dai totali di stagione non si sa *in quale* partita sono
    capitati. Lo scarto misurato è ≤ 0.5 e riguarda 6 giocatori su 414: si dichiara,
    non si stima. Il settimo (Halhal) resta senza spiegazione e sta scritto qui.
    """
    partite = giocatore.get("partite_a_voto") or 0
    if not partite:
        return None, []
    segnati, tirati = rigori_segnati_tirati(giocatore.get("rigori"))
    conteggi = dict(giocatore)
    conteggi["rigori_sbagliati"] = max(0, tirati - segnati)
    pezzi, totale = [], 0.0
    for colonna, regola, etichetta in VOCI_FANTAMEDIA:
        quanti = conteggi.get(colonna) or 0
        valore = regole.get(regola)
        if not quanti or valore in (None, 0):
            continue
        punti = quanti * float(valore)
        totale += punti
        pezzi.append({"voce": etichetta, "quanti": quanti,
                      "valore": float(valore), "punti": punti})
    return (giocatore.get("media_voto") or 0) + totale / partite, pezzi


def valuta_rosa(rosa, probabili, regole):
    """Una riga per giocatore, coi numeri su cui il consiglio decide.

    `rosa` sono le righe della rosa (col listone dentro), `probabili` è
    `{player_id: {stato, percentuale, …}}` come lo costruisce la pagina della lega,
    `regole` è la riga della lega. Per ognuno:

    - `stato` e `percentuale` dalle probabili, `fascia` dalla soglia della fonte;
    - `fm` dalla fantamedia rifatta con le regole, `fidata` se le partite a voto
      arrivano a `MINIMO_PARTITE_FIDATO`;
    - `schierabile`, che è la **porta**: convocato e percentuale sopra la soglia;
    - `atteso`, i punti attesi (`percentuale × fm`), che è una colonna e non
      l'ordinamento.
    """
    fuori = []
    for g in rosa:
        p = probabili.get(g["id"]) or {}
        stato = p.get("stato")
        percentuale = p.get("percentuale")
        fm, pezzi = fantamedia_regole(g, regole)
        convocato = stato in ("titolare", "panchina")
        fuori.append({
            "g": g, "stato": stato, "percentuale": percentuale,
            "fascia": fascia_titolarita(percentuale),
            "fm": fm, "pezzi": pezzi,
            "partite": g.get("partite_a_voto") or 0,
            "fidata": (g.get("partite_a_voto") or 0) >= MINIMO_PARTITE_FIDATO,
            "convocato": convocato,
            "schierabile": bool(convocato and (percentuale or 0) >= SOGLIA_SCHIERABILE),
            "atteso": (None if fm is None or not percentuale
                       else round(percentuale / 100.0 * fm, 2)),
        })
    return fuori


ORDINE_FASCE = {chiave: n for n, (_, chiave, _) in enumerate(FASCE_TITOLARITA)}


def _chiave_merito(v):
    """L'ordine **dentro** un reparto: prima *se* gioca, poi *se conviene*.

    ⚠️ La chiave è **la fascia prima della fantamedia**, ed è la parte che si
    sbaglia facilmente. Il primo giro ordinava per fantamedia fra tutti quelli sopra
    la soglia del 40%, e il risultato su una rosa vera si è visto subito:
    **Calhanoglu al 50% («ballottaggio effettivo») veniva schierato davanti a
    Zaccagni al 90% («titolare, nessun dubbio»)** perché aveva 8.5 di fantamedia
    contro meno. Cioè il merito scavalcava la titolarità, che è esattamente quello
    che la gerarchia della fonte esiste per impedire: un 50% **non è** un giocatore
    di cui si sa che gioca, è la moneta che «decide una giornata».
    Quindi: fascia (sicuro → favorito → ballottaggio → panchina), e **dentro** la
    fascia la fantamedia della lega. La percentuale esatta resta l'ultimo spareggio,
    per non lasciare decidere all'ordine alfabetico fra due pari.

    ⚠️ Questa è una **scelta di lettura**, non un dato: la fonte dichiara le quattro
    fasce e l'ordine delle due domande, non quanto una fascia valga in fantamedia.
    Si è preso il verso prudente — mai una moneta al posto di un titolare — e la
    pagina dichiara **dove le due letture litigano** (`contesi` in
    `consiglia_formazione()`), invece di nascondere che esiste un'altra risposta.
    """
    return (not v["convocato"],
            ORDINE_FASCE.get(v["fascia"], 9),
            -(v["fm"] if v["fm"] is not None else -99),
            -(v["percentuale"] or 0),
            v["g"].get("nome") or "")


def rosa_per_merito(valutazioni):
    """Le valutazioni per ruolo, ognuna **nell'ordine in cui il consiglio sceglie**.

    La usano il motore e la pagina: la graduatoria che si legge a schermo deve
    essere la stessa che ha deciso l'undici, altrimenti il consiglio sembrerebbe
    saltare qualcuno senza motivo.
    """
    return {r: sorted([v for v in valutazioni if v["g"].get("ruolo_classic") == r],
                      key=_chiave_merito) for r in ORDINE_RUOLI_FANTA}


# Quanti difensori devono portare voto perché il modificatore si applichi. Non è
# una scelta: lo scrive la guida ufficiale di Leghe Fantacalcio, ed è la ragione per
# cui il modificatore **dipende dal modulo** — un tre-difensori non ci arriva se non
# entra un quarto difensore dalla panchina.
MINIMO_DIFENSORI_MOD = 4


def modificatore_atteso(titolari, regole):
    """Quanto vale il modificatore di difesa per **questo** undici. `None` se la
    lega non lo usa.

    Il consiglio ordinava i moduli sui soli punti attesi dei giocatori, e il
    modificatore vale su un **reparto**: in una lega che lo usa, un 5-3-2 e un
    3-4-3 non sono confrontabili senza. Aggiunto il 22/09/2026 su richiesta di
    Davide.

    Come si conta, e ogni pezzo è dichiarato perché nessuno di questi numeri è
    un dato:

    - il **voto atteso** di un difensore è la sua `media_voto` del listone, che è
      il voto **senza bonus e malus** — esattamente quello che il regolamento vuole
      nella media. Non la fantamedia, che i bonus li contiene;
    - la media è del **portiere e dei migliori 3 difensori**, o dei **migliori 4
      difensori** se la lega esclude il portiere (`mod_difesa_portiere`), come dice
      la guida ufficiale;
    - ⚠️ servono `MINIMO_DIFENSORI_MOD` difensori **a voto**: con un modulo a tre
      difensori il modificatore **non si applica**, a meno che un quarto non
      subentri. Qui si risponde di no, e si dice perché: fingere che si applichi
      renderebbe il 3-4-3 migliore di quello che è;
    - ⚠️ e il numero che esce **non è i punti della tabella**: sono quelli
      **moltiplicati per la probabilità che quei quattro giochino davvero**, cioè
      il prodotto delle loro percentuali di titolarità. Senza, un reparto di
      ballottaggi al 45% varrebbe come uno di titolari al 95%, e in una lega col
      modificatore acceso il consiglio sceglierebbe sempre il modulo con più
      difensori. La pagina mostra **tutti e due** i numeri, perché sono due cose
      diverse: quanto vale se giocano, e quanto ci si può aspettare.
    """
    if not regole or not (regole.get("mod_difesa") if hasattr(regole, "get")
                          else regole["mod_difesa"]):
        return None
    soglie = soglie_mod_difesa(regole.get("mod_difesa_soglie"))
    col_portiere = (regole.get("mod_difesa_portiere") or 0) != 0
    voto = lambda v: v["g"].get("media_voto")
    dif = sorted([v for v in titolari
                  if v["g"].get("ruolo_classic") == "d" and voto(v) is not None],
                 key=voto, reverse=True)
    por = [v for v in titolari
           if v["g"].get("ruolo_classic") == "p" and voto(v) is not None]
    vuoto = {"punti": 0.0, "pieni": 0.0, "media": None, "chi": [],
             "probabilita": None, "col_portiere": col_portiere}
    if len(dif) < MINIMO_DIFENSORI_MOD:
        quanti = len([v for v in titolari if v["g"].get("ruolo_classic") == "d"])
        return dict(vuoto, perche=(
            f"il modulo schiera {quanti} difensori e ne servono "
            f"{MINIMO_DIFENSORI_MOD} a voto" if quanti < MINIMO_DIFENSORI_MOD else
            f"solo {len(dif)} dei {quanti} difensori hanno una media voto"))
    if col_portiere and not por:
        return dict(vuoto, perche="il portiere non ha una media voto")

    chi = ([por[0]] + dif[:3]) if col_portiere else dif[:4]
    media = round(sum(voto(v) for v in chi) / len(chi), 2)
    pieni = modificatore_difesa(media, soglie)
    # La probabilità che il reparto porti voto: le percentuali sono indipendenti
    # quanto basta, e una che manca vale «non lo sappiamo» — cioè zero, non uno.
    probabilita = 1.0
    for v in chi:
        probabilita *= (v.get("percentuale") or 0) / 100.0
    return {"punti": round(pieni * probabilita, 2), "pieni": pieni, "media": media,
            "chi": chi, "probabilita": round(probabilita, 3),
            "col_portiere": col_portiere, "perche": None}


def consiglia_formazione(valutazioni, modulo, n_panchinari=7, regole=None):
    """L'undici e la panchina consigliati per **un** modulo.

    Torna `{"modulo", "titolari", "panchina", "atteso", "senza_fm", "forzati",
    "ballottaggi"}`, dove `titolari` e `panchina` sono liste di valutazioni **in
    ordine**.

    - i titolari sono i migliori del reparto secondo `_chiave_merito()`;
    - ⚠️ `forzati` sono i posti riempiti con chi la porta escluderebbe, perché il
      reparto non si riempiva altrimenti. Non è un caso di scuola: con tre portieri
      di cui nessuno convocato, un portiere lo devi schierare comunque. La pagina lo
      dichiara invece di far finta che sia un consiglio;
    - la **panchina** segue la regola operativa della fonte: prima i **rivali dei
      ballottaggi schierati** — chi è in campo con una percentuale da ballottaggio
      lascia il primo posto in panchina a un altro del suo ruolo, così la
      sostituzione automatica lo fa subentrare — poi il resto per merito.
    """
    serve = scomponi_modulo(modulo)
    if not serve:
        return None
    per_ruolo = rosa_per_merito(valutazioni)
    titolari, forzati, ballottaggi, avanzi = [], [], [], []
    for ruolo in ORDINE_RUOLI_FANTA:
        elenco = per_ruolo[ruolo]
        presi = elenco[:serve[ruolo]]
        titolari += presi
        avanzi += elenco[serve[ruolo]:]
        forzati += [v for v in presi if not v["schierabile"]]
        ballottaggi += [v for v in presi if v["fascia"] == "ballottaggio"]

    # I rivali: per ogni ballottaggio schierato, il primo del suo ruolo che è
    # rimasto fuori. ⚠️ Uno per volta e senza ripetere — due ballottaggi nello
    # stesso reparto non possono contare sullo stesso sostituto.
    panchina, usati = [], set()
    for v in ballottaggi:
        for altro in avanzi:
            if (altro["g"]["id"] not in usati
                    and altro["g"].get("ruolo_classic") == v["g"].get("ruolo_classic")):
                panchina.append(altro)
                usati.add(altro["g"]["id"])
                break
    # ⚠️ **Il tetto per ruolo, che non è una preferenza: è aritmetica.** Con un
    # portiere in campo si può avere bisogno di **un** sostituto portiere, mai di
    # due — il secondo occuperebbe un posto di panchina che non potrà mai servire.
    # Il primo giro non ce l'aveva, e su una rosa vera si è visto: **due portieri di
    # riserva stavano al quarto e quinto posto**, davanti al miglior attaccante
    # della rosa. Il tetto è quindi «quanti ne gioco», ruolo per ruolo, e quello che
    # resta fuori rientra solo **dopo**, se la panchina non si è riempita: un posto
    # vuoto sarebbe peggio di un posto occupato male.
    quanti_ruolo = {}
    for v in panchina:
        r = v["g"].get("ruolo_classic")
        quanti_ruolo[r] = quanti_ruolo.get(r, 0) + 1
    scartati = []
    for v in sorted(avanzi, key=_chiave_merito):
        if v["g"]["id"] in usati:
            continue
        r = v["g"].get("ruolo_classic")
        if quanti_ruolo.get(r, 0) >= serve.get(r, 0):
            scartati.append(v)
            continue
        panchina.append(v)
        usati.add(v["g"]["id"])
        quanti_ruolo[r] = quanti_ruolo.get(r, 0) + 1
    for v in scartati:
        panchina.append(v)
        usati.add(v["g"]["id"])
    panchina = panchina[:n_panchinari or 0]

    # ⚠️ Dove le due letture litigano: un giocatore **non** schierato che ha punti
    # attesi più alti di un titolare del suo stesso ruolo. Succede quando la fascia
    # (che qui comanda) e il prodotto `percentuale × fantamedia` dicono cose
    # diverse, cioè nel caso di un ballottaggio con la fantamedia alta. Non è un
    # baco da correggere: è la scelta di lettura, e la pagina la mette in chiaro
    # invece di far credere che una risposta sola ci sia.
    # ⚠️ Si guardano **tutti quelli rimasti fuori**, non i soli panchinari: il
    # primo giro scorreva `panchina`, che è tagliata a `n_panchinari`, e quindi il
    # disaccordo più interessante — un giocatore con punti attesi altissimi che non
    # entra nemmeno in panchina — era l'unico che non veniva mai dichiarato. L'ha
    # preso la prova, con un caso costruito apposta.
    contesi = []
    for v in avanzi:
        if v["atteso"] is None:
            continue
        for t in titolari:
            if (t["g"].get("ruolo_classic") == v["g"].get("ruolo_classic")
                    and t["atteso"] is not None and v["atteso"] > t["atteso"]):
                contesi.append({"fuori": v, "dentro": t})
                break

    attesi = [v["atteso"] for v in titolari if v["atteso"] is not None]
    atteso = round(sum(attesi), 2) if attesi else None
    # ⚠️ Il modificatore sta **accanto** ai punti attesi, non dentro: `atteso` resta
    # la somma dei giocatori — che è quello che la pagina mostra riga per riga — e
    # `totale` è il numero su cui si confrontano due moduli. Sommarli in un campo
    # solo avrebbe reso impossibile capire da dove viene la differenza.
    mod = modificatore_atteso(titolari, regole)
    return {"modulo": modulo, "titolari": titolari, "panchina": panchina,
            "atteso": atteso, "mod": mod,
            "totale": (None if atteso is None else
                       round(atteso + (mod or {}).get("punti", 0.0), 2)),
            "senza_fm": len([v for v in titolari if v["fm"] is None]),
            "forzati": forzati, "ballottaggi": ballottaggi, "contesi": contesi}


def consiglia_moduli(valutazioni, moduli, n_panchinari=7, regole=None):
    """Un consiglio per ogni modulo ammesso, col migliore segnato.

    ⚠️ Il modulo si sceglie sui **punti attesi** dell'undici, che è l'unico modo di
    confrontare due formazioni con un numero solo — ed è dichiarato in pagina. Ma la
    graduatoria vale quanto vale la fantamedia che ci sta dentro: `senza_fm` dice
    per quanti dei titolari quel numero non esiste, e quando sono tanti il
    confronto fra moduli **non va creduto**. A settembre sono quasi tutti.
    """
    fuori = [c for c in (consiglia_formazione(valutazioni, m, n_panchinari, regole)
                         for m in moduli) if c]
    # ⚠️ Il confronto è sul `totale`, cioè punti attesi **più** modificatore di
    # difesa: in una lega che lo usa è la metà della domanda, e fino al 22/09/2026
    # il consiglio la ignorava — un 5-3-2 e un 3-4-3 venivano confrontati come se
    # il reparto difensivo valesse uguale. Dove il modificatore è spento `totale`
    # è `atteso`, quindi la graduatoria non cambia.
    migliore = None
    for c in fuori:
        if c["totale"] is not None and (migliore is None
                                        or c["totale"] > migliore["totale"]):
            migliore = c
    for c in fuori:
        c["migliore"] = (migliore is not None and c["modulo"] == migliore["modulo"])
    return fuori


# ── La rosa incollata ────────────────────────────────────────────────────────
# Una rosa di fantacalcio sono ~25 giocatori, e metterli in rosa uno per volta con
# la ricerca vuol dire 25 ricerche: è il motivo per cui il 21/09/2026, con tutto il
# resto della sezione in piedi, la rosa vera era ferma a **un** giocatore. Qui si
# incolla la lista e si scrive **dopo** aver visto cosa è stato riconosciuto: mai
# alla cieca, perché un nome abbinato male non dà nessun errore — dà la rosa di
# qualcun altro.
#
# ⚠️ **Quanto è ambiguo un nome, misurato sul listone del 21/09/2026** (597
# giocatori, 597 chiavi distinte):
#
#   * **0** nomi identici fra due giocatori: un nome scritto **per intero** come lo
#     scrive la fonte (`Martinez L.`) è sempre univoco;
#   * **24 cognomi** condivisi da due o più giocatori — `Martinez L.`/`Martinez Jo.`,
#     `Pellegrini Lo.`/`Pellegrini Lu.`, otto `De …`: un cognome secco **non basta**,
#     e va mostrata la scelta;
#   * e il caso che si sarebbe sbagliato in silenzio: **5 nomi che sono anche il
#     prefisso di un altro** — `Thuram` (INT, attaccante) esiste **e** c'è
#     `Thuram K.` (JUV, centrocampista), come `Colombo`/`Colombo L.`,
#     `Pessina`/`Pessina Mas.`, `Rrahmani`/`Rrahmani Al.`,
#     `Terracciano`/`Terracciano F.`. Scrivendo «Thuram» l'abbinamento esatto **è**
#     univoco e un codice ragionevole lo prenderebbe senza fiatare. Per questo un
#     nome che ha degli omonimi non è mai «ok»: è **«da confermare»**, con gli altri
#     in tendina e quello esatto già scelto.
#
# Quello che **non** si fa: indovinare un nome scritto male. Niente distanza di
# edit, niente «forse intendevi»: una riga che non combacia si dichiara non
# trovata. Un errore di battitura corretto a caso è esattamente il valore
# plausibile e falso di cui parla la regola #3.

# I modi in cui un ruolo può essere scritto in una lista incollata, singolare e
# plurale: il plurale serve perché una rosa esportata è spesso **raggruppata per
# ruolo**, e «Portieri» su una riga da sola è un'intestazione, non un giocatore.
RUOLI_SCRITTI = {
    "p": "p", "por": "p", "portiere": "p", "portieri": "p",
    "d": "d", "dif": "d", "difensore": "d", "difensori": "d",
    "c": "c", "cen": "c", "centrocampista": "c", "centrocampisti": "c",
    "a": "a", "att": "a", "attaccante": "a", "attaccanti": "a",
}

# La virgola fra due cifre è il separatore decimale italiano, non un separatore di
# campi: `Sommer, 12,5` ha una virgola di ognuno dei due tipi. Si distinguono
# guardando cosa hanno intorno, che è la stessa lezione di `soglie_mod_difesa()`.
_VIRGOLA_DECIMALE = re.compile(r"(?<=\d),(?=\d)")
_PEZZO = re.compile(r"[^\s;|,\t]+")


def chiave_nome(nome):
    """La forma con cui due nomi si confrontano: minuscolo, senza accenti né punti.

    ⚠️ I punti diventano **spazi**, non niente: `Martinez L.` e `Martinez Lo.`
    restano due chiavi diverse (`martinez l` e `martinez lo`), mentre togliendoli
    del tutto si otterrebbero `martinezl` e `martinezlo` — ancora diverse, ma
    `Esposito F.P.` diventerebbe `espositofp`, che non combacia più con niente di
    scritto a mano. E gli accenti si spogliano perché `Koné` e `Kone` sono lo
    stesso giocatore: nel listone vero ci sono tutti e due i modi.
    """
    grezzo = unicodedata.normalize("NFKD", str(nome or ""))
    grezzo = grezzo.encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", grezzo).split())


def _come_numero(pezzo):
    """Il numero che quel pezzo è, o `None`. `12.` e `12)` contano, `F.P.` no."""
    try:
        return float(str(pezzo).rstrip(".)"))
    except ValueError:
        return None


def indice_squadre(giocatori):
    """`{chiave: squadra}` per riconoscere «INT», «Inter» o «inter» in una riga.

    Sia la sigla (`squadra`) sia lo slug (`squadra_slug`) portano alla stessa
    sigla, che è quella che poi si confronta con `giocatori`.
    """
    fuori = {}
    for g in giocatori:
        sigla = (g.get("squadra") or "").strip()
        if not sigla:
            continue
        for forma in (sigla, g.get("squadra_slug") or ""):
            if forma:
                fuori[chiave_nome(forma)] = sigla
    return fuori


def analizza_riga_rosa(riga, squadre=None):
    """Una riga incollata, scomposta: nome, squadra, ruolo, prezzo.

    Torna `{"grezzo", "nome", "squadra", "ruolo", "prezzo", "intestazione",
    "dubbia"}`. Accetta le forme che una rosa incollata ha davvero — `Sommer`,
    `Sommer 15`, `P Sommer INT 15`, `1. Sommer;INT;15`, una riga di un foglio con
    i tab — perché non c'è un formato: c'è quello che esce dalla piattaforma di
    turno o da un messaggio in chat.

    Come si decide cos'è un pezzo, in quest'ordine:

    - un **numero** è l'indice se sta in testa (`1. Sommer`), il prezzo altrimenti.
      Con più di un prezzo possibile la riga si dichiara `dubbia` invece di
      scegliere: un numero in mezzo può essere tutto, e indovinare qui vorrebbe
      dire scrivere in rosa un prezzo che nessuno ha pagato;
    - un **ruolo** è `P`/`D`/`C`/`A` (o `por`, `difensori`, …) **senza il punto**:
      ⚠️ il punto è quello che distingue il ruolo dall'iniziale del nome, che nel
      listone è dappertutto (`Adams A.`, `Martinez L.`). Con `Adams A` — iniziale
      senza punto — la `A` viene letta come ruolo e il nome resta `Adams`, che è
      ambiguo: la riga finisce «da scegliere», cioè si sbaglia **verso la
      domanda**, non verso il giocatore sbagliato;
    - una **squadra** è una sigla o uno slug che esiste nel listone, e serve a
      disambiguare: `Martinez INT p` è uno solo;
    - tutto il resto è il **nome**.

    Una riga fatta di **solo ruolo** (`Difensori`) è un'intestazione: non è un
    giocatore e non è un errore.
    """
    grezzo = str(riga or "").strip()
    testo = _VIRGOLA_DECIMALE.sub(".", grezzo)
    pezzi = [p.strip("-–—•*·()[]\"'") for p in _PEZZO.findall(testo)]
    nome, squadra, ruolo, numeri, dubbia = [], None, None, [], False
    for posto, pezzo in enumerate(pezzi):
        if not pezzo:
            continue
        valore = _come_numero(pezzo)
        if valore is not None:
            numeri.append((posto, valore))
            continue
        chiave = chiave_nome(pezzo)
        if "." not in pezzo and chiave in RUOLI_SCRITTI:
            if ruolo is None:
                ruolo = RUOLI_SCRITTI[chiave]
            else:
                dubbia = True
            continue
        if squadre and chiave in squadre:
            if squadra is None:
                squadra = squadre[chiave]
                continue
            dubbia = True
        nome.append(pezzo)
    # Il prezzo: i numeri che non sono l'indice di testa. Più di uno e la riga si
    # dichiara, perché il secondo potrebbe essere il prezzo e potrebbe essere
    # qualunque altra cosa.
    prezzi = [v for posto, v in numeri if posto > 0]
    if len(prezzi) > 1:
        dubbia = True
    # ⚠️ Lo `strip` finale **non** tocca il punto, e la prova l'ha preso subito:
    # togliendolo, `Thuram K.` diventava `Thuram K` a schermo. Per l'abbinamento
    # non cambiava niente (`chiave_nome()` ignora i punti), ed è proprio per
    # questo che sarebbe passato inosservato — l'anteprima avrebbe mostrato per
    # venticinque righe un nome scritto diverso da come lo scrive la fonte.
    return {"grezzo": grezzo,
            "nome": " ".join(nome).strip(" ,-"),
            "squadra": squadra, "ruolo": ruolo,
            "prezzo": prezzi[-1] if prezzi else None,
            "intestazione": not nome and ruolo is not None and not prezzi,
            "dubbia": dubbia}


def _ordina_candidati(candidati, esatto=None):
    """Chi va mostrato per primo: l'abbinamento esatto, poi gli attivi di più valore.

    ⚠️ `attivo` prima di `fvm` e non il contrario: un giocatore **fuori listone** è
    quasi sempre la risposta sbagliata a un nome incollato oggi, per quanto valesse
    a settembre.
    """
    return sorted(candidati,
                  key=lambda g: (g["id"] != (esatto or {}).get("id"),
                                 not g.get("attivo", 1),
                                 -(g.get("fvm") or 0), g.get("nome") or ""))


def leggi_rosa_incollata(testo, giocatori, gia_in_rosa=()):
    """Le righe incollate, abbinate al listone. **Non scrive niente.**

    `giocatori` sono le righe del listone (`id`, `nome`, `squadra`,
    `squadra_slug`, `ruolo_classic`, `fvm`, `attivo`), `gia_in_rosa` gli id che
    quella lega ha già. Torna una lista di dict, uno per riga non vuota, con:

        grezzo, nome, prezzo, squadra, ruolo, candidati, scelto, stato,
        gia, doppione, dubbia, scarti

    I quattro stati, che sono quattro cose diverse e la pagina le dice diverse:

    - **`ok`** — un solo giocatore, nome esatto, nessun omonimo: si scrive;
    - **`conferma`** — un candidato ma da guardare, perché il nome ha **omonimi**
      (`Thuram`, che è anche `Thuram K.`), perché l'abbinamento non era esatto, o
      perché quello che c'era scritto sulla riga **non combacia** col giocatore
      trovato (`scarti`: la squadra, il ruolo). È già scelto, ma è dichiarato;
    - **`scegli`** — più candidati e nessuno esatto: **niente** è scelto, e la
      riga non si scrive finché non lo decide qualcuno;
    - **`niente`** — nessun candidato. Non si indovina.

    ⚠️ Il ruolo di un'intestazione (`Difensori`) **scende sulle righe dopo**: è il
    modo in cui una rosa raggruppata per ruolo si incolla intera, ed è anche quello
    che rende univoco un cognome condiviso da due giocatori di ruolo diverso.
    Il contrario — ignorarla — farebbe finire quattro righe su cinque in «scegli».
    """
    squadre = indice_squadre(giocatori)
    per_chiave, per_cognome = {}, {}
    for g in giocatori:
        chiave = chiave_nome(g.get("nome"))
        per_chiave.setdefault(chiave, []).append(g)
        if chiave:
            per_cognome.setdefault(chiave.split()[0], []).append(g)

    fuori, presi, ruolo_corrente = [], set(), None
    for riga in str(testo or "").splitlines():
        voce = analizza_riga_rosa(riga, squadre)
        if voce["intestazione"]:
            ruolo_corrente = voce["ruolo"]
            continue
        if not voce["nome"]:
            continue
        cercato = voce["ruolo"] or ruolo_corrente
        chiave = chiave_nome(voce["nome"])
        esatti = list(per_chiave.get(chiave, []))
        # Gli omonimi: chi ha lo stesso nome **più qualcosa** (`Thuram K.` per
        # `Thuram`). Servono in tutti e due i casi — se l'esatto c'è sono la
        # ragione per cui va confermato, se non c'è sono i candidati.
        piu_lunghi = [g for g in giocatori
                      if chiave and chiave_nome(g.get("nome")).startswith(chiave + " ")]
        if esatti:
            candidati, esatto = esatti + piu_lunghi, esatti[0]
        elif piu_lunghi:
            candidati, esatto = piu_lunghi, None
        else:
            # L'ultima rete: il cognome. Prende sia «Martinez» sia «Lautaro
            # Martinez», che nel listone è `Martinez L.` e per chiave non
            # combacerebbe con nessuno dei due versi.
            parole = chiave.split()
            candidati = list(per_cognome.get(parole[0], []))
            if len(parole) > 1:
                for g in per_cognome.get(parole[-1], []):
                    if g not in candidati:
                        candidati.append(g)
            esatto = None

        # Squadra e ruolo **restringono**, e solo se restano dei candidati: una
        # sigla scritta male non deve far sparire l'unico giocatore giusto — la
        # riga si vede comunque, con la scelta in mano a chi guarda.
        scarti = []
        for campo, atteso in (("squadra", voce["squadra"]), ("ruolo_classic", cercato)):
            if atteso:
                ridotti = [g for g in candidati if (g.get(campo) or "") == atteso]
                if ridotti:
                    candidati = ridotti
                    if esatto is not None and esatto not in ridotti:
                        esatto = None
                elif candidati:
                    # Niente combacia: i candidati restano tutti, ma la cosa si
                    # **dichiara**. ⚠️ Una squadra scritta sulla riga che non è
                    # quella del giocatore trovato non è un dettaglio: o la sigla
                    # è sbagliata, o il giocatore giusto è un altro che nel
                    # listone non c'è. Buttarla via lascerebbe una riga «sicura»
                    # che dice il contrario di quello che c'era scritto.
                    scarti.append(campo)

        # E restringe anche **l'iniziale**, con la stessa regola: se il nome
        # incollato è per intero (`Lautaro Martinez`) e i candidati si distinguono
        # per un'iniziale (`Martinez L.` contro `Martinez Jo.`), tiene quelli la cui
        # iniziale comincia davvero una delle parole scritte. Non è un indovinello:
        # `l` sta in «Lautaro» e `jo` non sta in niente, quindi resta uno.
        # ⚠️ Se non resta nessuno — «Martinez» secco, che non ha un nome proprio da
        # confrontare — non tocca niente e la riga va **in scelta**. È sempre la
        # stessa preferenza: sbagliare verso la domanda.
        # ⚠️ Il confronto **esclude il cognome**, e senza questa riga la regola si
        # ribalta: «Adams» da solo, contro `Adams A.` e `Adams C.`, sceglierebbe
        # `Adams A.` perché la «a» comincia «adams». Cioè inventerebbe una risposta
        # proprio nel caso in cui non c'è niente da confrontare. Preso qui il
        # 21/09/2026, col primo giro di prove.
        if len(candidati) > 1 and esatto is None:
            ridotti = []
            for g in candidati:
                pezzi_nome = chiave_nome(g.get("nome")).split()
                cognome, extra = pezzi_nome[0], pezzi_nome[1:]
                parole = [w for w in chiave.split() if w != cognome]
                if extra and parole and all(
                        any(w.startswith(pezzo) for w in parole) for pezzo in extra):
                    ridotti.append(g)
            if len(ridotti) == 1:
                candidati = ridotti

        candidati = _ordina_candidati(candidati, esatto)
        if not candidati:
            stato, scelto = "niente", None
        elif esatto is not None and len(candidati) == 1 and not scarti:
            stato, scelto = "ok", esatto
        elif esatto is not None:
            stato, scelto = "conferma", esatto
        elif len(candidati) == 1:
            stato, scelto = "conferma", candidati[0]
        else:
            stato, scelto = "scegli", None

        voce.update({"candidati": candidati, "scelto": scelto, "stato": stato,
                     "ruolo": cercato, "scarti": scarti,
                     "gia": bool(scelto and scelto["id"] in set(gia_in_rosa)),
                     "doppione": bool(scelto and scelto["id"] in presi)})
        if scelto:
            presi.add(scelto["id"])
        fuori.append(voce)
    return fuori


# ── Categorie di oggetti e abilità ───────────────────────────────────────────
# ⚠️ La **chiave** è il dato: sta in `category` dentro il catalogo, è il `value` delle
# tendine e il suffisso delle classi CSS (`cat-berry`, `cat-weather_override`). Non si
# tocca. Qui c'è solo l'etichetta italiana, che poi passa da `t()` come tutto il resto.
# Sta in un posto solo perché la usano tre schermate: i due editor e il catalogo.
CATEGORIE_OGGETTI = {
    "berry":      "Bacca",
    "choice":     "Scelta obbligata",
    "conditional": "Condizionale",
    "damage":     "Danno",
    "defensive":  "Difensivo",
    "healing":    "Cura",
    "orb":        "Sfera",
    "support":    "Supporto",
    "survival":   "Sopravvivenza",
    "terrain":    "Terreno",
    "type_boost": "Bonus di tipo",
    "utility":    "Utilità",
    "weather":    "Meteo",
    # ⚠️ `other` mancava, ed è **339 oggetti su 397**: la categoria di gran lunga più
    # comune. Senza, il badge e il filtro ricadevano sulla chiave grezza, e la tendina
    # non permetteva di filtrare l'86% del catalogo. Trovato il 13/08/2026 traducendo.
    "other":      "altro",
}
CATEGORIE_ABILITA = {
    "none":              "nessun effetto",
    "weather_override":  "impone il meteo",
    "weather_setter":    "evoca il meteo",
    "weather_boost":     "bonus col meteo",
    "type_immunity":     "immunità di tipo",
    "damage_reduction":  "riduzione del danno",
    "stab_boost":        "bonus STAB",
    "stat_modifier":     "modifica una stat",
    "power_boost":       "bonus di potenza",
    "speed_boost":       "bonus di Velocità",
    "status_boost":      "bonus con lo stato",
    "stat_boost_low_hp": "bonus a PS bassi",
    "other":             "altro",
}

GAME_STATUSES    = ["In corso","Completato","Pausa","Wishlist","Abbandonato"]
GAME_PLATFORMS   = ["PC","PlayStation 5","PlayStation 4","Nintendo Switch","Xbox","Mobile","Altro"]
ARDUINO_STATUSES = ["Idea","In sviluppo","Completato","Pubblicato"]
ARDUINO_BOARDS   = ["Arduino Uno","Arduino Nano","Arduino Mega","Arduino Leonardo","Arduino Pro Mini","ESP8266","ESP32","Raspberry Pi","Altro"]

SLUG_OVERRIDES = {
    "mr-rime": "mr-rime",
    "tauros-paldea-combat": "tauros-paldea-combat-breed",
    "tauros-paldea-blaze": "tauros-paldea-blaze-breed",
    "tauros-paldea-aqua": "tauros-paldea-aqua-breed",
    "meowstic-m": "meowstic-male",
    "meowstic-f": "meowstic-female",
    "basculegion-m": "basculegion-male",
    "basculegion-f": "basculegion-female",
    "mega-venusaur": "venusaur-mega",
    "mega-charizard-x": "charizard-mega-x",
    "mega-charizard-y": "charizard-mega-y",
    "mega-blastoise": "blastoise-mega",
    "mega-beedrill": "beedrill-mega",
    "mega-pidgeot": "pidgeot-mega",
    "mega-alakazam": "alakazam-mega",
    "mega-slowbro": "slowbro-mega",
    "mega-gengar": "gengar-mega",
    "mega-kangaskhan": "kangaskhan-mega",
    "mega-pinsir": "pinsir-mega",
    "mega-gyarados": "gyarados-mega",
    "mega-aerodactyl": "aerodactyl-mega",
    "mega-meganium": "meganium-mega",
    "mega-ampharos": "ampharos-mega",
    "mega-scizor": "scizor-mega",
    "mega-heracross": "heracross-mega",
    "mega-houndoom": "houndoom-mega",
    "mega-tyranitar": "tyranitar-mega",
    "mega-blaziken": "blaziken-mega",
    "mega-gardevoir": "gardevoir-mega",
    "mega-mawile": "mawile-mega",
    "mega-aggron": "aggron-mega",
    "mega-medicham": "medicham-mega",
    "mega-manectric": "manectric-mega",
    "mega-sharpedo": "sharpedo-mega",
    "mega-camerupt": "camerupt-mega",
    "mega-altaria": "altaria-mega",
    "mega-banette": "banette-mega",
    "mega-absol": "absol-mega",
    "mega-glalie": "glalie-mega",
    "mega-salamence": "salamence-mega",
    "mega-metagross": "metagross-mega",
    "mega-latias": "latias-mega",
    "mega-latios": "latios-mega",
    "mega-garchomp": "garchomp-mega",
    "mega-lucario": "lucario-mega",
    "mega-abomasnow": "abomasnow-mega",
    "mega-gallade": "gallade-mega",
    "mega-audino": "audino-mega",
    "mega-diancie": "diancie-mega",
    "mega-sableye": "sableye-mega",
    "mega-lopunny": "lopunny-mega",
    "mega-steelix": "steelix-mega",
    "mega-clefable": "clefable-mega",
    "mega-dragonite": "dragonite-mega",
    "mega-excadrill": "excadrill-mega",
    "mega-feraligatr": "feraligatr-mega",
    "mega-froslass": "froslass-mega",
    "mega-golurk": "golurk-mega",
    "mega-greninja": "greninja-mega",
    "mega-hawlucha": "hawlucha-mega",
    "mega-skarmory": "skarmory-mega",
    "mega-starmie": "starmie-mega",
    "mega-victreebel": "victreebel-mega",
    "mega-drampa": "drampa-mega",
    "mega-scovillain": "scovillain-mega",
    "mega-chesnaught": "chesnaught-mega",
    "mega-delphox": "delphox-mega",
    "mega-emboar": "emboar-mega",
    "mega-glimmora": "glimmora-mega",
    "mega-chandelure": "chandelure-mega",
    "mega-meowstic-(male)": "meowstic-male",
    "mega-meowstic-(f)": "meowstic-female",
    "mega-meowstic-(m)": "meowstic-male",
    "mega-floette": "floette-eternal",
    "eternal-flower-floette": "floette-eternal",
    "mega-crabominable": "crabominable",
    "alolan-ninetales": "ninetales-alola",
    "alolan-raichu": "raichu-alola",
    "hisuian-arcanine": "arcanine-hisui",
    "hisuian-typhlosion": "typhlosion-hisui",
    "hisuian-samurott": "samurott-hisui",
    "hisuian-decidueye": "decidueye-hisui",
    "hisuian-zoroark": "zoroark-hisui",
    "hisuian-avalugg": "avalugg-hisui",
    "hisuian-goodra": "goodra-hisui",
    "galarian-slowbro": "slowbro-galar",
    "galarian-slowking": "slowking-galar",
    "heat-rotom": "rotom-heat",
    "wash-rotom": "rotom-wash",
    "frost-rotom": "rotom-frost",
    "fan-rotom": "rotom-fan",
    "mow-rotom": "rotom-mow",
    "palafin-(hero-form)": "palafin-hero",
    "palafin-(zero-form)": "palafin",
    "aegislash-(blade-forme)": "aegislash-blade",
    "aegislash-(shield-forme)": "aegislash-shield",
    "meowstic-(male)": "meowstic-male",
    "meowstic-(female)": "meowstic-female",
    "basculegion-(male)": "basculegion-male",
    "basculegion-(female)": "basculegion-female",
    "morpeko-(full-belly-mode)": "morpeko",
    "gourgeist-(average)": "gourgeist",
    "gourgeist-(small)": "gourgeist-small",
    "gourgeist-(large)": "gourgeist-large",
    "gourgeist-(super)": "gourgeist-super",
}

# `ABILITIES_CALC` stava qui: elenco di 20 nomi inglesi delle abilità "supportate
# dal calcolatore". Rimossa l'11/08/2026 perché **non la importava nessuno**: chi
# marca le abilità che incidono è `abilityIncideSulDanno()` in calcolatori-core.js,
# che legge il blocco `effect` del catalogo — quindi l'elenco non solo era inerte,
# era anche destinato a divergere dai dati veri.

# Carica base stats dal catalogo. data/catalog/pokemon.json è il database di
# default completo; data/pokemon_catalog.json resta come fallback finché c'è.
def _load_champions_bst():
    for path in (os.path.join(DATA_DIR, "catalog", "pokemon.json"),
                 os.path.join(DATA_DIR, "pokemon_catalog.json")):
        try:
            with open(path, encoding="utf-8") as f:
                catalog = json.load(f)
            print(f"[DATA] Catalogo caricato: {len(catalog)} Pokémon da {os.path.basename(path)}")
            return catalog
        except Exception:
            continue
    if True:
        print("[DATA] Errore catalogo: nessun file leggibile")
        return {
            'pikachu': {'base_stats': {'hp':35,'atk':55,'def':40,'spa':50,'spd':50,'spe':90}, 'types':['Elettro'], 'abilities':[], 'moves':[]},
            'mimikyu': {'base_stats': {'hp':90,'atk':72,'def':90,'spa':50,'spd':94,'spe':96}, 'types':['Spettro','Folletto'], 'abilities':[], 'moves':[]},
        }

CHAMPIONS_BST = _load_champions_bst()


# ---------------------------------------------------------------------------
# MEGA MAP: quale specie base porta a quale Mega.
#
# Una Mega che sta nel roster ma che nessuna specie base punta e' **irraggiungibile**:
# il team builder non la offre e il calcolatore non ci arriva, senza nessun errore.
# La deduzione sta qui e non in `scripts/completa_mega_map.py` perche' dal 10/09/2026
# la usano in due — lo script da riga di comando e il pulsante «ricalcola» dell'editor
# regulation — e due copie della stessa regola divergono al primo caso nuovo.
# ---------------------------------------------------------------------------

# Le Mega inventate che non seguono la regola del nome. Il catalogo scrive la forma
# come `<Specie> (<Forma> Form)`, queste come `Mega <Forma> <Specie>`: nessuna regola
# generale le lega, quindi stanno qui una per una invece di essere indovinate.
# Verificate contro i nomi veri del catalogo il 12/08/2026.
BASE_A_MANO = {
    # Curly e' la forma predefinita di Tatsugiri: nel catalogo e' la voce nuda.
    "Mega Curly Tatsugiri":    "Tatsugiri",
    "Mega Droopy Tatsugiri":   "Tatsugiri (Droopy Form)",
    "Mega Stretchy Tatsugiri": "Tatsugiri (Stretchy Form)",
    "Mega Original Magearna":  "Magearna (Original Color)",
}


def base_attesa(mega):
    """`Mega Raichu X` -> `Raichu`; `Mega Meowstic (Male)` -> `Meowstic (Male)`."""
    if mega in BASE_A_MANO:
        return BASE_A_MANO[mega]
    base = re.sub(r"^Mega ", "", mega)
    # `Z` insieme a X e Y: `Mega Absol Z` sta a `Absol` come `Mega Charizard X` sta a
    # `Charizard`. E' la stessa convenzione, non un caso nuovo.
    return re.sub(r" [XYZ]$", "", base)


def collega_mega(roster, nomi_catalogo, mega_map):
    """Le Mega del roster non ancora raggiungibili, divise per cosa serve a collegarle.

    Torna tre elenchi, e la divisione **e' il punto**: solo il primo e' deducibile.

    - `collegamenti`  coppie `(base, mega)` con la base gia' nel roster: nessun dato
      nuovo, solo il collegamento fra due nomi gia' presenti
    - `senza_base`    coppie `(base, mega)` con la base nel catalogo ma **fuori** dal
      roster: collegarle vuol dire **aggiungere una specie**, che e' una scelta di
      contenuto e la prende chi chiama, non questa funzione
    - `problemi`      le Mega su cui ci si ferma: la base non e' nel catalogo, oppure
      la Mega stessa non c'e'. Non si indovina un nome che non esiste
    """
    mappate = {m for v in (mega_map or {}).values() for m in v}
    nomi = set(nomi_catalogo)
    collegamenti, senza_base, problemi = [], [], []
    for mega in sorted(n for n in roster if n.startswith("Mega ") and n not in mappate):
        base = base_attesa(mega)
        if mega not in nomi:
            problemi.append((mega, f"'{mega}' non e' nel catalogo"))
            continue
        if base not in nomi:
            problemi.append((mega, f"la base attesa '{base}' non e' nel catalogo"))
            continue
        (collegamenti if base in set(roster) else senza_base).append((base, mega))
    return collegamenti, senza_base, problemi


def applica_collegamenti(mega_map, collegamenti):
    """Aggiunge le coppie `(base, mega)` alla mega_map, ordinata. Torna la nuova."""
    nuova = {k: list(v) for k, v in (mega_map or {}).items()}
    for base, mega in collegamenti:
        nuova.setdefault(base, [])
        if mega not in nuova[base]:
            nuova[base].append(mega)
        nuova[base].sort()
    return dict(sorted(nuova.items()))
