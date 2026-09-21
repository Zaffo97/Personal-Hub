import os
import json
import re

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
