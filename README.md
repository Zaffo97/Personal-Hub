# 🚀 Personal Hub v11.1a

Dashboard personale Flask con autenticazione, struttura a blueprint e moduli separati per ogni sezione.

## Stack tecnico

- **Backend:** Python 3.10+ · Flask 3.x · SQLite (`hub.db`)
- **Architettura:** `app.py` con `create_app()` · `blueprints/` · `extensions.py`
- **Frontend:** Jinja2 · CSS custom · Vanilla JS
- **Dati:** JSON locali + PokéAPI

## Struttura progetto

```text
personal-hub-v2/
├── app.py
├── data.py
├── extensions.py
├── requirements.txt
├── hub.db
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

## Avvio rapido

```bash
pip install -r requirements.txt
python app.py
```

Apri poi [http://localhost:5000](http://localhost:5000).

Credenziali default attese:
- `admin`
- `admin123`

## Funzionalità

### 🎮 Gaming
- Libreria giochi con stato, piattaforma, genere e progressi.
- CRUD completo per i titoli.

### 🐉 Pokémon VGC
- Sistema **multi-regulation** con file JSON separati.
- Team builder con regulation dinamica.
- Editor regulation, roster, mosse e oggetti.
- Calcolatori VGC: danno, speed tier e stat preview.
- Integrazione PokéAPI per sprite e stats.

### 🔌 Arduino
- Gestione progetti, board, stato, link e codice.

### 🐍 Python
- Tracker argomenti con checklist e progresso.

### 🖥️ PC Builder
- Build multiple, componenti, prezzi e import DxDiag.

## Stato attuale del refactor

L'app attualmente **si avvia senza errori** dopo il passaggio da file monolitico a struttura modulare.

Sono però presenti alcuni placeholder temporanei nei blueprint per evitare errori di import finché non verranno ricollocati correttamente alcuni simboli legacy:
- `CHAMPIONS_BST = {}`
- `TYPE_TABLE_HTML = ""`
- `NATURE_TABLE_HTML = ""`

Questo significa che il bootstrap è stabile, ma la fase successiva è il test pagina per pagina delle route e dei template.

## Checklist consigliata post-avvio

Testare manualmente:
- `/login`
- `/`
- `/pokemon`
- `/pokemon/calcolatori`
- `/gaming`
- `/arduino`
- `/python`
- `/pcbuilder`

## Possibili problemi residui

Dopo il bootstrap, gli errori più probabili sono:
- `url_for(...)` non aggiornati nei template
- variabili mancanti in `render_template(...)`
- JS che punta ancora a route legacy
- costanti temporaneamente stub bate nei blueprint

## Sicurezza

- Imposta `SECRET_KEY` via variabile d'ambiente in produzione.
- Non esporre `hub.db` pubblicamente.
- Per HTTPS usa un reverse proxy come nginx o Caddy.

## Log sintetico

| Data | Versione | Contenuto |
|------|----------|-----------|
| 2026-05-07 | v10–v11 | Multi-regulation e editor dinamici |
| 2026-05-10 | v11.1a | Refactor a blueprint, app factory, bootstrap avviato correttamente |
