# Graph Report - .  (2026-09-14)

## Corpus Check
- 69 files · ~894,395 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1029 nodes · 2005 edges · 89 communities (76 shown, 13 thin omitted)
- Extraction: 93% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 127 edges (avg confidence: 0.86)
- Token cost: 372,457 input · 0 output

## Community Hubs (Navigation)
- API Pokémon e loader
- Salvataggio e validazione catalogo
- Dump PokéAPI ed evoluzioni
- Shell, utenti e sezioni
- Gaming con proprietario
- Editor e bachi storici
- Admin e permessi
- Calendario uscite Gaming
- Trappole dati e cache
- Login e password
- Motore abilità calcolatore
- Avvio app e helper
- Costanti calcolatore
- Voci aperte del backlog
- Arduino e API team
- Build catalogo dal dump
- Dashboard, team ed export
- Nomi da PokéAPI
- Stat Preview e forme
- Editor oggetti e regulation
- Proprietà dati e online
- Controllo proprietario query
- Editor abilità e mosse
- Prova ripristino dati
- Tab Danno e oggetti
- Tab calcolatore e categorie
- Regulation come filtro
- Import roster Champions
- Import moveset specie
- Tabelle di riferimento
- Prove catalogo e import
- Contenuti regulation e Steam
- Regola #8 e formule
- Sezioni Arduino e Gaming
- Integrazione Steam
- Base template ed editor
- Client IGDB
- Bootstrap e tab calcolatore
- Categorie oggetti e abilità
- Traduzioni IT/EN
- Sweep e verifiche
- Editor mosse e roster
- Controllo esposizione
- README e avvio
- Sonda IGDB
- Speed Tier
- Editor catalogo
- Legame Pokémon-abilità
- Mega e tabelle storiche
- Regulation MA e mega_map
- Prova build catalogo
- Form Gaming e Python
- Flusso regulation editor
- Export dati
- Tag roster e mega map
- Meta regulation editor
- Moduli JS calcolatore
- Motore meteo e abilità
- Fusione abilità doppie
- Fusione doppioni nome
- Migrazione regulation
- Patch abilità catalogo
- Prova regulation nuova
- Stage e schermi
- Panoramica progetto
- Tema chiaro/scuro
- Import DxDiag PC
- Chiave Steam
- Report descrizioni mosse
- Elenco regulation
- Editor catalogo separato
- Voci PC Builder
- Hook before_request
- Prompt di sessione
- Bootstrap dati Flask
- Prefissi ID
- Tab Reference
- Pagina login
- JSON grezzo regulation

