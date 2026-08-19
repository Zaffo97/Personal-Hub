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
RADICI = ("games", "teams", "arduino_projects", "pc_builds")
FIGLIE = ("team_members", "pc_components")
# `python_topics` è l'elenco fisso dei 53 argomenti, condiviso di suo: quello che è
# personale è la spunta, che dal blocco Python vivrà in `python_progress`.
ALTRE = ("python_topics",)
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
     "INSERT INTO pc_components(build_id,category,name,price,notes) VALUES(?,?,?,?,?)"):
        "stessa build appena verificata: il proprietario e' quello del padre",
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
        "quattro radici e **cambia** il proprietario, non lo legge. Route da "
        "amministratore",
    ("extensions.py", "init_db",
     "UPDATE {…} SET user_id=? WHERE user_id IS NULL"):
        "la migrazione del 19/08/2026 che intesta ad admin le righe nate prima del "
        "proprietario. Gira una volta sola, nel giro in cui la colonna nasce",
    ("blueprints/pokemon.py", "regulation_editor",
     "SELECT id, name, format, record FROM teams WHERE regulation_id=? ORDER BY created_at DESC"):
        "chi tocca una regulation deve vedere tutti i team che ne dipendono, non solo "
        "i propri. Route da amministratore",
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
            "ambito": funzione_di(n) in con_ambito,
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
            elif q["ambito"] and "{…}" in q["sql"]:
                # La condizione è quella di `ambito_utente()`, innestata nella query.
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

    if scoperte:
        print("\n-- SCOPERTE: mostrano le righe di tutti --")
        for q in sorted(scoperte, key=lambda x: (x["file"], x["riga"])):
            print(f"  {q['file']}:{q['riga']} {q['funzione']}()  [{', '.join(q['tabelle'])}]")
            print(f"      {q['sql'][:110]}")

    return 1 if (scoperte or calcolate) else 0


if __name__ == "__main__":
    sys.exit(main())
