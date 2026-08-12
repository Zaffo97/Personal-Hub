# 📋 BACKLOG — Personal Hub

> Fonte: `Nuove implementazioni.docx` (verde = fatto).
> Questo file è la versione tracciabile di quel documento: qui restano solo le voci
> **non ancora chiuse**, più quelle chiuse di recente con la data.
> Aggiornato: 12/08/2026

Legenda: ⬜ da fare · 🟨 parziale / da verificare · ✅ fatto

---

## 🏁 ⬜ DA FARE PER ULTIMO — il giro completo di collaudo

**Questa voce si chiude dopo tutte le altre.** Quando i lavori in questo file sono
finiti, si fa **un giro completo della web app**: ogni sezione, ogni pagina, **ogni
campo e ogni funzione**, per vedere se c'è qualcosa che non torna. Non un controllo a
campione sulle cose toccate di recente — tutto, comprese le parti che nessuno guarda da
mesi.

Perché serve, e perché va fatto **alla fine**: qui i bachi peggiori non hanno mai dato
errore. Il PC Builder è rimasto inerte per settimane per un apice di troppo, il
Ripristina del roster sovrascriveva senza chiedere conferma, lo Speed Tier ricadeva in
silenzio su una lista statica e `/api/moves` leggeva il file sbagliato. Tutta roba che
si vede solo **usando** la pagina, e che un lavoro fatto dopo può rimettere in piedi.

Cosa deve coprire il giro, come promemoria — da dettagliare quando ci si arriva:

- **ogni campo di ogni form**: vuoto, valore limite, valore assurdo, caratteri strani
  (apostrofi e accenti: è la classe di bug che ha ucciso il Ripristina)
- **ogni pulsante e ogni azione**: creazione, modifica, eliminazione, ripristino,
  import, export — e la conferma dove deve esserci
- **le due lingue**, `IT` ed `EN`, su tutte le pagine Pokémon
- **tutte le regulation**, non solo `ma`: `pokedex` e `mb` sono quelle dove sono
  usciti i bachi degli endpoint
- **il calcolatore in tutti e quattro i tab**, con la regola #8 come pietra di paragone
- lo sweep tecnico che qui ha già ripagato: rendere ogni pagina ed eseguire
  `new Function()` su **ogni blocco `<script>` e ogni handler inline**
- le sezioni non-Pokémon, che ricevono meno attenzione: Gaming, Arduino, PC Builder,
  Python, e la Stampa 3D quando ci sarà

L'esito va scritto qui, con i numeri: quante pagine, quanti campi, quante anomalie
trovate e quali. Le anomalie che non rientrano nello scope del giro si segnalano, non
si correggono al volo.

### ⬜ Nello stesso giro — l'inventario di cosa non serve più

Insieme al collaudo, un **censimento di tutto quello che sta nel progetto** per capire
cosa non viene più usato e si può togliere. Va fatto **alla fine** per lo stesso motivo:
finché i lavori sono in corso, un file che oggi sembra morto può servire domani.

Cosa passare in rassegna, tutto quanto:

- **template** — chi li renderizza? `reference.html` è già noto come orfano (nessuna
  route lo chiama). Vanno cercati anche i blocchi Jinja, gli `{% include %}` e i
  `{% block %}` che nessuno estende più
- **script** `static/js/` e `static/css/` — chi li carica, e all'interno **quali
  funzioni non chiama nessuno**. Qui sono già state trovate `MEGA_DATA`, `PKMN_DB`,
  `calc_stat_champions()` e una `switchTab` duplicata: la classe esiste
- **route Python** — quali non sono raggiunte da nessun `url_for()`, link o `fetch()`
- **funzioni e helper** nei blueprint, in `data.py` e in `extensions.py` mai importati
- **gli script di `scripts/`** — quali sono una-tantum già consumati e quali vanno
  tenuti perché rieseguibili (`build_catalog.py`, `importa_*`, `esporta_dati.py` restano;
  altri no)
- **i file di dati storici**, la voce più concreta: `data/roster_ma.json`,
  `moves_ma.json`, `items_ma.json`, `abilities.json` e `pokemon_catalog.json` sono
  ancora lì come **fallback** del catalogo unico. `pokemon_catalog.json` contiene per
  giunta le Mega nella vecchia forma convertita. Da dismettere **solo** a verifica
  finita — cioè qui
- **colonne e tabelle del DB** che nessuna query legge più
- **immagini e asset** in `static/` non referenziati

Il metodo: **prima si misura, poi si propone**. Per ogni candidato serve la prova che
non è usato (la ricerca che non trova riferimenti), e la rimozione si fa in un blocco
suo, dopo il via libera di Davide — non insieme al collaudo, così se qualcosa si rompe
si sa quale dei due l'ha rotto.

---

## ✅ Regulation e interfaccia — le quattro voci, chiuse (11/08/2026)

Tutte e quattro fatte e verificate: **41 controlli su 41** sul test client, regola #8
esatta in browser (A=183, D=122, HP=221, 85-102 = 38.5%–46.2%) **su `pokedex` senza
`?reg=`**, cioè proprio perché è il nuovo default, e sweep su **26 pagine, 44 blocchi
`<script>` e 2197 handler inline**.

| | Cosa è stato fatto |
|---|---|
| ✅ | **Niente più JSON per regulation.** I tre input `roster_file`/`moves_file`/`items_file` compaiono ora **solo** sulle regulation non migrate (`{% if not reg.filter_file %}`), e con loro spariscono da `saveMeta()`: `campiFile()` legge solo gli input presenti, quindi su una regulation a filtro quei campi non vengono più scritti. Su `ma`, che ha ancora i percorsi legacy nel registro, restano **conservati** — verificato salvando davvero dal browser: toast "✅ Metadati salvati!" e i tre file ancora nel JSON. Anche `regulations_list.html` non stampa più tre righe vuote: mostra `🔎 filtro sul catalogo — regulations/<id>.json` |
| ✅ | **Titolo della sezione Pokémon** — `pokemon.html:24` è ora `🎮 Pokémon VGC`, senza regulation. Nello stesso giro sono caduti gli altri "Reg MA" scritti a mano che il cambio di default avrebbe reso **falsi a schermo**: i topbar e i titoli di `moves_editor`, `items_editor` e `roster_editor` ora dicono la regulation vera (`current_reg.label`, che le tre route già passavano), i due placeholder "Cerca nel Reg MA…" del calcolatore sono "Cerca un Pokémon…", e la card della dashboard dice "VGC". Resta di proposito il valore iniziale del campo **Formato** in `team_form.html:42` (`VGC Reg MA`): è testo libero del team, non un'etichetta di sistema |
| ✅ | **Catalogo a sinistra del Calcolatore** — invertite le due righe in `pokemon.html:34-35` |
| ✅ | **`pokedex` è il default del sito** — i 14 letterali `"ma"` sono spariti. Ora c'è **`regulation_default()` in `data.py`**, che restituisce **la prima regulation di `regulations.json`**: lo stesso criterio del fallback `regs[0]` che tutte le route già usavano quando l'id non esiste, quindi il file dice una cosa sola e la dice in un posto solo. Per cambiare default si sposta una voce in cima al registro, senza toccare il codice. In `regulations.json` l'ordine è ora `pokedex`, `ma`, `mb`. Misurato: `/api/moves` senza `reg` passa da 461 a **921** mosse, gli oggetti da 58 a **398**, il roster del team builder da 279 a **1343** |

> ⚠️ **Una cosa che resta a `ma`**: `extensions.py:143` crea la colonna con
> `regulation_id TEXT DEFAULT 'ma'`. Non è un doppione dei 14 — è il default del **DB**,
> e cambiarlo richiede una migrazione. Oggi non fa danno perché `_team_upsert()` passa
> sempre un valore esplicito, che ora è `regulation_default()`. I team già salvati
> restano sulla loro regulation: nessuno è stato toccato.

### ✅ Tre endpoint che il JS chiamava e che non esistevano

Saltati fuori verificando la voce 1: `GET /pokemon/api/regulations` e
`POST /pokemon/api/regulations/save` **non erano mai stati scritti**, e `team_form.html`
chiamava `/api/regulations`, che pure non esiste. Conseguenze reali, non teoriche:

- il pulsante **💾 Salva Metadati** dell'editor regulation non ha mai salvato niente:
  404 → `r1.json()` lancia → `catch` → toast "Errore rete"
- la tendina **Regulation** del team builder falliva dentro un `catch(e){}` muto e
  restava con la **sola `<option>` stampata dal template**. Cioè: non si è mai potuta
  scegliere la regulation di un team dall'interfaccia

Sono stati aggiunti entrambi (`blueprints/pokemon.py`, accanto a create/delete) e
`team_form.html` ora chiama quello giusto. Il salvataggio **rifiuta** un registro vuoto,
non-lista, senza `id`/`label`, con id duplicati, o che **perderebbe una regulation**
esistente — 5 payload rifiutati su 5, con il file verificato intatto dopo. Il motivo dei
controlli: da oggi il registro dice anche **qual è il default del sito**, quindi un
salvataggio sbagliato non toglierebbe solo un'etichetta.

Verificato in browser: la tendina del team ora elenca **3** regulation e cambiandola il
roster passa da **1343** (pokedex) a **279** (MA).

### ✅ I cinque bachi piccoli — chiusi subito dopo (11/08/2026)

Erano tutti già localizzati, e due erano diventati più visibili col nuovo default.
**22 controlli su 22** sul test client, più la prova in browser di ognuno.

