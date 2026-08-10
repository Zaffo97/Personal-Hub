# 📋 BACKLOG — Personal Hub

> Fonte: `Nuove implementazioni.docx` (verde = fatto).
> Questo file è la versione tracciabile di quel documento: qui restano solo le voci
> **non ancora chiuse**, più quelle chiuse di recente con la data.
> Aggiornato: 08/08/2026

Legenda: ⬜ da fare · 🟨 parziale / da verificare · ✅ fatto

---

## ⚠️ Regulation MA — da riallineare alla vera M-A

`ma` deve corrispondere alla **vera Regulation M-A di Pokémon Champions**. L'elenco
attuale è ereditato dai file storici del progetto ed è **non verificato**: contiene
208 Pokémon fra cui Alcremie, Appletun, Arbok, Ariados e Audino, ma **non** Amoonguss,
Rillaboom, Urshifu, Flutter Mane e Chi-Yu. Non va preso come fonte di verità.

Ora la struttura per riallinearla c'è: catalogo completo + schermata
`/pokemon/regulation/ma/contenuto` per spuntare cosa ne fa parte. **Serve l'elenco
reale di M-A**: non va dedotto né inventato. Stesso discorso per la **M-B**, che
l'utente aggiungerà in seguito — la creazione di una regulation nuova produce già il
formato a filtro, quindi basterà crearla e spuntarne i contenuti.

---

## ✅ Chiuso il 10/08/2026 — struttura pronta ad agganciare le regulation

- **Creazione regulation nel modello a filtro** — `api_regulations_create` generava
  ancora i vecchi `roster_/moves_/items_`, quindi una M-B nuova sarebbe nata fuori dal
  catalogo. Ora crea `data/regulations/<id>.json` con elenchi di nomi e registra
  `filter_file`. Tre punti di partenza: **vuota** (default), **tutto** il catalogo, o
  **copia** da una regulation esistente
- **Schermata contenuti** `/pokemon/regulation/<id>/contenuto?db=…` — spunti quali
  voci del catalogo appartengono alla regulation, con le quattro linguette e i
  contatori (`208/1350`, `461/921`, `58/398`, `tutte`). Ricerca, selezione di massa
  che agisce su **tutti i filtrati** e non solo sulle 400 righe visibili, e una
  casella "includi tutte le voci, anche quelle future" che scrive `null` nel filtro.
  I nomi non presenti nel catalogo vengono ignorati e segnalati
- 24 controlli sul ciclo completo: creo una regulation, la trovo vuota, ne scelgo i
  contenuti, verifico che i loader filtrino davvero, provo "tutto" e la copia da MA,
  apro il calcolatore sulla regulation nuova. 23 pagine senza errori di sintassi

## ✅ Chiuso il 10/08/2026 — catalogo unico completato

- **Doppioni unificati e `ALIAS` riparati** — i doppioni veri erano **solo 3**: il
  trio `Tauros (X Breed)` scritto a mano accanto a `Paldean Tauros (X Breed)`
  importato, identici campo per campo a parte lo `slug`. Rimossi quelli a mano.
  Mega Machamp, Mega Meowstic e i Gourgeist **non** erano doppioni: sono forme
  originali tue, senza corrispettivo ufficiale, e sono rimaste.

  Nel controllo sono saltati fuori **6 `ALIAS` che non puntavano a nulla**: tre a
  `Tauros (Paldean Combat)` e simili, nomi inesistenti nel catalogo; due
  (`Lycanroc-Dusk`, `Lycanroc-Midnight`) puntavano a sé stessi; `Stunfisk-Galar`
  mancava del tutto. Erano esattamente i 6 nomi che lo Speed Tier non risolveva.

  **Speed Tier: 208 su 208, nessun nome irrisolto** (era 189 prima del catalogo,
  202 dopo). Regola #8 invariata, 19 pagine pulite.

  > Nota di metodo: la prima ricerca dei doppioni usava "stessi tipi e stesse stat"
  > e dava 17 gruppi — quasi tutti falsi positivi (i 7 nuclei di Minior, i costumi
  > di Pikachu, le build di Koraidon: stat identiche ma forme diverse davvero). Il
  > segnale giusto era un altro: le forme **senza `slug`**, cioè quelle scritte a
  > mano e mai riconciliate con i dati ufficiali.

