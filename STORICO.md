# 📜 STORICO — Personal Hub

**Questo file è la memoria di ciò che è già chiuso**: una riga per lavoro, con la data e
i numeri della verifica. Serve a rispondere a «questo l'avevamo già fatto, e com'è
andata?» senza rileggere tutto.

- Le voci **aperte** stanno in `BACKLOG.md`.
- Le **trappole che valgono ancora** stanno anch'esse in `BACKLOG.md`, non qui: non sono
  storia, sono regole di lavoro.
- Il testo lungo di ogni voce — le tabelle di misura, i ragionamenti, i vicoli ciechi —
  resta nella cronologia di git. L'ultima versione prima della potatura del 13/08/2026 è
  `git show cf79124:BACKLOG.md` (1967 righe).

Convenzioni dei numeri: «N su N» è il test client; **sweep** è il giro che rende ogni
pagina ed esegue `new Function()` su ogni blocco `<script>` **e** su ogni handler inline;
**regola #8** è il caso di prova Incineroar → Amoonguss (A=183, D=122, HP=221, 85-102 =
38.5%–46.2%), che va eseguito sulla regulation `pokedex`.

---

## 17/08/2026

**Gli editor Pokémon solo per gli admin — 30 route su 36 chiuse a chiave (§1.2)**

- ✅ **La lista è quella del permesso, non del divieto**, ed è la decisione che regge tutto.
  `APERTE_A_TUTTI` in `blueprints/pokemon.py` elenca le **6** viste d'uso — `pokemon`,
  `calcolatori`, `team_new`, `team_edit`, `team_delete`, `api_regulations_list` — e un
  `before_request` chiude le altre **30**. Il verso opposto (elencare il vietato) fallirebbe
  **aperto** sulla prossima route dimenticata, e la dimenticanza non darebbe nessun segnale.
- ✅ **Le route sono 36, non 28** come diceva il backlog: contate sulla `url_map`, non stimate.
- ✅ **Verifica: 36 route × 2 ruoli.** Utente normale con la sezione `pokemon`: **30
  bloccate, 6 aperte**, e l'insieme delle aperte coincide **esattamente** con
  `APERTE_A_TUTTI`. Amministratore: **0 bloccate**. Ogni route di scrittura fuori
  dall'elenco è bloccata (`True`).
- ✅ **End-to-end con due account veri** sul test client: le 9 pagine degli editor
  rispondono **302 → `/pokemon/`** all'utente e **200** all'admin; `/pokemon/calcolatori`,
  `/pokemon/team/new` e `/pokemon/api/regulations` rispondono **200 a entrambi**.
- ✅ **La prova che il divieto arriva prima della scrittura**: 8 API di scrittura chiamate
  **direttamente** dall'utente normale con payload distruttivi (salva una voce vuota,
  elimina Incineroar, `regulations: []`) → **403 su 8 su 8**, e
  `data/catalog/pokemon.json` **invariato** per mtime e dimensione. Più 5 form POST di
  archiviazione → 302, nessun archivio creato.
- ✅ **Risposta giusta al chiamante giusto**: 403 JSON `{"ok": false, "error": …}` a chi
  chiama un path con `/api/` o una delle tre viste che rispondono in JSON senza averlo nel
  path (`*_archives`); redirect con flash a chi naviga. Un redirect dentro una `fetch()`
  darebbe un errore di parsing invece di un messaggio — stesso ragionamento di `app.py`.
- ✅ **E poi il pulsante**, che è cosmesi e viene dopo: i **6** link agli editor in
  `pokemon.html` sotto `{% if e_admin %}`. Reso e contato: **0/6 all'utente, 6/6
  all'admin**, con «Calcolatori VGC» e «Nuovo Team» presenti per entrambi. Due blocchi
  `{% if %}` e non uno, per non cambiare l'ordine dei pulsanti a chi è admin.
- ⚠️ **Sweep fatto in un motore JS vero, ma non con Node**: su questa macchina Node non
  c'è (già annotato il 16/08). Le pagine sono state rese col test client per **entrambi i
  ruoli** e i pezzi estratti sono passati a `new Function()` **nel browser** —
  **14 pezzi su 14, zero errori**. Traduzioni **587 su 587**, zero mancanti e zero orfane.
- ⚠️ **Test su una copia di `hub.db`**, come dal 16/08: i due utenti di prova non sono mai
  esistiti nel DB vero, e la copia è stata cancellata a fine giro.
- ⚠️ **Due cose trovate censendo le route e non corrette** (fuori scope, sono in
  `BACKLOG.md` §3): `/api/team/<id>` **non esiste** — `calcolatori-ui.js:9` lo chiama e
  prende 404 dentro un `catch` muto, quindi il pulsante «Analizza» non carica il team; e
  `/pokemon/api/abilities` (GET) **non lo chiama nessuno**.

**Calendario uscite — il filtro «quanto è atteso», e il periodo che torna a servire (§4.1c)**

- ✅ **Dei tre campi che il backlog proponeva ne funziona uno solo, e si è visto misurando**
  (sonda di sola lettura su 5954 uscite future): **`follows` è vuoto su tutte e 5954** —
  il campo esiste ancora nell'API, la risposta no; **`total_rating_count` è valorizzato sul
  2%** e conta i voti dei giochi **già usciti** (Elden Ring 2251, Minecraft 557), cioè
  misura un'altra cosa; **`hypes`** — quante persone hanno messo il gioco in lista d'attesa
  — c'è sul **39%** delle righe, fino a 982.
- ✅ **Soglie scelte sui conti, non a occhio.** Nei prossimi 90 giorni: senza filtro 4598
  voci fuse (e il tetto le taglia agli **11 giorni** più vicini); `hypes ≥ 2` → **317 voci**;
  `hypes ≥ 10` → 126. Tendina a tre posizioni — «Tutte le uscite», «Quelle un po' attese»
  (default, soglia 2), «Solo le più attese» (10).
- ✅ **Il risultato è quello che la voce chiedeva**: con il default le 300 righe della
  pagina coprono **tre mesi (31 giorni distinti, agosto→ottobre)** invece di **undici
  giorni di solo agosto**. Il selettore del periodo torna a fare qualcosa.
- ✅ **Nuova colonna `hypes` in `game_releases`**, con `ALTER TABLE` per i DB che esistono
  già (la `CREATE TABLE` tocca solo i nuovi) — provato su una copia: colonna assente →
  presente dopo `init_db()`. Il numero si vede **anche sulla riga** (👀 289), perché una
  soglia il cui valore non si legge da nessuna parte è una decisione presa al buio.
- ⚠️ ✅ **Il filtro dichiara quanto nasconde** («Nascoste 1109 uscite che su IGDB non
  aspetta quasi nessuno» + «Mostrale tutte»), e **si spegne da solo** se la cache non ha
  ancora il dato, dicendolo. La prova è stata fatta nello stato reale di oggi (colonna
  migrata, tutta `NULL`): 300 righe mostrate, tendina assente, avviso presente — invece di
  un calendario vuoto. Le righe con `hypes` a `None` **restano dentro**: mancante non è
  zero, ed è la stessa regola di `moves: null`.
- ✅ **Import provato contro IGDB vero, scrivendo su una copia di `hub.db`**: 500 uscite
  lette, 389 righe aggiornate col nuovo campo, **210 con attesa maggiore di zero**, 1373
  righe potate dalle piattaforme escluse, 0 scarti.
