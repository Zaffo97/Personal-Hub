# 📋 BACKLOG — Personal Hub

> **Qui c'è solo ciò che è aperto.** Le voci chiuse stanno in [`STORICO.md`](STORICO.md),
> una riga per lavoro con la data e i numeri della verifica.
> Aggiornato: **25/09/2026** (potatura: da 1310 righe; il testo di prima è
> `git show 513c082:BACKLOG.md`). Fonte storica: `Nuove implementazioni.docx`.

Legenda: ⬜ da fare · 🟨 parziale · ✅ chiuso (resta il titolo, perché il codice cita il
numero del paragrafo) · ⚠️ trappola nota, da rileggere prima di toccare la zona

**Indice**

1. [Le trappole che valgono ancora](#-le-trappole-che-valgono-ancora) — leggere prima di lavorare
2. [L'ordine](#-lordine-aggiornato-il-25092026)
3. [I blocchi aperti](#1-i-blocchi-aperti)
4. [I lavori a metà](#2-i-lavori-a-metà)
5. [Bachi noti](#3-bachi-noti)
6. [Voci minori, per sezione](#4-voci-minori-per-sezione)
7. [🏁 Il giro di collaudo finale](#5--il-giro-di-collaudo-finale-va-fatto-per-ultimo)

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
| ⚠️ **Un parametro che vale «vedi tutto» quando lo dimentichi** | Dal 21/09/2026 (il modulo è stato tolto il 25/09/2026 con la sezione vecchia, la regola resta, e `fanta._rose()` la segue). `fanta_import._rose()` nasceva con `ambito=None`, che voleva dire «conta le rose di tutti»: giusto per uno script da riga di comando, che una sessione non ce l'ha — **sbagliato** per il pulsante «Aggiorna», che una sessione ce l'ha, e che così diceva «2 dei giocatori usciti sono in una tua rosa» contando rose altrui. L'ha preso `controlla_proprietario.py`. La regola: quando la stessa funzione la chiamano il web e uno script, il «vedo tutto» **si scrive** (`TUTTE_LE_ROSE`), non si ottiene lasciando fuori un parametro. ⚠️ E lo strumento ha imparato un caso nuovo — una funzione che **riceve** la condizione invece di chiederla a `ambito_utente()` — con un criterio volutamente stretto: il parametro si chiama `ambito` **e** dev'essere letto nel corpo. Un primo tentativo più largo marcava filtrata l'intera funzione, rami senza filtro compresi: la scappatoia esatta che quello strumento esiste per chiudere |
| ⚠️ **In italiano la virgola è ANCHE il separatore decimale** | Dal 21/09/2026, preso dalla prova al primo giro sulle soglie del modificatore di difesa. `"7,5:8, 6:2"` spezzato sulle virgole dà `7` e `5:8`: una tabella diversa da quella scritta, **senza nessun errore**. Ora le coppie `media:punti` si **cercano** con una regex invece di spezzare la riga, e se dopo averle tolte resta qualcosa che non è un separatore si torna allo standard — meglio un default dichiarato che tre righe su quattro. Vale per qualunque elenco di numeri scritto a mano in questo progetto |
| ⚠️ **Il valore di partenza di un form non è il DEFAULT della tabella** | Dal 21/09/2026, trovato provando il JS in browser (lo sweep non poteva: era sintatticamente perfetto). Le tendine nuove delle regole precompilavano dai **valori ufficiali**, e le due voci che il regolamento non fissa — porta inviolata e autogol — non essendoci, partivano dal **primo valore della tendina**, cioè `0`. Una lega nuova nasceva con l'autogol che non toglie niente, mentre la tabella ha `DEFAULT -2`. Nessun errore, solo una regola sparita. Ora `VALORE_PARTENZA` è un dizionario **diverso** da `VALORE_UFFICIALE` e i due non si confondono. ⚠️ Fin quando il campo era vuoto il difetto non poteva esistere — era il DB a decidere: **dare un valore iniziale a un campo sposta la decisione dal DB al form**, e da lì in poi i due devono concordare |
| ⚠️ **`{{ nome|e }}` dentro un handler inline è un `SyntaxError` che aspetta un apostrofo** | Dal 22/09/2026, sul `confirm` che chiede se togliere un giocatore dalla rosa. L'escape HTML rende `N'Dicka` come `N&#39;Dicka`, e il browser **decodifica l'attributo prima** di passare il codice al parser JS: l'handler non compila, il `confirm` sparisce e **il form parte lo stesso**, cioè la conferma di una cosa irreversibile non c'è più. Nessun errore a schermo. E lo **sweep non lo vede finché il dato non ha l'apostrofo**: i nomi con l'apostrofo nel listone sono 2 su 597, e con nessuno dei due in rosa la pagina resa era pulita. La cura è `|tojson` con l'attributo fra **apici singoli** (regge anche le virgolette doppie); lo sweep prende solo ciò che la pagina resa contiene davvero, quindi il caso difficile va **messo nei dati di prova**. ✅ L'ultimo caso rimasto, `admin_utenti.html` con `{{ u.username }}`, è chiuso il 25/09/2026, e `prova_travaso_utente.py` ha nei dati un utente `d'amico "bis"` |
| ⚠️ **Lo sweep controlla il JavaScript, non che l'HTML sia ben formato** | Dal 21/09/2026, trovata da Davide cliccando «Fantacalcio» in sidebar e finendo sul PC Builder. Il blocco `{% if 'fantacalcio' … %}` era finito **dentro l'attributo `class`** del link PC Builder, che non veniva mai chiuso: il parser fonde i due `<a>` in uno solo, e resta un `href="/pcbuilder"` con scritto «Fantacalcio». `sweep_pagine.py` era a **0 errori** anche così, perché rende la pagina ed esegue `new Function()` sugli script e sugli handler — un tag mai chiuso non è JavaScript, quindi non lo guarda nessuno. Un link aggiunto a `base.html` va verificato **sulla pagina resa con un parser HTML** (href per href, e `<a>` aperti = chiusi), non a occhio sul template: l'errore si legge male proprio perché il pezzo giusto è tutto lì, solo nel posto sbagliato |
| ⚠️ **Lo sweep guardava solo le pagine che si aprono con una `GET`** | Dal 21/09/2026, con l'anteprima della rosa incollata. `sweep_pagine.py` scorreva un elenco di URL e faceva `c.get()` su ognuno: una pagina che **esiste solo mandando un form** non era in nessun elenco, quindi lo sweep avrebbe detto «0 errori» senza averla mai resa — ed è una pagina piena di form, tendine e `<script>`, cioè esattamente quello che quello script esiste per controllare. È la stessa forma della trappola sulle tabelle nuove: un elenco scritto a mano che non si accorge di quello che non contiene. Ora c'è `PAGINE_POST` (URL + dati), e i dati di prova contengono di proposito un nome ambiguo e uno inesistente, perché la pagina resa abbia davvero dentro una tendina e una riga «non trovata». La regola: **una pagina nuova si aggiunge all'elenco giusto dei due nello stesso commit in cui nasce** |
| ⚠️ **Una prova costruita male dice NO a un codice giusto, e costa come un baco** | Dal 21/09/2026, tre volte in un pomeriggio scrivendo le prove del consiglio e della rosa incollata. (1) Due righe incollate identiche messe in un **dizionario per testo** diventavano una: la prova chiedeva due esiti e ne trovava uno. (2) Il «contesi» del consiglio pretendeva un disaccordo fra fascia e punti attesi che coi numeri scelti **non poteva esistere** — serviva fm > 10.8, il banco ne aveva 9.0. (3) La regola del rivale in panchina veniva provata su un banco dove **tutti** i centrocampisti erano in campo, cioè chiedendo un rivale che non c'era. Ogni volta il primo istinto è stato «allora il codice sbaglia», e ogni volta la cura era rifare il banco: il numero che una prova pretende va **contato**, non scelto perché sembra grosso. Il danno è doppio — si perde tempo e, se si «corregge» il codice per far passare la prova, si rompe quello che funzionava |
| ⚠️ **Passare `None` a una colonna con un `DEFAULT` scavalca il default** | Dal 21/09/2026, presa da `prova_fantacalcio.py` al primo giro. Il salvataggio di una lega costruiva l'`INSERT` con **tutte** le colonne delle regole, mettendo `None` dove il form non aveva niente: in SQLite un `NULL` **esplicito** è un valore, non un'assenza, quindi il `DEFAULT 3` del bonus gol non entrava mai e una lega nuova nasceva coi bonus a `NULL`. Nessun errore: il bonus semplicemente non c'era. La cura è non mettere la colonna nella query — che nell'`UPDATE` vuol dire anche «lascia il valore di prima», cioè la stessa cosa detta bene |
| ⚠️ **«PokéAPI non la conosce» quasi mai vuol dire «è inventata»** | Misurato il 21/09/2026, e per un mese si è creduto il contrario. Il rapporto dell'import stampava 16 voci sotto la frase «forme che PokéAPI non conosce», e il backlog le chiamava «forme di Davide»: **falso per 14 su 16**. I loro slug — `darkrai-mega`, `absol-mega-z`, `golisopod-mega`, … — sono **tutti in `pokemon.csv`**. PokéAPI le conosce benissimo; quello che non ha sono le **righe di mosse**, perché i loro unici giochi sono `legends-za` e `mega-dimension`, i due version group che nel dump hanno **zero righe** (gli stessi che `VG_FUORI_SERIE` sorveglia). Fra quelle 14 ce n'erano **cinque Mega vere di Regulation M-C** — Mega Absol Z, Mega Garchomp Z, Mega Lucario Z, Mega Golisopod, Mega Baxcalibur — confermate da Serebii **e** da Game8. E **nemmeno le due Mega Meowstic** erano sconosciute, scoperto lo stesso giorno: `meowstic-male-mega` e `meowstic-female-mega` sono nel dump **con le loro righe di mosse**. Mancava solo lo `slug` nel catalogo, e mancava perché `aggiungi_slug_forme.py` si **rifiutava** di scriverlo: le sei base stat della femmina non combaciavano, perché la voce era rimasta a **466**, il totale della forma **non** Mega. Cioè un dato sbagliato teneva fuori una voce vera, e il rifiuto era il verso giusto. Corretto a 566 su tre fonti concordi. Quindi delle 16 la frase era falsa per **tutte e 16**. ⚠️ La regola generale, che era già scritta dal 13/09 e non era stata applicata a questa conclusione: **prima di dare per inventata una voce senza moveset, cercarne lo slug nel dump.** Ora il rapporto dell'import stampa i due gruppi separati, con l'etichetta giusta |
| ⚠️ **Una toppa è scritta con la chiave di una specie, e le forme non sono la specie** | Trovata il 21/09/2026 da `verifica_moveset.py`. Le toppe della 1.2.0 nominavano **33 specie**, e si fermavano lì: **19 forme** di quelle specie — Mega Absol, Mega Charizard X e Y, Aegislash (Blade Forme), Mimikyu (Busted Form), … — sono rimaste senza lo *Slash* che la loro specie aveva preso, e **sono tutte in MA e MB**. A schermo voleva dire che Absol poteva sceglierlo e Mega Absol no, che è lo stesso Pokémon a metà partita. Nessun errore, solo la tendina più corta. Ora `applica_toppe_moveset()` raggiunge anche le forme, ma **solo** quelle la cui lista, tolte le mosse che la toppa nomina, è **identica** a quella della specie: una forma con una lista sua (le Rotom, Hisuian Samurott) finisce in un terzo elenco che l'import stampa, e non viene toccata. Il confronto ignora le mosse nominate proprio perché regga sia sul file appena rigenerato dal dump sia su uno già toppato a metà. ⚠️ Chi aggiunge una toppa nuova non deve elencare le forme a mano: se lo fa, quella forma viene saltata dalla propagazione (`if nome_forma in toppe`) ed è giusto così, ma la sua lista va scritta intera |
| ⚠️ **L'eredità è costruita prima che integrazioni e toppe entrino** | Dal 21/09/2026. In `costruisci_moveset()` la forma Gigantamax copia il dizionario della specie: **mutare** una lista condivisa si propaga, **aggiungere un blocco nuovo alla specie no**. Integrando le 25 voci di Regulation M-C è successo esattamente questo: Cinderace, Inteleon, Rillaboom e Toxtricity hanno preso la loro lista `champions` da Bulbapedia, e le loro quattro Gigantamax — che dichiarano `eredita_da` — sono rimaste **senza**, con l'avviso giallo «nessun elenco mosse». Nessun errore. Ora `riallinea_forme_eredi()` gira **dopo** integrazioni e toppe in tutti i percorsi che scrivono il file, e `prova_moveset_main.py` controlla che ogni voce con `eredita_da` abbia davvero la lista della sua base |
| ⚠️ **Una forma Gigantamax condivide l'oggetto della sua base, non una copia** | Trovata il 21/09/2026. In `costruisci_moveset()` l'eredità è una copia **superficiale**: `voce["champions"]` della Gmax **è lo stesso dizionario** della specie base. Per l'import in blocco è il verso giusto — `eredita_da` dichiara proprio che la lista è quella della base, quindi una toppa applicata a `charizard` arriva anche alla sua Gmax — ma `applica_toppe_champions.py` lavora sul JSON **dal disco**, dove le due liste sono due oggetti separati, e lì la propagazione non c'è. Risultato: il file del 18/09/2026 aveva `Charizard (Gigantamax Form)` **senza** lo *Slash* della 1.2.0 che la sua base aveva, e nessuno se n'è accorto. La rigenerazione del 21/09 le ha riallineate (`champions` 20 699 → 20 700 mosse, una sola voce). La rete: `prova_moveset_main.py` controlla che **ogni** forma con `eredita_da` abbia davvero la lista della sua base |
| ⚠️ **I dati delle mosse sono quelli di Champions, non di Scarlatto/Violetto** | Dal 18/09/2026, decisione di Davide. Champions **ribilancia** le mosse rispetto ai giochi principali, e il catalogo viene da PokéAPI, cioè da S/V: la sezione «Changes from Scarlet and Violet» della pagina «Pokémon Champions» su Bulbapedia elenca una trentina di differenze. Delle 29 misurabili il catalogo ne aveva **17 già giuste** e 12 no (Slash bp 70→80, Grav Apple 80→90, Crabhammer precisione 90→95, Snap Trap da Erba ad **Acciaio**, …): un numero sbagliato, nessun errore a schermo. Le riallinea `scripts/allinea_dati_mosse_champions.py`. ⚠️ Quella sezione ha in fondo un blocco **commentato** di mosse «that aren't in the game yet» (Gear Grind, Anchor Shot, Hyper Drill, …): quelle **non** vanno scritte. E i **PP** non hanno dove andare — nessuna delle 919 mosse ha quel campo |
| ⚠️ **Un file di dati si riscrive come lo scrivono gli altri** | Due modi di sporcare un diff, trovati il 18/09/2026 su `pokemon_moves.json` (3 MB). **(1) L'indentazione**: i due scrittori del file usano `indent=1`, uno script nuovo con `indent=2` lo reindenta tutto — **100 000 righe di diff per 33 voci cambiate**, e la modifica vera diventa impossibile da leggere in revisione. ✅ Dal 23/09/2026 anche `salva_moveset()` in `blueprints/pokemon.py` usa `indent=1`. **(2) L'ordine dei set**: l'hash delle stringhe in Python è randomizzato per processo, quindi iterare un `set` di nomi dà un ordine diverso a ogni giro. Uno script che scrive nell'ordine in cui itera **non è idempotente**, e si vede solo confrontando l'md5 di due giri in **processi separati** — nello stesso processo l'ordine è stabile e la prova passa. Si chiude con `sorted()` e riordinando i dizionari scritti |
| ⚠️ **Il Pokedex mostra le mosse di Champions, e per 1009 voci su 1342 non ne mostra nessuna** | Dal 18/09/2026, decisione di Davide: «voglio solo ciò che imparano in Champions». `pokedex` è passata da `moveset: main` a `champions`, che copre **333 voci** — il roster del gioco. Tutte le altre, Abra e **Amoonguss** compresi, prendono l'avviso giallo «nessun elenco mosse: sono mostrate tutte» e la tendina da 919. **Non è un guasto**, è la risposta onesta: `null` vuol dire «non lo sappiamo», ed è la stessa che prendono le forme inventate. ⚠️ Vale anche per il **caso della regola #8**, che gira proprio su `pokedex` con Amoonguss: l'avviso giallo su Amoonguss è previsto, il danno si calcola lo stesso perché la mossa si scrive a mano (Buio, fisica, BP 100). Chi «aggiusta» quell'avviso rompe una decisione, non un baco |
| ⚠️ **Ci sono due export, e uno non deve mai entrare in git** | Dal 18/09/2026. `esporta_dati.py` senza opzioni scrive `data/backup/hub_export.json`, che **viene committato** e per questo **non contiene le password**. `--completo --uscita <percorso>` scrive il backup vero, con gli **hash delle password** e `regulations`. Non ha un percorso di default di proposito: pretende `--uscita` e si **rifiuta** di scrivere se risalendo l'albero dalla destinazione trova un `.git`. In `.gitignore` c'è la seconda rete (`*_completo.json`). ⚠️ Chi aggiunge un default «comodo» dentro al repo, o toglie il controllo per far passare una prova, rimette in piedi esattamente il buco per cui `hub.db` non è versionato |
| **Risoluzione per nome** | Due chiavi diverse possono avere lo stesso `nome_it`/`nome_en`, e il catalogo Pokémon cita le abilità col nome **inglese** mentre le chiavi sono italiane. Ogni confronto per nome va fatto con `risolviChiave()` / `_INDICE`, mai con un match esatto sulla chiave |
| **Fallback silenziosi** | Più di un baco qui non dava errore, dava il numero sbagliato: lo Speed Tier che ricadeva su una lista statica, `/api/moves` che leggeva il file di MA, un alias che rispondeva Mega Venusaur. Se un loader ha un ramo di riserva, va verificato **quale dei due** sta rispondendo |
| **Endpoint fantasma** | **Quattro volte** il JS ha chiamato una risposta che nessuno aveva mai implementato: `/api/regulations`, `d.moves`, `d.regulation` e — trovato il 17/08 e scritto il 19/08 — `/api/team/<id>`. Tutte e quattro fallivano **dentro un `catch` muto**, quindi la pagina si apriva e mancava solo un pezzo, senza un errore a schermo. Sono tutte chiuse, ma la classe resta: **un `catch(e){}` vuoto qui è un baco in attesa**, e il modo di trovarli è leggere cosa il JS chiede e cercarlo nella `url_map` |
| **Le Mega** | La firma «+75 HP» individua le voci convertite **specie per specie, non stat per stat**: su Froslass cinque valori su sei erano convertiti e uno no, e la regola applicata in blocco ha rotto proprio quello. E la conversione può partire da una forma diversa da quella di testa (Zygarde Complete) |
| **File storici** | `data/pokemon_catalog.json`, `roster_ma.json`, `moves_ma.json`, `items_ma.json`, `abilities.json` sono ancora lì come **fallback**, e `pokemon_catalog.json` contiene le Mega nella vecchia forma convertita. Si dismettono al collaudo finale, non prima |
| **Scritture concorrenti** | `salva_catalogo()` riscrive il file intero **senza lock**: due salvataggi nello stesso istante non danno errore, l'ultimo vince e l'altro si perde. Rilevante appena l'app va online |
| **`t` come variabile** | `{% for t in … %}` **ombra la funzione `t()`** delle traduzioni. Negli editor Pokémon è stato rinominato quando sono stati tradotti; oggi resta solo in `python.html:39`, sezione non tradotta: va rinominato se un giorno la si traduce |
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
| ⚠️ **Un tema è una lista di variabili, e vive in cinque posti** | Dal 22/09/2026 i temi sono quattro. I colori stanno in `templates/_temi.html` — **un file solo**, incluso da `base.html` e da `login.html`, perché fino a quel giorno il login aveva una copia sua con dentro due temi e sarebbe rimasto scuro per chi ne sceglieva un altro. Gli altri quattro posti: la lista `temi` del menu, `TEMI` e `TEMI_CHIARI` in JavaScript (`base.html`), e l'elenco nel `<head>` del login. ⚠️ Ognuno rompe **in silenzio**: una variabile che manca eredita quella di `:root` (il tema scuro) e dà un colore sbagliato solo su quel tema; un tema fuori dal menu esiste e non si sceglie; fuori da `TEMI` dà un pulsante che non fa niente; fuori da `TEMI_CHIARI` tiene l'icona della luna. Che restino d'accordo lo controlla `python scripts/prova_temi.py`, che misura **anche i contrasti** — il ciano scelto a occhio per Oceano dava 2.43, e a occhio sembrava a posto |
| ⚠️ **Uno script che gira «su tutte le regulation» spesso gira su un elenco scritto a mano** | Dal 22/09/2026, e la prova è che ha mentito: completata Regulation MC, `completa_mega_map.py` ha risposto «niente da fare: ogni Mega nel roster è già raggiungibile» mentre **sei Mega di MC non lo erano** — dentro aveva `REGULATION = ("ma", "mb", "pokedex")`. Ora l'elenco lo legge dal **registro** (`data/regulations.json`), così una regulation nuova entra da sola. ⚠️ Stesso script, secondo baco trovato lì accanto: scriveva `last_updated = "2026-08-11"` **fisso**, cioè il giorno in cui era stato scritto — su MC avrebbe messo una data di un mese e mezzo prima, che è il tipo peggiore di dato falso perché è plausibile. Chi scrive uno script che gira su più regulation parta dal registro, e chi ne legge uno vecchio controlli **da dove prende l'elenco** prima di fidarsi di un «niente da fare» |
| ⚠️ **Lo sprite di una forma si prende dal catalogo, non dal nome a schermo** | Dal 22/09/2026, ed è il baco che ha tenuto **333 URL rotti**: `_costruisci_indice()` in `api_pokemon.py` ricavava lo slug dal nome visualizzato — «Venusaur (Gigantamax Form)» → `venusaur-gigantamax-form` — mentre la stessa voce del catalogo aveva già scritto `venusaur-gmax`. ⚠️ Poi c'è un secondo passaggio, e vanno tenuti distinti: il catalogo parla **PokéAPI** (`raichu-alola`, `-gmax`), pokemondb usa altre parole (`raichu-alolan`, `-gigantamax`). La traduzione sta in `SUFFISSI_PDB`, e confronta la **fine** dello slug — con un `in` la regola `-alola` colpirebbe `pikachu-alola-cap`, che funziona. ⚠️⚠️ **Nei template non c'è un `onerror` su nessuna `<img>`**: uno sprite rotto è l'icona spezzata del browser e nient'altro, quindi questi 333 non li ha segnalati nessuno per mesi. Chi tocca la zona lanci `python scripts/controlla_sprite.py` (rete, con cache) |
| ⚠️ **Il cookie «resta collegato» è `secure` solo in https, e non è una svista** | Dal 22/09/2026: `secure` segue `request.is_secure` invece di essere fisso. In casa l'hub gira in **http**, e un cookie `secure` lì il browser non lo manda mai — la spunta sembrerebbe rotta **senza dare nessun errore**. Quando l'app uscirà di casa (§1.5) sarà in https e il cookie diventerà `secure` da sé, senza toccare niente. ⚠️ Chi mette l'app online **verifichi che sia davvero https**: in http su internet quel cookie viaggia in chiaro, e chi lo intercetta entra. `httponly` e `samesite=Lax` invece valgono sempre |
| ⚠️ **Una tabella nuova con un `user_id` va messa in `TABELLE_UTENTE`; una sua figlia in `FIGLIE_DI`** | Dal 22/09/2026, in `extensions.py`. `TABELLE_UTENTE` dice **cosa farne** quando l'utente sparisce: `passa` (contenuto, cambia proprietario) o `cancella` (stato personale, e quante righe erano si dice a schermo). `FIGLIE_DI` dice **quali righe seguono un padre**, e serve solo alla **copia**: nel travaso le figlie seguono da sole perché il padre resta quello, in una copia il padre nuovo ha un id nuovo. Nessuno dei due è un promemoria da ricordarsi: `tabelle_senza_regola()` legge le colonne vere, `figlie_senza_regola()` legge le **chiavi esterne** vere, e le due route **si rifiutano** nominando chi manca. ⚠️ Una figlia dimenticata è la peggiore delle due: non dà nessun errore, fa nascere il padre **vuoto**. Ma la tabella nuova va messa anche in `RADICI` di `controlla_proprietario.py`, e **quello nessuno lo controlla**: una tabella fuori da quel raggio fa dire «0 scoperte» senza che nessuno l'abbia guardata — è successo tre volte (le due del Fantacalcio il 21/09, `python_progress` il 22/09) |
| **`user_id` a `NULL`** | Il travaso ad `admin` gira **solo nel giro in cui la colonna nasce**, non a ogni avvio: è voluto, perché un `WHERE user_id IS NULL` permanente intesterebbe all'admin qualunque riga scritta male, in silenzio. Il prezzo: una riga senza proprietario **sparisce dalla vista del suo autore** — ma non è persa e non è invisibile a tutti, perché l'admin filtra `1=1` e la vede, col badge che dice «senza proprietario». È lì che si va a cercarla quando qualcuno dice «il dato è sparito» |
| ⚠️ **Un campo che manca vale «main»** | La sorgente delle mosse di una regulation e' `moveset` in `data/regulations.json`, e **se manca non e' un errore**: `sorgente_moveset()` ricade su `main`. Fino al 10/09/2026 la creazione non lo scriveva affatto, quindi una regulation copiata da MA — 279 nomi di Champions — leggeva gli elenchi dei giochi principali: **80 mosse su Incineroar invece di 77**, Knock Off compresa, senza un errore da nessuna parte. Ora la creazione lo scrive sempre esplicito e il salvataggio rifiuta un nome che non esiste, ma il fallback resta: **un file scritto a mano senza quel campo dira' `main` e sembrera' giusto** |
| **Default del DB** | `extensions.py:143` crea la colonna con `regulation_id TEXT DEFAULT 'ma'`. Non è un residuo dei 14 letterali tolti l'11/08: è il default del **DB**, e cambiarlo richiede una migrazione. Oggi non fa danno perché `_team_upsert()` passa sempre un valore esplicito |
| ⚠️ **L'import di una specie riconosce la voce dallo slug, non dalla chiave** | Dal 21/08/2026 (§1.3). Delle specie di default del dump che mancano al catalogo ce ne sono 4, e ci sono già tutte **sotto un'altra chiave**: confrontare per chiave le importerebbe in doppio. **Le forme non passano dall'import** — stanno annidate in `forms`, e importarle al primo livello farebbe un doppione. E reimportando una specie le sue `forms` vanno **ricopiate**: il dump non le ha e nessun import può ricostruirle. Dal 23/09/2026 anche `build_catalog.py` confronta lo slug |
| ⚠️ **Il pulsante della `mega_map` completa, non ricalcola** | Dal 10/09/2026 (§1.3). I collegamenti scritti a mano restano, e le Mega la cui base è fuori dal roster **non si collegano da sole**: aggiungere una specie è una scelta di contenuto |
| ⚠️ **Il ripristino: password fuori, e l'unità è la riga con il suo `id`** | Dal 21/08/2026 (§1.4). Con l'export normale un utente ripristinato nasce con una password casuale che nessuno conosce, e va reimpostata da `/utenti` (lo script lo dice). Con `--completo` le password entrano **solo** per gli utenti nuovi. Non c'è nessuna fusione per titolo o per nome, perché `team_members.team_id`, `pc_components.build_id` e `python_progress.topic_id` puntano a quegli `id`. `regulations` sta in `MAI_SOVRASCRITTE`: la sua `created_at` la scrive `init_db()` al momento, e senza quella regola ogni ripristino su un DB nuovo si fermerebbe su un timestamp. ⚠️ Stessa forma, trovata il 25/09/2026: `users.tema` e `users.lingua` nascono **vuoti** sull'admin di `init_db()`, e un export con un tema scelto fermava il ripristino su un PC nuovo (e 13 prove su 32 con lui). Ora stanno in `DA_COMPLETARE`: vuoti nel DB si riempiono dall'export e lo si dice; un valore **suo** e diverso resta un conflitto. **Una colonna nuova in `users` che `init_db()` crea vuota va pensata qui**, o il ripristino si riferma |
| ⚠️ **Un effetto che il motore non conosce non si attiva** | Dal 14/09/2026. Il calcolatore gestisce gli effetti elencati nel docstring di `scripts/assegna_categorie_oggetti.py`, più `pikachu_boost` e `resist_<tipo>`. Un oggetto nuovo con `effect` e `modifier` compare nella tendina, ma finché `calcDamage()` non conosce l'effetto il risultato dice «non si attiva». È voluto: fino al 14/09 un oggetto sconosciuto moltiplicava l'Attacco in silenzio. **Ogni effetto nuovo va scritto anche nel motore**, e provato con un caso calcolato a mano. ⚠️ La tendina mostra le voci con `modifier` **non nullo**, e 0 è un valore: il Palloncino ha `modifier: 0` |
| ⚠️ **`puo_evolversi` ha tre valori** | Lo scrive `scripts/importa_evoluzioni.py` (1342 voci su 1342), **per forma** e non per specie: Corsola di Galar sì, quella di Kanto no, le Mega mai. **Assente vuol dire «non lo sappiamo»**, e l'Evolcondensa lo dice a schermo, come `moves: null`. L'import dal pannello lo calcola da sé; **una voce aggiunta a mano dall'editor nasce senza**, e va rilanciato lo script. Nelle forme **non si eredita** dalla specie in `api_pokemon.py`: darebbe `true` a tutte le Mega |
| ⚠️ **Un'assenza da una pagina non è una smentita** | Dal 18/09/2026 (§5.2). La pagina Champions di Gardevoir su Bulbapedia **comincia da «Charm»**: le cinque mosse che il dump ha in più sono esattamente le cinque prima in ordine alfabetico, cioè la testa della lista tagliata. Su Blaziken *U-turn* è un'omissione isolata. Le mosse proprie delle **forme di Rotom** Bulbapedia le mette sulla pagina unica, il dump le separa: non sono errori. Non si sovrascrive PokéAPI con Bulbapedia alla cieca, né il contrario. E anche Game8 sbaglia: «Annihilape lost Pound» è falso, Pound lo impara Politoed |
| ⚠️ **Un id scelto a tavolino non è una prova di proprietà** | Pagata il 16/08/2026 (§4.1). La cache IGDB vera usa `igdb_release_id` fra **486664 e 954196**; uno script di prova che cancellava «il suo intervallo» 900000-910000 si è portato via **497 righe vere**. Un test che condivide lo stato coi dati veri misura anche quelli: la prova del calendario gira su una **copia** di `hub.db` |
| ⚠️ **`controlla_proprietario.py` riconosce il filtro in modo volutamente stretto** | Dal 22/09/2026 (§4.5). `nomi_innestati()` torna un nome solo se il segnaposto è un nome e basta: `{cond[0]}`, `{" ".join(...)}` o una condizione passata da un parametro **non** vengono riconosciuti, e quella query finisce fra le **scoperte**. È il verso giusto in cui sbagliare, ma una riscrittura innocua può far comparire una scoperta nuova: prima di dichiararla con un'eccezione, guardare se il filtro c'è davvero. La catena `cond` → `mia` → query si segue solo attraverso assegnazioni a un nome da una f-string |
| ⚠️ **Un indirizzo che un sito dichiara non è un indirizzo che funziona** | Dal 25/09/2026, sul PC Builder. Versus dichiara nella pagina (dati strutturati `SearchAction`) la ricerca `versus.com/it/search?q={query}`: aperta, **ignora la query** e mostra i risultati di un'altra ricerca. Un link costruito su quella dichiarazione avrebbe aperto sempre la pagina sbagliata, senza nessun errore. Ogni formato di link verso un sito esterno va **aperto e guardato** prima di scriverlo nel codice; quelli verificati sono scritti in cima a `pc_negozi.py` (la ricerca di BPM-Power, che Cloudflare nasconde a Claude, l'ha presa Davide da una ricerca vera) |
| ⚠️ **Scelte che sembrano bachi, e non vanno «corrette»** | **L'hover del tema scuro** (`--primary-h: #9488f7`, bianco sopra a **2.95**, sotto la soglia di 3.0) resta com'è per decisione di Davide del 22/09/2026: `prova_temi.py` lo tiene in `DICHIARATE` e lo ristampa a ogni giro. **Il travaso fra utenti non è rieseguibile**: premuto due volte lascia tutto in doppio, la conferma lo dice coi numeri, e `prova_travaso_utente.py` c'è apposta. **In italiano il calcolatore scrive `Privazione`**, non `Knock Off`: se si vuole l'inglese anche in italiano si cambia in un punto solo, `nomeVis` nel `<head>` di `base.html` |

---

## 📌 L'ordine, aggiornato il 25/09/2026

> **Il PC Builder (§4.7)** è fatto e provato da Davide nel suo Chrome (25/09/2026): restano
> solo voci rimandate per scelta (API eBay, notifiche vere) e i limiti dichiarati del catalogo.
> Il Fantacalcio (§4.6) è in piedi e provato a mano da Davide (25/09/2026): resta solo una
> misura che aspetta un evento (una partita spostata), non codice.

Le decisioni che valgono ancora: la sezione Pokémon si finisce prima delle altre (14/09),
il collaudo va alla fine, le guide dopo il collaudo, e **mettere l'app online per ultimo**
(«caricare il sito da qualche parte lo voglio tenere come una delle ultime cose»).

1. §4 — le sezioni: **Log**. Stampa 3D (§4.8), Arduino (§4.9) e Python (§4.10) sono
   fatte; restano le prove nel Chrome di Davide (Arduino: rimandata da lui il 25/09) e ciò
   che aspetta la stampante
2. I residui Pokémon: le due abilità senza effetto (§3), Kingambit e Game8 (§4.3)
3. §5 — il giro di collaudo, l'inventario del codice morto
4. §1.6 — le due guide, **dopo** il collaudo
5. §1.5 — l'app online

---

## 1. I blocchi aperti

Sei blocchi aperti il 12/08/2026. **1.1 e 1.2 sono chiusi**, e le regole che hanno lasciato
sono nelle trappole (una route nuova sotto `/pokemon/*` nasce **chiusa**, una query nuova
sui contenuti nasce **scoperta**).

### 1.1 ✅ I dati hanno un proprietario — chiuso il 19/08/2026

78 query su 78 che sanno di chi parlano. Restano due cose piccole:

- ⬜ **La colonna `python_topics.done` non la legge più nessuno** (fotografia delle spunte
  dell'admin al 19/08; il progresso vero è in `python_progress`). Toglierla è una
  migrazione: va con §5.3
- ⬜ **Il proprietario non si può cambiare da interfaccia** — oggi solo dal DB. Non è stato
  chiesto

I dati condivisi (catalogo, regulation, mosse, oggetti, abilità) **non** hanno un
proprietario e non devono averlo: li protegge §1.2.

### 1.2 ✅ Gli editor Pokémon solo per gli admin — chiuso il 17/08/2026

30 route su 36 solo per un amministratore (`APERTE_A_TUTTI` in `blueprints/pokemon.py`).
La regola è nelle trappole.

### 1.3 🟨 Aggiungere dati dalla web app

Chiuso tutto quello che era stato chiesto: import di una specie per nome con anteprima
(21/08), moveset, spunta «aggiungi anche a…», validazione, regulation nuova
dall'interfaccia (10/09). Le regole che restano sono nelle trappole. Aperto:

- ⬜ **Una regulation che non sia basata su Champions o sui giochi principali** non ha una
  terza sorgente di mosse da scegliere, perché nel dump non c'è (§2.3). È dato, non codice
- ⬜ **Gli `overrides` del filtro** si scrivono a mano nel JSON, per decisione del
  14/09/2026: oggi valgono `{}` in tutte le regulation, e un editor si fa quando serviranno

### 1.4 ✅ Esportare tutto il DB — chiuso il 22/09/2026

`esporta_dati.py` (11 tabelle su 13, senza password, committato) e `--completo --uscita`
(con gli hash e `regulations`, mai dentro un repo); il ritorno è `importa_dati.py`. Tema e
lingua seguono l'utente (colonne `tema` e `lingua` in `users`). Fuori da entrambi, di
proposito: `fanta_players` (si rifà con `importa_listone.py`) e `game_releases` (la cache
IGDB, si rifà col pulsante). Le regole del ripristino sono nelle trappole.

### 1.5 🟨 Mettere l'app online

> **Aggiornato il 23/09/2026 da Davide**: per ora non si mette online niente. Quando
> succederà, **solo sulla sua rete di casa**, al massimo con strumenti come **Railway**. ⚠️
> Railway era stato escluso dal vincolo «gratis» (il disco persistente si paga): se torna in
> gioco, il vincolo va riconfermato con lui, non dato per caduto.

**I due vincoli, posti da Davide il 12/08/2026**: (1) **i dati degli utenti restano
salvati, sempre** — una soluzione che al riavvio riparte pulita è esclusa; (2) **gratis**.
⚠️ Il vincolo 1 va **verificato, non creduto**: salvare qualcosa, riavviare il servizio,
ricontrollare che ci sia ancora. Il filesystem effimero non dà errore, la pagina dice
«Salvato» lo stesso.

| | Strada | Esito |
|---|---|---|
| 1 | **PythonAnywhere, piano gratuito** | ✅ la candidata: filesystem persistente, nessun letargo. Limiti: una sola web app, quota CPU giornaliera, **rinnovo a mano ogni tre mesi** |
| 2 | Railway / Render / Fly con un volume | ❌ ~5 $/mese, esclusa dal vincolo «gratis» (vedi sopra) |
| 3 | **PC di casa con un tunnel Cloudflare** | 🟨 la riserva: gratis, i dati non si spostano, davanti Cloudflare Access. Il prezzo: il PC resta acceso |

✅ Le quattro cose da fare prima di esporre qualunque cosa sono chiuse il 21/08/2026
(debugger solo con `HUB_DEBUG=1`, `SECRET_KEY` in `data/secret_key.txt`, niente
`admin/admin123` nel login, `requirements.txt` vero, `wsgi.py`). ⚠️ `wsgi.py` va servito con
**un worker solo** finché le scritture concorrenti sui JSON restano senza lock.

**⬜ Aperto:**

- **Quale strada**, e poi il collaudo del vincolo 1
- **I 20 punti che scrivono file su disco** mentre l'app gira (in `blueprints/` ed
  `extensions.py`, più `hub.db`): il vero motivo per cui l'app non si sposta da sola. Da
  spostare: `data/` versionato pesa 7,3 MB, `data/cache/` (84 MB) si rigenera
- **Le chiavi su Debian** (segnato da Davide il 24/09/2026): un domani l'hub girerà su
  Debian, e le chiavi non potranno stare in variabili d'ambiente di Windows (`setx`, e il
  registro che il Fantacalcio legge per `FOOTBALL_DATA_API_KEY`). Oggi dall'ambiente si
  leggono `SECRET_KEY`, `STEAM_API_KEY`, `STEAM_ID`, `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`,
  `HUB_DEBUG`, `HUB_HOST`, `HUB_PORT`, `FOOTBALL_DATA_API_KEY` e `FANTA_CARTELLA_DOWNLOAD`
  (facoltativa). Una strada già usata è quella di `SECRET_KEY`: un file in `data/` escluso
  da git. Qualunque cosa si scelga **resta fuori dal repository** (i termini di
  football-data.org lo chiedono, §6.1) e fuori da `hub_export.json`
- ⚠️ **L'esecuzione di codice sul PC** (sezione Python, §4.10): chi è amministratore esegue
  codice Python col Python e i permessi dell'hub, e quel codice può leggere `hub.db`, la
  chiave di sessione, tutto il disco. In casa è quello che Davide ha chiesto; **online no**:
  prima di esporre l'hub, `HUB_ESEGUI_CODICE=0` o un ripensamento (un container, un utente
  del sistema senza permessi). Nel browser (Pyodide) il problema non c'è
- **L'export deve girare da solo sul server**: oggi `esporta_dati.py` lo lancio io a mano,
  e «persistente» non vuol dire «al sicuro»
- **Contemporaneità**: SQLite regge; i **JSON scritti a mano no** (trappola sulle scritture
  concorrenti). Le cache in memoria seguono l'mtime

**I termini d'uso delle fonti, letti il 23/09/2026** — non un parere legale:

- **fantacalcio.it**, art. 3: vieta programmi o meccanismi automatici per copiare o accedere
  alle pagine (scraping compreso); art. 9: a fini personali si può solo **visualizzare**.
  ✅ Dal 25/09/2026 nessun programma dell'hub legge il sito (§4.6). Il riquadro delle
  probabili sta nell'uso personale **finché lo guarda solo Davide**: mostrato ad altri
  utenti no
- **Serebii**: nessun termine pubblicato, «All Content is © Copyright of Serebii.net»;
  `robots.txt` non blocca le pagine che leggiamo. Leggerle per uso personale va bene,
  **ripubblicarle** no
- **Bulbapedia**: testo CC BY-NC-SA, uso non commerciale con attribuzione

### 1.6 ⬜ Due guide: com'è fatto, e come si riparte da un PC nuovo

Da fare **dopo** il collaudo (§5): documentare un'app che sta per cambiare vuol dire
riscrivere la guida due volte.

**I documenti che ci sono, e si contraddicono**: `DOCUMENTAZIONE_PersonalHub.md` (ferma al
07/08/2026, «v16.2»), `PROJECT_CONTEXT.md`, `README.md` («v11.1a»), `README-GitHub.md` (la
vetrina), `howtouse.txt` (appunti). Due numeri di versione sullo stesso progetto: il
problema è **decidere chi dice cosa** e buttare i doppioni.

> ⚠️ **`DOCUMENTAZIONE_PersonalHub.md` dice cose false** (misurato il 18/09/2026): elenca
> come «mai implementate» tre route che esistono (solo `/api/stat_champions` manca
> davvero), dà come voce più grossa il «DB Pokedex completo» già fatto, e descrive i dati
> per regulation come prima della migrazione al catalogo dell'11/08. È il punto di
> partenza della guida n. 1, ma **va riscritto leggendo il codice**, non aggiornato a toppe.

⚠️ `howtouse.txt` indica una cartella che non è questa e scrive la password in chiaro.

**Cosa la guida n. 2 deve dire**: Pyodide non è in git e si scarica con
`python scripts/scarica_pyodide.py` (senza, «Esegui nel browser» non c'è); i file della
Stampa 3D (`data/stampa3d/`) vanno copiati a mano; le password non rientrano dall'export normale (si entra
come `admin` con la password del primo avvio, le altre da `/utenti`); `data/cache/` si
rigenera, e il primo import sembra bloccato mentre scarica; `admin123` è il seme di
`init_db()`, non va propagato e va cambiato al primo accesso.

**Come dovrebbero essere fatte**: la n. 1 è **per Davide fra sei mesi** — deve spiegare
*perché* (catalogo unico, chiavi che non si rinominano, lingua in un cookie). La n. 2 è
una sequenza di comandi **eseguibile alla lettera**, provata su una macchina pulita, e
la prova finale è la regola #8.

---

## 2. I lavori a metà

### 2.1 ✅ Switch lingua — chiuso il 13/08/2026 (Pokémon e Gaming)

Le altre sezioni restano in italiano **per scelta**. Le regole sono nelle trappole;
`python scripts/controlla_traduzioni.py` trova mancanti, vuote, orfane e doppie.

### 2.2 ✅ Le abilità da fondere — chiuso il 10/09/2026, erano già fuse

La rete è `python scripts/controlla_abilita.py` (oggi 0 orfani, 0 doppioni, 10 voci
attive irraggiungibili: le abilità di Champions decise fuori — se il numero cresce, un
effetto è finito dalla parte sbagliata). ⬜ Il fallback `data/abilities.json` non è
riallineato (ha ancora `Megasolar` inerte): va con §5.3.

### 2.3 ⬜ Mosse per regulation — quello che richiede una fonte

Il meccanismo è chiuso; dove manca il dato, manca la **fonte**:

- ⬜ **La differenza fra M-A e M-B**: nel dump c'è un solo version group `champions`, quindi
  se le due regulation **bandiscono** mosse diverse, quella differenza non è in nessun dato
  che abbiamo. (MA 492 e MB 494 differiscono per il **roster**, non per un divieto)
- **Le 9 Mega di Leggende Z-A** (Darkrai, Heatran, Zeraora, Zygarde Complete, le due
  Magearna, i tre Tatsugiri) restano senza lista, ed è **giusto**: sono reali ma in
  Champions non ci sono
- ⬜ **La prossima regulation**: M-C va dal 9 settembre al **2 dicembre 2026**. Se sarà
  basata su Champions: «crea regulation», «Confronta con le fonti», «Allinea», poi
  `allinea_mosse_regulation.py`. Se non lo sarà, non avrà un version group nel dump

Il metodo resta quello del roster: dove la fonte esiste si importa con uno script
rieseguibile che **si ferma su ciò che non risolve**; dove non esiste, il dato si lascia
mancante e **lo si dichiara**. Non si riempie a stima.

---

## 3. Bachi noti

| | Baco | Stato |
|---|---|---|
| ⬜ | **Due abilità senza effetto nel motore** | Trovate il 23/09/2026. **Affilama** (Sharpness, di Mega Absol Z) ha `effect: none` e dovrebbe potenziare le mosse **da taglio** — che hanno il flag `slicing`, quindi il motore potrebbe leggerlo. **Aura Guard** (Mega Lucario Z) è nuova e senza descrizione. Tutti e due i valori vanno presi da una fonte, non da memoria |

Tutti gli altri bachi elencati qui fino al 23/09/2026 sono chiusi: vedi `STORICO.md`.

---

## 4. Voci minori, per sezione

| Sezione | Voce |
|---|---|
| 💻 **PC Builder** | 🟨 Wishlist, prezzi, link ai negozi, avvisi, **compatibilità** e **novità del catalogo** fatti il 25/09/2026: vedi §4.7 |
| 🖨️ **Stampa 3D** | 🟨 Progetti con link, file allegati e inventario bobine **fatti il 25/09/2026**: vedi §4.8 |
| 🤖 **Arduino** | 🟨 Anteprima di Tinkercad e Wokwi, «nuovo circuito» e tabella dei piedini coi controlli **fatti il 25/09/2026**, e il baco del `href` senza controllo chiuso: vedi §4.9 |
| 🐍 **Python** | 🟨 Progetti con file (scritti, caricati, da GitHub), esecuzione nel browser e sul PC, note per argomento e frammenti **fatti il 25/09/2026**: vedi §4.10 |
| 💾 **Log** | ⬜ Aggiungere una funzione di salvataggio log |
| 🎨 **Grafica** | ⬜ `form-select` è usata da **4 tendine** (selettore di sezione in `arduino.html`, `gaming.html`, `pcbuilder.html`, `pokemon.html`) e non è definita da nessuna parte · ⬜ rivedere **lo scorrimento di sezioni e sottosezioni** (richiesta del 22/09/2026). ⚠️ Solo il Fantacalcio ha il `<form>` che avvolge header e footer della modale; in `arduino.html` e `pcbuilder.html` il form sta dentro `.modal-body` e lo scroll funziona, quindi la cura del Fantacalcio non va copiata a tappeto |

### 4.1 🟨 Gaming — il calendario delle uscite

Chiuso il 16-17/08/2026 (IGDB, piattaforme 4.1a, ricerca 4.1b, attesa 4.1c): vedi
`STORICO.md`. Il tetto delle 300 righe resta di proposito (senza, 3,3 MB e 4224 immagini).

- ⬜ **La cache va aggiornata una volta** perché il dato dell'attesa entri: fino ad allora il
  filtro è spento e la pagina lo dice. È un'azione di Davide
- ⬜ **La striscia in cima a `/gaming`** mostra le 6 uscite più vicine senza guardare
  l'attesa: se dà fastidio, `filtra_per_attesa` è già scritta
- ⬜ **Le soglie dell'attesa sono due numeri fissi** (2 e 10), scelti sui conti del 17/08:
  se in cache entrasse molto altro vanno rimisurate

### 4.2 ✅ Fantacalcio, la sezione di prima — tolta il 25/09/2026

Sostituita da quella che è nata come «Fantacalcio 2» (§4.6). Il testo lungo è in
`git show 85f8c03:BACKLOG.md`, §4.2.

### 4.3 🟨 Le richieste di Davide del 22/09/2026 «per il futuro»

Fatte: il pulsante che aggiorna il Pokédex, quello che confronta una regulation con le
fonti, gli sprite, i quattro temi, «resta collegato», il travaso fra utenti (vedi
`STORICO.md`). Aperto:

- ⬜ **Kingambit in M-C**: Serebii lo dà, Bulbapedia no. Resta nel roster, e «Confronta» lo
  ristampa. **Game8** come terzo voto non è ancora stato letto
- ⬜ **Proteggere l'accesso al GitHub** «per non farmi rubare il lavoro». La parte veloce è
  già vera: `controlla_esposizione.py` dice che né `hub.db` né la chiave di sessione sono
  versionati, e l'export è senza password. Il resto — repo privato, 2FA, chiavi di firma,
  chi ha accesso — va fatto **guardando insieme le impostazioni del repo**, non da qui

### 4.4 ⚠️ Quello che il timer della giornata dà per buono

Non è un baco: è quello che può smettere di funzionare senza dare errore.

- La scadenza è `fanta.scadenza()`: la prima partita della giornata corrente con l'**ora
  esatta** (`TIMED`, o già cominciata). La giornata è `fanta.giornata_corrente()`, la prima
  con una partita ancora da giocare, **rinviate escluse**. Se nessuna partita ha l'ora
  esatta, il timer **dichiara di non saperla** e conta le altre in `senza_ora`. La
  Dashboard usa la stessa funzione e non richiama l'API.
- ⚠️ `SCHEDULED` su football-data.org vuol dire data **approssimativa**: fidarsi solo di
  `TIMED`, altrimenti è una scadenza inventata.
- ⚠️ «Un giorno» (`fanta.VECCHIO_CALENDARIO`) è una soglia scelta, non misurata; il ritardo
  del piano gratuito («Schedules delayed») non è misurato (§4.6).

### 4.5 ✅ Il punto cieco di `controlla_proprietario.py` — chiuso il 22/09/2026

Quello che serve a chi tocca lo script è nelle trappole.

### 4.6 🟨 Il Fantacalcio con le fonti in regola — dal 25/09/2026 è l'unica sezione

> Decisione di Davide del 23/09/2026: «voglio evitare problemi». Provata come «Fantacalcio
> 2» il 24/09 accanto alla vecchia, scelta il 25/09: la vecchia è tolta e la 2 ne ha preso
> nome, route (`/fantacalcio`), permesso, file e tabelle (`fanta_*`). La fusione del DB la fa
> `extensions._unisci_fantacalcio()` in `init_db()`, una volta sola, con la copia in
> `data/archive/hub_pre-unione-fantacalcio.db`. Il testo lungo delle verifiche del 24/09 è in
> `git show 513c082:BACKLOG.md`, §4.6.

**Le decisioni di Davide che valgono** (21-25/09/2026): due leghe, tutte e due **Classic**
(il Mantra non serve); regole **in colonne**, gol +3 per tutti; **una formazione per lega**,
che si sovrascrive (niente storico, quindi non si può misurare se il consiglio consigliava
bene); chi esce dalla rosa esce anche dal campo; l'avversario **si mostra e non si pesa**;
le probabili sono **un link**, niente scelte titolare/dubbio; per gli Excel
**l'autorizzazione scritta non serve**; la **porta inviolata** del portiere non si cerca
(25/09/2026: «freghiamocene» — il file delle statistiche non la porta, e ricavarla dal
calendario darebbe un numero falso a ogni secondo portiere).

**Cosa c'è** — `fanta_fonti.py` (legge), `fanta.py` (logica), `blueprints/fantacalcio.py`, i
template `fantacalcio.html` e `fanta_*.html`, `scripts/importa_listone.py` e
`scripts/prova_fantacalcio.py`.

| Dato | Fonte | Come arriva |
|---|---|---|
| **Listone e statistiche** | i due Excel di fantacalcio.it | Davide li scarica **col suo login**; l'hub li trova nei download (entrando o con «Leggi i download»), li importa e li cancella — o dalla pagina, o con `importa_listone.py`. Letti in memoria, **mai salvati** e mai nel repository |
| **Calendario e classifica** | football-data.org, piano gratuito | con la chiave, da solo se la copia ha più di un giorno, o con «Aggiorna ora» |
| **Probabili** | nessuna | un **link** e un riquadro che le apre nel browser di Davide |

Il **consiglio** mette in fondo chi **di sicuro non gioca** (ceduto, squadra senza partita,
rinviata), poi ordina per **fantamedia della lega**, autogol compreso. La titolarità **non
la sa**, e lo dice. Il **modificatore di difesa** è il valore pieno.

**⬜ Resta aperto:**

- **Il ritardo del calendario gratuito** («Schedules delayed»): serve una partita spostata
  da veder arrivare
- **I ruoli Mantra** sono nel DB e non li legge nessuno (le leghe sono Classic)
- ⚠️ **Gli Excel dai download, su Debian**: la cartella la trova anche su Linux
  (`XDG_DOWNLOAD_DIR`), ma solo se browser e hub stanno **sulla stessa macchina**. Se l'hub
  diventa un server, serve una cartella condivisa (es. Samba) indicata con
  `FANTA_CARTELLA_DOWNLOAD`, altrimenti resta il caricamento dalla pagina. La chiave su
  Debian è la voce di §1.5

**Da sapere sulle fonti** (verificato il 24/09/2026):

- **Gli Excel**: l'`Id` è lo stesso del listone letto prima (597 su 597), quotazioni e
  statistiche identiche. Il file delle quotazioni ha un foglio **`Ceduti`** separato. Il
  ruolo Mantra è scritto `M;C`. `openpyxl` non serve: `fanta_fonti.leggi_xlsx()` usa
  `zipfile` e `xml`
- **football-data.org**: Serie A nel piano gratuito, **10 chiamate al minuto**, `utcDate` in
  UTC. `fanta_fonti.ora_italiana()` usa `zoneinfo` se c'è, altrimenti la regola dell'ora
  legale europea (su Windows senza `tzdata` `Europe/Rome` non si trova). Le squadre si legano
  col `shortName`, con due ritocchi: `Como 1907` → `como`, `Venezia FC` → `venezia`. I
  termini: **§7.1** chiede la scritta «Football data provided by the Football-Data.org API»
  nella pagina, **§6.1** la chiave fuori da ogni repository, **§9.1** chiusa l'iscrizione non
  si possono più mostrare i dati presi
- **Gli strumenti già esistenti non sono fonti utilizzabili**: fantacalcio-mcp legge
  fantacalcio.it e la sua API interna (e non ha licenza); Fantacalcio-PY fa scraping
  dichiarato di fantacalciopedia.com; FantaLab e Fantagoat non hanno API e ne vietano il
  riuso. Restano utili **come app** accanto all'hub

### 4.7 🟨 PC Builder — wishlist, prezzi e link ai negozi (25/09/2026)

Chiesto da Davide: il prezzo su Amazon, ePrice, BPM-Power; i prezzi di eBay per capire quando
conviene vendere i pezzi attuali; il confronto su Versus; un avviso quando cambia un pezzo in
wishlist. **Fatto il 25/09/2026**, numeri in `STORICO.md`: stato per componente (posseduto,
desiderato, venduto), prezzo con la **data** in cui l'hai scritto, soglia, valore da usato,
link ai negozi, confronto Versus fra posseduto e desiderato della stessa categoria, e il
riquadro «Da guardare» all'apertura. Logica in `pc_negozi.py`, prova `prova_pcbuilder.py`.

**Le fonti, lette il 25/09/2026** — il motivo per cui l'hub costruisce link e non legge prezzi:

| Fonte | Cosa dice | Scelta di Davide |
|---|---|---|
| Amazon | Condizioni d'uso: vietati «data mining, robot o simili strumenti» senza consenso scritto. L'API (Creators API, dal maggio 2026 al posto della PA-API) solo per affiliati con 10 vendite in 30 giorni. Keepa API da 49 €/mese | link |
| ePrice | Il contratto di vendita non ne parla; `robots.txt` permette le pagine prodotto, vieta `/search/`. Feed su Awin, per affiliati | link (la lettura della pagina prodotto era possibile, scartata) |
| BPM-Power | verifica anti-bot di Cloudflare: non si aggira | link |
| eBay | API Browse gratis, ma **solo annunci attivi**; i venduti (Marketplace Insights) chiusi ai nuovi. La licenza vuole dati vecchi al massimo 6 ore e vieta, senza permesso, il prezzo medio di vendita **di una categoria** | link (attivi e venduti). L'API **rimandata** |
| Versus | vieta di copiare o riusare i contenuti; nessuna API, solo affiliazioni | link |

**⬜ Resta aperto:**

- ⚠️ **L'avviso di prezzo si imposta dentro Keepa** (account gratuito, «Traccia prodotto»),
  non nell'hub: l'API di Keepa costa 49 €/mese
- ⚠️ **L'ASIN di OpenDB è copiato su tutti i 15 canali Amazon** (12 118 pezzi per ognuno, tutti
  `verified`): non è la prova che il prodotto esista su amazon.it. Aperti a mano **12 su 12
  giusti**, ma è un campione. Se un link Amazon «dal catalogo» apre il prodotto sbagliato o
  una pagina vuota, si incolla quello vero, che vince sempre. Copertura: 83% delle CPU, 47%
  delle GPU, 39% delle schede madri, 32% degli alimentatori
- **`GIORNI_PROMEMORIA = 14`** è una soglia scelta, non misurata: si cambia in un punto solo,
  in `pc_negozi.py`
- **L'intervallo di prezzo degli usati da eBay** (API Browse, con account sviluppatore gratuito
  e chiave fuori dal repo): rimandato da Davide, «prima solo i link»
- **Notifiche vere** (email, telefono, a PC spento): per Amazon le fa Keepa, per eBay le
  ricerche salvate. L'hub avvisa solo quando lo apri
- ⚠️ **Le novità del catalogo sono rispetto all'aggiornamento precedente**, non «da quando le
  hai guardate»: premere «Aggiorna catalogo» due volte di fila e la seconda dice «niente di
  nuovo», perdendo l'elenco della prima. E «entrato» vuol dire aggiunto a OpenDB, non uscito
  sul mercato: l'anno c'è per l'88% delle CPU, il 31% delle GPU, il 4% degli alimentatori

**✅ La compatibilità, fatta il 25/09/2026** (numeri in `STORICO.md`). Fonte: **BuildCores
OpenDB**, licenza ODC-By 1.0, scaricata col pulsante «Aggiorna catalogo» (zip da 46 MB, indice
da 3,9 MB in `data/cache/`). Scartati UserBenchmark (ne vieta ogni uso senza permesso) e
PCPartPicker (nessuna API: quella che circola è scraping). Ogni pezzo si **collega** al suo
modello dal modulo; i controlli (dodici, più «Più kit di RAM insieme», dal 25/09 anche
connettori GPU e slot M.2) girano sulla configurazione **dopo gli acquisti** e
dicono ✓ / ✗ / non noto / da verificare, con la percentuale sui soli verificabili. Scelte di
Davide: elenco più percentuale, alimentatore a **+30%** sulla somma dei TDP, aggiornamento a
pulsante. Logica in `pc_catalogo.py`.

**⬜ Della compatibilità resta:**

- **Quello che il catalogo non sa**, ed è dichiarato a schermo: l'altezza massima del
  dissipatore c'è solo per **1 case su 3** (36%), l'altezza dei dissipatori per il 70%;
  **LGA 1151** dà «da verificare» (due generazioni incompatibili sullo stesso socket), e su
  **AM4** una CPU recente può chiedere un BIOS aggiornato, che nessun dato dice. Negli slot M.2
  il dump è **avaro** di misure e del supporto SATA (per questo più corto o SATA è «da
  verificare»), e 751 schede su 3701 non hanno slot M.2 indicati; gli zeri nei connettori di
  GPU e alimentatori sono quasi sempre dati mancanti
- **Non controllati**: la velocità degli slot M.2 (un PCIe 5.0 in uno slot 4.0 va, più lento),
  le porte SATA che alcune schede spengono usando un M.2, i connettori EPS della CPU. Il
  campo `storage_devices` delle schede non è usabile: la B450 Prime Plus vi ha **0** porte SATA
- **Più GPU, case, alimentatori…**: si controlla il primo e la pagina lo dice. Si sommano solo
  SSD e kit di RAM

### 4.8 🟨 Stampa 3D (25/09/2026)

Chiesta così nel docx: «come quella per Arduino, si riesce a richiamare un sito per
disegnare? Vorrei salvarmi i progetti». Davide comprerà una **Bambu Lab**, disegnerà da
**MakerWorld** (anche modificando modelli esistenti) e ha voluto file allegati e un
inventario delle bobine. Fatto: numeri in `STORICO.md`, logica in `stampa3d.py`, prova
`prova_stampa3d.py`.

**Le fonti, lette il 25/09/2026**:

| Cosa | Cosa dice | Scelta |
|---|---|---|
| MakerWorld | Condizioni d'uso: vietati «robot, spider» e ogni strumento automatico per accedere o copiare. Nessuna API pubblica | link (e la ricerca col nome, formato aperto a mano) |
| `bambustudio://open?file=` | Carica solo file dai domini di Bambu (elenco dentro lo slicer); su macOS non va | i file si **scaricano** e si aprono col doppio clic |
| Stampante in rete | Dal firmware di inizio 2025 i programmi esterni solo in «LAN Mode» + «Developer Mode» (MQTT, FTP, camera) | **aspetta la stampante** |
| Printables | Cloudflare davanti anche alla ricerca | solo link incollati, nessuno costruito |

**⬜ Resta aperto:**

- **Lo stato della stampante** (avanzamento, temperature, bobine dell'AMS) quando la
  stampante arriva. Da verificare **su quella stampante**, non da documentazione: modello,
  firmware, e se Davide vuole accendere la Developer Mode (toglie l'autorizzazione di Bambu
  sulla rete di casa, ed è una scelta sua). Con l'AMS l'inventario potrebbe leggere i
  grammi invece di scalarli a mano
- ✅ **L'anteprima 3D** è fatta (25/09/2026, `STORICO.md`). ⬜ Resta da provarla con **un
  .3mf vero di MakerWorld o di Bambu Studio**: la struttura (sotto-modelli in
  `3D/Objects/`) è stata provata su un file costruito a imitazione, non su uno vero. Se un
  file vero non si apre, il messaggio a schermo dice perché. ⚠️ three.js è **fissato** alla
  0.186.1 in `static/vendor/three-0.186.1/`: aggiornarlo vuol dire cambiare la cartella
  **e** l'importmap in `stampa3d.html`, e `prova_stampa3d.py` §10 controlla che ogni
  nome porti a un file
- ⚠️ **I file non sono nell'export**: su un PC nuovo la cartella `data/stampa3d/` va
  copiata a mano, e la guida n. 2 (§1.6) lo deve dire. Senza, le righe dicono «file
  mancante»
- **Soglie scelte, non misurate**: 200 MB per file (`MAX_BYTE`), 150 g per «quasi finita»
  (`SOGLIA_BOBINA_G`), in `stampa3d.py`
- **La Dashboard** non ha un riquadro della Stampa 3D: non chiesto

---

### 4.9 🟨 Arduino: Tinkercad, Wokwi e i piedini (25/09/2026)

Nel docx: «richiamo a Tinkercad per poter disegnare il progetto e vedere se i connettori
ecc. sono funzionanti». Davide ricordava un editor che **simula** il progetto: sono
Tinkercad Circuits e Wokwi. Scelte sue: tutti e due; la tabella dei piedini **non a mano**
ma dal `diagram.json` di Wokwi incollato; le schede «non lo so», quindi i controlli ci
sono per quelle che Wokwi simula e che stanno nell'elenco (Uno, Nano, Mega, ESP32).
Numeri in `STORICO.md`, logica in `arduino_circuito.py`, prova `prova_arduino.py`.

**Le fonti, lette il 25/09/2026**:

| Cosa | Da dove |
|---|---|
| Piedini e segnali di schede e componenti | sorgente di **wokwi-elements** (MIT): è quello che usa il simulatore |
| GPIO dietro i piedini delle ESP32 | `board.json` di **wokwi-boards** (DevKitC V4 e DevKit V1) |
| Limiti dei GPIO ESP32 (solo ingresso, flash, avvio, ADC2) | tabella «GPIO Summary» di **ESP-IDF** |
| I2C predefinito ESP32 (21/22) | `pins_arduino.h` del core **Arduino-ESP32** |

⚠️ **`data/arduino_piedini.json` è derivato**: si rifà con `python scripts/importa_piedini_wokwi.py`
(con `--dry-run` e `--rileggi`), non si modifica a mano. Lo script si **ferma** se i
controlli incrociati non tornano (PWM di Uno e Mega contro la documentazione, frase su A6/A7
della Nano, 34 GPIO di Espressif, PWM e I2C della DevKit V1 contro il suo elemento). Al primo
giro l'incrocio ha preso il D15 della DevKit V1, scritto `"15"` invece di `"GPIO15"` nella
fonte: sarebbe rimasto senza segnali in silenzio.

**⬜ Resta aperto:**

- **Provarlo nel Chrome di Davide**: nel pannello di Claude gli iframe di Tinkercad e Wokwi
  restano bianchi senza nemmeno partire (lo stesso limite del Fantacalcio). Tinkercad si
  vede solo se il circuito è **pubblico**
- **Tinkercad non dà la tabella dei piedini**: non ha un `diagram.json` da incollare
- **Schede senza controlli**: Leonardo, Pro Mini, ESP8266 (Wokwi non le simula),
  Raspberry Pi, e nell'ESP32 le varianti S2/S3/C3 (i dati sono della ESP32 classica)
- **Controlli che non ci sono**: il LED senza resistenza, la corrente per piedino, la
  direzione (un LED è un'uscita, ma i componenti Wokwi non lo dichiarano: per questo su
  34-39 dell'ESP32 l'avviso è generico), i pull-up
- ⚠️ **Wokwi con un modello che non esiste apre un progetto Uno, senza dirlo**:
  `/projects/new/scheda-che-non-esiste` ha il titolo «New Arduino Uno Project». I quattro
  indirizzi di `WOKWI_NUOVO` sono stati aperti uno per uno (titolo e `diagram.json`): uno
  nuovo va aperto allo stesso modo, non indovinato

---

### 4.10 🟨 Python: progetti, esecuzione, note e frammenti (25/09/2026)

Nel docx: «uno spazio dove inserire tutti i miei progetti e testarli» e «pensare a cosa
posso integrare per renderlo più figo». Scelte di Davide: file **scritti, caricati e da
GitHub**; il codice gira **sul PC dell'hub** e, comodo, **anche nel browser**; delle idee
proposte, le **note per argomento**, la **prova al volo** e i **frammenti** (non il legame
progetto↔argomenti). Numeri in `STORICO.md`, prova `prova_python.py`.

| Pezzo | Dove |
|---|---|
| Esecuzione sul PC (solo admin, 30 s, output tagliato, niente variabili d'ambiente dell'hub, albero dei processi chiuso) | `python_esegui.py`, route `/python/esegui` |
| Esecuzione nel browser (Pyodide 314.0.7 in un Web Worker, pacchetti dal CDN al primo import) | `static/js/python-worker.js`, `python-esegui.js`, `scripts/scarica_pyodide.py` |
| File: caricamento, zip, GitHub (API `zipball`, repository pubblici, 60 richieste/ora) | `python_sorgenti.py` |
| Il pannello «Esegui» uguale ovunque | `templates/_python_esegui.html` |

**⬜ Resta aperto:**

- ⚠️ **Online l'esecuzione sul PC va spenta** (`HUB_ESEGUI_CODICE=0`): vedi §1.5
- **Nel browser non c'è tutto**: niente file del PC, niente finestre (tkinter), la rete solo
  verso chi la permette; i pacchetti che Pyodide non ha non si installano. Per quello c'è il PC
- **Il tempo massimo (30 s) e i limiti** (200 000 caratteri di output, 50 file, 3 MB per
  progetto) sono scelti, non misurati: `python_esegui.py` e `python_sorgenti.py`
- **GitHub importa il ramo predefinito** e solo repository pubblici; non si **spinge** niente
  su GitHub (sarebbe un token da custodire: non chiesto)
- **Il legame progetto↔argomenti** (idea «a»): proposto, non scelto
- **L'editor è un `<textarea>`**: niente colori della sintassi né completamento. Un editor
  vero (CodeMirror) sarebbe un'altra libreria in `static/vendor/`

---

## 5. 🏁 Il giro di collaudo finale (va fatto **per ultimo**)

**Questa voce si chiude dopo tutte le altre.** Qui i bachi peggiori non hanno mai dato
errore — il PC Builder inerte per settimane per un apice di troppo, il Ripristina che
sovrascriveva senza chiedere, lo Speed Tier che ricadeva su una lista statica — e un
lavoro fatto dopo può rimetterli in piedi.

⚠️ **Prima di iniziare**: `graphify-out/` va rifatto (`/graphify . --update`)
**obbligatoriamente** prima di 5.1 e 5.3. L'ultimo giro è del 21/09/2026 (1321 nodi, 2291
archi), e da allora è cambiato molto (M-C, il Fantacalcio intero).

### 5.1 ⬜ Il giro completo della web app

Ogni sezione, ogni pagina, **ogni campo e ogni funzione** — non un campione sulle cose
toccate di recente.

- **ogni campo di ogni form**: vuoto, valore limite, valore assurdo, caratteri strani —
  apostrofi e accenti sono la classe di bug che ha ucciso il Ripristina
- **ogni pulsante e ogni azione**: creazione, modifica, eliminazione, ripristino, import,
  export — e la conferma dove deve esserci
- **le due lingue** su tutte le pagine Pokémon
- **tutte le regulation**, non solo `ma`: `pokedex`, `mb` e `mc`
- **il calcolatore in tutti e quattro i tab**, con la regola #8 come pietra di paragone
- lo **sweep** su ogni blocco `<script>` e ogni handler inline, **e** le pagine caricate
  davvero, contando le righe che compaiono
- le sezioni che ricevono meno attenzione: Gaming, Arduino, PC Builder, Python, Fantacalcio

L'esito va scritto qui con i numeri: quante pagine, quanti campi, quante anomalie e quali.
Le anomalie fuori scope si segnalano, non si correggono al volo.

### 5.2 🟨 Le mosse assegnate sono davvero quelle giuste?

La lista `champions` è confrontata con Bulbapedia dal 14/09/2026 e allineata alla 1.2.0 il
18/09 (Serebii e Game8 come seconda fonte dal 21/09); la lista `main` è curata dal 21/09
(`VG_FUORI_SERIE`). Numeri in `STORICO.md`, regole nelle trappole.

- ⬜ **Il campione di `main` contro Bulbapedia** si fa **solo se** `main` tornerà in uso:
  oggi non lo legge nessuna regulation, e le pagine learnset per generazione hanno una
  struttura diversa da quelle di Champions

### 5.3 ⬜ L'inventario di cosa non serve più

Va fatto alla fine: finché i lavori sono in corso, un file che oggi sembra morto può servire
domani.

- **template** — chi li renderizza? Anche blocchi Jinja, `{% include %}` e `{% block %}` che
  nessuno estende più
- **`static/js/` e `static/css/`** — chi li carica, e **quali funzioni non chiama nessuno**
  (già trovate `MEGA_DATA`, `PKMN_DB`, `calc_stat_champions()` e una `switchTab` duplicata:
  la classe esiste)
- **route Python** non raggiunte da nessun `url_for()`, link o `fetch()`
- **funzioni e helper** nei blueprint, in `data.py` e in `extensions.py` mai importati
- **gli script di `scripts/`** una tantum già consumati (`build_catalog.py`, gli `importa_*`
  ed `esporta_dati.py` restano perché rieseguibili)
- **i file di dati storici** — vedi la trappola in cima — compreso `data/abilities.json`,
  che ha ancora `Megasolar` inerte (§2.2)
- **la tabella `regulations` nel DB** (la scrive `init_db()`, non la legge nessuno), la
  colonna `python_topics.done` (§1.1) e ogni altra colonna che nessuna query legge più
- **immagini e asset** in `static/` non referenziati
- ✅ **il blocco `main` di `pokemon_moves.json` NON è codice morto**: decisione di Davide del
  21/09/2026 («la base dati di tutti i pokemon… deve comunque esserci per poter costruire
  facilmente una nuova regulation»). Chi farà l'inventario lo troverà non letto da nessuna
  regulation, e **non è una prova che sia morto**

Il metodo: **prima si misura, poi si propone.** Per ogni candidato serve la prova che non è
usato, e la rimozione si fa in un blocco suo, dopo il via libera di Davide — non insieme al
collaudo, così se qualcosa si rompe si sa quale dei due l'ha rotto.
