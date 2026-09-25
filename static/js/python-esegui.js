// «Esegui» della sezione Python: nel browser (Pyodide, in un worker) o sul PC dell'hub.
//
// Le due strade restituiscono la **stessa forma** — {uscita, errori, codice, secondi,
// scaduto, troncato} più `errore` se non è partito niente — così chi mostra il
// risultato non deve sapere da dove arriva.
//
// ⚠️ Nel browser il tempo massimo è **questo** file a tenerlo: allo scadere il worker si
// chiude (è l'unico modo di fermare un `while True`) e il prossimo «Esegui» ne apre uno
// nuovo, ricaricando Pyodide. Il caricamento di Pyodide **non** conta nel tempo: la prima
// volta ci vogliono alcuni secondi, e non sono colpa del codice.

(function () {
  const TEMPO = 30;              // secondi, lo stesso del PC (python_esegui.py)
  let worker = null, contatore = 0;
  const attese = new Map();

  function nuovoWorker() {
    worker = new Worker('/static/js/python-worker.js', { type: 'module' });
    worker.onmessage = ev => {
      const a = attese.get(ev.data.id);
      if (a) { attese.delete(ev.data.id); a(ev.data); }
    };
    worker.onerror = ev => {
      for (const [id, a] of attese) a({ errore: 'il worker si è fermato: ' + (ev.message || 'errore') });
      attese.clear();
      worker = null;
    };
    return worker;
  }

  function chiedi(messaggio, secondi) {
    const w = worker || nuovoWorker();
    const id = ++contatore;
    return new Promise(risolvi => {
      let timer = null;
      attese.set(id, dati => { clearTimeout(timer); risolvi(dati); });
      if (secondi) {
        timer = setTimeout(() => {
          attese.delete(id);
          w.terminate();
          if (worker === w) worker = null;
          risolvi({ uscita: '', errori: '', codice: null, secondi, scaduto: true });
        }, secondi * 1000);
      }
      w.postMessage(Object.assign({ id }, messaggio));
    });
  }

  async function browser(opzioni) {
    const pronto = await chiedi({ tipo: 'prepara' }, 0);
    if (pronto.errore) {
      return { errore: pronto.errore + ' — manca Pyodide? python scripts/scarica_pyodide.py' };
    }
    return chiedi({ tipo: 'esegui', file: opzioni.file, principale: opzioni.principale,
                    stdin: opzioni.stdin || '', test: !!opzioni.test }, TEMPO);
  }

  async function pc(opzioni) {
    try {
      const r = await fetch('/python/esegui', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: opzioni.file, principale: opzioni.principale,
                               stdin: opzioni.stdin || '', test: !!opzioni.test })
      });
      const d = await r.json().catch(() => ({ errore: 'risposta illeggibile (' + r.status + ')' }));
      if (!r.ok && !d.errore) d.errore = 'HTTP ' + r.status;
      return d;
    } catch (e) {
      return { errore: 'rete: ' + e.message };
    }
  }

  // Scrive un risultato in un <pre>. Testo, mai HTML: l'output è di chi ha scritto il
  // codice, e un print('<img onerror=…>') non deve diventare un tag.
  function mostra(pre, r, dove) {
    pre.textContent = '';
    const riga = (testo, colore) => {
      const s = document.createElement('span');
      s.textContent = testo;
      if (colore) s.style.color = colore;
      pre.appendChild(s);
    };
    if (r.errore) { riga('⚠ ' + r.errore + '\n', 'var(--error)'); return; }
    if (r.pacchetti && r.pacchetti.length) riga(r.pacchetti.join('\n') + '\n', 'var(--text-faint)');
    if (r.uscita) riga(r.uscita);
    if (r.errori) riga(r.errori, 'var(--error)');
    const fine = r.scaduto ? `⏱ fermato dopo ${r.secondi} s (tempo massimo)`
      : `— ${dove}, codice di uscita ${r.codice}, ${r.secondi} s`;
    riga('\n' + fine + (r.troncato ? ' · output tagliato' : '') + '\n',
         r.scaduto || r.codice ? 'var(--warning)' : 'var(--text-faint)');
  }

  // Collega un pannello: dentro `radice` i pulsanti [data-esegui="browser|pc"] (con
  // [data-test] per i test), un <textarea data-stdin> facoltativo e un <pre data-uscita>.
  // `fornisci()` dà {file, principale} al momento del clic, così si esegue quello che
  // c'è **nell'editor**, salvato o no.
  function collega(radice, fornisci) {
    const pulsanti = [...radice.querySelectorAll('[data-esegui]')];
    pulsanti.forEach(b => b.addEventListener('click', async () => {
      const dove = b.dataset.esegui;
      const pre = radice.querySelector('[data-uscita]');
      const stdin = radice.querySelector('[data-stdin]');
      const opz = Object.assign({ test: b.hasAttribute('data-test'),
                                  stdin: stdin ? stdin.value : '' }, fornisci());
      pulsanti.forEach(x => { x.disabled = true; });
      pre.hidden = false;
      pre.textContent = dove === 'browser' ? 'Avvio Python nel browser… (la prima volta ci vuole qualche secondo)'
                                           : 'Eseguo sul PC dell\'hub…';
      try {
        const r = dove === 'browser' ? await browser(opz) : await pc(opz);
        mostra(pre, r, dove === 'browser' ? 'nel browser' : 'sul PC');
      } finally {
        pulsanti.forEach(x => { x.disabled = false; });
      }
    }));
  }

  // Tab negli editor di codice: quattro spazi invece di passare al campo dopo. Solo nei
  // <textarea class="py-editor">; da lì si esce con Esc e poi Tab.
  let esciConTab = false;
  document.addEventListener('keydown', e => {
    const t = e.target;
    if (!(t instanceof HTMLTextAreaElement) || !t.classList.contains('py-editor')) return;
    if (e.key === 'Escape') { esciConTab = true; return; }
    if (e.key !== 'Tab' || e.shiftKey || esciConTab) { esciConTab = false; return; }
    e.preventDefault();
    const i = t.selectionStart;
    t.setRangeText('    ', i, t.selectionEnd, 'end');
    t.dispatchEvent(new Event('input', { bubbles: true }));
  });

  window.PyEsegui = { browser, pc, mostra, collega, TEMPO };
})();
