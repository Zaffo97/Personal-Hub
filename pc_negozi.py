"""I link ai negozi e gli avvisi del PC Builder. **Nessuna lettura automatica.**

Deciso da Davide il 25/09/2026, dopo aver letto le fonti (BACKLOG §4, PC Builder):

- **Amazon** vieta «data mining, robot o simili strumenti» nelle Condizioni d'uso, e la
  sua API si apre solo agli affiliati con 10 vendite in 30 giorni
- **BPM-Power** risponde con la verifica anti-bot di Cloudflare
- **ePrice** non lo vieta per scritto (il `robots.txt` permette le pagine prodotto), ma
  Davide ha scelto i soli link anche lì
- **eBay**: l'API gratuita dà solo gli annunci attivi, i venduti sono chiusi ai nuovi
  sviluppatori. Il link ai venduti mostra i prezzi veri nel browser di chi è collegato
- **Versus** vieta di copiare o riusare i contenuti, e non ha un'API

Quindi qui si costruiscono **indirizzi**, e il prezzo lo scrive Davide. L'hub sa solo
quello che gli viene scritto: quando e a quanto. Gli avvisi si basano su quello.

⚠️ Formati verificati a mano il 25/09/2026:
- ricerca ePrice `/sa/?qs=` (la pagina `/search/` del `robots.txt` è un'altra cosa)
- Versus `/it/<pezzo-a>-vs-<pezzo-b>`: l'ordine lo sistema da solo; **la ricerca
  `/it/search?q=` che la pagina dichiara NON funziona** — ignora la query e mostra
  un'altra ricerca. Per questo non c'è: sarebbe un link che apre la pagina sbagliata
- Keepa `#!product/8-<ASIN>`: 8 è amazon.it nell'enumerazione dei domini di Keepa
- ricerca BPM-Power `/it/ricerca?k=`: dal pannello di Claude non si vede (Cloudflare), l'ha
  presa Davide da una ricerca vera nel suo browser (`/it/ricerca?k=rtx+5090`)
"""
import re
from datetime import date, datetime
from urllib.parse import quote_plus, urlparse

STATI = ("posseduto", "desiderato", "venduto")

# ⚠️ Scelta, non misurata: dopo quanti giorni il prezzo scritto di un pezzo si
# considera da ricontrollare. Se diventa fastidioso si cambia qui, non a occhio altrove.
GIORNI_PROMEMORIA = 14

# Per ogni negozio: il campo che tiene l'indirizzo incollato e i domini accettati.
# Un indirizzo di un altro sito, o che non comincia per http(s), **non** si salva: finirebbe
# in un `href`, e `javascript:` lì dentro è codice che gira al clic.
NEGOZI = {
    "link_amazon": ("Amazon", ("amazon.it", "amzn.eu", "amzn.to")),
    "link_eprice": ("ePrice", ("eprice.it",)),
    "link_bpm": ("BPM-Power", ("bpm-power.com",)),
    "link_versus": ("Versus", ("versus.com",)),
}


def link_valido(campo, url):
    """Torna l'indirizzo se è http(s) e del dominio giusto, altrimenti None."""
    url = (url or "").strip()
    if not url:
        return None
    try:
        p = urlparse(url)
    except ValueError:
        return None
    host = (p.hostname or "").lower()
    domini = NEGOZI[campo][1]
    if p.scheme not in ("http", "https"):
        return None
    if not any(host == d or host.endswith("." + d) for d in domini):
        return None
    return url


def asin(url):
    """L'ASIN da un indirizzo di prodotto Amazon (`/dp/…` o `/gp/product/…`).

    Un link corto (`amzn.eu/d/…`) non lo contiene, e allora niente Keepa: il link
    corto si risolverebbe solo chiedendolo ad Amazon, cioè leggendo il sito."""
    m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", url or "")
    return m.group(1) if m else None


def slug_versus(nome):
    """`Nvidia GeForce RTX 3070` → `nvidia-geforce-rtx-3070`.

    È un'**ipotesi**: funziona coi nomi puliti, non con quelli di DxDiag
    («AMD Ryzen 7 5800X 8-Core Processor» dà Not found). Per quello c'è `link_versus`."""
    return re.sub(r"[^a-z0-9]+", "-", (nome or "").lower()).strip("-")


def _slug_da_link(url):
    """L'ultimo pezzo del percorso di una pagina Versus, se è quella di un prodotto."""
    percorso = urlparse(url).path.strip("/").split("/")
    if len(percorso) >= 2 and "-vs-" not in percorso[-1]:
        return percorso[-1]
    return None


def slug_di(comp):
    return (comp.get("link_versus") and _slug_da_link(comp["link_versus"])) \
        or slug_versus(comp.get("name"))