- **Verifica in browser del nuovo modello** — regola #8 esatta sul Pokedex (A=183,
  D=122, HP=221, 85-102), 8 condizioni di danno su 8, 7 casi meteo su 7, tabelle di
  riferimento rigenerate, 19 pagine senza errori di sintassi. **Speed Tier da 189 a
  202 su 208**: il catalogo ha colmato quasi tutti i buchi, ne restano 6
- **`/api/moves` ignorava la regulation** ⚠️ — leggeva `moves_ma.json` hardcoded, e
  `loadMovesDB()` ci sovrascriveva sopra le mosse corrette arrivate dal bootstrap:
  sul Pokedex le mosse passavano da **921 a 461**. Ora l'endpoint accetta `?reg=` e
  `loadMovesDB()` non rifà più il fetch, perché il bootstrap porta già le mosse
  filtrate sulla regulation attiva
- **Editor del catalogo separato** — nuova schermata `/pokemon/catalogo` con le
  quattro linguette (Pokémon · Mosse · Abilità · Oggetti). Modifica una voce per
  volta via API invece di scaricare 449 KB di JSON nel browser; tabella limitata a
  300 righe con ricerca; creazione, rinomina ed eliminazione, con avviso se la voce
  è usata da una regulation. Archivio, elenco, ripristino e copia automatica prima
  di ogni salvataggio, come per le abilità. 31 controlli end-to-end superati, con i
  quattro file del catalogo verificati identici dopo il ripristino

> La distinzione ora è netta: **`/pokemon/catalogo` modifica i dati**, gli editor di
> regulation scelgono **quali nomi** ne fanno parte.

---

## 🚧 STATO — catalogo unico + regulation come filtro (08/08/2026)

Nuovo modello: **un database di default** in `data/catalog/` con tutte le voci, e le
regulation che contengono **solo elenchi di nomi** che puntano lì (`null` = tutte).

**Fatto e verificato (29 controlli su 29):**
- `data/catalog/` — 1032 specie + 321 forme, 921 mosse, 398 oggetti, 415 abilità
- `data/regulations/ma.json` (elenchi di nomi) e `pokedex.json` (nessun filtro)
- loader in `blueprints/pokemon.py` che filtrano il catalogo; `data.py` e
  `api_pokemon.py` leggono il nuovo catalogo con fallback al vecchio file
- editor roster/mosse/oggetti adattati: su una regulation migrata salvano la
  **selezione dei nomi**, non i dati
- Regulation MA identica a prima: stesse 461 mosse, 58 oggetti, 208 Pokémon, stessa
  mega_map, dati invariati. Pokedex vede tutto.

**Da decidere, non urgente:**
1. **Il roster di MA è ristretto**: non contiene Amoonguss, Rillaboom, Urshifu,
   Flutter Mane, Chi-Yu. Prima il calcolatore li offriva lo stesso perché
   `CHAMPIONS_BST` era globale; ora la regulation filtra davvero e in MA non
   compaiono. Se li vuoi, vanno aggiunti al roster — è il comportamento richiesto,
   ma è un cambiamento visibile
2. I file `data/roster_ma.json`, `moves_ma.json`, `items_ma.json`, `abilities.json` e
   `pokemon_catalog.json` restano come **fallback**: dismetterli solo a verifica finita

Script rieseguibili: `scripts/build_catalog.py` (`--dry-run` per provare) e
`scripts/migra_regulation.py`. Entrambi si rifiutano di modificare dati curati.

---

## 🐾 POKÉMON

