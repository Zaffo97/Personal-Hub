"""
Personal Hub — entry point.
Ogni area funzionale vive in blueprints/.
"""
import os
from flask import Flask
from extensions import init_db, lingua_attiva, nome_vis

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    with app.app_context():
        init_db()

    # La lingua attiva serve a ogni pagina: il pulsante sta in base.html e le
    # tendine di Pokémon, mosse e oggetti sono renderizzate dal server.
    @app.context_processor
    def _lingua():
        return {"lang": lingua_attiva(), "nome_vis": nome_vis}

    from blueprints.auth           import bp as auth_bp
    from blueprints.dashboard      import bp as dashboard_bp
    from blueprints.gaming         import bp as gaming_bp
    from blueprints.pokemon        import bp as pokemon_bp
    from blueprints.api_pokemon    import bp as api_pokemon_bp
    from blueprints.arduino        import bp as arduino_bp
    from blueprints.python_tracker import bp as python_bp
    from blueprints.pcbuilder      import bp as pcbuilder_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(gaming_bp)
    app.register_blueprint(pokemon_bp)
    app.register_blueprint(api_pokemon_bp)
    app.register_blueprint(arduino_bp)
    app.register_blueprint(python_bp)
    app.register_blueprint(pcbuilder_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)