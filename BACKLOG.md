# 📋 BACKLOG — Personal Hub

> **Qui c'è solo ciò che è aperto.** Le voci chiuse stanno in [`STORICO.md`](STORICO.md),
> una riga per lavoro con la data e i numeri della verifica.
> Aggiornato: **22/09/2026**. Fonte storica: `Nuove implementazioni.docx` (verde = fatto).

Legenda: ⬜ da fare · 🟨 parziale · ⚠️ trappola nota, da rileggere prima di toccare la zona

**Indice**

1. [Le trappole che valgono ancora](#-le-trappole-che-valgono-ancora) — leggere prima di lavorare
2. [I blocchi aperti](#1-i-blocchi-aperti-quattro-su-sei)
3. [I lavori a metà](#2-i-lavori-a-metà)
4. [Bachi noti](#3-bachi-noti)
5. [Voci minori, per sezione](#4-voci-minori-per-sezione)
6. [🏁 Il giro di collaudo finale](#5--il-giro-di-collaudo-finale-va-fatto-per-ultimo)

---

## ⚠️ Le trappole che valgono ancora

Non sono storia: sono le cose che questo progetto ha già pagato e che tornano a mordere.
(Le regole di metodo — regola #8, sweep `new Function()`, `salva_catalogo()` — stanno in
`CLAUDE.md`; qui c'è solo ciò che è specifico dei dati e del codice.)

| Zona | La trappola |
|---|---|
| **Dati mancanti** | `moves: null` **non** vuol dire «nessuna mossa», vuol dire «non lo sappiamo». Le forme inventate non stanno su PokéAPI: se `null` valesse zero, diventerebbero inutilizzabili. Stessa logica per `roster: null` = tutto il catalogo |
| ⚠️ **Una voce senza `slug` sparisce dal moveset, e sembra una forma inventata** | Trovata il 13/09/2026. `indice_catalogo()` in `importa_mosse_specie.py` prende **solo** le voci del catalogo che hanno il campo `slug`: è il verso giusto (senza slug non c'è niente da cercare nel dump), ma vuol dire che una forma **vera** a cui lo slug manca esce dal moveset **insieme** alle Mega fan-made, e a schermo prende lo stesso avviso giallo «nessun elenco mosse». Nessun errore, e il rapporto dell'import la elenca sotto «forme che PokéAPI non conosce», che per lei è **falso**. Così i tre Gourgeist e Floette Fiore Eterno sono rimasti senza le loro 397 e 229 righe di mosse dal 12/08 al 13/09. La regola: **prima di dare per inventata una voce senza moveset, cercarne lo slug nel dump.** Lo script è `scripts/aggiungi_slug_forme.py`, e lo slug non si scrive a occhio — le sei base stat devono combaciare con quelle del dump, altrimenti si prende l'elenco mosse di un altro Pokémon senza accorgersene |
| ⚠️ **Il moveset di Champions è fermo a M-B** | Trovato il 14/09/2026 con `scripts/verifica_moveset.py`. La lista `champions` di PokéAPI arriva a Regulation M-B e non ha la **versione 1.2.0** (uscita il 9 settembre 2026): 26 voci arrivate con quella versione restano senza lista, e a schermo prendono l'avviso giallo «nessun elenco mosse», esattamente come una forma inventata. **Nessun errore.** Riscaricare il dump non serve, perché è PokéAPI a non averla. Prima di dare per mancante una specie di Champions, guardare la frase «available from Version …» sulla sua pagina Bulbapedia. ⚠️ Dal 18/09/2026 le **mosse** della 1.2.0 sono allineate (vedi la riga qui sotto sulle toppe), ma quelle 25 voci senza lista **no**: sono il roster di **Regulation M-C**, che la nota ufficiale dice aggiunto proprio con la 1.2.0 |
| ⚠️ **`applica_toppe_champions.py` riscrive la sezione `toppe` per intero** | Dal 21/09/2026. La riga era `documento["toppe"] = {…derivate…}`: una toppa aggiunta a mano nel JSON sarebbe sparita al giro dopo **senza nessun errore**. Le toppe che il confronto con Bulbapedia **non può produrre** — oggi una sola, Morpeko, perché Bulbapedia ha un blocco unico per le due forme — stanno ora in `TOPPE_A_MANO` dentro lo script, e vengono unite alle derivate. Chi ne aggiunge una la scrive lì, non nel file |
| ⚠️ **Le liste integrate stanno fuori da `pokemon_moves.json`** | Dal 14/09/2026 (Pawmot). `pokemon_moves.json` lo **rigenerano** `importa_mosse_specie.py` e l'import dal pannello: una lista scritta a mano lì dentro sparirebbe al giro dopo, senza errori. Le integrazioni stanno quindi in `data/catalog/moveset_integrazioni.json`, con fonte e versione, e tutte e due le strade le riapplicano con `applica_integrazioni_moveset()`. **Il dump vince**: dove PokéAPI avrà una lista sua, l'integrazione non si applica e l'import la segnala come «superata», da togliere. Non si modifica il blocco `champions` a mano |
| ⚠️ **L'elenco `moves` di una regulation è derivato, non curato** | Dal 18/09/2026. Lo scrive `scripts/allinea_mosse_regulation.py` dall'unione delle mosse del roster, e **non si aggiorna da solo**: un Pokémon aggiunto a MA porta con sé mosse che restano fuori dalla tendina del calcolatore **senza nessun avviso**, perché quella tendina è l'intersezione fra l'elenco della regulation e la lista del singolo Pokémon. È esattamente il baco che lo script ha chiuso (3239 mosse nascoste su 17219 in MA), e si riapre da sé se lo script non viene rilanciato. **Dopo ogni modifica a un roster: `python scripts/allinea_mosse_regulation.py`.** Modificarlo a mano dall'editor contenuti funziona, ma il giro dopo lo script lo riscrive |
| ⚠️ **Tre livelli sopra il dump, e fanno cose diverse** | Dal 21/09/2026 `moveset_integrazioni.json` ha una **terza** sezione: `eredita`. Dà a una forma la lista della sua **specie**, dove una fonte per-forma dice che sono la stessa — le 6 Mega di Regulation M-C, che il dump non ha e a cui Bulbapedia non dà un blocco. La applica `applica_eredita_dichiarata()` **dopo** le toppe, così copia la lista finale, e **crea la voce** se il moveset non ce l'ha (cinque delle sei non esistevano affatto: il primo giro ne applicò una su sei senza dirlo). Il dump vince, come per `voci`: se un domani avrà righe per loro, l'eredità è detta **superata**. ⚠️ La derivazione è dichiarata **dentro il blocco** (`eredita_da`) e non a livello di voce: a livello di voce vorrebbe dire «tutti i blocchi», e a cinque di quelle sei la lista `main` della specie **non spetta** — nei giochi principali non esistono |
| ⚠️ **Due livelli di toppa sopra il dump, e fanno cose diverse** | Dal 18/09/2026 `moveset_integrazioni.json` ha **due** sezioni, e confonderle non dà errore. `voci` sostituisce una **lista intera** e **solo dove il dump non ne ha una** — il dump vince, è il caso di Pawmot. `toppe` aggiunge e toglie **singole mosse** sopra una lista che il dump **ha già**, ed è il caso della versione 1.2.0: `applica_toppe_moveset()`. Una toppa su una voce senza lista non ne inventa una (sarebbe una lista di una mossa sola), e una toppa che non serve più viene detta **superata**, da togliere. ⚠️ E chi scrive le toppe deve **disfare quelle già presenti prima di misurare**: `pokemon_moves.json` le contiene già, e confrontando quello la differenza sparisce — il secondo giro cancellerebbe il proprio lavoro in silenzio. È il motivo di `disfa_toppe()` in `scripts/applica_toppe_champions.py` |
| ⚠️ **In `main` vince il gioco più recente, e «più recente» non vuol dire «più completo»** | Dal 21/09/2026. `main` prende l'ultimo version group in cui la voce compare, e fino a quel giorno bastava questo: il risultato era che **Leggende Arceus** e **Let's Go**, che hanno un sistema di mosse ridotto, vincevano su Scarlatto/Violetto per **77 voci** — Abra con **una** mossa sola, e nessun errore da nessuna parte. Ora `VG_FUORI_SERIE` in `pokeapi.py` li tiene fuori, e li usa **solo come ripiego** per chi non compare altrove (Partner Pikachu ed Eevee). ⚠️ Due cose da sapere prima di toccarlo: **`legends-za` e `mega-dimension` sono nell'elenco pur avendo zero righe oggi**, perché hanno order 30 e 31 e il giorno che PokéAPI li riempie diventerebbero da soli la sorgente di centinaia di voci — il rapporto dell'import stampa quante righe ha ognuno degli esclusi, così se uno smette di essere vuoto si va a guardare; e la regola è **una sola funzione**, `scegli_vg_main()`, importata da tutti e due gli scrittori (`importa_mosse_specie.py` e `pokeapi.moveset()`, l'import dal pannello), perché finché erano due copie una restava indietro — ed è esattamente così che il difetto è sopravvissuto |
| ⚠️ **Una tabella nuova nasce FUORI dal raggio dei controlli, e lo zero diventa falso** | Dal 21/09/2026, trovata aggiungendo il Fantacalcio. `controlla_proprietario.py` cerca le query **per nome di tabella** (`RADICI`, `FIGLIE`, `ALTRE`) e `sweep_pagine.py` ha un **elenco di URL scritto a mano**: una sezione nuova non è in nessuno dei due, quindi tutti e due rispondono «0 problemi» **senza averla guardata**. È peggio di un errore, perché ha l'aria di una conferma. Aggiungendo le tabelle al raggio sono saltate fuori **4 query scoperte** che prima non si vedevano. La regola: **una sezione nuova si aggiunge ai due elenchi nello stesso commit in cui nasce**, e lo stesso vale per l'export (`esporta_dati.py`), o i suoi dati non finiscono in nessun backup |
| ⚠️ **Un parser HTML che chiude un blocco al primo tag di chiusura lo chiude a metà** | Dal 21/09/2026, scrivendo il lettore delle probabili. `_Probabili` chiudeva la partita al primo `</li>` incontrato dopo averla aperta — ma dentro una partita ci sono decine di `li` (i giocatori del campo, i separatori), quindi il primo separatore la chiudeva, e tutto quello che veniva dopo finiva fuori: il sintomo era che **le dieci squadre in trasferta restavano senza modulo**, esattamente dieci su venti, e **nessun errore**. La cura è contare gli annidamenti (`_liv_li`, `_liv_div`), non fidarsi del primo tag che passa. ⚠️ E il modo in cui è saltato fuori è la vera lezione: la stessa pagina era stata misurata **due volte con strumenti diversi** — una regex grezza contava 20 moduli, il parser ne dava 10 — e il numero che non tornava era il baco. Su una fonte nuova la prima misura va fatta due volte, da due strade |
| ⚠️ **Una foreign key verso una tabella che l'export NON porta rompe il ripristino, ma solo quando la figlia ha righe** | Dal 21/09/2026. `fanta_roster` e `fanta_formazione` nominano `fanta_players`, e il listone **non è nell'export** di proposito (è una copia di fantacalcio.it che si rifà in un minuto). Finché la rosa era **vuota** il ripristino su un DB nuovo funzionava; è bastato **un** giocatore in rosa perché `importa_dati.py` si fermasse con «FOREIGN KEY constraint failed» — un messaggio che non dice né cosa manca né cosa fare. ⚠️ Il difetto era lì da quando la tabella è nata: non l'ha creato la riga in più, l'ha **rivelato**. Ora l'import controlla **prima di scrivere** che i giocatori nominati esistano, e se non ci sono dice di lanciare `importa_listone.py`; `prova_importa_dati.py` ha il caso, e il suo DB di prova semina i giocatori che l'export nomina. La regola generale: quando una tabella esportata punta a una **non** esportata, il caso «ripristino su DB nuovo» va provato con la figlia **piena**, non vuota |
| ⚠️ **Aprire una pagina, da oggi, può SCARICARE — e la suite di prove va isolata** | Dal 21/09/2026, con l'aggiornamento automatico del Fantacalcio: le route rileggono la fonte da sé quando la copia in cache è vecchia. Conseguenza che non era prevista: `prova_fantacalcio.py`, che per regola «non tocca `hub.db` né la rete», ha cominciato a **scaricare davvero** a ogni `GET`. Il sintomo è stato una prova che trovava **482 convocati veri** in un DB temporaneo che doveva averne zero — cioè una prova che passava o falliva a seconda di come andava la linea. La cura sta in cima a `prove()`: `F.eta_cache` torna sempre `0.0` (l'automatico non scatta mai per caso) e `F.scarica` **solleva**, così una lettura di rete non voluta si vede come errore invece di riuscire in silenzio. **Chi aggiunge un automatismo in una route deve chiedersi cosa fa alle prove**, e vale per qualunque sezione |
| ⚠️ **Un parametro che vale «vedi tutto» quando lo dimentichi** | Dal 21/09/2026. `fanta_import._rose()` nasceva con `ambito=None`, che voleva dire «conta le rose di tutti»: giusto per uno script da riga di comando, che una sessione non ce l'ha — **sbagliato** per il pulsante «Aggiorna», che una sessione ce l'ha, e che così diceva «2 dei giocatori usciti sono in una tua rosa» contando rose altrui. L'ha preso `controlla_proprietario.py`. La regola: quando la stessa funzione la chiamano il web e uno script, il «vedo tutto» **si scrive** (`TUTTE_LE_ROSE`), non si ottiene lasciando fuori un parametro. ⚠️ E lo strumento ha imparato un caso nuovo — una funzione che **riceve** la condizione invece di chiederla a `ambito_utente()` — con un criterio volutamente stretto: il parametro si chiama `ambito` **e** dev'essere letto nel corpo. Un primo tentativo più largo marcava filtrata l'intera funzione, rami senza filtro compresi: la scappatoia esatta che quello strumento esiste per chiudere |
| ⚠️ **In italiano la virgola è ANCHE il separatore decimale** | Dal 21/09/2026, preso dalla prova al primo giro sulle soglie del modificatore di difesa. `"7,5:8, 6:2"` spezzato sulle virgole dà `7` e `5:8`: una tabella diversa da quella scritta, **senza nessun errore**. Ora le coppie `media:punti` si **cercano** con una regex invece di spezzare la riga, e se dopo averle tolte resta qualcosa che non è un separatore si torna allo standard — meglio un default dichiarato che tre righe su quattro. Vale per qualunque elenco di numeri scritto a mano in questo progetto |
| ⚠️ **Il valore di partenza di un form non è il DEFAULT della tabella** | Dal 21/09/2026, trovato provando il JS in browser (lo sweep non poteva: era sintatticamente perfetto). Le tendine nuove delle regole precompilavano dai **valori ufficiali**, e le due voci che il regolamento non fissa — porta inviolata e autogol — non essendoci, partivano dal **primo valore della tendina**, cioè `0`. Una lega nuova nasceva con l'autogol che non toglie niente, mentre la tabella ha `DEFAULT -2`. Nessun errore, solo una regola sparita. Ora `VALORE_PARTENZA` è un dizionario **diverso** da `VALORE_UFFICIALE` e i due non si confondono. ⚠️ Fin quando il campo era vuoto il difetto non poteva esistere — era il DB a decidere: **dare un valore iniziale a un campo sposta la decisione dal DB al form**, e da lì in poi i due devono concordare |
| ⚠️ **La cache delle probabili invecchia in ORE, non in mesi** | Dal 21/09/2026. Le tre pagine di fantacalcio.it stanno nella stessa cache, ma non hanno la stessa scadenza: il listone cambia a ogni mercato, le **probabili cambiano fino al fischio d'inizio** — un titolare diventa panchinaro il sabato mattina. Rileggere la cache e scrivere nel DB **non dà nessun errore**, dà una formazione vecchia con l'aria di essere quella di oggi. Per questo `importa_probabili.py` stampa **sempre** l'età della copia in ore e dice `--scarica`: praticamente ogni giro delle probabili vuole `--scarica`, al contrario del listone |
| ⚠️ **`{{ nome|e }}` dentro un handler inline è un `SyntaxError` che aspetta un apostrofo** | Dal 22/09/2026, sul `confirm` che chiede se togliere un giocatore dalla rosa. L'escape HTML rende `N'Dicka` come `N&#39;Dicka`, e il browser **decodifica l'attributo prima** di passare il codice al parser JS: l'handler non compila, il `confirm` sparisce e **il form parte lo stesso**, cioè la conferma di una cosa irreversibile non c'è più. Nessun errore a schermo. E lo **sweep non lo vede finché il dato non ha l'apostrofo**: i nomi con l'apostrofo nel listone sono 2 su 597, e con nessuno dei due in rosa la pagina resa era pulita. La cura è `|tojson` con l'attributo fra **apici singoli** (regge anche le virgolette doppie); lo sweep prende solo ciò che la pagina resa contiene davvero, quindi il caso difficile va **messo nei dati di prova**. ⬜ Lo stesso handler è ancora in `admin_utenti.html:88` con `{{ u.username }}`: uno username con l'apostrofo lo romperebbe uguale |
| ⚠️ **Lo sweep controlla il JavaScript, non che l'HTML sia ben formato** | Dal 21/09/2026, trovata da Davide cliccando «Fantacalcio» in sidebar e finendo sul PC Builder. Il blocco `{% if 'fantacalcio' … %}` era finito **dentro l'attributo `class`** del link PC Builder, che non veniva mai chiuso: il parser fonde i due `<a>` in uno solo, e resta un `href="/pcbuilder"` con scritto «Fantacalcio». `sweep_pagine.py` era a **0 errori** anche così, perché rende la pagina ed esegue `new Function()` sugli script e sugli handler — un tag mai chiuso non è JavaScript, quindi non lo guarda nessuno. Un link aggiunto a `base.html` va verificato **sulla pagina resa con un parser HTML** (href per href, e `<a>` aperti = chiusi), non a occhio sul template: l'errore si legge male proprio perché il pezzo giusto è tutto lì, solo nel posto sbagliato |
| ⚠️ **Lo sweep guardava solo le pagine che si aprono con una `GET`** | Dal 21/09/2026, con l'anteprima della rosa incollata. `sweep_pagine.py` scorreva un elenco di URL e faceva `c.get()` su ognuno: una pagina che **esiste solo mandando un form** non era in nessun elenco, quindi lo sweep avrebbe detto «0 errori» senza averla mai resa — ed è una pagina piena di form, tendine e `<script>`, cioè esattamente quello che quello script esiste per controllare. È la stessa forma della trappola sulle tabelle nuove: un elenco scritto a mano che non si accorge di quello che non contiene. Ora c'è `PAGINE_POST` (URL + dati), e i dati di prova contengono di proposito un nome ambiguo e uno inesistente, perché la pagina resa abbia davvero dentro una tendina e una riga «non trovata». La regola: **una pagina nuova si aggiunge all'elenco giusto dei due nello stesso commit in cui nasce** |
| ⚠️ **Una prova costruita male dice NO a un codice giusto, e costa come un baco** | Dal 21/09/2026, tre volte in un pomeriggio scrivendo le prove del consiglio e della rosa incollata. (1) Due righe incollate identiche messe in un **dizionario per testo** diventavano una: la prova chiedeva due esiti e ne trovava uno. (2) Il «contesi» del consiglio pretendeva un disaccordo fra fascia e punti attesi che coi numeri scelti **non poteva esistere** — serviva fm > 10.8, il banco ne aveva 9.0. (3) La regola del rivale in panchina veniva provata su un banco dove **tutti** i centrocampisti erano in campo, cioè chiedendo un rivale che non c'era. Ogni volta il primo istinto è stato «allora il codice sbaglia», e ogni volta la cura era rifare il banco: il numero che una prova pretende va **contato**, non scelto perché sembra grosso. Il danno è doppio — si perde tempo e, se si «corregge» il codice per far passare la prova, si rompe quello che funzionava |
| ⚠️ **Passare `None` a una colonna con un `DEFAULT` scavalca il default** | Dal 21/09/2026, presa da `prova_fantacalcio.py` al primo giro. Il salvataggio di una lega costruiva l'`INSERT` con **tutte** le colonne delle regole, mettendo `None` dove il form non aveva niente: in SQLite un `NULL` **esplicito** è un valore, non un'assenza, quindi il `DEFAULT 3` del bonus gol non entrava mai e una lega nuova nasceva coi bonus a `NULL`. Nessun errore: il bonus semplicemente non c'era. La cura è non mettere la colonna nella query — che nell'`UPDATE` vuol dire anche «lascia il valore di prima», cioè la stessa cosa detta bene |
| ⚠️ **«PokéAPI non la conosce» quasi mai vuol dire «è inventata»** | Misurato il 21/09/2026, e per un mese si è creduto il contrario. Il rapporto dell'import stampava 16 voci sotto la frase «forme che PokéAPI non conosce», e il backlog le chiamava «forme di Davide»: **falso per 14 su 16**. I loro slug — `darkrai-mega`, `absol-mega-z`, `golisopod-mega`, … — sono **tutti in `pokemon.csv`**. PokéAPI le conosce benissimo; quello che non ha sono le **righe di mosse**, perché i loro unici giochi sono `legends-za` e `mega-dimension`, i due version group che nel dump hanno **zero righe** (gli stessi che `VG_FUORI_SERIE` sorveglia). Fra quelle 14 ce n'erano **cinque Mega vere di Regulation M-C** — Mega Absol Z, Mega Garchomp Z, Mega Lucario Z, Mega Golisopod, Mega Baxcalibur — confermate da Serebii **e** da Game8. E **nemmeno le due Mega Meowstic** erano sconosciute, scoperto lo stesso giorno: `meowstic-male-mega` e `meowstic-female-mega` sono nel dump **con le loro righe di mosse**. Mancava solo lo `slug` nel catalogo, e mancava perché `aggiungi_slug_forme.py` si **rifiutava** di scriverlo: le sei base stat della femmina non combaciavano, perché la voce era rimasta a **466**, il totale della forma **non** Mega. Cioè un dato sbagliato teneva fuori una voce vera, e il rifiuto era il verso giusto. Corretto a 566 su tre fonti concordi. Quindi delle 16 la frase era falsa per **tutte e 16**. ⚠️ La regola generale, che era già scritta dal 13/09 e non era stata applicata a questa conclusione: **prima di dare per inventata una voce senza moveset, cercarne lo slug nel dump.** Ora il rapporto dell'import stampa i due gruppi separati, con l'etichetta giusta |
| ⚠️ **Una toppa è scritta con la chiave di una specie, e le forme non sono la specie** | Trovata il 21/09/2026 da `verifica_moveset.py`. Le toppe della 1.2.0 nominavano **33 specie**, e si fermavano lì: **19 forme** di quelle specie — Mega Absol, Mega Charizard X e Y, Aegislash (Blade Forme), Mimikyu (Busted Form), … — sono rimaste senza lo *Slash* che la loro specie aveva preso, e **sono tutte in MA e MB**. A schermo voleva dire che Absol poteva sceglierlo e Mega Absol no, che è lo stesso Pokémon a metà partita. Nessun errore, solo la tendina più corta. Ora `applica_toppe_moveset()` raggiunge anche le forme, ma **solo** quelle la cui lista, tolte le mosse che la toppa nomina, è **identica** a quella della specie: una forma con una lista sua (le Rotom, Hisuian Samurott) finisce in un terzo elenco che l'import stampa, e non viene toccata. Il confronto ignora le mosse nominate proprio perché regga sia sul file appena rigenerato dal dump sia su uno già toppato a metà. ⚠️ Chi aggiunge una toppa nuova non deve elencare le forme a mano: se lo fa, quella forma viene saltata dalla propagazione (`if nome_forma in toppe`) ed è giusto così, ma la sua lista va scritta intera |
| ⚠️ **L'eredità è costruita prima che integrazioni e toppe entrino** | Dal 21/09/2026. In `costruisci_moveset()` la forma Gigantamax copia il dizionario della specie: **mutare** una lista condivisa si propaga, **aggiungere un blocco nuovo alla specie no**. Integrando le 25 voci di Regulation M-C è successo esattamente questo: Cinderace, Inteleon, Rillaboom e Toxtricity hanno preso la loro lista `champions` da Bulbapedia, e le loro quattro Gigantamax — che dichiarano `eredita_da` — sono rimaste **senza**, con l'avviso giallo «nessun elenco mosse». Nessun errore. Ora `riallinea_forme_eredi()` gira **dopo** integrazioni e toppe in tutti i percorsi che scrivono il file, e `prova_moveset_main.py` controlla che ogni voce con `eredita_da` abbia davvero la lista della sua base |
| ⚠️ **Una forma Gigantamax condivide l'oggetto della sua base, non una copia** | Trovata il 21/09/2026. In `costruisci_moveset()` l'eredità è una copia **superficiale**: `voce["champions"]` della Gmax **è lo stesso dizionario** della specie base. Per l'import in blocco è il verso giusto — `eredita_da` dichiara proprio che la lista è quella della base, quindi una toppa applicata a `charizard` arriva anche alla sua Gmax — ma `applica_toppe_champions.py` lavora sul JSON **dal disco**, dove le due liste sono due oggetti separati, e lì la propagazione non c'è. Risultato: il file del 18/09/2026 aveva `Charizard (Gigantamax Form)` **senza** lo *Slash* della 1.2.0 che la sua base aveva, e nessuno se n'è accorto. La rigenerazione del 21/09 le ha riallineate (`champions` 20 699 → 20 700 mosse, una sola voce). La rete: `prova_moveset_main.py` controlla che **ogni** forma con `eredita_da` abbia davvero la lista della sua base |
| ⚠️ **I dati delle mosse sono quelli di Champions, non di Scarlatto/Violetto** | Dal 18/09/2026, decisione di Davide. Champions **ribilancia** le mosse rispetto ai giochi principali, e il catalogo viene da PokéAPI, cioè da S/V: la sezione «Changes from Scarlet and Violet» della pagina «Pokémon Champions» su Bulbapedia elenca una trentina di differenze. Delle 29 misurabili il catalogo ne aveva **17 già giuste** e 12 no (Slash bp 70→80, Grav Apple 80→90, Crabhammer precisione 90→95, Snap Trap da Erba ad **Acciaio**, …): un numero sbagliato, nessun errore a schermo. Le riallinea `scripts/allinea_dati_mosse_champions.py`. ⚠️ Quella sezione ha in fondo un blocco **commentato** di mosse «that aren't in the game yet» (Gear Grind, Anchor Shot, Hyper Drill, …): quelle **non** vanno scritte. E i **PP** non hanno dove andare — nessuna delle 919 mosse ha quel campo |
| ⚠️ **Un file di dati si riscrive come lo scrivono gli altri** | Due modi di sporcare un diff, trovati il 18/09/2026 su `pokemon_moves.json` (3 MB). **(1) L'indentazione**: i due scrittori del file usano `indent=1`, uno script nuovo con `indent=2` lo reindenta tutto — **100 000 righe di diff per 33 voci cambiate**, e la modifica vera diventa impossibile da leggere in revisione. ⚠️ `salva_moveset()` in `blueprints/pokemon.py` usa ancora `indent=2`: l'import dal pannello reindenta il file, ed è così da prima, segnalato e non corretto. **(2) L'ordine dei set**: l'hash delle stringhe in Python è randomizzato per processo, quindi iterare un `set` di nomi dà un ordine diverso a ogni giro. Uno script che scrive nell'ordine in cui itera **non è idempotente**, e si vede solo confrontando l'md5 di due giri in **processi separati** — nello stesso processo l'ordine è stabile e la prova passa. Si chiude con `sorted()` e riordinando i dizionari scritti |
| ⚠️ **Il Pokedex mostra le mosse di Champions, e per 1009 voci su 1342 non ne mostra nessuna** | Dal 18/09/2026, decisione di Davide: «voglio solo ciò che imparano in Champions». `pokedex` è passata da `moveset: main` a `champions`, che copre **333 voci** — il roster del gioco. Tutte le altre, Abra e **Amoonguss** compresi, prendono l'avviso giallo «nessun elenco mosse: sono mostrate tutte» e la tendina da 919. **Non è un guasto**, è la risposta onesta: `null` vuol dire «non lo sappiamo», ed è la stessa che prendono le forme inventate. ⚠️ Vale anche per il **caso della regola #8**, che gira proprio su `pokedex` con Amoonguss: l'avviso giallo su Amoonguss è previsto, il danno si calcola lo stesso perché la mossa si scrive a mano (Buio, fisica, BP 100). Chi «aggiusta» quell'avviso rompe una decisione, non un baco |
| ⚠️ **Ci sono due export, e uno non deve mai entrare in git** | Dal 18/09/2026. `esporta_dati.py` senza opzioni scrive `data/backup/hub_export.json`, che **viene committato** e per questo **non contiene le password**. `--completo --uscita <percorso>` scrive il backup vero, con gli **hash delle password** e `regulations`. Non ha un percorso di default di proposito: pretende `--uscita` e si **rifiuta** di scrivere se risalendo l'albero dalla destinazione trova un `.git`. In `.gitignore` c'è la seconda rete (`*_completo.json`). ⚠️ Chi aggiunge un default «comodo» dentro al repo, o toglie il controllo per far passare una prova, rimette in piedi esattamente il buco per cui `hub.db` non è versionato |
| **Risoluzione per nome** | Due chiavi diverse possono avere lo stesso `nome_it`/`nome_en`, e il catalogo Pokémon cita le abilità col nome **inglese** mentre le chiavi sono italiane. Ogni confronto per nome va fatto con `risolviChiave()` / `_INDICE`, mai con un match esatto sulla chiave |
| **Fallback silenziosi** | Più di un baco qui non dava errore, dava il numero sbagliato: lo Speed Tier che ricadeva su una lista statica, `/api/moves` che leggeva il file di MA, un alias che rispondeva Mega Venusaur. Se un loader ha un ramo di riserva, va verificato **quale dei due** sta rispondendo |
| **Endpoint fantasma** | **Quattro volte** il JS ha chiamato una risposta che nessuno aveva mai implementato: `/api/regulations`, `d.moves`, `d.regulation` e — trovato il 17/08 e scritto il 19/08 — `/api/team/<id>`. Tutte e quattro fallivano **dentro un `catch` muto**, quindi la pagina si apriva e mancava solo un pezzo, senza un errore a schermo. Sono tutte chiuse, ma la classe resta: **un `catch(e){}` vuoto qui è un baco in attesa**, e il modo di trovarli è leggere cosa il JS chiede e cercarlo nella `url_map` |
| **Le Mega** | La firma «+75 HP» individua le voci convertite **specie per specie, non stat per stat**: su Froslass cinque valori su sei erano convertiti e uno no, e la regola applicata in blocco ha rotto proprio quello. E la conversione può partire da una forma diversa da quella di testa (Zygarde Complete) |
| **File storici** | `data/pokemon_catalog.json`, `roster_ma.json`, `moves_ma.json`, `items_ma.json`, `abilities.json` sono ancora lì come **fallback**, e `pokemon_catalog.json` contiene le Mega nella vecchia forma convertita. Si dismettono al collaudo finale, non prima |
| **Scritture concorrenti** | `salva_catalogo()` riscrive il file intero **senza lock**: due salvataggi nello stesso istante non danno errore, l'ultimo vince e l'altro si perde. Rilevante appena l'app va online |
| **`t` come variabile** | `{% for t in … %}` in `moves_editor.html:97,153` e `regulation_editor.html:215` **ombrerebbe la funzione `t()`** delle traduzioni. Vanno rinominate quando si traducono quei due file |
| **`|tojson` negli attributi** | `|tojson` rende `"pokedex"` **con le doppie**: dentro un attributo delimitato dalle doppie, l'attributo si chiude a metà. Usare gli apici singoli. ⚠️ Trappola già pagata due volte — il 12/08 e di nuovo il 13/08, ripresa dallo sweep entrambe le volte |
| **Commenti e traduzioni** | `controlla_traduzioni.py` legge il **file grezzo**, commenti Jinja compresi: una chiamata a `t()` citata come esempio dentro un `{# … #}` viene contata fra le stringhe chieste dal codice e chiede una traduzione che non serve a nessuno. Nei commenti si descrive, non si cita la sintassi |
| ⚠️ **Lo sweep statico non basta** | `new Function()` su script e handler dice che la **sintassi** è valida, **non** che il codice giri. Il 13/08 la tabella dell'editor mosse è rimasta **vuota** con lo sweep a zero errori: `renderTable()` lanciava `tf is not defined` a runtime. Ogni giro di verifica va chiuso **caricando davvero** le pagine e contando le righe che compaiono — 919 mosse, 1343 tag del roster, 397 oggetti, 386 abilità. Una tabella vuota non dà errore a schermo |
| **`t`/`tf` e l'ordine degli script** | Sono definite in un `<script>` nel **`<head>`** di `base.html`, e devono restarci. Più di un template le chiama **durante il parsing** e non dentro un evento (`moves_editor.html` chiude il suo script con `renderTable()`): con la definizione in fondo alla pagina, come era fino al 13/08, quella chiamata non le trova |
| ⚠️ **Una copia in memoria che non guarda più il file** | Trovata il 21/08/2026 in `blueprints/api_pokemon.py`: il catalogo era letto **all'import del modulo** e non più riletto, quindi una voce aggiunta dall'editor compariva nel roster e dava **404** aprendola, e una base stat modificata continuava a rispondere col valore vecchio **senza errore** fino al riavvio. Ora segue l'mtime, come `_MOVESET` e `_TRADUZIONI`. La regola generale: **un file che si modifica mentre l'app gira non si legge una volta sola.** L'unica copia a modulo rimasta è `CHAMPIONS_BST` in `data.py`, ed è voluto — serve **solo** da riserva quando `load_catalog()` non legge niente, cioè quando avere dati vecchi è meglio che non averne |
| **Variabili mancanti nei template** | Jinja rende una variabile che non è nel contesto come **stringa vuota**, senza dire niente. `items_editor.html` usava `{{ regulation }}`, che quella route non ha **mai** passato: la conferma di archiviazione ha sempre detto «Archivia gli oggetti correnti ()?» con le parentesi vuote. Se ne è accorto solo `\|tojson`, che su `Undefined` solleva invece di tacere |
| ⚠️ **Solo Pokémon e Gaming sono tradotte** | Arduino, Python, PC Builder, Dashboard, login e utenti sono in italiano **per scelta** (13/08/2026), e la **sidebar con loro**. Il pulsante lingua compare solo dove la sezione è tradotta: l'elenco è `sezioni_tradotte` in `base.html`, unico punto. Pulsante confinato e shell italiana sono la **stessa** decisione — tradurre la sidebar lascerebbe chi mette EN e va su Arduino senza un modo per tornare indietro |
| ⚠️ **Le `desc` sono italiane per scelta** | **Non è un lavoro rimasto a metà.** Le 1584 descrizioni di mosse, oggetti e abilità restano **solo in italiano** per decisione di Davide del 13/08/2026, presa dopo aver visto il conto: i **nomi** sono bilingui al 100%, le descrizioni no e non lo diventeranno. Quindi in modalità inglese si legge un nome inglese con sotto una descrizione italiana, ed **è previsto**. `desc_en` non esiste e non va aggiunto; non serve nessun import da PokéAPI né una gemella di `nome_vis()` per i testi |
| **Una parola italiana, due inglesi** | La chiave del dizionario **è la frase italiana**, quindi una parola che in inglese cambia col contesto non è esprimibile. Caso vivo: `Abilità` è la linguetta del catalogo (→ *Abilities*) **e** l'etichetta di un campo singolo nel team builder e nello Stat Preview, dove dovrebbe essere *Ability*. Oggi vince il plurale. Si risolve solo cambiando la frase **italiana** in uno dei due punti, e va fatto se e quando dà fastidio: storpiare l'italiano per aggiustare l'inglese è un cattivo affare |
| **Le piattaforme del calendario** | `PIATTAFORME_TENUTE` in `blueprints/gaming.py` è un elenco di **inclusi**, quindi **fallisce chiuso**: una piattaforma che IGDB aggiunge domani non entra in cache finché nessuno la scrive lì. È voluto, ma il silenzio no — l'unico segnale è l'elenco delle **escluse per nome** che l'import scrive a fine giro. Un nome che non ti aspetti lì dentro vuol dire «aggiungimi». I nomi sono le stringhe esatte di IGDB (`PC (Microsoft Windows)`, `Xbox Series X\|S`), non si indovinano |
| ⚠️ **Una route nuova sotto `/pokemon/*` nasce chiusa** | Dal 17/08/2026 c'è un `before_request` in `blueprints/pokemon.py` che lascia passare **solo** le viste elencate in `APERTE_A_TUTTI`; per tutte le altre serve un amministratore. È il verso giusto — una lista del vietato fallirebbe **aperta** — ma vuol dire che una route nuova destinata a tutti **non funzionerà** finché non la si scrive lì, e il sintomo è un redirect a `/pokemon` con un flash, o un 403 JSON se il path contiene `/api/`. I nomi nell'elenco sono quelli delle **viste**, non gli URL |
| ⚠️ **Una query nuova sui contenuti nasce scoperta** | Al contrario delle route sotto `/pokemon/*`, che dal 17/08 nascono **chiuse**, una `SELECT` nuova su `games`, `teams`, `arduino_projects` o `pc_builds` non filtra per proprietario finché non lo si scrive, e mostrare la riga di un altro **non dà nessun errore**. L'unico segnale è `python scripts/controlla_proprietario.py`, che va eseguito dopo aver toccato una query: dice **filtrata**, **dichiarata**, **a tabella calcolata** o **scoperta**, ed esce con 1 se resta una scoperta. Le eccezioni si dichiarano lì dentro **con il testo della query**: se la query cambia, l'eccezione smette di combaciare ed è voluto |
| ⚠️ **Si legge con `ambito_utente()`, si scrive con `solo_mie()`** | Sono due domande diverse. Per **leggere**, l'amministratore vede tutto (`1=1`): giusto in elenco. Per **importare o arricchire**, quella deroga è un baco: l'import da Steam cerca gli appid già presenti per non duplicarli, e con l'elenco di tutti un admin che importa la propria libreria **riscriverebbe le ore giocate di un altro utente** invece di crearsi la riga sua. Misurato e provato il 19/08: la riga di admin resta a 104,1 ore e all'utente ne nasce una nuova |
| ⚠️ **`rowcount` sulle scritture filtrate** | Un `UPDATE`/`DELETE` con la condizione del proprietario che non tocca niente **non dà errore**: il codice sotto continua. In `_team_upsert()` questo avrebbe svuotato i membri della squadra di un altro dopo un UPDATE andato a vuoto. Ogni scrittura filtrata deve guardare il `rowcount` e uscire |
| ⚠️ **Una tabella senza colonna `id` è il caso che rompe gli script dei dati** | Oggi sono due: `python_progress` `(user_id, topic_id)` e `fanta_formazione` `(league_id, player_id)`. Hanno già rotto **due** script in due modi diversi — `esporta_dati.py` dichiarava **assente** una tabella che c'era (`ORDER BY id` che sollevava e finiva nel ramo «tabella non creata»), e `importa_dati.py` moriva con `KeyError: 'id'` tenendo **rotto il ripristino intero** dal 21/09 al 22/09/2026. Da entrambe le volte è uscita la stessa regola, e ora è scritta in tutti e due i file: **la chiave si chiede allo schema** (`PRAGMA table_info`, colonna `pk`), non si tiene in un elenco a mano. Chi scrive uno script nuovo che gira su più tabelle la usi, e **si fermi** se la chiave non c'è invece di ricadere su `id` |
| ⚠️ **Una tabella nuova con un `user_id` va messa in `TABELLE_UTENTE`; una sua figlia in `FIGLIE_DI`** | Dal 22/09/2026, in `extensions.py`. `TABELLE_UTENTE` dice **cosa farne** quando l'utente sparisce: `passa` (contenuto, cambia proprietario) o `cancella` (stato personale, e quante righe erano si dice a schermo). `FIGLIE_DI` dice **quali righe seguono un padre**, e serve solo alla **copia**: nel travaso le figlie seguono da sole perché il padre resta quello, in una copia il padre nuovo ha un id nuovo. Nessuno dei due è un promemoria da ricordarsi: `tabelle_senza_regola()` legge le colonne vere, `figlie_senza_regola()` legge le **chiavi esterne** vere, e le due route **si rifiutano** nominando chi manca. ⚠️ Una figlia dimenticata è la peggiore delle due: non dà nessun errore, fa nascere il padre **vuoto**. Ma la tabella nuova va messa anche in `RADICI` di `controlla_proprietario.py`, e **quello nessuno lo controlla**: una tabella fuori da quel raggio fa dire «0 scoperte» senza che nessuno l'abbia guardata — è successo tre volte (le due del Fantacalcio il 21/09, `python_progress` il 22/09) |
| **`user_id` a `NULL`** | Il travaso ad `admin` gira **solo nel giro in cui la colonna nasce**, non a ogni avvio: è voluto, perché un `WHERE user_id IS NULL` permanente intesterebbe all'admin qualunque riga scritta male, in silenzio. Il prezzo: una riga senza proprietario **sparisce dalla vista del suo autore** — ma non è persa e non è invisibile a tutti, perché l'admin filtra `1=1` e la vede, col badge che dice «senza proprietario». È lì che si va a cercarla quando qualcuno dice «il dato è sparito» |
| ⚠️ **Un campo che manca vale «main»** | La sorgente delle mosse di una regulation e' `moveset` in `data/regulations.json`, e **se manca non e' un errore**: `sorgente_moveset()` ricade su `main`. Fino al 10/09/2026 la creazione non lo scriveva affatto, quindi una regulation copiata da MA — 279 nomi di Champions — leggeva gli elenchi dei giochi principali: **80 mosse su Incineroar invece di 77**, Knock Off compresa, senza un errore da nessuna parte. Ora la creazione lo scrive sempre esplicito e il salvataggio rifiuta un nome che non esiste, ma il fallback resta: **un file scritto a mano senza quel campo dira' `main` e sembrera' giusto** |
| **Default del DB** | `extensions.py:143` crea la colonna con `regulation_id TEXT DEFAULT 'ma'`. Non è un residuo dei 14 letterali tolti l'11/08: è il default del **DB**, e cambiarlo richiede una migrazione. Oggi non fa danno perché `_team_upsert()` passa sempre un valore esplicito |

---

## 📌 L'ordine deciso il 21/08/2026

**Mettere l'app online (§1.5) va per ultimo**, per scelta di Davide: «caricare il sito da
qualche parte lo voglio tenere come una delle ultime cose». I quattro buchi di sicurezza
che rendevano pericoloso esporla sono comunque **chiusi lo stesso giorno**, quindi la
voce non è più urgente e non blocca niente — l'hub in casa funziona come sempre.

L'ordine che ne esce, e che vale finché Davide non lo cambia:

1. ~~§1.3 — le voci collegate che restano (una regulation nuova dall'interfaccia)~~
   ✅ **chiuso il 10/09/2026**
2. ~~§2.2 — le 103 abilità da fondere~~ ✅ **chiuso il 10/09/2026**: erano già fuse,
   e la rimisura l'ha detto. Restava un legame rotto su Mega Meganium
3. §4 — le sezioni: Stampa 3D, Tinkercad, PC Builder, Python

> **Cambiato il 14/09/2026**: Davide ha scelto di **finire prima la sezione Pokémon**.
> Quindi vengono anticipate l'assegnazione delle 7 categorie di oggetti vuote (§3) e la
> verifica del moveset contro Bulbapedia (§5.2). Le sezioni del §4 vengono dopo.
4. ~~§1.4 — l'export `--completo`~~ ✅ **chiuso il 18/09/2026**: resta aperta solo la falla 2 (tema e lingua non sono nel DB)
5. ~~§3 — i bachi noti~~ ✅ **guardati tutti il 10/09/2026**: tre chiusi, uno mezzo,
   uno che non si riproduce, uno lasciato apposta
6. §5 — il giro di collaudo, la verifica dei moveset, l'inventario del codice morto
7. §1.6 — le due guide, che vanno **dopo** il collaudo
8. §1.5 — l'app online

> **Aggiunta il 10/09/2026, definita il 21/09/2026**: la sezione **Fantacalcio**
> (§4.2) non è più un segnaposto — le fondamenta dei dati sono in piedi e il resto
> (formazione, probabili, consiglio) è scritto lì con le sue risposte.

---

## 1. I blocchi aperti (quattro su sei)

Erano sei, aperti il 12/08/2026: **1.2 è chiuso il 17/08/2026** e resta qui solo come riga
di richiamo, perché la regola che ha lasciato in eredità va letta prima di aggiungere una
route. Tutti **misurati sul codice, non ipotizzati**. L'ordine consigliato è quello in cui
sono scritti: 1.1 e 1.2 erano due metà della stessa domanda — *di chi* sono i dati e *chi*
può cambiarli — e 1.5 dipende da entrambe. **Sono chiuse entrambe**: 1.2 il 17/08/2026
(36 route), 1.1 il 19/08/2026 (78 query). Restano qui come righe di richiamo, perché
tutte e due hanno lasciato una regola che va letta prima di scrivere codice nuovo:
una route nuova sotto `/pokemon/*` nasce **chiusa**, una query nuova sui contenuti nasce
**scoperta**.

### 1.1 ✅ I dati hanno un proprietario — chiuso il 19/08/2026

**Trovata da Davide provando la web app**: un team Pokémon salvato da un utente **lo
vedevano tutti**, e lo stesso per giochi, progetti Arduino e build PC. I permessi per
sezione dicono **quali sezioni** vedi, non **di chi sono i dati** dentro.

Chiuso in un blocco solo: `user_id` sulle quattro tabelle radice, `python_progress` per
la sezione Python, e **78 query su 78** che ora sanno di chi parlano — 52 filtrate, 26
dichiarate con la ragione scritta, **0 scoperte**. Numeri e prove in `STORICO.md`.

> ⚠️ **La regola che resta, e va letta prima di scrivere una query nuova**: una `SELECT`
> nuova su `games`, `teams`, `arduino_projects` o `pc_builds` **non filtra da sola**, e
> mostrare la riga di un altro non dà nessun errore. Si chiede la condizione a
> `ambito_utente()` (o a `solo_mie()` se si sta **scrivendo**), e si controlla con
> `python scripts/controlla_proprietario.py`, che esce con 1 se resta una query
> scoperta. Le eccezioni si dichiarano lì dentro **con il testo della query**: se la
> query cambia, l'eccezione smette di combaciare, ed è voluto.

**⬜ Cosa resta aperto, ed è piccolo:**

- ⬜ **La colonna `python_topics.done` non la legge più nessuno.** È rimasta nel DB con
  la fotografia delle spunte dell'admin al 19/08/2026; il progresso vero sta in
  `python_progress`. Toglierla è una migrazione a sé — va con l'inventario del codice
  morto (§5.3), non prima
- ⬜ **Il proprietario non si può cambiare da interfaccia.** Se un giorno serve
  «passa questo gioco a un altro utente», oggi si fa solo dal DB. Non è stato chiesto
- ⬜ **I dati condivisi restano condivisi**: catalogo, regulation, mosse, oggetti e
  abilità non hanno un proprietario e non devono averlo — sono di tutti, e a
  proteggerli è §1.2, che li ha riservati agli amministratori

### 1.2 ✅ Gli editor Pokémon solo per gli admin — chiuso il 17/08/2026

Chiuso con `APERTE_A_TUTTI` e un `before_request` in `blueprints/pokemon.py`: **30 route
su 36** ora rispondono solo a un amministratore, le altre 6 sono le pagine d'uso. Numeri e
prove in `STORICO.md`.

> ⚠️ **Quando si aggiunge una route sotto `/pokemon/*`**: nasce **riservata agli
> amministratori**. Se deve essere aperta a tutti va scritta in `APERTE_A_TUTTI`, ed è
> voluto che il verso sia questo — una lista del vietato fallirebbe **aperta** sulla
> prossima route che qualcuno dimentica, e la dimenticanza non darebbe nessun segnale.
> Così invece si vede subito, perché la pagina non si apre.

### 1.3 🟨 Aggiungere dati dalla web app, senza passarmi dal mezzo

Poter importare nuovi Pokémon in `pokedex` **dall'interfaccia**, e lo stesso per oggetti,
mosse e abilità.

**Metà esiste già**, e va detto prima di progettare il resto:

- `/pokemon/catalogo?db=pokemon|moves|abilities|items` ([pokemon.py:712](blueprints/pokemon.py:712))
  crea, aggiorna, rinomina ed elimina **una voce alla volta**, con archivio e ripristino:
  `DB_CATALOGO` copre tutti e quattro i database chiesti
- `/pokemon/regulation/<id>/contenuto` ([pokemon.py:604](blueprints/pokemon.py:604)) sceglie
  **quali nomi** entrano in una regulation, per **ogni** regulation convertita al filtro

E su `pokedex` i quattro filtri sono `null`, cioè «tutto il catalogo»: un Pokémon aggiunto
**compare da solo**. In `ma` (279/460/58) e `mb` (308/460/58) gli elenchi sono espliciti,
quindi lì va spuntato a mano.

**✅ Il primo ostacolo è stato tolto il 21/08/2026, e non era quello che c'era scritto qui.**
Misurato: una voce aggiunta dall'editor **compariva nel roster** e `/api/pokemon/<nome>`
rispondeva **404** — nell'elenco c'era, aprendola non esisteva. E cambiando una base stat il
file diceva 999 mentre l'API continuava a rispondere 115, **senza nessun errore**, fino al
riavvio dell'app. Causa: `POKEMON_CATALOG` e `_INDICE` in `blueprints/api_pokemon.py` erano
caricati **una volta sola all'avvio**. Ora seguono l'mtime del file, come `_MOVESET` e
`_TRADUZIONI`. Numeri e prove in `STORICO.md`, rete in `scripts/prova_catalogo_vivo.py`.

**Cosa manca davvero, in ordine di rischio:**

1. ✅ **Il moveset — chiuso il 21/08/2026.** Una specie importata porta l'elenco `main`
   e, quando il dump ce l'ha, anche `champions`: sono le regole di Champions chieste da
   Davide. Dove Champions non conosce la specie l'elenco **non si inventa** e resta
   l'avviso giallo. ⚠️ E la frase che stava qui — «la tendina esce vuota senza dire
   perché» — era **sbagliata**. Verificato il 21/08: `mosse_legali()` torna `None`, e sia il
   team builder sia il calcolatore mostrano **tutte** le mosse della regulation con l'avviso
   giallo «Nessun elenco mosse per X: sono mostrate tutte». Quindi la seconda metà del
   requisito — *dichiarare a schermo* — è **già soddisfatta**, ed è la stessa strada delle
   forme inventate. Resta la prima: **dare le mosse** a una specie nuova quando la fonte
   esiste. `data/catalog/pokemon_moves.json` non è tra i `DB_CATALOGO`
   ([pokemon.py:71](blueprints/pokemon.py:71)) e lo scrive solo
   `scripts/importa_mosse_specie.py`, che legge il dump CSV di PokéAPI
2. ✅ **L'import — chiuso il 21/08/2026.** Forma scelta da Davide: **si scrive un nome e i
   dati li pesca il programma**. `pokeapi.py` legge il dump CSV, `/pesca` mostra cosa
   entrerebbe senza scrivere niente e `/importa` scrive dopo l'anteprima, con
   `salva_catalogo()` sotto. Pannello in `catalog_editor.html`, solo sotto la linguetta
   Pokémon. ⚠️ **Oggi non c'è niente di davvero nuovo da importare** — il dump non ha
   specie di default che al catalogo manchino: è una porta per il futuro, non un
   riempimento
3. ✅ **Le regulation non-`pokedex` — chiuso il 21/08/2026**: una spunta «aggiungi anche
   a…» al salvataggio, scelta di Davide. `pokedex` non compare fra le spunte, ed è voluto:
   i suoi filtri sono `null` e la voce ci finisce da sola
4. ✅ **Validazione — chiusa il 21/08/2026**, e con **due esiti diversi** invece di uno:
   un campo del **tipo sbagliato** viene rifiutato con 400 (`base_stats.hp = "molti"` non
   darebbe un errore a valle, darebbe **un numero sbagliato** nel calcolatore), un campo
   **mancante** si salva e si **dichiara** a schermo — serve poter tenere una bozza, e le
   forme inventate sono nate così. I campi attesi sono contati sul catalogo, non desiderati:
   sono quelli che oggi hanno **tutte** le voci. ⚠️ `bp` sulle mosse è escluso di proposito
   (760 su 919: le mosse di stato non hanno potenza)
5. **Chi può farlo**: ✅ risposto dal 17/08/2026 — è scrittura su dati condivisi, quindi
   **solo gli amministratori**, e una route nuova lo è già senza fare niente (§1.2). Resta
   da incrociare con 1.1 solo se un giorno anche i dati condivisi avranno un proprietario

**I punti 1-4 sono chiusi il 21/08/2026**; resta aperta solo la voce collegata qui
sotto — creare i JSON di una regulation nuova dall'interfaccia. Numeri e prove: numeri
e prove in `STORICO.md`, rete in `scripts/prova_import_specie.py` (23 su 23).

> ⚠️ **Le tre regole che l'import ha lasciato**, da leggere prima di toccarlo: una voce si
> riconosce dallo **slug** e non dalla chiave (delle specie di default che mancano al
> catalogo ce ne sono 4, e ci sono già tutte sotto un'altra chiave); **le forme non
> passano di lì** — sono annidate in `forms`, e importarle al primo livello farebbe un
> doppione; e reimportando una specie le sue `forms` vanno **ricopiate**, perché il dump
> non le ha e nessun import può ricostruirle.

**Voce collegata** (dal docx): ✅ **chiusa il 10/09/2026** — *creare i JSON di una
regulation nuova dalla web app*. Il pulsante «Nuova Regulation» c'era già; quello che
mancava erano quattro cose senza le quali la regulation che nasceva da lì non era usabile,
e tre su quattro **non davano nessun errore**: la sorgente delle mosse non si sceglieva
(una copia di MA leggeva `main` e su Incineroar dava 80 mosse invece di 77), la pagina
Regulations mostrava 208/461 su MA e 0 su tutto il resto, la `mega_map` si poteva riempire
solo da riga di comando, e una regulation vuota rispondeva 404 facendo ricadere lo Speed
Tier sulla lista statica. Numeri e prove in `STORICO.md`, rete in
`scripts/prova_regulation_nuova.py` (32 su 32).

> ⚠️ **Le due regole che restano**: la sorgente delle mosse (`moveset` in
> `regulations.json`) **non ha un valore obbligatorio** — se manca vale `main`, ed è
> il motivo per cui ora la creazione la scrive sempre esplicita e il salvataggio rifiuta
> un nome che non esiste. E il pulsante della `mega_map` **completa, non ricalcola**: i
> collegamenti scritti a mano restano, e le Mega la cui base è fuori dal roster non si
> collegano da sole, perché aggiungere una specie è una scelta di contenuto.

**⬜ Cosa resta di questa voce, ed è dato, non codice**: una regulation nuova che **non**
sia basata su Champions o sui giochi principali non ha una terza sorgente di mosse da
scegliere, perché nel dump non c'è (vedi §2.3). Gli `overrides` del filtro — i campi
sovrascritti voce per voce — si scrivono a mano nel JSON **per decisione del 14/09/2026**:
in tutte e tre le regulation valgono `{}`, e un editor si fa quando serviranno.

### 1.4 🟨 Esportare tutto il DB, utenti e personalizzazioni comprese

> Precisazione di Davide: «con esportazione db intendo anche esportare tutto il resto».
> **Quella parte c'è già.** Contato sul DB vero: 33 giochi, 1 team con 1 membro, 1 build PC
> con 5 componenti, 53 argomenti Python, 2 utenti, tutto in `data/backup/hub_export.json`.

`scripts/esporta_dati.py` copre **11 tabelle** su 13 (erano 9 su 11 finché il 21/09/2026 non sono entrate `fanta_leagues` e `fanta_roster`; il listone `fanta_players` resta fuori di proposito, si rifà con `importa_listone.py`) (erano scritte 8 finché
`python_progress` non è entrata nell'elenco il 19/08/2026) e degli utenti esporta tutte
le colonne tranne `password` — quindi **i permessi per sezione ci sono già**, stanno in
`users.sections`, che è una colonna e non una tabella a parte. Con `--completo` le
tabelle sono **10**: si aggiunge `regulations`, e resta fuori solo `game_releases`.

**✅ La falla 2 è chiusa il 21/08/2026: `scripts/importa_dati.py` esiste.** Il ritorno
c'è, è rieseguibile, ha `--dry-run` e **non sovrascrive niente senza averlo detto
prima**. 19 prove su 19 in `scripts/prova_importa_dati.py`, ognuna su un DB suo creato
da `init_db()` in una cartella temporanea. Numeri e prove in `STORICO.md`.

> ⚠️ **Le due regole che restano, e vanno lette prima di usarlo**: le **password non
> rientrano** (l'export non le contiene di proposito), quindi un utente ripristinato
> nasce con una password casuale che nessuno conosce e va reimpostata da `/utenti` —
> lo script lo dice a schermo, ed è il verso giusto. E l'unità del ripristino è **la
> riga con il suo `id`**: non c'è nessuna fusione per titolo o per nome, perché
> `team_members.team_id`, `pc_components.build_id` e `python_progress.topic_id`
> puntano a quegli `id`.

**Delle due falle ne resta una:**

1. ✅ **`regulations` è nel backup dal 18/09/2026.** Non nell'export committabile — lì
   continua a non esserci — ma in `--completo` sì, e `importa_dati.py` sa rimetterla.
   Resta una **tabella morta** (la scrive `init_db()`, non la legge nessuno), e proprio
   per questo è nell'elenco anche dell'import: così con l'export normale compare fra le
   «tabelle non presenti nell'export» invece di non comparire affatto. ⚠️ La sua
   `created_at` la scrive `init_db()` **al momento**, quindi due DB creati a secondi di
   distanza hanno la stessa riga con una data diversa: è in `MAI_SOVRASCRITTE`, altrimenti
   ogni ripristino su un DB appena inizializzato si fermerebbe su un conflitto — su una
   tabella morta, per un timestamp — e l'unica uscita sarebbe `--sovrascrivi`
2. ⚠️ **Due personalizzazioni non sono nel DB**, quindi nessun export potrà mai prenderle:
   il **tema** è in `localStorage` e la **lingua** nel cookie `hub_lang`, entrambi per
   browser. Vanno su colonne di `users` se devono seguire l'utente — cioè esattamente
   quando l'app sarà online e la userai dal telefono e dal PC

**✅ I due export esistono, dal 18/09/2026.** `esporta_dati.py` è rimasto com'era e
scrive il file committabile senza password; `--completo --uscita <percorso>` scrive il
backup vero, con gli hash e `regulations`. Non ha un percorso di default **di proposito**:
pretende `--uscita` e si **rifiuta** di scrivere se, risalendo l'albero dalla destinazione,
trova un `.git` — la rete che tiene in piedi la distinzione, perché un default dentro al
repo verrebbe committato la prima volta che qualcuno fa `git add -A` senza guardare.
In `.gitignore` c'è una seconda rete (`*_completo.json`) per il file copiato a mano.
Il ritorno è `importa_dati.py --file <quel percorso>`, che era già pronto: le password
entrano **solo** per gli utenti nuovi, e quelle già nel DB non si toccano mai. Lo script
dice **quale dei due export** ha letto, con due messaggi diversi — «rientrati senza
password» dopo un backup completo sarebbe falso. Fuori anche dal completo resta
`game_releases`, la cache IGDB da 6007 righe che si rifà col pulsante.
`scripts/prova_esporta_completo.py`: **21 prove su 21**.


Da incrociare con 1.5: online questo export deve girare **da solo sul server**.

### 1.5 🟨 Mettere l'app online

Usare la web app dal telefono e da altri PC, **in contemporanea**.

> **I due vincoli, posti da Davide il 12/08/2026:**
> 1. **I dati degli utenti restano salvati, sempre.** Una soluzione che al riavvio riparte
>    pulita è esclusa a prescindere
> 2. **Gratis.**
>
> Insieme **tagliano fuori Railway**, e con lui Render e Fly nella forma gratuita: il disco
> persistente lì è la parte che si paga.
>
> ⚠️ Il vincolo 1 va **verificato, non creduto**: qualunque strada si scelga, il collaudo
> obbligatorio è **salvare qualcosa, riavviare il servizio, ricontrollare che ci sia
> ancora**. Il filesystem effimero non dà nessun errore: la pagina dice «Salvato» lo stesso.

**Il problema non è quale hosting, è che questa app tiene lo stato in file su disco**:
**20 punti** in `blueprints/` ed `extensions.py` aprono un file in scrittura mentre l'app
gira, più `hub.db`. Quanto deve viaggiare, misurato: `data/` pesa 92 MB ma **84 sono
`data/cache/`**, rigenerabile e già ignorata da git — restano **7,3 MB versionati** più
`hub.db` (60 KB) e `data/archive/` (3 MB). È poco.

| | Strada | Esito |
|---|---|---|
| 1 | **PythonAnywhere, piano gratuito** | ✅ **la candidata**: filesystem **persistente**, nessun letargo. Limiti: una sola web app, quota CPU giornaliera, **rinnovo a mano ogni tre mesi**, whitelist in uscita (irrilevante: gli import si lanciano da qui) |
| 2 | Railway / Render / Fly con un volume | ❌ ~5 $/mese. **Esclusa dal vincolo «gratis»**, resta scritta solo per sapere cosa si comprerebbe |
| 3 | **PC di casa con un tunnel Cloudflare** | 🟨 la riserva. Gratis, e i dati non si spostano di qui. Davanti ci va Cloudflare Access. Il prezzo: **il PC deve restare acceso** |

✅ **Le quattro cose da fare prima di esporre qualunque cosa sono chiuse il 21/08/2026.**
Erano trovate nel codice, non opinabili, e adesso ognuna ha la sua contromisura — 13 prove
su 13, numeri in `STORICO.md`:

- ✅ **il debugger non si accende più da sé.** `app.py` finiva con `debug=True` su
  `0.0.0.0`, e il debugger di Werkzeug offre una console Python dentro la pagina d'errore:
  chiunque arrivasse a quella porta eseguiva codice sulla macchina. Ora serve `HUB_DEBUG=1`,
  e l'app lo dice a schermo quando parte. L'indirizzo resta `0.0.0.0` **di proposito** — è
  così che l'hub si apre dal telefono sulla rete di casa, e il pericolo era il debugger, non
  l'indirizzo; si stringe con `HUB_HOST=127.0.0.1`
- ✅ **`SECRET_KEY` non ha più un default costante.** Era `"dev-secret-change-me"`, scritta
  nel codice e quindi su GitHub: chi la legge **si firma da solo un cookie da admin**. Ora
  `chiave_di_sessione()` prende la variabile d'ambiente `SECRET_KEY`, e in mancanza genera
  32 byte casuali in `data/secret_key.txt`, che è in `.gitignore`. Generarla a ogni avvio
  sarebbe stato peggio, non meglio: far cadere le sessioni a ogni riavvio è il fastidio che
  invita a rimettere una costante
- ✅ **la pagina di login non stampa più `admin / admin123`**, e al suo posto c'è un avviso
  in dashboard che vede **solo un amministratore** e **solo finché quella password funziona
  davvero**. Il seme di `init_db()` resta — un DB nuovo ha bisogno di un modo per entrarci —
  ma ora chi ce l'ha ancora lo sa, e l'avviso sparisce da sé quando la cambia
- ✅ **`requirements.txt` dice la verità**: `flask`, `requests` e `werkzeug`, contati sui
  sorgenti, più il server WSGI a seconda del sistema operativo e `esprima` per lo sweep.
  Prima era una riga sola, e una guida che dicesse `pip install -r requirements.txt`
  **mentiva**
- ✅ **`wsgi.py`** è il punto d'ingresso per un server vero (`wsgi:application`, il nome che
  waitress, gunicorn e PythonAnywhere si aspettano). Provato servito da un server esterno.
  ⚠️ **Un worker solo** finché la trappola sulle scritture concorrenti resta aperta

⬜ **Quello che resta di §1.5, e va deciso da Davide**: quale strada (tabella qui sopra), e
poi il collaudo obbligatorio del vincolo 1 — salvare, riavviare, ricontrollare. Più i **20
punti che scrivono file su disco** mentre l'app gira, che sono il vero motivo per cui questa
app non si sposta da sola: quelli non sono stati toccati.

**Sulla contemporaneità**: SQLite regge un uso come questo senza problemi. I **file JSON
scritti a mano no** — vedi la trappola sulle scritture concorrenti. Le cache in memoria
sono sull'mtime — ⚠️ **lo sono da poco**: quella del catalogo in `api_pokemon.py` è stata sistemata il 21/08/2026, e fino a quel giorno questa riga
diceva il falso.

**E una rete sotto**: «persistente» non vuol dire «al sicuro». Un piano gratuito può
chiudere o essere sospeso, e oggi `esporta_dati.py` lo lancio io a mano da qui.

### 1.6 ⬜ Due guide: com'è fatto, e come si riparte da un PC nuovo

**Lo stato di fatto: i documenti non sono zero, sono cinque**, e in parte si contraddicono.

| File | Righe | Cos'è, davvero |
|---|---|---|
| `DOCUMENTAZIONE_PersonalHub.md` | 303 | La più vicina alla guida n. 1. **Ferma al 07/08/2026**, «v16.2» |
| `PROJECT_CONTEXT.md` | 578 | Dettagli tecnici, convenzioni, log delle sessioni. Aggiornato al 13/08/2026 |
| `STORICO.md` | 431 | Una riga per lavoro chiuso, dal 13/08/2026. Non è una guida: è la memoria |
| `README.md` | 133 | Stack e struttura. Dice **«v11.1a»** |
| `README-GitHub.md` | 104 | La vetrina coi badge |
| `howtouse.txt` | 22 | Appunti a mano. È il germe della guida n. 2 |

> ⚠️ **Quanto è vecchio `DOCUMENTAZIONE_PersonalHub.md`, misurato il 18/09/2026** e non
> dedotto dalla data in copertina. Non è «un po' indietro»: **dice cose false**, e chi
> lo legge per capire com'è fatta l'app parte male.
>
> - alla riga 196 elenca quattro route come «documentate ma mai implementate»:
>   `/api/team/<id>`, `/api/stat_champions`, `/api/regulations`, `/api/regulations/save`.
>   **Tre su quattro esistono** (`/api/team/<int:tid>`, `/pokemon/api/regulations`,
>   `/pokemon/api/regulations/save`, aggiunte l'11/08 e il 19/08). Solo
>   `/api/stat_champions` manca davvero. Contate sulla `url_map`: **79 route** in tutto
> - alla riga 290 dà come voce più grossa del backlog il «**DB Pokedex completo**», che è
>   stato fatto: il catalogo ha 1025 specie e 1342 voci col roster, e `pokedex` è una
>   regulation vera dall'11/08/2026
> - la riga 23 descrive i dati come «roster/mosse/oggetti locali JSON» **per regulation**,
>   che è il modello di prima della migrazione al catalogo dell'11/08: oggi i dati stanno
>   in `data/catalog/` e le regulation contengono **solo elenchi di nomi**
>
> Quando si scriverà la guida n. 1 il punto di partenza è questo file, ma **va riscritto
> leggendo il codice**, non aggiornato a toppe: una riga vecchia qui costa più di una
> riga mancante, perché sembra vera.

⚠️ **Due numeri di versione diversi** sullo stesso progetto dicono che il problema non è
scrivere, è **decidere chi dice cosa** e buttare i doppioni. La guida n. 1 nasce dal fondere
`DOCUMENTAZIONE_PersonalHub.md` con tutto ciò che è successo dopo il 07/08 — catalogo
unico, regulation come filtro, Mega alle base, moveset per specie, utenti e permessi,
switch lingua — che **non è documentato in nessuno dei cinque**.

⚠️ `howtouse.txt` **è già sbagliato**: indica `C:\Progetti_Python\personal-hub`, che non è
questa cartella, e scrive la password in chiaro. Le sue ultime due righe però sono la
stessa richiesta di oggi scritta mesi fa: «accesso al di fuori del pc», «accesso senza
avere il pc acceso».

**⚠️ Cosa la guida n. 2 troverà rotto, e va sistemato prima di scriverla:**

- ✅ **`requirements.txt`** diceva una riga sola: corretto il 21/08/2026, ora `pip install
  -r requirements.txt` fa davvero quello che dice
- ✅ **il ripristino dei dati esiste** dal 21/08/2026: `python scripts/importa_dati.py`
  rimette dentro `hub_export.json` (§1.4). ⚠️ Con un'eccezione che la guida **deve**
  scrivere: le password non rientrano, quindi su un PC nuovo si entra come `admin` con la
  password del primo avvio e le altre si reimpostano da `/utenti`
- `data/cache/` (84 MB) si rigenera, ma va **detto**, altrimenti il primo import sembra
  bloccato mentre sta scaricando
- ⚠️ **`admin123` resta il seme di `init_db()`**, ed è giusto — un DB nuovo ha bisogno di un
  modo per entrarci. Dal 21/08 non è più stampata nella pagina di login, ma sta ancora in
  `howtouse.txt`: la guida nuova non deve propagarla, e deve dire di cambiarla al primo
  accesso. Se non lo si fa, lo ricorda l'avviso in dashboard

**Come dovrebbero essere fatte**: la n. 1 è **per Davide fra sei mesi**, non per un
estraneo — deve spiegare *perché* le cose stanno come stanno (perché il catalogo è unico,
perché le chiavi non si rinominano, perché la lingua è in un cookie), che è la parte che si
perde per prima. La n. 2 è una sequenza di comandi **eseguibile alla lettera**, provata su
una macchina pulita, e la prova finale è la regola #8.

Da fare **dopo** il collaudo (§5): documentare un'app che sta per cambiare significa
riscrivere la guida due volte.

---

## 2. I lavori a metà

### 2.1 ✅ Switch lingua — chiuso il 13/08/2026 (Pokémon e Gaming)

Il primo blocco (i **nomi dei dati**) è chiuso l'11/08. Questo è l'**interfaccia**.

**Quanto è grande, contato**: **453** stringhe fisse nelle pagine Pokémon + **~110** nel
JavaScript. Nell'intero progetto sono 691.

**Come funziona**: `t('frase')` in Jinja e in JS, `tf('frase con {n}', {n: …})` per quelle
coi numeri. **La chiave del dizionario è la frase italiana stessa**, non un codice tipo
`btn.salva`: il template resta leggibile e una traduzione mancante ricade sull'italiano,
che è sempre giusto. Il dizionario è `data/i18n/en.json`, con cache sull'mtime; il JS lo
riceve in `window.T`. ⚠️ Il prezzo, dichiarato: **cambiare una parola italiana in un
template stacca la traduzione in silenzio** — per questo esiste
`python scripts/controlla_traduzioni.py`, che elenca mancanti, vuote e orfane.

✅ **Chiuso: 15 template**, i 12 della sezione Pokémon più `gaming.html`,
`game_form.html` e `steam_import.html`, e le frasi dei suggerimenti in `gaming.py`.
Dizionario a **489 chiavi su 489 chieste**.

✅ **Il blocco Pokémon: 12 template su 12.** `pokemon.html` (16),
`regulation_content.html` (15), `catalog_editor.html` (23) il 12/08; **`calcolatori.html`
(142) più i 7 moduli `static/js/calcolatori-*.js`, `moves_editor.html` (52), `base.html`,
`roster_editor.html` (26), `items_editor.html` (43), `abilities_editor.html` (47),
`regulations_list.html` (33), `regulation_editor.html` (42) e `team_form.html` il 13/08**.
Il dizionario è a **383 chiavi su 383 chieste**, zero mancanti, zero orfane e zero doppie.

> ⚠️ **Cosa NON si traduce, e il perché è sempre lo stesso**: quello che viene **salvato**
> non cambia con la lingua. I `value` dei tipi (chiavi di `TYPE_CHART`), le categorie
> degli oggetti e delle abilità (chiavi del blocco `effect`), le meccaniche (`mega`,
> `tera`), i datalist di mosse e oggetti (chiavi del catalogo, ed è ciò che finisce nel
> DB) e **`TERA_TYPES` in `team_form.html`**, le cui `<option>` non hanno un attributo
> `value`: lì il testo *è* il valore salvato in `mechanic_value`, e tradurlo cambierebbe
> i dati dei team già salvati.

✅ **`controlla_traduzioni.py` ora trova anche le chiavi doppie.** Non poteva vederle:
usa `json.load()`, che **tiene l'ultima e butta la prima in silenzio** — correggere la
traduzione sbagliata non cambierebbe niente a schermo e non si capirebbe perché. Il
controllo legge il file grezzo. Ne aveva già accumulate **6** (`Aggiungi`, `Archivio`,
`Rimuovi`, `Es. Earthquake`, `Editor Abilità`, `Il nome è obbligatorio`), tutte con la
stessa traduzione da entrambe le parti, quindi nessun danno visibile — ma è la classe di
silenzio per cui quello script esiste.

> ⚠️ **`team_form.html` non era nel censimento delle 453 stringhe** del 12/08: è un buco
> del conteggio, non una scelta. È il team builder, 345 righe, e sta sotto `/pokemon/*`
> come le altre. Va tradotto con le altre.

✅ **La shell è tradotta e il pulsante lingua sta su tutte le pagine**, deciso da Davide
il 13/08/2026. Era la scelta obbligata una volta che si traduce l'interfaccia e non solo
i nomi dei dati: confinare il pulsante sotto `/pokemon/*` avrebbe lasciato chi mette EN e
poi va su Gaming **senza un modo per tornare indietro**. Tradotte sidebar, «Esporta
JSON», «Utenti», «Cambia tema», e `<html lang>` ora segue la lingua attiva.

### ✅ Quali sezioni sono tradotte, e perché non tutte

**Deciso da Davide il 13/08/2026, dopo due ripensamenti: solo Pokémon e Gaming** — sono
le due che contano anche per gli utenti non amministratori. Arduino, Python, PC Builder,
Dashboard, login e gestione utenti **restano in italiano**, e non è un lavoro rimasto
indietro.

⚠️ **Il pulsante e la shell sono la stessa decisione, e si cambiano insieme o per
niente.** Il pulsante compare **solo dove la sezione è tradotta**, e la **sidebar resta
in italiano**: la lingua sta in un cookie e vale per tutto il sito, quindi con la shell
tradotta chi mettesse EN e poi andasse su Arduino si troverebbe una pagina italiana sotto
un'interfaccia inglese **senza un modo per tornare indietro**.

> Per aggiungere una sezione: si traduce, e poi si aggiunge **un prefisso** a
> `sezioni_tradotte` in `base.html` — il pulsante compare da solo. È l'unico punto.

✅ **Il plurale `1 team salvati` è chiuso**, e non è servito insegnare i plurali a `tf()`:
la frase italiana è stata riscritta in una forma che non si flette — `Team salvati: {n}`
→ `Saved teams: {n}` — che è giusta per qualunque numero in **entrambe** le lingue.
Gestire singolare/plurale servirà solo se salterà fuori una frase che non si può
riformulare così.

✅ **`tf()` ora esiste anche in Jinja** (`extensions.py`, registrata nel context processor
di `app.py`), gemella di quella in `base.html`. Prima c'era **solo nel JS**, ed è il vero
motivo per cui il plurale era rotto: nei template le frasi coi numeri si spezzavano in
`{{ n }} {{ t('team salvati') }}`, cioè in due pezzi che nessun dizionario può rimettere
nell'ordine inglese. Sostituzione a mano e non `str.format()`, perché le frasi contengono
graffe che non sono segnaposto (i blocchi `effect` mostrati negli editor).

✅ **Gli editor seguono la lingua** dal 13/08/2026: nome tradotto in grande, chiave sotto.
✅ **Le descrizioni restano in italiano**, per decisione di Davide dello stesso giorno —
vedi la riga nelle trappole in cima. Dettagli di entrambe in `STORICO.md`.

> ⚠️ Conseguenza già visibile: in italiano il calcolatore scrive **`Privazione`, non
> `Knock Off`**, e `Cinturanera` invece di `Black Belt`. È quello che la voce chiedeva, ma
> se per abitudine VGC preferisci l'inglese anche in italiano si cambia in un punto solo
> (`nomeVis`, ora nel `<head>` di `base.html`).

### 2.2 ✅ Le abilità da fondere — chiuso il 10/09/2026, erano già fuse

**Rimisurato prima di toccare, ed è il punto della voce**: i numeri scritti qui erano
quelli di **prima** della fusione dell'11/08, e nessuno li aveva più contati.

| | Quello che c'era scritto | Misurato il 10/09/2026 |
|---|---|---|
| voci totali | 415 | **386** |
| senza traduzione | 108 | **82** |
| di quelle, con un effetto | 34 | **10** |

Le **10** rimaste con un effetto sono esattamente quelle che Davide aveva deciso di
lasciare fuori l'11/08 (`Nervosismo`, `Sforzo`, `Tiratore`, `Manto Neve`, `Tempra`,
`Assorbifuoco`, `Colpo Secco`, `Compressione`, `Vento Misterioso`, `Polifagia`). Delle
altre 72, **7** sono appese a un Pokémon — anche quelle già decise — e **65** sono
inerti e non le possiede nessuno: sono le abilità inventate di Champions e i
placeholder, ed è giusto che non abbiano un nome ufficiale. **Non c'è più niente da
fondere**, e nei quattro database del catalogo i doppioni di nome sono **zero**.

**⚠️ La fusione aveva però lasciato un filo staccato, e l'ha trovato Davide.** Prima
dell'11/08 c'erano tre voci in gioco: la chiave `Mega Sol`, con l'effetto sole
permanente; la chiave **`Megasolar`**, inerte, il cui `nome_en` era `Mega Sol` — ed è
quella che il catalogo Pokémon cita su **Mega Meganium**, perché le abilità le cita
col nome **inglese**; e `Terra Estrema` (`Desolate Land`), ufficiale e inerte, di
Primal Groudon. La fusione ha portato l'effetto su `Terra Estrema` — e per Primal
Groudon **è giusto** — poi il giro sui nomi ha cambiato il `nome_en` di `Megasolar`, e
da lì il nome scritto su Mega Meganium non ha più risolto su niente: nessuna
descrizione, nessuna traduzione, nessun effetto, **nessun errore**. Chiuso il
10/09/2026 con `scripts/ricollega_megasolar.py`, decisioni di Davide: il `nome_en`
torna `Mega Sol` e la voce riprende il blocco della voce cancellata, copiato
dall'archivio. Numeri in `STORICO.md`.

> ⚠️ **La rete che resta**: `python scripts/controlla_abilita.py` risponde alle tre
> domande che non danno errore da sole — ogni nome citato da un Pokémon risolve? due
> chiavi si chiamano uguale? quante voci attive sono irraggiungibili? Oggi dice
> **312 nomi citati, 0 orfani, 0 doppioni, 50 voci attive di cui 10 irraggiungibili**
> — e quelle 10 sono le abilità di Champions decise fuori. Se quel numero cresce, un
> effetto è finito di nuovo dalla parte sbagliata.

**⬜ Cosa resta, ed è piccolo**: il fallback `data/abilities.json` **non** è stato
riallineato, quindi contiene ancora `Megasolar` inerte e col nome vecchio. Non fa
danno finché `data/catalog/abilities.json` è leggibile — è lui che vince — ma è la
stessa «macchina del tempo» che l'11/08 era stata disinnescata. Va con la dismissione
dei file storici (§5.3), o con una riga di riallineamento se dà fastidio prima.

### 2.3 ⬜ Mosse per regulation — le quattro cose che richiedono una fonte

Il meccanismo è chiuso (calcolatore, team builder, Speed Tier). Manca **il dato**, e le
quattro cose richiedono **fonti diverse**:

| Cosa manca | Fonte che servirebbe |
|---|---|
| **La differenza fra M-A e M-B** | Nel dump c'è **un solo** version group `champions`: se le due regulation **bandiscono** mosse diverse, quella differenza non è in nessun dato che abbiamo. ⚠️ Dal 18/09/2026 i due elenchi **non sono più identici** (MA 492, MB 494), ma la differenza viene dal **roster**, non da un divieto: `No Retreat` e `Topsy-Turvy` sono lì perché le impara una specie che sta solo in MB. Per gli **oggetti** il buco resta intero: MB copia i 58 di MA |
| **Le 9 forme che il dump conosce e di cui non ha le mosse** | ⚠️ **La riga che stava qui era sbagliata due volte.** Diceva «16 forme inventate, PokéAPI non le conosce»: misurato il 21/09/2026, gli slug di **14 su 16** sono in `pokemon.csv` — PokéAPI le conosce, non ha le loro **mosse**, perché i loro giochi (`legends-za`, `mega-dimension`) nel dump hanno zero righe. E cinque di quelle 14 sono **Mega vere di Regulation M-C** (Absol Z, Garchomp Z, Lucario Z, Golisopod, Baxcalibur), confermate da Serebii e Game8. Le altre — Darkrai, Heatran, Zeraora, Zygarde Complete, Magearna, i tre Tatsugiri — sono Mega di **Leggende Z-A**, reali ma **non ancora in Champions**, quindi è giusto che non abbiano una lista. ✅ **E le due Mega Meowstic sono rientrate il 21/09/2026**: il dump le ha, con 59 e 56 righe di mosse; mancava lo `slug`, e mancava perché la femmina aveva le base stat della forma **non** Mega (466 invece di 566) e il controllo delle sei stat — giusto — bloccava la scrittura. Corretta su tre fonti da `scripts/correggi_mega_meowstic.py`. Erano in MA e in MB, quindi l'avviso giallo si vedeva: ora **nessuna voce di MA o MB è senza elenco mosse**. ✅ **Le 6 Mega di M-C hanno la loro lista dal 21/09/2026**: Bulbapedia non dà un blocco alle Mega, ma **Pokémon Zone** ha una pagina per **ogni** Mega, e confrontate danno **6 su 6** la lista identica a quella della specie. Sono scritte nella sezione `eredita` (vedi le trappole in cima). ⬜ Restano senza lista le **9 Mega di Leggende Z-A** — Darkrai, Heatran, Zeraora, Zygarde Complete, le due Magearna, i tre Tatsugiri — ed è **giusto**: sono reali ma in Champions non ci sono. Più le 2 Mega Meowstic, che non hanno slug |
| **`Pawmot`** | ✅ **Chiuso il 14/09/2026.** La spiegazione del 12/08 («buco del dump») era sbagliata: Pawmot **è in Champions dalla versione 1.2.0**, che PokéAPI non ha. Ora ha la sua lista, integrata da Bulbapedia (64 mosse). Vedi §5.2 e la trappola delle integrazioni in cima |
| **Le regulation future** | ✅ **Le liste di Regulation M-C ci sono dal 21/09/2026**: le 25 voci che il dump non aveva sono state integrate da Bulbapedia, e il roster è confermato **due volte** — Serebii e Game8 elencano le stesse 26 specie più 6 Mega. Il giorno che si vorrà aggiungere M-C come regulation, il roster e le mosse ci sono. ✅ Anche le **6 Mega** (Salamence, Absol Z, Garchomp Z, Lucario Z, Golisopod, Baxcalibur) hanno la loro lista, presa dalla specie su fonte per-forma di Pokémon Zone. ⬜ Resta fuori una cosa sola: non si sa quali **oggetti** M-C aggiunga. Regulation M-C va dal **9 settembre al 2 dicembre 2026** (Serebii). (Da non confondere con la `mc` tolta il 13/09/2026: quella era una regulation di prova, vuota.) Se invece la prossima non è basata su Champions non ha un version group nel dump, e il suo elenco va dalla schermata contenuti o da uno script dedicato |

> Il metodo resta quello del roster: dove esiste una fonte la si importa con uno script
> rieseguibile che **si ferma su ciò che non risolve**; dove non esiste, il dato si lascia
> mancante e **lo si dichiara**. Non si riempie a stima.

---

## 3. Bachi noti

| | Baco | Stato |
|---|---|---|
| ✅ | **`build_catalog.py` avrebbe distrutto il catalogo** | **Chiuso il 10/09/2026.** Leggeva come base i **file storici** (174 voci contro 1026) e riapplicava alle Mega il `+75 HP / +20` che la deconversione dell'11/08 aveva tolto: rieseguirlo avrebbe riscritto `data/catalog/` con quella base, **in silenzio**. Ora la base è `data/catalog/` quando c'è — e lo script **dice da quale file legge** — `MEGA_BONUS` non esiste più, e `scrivi_json()` **rifiuta** un file più povero di quello sul disco. Provato: dry-run reale 1026→1029 specie, 919→920 mosse, 386→387 abilità, 397→398 oggetti, **0 voci curate modificate**; `scripts/prova_build_catalog.py` 9 su 9 |
| ✅ | **La regex delle traduzioni taglia sull'apostrofo** — **non si riproduce** | Rimisurato il 10/09/2026 **su un file vero**: `t('Nessun team per l\'utente scelto.')` viene estratto **intero**. Il ramo `\\.` dell'alternanza consuma la coppia backslash-apice, e la `replace()` sotto toglie il backslash. La diagnosi del 19/08 è quasi certamente nata da una prova fatta in una shell che si mangia un livello di backslash — la stessa trappola è ricapitata **due volte** mentre si scriveva questa riga. La spiegazione sta ora nel commento sopra la regex, perché il caso non si riapra una terza volta |
| ✅ | **`scripts/` è fuori dal raggio di `controlla_proprietario.py`** | **Chiuso il 10/09/2026**, ed è rimasto fuori: uno script da riga di comando non ha una sessione, quindi `ambito_utente()` lì non vuol dire niente e lavora su tutto il DB per costruzione. Quello che mancava era **dirlo**: ora è scritto nel docstring e il riassunto conta e **nomina** gli script che toccano una tabella di contenuto (oggi 2: `importa_dati.py` e `prova_importa_dati.py`). Se ne compare uno che non ti aspetti, quello va letto |
| ✅ | **L'elenco mosse di MA e MB escludeva 159 mosse che Champions permette** | **Chiuso il 18/09/2026, decisione di Davide** («i cataloghi saranno sempre di Champions, quindi la lista mosse sarà sempre quella in relazione alla regulation»). L'elenco non è più un dato curato: lo **deriva** `scripts/allinea_mosse_regulation.py` dall'unione delle mosse del roster, secondo la sorgente `moveset` della regulation. MA 460 → **492**, MB 460 → **494**, e per la prima volta **non sono più identiche** (`No Retreat` e `Topsy-Turvy` arrivano da specie solo di MB). Mosse nascoste: **da 3239 su 17219 a 0** in MA, da 3583 su 19039 a 0 in MB. Numeri e prova del perché le 460 non fossero un elenco di legalità in `STORICO.md`. ⚠️ **Va rilanciato ogni volta che cambia un roster**: un Pokémon aggiunto porta mosse che restano fuori dalla tendina in silenzio |
| ✅ | **Gli oggetti del calcolatore davano il numero sbagliato** | **Chiuso il 14/09/2026.** La tendina ATK faceva `A × modifier` con qualunque oggetto (Carbonella su una mossa Buio: 85-102 → 102-120; Stolascelta: → 127-150), e la DEF non applicava mai niente. Colpiva MA e MB. Ora ogni effetto ha la sua condizione presa da Bulbapedia, e un oggetto che non si attiva lo dice a schermo. Numeri in `STORICO.md` |
| ✅ | **Le 7 categorie di oggetti senza nessuna voce** | **Chiuso il 14/09/2026, decisioni di Davide.** Le 7 vuote erano i gruppi delle due tendine Item del calcolatore, e `other` erano esattamente gli oggetti senza `effect`: dare una categoria voleva dire dare un effetto. **88 oggetti** assegnati con `scripts/assegna_categorie_oggetti.py`, ogni valore preso da Bulbapedia; `other` passa da 339 a 251, e 12 effetti nuovi sono scritti nel motore. Riguarda solo `pokedex`: MA e MB restano sui loro 58. Gli oggetti delle leggende (Adamasfera, Splendisfera, Grigiosfera, Cuorugiada, maschere di Ogerpon) stanno in `conditional`, confermato da Davide. Numeri in `STORICO.md` |
| ⚠️ | **Un effetto che il motore non conosce non si attiva** | Il calcolatore gestisce **gli effetti elencati nel docstring di `scripts/assegna_categorie_oggetti.py`**, più `pikachu_boost` e `resist_<tipo>`. Un oggetto nuovo con un `effect` e un `modifier` compare nella tendina, ma finché `calcDamage()` non conosce l'effetto il risultato dice «non si attiva». È voluto: fino al 14/09 un oggetto sconosciuto moltiplicava l'Attacco in silenzio. Quindi **ogni effetto nuovo va scritto anche nel motore**, e provato con un caso calcolato a mano. ⚠️ La tendina mostra le voci con `modifier` **non nullo**, e 0 è un valore: il Palloncino ha `modifier: 0` |
| ⚠️ | **`puo_evolversi` ha tre valori** | Lo scrive `scripts/importa_evoluzioni.py` su **1342 voci su 1342**, per forma e non per specie: Corsola di Galar sì, quella di Kanto no, le Mega mai. **Assente vuol dire «non lo sappiamo»**, e l'Evolcondensa lo dice a schermo («evoluzione non nota»), come `moves: null`. ✅ **Dal 21/09/2026 sono 1342 su 1342**: le ultime due, le Mega Meowstic, hanno preso lo slug e con lui l'esito. L'import dal pannello lo calcola da sé (`pokeapi.evoluzioni()`); **una voce aggiunta a mano dall'editor invece nasce senza**, e va rilanciato lo script. Nelle forme **non si eredita** dalla specie in `api_pokemon.py`: ereditarlo darebbe `true` a tutte le Mega |
| ⬜ | **Limiti dichiarati degli oggetti nel calcolatore** | Trovati scrivendoli il 14/09/2026 e lasciati fuori di proposito: il **Guantone** alza la potenza ma non toglie il contatto (Unghie Dure e Soffice lo vedono ancora); il **Plessimetro** resta in `other`, perché serve un campo «usi consecutivi»; i **semi** del terreno hanno solo l'etichetta, e il loro +1 andrebbe collegato alla tendina del terreno; la **Metalpolvere** non sa se Ditto si è trasformato; e le **gemme** si consumano al primo colpo, cosa che un calcolo singolo non vede |

## 4. Voci minori, per sezione

| Sezione | Voce |
|---|---|
| 💾 **Log** | ⬜ Aggiungere una funzione di salvataggio log |
| 🖨️ **Stampa 3D** | ⬜ Sezione nuova, sul modello di Arduino: richiamo a un sito per disegnare e salvataggio dei progetti |
| 🤖 **Arduino** | ⬜ Richiamo a Tinkercad per disegnare il progetto e verificare i connettori |
| 💻 **PC Builder** | ⬜ Wishlist Amazon o altri · ⬜ prezzo componente · ⬜ percentuale di compatibilità fra i pezzi (valutare UserBenchmark) · ⬜ gestire l'uscita di nuovi pezzi nel tempo |
| 🐍 **Python** | ⬜ Spazio per inserire i propri progetti e testarli · ⬜ idee per rendere la sezione più utile |
| ⚽ **Fantacalcio** | ✅ **Fatta, dal 21/09/2026**, e allargata il 22/09: listone **sfogliabile con la scheda di ogni giocatore**, leghe con regole strutturate, rose (una per volta, **incollate in blocco** o **svuotate per reparto**), **probabili formazioni**, **campo per schierare** col **consiglio sotto**, e il **timer** che dice entro quando (vedi §4.2). Restano i ruoli Mantra, che sono nel DB e non li legge nessuno, e quello che il timer dà per buono (§4.4) |

### 4.1 🟨 Gaming — il calendario delle uscite (chiesto il 13/08, costruito il 16/08/2026)

> ⚠️ **Trappola pagata il 16/08/2026**: la cache vera usa `igdb_release_id`
> fra **486664 e 954196**. Uno script di prova che cancellava «il mio intervallo»
> 900000-910000 si è portato via **497 righe vere**. Non è grave — la cache si rifà col
> pulsante — ma la regola vale in generale: **un id scelto a tavolino non è una prova di
> proprietà**, un campo che scrive solo il test sì. E un test che condivide lo stato con
> i dati veri misura anche quelli: la prova gira ora su una **copia** di `hub.db`.

**Chiesto**: nella sezione Gaming una **barra o un calendario con le prossime uscite**,
di **tutte le piattaforme** e non solo Steam, sul modello di quello di Opera GX.

✅ **Le decisioni sono prese e la metà lettura è chiusa e verificata** (dettagli in
`STORICO.md`). **Fonte scelta: IGDB.** Il backlog dava RAWG come «più semplice da
attaccare»: il 16/08/2026 RAWG rispondeva **522 da Cloudflare su API *e* sito**, tre
tentativi, mentre dalla stessa macchina Steam rispondeva normalmente e IGDB dava un 401
regolare con l'istruzione sugli header. Scrivere il client di un servizio irraggiungibile
avrebbe significato non poterlo provare. Opera GX / GX Corner **non è stata cercata**: la
domanda «esiste una API» resta aperta e ormai è accademica, la fonte è decisa.

Le due decisioni che il backlog lasciava in sospeso: le **piattaforme sono un filtro
nell'URL** (`?platform=`) e non una preferenza salvata — le preferenze per utente nel DB
non esistono, vedi §1.4 falla 3, e i filtri di Gaming viaggiano già tutti nella
querystring; la **cache la aggiorni tu da un pulsante**, come ogni altro import qui, e
l'aggiornamento automatico resta agganciato a §1.5, che è l'unico contesto in cui ha senso.

✅ **L'import è stato eseguito il 16/08 e funziona**: **6827 uscite** in cache, 4280
giochi distinti su 29 piattaforme. Le domande che erano aperte hanno tutte una risposta
misurata: **zero righe su 6827 con precisione «ignota»**, cioè il campo della precisione
è stato letto per tutte (la doppia lettura `category` / `date_format` regge); 0 righe
senza piattaforma e 0 senza URL IGDB; 196 su 6827 senza copertina (2,9%, sono giochi che
su IGDB una copertina non ce l'hanno).

✅ **Le uscite multipiattaforma si fondono** (chiesto da Davide il 16/08): un gioco che
esce lo stesso giorno su più piattaforme è **una riga sola**. Nei soli prossimi 90 giorni
la fusione unisce **454 gruppi** — *Vampire Survivors: Legacy of the Bloodmoon* passa da
9 righe a 1. Si fonde in **lettura** e **dopo il filtro**, mai in scrittura.

✅ **4.1a è chiuso il 17/08/2026** — in cache entrano solo PC, PS5, Xbox Series, Switch e
Switch 2 e i VR; le console vecchie (PS4, Xbox One, 360, Vita, Wii) le ha escluse Davide
lo stesso giorno. −1373 righe su 7327, e solo 45 giochi persi. Numeri e prove in
`STORICO.md`; la trappola dell'elenco che fallisce chiuso è in cima a questo file.

✅ **4.1b è chiuso il 17/08/2026** — la ricerca per titolo è nella riga dei filtri, viaggia
come `?q=` e filtra **in SQL prima del tetto**, quindi trova anche ciò che il tetto taglia.
In più dice quante uscite col titolo cercato cadono **fuori dal periodo scelto**, che era
la trappola rimasta: il periodo è un filtro esplicito, ma con una ricerca attiva un
«nessun risultato» sarebbe stato letto come «non c'è». Numeri e prove in `STORICO.md`.

✅ **4.1c è chiuso il 17/08/2026** — filtro «quanto è atteso» su `hypes`, con la finestra
di default che passa da 11 giorni a **tre mesi** di calendario. Numeri e prove in
`STORICO.md`.

**Il tetto delle 300 righe resta, ed è giusto che resti**: senza, la pagina pesava
**3,3 MB con 4224 immagini**. Quello che è cambiato è **quanto calendario ci sta dentro**:
con «quelle un po' attese» le 300 righe coprono **tre mesi** invece di undici giorni, e
sulla finestra di default le voci che passano i filtri sono **317** — il tetto sfiora
appena. Le tre leve sono ora l'attesa, la piattaforma e la ricerca; il periodo da solo
non basta mai, e l'avviso a schermo lo dice.

**⬜ Cosa resta, ed è piccolo:**

- ⬜ **La cache va aggiornata una volta** perché il dato dell'attesa entri: fino ad allora
  il filtro è spento e la pagina lo dice. È un'azione di Davide, non un lavoro
- ⬜ **La striscia in cima a `/gaming`** mostra ancora le **6 uscite più vicine**, senza
  guardare l'attesa: è un assaggio e va bene così, ma se dà fastidio vedere lì un gioco
  che non conosce nessuno si applica la stessa soglia (`filtra_per_attesa` è già scritta)
- ⬜ **Le soglie sono due numeri fissi** (2 e 10) scelti sui conti del 17/08. Se in cache
  entrasse molto altro andrebbero rimisurate, non ritoccate a occhio


### 4.2 ✅ Fantacalcio — tutto quello che era stato chiesto, dal 21/09/2026

Chiesta il 10/09/2026, **definita e iniziata il 21/09/2026**. Le quattro domande che
stavano qui hanno una risposta, data da Davide:

- **cosa deve fare**: inserire la propria formazione avendo tutti i giocatori di
  Serie A, vedere le probabili formazioni dei propri giocatori, avere un consiglio, e
  ricordare le regole — **due leghe, quindi due regolamenti e due formazioni**
- **i dati**: il listone di Fantagazzetta, cioè `fantacalcio.it`
- **quanto è personale**: leghe e rose sono per utente, il listone è condiviso
- **le regole**: **strutturate**, non un testo — così l'app può applicarle
- **il sistema**: tutte e due le leghe **Classic**

**✅ Le tre fonti, misurate il 21/09/2026 e tutte su un sito solo.** Le pagine di
`fantacalcio.it` sono **renderizzate dal server**, quindi si leggono con `requests` +
`HTMLParser` come la wiki, **senza login**. ⚠️ Il download Excel del listone invece
**pretende un account**: `/api/v1/Excel/prices/21/1` risponde **401**, e per questo si
leggono le pagine — evita anche di mettere credenziali nel progetto.

| Pagina | Cosa dà | Misurato |
|---|---|---|
| `/quotazioni-fantacalcio` | ruolo Classic e Mantra, squadra, QI, QA, FVM | 597 giocatori |
| `/statistiche-serie-a` | media voto, fantamedia, gol, assist, cartellini, rigori | 597, 11 colonne |
| `/probabili-formazioni-serie-a` | giornata, modulo di ogni squadra, undici, panchina e **percentuale di titolarità** | 10 partite, 20 moduli, 482 convocati (220 titolari) |

⚠️ **La riga delle probabili era misurata male**, e l'ha corretta il lavoro del
21/09/2026 che l'ha letta davvero: «761 voci, 20 ballottaggi» contava tutti gli
`a.player-name` della pagina — i 220 del campo disegnato, i 482 delle schede e una
sessantina altrove — e i «ballottaggi» non esistono come marcatore. Quello che il
sito dichiara è una **percentuale** per ogni convocato (da 1 a 90), ed è quella che
viene salvata: un ballottaggio, se serve, si deduce da lì **dichiarando la soglia**,
non si legge da un campo che non c'è.

⚠️ **Si incrociano per `id`, non per nome.** Ogni giocatore porta il suo id numerico
nell'URL (`/serie-a/squadre/inter/martinez-l/2764`), **uguale in tutte e tre** le
pagine. Il nome è abbreviato (`Martinez L.`) e due squadre possono avere due
`Martinez`: legare per nome qui è la stessa classe di baco già pagata sul catalogo
Pokémon.

**✅ Cosa c'è, dal 21/09/2026** — `fantacalcio_it.py` (legge e basta),
`scripts/importa_listone.py` e `scripts/importa_probabili.py` (gli unici che
scrivono), `blueprints/fantacalcio.py`, cinque template, e
`scripts/prova_fantacalcio.py` (**245 prove su 245** al 22/09/2026, erano 156 il
21/09):

- il **listone in `hub.db`**: 597 giocatori, 20 squadre, con ruolo, quotazioni e
  statistiche
- le **probabili della giornata**: 10 partite, i moduli veri delle venti squadre di
  Serie A e 482 convocati con la loro **percentuale di titolarità**, in due tabelle
  con chiave `(giornata, …)`. La pagina `/fantacalcio/probabili` le mostra partita
  per partita segnando i tuoi; quella della lega dice, per ogni giocatore in rosa,
  quale dei **quattro** stati è il suo — titolare, panchina, **non convocato** (la
  sua squadra gioca, lui non c'è) o **non gioca** (la sua squadra non è in questa
  giornata). ⚠️ Le ultime due si confondono facilmente e non sono la stessa cosa:
  scambiarle vorrebbe dire schierare qualcuno che non scende in campo
- le **due leghe** con le regole in colonne: moduli ammessi, panchinari, modificatore
  di difesa e dodici fra bonus e malus
- la **rosa** per lega, con il prezzo pagato, e il conto di quali moduli sono
  copribili
- ⚠️ **l'aggiornamento del mercato**, che è la parte che Davide ha chiesto di mettere
  subito: `importa_listone.py --scarica` è rieseguibile e chi esce dalla Serie A viene
  **spento, non cancellato** — cancellarlo porterebbe via la riga di rosa che lo
  nomina. Lo script dice quanti degli spenti sono in una tua rosa, che è l'unica cosa
  che ti riguarda davvero, e la pagina della lega li mostra col cartellino «fuori
  listone» invece di nasconderli

**✅ L'aggiornamento senza riga di comando, dal 21/09/2026.** Chiesto da Davide: un
pulsante, o meglio l'aggiornamento entrando nella sezione. Ci sono tutti e due —
**«Aggiorna ora»** (un `POST`, perché scarica e riscrive: un `GET` si rifarebbe a
ogni F5) e l'**automatico**, che scatta quando la copia in cache ha passato la sua
soglia: **una settimana** per il listone, **tre ore** per le probabili
(`fanta_import.VECCHIA_*`). Non a ogni visita, perché vorrebbe dire aspettare
fantacalcio.it ogni volta che si apre la pagina. ⚠️ Se la fonte non risponde la
sezione **si apre lo stesso**, col dato di prima e un avviso: una pagina che sa già
cosa mostrare non può diventare un errore 500 perché la rete è lenta.

⚠️ La logica sta in **`fanta_import.py`**, non negli script: la chiamano tutti e due
e gli script sono ora solo il rivestimento che stampa il rapporto. Scriverla due
volte era la strada facile, ed è lo stesso errore che ha tenuto in vita per un mese
il difetto di `main` nel moveset.

**✅ Le regole della lega, rifatte il 21/09/2026** su tre richieste di Davide:

- **il gol è una casella sola.** Erano quattro (una per ruolo) e il regolamento dà
  **+3 a chiunque segni**, portiere compreso: quattro caselle da riempire con lo
  stesso numero erano quattro occasioni di sbagliarne una. La migrazione travasa il
  valore e toglie le colonne vecchie, ma **solo se erano uguali fra loro** — dove non
  lo fossero resterebbero, invece di perdere in silenzio una differenza voluta
- **il modificatore di difesa ha la sua tabella**, e dal 22/09/2026 le sue fasce si
  **aggiungono e si tolgono** (da 1 a 8) e arrivano ai **quarti di voto**: il
  regolamento fissa *come* si fa la media, non in quanti scalini si traduce. ⚠️ Il
  campo aveva `step="0.1"`, quindi `6.25` il **browser lo rifiutava senza dire
  perché** mentre il server l'avrebbe salvato: ora è `0.01`, e ci sono due pulsanti
  che riempiono la tabella — quella storica a tre fasce e quella a **sei fasce a
  quarti** (6,00 → +1, 6,01-6,25 → +2, … 7,01+ → +6). ⚠️ Quei numeri **non** stanno
  nel regolamento pubblico: §10.1 dice solo che la piattaforma «propone la versione
  più diffusa» e la tabella vera sta dietro il login, quindi la fonte dichiarata è
  `fantacalcio-online.com`, la stessa delle fasce di titolarità. ⚠️ E le soglie
  restano «da X in su»: la fascia che la fonte scrive `6,01-6,25` qui si scrive
  `6.01`, e le due letture danno **lo stesso punto** perché fra 6,25 e 6,26 non
  esiste nessuna media — i voti hanno due decimali. La scheda della lega le mostra
  comunque come intervalli («da 6,26 a 6,50 → +3»), che è come si leggono. ⚠️ **L'ultima riga non si toglie** e nessuna riga
  leggibile vuol dire «tieni la tabella di prima», non «tabella vuota» — per non
  avere nessun bonus si spegne il modificatore. La **struttura** viene dalla guida
  ufficiale di Leghe Fantacalcio (letta il 21/09/2026): media aritmetica del
  **portiere e dei migliori 3 difensori** — o dei **migliori 4 difensori** se il
  portiere si esclude — **esclusi bonus e malus**, e serve che almeno **4 difensori**
  portino voto. I **valori** invece la piattaforma li lascia cambiare, e quelli di
  partenza sono i tre storici di FantaGazzetta: **+6** da 7, **+3** da 6.5, **+1** da
  6, niente sotto il 6. La scheda della lega mostra la tabella, come si fa la media, e
  qualche esempio
- **ogni regola è una tendina** coi valori che si usano davvero, e il valore del
  regolamento è segnato «(ufficiale)» — più «Altro…», che scopre la casella libera:
  la scelta resta, ma non è più una casella vuota davanti a chi non ricorda se
  l'ammonizione toglie mezzo punto o uno

⚠️ **I valori dal regolamento sono SETTE, non tre** — corretto il 21/09/2026
rileggendo `/regolamenti/leghe-private`, che li elenca per esteso: gol **+3**
(rigori compresi), assist **+1** (da fermo +0,5), ammonizione **−0,5**, espulsione
**−1**, gol subito **−1**, rigore parato **+3**, rigore sbagliato **−3**. La riga di
prima ne dichiarava tre ed era una **misura incompleta**, non una regola diversa: la
prima lettura si era fermata alla pagina sbagliata. I cartellini si fermano a −1
comunque siano combinati. Restano fuori **porta inviolata e autogol**, che il
regolamento davvero non fissa: quelli sono convenzionali e vanno decisi lega per
lega. È il motivo per cui le regole stanno in colonne, e ora il valore ufficiale
compare **accanto a ogni tendina**, non solo l'etichetta «(ufficiale)».

**✅ La rosa si incolla, dal 21/09/2026.** Messa davanti al consiglio su scelta di
Davide, e il motivo stava nel DB: con tutto il resto in piedi la rosa vera era ferma
a **un giocatore su ~25**, perché si aggiungeva uno per volta con la ricerca — e
formazione, copertura dei moduli e consiglio girano tutti su una rosa che non c'era.
Si incolla la lista, si **guarda l'anteprima** e si scrive solo quello che si spunta.

⚠️ **L'anteprima non è comodità, è la parte sicura**: un nome abbinato male non dà
nessun errore, e sul listone del 21/09/2026 l'ambiguità ha tre forme misurate — **0**
nomi identici fra due giocatori, **24 cognomi** condivisi (`Martinez L.`/`Martinez
Jo.`, otto `De …`), e **5 nomi che sono anche il prefisso di un altro**: `Thuram`
esiste **e** c'è `Thuram K.`, come `Colombo`, `Pessina`, `Rrahmani`, `Terracciano`.
L'ultimo è il caso che si sbaglia in silenzio, perché l'abbinamento esatto **è**
univoco: per questo un nome con omonimi non è mai «sicuro», è «da confermare» con
l'altro in tendina, e una riga «da scegliere» nasce **senza niente selezionato**.
Un nome scritto male **non viene indovinato** — niente distanza di edit.

⚠️ E una cosa da sapere prima di toccare l'abbinamento: le regole che restringono
(squadra, ruolo, iniziale del nome proprio) si applicano **solo se lasciano un
candidato**, e quando non combaciano si **dichiarano** invece di sparire. Una riga
che chiede `Bastoni JUV` e trova il Bastoni dell'Inter non è una riga sicura: o la
sigla è sbagliata, o il giocatore giusto è un altro.

✅ **Chiuso il 22/09/2026**: il prezzo si corregge e si toglie in blocco dal pannello
«Correggi la rosa», con una conferma sola. Numeri in `STORICO.md`.

✅ **Chiuse il 22/09/2026, secondo giro — le quattro «da fare subito» di Davide**
(numeri e trappole in `STORICO.md`):

- il **listone si sfoglia** (`/fantacalcio/listone`), con filtri, ordinamenti e la
  **scheda** di ogni giocatore: tutti i suoi numeri, la probabile della giornata e
  in quali tue rose sta;
- **svuota il reparto** e **svuota la rosa**, con una conferma che dice quanti ne
  toglie — e chi esce dalla rosa esce anche dal campo;
- il **timer «schieri entro»** in Dashboard, nell'elenco, nella lega e sul campo,
  con la sua fonte nuova: `fanta_calendario` e la quarta pagina di fantacalcio.it.
  ⚠️ L'ora **non** era nelle probabili, dove c'è un riquadro pieno di segnaposto;
- il **consiglio sotto il campo**, nella stessa schermata. `fanta_consiglio.html`
  non esiste più: il corpo è `_fanta_consiglio.html`, e `/consiglio` rimanda a
  `…/formazione#consiglio`.

⚠️ Quello che il timer **dà per buono**, e che può smettere di funzionare in
silenzio, sta in **§4.4**. Le altre richieste di quel giorno («per il futuro») sono
in **§4.3**.

✅ **Chiuso il 22/09/2026: le classi che non esistevano.** Erano `form-input` (10
campi), `form-select` (3 punti nel Fantacalcio) e `form-label` (6, tolta perché il
selettore `label` di `base.html` fa già quel lavoro); `items-end` mancava davvero ed è
stata definita. ⬜ **Resta fuori dal Fantacalcio**: `form-select` è ancora usata da
**4 tendine** — il selettore di sezione in `arduino.html`, `gaming.html`,
`pcbuilder.html` e `pokemon.html` — e lì non è definita da nessuna parte. Sono senza
stile come lo erano queste; si fa quando si tocca la grafica di quelle sezioni, non
prima.

**⬜ Due cose chieste da Davide il 22/09/2026, da fare quando il resto della
sezione è finito:**

- ✅ **I riquadri, fatti il 22/09/2026.** Campi e pulsanti **tondi** (pillola),
  spunte col verde della sezione, riquadri con angoli più morbidi, ogni regola in
  una sua pastiglia, righe della rosa che si accendono al passaggio. ⚠️ Tutto sta
  in `static/css/fantacalcio.css` sotto `body.sez-fanta`, e non è pignoleria:
  `.form-control`, `.btn` e le card stanno in `base.html` e le usano **tutte** le
  sezioni — ritoccarle lì avrebbe cambiato Pokémon, Gaming, Arduino e PC Builder
  senza che nessuno l'avesse chiesto. Il gancio è il blocco `body_class`, che
  nasce vuoto per tutte le altre pagine. ⚠️ E i colori vengono dalle variabili del
  tema, con l'accento dichiarato per **tutti e due** i temi: un verde fisso starebbe
  bene sullo scuro e male sul chiaro, e non se ne accorgerebbe nessuno finché
  qualcuno non cambia tema
- ✅ ⚠️ **La modale della lega si tagliava su uno schermo basso — corretto il
  22/09/2026.**
  Segnalato da Davide il 22/09/2026 («in fantacalcio in un monitor piccolo non posso
  scrollare le regole della lega») e **riprodotto**: a 1280×620 la `.modal-box` si
  ferma a `max-height:92dvh` = **570 px** e dentro c'è un `<form>` alto **733 px**,
  quindi gli ultimi ~160 px — le regole della lega **e il pulsante Salva** — sono
  tagliati da `overflow:hidden` e non si raggiungono in nessun modo. ⚠️ La causa non
  è `.modal-body`, che ha già `overflow-y:auto`: è che fra lui e `.modal-box` c'è il
  `<form>`, che **non è un contenitore flex**, quindi il `flex:1` del body non
  agisce e non c'è nessuna altezza limitata su cui scrollare. Corretto dando al form
  lo stesso ruolo di colonna (`display:flex;flex-direction:column;flex:1;min-height:0`):
  ora a 1280×620 il corpo mostra **474 px su 652** e scrolla, coi pulsanti
  Salva/Annulla sempre in vista.
  ⚠️ **Solo il Fantacalcio ha questo schema**: in `arduino.html` e `pcbuilder.html`
  il form sta **dentro** `.modal-body`, e lì lo scroll funziona — quindi la cura non
  va copiata a tappeto, va messa dove il form avvolge header e footer.
  ⬜ E la richiesta più larga che Davide ha allegato: **rivedere lo scorrimento di
  sezioni e sottosezioni** in generale, non solo di questa modale.

- ✅ **I testi a schermo riscritti in forma generica, il 22/09/2026**: **29 testi**
  nelle sei pagine e nell'avviso, che ora dicono **cosa fa** la pagina e **cosa
  farci**. ⚠️ I **commenti** dei template e del codice restano come sono: lì il
  ragionamento serve. ⚠️ E due prove della suite verificavano il *testo esatto* della
  pagina del consiglio: riscritte sulle frasi nuove, e succederà di nuovo a ogni
  ritocco — è il prezzo di provare ciò che l'utente legge davvero.
  La richiesta, per memoria: Perimetro chiarito da
  Davide il 22/09/2026: **i testi visibili**, non i commenti del codice. «È brutto
  far leggere a qualcuno di esterno il nostro ragionamento, voglio qualcosa di
  generico, preciso e che faccia comprendere bene il tutto». Oggi più di un testo
  racconta **perché** una cosa è fatta così — la decisione, la data, il baco che
  c'era prima — invece di dire **cosa fa** e **cosa deve farci l'utente**. I
  commenti nei template e nel codice **restano come sono**: lì il ragionamento
  serve, ed è quello che tiene in piedi il progetto

**⬜ Cosa resta, in ordine di quanto è stato chiesto:**

- ✅ **inserire la formazione** — fatta il 21/09/2026, com'è stata chiesta: **un
  campo da gioco come quello dell'app Fantagazzetta**, dinamico, che cambia
  disposizione al cambio di modulo, dove si schiera scegliendo dal **ruolo del
  posto**. Sta dentro la lega: `/fantacalcio/lega/<id>/formazione`.

  Le due decisioni di Davide, prese quel giorno: **una formazione per lega, che si
  sovrascrive** (niente giornata, niente storico) e **validazione severa** — quello
  che non torna non si salva, come per un modulo scritto male.

  Come si comporta il campo, che è la parte che si sarebbe potuta fare peggio:
  - al **cambio di modulo** i giocatori non si buttano via — ognuno resta se c'è
    ancora un posto del suo ruolo, e chi avanza finisce **in panchina** invece di
    sparire (da 3-4-3 a 3-5-2 il terzo attaccante deve pur andare da qualche parte);
  - la **panchina è ordinata** e si riordina con le frecce: nel fantacalcio
    l'ordine decide chi subentra, quindi è un dato, non una decorazione;
  - accanto a ogni giocatore, in campo e nell'elenco da cui si sceglie, c'è la sua
    **probabile** — titolare, panchina, non convocato, non gioca, con la
    percentuale. È l'informazione che serve **mentre** si schiera, ed è tutto il
    motivo per cui le probabili sono state fatte prima.

  ⚠️ Il **ruolo lo decide la rosa, non il form**: un `ruolo` mandato dal browser
  farebbe tornare i conti dei reparti dicendo che un attaccante è un difensore, e
  la prova lo verifica.

  ✅ **Il controllo quando le probabili cambiano, dal 22/09/2026.** Aprendo la
  sezione, la formazione salvata viene confrontata con le probabili di adesso e
  l'avviso dice **chi** e **perché**: titolari che non scendono in campo, titolari
  sotto la soglia del ballottaggio, chi è schierato ma non è più in rosa, e — come
  contorno — chi in panchina è invece dato titolare. Sta sulla scheda della lega,
  sul campo, e come numero sull'elenco delle leghe, che è la pagina che si apre per
  prima. ⚠️ «Automatico» qui vuol dire **quando apri la pagina**: non c'è niente
  che giri in sottofondo, quindi nessun avviso arriva il venerdì sera da solo —
  per quello servirebbe un processo schedulato, ed è un lavoro a sé.

  ❌ **Copiare una formazione nell'altra lega: non serve** — deciso da Davide il
  22/09/2026. Le due leghe restano indipendenti, com'è adesso.

  ✅ **Chiuso il 22/09/2026, con la decisione di Davide: chi esce dalla rosa esce
  anche dal campo.** `fanta_roster` e `fanta_formazione` sono due tabelle e il
  `DELETE` sulla prima non toccava la seconda — il campo smetteva di disegnarlo,
  quindi a schermo sembrava tutto normale, e i titolari diventavano dieci in
  silenzio (misurata 1 riga orfana dopo un `rosa/rimuovi`). Ora lo fa
  `_scendi_dal_campo()`, per la × di una riga e per il «togli in blocco», e il
  messaggio lo dice («Tolto dalla rosa, ed era schierato»). ⚠️ **Chi esce dal
  listone è un'altra cosa** e resta dov'è: spento, in rosa e in campo, col suo
  cartellino — è la scelta del mercato di gennaio, e c'è una prova apposta perché
  nessuno le confonda.

- ✅ **le probabili formazioni** — fatte il 21/09/2026, vedi lo storico. Ci sono
  `fantacalcio_it.probabili()`, `scripts/importa_probabili.py`, due tabelle per
  giornata e la pagina `/fantacalcio/probabili`; la pagina della lega dice, per ogni
  giocatore in rosa, se è titolare, in panchina, **non convocato** o se la sua
  squadra **non gioca**. ❌ **L'archivio non si pota** — misurato e
  deciso il 22/09/2026. `fanta_probabili` ha chiave `(giornata, player_id)`, quindi
  una giornata nuova **si aggiunge** e la stessa giornata riletta si sovrascrive:
  nessuno cancella mai niente. Il conto: oggi c'è **una** giornata (la 6, 483
  convocati e 20 squadre), a fine stagione saranno 38 giornate, cioè **~18 000
  righe, meno di 2 MB** su un DB che ne pesa 2,7 in tutto — e ogni query filtra per
  giornata, quindi non rallenta niente. ⚠️ E c'è un motivo per **non** potare: le
  probabili archiviate sono metà di ciò che servirebbe per rispondere a «il
  consiglio ci aveva preso?», che è l'altra voce ancora aperta. La fonte pubblica
  solo la giornata corrente, quindi una riga cancellata non torna più
- ✅ **il consiglio — fatto il 21/09/2026**, e la parte lunga è stata **leggere**,
  non scrivere. `/fantacalcio/lega/<id>/consiglio`, più «applica al campo».

  **Cos'è venuto fuori dalla ricerca**, che è la risposta alla domanda di Davide
  («quello che consigliano di più sulla piattaforma o altre fonti affidabili»):

  - ⚠️ **una formula non la pubblica nessuno.** Il *Comparatore* di fantacalcio.it
    («ti diremo quale dei due potrebbe rendere al meglio nel prossimo turno»)
    confronta partite a voto, media voto, fantamedia, gol, assist e gol subiti ma
    **non dichiara come li combina**, ed è premium; la pagina dell'*algoritmo delle
    quotazioni* dice per esteso di non rivelare i coefficienti; il *FantaIndex* è
    «un numero da 0 a 100» ricavato da «sette macroaree». Quindi il peso α che §4.2
    chiedeva di andare a copiare **non esiste da nessuna parte**: la risposta alla
    domanda era che la domanda non ha una fonte
  - ✅ quello che le fonti **dichiarano davvero** è una **gerarchia con delle
    soglie**, e quella è implementabile. L'*Indice di Titolarità* di fantacalcio.it
    è «lo strumento imprescindibile per poter schierare al meglio», su scala 0–100;
    le fasce le scrive `fantacalcio-online.com`: **≥90** «titolare, nessun dubbio»,
    **60–89** «favorito in un ballottaggio», **40–59** «ballottaggio effettivo: è
    qui che si decide una giornata», **<40** «parte dalla panchina». E dice che
    titolarità e merito sono **due domande diverse** — «*se* gioca» e «*se conviene*
    schierarlo» — da rispondere **in quest'ordine**
  - ✅ più una **regola operativa** che qui si può eseguire perché la panchina è una
    lista ordinata: sui ballottaggi, «schierare chi ha la percentuale più alta e
    collocare l'altro **in cima alla panchina**», così la sostituzione automatica lo
    fa subentrare
  - ✅ e un **numero** che la piattaforma dichiara e che serviva: la fantamedia entra
    nel suo algoritmo **dal quinto match in poi**. È da lì che viene la soglia
    dell'avviso «poche partite», che prima era un 3 scelto a occhio

  **Com'è fatto**: una porta e un ordinamento, non una media pesata. La percentuale
  decide **chi può giocare** (sotto il 40% non entra, se il reparto si riempie
  altrimenti), la fantamedia rifatta con le regole della lega decide **chi conviene**
  fra quelli che giocano. I **punti attesi** (`percentuale × fantamedia`) sono una
  **colonna** e servono a confrontare due moduli interi con un numero solo.
  Chi ha meno di 5 partite a voto compare **pallido e con l'avviso**, chi non ne ha
  nessuna porta scritto «dato insufficiente» al posto del numero: dichiarati, non
  corretti, com'era la seconda decisione di Davide.

  ⚠️ **La scelta di lettura è dichiarata, in pagina e nel codice**: la **fascia conta
  prima della fantamedia**. Vuol dire che un titolare sicuro mediocre gioca prima di
  un ballottaggio bravo. È il verso prudente, e non è l'unica risposta possibile —
  per questo il consiglio elenca i **«contesi»**, cioè chi resta fuori pur avendo
  punti attesi più alti di un titolare del suo ruolo. Chi tocca `_chiave_merito()`
  in `data.py` cambia questa scelta, e deve cambiare anche la pagina.

  ⚠️ **Il ricalcolo della fantamedia è verificato contro la fonte, non dedotto**:
  eseguito coi valori standard e confrontato con la colonna del sito, **407
  giocatori su 414 tornano esatti** entro 0.01 (tutti e 26 i portieri, tutti e 75
  gli attaccanti). È la prova che le voci sono contate giuste — se `gol` non
  comprendesse i rigori, gli attaccanti sarebbero sfasati in blocco — e che **la
  porta inviolata non è dentro la fantamedia del sito**. I 7 che non tornano: sei
  sono il **tetto dei cartellini** (ammonizione + espulsione nella stessa partita si
  fermano a −1, e dai totali di stagione non si sa in quale partita siano capitati:
  scarto ≤ 0,5), il settimo (Halhal) resta senza spiegazione e sta scritto nel
  codice.

  ⚠️ **Il tetto della panchina per ruolo non è una preferenza, è aritmetica**: con un
  portiere in campo serve **un** sostituto portiere, mai due. Il primo giro non
  l'aveva e su una rosa vera metteva **due portieri di riserva davanti al miglior
  attaccante**.

  ⬜ Quello che resta aperto qui:
  - ❌ **l'avversario: non interessa** — deciso da Davide il 22/09/2026. Il
    consiglio non guarda casa/trasferta né la forza della difesa che si affronta, e
    resta così: i dati non sono nel DB (le probabili danno l'avversario, non il suo
    rendimento) e sarebbe stato un lavoro a sé
  - ✅ **il modificatore di difesa, dal 22/09/2026**: i moduli si confrontano sul
    `totale` = punti attesi **più** modificatore stimato, e in una lega che lo usa
    cambia la graduatoria. Il voto atteso è la `media_voto` del listone (il voto
    **senza** bonus e malus, che è quello che il regolamento vuole nella media), la
    media è del portiere e dei migliori 3 difensori o dei migliori 4, e servono
    **4 difensori a voto** — quindi un modulo a tre difensori prende +0, e la
    pagina dice perché. ⚠️ I punti della tabella sono poi **moltiplicati per la
    probabilità che quei quattro giochino** (prodotto delle percentuali): senza,
    un reparto di ballottaggi varrebbe come uno di titolari sicuri e vincerebbe
    sempre il modulo con più difensori. La pagina mostra tutti e due i numeri.
    ⬜ Resta che è una **stima**: suppone che i migliori per media voto siano
    quelli che giocano, e non sa niente dell'avversario
  - ❌ **lo storico del consiglio: non interessa** — deciso da Davide il
    22/09/2026, «o va bene o va male». Resta la conseguenza, scritta perché non
    venga riscoperta come un baco: non essendoci traccia di **cosa** il consiglio
    aveva detto, non si potrà mai misurare se consigliava bene. È coerente con «una
    formazione per lega, che si sovrascrive» (21/09/2026)
  - `bonus_imbattibilita` e `malus_autogol` restano **colonne che nessuno legge**,
    dichiaratamente: manca la statistica
- ❌ **il secondo sistema: non serve** — deciso da Davide il 22/09/2026, le sue due
  leghe sono Classic. La riga qui sotto resta perché il **dato** c'è comunque, e
  chi un giorno volesse leggerlo deve sapere che non va importato, va solo usato.
- ⬜ ~~**il secondo sistema**~~: il listone porta anche i ruoli **Mantra** e sono già nel
  DB, ma oggi non li legge nessuno. Il giorno che una lega passasse a Mantra il dato
  c'è
- ⬜ **la licenza**: si legge un sito pubblico per uso personale, come già si fa con
  Bulbapedia. Se la sezione uscisse di casa (§1.5) la domanda va riaperta

### 4.3 ⬜ Le richieste di Davide del 22/09/2026 «per il futuro»

Dettate il 22/09/2026 insieme alle quattro che sono state fatte subito (listone
sfogliabile, svuota rosa, timer e consiglio sotto il campo: chiuse, vedi
`STORICO.md`). Queste restano aperte, **nelle parole con cui sono state chieste**,
perché nessuna è stata ancora misurata: sotto ogni voce c'è solo quello che già si
sa dal codice, non un piano.

**Sezione Pokémon**

- ⬜ **Un pulsante che aggiorni da solo tutto il Pokédex** quando la fonte cambia:
  Pokémon nuovi, statistiche, oggetti, mosse e abilità. C'è già il pezzo di sotto —
  `pokeapi.py` legge e `scripts/build_catalog.py` scrive — e c'è già il precedente
  giusto nel Fantacalcio: la logica in un modulo solo (`fanta_import.py`), gli
  script e il web che la chiamano, e un rifiuto **dichiarato** davanti ai numeri che
  sono il sintomo di una fonte letta male. ⚠️ Qui però il catalogo è **curato a
  mano** in molti punti (nomi italiani, forme, toppe): un aggiornamento automatico
  che sovrascrive tutto cancellerebbe quel lavoro senza dare errore. La domanda da
  rispondere prima di scrivere una riga è **quali colonne la fonte comanda e quali
  no**, e la regola d'oro dei dati vale sempre: si scrive con `salva_catalogo()` e
  `_save_abilities()`, che fanno la copia di sicurezza.
- ⬜ **Un pulsante per creare una regulation nuova senza inserire i dati a mano**,
  con una **fonte affidabile da cui confrontare i dati**. Il guscio c'è dal
  10/09/2026 (§1.3, la regulation nuova dall'interfaccia): quello che manca è la
  fonte. ⚠️ È la stessa domanda di §2.3 e §5.2 — un roster e un moveset non si
  inventano, e finché la fonte non è decisa questa voce non è pronta.
- ⬜ **Gli sprite mancanti, e quelli delle forme che usano ancora la forma base.**
  Sta anche in §3 come baco noto: qui è la richiesta di chiuderlo per bene.

**Altro**

- ⬜ **Proteggere l'accesso al GitHub** «per non farmi rubare il lavoro». Davide ha
  chiesto di farlo subito **se è veloce**: la parte veloce è verificare che il repo
  sia privato e che i segreti non siano dentro — `controlla_esposizione.py` dice già
  che né `hub.db` né la chiave di sessione sono versionati, e l'export senza
  password è di proposito. ⚠️ Quello che **non** è veloce è il resto: 2FA, chiavi di
  firma, chi ha accesso. Da fare guardando insieme le impostazioni del repo, non da
  qui.
- ⬜ **Altri colori per il tema**, oltre al bianco e nero. ⚠️ Il tema oggi sono due
  blocchi di variabili in `base.html` (`--primary`, `--surface`, …) più l'accento
  del Fantacalcio in `static/css/fantacalcio.css`: un terzo tema è **una terza lista
  di variabili**, non un foglio nuovo. ⚠️ E il tema scelto **non è nel DB** — è la
  falla 2 di §1.4, quella che l'export non porta con sé: un tema in più la rende più
  evidente, non la crea.
- ⬜ **Ricordare utente e password**, con la spunta «ricorda credenziali» come sui
  siti di oggi. ⚠️ Vuol dire un cookie firmato di lunga durata, **non** la password
  salvata: la password non esce mai dal DB, e quello che si ricorda è una sessione.
  Da fare sapendo che l'app può uscire di casa (§1.5), quindi con scadenza e con la
  possibilità di revocarla.
- ✅ **Un pulsante in Utenti per copiare tutti i dati in un altro utente** — fatto il
  22/09/2026, numeri in `STORICO.md`. Le due decisioni che il codice non poteva
  dedurre le ha prese Davide: **aggiunge** (non sostituisce, non si perde niente) e
  le **spunte di Python non si copiano**. ⚠️ Quello che resta da sapere, perché è una
  scelta e non un difetto: il pulsante **non è rieseguibile** — premuto due volte
  lascia tutto in doppio, e la conferma lo dice coi numeri prima di premere. Renderlo
  rieseguibile vorrebbe dire riconoscere «questa riga c'è già» dai **contenuti**,
  cioè fondere per titolo, che è la scorciatoia che `importa_dati.py` rifiuta per
  iscritto. C'è una prova apposta (`prova_travaso_utente.py`, §7) perché nessuno la
  «corregga» credendola un baco.

### 4.4 ⚠️ Quello che il timer della giornata dà per buono

Aperto il 22/09/2026 col timer stesso, e scritto qui perché **non è un baco oggi**:
è una cosa che può smettere di funzionare senza dare errore.

- La scadenza esce da `fanta_calendario`, che si riempie leggendo
  `/serie-a/calendario/<giornata>`. La giornata la dicono **le probabili**: se le
  probabili non sono importate, il timer ripiega sulla prima partita non ancora
  giocata che il calendario conosce, e se il calendario non ha quella giornata
  **dichiara di non sapere l'ora**. Sono tre casi diversi e la pagina li dice
  diversi: quello da non perdere di vista è il terzo, perché è silenzioso di natura.
- ⚠️ La cache del calendario è **una per giornata** (`calendario-7.html`). Se un
  giorno la fonte cambiasse la forma dell'URL, il lettore troverebbe una pagina
  senza `match-pill` e si rifiuterebbe — il rifiuto c'è ed è provato. Quello che
  nessuno controlla è che la giornata che si chiede **esista**: `/calendario/99`
  risponde comunque una pagina.
- ⚠️ E resta vero che «tre ore» e «un giorno» sono soglie scelte, non misurate:
  `VECCHIA_PROBABILI` e `VECCHIA_CALENDARIO` in `fanta_import.py`.

### 4.5 ✅ Il punto cieco di `controlla_proprietario.py` — chiuso il 22/09/2026

Trovato e chiuso lo stesso giorno, insieme al travaso di §4.3 che l'aveva fatto
guardare. Cosa faceva e cosa fa ora sta in `STORICO.md`; qui resta solo la parte
che serve a **chi tocca ancora quello script**:

⚠️ Il riconoscimento è **volutamente stretto**. `nomi_innestati()` torna un nome solo
quando il segnaposto è un nome e basta: `{cond[0]}`, `{" ".join(...)}` o una
condizione che passa per un parametro di funzione **non** vengono riconosciuti, e
quella query finisce fra le **scoperte**. È il verso giusto in cui sbagliare, ma vuol
dire che una riscrittura innocua di un punto di chiamata può far comparire una
scoperta nuova: prima di dichiararla con un'eccezione, guardare se il filtro c'è
davvero. La catena `cond` → `mia` → query si segue a punto fisso, ma **solo**
attraverso assegnazioni a un nome da una f-string.


---

## 5. 🏁 Il giro di collaudo finale (va fatto **per ultimo**)

**Questa voce si chiude dopo tutte le altre.** Sono tre lavori che si fanno insieme, e
vanno alla fine per lo stesso motivo: qui i bachi peggiori non hanno mai dato errore — il
PC Builder inerte per settimane per un apice di troppo, il Ripristina che sovrascriveva
senza chiedere, lo Speed Tier che ricadeva su una lista statica — e un lavoro fatto dopo
può rimetterli in piedi.

⚠️ **Prima di iniziare**: `graphify-out/` è una fotografia, non uno specchio. Va rifatto
(`/graphify . --update`) **obbligatoriamente** prima di 5.2 e 5.3, che sono i due lavori in
cui il grafo deve essere completo. ✅ **Rifatto il 21/09/2026** dopo i quattro blocchi della
giornata: 1029 → **1321 nodi** e 2005 → **2291 archi**, 221 comunità, 35 file riestratti
(31 di codice via AST, 4 documenti via subagent). Salute del grafo: nessun arco
penzolante, mancante o collassato.

### 5.1 ⬜ Il giro completo della web app

Ogni sezione, ogni pagina, **ogni campo e ogni funzione**. Non un controllo a campione
sulle cose toccate di recente: tutto, comprese le parti che nessuno guarda da mesi.

- **ogni campo di ogni form**: vuoto, valore limite, valore assurdo, caratteri strani —
  apostrofi e accenti sono la classe di bug che ha ucciso il Ripristina
- **ogni pulsante e ogni azione**: creazione, modifica, eliminazione, ripristino, import,
  export — e la conferma dove deve esserci
- **le due lingue** su tutte le pagine Pokémon
- **tutte le regulation**, non solo `ma`: `pokedex` e `mb` sono quelle dove sono usciti i
  bachi degli endpoint
- **il calcolatore in tutti e quattro i tab**, con la regola #8 come pietra di paragone
- lo **sweep** su ogni blocco `<script>` e ogni handler inline
- le sezioni non-Pokémon, che ricevono meno attenzione: Gaming, Arduino, PC Builder, Python

L'esito va scritto qui con i numeri: quante pagine, quanti campi, quante anomalie e quali.
Le anomalie fuori scope si segnalano, non si correggono al volo.

### 5.2 🟨 Le mosse assegnate sono davvero quelle giuste?

> **La lista `champions` è confrontata dal 14/09/2026** con `scripts/verifica_moveset.py`
> (numeri in `STORICO.md`). Il risultato cambia la domanda: **il dump non è sbagliato, è
> fermo.** PokéAPI ha Champions fino a Regulation M-B (ultimo commit del file: 21/07/2026),
> e Bulbapedia è già alla **versione 1.2.0**. La cache locale è identica al dump pubblicato,
> quindi riscaricarlo non cambia niente.
>
> **✅ Le decisioni sono prese il 18/09/2026, e le liste sono allineate alla 1.2.0.**
>
> La fonte che ha sciolto tutto **non** è la pagina learnset: è la **nota ufficiale di
> aggiornamento della 1.2.0** (9 settembre 2026), citata in «Pokémon Champions#Version
> history» su Bulbapedia. È una **lista chiusa** dei cambi di mossa, e dice:
> Politoed non può più usare *Pound*, Archaludon né *Mirror Coat* né *Metal Burst*,
> *Slash* «can now be used», e i PP di *Wish* e *Strength Sap* passano da 12 a 8.
>
> 1. ✅ **Pawmot integrato il 14/09/2026** da Bulbapedia (64 mosse). Le altre **25 voci
>    arrivate con la 1.2.0** restano senza lista, e ora si sa **cosa sono**: la nota dice
>    «Pokémon and held items have been added for **Regulation Set M-C**». Nessuna è in un
>    roster. Si integrano una alla volta con
>    `python scripts/integra_moveset_bulbapedia.py --voci <chiave>`
> 2. ✅ **Applicate**: *Slash* a **29 voci**, le tre rimozioni di Politoed e Archaludon,
>    *Psychic Fangs* al posto di *Psychic* su Ariados, e le quattro mosse che mancavano a
>    Mawile e Houndstone. Le scrive `scripts/applica_toppe_champions.py`, che **non ha un
>    elenco di nomi dentro**: ricostruisce il confronto con Bulbapedia e si ferma su ogni
>    differenza che non sia in `DECISIONI` o in `IGNORATE`. I PP non si applicano: il
>    catalogo non ha quel campo
> 3. ✅ **Gardevoir e Blaziken: il dump aveva ragione, e non era un sospetto.** La pagina
>    Champions di Gardevoir è alfabetica e **comincia da «Charm»**: le cinque mosse che il
>    dump ha in più — *Alluring Voice, Aura Sphere, Body Slam, Calm Mind, Charge Beam* —
>    sono **esattamente** le cinque che vengono prima di Charm. È la testa della lista
>    tagliata via. Su Blaziken *U-turn* è un'omissione isolata (la lista va da Acrobatics a
>    Will-O-Wisp senza buchi, la mossa non è fra le perse, e compare su 48 delle 232 pagine).
>    Nessuna delle due è nel changelog della 1.2.0. **Non si tocca niente**, ed è la regola
>    che resta: *un'assenza da una pagina non è una smentita*
> 4. ✅ **Morpeko (Hangry Mode) — chiuso il 21/09/2026**, cercando una terza fonte come
>    ha chiesto Davide. Nel dump la Hangry aveva **5 mosse in meno** della Full Belly
>    (60 contro 65: Assurance, Payback, Rising Voltage, Round, Snore) e tutte e due le
>    forme sono in MA e MB. Bulbapedia ha un blocco unico e quindi non diceva niente;
>    **Serebii** e **Game8** danno anche loro una lista unica per le due forme, con
>    dentro tutte e cinque le mosse, e dicono esplicitamente che l'unica cosa che dipende
>    dalla forma è il **tipo di Aura Wheel**. Regge anche la misura interna: delle 24
>    forme che in Champions avevano una lista diversa dalla specie, **23 avevano mosse
>    proprie** — la Hangry era l'unica ad averne solo in meno e nessuna sua — e in `main`
>    le due forme erano già identiche (67 e 67). Scritta come toppa in `TOPPE_A_MANO`,
>    con le due fonti e la data. Ora 65 e 65, zero differenze
>
> Le differenze delle **forme di Rotom** non sono errori: Bulbapedia mette le mosse proprie
> di ogni forma (Overheat, Hydro Pump, …) sulla pagina unica di Rotom, il dump le separa.

Il moveset importato il 12/08 non è mai stato confrontato con una fonte indipendente:
viene tutto dal dump di PokéAPI, e finora l'unica verifica è stata **interna** — i nomi
risolvono, i conti tornano, Incineroar perde Knock Off. Questo dice che il meccanismo
funziona, **non** che gli elenchi siano corretti.

**Fonte: [Bulbapedia](https://bulbapedia.bulbagarden.net/)**, indicata da Davide come la più
attendibile e già usata con profitto (ha confermato `Mirror Herb` → «Foglia carbone» come
seconda fonte indipendente).

In ordine di rischio:

- ✅ **la lista `champions` per prima** (14/09/2026, vedi sopra): è la più giovane e la meno vista (19 810 righe su 319
  voci), e nessuno ha mai controllato che quel version group sia completo. Se lì manca
  qualcosa, su M-A e M-B una mossa legale sparisce dalla tendina **senza dire niente**.
  ⚠️ **Dal 21/09/2026 ha anche una seconda fonte**, cercata su richiesta di Davide:
  Game8 e Serebii. Il conto: dei **10 cambi di roster di Regulation M-B** che Game8
  elenca, il dump li ha **tutti e 10 giusti** (Swampert ha *Wave Crash*, Gholdengo non ha
  *Thunder Wave*, Metagross non ha *Heavy Slam* né *Knock Off*, …), e dei **27 dati di
  mossa** confrontabili ne combaciavano **26**. L'unico scarto era *Growth*, che in
  Champions è di tipo **Erba** — Bulbapedia non lo cita, quindi il 18/09 era rimasto
  Normale. Corretto. ⚠️ Game8 sbaglia invece su una riga, e vale la pena saperlo: dice
  «Annihilape lost Pound», ma **Annihilape non impara Pound in nessun gioco** (né Mankey
  né Primeape), mentre **Politoed sì**, a livello 1. La nota di Bulbapedia su Politoed
  regge, e la nostra toppa era giusta
- ✅ **i metodi: il dump non gonfia le MT** (18/09/2026). Scaricato `machines.csv` dallo stesso
  dump e confrontate, gioco per gioco, le mosse insegnate da `machine` col catalogo MT
  del gioco: **23 version group su 24 coincidono esatti** — 55 in Rosso/Blu, 57 in
  Oro/Argento, 100 in Diamante/Perla, 105 in X/Y, 107 in ORAS, 200 in Spada/Scudo,
  **229 in Scarlatto/Violetto** coi DLC. L'unico scarto è **BDSP**, dove `machines.csv` ne
  dichiara 17 contro 100 usate: è un buco di quel file di PokéAPI, che noi non leggiamo,
  non un gonfiaggio dei moveset. Il 65,5% di `machine` è la proporzione vera
- ✅ **la lista `main` è stata curata il 21/09/2026**, ed era stata trovata il 18/09 col
  campione su generazioni diverse, senza bisogno di una seconda fonte: per **77 voci**
  l'ultimo gioco in cui comparivano era **Leggende Arceus** (58) o **Let's Go** (19), due
  giochi col sistema di mosse ridotto — Abra aveva **una** mossa, `Teleport`, invece delle
  49 di Brillante Diamante. Il difetto non era «Leggende Arceus dà poche mosse»: era che un
  gioco fuori serie **vince perché è più recente**. Ora `VG_FUORI_SERIE` in `pokeapi.py`
  tiene fuori `colosseum`, `xd`, `lets-go-*`, `legends-arceus` — più `legends-za` e
  `mega-dimension`, che oggi sono **vuoti** ma hanno order 30 e 31, cioè **sopra**
  Scarlatto/Violetto. Misurato: **74 voci** cambiano gioco, `main` passa da 68 030 a
  **70 755 mosse** (+2725), zero voci restano su Leggende Arceus, e le sole due rimaste su
  un gioco fuori serie sono **Partner Pikachu e Partner Eevee**, che in nessun altro gioco
  esistono — prese lo stesso, e il rapporto dell'import le **nomina** come ripiego. Perdono
  mosse solo Silcoon e Cascoon (3 → 1), e quell'1 è onesto: in Brillante Diamante imparano
  davvero solo *Rafforzatore*. Prova: `scripts/prova_moveset_main.py` (19 su 19)
- ⬜ **il campione di `main` contro Bulbapedia** resta da fare **solo se** `main` tornerà in
  uso: oggi non lo legge nessuno, e le pagine learnset per generazione hanno una
  struttura diversa da quelle di Champions, quindi il lavoro andrebbe rifatto lo stesso

Metodo: uno script rieseguibile che scarica, che **si ferma su ciò che non risolve**, e che
dove le due fonti non concordano **lo segnala e basta**. Non si sovrascrive PokéAPI con
Bulbapedia alla cieca: nessuna delle due è sempre giusta, e la lezione è già stata pagata.

### 5.3 ⬜ L'inventario di cosa non serve più

Un censimento di tutto il progetto per capire cosa si può togliere. Va fatto alla fine
perché finché i lavori sono in corso, un file che oggi sembra morto può servire domani.

- **template** — chi li renderizza? Vanno cercati anche i blocchi Jinja, gli `{% include %}`
  e i `{% block %}` che nessuno estende più
- **`static/js/` e `static/css/`** — chi li carica, e **quali funzioni non chiama nessuno**
  (qui sono già state trovate `MEGA_DATA`, `PKMN_DB`, `calc_stat_champions()` e una
  `switchTab` duplicata: la classe esiste)
- **route Python** non raggiunte da nessun `url_for()`, link o `fetch()`
- **funzioni e helper** nei blueprint, in `data.py` e in `extensions.py` mai importati
- **gli script di `scripts/`** — quali sono una-tantum già consumati (`build_catalog.py`,
  gli `importa_*` ed `esporta_dati.py` restano perché rieseguibili)
- ✅ **il blocco `main` di `pokemon_moves.json` NON è codice morto**, e la domanda è
  chiusa il 21/09/2026 da una decisione di Davide: «la base dati di tutti i pokemon, le
  mosse, oggetti e abilità deve comunque esserci per poter costruire facilmente una nuova
  regulation in futuro». Delle tre strade — sistemarlo, toglierlo dalla tendina, lasciarlo
  dichiarato — è stata presa la prima, l'unica che tiene insieme le due cose: **1293 voci**
  e 1,7 MB dei 3 restano nel file, `sorgenti_moveset()` continua a offrirlo, e adesso è
  **giusto** invece che rotto (vedi §5.2). ⚠️ Quindi qui non si tocca: chi farà
  l'inventario lo troverà non letto da nessuna regulation, e non è una prova che sia morto
- **i file di dati storici**, la voce più concreta — vedi la trappola in cima. Da dismettere
  **solo** a verifica finita, cioè qui
- **la tabella `regulations` nel DB** (vedi §1.4, falla 1) e ogni altra colonna che nessuna
  query legge più
- **immagini e asset** in `static/` non referenziati

Il metodo: **prima si misura, poi si propone.** Per ogni candidato serve la prova che non è
usato, e la rimozione si fa in un blocco suo, dopo il via libera di Davide — non insieme al
collaudo, così se qualcosa si rompe si sa quale dei due l'ha rotto.
