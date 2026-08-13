# Istruzioni per Claude — Personal Hub

Questo file viene caricato **da solo** all'inizio di ogni sessione: qui stanno le
regole che valgono sempre. Il *cosa* fare sta in `BACKLOG.md`, il *com'è fatto* in
`PROJECT_CONTEXT.md`, e quello che è **già stato fatto** in `STORICO.md`.

> ⚠️ **Leggi `BACKLOG.md`, non `STORICO.md`.** Dal 13/08/2026 sono due file: nel backlog
> c'è **solo ciò che è aperto** (~370 righe), più le trappole note che vanno rilette prima
> di toccare una zona. Lo storico è una riga per lavoro chiuso, con la data e i numeri:
> si apre **solo** per rispondere a «questo l'avevamo già fatto, e com'è andata?», non
> all'inizio di una sessione.

---

## 🏆 REGOLA D'ORO — mettere al sicuro il lavoro

**Dopo ogni blocco di lavoro completato e verificato, chiedi a Davide di pushare.**
Non aspettare che te lo dica lui: proponilo tu, subito dopo aver committato.

Vale anche quando si sta chiudendo la sessione, o quando Davide dice che ha finito.

**Prima di proporre il push, due cose, in quest'ordine.**

**1. Aggiorna `BACKLOG.md` e `STORICO.md`** con quello che è successo nella sessione.
Cosa resta **sospeso** va nel backlog — le voci aperte, i casi da decidere a mano, i
bachi trovati e non corretti perché fuori scope. Cosa hai **chiuso** esce dal backlog e
diventa **una riga** in `STORICO.md`, con la data e i numeri della verifica: è la potatura
del 13/08/2026, e si mantiene sola solo se la fai ogni volta. Se una voce esisteva già,
spostala o correggila invece di scriverne una seconda.

Non è un doppione della regola #5 ("tieni aggiornati `BACKLOG.md` e `PROJECT_CONTEXT.md`
insieme al codice"): quella dice *quando* scrivere, questa è il **controllo prima di
spingere**. Un push che porta su GitHub del codice senza il backlog aggiornato lascia il
lavoro senza la sua spiegazione, ed è proprio quando serve — alla sessione dopo, che di
questa non ricorda niente. Se non c'è niente da aggiungere, dillo esplicitamente a
Davide invece di saltare il passo in silenzio.

**2. Esporta i dati:**

```bash
python scripts/esporta_dati.py
```

`hub.db` è escluso da git — è un binario e dentro c'è l'hash della password — quindi
la libreria giochi importata da Steam, i team, i progetti Arduino e le build del PC
**non avrebbero nessuna copia su GitHub**. Lo script ne scrive una leggibile in
`data/backup/hub_export.json`, che invece viene committata. Se non è cambiato niente
lo dice e non tocca il file, quindi eseguirlo è sempre sicuro. Le password non
finiscono nell'export, di proposito.

> ⚠️ Nota onesta sul perché la regola è scritta così: **non ho modo di sapere quanti
> token restano.** Non posso accorgermi di essere "verso la fine". L'unico innesco su
> cui posso contare è **il commit**: se ho appena committato, propongo il push.

**Due zone, sempre:**

| Branch | A cosa serve |
|---|---|
| `sviluppo` | **zona test** — ci finisce ogni blocco di lavoro, anche intermedio |
| `main` | **ufficiale** — solo roba verificata, e solo quando Davide lo dice |
| `archivio/…` | fotografie da non toccare mai più, tenute per poter tornare indietro |

Più un **tag** a ogni blocco chiuso (`git tag lavoro-2026-08-11-mega`), che è il modo
per tornare a uno stato esatto senza dover cercare un hash.

Il push **lo autorizza Davide ogni volta**: tu lo proponi, dicendo cosa stai per
spingere e su quale branch. Non spingere mai su `main` di tua iniziativa, e non usare
`--force` senza un sì esplicito e specifico.

Sistemato l'11/08/2026: `main` era fermo a giugno (il `calcolatori.html` da 205 KB
con il JS inline) e i suoi 9 commit non contenevano nessun sorgente che non fosse già
nel lavoro. Ora `main` e `sviluppo` hanno lo stesso contenuto, e la fotografia di
giugno vive su `archivio/main-giugno-2026`.

---

## 📐 Le regole di lavoro di Davide

