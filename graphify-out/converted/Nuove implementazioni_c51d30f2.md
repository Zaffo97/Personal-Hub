<!-- converted from Nuove implementazioni.docx -->

https://github.com/Zaffo97/Personal-Hub.git

POKEMON (dalla 1.0 alla 7.0)

- Fargli controllare le BST perché non sembrano corrette – dargli le BST con già le IVs impostate perché in Champions sono già 31 – segui l’esempio di Game8 - fatto
- Rimuovere IVs, non servono più perché sono fisse a 31 – fatto
- Vedere se manca qualcosa nel calcolatore - tailwind/trick room , campo nebbioso (folletto) , l’aumento di stage ATK dovrebbe essere x1.5,x2,x2,5,x3,x3.5,x4. Vorrei anche quindi aumento stage per SP ATK e quindi anche da aggiungere stage DEF e SPDEF del pokemon difensore. Riesci a distinguere la selezione dello stage in base alla mossa selezionata? Disabilita uno dei due campi in base alla mossa – fatto
- Filtri per cercare mosse e pokemon - fatto
- Cosa significa la voce Spread nei calcolatori? Riesci a vedere se è corretta come voce? – fatto
- Mettere visibile la possibilità di modificare i pokemon qualora cambi la regulation quindi il roster – fatto
- Mancano tutte le mega nei vari calcolatori - fatto
- Confronta pokemon nella sezione stat preview – fatto
- Il tipo mossa selezionato deve prendere in automatico il tipo mossa senza che tu debba selezionarlo - fatto
- Aggiungere la descrizione delle mosse nel roster – fatto
- Distinzione tra la voce base e il secondo numero nelle stats, a cosa serve? - fatto
- Editor Roster e editor mosse, sulle nuove aggiunte devono fare il controllo sul nome per poter aggiungere tutte le caratteristiche che servono, se il nome non esiste restituire messaggio di errore.
Trovare anche il modo di aggiornare automaticamente quando la regulation cambierà. Salvare quindi la vecchia regulation a parte per poterla ripescare in futuro – fatto

