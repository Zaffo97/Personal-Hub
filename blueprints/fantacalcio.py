"""La sezione Fantacalcio: le leghe con le loro regole, e la rosa di ognuna.

§4.2 del backlog, aperta il 21/09/2026. Le decisioni di Davide che danno forma a
questo file: **due leghe**, tutte e due **Classic**, e le regole **strutturate** —
cioè in colonne che l'app può leggere, non in un testo libero da rileggere a occhio.

⚠️ **Di chi sono i dati.** `fanta_players` è il listone ed è **condiviso**, come il
catalogo Pokémon: nessun proprietario, e non deve averlo. `fanta_leagues` e
`fanta_roster` sono invece **tuoi**, quindi ogni lettura passa da `ambito_utente()`
e ogni scrittura da `solo_mie()`. La rosa non ha una colonna `user_id` di suo: il
proprietario le arriva dalla lega, quindi le sue query **devono** passare dalla
`fanta_leagues` per essere filtrate — una `SELECT` su `fanta_roster` da sola sarebbe
scoperta, ed è la trappola scritta in §1.1.

⚠️ E ogni `UPDATE`/`DELETE` filtrato guarda il `rowcount`: una scrittura che non
tocca niente **non dà errore**, e senza quel controllo il codice sotto andrebbe
avanti come se avesse funzionato.
"""
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify)

from extensions import (get_db, login_required, _i, ambito_utente, solo_mie,
                        utente_id, e_admin)
from data import (RUOLI_FANTA, ORDINE_RUOLI_FANTA, nome_ruolo, scomponi_modulo,
                  controlla_schierati, quanti_guai,
                  MOD_DIFESA_SOGLIE, MOD_DIFESA_SOGLIE_QUARTI,
                  fasce_mod_difesa, soglie_mod_difesa, scrivi_soglie,
                  modificatore_difesa, controlla_formazione,
                  leggi_rosa_incollata, valuta_rosa, consiglia_moduli,
                  rosa_per_merito, etichetta_fascia, FASCE_TITOLARITA,
                  SOGLIA_SCHIERABILE, MINIMO_PARTITE_FIDATO)
import fanta_import as I

bp = Blueprint("fantacalcio", __name__, url_prefix="/fantacalcio")

# Le colonne delle regole, in un posto solo: le usano il form, il salvataggio e la
# scheda che le mostra. ⚠️ **Sette su nove** vengono dal regolamento ufficiale, che
# `/regolamenti/leghe-private` elenca per esteso (riletto il 21/09/2026): il terzo
# valore di ogni riga dice quali. Porta inviolata e autogol no — quelli il
# regolamento non li fissa, e sono il motivo per cui queste regole stanno in colonne
# invece che in un testo da rileggere a occhio.
#
# ⚠️ **Il gol è uno solo.** Fino al 21/09/2026 c'erano quattro colonne, una per
# ruolo. Il regolamento ufficiale — riletto quel giorno su
# `/regolamenti/leghe-private` — dà **+3 a chiunque segni**, portiere compreso, e
# quattro caselle da riempire con lo stesso numero erano quattro occasioni di
# sbagliarne una senza accorgersene.
#
# La quarta voce di ogni riga sono i **valori proposti** nella tendina. Non sono
# una gabbia: la tendina ha sempre «Altro…», che scopre la casella per scrivere un
# numero qualsiasi. Servono a far vedere subito quello **giusto** — i valori del
# regolamento sono segnati «(ufficiale)» — invece di lasciare una casella vuota
# davanti a chi non ricorda se l'ammonizione toglie mezzo punto o uno.
REGOLE = [
    ("bonus_gol", "Gol segnato", True, [2, 2.5, 3, 3.5, 4]),
    ("bonus_assist", "Assist", True, [0, 0.5, 1, 1.5, 2]),
    ("malus_amm", "Ammonizione", True, [0, -0.25, -0.5, -1]),
    ("malus_esp", "Espulsione", True, [0, -0.5, -1, -2]),
    ("malus_gol_subito", "Gol subito (portiere)", True, [0, -0.5, -1]),
    ("bonus_imbattibilita", "Porta inviolata", False, [0, 0.5, 1, 1.5, 2]),
    ("bonus_rigore_parato", "Rigore parato", True, [0, 1, 2, 3]),
    ("malus_rigore_sbagliato", "Rigore sbagliato", True, [0, -1, -2, -3]),
    ("malus_autogol", "Autogol", False, [0, -1, -2, -3]),
]
UFFICIALI = {c for c, _, ufficiale, _ in REGOLE if ufficiale}
# Il valore che il regolamento ufficiale dà, per le voci che ci sono dentro: la
# tendina lo segna, così «(ufficiale)» dice **quale** numero lo è, non solo che
# la voce esiste nel regolamento.
VALORE_UFFICIALE = {
    "bonus_gol": 3, "bonus_assist": 1, "malus_amm": -0.5, "malus_esp": -1,
    "malus_gol_subito": -1, "bonus_rigore_parato": 3, "malus_rigore_sbagliato": -3,
}
# ⚠️ Con che valore nasce una lega nuova. **Non** è lo stesso dizionario di sopra:
# porta inviolata e autogol il regolamento non li fissa, ma un default ce l'hanno
# lo stesso — quello convenzionale, che è anche il `DEFAULT` scritto nella tabella.
# Il primo giro lasciava partire queste due da zero, cioè dal primo valore della
# tendina, e una lega nuova nasceva con l'autogol che non toglie niente: nessun
# errore, solo una regola sparita. L'ha preso la prova in browser.
VALORE_PARTENZA = dict(VALORE_UFFICIALE,
                       bonus_imbattibilita=1, malus_autogol=-2)


def _lega_mia(db, lid):
    """La lega `lid` **se è di chi sta guardando**, altrimenti `None`.

    Un punto solo per la domanda «questa lega è mia?»: ripeterla in sei route è il
    modo per dimenticarsela nella settima.
    """
    cond, par = ambito_utente()
    r = db.execute(f"SELECT * FROM fanta_leagues WHERE id=? AND {cond}",
                   (lid,) + tuple(par)).fetchone()
    return dict(r) if r else None


def _aggiorna(db, quale, forza_scrittura=False, giornata=None):
    """Rilegge dalla fonte e scrive. Torna `(messaggio, categoria)` per il flash.

    ⚠️ **Se la fonte non risponde, la sezione deve aprirsi lo stesso.** Questa
    funzione viene chiamata anche da una pagina che si sta semplicemente aprendo:
    un `requests` che va in timeout, o un sito che cambia forma, non possono
    diventare un errore 500 su una pagina che sa già cosa mostrare. Perciò ogni
    guaio esce da qui come **messaggio**, e il dato di prima resta dov'è.
    """
    # ⚠️ «in una tua rosa» dev'essere **tua**: da web c'è una sessione, e senza
    # questo l'avviso conterebbe le rose di tutti gli utenti (§1.1). La rosa non
    # ha un proprietario suo: lo eredita dalla lega, quindi il filtro è su quella.
    ambito = ambito_utente("l.user_id")
    try:
        if quale == "listone":
            r = I.aggiorna_listone(db, scarica=True, scrivi=True,
                                   forza=forza_scrittura, ambito=ambito)
            if not r["ok"]:
                return f"Listone non aggiornato: {r['motivo']}", "error"
            pezzi = [f"{r['letti']} giocatori"]
            if r["nuovi"]:
                pezzi.append(f"{len(r['nuovi'])} nuovi")
            if r["spenti"]:
                quanti = sum(1 for x in r["spenti"] if r["in_rosa"].get(x["id"]))
                pezzi.append(f"{len(r['spenti'])} usciti dalla Serie A" +
                             (f" ({quanti} in una tua rosa)" if quanti else ""))
            return "Listone aggiornato: " + ", ".join(pezzi), "success"

        if quale == "calendario":
            # ⚠️ `giornata` dice **quale pagina** leggere, ed è quella delle
            # probabili: la pagina generica del calendario mostra la giornata in
            # corso, che può essere già giocata quando le probabili sono passate
            # alla successiva — e allora il timer resterebbe senza ora proprio
            # nella settimana in cui serve.
            r = I.aggiorna_calendario(db, scarica=True, scrivi=True,
                                      forza=forza_scrittura, giornata=giornata)
            if not r["ok"]:
                return f"Calendario non aggiornato: {r['motivo']}", "error"
            giornate = ", ".join(f"giornata {g} ({n} partite)"
                                 for g, n in sorted(r["giornate"].items()))
            return (f"Calendario aggiornato: {giornate}" +
                    (f", {r['senza_ora']} senza orario" if r["senza_ora"] else ""),
                    "success")

        r = I.aggiorna_probabili(db, scarica=True, scrivi=True,
                                 forza=forza_scrittura, ambito=ambito)
        if not r["ok"]:
            return f"Probabili non aggiornate: {r['motivo']}", "error"
        return (f"Probabili aggiornate: giornata {r['giornata']}, "
                f"{r['voci']} convocati, {r['squadre']} squadre"), "success"
    except Exception as e:
        # Il tipo dell'errore serve: «timeout» e «la pagina non ha più quella
        # forma» si rimediano in due modi diversi.
        return (f"Non sono riuscito a leggere fantacalcio.it "
                f"({type(e).__name__}). Il dato di prima è rimasto com'era.",
                "error")