## God Nodes (most connected - your core abstractions)
1. `login_required()` - 77 edges
2. `get_db()` - 54 edges
3. `salva_catalogo()` - 29 edges
4. `ambito_utente()` - 28 edges
5. `_list_regulation_files()` - 27 edges
6. `voci_catalogo()` - 24 edges
7. `utente_id()` - 20 edges
8. `_load_filtro()` - 16 edges
9. `regulation_default()` - 16 edges
10. `load_catalog()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `showMsg() — banner esito nel roster` --semantically_similar_to--> `rendi() - render catalog table`  [AMBIGUOUS] [semantically similar]
  templates/roster_editor.html → templates/catalog_editor.html
- `Trap: concurrent writes to salva_catalogo without lock` --references--> `salva_catalogo()`  [EXTRACTED]
  BACKLOG.md → blueprints/pokemon.py
- `Trap: rowcount on owner-filtered writes` --references--> `_team_upsert()`  [EXTRACTED]
  BACKLOG.md → blueprints/pokemon.py
- `Read with ambito_utente(), write with solo_mie()` --references--> `solo_mie()`  [AMBIGUOUS]
  BACKLOG.md → extensions.py
- `Trap: phantom endpoints swallowed by empty catch` --semantically_similar_to--> `Diffidare dei fallback silenziosi`  [INFERRED] [semantically similar]
  BACKLOG.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Silent-failure class: wrong numbers instead of errors** — claude_fallback_silenziosi, backlog_endpoint_fantasma, backlog_moveset_default_main, storico_regulation_vuota_200, project_context_indice_nomi_non_aliasabili, backlog_trappola_slug_mancante, backlog_oggetti_calcolatore [INFERRED 0.85]
- **Ownership and access control rules (fail-closed routes, owner-filtered queries)** — backlog_1_1_dati_proprietario, backlog_1_2_editor_solo_admin, backlog_route_pokemon_nasce_chiusa, backlog_query_nasce_scoperta, backlog_ambito_utente_vs_solo_mie, backlog_rowcount_scritture_filtrate, storico_controlla_proprietario_categorie [EXTRACTED 1.00]
- **Pre-push workflow: update BACKLOG/STORICO, export data, propose push on sviluppo** — claude_regola_d_oro_push, backlog, storico, scripts_esporta_dati, claude_branch_sviluppo_main_archivio [EXTRACTED 1.00]
- **Stored values/keys stay untranslated; only display text is translated** — templates_calcolatori_type_value_italian_key, templates_gaming_untranslated_status_platform, templates_items_editor_category_keys, templates_regulation_editor_mechanics_untranslated, templates_team_form_tera_types_untranslated [INFERRED 0.95]
- **Admin-only ?utente= owner filter and owner badge across sections** — templates_arduino, templates_gaming, templates_pcbuilder, templates_pokemon, templates_arduino_admin_owner_filter [INFERRED 0.95]
- **Regulation metadata, mega_map and movesets flowing from editor to team builder** — templates_regulation_editor_savemeta, templates_regulation_editor_megamap, templates_team_form_initregulations, templates_team_form_loadregulationdata, templates_team_form_mega_map, templates_regulations_list_moveset_source [INFERRED 0.85]
- **Lo switch lingua IT/EN: dizionario, funzioni gemelle e pulsante confinato** — templates_base_t, templates_base_tf, templates_base_nomevis, templates_base_sezioni_tradotte, templates_base_togglelingua [EXTRACTED 1.00]
- **Pattern editor: tabella e textarea JSON sincronizzati nei due sensi** — templates_abilities_editor_rendertable, templates_items_editor_rendertable, templates_moves_editor_rendertable, templates_catalog_editor_rendi, templates_roster_editor_synctagstojson [INFERRED 0.85]
- **Flusso archivio/ripristino condiviso dagli editor** — templates_catalog_editor_caricaarchivi, templates_abilities_editor_loadabilityarchives, templates_roster_editor_loadarchives, templates_roster_editor_trappola_apostrofo_confirm, templates_moves_editor_tojson_apici_singoli [INFERRED 0.85]
- **Cambio regulation nel Team Builder: roster, oggetti, meccaniche, mosse legali** — templates_team_form_initregulations, templates_team_form_loadregulationdata, templates_team_form_scrivimosse, templates_team_form_updatemechanicoptions, templates_team_form_updatemechanicvalue, templates_team_form_fetchpkmn, templates_team_form_mega_map [EXTRACTED 1.00]
- **Flusso di selezione dei contenuti di una regulation** — templates_regulation_content_filtrati, templates_regulation_content_rendi, templates_regulation_content_commuta, templates_regulation_content_spuntafiltrati, templates_regulation_content_salva, templates_regulation_content_cambiatutto [EXTRACTED 1.00]
- **Ciclo di vita di una regulation: crea, modifica, copia, elimina** — templates_regulations_list_createregulation, templates_regulations_list_deleteregulation, templates_regulation_editor_savemeta, templates_regulation_editor_copiada, templates_regulation_content_salva [INFERRED 0.85]
- **Pipeline Steam: import libreria, generi, tag e suggerimenti** — templates_steam_import_disegna, templates_steam_import_conta_generi, templates_steam_import_conta_tag, templates_gaming_suggerimenti_dalla_libreria, templates_game_form_collegamento_steam_appid [INFERRED 0.85]

## Communities (89 total, 13 thin omitted)

### Community 0 - "API Pokémon e loader"
Cohesion: 0.05
Nodes (110): api_moves(), api_regulation_data(), route, Restituisce il roster Pokémon della regulation richiesta. Usato dallo Speed…, Mosse della regulation richiesta. Default: la prima del registro. Prima leggeva…, abilities_archive(), abilities_archives(), abilities_editor() (+102 more)

### Community 1 - "Salvataggio e validazione catalogo"
Cohesion: 0.07
Nodes (40): Scrive un database del catalogo, tenendo da parte la versione precedente.…, `(errori, avvisi)` per una voce del catalogo. ⚠️ **Due elenchi e non uno**,…, salva_catalogo(), _valida_voce(), Catalog keys are never renamed (use nome_it/nome_en), Single catalog; regulation is only a filter, main(), tipo() (+32 more)

### Community 2 - "Dump PokéAPI ed evoluzioni"
Cohesion: 0.09
Nodes (42): _abilita_per_pokemon(), evoluzioni(), file_mancanti(), _firma(), _forme_per_pokemon(), _indice_pokemon(), _indice_specie(), leggi() (+34 more)

### Community 3 - "Shell, utenti e sezioni"
Cohesion: 0.07
Nodes (28): Form «Nuovo utente» con le spunte per sezione, mostraSezioni() — nasconde le spunte per gli admin, admin_utenti.html — utenti e permessi, Admin owner filter (?utente=) on Arduino, nomeVis() — il nome del dato nella lingua attiva, sezioni_tradotte — l'elenco che accende il pulsante lingua, Sidebar filtrata su sezioni_permesse, t() — traduzione delle etichette (JS) (+20 more)

### Community 4 - "Gaming con proprietario"
Cohesion: 0.09
Nodes (33): Read with ambito_utente(), write with solo_mie(), game_delete(), game_new(), route, Butta la cache. E' rigenerabile per definizione, quindi non c'e' niente da…, Da quello che l'utente incolla ricava uno steamID64. Accetta: 17 cifre,…, Giochi posseduti + ore giocate. Unico endpoint che richiede la chiave., Importa gli appid scelti. Aggiorna le ore se il gioco c'e' gia', non duplica. (+25 more)

### Community 5 - "Editor e bachi storici"
Cohesion: 0.08
Nodes (31): Copia di sicurezza automatica prima di ogni salvataggio, SyntaxError negli handler inline generati da JS, Ripristino roster senza conferma (onsubmit rotto), Richiamo a Tinkercad per il progetto Arduino, Verifica dei template eseguendo i blocchi inline con vm.Script, loadAbilityArchives, closeModal, Una sola modale per crea e modifica (+23 more)

### Community 6 - "Admin e permessi"
Cohesion: 0.11
Nodes (24): _blocca_non_admin(), before_request, route, Gestione utenti e permessi per sezione — solo per gli amministratori. Il…, Come login_required, ma richiede anche il ruolo. Applicato a tutto il blueprint., Il controllo sta qui e non sulle singole viste: una route nuova nasce protetta., Le spunte del form -> valore per la colonna. ⚠️ Tre casi, non due, ed è il…, _sezioni_dal_form() (+16 more)

### Community 7 - "Calendario uscite Gaming"
Cohesion: 0.12
Nodes (27): cache_ha_attesa(), _campi(), _etichetta(), filtra_per_attesa(), _fra_giorni(), gaming(), leggi_uscite(), _oggi() (+19 more)

### Community 8 - "Trappole dati e cache"
Cohesion: 0.12
Nodes (26): 1.3 Add data from the web app (PokeAPI species import), In-memory cache must follow file mtime, Trap: phantom endpoints swallowed by empty catch, moves: null means 'unknown', not 'no moves', Trap: missing moveset field falls back to main, aggiorna_catalogo(), api_pokemon(), _build_slug() (+18 more)

### Community 9 - "Login e password"
Cohesion: 0.12
Nodes (25): login(), logout(), route, hash_password(), Hash nuovo (scrypt con sale). Da usare per ogni scrittura da oggi in poi., `(corretta, da_riscrivere)`. `da_riscrivere` e' True quando la verifica e'…, verifica_password(), argomenti_disallineati() (+17 more)

### Community 10 - "Motore abilità calcolatore"
Cohesion: 0.14
Nodes (21): ABILITA_POKEMON, abilityEffect(), abilityIncideSulDanno(), abilityIncideSulleStat(), aggiornaNotaMeteo(), applicaMeteoAllaMossa(), catalogEntry(), catalogIndex() (+13 more)

### Community 11 - "Avvio app e helper"
Cohesion: 0.17
Nodes (21): create_app(), Personal Hub — entry point. Ogni area funzionale vive in blueprints/., raggruppa_per_mese(), `[(etichetta_mese, [voce, …]), …]`, nell'ordine in cui arrivano. Il…, categorie(), chiave_di_sessione(), e_admin(), init_db() (+13 more)

### Community 12 - "Costanti calcolatore"
Cohesion: 0.09
Nodes (21): ALIAS, BS, CALC_BOOTSTRAP, FORM_BASE, FORM_VARIANTS, METEO_LABEL, MOSSE_METEO, NM (+13 more)

### Community 13 - "Voci aperte del backlog"
Cohesion: 0.14
Nodes (19): 1.6 Two guides: architecture and new-PC restore, 2.3 Moves per regulation: data needing a source, 4.2 Fantacalcio section (to be defined), 5.2 Verify moveset against Bulbapedia, 5.3 Dead code inventory, 5. Final collaudo round (full web app test), Historical data files kept as fallback until final collaudo, Work order decided 21/08/2026 (online last; Pokemon first from 14/09) (+11 more)

### Community 14 - "Arduino e API team"
Cohesion: 0.22
Nodes (18): api_team(), arduino(), arduino_delete(), arduino_save(), route, game_edit(), _game_upsert(), import_dxdiag() (+10 more)

### Community 15 - "Build catalogo dal dump"
Cohesion: 0.21
Nodes (18): base_curata(), carica_json(), costruisci_abilita(), costruisci_mosse(), costruisci_oggetti(), costruisci_pokemon(), leggi(), main() (+10 more)

### Community 16 - "Dashboard, team ed export"
Cohesion: 0.23
Nodes (16): dashboard(), export_data(), route, _team_upsert(), route, python_toggle(), python_tracker(), get_db() (+8 more)

### Community 17 - "Nomi da PokéAPI"
Cohesion: 0.24
Nodes (16): abilita_per_nome_italiano(), chiave_confronto(), imposta(), main(), nomi_localizzati(), per_nome_inglese(), pokemon_per_specie(), (italiano, inglese) dal blocco `names`, con None se la lingua manca. (+8 more)

### Community 18 - "Stat Preview e forme"
Cohesion: 0.17
Nodes (11): STAT_KEYS, clearStatB(), loadStatPkmn(), resetStEVs(), updateStatPreview(), updStEV(), loadTeamPkmn(), Stat Preview tab (Pokemon A/B compare) (+3 more)

### Community 19 - "Editor oggetti e regulation"
Cohesion: 0.15
Nodes (16): Tendine Item ATK/DEF filtrate per categoria e modifier, itemsData — items.json nel textarea, saveJson(), La variabile di ciclo si chiama `tipo`, non `t`, Mechanics values (mega/tera/zmove/dynamax) not translated, Moveset source (main vs champions), fetchPkmn() - /api/pokemon/<name>?reg=, Il formato del team resta testo libero non tradotto (+8 more)

### Community 20 - "Proprietà dati e online"
Cohesion: 0.16
Nodes (13): 1.1 Data ownership (user_id, 78/78 queries), 1.4 Full DB export (--completo mode), 1.5 Put the app online (PythonAnywhere free / Cloudflare tunnel), Trap: rowcount on owner-filtered writes, Trap: concurrent writes to salva_catalogo without lock, Tech stack: Flask 3 + SQLite + Jinja2 + vanilla JS, STEAM_API_KEY read only from environment, SQLite tables (users, games, teams, team_members, ...) (+5 more)

### Community 21 - "Controllo proprietario query"
Cohesion: 0.21
Nodes (13): 1.2 Pokemon editors admin-only (30/36 routes), New content query is born uncovered (ownership filter), New /pokemon/* route is born closed (APERTE_A_TUTTI allowlist), fuori_dal_raggio(), main(), normalizza(), query_del_file(), Il testo di una stringa SQL, anche quando è una f-string. Le f-string qui… (+5 more)

### Community 22 - "Editor abilità e mosse"
Cohesion: 0.20
Nodes (14): addAbility, deleteAbility, formatJson() — textarea -> abData, renderTable (abilita), saveDesc (abilita), syncJson (abilita), I tipi si traducono solo a schermo, il value resta italiano, nuovaVoce() (+6 more)

### Community 23 - "Prova ripristino dati"
Cohesion: 0.28
Nodes (12): app_regge(), conta(), db_vergine(), esegui(), esito(), gira(), io_json(), main() (+4 more)

### Community 24 - "Tab Danno e oggetti"
Cohesion: 0.23
Nodes (11): applicaMosseLegali(), calcDamage(), loadMovesDB(), loadSide(), loadTimers, oggettoScelto(), recalcSide(), specieCombacia() (+3 more)

### Community 25 - "Tab calcolatore e categorie"
Cohesion: 0.22
Nodes (6): Reference tab + overlay (types / natures tables), Speed Tier tab, Team quick-load (?team=N), Item category keys are data; only labels translated, Archive confirm used missing 'regulation' variable, Hiding editor buttons is cosmetic; before_request is the real check

### Community 26 - "Regulation come filtro"
Cohesion: 0.24
Nodes (12): Catalogo unico + regulation come filtro, Clonazione di una regulation, Piano di riconversione delle 95 Mega, Schermata contenuti della regulation, Procedura di creazione di una nuova regulation, cambiaTutto, Dati passati via script application/json, Pagina Contenuti Regulation (+4 more)

### Community 27 - "Import roster Champions"
Cohesion: 0.23
Nodes (7): HTMLParser, carica(), leggi_csv(), main(), Estrae dalle tabelle: numero dex, nome, tipi e file dello sprite., scarica_elenco(), TabellaWiki

### Community 28 - "Import moveset specie"
Cohesion: 0.30
Nodes (11): carica_json(), costruisci_moveset(), indice_catalogo(), leggi(), main(), Ogni voce del catalogo che ha uno `slug`, specie e forme annidate. La chiave…, PokéAPI e il catalogo scrivono lo stesso nome in due modi: li riallinea. Serve…, Scrive il file, tenendo da parte la versione precedente come fa il catalogo. (+3 more)

### Community 29 - "Tabelle di riferimento"
Cohesion: 0.33
Nodes (9): abbrTipo(), EFF_CELLA, htmlTabellaNature(), htmlTabellaTipi(), openRef(), preparaTabelleRiferimento(), riempiUnaVolta(), showRef() (+1 more)

### Community 30 - "Prove catalogo e import"
Cohesion: 0.29
Nodes (8): 4.1 Gaming release calendar (IGDB), esito(), main(), prove(), esito(), main(), prove(), Tests must redirect files the code under test writes

### Community 31 - "Contenuti regulation e Steam"
Cohesion: 0.29
Nodes (10): hours_played distinta da hours_hltb, commuta, esc, filtrati, rendi, spuntaFiltrati, Tetto di 400 righe renderizzate, disegna (+2 more)

### Community 32 - "Regola #8 e formule"
Cohesion: 0.22
Nodes (10): Calculator items: per-effect conditions (effect engine), Regola #8: Incineroar -> Amoonguss known test case, Damage conditions multipliers (crit, screens 2732/4096, terrain x1.3), Convenzione SP Champions: ogni SP vale +2, cap 32, Formula Stat Champions (calcSt), Calculator organization: HTML-only template + 6 ordered calcolatori-*.js, STAGE_MULT stage multipliers table, stat_changes on moves (Speed Tier boost moves) (+2 more)

### Community 33 - "Sezioni Arduino e Gaming"
Cohesion: 0.22
Nodes (10): Nuova sezione Stampa 3D sul modello di Arduino, Arduino Projects, Filtri, ricerca e ordinamento in un solo form, Gaming Tracker, Suggerimenti dalla libreria per tag rari, Stati e piattaforme sono valori salvati, Arricchimento a lotti interrompibile, conta (generi da arricchire) (+2 more)

### Community 34 - "Integrazione Steam"
Cohesion: 0.29
Nodes (10): Integrazione Steam del Gaming tracker, Suggerimenti giochi in base a cosa si sta giocando, aggiornaAnteprima, cerca (autocomplete Steam), Collegamento a Steam via steam_appid, collegato, msg (stato ricerca Steam), Debounce e scarto delle risposte sorpassate (+2 more)

### Community 35 - "Base template ed editor"
Cohesion: 0.24
Nodes (10): textarea.form-control batte .code-area per specificita, extra_head sta fuori dallo <style> di base.html, salva_catalogo / _save_abilities unico punto di scrittura protetto, abilities_editor.html - editor abilita, block extra_head, base.html — layout sidebar, topbar, blocchi Jinja, regola CSS textarea.form-control{min-height:70px}, toggleSidebar (+2 more)

### Community 36 - "Client IGDB"
Cohesion: 0.22
Nodes (10): igdb_credenziali(), igdb_query(), igdb_token(), _mappa_uscita(), Un lotto di uscite future da IGDB. Il client richiama finche' `finito`.…, `(client_id, client_secret)` dall'ambiente. Stringhe vuote se non impostate., Token applicativo, preso una volta e riusato. Ritorna (token, errore)., POST Apicalypse su IGDB. Ritorna (dati, errore). ⚠️ IGDB **non** usa la… (+2 more)

### Community 37 - "Bootstrap e tab calcolatore"
Cohesion: 0.31
Nodes (10): abData — abilities.json vivo nel textarea, calc-bootstrap JSON (moves, abilities, reg_id, natures, champions), Datalist roster + mega con nomi visualizzati, align-items:stretch sulla griglia Attaccante/Mossa/Difensore, Ordine obbligatorio degli script del calcolatore, Tab Danno del calcolatore, Tab Speed Tier del calcolatore, Tab Stat Preview (confronto A/B) (+2 more)

### Community 38 - "Categorie oggetti e abilità"
Cohesion: 0.24
Nodes (9): CAT_LABELS abilita' da categorie('abilities'), Le chiavi di categoria restano tecniche in entrambe le lingue, bindActions(), CAT_LABELS oggetti da categorie('items'), closeModal() (items), confirmAdd(), deleteItem(), editItem() (+1 more)

### Community 39 - "Traduzioni IT/EN"
Cohesion: 0.31
Nodes (8): 2.1 Language switch IT/EN (t()/tf(), en.json), Only Pokemon and Gaming sections are translated (sezioni_tradotte), Language stored in cookie hub_lang (not localStorage), chiavi_doppie(), chiavi_nel_codice(), main(), Ogni frase passata a t() o tf(), con i file in cui compare., Le chiavi ripetute nel file, che `json.load()` non può vedere. Il dizionario si…

### Community 40 - "Sweep e verifiche"
Cohesion: 0.28
Nodes (8): Trap: static sweep is not enough (load pages, count rows), Trap: |tojson inside double-quoted attributes, Sweep new Function() on scripts and inline handlers, esprima (for sweep_pagine.py syntax check), controlla(), main(), moderno(), Smussa ciò che `esprima` 4.0.1 (2018) non sa leggere ma i browser sì. ⚠️ Serve…

### Community 41 - "Editor mosse e roster"
Cohesion: 0.25
Nodes (9): API documentate ma mai implementate, Sprite da pokemondb, non dal repo pokesprite, addMove, deleteMove, fetchFromPokeAPI, syncJson (mosse), Nessuna mossa entra nel catalogo senza passare da PokeAPI, addPkmn (verifica il nome contro /api/pokemon) (+1 more)

### Community 42 - "Controllo esposizione"
Cohesion: 0.42
Nodes (8): chiave_di_sessione(), cosa_segue_git(), debugger(), dipendenze(), main(), password_admin(), punto_wsgi(), voce()

### Community 43 - "README e avvio"
Cohesion: 0.25
Nodes (8): howtouse — istruzioni di avvio e credenziali, Obiettivo: accesso fuori dal PC e a PC spento, Autore e link placeholder ([Tuo Nome], tuonome), README-GitHub (vetrina pubblica del progetto), README Personal Hub v11.1a, Checklist post-avvio delle route da testare, Avvio rapido (pip install -r requirements.txt; python app.py), Note di sicurezza (SECRET_KEY da env, hub.db non esposto, reverse proxy)

### Community 44 - "Sonda IGDB"
Cohesion: 0.39
Nodes (7): credenziali(), interroga(), main(), mostra(), prendi_token(), Token applicativo (client_credentials). Ritorna (token, scadenza_s, errore)., POST Apicalypse su IGDB. Ritorna (dati, errore).

### Community 45 - "Speed Tier"
Cohesion: 0.46
Nodes (7): intestazioneSpeed(), loadRegSpeed(), loadSpePkmn(), onBoostSelect(), popolaBoost(), renderSpeed(), updateSpeed()

### Community 46 - "Editor catalogo"
Cohesion: 0.39
Nodes (7): apri() - load catalog entry, La chiave si mostra solo se dice qualcosa in piu' del nome, elimina(), INDICE (indice-dati del catalogo), messaggio(), rendi() - render catalog table, salvaVoce()

### Community 47 - "Legame Pokémon-abilità"
Cohesion: 0.43
Nodes (6): 2.2 Abilities merge (already merged; Megasolar relinked), Pokemon-ability link passes through nome_en, attivo(), carica(), main(), Megasolar / Mega Sol relinked to Mega Meganium

### Community 48 - "Mega e tabelle storiche"
Cohesion: 0.33
Nodes (7): Chiavi mega incoerenti nel catalogo, loadRegSpeed leggeva bst.spe invece di base_stats.spe, MEGA_DATA come fonte di verita delle Mega, Mega col calcolo Lv.50 salvato in base_stats, Tabelle di riferimento generate dagli stessi dati del calcolo, _INDICE / catalogIndex per le 84 forme annidate in forms, TYPE_CHART e l'unica type chart del progetto

### Community 49 - "Regulation MA e mega_map"
Cohesion: 0.29
Nodes (7): Import roster Champions dai suffissi dello sprite, mega_map delle regulation, Regulation MA = vera M-A di Pokemon Champions, I terreni dipendono solo dal tipo della mossa, Caso di prova Incineroar -> Amoonguss, Regola #8: ogni modifica ai calcolatori va testata con un caso noto, Regulation Editor

### Community 50 - "Prova build catalogo"
Cohesion: 0.48
Nodes (6): carica_modulo(), esito(), main(), prove(), `build_catalog` importato senza eseguirlo: `requests` c'è, la rete non serve., scrivi()

### Community 51 - "Form Gaming e Python"
Cohesion: 0.33
Nodes (7): Form gioco, Python Tracker (W3Schools), Spunta che invia il form al change, toggleCat, Variabile di ciclo che ombra t(), Chiave Steam solo in variabile d'ambiente, Importa da Steam

### Community 52 - "Flusso regulation editor"
Cohesion: 0.33
Nodes (6): /api/moves ignorava la regulation, Flusso dinamico della regulation nel Team Builder, addMech, removeMech, showToast, msg (stato libreria)

### Community 53 - "Export dati"
Cohesion: 0.47
Nodes (5): cali_sospetti(), main(), Le righe di una tabella, in ordine stabile, senza le colonne escluse. ⚠️…, Tabelle che nell'export precedente avevano righe e ora sono **vuote**. Serve…, righe()

### Community 54 - "Tag roster e mega map"
Cohesion: 0.33
Nodes (4): syncTableFromJson(), megaMap() - complete mega_map (preview/write), syncTagsToJson, MEGA_MAP (follows selected regulation)

### Community 55 - "Meta regulation editor"
Cohesion: 0.40
Nodes (6): campiFile, getMechs, Meccaniche non tradotte, Regulation as filter on the catalog (filter_file), Salvataggio che non azzera i campi assenti, saveMeta

### Community 56 - "Moduli JS calcolatore"
Cohesion: 0.50
Nodes (4): calcolatori.html spacchettato in moduli static/js, Doc stale: nessuna cartella static/, CSS e JS inline nei template, Classic script non moduli: gli handler inline vedono le globali, Ordine obbligatorio degli script del calcolatore

### Community 57 - "Motore meteo e abilità"
Cohesion: 0.50
Nodes (4): Motore meteo del calcolatore, Tipi di effetto abilita supportati, Motore abilita data-driven da abilities.json, I nomi in abilities.json non sono sempre quelli ufficiali

### Community 58 - "Fusione abilità doppie"
Cohesion: 0.83
Nodes (3): attivo(), carica(), main()

### Community 59 - "Fusione doppioni nome"
Cohesion: 0.67
Nodes (3): main(), piu_ricca(), Quanto è completa una voce: campi non vuoti, con peso a `effect`.

### Community 60 - "Migrazione regulation"
Cohesion: 0.83
Nodes (3): carica(), main(), scrivi()

### Community 61 - "Patch abilità catalogo"
Cohesion: 0.67
Nodes (3): main(), patch_catalog(), Itera il catalogo e aggiunge le abilità alle forme che le mancano. Restituisce…

### Community 62 - "Prova regulation nuova"
Cohesion: 0.83
Nodes (3): esito(), main(), prove()

### Community 63 - "Stage e schermi"
Cohesion: 0.67
Nodes (3): Il critico ignora gli stage sfavorevoli all'attaccante, SCHERMO_DOPPIE: Reflect/Light Screen al valore delle doppie, Stage multipliers (stageMult)

### Community 64 - "Panoramica progetto"
Cohesion: 0.67
Nodes (3): reference.html e orfano: nessuna route lo renderizza, Personal Hub: web app Flask a blueprint, Registry regulations.json + tabella regulations

### Community 65 - "Tema chiaro/scuro"
Cohesion: 0.67
Nodes (3): Divieto di localStorage/sessionStorage (regola #9), toggleTheme, updateThemeIcon

## Ambiguous Edges - Review These
- `Catalogo unico + regulation come filtro` → `Procedura di creazione di una nuova regulation`  [AMBIGUOUS]
  DOCUMENTAZIONE_PersonalHub.md · relation: conceptually_related_to
- `calcolatori.html spacchettato in moduli static/js` → `Doc stale: nessuna cartella static/, CSS e JS inline nei template`  [AMBIGUOUS]
  DOCUMENTAZIONE_PersonalHub.md · relation: conceptually_related_to
- `Divieto di localStorage/sessionStorage (regola #9)` → `toggleTheme`  [AMBIGUOUS]
  templates/base.html · relation: references
- `API documentate ma mai implementate` → `fetchFromPokeAPI`  [AMBIGUOUS]
  templates/moves_editor.html · relation: conceptually_related_to
- `Arduino Projects` → `Stati e piattaforme sono valori salvati`  [AMBIGUOUS]
  templates/arduino.html · relation: conceptually_related_to
- `rendi() - render catalog table` → `showMsg() — banner esito nel roster`  [AMBIGUOUS]
  templates/roster_editor.html · relation: semantically_similar_to
- `Variabile di ciclo che ombra t()` → `Python Tracker (W3Schools)`  [AMBIGUOUS]
  templates/python.html · relation: conceptually_related_to
- `solo_mie()` → `Read with ambito_utente(), write with solo_mie()`  [AMBIGUOUS]
  BACKLOG.md · relation: references
- `calcolatori.html` → `Archive confirm used missing 'regulation' variable`  [AMBIGUOUS]
  templates/items_editor.html · relation: conceptually_related_to

## Knowledge Gaps
- **68 isolated node(s):** `Autore e link placeholder ([Tuo Nome], tuonome)`, `Checklist post-avvio delle route da testare`, `Report fetch descrizioni mosse (315/317 aggiornate)`, `Mosse non trovate su PokéAPI (Bolt Tackle, Hi Jump Kick)`, `Obiettivo: accesso fuori dal PC e a PC spento` (+63 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

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
- **What is the exact relationship between `Arduino Projects` and `Stati e piattaforme sono valori salvati`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `rendi() - render catalog table` and `showMsg() — banner esito nel roster`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **What is the exact relationship between `Variabile di ciclo che ombra t()` and `Python Tracker (W3Schools)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._