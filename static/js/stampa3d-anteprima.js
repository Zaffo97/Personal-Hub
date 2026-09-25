// L'anteprima 3D dei file allegati a un progetto di Stampa 3D.
//
// three.js (0.186.1, MIT) sta in static/vendor/ e si carica **solo al primo clic** su
// «Anteprima», con import() dinamici risolti dall'importmap della pagina: sono 2,3 MB,
// e chi apre la sezione senza guardare un modello non li scarica.
//
// ⚠️ Cosa NON fa, e lo dice a schermo invece di mostrare una scena vuota:
//   - STEP/STP: three.js non li legge (servirebbe OpenCascade in WebAssembly, decine
//     di MB). Il pulsante non compare nemmeno
//   - i colori e le impostazioni di stampa di un progetto Bambu: il 3MF porta la
//     geometria e, se ci sono, i colori dei materiali; il resto lo sa solo lo slicer
//
// ⚠️ Gli assi: la stampa 3D è Z-su, three.js è Y-su. STL e 3MF vengono ruotati di
// -90° su X perché stiano in piedi sul piatto come nello slicer. L'OBJ no: non ha una
// convenzione, e i file dei siti di modelli arrivano in tutti e due i modi.

const UNITA_MM = { micron: 0.001, millimeter: 1, centimeter: 10, inch: 25.4, foot: 304.8, meter: 1000 };

let caricati = null;          // i moduli di three.js, dopo il primo clic
let scena = null;             // quello che va smontato alla chiusura

function carica() {
  if (!caricati) {
    caricati = Promise.all([
      import('three'),
      import('three/addons/controls/OrbitControls.js'),
      import('three/addons/loaders/STLLoader.js'),
      import('three/addons/loaders/3MFLoader.js'),
      import('three/addons/loaders/OBJLoader.js'),
      import('three/addons/libs/fflate.module.js'),
    ]).then(([THREE, oc, stl, tmf, obj, fflate]) => ({
      THREE, OrbitControls: oc.OrbitControls, STLLoader: stl.STLLoader,
      ThreeMFLoader: tmf.ThreeMFLoader, OBJLoader: obj.OBJLoader, fflate,
    })).catch(e => { caricati = null; throw e; });
  }
  return caricati;
}

// L'unità del 3MF: il loader la legge ma non la applica, quindi le misure uscirebbero
// in pollici o centimetri scritte come millimetri. Si cerca nel modello principale.
function unita3mf(fflate, buffer) {
  try {
    const zip = fflate.unzipSync(new Uint8Array(buffer), {
      filter: f => /^3D\/[^\/]*\.model$/.test(f.name),
    });
    const nome = Object.keys(zip)[0];
    if (!nome) return 1;
    const testa = new TextDecoder().decode(zip[nome].slice(0, 4000));
    const m = testa.match(/<model[^>]*\bunit="([a-z]+)"/);
    return m ? (UNITA_MM[m[1]] || 1) : 1;
  } catch (e) {
    return 1;
  }
}

function colore(nomeVar, riserva) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(nomeVar).trim();
  return v || riserva;
}

function smonta() {
  if (!scena) return;
  cancelAnimationFrame(scena.giro);
  scena.osserva.disconnect();
  scena.controlli.dispose();
  scena.oggetto.traverse(o => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) [].concat(o.material).forEach(m => m.dispose());
  });
  scena.renderer.dispose();
  scena.renderer.domElement.remove();
  scena = null;
}

function scrivi(testo, errore) {
  const el = document.getElementById('anteprimaInfo');
  el.textContent = testo;
  el.style.color = errore ? 'var(--error)' : '';
}

