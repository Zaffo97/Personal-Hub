# 📘 Personal Hub — Documentazione Completa
> Ultima modifica: 07/08/2026 — v16.2
> Stato verificato eseguendo l'app, non solo leggendo il codice.
> Per il lavoro ancora aperto vedi `BACKLOG.md`; per i dettagli tecnici `PROJECT_CONTEXT.md`.

---

## 🗂️ Panoramica

**Personal Hub** è una web app Flask privata con autenticazione, organizzata in moduli Flask separati tramite blueprint. Centralizza strumenti per:
- Gestione squadre Pokémon VGC con sistema **multi-regulation**
- Libreria videogiochi
- Progetti Arduino
- Tracker Python
- Configuratore PC

| Stack | Dettaglio |
|-------|-----------|
| Backend | Python 3.10+ + Flask |
| Architettura | `app.py` con factory `create_app()` + `blueprints/` + `extensions.py` |
| Database | SQLite (`hub.db`) |
| Frontend | HTML/CSS/JS vanilla + Jinja2 |
| Dati esterni | PokéAPI (sprite e stats), roster/mosse/oggetti locali JSON |
| Auth | Session-based (login obbligatorio sulle route protette) |

---

## 🧱 Stato architettura attuale

Il progetto è stato **refactorato** da file monolitico a struttura modulare con blueprint, e l'app attualmente si avvia senza errori.

### Struttura logica attesa

```text
personal-hub-v2/
├── app.py
├── data.py
├── extensions.py
├── hub.db
├── requirements.txt
├── BACKLOG.md               # lavoro aperto (fonte: Nuove implementazioni.docx)
├── PROJECT_CONTEXT.md       # dettagli tecnici e convenzioni
├── blueprints/
│   ├── auth.py
│   ├── dashboard.py         # (non "main.py")
│   ├── gaming.py
│   ├── pokemon.py
│   ├── api_pokemon.py
│   ├── arduino.py
│   ├── python_tracker.py
│   └── pcbuilder.py
├── data/
│   ├── regulations.json
│   ├── pokemon_catalog.json # 174 Pokemon + 84 forme annidate in `forms`
│   ├── abilities.json       # 408 abilita IT, 56 con blocco `effect`
│   ├── roster_ma.json · moves_ma.json · items_ma.json
│   └── archive/             # backup roster/mosse per regulation
├── scripts/                 # manutenzione dati (non parte del server)
│   ├── fix_pokemon_catalog.py
│   ├── patch_catalog_abilities.py
│   └── patch_abilities_effects.py
└── templates/               # 18 template
    ├── base.html · login.html · dashboard.html
    ├── gaming.html · game_form.html
    ├── pokemon.html · team_form.html · calcolatori.html
    ├── regulations_list.html · regulation_editor.html
    ├── moves_editor.html · roster_editor.html · items_editor.html
    ├── abilities_editor.html
    ├── arduino.html · python.html · pcbuilder.html
    └── reference.html       # orfano: nessuna route lo renderizza
```

> Non esiste una cartella `static/`: CSS e JS sono inline nei template. `calcolatori.html` da solo pesa ~200 KB.

### Refactor completato

Gli shim temporanei di bootstrap (`CHAMPIONS_BST = {}`, `TYPE_TABLE_HTML`, `NATURE_TABLE_HTML`) **non esistono più**: rimossi il 07/08/2026.

- `CHAMPIONS_BST` è popolato per davvero da `data.py`, che carica **174 Pokémon** da `data/pokemon_catalog.json`
- `TYPE_TABLE_HTML` e `NATURE_TABLE_HTML` erano stringhe vuote passate a un template che non le usava: eliminate insieme ai parametri `type_table` / `nature_table`
- Le tabelle tipi e nature sono ora inline nel tab **Reference** di `calcolatori.html`

> ⚠️ `templates/reference.html` esiste ma è **orfano**: nessuna route lo renderizza.

---

## 🗃️ Database — Tabelle SQLite

| Tabella | Colonne principali | Descrizione |
|---------|--------------------|-------------|
| `users` | id, username, password, display_name, role | Account utenti |
| `games` | id, title, platform, genre, status, hours_hltb, cover_url, prog_story/side/collect, date_start/end | Libreria giochi |
| `teams` | id, name, format, record, description, notes, `regulation_id` | Team Pokémon |
| `team_members` | id, team_id, slot, pokemon, mega_stone, nature, ability, held_item, tera_type, move1-4, EV per stat, sprite_url | Slot dei team |
| `arduino_projects` | id, name, board, status, tinkercad_url, code, description | Progetti Arduino |
| `python_topics` | id, category, name, done | Argomenti Python |
| `pc_builds` | id, name, notes | Build PC |
| `pc_components` | id, build_id, category, name, price, notes | Componenti build |