def _aggiorna_se_vecchio(db, quale, giornata=None):
    """L'aggiornamento automatico entrando nella sezione. Torna il messaggio o `None`.

    ⚠️ Non aggiorna **a ogni visita**, e la ragione è che aprire la pagina
    significherebbe aspettare ogni volta che fantacalcio.it risponda — tre pagine
    da più di un mega. Aggiorna quando la copia è più vecchia della sua soglia
    (`fanta_import.VECCHIA_*`): una settimana per il listone, **tre ore** per le
    probabili, che cambiano fino al fischio d'inizio. Il pulsante «Aggiorna ora»
    resta per quando non si vuole aspettare la soglia.
    """
    serve, _ore = I.serve_aggiornare(db, quale, giornata)
    if not serve:
        return None
    messaggio, categoria = _aggiorna(db, quale, giornata=giornata)
    # Un aggiornamento automatico riuscito non merita un avviso: la pagina mostra
    # già la data del dato. Si parla solo quando è andato storto.
    return None if categoria == "success" else messaggio


def _giornata_probabili(db, chiesta=None):
    """La giornata da mostrare: quella chiesta, se c'è il dato, altrimenti l'ultima.

    ⚠️ **Non si inventa un numero.** Con l'archivio vuoto torna `None` e le pagine
    dicono che le probabili non sono state importate: un `1` di ripiego mostrerebbe
    una giornata vuota come se fosse una giornata senza convocati.
    """
    if chiesta:
        r = db.execute("SELECT giornata FROM fanta_probabili_squadre WHERE giornata=? "
                       "LIMIT 1", (chiesta,)).fetchone()
        if r:
            return r["giornata"]
    r = db.execute("SELECT MAX(giornata) AS g FROM fanta_probabili_squadre").fetchone()
    return r["g"] if r and r["g"] else None


def scadenza_giornata(db, giornata=None):
    """Quando **inizia** la giornata: la prima partita in calendario, o `None`.

    È la scadenza per schierare la formazione, e vale per tutte le leghe: il
    fischio d'inizio della prima partita non dipende da quale lega si gioca.

    ⚠️ Non ha l'underscore davanti perché la usa **anche la Dashboard**, che il
    riquadro del Fantacalcio ce l'ha pure lei. Una seconda copia della query là
    dentro sarebbe due scadenze che possono dire due cose diverse — è lo stesso
    motivo per cui `fanta_import.py` esiste.

    Senza `giornata` la prende dalle probabili importate, e se non ce ne sono
    dalla **prima partita non ancora giocata** che il calendario conosce: sono due
    modi di rispondere alla stessa domanda, e il secondo serve a chi ha il
    calendario ma non ha ancora importato le probabili.

    ⚠️ Torna `None` quando il calendario non c'è o quella giornata non ha ancora
    orari, e chi chiama **lo dice** invece di mostrare un timer fermo. Un timer è
    il caso perfetto del fallback silenzioso: un numero che scorre sembra vero
    anche quando è calcolato su una data inventata.

    ⚠️ `inizio` è ora italiana senza fuso (vedi lo schema): il conto alla rovescia
    lo fa il browser, che sta nello stesso fuso.
    """
    if not giornata:
        adesso = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Il confronto è fra stringhe, e funziona **perché** il formato è
        # `YYYY-MM-DD HH:MM`: in quella forma l'ordine alfabetico è l'ordine
        # cronologico. Con le date scritte all'italiana non lo sarebbe.
        r = db.execute("SELECT giornata FROM fanta_calendario WHERE inizio >= ? "
                       "ORDER BY inizio LIMIT 1", (adesso,)).fetchone()
        giornata = r["giornata"] if r else None
    if not giornata:
        return None
    riga = db.execute(
        "SELECT * FROM fanta_calendario WHERE giornata=? AND inizio IS NOT NULL "
        "ORDER BY inizio LIMIT 1", (giornata,)).fetchone()
    if riga is None:
        return None
    conto = db.execute(
        "SELECT COUNT(*) AS quante, SUM(inizio IS NULL) AS senza_ora "
        "FROM fanta_calendario WHERE giornata=?", (giornata,)).fetchone()
    # La stessa data scritta per chi legge, **senza `locale`**: i nomi dei giorni
    # in italiano dipendono da come è configurato il sistema, e un server che non
    # ha la locale italiana scriverebbe «Saturday». Il conto alla rovescia lo fa
    # il browser; questa riga è quello che resta scritto comunque.
    try:
        quando = datetime.strptime(riga["inizio"], "%Y-%m-%d %H:%M").strftime(
            "%d/%m/%Y alle %H:%M")
    except ValueError:
        quando = riga["inizio"]
    return {"giornata": giornata, "inizio": riga["inizio"], "quando": quando,
            "casa": riga["squadra_casa"], "fuori": riga["squadra_fuori"],
            "quante": conto["quante"], "senza_ora": conto["senza_ora"] or 0}


def _probabili_della_rosa(db, giornata, rosa):
    """Attacca a ogni giocatore della rosa la sua probabile, se c'è.

    ⚠️ Un giocatore senza riga nelle probabili **non è «non convocato»**: può
    esserlo, oppure la sua squadra può non giocare quella giornata (rinvii,
    recuperi). Sono due cose diverse e la pagina le dice diverse, perché è
    esattamente il caso in cui un'etichetta sbagliata farebbe schierare un giocatore
    che non scende in campo. Chi decide è `fanta_probabili_squadre`: se la squadra
    è lì, la giornata la gioca.
    """
    if not giornata or not rosa:
        return {}
    squadre = {r["squadra_slug"]: dict(r) for r in db.execute(
        "SELECT * FROM fanta_probabili_squadre WHERE giornata=?", (giornata,)).fetchall()}
    ids = [g["id"] for g in rosa]
    segni = ",".join("?" * len(ids))
    righe = {r["player_id"]: dict(r) for r in db.execute(
        f"SELECT * FROM fanta_probabili WHERE giornata=? AND player_id IN ({segni})",
        [giornata] + ids).fetchall()}
    fuori = {}
    for g in rosa:
        squadra = squadre.get(g["squadra_slug"])
        voce = righe.get(g["id"])
        if voce:
            stato = "titolare" if voce["titolare"] else "panchina"
        elif squadra:
            stato = "fuori"          # la squadra gioca, lui non è fra i convocati
        else:
            stato = "non_gioca"      # la sua squadra non è in questa giornata
        fuori[g["id"]] = {"stato": stato,
                          "percentuale": (voce or {}).get("percentuale"),
                          "squadra": squadra}
    return fuori


def _schierati(db, lid):
    """Chi è schierato in questa lega: `{player_id: riga}`.

    ⚠️ La query non filtra per proprietario e **non deve**: `fanta_formazione` non
    ha un `user_id` e lo eredita dalla lega, esattamente come `fanta_roster`. Chi
    chiama ha già in mano la lega — perché l'ha letta con `_lega_mia()` o perché
    gliel'ha data `ambito_utente()` — e questa funzione non si usa con un `lid`
    che non sia passato di lì (§1.1).
    """
    return {r["player_id"]: dict(r) for r in db.execute(
        "SELECT player_id, titolare, ordine FROM fanta_formazione WHERE league_id=?",
        (lid,)).fetchall()}


def _scendi_dal_campo(db, lid, player_ids):
    """Toglie dalla formazione chi esce dalla rosa. Torna quante righe ha tolto.

    Decisione di Davide del 22/09/2026, presa sul baco trovato il giorno prima:
    `fanta_roster` e `fanta_formazione` sono due tabelle, e il `DELETE` sulla prima
    non toccava la seconda. A schermo non si vedeva niente — il campo smette di
    disegnare chi non è in rosa — ma i titolari diventavano dieci in silenzio.

    ⚠️ Vale **solo per chi esce dalla rosa**, non per chi esce dal listone: quello
    resta in rosa, spento, col suo cartellino «fuori listone», ed è la scelta del
    mercato di gennaio. Le due cose si somigliano e non sono la stessa.

    ⚠️ Il chiamante ha già cancellato dalla rosa **con il filtro del proprietario**
    e ha guardato il `rowcount`: qui si arriva solo se quella riga era davvero sua
    (§1.1, stessa ragione dichiarata per `_schierati()`).
    """
    if not player_ids:
        return 0
    segni = ",".join("?" * len(player_ids))
    return db.execute(
        f"DELETE FROM fanta_formazione WHERE league_id=? AND player_id IN ({segni})",
        (lid,) + tuple(player_ids)).rowcount


