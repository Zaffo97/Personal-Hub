#!/usr/bin/env python
"""Le prove della sezione Stampa 3D. Non tocca `hub.db`, né `data/stampa3d/`, né la rete.

    python scripts/prova_stampa3d.py [--tieni]

Quello che queste prove devono tenere fermo sono i difetti che non darebbero errore:

- un **link incollato** che finisce in un `href`: `javascript:` lì è codice che gira al
  clic, e un sito qualunque sotto l'etichetta «Modello» è un'etichetta falsa. Un link
  rifiutato va **detto**, non perso in silenzio
- un **file condiviso** da due righe (una copia fra utenti, lo stesso .3mf in due
  progetti): cancellandone una, il file deve restare per l'altra
- il file **di un altro utente** scaricato, tolto, o la sua bobina scalata
- un **nome con l'apostrofo** dentro le conferme inline: se l'handler non compila, la
  conferma sparisce e il form parte lo stesso (la trappola di `{{ nome|e }}`)
- una **tinta** che nessuno ha scelto, e una bobina che va sotto zero
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RADICE not in sys.path:
    sys.path.insert(0, RADICE)
sys.path.insert(0, os.path.join(RADICE, "scripts"))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

esiti = []
PW = "password-di-prova"
# Il caso difficile, messo nei dati apposta: lo sweep sul DB vero non lo vedrebbe finché
# nessuno salva un progetto con l'apostrofo.
NOME = "Supporto dell'auricolare \"grande\""


def esito(nome, ok, dettaglio=""):
    esiti.append(bool(ok))
    print(f"  {'OK ' if ok else 'NO '} {nome}" + (f"   {dettaglio}" if dettaglio else ""))


def prove_modulo(dove):
    import stampa3d as S
    S.CARTELLA = os.path.join(dove, "file")
    print("\n== 1. i link ==")
    esito("un `javascript:` non passa", S.link_valido("link_modello", "javascript:alert(1)") is None)
    esito("un sito che finge MakerWorld non passa",
          S.link_valido("link_modello", "https://makerworld.com.truffa.it/models/1") is None)
    esito("un modello di MakerWorld passa",
          S.link_valido("link_modello", "https://makerworld.com/it/models/1944124-cable-clip"))
    esito("Tinkercad come modello non passa: è un sito di disegno",
          S.link_valido("link_modello", "https://www.tinkercad.com/things/abc") is None)
    esito("Tinkercad come disegno passa",
          S.link_valido("link_disegno", "https://www.tinkercad.com/things/abc"))
    esito("la ricerca di MakerWorld codifica il nome",
          S.cerca_makerworld("cable clip") == "https://makerworld.com/it/search/models?keyword=cable%20clip")
    esito("   e senza nome non ne costruisce una", S.cerca_makerworld("  ") is None)

    print("\n== 2. i file ==")
    esito("le estensioni: .3mf e .STL sì, .exe no",
          S.estensione_ammessa("a.3mf") and S.estensione_ammessa("B.STL")
          and not S.estensione_ammessa("a.exe"))
    try:
        S.percorso("../hub.db"); fuori = False
    except ValueError:
        fuori = True
    esito("un'impronta con `..` non diventa un percorso", fuori)
    i1, b1 = S.salva_file(io.BytesIO(b"solid prova"))
    i2, _ = S.salva_file(io.BytesIO(b"solid prova"))
    esito("lo stesso file due volte: una copia sola su disco",
          i1 == i2 and len(os.listdir(S.CARTELLA)) == 1 and b1 == 11)
    vecchio = S.MAX_BYTE
    S.MAX_BYTE = 10
    troppo, _ = S.salva_file(io.BytesIO(b"x" * 50))
    S.MAX_BYTE = vecchio
    esito("oltre la soglia: rifiutato, e su disco non resta niente",
          troppo is None and len(os.listdir(S.CARTELLA)) == 1, str(os.listdir(S.CARTELLA)))
    os.remove(S.percorso(i1))
    esito("le misure", (S.misura(500), S.misura(2048), S.misura(3 * 1024 * 1024 // 2))
          == ("500 B", "2 KB", "1,5 MB"))


def prove_anteprima():
    """three.js sta in static/vendor e si raggiunge per nome, dall'importmap della pagina.
    Un file che manca lì non dà nessun errore finché qualcuno non preme «Anteprima»:
    qui si controlla che ogni nome porti a un file vero."""
    import stampa3d as S
    print("\n== 10. l'anteprima 3D: i file di three.js ci sono tutti ==")
    esito("STL, 3MF e OBJ hanno l'anteprima, STEP no",
          S.ha_anteprima("a.STL") and S.ha_anteprima("b.3mf") and S.ha_anteprima("c.obj")
          and not S.ha_anteprima("d.step"))
    tpl = open(os.path.join(RADICE, "templates", "stampa3d.html"), encoding="utf-8").read()
    mappa = json.loads(re.search(r'<script type="importmap">(.*?)</script>', tpl, re.S).group(1))["imports"]
    def su_disco(url):
        return os.path.join(RADICE, *url.lstrip("/").split("/"))
    esito("il `three` dell'importmap esiste", os.path.isfile(su_disco(mappa["three"])), mappa["three"])
    js = open(os.path.join(RADICE, "static", "js", "stampa3d-anteprima.js"), encoding="utf-8").read()
    addons = re.findall(r"import\('three/addons/([^']+)'\)", js)
    mancanti = [a for a in addons if not os.path.isfile(su_disco(mappa["three/addons/"] + a))]
    esito(f"i {len(addons)} addon chiesti dal modulo esistono", addons and not mancanti, str(mancanti))
    # E gli import **dentro** i file di three.js: relativi, o `three` per nome.
    vendor = os.path.dirname(os.path.dirname(su_disco(mappa["three"])))
    rotti = []
    for cartella, _, nomi in os.walk(vendor):
        for n in nomi:
            if not n.endswith(".js"):
                continue
            testo = open(os.path.join(cartella, n), encoding="utf-8").read()
            for rif in re.findall(r"^\s*(?:import|export)[^;]*?from\s*'([^']+)'", testo, re.M):
                if rif == "three":
                    continue
                if not os.path.isfile(os.path.normpath(os.path.join(cartella, rif))):
                    rotti.append(f"{n} -> {rif}")
    esito("ogni import relativo dentro static/vendor porta a un file", not rotti, str(rotti))


def prove_web(dove):
    import extensions
    import stampa3d as S
    extensions.DB = os.path.join(dove, "prova.db")
    extensions.CHIAVE = os.path.join(dove, "chiave.txt")
    extensions.init_db()
    db = extensions.get_db()
    print("\n== 3. schema e regole degli utenti ==")
    tabelle = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    esito("le tre tabelle esistono",
          {"stampa_progetti", "stampa_file", "stampa_filamenti"} <= tabelle)
    esito("nessuna tabella con un proprietario senza regola",
          extensions.tabelle_senza_regola(db) == [], str(extensions.tabelle_senza_regola(db)))
    esito("nessuna figlia senza regola",
          extensions.figlie_senza_regola(db) == [], str(extensions.figlie_senza_regola(db)))
    for u in ("tizio", "caio"):
        db.execute("INSERT INTO users(username,password,display_name,role) VALUES(?,?,?,?)",
                   (u, extensions.hash_password(PW), u.title(), "user"))
    db.commit()
    uid = {r["username"]: r["id"] for r in db.execute("SELECT id, username FROM users")}
    db.close()

    import app as m
    app = m.create_app()
    app.config["TESTING"] = True

    def entra(c, chi):
        c.post("/login", data={"username": chi, "password": PW})

    def righe(tabella):
        d = extensions.get_db()
        r = [dict(x) for x in d.execute(f"SELECT * FROM {tabella} ORDER BY id")]
        d.close()
        return r

    def su_disco():
        return sorted(os.listdir(S.CARTELLA)) if os.path.isdir(S.CARTELLA) else []

    print("\n== 4. il salvataggio ==")
    with app.test_client() as c:
        entra(c, "tizio")
        r = c.post("/stampa3d/save", data={
            "nome": NOME, "stato": "Da stampare", "materiale": "PLA", "grammi": "42",
            "link_modello": "javascript:alert(1)",
            "link_disegno": "https://www.tinkercad.com/things/abc",
            "file": [(io.BytesIO(b"PK finto 3mf"), "supporto.3mf"),
                     (io.BytesIO(b"MZ"), "virus.exe")],
        }, content_type="multipart/form-data", follow_redirects=True)
        testo = r.get_data(as_text=True)
        p = righe("stampa_progetti")
        esito("un progetto salvato", len(p) == 1 and p[0]["nome"] == NOME)
        esito("   il link `javascript:` non è salvato, e la pagina lo dice",
              p[0]["link_modello"] is None and "non salvato" in testo)
        esito("   il link di Tinkercad sì", p[0]["link_disegno"] == "https://www.tinkercad.com/things/abc")
        f = righe("stampa_file")
        esito("   un file allegato, l'.exe rifiutato dicendolo",
              [x["nome"] for x in f] == ["supporto.3mf"] and "virus.exe" in testo
              and len(su_disco()) == 1)
        pid, fid = p[0]["id"], f[0]["id"]

        print("\n== 5. la pagina resa ==")
        pagina = c.get("/stampa3d/").get_data(as_text=True)
        esito("il progetto e il file compaiono", "supporto.3mf" in pagina and "Supporto dell" in pagina)
        esito("   col pulsante dell'anteprima", 'title="Anteprima 3D"' in pagina)
        esito("   con la ricerca di MakerWorld, visto che il modello non c'è",
              "makerworld.com/it/search/models?keyword=" in pagina)
        try:
            import esprima
            from sweep_pagine import controlla
            errori = controlla(esprima, "/stampa3d/", pagina)
            esito("script e handler compilano, col nome che ha apostrofo e virgolette",
                  errori == 0, f"{errori} errori")
        except ImportError:
            esito("manca esprima: pip install esprima", False)

        d = c.get(f"/stampa3d/file/{fid}")
        esito("il file si riscarica, col suo nome",
              d.status_code == 200 and d.data == b"PK finto 3mf"
              and "supporto.3mf" in d.headers.get("Content-Disposition", ""))
        d.close()

        print("\n== 6. le righe di un altro ==")
        with app.test_client() as altro:
            entra(altro, "caio")
            esito("caio non scarica il file di tizio",
                  altro.get(f"/stampa3d/file/{fid}").status_code == 404)
            altro.post(f"/stampa3d/file/{fid}/delete")
            altro.post(f"/stampa3d/{pid}/delete")
            esito("   né lo toglie, né cancella il progetto",
                  len(righe("stampa_file")) == 1 and len(righe("stampa_progetti")) == 1
                  and len(su_disco()) == 1)
            esito("   e nella sua pagina non c'è", "supporto.3mf" not in
                  altro.get("/stampa3d/").get_data(as_text=True))

        print("\n== 7. lo stesso file in due progetti ==")
        c.post("/stampa3d/save", data={"nome": "Secondo", "stato": "Idea",
               "file": [(io.BytesIO(b"PK finto 3mf"), "copia.3mf")]},
               content_type="multipart/form-data")
        esito("due righe, un file solo su disco",
              len(righe("stampa_file")) == 2 and len(su_disco()) == 1)
        secondo = [x for x in righe("stampa_progetti") if x["nome"] == "Secondo"][0]["id"]
        c.post(f"/stampa3d/{secondo}/delete")
        esito("cancellato un progetto, il file resta per l'altro",
              len(righe("stampa_file")) == 1 and len(su_disco()) == 1)

        print("\n== 8. le bobine ==")
        c.post("/stampa3d/bobina/save", data={"materiale": "PLA", "colore": "Nero",
                                              "peso_totale": "1000"})
        b = righe("stampa_filamenti")[0]
        esito("una bobina nuova è piena, e senza una tinta che nessuno ha scelto",
              b["peso_rimasto"] == 1000 and b["colore_hex"] is None, str(b["colore_hex"]))
        c.post("/stampa3d/bobina/save", data={"materiale": "PETG", "colore_hex": "javascript:1"})
        esito("   una tinta che non è un colore non entra",
              righe("stampa_filamenti")[1]["colore_hex"] is None)
        with app.test_client() as altro:
            entra(altro, "caio")
            altro.post(f"/stampa3d/bobina/{b['id']}/usa", data={"grammi": "100"})
        esito("caio non scala la bobina di tizio", righe("stampa_filamenti")[0]["peso_rimasto"] == 1000)
        r = c.post(f"/stampa3d/{pid}/scala", data={"bobina_id": b["id"]}, follow_redirects=True)
        esito("«Stampato» dal progetto: 1000 − 42 = 958, e il progetto cambia stato",
              righe("stampa_filamenti")[0]["peso_rimasto"] == 958
              and righe("stampa_progetti")[0]["stato"] == "Stampato")
        r = c.post(f"/stampa3d/bobina/{b['id']}/usa", data={"grammi": "5000"}, follow_redirects=True)
        esito("usarne più di quanta ce n'è: a zero, e lo dice",
              righe("stampa_filamenti")[0]["peso_rimasto"] == 0
              and "non 5000" in r.get_data(as_text=True))
        esito("   e a zero è «quasi finita»", "quasi finita" in c.get("/stampa3d/").get_data(as_text=True))

    print("\n== 9. la copia fra utenti, e un file che manca ==")
    d = extensions.get_db()
    d.execute("UPDATE users SET role='admin' WHERE username='caio'")
    d.commit(); d.close()
    with app.test_client() as adm:
        entra(adm, "caio")
        # ⚠️ L'id nell'URL è la **sorgente**, `da` il destinatario (il nome del campo
        # inganna). Una copia sola: una seconda all'indietro ricopierebbe anche la
        # riga appena copiata, e il conto sarebbe 3, non 2.
        adm.post(f"/admin/utenti/{uid['tizio']}/copia", data={"da": str(uid["caio"])})
    f = righe("stampa_file")
    esito("la copia duplica la riga del file, non il file",
          len(f) == 2 and len({x["impronta"] for x in f}) == 1 and len(su_disco()) == 1,
          f"{len(f)} righe, {len(su_disco())} file")
    with app.test_client() as c:
        entra(c, "tizio")
        c.post(f"/stampa3d/{pid}/delete")
        esito("cancellato l'originale, il file resta per la copia",
              len(righe("stampa_file")) == 1 and len(su_disco()) == 1)
    for n in su_disco():
        os.remove(os.path.join(S.CARTELLA, n))
    d = extensions.get_db()
    d.execute("UPDATE users SET role='user' WHERE username='caio'")
    d.commit(); d.close()
    with app.test_client() as c:
        entra(c, "caio")
        pagina = c.get("/stampa3d/").get_data(as_text=True)
        esito("il file tolto dal disco: la pagina dice «file mancante»", "file mancante" in pagina)
        fid = righe("stampa_file")[0]["id"]
        r = c.get(f"/stampa3d/file/{fid}", follow_redirects=True)
        esito("   e scaricarlo lo dice invece di dare un errore",
              r.status_code == 200 and "manca dal disco" in r.get_data(as_text=True))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tieni", action="store_true", help="non cancella la cartella temporanea")
    args = ap.parse_args()
    dove = tempfile.mkdtemp(prefix="prova_stampa3d_")
    try:
        prove_modulo(dove)
        prove_web(dove)
        prove_anteprima()
    finally:
        if args.tieni:
            print(f"\ncartella tenuta: {dove}")
        else:
            shutil.rmtree(dove, ignore_errors=True)
    passate = sum(esiti)
    print(f"\n{passate} prove su {len(esiti)}." +
          ("  Tutte passate." if passate == len(esiti) else "  FALLITE."))
    return 0 if passate == len(esiti) else 1


if __name__ == "__main__":
    sys.exit(main())