| | Voce | Come è stato chiuso |
|---|---|---|
| ✅ | **`/pcbuilder/` rispondeva 500** ⚠️ | `pcbuilder.py:16` metteva la `sqlite3.Row` grezza in `{"data": b}`, e il template la passa a `\|tojson` nell'`onclick` di Modifica: `TypeError: Object of type Row is not JSON serializable`. **La sezione era inaccessibile** appena c'era una build salvata — e nel DB ce n'è una, quindi lo era davvero. Ora `dict(b)`, lo stesso che `pokemon()` fa per `teams_json`. Verificato in browser: la pagina si apre e il modale Modifica carica `ZAFFO-PC` con i suoi **5 componenti**, il primo un Ryzen 7 7800X3D |
| ✅ | **53 `onmouseout` morti in `python.html:45`** | Il ramo `{% else %}` aggiungeva due apici dentro una stringa già quotata: l'attributo usciva `this.style.background=''''`, un `SyntaxError`, quindi su ogni argomento **non** completato l'handler era `null` e lo sfondo dell'hover non si spegneva più. Tolti i due apici di troppo. Da **0 handler vivi su 53 a 53 su 53**, verificato eseguendo davvero mouseover/mouseout: lo sfondo passa a `var(--surface-off)` e torna a vuoto. Renderizzati entrambi i rami: da fare → `background=''`, completato → `background='var(--success-dim)'` |
| ✅ | **`loadSpePkmn()` non ricalcolava** | Riempiva `spe_base` ma non chiamava `updateSpeed()`: dopo aver scritto un nome nello Speed Tier la propria Velocità restava `—` e la tabella continuava a confrontarsi con il valore precedente. Aggiunta la chiamata. Misurato: Incineroar → base **60**, Velocità **80**; poi Dragapult → base **142**, Velocità **162**, con 1321 righe su 1343 marcate più lente |
| ✅ | **L'eliminazione di una regulation lasciava il filtro orfano** | `api_regulations_delete` cancellava solo `roster_file`, `moves_file` e `items_file` — che sulle regulation nuove **non esistono**: `data/regulations/<id>.json` restava sul disco mentre la modale prometteva di averlo cancellato. Ora `filter_file` è nell'elenco, e **prima di toglierlo se ne tiene una copia** in `data/archive/regulation_<id>_pre-eliminazione.json`: il filtro è l'elenco di nomi scelto a mano, ricostruirne 279 sarebbe la perdita che l'archivio esiste per evitare. Il testo della modale ora dice il vero. Provato sul ciclo completo con una regulation usa-e-getta: creata, filtro sul disco, eliminata, filtro sparito, copia in archivio, registro con le tre vere intatte |
| ✅ | **`Galarian Darmanitan` dava 404** | Delle **57** voci con un qualificatore regionale, **56** usano il prefisso (`Galarian Zapdos`) e **una sola** la parentesi: `Darmanitan (Galarian Form)`. Il nome nel catalogo **non è stato toccato** — è l'identità della forma e la usano i filtri delle regulation: la differenza si colma nell'indice di `api_pokemon.py`, che per una forma `X (Y Form)` con `Y` regionale registra anche l'alias `Y X`. Verificato che risolva con le stesse stat del nome canonico, che `Galarian Zapdos`, `Alolan Raichu`, `Hisuian Arcanine` e `Paldean Tauros (Aqua Breed)` continuino a risolvere, e che `Galarian Machamp`, `Mega Machamp` e `Alolan Pippo` restino **404** invece di rispondere un Pokémon a caso |

> Sweep dopo i fix: **26 pagine, 45 blocchi `<script>`, 2206 handler inline, zero errori.**
> Prima erano 54: i 53 di `python.html` più il 500 del PC Builder, che non essendo
> renderizzabile non entrava nemmeno nel conteggio.

---

## Le quattro voci — com'erano state aperte (11/08/2026)

| | Voce | Cosa ho trovato guardando il codice |
|---|---|---|
| ✅ | **Verifica creazione regulation — servono ancora i JSON?** | **No, e in parte è già così.** `api_regulations_create` (`blueprints/pokemon.py:829`) scrive **da sé** un solo file, `data/regulations/<id>.json`, e registra `filter_file` in `regulations.json`: elenchi di nomi che puntano al catalogo, nessuna copia dei dati. I campi vuoti che si vedono sono i **tre residui del vecchio modello** — `roster_file`, `moves_file`, `items_file` — ancora stampati da `regulation_editor.html:83,88,93` (input modificabili) e da `regulations_list.html:45-47`. Su una regulation nuova sono vuoti perché quei file **non esistono più e non devono esistere**. Delle tre in `regulations.json` solo `ma` ha ancora i percorsi legacy. La strada più semplice ed efficace è quindi la seconda che proponi: **non creare nulla**, e togliere quei tre campi dove c'è `filter_file` (l'editor ha già il ramo `{% if reg.filter_file %}` alla riga 105, basta estenderlo). ⚠️ Da verificare prima: quei tre input sono anche **scritti** al salvataggio (`regulation_editor.html:277-292`), quindi vanno tolti da lì insieme |
| ✅ | **Titolo della sezione Pokémon fisso su "Reg MA"** | `templates/pokemon.html:24` ha `<h1>🎮 Pokémon VGC — Reg MA</h1>` scritto a mano: resta "Reg MA" qualunque regulation sia attiva. Va reso generico — o senza regulation, o con la `label` di quella davvero in uso. La topbar (`pokemon.html:3`) e la sidebar (`base.html:152`) dicono già solo "Pokémon VGC" e vanno bene |
| ✅ | **Pulsante Catalogo a sinistra del Calcolatore** | `templates/pokemon.html:34-35`: oggi l'ordine è `📊 Calcolatori VGC` e poi `📚 Catalogo`. Vanno invertiti. È uno scambio di due righe |
| ✅ | **`pokedex` come default del sito** | Oggi il default è `ma`, **scritto a mano in 14 punti**: 11 in `blueprints/pokemon.py` (righe 181, 242, 330, 343, 365, 965, 1010, 1048, 1085, 1227, 1282), uno in `blueprints/api_pokemon.py:507` e due in `templates/team_form.html` (48 e 163). In `data/regulations.json` l'ordine è `ma`, `pokedex`, `mb`, e le tendine seguono quell'ordine. Serve **un punto solo** che dica qual è la regulation di partenza — costante o campo in `regulations.json` — invece di 12 letterali sparsi, e `pokedex` va messo per primo anche nell'elenco, così è il primo che si vede pure nell'editor. ⚠️ Attenzione a `_pokemon_regulation` (riga 252): se l'id non esiste ricade su `regs[0]`, quindi cambiare l'ordine del file **cambia già da solo** il comportamento di quel fallback |

> Nota di metodo, ora avverata: la regola #8 va eseguita su **`pokedex`** (Amoonguss non
> è nel roster di MA), che da oggi **è** il default — quindi il caso di prova e il
> default coincidono, e aprire il calcolatore senza `?reg=` basta a rieseguirlo.

---

## 🟨 Switch lingua IT ⇄ EN — primo blocco chiuso (11/08/2026)

Pulsante **`IT`/`EN`** in `base.html`, accanto a quello del tema. Cambia lingua a
**tutti i nomi dei dati**: Pokémon, mosse, abilità e oggetti.

### Come è fatto

- **Le chiavi del catalogo non cambiano mai.** Sono referenziate dai filtri delle
  regulation, dal motore degli effetti, da `ABILITIES_CALC` e dai team salvati nel DB.
  Ogni voce ha `nome_it` e `nome_en`, e cambia solo ciò che si legge
- la lingua sta in un **cookie** (`hub_lang`), non in `localStorage`, perché la deve
  leggere anche Flask: roster, mosse e oggetti nelle tendine li renderizza il server
- il pulsante **ricarica** la pagina. È voluto: così cambia davvero tutto in un colpo
  solo, senza metà pagina in una lingua e metà nell'altra. Il prezzo è che sul
  calcolatore si perde quel che si stava scrivendo
- si può **scrivere in entrambe le lingue**: `risolviChiave()` lato JS e `_INDICE`
  lato Python accettano chiave, nome italiano e nome inglese. Scrivere `Privazione`
  o `Knock Off` porta alla stessa mossa

### L'import — `python scripts/importa_nomi_lingua.py [--dry-run] [--solo …]`

Da PokéAPI, con cache in `data/cache/pokeapi/` (ignorata da git): la seconda
esecuzione non ripassa dalla rete. ⚠️ PokéAPI risponde **403 senza `User-Agent`**.

| Database | Con nome ufficiale nelle due lingue | Senza | Nomi davvero diversi tra IT ed EN |
|---|---|---|---|
| Mosse | **899 / 921** | 22 | 889 |
| Oggetti | **378 / 398** | 20 | 341 |
| Abilità | **312 / 415** | 103 | 307 |
| Pokémon | **1019 / 1026** | 7 | **21** |

Chi non si aggancia non resta a metà: prende `nome_it == nome_en == chiave`, così il
commutatore ha sempre qualcosa da mostrare.

**Cosa c'è dietro ogni "senza":**

- **mosse (22)** ✅ — le mosse Z (`Breakneck Blitz`…) e `Syrup Bomb`: PokéAPI non ha
  l'italiano. **Chiuse dalla wiki l'11/08/2026**, vedi la sezione qui sotto
- **oggetti (20)** ✅ — roba recente: `Booster Energy`, `Clear Amulet`, `Covert Cloak`,
  `Loaded Dice`, le maschere di Ogerpon. Buco a monte, non nostro. **Chiusi dalla wiki**
- **Pokémon (7)** — le sole voci il cui nome è una forma (`Palafin (Zero Form)`,
  `Meowstic (Male)`…). Giusto così: il nome italiano di una forma non è deducibile e
  non va inventato. I **21** diversi sono i Paradosso più `Type: Null` →
  `Crinealato`, `Manoferrea`, `Lunaruggente`, `Tipo Zero`…
- **abilità (103)** ✅ — chiuse l'11/08/2026, ma **non traducendole**: erano doppioni,
  e 24 coppie sono state fuse. La wiki infatti non le chiudeva: ne recuperava 5,
  confermando che sono identiche nelle due lingue (`Download`, `Libero`, `Punk Rock`,
  `Teravolt`, `Transistor`). Il problema non era di traduzione, vedi qui sotto

### ✅ Il secondo giro — `python scripts/importa_nomi_wiki.py [--dry-run] [--solo …]`

Fonte: **wiki di Pokémon Central**, la stessa di `importa_roster_champions.py`. Cache
in `data/cache/wiki/` (ignorata da git). Due fonti nell'ordine:

1. le pagine **«… in altre lingue»** (mosse, strumenti, abilità), tabelle con una riga
   *Italiano* e una *Inglese*: 950 mosse, 860 strumenti, 306 abilità
2. per quello che quelle liste non coprono — **gli strumenti di nona generazione non ci
   sono** — la **pagina singola**, trovata con la ricerca della wiki e accettata solo se
   la sua riga *Inglese* combacia con la chiave del catalogo. Così un risultato di
   ricerca sbagliato viene scartato invece di entrare nei dati

| Database | Senza traduzione prima | Riempite | Di cui davvero diverse in italiano | Restano |
|---|---|---|---|---|
| Mosse | 32 | **32** | 22 | **0** |
| Oggetti | 57 | **57** | 20 (tutti presi dalla pagina singola) | **0** |
| Abilità | 108 | 5 | 0 | **103** |

Le 22 mosse nuove sono le 18 mosse Z (`Gigavolt Havoc` → **Gigascarica Folgorante**,
`Black Hole Eclipse` → **Buco Nero del Non Ritorno**) più `Syrup Bomb` → Bomba
Sciroppata, `Blood Moon` → Luna Rossa, `Matcha Gotcha` → Spruzzatè, `Ivy Cudgel` →
Clava di Liane. I 20 oggetti sono `Booster Energy` → **Capsula energetica**,
`Covert Cloak` → Anonimanto, `Loaded Dice` → Dado truccato, le tre maschere di Ogerpon
e i sette Mochi. Gli altri 47 "senza traduzione" non erano un buco: sono le Megapietre,
i cristalli Z e le altre voci che in italiano **si scrivono uguale**, e ora è
verificato invece che presunto.

**Lo script non sovrascrive mai una traduzione già presa da PokéAPI**: tocca solo le
voci con `nome_it == nome_en`. Dove le due fonti non concordano lo **segnala e basta**,
perché nessuna delle due è sempre giusta — PokéAPI abbrevia (`Revitalizz. Max`,
`Autodistruz.`) e la wiki ha i suoi refusi (`Vasterngia`, `Morostretto`). ⬜ **11 voci
da decidere a mano**, elencate dal rapporto dello script:

| Voce | PokéAPI (in uso) | wiki |
|---|---|---|
| Aura Sphere | Forzasfera | **Sferapulsar** |
| Heal Pulse | Ondasana | **Curapulsar** |
| Self-Destruct | Autodistruzione | Autodistruz. |
| Max Revive | Revitalizz. Max | **Revitalizzante Max** |
| Exp. Share | Condividi esp. | **Condividi Esperienza** |
| Expanding Force · Jaw Lock · Psycho Shift · Swallow · Shadow Wave · Shadow Panic | Vastenergia · Morsostretto · Psicotransfer · Introenergia · Ondascura · Ombrapanico | Vasterngia · Morostretto · Psicotrasfer · Intoenergia · Ondaoscura · Ombropanico |

### ✅ Le 11 in disaccordo — decise l'11/08/2026

Guardandole una per una si dividono in tre gruppi, non in uno. Applicate con
`python scripts/applica_nomi_decisi.py [--dry-run]`, che verifica il valore di
partenza di ogni voce e si ferma se non è quello atteso, quindi non può lavorare
alla cieca né rifare il giro due volte.

| Gruppo | Esito |
|---|---|
| **Due nomi davvero diversi** | Si passa alla wiki: `Aura Sphere` → **Sferapulsar**, `Heal Pulse` → **Curapulsar** |
| **Tre abbreviazioni** | Forma estesa: `Max Revive` → **Revitalizzante Max**, `Exp. Share` → **Condividi Esperienza**. `Self-Destruct` era già «Autodistruzione». Nel gioco si abbrevia per stare nella casella di testo; qui lo spazio non manca |
| **Sei refusi della wiki** | Nessuna modifica, e nessuna decisione da prendere: `Vasterngia`, `Morostretto`, `Psicotrasfer`, `Intoenergia`, `Ondaoscura`, `Ombropanico` sono errori di battitura contro le forme corrette già in uso |

✅ **`Mirror Herb` → «Foglia carbone» è confermato**, e il sospetto è tolto.
Controllato l'11/08/2026 su [Bulbapedia](https://bulbapedia.bulbagarden.net/wiki/Mirror_Herb),
una fonte **indipendente** da quella che avevamo usato: dà lo stesso nome italiano.
Il giapponese è ものまねハーブ (*erba imitatrice*) e lo spagnolo *Hierba Copia*, quindi
è la localizzazione italiana ufficiale a essere strana, non il nostro dato. «Erba
Speculare», che i motori di ricerca suggeriscono, **non esiste** sulla wiki (404).

### ✅ Le abilità doppie — fuse l'11/08/2026

**24 coppie fuse**, `data/catalog/abilities.json` da **415 a 391 voci**, con
`python scripts/fondi_abilita_doppie.py [--dry-run]` (rieseguibile, copia in
`data/archive/abilities_pre-fusione.json`). **39 controlli su 39.**

**Il guasto era più grosso della fusione.** Il catalogo Pokémon cita le abilità col
**nome inglese** (`Swift Swim`), mentre le chiavi del file sono italiane
(`Nuotovelox`), e `abilityEffect()` faceva un match **esatto sulla chiave**: dei
**307** nomi di abilità posseduti dai Pokémon, **zero** arrivavano a un effetto, e
tutti e 56 gli effetti del file erano irraggiungibili partendo da un Pokémon. Nel tab
Danno non si vedeva — lì la tendina elenca tutte le abilità in italiano e si sceglie a
mano — ma nello **Speed Tier**, dove la tendina è popolata con le abilità del Pokémon,
nessun effetto si applicava mai. Misurato: **Kingdra sotto pioggia con Swift Swim
restava a 105 di Velocità invece di 210**.

Servivano tutte e due le metà, e da sole non bastavano:

1. **`abilityEffect()` ora risolve per chiave, nome italiano e nome inglese**, con lo
   stesso `risolviChiave()` già usato dalla casella delle mosse. Da sola non
   avrebbe acceso niente: avrebbe risolto su `Nuotovelox`, che era **inerte**
2. **la fusione**: l'effetto passa dalla voce vecchia a quella ufficiale. Da sola non
   avrebbe acceso niente: l'effetto sarebbe finito sulla voce giusta, ma il nome
   inglese non l'avrebbe raggiunta

Dopo: Kingdra **105 → 210**, esattamente ×2. Dei 307 nomi posseduti dai Pokémon,
**307 risolvono** su una voce (erano 7) e quelli che arrivano a un effetto attivo
passano da **22 a 39** a parità di risoluzione.

**Le coppie non sono state indovinate.** L'accoppiamento automatico per somiglianza di
testo è stato provato e sbagliava — proponeva `Combattività` → `Bruciaimpeto` e
`Nuoto Veloce` → `Clorofilla`. Ogni voce è invece mappata a mano sull'**abilità reale
che il suo `effect` descrive**, e lo script risolve quel nome inglese contro i dati,
fermandosi su ciò che non trova. 24 su 24 risolte, tutte con la controparte appesa a
un Pokémon vero:

| | |
|---|---|
| `Combattività` → `Dentistretti` (Guts) | `Nuoto Veloce` → `Nuotovelox` (Swift Swim) |
| `Assorbiacqua` → `Assorbacqua` · `Voltassorbi` → `Assorbivolt` | `Fuga` → `Remasabbia` · `Manto Slaccio` → `Spalaneve` |
| `Multiscaglia` → `Multisquame` · `Ombra Fantasma` → `Spettroguardia` | `Pioggerella` → `Piovischio` · `Nevischio` → `Scendineve` |
| `Scudo Peluria` → `Foltopelo` · `Spessore` → `Grassospesso` | `Tempesta di Sabbia` → `Sabbiafiume` |
| `Squame Miracolo` → `Pelledura` · `Passo Veloce` → `Piedisvelti` | `Mega Sol` → `Terra Estrema` (Desolate Land) |
| `Filtraggio`/`Prisma Armatura`/`Schermosaldo` → `Filtro`/`Scudoprisma`/`Solidroccia` | `Pioggia Perpetua` → `Mare Primordiale` |
| `Erboristeria` → `Erbaiuto` · `Torrente` e `Torrentismo` → `Acquaiuto` | `Vampirico` → `Aiutofuoco` |

Sulle 7 coppie dove **anche** la voce ufficiale aveva già un effetto, i due blocchi
sono stati confrontati prima di sovrascrivere: **identici 7 su 7**, quindi la
sovrascrittura non cambia nessun numero. Alla voce ufficiale seguono anche `category`,
i campi extra di calcolo (`weather_ball_type`, `atk_boost`, …) e la `desc` della
vecchia, che descrive l'effetto applicato davvero invece della formula generica.
Chiave, `nome_it` e `nome_en` restano quelli ufficiali.

> Correzione a quanto scritto sopra in questo file: **`Spettroguardia` non è un nome
> sbagliato**. È **Shadow Shield**, che ha davvero l'effetto di Multiscale — la
> descrizione era giusta e la nota «descrive Multiscaglia» era un falso allarme.

**Le 10 che non ho toccato**, per decisione di Davide dell'11/08/2026: il loro effetto
non corrisponde a nessuna abilità reale, quindi accoppiarle vorrebbe dire decidere che
l'effetto attuale è sbagliato. Sono probabilmente abilità **di Champions**:

| Voce | Perché non torna |
|---|---|
| `Nervosismo`, `Polifagia` | SpA +50% fisso, e sono identiche fra loro |
| `Sforzo` | Attacco +50% — Huge Power e Pure Power raddoppiano |
| `Tiratore` | +30% sulle mosse ad area — nessuna abilità reale |
| `Manto Neve` | Difesa +50% con la Neve — Snow Cloak dà elusione, e il +Def è la meccanica della Neve |
| `Tempra` | SpD +50% con la sabbia — è la meccanica della sabbia sui Roccia |
| `Assorbifuoco` | immunità Fuoco **che cura** — Flash Fire non cura |
| `Colpo Secco` | mosse Fuoco +50% sotto il Sole — Solar Power alza lo SpA |
| `Compressione` | `effect` dice `tinted_lens`, la desc dice «tutte le mosse +30%» |
| `Vento Misterioso` | meteo `fog` perpetuo — la nebbia non è un meteo del gioco |

✅ Dall'11/08/2026 ognuna delle 10 lo **dice nella propria descrizione** («— abilità di
Champions, senza corrispondente ufficiale», aggiunta da `scripts/rifinisci_abilita.py`),
così chi le trova nella tendina capisce perché esistono e non le scambia per un errore.
Gli effetti non sono stati toccati, e nessun'altra voce ha ricevuto la nota.

Intatte anche le **7** senza traduzione ma appese a un Pokémon (`Download`,
`Eelevate`, `Fire Mane`, `Libero`, `Punk Rock`, `Teravolt`, `Transistor`): non sono
doppioni di nessuno.

### Aperto dalla fusione

| | Voce | Note |
|---|---|---|
| ✅ | **`Megasolar` aveva `nome_en: "Mega Sol"`** | Aggancio sbagliato dell'import — «Mega Sol» non è un nome inglese. Corretto l'11/08/2026 con `scripts/applica_nomi_decisi.py`: `nome_en` riportato a `Megasolar`, la convenzione delle voci senza traduzione ufficiale. Ora «Mega Sol» non risolve più su una voce inerte, e l'effetto vive dove deve, su `Terra Estrema` |
| ✅ | **`ABILITIES_CALC` non la usava nessuno** | Rimossa da `data.py` l'11/08/2026 dopo aver verificato **zero consumer** in tutto il progetto: chi marca le abilità che incidono è `abilityIncideSulDanno()` in JS, che legge il blocco `effect`. L'elenco non era solo inerte, era destinato a divergere dai dati veri. Corretti anche i due documenti che lo citavano |
| ✅ | **Il fallback `data/abilities.json` aveva ancora le 24 vecchie** | Riallineato al catalogo l'11/08/2026 con `scripts/rifinisci_abilita.py`: 408 → 386 voci. **Non è stato dismesso** — quello si fa al collaudo finale, con gli altri file storici — ma ha smesso di essere una macchina del tempo: se un giorno il fallback scattasse davvero, non riporterebbe indietro i doppioni appena chiusi, e in silenzio |
| ✅ | **8 voci che condividevano il nome con un'altra chiave** ⚠️ | Trovate verificando le bandierine: **due chiavi diverse possono avere gli stessi `nome_it` e `nome_en`**, e la risoluzione per nome ne sceglie una sola. Il caso grave era **`Sheer Force`**, che esisteva come `Forza Bruta` (con l'effetto) e `Forzabruta` (inerte): vincendo l'ultima, un Pokémon con Sheer Force **non applicava niente**. Prima tamponato in `indiceNomi()` (a parità di nome tiene la voce con un effetto: danno da 82 a **106**, il ×1.3 atteso), poi **tolta la causa** con `scripts/fondi_doppioni_nome.py`. Il criterio non è «vince il nome ufficiale», che su `King's Rock` darebbe la voce sbagliata: resta la **chiave giusta** — quella che segue la convenzione del file e che i filtri già nominano — e i campi mancanti le arrivano dall'altra. Restano `Forzabruta` (con l'`effect` ereditato), `Pelledrago`, `Punta Perforante`, `Spargipiccante`, `Occhio Interiore` (senza lo spazio in fondo, con la desc ereditata), `Freeze-Dry`, `Mud Slap`, `King's Rock`. **I filtri sono stati aggiornati**: MA e MB contenevano entrambe le varianti di `Freeze Dry`, quindi le mosse scendono da 461 a **460** — la stessa mossa contata due volte, non una persa. Ora **zero** nomi condivisi e zero chiavi con spazi ai bordi in tutti e tre i database |

### ⬜ Com'era il problema, prima della fusione

Il secondo giro l'ha chiarito. La wiki ha **306** abilità ufficiali con nome italiano e
inglese, il catalogo ne ha **415**, e le 307 già tradotte usano tutte il nome ufficiale
— **zero disaccordi tra PokéAPI e wiki sulle abilità**, il che dice che quella parte è
solida. Le 103 che restano si dividono così:

- **69** hanno `effect: {"type": "none"}` — sono le abilità inventate (`Black Hole`,
  `Aqua Boost`, `Bodyguard`, `Climber`, `Eelevate`…) e i placeholder. Giusto che non
  abbiano un nome ufficiale
- **34** hanno un effetto vero e proprio, e **7 di queste hanno un blocco `effect`
  identico a una voce ufficiale già presente nel catalogo**:

  | Voce senza nome ufficiale | Voce ufficiale già in catalogo |
  |---|---|
  | `Erboristeria` | `Erbaiuto` (Overgrow) |
  | `Torrente`, `Torrentismo` | `Acquaiuto` (Torrent) |
  | `Vampirico` | `Aiutofuoco` (Blaze) |
  | `Filtraggio`, `Prisma Armatura`, `Schermosaldo` | `Filtro` / `Scudoprisma` / `Solidroccia` (Filter, Prism Armor, Solid Rock) |

  Le altre 27 (`Combattività`, `Assorbiacqua`, `Multiscaglia`, `Nuoto Veloce`,
  `Voltassorbi`…) sono lo stesso caso, solo che la controparte ufficiale in catalogo ha
  `effect: none` invece di un effetto uguale. Su undici controllate a campione la
  controparte c'è **sempre**, e sempre inerte: `Dentistretti` (Guts), `Assorbacqua`
  (Water Absorb), `Multisquame` (Multiscale), `Nuotovelox` (Swift Swim), `Assorbivolt`
  (Volt Absorb), `Pelledura`, `Grassospesso`, `Foltopelo`, `Piovischio`, `Scendineve`,
  `Sabbiafiume`

Il conto complessivo dice la stessa cosa: gli effetti veri stanno **dalla parte
sbagliata**. Delle 307 voci col nome ufficiale solo **22** hanno un effetto attivo,
contro **34 su 108** fra quelle senza. A far funzionare il calcolatore è in buona parte
la voce vecchia; a essere collegata ai Pokémon è quella ufficiale — i 307 nomi di
abilità usati dal catalogo Pokémon risolvono tutti, e risolvono sulle ufficiali.

> Quindi la voce da aprire non è "tradurre le 103": è **fondere ogni coppia**, tenendo
> la chiave giusta e portandoci sopra il blocco `effect` che funziona. È un lavoro sui
> dati, con conseguenze su `ABILITIES_CALC`, sui team salvati e sulle regulation, e va
> deciso da Davide — non l'ho toccato.
>
> Correzione a quanto scritto prima in questo file: l'italiano ufficiale di **Guts non è
> "Cuortenace" ma `Dentistretti`**, e quello di Water Absorb è `Assorbacqua`.

### ⬜ Cosa manca — deciso con Davide l'11/08/2026

| | Voce | Note |
|---|---|---|
| ⬜ | **Nomi e descrizioni tradotti anche negli editor** | Oggi `/pokemon/catalogo`, `/pokemon/mosse`, `/pokemon/oggetti` e `/pokemon/abilita` mostrano la **chiave**, e le descrizioni sono solo in italiano. Vanno tradotti sia i nomi sia i `desc` di mosse, abilità e oggetti. Serve un secondo giro di import per i testi inglesi — la chiave resta comunque l'identità della voce, quindi va deciso come mostrare entrambe |
| ✅ | **Lo switch riguarda solo la sezione Pokémon** | Chiuso 11/08/2026: il pulsante compare **solo sotto `/pokemon/*`**, così non promette quello che non fa. Verificato pagina per pagina: assente su `/`, Gaming, Arduino, PC Builder e Python, presente sulle tre pagine Pokémon provate |
| ✅ | **Bandierine al posto di `IT`/`EN`** | Chiuso 11/08/2026. Bandiera della lingua **attiva**, disegnata in **SVG inline** e non con le emoji bandiera: su Windows quelle non vengono renderizzate come tali e si sarebbero lette «IT» e «GB», cioè le stesse due lettere di prima. `toggleLingua()` legge ora `data-lang` invece del testo del pulsante, che non c'è più. Provato cliccandolo: il cookie passa a `en`, la bandiera diventa la Union Jack e le abilità nelle tendine passano all'inglese |

### Cosa NON copre ancora (stato tecnico)

- ⬜ **le stringhe dell'interfaccia** — etichette, pulsanti, titoli: italiano fisso in
  ~19 template. È il secondo blocco
- ⬜ **gli editor** (`/pokemon/catalogo`, roster, mosse, oggetti) mostrano ancora la
  **chiave**, non il nome tradotto. Lì la chiave è l'identità della voce, quindi va
  deciso se e come mostrarle entrambe
- ⬜ **le descrizioni** sono solo in italiano: `desc` non è stato toccato. Serve un
  secondo giro di import per i testi inglesi

> ⚠️ Conseguenza visibile subito: **in italiano il calcolatore ora scrive
> `Privazione`, non `Knock Off`**, e `Cinturanera` invece di `Black Belt`. È quello
> che la voce di backlog chiedeva, ma se per abitudine VGC preferisci i nomi inglesi
> anche in modalità italiana, si cambia in un punto solo (`nomeVis`).

---

## ✅ Stat delle Mega riportate alle base (11/08/2026)

Le Mega nel catalogo non avevano un bonus: avevano le **stat di Lv.50 già calcolate**
(IV 31, 0 SP) salvate dentro `base_stats`, mentre tutto il resto del catalogo tiene le
base vere. Con la formula del progetto la conversione vale esattamente **+75 HP e +20
sulle altre**, ed è per questo che nel gioco una Mega non cambia mai gli HP ma qui 95
su 101 avevano +75.

```
(2·base + 31) · 50 // 100  =  base + 15   →  HP: +60 → +75 · altre: +5 → +20
```

**Fatto:**

- **95 Mega deconvertite** (`hp − 75`, `− 20` sulle altre) con
  `python scripts/deconverti_mega_catalogo.py [--dry-run]`, rieseguibile e con copia
  in `data/archive/catalog_pokemon_pre-mega-deconv.json`
- **3 chiavi top-level rimosse** — `mega-banette`, `mega-chimecho`,
  `mega-crabominable` erano **doppioni** della forma annidata nella specie base, non
  anomalie: 1029 → 1026 voci. Chiude la vecchia voce *"chiavi mega incoerenti"*
- **`MEGA_DATA` eliminata** da `calcolatori-data.js` (−35 KB): `fetchPkmn()` prende
  anche le Mega da `/api/pokemon`, cioè dal catalogo. `isMega` e il BST sono ora
  derivati (`marcaMega()`), il BST è la somma delle base
- rimosso il `console.log('full d:', d)` di debug in `calcolatori-speed.js`

**Perché la deconversione è quella giusta**, e non un'ipotesi:

| Verifica | Esito |
|---|---|
| Mega coperte da `MEGA_DATA` | **56 su 57** identiche alla cifra dopo la deconversione |
| Mega **assenti** da `MEGA_DATA` ma ufficiali del gioco — Metagross, Mewtwo X/Y, Rayquaza, Salamence, Swampert, Sceptile, Latias, Latios, Mawile, Diancie, Blaziken | **tutte** coincidono coi valori reali |

La seconda riga è la conferma indipendente: la deconversione azzecca valori che
`MEGA_DATA` non poteva suggerire.

**Il bug che questo chiude.** `fetchPkmn()` leggeva `MEGA_DATA` per ogni nome che
inizia con `"Mega "` e non consultava mai il catalogo, mentre `loadRegSpeed()` leggeva
`catalogEntry(name).base_stats.spe` e ci riapplicava la formula Lv.50: sulle Mega la
formula finiva **applicata due volte**. Mega Venusaur valeva 80 di Velocità nel tab
Danno e 100 (→ 120 a Lv.50) nello Speed Tier. Ora entrambi partono da 80.

### ✅ Il bug che è saltato fuori verificando — `/api/regulation/<id>/data`

L'endpoint che alimenta lo Speed Tier leggeva ancora il vecchio `roster_file`.
Stessa identica storia di `/api/moves` chiusa il 10/08. Conseguenze **misurate**:

| Regulation | Prima | Ora |
|---|---|---|
| `ma` | **208** nomi ereditati, **0 Mega** | **279** nomi, **59 Mega** |
| `pokedex` | **404** → caduta muta sulla lista statica da 158 | **1344** nomi |
| `mb` | **404** → stessa caduta | **295** nomi |

Il roster legacy non conteneva **nessuna** Mega: lo Speed Tier non ne aveva mai
mostrata una, e il lavoro di oggi sarebbe rimasto invisibile lì dentro. Ora
l'endpoint chiama `_load_roster()`, lo stesso loader di tutto il resto, che sa
leggere il filtro e ricade sul file vecchio solo se la regulation non è migrata.

### Le tre Mega rimaste fuori — due chiuse da Davide

| Voce | Esito |
|---|---|
| ✅ `Mega Froslass` | Base Velocità riportata a **120** (→ **140** a Lv.50, il valore giusto secondo Davide). Quel singolo valore nel catalogo era **già una base**, non un dato convertito, e la deconversione l'aveva abbassato a 100 sottraendo 20 di troppo. Era l'unico caso del genere: con la correzione le Mega coperte da `MEGA_DATA` combaciano **57 su 58** |
| ✅ `Mega Machamp` | **Non esiste**: forma rimossa dal catalogo. Aveva `base_stats: {}` e non era referenziata da nessuna regulation (né nei roster né nei `mega_map` di MA, MB e Pokedex) |
| ⬜ `Mega Zygarde` | **Lasciata ferma, per decisione dell'11/08/2026.** Correzione a quanto scritto qui prima: non è vero che «le altre cinque non seguono nessuno schema» — seguono **tutte e sei** la stessa firma delle altre 95 (−75 HP, −20 sul resto), e deconvertita darebbe `hp 216 · atk 70 · def 91 · spa 216 · spd 85 · spe 100`, BST 778. Il problema non è più l'aritmetica ma il risultato: **SpA 216 sarebbe il più alto del catalogo di 43 punti** (il massimo oggi è Xurkitree con 173) e un Attacco di 70 per una Mega di Zygarde, che ne ha 100, è strano. Che la sottrazione «torni» del resto è banale: si può sempre sottrarre. Serve sapere che valori si volevano, quindi resta com'è |

> Lezione da tenere: la firma `+75 HP` individua le voci convertite **specie per specie**,
> non stat per stat. Su Froslass cinque valori su sei erano convertiti e uno no, e la
> regola applicata in blocco ha rotto proprio quello. Se ne salta fuori un altro, il
> segnale è il confronto con la Velocità della specie base.

### Il resto del catalogo NON è convertito — verificato

La domanda giusta di Davide: la conversione riguarda solo le Mega o tutto il catalogo?
Solo le Mega. Prove:

| Canarino | catalogo | se fosse convertito |
|---|---|---|
| Shedinja HP | **1** | 76 |
| Chansey HP | **250** | 325 |
| Magikarp | **20/10/55/15/20/80** | 95/30/75/35/40/100 |

20 specie note su 20 esatte, **200 specie su 1026 con HP sotto 50** (una conversione le
avrebbe messe tutte sopra 75), le uniche cinque stat sopra 200 in tutto il catalogo sono
reali (Chansey 250, Blissey 255, Shuckle 230, Guzzlord 223, Stakataka 211), e **nessuna
forma non-Mega** ha la firma +75 HP.

> `Mega Floette` era l'unica **già corretta** ed è rimasta intatta: era `MEGA_DATA` ad
> avere la versione convertita, e sparendo si è sistemata da sé. Stessa cosa per
> `Mega Meowstic (M)` vs `(Male)`: la trappola dei nomi non combacianti non esiste più,
> perché esiste una fonte sola.

> ⚠️ Il vecchio `data/pokemon_catalog.json` **non è stato toccato**: contiene ancora le
> Mega convertite, ma è solo il fallback di `data/catalog/pokemon.json` e viene letto
> unicamente se quest'ultimo manca. Da dismettere insieme agli altri file storici.

### ✅ L'alias che rispondeva con un Pokémon a caso

Togliere `Mega Machamp` ha scoperchiato un baco che c'era da sempre:
`/api/pokemon/Mega Machamp` non dava 404, rispondeva **Mega Venusaur** con le sue stat.

`_costruisci_indice()` registrava come alias il **primo pezzo** di ogni chiave con un
trattino. Serve a far risolvere `Palafin` quando in catalogo c'è solo
`palafin-zero-form` — ma su `mega-venusaur` registrava anche **`mega`**, e il fallback
di `_find_in_catalog` (prova la chiave senza l'ultimo pezzo) ci finiva dentro. Stessa
cosa per `alolan` (18 voci), `galarian` (18), `hisuian` (16), `totem` (12), `iron` (20),
`tapu` (8), `paldean` (4). **Qualsiasi nome inventato che iniziasse così riceveva le
stat di un Pokémon estraneo invece di un errore.**

Ora c'è `NON_ALIASABILI` in `api_pokemon.py`: quei primi pezzi non diventano alias.
Verificato che non rompe niente — dei **295** nomi usati da MA, MB e Pokedex **zero**
dipendevano da questi alias, e i nomi nudi che servono davvero (`Palafin`, `Aegislash`,
`Gourgeist`, `Zygarde`, `Meowstic`, `Morpeko`, `Mr. Mime`, `Iron Hands`, `Tapu Koko`…)
risolvono ancora tutti.

> Effetto collaterale utile: `Galarian Darmanitan` ora dà 404, e ha ragione — in
> catalogo si chiama **`Darmanitan (Galarian Form)`**, l'unica delle 19 voci Galarian
> scritta così invece che `Galarian X`. Prima l'alias spurio nascondeva l'incoerenza
> dietro una risposta sbagliata. ✅ Colmato l'11/08/2026 con un alias nell'indice
> (`X (Y Form)` con `Y` regionale → anche `Y X`): il nome nel catalogo non si tocca,
> ma `Galarian Darmanitan` risolve. Le voci regionali sono **57**, e questa è l'unica
> scritta con la parentesi.

## ✅ Già fatto il 10/08/2026: `mega_map` di MA e MB

| | prima | dopo |
|---|---|---|
| basi nel `mega_map` | 53 | **57** |
| Mega irraggiungibili in MA | 6 | **1** |
| Mega mappati ma fuori roster | 1 | **0** |

- **aggiunte** `Chesnaught`, `Delphox`, `Emboar`, `Golurk`, `Greninja` — base e mega
  entrambe già nel roster verificato, quindi nessun dato inventato
- **rimosso** `Mega Machamp`: mappato ma fuori dal roster M-A di Champions, il team builder
  offriva una mega non legale
- copia di sicurezza in `data/archive/ma_pre-mega_map.json` e `mb_pre-mega_map.json`

### ✅ Chiuso l'11/08/2026 — ogni Mega nel roster è raggiungibile

`python scripts/completa_mega_map.py [--dry-run]`. Per ogni Mega del roster non ancora
mappata deduce la specie base dal nome (`Mega Raichu X` → `Raichu`), **verifica che
esista nel catalogo** e la collega; si ferma su ciò che non risolve.

| | prima | dopo |
|---|---|---|
| MA — Mega raggiungibili | 58 / 59 | **59 / 59** |
| MB — Mega raggiungibili | 58 / 75 | **75 / 75** |
| MB — roster | 295 | **308** |

- **`Mega Meowstic (Male)`** era l'unica irraggiungibile di MA, e la voce di backlog era
  **sbagliata**: diceva che la base `Meowstic` non è nel roster, ma cercava il nome
  sbagliato — dentro ci sono `Meowstic (Male)` e `Meowstic (Female)`, con le rispettive
  forme nel catalogo. Bastava collegarle: nessun dato inventato
- **MB non è più un segnaposto.** Delle 17 Mega irraggiungibili, 4 avevano la base già
  nel roster (Meowstic M/F, Raichu X/Y); per le altre 13 — Barbaracle, Blaziken,
  Dragalge, Eelektross, Falinks, Malamar, Metagross, Pyroar, Sceptile, Scolipede,
  Scrafty, Staraptor, Swampert — **Davide ha deciso di aggiungere la specie base al
  roster**. È una scelta di contenuto, non un dato dedotto, ed è per questo che lo
  script la fa solo per le regulation elencate in `AGGIUNGI_BASI`: il roster di **MA**,
  che viene dalla wiki di Pokémon Central, non si tocca

✅ **Mosse e oggetti di MB restano quelli di MA** — 460 e 58 — per decisione dell'11/08/2026.
MB è nata come MA più le Mega, e finché non c'è una fonte su cosa cambi davvero, copiare
MA è l'ipotesi meno arbitraria: la differenza fra le due regulation resta il **roster**.
Se un giorno salta fuori l'elenco vero, si passa dalla schermata contenuti o da uno
script di import dedicato, come è stato fatto per il roster di MA con la wiki.

> Volevo dirti quante mosse mancassero ai 29 Pokémon che MB ha in più, e non si può:
> vedi la voce qui sotto.

## ✅ Gli elenchi mosse per specie — importati il 12/08/2026

Era **il buco più grosso rimasto nei dati**: zero specie su 1026 avevano un elenco
`moves`, e non ce l'aveva nemmeno il vecchio `data/pokemon_catalog.json` (0 su 174) —
non una regressione dell'import, un dato che **non era mai esistito**.

`python scripts/importa_mosse_specie.py [--dry-run] [--solo main,champions]`, che scrive
`data/catalog/pokemon_moves.json` (2,7 MB). Rieseguibile e **idempotente**: due
esecuzioni di fila danno lo stesso md5. Si rifiuta di scrivere se le voci calano.

### La scoperta che ha cambiato il lavoro: Champions è nel dump

Non è stata usata la API REST di PokéAPI ma il suo **dump CSV**, lo stesso di
`build_catalog.py`: il moveset sta tutto in `pokemon_moves.csv`, quindi si scarica **un
file da 10 MB** invece di fare 1026 chiamate. E lì dentro, fra i version group, c'è
**`champions` (id 32): 19 810 righe su 319 voci.** Il moveset ufficiale di Pokémon
Champions esiste, ed è la fonte esatta di cui `ma` e `mb` avevano bisogno.

Quindi ogni voce ha **due elenchi**, non uno:

| | Da dove | A cosa serve |
|---|---|---|
| `main` | il version group più recente in cui la voce compare (862 su Scarlatto/Violetto, 167 su Spada/Scudo, poi a scendere fino a 6 su Rubino Omega) | la regulation `pokedex` |
| `champions` | il version group `champions` del dump | `ma` e `mb` |

**E non coincidono.** Il caso che Davide ha citato è verificato sui dati veri:
**Incineroar in Champions non ha Knock Off**, che in Scarlatto/Violetto impara con una
MT. Sono **11** le mosse che ha in S/V e non in Champions (`Knock Off`, `U-turn`,
`Tera Blast`, `Fire Pledge`…) e **8** quelle che ha solo in Champions (`Superpower`,
`Blaze Kick`, `Brutal Swing`…): 80 mosse contro 77.

Il valore di ogni mossa dice **come** si impara — `level-up:32`, `machine`, `egg`,
`tutor`, `train` (l'unico metodo di Champions) — così l'interfaccia può filtrare per
metodo senza un secondo import. Il livello si scrive sempre, `0` compreso: nel dump vuol
dire «all'evoluzione o dal ricordamosse», che è un'informazione, non un buco.

### La copertura, contata

| | roster | nomi irrisolti | con moveset | con la lista Champions |
|---|---|---|---|---|
| `ma` | 279 | **0** | **274** | **273** |
| `mb` | 308 | **0** | **302** | **301** |
| `pokedex` | 1343 | **0** | **1291** | 314 |

66 033 mosse in `main` (52 per voce in media) e 19 515 in `champions` (62). Canarini:
**Magikarp ha 3 mosse** (Splash, Tackle, Flail) e **Fulmine non è fra queste** — è il
caso che il backlog citava come impossibile da rifiutare.

### Chi resta fuori, e perché

- **20 forme inventate** — le Mega fan-made (`Mega Darkrai`, `Mega Zygarde`, i tre
  Tatsugiri, i due `… Z`), `Mega Meowstic (M/F)`, le tre taglie di Gourgeist ed
  `Eternal Flower Floette`. **Non ereditano il moveset della specie base**, per
  decisione di Davide del 12/08: sono escluse e dichiarate, non riempite a caso.
  Quando ci sarà la fonte si riaprono da lì
- ⬜ **32 forme Gigantamax** — nel dump non hanno un moveset proprio, condividono
  quello della forma base. **Da decidere**: farle ereditare (non sarebbe un'invenzione,
  è come PokéAPI le modella) o lasciarle vuote. Non toccano il VGC, quindi non urge
- ⬜ **`Pawmot`** ha `main` ma **non** la lista Champions, pur essendo nel roster di MA

> ⚠️ `PROJECT_CONTEXT.md` documentava `CHAMPIONS_BST` con un campo `moves: [...]` nella
> struttura di ogni voce: **non c'è mai stato**. Corretto l'11/08/2026.

> ⚠️ **Il file c'è, ma non lo legge ancora nessuno**: nessuna route, nessun endpoint,
> nessun JS. Il consumo è la voce qui sotto.

---

## ⬜ DA FARE — le mosse giuste per ogni regulation (aperta il 12/08/2026)

Chiesta da Davide il 12/08. Il dato ora c'è; manca l'uso.

Quando si cambia regulation, **le mosse mostrate per un Pokémon devono cambiare con
lei**. Su `pokedex` si vedono tutte quelle che quel Pokémon può imparare; su `ma` e
`mb` solo quelle legali lì. L'esempio di Davide, che è anche il caso di prova già
verificato nei dati: **Incineroar in M-A e M-B non può più imparare Knock Off**.

Dove va agganciato:

- il **calcolatore**, tab Danno: la casella mossa oggi accetta qualunque nome
- il **team builder**, che è il punto dove serve di più
- lo **Speed Tier**, dove le mosse non entrano ma le abilità sì (stesso schema)

Da decidere quando ci si arriva: se un Pokémon **non ha** un elenco per la regulation
attiva (le 20 forme inventate, `Pawmot` su Champions), si mostra tutto o niente.
Mostrare niente renderebbe inutilizzabili proprio le forme inventate di Davide, quindi
il default sensato è **tutto, con un avviso** — ma è una scelta sua.

> ⚠️ Questa voce **non** è la stessa cosa di «ogni Pokémon deve mostrare solo le sue
> abilità»: quella riguarda le abilità e ha ancora il problema del catalogo incompleto
> (238 specie con una sola). Qui il dato è completo al 98%.

---

## ⬜ DA FARE — ogni Pokémon deve mostrare solo le **sue** abilità (aperta l'11/08/2026)

Oggi selezionando un Pokémon nel calcolatore la tendina Abilità elenca **tutte e 386**
le voci del catalogo, con un ● su quelle che incidono sul calcolo. Devono comparire
**solo le abilità di quel Pokémon**.

**Il dato per farlo c'è già**, a differenza delle mosse: il catalogo tiene le abilità
per specie, sono **307 nomi distinti** e — dopo la fusione dei doppioni dell'11/08 —
risolvono tutti tranne uno. Il lavoro è quindi di interfaccia, non di import.

Dov'è oggi il comportamento giusto e dove no:

| Punto | Come si comporta |
|---|---|
| **Speed Tier** (`loadSpePkmn`, `calcolatori-speed.js`) | ✅ già così: riempie `spe_abil` con le abilità del Pokémon, tradotte, col ● su quelle che incidono. È il modello da seguire |
| **Tab Danno** (`atk_ability` / `def_ability`) | ⬜ `popolaSelectAbilita()` in `calcolatori-core.js` le mette tutte |
| **Stat Preview** (`stat_abil` / `stat_abil_b`) | ⬜ idem — le abilità del Pokémon sono lì solo come **testo** in `stat_abils`, non nella tendina |
| **Team builder** | ⬜ da verificare quando ci si arriva |

⚠️ **Da decidere prima di stringere le tendine**, perché è la ragione per cui finora
erano larghe: la copertura del catalogo è **incompleta**. Contato l'11/08/2026:

| Abilità per voce | Specie (1026) | Forme annidate (317) |
|---|---|---|
| nessuna | 2 | 14 |
| una sola | **238** | **173** |
| due | 345 | 51 |
| tre | 441 | 79 |

Quasi tutti i Pokémon reali ne hanno 2-3 con la nascosta: le **238 specie con una sola**
sono quasi certamente incomplete, non Pokémon con un'abilità sola. Stringere la tendina
senza colmare quel buco vorrebbe dire **togliere scelte legittime** invece di togliere
rumore. Due strade, da scegliere: completare prima le abilità da PokéAPI (stessa strada
degli elenchi mosse, con `build_catalog.py`), oppure filtrare subito lasciando un modo
per vedere tutte le voci — una spunta «mostra tutte», che è anche l'unico modo di usare
le abilità inventate di Champions su un Pokémon che non le ha in catalogo.

Da guardare nello stesso giro: **`Zero To Hero`** (l'abilità di Palafin) è l'unico dei
307 nomi che non risolve su nessuna voce del catalogo abilità.

---

## ✅ Clonare una regulation (10/08/2026)

Due modi, per non ricostruire a mano una regulation simile a una esistente:

- **In creazione**: nella modale "Nuova Regulation" c'è **Parti da** — vuota, tutto il
  catalogo, oppure copia da una regulation esistente
- **Su una regulation già creata**: nella sua pagina c'è **📋 Copia contenuti**, con
  il selettore della sorgente e le caselle per scegliere cosa copiare (Pokémon,
  mosse, oggetti, abilità, mega map). Serve proprio nel caso di `mb`, creata vuota

`id` e `label` della destinazione non vengono mai sovrascritti, la sorgente non può
coincidere con la destinazione, e la conferma elenca cosa verrà sostituito.
20 controlli end-to-end, con `mb.json` verificato identico dopo il ripristino.

---

## ✅ Regulation MA allineata a Pokémon Champions (10/08/2026)

Roster preso da
[wiki.pokemoncentral.it](https://wiki.pokemoncentral.it/Elenco_dei_Pokémon_di_Pokémon_Champions):
**208 → 279 Pokémon**, Speed Tier a 279 su 279 senza nomi irrisolti.

Rieseguibile con `python scripts/importa_roster_champions.py --dry-run` (scarica la
pagina da solo). Per la futura **M-B** basterà crearla — la creazione produce già il
formato a filtro — e spuntarne i contenuti da `/pokemon/regulation/<id>/contenuto`.

> ⚠️ Nota per me stesso: in una sessione precedente avevo giudicato "sospetto" questo
> roster perché mancavano Amoonguss, Rillaboom e Urshifu e c'erano Arbok, Ariados e
> Audino. **Era sbagliato**: Champions ha un roster suo e quelle presenze/assenze sono
> corrette. Non applicare assunzioni da VGC standard a Champions.

Dettagli tecnici dell'import:
- la wiki **non scrive il nome della forma**: la distingue solo per tipi e codice
  sprite (`Minim0026A` = Raichu di Alola, `Minim0745C` = Lycanroc Crepuscolo). Lo
  script mappa i suffissi e **si ferma** su ciò che non risolve, invece di indovinare
- forme puramente estetiche (Vivillon, Florges, Furfrou, Alcremie: 40 righe)
  collassate sulla forma base, perché per il calcolatore sono la stessa voce
- i 29 nomi "rimossi" erano alias sostituiti dai nomi canonici del catalogo
  (`Arcanine-Hisui` → `Hisuian Arcanine`, `Rotom-Wash` → `Wash Rotom`)
- **3 doppioni di specie** rimasti dall'import PokéAPI uniti: `palafin-zero`,
  `morpeko-full-belly` e `aegislash-shield` erano stati creati accanto alle voci
  curate `palafin-zero-form`, `morpeko-full-belly-mode` e `aegislash-shield-forme`,
  perché il nome curato non combaciava con quello ufficiale
- un baco preso al volo: **"Meganium" inizia per "Mega"** e finiva nel ramo delle
  Mega, risolto come "Mega Meganium". Ora il ramo Mega si attiva sul suffisso dello
  sprite (`M`/`MX`/`MY`), che è il dato affidabile

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
1. **Il roster di MA non contiene** Amoonguss, Rillaboom, Urshifu, Flutter Mane,
   Chi-Yu — riverificato 10/08/2026 sul roster ufficiale a 279. Non è un buco da
   colmare: Champions ha un roster suo e quelle assenze sono corrette (vedi la nota
   più sopra). Prima il calcolatore li offriva lo stesso perché `CHAMPIONS_BST` era
   globale; ora la regulation filtra davvero.

   ⚠️ **Conseguenza sulla regola #8**: il caso di prova canonico è Incineroar →
   **Amoonguss**, e Amoonguss non è più selezionabile in MA (Incineroar sì). Il caso
   va eseguito sulla regulation **`pokedex`**, che non filtra nulla. Da tenere a mente
   ogni volta che si valida una modifica ai calcolatori.
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
| ✅ | **19 Pokémon del roster MA assenti dal catalogo** | Chiuso 10/08/2026 dall'import Champions e dall'unificazione dei doppioni: **0 mancanti su 279**, verificato risolvendo l'intero roster MA contro l'indice del catalogo (top-level + `name` + forme annidate in `forms`). La voce era rimasta ⬜ per svista |
| ✅ | Dividere / snellire `calcolatori.html` | Fatto 08/08/2026. Da **1885 righe / 222 KB a 685 righe / 147 KB**, con **zero JS inline**: CSS in `static/css/calcolatori.css` e JS in 6 file `static/js/calcolatori-*.js` (data · core · danno · speed · stat · ui). I dati di Flask passano da un blocco `<script type="application/json" id="calc-bootstrap">`, lo stesso schema di `items_editor.html` |
| ✅ | Tabelle di riferimento duplicate in `calcolatori.html` | Fatto 08/08/2026. Le 4 righe da 108 KB sono ora 4 `<div>` vuoti riempiti da `calcolatori-ref.js` dagli **stessi dati del calcolo**: `TYPE_CHART` per l'efficacia, `NATURES` + `NM` per le nature. Template a **38 KB** |
| ✅ | DB ufficiale con TUTTI i Pokémon/abilità/mosse/oggetti di ogni generazione | Chiuso 11/08/2026. La regulation **Pokedex** esiste, non filtra nulla e dall'11/08 è pure il **default del sito**: 1343 Pokémon, 921 mosse, 398 oggetti, 391 abilità. Il **selettore regulation** c'è ora in ogni sezione: calcolatore e team builder l'avevano già, e i tre editor — mosse, oggetti, roster — l'hanno ricevuto oggi. Prima lì si cambiava regulation solo scrivendo `?reg=` a mano nell'URL |
| ⬜ | Creare i JSON di una nuova regulation dalla web app | Roster, mosse, oggetti e abilità generati in autonomia, magari agganciandosi a una fonte esterna. **Obiettivo di fondo: aggiungere una regulation senza IA, solo da interfaccia** |
| ✅ | Testare Speed Tier | Fatto 08/08/2026. `loadRegSpeed()` **non funzionava**: leggeva `bst.spe` mentre la velocità sta in `base_stats.spe`, quindi tutti i 174 Pokémon venivano scartati e la funzione ricadeva in silenzio sulla lista statica da 158 nomi. Ora costruisce 189 righe dal roster MA (208 nomi, 19 assenti dal catalogo) |
| ✅ | Weather Ball e mosse condizionate da meteo/abilità | Fatto 08/08/2026. Nuovo motore meteo in `calcolatori.html`: `meteoEffettivo()` (le abilità `weather_override` impongono il meteo, le `weather_setter` lo evocano se non è stato scelto nulla), `tipoPallaClima()` che usa `weather_ball_type` di `abilities.json` come override della mappa meteo→tipo, `applicaMeteoAllaMossa()` che riscrive BP e tipo nei campi visibili. Coperte **Weather Ball** (tipo dal meteo, BP 50→100), **Solar Beam** e **Solar Blade** (BP dimezzato con pioggia/sabbia/neve). Aggiunta la Pioggia forte alla tendina, con `fire_blocked` che porta le mosse Fuoco a 0 |

| ✅ | Traduzione di tutte le mosse/abilità/oggetti | Fatto 11/08/2026 con `scripts/importa_nomi_lingua.py` (PokéAPI) e `scripts/importa_nomi_wiki.py` (wiki di Pokémon Central, per i buchi di PokéAPI): `nome_it` e `nome_en` su tutte le voci dei quattro database. **Mosse e oggetti sono a posto al 100%**; sulle abilità restano 103 voci che sono un problema di doppioni, non di traduzione. Non serve una linguetta per scegliere la lingua dei database: la sceglie il pulsante `IT`/`EN` globale |

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

## 👥 UTENTI E PERMESSI (sezione nuova — 11/08/2026)

| | Voce |
|---|---|
| ⬜ | **Gestione utenti con permessi per sezione.** Poter aggiungere utenti **normali** e **amministratori**, e scegliere per ognuno quali sezioni può vedere, con una casella da spuntare per sezione (Pokémon, Gaming, Arduino, PC Builder, Python, Stampa 3D…). Obiettivo: far entrare altre persone nella web app facendo vedere loro solo ciò che le riguarda |

Punti di partenza già presenti: la tabella `users` ha **già** la colonna `role`
(`DEFAULT 'user'`, e l'utente `admin` è creato con `role='admin'`), ma **nessuno la
legge**: `login_required` in `extensions.py` controlla solo che ci sia `username` in
sessione. Servono quindi una tabella o una colonna per i permessi di sezione, un
decoratore che li verifichi, la sidebar che nasconda le voci non permesse, e una
schermata di amministrazione per gestirli.

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
| | Voce | Note |
|---|---|---|
| ✅ | Collegamento a una API Steam per tracciare i videogiochi | Fatto 10/08/2026. Tre pezzi, vedi sotto |
| ⬜ | Suggerimenti giochi in base a cosa si sta giocando | Ora c'è la materia prima: 34 giochi con generi e ore. Steam **non** espone "giochi simili", quindi serve decidere la fonte: suggerire dalla libreria stessa (per genere e ore), o agganciare un servizio esterno |

### Steam — cosa è stato fatto (10/08/2026)

**1. Ricerca in fase di inserimento** — su `/gaming/new` un campo cerca su Steam e un clic
compila titolo, genere, copertina e piattaforma, collegando l'`appid`. Endpoint pubblici,
**nessuna chiave**: `storesearch` e `appdetails` (generi già in italiano).

**2. Import della libreria** — `/gaming/steam`: legge i giochi posseduti con le ore giocate.
È l'unico pezzo che richiede una chiave (`GetOwnedGames` risponde 401 senza).
Deduplica sull'`appid`, un reimport aggiorna le ore e non crea doppioni.

**3. Arricchimento generi** — l'import di massa non porta i generi (sarebbero N chiamate
in più): un pulsante li chiede a Steam a lotti di 15. Anche questo senza chiave.

Dettagli che vale la pena ricordare:
- **`hours_played` è una colonna nuova, distinta da `hours_hltb`**: le ore giocate non
  sono la stima di durata HowLongToBeat. L'import non tocca mai `hours_hltb`
- la chiave si legge **solo** da `os.environ["STEAM_API_KEY"]`: nessun campo
  nell'interfaccia, nessun file nel progetto, niente in git
- il **nome visualizzato Steam non è risolvibile**: l'API risolve solo l'indirizzo
  personalizzato (`/id/<vanity>`), che molti profili non hanno. Il campo accetta URL
  completo e steamID64, ed è la strada consigliata
- ⚠️ **trappola d'ambiente**: un processo Windows eredita una *copia* dell'ambiente. Se la
  app parte prima che `STEAM_API_KEY` esista, non la vedrà mai. La pagina lo rende
  diagnosticabile: guida gialla = il processo non ha la chiave, form = ce l'ha
- errore di mappatura corretto in corsa: l'import metteva `ore > 0 → In corso`, e con 33
  giochi il filtro per stato diventava inutile. Ora tutto entra come **Pausa**

---

## ⚙️ GENERICO
| | Voce |
|---|---|
| ⬜ | Deploy da GitHub a Railway — c'è un errore da diagnosticare |
| 🟨 | **Switch lingua italiano ⇄ inglese.** Pulsante `IT`/`EN` in `base.html` accanto al tema: fatto l'11/08/2026, **primo blocco chiuso** (i nomi dei dati). Resta da fare il **secondo blocco**: le stringhe dell'interfaccia, oggi italiano fisso in ~19 template. Vedi la sezione dedicata in cima al file |

---

## 🔧 Emerso dal codice (non nel docx)

| | Voce | Note |
|---|---|---|
| ✅ | Formattazione editor mosse/oggetti/roster | Fatto 07/08/2026. Il banner "Stai modificando" stava dentro la griglia e occupava la colonna larga: la tabella mosse aveva 373px su 838 necessari (465 tagliati). Ora a tutta larghezza |
| ✅ | `textarea.form-control` batte `.code-area` | Fatto 10/08/2026. In `base.html:95` la regola `textarea.form-control{min-height:70px}` ha specificità elemento+classe e vinceva su `.code-area` a prescindere dall'ordine. I template colpiti erano **5, non 3**: oltre a abilità, mosse e oggetti anche `roster_editor.html` e `arduino.html` (anche il campo codice Arduino era a 70px invece di 260). Aggiunta in ognuno la riga `textarea.code-area{min-height:…}` accanto alla regola esistente, lo stesso pattern già presente in `catalog_editor.html:16`. `base.html` non è stato toccato: la regola a 70px resta giusta per le textarea normali |
| ✅ | Editor abilità senza archivio né backup | Fatto 08/08/2026. Archivio manuale, elenco, ripristino e **copia automatica prima di ogni salvataggio**. Ora l'editor abilità è il più protetto dei quattro |
| ✅ | Colonne tab Danno del calcolatore | Chiuso 11/08/2026: `align-items` da `start` a `stretch`, una riga. I tre riquadri chiudevano a **548 / 699 / 564** px, ora tutti a **699**. Le larghezze non cambiano (360 · 265 · 360): il prezzo è un fondo vuoto di ~150 e ~135 px nei due laterali, perché la colonna Condizioni ha più campi delle altre. Deciso guardando il confronto misurato a 1280px |
| ✅ | Nessun `.gitignore` | Fatto 10/08/2026. Creato `.gitignore` (`__pycache__/`, `*.py[cod]`, venv, `hub.db`, file di editor/OS) e tolti dall'indice `hub.db` + **13** `.pyc` con `git rm --cached`: i file restano su disco, git smette di seguirli. Gli archivi in `data/archive/` sono stati **lasciati tracciati** di proposito — sono la rete di sicurezza dei salvataggi, non scarto di build |
| ⬜ | `main` diverge da `origin/main` | Locale avanti 2 / indietro 4. I commit remoti contengono un marker di conflitto e hanno perso `PROJECT_CONTEXT.md`. Riallineare richiede force-push |
| ✅ | `reference.html` era orfano | Rimosso l'11/08/2026: 70 righe che nessuna route renderizzava. Il tab Reference del calcolatore è un'altra cosa — vive dentro `calcolatori.html` ed è riempito da `calcolatori-ref.js` |
| ✅ | 53 `onmouseout` morti in `templates/python.html:45` | Chiuso 11/08/2026. Il ramo `{% else %}` aggiungeva due apici dentro una stringa già quotata (`this.style.background=''''`, `SyntaxError`), quindi su ogni argomento **non** completato l'handler era `null`. Tolti i due apici: da **0 handler vivi su 53 a 53 su 53**, provato eseguendo mouseover/mouseout |
| ✅ | `loadSpePkmn()` non ricalcola | Chiuso 11/08/2026: aggiunta la chiamata a `updateSpeed()`. Incineroar → base 60, Velocità **80**; Dragapult → base 142, Velocità **162** |
| ✅ | Speed Tier senza limite di righe | Chiuso 11/08/2026 con un tetto a **300 righe**, come le altre tabelle del progetto: su `pokedex` erano **1343 righe / 714 KB** in un solo `innerHTML`, ora **300 / 159 KB**. Le righe tagliate sono le più **lontane** dalla propria Velocità, perché chi guarda uno Speed Tier guarda chi gli sta intorno: con Kingdra a 105 la tabella va da 95 a 115. Sopra la tabella resta scritto il conto pieno (`300 righe su 1343`), e la ricerca continua a pescare fuori dal taglio — provato con Regieleki, che sta a 200 |
| ✅ | Nomi in `abilities.json` da rivedere → **fondere i doppioni** | Chiuso 11/08/2026: 24 coppie fuse, 415 → 391 voci, e `abilityEffect()` ora risolve anche per nome inglese. Dettagli nella sezione «Le abilità doppie», in cima. ⚠️ Restano le 10 voci il cui effetto non corrisponde a nessuna abilità reale, tenute apposta | Alcuni non corrispondono all'abilità descritta (es. `Spettroguardia` descrive Multiscaglia; il vero Wonder Guard è `Magidifesa`). Convivono nomi ufficiali IT e nomi di altra fonte. L'11/08/2026 il giro sulla wiki ha spiegato perché: **le due famiglie coesistono nello stesso file**, 307 voci col nome ufficiale (collegate ai Pokémon, ma solo 22 con un effetto attivo) e 108 vecchie (34 con l'effetto che il calcolatore usa davvero). Il lavoro non è tradurre, è fondere ogni coppia. Dettagli e tabella nella sezione dello switch lingua, in cima |
| ⬜ | **`build_catalog.py` oggi distruggerebbe il catalogo** ⚠️ | Trovato il 12/08/2026 preparando l'import delle mosse, **non corretto** perché fuori scope e perché non è più servito eseguirlo. Lo script legge come base i **file storici** (`data/pokemon_catalog.json`, `moves_ma.json`, …) e scrive il risultato in `data/catalog/`. Quella base ha **174 voci** contro le 1026 di oggi, non ha nessun `nome_it`/`nome_en` (il catalogo attuale li ha su 1026 su 1026) e ha ancora le **Mega convertite**: `Mega Venusaur` vale `hp 155` lì e `hp 80` qui. Peggio, `MEGA_BONUS` riapplicherebbe `+75 HP / +20` alle Mega nuove, cioè esattamente la conversione che la deconversione dell'11/08 ha tolto. Rieseguirlo oggi **riporterebbe indietro il catalogo di quattro giorni di lavoro, in silenzio**. Va fatto leggere `data/catalog/` quando esiste, e `MEGA_BONUS` va tolto. Fino ad allora, **non eseguirlo** |
| ⬜ | Catalogo con abilità incomplete | Ricontato 11/08/2026 sul catalogo di oggi: **238 specie su 1026** hanno una sola abilità e 2 nessuna, più **173 forme annidate su 317** con una sola. Quasi tutti ne hanno 2-3 con la nascosta. ⚠️ È il **prerequisito** della voce «ogni Pokémon deve mostrare solo le sue abilità», in cima: stringere le tendine prima di colmare questo buco toglierebbe scelte legittime |
| ✅ | Chiavi mega incoerenti nel catalogo | Chiuso 11/08/2026. Non erano anomalie ma **doppioni**: `mega-banette`, `mega-chimecho` e `mega-crabominable` esistevano sia come chiave top-level sia come forma annidata nella specie base. Le forme annidate, deconvertite, sono quelle giuste — le top-level sono state rimosse (1029 → 1026 voci). Gli override sprite in `api_pokemon.py:70-73` **restano**: sono indicizzati sul nome normalizzato, non sulla chiave, e servono ancora perché Mega Chimecho e Mega Crabominable sono inventate e non hanno uno sprite online |

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