- ✅ **Verifica: 19 controlli**, fra cui il gioco con `hypes` 0 (*10 Hours Before Sunrise*)
  che sparisce col default e torna con «tutte», la ricerca che continua a trovare i molto
  attesi, `?attesa=pippo` che ricade sul default, «azzera filtri» che compare solo quando
  un filtro c'è davvero, e l'inglese. ⚠️ Due prove erano **sbagliate le prove, non il
  codice**: una cercava un titolo che ha `hypes` esattamente 2 (quindi passa la soglia), e
  l'altra puntava a un DB non migrato a metà processo. Rifatte per bene.
- ✅ **Sweep 60 su 60** su sei varianti della pagina. Dizionario EN a **587 chiavi su 587**,
  con le tre etichette della tendina dichiarate in `_dinamiche` (sono tradotte da un `t()`
  che il controllore non può vedere, come già quelle del periodo).

---

## 17/08/2026

**Calendario uscite — la ricerca per titolo (§4.1b)**

- ✅ **`?q=` nella riga dei filtri di `/gaming/uscite`**, come `platform` ed `entro`:
  una ricerca si mette fra i preferiti. Filtro **in SQL, prima del tetto** — provato col
  caso che lo dimostra: *Liminal Shroud* è la **500esima** voce della finestra di default,
  quindi la pagina senza ricerca **non la contiene** (300 righe), e cercandola compare.
- ✅ **Il buco che restava era il periodo, non il tetto.** Il periodo è un filtro
  esplicito, ma con una ricerca attiva «nessun risultato» si legge come «non c'è»: ora la
  pagina conta quante uscite col titolo cercato cadono **fuori** dal periodo e offre il
  collegamento alla stessa ricerca senza limiti (tenendo la piattaforma scelta). Il conto
  è sulle **voci fuse**, come quello mostrato accanto, e la lettura in più si fa **solo**
  con una ricerca attiva.
- ✅ **Quattro frasi diverse per l'elenco vuoto**, perché «non trovato» ha significati
  diversi: fuori periodo, assente **su quella piattaforma** (con una piattaforma scelta
  non si può dire «non c'è in cache»), assente del tutto (e allora si dice **perché**: il
  calendario tiene solo da oggi in avanti), oppure nessun filtro attivo.
- ✅ **Verifica: 14 casi su 14** col test client — il titolo oltre il tetto, quello che
  esce oltre i 90 giorni (elenco vuoto ma «altre 1 fuori dal periodo», e con `entro=tutto`
  compare), ricerca + piattaforma, titolo inesistente, **apostrofo** (`Hero's Hand`),
  `' OR 1=1--` → 0 righe, `%` che resta jolly come nella libreria, ricerca vuota e soli
  spazi che non filtrano nulla, e la pagina in inglese. Più: valore che resta nel campo,
  «azzera filtri» che compare solo se un filtro c'è, striscia di `/gaming` intatta.
- ✅ **Sweep 45 su 45** fra blocchi `<script>` e handler inline su cinque varianti della
  pagina. Dizionario EN a **579 chiavi su 579**, e i segnaposto `{…}` combaciano su tutte
  e 601 le voci del dizionario.

---

## 17/08/2026

**Calendario uscite — in cache entrano solo le piattaforme che interessano (§4.1a)**

- ✅ **`PIATTAFORME_TENUTE` in `blueprints/gaming.py`**: PC, PlayStation 5, Xbox Series X|S,
  Switch e Switch 2, e i VR (SteamVR, Meta Quest 2 e 3, Oculus Quest, PlayStation VR2,
  visionOS). **Le console vecchie restano fuori** — deciso da Davide il 17/08, che ha
  scartato PlayStation 4 e Xbox One insieme a 360, Vita, Wii e Wii U: il backlog le dava
  per «restano» applicando la regola alla lettera, ed è l'unico punto in cui la decisione
  di oggi si discosta da quella del 16/08.
- ✅ **Misurato sulla cache vera (7327 righe, 4582 giochi): −1373 righe (18,7%), ma solo
  45 giochi spariscono del tutto.** Quasi tutto il taglio è la versione Mac (570) o Linux
  (491) di un gioco che è **anche su PC**: sparisce l'etichetta, non il gioco. Dei 45
  persi davvero: 21 iOS, 18 Android, 4 Playdate, 4 browser, 4 Wii, **3 solo-PS4, 1
  solo-Xbox One**, e undici uscite su console retro.
- ✅ **Elenco di inclusi e non di esclusi**, che fallisce **chiuso** sulla prossima
  piattaforma che IGDB aggiunge. Il prezzo — una console nuova scartata in silenzio — è
  pagato contando le righe escluse **per nome** e dicendole a schermo: nella prova la
  finta `PlayStation 6` è comparsa fra le escluse col suo nome, che è il segnale per
  aggiungerla all'elenco.
- ✅ **La cache vecchia si pota da sola**: `DELETE` al primo lotto dell'import, non alla
  fine, così gira anche se l'aggiornamento viene fermato a metà. Provato **su una copia di
  `hub.db`**: 7327 → 5954 righe, 11 piattaforme rimaste, seconda passata 0 righe
  (idempotente).
- ✅ **La route provata davvero**, con un finto IGDB e su una copia del DB: 4 uscite in
  ingresso → 1 salvata, 3 escluse per nome (`Mac`, `PlayStation 4`, `PlayStation 6`),
  0 scarti, 1373 righe potate.
- ✅ **Sweep a zero errori** su 18 fra blocchi `<script>` e handler inline di
  `/gaming/uscite` (due varianti di filtro), e le pagine rese e contate col test client:
  300 righe e 293 immagini in 228 KB, il tetto è intatto.
- ⚠️ **Il tetto delle 300 righe morde esattamente come prima, ed era prevedibile**: dopo
  il filtro la finestra di default passa da 4649 a **4598** voci fuse (−51), perché
  togliere Mac e Linux toglie etichette, non giochi. La 300esima resta il **27/08**, cioè
  11 giorni, quindi il selettore del periodo continua a non cambiare niente. **Il rimedio
  vero resta §4.1c** (la coda lunga), non questo.
- ⚠️ **Fino al prossimo «Aggiorna il calendario» la cache contiene ancora le 1373 righe
  escluse**: la potatura è dentro l'import, non è un lavoro fatto al posto di Davide.
- ✅ Dizionario EN a **572 chiavi su 572**, zero mancanti, zero orfane, zero doppie.

---

## 16/08/2026

**Calendario uscite in Gaming — la metà lettura, chiusa e verificata**

- ✅ **Fonte decisa: IGDB, e la scelta è stata misurata, non presa dal backlog.** Il
  backlog dava RAWG come «più semplice da attaccare»; il 16/08 RAWG rispondeva **522 da
  Cloudflare su API *e* sito**, tre tentativi di fila, mentre dalla stessa macchina Steam
  rispondeva normalmente e IGDB dava un **401 regolare** con l'istruzione sugli header —
  cioè era viva e voleva solo il token. Scrivere il client di un servizio irraggiungibile
  sarebbe stato scrivere codice non provabile.
- ✅ **`game_releases`, tabella sua e fuori dall'export.** Le uscite future **non** sono
  la libreria: dentro `games` sarebbero finite nei conteggi, nei filtri, nel suggeritore e
  nell'export. Verificato che non ci finiscano: con 6 uscite di prova in cache, `games`
  resta a **33** righe e il contatore della sezione dice ancora «Tutti (33)». La tabella
  è **fuori da `TABELLE` di `esporta_dati.py` per scelta** — ed è scritto nel codice,
  perché `regulations` oggi è fuori **per caso** ed è una falla nota (§1.4).
