"""Gestione utenti e permessi per sezione — solo per gli amministratori.

Il modello è quello chiesto a backlog: utenti **normali** e **amministratori**, e per
ognuno una spunta per sezione. Chi è admin vede tutto per definizione, quindi su di lui
le spunte non compaiono: sarebbero una promessa che il codice non mantiene.

⚠️ I permessi vivono in `users.sections`, un elenco di slug separati da virgole.
**Vuoto vale «tutte»**: è la scelta che tiene al sicuro chi c'era prima, perché la
colonna nasce vuota su tutti gli utenti esistenti.
"""
import re

from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   session)

from data import SEZIONI, SEZIONI_SLUG
from extensions import (get_db, login_required, NESSUNA_SEZIONE, hash_password,
                        TABELLE_UTENTE, tabelle_senza_regola, figlie_senza_regola,
                        copia_dati_utente, conteggi_utente, dimentica_tutte)

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Come si chiamano le tabelle a schermo. Un messaggio che dice «33 games, 1 pc_builds»
# fa leggere il nome di una tabella a chi sta guardando una pagina, e la conferma di
# un pulsante che non si annulla è l'ultimo posto dove farlo. Le figlie non ci sono:
# nel conto del padre sono già dentro — «2 leghe» vuol dire con le loro rose.
ETICHETTE = {
    "games": "giochi",
    "teams": "team",
    "arduino_projects": "progetti Arduino",
    "pc_builds": "build del PC",
    "fanta_leagues": "leghe del Fantacalcio",
    "stampa_progetti": "progetti di stampa 3D",
    "stampa_filamenti": "bobine di filamento",
    "stampa_file": "file da stampare",
    "team_members": "Pokémon nei team",
    "pc_components": "pezzi del PC",
    "fanta_roster": "giocatori in rosa",
    "fanta_formazione": "giocatori schierati",
    "python_progress": "spunte di Python",
}

# Dal 12/08/2026 le password nuove nascono già con lo schema forte (scrypt con sale
# di `werkzeug.security`). Le vecchie restano leggibili e vengono riscritte al primo
# login riuscito — vedi `verifica_password()` in extensions.py.
_hash = hash_password


def solo_admin(f):
    """Come login_required, ma richiede anche il ruolo. Applicato a tutto il blueprint."""
    from functools import wraps

    @wraps(f)
    def wrap(*a, **kw):
        if "username" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Serve un account amministratore.", "error")
            return redirect(url_for("dashboard.dashboard"))
        return f(*a, **kw)
    return wrap


@bp.before_request
@solo_admin
def _blocca_non_admin():
    """Il controllo sta qui e non sulle singole viste: una route nuova nasce protetta."""
    return None


def _sezioni_dal_form():
    """Le spunte del form -> valore per la colonna.

    ⚠️ Tre casi, non due, ed è il punto in cui è facile sbagliare: **tutte spuntate**
    si scrive vuoto (così resta «tutte» anche se domani se ne aggiunge una),
    **nessuna** si scrive `NESSUNA_SEZIONE` — perché `",".join([])` darebbe la stringa
    vuota, cioè esattamente il contrario di quello che l'admin ha appena spuntato.
    """
    scelte = [s for s in SEZIONI_SLUG if request.form.get("sez_" + s)]
    if len(scelte) == len(SEZIONI_SLUG):
        return ""
    if not scelte:
        return NESSUNA_SEZIONE
    return ",".join(scelte)


