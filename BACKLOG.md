# 📋 BACKLOG — Personal Hub

> **Qui c'è solo ciò che è aperto.** Le voci chiuse stanno in [`STORICO.md`](STORICO.md),
> una riga per lavoro con la data e i numeri della verifica.
> Aggiornato: **13/08/2026**. Fonte storica: `Nuove implementazioni.docx` (verde = fatto).

Legenda: ⬜ da fare · 🟨 parziale · ⚠️ trappola nota, da rileggere prima di toccare la zona

**Indice**

1. [Le trappole che valgono ancora](#-le-trappole-che-valgono-ancora) — leggere prima di lavorare
2. [I sei blocchi aperti](#1-i-sei-blocchi-aperti)
3. [I lavori a metà](#2-i-lavori-a-metà)
4. [Bachi noti e non corretti](#3-bachi-noti-e-non-corretti)
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
| **Risoluzione per nome** | Due chiavi diverse possono avere lo stesso `nome_it`/`nome_en`, e il catalogo Pokémon cita le abilità col nome **inglese** mentre le chiavi sono italiane. Ogni confronto per nome va fatto con `risolviChiave()` / `_INDICE`, mai con un match esatto sulla chiave |
| **Fallback silenziosi** | Più di un baco qui non dava errore, dava il numero sbagliato: lo Speed Tier che ricadeva su una lista statica, `/api/moves` che leggeva il file di MA, un alias che rispondeva Mega Venusaur. Se un loader ha un ramo di riserva, va verificato **quale dei due** sta rispondendo |
| **Endpoint fantasma** | Tre volte il JS ha chiamato una risposta che nessuno aveva mai implementato (`/api/regulations`, `d.moves`, `d.regulation`), fallendo dentro un `catch` muto. Un `catch(e){}` vuoto qui è un baco in attesa |
| **Le Mega** | La firma «+75 HP» individua le voci convertite **specie per specie, non stat per stat**: su Froslass cinque valori su sei erano convertiti e uno no, e la regola applicata in blocco ha rotto proprio quello. E la conversione può partire da una forma diversa da quella di testa (Zygarde Complete) |
| **File storici** | `data/pokemon_catalog.json`, `roster_ma.json`, `moves_ma.json`, `items_ma.json`, `abilities.json` sono ancora lì come **fallback**, e `pokemon_catalog.json` contiene le Mega nella vecchia forma convertita. Si dismettono al collaudo finale, non prima |
| **Scritture concorrenti** | `salva_catalogo()` riscrive il file intero **senza lock**: due salvataggi nello stesso istante non danno errore, l'ultimo vince e l'altro si perde. Rilevante appena l'app va online |
| **`t` come variabile** | `{% for t in … %}` in `moves_editor.html:97,153` e `regulation_editor.html:215` **ombrerebbe la funzione `t()`** delle traduzioni. Vanno rinominate quando si traducono quei due file |
| **`|tojson` negli attributi** | `|tojson` rende `"pokedex"` **con le doppie**: dentro un attributo delimitato dalle doppie, l'attributo si chiude a metà. Usare gli apici singoli |
| **Default del DB** | `extensions.py:143` crea la colonna con `regulation_id TEXT DEFAULT 'ma'`. Non è un residuo dei 14 letterali tolti l'11/08: è il default del **DB**, e cambiarlo richiede una migrazione. Oggi non fa danno perché `_team_upsert()` passa sempre un valore esplicito |

---

## 1. I sei blocchi aperti

Tutti aperti il 12/08/2026, tutti **misurati sul codice, non ipotizzati**. L'ordine
consigliato è quello in cui sono scritti: 1.1 e 1.2 sono due metà della stessa domanda —
*di chi* sono i dati e *chi* può cambiarli — e 1.5 dipende da entrambe.

### 1.1 ⬜ I dati non hanno un proprietario

**Trovata da Davide provando la web app.** Un team Pokémon salvato da un utente **lo
vedono tutti**, e lo stesso vale per giochi, progetti Arduino e build PC. I permessi per
sezione decidono **quali sezioni** vedi, non **di chi sono i dati** dentro.

Serve: ogni riga sa chi l'ha creata · ogni utente vede solo le proprie · l'**admin vede
tutto**, con scritto accanto chi ha inserito cosa e un filtro per utente.

**Quanto costa, contato**: **68 query** toccano le tabelle di contenuto — `games` 29,
`teams` 10, `arduino_projects` 7, `pc_builds` 7, `python_topics` 6, `team_members` 5,
`pc_components` 4. Per blueprint: `gaming.py` 24, `dashboard.py` 22, `pokemon.py` 12,
`pcbuilder.py` 7, `arduino.py` 4, `python_tracker.py` 3.

**Le decisioni da prendere prima di partire:**

1. **Dove mettere il proprietario**: solo sulle quattro tabelle radice (`games`, `teams`,
   `arduino_projects`, `pc_builds`); `team_members` e `pc_components` lo ereditano con una
   join. Metterlo anche sui figli sarebbe un dato ripetuto che può divergere
2. ⚠️ **`python_topics` è il caso storto**: non è contenuto dell'utente, è un elenco fisso
   di 53 voci seminato da `init_db()`, con la spunta `done` sulla riga stessa. Servono o 53
   righe per utente, o — meglio — una tabella `python_progress(user_id, topic_id, done)`
3. **Le righe esistenti**: assegnarle ad `admin` è l'unica scelta che non perde niente, ma
   va fatta in una migrazione dichiarata
4. ⚠️ **Come non lasciare buchi**: con 68 query, dimenticarne una significa mostrare i dati
   di un altro **senza che nulla lo segnali**. Serve un meccanismo che **fallisca chiuso** —
   un helper obbligatorio, o un test che elenchi le query e verifichi che ognuna filtri —
   non `WHERE user_id=?` scritto a mano 68 volte

Da fare in un blocco suo. Si verifica creando due utenti e provando che nessuno veda le
cose dell'altro.

### 1.2 ⬜ Gli editor Pokémon solo per gli admin

Chi ha la sezione `pokemon` fra le proprie vede **tutto** ciò che sta sotto `/pokemon/*`,
quindi può aprire catalogo, mosse, oggetti, abilità, roster e gli editor di regulation e
**scrivere sui dati condivisi da tutti**: sono **28 route** in `blueprints/pokemon.py`.

- il modello esiste già: `solo_admin` in [admin.py:28](blueprints/admin.py:28), agganciato
  con un `before_request` **a tutto il blueprint** perché «una route nuova nasce protetta»
- ⚠️ ma `/pokemon` **non** si può bloccare in blocco: mescola le pagine d'uso (team,
  calcolatori, Speed Tier) con gli editor. Serve un elenco, e va fatto **al contrario di
  come viene istintivo**: non la lista del vietato, che **fallisce aperto** sulla prossima
  route che qualcuno aggiunge, ma la lista di ciò che è **permesso a tutti**
- **le API vanno protette insieme alle pagine** (`/api/catalogo/<db>/salva`, `/elimina`,
  `/api/abilities/update`, `/api/regulations/save`…): nascondere il pulsante non protegge
  niente
- **e poi anche il pulsante**: i 7 collegamenti agli editor in `pokemon.html`. `e_admin` è
  già in ogni template dal context processor, quindi è una riga — ma è **cosmesi**, dopo il
  controllo vero e non al posto suo

Si verifica con due account, **chiamando direttamente** una route di scrittura col secondo.

### 1.3 ⬜ Aggiungere dati dalla web app, senza passarmi dal mezzo

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

**Cosa manca davvero, in ordine di rischio:**

1. ⚠️ **Il moveset è il buco vero.** `data/catalog/pokemon_moves.json` **non** è tra i
   `DB_CATALOGO` ([pokemon.py:71](blueprints/pokemon.py:71)) e nessuna pagina lo tocca: lo
   scrive solo `scripts/importa_mosse_specie.py`. Una specie aggiunta a mano nasce **senza
   mosse legali**, e la tendina esce vuota **senza dire perché**. Qualunque forma prenda
   l'import, deve dare le mosse alla specie nuova o **dichiarare a schermo** che non ne ha
2. **L'import in blocco**, che è la richiesta letterale: oggi si può fare solo dagli script.
   Serve decidere la forma (incollare JSON, caricare un file, pescare da PokéAPI per nome) e
   in ogni caso riusare `salva_catalogo()` / `_save_abilities()`
3. **Le regulation non-`pokedex`**: o si offre un «aggiungi anche a…» al salvataggio, o si
   accetta il doppio passaggio — ma allora va **scritto a schermo**
4. **Validazione, oggi assente**: `/api/catalogo/<db>/salva` accetta qualunque oggetto, il
   solo controllo è `isinstance(voce, dict)` ([pokemon.py:756](blueprints/pokemon.py:756)).
   Senza `base_stats` il calcolatore sbaglia i conti, senza `nome_it`/`nome_en` lo switch
   lingua non ha cosa mostrare
5. **Chi può farlo**: è scrittura su dati condivisi, da incrociare con 1.1 e 1.2

Nessuno dei cinque punti è deciso: la voce è aperta, non progettata.

**Voce collegata** (dal docx): ⬜ *creare i JSON di una regulation nuova dalla web app* —
roster, mosse, oggetti e abilità generati in autonomia. Obiettivo di fondo: **aggiungere
una regulation senza IA, solo da interfaccia**.

### 1.4 ⬜ Esportare tutto il DB, utenti e personalizzazioni comprese

> Precisazione di Davide: «con esportazione db intendo anche esportare tutto il resto».
> **Quella parte c'è già.** Contato sul DB vero: 33 giochi, 1 team con 1 membro, 1 build PC
> con 5 componenti, 53 argomenti Python, 2 utenti, tutto in `data/backup/hub_export.json`.

`scripts/esporta_dati.py` copre **8 tabelle** e degli utenti esporta tutte le colonne
tranne `password` — quindi **i permessi per sezione ci sono già**, stanno in
`users.sections`, che è una colonna e non una tabella a parte.

**Le tre falle, misurate sul DB vero:**

1. ⚠️ **Una tabella su nove non è nell'elenco**: `regulations` (1 riga) non è in `TABELLE`.
   Ma è una **tabella morta** — la scrive solo `init_db()` e non la legge nessuno, le
   regulation vivono in `data/regulations/*.json` dal 10/08. Da decidere: o entra
   nell'export, o si toglie dal DB con l'inventario del codice morto. Oggi è omessa **per
   caso**, non per scelta
2. ⚠️ **Manca il ritorno**: nessuno script rilegge `hub_export.json`. Un export senza import
   non è un backup, è un file che nessuno sa rimettere dentro. Serve
   `scripts/importa_dati.py` rieseguibile, con `--dry-run`, che dica **prima** cosa
   sovrascriverebbe
3. ⚠️ **Due personalizzazioni non sono nel DB**, quindi nessun export potrà mai prenderle:
   il **tema** è in `localStorage` e la **lingua** nel cookie `hub_lang`, entrambi per
   browser. Vanno su colonne di `users` se devono seguire l'utente — cioè esattamente
   quando l'app sarà online e la userai dal telefono e dal PC

**La decisione da prendere: due export, non uno.** Le password sono escluse di proposito
perché `hub_export.json` **viene committato**. Ma un backup vero le deve contenere. Quindi
`esporta_dati.py` resta com'è, e serve una modalità **`--completo`** che scriva tutto,
`regulations` e password comprese, in un file **fuori dal repo** — e che si **rifiuti** di
scrivere in una cartella versionata, unico modo perché la distinzione non salti per
distrazione.

Da incrociare con 1.5: online questo export deve girare **da solo sul server**.

### 1.5 ⬜ Mettere l'app online

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

⚠️ **Prima di esporre qualunque cosa, quattro cose trovate nel codice, nessuna opinabile:**

- `app.py` finisce con `app.run(host="0.0.0.0", debug=True, port=5000)`. Il debugger di
  Werkzeug su una porta pubblica è **esecuzione di codice da remoto**: serve un WSGI vero
  (`gunicorn` su Linux, `waitress` su Windows)
- `SECRET_KEY` ha come default `"dev-secret-change-me"`: chi conosce quella stringa **si
  firma da solo un cookie di sessione da admin**
- la pagina di login **stampa `admin / admin123`**: va tolto e la password cambiata
- `requirements.txt` ha una riga sola

**Sulla contemporaneità**: SQLite regge un uso come questo senza problemi. I **file JSON
scritti a mano no** — vedi la trappola sulle scritture concorrenti. Le cache in memoria
sono già sull'mtime, quindi con più worker si comportano bene.

**E una rete sotto**: «persistente» non vuol dire «al sicuro». Un piano gratuito può
chiudere o essere sospeso, e oggi `esporta_dati.py` lo lancio io a mano da qui.

### 1.6 ⬜ Due guide: com'è fatto, e come si riparte da un PC nuovo

**Lo stato di fatto: i documenti non sono zero, sono cinque**, e in parte si contraddicono.

| File | Righe | Cos'è, davvero |
|---|---|---|
| `DOCUMENTAZIONE_PersonalHub.md` | 303 | La più vicina alla guida n. 1. **Ferma al 07/08/2026**, «v16.2» |
| `PROJECT_CONTEXT.md` | 656 | Dettagli tecnici, convenzioni, log delle sessioni. Aggiornato |
| `README.md` | 133 | Stack e struttura. Dice **«v11.1a»** |
| `README-GitHub.md` | 104 | La vetrina coi badge |
| `howtouse.txt` | 22 | Appunti a mano. È il germe della guida n. 2 |

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

- **`requirements.txt` ha una riga sola**, `flask>=3.0`, ma gli script usano `requests` e le
  password passano da `werkzeug.security`. Una guida che dice `pip install -r requirements.txt`
  **oggi mente**
- ⚠️ **il ripristino dei dati non esiste** (vedi 1.4): su un PC nuovo l'app riparte col DB
  che `init_db()` crea da zero — solo l'utente `admin`, e **niente** giochi, team, Arduino o
  build PC
- `data/cache/` (84 MB) si rigenera, ma va **detto**, altrimenti il primo import sembra
  bloccato mentre sta scaricando
- la password `admin123` sta nella pagina di login e in `howtouse.txt`: la guida nuova non
  deve propagarla

**Come dovrebbero essere fatte**: la n. 1 è **per Davide fra sei mesi**, non per un
estraneo — deve spiegare *perché* le cose stanno come stanno (perché il catalogo è unico,
perché le chiavi non si rinominano, perché la lingua è in un cookie), che è la parte che si
perde per prima. La n. 2 è una sequenza di comandi **eseguibile alla lettera**, provata su
una macchina pulita, e la prova finale è la regola #8.

Da fare **dopo** il collaudo (§5): documentare un'app che sta per cambiare significa
riscrivere la guida due volte.

---

## 2. I lavori a metà

### 2.1 🟨 Switch lingua — il secondo blocco, le stringhe dell'interfaccia

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

**Fatti 3 template su 11**: `pokemon.html` (16), `regulation_content.html` (15),
`catalog_editor.html` (23). Verifica: 14 pagine × 2 lingue rese 200, 69 chieste / 69
presenti / 0 mancanti, sweep 1587 pezzi sani.

⬜ **Restano 8 template (~380 stringhe)**: `calcolatori.html` più i 24 nei
`static/js/calcolatori-*.js`, `moves_editor`, `abilities_editor`, `items_editor`,
`regulation_editor`, `regulations_list`, `roster_editor`, `base.html`.

⬜ **Due cose da decidere con Davide:**

1. **La shell resta in italiano.** `base.html` (sidebar, «Esporta JSON», «Utenti») non è
   tradotta di proposito: il pulsante lingua compare solo sotto `/pokemon/*`, quindi
   tradurre la sidebar mostrerebbe l'inglese anche su Gaming e Arduino **senza un modo per
   tornare indietro** da lì. O si lascia così, o il pulsante torna su tutte le pagine
2. **`1 team salvati` → `1 saved teams`**: il plurale è sbagliato in entrambe le lingue (in
   italiano lo era già prima). Si sistema quando si decide se `tf()` deve gestirlo

⬜ **Due cose che lo switch non copre ancora:**

- **gli editor** (`/pokemon/catalogo`, roster, mosse, oggetti) mostrano ancora la **chiave**,
  non il nome tradotto. Lì la chiave è l'identità della voce, quindi va deciso se e come
  mostrarle entrambe
- **le descrizioni** sono solo in italiano: `desc` non è stato toccato, serve un secondo
  giro di import per i testi inglesi

> ⚠️ Conseguenza già visibile: in italiano il calcolatore scrive **`Privazione`, non
> `Knock Off`**, e `Cinturanera` invece di `Black Belt`. È quello che la voce chiedeva, ma
> se per abitudine VGC preferisci l'inglese anche in italiano si cambia in un punto solo
> (`nomeVis`).

### 2.2 ⬜ Le 103 abilità da fondere — gli effetti stanno dalla parte sbagliata

24 coppie sono state fuse l'11/08 (415 → 391 voci). **Restano 103 voci**, e il problema
**non è di traduzione**: la wiki ne recuperava solo 5, confermando che sono identiche nelle
due lingue.

Delle 103: **69** hanno `effect: {"type": "none"}` — sono le abilità inventate e i
placeholder, ed è giusto che non abbiano un nome ufficiale. **34** hanno un effetto vero, e
**7 di queste hanno un blocco `effect` identico a una voce ufficiale già in catalogo**
(`Erboristeria` ↔ `Erbaiuto`, `Torrente`/`Torrentismo` ↔ `Acquaiuto`, `Vampirico` ↔
`Aiutofuoco`, `Filtraggio`/`Prisma Armatura`/`Schermosaldo` ↔ `Filtro`/`Scudoprisma`/`Solidroccia`).
Le altre 27 sono lo stesso caso, solo che la controparte ufficiale ha `effect: none`: su
undici controllate a campione la controparte c'è **sempre**, e sempre inerte.

Il conto complessivo dice la stessa cosa: delle 307 voci col nome ufficiale solo **22**
hanno un effetto attivo, contro **34 su 108** fra quelle senza. **A far funzionare il
calcolatore è la voce vecchia; a essere collegata ai Pokémon è quella ufficiale.**

> Il lavoro quindi è **fondere ogni coppia**, tenendo la chiave giusta e portandoci sopra
> il blocco `effect` che funziona — lo stesso metodo delle 24 già fatte, mappate a mano e
> mai indovinate per somiglianza. Ha conseguenze sui team salvati e sulle regulation, e va
> deciso da Davide: non l'ho toccato.
>
> ✅ Le **10 voci senza corrispondente reale** (`Nervosismo`, `Sforzo`, `Tiratore`,
> `Manto Neve`, `Tempra`, `Assorbifuoco`, `Colpo Secco`, `Compressione`, `Vento Misterioso`,
> `Polifagia`) restano fuori per decisione dell'11/08, e ognuna lo dichiara nella propria
> descrizione. Fuori anche le **7** senza traduzione ma appese a un Pokémon (`Download`,
> `Libero`, `Punk Rock`, `Teravolt`, `Transistor`, `Eelevate`, `Fire Mane`).

### 2.3 ⬜ Mosse per regulation — le quattro cose che richiedono una fonte

Il meccanismo è chiuso (calcolatore, team builder, Speed Tier). Manca **il dato**, e le
quattro cose richiedono **fonti diverse**:

| Cosa manca | Fonte che servirebbe |
|---|---|
| **La differenza fra M-A e M-B** | Nel dump c'è **un solo** version group `champions`, quindi oggi le due regulation riceverebbero la **stessa identica lista**. Se bandiscono mosse diverse, quella differenza non è in nessun dato che abbiamo. È lo stesso buco già noto per mosse e oggetti, che oggi MB copia da MA |
| **Le 20 forme inventate** | Sono forme di Davide, PokéAPI non le conosce. Non è solo il moveset: è la stessa fonte che servirà per le loro stat e abilità. Restano fuori — dichiarate, non riempite |
| **`Pawmot`** | ✅ chiarito il 12/08: è un buco del dump, non un errore nostro. Resta senza elenco, con l'avviso giallo. Da riconfermare sulla wiki nel giro di collaudo |
| **Le regulation future** | Se la prossima non è basata su Champions non ha un version group nel dump: il suo elenco va dalla schermata contenuti o da uno script dedicato |

> Il metodo resta quello del roster: dove esiste una fonte la si importa con uno script
> rieseguibile che **si ferma su ciò che non risolve**; dove non esiste, il dato si lascia
> mancante e **lo si dichiara**. Non si riempie a stima.

---

## 3. Bachi noti e non corretti

| | Baco | Stato |
|---|---|---|
| ⚠️ | **`build_catalog.py` oggi distruggerebbe il catalogo** | Trovato il 12/08, **non corretto** perché fuori scope. Legge come base i **file storici** (174 voci contro le 1026 di oggi, nessun `nome_it`/`nome_en`, Mega ancora convertite) e scrive in `data/catalog/`. Peggio: `MEGA_BONUS` riapplicherebbe il `+75 HP / +20` che la deconversione dell'11/08 ha tolto. Rieseguirlo **riporterebbe indietro il catalogo di quattro giorni di lavoro, in silenzio**. Va fatto leggere `data/catalog/` quando esiste, e `MEGA_BONUS` va tolto. Fino ad allora **non eseguirlo** |
| ⬜ | **Il calcolatore non impedisce di scrivere una mossa illegale** | La segnala e basta. **È voluto per ora**: un blocco duro sulle voci senza elenco sarebbe un falso divieto |
| ⬜ | **`1 team salvati` / `1 saved teams`** | Plurale sbagliato in entrambe le lingue, vedi §2.1 |

---

## 4. Voci minori, per sezione

| Sezione | Voce |
|---|---|
| 💾 **Log** | ⬜ Aggiungere una funzione di salvataggio log |
| 🖨️ **Stampa 3D** | ⬜ Sezione nuova, sul modello di Arduino: richiamo a un sito per disegnare e salvataggio dei progetti |
| 🤖 **Arduino** | ⬜ Richiamo a Tinkercad per disegnare il progetto e verificare i connettori |
| 💻 **PC Builder** | ⬜ Wishlist Amazon o altri · ⬜ prezzo componente · ⬜ percentuale di compatibilità fra i pezzi (valutare UserBenchmark) · ⬜ gestire l'uscita di nuovi pezzi nel tempo |
| 🐍 **Python** | ⬜ Spazio per inserire i propri progetti e testarli · ⬜ idee per rendere la sezione più utile |
| 🐾 **Pokémon** | ⬜ Creare i JSON di una regulation nuova dalla web app (vedi §1.3) |

---

## 5. 🏁 Il giro di collaudo finale (va fatto **per ultimo**)

**Questa voce si chiude dopo tutte le altre.** Sono tre lavori che si fanno insieme, e
vanno alla fine per lo stesso motivo: qui i bachi peggiori non hanno mai dato errore — il
PC Builder inerte per settimane per un apice di troppo, il Ripristina che sovrascriveva
senza chiedere, lo Speed Tier che ricadeva su una lista statica — e un lavoro fatto dopo
può rimetterli in piedi.

⚠️ **Prima di iniziare**: `graphify-out/` è una fotografia, non uno specchio. Va rifatto
(`/graphify . --update`) **obbligatoriamente** prima di 5.2 e 5.3, che sono i due lavori in
cui il grafo deve essere completo.

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

### 5.2 ⬜ Le mosse assegnate sono davvero quelle giuste?

Il moveset importato il 12/08 non è mai stato confrontato con una fonte indipendente:
viene tutto dal dump di PokéAPI, e finora l'unica verifica è stata **interna** — i nomi
risolvono, i conti tornano, Incineroar perde Knock Off. Questo dice che il meccanismo
funziona, **non** che gli elenchi siano corretti.

**Fonte: [Bulbapedia](https://bulbapedia.bulbagarden.net/)**, indicata da Davide come la più
attendibile e già usata con profitto (ha confermato `Mirror Herb` → «Foglia carbone» come
seconda fonte indipendente).

In ordine di rischio:

- **la lista `champions` per prima**: è la più giovane e la meno vista (19 810 righe su 319
  voci), e nessuno ha mai controllato che quel version group sia completo. Se lì manca
  qualcosa, su M-A e M-B una mossa legale sparisce dalla tendina **senza dire niente**
- **`Pawmot`**, il canarino: un caso solo, già spiegato come buco del dump, da riconfermare
- **un campione della lista `main`** su generazioni diverse: per 429 voci su 1258 il version
  group scelto **non** è Scarlatto/Violetto
- **i metodi**: `machine` è il 76% delle righe (50 551 su 66 033). Se il dump gonfia le MT,
  gli elenchi sono più larghi del vero e il filtro serve a poco

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
- **i file di dati storici**, la voce più concreta — vedi la trappola in cima. Da dismettere
  **solo** a verifica finita, cioè qui
- **la tabella `regulations` nel DB** (vedi §1.4, falla 1) e ogni altra colonna che nessuna
  query legge più
- **immagini e asset** in `static/` non referenziati

Il metodo: **prima si misura, poi si propone.** Per ogni candidato serve la prova che non è
usato, e la rimozione si fa in un blocco suo, dopo il via libera di Davide — non insieme al
collaudo, così se qualcosa si rompe si sa quale dei due l'ha rotto.