- ✅ **Pagina `/gaming/uscite`** con raggruppamento per mese, giorno della settimana,
  filtro piattaforma, quattro finestre (30gg / 3 mesi / 1 anno / tutto) e la cache che
  **dichiara la propria età**. Più una **striscia** delle 6 prossime in cima a `/gaming`.
- ✅ **29 controlli su 29** sul test client, con righe finte inserite e poi rimosse (stesso
  metodo dei filtri Gaming del 12/08): oggi è incluso e ieri no, le righe **senza data
  restano fuori**, le tre finestre tagliano dove devono, `?entro=pippo` ricade sul default
  invece di esplodere, `?platform=' OR 1=1--` dà zero righe, e una data imprecisa mostra
  **`~ Q1 2027`** invece di spacciare il primo giorno del trimestre per l'uscita.
- ⚠️ **Sweep fatto in un modo diverso, e va detto: su questa macchina non c'è Node**,
  quindi `new Function()` come nelle sessioni precedenti non era lanciabile. Al suo posto
  le pagine sono state rese su file e aperte in un **browser vero** — controllo più forte,
  perché vede anche il runtime. Esito: **4 pagine, 3 script inline sulla pagina uscite e 2
  su gaming, zero messaggi in console**, `t`/`tf` funzioni, il pulsante col suo listener,
  e titoli con apostrofi, `&`, virgolette doppie e `<tag>` resi senza rompere niente.
  ⚠️ Al primo giro il blocco `<script>` **non era nemmeno stato reso** (sta dentro
  `{% if chiavi_presenti %}`): rifatto con credenziali finte, che fanno comparire il
  pulsante senza chiamare nessuno. Uno sweep che non rende il codice non lo prova.
- ✅ **Le due lingue**, 565 chiavi su 565, zero mancanti, zero orfane, zero doppie: mesi
  (`agosto 2026` → `August 2026`), giorni (`16 dom` → `16 Sun`), finestre e frasi del JS.
- ⚠️ **Trappola intercettata prima di pagarla**: `mar` in italiano è **marzo** *e*
  **martedì**, e la chiave del dizionario è la frase italiana — una traduzione sola per
  due parole inglesi. Abbreviando entrambi, uno avrebbe preso la parola dell'altro **senza
  nessun errore**. Rotto il pareggio dove costa meno: mesi per esteso («16 agosto» è
  italiano normale), giorni abbreviati, che in italiano si scrivono proprio così.
- ✅ **L'import eseguito, e i dati veri hanno risposto alle domande aperte**: **6827
  uscite**, 4280 giochi su 29 piattaforme. **Zero righe su 6827 con precisione «ignota»**
  — il campo della precisione è stato letto per tutte, quindi la doppia lettura
  `category` / `date_format` regge; 0 senza piattaforma, 0 senza URL, 196 senza copertina
  (2,9%, giochi che su IGDB non ce l'hanno).
- ✅ **Uscite multipiattaforma fuse in una riga sola**, chiesto da Davide lo stesso
  giorno. Nei soli prossimi 90 giorni la fusione unisce **454 gruppi**: *Vampire
  Survivors: Legacy of the Bloodmoon* da 9 righe a 1. Si fonde in **lettura** e **dopo il
  filtro** — filtrando PS5 la riga elenca solo PS5, o sembrerebbe che il filtro non
  funzioni. La chiave è `igdb_game_id` e non il titolo, così due giochi omonimi non si
  fondono; le piattaforme si deduplicano, e serve davvero (*Romance of the Three Kingdoms
  XIV* su IGDB ha la stessa piattaforma due volte, regioni diverse: a schermo esce una
  volta). *EA Sports FC 27* resta **due** righe, 18 e 25 settembre, ed è corretto.
  **38 controlli su 38.**
- ⚠️ **Tetto a 300 righe, e l'effetto collaterale è dichiarato invece che nascosto.**
  Senza tetto la pagina pesava **3,3 MB con 4224 immagini** su «tutto» e 994 KB con 1291
  già sul default; col tetto **225 KB e 292 immagini** (stesso rimedio dello Speed Tier).
  Ma 300 righe **coprono 11 giorni**, quindi con la cache piena le quattro finestre
  mostrano lo stesso periodo e il selettore non fa niente: è scritto nell'avviso a
  schermo, che indica il **filtro piattaforma** — l'unico che funziona davvero (PS5 a 221
  righe, sotto il tetto). ⬜ La strada vera è **importare di meno**, filtrando su `hypes`
  / `follows`: decisione di Davide, cambia quali dati entrano in cache.
- ⚠️ **Due errori miei nello script di prova, entrambi della stessa famiglia.** La
  pulizia cancellava `igdb_release_id` fra 900000 e 910000 «il mio intervallo»: gli id
  veri stanno fra 486664 e 954196, e sono sparite **497 righe di cache vere** (rigenerabili
  col pulsante, ma non doveva poter succedere). Poi il tetto ha fatto cadere fuori pagina
  le righe finte, perché con 6827 uscite le prime 300 coprono pochi giorni. Stessa causa:
  **un test che divide lo stato con i dati veri misura anche loro**. Ora gira su una
  **copia** di `hub.db`, e la copia lo dimostra a fine giro.

---

## 13/08/2026

**Il backlog potato in due**

- ✅ **`BACKLOG.md` da 1967 a ~370 righe** (144 KB → 30 KB, il **21%**): dentro resta solo
  ciò che è aperto, più le trappole. Le voci chiuse sono diventate questo file, una riga
  per lavoro. Tolti i doppioni contati: i cinque bachi piccoli dell'11/08 stavano anche in
  «Emerso dal codice», le quattro voci di regulation comparivano sia chiuse sia nella
  versione «com'erano state aperte», le abilità doppie in tre punti, Mega Machamp in tre
  sezioni. Corrette due voci **stale**: «`main` diverge da `origin/main`» (riallineati
  l'11/08) e «`reference.html` è noto come orfano» (rimosso l'11/08).

**Switch lingua — il secondo blocco, l'interfaccia**

- ✅ **La sezione Pokémon è tradotta: 12 template su 12**, dizionario a **383 chiavi su
  383 chieste**, zero mancanti, zero orfane, zero doppie. `calcolatori.html` (142 stringhe)
  coi 7 moduli `calcolatori-*.js`, `moves_editor` (52), `roster_editor` (26),
  `items_editor` (43), `abilities_editor` (47), `regulations_list` (33),
  `regulation_editor` (42), `team_form`, `base.html`.
- ⚠️ **`team_form.html` non era nel censimento delle 453 stringhe** del 12/08: buco del
  conteggio, non una scelta. Recuperato.
- ✅ **`tf()` esiste ora anche in Jinja**, gemella di quella in `base.html`. Prima stava
  **solo nel JS**, ed è il motivo per cui «1 team salvati» era rotto: nei template le
  frasi coi numeri si spezzavano in due pezzi che nessun dizionario può rimettere
  nell'ordine inglese. Il plurale è chiuso **senza** insegnare i plurali a `tf()`: la
  frase italiana è ora `Team salvati: {n}`, che non si flette in nessuna delle due lingue.
- ✅ **Quali sezioni si traducono: Pokémon e Gaming, e basta.** Deciso da Davide dopo due
  ripensamenti nella stessa giornata — prima il pulsante ovunque con la shell tradotta,
  poi solo Pokémon, infine Pokémon **e Gaming**, «alla fine è ciò che conta anche per gli
  utenti non admin». Arduino, Python, PC Builder, Dashboard, login e utenti restano in
  italiano, **e la sidebar con loro**: il pulsante compare solo dove la sezione è
  tradotta, e con una shell inglese chi andasse su Arduino resterebbe senza un modo per
  tornare indietro. L'elenco è `sezioni_tradotte` in `base.html`, unico punto da toccare.