> `teams.regulation_id` collega ogni team alla regulation definita in `data/regulations.json`.

---

## 🗂️ Sistema Regulation

### `data/regulations.json`
Registro centrale di tutte le regulation disponibili.

```json
[
  {
    "id": "ma",
    "label": "Regulation MA",
    "mechanics": ["mega"],
    "roster_file": "roster_ma.json",
    "moves_file": "moves_ma.json",
    "items_file": "items_ma.json"
  }
]
```

| Campo | Descrizione |
|-------|-------------|
| `id` | Identificatore univoco (`ma`, `mb`, ecc.) |
| `label` | Nome mostrato nell'interfaccia |
| `mechanics` | Meccaniche abilitate (`mega`, `tera`, `zmove`, `dynamax`) |
| `roster_file` | File roster nella cartella `data/` |
| `moves_file` | File mosse |
| `items_file` | File oggetti |

### Flusso dinamico nel Team Builder
1. L'utente seleziona la regulation nel form team.
2. Il frontend chiama `/api/regulation/<id>/data`.
3. L'API restituisce `roster`, `moves`, `items` e `mechanics`.
4. Il form aggiorna select Pokémon, mosse, oggetti e opzioni meccaniche.
5. Al salvataggio, `regulation_id` viene scritto nella tabella `teams`.

### Creare una nuova regulation
1. Vai su `/pokemon/regulations`.
2. Clicca **+ Nuova Regulation**.
3. Inserisci ID, label e meccaniche.
4. Il sistema crea i file JSON vuoti associati.
5. La nuova regulation viene aggiunta a `regulations.json`.
6. Redirect verso l'editor dedicato.

---

## 🗺️ Mappa delle route

### 🔐 Auth
| URL | Metodi | Funzione | Descrizione |
|-----|--------|----------|-------------|
| `/login` | GET, POST | `login()` | Form login |
| `/logout` | GET | `logout()` | Logout utente |

### 🏠 Dashboard
| URL | Metodi | Funzione | Descrizione |
|-----|--------|----------|-------------|
| `/` | GET | `dashboard()` | Home con statistiche |
| `/export` | GET | `export_data()` | Export dati JSON |

### 🎮 Gaming
| URL | Metodi | Funzione | Descrizione |
|-----|--------|----------|-------------|
| `/gaming` | GET | `gaming()` | Libreria giochi |
| `/gaming/new` | GET, POST | `game_new()` | Nuovo gioco |
| `/gaming/<id>/edit` | GET, POST | `game_edit()` | Modifica gioco |
| `/gaming/<id>/delete` | POST | `game_delete()` | Elimina gioco |

### 🐾 Pokémon
| URL | Metodi | Funzione | Descrizione |
|-----|--------|----------|-------------|
| `/pokemon` | GET | `pokemon()` | Lista team VGC |
| `/pokemon/team/new` | GET, POST | `team_new()` | Nuovo team |
| `/pokemon/team/<id>/edit` | GET, POST | `team_edit()` | Modifica team |
| `/pokemon/team/<id>/delete` | POST | `team_delete()` | Elimina team |
| `/pokemon/calcolatori` | GET | `calcolatori()` | Calcolatori VGC |
| `/pokemon/regulations` | GET | `regulations_list()` | Elenco regulation |
| `/pokemon/regulation/<id>` | GET | `regulation_editor()` | Editor regulation |
| `/pokemon/roster` | GET, POST | `roster_editor()` | Editor roster |
| `/pokemon/mosse` | GET, POST | `moves_editor()` | Editor mosse |
| `/pokemon/oggetti` | GET, POST | `items_editor()` | Editor oggetti |
| `/pokemon/abilita` | GET, POST | `abilities_editor()` | Editor abilità — **`abilita`, non `abilities`** |

