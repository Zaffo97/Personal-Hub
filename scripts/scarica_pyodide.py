#!/usr/bin/env python
"""Scarica Pyodide (Python nel browser) in `static/vendor/pyodide-<versione>/`.

    python scripts/scarica_pyodide.py [--dry-run]

Serve all'«Esegui nel browser» della sezione Python. Sono circa 13 MB, quindi **non
stanno in git** (`.gitignore`): si scaricano una volta per PC con questo script, come il
catalogo del PC Builder. Senza, la pagina lo dice e resta l'esecuzione sul PC.

- **Fonte**: il pacchetto `pyodide-core` della release ufficiale su GitHub
  (github.com/pyodide/pyodide, licenza MPL-2.0). Dentro c'è il motore e la libreria
  standard; i pacchetti in più (numpy, pandas, …) li carica Pyodide dal CDN ufficiale
  (`cdn.jsdelivr.net/pyodide/v<versione>/full/`) al primo `import`, e solo se servono
- **Versione fissata** e **impronta controllata**: lo sha256 qui sotto è quello che
  GitHub pubblica per il file (letto il 25/09/2026). Se il file scaricato non combacia,
  non si estrae niente
- Rieseguibile: se la cartella c'è già con tutti i file, non scarica
"""
import argparse
import hashlib
import io
import os
import shutil
import sys
import tarfile

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIONE = "314.0.7"
URL = f"https://github.com/pyodide/pyodide/releases/download/{VERSIONE}/pyodide-core-{VERSIONE}.tar.bz2"
SHA256 = "2abdcc2e35208af406e07724cffa85bc582ced97e9028383ecf5462541393f95"
CARTELLA = os.path.join(RADICE, "static", "vendor", f"pyodide-{VERSIONE}")
# Quelli che servono al browser. Gli altri del pacchetto (python.exe, i .d.ts, la
# riga di comando per Node) non li carica nessuno.
FILE = ("pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip",
        "pyodide-lock.json", "package.json")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def completa():
    return all(os.path.isfile(os.path.join(CARTELLA, f)) for f in FILE)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="dice cosa farebbe, non scarica")
    args = ap.parse_args()
    if completa():
        print(f"Pyodide {VERSIONE} c'è già in {os.path.relpath(CARTELLA, RADICE)}: niente da fare.")
        return 0
    if args.dry_run:
        print(f"--dry-run: scaricherei {URL} (circa 7 MB) in {os.path.relpath(CARTELLA, RADICE)}.")
        return 0
    import requests
    print(f"Scarico {URL} …")
    r = requests.get(URL, timeout=300)
    r.raise_for_status()
    impronta = hashlib.sha256(r.content).hexdigest()
    if impronta != SHA256:
        print(f"FERMO: lo sha256 non combacia ({impronta}): non estraggo niente.")
        return 1
    temporanea = CARTELLA + ".parziale"
    shutil.rmtree(temporanea, ignore_errors=True)
    os.makedirs(temporanea)
    with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:bz2") as tar:
        for f in FILE:
            membro = tar.getmember(f"pyodide/{f}")
            with tar.extractfile(membro) as sorgente, open(os.path.join(temporanea, f), "wb") as d:
                shutil.copyfileobj(sorgente, d)
    # Tutto o niente: una cartella a metà farebbe credere alla pagina che Pyodide c'è.
    shutil.rmtree(CARTELLA, ignore_errors=True)
    os.replace(temporanea, CARTELLA)
    peso = sum(os.path.getsize(os.path.join(CARTELLA, f)) for f in FILE)
    print(f"Pyodide {VERSIONE} in {os.path.relpath(CARTELLA, RADICE)} ({peso / 1024 / 1024:.1f} MB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
