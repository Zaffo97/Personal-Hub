# -*- coding: utf-8 -*-
"""Elenca ogni query sui contenuti e dice quali **non** filtrano per proprietario.

Dal 19/08/2026 le righe di `games`, `teams`, `arduino_projects` e `pc_builds` hanno
un `user_id`: ogni utente vede le proprie, l'amministratore vede tutto. Il punto
debole non è il meccanismo, è il **numero**: le query che toccano quelle tabelle
sono decine, e dimenticarne una mostra i dati di un altro **senza che nulla lo
segnali** — nessun errore, nessuna pagina rotta, solo una riga di troppo in elenco.

Questo script rende rumoroso quel silenzio. Legge i blueprint con `ast`, tira fuori
ogni stringa SQL che nomina una tabella di contenuto e la mette in una di tre file:

  * **filtrata**  — la query nomina `user_id`: si fida
  * **dichiarata**— sta in `ECCEZIONI` qui sotto, con scritto **perché** è giusto
                    che veda tutto (di solito: è un dato condiviso, o una route da
                    amministratore)
  * **scoperta**  — nessuna delle due. È il lavoro che resta

    python scripts/controlla_proprietario.py            # il riassunto
    python scripts/controlla_proprietario.py --tutte    # anche le filtrate, per rilettura

⚠️ La chiave di `ECCEZIONI` contiene il **testo della query**. Se qualcuno la cambia,
l'eccezione smette di combaciare e la query torna «scoperta»: è voluto. Un'eccezione
che segue in silenzio le modifiche non sarebbe una rete, sarebbe un cerotto.

**Cosa resta fuori dal raggio, e perché** (scritto qui dal 10/09/2026, prima era solo
un silenzio): le sorgenti sono `blueprints/` e i `.py` della radice, e la scansione
**non è ricorsiva**. Quindi `scripts/` non viene guardato — ed è giusto: uno script da
riga di comando **non ha una sessione**, `ambito_utente()` lì non vuol dire niente, e
per definizione lavora su tutto il DB, perché è per questo che lo si lancia. Ma un
silenzio somiglia troppo a una svista: da oggi gli script che nominano una tabella di
contenuto vengono **contati e nominati** in fondo al riassunto, come categoria
dichiarata. Se ne compare uno che non ti aspetti, quello va letto.

Esce con 1 se resta anche una sola query scoperta.
"""
import argparse
import ast
import io
import os
import re
import sys

# La console di Windows e' cp1252 e non sa scrivere gli accenti di questi messaggi.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORGENTI = [os.path.join(BASE, "blueprints"), BASE]

# Le quattro radici hanno la colonna. I due figli il proprietario lo **ereditano**
# dal padre con una join, quindi una query su di loro è a posto se passa per l'id
# del padre — che a sua volta va filtrato: per questo restano in elenco.
# ⚠️ `python_progress` entra il 22/09/2026, **insieme al codice che la tocca** — il
# travaso di `admin.py`, che prima la dimenticava. Fino a quel giorno era fuori dal
# raggio, quindi le sue 6 query non erano né filtrate né scoperte: non esistevano, e
# questo script diceva «0 scoperte» senza averle guardate. È la terza volta che
# succede (le due del Fantacalcio il 21/09), ed è la ragione per cui una tabella
# nuova si aggiunge qui **prima** di scrivere la query che la usa.
# ⚠️ `sessioni_ricordate` entra il 22/09/2026 **insieme alla tabella**, prima ancora
# che una sua query esistesse: è la regola scritta qui sopra applicata per la prima
# volta al momento giusto invece che un mese dopo. E qui vale doppio — una query
# scoperta su questa tabella non mostrerebbe una riga di troppo in un elenco, darebbe
# a qualcuno la sessione di qualcun altro.
# Stampa 3D, dal 25/09/2026: entrano **insieme alle tabelle**, prima della prima query.
RADICI = ("games", "teams", "arduino_projects", "pc_builds", "fanta_leagues",
          "python_progress", "sessioni_ricordate",
          "stampa_progetti", "stampa_filamenti",
          "python_progetti", "python_note", "python_frammenti")
FIGLIE = ("team_members", "pc_components", "fanta_roster", "fanta_formazione",
          "stampa_file", "python_file")
# `python_topics` è l'elenco fisso dei 53 argomenti, condiviso di suo: quello che è
# personale è la spunta, che dal blocco Python vivrà in `python_progress`.
# `fanta_players` è il **listone**: condiviso come il catalogo Pokémon, nessun
# proprietario e non deve averlo. Sta in elenco per essere **contato e dichiarato**
# invece che invisibile — una tabella fuori dal raggio fa dire zero a questo script
# senza che nessuno l'abbia guardata, ed è successo: le due tabelle del Fantacalcio
# sono state aggiunte il 21/09/2026 proprio dopo aver visto che non c'erano.
# Le probabili formazioni sono condivise per la stessa ragione del listone: le
# formazioni della Serie A non sono di nessun utente. Entrano in elenco il
# 21/09/2026 **insieme al codice che le scrive**, che è la regola imparata due
# blocchi fa: una tabella fuori dal raggio fa dire «0 scoperte» a vuoto.
# `fanta_calendario` entra il 22/09/2026, **insieme al codice che lo legge**, per
# la stessa ragione delle due qui sopra: dice quando si gioca, cioè un fatto della
# Serie A che non è di nessun utente. Aggiungerla dopo avrebbe voluto dire un altro
# «0 scoperte» detto senza aver guardato.
# Dal 25/09/2026 le tabelle del Fantacalcio sono quelle della sezione nata come
# «Fantacalcio 2»: le probabili lette dal sito non ci sono più, la classifica sì.
ALTRE = ("python_topics", "fanta_players", "fanta_calendario", "fanta_classifica")
TABELLE = RADICI + FIGLIE + ALTRE