### Abilità — 15.0
| | Voce | Note |
|---|---|---|
| ✅ | Abilità che agiscono su calcolo danno / speed tier / stat preview | Fatto 07/08/2026. Motore data-driven che legge il blocco `effect` di `abilities.json`. Prima nessuna abilità funzionava: le tendine erano in italiano, il codice confrontava nomi inglesi |
| ✅ | Editor abilità unico, non legato alla regulation | Verificato 08/08/2026: **era già tutto presente**, la voce era stale. `/pokemon/abilita` ha ricerca (`ab_search`), filtro categoria (13 opzioni, tutte corrispondenti ai dati), modale di aggiunta con rifiuto di duplicati e di `effect` JSON non valido, modifica descrizione inline, eliminazione, sync col JSON raw e POST di salvataggio. Provato eseguendolo su tutte le 408 abilità |

### Revisione finale
| | Voce | Note |
|---|---|---|
| ✅ | Sprite mancanti | Fatto 07/08/2026. Erano 96 nomi su 300 irrisolti (Mega e forme regionali erano irraggiungibili nel catalogo) + 38 sprite rotti dal repo pokesprite. Ora 296/300 risolti, 0 immagini rotte |
| ⬜ | **19 Pokémon del roster MA assenti dal catalogo** | Elenco esatto ottenuto 08/08/2026 facendo funzionare lo Speed Tier: `Ariados`, `Banette`, `Castform`, `Chimecho`, `Crabominable`, `Diggersby`, `Florges`, `Liepard`, `Lycanroc-Dusk`, `Lycanroc-Midday`, `Lycanroc-Midnight`, `Maushold`, `Stunfisk`, `Stunfisk-Galar`, `Tauros-Paldea-Aqua`, `Tauros-Paldea-Blaze`, `Tauros-Paldea-Combat`, `Toucannon`, `Vivillon`. Servono base stat, tipi e abilità. Nota: di `Banette`, `Chimecho` e `Crabominable` il catalogo ha **solo la Mega** come chiave di primo livello, non la forma base. `loadRegSpeed()` ora li elenca in `console.warn` invece di scartarli in silenzio |
| ✅ | Dividere / snellire `calcolatori.html` | Fatto 08/08/2026. Da **1885 righe / 222 KB a 685 righe / 147 KB**, con **zero JS inline**: CSS in `static/css/calcolatori.css` e JS in 6 file `static/js/calcolatori-*.js` (data · core · danno · speed · stat · ui). I dati di Flask passano da un blocco `<script type="application/json" id="calc-bootstrap">`, lo stesso schema di `items_editor.html` |
| ✅ | Tabelle di riferimento duplicate in `calcolatori.html` | Fatto 08/08/2026. Le 4 righe da 108 KB sono ora 4 `<div>` vuoti riempiti da `calcolatori-ref.js` dagli **stessi dati del calcolo**: `TYPE_CHART` per l'efficacia, `NATURES` + `NM` per le nature. Template a **38 KB** |
| ⬜ | DB ufficiale con TUTTI i Pokémon/abilità/mosse/oggetti di ogni generazione | Come regulation dedicata chiamata **Pokedex**. Selettore regulation in ogni sezione Pokémon, che pilota calcolatori, team ed editor. Stat sempre in formato Champions (66 totali, 32 per stat). Include tutti gli sprite |
| ⬜ | Creare i JSON di una nuova regulation dalla web app | Roster, mosse, oggetti e abilità generati in autonomia, magari agganciandosi a una fonte esterna. **Obiettivo di fondo: aggiungere una regulation senza IA, solo da interfaccia** |
| ✅ | Testare Speed Tier | Fatto 08/08/2026. `loadRegSpeed()` **non funzionava**: leggeva `bst.spe` mentre la velocità sta in `base_stats.spe`, quindi tutti i 174 Pokémon venivano scartati e la funzione ricadeva in silenzio sulla lista statica da 158 nomi. Ora costruisce 189 righe dal roster MA (208 nomi, 19 assenti dal catalogo) |
| ✅ | Weather Ball e mosse condizionate da meteo/abilità | Fatto 08/08/2026. Nuovo motore meteo in `calcolatori.html`: `meteoEffettivo()` (le abilità `weather_override` impongono il meteo, le `weather_setter` lo evocano se non è stato scelto nulla), `tipoPallaClima()` che usa `weather_ball_type` di `abilities.json` come override della mappa meteo→tipo, `applicaMeteoAllaMossa()` che riscrive BP e tipo nei campi visibili. Coperte **Weather Ball** (tipo dal meteo, BP 50→100), **Solar Beam** e **Solar Blade** (BP dimezzato con pioggia/sabbia/neve). Aggiunta la Pioggia forte alla tendina, con `fire_blocked` che porta le mosse Fuoco a 0 |