def _allerta(db, lid, rosa, probabili):
    """L'avviso «la formazione salvata non torna più con le probabili», o `None`.

    Chiesto da Davide il 22/09/2026, ed è automatico nel solo senso che questa
    app può permettersi: **si calcola quando apri la pagina**, non mentre non la
    guardi. Le probabili si rileggono da sé quando la copia ha più di tre ore
    (`_aggiorna_se_vecchio`), quindi entrare nella sezione basta; un avviso che
    arrivi venerdì sera da solo vorrebbe dire un processo che gira sempre, ed è
    un'altra cosa.

    ⚠️ Torna `None` quando non c'è **niente da dire**, compreso il caso «non ho
    ancora schierato»: un riquadro giallo vuoto insegna a ignorare i riquadri
    gialli.
    """
    schierati = _schierati(db, lid)
    if not schierati:
        return None
    in_rosa = {g["id"] for g in rosa}
    nomi = {g["id"]: g["nome"] for g in rosa}
    # ⚠️ Chi è schierato ma **non è più in rosa** un nome nella rosa non ce l'ha
    # più, e l'avviso lo chiamava «?» — cioè diceva «c'è un problema» senza dire
    # su chi. Il nome si prende dal listone, che è dato condiviso e li ha tutti.
    mancanti = [p for p in schierati if p not in nomi]
    if mancanti:
        segni = ",".join("?" * len(mancanti))
        nomi.update({r["id"]: r["nome"] for r in db.execute(
            f"SELECT id, nome FROM fanta_players WHERE id IN ({segni})",
            mancanti).fetchall()})
    allerta = controlla_schierati(schierati, probabili, nomi, in_rosa=in_rosa)
    # ⚠️ Senza **guai** non si torna niente, anche se ci fossero delle occasioni:
    # «in panchina hai due titolari» su una formazione che torna è rumore, e un
    # riquadro giallo che compare quando va tutto bene insegna a non leggerlo. Le
    # occasioni sono il contorno di un avviso, non un avviso.
    if not quanti_guai(allerta):
        return None
    return allerta


def _prezzo(grezzo):
    """Il prezzo pagato come lo scrive chi compila: `12`, `12,5`, o niente.

    Un campo vuoto vale **0**, non `None`: è la convenzione con cui la colonna è
    nata (`DEFAULT 0`) e con cui la pagina la legge — `{% if g.prezzo %}` non
    mostra lo zero, quindi «non l'ho pagato» e «non me lo ricordo» si vedono uguali.
    Cambiarla adesso vorrebbe dire rileggere tutte le rose già scritte.
    """
    try:
        return float(str(grezzo or 0).replace(",", "."))
    except ValueError:
        return 0.0


def _numeri(f):
    """**Solo** le regole che il form ha davvero mandato, già convertite.

    ⚠️ Un campo vuoto non vale zero e non vale `None`: vale «non l'ho toccato», e
    quindi la colonna **non entra nella query**. Sono due bachi in uno, e la prova
    li ha presi tutti e due:

    - in `INSERT`, passare `None` per un campo non compilato **scavalca il `DEFAULT`
      della tabella**: una lega nuova nasceva con gol +NULL invece di +3, e nessuno
      dava errore — il bonus semplicemente non c'era;
    - in `UPDATE`, rimetterci il valore vecchio funziona, ma solo finché qualcuno
      non dimentica di passare `riga`. Non mettendo la colonna nel `SET`, il valore
      di prima resta perché non è stato toccato, che è la stessa cosa detta bene.
    """
    fuori = {}
    for colonna, _, _, _ in REGOLE:
        grezzo = f.get(colonna)
        # ⚠️ Dal 21/09/2026 ogni regola è una tendina, e la tendina manda sempre
        # qualcosa: `altro` vuol dire «guarda la casella qui accanto», che è
        # `<colonna>_altro`. Se anche quella è vuota la colonna **non entra nella
        # query** — la regola di sopra vale ancora, ed è quella che impedisce a un
        # campo lasciato stare di azzerare un bonus.
        if str(grezzo).strip() == "altro":
            grezzo = f.get(colonna + "_altro")
        if grezzo is None or str(grezzo).strip() == "":
            continue
        try:
            fuori[colonna] = float(str(grezzo).replace(",", "."))
        except ValueError:
            continue
    return fuori


@bp.route("/")
@login_required
def fantacalcio():
    db = get_db()
    # Entrando nella sezione: se la copia è più vecchia della sua soglia, si
    # rilegge. Non blocca la pagina se la fonte non risponde — il guaio diventa un
    # avviso e i numeri di prima restano.
    for quale in ("listone", "probabili"):
        guaio = _aggiorna_se_vecchio(db, quale)
        if guaio:
            flash(guaio, "error")
    # ⚠️ Il calendario **dopo** le probabili, e sapendo quale giornata: la pagina
    # generica del calendario è quella in corso, e le probabili sono già sulla
    # prossima. Chiedendo la giornata giusta il timer non sparisce proprio nella
    # settimana in cui serve.
    guaio = _aggiorna_se_vecchio(db, "calendario", _giornata_probabili(db))
    if guaio:
        flash(guaio, "error")
    di = _i(request.args.get("utente")) or None
    cond, par = ambito_utente(di=di)
    leghe = [dict(r) for r in db.execute(
        "SELECT l.*, (SELECT COUNT(*) FROM fanta_roster r WHERE r.league_id=l.id) "
        f"AS quanti FROM fanta_leagues l WHERE {cond} ORDER BY l.nome", par).fetchall()]
    listone = db.execute(
        "SELECT COUNT(*) AS attivi, MAX(visto_il) AS visto, "
        "(SELECT COUNT(*) FROM fanta_players WHERE attivo=0) AS spenti "
        "FROM fanta_players WHERE attivo=1").fetchone()
    # Lo stesso motivo per cui si dichiara la data del listone: una giornata vecchia
    # non dà errore, dà una formazione che non è più quella.
    stato_probabili = db.execute(
        "SELECT giornata, COUNT(*) AS quanti, MAX(aggiornato_il) AS quando "
        "FROM fanta_probabili GROUP BY giornata "
        "ORDER BY giornata DESC LIMIT 1").fetchone()
    nomi_utenti = {r["id"]: r["username"] for r in
                   db.execute("SELECT id, username FROM users")} if e_admin() else {}
    proprietari = []
    if e_admin():
        proprietari = [dict(r) for r in db.execute(
            "SELECT u.id, u.username, COUNT(l.id) AS quanti FROM users u "
            "JOIN fanta_leagues l ON l.user_id=u.id GROUP BY u.id, u.username "
            "ORDER BY u.username").fetchall()]
    # Quante cose da guardare ha la formazione di ogni lega. ⚠️ Si conta qui, in
    # cima alla sezione, perche' e' la pagina che si apre per prima: sapere che c'e'
    # qualcosa da sistemare **prima** di entrare nella lega e' tutto il punto.
    # Le occasioni non entrano nel conto (`quanti_guai`): un suggerimento non e' un
    # guaio, e un numero rosso su una formazione a posto si impara a ignorarlo.
    giornata_ora = _giornata_probabili(db)
    guai_lega = {}
    for l in leghe:
        rosa_l = _rosa_della_lega(db, l["id"])
        allerta = _allerta(db, l["id"], rosa_l,
                           _probabili_della_rosa(db, giornata_ora, rosa_l))
        quanti = quanti_guai(allerta)
        if quanti:
            guai_lega[l["id"]] = quanti
    eta = {q: I.serve_aggiornare(db, q)[1] for q in ("listone", "probabili")}
    eta["calendario"] = I.serve_aggiornare(db, "calendario", giornata_ora)[1]
    # Entro quando si schiera: e' il fischio d'inizio della prima partita della
    # giornata, uguale per tutte le leghe. Puo' mancare, e allora la pagina lo dice.
    scadenza = scadenza_giornata(db, giornata_ora)
    db.close()
    return render_template("fantacalcio.html", leghe=leghe,
                           listone=dict(listone) if listone else {},
                           probabili=dict(stato_probabili) if stato_probabili else {},
                           regole=REGOLE, ufficiali=UFFICIALI,
                           valore_ufficiale=VALORE_UFFICIALE,
                           valore_partenza=VALORE_PARTENZA,
                           soglie_standard=MOD_DIFESA_SOGLIE,
                           soglie_quarti=MOD_DIFESA_SOGLIE_QUARTI,
                           soglie_lega={l["id"]: soglie_mod_difesa(
                               l.get("mod_difesa_soglie")) for l in leghe},
                           eta_cache=eta, guai_lega=guai_lega, scadenza=scadenza,
                           giornata=giornata_ora,
                           proprietari=proprietari, filtro_utente=di,
                           nomi_utenti=nomi_utenti)


