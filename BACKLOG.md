# 📋 BACKLOG — Personal Hub

> Fonte: `Nuove implementazioni.docx` (verde = fatto).
> Questo file è la versione tracciabile di quel documento: qui restano solo le voci
> **non ancora chiuse**, più quelle chiuse di recente con la data.
> Aggiornato: 08/08/2026

Legenda: ⬜ da fare · 🟨 parziale / da verificare · ✅ fatto

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
| ⬜ | **Editor abilità senza archivio né backup** | Emerso 08/08/2026: roster, mosse e oggetti hanno `/archive` (e il roster anche `/archives` + `/restore`), l'editor abilità no. `_save_abilities()` in `blueprints/pokemon.py:24` sovrascrive `data/abilities.json` senza copia di sicurezza: un salvataggio sbagliato azzera 408 abilità, **incluse le 56 con blocco `effect` da cui dipende il calcolatore danno**. L'unico backup esistente (`abilities.json.20260807_124209.bak`) l'ha creato uno script, non l'app |
| ⬜ | Colonne tab Danno del calcolatore | 360/264/360 px, altezze 546/689/562: i tre riquadri chiudono a quote diverse. Non è un bug, è scelta di layout — da decidere se e come cambiarla |
| ⬜ | Nessun `.gitignore` | `hub.db` e 11 `.pyc` sono tracciati in git; la doc dice esplicitamente di non committare `hub.db` |
| ⬜ | `main` diverge da `origin/main` | Locale avanti 2 / indietro 4. I commit remoti contengono un marker di conflitto e hanno perso `PROJECT_CONTEXT.md`. Riallineare richiede force-push |
| ⬜ | `reference.html` è orfano | Nessuna route lo renderizza |
| ⬜ | Nomi in `abilities.json` da rivedere | Alcuni non corrispondono all'abilità descritta (es. `Spettroguardia` descrive Multiscaglia; il vero Wonder Guard è `Magidifesa`). Convivono nomi ufficiali IT e nomi di altra fonte |
| ⬜ | Catalogo con abilità incomplete | 84 Pokémon su 174 hanno una sola abilità; quasi tutti ne hanno 2-3 con la nascosta |
| ⬜ | Chiavi mega incoerenti nel catalogo | 3 mega sono chiavi di primo livello (`mega-banette`, `mega-chimecho`, `mega-crabominable`), le altre 81 forme sono annidate in `forms` |

---

## ✅ Chiuso l'08/08/2026

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