def link(comp):
    """I link di un componente, nell'ordine in cui compaiono.

    Ognuno è `{etichetta, url, nota}`: la nota finisce nel `title`, e dice quando il link
    è una **ricerca** e non la pagina del prodotto, o quando è un ripiego."""
    nome = (comp.get("name") or "").strip()
    q = quote_plus(nome)
    fuori = []

    def aggiungi(etichetta, url, nota=""):
        fuori.append({"etichetta": etichetta, "url": url, "nota": nota})

    # Senza link incollato, l'ASIN del modello collegato al catalogo (`opendb_asin`, messo
    # dalla vista): il link incollato vince sempre, è quello che Davide ha guardato.
    if comp.get("link_amazon"):
        aggiungi("Amazon", comp["link_amazon"], "la pagina del prodotto")
        a = asin(comp["link_amazon"])
        if a:
            aggiungi("Keepa", f"https://keepa.com/#!product/8-{a}",
                     "storico del prezzo su Amazon, e da lì l'avviso via email")
    elif comp.get("opendb_asin"):
        a = comp["opendb_asin"]
        aggiungi("Amazon", f"https://www.amazon.it/dp/{a}",
                 "la pagina del modello collegato, dal catalogo OpenDB: se non è quello "
                 "giusto, incolla la pagina vera")
        aggiungi("Keepa", f"https://keepa.com/#!product/8-{a}",
                 "storico del prezzo su Amazon del modello collegato, e da lì l'avviso via email")
    else:
        aggiungi("Amazon", f"https://www.amazon.it/s?k={q}",
                 "ricerca per nome: incolla la pagina del prodotto per avere anche Keepa")
    if comp.get("link_eprice"):
        aggiungi("ePrice", comp["link_eprice"], "la pagina del prodotto")
    else:
        aggiungi("ePrice", f"https://www.eprice.it/sa/?qs={q}", "ricerca per nome")
    if comp.get("link_bpm"):
        aggiungi("BPM", comp["link_bpm"], "la pagina del prodotto")
    else:
        aggiungi("BPM", f"https://www.bpm-power.com/it/ricerca?k={q}", "ricerca per nome")
    aggiungi("eBay", f"https://www.ebay.it/sch/i.html?_nkw={q}",
             "annunci in vendita adesso")
    aggiungi("eBay venduti", f"https://www.ebay.it/sch/i.html?_nkw={q}&LH_Sold=1&LH_Complete=1",
             "i prezzi a cui si è venduto davvero. Serve il login su eBay")
    if comp.get("link_versus"):
        aggiungi("Versus", comp["link_versus"], "la pagina del prodotto")
    elif nome:
        aggiungi("Versus", f"https://versus.com/it/{slug_versus(nome)}",
                 "indirizzo ricavato dal nome: se dà «Not found», incolla quello giusto")
    return fuori


def confronti(componenti):
    """«Confronta su Versus» fra un pezzo posseduto e uno desiderato della stessa
    categoria: è la domanda «mi conviene cambiarlo?». Uno per coppia."""
    fuori = []
    per_cat = {}
    for c in componenti:
        per_cat.setdefault(c.get("category"), []).append(c)
    for cat, pezzi in per_cat.items():
        miei = [c for c in pezzi if c.get("stato") == "posseduto"]
        voglio = [c for c in pezzi if c.get("stato") == "desiderato"]
        for a in miei:
            for b in voglio:
                sa, sb = slug_di(a), slug_di(b)
                if sa and sb and sa != sb:
                    fuori.append({"categoria": cat, "a": a.get("name"), "b": b.get("name"),
                                  "url": f"https://versus.com/it/{sa}-vs-{sb}"})
    return fuori


def _giorno(testo):
    try:
        return datetime.strptime(testo or "", "%Y-%m-%d").date()
    except ValueError:
        return None


def data_valore(nuovo, prima, data_prima, oggi):
    """La data di un prezzo scritto a mano: resta quella di prima se il valore non è
    cambiato, diventa oggi se è cambiato, sparisce se il valore non c'è.

    ⚠️ Serve perché `pcbuilder_save()` **cancella e ricrea** i componenti a ogni
    salvataggio: senza passare la data dal form, ogni salvataggio la rifarebbe oggi e
    il promemoria non scatterebbe mai."""
    if not nuovo:
        return None
    if prima is not None and abs(nuovo - prima) < 0.005 and _giorno(data_prima):
        return data_prima
    return oggi.isoformat()


def avvisi(componenti, oggi=None):
    """Quello che il PC Builder dice all'apertura, da quello che l'hub sa.

    - **obiettivo**: un desiderato il cui prezzo è sceso fino alla soglia, o un
      posseduto il cui valore da usato è salito fino alla soglia
    - **ricontrollare**: un desiderato col prezzo mai scritto o più vecchio di
      `GIORNI_PROMEMORIA`; un posseduto con una soglia di vendita e il valore da usato
      mai scritto o vecchio. Un posseduto **senza** soglia non chiede niente: non si
      sta pensando di venderlo

    I venduti e i pezzi senza stato non compaiono."""
    oggi = oggi or date.today()
    obiettivo, ricontrollare = [], []
    for c in componenti:
        stato = c.get("stato")
        soglia = c.get("obiettivo")
        if stato == "desiderato":
            prezzo, quando = c.get("price") or 0, _giorno(c.get("prezzo_data"))
            if soglia and prezzo and prezzo <= soglia:
                obiettivo.append({**c, "motivo": f"costa {prezzo:.2f} €, la soglia è {soglia:.2f} €"})
            if not prezzo or not quando:
                ricontrollare.append({**c, "motivo": "prezzo mai scritto"})
            elif (oggi - quando).days > GIORNI_PROMEMORIA:
                ricontrollare.append({**c, "motivo": f"prezzo di {(oggi - quando).days} giorni fa"})
        elif stato == "posseduto" and soglia:
            valore, quando = c.get("valore_usato"), _giorno(c.get("valore_usato_data"))
            if valore and valore >= soglia:
                obiettivo.append({**c, "motivo": f"da usato vale {valore:.2f} €, la soglia è {soglia:.2f} €"})
            if not valore or not quando:
                ricontrollare.append({**c, "motivo": "valore da usato mai scritto"})
            elif (oggi - quando).days > GIORNI_PROMEMORIA:
                ricontrollare.append({**c, "motivo": f"valore da usato di {(oggi - quando).days} giorni fa"})
    return {"obiettivo": obiettivo, "ricontrollare": ricontrollare}
