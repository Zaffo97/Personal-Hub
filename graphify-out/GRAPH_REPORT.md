# Graph Report - .  (2026-08-07)

## Corpus Check
- 53 files · ~83,996 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 353 nodes · 583 edges · 30 communities (22 shown, 8 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.87)
- Token cost: 355,569 input · 0 output

## Community Hubs (Navigation)
- Blueprint Flask e Route
- Backlog e Sistema Regulation
- Blueprint Pokemon ed Editor
- Calcolatore Danno JS
- Template UI e Tema
- Editor CRUD JavaScript
- Motore Abilita e Formula Stat
- API Regulation e PokeAPI
- Debito Tecnico e Storia Formule
- Risoluzione Nomi e Sprite
- Backlog Abilita e Manutenzione
- Script Patch Abilita Catalogo
- Pannello Reference
- Eliminazione Regulation
- Import File DxDiag
- Stampa 3D e Tinkercad
- Modale Aggiunta Abilita
- Modale Aggiunta Oggetti
- Modale Aggiunta Mosse
- Modifica Descrizione Mosse
- Rimozione Meccaniche
- Formattazione JSON Roster
- Cap SP Team Builder

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 43 edges
2. `get_db()` - 31 edges
3. `base.html layout template` - 20 edges
4. `_list_regulation_files()` - 13 edges
5. `calcDamage` - 11 edges
6. `updateStatPreview` - 11 edges
7. `team_edit()` - 10 edges
8. `calcolatori()` - 10 edges
9. `calcolatori.html (Calcolatori VGC, tutto inline)` - 10 edges
10. `_i()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `Formula stat legacy con floor(EV/4)` --semantically_similar_to--> `Formula Stat Champions (calc_stat_champions / calcSt)`  [INFERRED] [semantically similar]
  DOCUMENTAZIONE_PersonalHub.md → PROJECT_CONTEXT.md
- `Documentazione Completa Personal Hub v11.1a` --semantically_similar_to--> `Personal Hub (progetto Flask)`  [INFERRED] [semantically similar]
  DOCUMENTAZIONE_PersonalHub.md → PROJECT_CONTEXT.md
- `Collegamento API Steam per tracciare i videogiochi` --semantically_similar_to--> `Integrazione PokéAPI (sprite e stats)`  [INFERRED] [semantically similar]
  BACKLOG.md → PROJECT_CONTEXT.md
- `README-GitHub (vetrina pubblica del progetto)` --semantically_similar_to--> `README Personal Hub v11.1a`  [INFERRED] [semantically similar]
  README-GitHub.md → README.md
- `Avvio rapido (pip install -r requirements.txt; python app.py)` --semantically_similar_to--> `howtouse — istruzioni di avvio e credenziali`  [INFERRED] [semantically similar]
  README.md → howtouse.txt

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Flusso dati multi-regulation (registry, API, editor, team)** — project_context_multi_regulation_system, documentazione_personalhub_regulations_json, documentazione_personalhub_regulation_flow, project_context_regulation_id, backlog_pokedex_regulation, backlog_regulation_from_webapp [EXTRACTED 1.00]
- **Divergenza della formula stat Champions tra Python, JS e documentazione** — project_context_calc_stat_champions, documentazione_personalhub_stat_formula_legacy, backlog_stat_formula_inconsistency, project_context_ev_champions_rules, graphify_out_converted_nuove_implementazioni_c51d30f2_ev_cap_rule [INFERRED 0.95]
- **Debito tecnico del calcolatore VGC (JS inline, dead code, abilità e meteo)** — project_context_calcolatori_html, backlog_syntax_error_calcolatori, backlog_calcolatori_split, project_context_dead_js_globals, backlog_weather_ball, backlog_abilities_engine [INFERRED 0.85]
- **Motore abilita data-driven (lettura effect da abilities.json)** — templates_calcolatori_abilityeffect, templates_calcolatori_abilities_data, templates_calcolatori_effetti_sul_danno, templates_calcolatori_effetti_sulle_stat, templates_calcolatori_abilityincidesuldanno, templates_calcolatori_abilityincidesullestat, templates_calcolatori_moltiplicatorestat, templates_calcolatori_popolaselectabilita [EXTRACTED 1.00]
- **Flusso di calcolo del danno (tab Danno)** — templates_calcolatori_calcdamage, templates_calcolatori_calcst, templates_calcolatori_getnm, templates_calcolatori_stagemult, templates_calcolatori_tc, templates_calcolatori_abilityeffect, templates_calcolatori_formula_danno_gen9 [EXTRACTED 1.00]
- **Risoluzione nomi Pokemon (alias, mega, forme, cache)** — templates_calcolatori_fetchpkmn, templates_calcolatori_normalizename, templates_calcolatori_alias, templates_calcolatori_mega_data, templates_calcolatori_champions_bst, templates_calcolatori_pkcache, templates_calcolatori_checkformtoggle, templates_calcolatori_form_variants [INFERRED 0.85]
- **VGC JSON data editors (table UI + raw JSON textarea + POST save)** — templates_abilities_editor_template, templates_items_editor_template, templates_moves_editor_template, templates_roster_editor_template [INFERRED 0.85]
- **Regulation lifecycle: list, create, edit metadata, consume in team builder** — templates_regulations_list_template, templates_regulation_editor_template, templates_team_form_template, templates_regulation_editor_api_regulations_save_endpoint, templates_team_form_api_regulation_data_endpoint [EXTRACTED 1.00]
- **Shared hidden-div modal CRUD pattern (open/close + prefill + form submit)** — templates_arduino_openmodal, templates_pcbuilder_openbuildmodal, templates_items_editor_showaddmodal, templates_abilities_editor_showaddmodal, templates_moves_editor_showaddmodal [INFERRED 0.85]

## Communities (30 total, 8 thin omitted)

### Community 0 - "Blueprint Flask e Route"
Cohesion: 0.10
Nodes (33): create_app(), Personal Hub — entry point. Ogni area funzionale vive in blueprints/., arduino(), arduino_delete(), arduino_save(), route, login(), logout() (+25 more)

### Community 1 - "Backlog e Sistema Regulation"
Cohesion: 0.07
Nodes (37): Nessun .gitignore (hub.db e .pyc tracciati), Regulation Pokedex (DB completo di tutte le generazioni), Deploy da GitHub a Railway (errore da diagnosticare), Creare i JSON di una nuova regulation dalla web app, Speed Tier legato alla regulation attiva (loadRegSpeed), Risoluzione sprite mancanti (296/300, 0 rotti), Collegamento API Steam per tracciare i videogiochi, Mosse non trovate su PokéAPI (Bolt Tackle, Hi Jump Kick) (+29 more)

### Community 2 - "Blueprint Pokemon ed Editor"
Cohesion: 0.18
Nodes (36): abilities_editor(), api_abilities_delete(), api_abilities_list(), api_abilities_update(), api_regulations_create(), api_regulations_delete(), _build_full_roster(), calcolatori() (+28 more)

### Community 3 - "Calcolatore Danno JS"
Cohesion: 0.08
Nodes (36): Abilita -ate applicate prima di STAB e type chart, BS (base stats per side), calcDamage, checkFormToggle, enforceEVLimit, Limite EV 66 totali / 32 per campo, EV_TOTAL_MAX / EV_FIELD_MAX, fetchPkmn (+28 more)

### Community 4 - "Template UI e Tema"
Cohesion: 0.10
Nodes (21): Ability category taxonomy (weather_override, type_immunity, ...), closeModal() - arduino, closeSidebar(), base.html layout template, CSS theme token system (dark/light data-theme), toggleSidebar(), toggleTheme(), login.html (standalone, no base) (+13 more)

### Community 5 - "Editor CRUD JavaScript"
Cohesion: 0.08
Nodes (25): addAbility(), deleteAbility(name), formatJson() - abilities, renderTable() - abilities, saveDesc(name) - abilities, startEditDesc(name) - abilities, syncJson() - abilities, openModal(p) - arduino sketch editor (+17 more)

### Community 6 - "Motore Abilita e Formula Stat"
Cohesion: 0.10
Nodes (27): ABILITIES_DATA, abilityEffect, abilityIncideSulDanno, abilityIncideSulleStat, ALIAS (regional form name map), calcSt, CHAMPIONS_BST, clearStatB (+19 more)

### Community 7 - "API Regulation e PokeAPI"
Cohesion: 0.09
Nodes (21): fetchFromPokeAPI(), GET pokeapi.co/api/v2/move/<slug> (external), GET /pokemon/api/regulations, POST /pokemon/api/regulations/save, Regulation as a bundle of roster/moves/items JSON files, saveMeta() - read-modify-write of regulations list, showToast(msg, ok), addPkmn() (+13 more)

### Community 8 - "Debito Tecnico e Storia Formule"
Cohesion: 0.13
Nodes (19): Snellire calcolatori.html estraendo CSS/JS in static/, Catalogo con abilità incomplete (84/174 con una sola), Lycanroc assente da pokemon_catalog.json, Chiavi mega incoerenti nel catalogo (top-level vs forms), reference.html orfano (nessuna route lo renderizza), Formula stat incoerente (ev*2 vs floor(ev/4)), SyntaxError che azzerava tutto il JS di calcolatori.html, Formula stat legacy con floor(EV/4) (+11 more)

### Community 9 - "Risoluzione Nomi e Sprite"
Cohesion: 0.18
Nodes (17): api_moves(), api_pokemon(), api_regulation_data(), _build_slug(), _costruisci_indice(), _find_in_catalog(), _generate_alt_keys(), _normalize_key() (+9 more)

### Community 10 - "Backlog Abilita e Manutenzione"
Cohesion: 0.13
Nodes (17): ABILITIES_DATA a doppio encoding, Editor abilità unico /pokemon/abilita, Motore abilità data-driven (blocco effect di abilities.json), Nomi incoerenti in abilities.json (IT ufficiali vs altra fonte), BACKLOG Personal Hub, Formattazione editor mosse/oggetti/roster (banner fuori griglia), Funzione di salvataggio log, main diverge da origin/main (richiede force-push) (+9 more)

### Community 11 - "Script Patch Abilita Catalogo"
Cohesion: 0.67
Nodes (3): main(), patch_catalog(), Itera il catalogo e aggiunge le abilità alle forme che le mancano. Restituisce…

### Community 12 - "Pannello Reference"
Cohesion: 0.50
Nodes (4): closeRef, openRef, showRef, showRefSection

### Community 13 - "Eliminazione Regulation"
Cohesion: 0.50
Nodes (4): POST /pokemon/api/regulations/<id>/delete, confirmDelete(id, label), Delete guard: regulation with teams_count > 0 is not deletable, deleteRegulation()

### Community 14 - "Import File DxDiag"
Cohesion: 0.67
Nodes (3): handleDrop(e), loadFile(e), readFile(f)

## Ambiguous Edges - Review These
- `Schema SQLite creato da init_db()` → `extensions.py descritto come istanza SQLAlchemy`  [AMBIGUOUS]
  DOCUMENTAZIONE_PersonalHub.md · relation: conceptually_related_to
- `extensions.py descritto come istanza SQLAlchemy` → `Dipendenza flask>=3.0`  [AMBIGUOUS]
  requirements.txt · relation: conceptually_related_to

## Knowledge Gaps
- **76 isolated node(s):** `Stage Multipliers (stageMult)`, `Convenzioni ID HTML (atk_*, def_*, spe_*, mv_*, f_*, dmg_*)`, `login_required (auth session-based)`, `Variabili JS deprecate (currentSpeAbility, atkAbilityFx, defAbilityFx)`, `Editor abilità unico /pokemon/abilita` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Schema SQLite creato da init_db()` and `extensions.py descritto come istanza SQLAlchemy`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `extensions.py descritto come istanza SQLAlchemy` and `Dipendenza flask>=3.0`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `base.html layout template` connect `Template UI e Tema` to `API Regulation e PokeAPI`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `showMsg(msg, type)` connect `API Regulation e PokeAPI` to `Template UI e Tema`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `login_required()` connect `Blueprint Pokemon ed Editor` to `Blueprint Flask e Route`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `base.html layout template` (e.g. with `arduino.html` and `showMsg(msg, type)`) actually correct?**
  _`base.html layout template` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Stage Multipliers (stageMult)`, `Convenzioni ID HTML (atk_*, def_*, spe_*, mv_*, f_*, dmg_*)`, `login_required (auth session-based)` to the rest of the system?**
  _76 weakly-connected nodes found - possible documentation gaps or missing edges._