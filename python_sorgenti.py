"""I file dei progetti Python: da un caricamento, da uno zip, da GitHub.

Tutto finisce come **testo nel DB** (`python_file`): sono sorgenti, e così entrano
nell'export. Quello che non è testo (immagini, binari, cartelle di ambienti virtuali) si
**salta dicendolo**, non si perde in silenzio.

GitHub, verificato il 25/09/2026: `api.github.com/repos/<proprietario>/<repo>/zipball`
risponde con un redirect a codeload e dà lo zip del ramo predefinito, con una cartella in
cima (`proprietario-repo-commit/`) che qui si toglie. Senza chiave: **60 richieste
all'ora**, e solo repository **pubblici** (un privato risponde 404, come uno che non
esiste — lo si dice con tutte e due le possibilità). È l'API ufficiale, non una lettura
delle pagine del sito.
"""
import io
import re
import zipfile
from urllib.parse import urlparse

import python_esegui

ESTENSIONI = (".py", ".txt", ".md", ".json", ".csv", ".cfg", ".toml", ".ini",
              ".yaml", ".yml", ".sql", ".html", ".css", ".js")
BYTE_FILE = 500_000              # per file; scelte, non misurate
BYTE_TOTALI = 3_000_000
FILE_MASSIMI = python_esegui.FILE_MASSIMI
# Cartelle che non sono il progetto: ambienti virtuali, cache, git.
SALTA = re.compile(r"(^|/)(\.git|__pycache__|\.venv|venv|env|node_modules|\.idea|\.vscode|"
                   r"\.mypy_cache|\.pytest_cache|dist|build|[^/]+\.egg-info)(/|$)")


def github_valido(url):
    """`(proprietario, repo)` da un link a un repository GitHub, o None."""
    url = (url or "").strip()
    try:
        p = urlparse(url)
    except ValueError:
        return None
    if p.scheme not in ("http", "https") or (p.hostname or "").lower() not in ("github.com", "www.github.com"):
        return None
    parti = [x for x in p.path.split("/") if x]
    if len(parti) < 2 or not all(re.fullmatch(r"[\w.-]+", x) for x in parti[:2]):
        return None
    return parti[0], re.sub(r"\.git$", "", parti[1])


def ammesso(nome):
    return nome.lower().endswith(ESTENSIONI) and python_esegui.nome_valido(nome)


def da_zip(dati, togli_radice=False):
    """`(file, saltati)` da uno zip: {nome: testo} e l'elenco di quello che non entra."""
    file, saltati, totale = {}, [], 0
    try:
        z = zipfile.ZipFile(io.BytesIO(dati))
    except zipfile.BadZipFile:
        return {}, ["non è uno zip leggibile"]
    nomi = [i for i in z.infolist() if not i.is_dir()]
    radice = ""
    if togli_radice and nomi:
        prima = nomi[0].filename.split("/")[0] + "/"
        if all(i.filename.startswith(prima) for i in nomi):
            radice = prima
    for info in nomi:
        nome = info.filename[len(radice):]
        if SALTA.search(nome):
            continue                                    # cartelle di servizio: non si elencano
        if not ammesso(nome):
            saltati.append(f"{nome} (tipo non ammesso)")
            continue
        if info.file_size > BYTE_FILE:
            saltati.append(f"{nome} (troppo grande)")
            continue
        if len(file) >= FILE_MASSIMI or totale + info.file_size > BYTE_TOTALI:
            saltati.append(f"{nome} (oltre il limite del progetto)")
            continue
        try:
            file[nome] = z.read(info).decode("utf-8")
        except UnicodeDecodeError:
            saltati.append(f"{nome} (non è testo UTF-8)")
            continue
        totale += info.file_size
    return file, saltati


def da_caricamento(nome, dati):
    """`(file, saltati)` da un file caricato: un .zip si apre, un file di testo entra."""
    nome = (nome or "").replace("\\", "/").split("/")[-1]
    if nome.lower().endswith(".zip"):
        return da_zip(dati, togli_radice=True)
    if not ammesso(nome):
        return {}, [f"{nome} (tipo non ammesso)"]
    if len(dati) > BYTE_FILE:
        return {}, [f"{nome} (troppo grande)"]
    try:
        return {nome: dati.decode("utf-8")}, []
    except UnicodeDecodeError:
        return {}, [f"{nome} (non è testo UTF-8)"]


def scarica_github(proprietario, repo):
    """Lo zip del ramo predefinito. A parte perché le prove lo sostituiscono."""
    import requests
    r = requests.get(f"https://api.github.com/repos/{proprietario}/{repo}/zipball",
                     timeout=60, headers={"User-Agent": "personal-hub"})
    if r.status_code == 404:
        raise LookupError("GitHub risponde 404: il repository non esiste o è privato")
    if r.status_code == 403:
        raise LookupError("GitHub ha rifiutato (limite di 60 richieste all'ora?): riprova più tardi")
    r.raise_for_status()
    return r.content


def da_github(url):
    """`(file, saltati)` dal repository del link."""
    coppia = github_valido(url)
    if not coppia:
        raise ValueError("non è il link a un repository GitHub (github.com/proprietario/repo)")
    return da_zip(scarica_github(*coppia), togli_radice=True)


def a_zip(file):
    """Lo zip dei file di un progetto, da scaricare."""
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, testo in sorted(file.items()):
            z.writestr(nome, testo or "")
    return b.getvalue()