@bp.route("/utenti")
def utenti():
    db = get_db()
    righe = db.execute("SELECT id, username, display_name, role, sections"
                       " FROM users ORDER BY username COLLATE NOCASE").fetchall()
    conteggi = conteggi_utente(db)
    ricordati = {r["user_id"]: r["quanti"] for r in db.execute(
        "SELECT user_id, COUNT(*) AS quanti FROM sessioni_ricordate "
        "GROUP BY user_id")}
    db.close()
    utenti = []
    for r in righe:
        grezzo = (r["sections"] or "").strip()
        if r["role"] == "admin":
            permesse, nota = list(SEZIONI_SLUG), "tutte (amministratore)"
        elif not grezzo:
            permesse, nota = list(SEZIONI_SLUG), "tutte"
        elif grezzo == NESSUNA_SEZIONE:
            permesse, nota = [], "nessuna — vede solo la Dashboard"
        else:
            permesse = [s for s in SEZIONI_SLUG if s in
                        {x.strip() for x in grezzo.split(",")}]
            nota = f"{len(permesse)} su {len(SEZIONI_SLUG)}"
        # Cosa la copia duplicherebbe, in italiano e coi numeri: la conferma del
        # pulsante «Copia» si costruisce da qui. ⚠️ Il pulsante **non è
        # rieseguibile** (vedi `copia_dati_utente()`), quindi un «sei sicuro?» senza
        # dire cosa raddoppia sarebbe solo un passaggio da premere in fretta.
        suoi = conteggi.get(r["id"], {})
        roba = ", ".join(f"{quante} {ETICHETTE.get(t, t)}"
                         for t, quante in suoi.items() if quante)
        utenti.append({"id": r["id"], "username": r["username"],
                       "display_name": r["display_name"], "role": r["role"],
                       "permesse": permesse, "nota": nota,
                       "roba": roba, "quante": sum(suoi.values()),
                       "ricordati": ricordati.get(r["id"], 0)})
    return render_template("admin_utenti.html", utenti=utenti, sezioni=SEZIONI,
                           io_sono=session.get("username"))


@bp.route("/utenti/nuovo", methods=["POST"])
def utente_nuovo():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        flash("Nome utente non valido: da 3 a 32 caratteri fra lettere, cifre, . _ -", "error")
        return redirect(url_for("admin.utenti"))
    if len(password) < 8:
        flash("La password deve essere di almeno 8 caratteri.", "error")
        return redirect(url_for("admin.utenti"))

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        db.close()
        flash(f"Esiste già un utente «{username}».", "error")
        return redirect(url_for("admin.utenti"))
    ruolo = "admin" if request.form.get("role") == "admin" else "user"
    db.execute("INSERT INTO users(username,password,display_name,role,sections)"
               " VALUES(?,?,?,?,?)",
               (username, _hash(password),
                (request.form.get("display_name") or username).strip(),
                ruolo, "" if ruolo == "admin" else _sezioni_dal_form()))
    db.commit(); db.close()
    flash(f"Utente «{username}» creato.", "success")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:uid>/permessi", methods=["POST"])
def utente_permessi(uid):
    db = get_db()
    r = db.execute("SELECT username, role FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        db.close(); flash("Utente non trovato.", "error")
        return redirect(url_for("admin.utenti"))

    ruolo = "admin" if request.form.get("role") == "admin" else "user"
    # ⚠️ Non ci si può togliere il ruolo da soli, e non si può togliere l'ultimo
    # amministratore: senza questo controllo bastano due clic per chiudere fuori
    # tutti dalla schermata che serve a rimettere i permessi.
    if r["role"] == "admin" and ruolo != "admin":
        rimasti = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND id<>?",
                             (uid,)).fetchone()[0]
        if r["username"] == session.get("username"):
            db.close(); flash("Non puoi togliere a te stesso il ruolo di amministratore.", "error")
            return redirect(url_for("admin.utenti"))
        if rimasti == 0:
            db.close(); flash("Deve restare almeno un amministratore.", "error")
            return redirect(url_for("admin.utenti"))

    db.execute("UPDATE users SET role=?, sections=? WHERE id=?",
               (ruolo, "" if ruolo == "admin" else _sezioni_dal_form(), uid))
    db.commit(); db.close()
    flash(f"Permessi di «{r['username']}» aggiornati.", "success")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:uid>/password", methods=["POST"])
def utente_password(uid):
    password = request.form.get("password") or ""
    if len(password) < 8:
        flash("La password deve essere di almeno 8 caratteri.", "error")
        return redirect(url_for("admin.utenti"))
    db = get_db()
    r = db.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        db.close(); flash("Utente non trovato.", "error")
        return redirect(url_for("admin.utenti"))
    db.execute("UPDATE users SET password=? WHERE id=?", (_hash(password), uid))
    # ⚠️ E le sessioni ricordate cadono con lei. Non è un di più: se la password è
    # stata cambiata **perché** qualcuno la sapeva, lasciargli vivo il cookie di
    # «resta collegato» vorrebbe dire non aver cambiato niente.
    cadute = dimentica_tutte(db, uid)
    db.commit(); db.close()
    messaggio = f"Password di «{r['username']}» cambiata."
    if cadute:
        messaggio += (f" {cadute} dispositiv{'o' if cadute == 1 else 'i'} "
                      f"«resta collegato» " +
                      ("è stato disconnesso" if cadute == 1 else "sono stati disconnessi")
                      + ": la password nuova vale da subito ovunque.")
    flash(messaggio, "success")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:uid>/dimentica", methods=["POST"])