1. Non modificare nulla **fuori dallo scope** richiesto, e non fare refactoring di
   funzioni non citate. Se trovi un altro baco: **segnalalo, non correggerlo di tua
   iniziativa** — a meno che senza quella correzione la verifica di ciò che ti è stato
   chiesto sarebbe una bugia. In quel caso correggi e **dillo chiaramente**.
2. Non inventare nomi di file, variabili, ID HTML o route. Se c'è ambiguità, chiedi.
3. **Non inventare dati.** Se il nome italiano di una forma o le stat di una Mega non
   sono deducibili da una fonte, si lasciano com'è e si segnalano. Meglio una lacuna
   dichiarata di un valore plausibile e falso.
4. Rispetta le convenzioni già presenti (vedi "Convenzioni" in `PROJECT_CONTEXT.md`).
5. Tieni aggiornati `BACKLOG.md` e `PROJECT_CONTEXT.md` insieme al codice, nella stessa
   sessione. Il log delle sessioni sta in fondo a `PROJECT_CONTEXT.md`.

---

## 🧪 Verificare, non dedurre

**Regola #8 — ogni modifica ai calcolatori va provata con un caso noto** prima di
considerarla finita:

> Incineroar (atk base 115) Adamant, 32 SP atk, Lv.50 → Amoonguss (def 70, hp 114),
> mossa fisica Buio BP 100.
> Atteso: **A=183, D=122, HP=221, danno 85-102 (38.5%–46.2%)**.

Va eseguito sulla regulation **`pokedex`**: Amoonguss non è nel roster di MA.

Altre abitudini che in questo progetto hanno già ripagato:

- dopo ogni modifica ai template, **renderizza le pagine ed esegui `new Function()`**
  su ogni blocco `<script>` **e su ogni handler inline** (`onclick`, `onsubmit`, …).
  Qui un `SyntaxError` in un attributo ha tenuto morto il Ripristina del roster, e uno
  in un `<script>` ha tenuto morto l'intero PC Builder per settimane
- diffida dei **fallback silenziosi**: più di un baco qui non dava errore, dava il
  numero sbagliato (lo Speed Tier che ricadeva su una lista statica, `/api/moves` che
  leggeva il file di MA, un nome inesistente che rispondeva Mega Venusaur)
- misura prima di proporre. I numeri in questo repo sono stati contati, non stimati

**Il grafo è una fotografia, non uno specchio.** `graphify-out/` viene da un `/graphify`
già passato, e non si aggiorna da solo. Prima di rispondere a una domanda
sull'architettura usandolo, confronta la data di `graphify-out/graph.json` con l'ultimo
commit che ha toccato il codice: se è più vecchia, `/graphify . --update`, che
**ri-estrae solo i file cambiati** (`manifest.json` tiene `mtime` e hash di ognuno) e
costa una frazione di un giro completo. Non va rifatto a ogni sessione — solo quando il
grafo serve davvero, e **obbligatoriamente** prima del giro di collaudo finale e
dell'inventario del codice morto, che sono i due lavori in cui deve essere completo.

---

## 💾 Toccare i dati

- il catalogo si scrive **solo** con `salva_catalogo()`, le abilità **solo** con
  `_save_abilities()`: è lì che vive la copia di sicurezza automatica
- **le chiavi del catalogo non si rinominano.** Le usano i filtri delle regulation, il
  motore degli effetti e i team salvati nel DB. Per cambiare ciò che si legge a schermo
  ci sono `nome_it` e `nome_en`
- ⚠️ **due chiavi diverse possono avere lo stesso `nome_it`/`nome_en`**, quindi la
  risoluzione per nome è ambigua: `Sheer Force` esiste come `Forza Bruta` e come
  `Forzabruta`. `indiceNomi()` a parità di nome tiene la voce che ha un `effect`; i
  doppioni veri sono elencati in `BACKLOG.md` e vanno fusi, non aggirati
- gli script in `scripts/` sono **rieseguibili** e hanno `--dry-run`. Uno script che
  modifica dati curati deve rifiutarsi di farlo alla cieca e lasciare una copia in
  `data/archive/`

---

## 🗣️ Come parlare

Italiano. Davide conosce il progetto: niente ripassi di cose che sa già, niente elenchi
di opzioni che non seguirai. Se una cosa è stata verificata dillo con i numeri; se non
lo è stata, dillo pure.
