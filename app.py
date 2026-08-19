"""
Personal Hub — entry point.
Ogni area funzionale vive in blueprints/.
"""
import os
import json
from flask import Flask
from extensions import (init_db, lingua_attiva, nome_vis, t, tf, traduzioni,
                        categorie)
from data import SEZIONI, BLUEPRINT_SEZIONE

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    with app.app_context():
        init_db()

    # La lingua attiva serve a ogni pagina: il pulsante sta in base.html e le
    # tendine di Pokémon, mosse e oggetti sono renderizzate dal server.
    @app.context_processor
    def _lingua():
        # `t` traduce le etichette dell'interfaccia, `nome_vis` i nomi dei dati.
        # `traduzioni_json` è lo stesso dizionario per il JS: le pagine Pokémon
        # costruiscono pezzi di interfaccia nel browser, e senza questo resterebbero
        # in italiano anche in modalità inglese. In italiano è `{}`, cioè niente.
        lingua = lingua_attiva()
        return {"lang": lingua, "nome_vis": nome_vis, "t": t, "tf": tf,
                "categorie": categorie,
                "traduzioni_json": json.dumps(traduzioni(lingua), ensure_ascii=False)}

    # La sidebar mostra solo le sezioni permesse. È un context processor e non un
    # calcolo dentro base.html perché la stessa risposta serve al controllo qui sotto.
    @app.context_processor
    def _permessi():
        from extensions import sezioni_utente, e_admin
        from flask import session
        permesse = sezioni_utente() if "username" in session else []
        # `e_admin` era ricalcolato qui a mano. Ora la definizione è una sola, in
        # `extensions.py`: la stessa che decide **di chi** sono le righe, e due
        # copie della stessa domanda sono due copie che possono divergere.
        return {"sezioni": SEZIONI, "sezioni_permesse": permesse,
                "e_admin": e_admin()}

    # ⚠️ Il controllo sta **qui**, su `request.blueprint`, e non su un decoratore da
    # mettere sulle singole viste: le sezioni hanno decine di route ciascuna — solo
    # Pokémon ne ha oltre trenta fra pagine e API — e bastava dimenticarne una per
    # lasciare aperta una porta senza che nulla lo segnalasse. Così una route nuova è
    # protetta dal giorno in cui viene scritta, senza che nessuno se ne debba ricordare.
    @app.before_request
    def _controlla_sezione():
        from flask import request, session, redirect, url_for, flash
        from extensions import sezioni_utente
        slug = BLUEPRINT_SEZIONE.get(request.blueprint or "")
        if not slug or "username" not in session:
            return None                     # non è una sezione, o ci pensa login_required
        if slug in sezioni_utente():
            return None
        # Una risposta JSON a chi chiama un'API, una pagina a chi naviga: rispondere
        # con un redirect a una fetch() darebbe un errore di parsing invece di un 403.
        if request.blueprint == "api_pokemon" or request.path.startswith("/api/") \
                or "/api/" in request.path:
            return {"ok": False, "error": "Sezione non permessa"}, 403
        flash("Non hai accesso a questa sezione.", "error")
        return redirect(url_for("dashboard.dashboard"))

    from blueprints.auth           import bp as auth_bp
    from blueprints.dashboard      import bp as dashboard_bp
    from blueprints.gaming         import bp as gaming_bp
    from blueprints.pokemon        import bp as pokemon_bp
    from blueprints.api_pokemon    import bp as api_pokemon_bp
    from blueprints.arduino        import bp as arduino_bp
    from blueprints.python_tracker import bp as python_bp
    from blueprints.pcbuilder      import bp as pcbuilder_bp
    from blueprints.admin          import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(gaming_bp)
    app.register_blueprint(pokemon_bp)
    app.register_blueprint(api_pokemon_bp)
    app.register_blueprint(arduino_bp)
    app.register_blueprint(python_bp)
    app.register_blueprint(pcbuilder_bp)
    app.register_blueprint(admin_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)