def utente_dimentica(uid):
    """Revoca tutti i «resta collegato» di un utente, senza toccargli la password."""
    db = get_db()
    r = db.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        db.close(); flash("Utente non trovato.", "error")
        return redirect(url_for("admin.utenti"))
    cadute = dimentica_tutte(db, uid)
    db.commit(); db.close()
    if cadute:
        flash(f"«{r['username']}»: {cadute} dispositiv"
              f"{'o disconnesso' if cadute == 1 else 'i disconnessi'}. "
              "La password resta quella di prima.", "success")
    else:
        flash(f"«{r['username']}» non ha nessun dispositivo da dimenticare.", "success")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:uid>/copia", methods=["POST"])
def utente_copia(uid):
    """Duplica i contenuti di `uid` su un altro utente. Aggiunge, non sostituisce.

    ⚠️ Non è il travaso di `utente_elimina()` con un altro nome, ed è la differenza
    che rende questa route un lavoro a sé: là le righe **cambiano mano** e le figlie
    seguono il padre da sole, qui vanno **duplicate**, e il padre nuovo ha un id
    nuovo che va riscritto su ognuna. La decisione «aggiunge» è di Davide
    (22/09/2026): non si perde niente, in cambio premerlo due volte lascia tutto in
    doppio — per questo la conferma nella pagina dice **cosa** sta per raddoppiare.
    """
    da = request.form.get("da") or ""
    db = get_db()
    sorgente = db.execute("SELECT id, username FROM users WHERE id=?", (uid,)).fetchone()
    destinatario = db.execute("SELECT id, username FROM users WHERE id=?",
                              (da,)).fetchone() if da.isdigit() else None
    if not sorgente or not destinatario:
        db.close()
        flash("Utente non trovato: non ho copiato niente.", "error")
        return redirect(url_for("admin.utenti"))
    if sorgente["id"] == destinatario["id"]:
        db.close()
        flash("Sorgente e destinatario sono lo stesso utente.", "error")
        return redirect(url_for("admin.utenti"))

    # Le due reti, e sono la stessa idea da due lati: una tabella con un proprietario
    # che non sappiamo se copiare, e una **figlia** che non sappiamo di dover
    # duplicare. La seconda è la più insidiosa — non darebbe nessun errore, farebbe
    # nascere il padre **vuoto**, e un team senza i suoi Pokémon somiglia a un team.
    ignote = tabelle_senza_regola(db)
    orfane = figlie_senza_regola(db)
    if ignote or orfane:
        db.close()
        pezzi = []
        if ignote:
            pezzi.append("senza una regola in TABELLE_UTENTE: " + ", ".join(ignote))
        if orfane:
            pezzi.append("figlie non dichiarate in FIGLIE_DI: "
                         + ", ".join(f"{f} (di {p})" for f, p in orfane))
        flash("Non copio niente — " + "; ".join(pezzi) + ". Una copia che le salta "
              "non darebbe errore, lascerebbe dei dati a metà.", "error")
        return redirect(url_for("admin.utenti"))

    try:
        fatte = copia_dati_utente(db, sorgente["id"], destinatario["id"])
        db.commit()
    except Exception as e:
        db.rollback()
        db.close()
        flash(f"Non ho copiato niente, il DB è com'era: {e}", "error")
        return redirect(url_for("admin.utenti"))
    saltate = db.execute("SELECT COUNT(*) FROM python_progress WHERE user_id=?",
                         (sorgente["id"],)).fetchone()[0]
    db.close()

    if not fatte:
        flash(f"«{sorgente['username']}» non ha niente da copiare.", "success")
        return redirect(url_for("admin.utenti"))
    quali = ", ".join(f"{quante} {ETICHETTE.get(t, t)}" for t, quante in fatte.items())
    messaggio = (f"Copiati da «{sorgente['username']}» a "
                 f"«{destinatario['username']}»: {quali}. "
                 "Sono righe nuove, accanto a quelle che aveva già: premere di "
                 "nuovo il pulsante le rifarebbe in doppio.")
    if saltate:
        # ⚠️ Dirlo, non tacerlo: il progresso di Python è di chi lo fa (decisione del
        # 22/09/2026), e un dato lasciato fuori in silenzio somiglia a un dato perso.
        messaggio += (f" Le {saltate} spunte di Python non sono state copiate: "
                      "quelle sono di chi le mette.")
    flash(messaggio, "success")
    return redirect(url_for("admin.utenti"))