- ✅ **Gaming tradotto**: `gaming.html`, `game_form.html`, `steam_import.html` e le frasi
  dei suggerimenti in `gaming.py`. Dizionario da 383 a **489 chiavi**.
  ⚠️ **Stati e piattaforme sono valori salvati** in `games.status`/`games.platform` e
  finiscono negli URL dei filtri: il valore resta italiano, si traduce solo l'etichetta.
  In `game_form.html` le `<option>` **non avevano un `value`** — il testo *era* il valore
  inviato — quindi tradurle senza aggiungerlo avrebbe salvato «Paused» al posto di
  «Pausa». Verificato: in inglese il filtro «On hold» chiama `?status=Pausa` e trova i
  suoi **33 giochi**.
- ✅ **Anche le categorie di oggetti e abilità seguono la lingua** (segnalato da Davide).
  Erano ferme su due livelli diversi: negli oggetti metà erano parole inglesi lasciate lì
  (`Berry`, `Healing`, `Orb`), nelle abilità le **chiavi grezze** (`weather_override`).
  La mappa chiave → etichetta italiana sta ora in `data.py` e passa da `categorie()` in
  `extensions.py`: **una sola sorgente** per le tendine, i badge delle tabelle e la
  colonna Info del catalogo, dove prima erano tre elenchi scritti a mano. La chiave resta
  il dato, e sul badge è rimasta come `title`.
- ⚠️ **Trovato traducendo: `other` non era fra le categorie degli oggetti**, ed è **339
  voci su 397** — l'86% del catalogo. Il badge cadeva sulla chiave grezza e quella
  categoria non si poteva filtrare. Aggiunta. Resta aperto che la tendina ne offre **6
  che non hanno nemmeno una voce**: vedi i bachi noti.
- ✅ **`controlla_traduzioni.py` legge anche `blueprints/`**: da quando alcune frasi
  nascono in Python, senza quella cartella le loro voci nel dizionario sarebbero sembrate
  **orfane** e qualcuno le avrebbe cancellate. ⚠️ In Python le frasi vanno su **una riga
  sola**: la concatenazione implicita (`"a" "b"`) veniva troncata al primo pezzo.
- ✅ **I tipi si traducono solo a schermo**: il `value` delle tendine resta italiano perché
  è la chiave di `TYPE_CHART` e `TYPE_CLR_IT`. Le abbreviazioni della tabella di
  riferimento seguono la lingua (Norm/Fire/Wate in EN), verificato che a 4 lettere non
  nasca nessuna collisione.
- ✅ **Due cose corrette anche in italiano**, senza le quali «tradotto» sarebbe stata una
  bugia: lo Stat Preview mostrava i tipi coi nomi inglesi grezzi di `/api/pokemon`
  (`Grass/Poison` invece di `Erba/Veleno`) e le abilità con la chiave inglese.

**Il baco che Davide ha trovato, e la lezione**

- ⚠️ ✅ **La tabella dell'editor mosse era vuota — regressione introdotta lo stesso
  giorno.** `t()` e `tf()` stavano in fondo a `base.html`, ma `moves_editor.html` chiude
  il suo script con `renderTable()`, che gira **durante il parsing**: la chiamata trovava
  `tf is not defined`, l'eccezione moriva dentro lo script della pagina e le **919 righe**
  sparivano **senza dire niente**. Ora `window.T`, `t()` e `tf()` sono in un `<script>` nel
  **`<head>`**, quindi esistono prima di qualunque script di un figlio: tolta la classe di
  baco, non solo il caso.
- ⚠️ **La lezione, che vale più della correzione: lo sweep statico non basta.**
  `new Function()` su script e handler dava **zero errori** mentre la tabella era vuota,
  perché la sintassi era valida e a lanciare era il runtime. Da oggi ogni giro si chiude
  **caricando davvero le pagine e contando le righe** che compaiono.
- ⚠️ ✅ **`|tojson` dentro un attributo a doppie**, la stessa trappola del 12/08, rifatta e
  ripresa dallo sweep. Corretta con gli apici singoli.

**Gli editor che non seguivano la lingua**

- ✅ **Segnalato da Davide provando la web app**, e il quadro era **il rovescio esatto sui
  tre editor**: mosse (`Absorb`) e oggetti (`Black Belt`) sempre in inglese — 10 chiavi su
  919 e 37 su 397 coincidono col `nome_it` — e **abilità sempre in italiano**, perché lì
  le chiavi *sono* italiane (`Abillegame` ha `nome_en: Skill Link`): **386 su 386**. Una
  correzione scritta pensando «la chiave è inglese» avrebbe sistemato due editor e
  peggiorato il terzo. Ora il nome tradotto in grande e **la chiave sotto**, perché è
  l'identità della voce e quello che si scrive nel JSON lì accanto. Estesi anche ricerca e
  ordinamento al nome tradotto. `catalog_editor` sistemato **lato server**: `_riga_indice()`
  già distingueva `nome` da `chiave`.
- ✅ **`nomeVis()`, `tipoIT()`, `tipoVis()` e `TIPI_EN_IT` deduplicati** nel `<head>` di
  `base.html`, una copia sola: servivano anche agli editor, che i moduli del calcolatore
  non caricano. Tolte le copie in `calcolatori-data.js` (`nomeVis`, `LANG`,
  `TYPE_EN_TO_IT`) e in `calcolatori-core.js`.

**Decisioni prese da Davide**

- ✅ **Le descrizioni restano in italiano** (13/08/2026). Contate prima di decidere:
  **1584 `desc`** fra mosse (823), oggetti (378) e abilità (383), di cui 1458 con una
  controparte ufficiale su cui pescare. Davide ha scelto di **non tradurle**: «facilitano
  il tutto». Quindi in inglese si legge un nome inglese con sotto una descrizione
  italiana, **ed è previsto** — `desc_en` non esiste e non va aggiunto. I **nomi** restano
  bilingui al 100%.

**Strumenti**

- ✅ **`controlla_traduzioni.py` trova ora le chiavi doppie.** Non poteva vederle: usa
  `json.load()`, che **tiene l'ultima e butta la prima in silenzio**, quindi correggere la
  traduzione sbagliata non cambierebbe niente a schermo. Il controllo legge il file
  grezzo. Ne aveva già accumulate **6**, e ne ha prese altre **2** al primo giro dopo.

**Aperto dalla giornata**

- ⬜ **Il calendario delle uscite** per Gaming, chiesto da Davide: `games` non ha nessuna
  data di uscita (`date_start`/`date_end` sono quando *hai giocato*), e le uscite future
  non vanno in quella tabella. Fonti da verificare: IGDB, RAWG; su Opera GX **non risulta
  un'API pubblica documentata**.

---

## 12/08/2026

**Dati Pokémon**

