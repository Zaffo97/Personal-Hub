# 📘 Personal Hub — Documentazione Completa
> Ultima modifica: 10/05/2026 — v11.1a

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
├── blueprints/
│   ├── auth.py
│   ├── main.py
│   ├── gaming.py
│   ├── pokemon.py
│   ├── api_pokemon.py
│   ├── arduino.py
│   ├── python_tracker.py
│   └── pcbuilder.py
├── data/
│   ├── regulations.json
│   ├── roster_ma.json
│   ├── moves_ma.json
│   ├── items_ma.json
│   └── roster_<id>.json / moves_<id>.json / items_<id>.json
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── gaming.html
    ├── game_form.html
    ├── pokemon.html
    ├── team_form.html
    ├── calcolatori.html
    ├── regulations_list.html
    ├── regulation_editor.html
    ├── moves_editor.html
    ├── roster_editor.html
    ├── items_editor.html
    ├── arduino.html
    ├── python.html
    ├── pcbuilder.html
    └── reference.html
```

### Note importanti sul refactor

Durante l'avvio del refactor sono emerse differenze tra il `data.py` reale e quello ipotizzato dalla documentazione precedente. Per consentire il boot immediato dell'app, sono stati temporaneamente neutralizzati alcuni import nei blueprint.

#### Shim temporanei usati per l'avvio
- `CHAMPIONS_BST = {}` nei blueprint Pokémon/API
- `TYPE_TABLE_HTML = ""`
- `NATURE_TABLE_HTML = ""`

Questi placeholder servono solo a evitare `ImportError` in fase di bootstrap. Quando il refactor sarà stabilizzato, conviene ripristinare questi oggetti nella loro posizione definitiva (`data.py` oppure modulo dedicato).

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

### 🔌 API Pokémon
| URL | Metodi | Descrizione |
|-----|--------|-------------|
| `/api/pokemon/<name>` | GET | Stats + sprite da PokéAPI/locali |
| `/api/team/<id>` | GET | Dati team JSON |
| `/api/stat_champions` | GET | Champions stats JSON |
| `/api/moves` | GET | Mosse legacy Reg. M-A |
| `/api/regulations` | GET | Elenco regulation |
| `/api/regulation/<id>/data` | GET | Dati completi regulation |
| `/api/regulations/save` | POST | Salva `regulations.json` |
| `/api/regulations/create` | POST | Crea regulation |
| `/api/regulations/<id>/delete` | POST | Elimina regulation |

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
Contiene le estensioni condivise, in particolare l'istanza `db = SQLAlchemy()` inizializzata tramite app factory.

### `blueprints/`
Ogni area funzionale è stata estratta in un modulo dedicato:
- `auth.py`
- `main.py`
- `gaming.py`
- `pokemon.py`
- `api_pokemon.py`
- `arduino.py`
- `python_tracker.py`
- `pcbuilder.py`

### `data.py`
Modulo per costanti e mapping statici del progetto. Al momento non contiene ancora tutti i simboli che la documentazione legacy attribuiva al file, per questo alcuni valori sono stati temporaneamente sostituiti nei blueprint.

### `data/`
Contiene i JSON dinamici delle regulation.

---

## 🧠 Calcolatori VGC

La pagina `/pokemon/calcolatori` include tre aree principali:
- **Danno**
- **Speed Tier**
- **Stat Preview**

### Regole EV Champions (Reg. M-A)
- Max 32 EV per singola stat
- Max 66 EV totali
- IV fissi a 31
- Livello fisso 50

### Formula stat
**HP:** `floor((2×base + 31 + floor(EV/4)) × lvl/100) + lvl + 10`

**Altre stat:** `floor((floor((2×base + 31 + floor(EV/4)) × lvl/100) + 5) × natura)`

---

## 📝 Note operative attuali

### Priorità post-avvio
Ora che l'app si avvia, il prossimo controllo consigliato è testare in browser queste pagine:
- `/login`
- `/`
- `/pokemon`
- `/pokemon/calcolatori`
- `/gaming`
- `/arduino`
- `/python`
- `/pcbuilder`

### Cosa aspettarsi nei prossimi bug
I problemi residui più probabili dopo il refactor non sono più di bootstrap, ma di integrazione:
- `url_for(...)` nei template
- variabili mancanti passate a Jinja
- endpoint JS che puntano ancora ai vecchi nomi
- import temporanei da ripulire

### Obiettivo successivo
Stabilizzare i blueprint eliminando gli shim temporanei e ricollocando in modo definitivo:
- `CHAMPIONS_BST`
- `TYPE_TABLE_HTML`
- `NATURE_TABLE_HTML`

---

## 🗓️ Log sessioni

| Data | Versione | Contenuto |
|------|----------|-----------|
| 2026-05-02 | v1 | Setup Flask, DB, autenticazione, sidebar |
| 2026-05-03 | v2 | Tutti i template, Pokémon VGC, PC Builder + DxDiag |
| 2026-05-04 | v3–v9 | Calcolatori VGC completi, 461 mosse, fix EV/IV, editor mosse/roster |
| 2026-05-07 | v10–v11 | Sistema Regulation multi, `regulations.json`, editor regulation, API regulation-aware |
| 2026-05-10 | v11.1a | Refactor in blueprint, `app.py` con app factory, avvio riuscito con shim temporanei per import mancanti |
