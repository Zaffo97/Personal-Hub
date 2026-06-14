# 🗂️ PROJECT_CONTEXT — Personal Hub
> Repo: https://github.com/Zaffo97/Personal-Hub.git  
> Aggiornato: 09/06/2026 — generato da lettura diretta del codice sorgente

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
├── static/                  # File statici (CSS, JS, immagini)
│
└── templates/
    ├── base.html                # Layout: sidebar · topbar · dark/light toggle
    ├── login.html
    ├── dashboard.html
    ├── gaming.html · game_form.html
    ├── pokemon.html             # Lista team VGC
    ├── team_form.html           # Team builder con select regulation
    ├── calcolatori.html         # ⭐ Calcolatori VGC — 215KB, tutto inline
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
def init_db()      # → CREATE TABLE IF NOT EXISTS per tutte le tabelle + ALTER TABLE teams ADD regulation_id
def login_required # → decorator, redirect a auth.login se "username" non in session
def _i(v, d=0)     # → int(v) con fallback d
def _f(v, d=0.0)   # → float(v) con fallback d

def calc_stat_champions(base, sp, alignment, is_hp=False):
    if is_hp:
        return base + sp         # HP: base_stat + sp (grezzo)
    return math.floor((base + sp) * alignment)   # Altre: floor((base + sp) * alignment)
```

> ⚠️ `calc_stat_champions` in Python è usata solo lato server. Il frontend usa `calcSt()` in JS in `calcolatori.html`. Devono restare **sincronizzate**.

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
def _save_abilities(data)      # scrive data/abilities.json
```

Import da `data.py`: `DATA_DIR, REG_MA_ROSTER, MEGA_EVOLUTIONS_MA, NATURES, NATURE_EFFECTS, CHAMPIONS_BST, ABILITIES_CALC`

---

### `blueprints/api_pokemon.py` ⭐
Tutte le API JSON del progetto (19KB). Prefix: nessuno (route `/api/*` dirette).

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

### Pokémon — `blueprints/pokemon.py`
| URL | Metodo | Descrizione |
|-----|--------|-------------|
| `/pokemon` | GET | Lista team VGC |
| `/pokemon/team/new` | GET/POST | Crea team |
| `/pokemon/team/<id>/edit` | GET/POST | Modifica team |
| `/pokemon/team/<id>/delete` | POST | Elimina team |
| `/pokemon/calcolatori` | GET | Calcolatori VGC (passa `CHAMPIONS_BST`, `ABILITIES_CALC`, `NATURES`) |
| `/pokemon/regulations` | GET | Elenco regulation |
| `/pokemon/regulation/<id>` | GET/POST | Editor metadati regulation |
| `/pokemon/roster` | GET/POST | Editor roster (`?reg=<id>`) |
| `/pokemon/mosse` | GET/POST | Editor mosse (`?reg=<id>`) |
| `/pokemon/oggetti` | GET/POST | Editor oggetti (`?reg=<id>`) |
| `/pokemon/abilities` | GET/POST | Editor abilità (`?reg=<id>`) |

### API Pokémon — `blueprints/api_pokemon.py`
| URL | Metodo | Descrizione |
|-----|--------|-------------|
| `/api/pokemon/<name>` | GET | Stats + sprite da PokéAPI + override locale |
| `/api/stat_champions` | GET | CHAMPIONS_BST serializzato in JSON |
| `/api/regulations` | GET | Lista regulation |
| `/api/regulation/<id>/data` | GET | Roster + mosse + oggetti + meccaniche |
| `/api/regulations/save` | POST | Salva regulations.json |
| `/api/regulations/create` | POST | Crea nuova regulation |
| `/api/regulations/<id>/delete` | POST | Elimina regulation |

---

## 🗄️ Database — Tabelle SQLite

Tutte create da `init_db()` in `extensions.py`.

| Tabella | Colonne chiave |
|---------|----------------|
| `users` | id, username UNIQUE, password (hash), display_name, role DEFAULT 'user' |
| `games` | id, title, platform, genre, status DEFAULT 'Wishlist', hours_hltb, cover_url, prog_story/side/collect (int), date_start/end, notes, created_at |
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

## 🧮 Formula Stat Champions

