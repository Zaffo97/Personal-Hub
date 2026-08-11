# Graph Report - .  (2026-08-10)

## Corpus Check
- 74 files · ~200,849 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 442 nodes · 797 edges · 32 communities (23 shown, 9 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 1% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.83)
- Token cost: 160,891 input · 0 output

## Community Hubs (Navigation)
- Pokemon Routes & Catalog API
- Flask App & Blueprints
- Backlog & Design Decisions
- Regulation & Mega Data Fixes
- Abilities Engine & UI State
- Calculator Data Tables
- Calculator Core Engine
- Damage & Stat Calculators
- Pokemon API & Name Slugs
- Catalog Build Pipeline
- Template Inline Script Safety
- Champions Roster Wiki Import
- Reference Tables UI
- Regulation API & Mechanic Slots
- README & Setup Docs
- Speed Calculator
- Regulation Migration Script
- Catalog Abilities Patch
- Damage Modifier Rules
- Dashboard & Python Tracker
- PC Builder Components
- Steam API Key Handling
- Arduino Project Modal
- Template extra_head Block
- Reference & Team Builder Templates
- Session Start Prompt
- Sidebar Toggle
- Standalone Login Page
- EV/SP Cap Enforcement

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 63 edges
2. `get_db()` - 35 edges
3. `_list_regulation_files()` - 19 edges
4. `base.html - layout globale (sidebar, topbar, flash)` - 15 edges
5. `_load_filtro()` - 14 edges
6. `calcolatori()` - 11 edges
7. `_load_roster()` - 10 edges
8. `team_edit()` - 10 edges
9. `_i()` - 10 edges
10. `steam_libreria()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `README-GitHub (vetrina pubblica del progetto)` --semantically_similar_to--> `README Personal Hub v11.1a`  [INFERRED] [semantically similar]
  README-GitHub.md → README.md
- `Avvio rapido (pip install -r requirements.txt; python app.py)` --semantically_similar_to--> `howtouse — istruzioni di avvio e credenziali`  [INFERRED] [semantically similar]
  README.md → howtouse.txt
- `MEGA_DATA come fonte di verita delle Mega` --semantically_similar_to--> `TYPE_CHART e l'unica type chart del progetto`  [INFERRED] [semantically similar]
  BACKLOG.md → PROJECT_CONTEXT.md
- `Procedura di creazione di una nuova regulation` --conceptually_related_to--> `Catalogo unico + regulation come filtro`  [AMBIGUOUS]
  DOCUMENTAZIONE_PersonalHub.md → BACKLOG.md
- `Import roster Champions dai suffissi dello sprite` --semantically_similar_to--> `SLUG_OVERRIDES per le forme speciali PokeAPI`  [INFERRED] [semantically similar]
  BACKLOG.md → PROJECT_CONTEXT.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pattern: dati Flask iniettati con <script type=application/json>** — templates_calcolatori_calc_bootstrap, templates_items_editor_items_data_block, templates_regulation_content_page, templates_catalog_editor_page, project_context_bootstrap_json_calcolatori [INFERRED 0.95]
- **Flusso archivio / ripristino / copia automatica dei quattro editor** — templates_abilities_editor_loadabilityarchives, templates_roster_editor_loadarchives, templates_catalog_editor_caricaarchivi, backlog_archivio_pre_salvataggio, project_context_salva_catalogo_protezione [INFERRED 0.95]
- **Modello catalogo unico + regulation come filtro** — backlog_catalogo_unico_regulation_filtro, templates_catalog_editor_page, templates_regulation_content_page, templates_regulation_editor_copiada, templates_regulations_list_createregulation, backlog_api_moves_reg_bug [INFERRED 0.95]

## Communities (32 total, 9 thin omitted)

### Community 0 - "Pokemon Routes & Catalog API"
Cohesion: 0.07
Nodes (75): abilities_archive(), abilities_archives(), abilities_editor(), abilities_restore(), api_abilities_delete(), api_abilities_list(), api_abilities_update(), api_catalogo_elimina() (+67 more)