CITA = re.compile(r"\b(?:FROM|INTO|UPDATE|JOIN)\s+(%s)\b" % "|".join(TABELLE), re.I)
# ⚠️ Il punto cieco: una query che si costruisce il **nome della tabella** — il
# travaso di `admin.py` gira sulle quattro radici in un ciclo — non nomina nessuna
# tabella nel testo, quindi la riga sopra non la vede. Invisibile è peggio che
# scoperta: queste vengono raccolte a parte e vanno lette a mano, o dichiarate.
CITA_CALCOLATA = re.compile(r"\b(?:FROM|INTO|UPDATE|JOIN)\s+\{…\}", re.I)

# (file, funzione, query normalizzata) -> perché è giusto che non filtri.
#
# Due sole ragioni valgono, e vanno scritte per esteso:
#   * la riga figlia **eredita** il proprietario dal padre, che in quella funzione è
#     già stato filtrato (`team_members` dal team, `pc_components` dalla build);
#   * il dato è **condiviso di suo** e la route è da amministratore — le regulation
#     stanno in file, non in `hub.db`, e chi le cancella deve sapere se qualcuno le
#     sta usando, non solo se le usa lui.
ECCEZIONI = {
    ("blueprints/pokemon.py", "_team_upsert",
     "DELETE FROM team_members WHERE team_id=?"):
        "i membri seguono il team, e il team è stato appena verificato: se non è di "
        "chi salva, la funzione è già uscita prima di arrivare qui",
    ("blueprints/pokemon.py", "_team_upsert",
     "INSERT INTO team_members (team_id,slot,pokemon,mechanic_type,mechanic_value, "
     "nature,ability,held_item, move1,move2,move3,move4, "
     "sp_hp,sp_atk,sp_def,sp_spatk,sp_spdef,sp_spe, sprite_url) "
     "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"):
        "stesso team appena verificato: il proprietario è quello del padre",
    ("blueprints/pokemon.py", "pokemon",
     "SELECT * FROM team_members WHERE team_id=? ORDER BY slot"):
        "i team dell'elenco sono già filtrati: qui si leggono i membri di quelli",
    ("blueprints/pokemon.py", "team_edit",
     "SELECT * FROM team_members WHERE team_id=? ORDER BY slot"):
        "il team è già stato letto con il filtro: se non era tuo, non si arriva qui",
    ("blueprints/pokemon.py", "api_regulations_delete",
     "SELECT COUNT(*) FROM teams WHERE regulation_id=?"):
        "le regulation sono condivise: cancellarne una tocca i team di tutti, quindi "
        "il conto deve vederli tutti. Route da amministratore",
    ("blueprints/pokemon.py", "regulations_list",
     "SELECT COUNT(*) FROM teams WHERE regulation_id=?"):
        "quanti team usano ogni regulation, di chiunque siano. Route da amministratore",
    ("blueprints/api_pokemon.py", "api_team",
     "SELECT * FROM team_members WHERE team_id=? ORDER BY slot"):
        "il team e' stato appena letto con il filtro del proprietario: se non e' tuo, "
        "la funzione ha gia' risposto 404 e non si arriva qui",
    ("blueprints/dashboard.py", "dashboard",
     "SELECT COUNT(*) FROM python_topics"):
        "il totale dei 53 argomenti: l'elenco e' condiviso di suo, personale e' solo "
        "la spunta, che sta in python_progress ed e' filtrata per utente",
    ("blueprints/dashboard.py", "export_data",
     "SELECT * FROM team_members WHERE team_id=? ORDER BY slot"):
        "i team del ciclo sono gia' filtrati: qui si leggono i membri di quelli",
    ("blueprints/dashboard.py", "export_data",
     "SELECT * FROM pc_components WHERE build_id=?"):
        "le build del ciclo sono gia' filtrate: qui si leggono i pezzi di quelle",
    ("blueprints/python_tracker.py", "python_toggle",
     "SELECT 1 FROM python_topics WHERE id=?"):
        "controlla solo che l'argomento **esista**: l'elenco e' condiviso, e la spunta "
        "che segue e' scritta su python_progress con l'id di chi la mette",
    ("blueprints/pcbuilder.py", "pcbuilder",
     "SELECT * FROM pc_components WHERE build_id=? ORDER BY category"):
        "le build dell'elenco sono gia' filtrate: qui si leggono i pezzi di quelle",
    ("blueprints/pcbuilder.py", "pcbuilder_save",
     "DELETE FROM pc_components WHERE build_id=?"):
        "i pezzi seguono la build, e la build e' stata appena verificata: se non e' di "
        "chi salva, la funzione e' gia' uscita prima di arrivare qui",
    ("blueprints/pcbuilder.py", "pcbuilder_save",
     "INSERT INTO pc_components(build_id,category,name,price,notes,stato,prezzo_data,"
     "obiettivo,valore_usato,valore_usato_data,link_amazon,link_eprice,link_bpm,"
     "link_versus,opendb_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"):
        "stessa build appena verificata: il proprietario e' quello del padre",
    # ── Python: i file dei progetti (25/09/2026) ────────────────────────────
    # Stessa forma di `pc_components`: i file seguono il progetto, e ogni route che
    # arriva a queste funzioni ha già letto il progetto con `_progetto()`, filtrato.
    ("blueprints/python_tracker.py", "_file_di",
     "SELECT nome, contenuto FROM python_file WHERE progetto_id=? ORDER BY nome"):
        "chi la chiama ha già verificato il progetto con _progetto() (ambito_utente): "
        "se non è tuo, la route è già uscita",
    ("blueprints/python_tracker.py", "_scrivi_file",
     "DELETE FROM python_file WHERE progetto_id=?"):
        "i file seguono il progetto, verificato dal chiamante (UPDATE filtrato col suo "
        "rowcount in progetto_salva, _progetto() in _aggiungi, INSERT proprio in progetto_nuovo)",
    ("blueprints/python_tracker.py", "_scrivi_file",
     "DELETE FROM python_file WHERE progetto_id=? AND nome=?"):
        "stesso progetto già verificato: si tolgono i file che il caricamento sostituisce",
    ("blueprints/python_tracker.py", "_scrivi_file",
     "INSERT INTO python_file(progetto_id, nome, contenuto) VALUES(?,?,?)"):
        "stesso progetto già verificato: il proprietario è quello del padre",
    ("blueprints/python_tracker.py", "nota_salva",
     "SELECT 1 FROM python_topics WHERE id=?"):
        "controlla solo che l'argomento **esista**: l'elenco è condiviso, e la nota che "
        "segue è scritta con l'id di chi la scrive",
    # ── Stampa 3D (25/09/2026) ──────────────────────────────────────────────
    ("blueprints/stampa3d.py", "_carica",
     "INSERT INTO stampa_file(progetto_id,nome,impronta,byte) VALUES(?,?,?,?)"):
        "il progetto e' stato appena verificato da `stampa3d_save()` (UPDATE filtrato "
        "col suo rowcount, o INSERT con l'id di chi salva): il file segue il padre",
    ("blueprints/stampa3d.py", "stampa3d_file_delete",
     "DELETE FROM stampa_file WHERE id=?"):
        "l'id viene da `_file()`, che l'ha letto con la join sul progetto filtrata "
        "per proprietario: se non era tuo, la funzione e' gia' uscita",
    ("stampa3d.py", "togli_orfani",
     "SELECT 1 FROM stampa_file WHERE impronta=?"):
        "deve vedere le righe di **tutti**: il file su disco e' uno per impronta, e "
        "una copia fra utenti lo condivide. Filtrando, cancellerebbe il file di un "
        "altro. Legge solo se esiste una riga, non ne mostra nessuna",
    ("blueprints/gaming.py", "steam_importa",
     "UPDATE games SET hours_played=? WHERE id=?"):
        "l'id viene dalla mappa degli appid gia' presenti, costruita con solo_mie(): "
        "si aggiorna una riga propria o non si aggiorna niente",
    ("blueprints/gaming.py", "steam_arricchisci",
     "UPDATE games SET genre=? WHERE id=?"):
        "l'id viene dal lotto pescato con solo_mie() poche righe sopra",
    ("blueprints/gaming.py", "steam_arricchisci",
     "UPDATE games SET genre='—' WHERE id=?"):
        "stesso lotto: e' il ramo «Steam ha risposto ma non ha generi»",
    ("blueprints/gaming.py", "steam_arricchisci_tag",
     "UPDATE games SET steam_tags=? WHERE id=?"):
        "l'id viene dal lotto pescato con solo_mie() poche righe sopra",
    ("blueprints/gaming.py", "steam_arricchisci_tag",
     "UPDATE games SET steam_tags='—' WHERE id=?"):
        "stesso lotto: e' il ramo «SteamSpy non ha tag per questo gioco»",
    ("blueprints/admin.py", "utente_elimina",
     "UPDATE {…} SET user_id=? WHERE user_id=?"):
        "il travaso dei contenuti di un utente che viene eliminato: gira sulle "
        "tabelle di `TABELLE_UTENTE` marcate `passa` e **cambia** il "
        "proprietario, non lo legge. Route da amministratore",
    # ⚠️ La riga sopra diceva «gira sulle quattro radici», ed era vero fino al
    # 22/09/2026: erano quattro scritte a mano, le tabelle con un `user_id` erano
    # sei, e le due dimenticate rompevano in silenzio. Ora l'elenco è
    # `TABELLE_UTENTE` in `extensions.py`, accoppiato allo schema vero da
    # `tabelle_senza_regola()`, e questa route **si rifiuta** se ne trova una che
    # non conosce. Resta una query a tabella calcolata, e resta da leggere a mano:
    # è quello che questo script non può fare per nessuno.
    ("blueprints/admin.py", "utente_elimina",
     "DELETE FROM {…} WHERE user_id=?"):
        "la seconda metà dello stesso travaso: le tabelle marcate `cancella` in "
        "`TABELLE_UTENTE` tengono **stato personale**, non contenuto (oggi solo "
        "`python_progress`), e intestarlo a un altro vorrebbe dire scrivere che "
        "ha fatto cose che non ha fatto. Quante righe erano si dice a schermo",
    # ── «Resta collegato» (22/09/2026, §4.3) ────────────────────────────────
    # Tre query che non nominano `user_id`, e non è una svista: su questa tabella il
    # permesso **non** è il proprietario, è il **token**. Chi presenta l'impronta
    # giusta è per definizione il padrone di quella riga — è la stessa logica per cui
    # `/login` cerca per username e non per «le mie righe».
    # ⚠️ Nota per chi legge: la `SELECT … JOIN users` qui accanto risulta «filtrata»
    # perché il testo contiene `s.user_id` nella JOIN, ma a filtrarla è
    # **l'impronta**, non il proprietario. È corretta lo stesso; il conto la mette
    # nella casella giusta per la ragione sbagliata, e questa riga serve a non far
    # credere il contrario a chi ci torna.
    ("extensions.py", "utente_da_ricordare",
     "DELETE FROM sessioni_ricordate WHERE scade_il < ?"):
        "butta le sessioni **scadute di tutti**, ed è giusto che le veda tutte: una "
        "riga scaduta non è più di nessuno, e lasciarla lì vorrebbe dire tenere in "
        "giro un permesso morto in attesa che qualcuno se ne ricordi",
    ("extensions.py", "utente_da_ricordare",
     "UPDATE sessioni_ricordate SET usata_il=? WHERE id=?"):
        "l'id viene dalla riga appena trovata con l'impronta del token, due righe "
        "sopra: è la riga di questa richiesta e di nessun'altra",
    ("extensions.py", "dimentica_sessione",
     "DELETE FROM sessioni_ricordate WHERE impronta=?"):
        "revoca **il dispositivo che sta uscendo**, e lo individua col token che ha "
        "in mano: l'impronta è il segreto, quindi solo chi ce l'ha può cancellarla. "
        "Quella per utente è `dimentica_tutte()`, che il `user_id` lo nomina",
    # ── La copia fra utenti (22/09/2026, §4.3) ──────────────────────────────
    # Quattro query a tabella calcolata, tutte e quattro del motore che duplica i
    # dati di un utente su un altro. Girano sulle stesse `TABELLE_UTENTE` del
    # travaso, e vanno lette qui perché nessun controllo automatico può dirlo: il
    # nome della tabella non è nel testo. ⚠️ Chi tocca `copia_dati_utente()` rilegga
    # queste quattro righe — e sappia che la rete vera non è questo elenco, sono
    # `tabelle_senza_regola()` e `figlie_senza_regola()`, che la route interroga
    # **prima** di scrivere e che la fanno rifiutare su una tabella sconosciuta.
    ("extensions.py", "_inserisci_copia",
     "INSERT INTO {…}({…}) VALUES({…})"):
        "riscrive una riga col proprietario (o l'id del padre) sostituito: il "
        "proprietario lo **scrive**, non lo legge. La tabella e i valori arrivano "
        "da `copia_dati_utente()`, mai dall'utente",
    ("extensions.py", "copia_dati_utente",
     "SELECT * FROM {…} WHERE user_id=?"):
        "le righe da duplicare, tabella per tabella: filtra **per il proprietario "
        "sorgente**, che è l'utente scelto nella pagina. Non è ambito_utente() "
        "perché non è «le mie»: è «le sue», e la route è da amministratore",
    ("extensions.py", "copia_dati_utente",
     "SELECT * FROM {…} WHERE {…}=?"):
        "le figlie di una riga appena letta: il filtro è l'id del **padre**, che "
        "viene dalla query qui sopra — il proprietario le figlie lo ereditano da "
        "lì, come ovunque in questo progetto",
    ("extensions.py", "conteggi_utente",
     "SELECT user_id, COUNT(*) AS quante FROM {…} WHERE user_id IS NOT NULL "
     "GROUP BY user_id"):
        "quante righe ha ogni utente, per scrivere nella conferma cosa sta per "
        "raddoppiare. Vede tutti di proposito: è la pagina Utenti, da "
        "amministratore, dove vedere tutti è il punto",
    ("extensions.py", "init_db",
     "UPDATE {…} SET user_id=? WHERE user_id IS NULL"):
        "la migrazione del 19/08/2026 che intesta ad admin le righe nate prima del "
        "proprietario. Gira una volta sola, nel giro in cui la colonna nasce",
    # La fusione del Fantacalcio (25/09/2026): gira in `init_db()`, senza una
    # sessione, e deve vedere **tutte** le leghe della sezione vecchia per portare
    # quelle che la nuova non ha. Il proprietario viaggia con la riga (`user_id`
    # copiato così com'è), le rose seguono la loro lega.
    ("extensions.py", "_unisci_fantacalcio",
     "SELECT * FROM fanta_leagues ORDER BY id"):
        "la fusione del 25/09/2026 legge tutte le leghe della sezione vecchia, di "
        "chiunque siano, e le porta col loro user_id. Una volta sola, in init_db()",
    ("extensions.py", "_unisci_fantacalcio",
     "SELECT COUNT(*) FROM fanta_roster WHERE league_id=?"):
        "quante righe di rosa aveva la lega che la fusione sta portando, per dire "
        "quante ne restano fuori",
    ("extensions.py", "_unisci_fantacalcio",
     "INSERT INTO fanta2_roster(league_id, player_id, prezzo, note) SELECT ?, "
     "player_id, prezzo, note FROM fanta_roster WHERE league_id=? AND player_id IN "
     "(SELECT id FROM fanta2_players)"):
        "la rosa segue la lega appena portata dalla fusione, col suo proprietario",
    ("blueprints/pokemon.py", "regulation_editor",
     "SELECT id, name, format, record FROM teams WHERE regulation_id=? ORDER BY created_at DESC"):
        "chi tocca una regulation deve vedere tutti i team che ne dipendono, non solo "
        "i propri. Route da amministratore",
    # ── Fantacalcio (§4.6) ──────────────────────────────────────────────────
    # Nato il 24/09/2026 come «Fantacalcio 2», dal 25/09/2026 è la sola sezione e ha
    # preso nomi di file e di tabella della vecchia, le cui eccezioni se ne sono
    # andate con lei. Il listone, il calendario e la classifica sono condivisi; rosa
    # e formazione passano da una lega già verificata.
    ('blueprints/fantacalcio.py', '_scrivi_formazione',
     'INSERT INTO fanta_formazione(league_id, player_id, titolare, ordine, ruolo) VALUES(?,?,?,?,?)'):
        "la lega è verificata da chi chiama, e subito dopo l'UPDATE sulla lega con solo_mie() guarda il rowcount (e toglie quello che ha scritto se è zero)",
    ('blueprints/fantacalcio.py', '_scendi_dal_campo',
     'DELETE FROM fanta_formazione WHERE league_id=? AND player_id IN ({…})'):
        'toglie dal campo chi il chiamante ha appena tolto dalla rosa con solo_mie() e rowcount guardato',
    ('blueprints/fantacalcio.py', 'lega_salva',
     'INSERT INTO fanta_leagues({…}) VALUES({…})'):
        "la INSERT della lega nuova: poco sopra fa `comuni['user_id'] = utente_id()`; il ramo che modifica filtra con solo_mie()",
    ('blueprints/fantacalcio.py', '_scrivi_formazione',
     'DELETE FROM fanta_formazione WHERE league_id=?'):
        "la lega è verificata da chi chiama, e subito dopo l'UPDATE sulla lega con solo_mie() guarda il rowcount (e toglie quello che ha scritto se è zero)",
    ('blueprints/fantacalcio.py', 'rosa_aggiungi',
     'INSERT INTO fanta_roster(league_id, player_id, prezzo, note) VALUES(?,?,?,?)'):
        'il listone condiviso per il nome, e la INSERT nella rosa di una lega appena verificata con _lega_mia()',
    ('blueprints/fantacalcio.py', 'fantacalcio',
     'SELECT COUNT(*) AS attivi, MAX(visto_il) AS visto, (SELECT COUNT(*) FROM fanta_players WHERE attivo=0) AS spenti FROM fanta_players WHERE attivo=1'):
        'il listone è condiviso: quanti giocatori e da quando è la stessa risposta per tutti',
    ('blueprints/fantacalcio.py', 'rosa_aggiungi',
     'SELECT nome FROM fanta_players WHERE id=?'):
        'il listone condiviso per il nome, e la INSERT nella rosa di una lega appena verificata con _lega_mia()',
    ('blueprints/fantacalcio.py', 'rosa_incolla_conferma',
     'INSERT INTO fanta_roster(league_id, player_id, prezzo) VALUES(?,?,?)'):
        'gli id del listone condiviso per rifiutare quelli inventati, e la INSERT nella rosa di una lega appena verificata con _lega_mia()',
    ('blueprints/fantacalcio.py', 'listone',
     'SELECT COUNT(*) AS attivi, MAX(visto_il) AS visto, (SELECT COUNT(*) FROM fanta_players WHERE attivo=0) AS spenti FROM fanta_players WHERE attivo=1'):
        'il listone da sfogliare: dato condiviso; le rose tue sono lette a parte con ambito_utente()',
    ('blueprints/fantacalcio.py', 'api_giocatore',
     'SELECT * FROM fanta_players WHERE id=?'):
        'la riga del listone condiviso; le rose tue sono lette a parte con ambito_utente()',
    ('blueprints/fantacalcio.py', 'api_giocatori',
     'SELECT id, nome, squadra, squadra_slug, ruolo_classic, qa, fvm, fantamedia, attivo FROM fanta_players WHERE nome LIKE ? ORDER BY attivo DESC, fvm DESC, nome LIMIT 25'):
        'la ricerca nel listone condiviso, per scegliere chi mettere in rosa',
    ('blueprints/fantacalcio.py', '_contesto_giornata',
     'SELECT 1 FROM fanta_calendario LIMIT 1'):
        'se il calendario è stato importato: dato condiviso, uguale per tutti',
    ('blueprints/fantacalcio.py', '_schierati',
     'SELECT player_id, titolare, ordine FROM fanta_formazione WHERE league_id=? ORDER BY titolare DESC, ordine'):
        'la lega arriva sempre da una lettura già filtrata (_lega_mia() o ambito_utente())',
    ('blueprints/fantacalcio.py', '_listone',
     'SELECT id, nome, squadra, squadra_slug, ruolo_classic, qa, fvm, fantamedia, attivo FROM fanta_players'):
        'il listone condiviso, letto intero per contare gli omonimi di un nome incollato',
    ('blueprints/fantacalcio.py', 'rosa_incolla_conferma',
     'SELECT id FROM fanta_players'):
        'gli id del listone condiviso per rifiutare quelli inventati, e la INSERT nella rosa di una lega appena verificata con _lega_mia()',
    ('blueprints/fantacalcio.py', 'listone',
     'SELECT * FROM fanta_players{…} ORDER BY ({…} IS NULL), {…}, nome'):
        'il listone da sfogliare: dato condiviso; le rose tue sono lette a parte con ambito_utente()',
    ('blueprints/fantacalcio.py', 'listone',
     'SELECT DISTINCT squadra FROM fanta_players WHERE squadra IS NOT NULL AND attivo=1 ORDER BY squadra'):
        'il listone da sfogliare: dato condiviso; le rose tue sono lette a parte con ambito_utente()',
    ('blueprints/fantacalcio.py', '_allerta',
     'SELECT id, nome FROM fanta_players WHERE id IN ({…})'):
        'il nome di chi è schierato ma non è più in rosa, preso dal listone condiviso',
    ('fanta.py', 'aggiorna_calendario',
     'DELETE FROM fanta_calendario'):
        'calendario e classifica della Serie A da football-data.org: dati condivisi, e le squadre del listone condiviso per abbinarli',
    ('fanta.py', 'aggiorna_calendario',
     'INSERT INTO fanta_calendario(match_id, giornata, stato, inizio, utc, casa, casa_slug, fuori, fuori_slug, gol_casa, gol_fuori, aggiornata_fonte) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)'):
        'calendario e classifica della Serie A da football-data.org: dati condivisi, e le squadre del listone condiviso per abbinarli',
    ('fanta.py', 'aggiorna_calendario',
     'DELETE FROM fanta_classifica'):
        'calendario e classifica della Serie A da football-data.org: dati condivisi, e le squadre del listone condiviso per abbinarli',
    ('fanta.py', 'aggiorna_calendario',
     'INSERT INTO fanta_classifica(squadra_slug, squadra, posizione, punti, giocate, gol_fatti, gol_subiti, stemma) VALUES(?,?,?,?,?,?,?,?)'):
        'calendario e classifica della Serie A da football-data.org: dati condivisi, e le squadre del listone condiviso per abbinarli',
    ('fanta.py', 'partite_della_giornata',
     'SELECT * FROM fanta_calendario WHERE giornata=? ORDER BY inizio'):
        'le partite della giornata: dato condiviso',
    ('fanta.py', 'importa_listone',
     'INSERT INTO fanta_players(id, {…}, attivo, visto_il, aggiornato_il) VALUES(?, {…}, ?, ?, CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET {…}, attivo=excluded.attivo, visto_il=excluded.visto_il, aggiornato_il=CURRENT_TIMESTAMP'):
        "l'import del listone condiviso dai due Excel: nessun proprietario, come faceva fanta_import.aggiorna_listone()",
    ('fanta.py', 'importa_listone',
     'UPDATE fanta_players SET attivo=0, aggiornato_il=CURRENT_TIMESTAMP WHERE id=?'):
        "l'import del listone condiviso dai due Excel: nessun proprietario, come faceva fanta_import.aggiorna_listone()",
    ('fanta.py', 'importa_listone',
     'SELECT * FROM fanta_players'):
        "l'import del listone condiviso dai due Excel: nessun proprietario, come faceva fanta_import.aggiorna_listone()",
    ('fanta.py', 'eta_calendario',
     'SELECT MAX(aggiornato_il) AS q FROM fanta_calendario'):
        "l'età del calendario condiviso",
    ('fanta.py', 'aggiorna_calendario',
     'SELECT DISTINCT squadra_slug FROM fanta_players WHERE attivo=1 AND squadra_slug IS NOT NULL'):
        'calendario e classifica della Serie A da football-data.org: dati condivisi, e le squadre del listone condiviso per abbinarli',
    ('fanta.py', 'giornata_corrente',
     'SELECT MIN(giornata) AS g FROM fanta_calendario WHERE stato IN ({…})'):
        'la giornata in corso: il calendario della Serie A è uguale per tutti',
    ('fanta.py', 'scadenza',
     'SELECT * FROM fanta_calendario WHERE giornata=? ORDER BY inizio'):
        "il fischio d'inizio della giornata: dato condiviso, uguale per tutte le leghe",
    ('fanta.py', 'classifica',
     'SELECT * FROM fanta_classifica ORDER BY posizione'):
        'la classifica della Serie A: dato condiviso',
    ('fanta.py', 'stemmi',
     'SELECT squadra_slug, stemma FROM fanta_classifica WHERE stemma IS NOT NULL AND squadra_slug IS NOT NULL'):
        'gli stemmi delle squadre di Serie A, dalla classifica: dato condiviso',
    ('fanta.py', 'conto_stemmi',
     'SELECT COUNT(*) AS tutte, COUNT(stemma) AS con FROM fanta_classifica'):
        'quanti stemmi ha la classifica della Serie A: dato condiviso',
}