@bp.route("/utenti/<int:uid>/elimina", methods=["POST"])
def utente_elimina(uid):
    db = get_db()
    r = db.execute("SELECT username, role FROM users WHERE id=?", (uid,)).fetchone()
    if not r:
        db.close(); flash("Utente non trovato.", "error")
        return redirect(url_for("admin.utenti"))
    if r["username"] == session.get("username"):
        db.close(); flash("Non puoi eliminare te stesso.", "error")
        return redirect(url_for("admin.utenti"))
    if r["role"] == "admin":
        rimasti = db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND id<>?",
                             (uid,)).fetchone()[0]
        if rimasti == 0:
            db.close(); flash("Deve restare almeno un amministratore.", "error")
            return redirect(url_for("admin.utenti"))
    # I contenuti dell'utente **passano all'amministratore**, non si cancellano:
    # deciso il 19/08/2026. È la stessa scelta fatta per le righe che esistevano
    # prima che il proprietario esistesse, e l'unica che non perde niente — oggi
    # `hub_export.json` è la sola copia di `hub.db`, e la lancia Davide a mano.
    # ⚠️ Va fatto **prima** della DELETE: `get_db()` accende le chiavi esterne e
    # `user_id` punta a `users(id)`, quindi senza il travaso la cancellazione
    # fallirebbe invece di lasciare righe orfane.
    # ⚠️ E l'elenco delle tabelle **non sta più qui**: sta in `TABELLE_UTENTE`, con
    # accanto cosa farne. Scritto a mano, si era fermato a quattro mentre le
    # tabelle erano sei (22/09/2026) — la spiegazione lunga è in `extensions.py`.
    ignote = tabelle_senza_regola(db)
    if ignote:
        db.close()
        flash(f"Non elimino «{r['username']}»: {', '.join(ignote)} " +
              ("ha" if len(ignote) == 1 else "hanno") + " un proprietario e "
              "nessuna regola in TABELLE_UTENTE, quindi non so se le sue righe "
              "vadano passate o cancellate. Va deciso lì, non qui.", "error")
        return redirect(url_for("admin.utenti"))
    io_admin = db.execute("SELECT id FROM users WHERE username=?",
                          (session.get("username"),)).fetchone()
    if not io_admin:
        db.close()
        flash("Non elimino nessuno: non riesco a ritrovare il tuo utente, quindi "
              "non ho a chi intestare i contenuti di chi se ne va.", "error")
        return redirect(url_for("admin.utenti"))
    passati = 0
    cancellate = {}
    try:
        for tabella, regola in TABELLE_UTENTE.items():
            if regola == "passa":
                cur = db.execute(f"UPDATE {tabella} SET user_id=? WHERE user_id=?",
                                 (io_admin["id"], uid))
                passati += cur.rowcount
            else:
                cur = db.execute(f"DELETE FROM {tabella} WHERE user_id=?", (uid,))
                if cur.rowcount:
                    cancellate[tabella] = cur.rowcount
        db.execute("DELETE FROM users WHERE id=?", (uid,))
        db.commit()
    except Exception as e:
        # ⚠️ Senza questo ramo una chiave esterna dimenticata diventava un 500 con
        # la connessione aperta, e l'utente restava lì senza che la pagina lo
        # dicesse. Meglio un messaggio che nomina l'errore: è il sintomo di una
        # tabella che `TABELLE_UTENTE` non copre come crede.
        db.rollback(); db.close()
        flash(f"Utente «{r['username']}» non eliminato, e il DB è com'era: {e}",
              "error")
        return redirect(url_for("admin.utenti"))
    db.close()
    pezzi = [f"Utente «{r['username']}» eliminato."]
    if passati:
        pezzi.append(f"{passati} righe di contenuto sono passate a te.")
    if cancellate:
        # Nominate una per una invece che sommate: è **stato personale** che
        # sparisce, non contenuto che cambia mano, e chi preme il pulsante ha il
        # diritto di sapere cosa ha portato via.
        quali = ", ".join(f"{q} in {t}" for t, q in cancellate.items())
        pezzi.append(f"Righe cancellate perché sono lo stato personale di chi se "
                     f"ne va, non contenuto: {quali}.")
    flash(" ".join(pezzi), "success")
    return redirect(url_for("admin.utenti"))