### Community 1 - "Flask App & Blueprints"
Cohesion: 0.08
Nodes (55): create_app(), Personal Hub — entry point. Ogni area funzionale vive in blueprints/., arduino(), arduino_delete(), arduino_save(), route, login(), logout() (+47 more)

### Community 2 - "Backlog & Design Decisions"
Cohesion: 0.06
Nodes (47): calcolatori.html spacchettato in moduli static/js, Catalogo unico + regulation come filtro, Clonazione di una regulation, Editor del catalogo separato (/pokemon/catalogo), PC Builder: wishlist, prezzi e compatibilita fra pezzi, Piano di riconversione delle 95 Mega, Schermata contenuti della regulation, Nuova sezione Stampa 3D sul modello di Arduino (+39 more)

### Community 3 - "Regulation & Mega Data Fixes"
Cohesion: 0.06
Nodes (37): /api/moves ignorava la regulation, Chiavi mega incoerenti nel catalogo, Import roster Champions dai suffissi dello sprite, loadRegSpeed leggeva bst.spe invece di base_stats.spe, MEGA_DATA come fonte di verita delle Mega, mega_map delle regulation, Mega col calcolo Lv.50 salvato in base_stats, reference.html e orfano: nessuna route lo renderizza (+29 more)

### Community 4 - "Abilities Engine & UI State"
Cohesion: 0.09
Nodes (26): hours_played distinta da hours_hltb, Motore meteo del calcolatore, Switch lingua italiano/inglese per tutta la web app, Tipi di effetto abilita supportati, Motore abilita data-driven da abilities.json, I nomi in abilities.json non sono sempre quelli ufficiali, Divieto di localStorage/sessionStorage (regola #9), addAbility (+18 more)

### Community 5 - "Calculator Data Tables"
Cohesion: 0.09
Nodes (22): ALIAS, BS, CALC_BOOTSTRAP, FORM_BASE, FORM_VARIANTS, MEGA_DATA, METEO_LABEL, MOSSE_METEO (+14 more)

### Community 6 - "Calculator Core Engine"
Cohesion: 0.17
Nodes (14): abilityEffect(), abilityIncideSulDanno(), abilityIncideSulleStat(), aggiornaNotaMeteo(), applicaMeteoAllaMossa(), catalogEntry(), catalogIndex(), EFFETTI_SUL_DANNO (+6 more)

### Community 7 - "Damage & Stat Calculators"
Cohesion: 0.14
Nodes (12): tipoIT(), loadSide(), loadTimers, recalcSide(), STAT_KEYS, clearStatB(), loadStatPkmn(), onFormChange() (+4 more)

### Community 8 - "Pokemon API & Name Slugs"
Cohesion: 0.16
Nodes (18): api_moves(), api_pokemon(), api_regulation_data(), _build_slug(), _costruisci_indice(), _find_in_catalog(), _generate_alt_keys(), _normalize_key() (+10 more)

### Community 9 - "Catalog Build Pipeline"
Cohesion: 0.26
Nodes (15): carica_json(), costruisci_abilita(), costruisci_mosse(), costruisci_oggetti(), costruisci_pokemon(), leggi(), main(), nome_forma() (+7 more)

### Community 10 - "Template Inline Script Safety"
Cohesion: 0.20
Nodes (12): Copia di sicurezza automatica prima di ogni salvataggio, SyntaxError negli handler inline generati da JS, Ripristino roster senza conferma (onsubmit rotto), Verifica dei template eseguendo i blocchi inline con vm.Script, Dati Flask da un solo blocco application/json, loadAbilityArchives, blocco calc-bootstrap (application/json), caricaArchivi (catalogo) (+4 more)

### Community 11 - "Champions Roster Wiki Import"
Cohesion: 0.23
Nodes (7): HTMLParser, carica(), leggi_csv(), main(), Estrae dalle tabelle: numero dex, nome, tipi e file dello sprite., scarica_elenco(), TabellaWiki

### Community 12 - "Reference Tables UI"
Cohesion: 0.33
Nodes (9): abbrTipo(), EFF_CELLA, htmlTabellaNature(), htmlTabellaTipi(), openRef(), preparaTabelleRiferimento(), riempiUnaVolta(), showRef() (+1 more)

### Community 13 - "Regulation API & Mechanic Slots"
Cohesion: 0.20
Nodes (10): GET /api/pokemon/<name>, GET /api/regulation/<id>/data, GET /api/regulations, Regulation-driven dynamic mechanic slot (mega/tera), fetchPkmn(slot) - debounced sprite/ability/move lookup, initRegulations(), loadRegulationData(), onPokemonChange(slot) (+2 more)

### Community 14 - "README & Setup Docs"
Cohesion: 0.22
Nodes (9): howtouse — istruzioni di avvio e credenziali, Obiettivo: accesso fuori dal PC e a PC spento, Autore e link placeholder ([Tuo Nome], tuonome), README-GitHub (vetrina pubblica del progetto), README Personal Hub v11.1a, Checklist post-avvio delle route da testare, Avvio rapido (pip install -r requirements.txt; python app.py), Note di sicurezza (SECRET_KEY da env, hub.db non esposto, reverse proxy) (+1 more)

### Community 15 - "Speed Calculator"
Cohesion: 0.60
Nodes (3): loadRegSpeed(), renderSpeed(), updateSpeed()

### Community 16 - "Regulation Migration Script"
Cohesion: 0.83
Nodes (3): carica(), main(), scrivi()

### Community 17 - "Catalog Abilities Patch"
Cohesion: 0.67
Nodes (3): main(), patch_catalog(), Itera il catalogo e aggiunge le abilità alle forme che le mancano. Restituisce…

### Community 18 - "Damage Modifier Rules"
Cohesion: 0.67
Nodes (3): Il critico ignora gli stage sfavorevoli all'attaccante, SCHERMO_DOPPIE: Reflect/Light Screen al valore delle doppie, Stage multipliers (stageMult)

### Community 20 - "PC Builder Components"
Cohesion: 0.67
Nodes (3): addRow (componente build), parseDx (import DxDiag), useDxComponents

## Ambiguous Edges - Review These
- `Catalogo unico + regulation come filtro` → `Procedura di creazione di una nuova regulation`  [AMBIGUOUS]
  DOCUMENTAZIONE_PersonalHub.md · relation: conceptually_related_to
- `calcolatori.html spacchettato in moduli static/js` → `Doc stale: nessuna cartella static/, CSS e JS inline nei template`  [AMBIGUOUS]
  DOCUMENTAZIONE_PersonalHub.md · relation: conceptually_related_to
- `Divieto di localStorage/sessionStorage (regola #9)` → `toggleTheme`  [AMBIGUOUS]
  templates/base.html · relation: references
- `API documentate ma mai implementate` → `fetchFromPokeAPI`  [AMBIGUOUS]
  templates/moves_editor.html · relation: conceptually_related_to
- `API documentate ma mai implementate` → `saveMeta`  [AMBIGUOUS]
  templates/regulation_editor.html · relation: references
- `Doc stale: nessuna cartella static/, CSS e JS inline nei template` → `calcolatori.html - calcolatori VGC (solo HTML)`  [AMBIGUOUS]
  DOCUMENTAZIONE_PersonalHub.md · relation: references

## Knowledge Gaps
- **68 isolated node(s):** `loadTimers`, `CALC_BOOTSTRAP`, `TYPE_EN_TO_IT`, `NM`, `TIPI_IT` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Catalogo unico + regulation come filtro` and `Procedura di creazione di una nuova regulation`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `calcolatori.html spacchettato in moduli static/js` and `Doc stale: nessuna cartella static/, CSS e JS inline nei template`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Divieto di localStorage/sessionStorage (regola #9)` and `toggleTheme`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `API documentate ma mai implementate` and `fetchFromPokeAPI`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `API documentate ma mai implementate` and `saveMeta`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Doc stale: nessuna cartella static/, CSS e JS inline nei template` and `calcolatori.html - calcolatori VGC (solo HTML)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `login_required()` connect `Flask App & Blueprints` to `Pokemon Routes & Catalog API`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._