def normalizza(sql):
    return " ".join(sql.split())


def testo(nodo):
    """Il testo di una stringa SQL, anche quando è una f-string.

    Le f-string qui dentro ci sono davvero: la condizione di `ambito_utente()` si
    innesta con `{cond}`. I pezzi calcolati diventano `{…}`, che basta per
    riconoscere la query e per scriverla in un'eccezione.
    """
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.JoinedStr):
        pezzi = []
        for v in nodo.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                pezzi.append(v.value)
            else:
                pezzi.append("{…}")
        return "".join(pezzi)
    return None


def nomi_innestati(nodo):
    """I nomi di variabile innestati in una f-string, quando sono nomi e basta.

    ⚠️ Serve perché `{…}` da solo **non dice quale** pezzo è stato innestato, e su
    quella confusione si reggeva il punto cieco chiuso il 22/09/2026: bastava che
    in una funzione comparisse `ambito_utente()` perché **qualunque** query con un
    pezzo calcolato passasse per filtrata. Succedeva a `listone()`, dove il pezzo
    calcolato è l'ORDER BY della tendina e col proprietario non c'entra niente.
    Un `{cond[0]}` o un `{" ".join(...)}` qui non tornano: è voluto, perché il
    riconoscimento dev'essere stretto — quello che non riconosce finisce fra le
    scoperte, che è il verso giusto in cui sbagliare.
    """
    fuori = set()
    if not isinstance(nodo, ast.JoinedStr):
        return fuori
    for v in nodo.values:
        if isinstance(v, ast.FormattedValue) and isinstance(v.value, ast.Name):
            fuori.add(v.value.id)
    return fuori