### 🔌 API
| URL | Metodi | Descrizione |
|-----|--------|-------------|
| `/api/pokemon/<path:name>` | GET | Stats, tipi, abilità e sprite **dal catalogo locale** |
| `/api/regulation/<id>/data` | GET | Roster della regulation |
| `/api/moves` | GET | Mosse Reg. M-A |
| `/pokemon/api/abilities` | GET | Elenco abilità |
| `/pokemon/api/abilities/update` · `/delete` | POST | Modifica / elimina abilità |
| `/pokemon/api/regulations/create` | POST | Crea regulation |
| `/pokemon/api/regulations/<id>/delete` | POST | Elimina regulation |

> ⚠️ **Non esistono** (erano documentate ma mai implementate): `/api/team/<id>`, `/api/stat_champions`, `/api/regulations`, `/api/regulations/save`.
> Nota: `/api/pokemon/<name>` **non chiama PokéAPI a runtime** — legge solo `pokemon_catalog.json`. Gli URL degli sprite puntano a pokemondb.

### 🤖 Arduino
| URL | Metodi | Funzione | Descrizione |
|-----|--------|----------|-------------|
| `/arduino` | GET | `arduino()` | Lista progetti |
| `/arduino/save` | POST | `arduino_save()` | Salva progetto |
| `/arduino/<id>/delete` | POST | `arduino_delete()` | Elimina progetto |

### 🐍 Python
| URL | Metodi | Funzione | Descrizione |
|-----|--------|----------|-------------|
| `/python` | GET | `python_tracker()` | Tracker Python |
| `/python/toggle/<id>` | POST | `python_toggle()` | Toggle completato |

### 💻 PC Builder
| URL | Metodi | Funzione | Descrizione |
|-----|--------|----------|-------------|
| `/pcbuilder` | GET | `pcbuilder()` | Lista build |
| `/pcbuilder/save` | POST | `pcbuilder_save()` | Salva build |
| `/pcbuilder/<id>/delete` | POST | `pcbuilder_delete()` | Elimina build |
| `/pcbuilder/import_dxdiag` | POST | `import_dxdiag()` | Import DxDiag |

---

## 🧩 Moduli principali

### `app.py`
Responsabile della creazione applicazione Flask tramite `create_app()`, registrazione blueprint e bootstrap generale.

### `extensions.py`
**Nessun ORM: `sqlite3` grezzo.** Non c'è SQLAlchemy nel progetto — `requirements.txt` elenca solo `flask`.