async function apri(fid, nome) {
  const modale = document.getElementById('modaleAnteprima');
  const box = document.getElementById('anteprimaTela');
  document.getElementById('titoloAnteprima').textContent = nome;
  smonta();
  modale.classList.add('open');
  scrivi('Carico…');
  const est = (nome.split('.').pop() || '').toLowerCase();
  try {
    const [m, risposta] = await Promise.all([carica(), fetch('/stampa3d/file/' + fid)]);
    // Un file che manca dal disco risponde con un redirect alla pagina (e un flash):
    // senza questo controllo si passerebbe l'HTML al lettore, con un errore che non
    // dice niente.
    if (!risposta.ok || risposta.redirected) {
      throw new Error('il file non si è scaricato (manca dal disco?)');
    }
    const dati = await risposta.arrayBuffer();
    const { THREE } = m;
    let oggetto, scala = 1, ruota = true;
    if (est === 'stl') {
      const geo = new m.STLLoader().parse(dati);
      // ⚠️ Le normali scritte nel file non sono affidabili: molti programmi le
      // esportano tutte a zero, e il lettore le prende com'è — il pezzo esce nero,
      // senza nessun errore. Si ricalcolano sempre dai triangoli.
      geo.computeVertexNormals();
      const mat = geo.hasColors
        ? new THREE.MeshStandardMaterial({ vertexColors: true })
        : new THREE.MeshStandardMaterial({ color: colore('--primary', '#7c6ff0') });
      oggetto = new THREE.Mesh(geo, mat);
    } else if (est === '3mf') {
      oggetto = new m.ThreeMFLoader().parse(dati);
      scala = unita3mf(m.fflate, dati);
    } else if (est === 'obj') {
      oggetto = new m.OBJLoader().parse(new TextDecoder().decode(dati));
      ruota = false;
    } else {
      throw new Error('anteprima non disponibile per .' + est);
    }
    // Un materiale senza colore (OBJ senza .mtl, 3MF senza colori) esce bianco puro:
    // si tinge col colore del tema, così si distingue dallo sfondo chiaro.
    oggetto.traverse(o => {
      if (o.isMesh && o.material && !o.material.vertexColors && o.material.color &&
          o.material.color.getHex() === 0xffffff && est !== 'stl') {
        o.material = new THREE.MeshStandardMaterial({ color: colore('--primary', '#7c6ff0') });
      }
    });
    if (ruota) oggetto.rotation.x = -Math.PI / 2;
    const gruppo = new THREE.Group();
    gruppo.add(oggetto);
    // Sul piatto: centrato in X/Z, appoggiato a Y=0.
    const b = new THREE.Box3().setFromObject(gruppo);
    if (b.isEmpty()) throw new Error('il file non contiene triangoli');
    const centro = b.getCenter(new THREE.Vector3());
    oggetto.position.x -= centro.x;
    oggetto.position.z -= centro.z;
    oggetto.position.y -= b.min.y;
    const dim = b.getSize(new THREE.Vector3());
    const lato = Math.max(dim.x, dim.y, dim.z);

    const larg = box.clientWidth, alt = box.clientHeight;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(larg, alt);
    box.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 2.2));
    const sole = new THREE.DirectionalLight(0xffffff, 2);
    sole.position.set(lato, lato * 2, lato * 1.5);
    scene.add(sole);
    scene.add(gruppo);
    const griglia = new THREE.GridHelper(lato * 2, 20, colore('--text-faint', '#888'), colore('--border', '#444'));
    scene.add(griglia);
    const camera = new THREE.PerspectiveCamera(40, larg / alt, lato / 100, lato * 100);
    camera.position.set(lato * 1.3, lato * 1.1, lato * 1.6);
    const controlli = new m.OrbitControls(camera, renderer.domElement);
    controlli.target.set(0, dim.y / 2, 0);
    controlli.enableDamping = true;
    controlli.update();

    const osserva = new ResizeObserver(() => {
      const w = box.clientWidth, h = box.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    osserva.observe(box);
    scena = { renderer, controlli, oggetto: gruppo, osserva, giro: 0 };
    const disegna = () => {
      if (!scena) return;
      scena.giro = requestAnimationFrame(disegna);
      controlli.update();
      renderer.render(scene, camera);
    };
    disegna();

    let triangoli = 0;
    gruppo.traverse(o => {
      if (o.isMesh) {
        const g = o.geometry;
        triangoli += (g.index ? g.index.count : g.attributes.position.count) / 3;
      }
    });
    // Le misure sono quelle del riquadro allineato agli assi, nell'orientamento del
    // file: sono quelle con cui lo slicer lo appoggia sul piatto. `dim` è già nella
    // scena (Y-su, ruotata se serviva), quindi l'altezza è sempre la Y.
    const mm = v => (v * scala).toLocaleString('it-IT', { maximumFractionDigits: 1 });
    scrivi(`${mm(dim.x)} × ${mm(dim.z)} × ${mm(dim.y)} mm (L × P × A) · ` +
           `${Math.round(triangoli).toLocaleString('it-IT')} triangoli · ` +
           'trascina per ruotare, rotella per lo zoom, tasto destro per spostare');
  } catch (e) {
    smonta();
    scrivi('Anteprima non riuscita: ' + (e && e.message ? e.message : e), true);
  }
}

function chiudiAnteprima() {
  smonta();
  document.getElementById('modaleAnteprima').classList.remove('open');
}

window.apriAnteprima = apri;
window.chiudiAnteprima = chiudiAnteprima;
