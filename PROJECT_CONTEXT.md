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
    ├── pcbuilder.html
    └── reference.html
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
- `_load_roster()` → legge `data/roster_ma.json`, popola `REG_MA_ROSTER` e `POKEMON_TO_MEGA`
- `MEGA_EVOLUTIONS_MA` → set ordinato di tutte le Mega da `POKEMON_TO_MEGA`
- `NATURES` → lista 25 nature
- `NATURE_EFFECTS` → dict `{nature: ("+Stat", "-Stat")}` (solo le 20 non neutre)
- `SLUG_OVERRIDES` → dict di mapping nome → slug PokéAPI (forme regionali, Rotom, Aegislash, ecc.)
- `ABILITIES_CALC` → lista abilità supportate dal calcolatore danno (20 abilità)
- `CHAMPIONS_BST` → caricato da `_load_champions_bst()` → legge `data/pokemon_catalog.json`
  - Struttura: `{nome: {base_stats: {hp, atk, def, spa, spd, spe}, types: [...], abilities: [...], moves: [...]}}`
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

Import da `data.py`: `DATA_DIR, REG_MA_ROSTER, MEGA_EVOLUTIONS_MA, NATURES, NATURE_EFFECTS, CHAMPIONS_BST, ABILITIES_CALC`

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
| `/pokemon/calcolatori` | GET | Calcolatori VGC (passa `CHAMPIONS_BST`, `ABILITIES_CALC`, `NATURES`) |
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
| `/pokemon/api/regulations/create` | POST | Crea regulation |
| `/pokemon/api/regulations/<id>/delete` | POST | Elimina regulation |

### API Pokémon — `blueprints/api_pokemon.py` (route `/api/*` dirette)
| URL | Metodo | Descrizione |
|-----|--------|-------------|
| `/api/pokemon/<path:name>` | GET | Stats, tipi, abilità e sprite **dal catalogo locale** (nessuna chiamata a PokéAPI a runtime) |
| `/api/regulation/<id>/data` | GET | Roster della regulation — passa da `_load_roster()`, quindi legge il **filtro** (`data/regulations/<id>.json`) e ricade sul vecchio `roster_file` solo se la regulation non è migrata |
| `/api/moves` | GET | Mosse Reg. MA |

> ⚠️ **Non esistono** (erano documentate ma mai implementate): `/api/stat_champions`, `/api/regulations`, `/api/regulations/save`, `/api/team/<id>`.

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
| `ABILITIES_DATA` | Ricevuto da Flask via `{{ abilities_data \| safe }}` — 408 abilità, con blocco `effect` |
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
| PC Builder + DxDiag import | ✅ | |

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