def query_del_file(percorso):
    """Ogni stringa SQL che nomina una tabella di contenuto, con la sua funzione."""
    albero = ast.parse(io.open(percorso, encoding="utf-8").read())
    padre = {}
    for n in ast.walk(albero):
        for figlio in ast.iter_child_nodes(n):
            padre[figlio] = n

    # ⚠️ Le docstring vanno saltate, e non è una pulizia cosmetica: `ambito_utente()`
    # spiega come si usa **mostrando una query di esempio**. Contarla come query vera
    # significherebbe chiedere un'eccezione per una riga di documentazione — lo stesso
    # inciampo di `controlla_traduzioni.py`, che leggeva le `t()` citate nei commenti.
    docstring = set()
    for n in ast.walk(albero):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            primo = n.body[0] if n.body else None
            if (isinstance(primo, ast.Expr) and isinstance(primo.value, ast.Constant)
                    and isinstance(primo.value.value, str)):
                docstring.add(id(primo.value))

    def funzione_di(n):
        while n in padre:
            n = padre[n]
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return n.name
        return "(modulo)"

    # ⚠️ I pezzi letterali di una f-string sono **anche** nodi Constant a sé: senza
    # questo insieme ogni query composta verrebbe contata due volte, una intera e una
    # monca, e l'eccezione scritta per l'una non coprirebbe l'altra.
    dentro_fstring = set()
    for n in ast.walk(albero):
        if isinstance(n, ast.JoinedStr):
            for v in ast.walk(n):
                if v is not n:
                    dentro_fstring.add(id(v))

    # Le funzioni che chiedono la condizione a `ambito_utente()`. Serve perché lì il
    # filtro **non si vede nel testo** della query: arriva dal segnaposto. Senza
    # questo, le query fatte bene risulterebbero scoperte e quelle vere si
    # perderebbero nel rumore.
    con_ambito = set()
    for n in ast.walk(albero):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id in ("ambito_utente", "solo_mie")):
            con_ambito.add(funzione_di(n))
    chiamano_ambito = set(con_ambito)
    # ⚠️ Dal 21/09/2026 c'è un secondo modo, e senza questo pezzo una query fatta
    # **bene** risultava scoperta: `fanta_import._rose()` non chiama
    # `ambito_utente()` — non potrebbe, la chiamano anche gli script, che una
    # sessione non ce l'hanno — ma la **riceve** come parametro `ambito` e la
    # innesta nel `WHERE`. Il criterio è volutamente stretto: il parametro deve
    # chiamarsi `ambito` **e** dev'essere letto nel corpo della funzione. Una
    # funzione che lo accetta e non lo usa non conta come filtrata, che è
    # esattamente il modo in cui questo riconoscimento potrebbe diventare una
    # scappatoia.
    for n in ast.walk(albero):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        nomi = [a.arg for a in n.args.args + n.args.kwonlyargs]
        if "ambito" not in nomi:
            continue
        usato = any(isinstance(v, ast.Name) and v.id == "ambito"
                    and isinstance(v.ctx, ast.Load) for v in ast.walk(n))
        if usato:
            con_ambito.add(n.name)

    # ⚠️ Chiedere `ambito_utente()` da qualche parte nella funzione **non basta**:
    # conta che sia proprio *quella* variabile a finire dentro *quella* query. È il
    # buco di §4.5, trovato il 22/09/2026 e chiuso qui. Si prende quindi il nome a
    # cui la condizione viene legata — `cond, par = ambito_utente()`, oppure
    # `cond, par = ambito` in chi la riceve come parametro — e si guarda se è lui
    # il segnaposto della query. Un'assegnazione a un nome solo (`ambito =
    # ambito_utente(...)`, che tiene la coppia intera) non conta: quel nome nel
    # `WHERE` non ci finisce mai.
    nomi_ambito = {}
    for n in ast.walk(albero):
        if not isinstance(n, ast.Assign) or len(n.targets) != 1:
            continue
        v, dove = n.value, funzione_di(n)
        da_ambito = (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                     and v.func.id in ("ambito_utente", "solo_mie"))
        if not da_ambito:
            da_ambito = (isinstance(v, ast.Name) and v.id == "ambito"
                         and dove in con_ambito - chiamano_ambito)
        if not da_ambito:
            continue
        t = n.targets[0]
        if isinstance(t, ast.Tuple) and t.elts and isinstance(t.elts[0], ast.Name):
            nomi_ambito.setdefault(dove, set()).add(t.elts[0].id)

    # La condizione fa **un pezzo di strada** prima di arrivare nella query, e
    # seguirlo fa parte del riconoscimento: `rosa_rimuovi()` scrive
    # `mia = f"league_id IN (SELECT l.id FROM fanta_leagues l WHERE {cond})"` e poi
    # innesta `{mia}`. È filtrata, e fermarsi a `cond` l'avrebbe data per scoperta.
    # Si va a punto fisso perché la catena può essere lunga più di un passo; il
    # legame resta stretto — serve un'assegnazione a un nome, da una f-string che
    # innesta un nome **già** riconosciuto. Una condizione che passa per una
    # `join()` o per un parametro di funzione qui non arriva, ed è giusto così:
    # quello che non si riconosce va a finire fra le scoperte, non fra le filtrate.
    assegnazioni = [n for n in ast.walk(albero)
                    if isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and isinstance(n.value, ast.JoinedStr)]
    cambiato = True
    while cambiato:
        cambiato = False
        for n in assegnazioni:
            dove = funzione_di(n)
            noti = nomi_ambito.get(dove, set())
            nome = n.targets[0].id
            if nome not in noti and (nomi_innestati(n.value) & noti):
                nomi_ambito.setdefault(dove, set()).add(nome)
                cambiato = True

    fuori = []
    for n in ast.walk(albero):
        if id(n) in docstring or id(n) in dentro_fstring:
            continue
        s = testo(n)
        if not s:
            continue
        calcolata = bool(CITA_CALCOLATA.search(s))
        if not CITA.search(s) and not calcolata:
            continue
        fuori.append({
            "calcolata": calcolata,
            "riga": n.lineno,
            "funzione": funzione_di(n),
            "sql": normalizza(s),
            "tabelle": sorted({m.lower() for m in CITA.findall(s)}),
            "cond_innestata": bool(nomi_innestati(n)
                                   & nomi_ambito.get(funzione_di(n), set())),
        })
    return fuori


