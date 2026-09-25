// Il worker che esegue Python nel browser con Pyodide (sezione Python).
//
// Sta in un Web Worker e non nella pagina per una ragione sola: un `while True` nella
// pagina la congela, e non c'è modo di fermarlo. Qui il tempo massimo lo tiene
// python-esegui.js, che allo scadere **chiude il worker** e ne apre uno nuovo.
//
// Pyodide (314.0.7) sta in static/vendor/, fuori da git: lo scarica
// `python scripts/scarica_pyodide.py`. I pacchetti che non sono nella libreria standard
// (numpy, pandas, …) li prende dal CDN ufficiale al primo import, e solo allora.

const VERSIONE = '314.0.7';
const BASE = `/static/vendor/pyodide-${VERSIONE}/`;
const CDN = `https://cdn.jsdelivr.net/pyodide/v${VERSIONE}/full/`;

let py = null;

async function prepara() {
  if (!py) {
    const { loadPyodide } = await import(BASE + 'pyodide.mjs');
    py = await loadPyodide({ indexURL: BASE, packageBaseUrl: CDN });
  }
  return py;
}

// Il lavoro vero lo fa Python: scrive i file in una cartella pulita, toglie da
// sys.modules i moduli della volta prima (altrimenti un file modificato resterebbe
// quello vecchio, in silenzio), poi esegue il principale o scopre i test.
// ⚠️ Una cartella **nuova a ogni esecuzione** (/progetto/1, /progetto/2, …): la prima
// versione cancellava /progetto mentre ci stava dentro (era la cartella corrente), la
// cancellazione falliva in silenzio e il secondo «Esegui» si rompeva. E se fosse
// fallita a metà, un file tolto dal progetto sarebbe rimasto lì, importabile.
const ESEGUI = `
import os, sys, shutil, runpy, traceback, unittest
os.chdir('/')
shutil.rmtree('/progetto', ignore_errors=True)
__hub_giro = globals().get('__hub_giro', 0) + 1
_d = f'/progetto/{__hub_giro}'
os.makedirs(_d)
sys.path[:] = [p for p in sys.path if not p.startswith('/progetto')]
for _n, _c in __hub_file.items():
    _p = os.path.join(_d, *_n.replace('\\\\', '/').split('/'))
    os.makedirs(os.path.dirname(_p), exist_ok=True)
    with open(_p, 'w', encoding='utf-8') as _f:
        _f.write(_c)
for _m in [k for k, v in list(sys.modules.items())
           if (getattr(v, '__file__', '') or '').startswith('/progetto')]:
    del sys.modules[_m]
os.chdir(_d)
sys.path.insert(0, _d)
__hub_codice = 0
try:
    if __hub_test:
        _suite = unittest.defaultTestLoader.discover(_d)
        _r = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(_suite)
        __hub_codice = 0 if _r.wasSuccessful() else 1
    else:
        runpy.run_path(__hub_principale, run_name='__main__')
except SystemExit as _e:
    __hub_codice = _e.code if isinstance(_e.code, int) else (0 if _e.code is None else 1)
except BaseException:
    traceback.print_exc()
    __hub_codice = 1
__hub_codice
`;

self.onmessage = async (ev) => {
  const { tipo, id } = ev.data;
  if (tipo === 'prepara') {
    try { await prepara(); self.postMessage({ id, pronto: true }); }
    catch (e) { self.postMessage({ id, errore: 'Pyodide non si carica: ' + (e && e.message || e) }); }
    return;
  }
  const { file, principale, stdin, test } = ev.data;
  const uscita = [], errori = [];
  const inizio = performance.now();
  try {
    const p = await prepara();
    p.setStdout({ batched: s => uscita.push(s + '\n') });
    p.setStderr({ batched: s => errori.push(s + '\n') });
    const righe = (stdin || '').split('\n');
    let i = 0;
    p.setStdin({ stdin: () => (i < righe.length ? righe[i++] : null) });
    // Gli import dei file che non sono nella libreria standard: numpy & co. dal CDN.
    const caricati = [];
    await p.loadPackagesFromImports(Object.values(file).join('\n'),
                                    { messageCallback: m => caricati.push(m), errorCallback: m => errori.push(m + '\n') });
    p.globals.set('__hub_file', p.toPy(file));
    p.globals.set('__hub_principale', principale || '');
    p.globals.set('__hub_test', !!test);
    const codice = await p.runPythonAsync(ESEGUI);
    self.postMessage({ id, uscita: uscita.join(''), errori: errori.join(''), codice: Number(codice) || 0,
                       secondi: Math.round(performance.now() - inizio) / 1000,
                       pacchetti: caricati.filter(m => /^Loaded /.test(m)) });
  } catch (e) {
    self.postMessage({ id, uscita: uscita.join(''), errori: errori.join('') + String(e && e.message || e) + '\n',
                       codice: 1, secondi: Math.round(performance.now() - inizio) / 1000 });
  }
};
