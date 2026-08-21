"""Il punto d'ingresso per un server WSGI vero. Non si esegue a mano.

    Windows:  python -m waitress --port=5000 wsgi:application
    Linux:    gunicorn -b 0.0.0.0:5000 wsgi:application

⚠️ Perché esiste (§1.5): `python app.py` avvia il **server di sviluppo di Flask**, che
regge una richiesta per volta e non è scritto per stare esposto — fino al 21/08/2026
lo faceva pure con `debug=True`, cioè offrendo una console Python a chiunque arrivasse
a una pagina d'errore. Per l'uso in casa quel server va benissimo; per mettere l'hub
online no, a nessuna condizione.

`application` è il nome che gunicorn, waitress e il file WSGI di PythonAnywhere si
aspettano di trovare. `app` è lo stesso oggetto, per chi scrive `wsgi:app`.

⚠️ **Con più di un worker**: SQLite regge un uso come questo, ma i file JSON scritti a
mano no — vedi la trappola sulle scritture concorrenti in `BACKLOG.md`. Finché quella
resta aperta, si sta a **un worker solo** (`--threads` va bene, i processi no).
"""
from app import app

application = app
