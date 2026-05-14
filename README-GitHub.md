# Personal Hub

Dashboard personale Flask con autenticazione, struttura modulare a blueprint e strumenti per gaming, Pokémon VGC, Arduino, Python e PC building.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Caratteristiche

- **🎮 Gaming Tracker** — Libreria giochi con progressi e filtri
- **🐉 Pokémon VGC** — Team builder multi-regulation, calcolatori danno/speed/stats
- **🔌 Arduino** — Gestione progetti con editor codice
- **🐍 Python** — Tracker argomenti con checklist
- **🖥️ PC Builder** — Build multiple + import automatico DxDiag
- **🛡️ Autenticazione** — Login session-based
- **🌙 Dark/Light mode** — Toggle tema
- **📱 Responsive** — Design mobile-first

## 📦 Struttura progetto

```
personal-hub-v2/
├── app.py                 # App factory create_app()
├── extensions.py          # SQLAlchemy, estensioni condivise
├── data.py                # Costanti, mapping, dati statici
├── blueprints/            # Moduli separati per area funzionale
│   ├── auth.py
│   ├── main.py
│   ├── gaming.py
│   ├── pokemon.py
│   ├── api_pokemon.py
│   ├── arduino.py
│   ├── python_tracker.py
│   └── pcbuilder.py
├── data/                  # JSON dinamici
│   ├── regulations.json
│   ├── roster_ma.json
│   └── moves_ma.json
└── templates/             # HTML + Jinja2
    ├── base.html
    ├── login.html
    └── ...
```

## 🚀 Avvio rapido

```bash
pip install -r requirements.txt
python app.py
```

**URL:** [http://localhost:5000](http://localhost:5000)  
**Credenziali default:** `admin` / `admin123`

## 🐛 Stato attuale

**✅ App si avvia correttamente** dopo refactor a blueprint.  
**🔄 Work in progress:** stabilizzazione template e rimozione shim temporanei (`CHAMPIONS_BST`, `TYPE_TABLE_HTML`).  
**📋 Test consigliati:** `/login` → `/` → `/pokemon` → `/gaming` → `/calcolatori`.

## 📊 Pokémon VGC — Sistema Regulation

- **Multi-regulation** con file JSON separati per roster/mosse/oggetti
- Team builder con select dinamica regulation
- Editor regulation, roster, mosse e oggetti
- Calcolatori Champions Reg. M-A (max 32 EV/stat, 66 totali)
- Integrazione [PokéAPI](https://pokeapi.co/) per sprite e stats

## 🛠️ Tecnologie

| Area | Tecnologie |
|------|------------|
| Backend | Flask · SQLAlchemy · SQLite |
| Frontend | Jinja2 · CSS custom · Vanilla JS |
| Dati | JSON locali · PokéAPI |
| Stile | Inter · JetBrains Mono · Responsive |

## 📱 Screenshot

![Dashboard][dashboard-screenshot]
![Pokémon][pokemon-screenshot]
![Calcolatori][calcolatori-screenshot]

## 🤝 Contribuire

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add some AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

## 📄 Licenza

[MIT License](LICENSE) — vedi [LICENSE](LICENSE) per dettagli.

## 🙏 Autore

**Sviluppato da [Tuo Nome]**  
[GitHub](https://github.com/tuonome) · [LinkedIn](https://linkedin.com/in/tuonome)

---

*Aggiornato: 10 maggio 2026 — v11.1a*
