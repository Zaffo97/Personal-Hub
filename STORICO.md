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

## 21/09/2026

**Fantacalcio: le fondamenta dei dati (§4.2)**

La sezione era un segnaposto dal 10/09/2026 — «solo il titolo, e finché resta così non
si scrive codice». Davide l'ha definita: inserire la formazione avendo tutti i
giocatori di Serie A, le probabili dei propri giocatori, un consiglio, e le regole di
**due leghe**, tutte e due **Classic**, con le regole **strutturate**.

- ✅ **Le fonti, cercate prima di scrivere e tutte su un sito solo.** Le tre pagine di
  `fantacalcio.it` (l'ex Fantagazzetta) sono **renderizzate dal server**, quindi si
  leggono con `requests` + `HTMLParser` **senza login**: quotazioni (597 giocatori,
  ruolo Classic e Mantra, QI/QA/FVM), statistiche (gli stessi 597, media voto,
  fantamedia, gol, assist, cartellini) e probabili formazioni (761 voci, il modulo di
  ogni squadra, 20 ballottaggi). ⚠️ Il download **Excel** del listone invece pretende
  un account — `/api/v1/Excel/prices/21/1` risponde **401** — e leggere le pagine
  evita anche di mettere credenziali nel progetto.
- ✅ **Si incrociano per `id`**: ogni giocatore porta il suo id numerico nell'URL,
  uguale in tutte e tre le pagine. Il nome è abbreviato (`Martinez L.`) e legarli per
  nome sarebbe la stessa classe di baco già pagata sul catalogo Pokémon.
- ✅ **Cosa c'è**: `fantacalcio_it.py` legge e basta, `scripts/importa_listone.py` è
  l'unico che scrive, più `blueprints/fantacalcio.py`, due template e la voce in
  sidebar. Nel DB: il listone condiviso (`fanta_players`, 597 voci), le leghe con le
  regole in colonne (`fanta_leagues`) e le rose (`fanta_roster`).
- ✅ **Il mercato, che Davide ha chiesto di mettere subito**: `importa_listone.py
  --scarica` è rieseguibile, e chi esce dalla Serie A viene **spento, non cancellato**
  — cancellarlo porterebbe via la riga di rosa che lo nomina. Lo script dice quanti
  degli spenti sono **in una tua rosa**, e la pagina li mostra col cartellino «fuori
  listone». Provato: secondo giro a 0 nuovi, 0 aggiornati, 0 spenti.
- ⚠️ **Solo tre valori vengono dal regolamento ufficiale**, letto lo stesso giorno: gol
  +3, ammonizione −0,5, espulsione −1 (e i cartellini si fermano a −1 comunque
  combinati). Assist, gol subito, porta inviolata, rigori e autogol il regolamento
  **non li fissa**, perché cambiano da lega a lega: i default sono convenzionali e la
  scheda della lega lo dichiara campo per campo.
- ⚠️ **Due trappole trovate costruendo, e tutte e due danno «tutto a posto» quando non
  lo è.** (1) `controlla_proprietario.py` cerca le query **per nome di tabella** e
  `sweep_pagine.py` ha un **elenco di URL scritto a mano**: una sezione nuova non è in
  nessuno dei due e tutti e due dicevano «0 problemi» **senza averla guardata** —
  allargando il raggio sono saltate fuori **4 query scoperte**, poi dichiarate. (2)
  Passare `None` a una colonna con un `DEFAULT` **scavalca il default**: una lega
  nuova nasceva coi bonus a `NULL` invece che a +3, e l'ha presa la prova al primo
  giro.
- ✅ **L'export**: `fanta_leagues` e `fanta_roster` sono entrate in `esporta_dati.py` e
  in `importa_dati.py` — sono dati che nessuna fonte ricostruisce. Il listone no, si
  rifà in un minuto; ⚠️ la conseguenza è che un ripristino su un DB vuoto va fatto
  **dopo** aver reimportato il listone.
- ✅ **Verifiche**: `prova_fantacalcio.py` **26 su 26** (fra cui: un secondo utente non
  vede, non modifica, non cancella e non tocca la rosa altrui; un modulo che non fa 10
  viene rifiutato; un campo vuoto non azzera; chi esce dal listone resta in rosa e lo
  dichiara). Più `controlla_proprietario.py` a **93 query, 0 scoperte**, lo **sweep a 0
  errori** sulle due pagine nuove in tutte e due le lingue, e le altre nove suite
  rieseguite — 224 controlli in tutto. Le pagine vere rese sul listone importato: 597
  giocatori dichiarati a schermo con la data.
- ⚠️ ✅ **La voce Fantacalcio in sidebar portava al PC Builder** (trovata da Davide
  cliccandola, lo stesso giorno). Il blocco `{% if 'fantacalcio' … %}` era finito
  **dentro l'attributo `class`** del link PC Builder, che non veniva mai chiuso: il
  parser fondeva i due `<a>` in uno solo con `href="/pcbuilder"`, quindi il testo
  «Fantacalcio» era cliccabile ma portava altrove. ⚠️ **Lo sweep non lo vedeva**: rende
  le pagine e controlla il **JavaScript**, non che l'HTML sia ben formato, e infatti
  era a 0 errori anche col link rotto. Ora verificato con un parser HTML sulla pagina
  resa: **9 voci di menu**, ognuna col suo `href`, e 19 `<a>` con 19 chiusure.

---

**Le due Mega Meowstic: un dato sbagliato teneva fuori una voce vera**

- ⚠️ **Il difetto**: erano le ultime due voci del catalogo senza `slug`, e il backlog le
  dava per forme che PokéAPI non conosce. Il dump invece le ha — `meowstic-male-mega` e
  `meowstic-female-mega` — **con 59 e 56 righe di mosse**. Lo slug mancava perché
  `aggiungi_slug_forme.py` si **rifiutava** di scriverlo: le sei base stat della femmina
  non combaciavano. E non combaciavano perché la voce era rimasta a **466**, cioè al
  totale di Meowstic femmina **normale**: la conversione a Mega non le era mai stata
  applicata. Il rifiuto era il verso giusto — uno slug plausibile ma sbagliato darebbe
  l'elenco mosse di un altro Pokémon senza un errore — ma nessuno era andato a vedere
  **perché** rifiutava.
- ✅ **Tre fonti concordi**, cercate su richiesta di Davide: il **dump**
  (`meowstic-female-mega` = 74/48/76/143/101/124), **Pokémon Database** (maschio e
  femmina hanno le stesse base stat, 466, e le due Mega condividono i 566) e
  **RotomLabs**, che ha una pagina apposta per la Mega femmina e dà gli stessi valori.
- ✅ **Corretto da `scripts/correggi_mega_meowstic.py`**, rieseguibile e con `--dry-run`:
  si rifiuta di scrivere se la voce non ha esattamente i valori vecchi attesi, se il dump
  non conferma i nuovi, o se non combaciano con quelli della Mega maschio già nel
  catalogo. Rieseguito, dice «ha già i valori di Champions» e non tocca niente.
- ✅ **Poi la catena**: `aggiungi_slug_forme.py` ha scritto i due slug con le **sei base
  stat combaciate 6 su 6**, `importa_mosse_specie.py` ha dato loro le liste e
  `importa_evoluzioni.py` l'esito. Ogni Mega prende esattamente la lista del **suo**
  genere: Mega Meowstic maschio 59 come Meowstic maschio, femmina 56 come la femmina.
- ✅ **Numeri**: `champions` da 368 a **370 voci** e da 22 863 a **22 978 mosse**; le
  voci del moveset da 1331 a **1333**; `puo_evolversi` da 1340 a **1342 su 1342**. E il
  risultato che si vede: **MA e MB non hanno più nessuna voce senza elenco mosse** —
  erano 1 e 2, ed erano queste. Gli elenchi delle regulation restano 492 e 494, perché
  quelle mosse erano già nell'unione.
- ✅ **Verifiche**: 40+19+16+30+32+9+11+21 su altrettanti, `controlla_abilita.py` pulito,
  `controlla_proprietario.py` senza query scoperte, **sweep di tutte le pagine a 0
  errori**, idempotenza del moveset in processi separati.

---

**Le 6 Mega di Regulation M-C hanno la loro lista, e la fonte c'era (§2.3)**

- ✅ **Davide ha chiesto di cercare prima se una fonte esiste, e esisteva.** Bulbapedia
  non dà un blocco alle Mega — le tratta come la specie, ed è per questo che
  `integra_moveset_bulbapedia.py` si rifiutava di integrarle. **Pokémon Zone** invece ha
  una pagina **per ogni Mega**, con la sua tabella «Learnable Moves». Confrontate tutte
  e sei con la lista della loro specie: **6 su 6 identiche**, stesso conteggio —
  Golisopod 67, Absol 72, Salamence 62, Garchomp 59, Lucario 83, Baxcalibur 51. L'unica
  differenza di testo era `Mud-Slap` contro `Mud Slap`, che è l'alias di nome già noto.
  Serebii dice la stessa cosa dall'altro verso: una **lista sola** per Absol, Mega Absol
  e Mega Absol Z.
- ✅ **Scritte come `eredita`, la terza sezione di `moveset_integrazioni.json`**: la
  lista non si duplica, si **dichiara derivata**. `applica_eredita_dichiarata()` gira
  **dopo** le toppe, così copia la lista finale della specie, e il dump vince — se un
  domani PokéAPI riempirà `mega-dimension`, l'eredità verrà detta **superata**.
- ⚠️ **Il primo giro ne applicò una su sei, e non lo disse**: cinque delle sei Mega non
  avevano **nessuna voce** nel moseset, perché `costruisci_moveset()` lascia fuori del
  tutto chi non ha righe nel dump. Ora la voce si crea, col suo slug preso dal catalogo.
  Il rapporto dell'import non le conta più fra le «conosciute dal dump ma senza nemmeno
  una mossa», che da 14 sono scese a **9** — e quelle 9 sono le Mega di Leggende Z-A,
  reali ma in Champions non ancora presenti, quindi è giusto che restino senza.
- ✅ **Numeri**: `champions` da 362 a **368 voci** e da 22 469 a **22 863 mosse**; le
  voci del moveset da 1326 a **1331**. `verifica_moveset.py`: **358 identiche su 368**,
  0 voci che Bulbapedia ha e il dump no.
- ✅ **Verifiche**: `prova_champions_1_2_0.py` **40 su 40** (sezione nuova sulle 6 Mega:
  la lista combacia, ognuna dichiara `eredita_da` e la fonte, e **non** si sono prese
  anche la `main` della specie — a cinque su sei non spetta, nei giochi principali non
  esistono). Più 19+16+30+32+9+11+21 sulle altre suite, `controlla_abilita.py` pulito,
  idempotenza in processi separati, MA 492 e MB 494 invariate.

---

**Regulation M-C, Morpeko e una seconda fonte per tutto il resto (§5.2, §2.3)**

Richiesta di Davide: fare le 25 voci di Regulation M-C, e **verificare sempre con siti
affidabili** (Serebii, Smogon, Game8) se esistono già delle fonti. È la richiesta che ha
trovato tutto il resto.

- ✅ **Le 25 voci di M-C sono integrate.** Le liste vengono da Bulbapedia; il **roster**
  è confermato da **Serebii** e da **Game8**, che elencano le stesse 26 specie (le 25 più
  Pawmot, già fatto il 14/09) e 6 Mega. `champions` passa da **333 a 362 voci** e da
  20 721 a **22 469 mosse**. `verifica_moveset.py`: le voci «Bulbapedia ha la lista, il
  dump no» passano da **25 a 0**, e le identiche sono 352 su 362.
- ✅ **Il controllo incrociato**, che è il punto: le **liste** vengono da Bulbapedia, i
  **cambi** li elenca Game8, e le due fonti non si copiano. **8 su 8**: Golisopod ha
  *Close Combat*, *U-turn* e *Gunk Shot* e non ha più *Knock Off*; Indeedee Femmina ha
  *Sing* e *Terrain Pulse*; Grapploct ha *Mach Punch*; Wigglytuff ha *Moonblast*.
- ✅ **E il dump ne esce confermato su Regulation M-B**: dei **10 cambi di roster** che
  Game8 elenca per M-B, il dump li ha **tutti e 10 giusti** — Swampert ha *Wave Crash*,
  Sceptile *Earth Power*, Scolipede *Leech Life* e *Trailblaze*; Gholdengo e Grimmsnarl
  non hanno *Thunder Wave*, Metagross non ha *Heavy Slam* né *Knock Off*, Scrafty non ha
  *Parting Shot*, Overqwil non ha *Mortal Spin*, Annihilape non ha *Final Gambit*.
- ✅ **Dei 27 dati di mossa confrontabili con Game8, 26 combaciavano.** L'unico scarto è
  **Growth**, che in Champions è di tipo **Erba**: Bulbapedia non lo cita nella sezione
  «Changes from Scarlet and Violet», ed è per questo che il 18/09 era rimasto Normale.
  Confermato anche da Serebii e corretto. È la dimostrazione del perché una fonte sola
  non basta: qui la prima taceva.
- ⚠️ **E Game8 sbaglia una riga, il che vale quanto le altre**: dice «Annihilape lost
  Pound», ma **Annihilape non impara *Pound* in nessun gioco** — né Mankey né Primeape —
  mentre **Politoed sì**, a livello 1. La nota di Bulbapedia su Politoed regge e la
  toppa del 18/09 era giusta. Nessuna fonte è sempre giusta: si incrociano.
- ✅ **Morpeko (Hangry Mode) è chiuso**, ed era l'ultima voce aperta del §5.2. Davide ha
  chiesto di cercare una terza fonte prima di decidere, e la terza fonte c'era:
  **Serebii** e **Game8** danno una **lista unica** per Full Belly e Hangry, con dentro
  le cinque mosse che nel dump mancavano alla Hangry, e dicono esplicitamente che
  l'unica cosa che dipende dalla forma è il **tipo di Aura Wheel**. Ora 65 e 65, zero
  differenze. ⚠️ Scritta in `TOPPE_A_MANO` **dentro lo script**, non nel JSON: quella
  sezione `applica_toppe_champions.py` la **riscrive per intero**, e una toppa aggiunta
  a mano sarebbe sparita al giro dopo in silenzio.
- ⚠️ **«PokéAPI non la conosce» quasi mai voleva dire «è inventata».** Il rapporto
  dell'import stampava 16 voci sotto quella frase e il backlog le chiamava «forme di
  Davide»: **falso per 14 su 16**. I loro slug — `darkrai-mega`, `absol-mega-z`,
  `golisopod-mega`, … — sono **tutti in `pokemon.csv`**. Quello che manca sono le righe
  di mosse, perché i loro unici giochi sono `legends-za` e `mega-dimension`, i due
  version group che nel dump hanno **zero righe**: gli stessi che stamattina sono
  finiti in `VG_FUORI_SERIE`. E **cinque di quelle 14 sono Mega vere di Regulation M-C**
  (Absol Z, Garchomp Z, Lucario Z, Golisopod, Baxcalibur), confermate da Serebii e
  Game8; le altre sono Mega di **Leggende Z-A**, reali ma non ancora in Champions. Le
  sole due che PokéAPI davvero non conosce sono le **Mega Meowstic**, senza slug. Il
  rapporto dell'import ora stampa i due gruppi separati, con l'etichetta giusta.
- ⚠️ **Un difetto trovato dalla prova scritta stamattina**: integrando le 25 voci,
  **quattro forme Gigantamax** — Cinderace, Inteleon, Rillaboom, Toxtricity — sono
  rimaste senza la lista nuova della loro specie, pur dichiarando `eredita_da`. Causa:
  l'eredità è costruita **prima** che integrazioni e toppe entrino, e aggiungere un
  blocco nuovo alla specie non raggiunge la copia. Chiuso con `riallinea_forme_eredi()`,
  che gira dopo le due in tutti i percorsi che scrivono il file.
- ✅ **Verifiche**: `prova_champions_1_2_0.py` **37 su 37** (tre sezioni nuove: M-C,
  Morpeko, Growth), `prova_moveset_main.py` 19 su 19, `prova_mosse_regulation.py` 16 su
  16, `prova_import_specie.py` 30 su 30, `prova_regulation_nuova.py` 32 su 32,
  `prova_build_catalog.py` 9 su 9, `prova_catalogo_vivo.py` 11 su 11,
  `prova_esporta_completo.py` 21 su 21, `controlla_abilita.py` pulito. Idempotenza in
  processi separati. `allinea_mosse_regulation.py --dry-run`: MA 492 e MB 494 invariate,
  perché nessuna voce di M-C è in un roster.
- ⬜ **Cosa resta aperto**: le **6 Mega di M-C** (Salamence, Absol Z, Garchomp Z,
  Lucario Z, Golisopod, Baxcalibur) sono in Champions ma **senza lista**, e lo script si
  rifiuta di integrarle perché Bulbapedia **non ha un blocco per le Mega** — le tratta
  come la specie. Decisione di Davide.

---

**Le toppe della 1.2.0 arrivano anche alle forme (§5.2)**

- ⚠️ **Il difetto, trovato da `verifica_moveset.py`**: le toppe erano scritte come elenco
  di **33 chiavi di specie**, e si fermavano lì. **19 forme** di quelle specie — Mega
  Absol, Mega Charizard X e Y, Mega Gallade, Aegislash (Blade Forme), Mimikyu (Busted
  Form), … — erano rimaste senza lo *Slash* della 1.2.0, e Mega Mawile senza *Charm*,
  *Draining Kiss* e *Misty Terrain*. **Tutte e 19 sono in MA e in MB**: a schermo Absol
  poteva scegliere Slash e Mega Absol no, cioè lo stesso Pokémon a metà partita. Nessun
  errore, solo la tendina più corta.
- ✅ **La prova che non era una differenza vera**: **19 su 19** erano copie **esatte**
  della lista della loro specie, a parte le mosse che la toppa nomina. Prima del 18/09
  forma e specie avevano la stessa lista; è stata la toppa a separarle.
- ✅ **La cura sta in `applica_toppe_moveset()`**, cioè in **un punto solo** per tutti e
  quattro i percorsi che applicano le toppe (import in blocco, import dal pannello,
  `applica_toppe_champions.py`, le prove). Una toppa raggiunge le forme della specie, ma
  **solo** quelle la cui lista — tolte le mosse che la toppa nomina — è **identica** a
  quella della specie. Il confronto ignora le mosse nominate di proposito: regge sia sul
  file appena rigenerato dal dump (dove nessuna delle due ce l'ha) sia su uno già toppato
  a metà (dove la specie sì e la forma no), e resta idempotente.
- ✅ **Una forma con una lista sua non viene toccata e viene dichiarata**: finisce nel
  terzo valore di ritorno, che l'import stampa. Oggi quell'elenco è **vuoto**, perché
  l'unica forma con una lista propria fra le 33 specie toppate — Hisuian Samurott — una
  toppa sua ce l'ha già.
- ✅ **Numeri**: `champions` da 20 700 a **20 721 mosse** (+21: 18 *Slash* più le 3 di
  Mega Mawile), toppe applicate da 33 a **52 voci**. Il giro di `verifica_moveset.py`
  passa da **26 forme con differenze a 8**, e le 8 rimaste hanno tutte già una
  spiegazione: 5 Rotom (Bulbapedia mette le mosse di ogni forma sulla pagina unica),
  Mega Blaziken e Mega Gardevoir (rispecchiano il troncamento noto della pagina della
  specie) e **Morpeko (Hangry Mode)**, che resta l'unica domanda aperta.
- ✅ **Verifiche**: `prova_champions_1_2_0.py` **28 su 28** — il conto di *Slash* non è
  più «29 secco» ma **29 voci nominate + 19 forme**, più un terzo controllo che nessuna
  forma di una specie con Slash sia rimasta indietro: era quello a valere zero, ed era
  proprio il difetto. Più `prova_moveset_main.py` 19 su 19, `prova_mosse_regulation.py`
  16 su 16, `prova_import_specie.py` 30 su 30, `prova_regulation_nuova.py` 32 su 32,
  `prova_build_catalog.py` 9 su 9, `prova_catalogo_vivo.py` 11 su 11. Idempotenza in
  processi separati, e `allinea_mosse_regulation.py --dry-run` con MA 492 e MB 494
  invariate (le mosse c'erano già nell'unione, mancavano alle singole forme).

---

**Il blocco `main` del moveset non è più rotto, e resta (§5.2, §5.3)**

- ✅ **La decisione di Davide prima dei numeri**: «in questo momento non mi interessa altro
  se non Pokémon Champions, la base dati di tutti i pokemon, le mosse, oggetti e abilità
  deve comunque esserci per poter costruire facilmente una nuova regulation in futuro».
  Delle tre strade che il backlog lasciava aperte — sistemarlo, toglierlo dalla tendina,
  lasciarlo dichiarato — è l'unica che le tiene insieme: `main` resta nel file e nella
  tendina, e smette di dire il falso.
- ✅ **Il difetto, riformulato dopo la misura**: non era «Leggende Arceus dà poche mosse»,
  era che un gioco col **sistema di mosse ridotto vince perché è più recente**. `main`
  prende l'ultimo version group in cui la voce compare, e per **77 voci** quello era
  Leggende Arceus (58) o Let's Go (19). Abra aveva **una** mossa — `Teleport` — contro le
  **49** di Brillante Diamante.
- ✅ **La cura**: `VG_FUORI_SERIE` esclude `colosseum`, `xd`, `lets-go-*` e
  `legends-arceus`, e li usa **solo come ripiego** per chi non compare altrove. Misurato
  sul file riscritto: **74 voci** cambiano gioco, `main` passa da **68 030 a 70 755 mosse**
  (+2725), **0** voci restano su Leggende Arceus, e su un gioco fuori serie restano solo
  **Partner Pikachu e Partner Eevee**, che in nessun altro gioco esistono — presi lo
  stesso, e il rapporto dell'import li **nomina**. Perdono mosse solo Silcoon e Cascoon
  (3 → 1), e quell'1 è onesto: in Brillante Diamante imparano davvero solo *Rafforzatore*.
- ✅ **`legends-za` e `mega-dimension` sono nell'elenco pur avendo zero righe**, ed è il
  punto: hanno order **30** e **31**, cioè stanno **sopra** Scarlatto/Violetto (27). Il
  giorno che PokéAPI li riempie diventerebbero da soli la sorgente di centinaia di voci
  senza che nessuno abbia toccato niente. Il rapporto dell'import stampa quante specie e
  quante mosse ha **ognuno** degli esclusi, con un `<- vuoto oggi, sorvegliato` su quelli a
  zero: così smettere di essere vuoto è una notizia, non un numero sbagliato.
- ✅ **Una regola sola per due scrittori.** La stessa scelta la faceva anche
  `pokeapi.moveset()`, l'import dal pannello, con una seconda copia del `max(candidati)`:
  una specie importata da lì sarebbe nata col difetto appena chiuso. Ora `VG_FUORI_SERIE` e
  `scegli_vg_main()` stanno in `pokeapi.py` e l'import in blocco **li importa**, non li
  ricopia — la prova controlla l'**identità** delle due funzioni, non che si somiglino.
- ⚠️ **Trovato di passaggio e dichiarato, non nascosto**: rigenerando il file, `champions`
  è passato da 20 699 a **20 700** mosse. La differenza è una sola voce,
  `Charizard (Gigantamax Form)`, che guadagna *Slash*. Causa provata: in
  `costruisci_moveset()` l'eredità Gigantamax è una copia **superficiale**, quindi la Gmax
  e la sua base **sono lo stesso dizionario** e la toppa della 1.2.0 le tocca tutte e due;
  `applica_toppe_champions.py`, che il 18/09 aveva scritto il file lavorando sul JSON dal
  disco, le aveva invece lasciate disallineate. Il verso giusto è questo — `eredita_da`
  dichiara che la lista **è** quella della base — e ora `prova_moveset_main.py` lo
  controlla su tutte e 32 le forme che ereditano.
- ✅ **Verifiche**: `scripts/prova_moveset_main.py` **19 su 19** (nuovo), più le suite già
  esistenti rieseguite — `prova_champions_1_2_0.py` 27 su 27, `prova_mosse_regulation.py`
  16 su 16, `prova_import_specie.py` 30 su 30, `prova_regulation_nuova.py` 32 su 32,
  `prova_build_catalog.py` 9 su 9, `controlla_abilita.py` pulito. **Idempotenza provata in
  processi separati** (stesso md5 su due giri), che è l'unico modo di vedere l'ordine
  randomizzato dei `set`. `allinea_mosse_regulation.py --dry-run`: MA 492 e MB 494
  invariate, niente da riscrivere. In `prova_champions_1_2_0.py` il conto di *Slash* non è
  stato alzato da 29 a 30: è stato **spezzato** in «29 voci scelte» più «le forme che
  ereditano», così un 30 che diventasse 31 per un'altra ragione fallisce lo stesso.
- ⚠️ **Non toccati**: template e JavaScript, quindi niente sweep; il calcolatore, quindi la
  regola #8 non è stata rieseguita — a schermo l'unica differenza è lo *Slash* sulla Gmax
  di Charizard nel Pokedex, perché tutte e tre le regulation leggono `champions`.

---

## 18/09/2026

**L'export completo del DB, quello che un backup deve essere (§1.4)**

- ✅ **Due export, non uno.** `esporta_dati.py` resta com'era e scrive il file
  committabile senza password; **`--completo --uscita <percorso>`** scrive il backup vero,
  con gli **hash delle password** e la tabella `regulations` — 10 tabelle su 11. Fuori
  resta solo `game_releases`, la cache IGDB da 6007 righe che si rifà col pulsante, e i
  due dati che nel DB non ci sono proprio: il tema (`localStorage`) e la lingua (cookie).
- ✅ **Nessun percorso di default, ed è la parte importante.** `--completo` pretende
  `--uscita` e **si rifiuta** di scrivere se, risalendo l'albero dalla destinazione, trova
  un `.git`: provato che rifiuta `data/backup/`, che rifiuta anche una sottocartella
  profonda come `data/archive/giu/ancora/`, e che in nessuno dei due casi lascia il file.
  Un default «comodo» dentro al repo verrebbe committato al primo `git add -A` distratto,
  ed è lo stesso buco per cui `hub.db` non è versionato. Seconda rete in `.gitignore`.
- ✅ **Il ritorno era già pronto e non è stato toccato quasi per niente**: `importa_dati.py
  --file <percorso>` rilegge il completo, le password entrano **solo** per gli utenti
  nuovi e quelle già nel DB non si toccano mai. Ora però dice **quale dei due export** ha
  letto, con due messaggi diversi: «rientrati senza password» dopo un backup completo
  sarebbe **falso**, e manderebbe a reimpostare a mano password appena rientrate giuste.
- ⚠️ ✅ **Il conflitto scoperto scrivendo la prova**: `regulations.created_at` lo scrive
  `init_db()` **al momento**, quindi due DB creati a secondi di distanza hanno la stessa
  riga con una data diversa — e il ripristino si **fermava**, su una tabella morta, per un
  timestamp, lasciando come unica uscita `--sovrascrivi`, cioè abituando a usare proprio
  il flag pericoloso. Ora quella colonna è in `MAI_SOVRASCRITTE`. ⚠️ La prova passava o
  falliva a seconda che i due `init_db()` cadessero nello stesso secondo: ora la
  differenza di data si **crea apposta**, così misura la regola e non l'orologio.
- ✅ Verificato: `scripts/prova_esporta_completo.py` **21 prove su 21**, ognuna su un DB
  suo creato da `init_db()` in una cartella temporanea — giro completo export → import con
  l'utente che rientra **con la sua password**, quella di `admin` già presente intatta,
  secondo import che non scrive. `prova_importa_dati.py` resta **20 su 20**, sweep 0
  errori, `controlla_proprietario.py` 0 query scoperte.

---

**Il Pokedex passa alle mosse di Champions, e i due controlli di §5.2 hanno una risposta**

- ✅ **I metodi: il dump non gonfia le MT, e non è un'impressione.** Scaricato `machines.csv`
  dallo stesso dump di PokéAPI e confrontate, gioco per gioco, le mosse insegnate da
  `machine` col **catalogo MT del gioco stesso**: **23 version group su 24 coincidono
  esatti** — 55 in Rosso/Blu, 57 in Oro/Argento, 58 in Rubino/Zaffiro, 100 in Diamante/Perla,
  101 in Bianco/Nero, 105 in X/Y, 107 in ORAS, 200 in Spada/Scudo (MT+MN), **229 in
  Scarlatto/Violetto** coi DLC. L'unico scarto è **BDSP**, dove `machines.csv` dichiara 17
  macchine contro 100 usate: è un buco di quel file, che noi non leggiamo.
- ⚠️ **Il campione sulla lista `main` ha trovato un difetto senza seconda fonte**: per
  **77 voci** l'ultimo gioco in cui compaiono è **Leggende Arceus** (58) o **Let's Go** (19),
  due giochi col sistema di mosse ridotto. Media **7,4 mosse** contro 56,3 di
  Scarlatto/Violetto, **1063 in tutto invece di 4562**. **Abra aveva una mossa sola**
  (Teleport), Mr. Mime 8, Mega Mewtwo X e Y 49 invece di 99.
- ✅ **Decisione di Davide: «voglio solo ciò che imparano in Champions».** `pokedex` passa da
  `moveset: main` a `champions`, un campo solo in `data/regulations.json`. **333 voci su 1342**
  hanno l'elenco vero; le altre **1009** prendono l'avviso giallo «nessun elenco mosse: sono
  mostrate tutte» e la tendina da 919 — la stessa risposta onesta che prendono le forme
  inventate, invece di un elenco preso da un gioco che non c'entra. Abra non ha più la
  tendina da una riga: non ha tendina.
- ⚠️ **Conseguenza da tenere a mente**: il caso della **regola #8** gira su `pokedex` con
  **Amoonguss**, che in Champions non c'è — quindi ora mostra l'avviso giallo. È previsto, e
  il danno si calcola lo stesso perché la mossa si scrive a mano. Misurato dopo il cambio:
  **85-102 = 38.5%–46.2%**, identico.
- ⚠️ **E il blocco `main` non lo legge più nessuno**: 1293 voci e la maggior parte dei 3 MB
  del file. Candidato per l'inventario del §5.3, ma `sorgenti_moveset()` lo offre ancora alla
  creazione di una regulation, quindi non si toglie senza decidere.
- ✅ Verificato: `prova_champions_1_2_0.py` **26 su 26** (5 controlli nuovi sul Pokedex),
  `prova_mosse_regulation.py` 16/16, e 30/30 + 9/9 + 11/11 + 32/32 sulle prove esistenti,
  sweep 0 errori. In browser: Abra 919 mosse con l'avviso, **Incineroar 77 anche in
  `pokedex`**, regola #8 invariata.

---

**Le liste di Champions portate alla versione 1.2.0, e i dati mossa con loro (§5.2)**

- ✅ **La fonte che ha sciolto i quattro punti aperti non era la pagina learnset**: è la
  **nota ufficiale di aggiornamento della 1.2.0** (9 settembre 2026), citata in «Pokémon
  Champions#Version history» su Bulbapedia. È una **lista chiusa** dei cambi di mossa —
  Politoed non può più usare *Pound*, Archaludon né *Mirror Coat* né *Metal Burst*,
  *Slash* «can now be used», PP di *Wish* e *Strength Sap* da 12 a 8 — e dice anche che
  la 1.2.0 ha aggiunto il roster di **Regulation M-C**, cioè le 25 voci che il dump non ha.
- ✅ **Applicate 33 voci**: *Slash* a **29**, le tre rimozioni, *Psychic Fangs* al posto di
  *Psychic* su Ariados, e le quattro mosse mancanti a Mawile e Houndstone. Lo fa
  `scripts/applica_toppe_champions.py`, che **non contiene un elenco di nomi**: ricostruisce
  il confronto con le 232 pagine Bulbapedia in cache e **si ferma** su ogni differenza che
  non sia in `DECISIONI` (con motivo e fonte) o in `IGNORATE`. Ha riconosciuto tutte e 35
  le differenze del rapporto del 14/09, zero indecise.
- ✅ **Livello nuovo, `toppe`**, in `moveset_integrazioni.json`: aggiunge e toglie **singole
  mosse** sopra una lista che il dump **ha già**, mentre `voci` sostituisce una lista intera
  e solo dove il dump non ne ha una. Le riapplica `applica_toppe_moveset()`, chiamata dalle
  stesse due strade che rigenerano `pokemon_moves.json` — senza, una mossa tolta a mano
  tornerebbe al giro dopo senza errori. Una toppa su una voce senza lista **non ne inventa
  una**, e una che non serve più viene detta **superata**.
- ⚠️ ✅ **Il difetto trovato provando lo script su sé stesso**: con le toppe già applicate la
  differenza sparisce, quindi il secondo giro avrebbe scritto `toppe: {}` **cancellando il
  proprio lavoro in silenzio**. Ora `disfa_toppe()` riporta le liste allo stato del dump
  prima di misurare — lossless, perché nelle liste `champions` il metodo è `train` su tutte
  le 20 699 righe. Due giri completi: **stesso md5** su tutti e due i file.
- ⚠️ ✅ **Trovato per strada: i dati delle mosse erano di Scarlatto/Violetto, non di
  Champions.** La sezione «Changes from Scarlet and Violet» elenca una trentina di
  ribilanciamenti; delle 29 misurabili il catalogo ne aveva **17 già giuste e 12 no**.
  Corretti da `scripts/allinea_dati_mosse_champions.py`: *Slash* 70→**80**, *Grav Apple*
  80→**90**, *Meteor Assault* 150→**170**, *Snipe Shot* 80→**85**, *Crabhammer* 90→**95**,
  *Syrup Bomb* 85→**90**, *Make It Rain* precisione **95** e Att.Sp. **−2**, *Toxic Thread*
  Velocità **−2**, *Snap Trap* da Erba ad **Acciaio**, *Freeze-Dry* che non congela più,
  *Dire Claw* slicing e *Double Shock* punch. Il blocco **commentato** della pagina
  («not in the game yet»: Gear Grind, Anchor Shot, Hyper Drill…) è lasciato fuori di
  proposito, e i PP non hanno dove andare — 0 mosse su 919 hanno quel campo.
- ⚠️ ✅ **Altri due difetti trovati misurando il proprio diff**, tutti e due muti.
  Lo script scriveva con `indent=2` mentre i due scrittori di `pokemon_moves.json`
  usano `indent=1`: **100 000 righe di diff per 33 voci**, cioè una modifica
  illeggibile in revisione — ora sono **102**. E iterava un **set** di nomi, il cui
  ordine cambia da processo a processo perché l'hash delle stringhe è randomizzato:
  due giri scrivevano lo stesso contenuto in ordine diverso. Si vedeva **solo**
  confrontando l'md5 fra processi separati. Ora `sorted()` ovunque e i dizionari
  delle mosse riordinati alla fine: **tre giri, stesso md5** su tutti e due i file.
- ✅ **L'elenco derivato si è aggiornato da solo**, che era il punto: rilanciato
  `allinea_mosse_regulation.py`, *Slash* è entrata e *Pound* è uscita dalle liste di MA e MB
  senza toccarle a mano (492 e 494, invariate nel totale).
- ✅ Verificato: `scripts/prova_champions_1_2_0.py` **21 su 21**, `prova_mosse_regulation.py`
  **16 su 16**, più `prova_import_specie` 30/30, `prova_build_catalog` 9/9,
  `prova_catalogo_vivo` 11/11, `prova_regulation_nuova` 32/32 (il 460 scritto dentro è
  diventato 492), `controlla_abilita` a posto, sweep **0 errori**. In browser: regola #8
  invariata su `pokedex` (85-102 = 38.5%–46.2%), Absol 72 mosse con **Lacerazione** che
  autocompila **BP 80** e calcola 56-66 su Rillaboom, Politoed 56 senza *Pound* (che non è
  più nemmeno nel `MOVES_DB` di MA), Archaludon 50 senza *Mirror Coat* e con *Slash*.

---

**L'elenco mosse di MA e MB non era quello di Champions: era il dump di maggio (§3)**

- ⚠️ ✅ **Il filtro `moves` nascondeva 3239 mosse legali su 17219 in MA**, 3583 su 19039
  in MB, su **278 specie su 278** e **306 su 306**: 11,7 a testa, e nessun avviso da
  nessuna parte. La tendina del calcolatore è l'intersezione fra l'elenco della
  regulation e la lista del singolo Pokémon (`loadMovesDB()`), quindi una mossa fuori
  dalle 460 spariva in silenzio. Peggiori: Hisuian Zoroark 50/73, Mega Gallade e Gallade
  84/105, Hawlucha 54/74, Infernape 68/88. **Crunch** non compariva su Incineroar, e
  **Pawmot mostrava 51 mosse invece delle 64** integrate da Bulbapedia quattro giorni prima.
- ✅ **Le 460 non erano un elenco di legalità, ed è dimostrato da due parti opposte.**
  Erano le chiavi di `data/moves_ma.json` (04/05/2026, «PokeAPI + patch Champions Reg
  M-A (Serebii)»), diventate il filtro l'11/08 con la costruzione del catalogo. Mancavano
  **Endure** e **Substitute**, che **332 voci di Champions su 333** imparano; e
  contenevano **126 mosse che nessuna voce di Champions impara**, comprese le esclusive di
  Pokémon che nel gioco non ci sono (Behemoth Bash, Bolt Beak, Defend Order). La «patch
  Champions» inoltre non ha lasciato traccia: confrontati i 460 record con
  `catalog/moves.json` su `type`, `category`, `bp` e `priority`, **una sola differenza su
  460**, ed è `Freeze Dry` scritto senza trattino — per quello l'elenco era 460 e non 461.
- ✅ **Decisione di Davide**: «i cataloghi saranno sempre di Champions, quindi la lista
  mosse sarà sempre quella in relazione alla regulation». L'elenco non è più un dato
  curato: lo **deriva** `scripts/allinea_mosse_regulation.py` dall'unione delle mosse del
  roster secondo la sorgente `moveset` dichiarata in `regulations.json`. **MA 460 → 492**
  (+159 / −127), **MB 460 → 494** (+161 / −127). Nessuna fonte nuova è servita: tutte e
  164 le mosse mancanti avevano già la voce in `catalog/moves.json`.
- ✅ **Le 127 che escono non tolgono niente a nessuno**: le specie con una lista hanno per
  costruzione le loro mosse dentro l'unione, e le uniche che ricadono sull'elenco della
  regulation sono **Mega Meowstic (Male)** e **(Female)**, che una lista non ce l'hanno —
  e per loro l'elenco passa da 460 a 492, cioè ne guadagnano.
- ✅ **MA e MB non sono più identiche per la prima volta**: differiscono di due mosse,
  `No Retreat` e `Topsy-Turvy`, che arrivano da specie presenti solo nel roster di MB.
  Non è una copia, è una differenza dedotta dai dati.
- ✅ Lo script si **rifiuta** di scrivere se una mossa dell'unione non ha una voce nel
  catalogo, se l'unione esce vuota, se un nome del roster non esiste, o se una mossa che
  uscirebbe è usata da un team salvato (guardia provata su una **copia** di `hub.db`:
  vede `Absorb` messa in un team di MA). Ha `--dry-run`, lascia la copia in
  `data/archive/regulation_<id>_pre-mosse.json` ed è rieseguibile — al secondo giro dice
  «già allineato» e non tocca i file.
- ✅ Verificato: `scripts/prova_mosse_regulation.py` **16 controlli su 16**, con **0 mosse
  nascoste** su 17219 e 19039 e **0 voci orfane** su 492 e 494; sweep **0 errori** su 27
  pagine per due lingue; `pokedex` invariata con `moves: null`.

---

## 14/09/2026

**Gli oggetti del calcolatore davano il numero sbagliato da giugno, su tutte le regulation (§3)**

- ⚠️ ✅ **La tendina «Item ATK» faceva `A × modifier` qualunque fosse l'oggetto**, e la
  tendina «Item DEF» controllava solo il valore `'av'`, che nessuna voce aveva. Nessun
  errore a schermo: il numero era solo sbagliato. Misurato nel calcolatore vero sul
  caso della regola #8 (85-102 senza oggetti): **Carbonella** su una mossa Buio dava
  **102-120**, **Stolascelta** dava **127-150**, **Elettropalla** raddoppiava l'Attacco a
  chiunque, e le **18 bacche** difensive si sceglievano e non facevano niente. Il codice
  era così dalla versione 14 (commit `f43927e`). Colpiva **MA e MB**: i loro 58 oggetti
  sono esattamente i 58 che hanno un `effect`.
- ✅ Ora il `value` delle due tendine è la **chiave** dell'oggetto, e `effect` e
  `modifier` viaggiano negli attributi `data-*`. `oggettoScelto()` in
  `calcolatori-danno.js` legge l'effetto, e ogni effetto ha la sua condizione, presa da
  Bulbapedia. `boost_<tipo>`: +20% alla **potenza**, solo sul tipo giusto, dopo le «-ate».
  `pikachu_boost`: Attacco ×2 solo se il `nome_en` contiene Pikachu. `resist_<tipo>`:
  ×0.5 sul danno finale, solo se la mossa è di quel tipo **e** super efficace; per
  Baccacinlan basta una mossa Normale. Ogni altro effetto, come `boost_spe` della
  Stolascelta, non tocca il danno. Un oggetto che non si attiva **lo dice** nella riga
  del risultato: `@ Carbonella (non si attiva)`.
- Verifica nel browser, su `pokedex`. Regola #8 invariata: **A=183, D=122, HP=221,
  85-102**. **10 casi su 10** col valore calcolato a mano: Carbonella su Buio 85-102
  (non si attiva), Occhialineri su Buio **102-121**, Stolascelta ed Elettropalla su
  Incineroar 85-102, Baccaxan su neutra 85-102 (non si attiva), su Psico **171-204 →
  85-102**, Baccacinlan su Normale **57-68 → 28-34**. Pikachu con Elettropalla:
  **69-84 → 138-165**. Su **MA in inglese**: 20 oggetti ATK e 18 DEF, Black Glasses
  67-79 → 79-94, Charcoal «not active». Sweep IT+EN: **44 pagine, 0 errori**.
  Traduzioni: **630 su 630**.

**Le 7 categorie di oggetti vuote, assegnate: 88 oggetti e 12 effetti nuovi nel calcolatore (§3)**

- ✅ **Decisioni di Davide**: `orb` = Assorbisfera, Fiammosfera e Tossicsfera; **tutte e
  18** le gemme; per l'Evolcondensa **si importano le evoluzioni**. Gli oggetti delle
  leggende (Adamasfera, Splendisfera, Grigiosfera, Cuorugiada, le tre maschere di Ogerpon)
  sono andati in `conditional`, perché `orb` era presa: confermato da Davide lo stesso giorno.
- ✅ `scripts/assegna_categorie_oggetti.py` (rieseguibile, `--dry-run`, non sovrascrive
  un oggetto già curato). **88 oggetti**: choice 2, damage 2, orb 3, conditional 9,
  utility 2, type_boost 41 (5 aromi, 18 lastre, 18 gemme), defensive 5; solo come
  etichetta weather 4, terrain 5, support 1, berry 14. `other` da **339 a 251**. Ogni
  valore da Bulbapedia, una pagina per oggetto; le frazioni arrotondate come i 58
  curati (4915/4096 → 1.2, 4505/4096 → 1.1, 5324/4096 → 1.3). Seconda esecuzione:
  «niente da fare».
- ✅ `scripts/importa_evoluzioni.py` scrive `puo_evolversi` su **1340 voci su 1342** (481
  sì, 859 no). Si decide **per forma** con `base_form_id` di `pokemon_evolution.csv`, e la
  regola sta in `pokeapi.evoluzioni()`, che usa anche l'import dal pannello. **22
  canarini** confrontati con Bulbapedia (Corsola/Corsola di Galar, Pikachu/Pikachu Cosplay,
  Farfetch'd/Farfetch'd di Galar, Qwilfish/Qwilfish di Hisui, Mega Venusaur, Meltan, …).
  Meltan è l'unica specie che il dump dà per pre-evoluzione **senza righe**: si evolve
  solo in Pokémon GO, ed è dichiarata in `EVOLUZIONI_FUORI_DAL_DUMP`. Restano senza valore
  le due Mega Meowstic, che non hanno `slug`.
- ✅ Il motore conosce `boost_atk`/`boost_spa`, `boost_physical`/`boost_special`,
  `boost_punch`, `life_orb`, `expert_belt`, `boost_specie`, `stat_specie`, `boost_spd`,
  `eviolite` e `air_balloon`. Le tendine hanno `data-specie`/`data-tipi`/`data-stat` e
  mostrano le voci con `modifier` **non nullo** (il Palloncino ha 0). `/api/pokemon`
  restituisce `puo_evolversi`, che nelle forme **non si eredita**.
- ⚠️ **Una rete ha trovato un difetto vero**: `prova_import_specie.py` 26/27. Reimportando
  una specie dal pannello, `puo_evolversi` spariva, cioè la stessa trappola delle `forms`.
  Ora lo scrive `pesca()`; `pokemon_species.csv` e `pokemon_evolution.csv` entrano in
  `FILE_CSV`.
- Verifica nel browser su `pokedex`: **44 casi su 44**. Attacco 18/18 (a mano:
  Bendascelta **127-150**, Muscolbanda **93-111**, Assorbisfera **110-132**, Abilcintura
  super efficace **205-244**, Bijoubuio **109-130**, Guantone su Fire Punch **129-153 →
  141-168**, e senza mossa scelta «non si attiva»). Specie 8/8 (Adamasfera su Dialga
  Drago sì e Fuoco no, Maschera Focolare su Ogerpon, Ossospesso su Marowak di Alola,
  Dente Abissi su Clamperl). Difesa 11/11 (Corpetto assalto solo sulle speciali;
  Evolcondensa su Porygon2 sì, Amoonguss no, Mega Meowstic «evoluzione non nota»;
  Squamabissi, Metalpolvere; Palloncino immune alle mosse Terra). Regressione 7/7
  sui casi del blocco precedente. Regola #8 invariata. Tendine: **77 oggetti ATK, 23
  DEF**. Reti: 27/27, 11/11, 9/9, 32/32, `controlla_abilita` a posto, traduzioni
  **631/631**, sweep 44 pagine a 0 errori.

**Pawmot ha la sua lista di Champions, integrata da Bulbapedia (§5.2, decisione di Davide)**

- ✅ `scripts/integra_moveset_bulbapedia.py --voci pawmot`: **64 mosse** dalla pagina
  «Pawmot (Pokémon)/Champions learnset» (versione 1.2.0), metodo `train` come nel dump.
  Scrive il dato curato in `data/catalog/moveset_integrazioni.json` (copia in
  `data/archive/`) e lo applica subito a `pokemon_moves.json`. Il diff tocca **solo**
  Pawmot: +74 righe su 2,7 MB. Si rifiuta di scrivere su una voce che il dump ha già
  (Incineroar: «Vince il dump»), su una voce inesistente e su una mossa sconosciuta.
- ✅ `applica_integrazioni_moveset()` in `blueprints/pokemon.py`, chiamata da `salva_moveset()`
  (import dal pannello) e da `importa_mosse_specie.py`: rigenerare non cancella
  l'integrazione (dry-run: voci **1326 → 1326**, liste `champions` **333**). Dove il dump ha
  una lista sua vince il dump, e l'integrazione viene detta «superata». L'anteprima del
  pannello dice «lista Champions integrata» invece di un falso «non è in Champions».
- ⚠️ **`prova_import_specie.py`**: due prove fallivano dopo l'integrazione, ed era atteso,
  perché dicevano che Pawmot non è in Champions. Non sono state tolte: le prove 1-2 ora
  girano **senza** il file delle integrazioni (così controllano ancora che il dump da solo
  non inventi una lista), e **tre prove nuove** controllano che l'anteprima conti 64 mosse,
  che reimportare dal dump non cancelli l'integrazione e che dove il dump ha una lista vinca
  il dump. **30 su 30**.
- Verifica dall'app vera: `/api/pokemon/pawmot` dà **64** mosse `champions` su MA e MB (prima
  `null`) e 71 `main` su `pokedex`; Incineroar resta a 77; Toxtricity, non integrato,
  resta `null`. `verifica_moveset.py`: identiche **270 → 271**, senza lista **26 → 25**.
  Reti 30/30, 11/11, 32/32, 9/9; sweep 44 pagine a 0 errori.
- ⚠️ **Trovato e non corretto**: la tendina di Pawmot in MA mostra **51** mosse, non 64. Le
  13 che mancano (Crunch, Endure, Substitute, Thief, …) non sono nell'elenco mosse della
  regulation, e il problema è generale: **159 mosse escluse, tutte le 278 specie di MA
  colpite**, Crunch sparita anche da Incineroar. Scritto nel §3 del backlog.

**La lista `champions` confrontata con Bulbapedia: il dump è fermo prima della 1.2.0 (§5.2)**

- ✅ `scripts/verifica_moveset.py`, rieseguibile. Legge le **231 pagine** della categoria
  «Pokémon learnsets (Champions)» (wikitext tramite l'API, cache in
  `data/cache/bulbapedia/champions/`, una richiesta al secondo, 0 errori), fa corrispondere
  pagina e sezione `===…===` a **una sola** voce del catalogo e **segnala senza scrivere**.
  Esce con 1 se un blocco non risolve. Esito: **0 non risolti**, 0 nomi di mossa ignoti,
  **358 voci confrontate** (252 con un blocco loro, 106 forme confrontate con la lista
  della specie), **270 identiche**.
- ⚠️ **Il dump non ha la versione 1.2.0.** **26 voci** hanno una pagina Bulbapedia e nessuna
  lista nel dump, e **tutte e 26** sono «available from Version 1.2.0». Fra queste c'è
  **Pawmot**, che il backlog dal 12/08 dava per «buco del dump» (64 mosse su Bulbapedia): è
  l'unica in un roster, MA e MB. Controllato alla fonte: la cache locale è **identica** al
  dump pubblicato oggi su GitHub (19.810 righe, 319 Pokémon). L'ultimo commit sul file è del
  21/07/2026, «Add Champions Regulation M-B learnsets». Le pagine per versione d'arrivo sono
  186 per la 1.0.2, 22 per la 1.1.0 e 23 per la 1.2.0.
- **Le differenze sulle voci con un blocco loro sono 35**, e quasi tutte sono la 1.2.0:
  Slash solo su Bulbapedia in **29**, e 34 pagine l'hanno accessibile; Mawile +3 (Charm,
  Draining Kiss, Misty Terrain); Houndstone +Bulldoze. Tre mosse sono solo nel dump e
  Bulbapedia le segna «Prior to Version 1.2.0» (Archaludon: Metal Burst e Mirror Coat;
  Politoed: Pound). **Non spiegati** da nessuna versione: Gardevoir con 5 mosse in più nel
  dump, che sulla sua pagina Bulbapedia mancano del tutto; Blaziken con U-turn; Ariados con
  Psychic contro Psychic Fangs. Le forme di Rotom differiscono perché Bulbapedia ha una
  pagina unica, e non è un errore. Morpeko (Hangry Mode) ha 5 mosse in meno nel dump.
  Nessun dato è stato toccato: le decisioni sono di Davide, elencate nel §5.2.