POKEMON (dalla 10.0 alla
- Nelle stat preview in una versione vecchia avevi messo il confronto tra pokemon, puoi ripristinarlo?
Ti chiederei di inserire la colonna relativa alla statistica del pokemon B appena sotto a quella del pokemon A per rendere più chiaro il confronto – fatto – 10.0
- Ripristina il colore delle stats nello stat preview e cambialo mettendo due colori solo nel caso del confronto tra pokemon A e pokemon B – fatto – 10.0
- Mancano tutte le mega evoluzioni nei vari calcolatori e quindi le loro statistiche in base alle selezioni fatte, pensi di riuscirci? Sarebbe fondamentale per i calcoli e poter confrontare i pokemon anche in base alle loro mega evoluzioni. Ricorda sempre il discorso delle IVs già applicate di default e se serve potresti guardare il sito di Game8 -> Pokemon Champions -> Pokemon List -> tabelle Stats (Max IVs) – fatto -10.1
- Sezione / tabella di confronto dei tipi di pokemon, che aiuti a capire debolezze e resistenze e Sezione / tabella di confronto delle nature dei pokemon – creiamo un overlay con bottoni per i calcolatori e una sezione Reference per il richiamo di questi dati e eventuale aggiunta di tabelle per BST e tier list – fatto– 10.2

- Pulsante Salva team anche in alto quando creo il team – fatto – 10.2

- La schermata del calcolo effettivo del danno nella sezione danno, una volta calcolato, vorrei comparisse sopra le schermate di attaccante e difensore – fatto – 10.2

- Servirebbe un editor oggetti, controllare la lista degli oggetti disponibili in regulation M-A, creare un organizzatore come gli altri editor con effetti e descrizione degli oggetti, e fare in modo che siano archiviabili e modificabili come gli altri 2 editor.
Controllare anche che in tutti i calcolatori ci siano gli oggetti della regulation M-A
Cercare anche in modo tale che, qualora si archiviano gli oggetti, vengano poi direttamente sostituiti dai nuovi nei calcolatori dove posso selezionarli e nella gestione dei team – fatto– 10.3

- Controllare, non ci sono esattamente gli oggetti della regulation M-A – fatto – 10.3
- Nelle stat preview a sinistra ci sono dei valori e a destra degli altri, mi spieghi a cosa servono quelli di sinistra? Quelli di sinistra sembrano non corretti, puoi eliminarli e spostare il numero di destra al loro posto? – fatto – 10.4

- Aggiungi BST totali nelle stat preview, la somma di tutte le statistiche - fatto - 10.5

- Logica che ti impedisca di mettere più di 66 EVs totali e in un campo il massimo che puoi inserire è 32 – fatto – 10.5
- Sostituzione delle icone varie tipo leone, zzz ecc con qualcosa più inerente ai pokemon e alla sezione specifica -fatto– 10.6



REGULATION – 11.0
- Regulation – devo poter recuperare l’intera regulation con oggetti, mosse e roster, nel caso abbia bisogno di buildare un team di una regulation particolare. Quindi, assegnare agli editor la regulation in corso. Capire quindi se devi fare un editor Regulation che comprenda gli altri editor. – fatto – 11.0

- Db dinamico che, quando crei il team, selezioni la regulation.- fatto -11.0

- Creazione team in base alla regulation. Riesci ad accedere direttamente ai dati specifici in base alla regulation scelta? – fatto – 11.0

- In base alla regulation, ti cambia la selezione dei possibili pokemon mosse e oggetti in base a cosa contiene quella regulation – fatto – 11.0

- Aggiungere editor JSON per il cambio di regulation, in modo tale da poter fare la modifica direttamente da web app senza passare dal codice – fatto– 11.0a

- Editor Regulation MA deve essere posizionato come pulsante dove sono gli altri – quando entro nella sezione Pokemon. Perciò, non mi interessa avere queste sezioni nel menu a sisnistra – fatto -11.0b

- Quando entro nell’Editor Regulation, come faccio a creare una nuova Regulation? Manca un pulsante “Crea nuova Regulation”? – fatto – 11.0b

- Serve comunque un pulsante per eliminare la Regulation da regulations.json e gli altri json relativi alla Regulation che voglio eliminare – fatto – 11.0c 11.0d

CONTINUARE CON ALCUNE MODIFICHE – 12.0
- Da fare tranquillamente a mano -> In app.py, alla fine del file dove trovi la riga
if __name__ == '__main__': 
app.run(debug=True, port=8080)

cambiala e metti

if __name__ == "__main__":
- app.run(host='0.0.0.0', debug=True, port=5000) -> per eseguirlo in locale su altri dispositivi –>               provare poi sul telefono - fatto

- Le statistiche delle mega in generale in tutti i moduli del programma sono sbagliate. Le statistiche delle mega non tengono conto delle IVs al massimo. – fatto– 12.0

- Calcolatore danno: il Pokèmon difensore deve prendere in automatico il tipo 1 e il tipo 2 se lo possiede, in modo tale da permettere il calcolo corretto in base alla mossa. Gestire bene anche in caso in cui il Pokemon sia solo di 1 tipo.
Il calcolatore tiene già conto della mossa STAB? Rivedere il calcolo in base a STAB, debolezza e resistenza del Pokemon difendente. – fatto – 13.0

- Rivedere il calcolo in generale perché ci sono delle differenze di calcolo tra il mio e quello di Pokemon Damage Calculator. - fatto – 13.4

- E probabilmente bisogna riguardare il calcolo danno tra le mega, mi sembrano non corretti, se ti serve posso farti un esempio. Noto che delle mega non prende le spread giuste – fatto – 13.5

- Alcuni HP dei Pokemon in generale con IVs al max non sembrano corretti.
Se applico le EVs non sembra fare i calcoli corretti
FIX totale, spostamento in un json generico dei pokemon per migliorare il ragionamento del programma – in corso – 14.0 – fix lungo - fatto

- Spostare pulsante calcolo in alto -14.1 - fatto
- Dovrò poter aggiungere una nuova regulation direttamente dalla web app – 14.2 – fatto

ABILITA’ – 15.0
- Aggiungere editor abilità, controllare quindi che agiscano sul calcolo danno/speed tier/stat preview.
- Un unico editor abilità, che non necessita di essere cambiato con la regulation, perché di fatto i Pokemon in teoria non cambiano abilità nel tempo, potrebbe cambiare soltanto il ragionamento dell’abilità stessa.
Possibilità di aggiungere nuove abilità, anche tramite editor JSON come per gli altri editor.
Aggiungere quindi filtro e ricerca abilità.

- Abilità: devi cercare di gestire gli esempi particolari nel calcolatore danno. Ad esempio Mega Meganium con la sua abilità, Mega Sol, colpisce l’avversario come se fosse sotto Sun, non viene quindi condizionato ad esempio dalla Rain. Sempre in questo caso quindi, anche la mossa Weather Ball diventerebbe di fuoco.
Valutare quindi se è necessario aggiungere nell’editor mosse anche le altre Weather Ball e fare in modo che l’abilità selezionata nel calcolo danno incida sul calcolo finale del danno. – fatto -15.0


REVISIONE FINALE POKEMON

- Ho modo di dividere calcolatori.html o comunque gestirlo meglio per fare in modo che sia più snello 
e organizzato? Vorrei farlo anche per permetterti di leggere l’intero file quando te lo passo

- Vorrei aggiungere dei db ufficiale contenente TUTTI i pokemon, abilità, mosse e oggetti conosciuti di tutte le generazioni.
Sarebbe il caso di dedicargli quindi una regulation a parte, chiamata Pokedex.
  Ogni volta che entro nelle sezioni dei pokemon, voglio che ci sia un selezionatore per la Regulation in questione (al momento ce ne sono 2 su Pokemon Champions – M-A e M-B)
Selezionando la regulation, accedo al json interessato dei pokemon, mosse, abilità e oggetti della regulation, sia dei calcolatori, sia dei team, sia degli editor.
Le statistiche dei Pokemon devono essere calcolate secondo il nuovo formato di Champions, quindi 66 punti massimi in totale, 32 massimi per statistica
Voglio quindi aggiugere tutti gli sprite.
Tutto questo perché in futuro devo avere la comodità di aggiungere una nuova regulation senza l’uso della IA, ma tutto tramite la web app
- - testare Speed Tier, ci sono alcune sezioni sbagliate e che non effettuano comunque il calcolo giusto. - nello speed tier prima mi facevi visualizzare il calcolo dei pokemon in generale. Vorrei una speed tier dedicata alla propria regulation, ovvero che carichi il confronto con i pokemon di quella regulation 

- Testare calcolo Danno:
Stab - ok
Terreni?
- Burn?
- Reflect/Light Screen?
- Helping Hand?
- Critico?
- Mancano le varie Weather Ball, o comunque fare in modo che vengano condizionate dal meteo o eventuali abilità.

- Nuova regulation, come farò ad aggiungere comodamente nuovi json del roster, delle mosse e degli oggetti e delle abilità? Potrà l’app costruirmeli in autonomia matchando magari con qualche sito?
- Sprites Mancanti

SALVATAGGIO LOG

- Aggiungere una funzione salvataggio log



NUOVA PARTE DA AGGIUNGERE – STAMPA 3D
- Aggiungere una nuova sezione stampa 3D
Vorrei che fosse come quella per Arduino, si riesce a richiamare un sito per disegnare?
Vorrei salvarmi i progetti lì sopra sempre come la sezione di Arduino
ARDUINO
- Richiamo a Tinkercad per poter disegnare il progetto e vedere se i connettori ecc. sono funzionanti.

PC BUILDER
- Wishlist amazon o altri?
- Prezzo componente?
- Percentuale di compatibilità tra i pezzi? Potresti usare il sito UserBenchmark?
- Come faccio in futuro se escono nuovi pezzi?
PYTHON
- Pensare a cosa posso integrare per renderlo più figo
- Uno spazio dove sarebbe possibile inserire tutti i miei progetti e testarli in qualche modo se possibile.
- Provare a chiedere direttamente a Claude/Perplexity come può essere migliorabile e più utile
GAMING
- Mancano i suggerimenti giochi in base a ciò che sto giocando
- Collegamento a qualche api di Steam per tracciare i videogiochi

GENERICO
- Come caricare il progetto da GitHub a Railway – ho un errore