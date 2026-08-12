# 🗂️ PROJECT_CONTEXT — Personal Hub
> Repo: https://github.com/Zaffo97/Personal-Hub.git  
> Aggiornato: 07/08/2026 — verificato eseguendo il codice, non solo leggendolo

---

## ⚡ Come usare questo file

All'inizio di ogni sessione apri **sempre** con questo messaggio:

```
Stiamo lavorando al progetto Flask Pokémon.
Contesto: [incolla tutto il contenuto di PROJECT_CONTEXT.md]
Oggi voglio fare: [obiettivo specifico]
```

---

## 📐 Regole di Lavoro

> **Prima di scrivere qualsiasi codice, controllati:**
>
> 1. **Hai usato le variabili corrette? Hai rispettato tutte le regole?**
> 2. Non modificare nulla **fuori dallo scope** richiesto.
> 3. Non fare refactoring di funzioni non citate nella richiesta.
> 4. Non inventare nomi di file, variabili, ID HTML o route — chiedi prima.
> 5. Incolla **solo il blocco che cambia**, mai riscrivere l'intero file.
> 6. Se c'è ambiguità, chiedi prima di procedere.
> 7. Rispetta le convenzioni JS/Python già presenti (vedi sezione Convenzioni).
> 8. Ogni modifica ai calcolatori va testata con un caso noto prima di considerarla completa.
> 9. Non usare `localStorage` o `sessionStorage` — non disponibili nel sandbox.
> 10. Le stat in `CHAMPIONS_BST` sono **base stat grezze da `pokemon_catalog.json`** — la formula `calc_stat_champions` le converte a runtime.
> 11. 🏆 **Regola d'oro**: dopo ogni blocco di lavoro completato e verificato, esegui `python scripts/esporta_dati.py` e proponi il push. Zona test su `sviluppo`, `main` solo per il verificato, un tag a ogni blocco chiuso, e i branch `archivio/…` non si toccano. Per esteso in `CLAUDE.md`, che si carica da solo a ogni sessione.

---

## 🏗️ Stack Tecnico

| Layer | Tecnologia |
|-------|------------|
| Backend | Python 3.10+ · Flask 3.x |
| Entry point | `app.py` → `create_app()` con `app_context` |
| Database | SQLite · file `hub.db` (root, non committare) |
| ORM | `sqlite3` raw con `row_factory = sqlite3.Row` |
| Frontend | Jinja2 · CSS custom · Vanilla JS |
| Dati esterni | PokéAPI (sprite/stats) + JSON locali in `data/` |
| Auth | Session Flask (`login_required` da `extensions.py`) |
| Secret key | `os.environ.get("SECRET_KEY", "dev-secret-change-me")` |

---

## 📁 Struttura del Progetto

```
personal-hub/
├── app.py                   # Entry point — create_app(), registra 8 blueprint
├── data.py                  # Costanti statiche, CHAMPIONS_BST da pokemon_catalog.json
├── extensions.py            # DB, login_required, _i(), _f(), calc_stat_champions()
├── requirements.txt
├── hub.db                   # SQLite — NON committare
│
├── blueprints/
│   ├── __init__.py
│   ├── auth.py              # /login · /logout
│   ├── dashboard.py         # / · /export
│   ├── gaming.py            # /gaming · CRUD giochi
│   ├── pokemon.py           # ⭐ /pokemon/* — team, regulation, editor
│   ├── api_pokemon.py       # ⭐ /api/* — tutte le API JSON
│   ├── arduino.py           # /arduino
│   ├── python_tracker.py    # /python
│   └── pcbuilder.py         # /pcbuilder
│
├── data/
│   ├── regulations.json         # Registry di tutte le regulation
│   ├── pokemon_catalog.json     # ⭐ Base stat grezze tutti i Pokémon (usato da CHAMPIONS_BST)
│   ├── abilities.json           # Abilità per regulation (letto da load_abilities())
│   ├── roster_ma.json           # Lista Pokémon Reg. MA (+ mega_map)
│   ├── moves_ma.json            # 461 mosse Reg. MA
│   ├── items_ma.json            # Oggetti Reg. MA
│   └── roster_XX / moves_XX / items_XX   # Per altre regulation
│
├── scripts/                 # Utility di manutenzione (non parte del server)
│
├── static/
│   ├── css/calcolatori.css        # Stili del calcolatore
│   └── js/                       # ⭐ JS del calcolatore, caricato in QUEST'ORDINE
│       ├── calcolatori-data.js      # bootstrap dal JSON + TYPE_CHART e tutte le costanti
│       ├── calcolatori-core.js      # formule, nomi, motore abilità, motore meteo
│       ├── calcolatori-danno.js     # tab Danno
│       ├── calcolatori-speed.js     # tab Speed Tier
│       ├── calcolatori-stat.js      # tab Stat Preview + forme
│       ├── calcolatori-ref.js       # genera tabelle tipi/nature, overlay + tab Reference
│       └── calcolatori-ui.js        # quick-load team, init
│
└── templates/
    ├── base.html                # Layout: sidebar · topbar · dark/light toggle
    ├── login.html
    ├── dashboard.html
    ├── gaming.html · game_form.html
    ├── pokemon.html             # Lista team VGC
    ├── team_form.html           # Team builder con select regulation
    ├── calcolatori.html         # ⭐ Calcolatori VGC — 685 righe, solo HTML: zero JS inline
    ├── abilities_editor.html    # Editor abilità regulation-aware
    ├── regulation_editor.html   # Metadati regulation
    ├── regulations_list.html    # Elenco regulation
    ├── moves_editor.html        # Editor mosse (?reg=<id>)
    ├── roster_editor.html       # Editor roster (?reg=<id>)
    ├── items_editor.html        # Editor oggetti (?reg=<id>)
    ├── arduino.html
    ├── python.html
    └── pcbuilder.html
```

---

## 🧩 Moduli Chiave

### `app.py`
Entry point. `create_app()` chiama `init_db()` dentro `app_context`, poi registra tutti e 8 i blueprint. Non contiene route dirette.

```python
app.run(host="0.0.0.0", debug=True, port=5000)
```

---

### `data.py`
- `regulation_default()` → **id della regulation di partenza del sito**: la **prima**
  di `data/regulations.json`. È lo stesso criterio del fallback `regs[0]` che le route
  usano quando l'id richiesto non esiste, quindi il registro è l'unica fonte: per
  cambiare default si sposta una voce in cima al file, non si tocca il codice. Dall'11/08/2026
  la prima è **`pokedex`**. Se il registro non è leggibile ricade su
  `REGULATION_DEFAULT_EMERGENZA = "ma"`, l'unica che `_list_regulation_files()` sa inventare
- `_load_roster()` → legge `data/roster_ma.json`, popola `REG_MA_ROSTER` e `POKEMON_TO_MEGA`
- `MEGA_EVOLUTIONS_MA` → set ordinato di tutte le Mega da `POKEMON_TO_MEGA`
- `NATURES` → lista 25 nature
- `NATURE_EFFECTS` → dict `{nature: ("+Stat", "-Stat")}` (solo le 20 non neutre)
- `SLUG_OVERRIDES` → dict di mapping nome → slug PokéAPI (forme regionali, Rotom, Aegislash, ecc.)
- ~~`ABILITIES_CALC`~~ → **rimossa l'11/08/2026**: lista di 20 nomi inglesi che non
  importava nessun modulo. Chi marca le abilità che incidono è
  `abilityIncideSulDanno()` in `calcolatori-core.js`, leggendo il blocco `effect`
- `CHAMPIONS_BST` → caricato da `_load_champions_bst()` → legge `data/pokemon_catalog.json`
  - Struttura: `{nome: {base_stats: {hp, atk, def, spa, spd, spe}, types: [...], abilities: [...], forms: {...}}}`
  - ⚠️ **non** c'è un campo `moves`: questo file lo documentava, ma **zero specie su 1026**
    hanno un elenco mosse, e non ce l'aveva nemmeno il vecchio `pokemon_catalog.json`.
    Il progetto non sa quali mosse un Pokémon possa imparare — vedi `BACKLOG.md`
  - ⚠️ Sono **base stat grezze** — la conversione a stat Lv.50 avviene in `calc_stat_champions()`

---