- ✅ **Elenchi mosse per specie importati** — `scripts/importa_mosse_specie.py`, dal **dump
  CSV** di PokéAPI (un file da 10 MB invece di 1026 chiamate) in `data/catalog/pokemon_moves.json`
  (2,7 MB), idempotente. Era il buco più grosso rimasto: **0 specie su 1026** avevano un
  elenco mosse, e non ce l'aveva nemmeno il vecchio `pokemon_catalog.json` (0 su 174).
  **Scoperta che ha cambiato il lavoro: Champions è nel dump** come version group a sé
  (id 32, 19 810 righe su 319 voci). Quindi ogni voce ha **due elenchi**: `main` (il
  version group più recente in cui compare) per `pokedex`, e `champions` per `ma`/`mb`.
  **Non coincidono**: Incineroar in Champions non ha Knock Off — 11 mosse in meno e 8 in
  più, 80 contro 77. Copertura: `ma` 274/279, `mb` 302/308, `pokedex` 1323/1343, **zero
  nomi irrisolti**. Il valore di ogni mossa dice *come* si impara (`level-up:32`,
  `machine`, `egg`, `tutor`, `train`). Canarino: Magikarp ha 3 mosse e Fulmine non c'è.
- ✅ **32 forme Gigantamax ereditano dalla base**, dichiarandolo con `eredita_da`: il
  Gigantamax è una trasformazione temporanea, non un learnset a sé — ed è il motivo per
  cui il dump non le elenca. `Charizard (Gigantamax Form)` ha le stesse 75 mosse di Charizard.
- ✅ **`Pawmot` chiarito**: è un **buco del dump**, non un errore nostro. In Champions ci
  sono solo le evoluzioni finali (Charizard sì, Charmander no), e di Pawmi/Pawmo/Pawmot
  mancano tutti e tre. Resta senza elenco con l'avviso giallo: assegnargli il moveset dei
  giochi principali non sarebbe legale su Champions.
- ✅ **Abilità del catalogo completate** — `scripts/completa_abilita_pokemon.py`: **182 voci,
  +184 abilità**, quasi tutte **nascoste** (a Venusaur mancava Chlorophyll, a Pikachu
  Lightning Rod). Le voci con una sola scendono da 411 a 325, e **323 ne hanno davvero una
  sola** anche per PokéAPI (Mega e forme regionali). Il backlog diceva «238 quasi certamente
  incomplete»: era vero solo per 182 su 411. Solo in aggiunta, mai in rimozione.
- ✅ **`mega_map` di `pokedex`** — `completa_mega_map.py` insegnato a leggere `roster: null`
  come «tutto il catalogo»: **91 basi, 97 Mega, 97 su 97 raggiungibili**. 7 forme inventate
  risolte a mano invece che indovinate (`BASE_A_MANO`, e il suffisso `Z` aggiunto alla
  regola di X e Y).
- ✅ **Mega Zygarde deconvertita** con la formula standard → `216/70/91/216/85/100`, BST 778.
  Non era «rotta a sé»: lo script cercava la firma `+75 HP` contro la sola voce di testa
  (Zygarde 50%, 108 HP) mentre era convertita dalla **Complete Forme** (216 + 75 = 291).
  Ora la firma si cerca contro **tutte le forme non-Mega** della specie.

**Interfaccia Pokémon**

- ✅ **Le mosse mostrate seguono la regulation** — campo `moveset` in `regulations.json`
  (`main` su `pokedex`, `champions` su `ma`/`mb`), `load_moveset()` con cache sull'mtime,
  `/api/pokemon/<nome>?reg=`. Il datalist è l'**intersezione** fra le mosse della regulation
  e quelle dell'attaccante. Misurato: `pokedex` 919 → 80 con Knock Off; `ma`/`mb` 460 → 61
  senza. Tre stati sotto la casella (elenco noto · mossa diventata illegale, segnalata e
  **non cancellata** · nessun elenco, tutte mostrate).
- ✅ **Team builder — il datalist mosse non aveva mai funzionato**: `fetchPkmn()` leggeva
  `d.moves`, che `/api/pokemon` **non ha mai restituito**. Ora cambiando regulation gli slot
  già compilati si rifanno chiedere le mosse: Incineroar 80 → 61.
- ✅ **Le meccaniche del team builder erano morte** — `/api/regulation/<id>/data` non
  restituiva `regulation`, quindi `CURRENT_MECHANICS` era **sempre vuoto** e **nessuna Mega
  era selezionabile su nessuna regulation**. Non bastava aggiungere il campo: `MEGA_MAP` era
  una `const` stampata da Jinja al caricamento. Ora l'endpoint restituisce anche `mega_map`
  e la costante è `let`: da `pokedex` a `ma` passa da 0 a 58 voci, Charizard offre le due Mega.
- ✅ **Speed Tier — mossa di potenziamento e stage** (−6/+6, impostato dalla mossa ma non
  bloccato: uno stage può arrivare da un Coaching alleato). Il dato non c'era: **0 mosse su
  919** dicevano quanti stage muovono, importato con `importa_variazioni_stat.py` — **174
  mosse arricchite, 22 alzano la Velocità**. Dragapult 162 → **243** con Dragodanza (×1.5),
  **324** con Agilità (×2). Baco trovato provando: cambiando Pokémon lo stage restava e
  Incineroar mostrava 160 invece di 80. `stageMult()` spostata in `calcolatori-data.js` per
  non averne due copie.
- ✅ **Ogni Pokémon mostra solo le sue abilità** nel tab Danno e nello Stat Preview (lo Speed
  Tier era già il modello): da **387 voci a 2** per Venusaur, 3 per Amoonguss, 4 per Torkoal.
  Spunta *«mostra tutte»* per riquadro, che serve per le abilità inventate di Champions.
  Chi non ha abilità in catalogo tiene la tendina piena; l'abilità che sparisce dall'elenco
  viene **azzerata**, non lasciata come `value` invisibile.

**Utenti, sicurezza, dati**

- ✅ **Utenti e permessi per sezione** — `/admin/utenti`. Il controllo è un `before_request`
  su `request.blueprint` in `app.py`, non un decoratore per vista: **una route nuova nasce
  protetta**. `users.sections` vuota vale «tutte» (nessuno perde accessi), «nessuna» si
  scrive `-` perché `",".join([])` dava la stringa vuota, cioè l'opposto. Non ci si può
  declassare o eliminare da soli, e deve restare almeno un admin. **24 controlli su 24.**
- ⚠️ ✅ **Due falle chiuse nello stesso giro**, senza le quali i permessi erano decorativi:
  `/export` restituiva **l'intero database** a chiunque avesse fatto login (28 KB con dentro
  `teams` e `pc_builds`); la **Dashboard** mostrava conteggi e ultimi elementi di ogni
  sezione. Ora entrambi rispettano le sezioni permesse.
- ✅ **Password migrate a scrypt** (erano sha256 **senza sale**). Non esiste migrazione in
  blocco — sha256 è a senso unico — quindi si riconosce il vecchio hash **al login**, unico
  istante in cui la password in chiaro esiste. ⚠️ Un pezzo si sarebbe rotto in silenzio:
  `login()` confrontava l'hash **dentro il `WHERE`**, cosa che con un sale casuale non
  avrebbe trovato nessuno. **14 controlli su 14.**
- ✅ **Dashboard ridotta alle sezioni dell'utente**: un riquadro a zero dice comunque che
  quella sezione esiste. `admin` vede 5 riquadri e 3 pannelli, un solo-Gaming ne vede 1 e 1.

**Gaming**

- ✅ **Filtri e ordinamento** — genere, piattaforma, cinque ordinamenti, contatore «N su M»,
  e i pulsanti di stato **portano con sé** ricerca e filtri. Tre dettagli: `genre` è una
  lista separata da virgole, quindi il confronto è per sottostringa **con le virgole ai
  bordi**; `NULLS LAST` non esiste in SQLite; l'`ORDER BY` viene da un dizionario del
  codice, mai dalla richiesta (`?sort=pippo'--` ricade sul default).