### In Python — `extensions.py`
```python
def calc_stat_champions(base, sp, alignment, is_hp=False):
    if is_hp:
        return base + sp
    return math.floor((base + sp) * alignment)
```
- `base` = base stat grezzo da `pokemon_catalog.json`
- `sp` = SP investiti (0–32, ogni SP vale +1 in questa formula)
- `alignment` = moltiplicatore natura (es. 1.1, 0.9, 1.0)
- `is_hp` = True per calcolo HP

### In JavaScript — `calcolatori.html`
```javascript
function calcSt(base, ev, iv, lvl, nm, isHP) {
    const b = parseInt(base, 10) || 0;
    const e = parseInt(ev, 10) || 0;   // SP 0-32, ogni SP vale +2 in questa formula JS
    const i = parseInt(iv, 10) ?? 31;
    const l = parseInt(lvl, 10) || 50;
    if (isHP) return Math.floor((2 * b + i + e * 2) * l / 100) + l + 10;
    return Math.floor(Math.floor((2 * b + i + e * 2) * l / 100 + 5) * (nm || 1.0));
}
```

> ⚠️ Le due formule **non sono identiche** — usano convenzioni diverse per SP.  
> Il frontend JS è quello visibile all'utente: è la versione autorevole per il calcolatore.

### Regole EV Champions
- Max **32 SP** per singola stat
- Max **66 SP** totali per team member
- IV fissi **31**, Livello fisso **50**

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
| `CHAMPIONS_DATA` | Ricevuto da Flask via `{{ champions_bst | tojson }}` |
| `ABILITIES_LIST` | Ricevuto da Flask via `{{ abilities_calc | tojson }}` |

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
| Calcolatore Danno — formula Gen9 | ✅ | Con type chart IT (18 tipi) |
| Calcolatore Danno — abilità ATK/DEF | ✅ | `ABILITIES_CALC` (20 abilità) |
| Speed Tier — abilità + condizioni | ✅ | `spe_abil`, checkbox, meteo |
| Formula EV Champions (`e * 2`) | ✅ | Fix applicato in `calcSt()` JS |
| `SLUG_OVERRIDES` forme speciali | ✅ | ~80 override in `data.py` |
| Arduino Projects | ✅ | |
| Python Tracker | ✅ | |
| PC Builder + DxDiag import | ✅ | |

---

## 🐛 Problemi Noti

| # | Problema | Dettaglio | Priorità |
|---|----------|-----------|----------|
| 1 | Abilità tipo-cambio | Aerilate/Pixilate/Galvanize/Refrigerate cambiano tipo mossa — non gestiti in `calcDamage()` | Media |
| 2 | Flag "contatto" mancante | Tough Claws e Fluffy dipendono da questo flag, non presente nel JSON mosse | Media |
| 3 | Fluffy doppio effetto incompleto | ×0.5 su contatto + ×2 vs Fuoco — attualmente solo ×2 su fisica generica | Bassa |
| 4 | Wonder Guard | Immune a tutto tranne super efficaci — richiede flag "tipo mossa" | Bassa |
| 5 | Overgrow/Blaze/Torrent/Swarm | Attivi solo sotto 1/3 HP — attualmente sempre attivi se selezionati | Bassa |
| 6 | `currentSpeAbility` deprecata | Variabile globale rimasta nel codice, non più usata | Bassa |
| 7 | `atkAbilityFx`/`defAbilityFx` | Calcolate in `calcDamage()` ma non usate — dead code | Bassa |
| 8 | `calc_stat_champions` Python/JS disallineate | Le due implementazioni usano convenzioni SP diverse — documentare o unificare | Media |

---

## 📅 Log Sessioni

| Data | Contenuto |
|------|-----------|
| 2026-05-02 | Setup Flask, DB, auth, sidebar base |
| 2026-05-03 | Tutti i template, Pokémon VGC, PC Builder + DxDiag |
| 2026-05-04 | Calcolatori VGC, 461 mosse, fix EV/IV, editor mosse/roster |
| 2026-05-07 | Sistema Regulation multi, refactor Blueprint, `extensions.py`, editor abilità |
| 2026-05-19 | Select abilità ATK/DEF calcolatore, select abilità Speed Tier, checkbox condizioni Speed, fix `calcDamage()` (moltiplicatori diretti, HH deduplicato), fix formula EV Champions (`e*2`) |
| 2026-06-09 | Generazione `PROJECT_CONTEXT.md` da lettura diretta del codice sorgente su GitHub |