@bp.route("/aggiorna/<quale>", methods=["POST"])
@login_required
def aggiorna(quale):
    """Il pulsante «Aggiorna ora»: rilegge dalla fonte adesso, senza aspettare.

    ⚠️ È un `POST` di proposito. Scarica tre pagine da fantacalcio.it e riscrive
    delle righe: un `GET` così si rifarebbe da solo a ogni ricarica del browser,
    e basterebbe tenere premuto F5 per martellare la fonte.
    """
    if quale not in ("listone", "probabili", "calendario"):
        flash("Non so cosa aggiornare", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    db = get_db()
    # Il pulsante del calendario legge **la giornata delle probabili**, come fa
    # l'aggiornamento automatico: premerlo e aspettare non devono dare due
    # risultati diversi.
    messaggio, categoria = _aggiorna(
        db, quale, giornata=_giornata_probabili(db) if quale == "calendario" else None)
    db.close()
    flash(messaggio, categoria)
    dove = request.form.get("torna_a")
    return redirect(dove if dove and dove.startswith("/fantacalcio")
                    else url_for("fantacalcio.fantacalcio"))


@bp.route("/lega/salva", methods=["POST"])
@login_required
def lega_salva():
    f = request.form
    lid = _i(f.get("lega_id", 0))
    nome = (f.get("nome") or "").strip()
    if not nome:
        flash("Il nome della lega è obbligatorio", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    moduli = (f.get("moduli") or "").strip()
    # ⚠️ Un modulo scritto male non si salva «tanto poi si vede»: senza questo
    # controllo la validazione della formazione direbbe di no a una rosa giusta.
    sbagliati = [m.strip() for m in moduli.split(",")
                 if m.strip() and not scomponi_modulo(m)]
    if sbagliati:
        flash(f"Moduli che non tornano (i dieci di movimento devono fare 10): "
              f"{', '.join(sbagliati)}", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    # Le soglie del modificatore di difesa arrivano come tre coppie media/punti.
    # ⚠️ Si salvano solo se ne è arrivata almeno una **leggibile**: una riga scritta
    # male non diventa una tabella a caso, si tiene quella di prima. Chi non tocca
    # niente non le manda affatto, e allora la colonna resta com'è.
    soglie = []
    for media, punti in zip(f.getlist("soglia_media"), f.getlist("soglia_punti")):
        media, punti = (media or "").strip(), (punti or "").strip()
        if not media or not punti:
            continue
        try:
            soglie.append((float(media.replace(",", ".")),
                           float(punti.replace(",", "."))))
        except ValueError:
            flash(f"Soglia del modificatore che non è un numero: «{media}: {punti}»",
                  "error")
            return redirect(url_for("fantacalcio.fantacalcio"))

    db = get_db()
    riga = _lega_mia(db, lid) if lid else None
    valori = _numeri(f)
    comuni = {
        "nome": nome,
        "sistema": "classic",
        "moduli": moduli or None,
        "n_panchinari": _i(f.get("n_panchinari"), 7),
        "mod_difesa": 1 if f.get("mod_difesa") else 0,
        "mod_difesa_portiere": 1 if f.get("mod_difesa_portiere") else 0,
        "note": (f.get("note") or "").strip() or None,
    }
    if soglie:
        comuni["mod_difesa_soglie"] = scrivi_soglie(
            sorted(soglie, key=lambda x: x[0], reverse=True))
    comuni.update(valori)

    if lid:
        if riga is None:
            db.close()
            flash("Lega non trovata", "error")
            return redirect(url_for("fantacalcio.fantacalcio"))
        cond, par = solo_mie()
        sets = ", ".join(f"{c}=?" for c in comuni)
        cur = db.execute(f"UPDATE fanta_leagues SET {sets} WHERE id=? AND {cond}",
                         list(comuni.values()) + [lid] + list(par))
        if cur.rowcount == 0:
            db.close()
            flash("Lega non trovata", "error")
            return redirect(url_for("fantacalcio.fantacalcio"))
    else:
        comuni["user_id"] = utente_id()
        colonne = ", ".join(comuni)
        segni = ", ".join("?" * len(comuni))
        db.execute(f"INSERT INTO fanta_leagues({colonne}) VALUES({segni})",
                   list(comuni.values()))
    db.commit()
    db.close()
    flash("Salvato", "success")
    return redirect(url_for("fantacalcio.fantacalcio"))


@bp.route("/lega/<int:lid>/elimina", methods=["POST"])
@login_required
def lega_elimina(lid):
    db = get_db()
    cond, par = solo_mie()
    # La rosa se ne va con la lega: `ON DELETE CASCADE` sullo schema, ma SQLite lo
    # applica solo con i foreign key accesi, quindi la si toglie qui a mano.
    db.execute("DELETE FROM fanta_roster WHERE league_id IN "
               f"(SELECT id FROM fanta_leagues WHERE id=? AND {cond})",
               (lid,) + tuple(par))
    cur = db.execute(f"DELETE FROM fanta_leagues WHERE id=? AND {cond}",
                     (lid,) + tuple(par))
    db.commit()
    db.close()
    flash("Eliminata" if cur.rowcount else "Lega non trovata",
          "success" if cur.rowcount else "error")
    return redirect(url_for("fantacalcio.fantacalcio"))


@bp.route("/lega/<int:lid>")
@login_required
def lega(lid):
    db = get_db()
    # Anche qui: la pagina mostra le probabili della rosa, quindi vale la stessa
    # regola dell'elenco: se la copia ha più di tre ore si rilegge. Il calendario
    # viene dopo, perché vuole sapere di quale giornata (vedi l'elenco).
    guaio = _aggiorna_se_vecchio(db, "probabili")
    if guaio:
        flash(guaio, "error")
    guaio = _aggiorna_se_vecchio(db, "calendario", _giornata_probabili(db))
    if guaio:
        flash(guaio, "error")
    riga = _lega_mia(db, lid)
    if riga is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    # ⚠️ La rosa si legge **passando dalla lega**: `fanta_roster` non ha un
    # proprietario suo, quindi una SELECT diretta sarebbe scoperta (§1.1).
    cond, par = ambito_utente("l.user_id")
    rosa = [dict(r) for r in db.execute(
        "SELECT r.id AS rid, r.prezzo, r.note, p.* FROM fanta_roster r "
        "JOIN fanta_leagues l ON l.id = r.league_id "
        "JOIN fanta_players p ON p.id = r.player_id "
        f"WHERE r.league_id=? AND {cond} "
        "ORDER BY CASE p.ruolo_classic WHEN 'p' THEN 0 WHEN 'd' THEN 1 "
        "WHEN 'c' THEN 2 ELSE 3 END, p.nome",
        (lid,) + tuple(par)).fetchall()]

    # Le probabili della giornata, attaccate alla rosa. Dato condiviso: non passa
    # da `ambito_utente()` perché le formazioni della Serie A non sono di nessuno.
    giornata = _giornata_probabili(db, _i(request.args.get("giornata")))
    probabili = _probabili_della_rosa(db, giornata, rosa)
    aggiornate = db.execute("SELECT MAX(aggiornato_il) AS q FROM fanta_probabili "
                            "WHERE giornata=?", (giornata,)).fetchone() if giornata else None
    # La formazione gia' schierata contro le probabili di adesso: e' qui e non solo
    # sul campo perche' questa e' la pagina da cui si passa, e un avviso che si vede
    # solo dove si sta gia' guardando non avvisa nessuno.
    allerta = _allerta(db, lid, rosa, probabili)
    scadenza = scadenza_giornata(db, giornata)
    db.close()

    per_ruolo = {r: [g for g in rosa if g["ruolo_classic"] == r]
                 for r in ORDINE_RUOLI_FANTA}
    spenti = [g for g in rosa if not g["attivo"]]
    moduli = [m.strip() for m in (riga.get("moduli") or "").split(",") if m.strip()]
    # Quanti ne servirebbero per ogni modulo ammesso, e se la rosa ci arriva.
    copertura = []
    for m in moduli:
        serve = scomponi_modulo(m)
        if not serve:
            continue
        mancano = {r: serve[r] - len([g for g in per_ruolo[r] if g["attivo"]])
                   for r in ORDINE_RUOLI_FANTA}
        copertura.append({"modulo": m, "serve": serve,
                          "mancano": {r: n for r, n in mancano.items() if n > 0}})
    speso = sum(g["prezzo"] or 0 for g in rosa)
    return render_template("fanta_lega.html", lega=riga, rosa=rosa,
                           per_ruolo=per_ruolo, ruoli=RUOLI_FANTA,
                           # «mancano 2 difensori», non «2 Difensore»: il plurale
                           # dei quattro ruoli lo sa già `nome_ruolo()`.
                           nome_ruolo=nome_ruolo,
                           ordine=ORDINE_RUOLI_FANTA, spenti=spenti,
                           copertura=copertura, speso=speso,
                           regole=REGOLE, ufficiali=UFFICIALI,
                           valore_ufficiale=VALORE_UFFICIALE,
                           soglie=soglie_mod_difesa(riga.get("mod_difesa_soglie")),
                           fasce=fasce_mod_difesa(
                               soglie_mod_difesa(riga.get("mod_difesa_soglie"))),
                           soglie_standard=MOD_DIFESA_SOGLIE,
                           esempi_difesa=[(m, modificatore_difesa(
                               m, soglie_mod_difesa(riga.get("mod_difesa_soglie"))))
                               for m in (5.5, 6.0, 6.5, 7.0, 7.5)],
                           giornata=giornata, probabili=probabili, allerta=allerta,
                           scadenza=scadenza,
                           probabili_aggiornate=(aggiornate["q"] if aggiornate else None))


def _rosa_della_lega(db, lid):
    """La rosa, coi campi che servono a schierare. Passa **dalla lega** (§1.1)."""
    cond, par = ambito_utente("l.user_id")
    return [dict(r) for r in db.execute(
        "SELECT r.prezzo, p.* FROM fanta_roster r "
        "JOIN fanta_leagues l ON l.id = r.league_id "
        "JOIN fanta_players p ON p.id = r.player_id "
        f"WHERE r.league_id=? AND {cond} "
        "ORDER BY CASE p.ruolo_classic WHEN 'p' THEN 0 WHEN 'd' THEN 1 "
        "WHEN 'c' THEN 2 ELSE 3 END, p.nome",
        (lid,) + tuple(par)).fetchall()]


@bp.route("/lega/<int:lid>/formazione")
@login_required
def formazione(lid):
    """Il campo da gioco **e** il consiglio della giornata, nella stessa pagina.

    ⚠️ Una formazione sola per lega, senza giornata: è la scelta di Davide del
    21/09/2026. Le **probabili** invece la giornata ce l'hanno, e si vedono accanto
    a ogni giocatore mentre si schiera — è tutto il motivo per cui sono state fatte
    prima di questa pagina.

    Dal 22/09/2026 il consiglio non ha più una pagina sua: sta **sotto il campo**,
    perché si schiera guardandolo e cambiare schermata per leggerlo significava
    tenere a mente undici nomi. Il contesto lo prepara `_consiglio()`, la stessa
    funzione che usa «applica»: due calcoli diversi per la stessa giornata
    potrebbero dire due cose diverse, e nessuno se ne accorgerebbe.
    """
    db = get_db()
    # Le probabili invecchiano in tre ore, il calendario in un giorno: se la copia
    # ha passato la sua soglia si rilegge, e se la fonte non risponde la pagina si
    # apre lo stesso col dato di prima. Il calendario chiede **la giornata delle
    # probabili**, non quella in corso (vedi l'elenco delle leghe).
    guaio = _aggiorna_se_vecchio(db, "probabili")
    if guaio:
        flash(guaio, "error")
    guaio = _aggiorna_se_vecchio(db, "calendario", _giornata_probabili(db))
    if guaio:
        flash(guaio, "error")
    lega, ctx = _consiglio(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    rosa, giornata = ctx["rosa"], ctx["giornata"]
    schierati = {r["player_id"]: dict(r) for r in db.execute(
        "SELECT * FROM fanta_formazione WHERE league_id=? ORDER BY titolare DESC, ordine",
        (lid,)).fetchall()}
    allerta = _allerta(db, lid, rosa, ctx["probabili"])
    scadenza = scadenza_giornata(db, giornata)
    db.close()

    moduli = [m.strip() for m in (lega.get("moduli") or "").split(",")
              if m.strip() and scomponi_modulo(m.strip())]
    # Il modulo da mostrare: quello salvato se è ancora fra gli ammessi, altrimenti
    # il primo. ⚠️ Un modulo tolto dalle regole dopo aver schierato lascerebbe la
    # pagina su un modulo che la lega non ammette più, e il salvataggio lo
    # rifiuterebbe senza che si capisca perché.
    scelto = lega.get("modulo_scelto")
    if scelto not in moduli:
        scelto = moduli[0] if moduli else None

    # Quale modulo il consiglio mostra in dettaglio. ⚠️ Il parametro si chiama
    # `dettaglio` e **non** `modulo`: in questa pagina «modulo» è già il modulo del
    # campo, e due cose diverse con lo stesso nome nell'URL finiscono per
    # sovrascriversi a vicenda. Senza richiesta esplicita si mostra il consiglio
    # per il modulo che è nel campo — è quello che serve mentre si schiera — e se
    # quel modulo non è consigliabile si ripiega sul migliore.
    consigli = ctx["consigli"]
    chiesto = (request.args.get("dettaglio") or "").strip()
    dettaglio = next((c for c in consigli if c["modulo"] == chiesto), None)
    if dettaglio is None and scelto:
        dettaglio = next((c for c in consigli if c["modulo"] == scelto), None)
    if dettaglio is None:
        dettaglio = next((c for c in consigli if c["migliore"]), None)
    if dettaglio is None and consigli:
        dettaglio = consigli[0]

    return render_template(
        "fanta_formazione.html", lega=lega, ruoli=RUOLI_FANTA,
        ordine=ORDINE_RUOLI_FANTA, moduli=moduli,
        modulo=scelto, schierati=schierati, allerta=allerta, scadenza=scadenza,
        reparti={m: scomponi_modulo(m) for m in moduli},
        dettaglio=dettaglio, fasce=FASCE_TITOLARITA, soglia=SOGLIA_SCHIERABILE,
        minimo_partite=MINIMO_PARTITE_FIDATO,
        etichetta_fascia=etichetta_fascia, **ctx)


def _scrivi_formazione(db, lid, modulo, titolari, panchinari, rosa):
    """Scrive la formazione e il modulo. `True` se ha scritto, `False` se la lega
    non è di chi sta scrivendo. **Chiude il db in ogni caso.**

    ⚠️ Sta qui, e non dentro la route, perché la scrivono in **due** — il campo e
    il pulsante «applica» del consiglio. Riscriverla due volte era la strada facile,
    ed è lo stesso errore che ha tenuto in vita per un mese il difetto di `main` nel
    moveset e che `fanta_import.py` esiste per non ripetere.

    Si riscrive per intero: una formazione è una cosa sola, e aggiornarla riga per
    riga vorrebbe dire poter lasciare in campo qualcuno che è stato tolto.
    ⚠️ Due forme della stessa condizione, e non sono intercambiabili: `UPDATE` non
    ha un alias, quindi vuole la colonna nuda. Scritta con l'alias dà «no such
    column: l.user_id» — l'ha presa la prova al primo giro.
    """
    cond, par = solo_mie()
    db.execute("DELETE FROM fanta_formazione WHERE league_id=? AND league_id IN "
               f"(SELECT id FROM fanta_leagues WHERE id=? AND {cond})",
               (lid, lid) + tuple(par))
    db.executemany(
        "INSERT INTO fanta_formazione(league_id, player_id, titolare, ordine, ruolo)"
        " VALUES(?,?,?,?,?)",
        [(lid, p, 1, i, rosa.get(p)) for i, p in enumerate(titolari)] +
        [(lid, p, 0, i, rosa.get(p)) for i, p in enumerate(panchinari)])
    cur = db.execute(f"UPDATE fanta_leagues SET modulo_scelto=? WHERE id=? AND {cond}",
                     (modulo, lid) + tuple(par))
    if cur.rowcount == 0:
        # La lega non è di chi salva: la formazione appena scritta non deve
        # restare. ⚠️ `_lega_mia()` l'aveva già detto in cima a chi chiama, ma qui
        # si guarda il `rowcount` perché una scrittura che non tocca niente **non
        # dà errore**.
        db.execute("DELETE FROM fanta_formazione WHERE league_id=?", (lid,))
        db.commit()
        db.close()
        return False
    db.commit()
    db.close()
    return True


@bp.route("/lega/<int:lid>/formazione/salva", methods=["POST"])
@login_required
def formazione_salva(lid):
    """Salva la formazione, **se torna**.

    Davide ha scelto la validazione severa: quello che non torna non si salva,
    come già succede a un modulo scritto male. ⚠️ Il ruolo di ogni giocatore lo
    decide la **rosa**, non il form: un `ruolo` mandato dal browser direbbe che
    un attaccante è un difensore, e il conto dei reparti tornerebbe lo stesso.
    """
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    modulo = (request.form.get("modulo") or "").strip()
    titolari = [_i(x) for x in request.form.getlist("titolare") if _i(x)]
    panchinari = [_i(x) for x in request.form.getlist("panchinaro") if _i(x)]
    rosa = {g["id"]: g["ruolo_classic"] for g in _rosa_della_lega(db, lid)}

    ammessi = [m.strip() for m in (lega.get("moduli") or "").split(",") if m.strip()]
    guai = []
    if ammessi and modulo not in ammessi:
        guai.append(f"Il modulo {modulo or '—'} non è fra quelli ammessi da questa "
                    f"lega ({', '.join(ammessi)}).")
    guai += controlla_formazione(modulo, titolari, panchinari, rosa,
                                 lega.get("n_panchinari"))
    if guai:
        db.close()
        for g in guai:
            flash(g, "error")
        return redirect(url_for("fantacalcio.formazione", lid=lid))

    if not _scrivi_formazione(db, lid, modulo, titolari, panchinari, rosa):
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    flash(f"Formazione salvata: {modulo}, {len(titolari)} titolari e "
          f"{len(panchinari)} in panchina", "success")
    return redirect(url_for("fantacalcio.formazione", lid=lid))


def _consiglio(db, lid):
    """Tutto quello che serve al consiglio di una lega: `(lega, contesto)`.

    Sta fuori dalle route perché la usano in due — la pagina che lo mostra e il
    pulsante che lo applica al campo. ⚠️ E devono usare **la stessa**: un «applica»
    che ricalcolasse il consiglio per conto suo potrebbe scrivere una formazione
    diversa da quella che è stata guardata, e nessuno se ne accorgerebbe.
    """
    lega = _lega_mia(db, lid)
    if lega is None:
        return None, None
    rosa = _rosa_della_lega(db, lid)
    giornata = _giornata_probabili(db)
    probabili = _probabili_della_rosa(db, giornata, rosa)
    aggiornate = db.execute("SELECT MAX(aggiornato_il) AS q FROM fanta_probabili "
                            "WHERE giornata=?", (giornata,)).fetchone() if giornata else None
    valutazioni = valuta_rosa(rosa, probabili, lega)
    moduli = [m.strip() for m in (lega.get("moduli") or "").split(",")
              if m.strip() and scomponi_modulo(m.strip())]
    consigli = consiglia_moduli(valutazioni, moduli, lega.get("n_panchinari"),
                                regole=lega)
    return lega, {
        "rosa": rosa, "giornata": giornata, "valutazioni": valutazioni,
        "per_ruolo": rosa_per_merito(valutazioni), "consigli": consigli,
        "probabili": probabili,
        "probabili_aggiornate": (aggiornate["q"] if aggiornate else None),
    }


@bp.route("/lega/<int:lid>/consiglio")
@login_required
def consiglio(lid):
    """Il vecchio indirizzo del consiglio: adesso porta al campo, dove il
    consiglio sta.

    Richiesta di Davide del 22/09/2026: «la sezione consiglio deve stare sotto
    alla scelta di formazione, non voglio cambiare schermata». Non è una pagina in
    meno per risparmiare codice — si schiera **guardando** il consiglio, e tenere
    le due cose su due schermate voleva dire ricordare a memoria undici nomi.

    ⚠️ Questo indirizzo resta perché è scritto in link e segnalibri, e perché un
    404 su una pagina che c'era non spiega niente. Il parametro `modulo` di prima
    diventa `dettaglio`: nel campo «modulo» vuol già dire un'altra cosa.

    ⚠️ Il controllo di proprietà **non si fa qui**: lo fa la pagina di arrivo, con
    `_lega_mia()`. Farlo in due punti vuol dire poterlo cambiare in uno solo.
    """
    chiesto = (request.args.get("dettaglio") or request.args.get("modulo") or "").strip()
    return redirect(url_for("fantacalcio.formazione", lid=lid,
                            dettaglio=chiesto or None, _anchor="consiglio"))


@bp.route("/lega/<int:lid>/consiglio/applica", methods=["POST"])
@login_required
def consiglio_applica(lid):
    """Porta il consiglio di un modulo nel campo, passando dalla **stessa**
    validazione del campo.

    ⚠️ Non scrive «perché lo dice il consiglio»: ricalcola il consiglio, prende
    l'undici e la panchina di **quel** modulo e li passa a `controlla_formazione()`
    come farebbe un salvataggio a mano. Se il consiglio producesse una formazione
    che non torna — un reparto che la rosa non copre, una panchina più lunga di
    quella ammessa — deve fallire come fallirebbe un form, non entrare da una porta
    di servizio. È anche l'unico modo di accorgersene.
    """
    db = get_db()
    lega, ctx = _consiglio(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    modulo = (request.form.get("modulo") or "").strip()
    scelto = next((c for c in ctx["consigli"] if c["modulo"] == modulo), None)
    if scelto is None:
        db.close()
        flash(f"Il modulo {modulo or '—'} non è fra quelli consigliabili per questa "
              "lega", "error")
        return redirect(url_for("fantacalcio.formazione", lid=lid,
                                _anchor="consiglio"))

    titolari = [v["g"]["id"] for v in scelto["titolari"]]
    panchinari = [v["g"]["id"] for v in scelto["panchina"]]
    rosa = {g["id"]: g["ruolo_classic"] for g in ctx["rosa"]}
    guai = controlla_formazione(modulo, titolari, panchinari, rosa,
                                lega.get("n_panchinari"))
    if guai:
        db.close()
        for g in guai:
            flash(g, "error")
        return redirect(url_for("fantacalcio.formazione", lid=lid,
                                _anchor="consiglio"))
    if not _scrivi_formazione(db, lid, modulo, titolari, panchinari, rosa):
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    flash(f"Consiglio applicato: {modulo}, {len(titolari)} titolari e "
          f"{len(panchinari)} in panchina. Ora aggiustalo come vuoi.", "success")
    return redirect(url_for("fantacalcio.formazione", lid=lid))


@bp.route("/lega/<int:lid>/rosa/aggiungi", methods=["POST"])
@login_required
def rosa_aggiungi(lid):
    pid = _i(request.form.get("player_id"))
    db = get_db()
    if _lega_mia(db, lid) is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    esiste = db.execute("SELECT nome FROM fanta_players WHERE id=?", (pid,)).fetchone()
    if not esiste:
        db.close()
        flash("Giocatore non trovato nel listone", "error")
        return redirect(url_for("fantacalcio.lega", lid=lid))
    prezzo = _prezzo(request.form.get("prezzo"))
    try:
        db.execute("INSERT INTO fanta_roster(league_id, player_id, prezzo, note) "
                   "VALUES(?,?,?,?)",
                   (lid, pid, prezzo, (request.form.get("note") or "").strip() or None))
        db.commit()
        flash(f"{esiste['nome']} aggiunto", "success")
    except Exception:
        # L'unico vincolo qui è UNIQUE(league_id, player_id): averlo già in rosa
        # non è un errore da mostrare come tale.
        flash(f"{esiste['nome']} è già in questa rosa", "error")
    db.close()
    return redirect(url_for("fantacalcio.lega", lid=lid))


@bp.route("/lega/<int:lid>/rosa/<int:rid>/rimuovi", methods=["POST"])
@login_required
def rosa_rimuovi(lid, rid):
    db = get_db()
    cond, par = solo_mie("l.user_id")
    mia = f"league_id IN (SELECT l.id FROM fanta_leagues l WHERE {cond})"
    # Il `player_id` si legge **prima** del DELETE: dopo non c'è più, e senza non
    # si saprebbe chi togliere anche dal campo.
    riga = db.execute(f"SELECT player_id FROM fanta_roster WHERE id=? AND "
                      f"league_id=? AND {mia}", (rid, lid) + tuple(par)).fetchone()
    cur = db.execute(
        f"DELETE FROM fanta_roster WHERE id=? AND league_id=? AND {mia}",
        (rid, lid) + tuple(par))
    scesi = _scendi_dal_campo(db, lid, [riga["player_id"]]) if cur.rowcount else 0
    db.commit()
    db.close()
    flash(("Tolto dalla rosa, ed era schierato" if scesi else "Tolto dalla rosa")
          if cur.rowcount else "Non trovato",
          "success" if cur.rowcount else "error")
    return redirect(url_for("fantacalcio.lega", lid=lid))


@bp.route("/lega/<int:lid>/rosa/modifica", methods=["POST"])
@login_required
def rosa_modifica(lid):
    """I prezzi corretti e le righe tolte, in un colpo solo.

    Chiude le due voci rimaste aperte il 21/09/2026: il prezzo si poteva correggere
    **solo** nell'anteprima dell'incolla — una volta in rosa bisognava togliere e
    rimettere — e il togli era una riga per volta, cioè venticinque conferme per
    rifare una rosa. Sono lo stesso elenco e lo stesso form, quindi sono una route
    sola.

    ⚠️ Di quello che torna dal browser non si fida niente: i `rid` vengono
    **riletti dalla rosa di questa lega** prima di essere usati, quindi un id di
    un'altra lega non tocca niente. È la stessa scelta di `rosa_incolla_conferma()`
    con i `player_id`.

    ⚠️ Scrive come `rosa_rimuovi()`: `solo_mie()` sulla **lega**, perché
    `fanta_roster` non ha un proprietario suo (§1.1), e il `rowcount` guardato —
    una scrittura filtrata che non tocca niente non dà errore.
    """
    db = get_db()
    cond, par = solo_mie("l.user_id")
    mia = f"league_id IN (SELECT l.id FROM fanta_leagues l WHERE {cond})"
    # La rosa vera, prima di guardare il form: dice **quali** rid esistono qui e a
    # che prezzo stanno, che è anche l'unico modo per contare i prezzi davvero
    # cambiati invece di riscriverli tutti e dire «25 corretti».
    righe = {r["id"]: dict(r) for r in db.execute(
        f"SELECT id, player_id, prezzo FROM fanta_roster WHERE league_id=? AND {mia}",
        (lid,) + tuple(par)).fetchall()}

    togli = [r for r in (_i(v, None) for v in request.form.getlist("togli"))
             if r in righe]
    tolti, scesi = 0, 0
    if togli:
        segna = ",".join("?" * len(togli))
        tolti = db.execute(
            f"DELETE FROM fanta_roster WHERE id IN ({segna}) AND league_id=? AND {mia}",
            tuple(togli) + (lid,) + tuple(par)).rowcount
        if tolti:
            scesi = _scendi_dal_campo(db, lid, [righe[r]["player_id"] for r in togli])

    corretti = 0
    for rid, prima in righe.items():
        if rid in togli or f"prezzo_{rid}" not in request.form:
            continue
        adesso = _prezzo(request.form.get(f"prezzo_{rid}"))
        if adesso == (prima["prezzo"] or 0):
            continue
        corretti += db.execute(
            f"UPDATE fanta_roster SET prezzo=? WHERE id=? AND league_id=? AND {mia}",
            (adesso, rid, lid) + tuple(par)).rowcount
    db.commit()
    db.close()

    pezzi = []
    if corretti:
        pezzi.append(f"{corretti} prezz{'i corretti' if corretti > 1 else 'o corretto'}")
    if tolti:
        pezzi.append(f"{tolti} tolt{'i' if tolti > 1 else 'o'} dalla rosa" +
                     (f" ({scesi} er{'ano' if scesi > 1 else 'a'} schierat"
                      f"{'i' if scesi > 1 else 'o'})" if scesi else ""))
    flash(", ".join(pezzi).capitalize() if pezzi else "Niente da cambiare",
          "success" if pezzi else "error")
    return redirect(url_for("fantacalcio.lega", lid=lid))


def _listone(db):
    """Il listone intero, coi campi che servono ad abbinare un nome incollato.

    Dato **condiviso** come il catalogo Pokémon: non passa da `ambito_utente()` e
    non deve. Sono 597 righe (misurate il 21/09/2026) e si leggono in una volta
    perché l'abbinamento deve poter dire «questo nome ne trova due»: una query per
    riga incollata non saprebbe mai quanti omonimi ci sono.
    """
    return [dict(r) for r in db.execute(
        "SELECT id, nome, squadra, squadra_slug, ruolo_classic, qa, fvm, "
        "fantamedia, attivo FROM fanta_players").fetchall()]


def _ids_in_rosa(db, lid):
    """Gli id già in quella rosa. Passa **dalla lega**, come ogni lettura di §1.1."""
    cond, par = ambito_utente("l.user_id")
    return {r["player_id"] for r in db.execute(
        "SELECT r.player_id FROM fanta_roster r "
        "JOIN fanta_leagues l ON l.id = r.league_id "
        f"WHERE r.league_id=? AND {cond}", (lid,) + tuple(par)).fetchall()}


@bp.route("/lega/<int:lid>/rosa/incolla", methods=["POST"])
@login_required
def rosa_incolla(lid):
    """L'anteprima della rosa incollata: **legge e mostra, non scrive niente.**

    Una rosa sono ~25 giocatori e la ricerca ne aggiunge uno per volta: è il
    motivo per cui questa pagina esiste. Il passo in due tempi però non è una
    comodità, è la parte che la rende sicura — l'abbinamento di un nome può
    sbagliare **senza dare errore** (`Thuram` sono due giocatori in due squadre e
    due ruoli), e l'unico modo di accorgersene è vederlo prima che sia scritto.

    ⚠️ È un `POST` anche se non scrive: il testo incollato è un dato, non un
    parametro da mettere in un URL, e una rosa di venticinque nomi in querystring
    sarebbe anche troppo lunga.
    """
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))
    testo = request.form.get("testo") or ""
    righe = leggi_rosa_incollata(testo, _listone(db), _ids_in_rosa(db, lid))
    db.close()
    if not righe:
        flash("Non ho letto nessun nome: incolla una riga per giocatore", "error")
        return redirect(url_for("fantacalcio.lega", lid=lid))
    conto = {s: len([r for r in righe if r["stato"] == s])
             for s in ("ok", "conferma", "scegli", "niente")}
    return render_template("fanta_rosa_incolla.html", lega=lega, righe=righe,
                           testo=testo, conto=conto, ruoli=RUOLI_FANTA)


@bp.route("/lega/<int:lid>/rosa/incolla/conferma", methods=["POST"])
@login_required
def rosa_incolla_conferma(lid):
    """Scrive in rosa **solo** le righe spuntate, e dice riga per riga com'è andata.

    ⚠️ Di quello che torna dal browser non si fida niente: il `player_id` viene
    ricontrollato nel listone (un id inventato non entra) e la lega è la solita
    `_lega_mia()`. Il nome che l'anteprima mostrava non viene nemmeno riletto —
    quello che conta è l'id, come per l'incrocio delle tre pagine della fonte.
    """
    db = get_db()
    lega = _lega_mia(db, lid)
    if lega is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    validi = {r["id"] for r in db.execute("SELECT id FROM fanta_players").fetchall()}
    indici = sorted({_i(k[4:]) for k in request.form if k.startswith("pid_")
                     and _i(k[4:]) is not None})
    aggiunti, saltati, ignoti = 0, 0, 0
    for n in indici:
        if not request.form.get(f"riga_{n}"):
            continue                      # la spunta è la decisione: senza, non si scrive
        pid = _i(request.form.get(f"pid_{n}"))
        if pid is None or pid not in validi:
            ignoti += 1
            continue
        prezzo = _prezzo(request.form.get(f"prezzo_{n}"))
        try:
            db.execute("INSERT INTO fanta_roster(league_id, player_id, prezzo) "
                       "VALUES(?,?,?)", (lid, pid, prezzo))
            aggiunti += 1
        except Exception:
            # L'unico vincolo è UNIQUE(league_id, player_id): averlo già in rosa
            # non è un errore, è una riga che non serve.
            saltati += 1
    db.commit()
    db.close()
    pezzi = [f"{aggiunti} in rosa"]
    if saltati:
        pezzi.append(f"{saltati} già in rosa da prima")
    if ignoti:
        pezzi.append(f"{ignoti} senza un giocatore valido")
    flash(", ".join(pezzi), "success" if aggiunti else "error")
    return redirect(url_for("fantacalcio.lega", lid=lid))


@bp.route("/lega/<int:lid>/rosa/svuota", methods=["POST"])
@login_required
def rosa_svuota(lid):
    """Svuota **un ruolo** o **tutta la rosa**, in un colpo solo.

    Chiesto da Davide il 22/09/2026. Rifare una rosa a fine mercato voleva dire
    spuntare venticinque caselle in «Correggi la rosa»: qui il reparto (o la rosa
    intera) se ne va con un pulsante e una conferma.

    ⚠️ Chi esce dalla rosa esce **anche dal campo**, come per la × di una riga:
    `fanta_roster` e `fanta_formazione` sono due tabelle, e un DELETE sulla prima
    lascerebbe una formazione con dei titolari che non sono più in rosa — senza
    nessun errore, perché il campo smette semplicemente di disegnarli.

    ⚠️ `ruolo` arriva dal browser e viene **controllato**: solo `tutti` o uno dei
    quattro ruoli del Classic. Un valore qualsiasi finito nella query non
    cancellerebbe niente, e il messaggio direbbe comunque «fatto».
    """
    ruolo = (request.form.get("ruolo") or "").strip().lower()
    if ruolo not in ("tutti",) + tuple(ORDINE_RUOLI_FANTA):
        flash("Non so quale parte della rosa svuotare", "error")
        return redirect(url_for("fantacalcio.lega", lid=lid))

    db = get_db()
    if _lega_mia(db, lid) is None:
        db.close()
        flash("Lega non trovata", "error")
        return redirect(url_for("fantacalcio.fantacalcio"))

    # Si leggono **prima** le righe da togliere: dopo il DELETE non c'è più modo di
    # sapere chi far scendere dal campo, ed è lo stesso motivo per cui
    # `rosa_rimuovi()` legge il `player_id` prima di cancellarlo.
    cond, par = solo_mie("l.user_id")
    mia = f"league_id IN (SELECT l.id FROM fanta_leagues l WHERE {cond})"
    filtro = "" if ruolo == "tutti" else " AND p.ruolo_classic=?"
    coda = () if ruolo == "tutti" else (ruolo,)
    righe = [dict(r) for r in db.execute(
        f"SELECT r.id, r.player_id FROM fanta_roster r "
        f"JOIN fanta_players p ON p.id = r.player_id "
        f"WHERE r.league_id=? AND r.{mia}{filtro}",
        (lid,) + tuple(par) + coda).fetchall()]
    if not righe:
        db.close()
        flash("Non c'era niente da togliere", "error")
        return redirect(url_for("fantacalcio.lega", lid=lid))

    segni = ",".join("?" * len(righe))
    tolti = db.execute(
        f"DELETE FROM fanta_roster WHERE id IN ({segni}) AND league_id=? AND {mia}",
        tuple(r["id"] for r in righe) + (lid,) + tuple(par)).rowcount
    scesi = _scendi_dal_campo(db, lid, [r["player_id"] for r in righe]) if tolti else 0
    db.commit()
    db.close()
    quali = "Rosa svuotata" if ruolo == "tutti" else f"Reparto {nome_ruolo(ruolo, 2)} svuotato"
    flash(f"{quali}: {tolti} tolt{'i' if tolti > 1 else 'o'} dalla rosa" +
          (f" ({scesi} er{'ano' if scesi > 1 else 'a'} schierat"
           f"{'i' if scesi > 1 else 'o'})" if scesi else ""), "success")
    return redirect(url_for("fantacalcio.lega", lid=lid))



# Le colonne per cui il listone si può ordinare, e la direzione che ha senso per
# ognuna. ⚠️ Non si prende il nome della colonna dal browser: finirebbe dentro una
# query, che è il modo per farsi scrivere l'ordinamento da chi passa di lì. Qui
# l'URL sceglie **una chiave di questo dizionario**, e quello che non c'è ricade
# sul primo.
ORDINI_LISTONE = {
    "fvm": ("fvm DESC", "valore di mercato"),
    "qa": ("qa DESC", "quotazione attuale"),
    "fantamedia": ("fantamedia DESC", "fantamedia"),
    "media_voto": ("media_voto DESC", "media voto"),
    "partite": ("partite_a_voto DESC", "partite a voto"),
    "gol": ("gol DESC", "gol"),
    "assist": ("assist DESC", "assist"),
    "nome": ("nome ASC", "nome"),
}


@bp.route("/listone")
@login_required
def listone():
    """Il listone intero, da sfogliare e filtrare. Dato **condiviso**, non filtrato.

    Chiesto da Davide il 22/09/2026: fino a ieri il listone si poteva solo cercare
    per nome dentro la rosa di una lega, cioè si vedeva un giocatore per volta e
    solo per aggiungerlo. Qui si guardano tutti, si ordinano per quello che
    interessa, e cliccandone uno si apre la sua **scheda** con tutti i numeri che
    il listone porta.

    ⚠️ Gli spenti (chi ha lasciato la Serie A) si vedono solo chiedendolo, e
    restano **dichiarati**: nasconderli del tutto farebbe sembrare che il
    giocatore non sia mai esistito, mostrarli in mezzo agli altri farebbe sembrare
    che sia ancora schierabile.
    """
    db = get_db()
    q = (request.args.get("q") or "").strip()
    ruolo = (request.args.get("ruolo") or "").strip().lower()
    squadra = (request.args.get("squadra") or "").strip()
    ordine = request.args.get("ordine") if request.args.get("ordine") in ORDINI_LISTONE else "fvm"
    spenti = request.args.get("spenti") == "1"

    dove, par = [], []
    if not spenti:
        dove.append("attivo=1")
    if q:
        dove.append("nome LIKE ?")
        par.append(f"%{q}%")
    if ruolo in ORDINE_RUOLI_FANTA:
        dove.append("ruolo_classic=?")
        par.append(ruolo)
    else:
        ruolo = ""
    if squadra:
        dove.append("squadra=?")
        par.append(squadra)
    filtro = (" WHERE " + " AND ".join(dove)) if dove else ""
    # ⚠️ `NULLS LAST` a mano: in SQLite un `NULL` in `ORDER BY ... DESC` finisce in
    # **cima**, quindi ordinando per fantamedia i primi sarebbero i giocatori che
    # non hanno ancora giocato. Non darebbe errore, darebbe la classifica al
    # contrario.
    colonna = ORDINI_LISTONE[ordine][0]
    chiave = colonna.split()[0]
    righe = [dict(r) for r in db.execute(
        f"SELECT * FROM fanta_players{filtro} "
        f"ORDER BY ({chiave} IS NULL), {colonna}, nome", par).fetchall()]
    squadre = [r["squadra"] for r in db.execute(
        "SELECT DISTINCT squadra FROM fanta_players WHERE squadra IS NOT NULL "
        "AND attivo=1 ORDER BY squadra").fetchall()]
    totali = db.execute(
        "SELECT COUNT(*) AS attivi, MAX(visto_il) AS visto, "
        "(SELECT COUNT(*) FROM fanta_players WHERE attivo=0) AS spenti "
        "FROM fanta_players WHERE attivo=1").fetchone()
    # In quali **tue** leghe ognuno è già in rosa: passa dalle leghe, perché
    # `fanta_roster` non ha un proprietario suo (§1.1).
    cond, par_u = ambito_utente("l.user_id")
    mie = {}
    for r in db.execute(
            "SELECT r.player_id, l.id AS lid, l.nome FROM fanta_roster r "
            f"JOIN fanta_leagues l ON l.id=r.league_id WHERE {cond}", par_u):
        mie.setdefault(r["player_id"], []).append({"lid": r["lid"], "nome": r["nome"]})
    db.close()
    return render_template("fanta_listone.html", righe=righe, squadre=squadre,
                           ruoli=RUOLI_FANTA, ordine=ordine, ordini=ORDINI_LISTONE,
                           q=q, ruolo=ruolo, squadra=squadra, spenti=spenti,
                           totali=dict(totali) if totali else {}, mie=mie)


@bp.route("/api/giocatore/<int:pid>")
@login_required
def api_giocatore(pid):
    """La scheda di un giocatore: tutto quello che il listone sa di lui.

    Tre pezzi, e sono di tre nature diverse: la **riga del listone** (condivisa),
    la sua **probabile** dell'ultima giornata importata (condivisa) e **in quali
    tue rose** si trova (tua, quindi filtrata da `ambito_utente()` passando dalle
    leghe).

    ⚠️ Un campo che il listone non ha resta `null` e la scheda scrive «—»: qui si
    guardano i numeri per decidere chi comprare, e uno zero al posto di un dato
    mancante è la differenza fra «non ha mai segnato» e «non ha mai giocato».
    """
    db = get_db()
    riga = db.execute("SELECT * FROM fanta_players WHERE id=?", (pid,)).fetchone()
    if riga is None:
        db.close()
        return jsonify({"errore": "Giocatore non trovato nel listone"}), 404
    voce = dict(riga)

    giornata = _giornata_probabili(db)
    probabile = None
    if giornata:
        squadra = db.execute(
            "SELECT * FROM fanta_probabili_squadre WHERE giornata=? AND squadra_slug=?",
            (giornata, voce["squadra_slug"])).fetchone()
        riga_p = db.execute(
            "SELECT * FROM fanta_probabili WHERE giornata=? AND player_id=?",
            (giornata, pid)).fetchone()
        # Gli stessi quattro stati della scheda della lega, e per la stessa
        # ragione: «non convocato» e «la sua squadra non gioca» non sono la stessa
        # cosa, e scambiarle vuol dire schierare chi non scende in campo.
        if riga_p:
            stato = "titolare" if riga_p["titolare"] else "panchina"
        elif squadra:
            stato = "fuori"
        else:
            stato = "non_gioca"
        probabile = {"giornata": giornata, "stato": stato,
                     "percentuale": riga_p["percentuale"] if riga_p else None,
                     "squadra": dict(squadra) if squadra else None}

    cond, par = ambito_utente("l.user_id")
    rose = [{"lid": r["lid"], "lega": r["lega"], "prezzo": r["prezzo"]}
            for r in db.execute(
                "SELECT l.id AS lid, l.nome AS lega, r.prezzo FROM fanta_roster r "
                f"JOIN fanta_leagues l ON l.id=r.league_id WHERE r.player_id=? AND {cond} "
                "ORDER BY l.nome", (pid,) + tuple(par)).fetchall()]
    db.close()
    return jsonify({"giocatore": voce, "probabile": probabile, "rose": rose})


@bp.route("/probabili")
@login_required
def probabili():
    """Le probabili della giornata, partita per partita, coi **tuoi** segnati.

    Le formazioni sono un dato condiviso e si leggono senza filtro. Quello che
    invece è tuo è **quali di quei giocatori hai in rosa**, e quella parte passa da
    `ambito_utente()` sulle leghe: `fanta_roster` non ha un proprietario suo (§1.1).
    """
    db = get_db()
    # ⚠️ Solo quando si guarda l'**ultima** giornata: chiedere una giornata
    # passata è guardare l'archivio, e rileggere la fonte lì vorrebbe dire
    # riscrivere la giornata di oggi mentre si guarda quella di ieri.
    if not _i(request.args.get("giornata")):
        guaio = _aggiorna_se_vecchio(db, "probabili")
        if guaio:
            flash(guaio, "error")
    giornata = _giornata_probabili(db, _i(request.args.get("giornata")))
    giornate = [r["giornata"] for r in db.execute(
        "SELECT DISTINCT giornata FROM fanta_probabili_squadre ORDER BY giornata DESC")]
    squadre, voci, miei, aggiornate = {}, {}, {}, None
    if giornata:
        squadre = {r["squadra_slug"]: dict(r) for r in db.execute(
            "SELECT * FROM fanta_probabili_squadre WHERE giornata=? "
            "ORDER BY match_id, in_casa DESC", (giornata,)).fetchall()}
        for r in db.execute(
                "SELECT * FROM fanta_probabili WHERE giornata=? "
                "ORDER BY titolare DESC, CASE ruolo WHEN 'p' THEN 0 WHEN 'd' THEN 1 "
                "WHEN 'c' THEN 2 ELSE 3 END, percentuale DESC, nome", (giornata,)):
            voci.setdefault(r["squadra_slug"], []).append(dict(r))
        cond, par = ambito_utente("l.user_id")
        for r in db.execute(
                "SELECT r.player_id, l.id AS lid, l.nome AS lega FROM fanta_roster r "
                f"JOIN fanta_leagues l ON l.id=r.league_id WHERE {cond}", par):
            miei.setdefault(r["player_id"], []).append(
                {"lid": r["lid"], "lega": r["lega"]})
        fila = db.execute("SELECT MAX(aggiornato_il) AS q FROM fanta_probabili "
                          "WHERE giornata=?", (giornata,)).fetchone()
        aggiornate = fila["q"] if fila else None
    db.close()

    # Una voce per partita: le squadre stanno nel DB una per riga, e l'avversario
    # ce l'hanno dentro. Si rimettono insieme per `match_id`, non per nome.
    partite, viste = [], set()
    for slug, s in squadre.items():
        if slug in viste:
            continue
        altro = squadre.get(s["avversario_slug"] or "")
        casa, fuori = (s, altro) if s["in_casa"] else (altro, s)
        viste.update({slug, s["avversario_slug"]})
        partite.append({"casa": casa, "fuori": fuori,
                        "match_id": s["match_id"]})
    return render_template("fanta_probabili.html", giornata=giornata,
                           giornate=giornate, partite=partite, voci=voci,
                           miei=miei, ruoli=RUOLI_FANTA, aggiornate=aggiornate)


@bp.route("/api/giocatori")
@login_required
def api_giocatori():
    """I giocatori del listone che combaciano con `q`. Dato condiviso, non filtrato.

    ⚠️ Gli spenti restano cercabili ma **dichiarati**: servono quando si ricostruisce
    una rosa vecchia, e nasconderli farebbe sembrare che il giocatore non sia mai
    esistito.
    """
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    db = get_db()
    righe = db.execute(
        "SELECT id, nome, squadra, ruolo_classic, qa, fvm, fantamedia, attivo "
        "FROM fanta_players WHERE nome LIKE ? "
        "ORDER BY attivo DESC, fvm DESC, nome LIMIT 25", (f"%{q}%",)).fetchall()
    db.close()
    return jsonify([dict(r) for r in righe])