### `extensions.py`
```python
DB = os.path.join(os.path.dirname(__file__), "hub.db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def get_db()       # → sqlite3.connect(DB) con row_factory e foreign_keys ON
def init_db()      # → CREATE TABLE IF NOT EXISTS + ALTER TABLE teams ADD regulation_id
                   #   crea anche l'utente di default admin/admin123
def login_required # → decorator, redirect a auth.login se "username" non in session
def _i(v, d=0)     # → int(v) con fallback d
def _f(v, d=0.0)   # → float(v) con fallback d

LINGUE = ("it", "en")
COOKIE_LINGUA = "hub_lang"
def lingua_attiva()          # → 'it' | 'en' dal cookie; 'it' fuori da una richiesta
def nome_vis(voce, chiave)   # → il nome da mostrare, `nome_it` o `nome_en`, con
                             #   fallback sulla chiave: mai una stringa vuota
```

> ⚠️ La lingua sta in un **cookie** e non in `localStorage` perché la deve leggere
> anche Flask: roster, mosse e oggetti nelle tendine li renderizza il server.
> `create_app()` espone `lang` e `nome_vis` a ogni template con un `context_processor`.

> ⚠️ **`calc_stat_champions()` non esiste più** (rimossa 07/08/2026). Era definita ma **mai chiamata** da nessun file, e usava una terza convenzione SP (`base + sp`) diversa sia dal JS sia dalla documentazione. Il calcolo delle stat vive **solo** in `calcSt()` in `calcolatori.html`.

---

### `blueprints/pokemon.py` ⭐

```python
bp = Blueprint("pokemon", __name__, url_prefix="/pokemon")
```

Funzioni helper interne:
```python
def _list_regulation_files()   # legge data/regulations.json, fallback a [{id:'ma',...}]
def _save_regulations(regs)    # scrive data/regulations.json
def _load_roster(reg)          # legge roster_file della regulation, fallback a REG_MA_ROSTER
def _load_mega_map(reg)        # legge mega_map dal roster_file della regulation
def load_abilities()           # legge data/abilities.json
def _save_abilities(data)      # scrive data/abilities.json, tenendo da parte la versione
                               #   precedente in archive/abilities_pre-salvataggio.json
def _archive_dir()             # data/archive/, creata se manca
```

> ⚠️ Passare **sempre** da `_save_abilities()` per le abilità e da `salva_catalogo()`
> per gli altri database: è lì che vive la copia di sicurezza. Scrivere i file del
> catalogo a mano salta la protezione.

### Catalogo e regulation — chi modifica cosa

| Schermata | Modifica |
|---|---|
| `/pokemon/catalogo` | **i dati**: base stat, potenza, tipi, effetti, descrizioni |
| `/pokemon/regulation/<id>/contenuto` | **quali voci** fanno parte della regulation (schermata a spunte) |
| `/pokemon/roster` · `/mosse` · `/oggetti` | idem, ma via JSON grezzo |

> ⚠️ **`ma` è la vera Regulation M-A di Pokémon Champions.** L'elenco attuale è
> ereditato dai file storici e **non è verificato** — non usarlo come fonte di verità
> e non dedurre da lì cosa sia legale. Quando serve popolare M-A o la futura M-B,
> l'elenco va chiesto: il catalogo contiene tutto, la regulation è solo un filtro.

Helper: `voci_catalogo(db)` legge sempre un dizionario piatto (le abilità sono
avvolte in `{"abilities": ...}`, gli altri tre no), `salva_catalogo(db, voci)` scrive
tenendo la copia precedente in `data/archive/catalog_<db>_pre-salvataggio.json`.

#### `data/catalog/pokemon_moves.json` — il quinto file, dal 12/08/2026

Le mosse che ogni voce **può imparare**. Sta a parte dal catalogo, non dentro, perché
`pokemon.json` finisce nel payload del browser e pesa già 547 KB per 8 campi a riga.
Generato da `scripts/importa_mosse_specie.py`, rieseguibile, e **non è un dato curato**:
si rigenera dal dump CSV di PokéAPI in un minuto, quindi non ha copia in
`data/archive/` — la rete di sicurezza è il controllo che le voci non calino.

```json
"incineroar": {
  "slug": "incineroar",
  "main":      {"vg": "scarlet-violet", "moves": {"Knock Off": "machine", …}},
  "champions": {"moves": {"Darkest Lariat": "train", …}}
}
```

**Due elenchi per voce, non uno**, ed è la cosa da non confondere:

- **`main`** — i giochi principali, dal version group più recente in cui la voce
  compare. È l'elenco della regulation `pokedex`
- **`champions`** — il moveset di **Pokémon Champions**, che nel dump di PokéAPI è un
  version group suo (`champions`, id 32). È l'elenco di `ma` e `mb`