Espone `get_db()` (connessione con `row_factory = sqlite3.Row` e foreign keys ON), `init_db()` (crea le tabelle e l'utente di default `admin` / `admin123`), il decorator `login_required` e gli helper numerici `_i()` / `_f()`.

### `blueprints/`
- `auth.py` · `dashboard.py` (**non** `main.py`) · `gaming.py` · `pokemon.py` · `api_pokemon.py` · `arduino.py` · `python_tracker.py` · `pcbuilder.py`

### `data.py`
Costanti e mapping statici: `CHAMPIONS_BST` (174 Pokémon dal catalogo), `NATURES`, `NATURE_EFFECTS`, `SLUG_OVERRIDES`, `REG_MA_ROSTER`, `MEGA_EVOLUTIONS_MA`.

> `ABILITIES_CALC` esiste ancora in `data.py` ma **non è più usata**: le abilità del calcolatore vengono da `data/abilities.json`.

### `data/`
Contiene i JSON dinamici delle regulation.

---

## 🧠 Calcolatori VGC

La pagina `/pokemon/calcolatori` include **quattro** tab: **Danno**, **Speed Tier**, **Stat Preview** e **Reference** (tabelle tipi e nature).

### Regole SP Champions (Reg. M-A)
- Max **32 SP** per singola stat, max **66 SP** totali (`EV_FIELD_MAX` / `EV_TOTAL_MAX`)
- IV fissi a 31, livello fisso 50

### Formula stat
Ogni SP vale **+2** — è la convenzione Champions, **non** gli EV standard 0-252:

**HP:** `floor((2×base + 31 + SP×2) × lvl/100) + lvl + 10`
**Altre:** `floor((floor((2×base + 31 + SP×2) × lvl/100) + 5) × natura)`

> ⚠️ La versione precedente di questo documento riportava `floor(EV/4)`. È la formula standard, **incompatibile col cap a 32 SP**: dava +4 invece di +32 a investimento pieno. Corretta nel codice e qui il 07/08/2026.

### Motore abilità
Le abilità **non** sono hardcoded: `calcDamage()`, `updateSpeed()` e `updateStatPreview()` leggono il blocco `effect` di `data/abilities.json` tramite `abilityEffect(nome)`.

- 408 abilità nelle tendine (nomi **in italiano**, come l'interfaccia), **56 con un effetto reale**
- Il pallino ● marca quelle che incidono sul calcolo del tab corrente; le altre restano selezionabili come informazione
- **Aggiungere un'abilità = modificare il JSON, zero codice.** Lo script `scripts/patch_abilities_effects.py` (con `--dry-run` e backup) aiuta a completare i blocchi `effect`

Tipi di effetto supportati: `ate`, `tough_claws`, `wonder_guard`, `overgrow`, `filter`, `fluffy`, `thick_fat`, `multiscale`, `marvel_scale`, `fur_coat`, `technician`, `sheer_force`, `tinted_lens`, `purifying_salt`, `stab_multiplier`, `guts`, `stat_mult`, `spread_boost`, `type_boost_weather`, `weather_def_boost`, `weather_spdef_boost`, `immunity`, `absorb`, `speed_weather`, `speed_status`.

> ⚠️ I nomi in `abilities.json` sono in italiano ma **non sempre quelli ufficiali**: `Magidifesa` è Wonder Guard, mentre `Spettroguardia` descrive in realtà Multiscaglia. Quando cerchi un'abilità, **fidati della descrizione, non del nome**.

---

## 📝 Note operative

### Come verificare una modifica ai template

L'app che **si avvia** non significa che le pagine **funzionino**: un `SyntaxError` in un blocco `<script>` inline non produce nessun errore server-side, ma azzera tutto il JavaScript di quella pagina. È successo due volte in questo progetto (`calcolatori.html` e `pcbuilder.html`), in entrambi i casi per mesi senza accorgersene.

Controllo consigliato dopo ogni modifica: renderizzare la pagina col test client, estrarre i blocchi `<script>` inline ed eseguire `new vm.Script()` su ciascuno. Individua il problema in pochi secondi.

> Attenzione ai falsi positivi: i blocchi `<script type="application/json">` (es. `items-data` in `items_editor.html`) contengono dati, non codice, e non vanno passati al parser JS.

Per i calcolatori vale in più la regola #8 di `PROJECT_CONTEXT.md`: ogni modifica va provata con un **caso noto** e confrontata con un valore calcolato a mano.

### Stato delle pagine
Tutte verificate il 07/08/2026: `/`, `/login`, `/pokemon`, `/pokemon/calcolatori`, `/pokemon/mosse`, `/pokemon/oggetti`, `/pokemon/roster`, `/pokemon/abilita`, `/pokemon/regulations`, `/pokemon/team/new`, `/gaming`, `/arduino`, `/python`, `/pcbuilder` — tutte 200, 18/18 template compilano, tutti i blocchi JS parsano.

### Obiettivo successivo
Vedi `BACKLOG.md`. La voce più grossa è il **DB Pokedex completo** (tutti i Pokémon, mosse, abilità e oggetti di ogni generazione come regulation dedicata): abiliterebbe l'obiettivo di fondo, cioè aggiungere una regulation **senza IA, solo dall'interfaccia**, e risolverebbe da sola sia il buco Lycanroc sia le abilità incomplete nel catalogo.

---

## 🗓️ Log sessioni

| Data | Versione | Contenuto |
|------|----------|-----------|
| 2026-05-02 | v1 | Setup Flask, DB, autenticazione, sidebar |
| 2026-05-03 | v2 | Tutti i template, Pokémon VGC, PC Builder + DxDiag |
| 2026-05-04 | v3–v9 | Calcolatori VGC completi, 461 mosse, fix EV/IV, editor mosse/roster |
| 2026-05-07 | v10–v11 | Sistema Regulation multi, `regulations.json`, editor regulation, API regulation-aware |
| 2026-05-10 | v11.1a | Refactor in blueprint, `app.py` con app factory, avvio riuscito con shim temporanei per import mancanti |
| 2026-08-07 | v16.2 | Corretto il `SyntaxError` che azzerava tutto il JS di `calcolatori.html`; formule stat allineate su `SP×2`; motore abilità data-driven da `abilities.json`; risolti i problemi noti 1-8; tendina abilità nello Stat Preview; pulizia dead code (−100 KB); sprite Mega e forme regionali (0 rotti su 296); layout dei tre editor; 5 bug trovati via grafo graphify e corretti, incluso il `SyntaxError` del PC Builder; shim di bootstrap eliminati; documentazione riallineata al codice |