- ✅ **Suggerimenti dalla libreria stessa** — Steam non espone «giochi simili» e inventarla
  sarebbe un dato finto. Il punteggio di un genere condiviso è `log(N/quanti_ce_l_hanno)`,
  così i generi rari contano: senza, direbbe solo «ti piace l'azione» (23 giochi su 33).
  Sotto `log(2)` **non suggerisce e spiega perché**, invece di riempire la fila.
- ✅ **Tag da SteamSpy** — `appdetails` di Valve non espone i tag e la pagina del negozio è
  dietro il controllo dell'età. **33 giochi in 35 secondi, 24 con tag e 9 senza**; da 17
  generi a **108 tag distinti**, 56 su un solo gioco. I tag sono solo in inglese.
- ⚠️ ✅ **I 33 giochi persi, e la guardia che ora c'è** — l'11/08 fra le 10:09 e le 10:43 i
  giochi sono spariti da `hub.db` (904.8 ore), ed `esporta_dati.py` ha esportato fedelmente
  il vuoto **sovrascrivendo l'unica copia buona**. Non recuperati per decisione di Davide.
  Ora lo script **si rifiuta di scrivere** se una tabella crolla da N righe a **zero**
  (`--anche-se-vuoto` è la via d'uscita esplicita), e ha il `sys.stdout.reconfigure` senza
  cui l'avviso moriva su `UnicodeEncodeError` per via dell'emoji.
- ✅ **«Non trovo GTA VI»: la ricerca funziona.** GTA VI non ha una pagina Steam — escluse
  misurando sia il filtro del negozio italiano (`total=0` anche con `l=english&cc=us`) sia
  l'ipotesi dei non ancora usciti (Silksong compare). Steam non capisce le abbreviazioni:
  `GTA VI` dà 0, `Grand Theft Auto` ne dà 7.
- 📌 Da sapere sul dato: `Monster Hunter Wilds Beta test` non ha generi (Steam non li dà
  alle beta), `Wallpaper Engine` porta categorie *software*, tutti e 33 i giochi sono in
  «Pausa» con `hours_hltb` vuota, e i titoli con `®`/`™` sono corretti nel DB (è la console).

---

## 11/08/2026

- ✅ **`pokedex` è il default del sito** — i 14 letterali `"ma"` spariti, sostituiti da
  **`regulation_default()` in `data.py`**, che restituisce la prima regulation di
  `regulations.json`: per cambiare default si sposta una voce in cima al registro. Misurato:
  `/api/moves` da 461 a **921**, oggetti da 58 a **398**, roster del team builder da 279 a **1343**.
- ✅ **Niente più JSON per regulation**: i tre input `roster_file`/`moves_file`/`items_file`
  compaiono solo sulle regulation non migrate, e spariscono anche dal salvataggio. Su `ma`
  i percorsi legacy restano conservati.
- ✅ Titolo della sezione Pokémon reso generico (e caduti gli altri «Reg MA» scritti a mano
  che il cambio di default avrebbe reso falsi a schermo); Catalogo a sinistra del Calcolatore.
- ⚠️ ✅ **Tre endpoint che il JS chiamava e che non esistevano** — `GET /api/regulations`,
  `POST /api/regulations/save` e la chiamata sbagliata di `team_form.html`. Conseguenze
  reali: **💾 Salva Metadati non ha mai salvato niente** (404 → `catch` → «Errore rete»), e
  la **tendina Regulation del team builder** falliva in un `catch(e){}` muto, quindi non si
  è mai potuta scegliere la regulation di un team. Il salvataggio ora rifiuta registro
  vuoto, non-lista, senza `id`/`label`, con id duplicati o che perderebbe una regulation:
  5 payload rifiutati su 5.
- ✅ **Stat delle Mega riportate alle base** — non avevano un bonus, avevano le **stat di
  Lv.50 già calcolate** dentro `base_stats`: con la formula del progetto la conversione vale
  esattamente **+75 HP e +20 sulle altre**, ed è per questo che 95 su 101 avevano +75 mentre
  nel gioco una Mega non cambia gli HP. **95 deconvertite** con `deconverti_mega_catalogo.py`;
  `MEGA_DATA` eliminata da `calcolatori-data.js` (−35 KB). Conferma indipendente: le 11 Mega
  **assenti** da `MEGA_DATA` ma ufficiali (Metagross, Mewtwo X/Y, Rayquaza…) coincidono
  tutte coi valori reali. Chiude il bug per cui Mega Venusaur valeva 80 di Velocità nel tab
  Danno e 100 nello Speed Tier (formula applicata due volte).
- ✅ **Il resto del catalogo NON è convertito**, verificato: Shedinja 1 HP, Chansey 250,
  Magikarp `20/10/55/15/20/80`, 20 specie note su 20, 200 specie su 1026 con HP sotto 50, e
  nessuna forma non-Mega con la firma +75.
- ✅ `Mega Froslass` riportata a 120 (era già una base, la deconversione le aveva tolto 20 di
  troppo); `Mega Machamp` **non esiste** e la forma è stata rimossa; 3 chiavi top-level
  (`mega-banette`, `mega-chimecho`, `mega-crabominable`) erano **doppioni** della forma
  annidata: 1029 → 1026 voci.
- ⚠️ ✅ **`/api/regulation/<id>/data` leggeva il vecchio `roster_file`** — `ma` 208 nomi e
  **0 Mega**, `pokedex` e `mb` **404 con caduta muta** sulla lista statica da 158. Ora
  chiama `_load_roster()`: `ma` 279 con 59 Mega, `pokedex` 1344, `mb` 295.
- ⚠️ ✅ **L'alias che rispondeva con un Pokémon a caso** — `_costruisci_indice()` registrava
  come alias il primo pezzo di ogni chiave col trattino, quindi `mega`, `alolan`, `galarian`,
  `hisuian`, `totem`, `iron`, `tapu`, `paldean`: **qualsiasi nome inventato che iniziasse
  così riceveva le stat di un Pokémon estraneo** invece di un 404 (`Mega Machamp` →
  Mega Venusaur). Ora c'è `NON_ALIASABILI`, e dei 295 nomi usati dalle regulation **zero**
  dipendevano da quegli alias.
- ✅ **`Galarian Darmanitan`** risolve: delle **57** voci regionali **56** usano il prefisso
  e una sola la parentesi. Il nome in catalogo non è stato toccato — la differenza si colma
  con un alias nell'indice, e `Galarian Machamp` / `Alolan Pippo` restano 404.
- ✅ **`completa_mega_map.py`** — MA da 58/59 a **59/59**, MB da 58/75 a **75/75** (roster
  295 → 308). `Mega Meowstic (Male)` era irraggiungibile e la voce di backlog **era
  sbagliata**: cercava `Meowstic`, ma in roster ci sono `Meowstic (Male)` e `(Female)`. Per
  MB, Davide ha deciso di aggiungere 13 specie base al roster — scelta di contenuto, quindi
  lo script la fa solo per le regulation in `AGGIUNGI_BASI`: **il roster di MA non si tocca**.
- ✅ **Mosse e oggetti di MB restano quelli di MA** (460 e 58): finché non c'è una fonte su
  cosa cambi davvero, copiare MA è l'ipotesi meno arbitraria. La differenza fra le due
  regulation resta il **roster**.
- ✅ **Switch lingua IT ⇄ EN, primo blocco** — nomi dei dati (Pokémon, mosse, abilità,
  oggetti). Le chiavi non cambiano mai; la lingua sta in un **cookie** (`hub_lang`) perché
  la deve leggere anche Flask; il pulsante **ricarica** la pagina di proposito; si può
  scrivere in entrambe le lingue (`risolviChiave()` / `_INDICE`). Bandiera in **SVG inline**,
  non emoji: su Windows le emoji bandiera si leggerebbero «IT» e «GB».
- ✅ **Import dei nomi, due giri** — `importa_nomi_lingua.py` (PokéAPI, ⚠️ 403 senza
  `User-Agent`): mosse 899/921, oggetti 378/398, abilità 312/415, Pokémon 1019/1026. Poi
  `importa_nomi_wiki.py` (wiki di Pokémon Central) chiude i buchi: **32 mosse su 32** (le 18
  mosse Z, `Syrup Bomb`, `Blood Moon`…) e **57 oggetti su 57** (`Booster Energy` →
  Capsula energetica, le maschere di Ogerpon, i Mochi). Dove le due fonti non concordano lo
  script **segnala e basta**: 11 voci, decise a mano con `applica_nomi_decisi.py` — due nomi
  davvero diversi passano alla wiki (`Sferapulsar`, `Curapulsar`), tre abbreviazioni vanno
  in forma estesa, sei sono **refusi della wiki** e non si toccano.
- ✅ **`Mirror Herb` → «Foglia carbone» confermato** su Bulbapedia, fonte indipendente. Il
  giapponese ものまねハーブ e lo spagnolo *Hierba Copia* dicono che è la localizzazione
  italiana a essere strana, non il nostro dato. «Erba Speculare» sulla wiki **non esiste**.
- ⚠️ ✅ **Le abilità doppie — 24 coppie fuse**, 415 → 391 voci. **Il guasto era più grosso
  della fusione**: il catalogo cita le abilità col nome **inglese** (`Swift Swim`) mentre le
  chiavi sono italiane (`Nuotovelox`), e `abilityEffect()` faceva match esatto sulla chiave —
  dei **307** nomi posseduti dai Pokémon, **zero** arrivavano a un effetto. Nel tab Danno
  non si vedeva (tendina piena, scelta a mano), ma nello **Speed Tier** nessun effetto si
  applicava mai: **Kingdra sotto pioggia con Swift Swim restava a 105 invece di 210**.
  Servivano entrambe le metà — risoluzione per chiave/IT/EN **e** fusione — e da sole non
  bastavano. Dopo: Kingdra **105 → 210**, 307 nomi su 307 risolvono (erano 7). Le coppie
  **non sono state indovinate**: l'accoppiamento automatico per somiglianza proponeva
  `Combattività` → `Bruciaimpeto`, quindi ognuna è mappata a mano sull'abilità reale che il
  suo `effect` descrive. Sulle 7 coppie dove anche la voce ufficiale aveva un effetto, i due
  blocchi erano **identici 7 su 7**.
- ✅ **8 voci che condividevano il nome con un'altra chiave** — il caso grave era
  `Sheer Force`, presente come `Forza Bruta` (con l'effetto) e `Forzabruta` (inerte):
  vincendo l'ultima, un Pokémon con Sheer Force **non applicava niente** (danno 82 invece di
  106). Fuse con `fondi_doppioni_nome.py`, tenendo la **chiave giusta** e non «il nome
  ufficiale», che su `King's Rock` darebbe la voce sbagliata. I filtri sono stati aggiornati:
  MA e MB avevano entrambe le varianti di `Freeze Dry`, quindi le mosse scendono da 461 a
  **460** — la stessa mossa contata due volte, non una persa.
- ✅ **Le 10 abilità senza corrispondente ufficiale** (`Nervosismo`, `Sforzo`, `Tiratore`,
  `Manto Neve`…) **non sono state toccate** per decisione di Davide: accoppiarle vorrebbe
  dire decidere che il loro effetto è sbagliato. Ognuna ora **lo dice nella propria
  descrizione** («— abilità di Champions, senza corrispondente ufficiale»).
- ✅ **`ABILITIES_CALC` rimossa** da `data.py` dopo aver verificato **zero consumer**: chi
  marca le abilità che incidono è `abilityIncideSulDanno()`, che legge il blocco `effect`.
- ✅ **Il fallback `data/abilities.json` riallineato** (408 → 386): non è stato dismesso, ma
  ha smesso di essere una macchina del tempo che avrebbe riportato indietro i doppioni.
- ⚠️ ✅ **`/pcbuilder/` rispondeva 500** — `sqlite3.Row` grezza passata a `|tojson`: la
  sezione era **inaccessibile** appena c'era una build salvata, e nel DB ce n'è una. Ora
  `dict(b)`; il modale Modifica carica `ZAFFO-PC` coi suoi 5 componenti.
- ⚠️ ✅ **53 `onmouseout` morti in `python.html:45`** — il ramo `{% else %}` produceva
  `this.style.background=''''`, un `SyntaxError`: su ogni argomento non completato
  l'handler era `null`. Da **0 su 53 a 53 su 53**.
- ✅ **`loadSpePkmn()` non ricalcolava**: riempiva `spe_base` senza chiamare `updateSpeed()`,
  quindi la Velocità restava `—` e la tabella si confrontava col valore precedente.
- ✅ **L'eliminazione di una regulation lasciava il filtro orfano** — `data/regulations/<id>.json`
  restava sul disco mentre la modale prometteva di averlo cancellato. Ora è nell'elenco, e
  prima di toglierlo se ne tiene una copia in `data/archive/`: ricostruire 279 nomi scelti a
  mano è la perdita che l'archivio esiste per evitare.
- ✅ **Speed Tier con un tetto a 300 righe** — su `pokedex` erano 1343 righe / 714 KB in un
  solo `innerHTML`, ora 300 / 159 KB. Le righe tagliate sono le più **lontane** dalla
  propria Velocità, il conto pieno resta scritto sopra e la ricerca pesca fuori dal taglio.
- ✅ **`reference.html` rimosso**: 70 righe che nessuna route renderizzava.
- ✅ Colonne del tab Danno allineate (`align-items: stretch`): 548/699/564 px → tutte a 699.

---

## 10/08/2026

- ✅ **Regulation MA allineata a Pokémon Champions** — roster dalla wiki di Pokémon Central,
  **208 → 279 Pokémon**, Speed Tier 279 su 279 senza nomi irrisolti, con
  `importa_roster_champions.py`. La wiki **non scrive il nome della forma**: la distingue
  per tipi e codice sprite (`Minim0026A` = Raichu di Alola), e lo script **si ferma** su ciò
  che non risolve. Le forme puramente estetiche (Vivillon, Florges, Furfrou, Alcremie: 40
  righe) sono collassate sulla base. Baco preso al volo: **«Meganium» inizia per «Mega»** e
  finiva nel ramo delle Mega — ora quel ramo si attiva sul suffisso dello sprite.
- ⚠️ **Nota che vale ancora**: in una sessione precedente avevo giudicato «sospetto» quel
  roster perché mancavano Amoonguss, Rillaboom e Urshifu e c'erano Arbok e Audino. **Era
  sbagliato**: Champions ha un roster suo. Non applicare assunzioni da VGC standard.
- ✅ **Catalogo unico completato** — doppioni unificati (erano **solo 3**, il trio
  `Tauros (X Breed)`), e **6 `ALIAS` che non puntavano a nulla** riparati: erano esattamente
  i 6 nomi che lo Speed Tier non risolveva. Nota di metodo: cercare i doppioni per «stessi
  tipi e stesse stat» dava 17 gruppi quasi tutti falsi (i nuclei di Minior, i costumi di
  Pikachu); il segnale giusto erano le forme **senza `slug`**, cioè quelle scritte a mano.
- ⚠️ ✅ **`/api/moves` ignorava la regulation** — leggeva `moves_ma.json` hardcoded e
  `loadMovesDB()` sovrascriveva le mosse corrette arrivate dal bootstrap: sul Pokedex si
  passava da **921 a 461**.
- ✅ **Editor del catalogo separato** (`/pokemon/catalogo`, quattro linguette): modifica una
  voce per volta via API invece di scaricare 449 KB di JSON, con archivio, ripristino e
  copia automatica prima di ogni salvataggio. **31 controlli end-to-end.**
- ✅ **Schermata contenuti** `/pokemon/regulation/<id>/contenuto?db=…`: si spunta quali voci
  del catalogo appartengono alla regulation, con selezione di massa che agisce su **tutti i
  filtrati** e non solo sulle righe visibili, e la casella «includi anche quelle future»
  che scrive `null`. **24 controlli** sul ciclo completo.
- ✅ **Clonare una regulation** — «Parti da» in creazione e «📋 Copia contenuti» su una già
  creata. `id` e `label` non vengono mai sovrascritti. **20 controlli end-to-end.**
- ✅ **`mega_map` di MA e MB**: 53 → 57 basi, Mega irraggiungibili da 6 a 1, e `Mega Machamp`
  rimosso perché mappato ma fuori roster (il team builder offriva una Mega non legale).
- ✅ **`.gitignore` creato** e `hub.db` + 13 `.pyc` tolti dall'indice. Gli archivi in
  `data/archive/` sono **rimasti tracciati** di proposito: sono la rete di sicurezza.
- ✅ `textarea.form-control` batteva `.code-area` per specificità: i template colpiti erano
  **5, non 3** (anche il campo codice Arduino era a 70px invece di 260).

---

## 08/08/2026

- ✅ **Catalogo unico + regulation come filtro** — `data/catalog/` con 1032 specie + 321
  forme, 921 mosse, 398 oggetti, 415 abilità; le regulation contengono **solo elenchi di
  nomi** (`null` = tutte). MA identica a prima. **29 controlli su 29.**
- ⚠️ ✅ **Archivio e backup delle abilità** — `_save_abilities()` sovrascriveva senza tenere
  nulla: un salvataggio sbagliato azzerava 408 abilità, incluse le 56 con `effect`. Ora
  copia automatica a scorrimento, archivio manuale, elenco e ripristino; il salvataggio
  **rifiuta** un `abilities` vuoto e mostra la differenza di conteggio; il ripristino
  respinge `../../app.py`. **18 controlli**, con ripristino a **md5 identico**.
- ⚠️ ✅ **Terreni: boost legato alla categoria sbagliata** — elettrico e psichico agivano
  solo sulle speciali, erboso solo sulle fisiche, mentre nel gioco dipende **solo dal tipo
  della mossa**: Wild Charge in terreno elettrico misurava 68 → 68, ora 68 → 88.
- ⚠️ ✅ **Il critico non ignorava gli stage** sfavorevoli a chi attacca: critico contro
  Difesa +2 dava **52 invece di 102**, con Attacco −2 dava **51 invece di 102**.
- ✅ **Reflect e Light Screen col valore delle singole** (×0.5) in un calcolatore che ha già
  lo spread a 0.75, cioè una meccanica esclusiva delle doppie. Ora `SCHERMO_DOPPIE` =
  2732/4096 ≈ ×0.667, in un punto solo.
- ✅ **`calcolatori.html` spacchettato** — **1885 → 687 righe, 222 → 38 KB, zero JS inline**:
  CSS in `static/css/`, JS in 7 moduli `calcolatori-*.js` caricati in ordine obbligato
  (`data` → `core` → `ui`). I dati di Flask passano da un blocco `<script type="application/json">`.
- ✅ **Tabelle di riferimento deduplicate** — 4 righe da 108 KB di HTML incollato diventate 4
  `<div>` riempiti da `calcolatori-ref.js` **dagli stessi dati del calcolo**: prima potevano
  divergere in silenzio dal motore che documentano. **0 disaccordi su 324 celle**, e l'HTML
  generato è **identico byte per byte** all'originale (45911 e 9820 byte).
- ⚠️ ✅ **`extra_head` di `base.html` stava dentro `<style>`**: il primo `</style>` di ogni
  figlio chiudeva lo stile di base, lasciando un `</style>` orfano in tutte e 10 le pagine.
  Il CSS funzionava per caso; un `<link>` veniva ignorato come testo CSS.
- ✅ **Motore meteo** — Weather Ball (tipo dal meteo, BP 50→100), Solar Beam e Solar Blade
  dimezzate con pioggia/sabbia/neve, abilità `weather_setter`/`weather_override`, Pioggia
  forte che porta le mosse Fuoco a 0. **12 casi su 12**; Sole/Pioggia sulla stessa mossa
  Fuoco = 153/51 = ×3 esatto. Il campo `weather_ball_type`, presente su 7 abilità e mai
  letto da nessuno, è finalmente in uso.
- ⚠️ ✅ **Speed Tier muto** — `loadRegSpeed()` leggeva `bst.spe` invece di `base_stats.spe`:
  **174 Pokémon su 174 scartati** e caduta silenziosa sulla lista statica da 158 nomi.
- ⚠️ ✅ **Ripristino roster senza conferma** — nell'`onsubmit`, `verra'` produceva un
  apostrofo dentro la stringa a singoli apici: l'handler era un `SyntaxError`, `form.onsubmit`
  era `null` e **il roster veniva sovrascritto senza chiedere niente**.
- ✅ **Editor abilità**: la voce di backlog era **stale**, era già tutto implementato e
  funzionante. Verificato eseguendolo su tutte le 408 abilità.
- ✅ **24 condizioni di danno misurate in browser** una per una: STAB, terreni, scottatura
  (×0.5 solo sulle fisiche, ×1.5 con Guts), schermi, Helping Hand, critico, e gli accumuli
  (HH + critico = ×2.25 esatto, scottatura + Reflect = ×0.25, spread ×0.75).

---

## 07/08/2026

- ⚠️ ✅ **`SyntaxError` che azzerava tutto il JS di `calcolatori.html`** (merge rotto alle
  righe 718-729): **nessuna riga della pagina veniva eseguita**, quindi fino a quel giorno
  nessuna funzione del calcolatore era mai stata realmente provata in browser.
- ✅ **Formula stat incoerente** — Speed Tier usava `ev*2`, Danno e Stat Preview `floor(ev/4)`:
  stesso Pokémon, numeri diversi. Ora entrambi `ev*2` (convenzione Champions).
- ✅ **Motore abilità data-driven** che legge il blocco `effect`: prima **nessuna abilità
  funzionava**, perché le tendine erano in italiano e il codice confrontava nomi inglesi.
- ✅ `ABILITIES_DATA` a doppio encoding; sprite da 96 nomi irrisolti su 300 a 296/300 risolti
  e 0 immagini rotte; pulizia di `PKMN_DB`, `calc_stat_champions()`, una `switchTab`
  duplicata, 816 `<option>` Jinja inutili e la mappa tipi ripetuta 5 volte.
- ⚠️ ✅ **5 bug trovati dal grafo (graphify)**, tutti della stessa famiglia — una riga
  malformata che azzera un intero blocco: apici singoli in `pcbuilder.html:202` (**tutto lo
  script del PC Builder morto**: tab, modali, import DxDiag), `calcDmg()` inesistente,
  `deleteMove` contro `removeMove`, `startEditDesc(el)` che riceveva una stringa, un `"` di
  troppo in `roster_editor.html`.