Non coincidono: **Incineroar in Champions non ha Knock Off**, che nei giochi principali
impara con una MT. Il valore dice *come* si impara — `level-up:<n>`, `machine`, `egg`,
`tutor`, `train` (l'unico di Champions) — separati da virgola quando sono più d'uno.

⚠️ **Il file c'è, ma non lo legge ancora nessuno**: nessuna route, nessun endpoint,
nessun JS. Il consumo è la voce di backlog «mosse giuste per regulation».

Le chiavi sono le stesse del catalogo: la **chiave** per le specie, il **nome della
forma** per le forme annidate. Le forme inventate (Mega fan-made, Gourgeist di taglia,
Mega Meowstic) **non ci sono**, di proposito: PokéAPI non le conosce e il moveset della
specie base non è il loro.

Import da `data.py`: `DATA_DIR, regulation_default, REG_MA_ROSTER, MEGA_EVOLUTIONS_MA, NATURES, NATURE_EFFECTS, CHAMPIONS_BST`

---

### `blueprints/api_pokemon.py` ⭐
API JSON con prefisso `/api/*`. **Non chiama PokéAPI a runtime**: legge solo `pokemon_catalog.json`.

Risoluzione nomi e sprite (riscritta 07/08/2026):
```python
_normalize_key(name)   # minuscolo, senza punteggiatura, trattini singoli
                       # regge "Mr. Rime" e "Palafin (Zero Form)"
_slug_forma(nome)      # "Mega Venusaur" -> "venusaur-mega"
                       # "Alolan Raichu" -> "raichu-alolan"   (aggettivo COMPLETO)
                       # "Heat Rotom"    -> "rotom-heat"
_INDICE                # indice costruito all'avvio: chiavi top-level + campo `name`
                       # + le forme annidate in `forms` + alias dei nomi base
NON_ALIASABILI         # primi pezzi che NON diventano alias: mega, alolan, galarian,
                       # hisuian, paldean, totem, primal, partner, eternal, original,
                       # iron, tapu
SPRITE_SLUG_OVERRIDES  # 19 casi irregolari; HD None = artwork grande assente,
                       # si ricade sullo sprite normale
```

> ⚠️ Il catalogo tiene **84 forme annidate** dentro `forms` di 72 Pokémon. Senza `_INDICE` sono irraggiungibili: prima del fix **96 nomi su 300 davano 404**, quindi Mega e forme regionali non avevano né stat né sprite.
> Tutti gli sprite vengono da **pokemondb**. Il repo `pokesprite` non contiene forme regionali, Rotom né Pokémon recenti: era la causa di 38 sprite rotti.

> ⚠️ L'alias sul **primo pezzo** della chiave (`palafin-zero-form` → `Palafin`) non va applicato ai qualificatori di forma: su `mega-venusaur` registrava `mega`, e insieme al fallback di `_find_in_catalog` faceva rispondere **Mega Venusaur** a un nome inesistente come `Mega Machamp`. Per questo esiste `NON_ALIASABILI`. Se aggiungi un qualificatore nuovo (una regione, un prefisso di forma), mettilo lì: la risposta giusta a un nome che non esiste è **404**, non un Pokémon a caso.

---

## 🗺️ Route Principali

### Auth — `blueprints/auth.py`
| URL | Metodo | Descrizione |
|-----|--------|-------------|
| `/login` | GET/POST | Form login con hash password |
| `/logout` | GET | `session.clear()` + redirect |

### Dashboard — `blueprints/dashboard.py`
| URL | Metodo | Descrizione |
|-----|--------|-------------|
| `/` | GET | Home con statistiche aggregate |
| `/export` | GET | Export JSON dei dati |

### Gaming — `blueprints/gaming.py`
| URL | Metodo | Chiave? | Descrizione |
|-----|--------|---------|-------------|
| `/gaming/` | GET | — | Lista giochi (filtri stato + ricerca). ⚠️ `/gaming` senza slash dà 308 |
| `/gaming/new` · `/gaming/<id>/edit` · `/gaming/<id>/delete` | GET/POST | — | CRUD |
| `/gaming/api/steam/cerca?q=` | GET | ❌ no | Ricerca titoli su `storesearch`, max 12 |
| `/gaming/api/steam/gioco/<appid>` | GET | ❌ no | Dettagli da `appdetails`: generi in italiano, copertina, uscita |
| `/gaming/steam` | GET | — | Schermata import. Senza chiave mostra la **guida** invece del form |
| `/gaming/api/steam/libreria?profilo=` | GET | ✅ **sì** | `GetOwnedGames`: posseduti + ore. Accetta steamID64, URL o vanity |
| `/gaming/steam/importa` | POST | ❌ no | Importa gli appid scelti, deduplica sull'`appid` |
| `/gaming/api/steam/da-arricchire` | GET | ❌ no | Quanti giochi Steam sono senza genere |
| `/gaming/steam/arricchisci` | POST | ❌ no | Riempie i generi a lotti di 15, il client richiama fino a `rimasti: 0` |

> ⚠️ La chiave si legge **solo** da `os.environ["STEAM_API_KEY"]` (`steam_key()`): nessun
> campo nell'interfaccia, nessun file nel progetto. Su Windows un processo eredita una
> *copia* dell'ambiente: se la app parte prima che la variabile esista non la vedrà mai,
> e nessun riavvio del browser aiuta — va riavviata la app da un terminale nuovo.

> ⚠️ Il **nome visualizzato** Steam non è risolvibile via API: `ResolveVanityURL` accetta
> solo l'indirizzo personalizzato (`/id/<vanity>`), che molti profili non hanno. La strada
> affidabile è incollare l'URL completo del profilo.

### Pokémon — `blueprints/pokemon.py`
| URL | Metodo | Descrizione |
|-----|--------|-------------|
| `/pokemon` | GET | Lista team VGC |
| `/pokemon/team/new` | GET/POST | Crea team |
| `/pokemon/team/<id>/edit` | GET/POST | Modifica team |
| `/pokemon/team/<id>/delete` | POST | Elimina team |
| `/pokemon/calcolatori` | GET | Calcolatori VGC. Il bootstrap JSON porta `moves`, `abilities`, `reg_id`, `natures` e `champions` — **non** `ABILITIES_CALC`, che non è passata a nessun template |
| `/pokemon/regulations` | GET | Elenco regulation |
| `/pokemon/regulation/<id>` | GET | Editor metadati regulation |
| `/pokemon/roster` | GET/POST | Editor roster (`?reg=<id>`) |
| `/pokemon/roster/archive` | POST | Archivia il roster corrente |
| `/pokemon/roster/archives` | GET | Elenco archivi (JSON) |
| `/pokemon/roster/restore/<filename>` | POST | Ripristina un archivio |
| `/pokemon/mosse` · `/pokemon/mosse/archive` | GET/POST · POST | Editor mosse |
| `/pokemon/oggetti` · `/pokemon/oggetti/archive` | GET/POST · POST | Editor oggetti |
| `/pokemon/regulation/<id>/contenuto` | GET | ⭐ **Contenuti della regulation** (`?db=…`) — sceglie **quali** voci ne fanno parte |
| `/pokemon/api/regulation/<id>/contenuto/<db>` | POST | Salva l'elenco (o `tutto: true` per non filtrare) |
| `/pokemon/api/regulation/<id>/copia-da` | POST | Clona gli elenchi da un'altra regulation (`sorgente`, `campi`) |
| `/pokemon/catalogo` | GET | ⭐ **Editor del catalogo** (`?db=pokemon\|moves\|abilities\|items`) — modifica i **dati** |
| `/pokemon/api/catalogo/<db>/voce` | GET | JSON di una singola voce (`?nome=`) |
| `/pokemon/api/catalogo/<db>/salva` | POST | Crea, aggiorna o rinomina una voce |
| `/pokemon/api/catalogo/<db>/elimina` | POST | Elimina una voce, segnalando le regulation che la usano |
| `/pokemon/catalogo/<db>/archive` · `/archives` · `/restore/<file>` | POST · GET · POST | Archivio del catalogo |
| `/pokemon/abilita` | GET/POST | Editor abilità — **`abilita`, non `abilities`** |
| `/pokemon/abilita/archive` | POST | Archivia le abilità correnti |
| `/pokemon/abilita/archives` | GET | Elenco archivi abilità (JSON) |
| `/pokemon/abilita/restore/<filename>` | POST | Ripristina un archivio (solo file `abilities_*` dell'archivio) |

### API — sotto il blueprint `pokemon` (prefisso `/pokemon`)
| URL | Metodo | Descrizione |
|-----|--------|-------------|
| `/pokemon/api/abilities` | GET | Elenco abilità |
| `/pokemon/api/abilities/update` | POST | Aggiorna un'abilità |
| `/pokemon/api/abilities/delete` | POST | Elimina un'abilità |
| `/pokemon/api/regulations` | GET | Registro completo — lo usa la tendina Regulation del team builder |
| `/pokemon/api/regulations/save` | POST | Riscrive `regulations.json`. Rifiuta registro vuoto, voci senza `id`/`label`, id duplicati e ogni salvataggio che **perderebbe** una regulation esistente: il file dice anche qual è il default del sito |
| `/pokemon/api/regulations/create` | POST | Crea regulation |
| `/pokemon/api/regulations/<id>/delete` | POST | Elimina regulation. ⚠️ Cancella solo `roster_file`/`moves_file`/`items_file`: su una regulation a filtro il `data/regulations/<id>.json` **resta orfano** |

### API Pokémon — `blueprints/api_pokemon.py` (route `/api/*` dirette)
| URL | Metodo | Descrizione |
|-----|--------|-------------|
| `/api/pokemon/<path:name>` | GET | Stats, tipi, abilità e sprite **dal catalogo locale** (nessuna chiamata a PokéAPI a runtime) |
| `/api/regulation/<id>/data` | GET | Roster della regulation — passa da `_load_roster()`, quindi legge il **filtro** (`data/regulations/<id>.json`) e ricade sul vecchio `roster_file` solo se la regulation non è migrata |
| `/api/moves` | GET | Mosse della regulation richiesta (`?reg=`). Senza parametro: `regulation_default()`, cioè la prima del registro |

> ⚠️ **Non esistono**: `/api/stat_champions`, `/api/team/<id>`.
>
> `/api/regulations` e `/api/regulations/save` erano nella stessa lista, ma **il JS le
> chiamava davvero**: il Salva Metadati dell'editor regulation e la tendina Regulation
> del team builder morivano su un 404, il primo con un toast "Errore rete", la seconda
> in un `catch` muto. Dall'11/08/2026 esistono, sotto il blueprint `pokemon`
> (`/pokemon/api/regulations` e `/pokemon/api/regulations/save`), ed è lì che i due
> template puntano.

---

## 🗄️ Database — Tabelle SQLite

Tutte create da `init_db()` in `extensions.py`.

| Tabella | Colonne chiave |
|---------|----------------|
| `users` | id, username UNIQUE, password (hash), display_name, role DEFAULT 'user' |
| `games` | id, title, platform, genre, status DEFAULT 'Wishlist', hours_hltb, cover_url, prog_story/side/collect (int), date_start/end, notes, created_at, **steam_appid** INTEGER, **hours_played** REAL |

> ⚠️ `hours_hltb` e `hours_played` sono due cose diverse: la prima è la **durata stimata**
> (HowLongToBeat), la seconda le **ore effettivamente giocate** lette da Steam. L'import
> Steam scrive solo la seconda. Entrambe le colonne arrivano da un `ALTER TABLE` in
> `init_db()` con `except: pass`, come `teams.regulation_id`.
| `teams` | id, name, format, record, description, notes, **regulation_id** DEFAULT 'ma', created_at |
| `team_members` | id, team_id (FK → teams CASCADE), slot, pokemon, mega_stone, nature, ability, held_item, tera_type, move1-4, ev_hp/atk/def/spa/spd/spe, sprite_url |
| `arduino_projects` | id, name, board, status, tinkercad_url, code, description |
| `python_topics` | id, category, name, done |
| `pc_builds` | id, name, notes |
| `pc_components` | id, build_id (FK), category, name, price, notes |
| `regulations` | id TEXT PK, label, roster_file, moves_file, items_file, created_at |

> ⚠️ `teams.regulation_id` corrisponde a un `id` in `data/regulations.json` **e** nella tabella `regulations`.  
> `init_db()` fa `ALTER TABLE teams ADD COLUMN regulation_id` con `except: pass` per compatibilità.

---

## 📦 Come è organizzato il calcolatore (dall'08/08/2026)

`calcolatori.html` contiene **solo HTML**. Regole per modificarlo:

1. **Non rimettere JS inline nel template.** Va in `static/js/calcolatori-*.js`, nel file del tab che tocca.
2. **I dati di Flask passano da un solo punto**: il blocco `<script type="application/json" id="calc-bootstrap">` in fondo al template. `calcolatori-data.js` lo legge e dichiara `MOVES_DB`, `ABILITIES_DATA`, `REG_ID`, `CHAMPIONS_BST`. Per passare un nuovo dato dal blueprint, aggiungi una chiave lì — non un nuovo `<script>`.
3. **L'ordine dei 6 `<script>` è obbligatorio**: `data` → `core` → `danno` → `speed` → `stat` → `ui`. I `const` di un file classico sono visibili agli altri, ma solo se dichiarati prima.
4. Sono classic script, non moduli: le funzioni sono globali e gli `onclick` del template le vedono. Non aggiungere `type="module"`, romperebbe ogni handler inline.
5. Il CSS della pagina va in `static/css/calcolatori.css`.
6. **Le tabelle di riferimento non sono HTML**: i quattro `<div>` `tab_tipi_box`, `tab_nature_box`, `ovl_tipi_box`, `ovl_nature_box` sono vuoti nel template e li riempie `calcolatori-ref.js` al primo accesso. Per cambiare l'efficacia di un tipo si tocca **`TYPE_CHART` e basta**: la stessa costante che usa `calcDamage()`, così tabella e calcolo non possono divergere.

7. **Le Mega non hanno una tabella tutta loro.** `fetchPkmn()` le chiede a `/api/pokemon` come qualsiasi altra forma: le stat stanno in `data/catalog/pokemon.json`, annidate in `forms` della specie base. `isMega` e il BST li deriva `marcaMega()` — il BST è la somma delle base.

8. **I nomi mostrati non sono le chiavi.** `nomeVis(voce, chiave)` sceglie fra `nome_it` e `nome_en` in base a `LANG` (dal cookie `hub_lang`), e `risolviChiave(db, nome)` fa il percorso inverso quando l'utente scrive in una casella con datalist. Nelle `<select>` il `value` resta **sempre** la chiave.

> ⚠️ `MEGA_DATA` **non esiste più** (eliminata l'11/08/2026). Era la terza copia delle stat: il tab Danno leggeva lei e lo Speed Tier il catalogo, che per le Mega conteneva le stat di Lv.50 già calcolate — quindi la formula finiva applicata due volte e lo stesso Mega Venusaur valeva 80 di Velocità di qua e 100 di là. Non reintrodurla: per cambiare le stat di una Mega si usa `/pokemon/catalogo`.

> ⚠️ `TYPE_CHART` sta in `calcolatori-data.js` ed è l'**unica** type chart. Non ricrearne una locale dentro `calcDamage()`: era così fino all'08/08/2026, e la tabella mostrata all'utente era un blocco di HTML scollegato, duplicato in due copie da 46 KB.

> ⚠️ `{% block extra_head %}` di `base.html` sta **fuori** dallo `<style>` (spostato l'08/08/2026): puoi metterci sia `<style>` sia `<link>`. Prima era dentro, e un `<link>` veniva silenziosamente ignorato.

---

## 🧮 Formula Stat Champions

**Unica implementazione**, in JavaScript — `static/js/calcolatori-core.js`:

```javascript
function calcSt(base, ev, iv, lvl, nm, isHP) {
    const b = parseInt(base, 10) || 0;
    const e = parseInt(ev, 10) || 0;   // SP 0-32, ogni SP vale +2 (convenzione Champions)
    const i = parseInt(iv, 10) ?? 31;
    const l = parseInt(lvl, 10) || 50;
    if (isHP) return Math.floor((2 * b + i + e * 2) * l / 100) + l + 10;
    return Math.floor(Math.floor((2 * b + i + e * 2) * l / 100 + 5) * (nm || 1.0));
}
```

`updateSpeed()` in `calcolatori-speed.js` usa la **stessa** formula inline: se tocchi una delle due, allinea l'altra.

> ⚠️ **Fino al 07/08/2026 le due erano disallineate**: Speed Tier usava `ev*2`, mentre `calcSt` (tab Danno e Stat Preview) usava `floor(ev/4)` — la convenzione EV standard 0-252, incompatibile col cap a 32 SP. Stesso Pokémon con 32 SP: **152 nello Speed Tier, 124 nello Stat Preview**. E investire tutti i 32 SP dava **+4** invece di **+32**, rendendo gli SP quasi inutili. Ora entrambe usano `ev*2`.

**Caso di prova noto** (usalo per validare ogni modifica, come da regola #8):
Incineroar (atk base 115) Adamant, 32 SP atk, Lv50 → Amoonguss (def 70, hp 114) Hardy, 32 SP hp e def, mossa fisica Buio BP 100.
Atteso: **A=183, D=122, HP=221, danno 85-102 (38.5%–46.2%)**.

### Regole EV Champions
- Max **32 SP** per singola stat
- Max **66 SP** totali per team member
- IV fissi **31**, Livello fisso **50**

### Condizioni del calcolo danno — valori in uso

Tutte misurate in browser l'08/08/2026, un effetto per volta.

| Condizione | Moltiplicatore | Note |
|---|---|---|
| Critico | ×1.5 | **Ignora** gli stage negativi dell'attaccante e positivi del difensore, e ignora gli schermi |
| Helping Hand | ×1.5 | |
| Scottatura | ×0.5 su A | Solo mosse fisiche. Con Combattività (Guts) diventa ×1.5 |
| Reflect / Light Screen | `SCHERMO_DOPPIE` = 2732/4096 | Valore delle **doppie**, non ×0.5. Ciascuno agisce solo sulla propria categoria |
| Terreno elettrico / erboso / psichico | ×1.3 | Dipende **solo dal tipo della mossa**, mai dalla categoria |
| Terreno nebbioso | ×0.5 | Solo mosse Drago |
| Spread | ×0.75 | |

> ⚠️ I terreni non hanno condizioni sulla categoria. Fino all'08/08/2026 ce le avevano, e Wild Charge, Energy Ball e Psychic Fangs non ricevevano nessun boost dal terreno corrispondente.

### Stage Multipliers (JS `stageMult`)
```
-6=×0.25 | -5≈×0.286 | -4≈×0.333 | -3=×0.4 | -2=×0.5 | -1≈×0.667
 0=×1.0  |  +1=×1.5  |  +2=×2.0  | +3=×2.5 | +4=×3.0 | +5=×3.5 | +6=×4.0
```

---

## 🏷️ Convenzioni

### HTML IDs — `calcolatori.html`
| Prefisso | Pannello |
|----------|----------|
| `atk_*` | Attaccante — es. `atk_name`, `atk_ev_atk`, `atk_ability`, `atk_nature` |
| `def_*` | Difensore — es. `def_name`, `def_ev_hp`, `def_ability`, `def_tera` |
| `spe_*` | Speed Tier — es. `spe_name`, `spe_base`, `spe_abil`, `spe_weather` |
| `mv_*` | Mossa — es. `mv_name`, `mv_bp`, `mv_type`, `mv_cat` |
| `f_*` | Flag/condizioni — es. `f_crit`, `f_hh`, `f_weather`, `f_terrain`, `f_burned` |
| `dmg_*` | Output — es. `dmg_result`, `dmg_min`, `dmg_max`, `dmg_rolls`, `dmg_percent` |

### Oggetti JS Globali
| Variabile | Contenuto |
|-----------|-----------|
| `BS.atk` | Oggetto con stats+sprite del Pokémon attaccante caricato |
| `BS.def` | Oggetto con stats+sprite del Pokémon difensore caricato |
| `loadTimers` | Oggetto per debounce: chiavi `spe`, `atk`, `def` (500ms) |
| `CHAMPIONS_BST` | Ricevuto da Flask via `{{ champions_bst\|safe }}` (già `json.dumps` nel blueprint). 174 voci top-level, stat in **`base_stats.spe`** — non `.spe` |
| `ABILITIES_DATA` | Ricevuto da Flask via `{{ abilities_data \| safe }}` — **391** abilità dopo la fusione dei doppioni dell'11/08/2026, con blocco `effect`. Si interroga con `abilityEffect(nome)`, che risolve chiave, nome italiano e nome inglese |
| `REG_ID` | Id della regulation attiva, da `{{ current_reg.id \| tojson }}` |
| `catalogIndex()` / `catalogEntry(nome)` | Indice del catalogo che copre anche le **84 forme annidate** in `forms` — equivalente JS di `_INDICE` in `api_pokemon.py` |
| `meteoEffettivo()` | `{weather, fonte}` — il meteo che il calcolo usa davvero. Le abilità `weather_override` vincono sulla tendina, le `weather_setter` valgono solo se non è stato scelto nulla. **Usare questo, non `f_weather` grezzo** |
| `WEATHER_BALL_TYPE` / `tipoPallaClima(w, fonte)` | Mappa meteo→tipo per la Palla Clima; `weather_ball_type` di `abilities.json` fa da override quando il meteo viene da un'abilità |
| `MOSSE_METEO` / `applicaMeteoAllaMossa()` | Mosse con BP o tipo dipendenti dal meteo (Weather Ball, Solar Beam, Solar Blade). Riscrive `mv_bp` e `mv_type` **nei campi visibili**, così il valore calcolato è quello che l'utente vede. Chiamata in testa a `calcDamage()` e da `onMoveSelect()` |

> ⚠️ `CHAMPIONS_DATA` e `ABILITIES_LIST` **non esistono**: erano documentati con questi nomi ma nel template si chiamano `CHAMPIONS_BST` e `ABILITIES_DATA`.

### Variabili JS — Deprecate / Da Rimuovere
| Variabile | Stato |
|-----------|-------|
| `currentSpeAbility` | ❌ Deprecata — usare `document.getElementById('spe_abil').value` |
| `atkAbilityFx` | ❌ Calcolata ma non usata in `calcDamage()` — da rimuovere |
| `defAbilityFx` | ❌ Calcolata ma non usata in `calcDamage()` — da rimuovere |

### Python / Blueprint
- Tutte le route protette da `@login_required` (decorator da `extensions.py`)
- Route GET → `render_template()`; POST → operazione DB + `redirect(url_for(...))`
- API JSON: prefisso `/api/`, sempre `jsonify()`
- Editor regulation-aware: `reg = request.args.get('reg', 'ma')`
- Helper numerici: usare sempre `_i()` e `_f()` da `extensions.py`
- Import da altri moduli: sempre da `extensions` o `data`, mai import ciclici tra blueprint

### Slug PokéAPI
Usare `SLUG_OVERRIDES` da `data.py` per tutte le forme speciali (regionali, Rotom, Aegislash, Palafin, Meowstic, Basculegion, ecc.) prima di chiamare la PokéAPI.

### Tipi Pokémon (in italiano nel codice)
`Normale · Fuoco · Acqua · Elettro · Erba · Ghiaccio · Lotta · Veleno · Terra · Volante · Psico · Coleottero · Roccia · Spettro · Drago · Buio · Acciaio · Folletto`

---

## ✅ Stato Attuale

| Feature | Stato | Note |
|---------|-------|------|
| Flask setup, auth, DB | ✅ | Session-based, SQLite, `init_db()` |
| Architettura Blueprint (8 bp) | ✅ | `create_app()` con `app_context` |
| `pokemon_catalog.json` | ✅ | Base stat grezze → `CHAMPIONS_BST` |
| Gaming Tracker | ✅ | CRUD completo + progressione |
| Pokémon Team Builder | ✅ | 6 slot, multi-regulation |
| Sistema Multi-Regulation | ✅ | `regulations.json` + tabella DB |
| Editor Abilità regulation-aware | ✅ | `abilities_editor.html` + `abilities.json` |
| Calcolatore Danno — formula Gen9 | ✅ | Con type chart IT (18 tipi). Verificato in browser 07/08/2026 |
| Calcolatore Danno — abilità ATK/DEF | ✅ | **Motore data-driven** dal blocco `effect` di `abilities.json` |
| Speed Tier — abilità + condizioni | ✅ | Stesso motore del tab Danno |
| Stat Preview — tendina abilità | ✅ | Aggiunta 07/08/2026 su entrambi i lati |
| Formula EV Champions (`e * 2`) | ✅ | Allineata in `calcSt()` **e** `updateSpeed()` |
| Sprite Mega e forme regionali | ✅ | 296/300 nomi risolti, **0 immagini rotte** |
| Arduino Projects | ✅ | |
| Python Tracker | ✅ | |
| PC Builder + DxDiag import | ✅ | Il 500 trovato l'11/08/2026 (`sqlite3.Row` passata a `\|tojson` con una build salvata) è chiuso lo stesso giorno: la vista costruisce `dict(b)`. Modale Modifica provato in browser |

---

## 🐛 Problemi Noti

**Tutti gli 8 problemi storici sono stati chiusi il 07/08/2026.** Vedi `BACKLOG.md` per ciò che resta aperto.

| # | Problema | Come è stato chiuso |
|---|----------|---------------------|
| 1 | Abilità tipo-cambio | Nuovo effetto `ate` su Pellecielo/Pellefolletto/Pellegelo/Pellelettro/Normalità — cambia il tipo **prima** di STAB e type chart, ×1.2 |
| 2 | Flag "contatto" mancante | Non mancava: `flags:["contact"]` c'era già su 164 mosse, nessuno lo leggeva. Ora compila la checkbox `f_contact` a ogni mossa scelta |
| 3 | Fluffy incompleta | Non è un boost di Difesa: ×0.5 su contatto e ×2 sul Fuoco, indipendenti |
| 4 | Wonder Guard | Implementata su `Magidifesa` (il nome corretto in `abilities.json`) |
| 5 | Overgrow/Blaze/Torrent/Swarm | Nuova checkbox `f_atk_pinch` "Attaccante sotto 1/3 HP" |
| 6 | `currentSpeAbility` | Rimossa |
| 7 | `atkAbilityFx`/`defAbilityFx` | Rimossi con tutto il vecchio motore `getAbilityEffects()` |
| 8 | Formule stat disallineate | `calc_stat_champions()` eliminata; `calcSt()` e `updateSpeed()` usano entrambe `ev*2` |

### ⚠️ Il problema che nessuno aveva notato

Fino al 07/08/2026 `calcolatori.html` conteneva un **`SyntaxError`** (resti di un merge alle righe 718-729: `const SPEED_META_STATIC=[` non chiuso + dichiarazioni duplicate). Il browser scartava l'intero blocco `<script>` da 320KB: **nessuna riga di JavaScript della pagina veniva eseguita**.

Di conseguenza tutto ciò che questa tabella dava per "funzionante" non era mai stato provato in un browser. Lo stesso identico guasto è stato poi trovato in `pcbuilder.html:202`, dove teneva morto l'intero PC Builder.

**Morale operativa:** dopo ogni modifica ai template, renderizzare la pagina ed eseguire `new vm.Script()` su ogni blocco inline. Intercetta questa classe di bug in pochi secondi.

---

## 📅 Log Sessioni

| Data | Contenuto |
|------|-----------|
| 2026-08-12 | **Gli elenchi mosse per specie, importati** — il buco più grosso che restava nei dati: zero specie su 1026 avevano un `moves`, e nemmeno il vecchio catalogo (0 su 174). `scripts/importa_mosse_specie.py` scrive `data/catalog/pokemon_moves.json` (2,7 MB), è rieseguibile e **idempotente** (due giri, stesso md5), e si ferma se le voci calano. Non usa la API REST ma il **dump CSV** di PokéAPI, lo stesso di `build_catalog.py`: un file da 10 MB invece di 1026 chiamate. La scoperta che ha cambiato il lavoro sta lì dentro: fra i version group c'è **`champions` (id 32), 19 810 righe su 319 voci** — il moveset ufficiale di Pokémon Champions esiste, ed è la fonte esatta di `ma` e `mb`. Quindi ogni voce ha **due elenchi**: `main` (il version group più recente in cui compare: 862 voci su Scarlatto/Violetto, 167 su Spada/Scudo, a scendere) e `champions`. **Non coincidono**, ed è verificato sul caso che Davide ha citato: **Incineroar in Champions non ha Knock Off**, che in S/V impara con una MT — 11 mosse in meno e 8 in più, 80 contro 77. Copertura contata: `ma` **274/279** con moveset e 273 con la lista Champions, `mb` **302/308** e 301, `pokedex` **1291/1343**, con **zero nomi irrisolti** in tutti e tre. Canarino: **Magikarp ha 3 mosse** e Fulmine non è fra queste. Restano fuori **20 forme inventate**, che per decisione di Davide **non ereditano** il moveset della specie base, e 32 Gigantamax, che nel dump non ne hanno uno proprio. ⚠️ Il file **non lo legge ancora nessuno**: il consumo è la voce di backlog «le mosse giuste per ogni regulation», aperta oggi. ⚠️ Trovato preparando l'import e **non corretto** perché fuori scope: **`build_catalog.py` oggi distruggerebbe il catalogo** — legge come base i file storici (174 voci, senza `nome_it`, con le Mega ancora convertite: `Mega Venusaur` a `hp 155` contro `hp 80`) e scrive in `data/catalog/`. Rieseguirlo riporterebbe indietro quattro giorni di lavoro, in silenzio |
| 2026-08-11 | **Due lavori aperti a backlog per le prossime sessioni.** (1) **Gli elenchi mosse per specie**, che non sono mai esistiti — zero su 1026, e nemmeno nel vecchio catalogo: per questo il calcolatore accetta qualunque mossa su qualunque Pokémon e nessuna regulation sa se le sue mosse bastino. La strada è `scripts/build_catalog.py` più i `moves[]` di PokéAPI, con `SLUG_OVERRIDES` e la cache già pronti; da decidere prima quali metodi di apprendimento tenere e cosa fare delle forme inventate, che su PokéAPI non ci sono. (2) **Ogni Pokémon deve mostrare solo le sue abilità**: oggi le tendine del tab Danno e dello Stat Preview elencano tutte e 386 le voci, mentre lo Speed Tier fa già la cosa giusta ed è il modello. Qui il dato **c'è** — 307 nomi distinti, tutti risolti tranne `Zero To Hero` — quindi è lavoro di interfaccia; ⚠️ ma prima va colmato il catalogo, perché **238 specie su 1026 hanno una sola abilità** (e 173 forme su 317): stringere le tendine adesso toglierebbe scelte legittime invece che rumore |
| 2026-08-11 | **Le tre voci che aspettavano una decisione, chiuse.** (1) **`Mirror Herb` → «Foglia carbone» è confermato**: controllato su [Bulbapedia](https://bulbapedia.bulbagarden.net/wiki/Mirror_Herb), fonte indipendente da quella usata dall'import, che dà lo stesso nome italiano. Il giapponese è ものまねハーブ (*erba imitatrice*) e lo spagnolo *Hierba Copia*: è la localizzazione italiana ufficiale a essere strana, non il nostro dato. Sospetto tolto. (2) **Mosse e oggetti di MB restano quelli di MA** (460 e 58): finché non c'è una fonte su cosa cambi davvero, copiare MA è l'ipotesi meno arbitraria, e la differenza fra le due regulation resta il roster. (3) **Colonne del tab Danno allineate**: `align-items` da `start` a `stretch`, da 548/699/564 a 699 per tutti e tre, con le larghezze invariate (360 · 265 · 360). ⚠️ Misurando MB è emerso che **il catalogo non contiene gli elenchi mosse per specie** — zero su 1026, e non li aveva nemmeno il vecchio `pokemon_catalog.json`: non si può sapere se le mosse di una regulation bastino ai suoi Pokémon, né quali manchino a chi viene aggiunto. Questo file documentava un campo `moves` che non è mai esistito: corretto |
| 2026-08-11 | **mega_map completate, MB popolata, doppioni di nome chiusi.** Con `scripts/completa_mega_map.py` ogni Mega presente in un roster è ora **raggiungibile**: MA passa da 58/59 a **59/59** e MB da 58/75 a **75/75**. Su MA la voce di backlog era sbagliata — diceva che la base di `Mega Meowstic (Male)` non era nel roster, ma cercava `Meowstic` mentre dentro c'è `Meowstic (Male)`: bastava collegarle. Su **MB**, che era rimasta un segnaposto, Davide ha deciso di **aggiungere le 13 specie base mancanti** (Barbaracle, Blaziken, Metagross, Swampert…), portando il roster da 295 a **308**; lo script lo fa solo per le regulation elencate in `AGGIUNGI_BASI`, perché aggiungere una specie è una scelta di contenuto e il roster di MA, che viene dalla wiki, non si tocca. Poi `scripts/fondi_doppioni_nome.py` ha tolto la causa del baco di `Sheer Force`: **8 coppie di chiavi diverse con lo stesso nome** fuse, con il criterio «resta la chiave giusta, i campi mancanti arrivano dall'altra» — non «vince il nome ufficiale», che su `King's Rock` avrebbe tenuto la variante importata e inerte invece di quella curata. I **filtri sono stati aggiornati di conseguenza**: MA e MB contenevano entrambe le varianti di `Freeze Dry`, quindi le mosse scendono da 461 a **460**, la stessa mossa contata due volte. Infine `scripts/rifinisci_abilita.py`: le **10 abilità di Champions** lo dicono ora nella propria descrizione, e il fallback `data/abilities.json` è stato **riallineato** al catalogo (408 → 386 voci) — non dismesso, ma non è più una macchina del tempo che riporterebbe indietro i doppioni. Chiuso anche lo **Speed Tier senza limite**: tetto a 300 righe (da 1343 righe / 714 KB a 300 / 159 KB), tagliando le più **lontane** dalla propria Velocità e lasciando il conto pieno scritto sopra la tabella. Verifica: **40 controlli su 40**, zero nomi condivisi e zero chiavi con spazi ai bordi in tutti e tre i database, regola #8 invariata, sweep su 25 pagine / 47 script / 2287 handler senza errori |
| 2026-08-11 | **Le decisioni sui nomi, e il pacchetto di lavori piccoli.** Applicate con `scripts/applica_nomi_decisi.py` le scelte fatte a mano sulle voci dove PokéAPI e wiki non concordavano: `Aura Sphere` → **Sferapulsar** e `Heal Pulse` → **Curapulsar** (la wiki ha ragione), `Max Revive` → **Revitalizzante Max** e `Exp. Share` → **Condividi Esperienza** (forma estesa: si abbrevia per la casella di testo del gioco, qui lo spazio non manca), mentre i **sei refusi della wiki** (`Vasterngia`, `Morostretto`…) restano scartati e `Mirror Herb` → «Foglia carbone» resta dichiarato sospetto. **Mega Zygarde lasciata ferma**: correggendo il backlog, tutte e sei le stat seguono la firma di conversione, ma deconvertirla darebbe uno SpA di 216, il più alto del catalogo di 43 punti. Lavori piccoli: **selettore regulation nei tre editor** (prima si cambiava solo con `?reg=` a mano nell'URL), **bandierine** al posto di `IT`/`EN` — in **SVG inline**, perché su Windows le emoji bandiera si leggerebbero «IT» e «GB», cioè le stesse due lettere — e il pulsante lingua **mostrato solo sotto `/pokemon/*`**, dato che traduce solo i dati Pokémon. Rimossi `ABILITIES_CALC` (zero consumer) e `reference.html` (orfano, 70 righe). ⚠️ Verificando è saltato fuori che **due chiavi diverse possono avere gli stessi `nome_it` e `nome_en`**: `Sheer Force` esiste come `Forza Bruta` (con l'effetto) e `Forzabruta` (inerte), e la risoluzione per nome introdotta poco prima sceglieva l'inerte — cioè quell'effetto non si applicava. `indiceNomi()` ora a parità di nome tiene la voce con un effetto: danno da 82 a **106**, il ×1.3 atteso. Restano 8 doppioni veri, segnalati. Verifica: regola #8 invariata, sweep su 26 pagine / 45 script / 2205 handler senza errori |
| 2026-08-11 | **Abilità doppie fuse — e il motore degli effetti riattaccato ai Pokémon.** Il guasto era più grosso della fusione: il catalogo Pokémon cita le abilità col **nome inglese** (`Swift Swim`), le chiavi del file sono italiane (`Nuotovelox`) e `abilityEffect()` faceva un match **esatto sulla chiave** — dei **307** nomi posseduti dai Pokémon, **zero** arrivavano a un effetto, e tutti e 56 gli effetti del file erano irraggiungibili. Nel tab Danno non si vedeva (lì la tendina elenca tutte le abilità in italiano); nello Speed Tier, popolato con le abilità del Pokémon, **nessun effetto si applicava mai**: Kingdra sotto pioggia con Swift Swim restava a **105** invece di 210. Servivano due metà, inutili da sole: `abilityEffect()` ora risolve per chiave/nome_it/nome_en con lo stesso `risolviChiave()` delle mosse, e **24 coppie sono state fuse** portando l'effetto sulla voce ufficiale (`scripts/fondi_abilita_doppie.py`, con `--dry-run` e copia in `data/archive/abilities_pre-fusione.json`): **415 → 391 voci**. Dopo: Kingdra **105 → 210**, i 307 nomi posseduti risolvono tutti (erano 7) e quelli che arrivano a un effetto passano da 22 a **39**. Le coppie non sono indovinate — l'accoppiamento per somiglianza di testo sbagliava (`Combattività` → `Bruciaimpeto`), quindi ogni voce è mappata a mano sull'abilità reale che il suo `effect` descrive e lo script risolve quel nome inglese contro i dati, fermandosi su ciò che non trova. Sulle 7 coppie con effetto su entrambe i blocchi erano **identici 7 su 7**. **Non toccate** le 10 voci il cui effetto non corrisponde a nessuna abilità reale (`Nervosismo`, `Tiratore`, `Manto Neve`…, probabilmente abilità di Champions) né le 7 senza traduzione appese a un Pokémon. Verifica: **39 controlli su 39**, regola #8 invariata (85-102), sweep su 27 pagine / 47 script / 2216 handler senza errori. Aperto dalla fusione: `Megasolar` ha `nome_en: "Mega Sol"` (aggancio sbagliato dell'import) e **`ABILITIES_CALC` non la usa nessuno** |
| 2026-08-11 | **I cinque bachi piccoli già localizzati, chiusi.** (1) **`/pcbuilder/` rispondeva 500**: la vista metteva la `sqlite3.Row` grezza in `{"data": b}` e il template la passa a `\|tojson` nell'`onclick` di Modifica — la sezione era inaccessibile appena c'era una build salvata, e nel DB ce n'è una. Ora `dict(b)`; modale provato in browser, carica `ZAFFO-PC` con i suoi 5 componenti. (2) **53 `onmouseout` morti in `python.html:45`**, il ramo `{% else %}` che produceva `background=''''`: da **0 handler vivi su 53 a 53 su 53**, provato eseguendo mouseover/mouseout e renderizzando entrambi i rami. (3) **`loadSpePkmn()`** riempiva `spe_base` senza chiamare `updateSpeed()`: Incineroar → base 60 / Velocità **80**, Dragapult → 142 / **162**. (4) **L'eliminazione di una regulation** cancellava solo i tre file del vecchio modello, quindi sulle regulation nuove `data/regulations/<id>.json` restava orfano mentre la modale prometteva di averlo cancellato: ora è nell'elenco, con **copia in `data/archive/`** prima di toglierlo, e il testo della modale dice il vero. (5) **`Galarian Darmanitan` dava 404**: delle 57 voci con qualificatore regionale è l'unica scritta `X (Y Form)` invece che `Y X`. Il nome nel catalogo **non è stato toccato** — è l'identità della forma, la usano i filtri — e la differenza si colma con un alias nell'indice; verificato che gli altri regionali risolvano ancora e che i nomi inventati restino 404. Verifica: **22 controlli su 22** sul test client e sweep su **26 pagine / 45 script / 2206 handler inline, zero errori** (erano 54) |
| 2026-08-11 | **Le quattro voci su regulation e interfaccia, chiuse.** (1) I tre campi legacy `roster_file`/`moves_file`/`items_file` compaiono ora solo sulle regulation **non** migrate, e con loro spariscono dal salvataggio: `campiFile()` legge solo gli input presenti, quindi su una regulation a filtro non vengono più scritti, e su `ma` restano conservati — verificato salvando davvero dal browser. (2) Titolo della sezione Pokémon generico; nello stesso giro sono caduti gli altri "Reg MA" scritti a mano che il nuovo default avrebbe reso falsi (i tre editor ora dicono `current_reg.label`, che le route già passavano). (3) Catalogo prima di Calcolatori. (4) **`pokedex` è il default**: i 14 letterali `"ma"` sono sostituiti da **`regulation_default()` in `data.py`**, che restituisce la **prima** regulation del registro — lo stesso criterio del fallback `regs[0]` già in uso, così il default si cambia spostando una riga in `regulations.json`. Misurato: `/api/moves` senza `reg` da 461 a **921** mosse, oggetti da 58 a **398**, roster del team builder da 279 a **1343**. Verificando è saltato fuori che **tre endpoint chiamati dal JS non esistevano**: il Salva Metadati dell'editor regulation non aveva mai salvato nulla (404 → catch → "Errore rete") e la tendina Regulation del team builder restava con la **sola opzione stampata dal template**, cioè la regulation di un team non era mai stata scegliibile dall'interfaccia. Aggiunti `GET /pokemon/api/regulations` e `POST /pokemon/api/regulations/save`, quest'ultimo con i controlli prima della scrittura (5 payload rifiutati su 5, file intatto dopo) perché ora il registro dice anche qual è il default del sito. Verifica: **41 controlli su 41** sul test client, regola #8 esatta in browser su `pokedex` **senza `?reg=`** (A=183, D=122, HP=221, 85-102 = 38.5%–46.2%), tendina del team a 3 regulation con roster 1343 → 279 al cambio, sweep su **26 pagine / 44 script / 2197 handler inline** con due soli errori, entrambi preesistenti e segnalati a backlog: i 53 `onmouseout` di `python.html` e **`/pcbuilder/` che risponde 500** (`Row` non serializzabile in `pcbuilder.html:63`, sezione inaccessibile appena c'è una build salvata) |
| 2026-08-11 | **Traduzioni mancanti chiuse con la wiki di Pokémon Central** — `scripts/importa_nomi_wiki.py`, il secondo giro dopo PokéAPI. Due fonti: le pagine «… in altre lingue» (950 mosse, 860 strumenti, 306 abilità) e, per ciò che quelle liste non coprono, la **pagina singola** dello strumento, accettata solo se la sua riga *Inglese* combacia con la chiave del catalogo — così un risultato di ricerca sbagliato viene scartato invece di entrare nei dati. Esito: **mosse 32/32** (22 traduzioni vere: le 18 mosse Z, `Syrup Bomb`, `Blood Moon`, `Matcha Gotcha`, `Ivy Cudgel`), **oggetti 57/57** (20 traduzioni vere, tutte dalla pagina singola perché gli strumenti di nona generazione non stanno nell'elenco: `Booster Energy` → Capsula energetica, le maschere di Ogerpon, i sette Mochi), **abilità 5 su 108**. Le altre 47 mosse/oggetti "senza traduzione" non erano un buco: Megapietre e cristalli Z in italiano si scrivono uguale, e ora è verificato invece che presunto. Lo script **non sovrascrive** una traduzione già presente: dove PokéAPI e wiki non concordano (11 voci) si limita a segnalarlo, perché nessuna delle due fonti è sempre giusta — PokéAPI abbrevia (`Autodistruz.`), la wiki ha refusi (`Vasterngia`). Le **103 abilità** che restano non sono un problema di traduzione: il file contiene **due famiglie di voci per la stessa abilità**, 307 col nome ufficiale (quelle a cui i Pokémon sono collegati, ma solo 22 con un effetto attivo) e 108 vecchie (34 con l'effetto che il calcolatore usa davvero) — 7 coppie hanno un blocco `effect` identico. Segnalato a backlog, non toccato. Verifica: 28 controlli sul test client e **regola #8 esatta in browser** su `pokedex` (A=183, D=122, HP=221, 85-102, 38.5%–46.2% con +STAB), con la tendina oggetti che mostra `Piuma fatata ×1.2` in italiano e `Fairy Feather ×1.2` in inglese |
| 2026-08-11 | **Switch lingua IT ⇄ EN, primo blocco: i nomi dei dati.** Pulsante `IT`/`EN` in `base.html` accanto al tema. Le **chiavi del catalogo non cambiano mai** — le usano i filtri delle regulation, il motore degli effetti e i team salvati — e ogni voce riceve `nome_it` e `nome_en` da `scripts/importa_nomi_lingua.py`: mosse 899/921, oggetti 378/398, abilità 312/415, Pokémon 1019/1026, con chi non si aggancia che tiene la chiave nelle due lingue. Si può scrivere in entrambe: `risolviChiave()` lato JS e `_INDICE` lato Python accettano chiave, italiano e inglese. La lingua sta in un **cookie**, non in localStorage, perché la legge anche Flask. Restano fuori le stringhe dell'interfaccia, gli editor (mostrano la chiave) e le descrizioni |
| 2026-08-11 | **Stat delle Mega riportate alle base.** Nel catalogo 95 Mega su 101 avevano le stat di Lv.50 già calcolate dentro `base_stats` (+75 HP e +20 sulle altre, l'aritmetica esatta della formula del progetto): deconvertite con `scripts/deconverti_mega_catalogo.py`. Prova che è la lettura giusta: 56 su 57 riproducono `MEGA_DATA` alla cifra, e **tutte** le Mega ufficiali che `MEGA_DATA` non copriva (Metagross, Mewtwo X/Y, Rayquaza, Salamence, Swampert, Sceptile, Latias, Latios, Mawile, Diancie, Blaziken) coincidono coi valori reali del gioco. Rimosse 3 chiavi top-level che erano **doppioni** della forma annidata (1029 → 1026 voci) ed eliminata `MEGA_DATA`, la terza copia delle stat: ora anche le Mega passano da `/api/pokemon`, quindi tab Danno e Speed Tier non possono più divergere. Restano tre casi da decidere a mano: `Mega Froslass` (Vel 100 o 120), `Mega Machamp` (nessuna stat) e `Mega Zygarde` (rotta a sé). Verificando è saltato fuori **`/api/regulation/<id>/data`**, che leggeva ancora il vecchio `roster_file` come faceva `/api/moves`: lo Speed Tier mostrava i 208 nomi ereditati di MA (**zero Mega**) invece dei 279 veri, e su `pokedex` e `mb` andava in 404 ricadendo muto sulla lista statica da 158. Corretto. Corretti poi, su indicazione di Davide, **Mega Froslass** (la Velocità nel catalogo era già una base, non un valore convertito: riportata a 120 → **140** a Lv.50) e **Mega Machamp**, che non esiste ed è stata rimossa. Rimuoverla ha scoperchiato un baco vecchio: `/api/pokemon/Mega Machamp` rispondeva **Mega Venusaur** invece di 404, perché `mega` era finito tra gli alias — di qui `NON_ALIASABILI`. Verifica finale: regola #8 esatta (A=183, D=122, HP=221, 85-102), Mega Venusaur **80 → 100** e Mega Froslass **120 → 140** identici nei tab Danno e Speed Tier, Speed Tier MA **279/279** con 59 Mega e 0 sprite mancanti, 24 pagine / 43 blocchi script / 929 handler inline senza errori tranne 53 `onmouseout` morti in `python.html:45`, preesistenti e lasciati a backlog |
| 2026-08-10 | **Sezione Gaming agganciata a Steam.** Ricerca in inserimento (un clic compila titolo, genere, copertina, `appid`), import della libreria con le ore giocate, arricchimento dei generi a lotti. Solo `GetOwnedGames` richiede la chiave, tutto il resto usa endpoint pubblici. Nuove colonne `steam_appid` e `hours_played`, quest'ultima **distinta** da `hours_hltb`. 41 controlli end-to-end + 0 errori di sintassi JS su 4 rendering. Importati 34 giochi / 904.8 ore con generi al 100%. Due bug miei corretti in corsa: l'import metteva tutto su "In corso" rendendo inutile il filtro per stato, e un errore di rete durante l'arricchimento marcava il gioco come senza-genere per sempre |
| 2026-05-02 | Setup Flask, DB, auth, sidebar base |
| 2026-05-03 | Tutti i template, Pokémon VGC, PC Builder + DxDiag |
| 2026-05-04 | Calcolatori VGC, 461 mosse, fix EV/IV, editor mosse/roster |
| 2026-05-07 | Sistema Regulation multi, refactor Blueprint, `extensions.py`, editor abilità |
| 2026-05-19 | Select abilità ATK/DEF calcolatore, select abilità Speed Tier, checkbox condizioni Speed, fix `calcDamage()` (moltiplicatori diretti, HH deduplicato), fix formula EV Champions (`e*2`) |
| 2026-06-09 | Generazione `PROJECT_CONTEXT.md` da lettura diretta del codice sorgente su GitHub |
| 2026-08-10 | **Editor del catalogo separato** (`/pokemon/catalogo`): quattro linguette, modifica una voce per volta via API invece di scaricare 449 KB nel browser, tabella limitata a 300 righe con ricerca, avviso se elimini una voce usata da una regulation, archivio e copia automatica pre-salvataggio. 31 controlli end-to-end. Verificato in browser il nuovo modello: regola #8 esatta, 8 condizioni di danno, 7 casi meteo, 19 pagine pulite, Speed Tier da 189 a 202 su 208. Corretto `/api/moves`, che leggeva `moves_ma.json` hardcoded e faceva crollare le mosse del Pokedex da 921 a 461 |
| 2026-08-08 | **Archivio e backup delle abilità**: `_save_abilities()` non teneva nulla da parte, quindi un salvataggio sbagliato azzerava 408 abilità. Ora copia automatica a scorrimento prima di ogni salvataggio, più archivio manuale, elenco e ripristino (`/pokemon/abilita/archive`, `/archives`, `/restore/<file>`). Il salvataggio rifiuta un `abilities` vuoto e il ripristino accetta solo file dell'archivio. 18 controlli end-to-end, giro completo con md5 identico |
| 2026-08-08 | **Condizioni del calcolo danno verificate una per una** (24 casi misurati in browser): 3 bug nei terreni — elettrico, erboso e psichico avevano una restrizione di categoria inesistente nel gioco, quindi le mosse della categoria "sbagliata" non prendevano nulla; il critico non ignorava gli stage sfavorevoli all'attaccante; Reflect e Light Screen usavano il valore delle singole (×0.5) invece di quello delle doppie (2732/4096). Tutti corretti. Burn, Guts, Helping Hand, spread e accumulo dei moltiplicatori erano già giusti |
| 2026-08-08 | **`calcolatori.html` spacchettato**: 1885 → 687 righe, **222 → 38 KB**, zero JS inline. CSS in `static/css/`, JS in 7 moduli `static/js/calcolatori-*.js`, dati da un blocco `application/json`. Le tabelle tipi e nature, 108 KB di HTML duplicato in due copie e scollegato dal motore, sono generate da `calcolatori-ref.js` a partire da `TYPE_CHART`/`NATURES`+`NM` — HTML risultante identico byte per byte all'originale, e 0 disaccordi su 324 celle nel confronto col motore. Parità verificata (regola #8, Speed Tier 189, 12 casi meteo, Drago→Folletto = 0). Corretto `extra_head` di `base.html`, che stava dentro lo `<style>` e lasciava un `</style>` orfano in 10 pagine — motivo per cui un `<link>` veniva ignorato |
| 2026-08-08 | **Motore meteo** nel calcolatore: `meteoEffettivo()` fa vincere le abilità `weather_override` sulla tendina e fa evocare il meteo alle `weather_setter` quando non è stato scelto nulla; `tipoPallaClima()` legge `weather_ball_type` da `abilities.json` (campo presente su 7 abilità e mai usato prima); `applicaMeteoAllaMossa()` riscrive BP e tipo nei campi visibili. Coperte Weather Ball, Solar Beam, Solar Blade; aggiunta la Pioggia forte con `fire_blocked`. Verificato l'editor abilità: era già completo, la voce di backlog era stale |
| 2026-08-08 | Verifica in browser di tutte le 13 pagine (script inline + handler negli attributi): 0 `SyntaxError`. Caso di prova regola #8 eseguito e superato (A=183, D=122, HP=221, 85-102). **Speed Tier**: `loadRegSpeed()` leggeva `bst.spe` invece di `base_stats.spe`, scartava 174 Pokémon su 174 e ricadeva muta sulla lista statica — ora costruisce 189 righe dal roster MA e segnala i 19 nomi assenti dal catalogo. **Ripristino roster**: l'`onsubmit` del pulsante Ripristina era un `SyntaxError`, `form.onsubmit` era `null` e il roster veniva sovrascritto senza conferma |
| 2026-08-07 | Chiuso il rebase interrotto e ripristinato `calcolatori.html`. Corretto il `SyntaxError` che azzerava tutto il JS della pagina. Allineate le formule stat su `ev*2`. Motore abilità **data-driven** da `abilities.json` (56 abilità con effetto, tutte e 408 nelle tendine con ● sulle 44 attive). Chiusi i problemi noti 1-8. Tendina abilità nello Stat Preview. Pulizia dead code (−100 KB a caricamento). Sprite: 0 rotti su 296 nomi. Corretto il layout dei tre editor. Trovati e corretti 5 bug via grafo graphify, incluso il `SyntaxError` del PC Builder. Documentazione riallineata |