def sorgenti():
    for radice in SORGENTI:
        for nome in sorted(os.listdir(radice)):
            if not nome.endswith(".py"):
                continue
            percorso = os.path.join(radice, nome)
            if os.path.isfile(percorso):
                yield percorso


def fuori_dal_raggio():
    """Gli script che nominano una tabella di contenuto: dichiarati, non controllati.

    Non sono un problema — uno script non ha una sessione, quindi lavora su tutto il
    DB per costruzione — ma vanno **contati**, altrimenti «non li guardo» e «me ne
    sono dimenticato» hanno lo stesso aspetto.
    """
    cartella = os.path.join(BASE, "scripts")
    trovati = []
    io_stesso = os.path.basename(os.path.abspath(__file__))
    for nome in sorted(os.listdir(cartella)):
        # Questo file nomina tutte le tabelle — sono la sua configurazione, non
        # query: contarsi da solo sarebbe l'unica riga sicuramente falsa dell'elenco.
        if not nome.endswith(".py") or nome == io_stesso:
            continue
        try:
            testo = io.open(os.path.join(cartella, nome), encoding="utf-8").read()
        except Exception:
            continue
        tabelle = sorted(set(t.lower() for t in CITA.findall(testo)))
        if tabelle:
            trovati.append((nome, tabelle))
    return trovati


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tutte", action="store_true",
                    help="stampa anche le query già filtrate")
    args = ap.parse_args()

    filtrate, dichiarate, scoperte, calcolate = [], [], [], []
    for percorso in sorgenti():
        rel = os.path.relpath(percorso, BASE).replace("\\", "/")
        for q in query_del_file(percorso):
            q["file"] = rel
            chiave = (rel, q["funzione"], q["sql"])
            # `extensions.py` crea le tabelle e le migra: lì il proprietario non
            # c'entra. La deroga vale **solo per `init_db()`** e non per tutto il
            # file: lì dentro vivono anche gli helper, e un domani ci potrebbe
            # finire una query vera, che non deve passare per esenzione d'ufficio.
            semina = rel == "extensions.py" and q["funzione"] == "init_db"
            if q["calcolata"] and chiave not in ECCEZIONI:
                calcolate.append(q)
            elif semina:
                q["perche"] = "schema e migrazioni, non una query di lettura"
                dichiarate.append(q)
            elif "user_id" in q["sql"].lower():
                filtrate.append(q)
            elif q["cond_innestata"]:
                # Il segnaposto di questa query **è** la variabile che tiene la
                # condizione di `ambito_utente()`/`solo_mie()`. Fino al 22/09/2026
                # qui bastava un `{…}` qualsiasi in una funzione che da qualche
                # parte chiamava `ambito_utente()`: vedi `nomi_innestati()`.
                filtrate.append(q)
            elif chiave in ECCEZIONI:
                q["perche"] = ECCEZIONI[chiave]
                dichiarate.append(q)
            else:
                scoperte.append(q)

    tot = len(filtrate) + len(dichiarate) + len(scoperte) + len(calcolate)
    print(f"Query sui contenuti: {tot}")
    print(f"  filtrate per proprietario : {len(filtrate)}")
    print(f"  dichiarate (eccezioni)    : {len(dichiarate)}")
    print(f"  a tabella calcolata       : {len(calcolate)}")
    print(f"  SCOPERTE                  : {len(scoperte)}")
    print(f"  fuori dal raggio: {len(fuori_dal_raggio())} script in scripts/ "
          f"(dichiarati, vedi in fondo)")

    if args.tutte and filtrate:
        print("\n-- filtrate --")
        for q in filtrate:
            print(f"  {q['file']}:{q['riga']} {q['funzione']}()  [{', '.join(q['tabelle'])}]")

    if dichiarate:
        print("\n-- dichiarate: vedono tutto, e c'è scritto perché --")
        for q in sorted(dichiarate, key=lambda x: (x["file"], x["riga"])):
            print(f"  {q['file']}:{q['riga']} {q['funzione']}()  [{', '.join(q['tabelle'])}]")
            print(f"      {q['perche']}")

    if calcolate:
        print("\n-- a tabella calcolata: il nome della tabella non è nel testo,")
        print("   quindi nessun controllo automatico può dire su cosa girano. Vanno lette --")
        for q in sorted(calcolate, key=lambda x: (x["file"], x["riga"])):
            print(f"  {q['file']}:{q['riga']} {q['funzione']}()")
            print(f"      {q['sql'][:110]}")

    script = fuori_dal_raggio()
    if script:
        print("\n-- fuori dal raggio, e dichiarato: scripts/ non viene controllato --")
        print("   uno script da riga di comando non ha una sessione, quindi "
              "`ambito_utente()`")
        print("   non vuol dire niente e lavora su tutto il DB. È voluto: qui si "
              "contano,")
        print("   così «non li guardo» non somiglia a «me ne sono dimenticato».")
        for nome, tabelle in script:
            print(f"  scripts/{nome}  [{', '.join(tabelle)}]")

    if scoperte:
        print("\n-- SCOPERTE: mostrano le righe di tutti --")
        for q in sorted(scoperte, key=lambda x: (x["file"], x["riga"])):
            print(f"  {q['file']}:{q['riga']} {q['funzione']}()  [{', '.join(q['tabelle'])}]")
            print(f"      {q['sql'][:110]}")

    return 1 if (scoperte or calcolate) else 0


if __name__ == "__main__":
    sys.exit(main())