| 🟨 | Traduzione di tutte le mosse/abilità/oggetti | Linguetta per indicare in che lingua caricare i vari database |

### Calcolo danno — da verificare uno per uno
Tutte queste voci sono **implementate nel codice**, ma nel docx erano segnate da testare.
Nota: fino al 07/08/2026 l'intero JS della pagina non veniva eseguito per un `SyntaxError`,
quindi nessuna di queste è mai stata realmente provata in browser.

L'08/08/2026 il caso di prova della regola #8 è stato **eseguito in browser e superato**
(Incineroar Adamant 32 SP atk → Amoonguss: A=183, D=122, HP=221, danno 85-102 = 38.5%-46.2%,
identico all'atteso), quindi la catena base — stat, STAB, tabella tipi, roll — è confermata.
Poi tutte le condizioni sono state provate una per una, **24 casi misurati in browser**
accendendo un effetto alla volta e confrontando il rapporto col moltiplicatore atteso.

| | Voce | Esito |
|---|---|---|
| ✅ | STAB | Confermato dal caso di prova (`+STAB(1.5×)` nell'output) |
| ✅ | Terreni (electric / grassy / psychic / misty) | **Tre bug trovati e corretti.** Elettrico, erboso e psichico avevano una restrizione di categoria inesistente nel gioco |
| ✅ | Burn (scottatura) | Corretto: ×0.5 sull'Attacco solo per le mosse fisiche, nessun effetto sulle speciali. Con Combattività (Guts) diventa ×1.5 |
| ✅ | Reflect / Light Screen | Funzionavano ma col **valore delle singole** (×0.5). Portati a 2732/4096 ≈ ×0.667, il valore delle doppie. Ciascuno agisce solo sulla propria categoria e il critico li ignora |
| ✅ | Helping Hand | ×1.5 corretto |
| ✅ | Critico | ×1.5 corretto, ma **non ignorava gli stage**: corretto |

Verificati anche l'accumulo dei moltiplicatori — Helping Hand + critico = ×2.25 esatto,
scottatura + Reflect = ×0.25, terreno erboso + HH + spread = ×1.4625 — e lo spread a ×0.75.

---

## 💾 SALVATAGGIO LOG
| | Voce |
|---|---|
| ⬜ | Aggiungere una funzione di salvataggio log |

---

## 🖨️ STAMPA 3D (sezione nuova)
| | Voce |
|---|---|
| ⬜ | Nuova sezione Stampa 3D, sul modello di quella Arduino: richiamo a un sito per disegnare e salvataggio dei progetti |

---

## 🤖 ARDUINO
| | Voce |
|---|---|
| ⬜ | Richiamo a Tinkercad per disegnare il progetto e verificare i connettori |

---

## 💻 PC BUILDER
| | Voce |
|---|---|
| ⬜ | Wishlist Amazon o altri |
| ⬜ | Prezzo componente |
| ⬜ | Percentuale di compatibilità tra i pezzi (valutare UserBenchmark) |
| ⬜ | Gestire l'uscita di nuovi pezzi nel tempo |

---

## 🐍 PYTHON
| | Voce |
|---|---|
| ⬜ | Spazio per inserire i propri progetti e testarli |
| ⬜ | Idee per rendere la sezione più utile |

---

## 🎮 GAMING
| | Voce |
|---|---|
| ⬜ | Suggerimenti giochi in base a cosa si sta giocando |
| ⬜ | Collegamento a una API Steam per tracciare i videogiochi |

---

## ⚙️ GENERICO
| | Voce |
|---|---|
| ⬜ | Deploy da GitHub a Railway — c'è un errore da diagnosticare |

---

## 🔧 Emerso dal codice (non nel docx)

| | Voce | Note |
|---|---|---|
| ✅ | Formattazione editor mosse/oggetti/roster | Fatto 07/08/2026. Il banner "Stai modificando" stava dentro la griglia e occupava la colonna larga: la tabella mosse aveva 373px su 838 necessari (465 tagliati). Ora a tutta larghezza |
| ⬜ | `textarea.form-control` batte `.code-area` | Emerso 08/08/2026: in `base.html` la regola `textarea.form-control{min-height:70px}` ha specificità elemento+classe e vince su `.code-area{min-height:380px}` a prescindere dall'ordine. Le textarea JSON di abilità, mosse e oggetti sono alte **70px invece di 380**. Fix: usare `textarea.code-area` |
| ✅ | Editor abilità senza archivio né backup | Fatto 08/08/2026. Archivio manuale, elenco, ripristino e **copia automatica prima di ogni salvataggio**. Ora l'editor abilità è il più protetto dei quattro |
| ⬜ | Colonne tab Danno del calcolatore | 360/264/360 px, altezze 546/689/562: i tre riquadri chiudono a quote diverse. Non è un bug, è scelta di layout — da decidere se e come cambiarla |
| ⬜ | Nessun `.gitignore` | `hub.db` e 11 `.pyc` sono tracciati in git; la doc dice esplicitamente di non committare `hub.db` |
| ⬜ | `main` diverge da `origin/main` | Locale avanti 2 / indietro 4. I commit remoti contengono un marker di conflitto e hanno perso `PROJECT_CONTEXT.md`. Riallineare richiede force-push |
| ⬜ | `reference.html` è orfano | Nessuna route lo renderizza |
| ⬜ | Nomi in `abilities.json` da rivedere | Alcuni non corrispondono all'abilità descritta (es. `Spettroguardia` descrive Multiscaglia; il vero Wonder Guard è `Magidifesa`). Convivono nomi ufficiali IT e nomi di altra fonte |
| ⬜ | Catalogo con abilità incomplete | 84 Pokémon su 174 hanno una sola abilità; quasi tutti ne hanno 2-3 con la nascosta |
| ⬜ | Chiavi mega incoerenti nel catalogo | 3 mega sono chiavi di primo livello (`mega-banette`, `mega-chimecho`, `mega-crabominable`), le altre 81 forme sono annidate in `forms` |

---

## ✅ Chiuso l'08/08/2026

- **Archivio e backup delle abilità** — `_save_abilities()` sovrascriveva `data/abilities.json` senza tenere nulla da parte: un salvataggio sbagliato azzerava 408 abilità, incluse le 56 con blocco `effect` da cui dipende il calcolatore. Ora:
  - **copia automatica** della versione precedente a ogni salvataggio, in `data/archive/abilities_pre-salvataggio.json`. È a scorrimento — sempre lo stesso nome — così non riempie la cartella. Protegge anche chi non tocca mai il pulsante Archivia
  - **archivio manuale** con `/pokemon/abilita/archive`, **elenco** con `/pokemon/abilita/archives`, **ripristino** con `/pokemon/abilita/restore/<file>`
  - il salvataggio **rifiuta** un `abilities` vuoto o non-oggetto, che prima avrebbe cancellato tutto, e il messaggio mostra la differenza di conteggio (`408 voci (-12 rispetto a prima)`), così un calo anomalo si vede subito
  - il ripristino accetta solo file dell'archivio col prefisso giusto: `../../app.py` viene respinto

  Verificato con 18 controlli end-to-end sul test client, compresi il giro completo archivia → salvataggio distruttivo → ripristina con **md5 identico all'originale**, i 4 payload che devono essere rifiutati, e il path traversal. Il test lavora sui dati veri, quindi ripristina lo stato e verifica di averlo fatto: file identico e nessun archivio residuo.

  Lato interfaccia, gli `onsubmit` generati sono stati passati a `new Function()` prima di considerarli fatti: è la classe di bug che teneva il Ripristina del roster senza conferma.

- **Terreni: boost legato alla categoria sbagliata** ⚠️ — elettrico e psichico agivano solo sulle mosse speciali, erboso solo sulle fisiche. Nel gioco il boost dipende **solo dal tipo della mossa**. Quindi Wild Charge in terreno elettrico, Energy Ball in quello erboso e Psychic Fangs in quello psichico non prendevano **nulla**: misurato 68 → 68. Ora 68 → 88. Il terreno nebbioso era già corretto (non aveva la restrizione)

- **Il critico non ignorava gli stage** — nel gioco un critico ignora gli stage che sfavoriscono chi attacca: quelli negativi dell'attaccante e quelli positivi del difensore. Qui li applicava comunque: critico contro Difesa a +2 dava **52 invece di 102**, e con Attacco a −2 dava **51 invece di 102**. Corretto, e verificato che continui a rispettare gli stage favorevoli (Difesa −2 alza ancora il danno)

- **Reflect e Light Screen col valore delle singole** — tagliavano a metà, ma il VGC si gioca **solo in doppie**, dove valgono 2732/4096 ≈ ×0.667. Il calcolatore ha già il selettore spread a 0.75, che è una meccanica esclusiva delle doppie, quindi il ×0.5 contraddiceva il suo stesso contesto. Ora la costante è `SCHERMO_DOPPIE` in `calcolatori-data.js`: se un giorno servisse il calcolo in singole, è l'unico punto da cambiare

- **`calcolatori.html` spacchettato** — **1885 → 687 righe, 222 → 38 KB, zero JS inline**. CSS in `static/css/`, JS in 7 moduli `static/js/calcolatori-*.js` caricati in ordine obbligato (`data` dichiara le costanti, `core` le formule, `ui` avvia). Prima `static/` era una cartella vuota

  | File | Righe | Contenuto |
  |---|---|---|
  | `calcolatori-data.js` | 118 | bootstrap dal JSON + `TYPE_CHART`, `TIPI_IT`, `TYPE_CLR_IT`, `SPEED_META_STATIC`, `MEGA_DATA`, `ALIAS`, mappe nature/meteo, limiti SP |
  | `calcolatori-core.js` | 288 | `calcSt`, `tipoIT`, indice catalogo, motore abilità, motore meteo, `fetchPkmn`, limiti SP |
  | `calcolatori-danno.js` | 383 | `loadMovesDB`, `onMoveSelect`, `loadSide`, `recalcSide`, `calcDamage` |
  | `calcolatori-speed.js` | 130 | `loadRegSpeed`, `loadSpePkmn`, `updateSpeed`, `renderSpeed` |
  | `calcolatori-stat.js` | 194 | Stat Preview e forme alternative |
  | `calcolatori-ref.js` | 119 | genera le tabelle tipi e nature, overlay e tab Reference |
  | `calcolatori-ui.js` | 96 | quick-load team, init |

- **Tabelle di riferimento deduplicate** — le 4 righe da 108 KB di HTML incollato sono diventate 4 `<div>` vuoti riempiti al primo accesso da `calcolatori-ref.js`. Non è solo peso: quelle tabelle erano **indipendenti dal motore**, quindi potevano divergere in silenzio dal calcolo che dovrebbero documentare. Ora l'efficacia esce da `TYPE_CHART` (la stessa che `calcDamage()` usa: prima era una `const TC` locale, ora è unica in `calcolatori-data.js`) e le nature da `NATURES` + `NM`.

  Prima di riscriverle ho estratto i dati dal markup e li ho confrontati col motore: **0 disaccordi su 324 celle** e le 25 nature identiche. Poi ho verificato l'inverso, cioè che l'HTML generato coincida con l'originale: **identico byte per byte, 45911 e 9820 byte, zero differenze**.

  Parità verificata anche a valle: regola #8 invariata (85-102), Speed Tier 189 (MA), 12 casi meteo identici, Fuoco su Erba/Veleno ×2 e Drago su Folletto = 0 (prova che il motore legge la chart condivisa), tab e overlay con titoli e stati dei pulsanti corretti, 7 file JS e il CSS validi e serviti.

- **`extra_head` di `base.html` stava dentro `<style>`** ⚠️ — il blocco era all'interno dell'elemento `<style>`, quindi il primo `</style>` di ogni template figlio chiudeva lo stile di base e il `</style>` di base restava **orfano in tutte e 10 le pagine** che usano il blocco. Il CSS funzionava per caso (assorbito nello stile di base); un `<link>` veniva ignorato come testo CSS — ed è così che il problema è emerso. Ora il blocco è fuori: `<style>` bilanciati su tutte le 13 pagine, cascata invariata

- **Motore meteo** — Weather Ball, Solar Beam e Solar Blade ora rispondono al meteo, e le abilità meteo determinano il meteo del calcolo. Il campo `weather_ball_type`, presente su 7 abilità e mai letto da nessuno, è finalmente in uso. Due note nell'interfaccia rendono visibile cosa sta succedendo: sotto il BP (`🌍 Sole forte → tipo Fuoco, BP 100`) e sotto la tendina Meteo quando un'abilità sovrascrive la scelta (`⚠️ Mega Sol impone Sole forte`)

  | Caso | Atteso | Ottenuto |
  |---|---|---|
  | Weather Ball, nessun meteo | Normale, BP 50 | ✅ 17-21 danno |
  | Weather Ball, Sole | Fuoco, BP 100 | ✅ 153-183 |
  | Weather Ball, Pioggia | Acqua, BP 100 | ✅ 25-30 |
  | Weather Ball, Sabbia / Neve | Roccia / Ghiaccio | ✅ |
  | Weather Ball, nessun meteo + Siccità | Sole → Fuoco | ✅ nota mostrata |
  | Weather Ball, Pioggia scelta + Mega Sol | Sole forte → Fuoco | ✅ l'abilità vince |
  | Solar Beam, Sole / Pioggia | BP 120 / 60 | ✅ |
  | Solar Blade, Sabbia | BP 62 | ✅ |
  | Mossa Fuoco, Pioggia forte | 0 | ✅ |
  | Mossa Fuoco, Pioggia normale | ×0.5 | ✅ 51-60 |

  Rapporto di controllo: Sole/Pioggia sulla stessa mossa Fuoco = 153/51 = **×3 esatto**, cioè ×1.5 contro ×0.5. Il caso di prova della regola #8 resta invariato a 85-102.

- **Editor abilità** — la voce di backlog era stale: ricerca, filtro, aggiunta, eliminazione e salvataggio erano già tutti implementati e funzionanti. Verificato eseguendoli
- **Speed Tier muto** — `loadRegSpeed()` leggeva `bst.spe` invece di `base_stats.spe`: 174 Pokémon su 174 scartati e caduta silenziosa sulla lista statica. Aggiunto `catalogEntry()`, che risolve anche le 84 forme annidate in `forms` (equivalente JS di `_INDICE`). Da 158 nomi statici a **189 dal roster MA**
- **Ripristino roster senza conferma** ⚠️ — nell'`onsubmit` del pulsante Ripristina, `verra'` produceva un apostrofo dentro la stringa a singoli apici dell'attributo: l'handler era un `SyntaxError`, `form.onsubmit` era `null` e **il roster corrente veniva sovrascritto senza alcuna richiesta di conferma**
- **Typo a video** — `roster_editor.html:166` mostrava "eà gia' nel roster", ora "è già nel roster"
- **Doc: nomi delle globali sbagliati** — `PROJECT_CONTEXT.md` documentava `CHAMPIONS_DATA` e `ABILITIES_LIST`, che non esistono: sono `CHAMPIONS_BST` e `ABILITIES_DATA`
- **Verifica in browser delle 13 pagine** — script inline **e** handler negli attributi passati a `new Function()`: 0 `SyntaxError`. I 4 fix del 07/08 (PC Builder, `calcDamage()`, `deleteMove`, `startEditDesc`) provati eseguendoli, non solo leggendoli

> Il check ora copre anche gli **handler inline negli attributi** (`onclick`, `onsubmit`, …), non solo i blocchi `<script>`: è così che è emerso il bug del Ripristina. Attenzione però: quel bug stava in HTML **generato da JS**, che uno sweep statico non vede — serve far girare la funzione che lo produce.

---

## ✅ Chiuso il 07/08/2026

- **`SyntaxError` che azzerava tutto il JS di `calcolatori.html`** — merge rotto alle righe 718-729: nessuna riga della pagina veniva eseguita
- **Formula stat incoerente** — Speed Tier usava `ev*2`, Danno e Stat Preview `floor(ev/4)`: stesso Pokémon, numeri diversi. Ora entrambi `ev*2` (convenzione Champions)
- **Bug abilità 1-5** — abilità tipo-cambio, flag contatto, Fluffy, Wonder Guard, Overgrow & co. sotto 1/3 HP
- **Tutte le 408 abilità nelle tendine** con ● sulle 44 che incidono sul calcolo
- **Tendina abilità nello Stat Preview** su entrambi i lati
- **`ABILITIES_DATA` a doppio encoding** — arrivava come stringa invece che oggetto
- **Pulizia dead code** — `PKMN_DB`, `calc_stat_champions()`, `switchTab` duplicata, 816 `<option>` Jinja inutili, mappa tipi ripetuta 5 volte
- **Sprite** — 0 rotti su 296 nomi
- **Formattazione editor** mosse/oggetti/roster — banner fuori dalla griglia, tabella da 373 a 961 px

### 5 bug trovati dal grafo (graphify) e sistemati
| File | Bug | Effetto |
|---|---|---|
| `templates/pcbuilder.html:202` | apici singoli attorno a `.comp-row` chiudevano la stringa JS | **`SyntaxError`: tutto lo script del PC Builder morto** (tab, modali, import DxDiag) |
| `templates/calcolatori.html:176,407` | le select oggetto chiamavano `calcDmg()`, inesistente | cambiare oggetto lanciava errore invece di ricalcolare |
| `templates/moves_editor.html:246` | il pulsante elimina chiamava `deleteMove`, la funzione era `removeMove(el)` | eliminare una mossa non funzionava |
| `templates/moves_editor.html:263` | `startEditDesc(el)` leggeva `el.dataset.name` ma riceveva una stringa | modifica inline della descrizione in errore |
| `templates/roster_editor.html:238` | un `"` di troppo dopo il tag `<form>` | apice spurio stampato a video negli archivi |

> Il primo è **lo stesso guasto** del `SyntaxError` di `calcolatori.html`: una riga malformata che azzera un intero blocco `<script>`. Il PC Builder era inerte da tempo senza che nulla lo segnalasse.
> Check utile per il futuro: renderizzare ogni pagina ed eseguire `new vm.Script()` su ogni blocco inline intercetta questa classe di bug in pochi secondi.