**Il grafo rifatto prima del §5.2, e un falso allarme dello sweep tolto**

- ✅ `/graphify . --update` (il grafo era del 16/08): **69 file** ri-estratti, 51 di codice
  con l'AST e 18 documenti con due subagenti (372.457 token). Risultato: **1029 nodi,
  2005 archi, 89 comunità**, cioè +409 nodi e −140 rispetto a prima. Controllo di
  integrità pulito: 0 archi pendenti, mancanti o collassati. ⚠️ Il subagente dei documenti
  **non ha letto per intero** il log di `PROJECT_CONTEXT.md` e le voci di `STORICO.md`
  prima del 19/08: quella parte del grafo è incompleta.
- ✅ `moderno()` in `scripts/sweep_pagine.py` trasformava `TC[mvType]?.[dt]` in
  `TC[mvType].[dt]`, che nessun parser accetta. Ora toglie `?.[` e `?.(` prima di `?.`.
  Prima: `calcolatori-danno.js` dava «Line 264: Unexpected token [». Dopo: i **7 file
  `.js` su 7** del calcolatore passano, e lo sweep delle 44 pagine resta a 0 errori.

**Tre voci chiuse come decise da Davide, senza codice**

- ✅ **Il calcolatore non blocca le mosse illegali**: le segnala e basta, perché un
  blocco sulle voci senza elenco mosse sarebbe un divieto falso.
- ✅ **Gli `overrides` delle regulation restano scritti a mano nel JSON**: in `ma`, `mb`
  e `pokedex` valgono `{}`, cioè non li ha mai usati nessuno. Un editor si fa quando
  servirà davvero.
- ✅ **La riga Pokémon in §4** («Creare i JSON di una regulation nuova») era chiusa dal
  10/09 e stava ancora fra le voci aperte: tolta.

## 13/09/2026

**Quattro forme vere erano contate fra le inventate, e da un mese non avevano le mosse (§2.3)**

- ⚠️ ✅ **Le voci del catalogo senza elenco mosse erano 20 su 1343, e per quattro il motivo
  era sbagliato.** Il backlog le chiamava tutte «forme inventate, che PokéAPI non conosce»:
  i tre **Gourgeist (Small/Large/Super)** e **Floette Fiore Eterno** invece il dump li
  conosce — 397 righe di mosse a testa i primi, 229 la seconda. Quello che mancava era il
  campo `slug` sulla voce del catalogo, e `indice_catalogo()` in `importa_mosse_specie.py`
  prende **solo** le voci che ce l'hanno. Quindi uscivano dal moveset insieme alle Mega
  fan-made e prendevano lo stesso avviso giallo «nessun elenco mosse», **senza nessun
  errore** — e il rapporto dell'import le elencava sotto «forme che PokéAPI non conosce»,
  che per loro era falso. Dal 12/08/2026 al 13/09/2026, un mese.
- **Lo slug non è stato scritto a occhio**: `scripts/aggiungi_slug_forme.py` pretende che le
  **sei base stat** del catalogo combacino esatte con quelle che il dump dà per quello slug,
  perché uno slug plausibile ma sbagliato non darebbe errore, darebbe l'elenco mosse di un
  altro Pokémon. Combaciate **6 su 6 su tutte e quattro le voci**. Se una sola voce non
  passa i controlli non si scrive niente e si esce con 1: provato **5 su 5** sui rifiuti
  (slug di un altro Pokémon, slug inesistente, nome che nel catalogo non c'è, voce che ha
  già uno slug diverso), zero scritture in tutti e cinque i casi.
- **Numeri della verifica**: catalogo **1343 voci prima e dopo, 4 cambiate, solo il campo
  `slug`**, tutto il resto byte per byte identico (copia in `data/archive/`). Moveset
  **1323 → 1327 voci, 0 perse, 0 preesistenti modificate**. Voci senza moveset **20 → 16**,
  e le 16 sono tutte e sole le Mega inventate di Davide. Passando dalla route vera
  (`/api/pokemon/<nome>`, test client su una copia di `hub.db`): Gourgeist (Small) dà **57**
  mosse su `pokedex` e **60** su `ma`, Floette Fiore Eterno **51** e **41** — due numeri
  diversi, cioè sta leggendo davvero `main` contro `champions`. Controprova sulle voci che
  non dovevano muoversi: Incineroar resta **80/77** e Mega Zygarde resta `null` con l'avviso
  giallo.
- **Contorno**: `sweep_pagine.py` 0 errori su 22 pagine in due lingue, `prova_catalogo_vivo`
  11 su 11, `prova_import_specie` 27 su 27, `prova_build_catalog` 9 su 9,
  `controlla_abilita` a posto.
- ✅ **Il doppione di Floette è stato fonduto lo stesso giorno, su decisione di Davide.**
  Lo stesso Pokémon stava in due posti: `eternal-flower-floette` di **primo livello**
  (`abilities: []`, e con **Mega Floette** fra le sue `forms`) e la forma **annidata**
  `floette` → `Floette (Eternal Flower)`. ⚠️ **Quale delle due resti non era una scelta di
  gusto**: la forma annidata è quella che `build_catalog.py` **rigenera dal dump**, quindi
  tenere il primo livello avrebbe fatto **rinascere il doppione** alla prossima esecuzione.
  Mega Floette è traslocata sotto `floette` **identica** — una Mega porta le sue
  `base_stats`, quindi il calcolatore non cambia di un punto — e la chiave vecchia è
  sparita. Prove dei rifiuti **5 su 5** (base stat diverse, slug diversi, forma annidata
  assente, fusione a metà, un team salvato che cita la voce che sparisce), zero scritture
  in tutti e cinque.
- ⚠️ **La fusione da sola avrebbe rotto due regulation, e in silenzio.** `ma` e `mb`
  citavano `Eternal Flower Floette` sia nell'elenco `pokemon` sia come chiave della
  `mega_map`: quelle liste sono elenchi di **nomi**, e un nome che nel catalogo non esiste
  più non dà errore — sparisce e basta. Rinominato in `Floette (Eternal Flower)` in tutti
  e quattro i punti, con copia in `data/archive/`: **ma 279 nomi prima e dopo, mb 308**,
  `mega_map` 58 e 73 invariate, il valore `['Mega Floette']` conservato, tutto il resto dei
  due file identico. In `pokedex` non c'era niente da cambiare: la sua `mega_map` diceva
  già `Floette → Mega Floette`, che dopo la fusione è il verso giusto.
- **Numeri finali**: catalogo **1026 → 1025 specie**, **1343 → 1342 voci**, l'unica sparita
  è `eternal-flower-floette` e nessuna delle altre è cambiata; moveset **1326 voci**, e
  rispetto all'inizio della giornata **0 perse, 0 modificate, 3 nuove** (i Gourgeist).
  Doppioni di nome fra tutte le 1342 voci: **0**. Dalla route vera,
  `Floette (Eternal Flower)` dà 41 mosse su `ma` e 51 su `pokedex`, `Mega Floette`
  risponde 200 con le sue stat, e `Eternal Flower Floette` ora dà **404**.
- ⚠️ **`importa_mosse_specie.py` si è rifiutato di scrivere**, ed era giusto: la sua rete
  ferma un import che fa **calare** le voci, perché una cache CSV troncata darebbe quel
  sintomo senza nessun errore. Qui il calo era voluto, ma lo script non può indovinarlo.
  Aggiunto `--tolte-apposta`, che **non** è un `--forza`: bisogna **nominare** le voci che
  devono sparire, un calo diverso da quello nominato si ferma lo stesso, e un nome che
  invece resta viene detto a schermo. Provato: senza flag esce **1**, con un nome sbagliato
  esce **1** e lo dice, col nome giusto esce **0**.
- **Quattro asserzioni aggiornate perché il catalogo è calato di uno apposta**: `1026 → 1025`
  in `prova_import_specie.py` e `prova_build_catalog.py`, `1343 → 1342` in due punti di
  `prova_regulation_nuova.py`. Il perché è scritto in un commento sopra ognuna, così la
  prossima sessione non le legge come un test addomesticato. Tutto verde dopo:
  **27/27, 32/32, 9/9, 11/11**, `controlla_abilita` a posto, `controlla_proprietario` e
  `controlla_traduzioni` a posto, sweep **0 errori**. I due script nuovi sono rieseguibili:
  rilanciati dicono «niente da fare» ed escono 0.
- ✅ **La regulation `mc` era una prova di Davide, e l'abbiamo tolta.** Faceva fallire
  `prova_regulation_nuova.py` **31 su 32**: la prova 12 pretende che `data/regulations/`
  abbia esattamente `ma`, `mb`, `pokedex`, e quel quarto file non era sporcizia del test ma
  una regulation vera creata dall'interfaccia (309 Pokémon, 73 Mega mappate) e mai
  committata. Zero team attaccati, copia in `data/archive/regulation_mc_pre-eliminazione.json`
  prima di toglierla, registro tornato a tre voci: la prova passa **32 su 32**.

---

## 10/09/2026

**I quattro bachi noti, guardati uno per uno (§3)**

- ⚠️ ✅ **`build_catalog.py` non è più una bomba.** Rieseguito com'era, avrebbe riscritto
  `data/catalog/` partendo dai **file storici** — 174 voci contro le 1026 di oggi, senza
  `nome_it`/`nome_en` — e avrebbe riapplicato alle Mega il `+75 HP / +20` che la
  deconversione dell'11/08 aveva tolto apposta. **In silenzio**: la regola «non tocco i
  dati curati» c'era già, ma confrontava il risultato con la **base sbagliata**, quindi
  le 852 voci che in quella base non c'erano non le difendeva nessuno. Ora la base è
  `data/catalog/` quando esiste (i file storici restano solo per il primo giro) e lo
  script **dice da quale file legge**; `MEGA_BONUS` è stato tolto; `scrivi_json()` si
  **rifiuta** di scrivere un file con meno voci di quello sul disco. Dry-run vero:
  **1026 → 1029 specie, 919 → 920 mosse, 386 → 387 abilità, 397 → 398 oggetti, 0 voci
  curate modificate**. `scripts/prova_build_catalog.py` **9 su 9**, senza rete e senza CSV.
- ✅ **La regex delle traduzioni non è rotta.** Il backlog diceva che
  `t('Nessun team per l\'utente scelto.')` veniva contato come «Nessun team per l»:
  rimisurato **su un file vero**, la frase esce **intera**. Il ramo `\\.` consuma la
  coppia backslash-apice e la `replace()` sotto la ripulisce. La diagnosi del 19/08 è
  nata quasi certamente da una prova scritta a mano in una shell che si mangia un
  livello di backslash — trappola ricapitata **due volte** oggi mentre si scriveva la
  spiegazione, che infatti ora sta nel commento sopra la regex.
- ✅ **`scripts/` resta fuori dal controllo proprietario, ma adesso c'è scritto.** Uno
  script da riga di comando non ha una sessione: `ambito_utente()` lì non vuol dire
  niente e lavora su tutto il DB **per costruzione**. Il problema non era la scelta, era
  il silenzio: ora il docstring lo dichiara e il riassunto **conta e nomina** gli script
  che toccano una tabella di contenuto — oggi **2**, `importa_dati.py` e
  `prova_importa_dati.py`. Il controllo esclude se stesso, che le tabelle le nomina
  tutte perché sono la sua configurazione.
- 🟨 **La tendina delle categorie oggetti: chiusa la metà che non chiedeva decisioni.**
  Il filtro offriva **14** categorie, gli oggetti ne usano **7**: le altre sette non
  hanno nemmeno una voce, quindi erano filtri che davano sempre zero. Ora il filtro
  mostra solo le presenti — **contate sui dati**, non tolte a mano, così si riaggiornano
  da sole — mentre la tendina del modulo resta a 14, perché è da lì che una categoria
  vuota si riempie. Verificato a schermo: filtro 7 opzioni, modulo 14. ⬜ Resta la
  ricategorizzazione, che è una decisione di Davide.
- **Verifica**: cinque giri di prove verdi (9/9, 32/32, 27/27, 11/11, 20/20), sweep **0
  errori**, traduzioni **629 su 629**, `controlla_abilita.py` pulito,
  `controlla_proprietario.py` **0 scoperte**.

**Le abilità da fondere erano già fuse — e un filo era rimasto staccato (§2.2)**

- ✅ **Rimisurato invece di eseguito.** Il backlog diceva 103 voci da fondere, 34 con un
  effetto: erano i numeri di **prima** della fusione dell'11/08, mai più ricontati. Oggi
  il catalogo ha **386 voci**, **82** senza traduzione e **10** di quelle con un effetto —
  e sono esattamente le 10 abilità di Champions che Davide aveva deciso di lasciare fuori.
  Delle altre 72: 7 appese a un Pokémon (anche quelle decise) e **65 inerti che nessuno
  possiede**. Doppioni di nome nei quattro database del catalogo: **zero**.
- ⚠️ ✅ **Mega Meganium citava un'abilità che non esisteva più, e l'ha visto Davide.**
  Prima dell'11/08 la chiave `Megasolar` aveva `nome_en: Mega Sol`, ed è così che il
  catalogo Pokémon la chiama: le abilità le cita col nome **inglese**. La fusione ha
  spostato l'effetto della chiave `Mega Sol` su `Terra Estrema` — giusto, è l'abilità di
  Primal Groudon, che infatti applica il sole — e poi il giro sui nomi ha cambiato il
  `nome_en` di `Megasolar`. Da quel giorno quel nome non risolveva **su nessuna voce**:
  nome grezzo nella tendina, niente descrizione, niente traduzione, nessun errore.
  Misurato: **1 nome su 312** citati dai Pokémon era orfano.
- ✅ **Chiuso con `scripts/ricollega_megasolar.py`** (rieseguibile, `--dry-run`, scrive
  con `_save_abilities()`): `nome_en` torna `Mega Sol` e la voce riprende il blocco della
  chiave cancellata — sole permanente, Fuoco ×1.5, Acqua ×0.5 — **copiato dall'archivio**,
  non riscritto a mano. Provato nel browser: Mega Meganium con una mossa Fuoco fisica BP
  100 su Amoonguss passa da **94-112 a 142-168**, cioè il ×1.5 del sole, che prima quella
  voce non applicava. Le voci attive salgono da 49 a **50**.
- ✅ **La rete perché non ricapiti**: `scripts/controlla_abilita.py` — 312 nomi citati,
  **0 orfani**, **0 doppioni di nome**, 50 voci attive di cui **10 irraggiungibili** (le
  abilità di Champions, decise fuori l'11/08). Provato **anche sul guasto**: sui dati di
  ieri lo trova. Esce con 1 se trova qualcosa.
- **Verifica**: quattro giri di prove verdi (32/32, 27/27, 11/11, 20/20), **sweep 0
  errori**, traduzioni **629 su 629**, **regola #8** rieseguita nel browser su `pokedex`
  dopo la modifica ai dati — A=183, D=122, HP=221, 85-102 (38.5%–46.2%).
- ⬜ **Non riallineato** il fallback `data/abilities.json`, che tiene ancora la voce
  vecchia: vedi §2.2 nel backlog.

**Una regulation nata dall'interfaccia è usabile davvero (§1.3, voce collegata)**

- ✅ **La sorgente delle mosse si sceglie, si eredita e si valida.** Era il campo che
  cambiava i numeri senza comparire da nessuna parte: `moveset` non veniva scritto alla
  creazione, quindi una regulation copiata da MA riceveva i 279 nomi di Champions e poi
  leggeva gli elenchi di `main` — **80 mosse su Incineroar invece di 77**, Knock Off
  compresa. Ora c'è una tendina alla creazione e nell'editor, il copia contenuti la porta
  con sé, e una sorgente inesistente è **rifiutata con 400** sia alla creazione sia al
  salvataggio (senza il rifiuto `mosse_legali()` avrebbe risposto `None`, cioè «mostrale
  tutte»). Le sorgenti si leggono dal file, non da una costante: sono `main` e
  `champions`, e le 32 forme Gigantamax che hanno anche `eredita_da` non sporcano
  l'elenco.
- ✅ **La pagina Regulations dice i numeri veri.** Leggeva ancora i file storici: su MA
  scriveva **208 Pokémon e 461 mosse** invece di **279 e 460**, e su MB, Pokedex e su
  qualunque regulation creata da lì — che quei file non li hanno mai avuti — **0 su
  tutto, anche piena**. Ora usa gli stessi loader dell'editor: Pokedex 1343/919/397, MA
  279/460/58, MB 308/460/58, e ogni card dice anche da quale sorgente prende le mosse.
- ✅ **La `mega_map` si completa da interfaccia.** Una Mega nel roster che nessuna base
  punta è irraggiungibile — il team builder non la offre — e l'unico modo di collegarla
  era `scripts/completa_mega_map.py` da riga di comando. Ora c'è un pulsante con
  anteprima (che non scrive niente, come un `--dry-run`): su una regulation «tutto il
  catalogo» collega **97 Mega su 97** in un colpo, tiene i collegamenti già scritti,
  dichiara quelle la cui base è fuori dal roster invece di aggiungerla di nascosto, e
  **non trasforma mai `pokemon: null` in un elenco chiuso**. La deduzione `Mega X → X` è
  stata spostata in `data.py` e ora è **una sola**: la usano lo script e il pulsante.
- ✅ **Una regulation vuota si dichiara invece di dare 404.** `/api/regulation/<id>/data`
  rispondeva 404 con roster vuoto, e i due che la chiamano lo prendevano nel `catch`: lo
  Speed Tier ricadeva **in silenzio** sulla lista statica da 158 nomi, il team builder
  usciva prima di aggiornare roster, oggetti e meccaniche — cioè restava con quelli della
  regulation precedente. Ora risponde 200 con `vuota: true`: il calcolatore scrive
  «nessun Pokémon in VUOTA9» con 0 righe, e il team builder mostra l'avviso e svuota i
  suggerimenti.
- **Verifica**: `scripts/prova_regulation_nuova.py` **32 su 32** su una copia dei dati;
  gli altri tre giri di prove restano verdi (import specie 27/27, catalogo vivo 11/11,
  importa dati 20/20); **sweep 0 errori** su 22 pagine per due lingue, con
  `/pokemon/regulation/ma` e la sua schermata contenuti **aggiunte all'elenco dello
  sweep**, dove non erano mai state; traduzioni **629 su 629**, 0 mancanti e 0 orfane;
  `controlla_proprietario.py` 53 filtrate, 27 dichiarate, **0 scoperte**; **regola #8**
  eseguita nel browser su `pokedex` — A=183, D=122, HP=221, 85-102 (38.5%–46.2%).
- **Provato davvero nel browser**, non solo col test client: regulation creata dalla
  modale copiando da MA (279/460/58, sorgente `champions` ereditata), pulsante della
  mega_map che scrive 91 basi per 97 Mega con la copia di sicurezza in archivio, e il
  filtro che resta `pokemon: null`. Su un'istanza di prova con i dati in `%TEMP%`: i file
  veri non sono stati toccati.

---

## 21/08/2026

**Il backup sa tornare indietro — `scripts/importa_dati.py` (§1.4, falla 2)**

- ✅ **Il ritorno di `esporta_dati.py` esiste.** Fino a ieri nessuno rileggeva
  `hub_export.json`: su un PC nuovo l'app ripartiva col DB che `init_db()` crea da zero,
  solo `admin` e **niente** giochi, team, Arduino o build PC. Ora `python
  scripts/importa_dati.py` li rimette dentro. Provato sul giro vero: DB appena creato da
  `init_db()` → import → **9 tabelle su 9 combaciano con l'export** (2 utenti, 33 giochi,
  3 team, 3 membri, 53 argomenti, 1 build, 5 componenti), **46 righe scritte**, e l'app
  ci si apre sopra — **6 pagine a 200**, col primo gioco visibile in `/gaming/`.
- ✅ **Rieseguibile**: una riga già presente e identica si salta, e la seconda esecuzione
  dice «Niente da fare» senza toccare il file. La tolleranza sui numeri non è un dettaglio:
  `hours_hltb` è REAL, SQLite torna `40.0` dove il JSON ha `40`, e senza il confronto
  numerico ogni riesecuzione avrebbe visto un conflitto inesistente — cioè lo script
  sarebbe stato rieseguibile solo sulla carta.
- ✅ **Non sovrascrive niente senza dirlo**: le righe già presenti e **diverse** sono un
  conflitto, e lo script si ferma elencando la riga, la colonna e i due valori. Per
  procedere serve `--sovrascrivi`, che è il momento in cui hai già visto cosa perdi.
  `--dry-run` non lascia nemmeno la copia di sicurezza.
- ⚠️ **Le password non rientrano, e non è un limite da correggere**: l'export non le
  contiene di proposito perché viene committato. Quindi un utente **nuovo** nasce con una
  password casuale che nessuno conosce — non con una vuota e non con una nota — e lo
  script lo dichiara a schermo; un utente **già presente** tiene la sua anche con
  `--sovrascrivi`. Riscriverla vorrebbe dire distruggere l'unica copia buona con il nulla.
- ⚠️ **La trappola vera era `python_topics`, e ha una rete apposta.** L'elenco lo semina
  `init_db()` con gli `id` 1..53 nell'ordine di `PYTHON_TOPICS`, e `python_progress.topic_id`
  punta a quegli `id`: se l'ordine cambia fra l'export e oggi, l'`id` 7 nel backup è un
  argomento **diverso** da quello nel DB, e importare le spunte le metterebbe sugli
  argomenti sbagliati **senza nessun errore**. Ora gli argomenti si confrontano per
  `(category, name)` a parità di `id`; con delle spunte da importare lo script si ferma,
  senza spunte avvisa e prosegue.
- ✅ **Le altre tre reti**: `username` duplicato con `id` diverso (`users.username` è
  UNIQUE, e senza il controllo l'INSERT sarebbe morta a metà strada senza dire **quale**
  utente); DB più vecchio dell'export, cioè una colonna che nell'export c'è e nel DB no —
  si ferma e manda a `init_db()`, perché scrivere lì perderebbe quella colonna; e il
  `rowcount` a zero sugli UPDATE, la trappola già pagata in `_team_upsert()`, che qui
  annulla la transazione invece di proseguire come se avesse funzionato.
- ✅ **Tutto o niente**: una sola transazione, `rollback` su qualunque intoppo, e una copia
  di `hub.db` in `data/archive/hub_pre-import_*.db` prima di scrivere. ⚠️ Quel nome è in
  `.gitignore` — aggiunta la riga `*.db` — perché la copia contiene gli hash delle
  password, ed è esattamente la ragione per cui `hub.db` non è versionato.
- ✅ **19 prove su 19 in `scripts/prova_importa_dati.py`**, ognuna su un DB **suo** creato
  da `init_db()` in una cartella temporanea: è la regola pagata il 16/08, quando uno script
  di prova che cancellava «il mio intervallo» di id si portò via 497 righe vere. Fra le
  prove ce ne sono due **a futuro**, per il `--completo` di §1.4 che ancora non esiste: un
  export che portasse le password vere deve poterle dare a un utente nuovo, e non deve
  finire con la colonna `password` scritta due volte nella stessa INSERT.
- ⚠️ **Trovato e non corretto**: `controlla_proprietario.py` legge `blueprints/` e i `.py`
  della radice, **non `scripts/`**, e non è ricorsivo. È giusto — uno script da riga di
  comando non ha una sessione — ma non è scritto da nessuna parte. Voce nel backlog.

**Le quattro cose da chiudere prima di esporre l'app (§1.5, primo blocco)**

- ✅ **Il debugger non si accende più da sé.** `app.py` finiva con
  `app.run(host="0.0.0.0", debug=True, port=5000)`: il debugger di Werkzeug offre una
  console Python dentro la pagina d'errore, quindi chiunque raggiungesse quella porta
  eseguiva codice sulla macchina. Ora si accende solo con `HUB_DEBUG=1`, e quando è acceso
  l'app lo scrive all'avvio. ⚠️ **L'indirizzo `0.0.0.0` è rimasto di proposito**: è così
  che l'hub si apre dal telefono sulla rete di casa, ed è un uso che già funziona — il
  pericolo era il debugger, non l'indirizzo. Si stringe con `HUB_HOST=127.0.0.1`.
- ✅ **`SECRET_KEY` non ha più un valore di riserva costante.** Era `dev-secret-change-me`,
  scritta nel codice e quindi pubblicata su GitHub: chi la legge **si firma da solo un
  cookie di sessione da amministratore**, senza sapere nessuna password. Ora
  `chiave_di_sessione()` legge la variabile d'ambiente `SECRET_KEY` e, se manca, genera 32
  byte casuali in `data/secret_key.txt` (in `.gitignore`, per la stessa ragione di
  `hub.db`). ⚠️ **Generarne una nuova a ogni avvio sarebbe stato peggio**: far cadere le
  sessioni a ogni riavvio è il fastidio quotidiano che invita a rimettere una costante,
  cioè a rifare il buco. Provato: due avvii di fila danno la stessa chiave, l'ambiente
  vince sul file, e il file nasce da solo al primo avvio.
- ✅ **La pagina di login non stampa più `admin / admin123`**, e al suo posto c'è un avviso
  in dashboard. Lo vede **solo un amministratore** e **solo finché quella password funziona
  davvero**: sparisce da sé appena la si cambia. Il seme di `init_db()` resta — un DB nuovo
  ha bisogno di un modo per entrarci — ma toglierlo dalla pagina senza dire niente a chi ce
  l'ha ancora avrebbe solo reso il buco più zitto.
- ✅ **`requirements.txt` dice la verità**: erano `flask>=3.0` e basta, e gli import di
  terze parti contati sui sorgenti sono **tre** — `flask`, `requests` e `werkzeug`, che
  arriva con flask ma qui è usato per nome (`generate_password_hash`). Più il server WSGI
  per sistema operativo e `esprima` per lo sweep. Una guida che diceva
  `pip install -r requirements.txt` fino a ieri mentiva.
- ✅ **`wsgi.py`**: `wsgi:application` è il nome che waitress, gunicorn e il file WSGI di
  PythonAnywhere si aspettano. Provato **servito da un server esterno vero** (`wsgiref`
  della stdlib, così la prova non dipende da un pacchetto da installare): `/login` 200,
  `/` 302 al login. ⚠️ Un worker solo finché la trappola sulle scritture concorrenti resta
  aperta.
- ⚠️ **Un fallback silenzioso creato e corretto nella stessa ora**, perché è la classe di
  baco che qui costa di più: `password_di_default()` era nata con un parametro `db` per
  riusare la connessione del chiamante, e in dashboard quella connessione era già chiusa
  due righe sopra. L'`except sqlite3.Error` traduceva l'errore in «no, la password non è
  quella di default» — **un avviso di sicurezza che spariva per un guasto**, senza dire
  niente. Ora la funzione apre la sua connessione e non ha nessun `except`. L'ha trovata la
  prova, non la lettura del codice.
- ✅ **Verifica: 13 prove su 13** (chiave, avviso, pagine, WSGI), **sweep 0 errori** su 19
  pagine, **traduzioni 590/590** invariate.
- ⚠️ **Conseguenza pratica al prossimo avvio**: la chiave di sessione cambia, quindi le
  sessioni aperte cadono e il login va rifatto una volta.
**Il catalogo si aggiorna mentre l'app gira (§1.3, primo ostacolo)**

- ⚠️ **Il buco non era quello scritto nel backlog.** Andando a misurare il punto 1 di §1.3
  («il moveset è il buco vero, la tendina esce vuota senza dire perché») sono saltate fuori
  due cose, e nessuna delle due era quella: la tendina **non** esce vuota, e il problema
  vero stava un piano sotto.
- ⚠️ **Il baco, misurato su una copia del catalogo**: `POKEMON_CATALOG` e `_INDICE` in
  `blueprints/api_pokemon.py` erano caricati **una volta sola all'avvio** — il commento lo
  diceva pure. Conseguenze, tutte e due silenziose:
  1. un Pokémon aggiunto dall'editor finiva sul file (1027 voci) e **compariva nel roster**
     di `pokedex` (1344 voci, dentro), perché quello rilegge il file ogni volta. Ma
     `/api/pokemon/<nome>` rispondeva **404**: niente stat, niente tipi, niente sprite.
     Compariva nell'elenco e non si apriva
  2. peggio: cambiando una base stat dall'editor, il file diceva **999** e l'API continuava
     a rispondere **115**. Nessun errore da nessuna parte — il calcolatore faceva i conti
     col valore vecchio fino al riavvio dell'app
- ✅ **La cura è il pattern che il progetto usa già** per `_MOVESET` e `_TRADUZIONI`: la
  copia in memoria segue l'**mtime** del file. `aggiorna_catalogo()` sta in
  `_find_in_catalog()`, che è il collo di bottiglia di ogni lettura: a file fermo costa una
  `stat()`, non una rilettura del JSON.
- ⚠️ **Firma `(mtime_ns, dimensione)` e non il solo mtime**: due salvataggi ravvicinati
  possono cadere nello stesso istante del filesystem, e sarebbe di nuovo il dato vecchio
  servito senza un errore.
- ⚠️ **Un file illeggibile non svuota la copia buona**, ed è il verso giusto: meglio il
  catalogo di un minuto fa che un catalogo vuoto, che qui vorrebbe dire 404 su **ogni**
  Pokémon. Provato scrivendo spazzatura nel file: 1026 voci restano in mano e i Pokémon
  continuano a rispondere.
- ✅ **Verifica che la correzione non sposti niente**: il codice di ieri e quello di oggi
  messi a confronto sulle stesse voci danno risultati **identici** — 9 casi su 9, indice
  **1457 chiavi** in entrambi, catalogo 1026 voci, e `Mega Machamp` continua a dare **404**
  invece di rispondere Mega Venusaur (la trappola dell'11/08 non è tornata).
  Più **11 prove su 11** in `scripts/prova_catalogo_vivo.py`, sweep **0 errori** su 19 pagine,
  **20 su 20** sull'import dati.
- ✅ **Corretta una riga sbagliata del backlog**: «la tendina esce vuota senza dire perché»
  non era vero. `mosse_legali()` torna `None`, e team builder e calcolatore mostrano
  **tutte** le mosse della regulation con l'avviso giallo «Nessun elenco mosse per X: sono
  mostrate tutte». Metà del requisito del punto 1 era già soddisfatta, e nessuno lo sapeva.
- ⚠️ **Trovato e non corretto**: `/api/catalogo/<db>/salva` accetta una voce col **solo**
  campo `name` e risponde `200 ok`. Da lì nasce una riga di catalogo senza tipi, senza stat
  e senza nomi. È il punto 4 di §1.3, ora misurato invece che supposto.
- ⚠️ **Le prove hanno sporcato la rete di sicurezza vera, e ora se ne accorgono da sole.**
  Deviare `CATALOG_DIR` non basta: `salva_catalogo()` tiene da parte la versione precedente
  in `data/archive/`, e quel percorso non era deviato — `catalog_pokemon_pre-salvataggio.json`
  si è ritrovato dentro `Provamon` e un Incineroar da 999 di attacco. **Il catalogo vero non
  è stato toccato** (1026 voci, Incineroar 115), la copia è stata ripristinata da git, e
  `_archive_dir()` ora è deviato come il resto. È la lezione del 16/08 un piano più in là:
  non bastano i file che il test **legge**, vanno deviati anche quelli che il codice sotto
  prova **scrive**. Le ultime due delle 11 prove controllano proprio questo.
- ⚠️ **Non eseguita la regola #8**: il caso Incineroar → Amoonguss va fatto **nel browser**,
  e per entrare serve la password, che non digito io. Il server è rimasto avviato apposta.
  Quello che copre il rischio della modifica è il confronto ieri/oggi qui sopra: le stat
  servite dall'API sono le stesse, quindi il calcolatore riceve gli stessi numeri.
**Importare una specie da PokéAPI dall'interfaccia (§1.3, punti 1-2-3)**

- ✅ **La forma l'ha scelta Davide**: si scrive un nome e i dati li pesca il programma,
  invece di incollare JSON. E **le regole di Champions**: la voce nuova porta l'elenco
  `champions` quando il dump ce l'ha. Nuovo modulo `pokeapi.py`, due route
  (`/pesca` per l'anteprima, `/importa` per scrivere) e un pannello in
  `catalog_editor.html`, visibile **solo** sotto la linguetta Pokémon.
- ✅ **La fonte è il dump CSV, non la API REST**, per la stessa ragione di
  `build_catalog.py` e `importa_mosse_specie.py`: è quella da cui il catalogo è stato
  costruito. E la prova che conta è questa — **pescate 397 voci già in catalogo e
  confrontate una per una: zero differenze** su base stat, tipi e abilità. Se la fonte
  fosse stata un'altra, si sarebbe visto lì.
- ✅ **Due passi, non uno**: `/pesca` mostra cosa entrerebbe — stat, tipi, abilità,
  quante mosse per elenco — e **non scrive niente**; il pulsante Importa resta spento
  finché non c'è un'anteprima davanti agli occhi. Le voci già presenti sono marcate
  prima, e sovrascriverle chiede conferma.
- ⚠️ **Tre porte che si chiudono, tutte trovate misurando:**
  1. **doppione sotto un'altra chiave.** Delle specie di default del dump ne mancano al
     catalogo **quattro** (`aegislash-shield`, `mimikyu-disguised`, `morpeko-full-belly`,
     `palafin-zero`) e **tutte e quattro ci sono già** con un'altra chiave. Importarle
     avrebbe fatto due voci per lo stesso Pokémon, con due verità sulle sue stat e
     nessun errore. Ora si confronta lo **slug**, non la chiave, e l'import si ferma
  2. **le forme non passano di qui.** Le 1025 voci di primo livello hanno tutte
     `is_default=1`, e le 317 forme — Mega, Gigantamax, regionali — stanno **annidate**
     in `forms`. Scrivere `deoxys-attack` al primo livello sarebbe stato un doppione
     con un altro nome
  3. **le `forms` di una voce che esisteva non si perdono**: reimportando una specie,
     le sue Mega e Gigantamax — che il dump non ha e che nessun import può ricostruire —
     vengono ricopiate sulla voce nuova invece di sparire in silenzio
- ⚠️ **Quello che l'import non aggiusta, e lo dichiara**: per **6 voci su 1025** il
  catalogo usa una convenzione sua per il nome (`Basculegion (Male)`) che il dump non
  ha (`Basculegion`). Comporre quel nome vorrebbe dire inventare una regola di
  scrittura: l'import scrive il nome del dump e **avvisa**, e si corregge dall'editor.
- ✅ **La spunta «aggiungi anche a ma/mb»**, l'altra decisione di Davide: scrive il nome
  negli elenchi delle regulation scelte. `pokedex` non compare fra le spunte, ed è
  voluto — i suoi filtri sono `null`, cioè tutto il catalogo, e offrirla darebbe
  l'idea che senza spunta la voce non ci finisca. Provato: **278 → 279 nomi in MA**.
- ⚠️ **Misura che cambia le aspettative**: oggi **non c'è niente di davvero nuovo da
  importare**. Il catalogo ha 1026 voci e il dump non ha nessuna specie di default che
  qui manchi davvero. Questo import serve al giorno in cui il dump avrà specie nuove —
  è una porta, non un riempimento.
- ✅ **Verifica: 27 prove su 27** in `scripts/prova_import_specie.py`, su copie di
  `catalog/`, `regulations/` e dell'archivio; **sweep 0 errori** su 19 pagine;
  traduzioni **610 su 610** con le 20 chiavi nuove, zero orfane, zero doppie.
- ⚠️ **Terzo sconfinamento in due giorni, e questa volta l'ho cercato prima che facesse
  danno**: la spunta della regulation passa da `_salva_filtro()`, che scrive sotto
  `DATA_DIR` — la prova aveva riscritto il file **vero** di `ma.json`, cambiandogli la
  data (nessun nome perso, ripristinato da git). Ora la prova copia anche
  `regulations/`. La regola, ormai pagata tre volte: **si deviano i file che il codice
  sotto prova scrive, non quelli che il test legge.**
- ⚠️ **Trovato correggendo il mio stesso codice**: `pokeapi.py` teneva in cache due
  letture diverse dello stesso CSV sotto la stessa chiave, e il sintomo era muto e
  sbagliato nel verso peggiore — `Deoxys` rispondeva «nome non trovato nel dump», cioè
  una specie vera dichiarata inesistente, e **solo per l'ordine delle chiamate**.
- ✅ **Anche il punto 4 è chiuso: la validazione di `/api/catalogo/<db>/salva`**, che fino
  a stamattina aveva come solo controllo `isinstance(voce, dict)`. Ora ha **due esiti**, ed
  è la stessa distinzione per cui `moves: null` non vuol dire «nessuna mossa»: un campo del
  **tipo sbagliato** si rifiuta con 400 — `base_stats.hp = "molti"` non darebbe un errore a
  valle, darebbe **un numero sbagliato** nel calcolatore — e un campo **mancante** si salva
  e si dichiara a schermo, perché una bozza deve poter esistere. I campi attesi non sono
  desiderati, sono contati: quelli che oggi hanno **tutte** le voci (1026 Pokémon, 919
  mosse, 397 oggetti, 386 abilità). ⚠️ `bp` sulle mosse è escluso di proposito, ce l'hanno
  760 su 919 perché le mosse di stato non hanno potenza: chiederlo avrebbe dichiarato
  incompleta una voce giusta. Il caso del backlog — la voce col solo `name` — ora entra con
  **5 avvisi** invece che con un `200 ok` muto.
---

## 19/08/2026

**I dati hanno un proprietario — schema, rete e la prima sezione (§1.1, primo blocco)**

- ✅ **La colonna sta solo sulle quattro radici**: `user_id INTEGER REFERENCES users(id)` su
  `games`, `teams`, `arduino_projects`, `pc_builds`. `team_members` e `pc_components` il
  proprietario lo **ereditano** dal padre con una join: ripeterlo sui figli vuol dire poterlo
  far divergere.
- ✅ **Il travaso ad `admin` gira una volta sola**, nel giro in cui la colonna nasce, e non a
  ogni avvio. Un `UPDATE … WHERE user_id IS NULL` permanente sarebbe il solito fallback
  silenzioso: una riga scritta domani senza proprietario diventerebbe dell'admin da sola.
  Così invece resta `NULL` e **non la vede nessuno** — sbagliato in modo visibile.
  Sul DB vero: **33 giochi, 3 team, 1 build** intestati ad admin, **0 righe orfane**.
- ✅ **`ambito_utente()` in `extensions.py`** torna *sempre* una condizione, mai la stringa
  vuota: utente → le sue righe; admin → `1=1`, e con `di=<id>` un utente solo; **nessuna
  sessione → `0=1`**, che è il ramo che deve fallire chiuso. Con `e_admin()` e `utente_id()`,
  quest'ultima capace di ripescare l'id **per nome** per le sessioni già aperte quando la
  colonna è entrata in servizio: il cookie sopravvive al riavvio, e senza quel ramo chi era
  già dentro si sarebbe visto la sezione vuota senza capire perché.
- ✅ **`e_admin` ha una definizione sola**: `app.py` la ricalcolava a mano nel context
  processor, ora chiama quella di `extensions.py`.
- ✅ **La rete: `scripts/controlla_proprietario.py`**, sul modello di
  `controlla_traduzioni.py`. Legge i sorgenti con `ast` e mette ogni query sui contenuti in
  una di quattro file: **filtrata** (nomina `user_id`, o innesta la condizione di
  `ambito_utente()`), **dichiarata** (sta in `ECCEZIONI` con scritto perché), **a tabella
  calcolata** (il nome della tabella non è nel testo: nessun controllo automatico può
  giudicarla, va letta), **scoperta**. Esce con 1 se resta anche una scoperta.
- ⚠️ **Tre trappole trovate scrivendo lo script stesso**, e tutte e tre erano silenzio: i
  pezzi letterali di una f-string sono **anche** nodi `Constant` a sé, e ogni query composta
  veniva contata due volte, una intera e una monca; la docstring di `ambito_utente()` mostra
  una query d'esempio e veniva **contata come query vera** (lo stesso inciampo delle `t()`
  citate nei commenti Jinja); e soprattutto una query che si costruisce il **nome della
  tabella** — il travaso di `admin.py` gira sulle quattro radici in un ciclo — **non era vista
  affatto**. Invisibile è peggio che scoperta: ora hanno una categoria loro.
- ✅ **Pokémon è la prima sezione convertita**, ed è coperta: **7 query filtrate, 7
  dichiarate, 0 scoperte**. Le dichiarate sono i due `team_members` che ereditano dal team
  già verificato, i due dell'elenco già filtrato, e le **tre query sulle regulation** — che
  sono dati condivisi in file, non in `hub.db`: chi ne cancella una deve sapere se la usa
  **qualcuno**, non se la usa lui. Sono già route da amministratore da §1.2.
- ⚠️ **Il buco vero non era la SELECT, era il salvataggio**: `_team_upsert()` cancella e
  riscrive i membri **dopo** l'UPDATE del team. Con l'UPDATE filtrato ma senza controllo, un
  `UPDATE` a vuoto non dice niente e il `DELETE FROM team_members` sotto avrebbe **svuotato la
  squadra di un altro**. Ora si esce sul `rowcount == 0`, prima di toccare i membri.
- ✅ **Verifica: 17 prove su 17**, su una **copia** di `hub.db` (la lezione del 16/08). Utente
  nuovo: elenco vuoto, nessun badge, nessuna tendina; crea un team e lo vede, intestato a lui.
  Digitando l'URL del team dell'admin: apertura respinta, eliminazione respinta (il team c'è
  ancora), modifica respinta (il nome non diventa «RUBATO»), **membri non svuotati**.
  Admin: **4 team su 4** con il badge del proprietario, filtro `?utente=` → **1** e **3**.
  Eliminando l'utente, il suo team **resta** e passa all'admin: 4 team, nessuno perso.
- ✅ **Eliminare un utente non porta via i suoi dati**: `admin.py` li travasa
  all'amministratore **prima** della `DELETE`, che con le chiavi esterne accese fallirebbe.
  Deciso il 19/08/2026, stessa scelta fatta per le righe preesistenti.
- ✅ **Sweep: 0 errori su 11 pagine × 2 lingue** (22 rese, 30 blocchi `<script>` e 1572
  handler inline per lingua). Tre falsi allarmi erano dello strumento, non delle pagine: un
  `return` in cima a un handler è **legale** dentro `new Function()`; i blocchi
  `type="application/json"` sono dati e non codice; e gli handler vanno cercati **fuori** dagli
  `<script>`, perché dentro il JS ci sono stringhe che ne costruiscono a pezzi. Un quarto era
  vero ma non nostro: `moves_editor.html` usa `d.damage_class?.name`, e l'optional chaining è
  del 2020 mentre `esprima` è del 2018.
- ✅ **Traduzioni: 590 chieste, 590 nel dizionario**, zero mancanti, vuote, orfane o doppie.
  Tre voci nuove (`Utente:`, `senza proprietario`, `Nessun team per questo utente.`).
  ⚠️ La frase è stata riscritta **senza apostrofo**: dentro `t('…')` andrebbe protetto, e la
  regex di `controlla_traduzioni.py` **taglia la chiave sull'apostrofo protetto** — la chiave
  finiva a «Nessun team per l».

**§1.1 chiusa lo stesso giorno: le altre cinque sezioni, 78 query su 78**

- ✅ **Il conto finale**: **52 filtrate, 26 dichiarate, 0 scoperte**. Le dichiarate non
  sono deroghe generiche: ognuna ha scritto **perché**, e sono di tre tipi soltanto —
  la riga figlia che eredita dal padre già filtrato (`team_members`, `pc_components`),
  il dato **condiviso di suo** (le tre query sulle regulation, l'elenco dei 53 argomenti
  Python), e le due scritture a **tabella calcolata** che girano su tutte e quattro le
  radici in un ciclo.
- ⚠️ **Gaming ha richiesto un secondo helper, e non è una rifinitura.** `ambito_utente()`
  all'amministratore risponde «vedi tutto», il che è giusto in lettura e **sbagliato in
  scrittura**: l'import da Steam cerca gli appid già presenti per non duplicarli, e con
  l'elenco di tutti un admin che importa la propria libreria **riscriverebbe le ore
  giocate di un altro** invece di crearsi la riga sua. Da lì `solo_mie()`, senza deroga.
  Provato: con la cavia *Call of Duty®* (appid 1938090) l'utente importa 999 ore, la riga
  dell'admin **resta a 104,1**, e il secondo import aggiorna la sua senza duplicare.
  La regola in una frase: **si legge con `ambito_utente()`, si scrive con `solo_mie()`**.
- ✅ **Arricchimento generi e tag con la stessa regola**: ognuno lavora sulle proprie
  righe, admin compreso, così il contatore «rimasti» dice esattamente ciò che il lotto
  successivo toccherà. Provato: l'API ne conta 1, e 1 sono le sue.
- ⚠️ **In Gaming il nome del proprietario si legge a parte, non con una join.** Gli
  ordinamenti finiscono con `id DESC`, e in una join fra `games` e `users` `id` sarebbe
  **ambiguo**: SQLite avrebbe sollevato. Due righe di dizionario costano meno del rischio.
- ✅ **Python: la tabella nuova, non 53 righe per utente.** `python_progress(user_id,
  topic_id, done)` con chiave primaria doppia; l'elenco dei 53 argomenti resta **uno e
  condiviso**, e chi non ha ancora spuntato niente nasce a zero grazie alla LEFT JOIN,
  senza seminare righe a ogni utente nuovo. Il travaso delle spunte già messe gira **una
  volta sola**: provato su una copia con 7 spunte finte → **7 su 7 all'admin**, e un
  secondo `init_db()` **non le raddoppia**.
- ⚠️ **`python_topics.done` resta nel DB e non la legge più nessuno.** È la fotografia
  delle spunte dell'admin al 19/08/2026: toglierla è una migrazione a sé, va con
  l'inventario del codice morto. Nel frattempo `esporta_dati.py` ha **`python_progress`
  in elenco** — senza, il backup avrebbe perso il progresso di tutti in silenzio,
  esportando una colonna `done` ferma al giorno della migrazione.
- ✅ **Dashboard: due filtri diversi per due domande diverse.** I permessi per sezione
  dicono *cosa* si vede, il proprietario *di chi* sono le righe contate. Prima da lì un
  utente leggeva quanti team e quanti giochi esistono in tutto — il numero che le altre
  pagine gli nascondono. Lo scarico JSON idem, e il progresso Python esportato è quello
  **di chi scarica**, non la colonna della riga.
- ✅ **PC Builder ha lo stesso buco di `_team_upsert()`**, e la stessa cura: `save`
  cancella i componenti **dopo** l'UPDATE della build. Provato: un utente che salva
  sull'id della build dell'admin non ne cambia il nome e **non le svuota i 5 pezzi**.
- ✅ **Verifica complessiva: 54 prove** su copie di `hub.db` — **17** su Pokémon, **18**
  su Gaming, **19** su Arduino, PC Builder, Python e Dashboard. Più **sweep 0 errori** su
  19 pagine × 2 lingue e **traduzioni 590/590**: le tre voci nuove degli elenchi Pokémon
  e Gaming bastavano già, e in Arduino e PC Builder l'italiano è scritto in chiaro perché
  quelle sezioni non sono tradotte per scelta.
- ✅ **Lo sweep è diventato uno script**, `scripts/sweep_pagine.py`: il giro che si faceva
  a mano ora è rieseguibile e ha un exit code. `requirements.txt` guadagna `esprima`,
  dichiarato come dipendenza di **sola verifica** — node su questa macchina non c'è.

**Il quarto endpoint fantasma: `/api/team/<id>` ora esiste**

- ✅ **Il pulsante 📊 sulle schede di `/pokemon` funziona.** Apriva il calcolatore e la
  barra dei sei Pokémon del team **non compariva**, senza dire perché: `calcolatori-ui.js`
  chiamava `/api/team/<id>`, che **non era nella `url_map`**, e il 404 moriva dentro un
  `catch(e){console.warn(…)}`.
- ⚠️ **«Manca la route» era solo metà del baco.** Il contratto lo detta il client, che era
  già scritto, e **due dei nomi che legge nel DB non esistono**:
  - **`ev_*` ← `sp_*`**. Non sono gli EV del gioco vero (252 a stat, 510 in tutto): sono
    gli **SP** di questo progetto, max 32 per stat e 66 in totale. Che sia la stessa cosa
    è verificato su due punti indipendenti — i campi del calcolatore hanno `max="32"`, e
    la regola #8 è scritta «32 SP atk». È una traduzione fra due nomi, non una conversione.
  - **`mega_stone` è la colonna vecchia**, e su ogni riga salvata da quando esistono le
    meccaniche vale `NULL`: oggi la Mega sta in `mechanic_type='mega'` + `mechanic_value`.
    Si risponde con la colonna se c'è, altrimenti con la meccanica, così il client resta
    com'è.
- ✅ **Gli IV non si mandano, di proposito**: questo progetto non li salva, e il client fa
  già la cosa giusta (`m[ivMap[s]]!==undefined ? … : 31`). Mandare uno zero sarebbe un
  dato inventato che cambia i conti.
- ✅ **Il team è di qualcuno**: la route legge con `ambito_utente()` come tutto il resto dal
  19/08, e un team che non è tuo risponde **404 «non trovato»**, non «vietato».
- ✅ **Verifica: 15 prove su 15** su una copia di `hub.db`, con un membro scritto apposta —
  Incineroar Adamant, SP 4/32/8/0/12/10, meccanica `mega` — perché le tre righe vere hanno
  tutto a zero e su quelle il test sarebbe passato **anche con la mappatura sbagliata**.
  `sp_atk` 32 arriva come `ev_atk` 32, `sp_spdef` 12 come `ev_spdef` 12, la Mega arriva
  come `mega_stone`, nessuna chiave `iv_*` nella risposta, i campi grezzi restano. Chi non
  è il proprietario: **404**; chi non ha fatto login: **302**; un id inesistente: **404
  pulito, non 500**.
- ⬜ **Quello che questa verifica non dice**: che la barra **compaia nel browser**. È JS che
  gira nella pagina, e per provarlo davvero servirebbe entrare nell'app con la password.
  I nomi dei campi sono stati confrontati **uno per uno** con quelli che il client legge,
  ma il clic finale sul pulsante 📊 resta da fare a mano.






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
