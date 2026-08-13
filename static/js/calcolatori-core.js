// calcolatori-core.js — formule, risoluzione nomi, motore abilita' e motore meteo.
// Serve calcolatori-data.js caricato prima.

// Unico punto di traduzione tipo EN->IT. Accetta qualsiasi capitalizzazione e
// lascia passare i tipi gia' in italiano.
function tipoIT(t){
  if(!t) return '';
  return TYPE_EN_TO_IT[String(t).toLowerCase()] || t;
}
// Il tipo **da mostrare**, nella lingua attiva. La chiave resta sempre quella
// italiana: TYPE_CHART, TYPE_CLR_IT e i `value` delle tendine sono indicizzati
// cosi', ed e' la stessa regola delle chiavi del catalogo — cambia solo cio' che
// si legge. Accetta anche i tipi inglesi che arrivano da /api/pokemon.
function tipoVis(tipo){
  const it = tipoIT(tipo);
  return it ? t(it) : '';
}
// ── Utility ───────────────────────────────────────────────────────────────────
function calcSt(base, ev, iv, lvl, nm, isHP) {
  const b = parseInt(base, 10) || 0;
  const e = parseInt(ev, 10) || 0;
  const i = parseInt(iv, 10) ?? 31;
  const l = parseInt(lvl, 10) || 50;

  // Convenzione Champions: SP 0-32, ogni SP vale +2 (NON gli EV 0-252 standard).
  // Deve restare allineata a updateSpeed() nel tab Speed Tier, che usa la stessa formula.
  if (isHP) return Math.floor((2 * b + i + e * 2) * l / 100) + l + 10;
  return Math.floor(Math.floor((2 * b + i + e * 2) * l / 100 + 5) * (nm || 1.0));
}

function getNM(nat,stat){return NM[nat]?.[stat]||1.0;}
// ── Motore abilità data-driven ────────────────────────────────────────────────
// Legge il blocco `effect` da data/abilities.json (via ABILITIES_DATA) invece di
// confrontare stringhe hardcoded. Aggiungere un'abilità = modificare il JSON.
// I nomi nel JSON sono in italiano, come le tendine dell'interfaccia.
function abilityEffect(name) {
  if (!name) return { type: 'none' };
  // Il match esatto sulla chiave non basta: il catalogo Pokémon cita le abilità
  // col **nome inglese** (`Swift Swim`) mentre le chiavi sono italiane
  // (`Nuotovelox`), quindi le tendine popolate dalle abilità del Pokémon non
  // trovavano mai niente — Kingdra sotto pioggia restava a 105 invece di 210.
  // `risolviChiave` accetta chiave, nome italiano e nome inglese, come già fa
  // la casella delle mosse.
  const voce = ABILITIES_DATA[risolviChiave(ABILITIES_DATA, name)];
  return (voce && voce.effect) ? voce.effect : { type: 'none' };
}

// Un'abilità "incide" se ha un effetto che il calcolatore danno sa applicare.
const EFFETTI_SUL_DANNO = new Set([
  'ate','tough_claws','wonder_guard','overgrow','filter','fluffy','thick_fat',
  'multiscale','marvel_scale','fur_coat','technician','sheer_force','tinted_lens',
  'purifying_salt','stab_multiplier','guts','stat_mult','spread_boost',
  'type_boost_weather','weather_def_boost','weather_spdef_boost','immunity','absorb'
]);
function abilityIncideSulDanno(name) {
  return EFFETTI_SUL_DANNO.has(abilityEffect(name).type);
}

// Effetti che modificano una stat visualizzata (usato dallo Stat Preview).
const EFFETTI_SULLE_STAT = new Set(['stat_mult','speed_weather','speed_status','fur_coat','marvel_scale']);
function abilityIncideSulleStat(name) {
  return EFFETTI_SULLE_STAT.has(abilityEffect(name).type);
}

// Moltiplicatore che un'abilità applica a una singola stat, dato il meteo.
function moltiplicatoreStat(fx, stat, weather) {
  if (!fx) return 1.0;
  if (fx.type === 'stat_mult' && fx.stat === stat)               return fx.value || 1.0;
  if (fx.type === 'speed_weather' && stat === 'spe' && weather === fx.weather) return fx.value || 2.0;
  if (fx.type === 'fur_coat'     && stat === 'def')              return 2.0;
  if (fx.type === 'marvel_scale' && stat === 'def')              return 1.5;
  return 1.0;
}

// Meteo effettivo: un'abilita' `weather_override` lo impone sul meteo scelto a mano,
// una `weather_setter` lo evoca solo se non e' stato scelto nulla (la evoca all'entrata).
// Ritorna anche l'abilita' che lo ha determinato, per leggerne `weather_ball_type`.
function meteoEffettivo() {
  const scelto = document.getElementById('f_weather')?.value || '';
  const nomi = [
    document.getElementById('atk_ability')?.value || '',
    document.getElementById('def_ability')?.value || ''
  ];
  for (const n of nomi) {
    const fx = abilityEffect(n);
    if (fx.type === 'weather_override' && fx.weather) return { weather: fx.weather, fonte: n };
  }
  if (!scelto) {
    for (const n of nomi) {
      const fx = abilityEffect(n);
      if (fx.type === 'weather_setter' && fx.weather) return { weather: fx.weather, fonte: n };
    }
  }
  return { weather: scelto, fonte: '' };
}

// Tipo della Palla Clima: mappa per meteo, con override dal JSON abilita'.
function tipoPallaClima(weather, fonte) {
  const daAbilita = fonte ? (ABILITIES_DATA[fonte] || {}).weather_ball_type : null;
  return daAbilita || WEATHER_BALL_TYPE[weather] || 'Normale';
}

// Aggiorna BP e tipo nei campi della mossa quando dipendono dal meteo, cosi' il
// valore usato dal calcolo e' anche quello che l'utente vede.
function applicaMeteoAllaMossa() {
  // MOSSE_METEO e' indicizzata per chiave, la casella contiene il nome tradotto.
  const nome = risolviChiave(MOVES_DB, document.getElementById('mv_name')?.value || '');
  const regola = MOSSE_METEO[nome];
  const nota = document.getElementById('mv_weather_note');
  const { weather, fonte } = meteoEffettivo();

  if (!regola) { if (nota) nota.style.display = 'none'; return; }

  const bpEl = document.getElementById('mv_bp');
  const tipoEl = document.getElementById('mv_type');
  let messaggio = '';

  if (regola.tipoDalMeteo) {
    const tipo = tipoPallaClima(weather, fonte);
    if (bpEl)   bpEl.value = weather ? regola.bpConMeteo : regola.bpBase;
    if (tipoEl) tipoEl.value = tipo;
    messaggio = weather
      ? tf('{meteo} → tipo {tipo}, BP {bp}', {meteo: t(METEO_LABEL[weather] || weather),
                                              tipo: tipoVis(tipo), bp: regola.bpConMeteo})
      : tf('Nessun meteo → tipo {tipo}, BP {bp}', {tipo: t('Normale'), bp: regola.bpBase});
  } else if (regola.dimezzaCon) {
    const dimezza = regola.dimezzaCon.includes(weather);
    if (bpEl) bpEl.value = dimezza ? Math.floor(regola.bpBase / 2) : regola.bpBase;
    messaggio = dimezza
      ? tf('{meteo} → BP dimezzato a {bp}', {meteo: t(METEO_LABEL[weather] || weather),
                                             bp: Math.floor(regola.bpBase / 2)})
      : tf('BP pieno {bp}', {bp: regola.bpBase});
  }

  if (nota) {
    nota.textContent = '🌍 ' + messaggio + (fonte ? ' ' + tf('(meteo da {fonte})', {fonte: fonte}) : '');
    nota.style.display = 'block';
  }
}

// Segnala sotto la tendina Meteo quando il meteo usato nel calcolo non e' quello
// scelto, perche' imposto o evocato da un'abilita'. Senza questo l'utente vede
// "Nessuno" e numeri da Sole, senza capire perche'.
function aggiornaNotaMeteo() {
  const nota = document.getElementById('f_weather_note');
  if (!nota) return;
  const scelto = document.getElementById('f_weather')?.value || '';
  const { weather, fonte } = meteoEffettivo();
  if (!fonte || weather === scelto) { nota.style.display = 'none'; return; }
  const fx = abilityEffect(fonte);
  // Le due frasi restano intere nel dizionario invece di essere "{abilita} " + verbo:
  // in inglese il verbo non sta nello stesso posto. E vanno scritte **dentro** la
  // chiamata a tf(), non passate da una variabile, altrimenti
  // controlla_traduzioni.py non le vede e le segnala come orfane.
  const chiaveAbil = risolviChiave(ABILITIES_DATA, fonte);
  const valori = {abilita: nomeVis(ABILITIES_DATA[chiaveAbil], chiaveAbil),
                  meteo: t(METEO_LABEL[weather] || weather)};
  nota.textContent = fx.type === 'weather_override'
    ? tf('⚠️ {abilita} impone {meteo}: il calcolo usa questo meteo', valori)
    : tf('⚠️ {abilita} evoca {meteo}: il calcolo usa questo meteo', valori);
  nota.style.display = 'block';
}

// Riempie una select con TUTTE le abilità (408), marcando con ● quelle che
// incidono sul calcolo. Le altre restano selezionabili come pura informazione.
// `ambito`: 'danno' (default) | 'velocita' | 'stat' — cambia solo quali marcare.
// Abilita' del Pokemon scelto, per ogni tendina che ne ha una. Serve a ripopolare
// quando si spunta "mostra tutte" senza dover rifare la fetch.
const ABILITA_POKEMON = {};

// `true` se la spunta "mostra tutte" del riquadro e' attiva. Esiste perche' il
// catalogo abilita' contiene anche le voci **inventate** di Champions, che nessun
// Pokemon ha in catalogo: senza una via d'uscita, stringere le tendine le renderebbe
// inutilizzabili.
function mostraTutteAbilita(chiave) {
  const box = document.getElementById(chiave === 'stat' ? 'abil_tutte_stat' : 'abil_tutte_dmg');
  return !!(box && box.checked);
}

// Ripopola le quattro tendine con le abilita' gia' note, senza rifare la rete.
function ripopolaAbilita() {
  popolaSelectAbilita(document.getElementById('atk_ability'), undefined, ABILITA_POKEMON.atk, 'dmg');
  popolaSelectAbilita(document.getElementById('def_ability'), undefined, ABILITA_POKEMON.def, 'dmg');
  popolaSelectAbilita(document.getElementById('stat_abil'), 'stat', ABILITA_POKEMON.stat, 'stat');
  popolaSelectAbilita(document.getElementById('stat_abil_b'), 'stat', ABILITA_POKEMON.stat_b, 'stat');
}

// `soloQueste` = le abilita' di quel Pokemon. Se e' nulla o vuota si mostrano tutte:
// e' il caso delle forme inventate, che in catalogo di abilita' non ne hanno, e
// lasciarle senza scelte sarebbe peggio del rumore che il filtro toglie.
function popolaSelectAbilita(sel, ambito, soloQueste, riquadro) {
  if (!sel || typeof ABILITIES_DATA !== 'object') return;
  const precedente = sel.value;
  let chiavi = Object.keys(ABILITIES_DATA);
  const proprie = (soloQueste || []).map(a => risolviChiave(ABILITIES_DATA, a)).filter(Boolean);
  const ristretto = proprie.length && !mostraTutteAbilita(riquadro);
  if (ristretto) chiavi = chiavi.filter(k => proprie.includes(k));
  const rilevante = ambito === 'velocita'
    ? (n => ['speed_weather','speed_status'].includes(abilityEffect(n).type))
    : ambito === 'stat' ? abilityIncideSulleStat
    : abilityIncideSulDanno;
  const frag = document.createDocumentFragment();
  const vuota = document.createElement('option');
  vuota.value = ''; vuota.textContent = t('— Nessuna —');
  frag.appendChild(vuota);
  // Il `value` resta la CHIAVE: e' quella che il motore degli effetti cerca dentro
  // ABILITIES_DATA. Cambia solo il testo che si legge.
  chiavi
    .sort((a, b) => nomeVis(ABILITIES_DATA[a], a)
                      .localeCompare(nomeVis(ABILITIES_DATA[b], b), LANG))
    .forEach(nome => {
    const o = document.createElement('option');
    o.value = nome;
    const attiva = rilevante(nome);
    o.textContent = (attiva ? '● ' : '   ') + nomeVis(ABILITIES_DATA[nome], nome);
    if (attiva) o.style.fontWeight = '600';
    const desc = (ABILITIES_DATA[nome] || {}).desc;
    if (desc) o.title = desc;
    frag.appendChild(o);
  });
  sel.innerHTML = '';
  sel.appendChild(frag);
  // L'abilita' scelta prima puo' non essere piu' in elenco (Pokemon cambiato, o
  // filtro appena stretto): rimetterla alla cieca lascerebbe un `value` che la
  // tendina non mostra piu', cioe' un calcolo con un'abilita' invisibile.
  if (precedente && chiavi.includes(precedente)) sel.value = precedente;
  else if (precedente) sel.value = '';
}

// ── Nome visualizzato -> chiave ──────────────────────────────────────────────
// Nelle caselle con datalist l'utente scrive il nome **tradotto**, mentre a
// indicizzare i dati e' la chiave. Questo indice riporta indietro: accetta la
// chiave, il nome italiano e quello inglese, senza distinzione di maiuscole.
const _INDICI_NOMI = new WeakMap();
function indiceNomi(db) {
  if (_INDICI_NOMI.has(db)) return _INDICI_NOMI.get(db);
  const idx = {};
  const conEffetto = v => v && v.effect && v.effect.type && v.effect.type !== 'none';
  for (const [chiave, voce] of Object.entries(db)) {
    for (const n of [chiave, voce && voce.nome_it, voce && voce.nome_en]) {
      if (!n) continue;
      const k = String(n).toLowerCase();
      // Piu' chiavi possono condividere lo stesso nome: `Forza Bruta` e
      // `Forzabruta` sono due voci distinte che si chiamano **entrambe**
      // Sheer Force, e una sola delle due ha l'effetto. Vincendo l'ultima,
      // Sheer Force risolveva sulla voce inerte e non applicava niente.
      // A parita' di nome tiene quella che ha qualcosa da applicare; sulle
      // mosse e sugli oggetti, che non hanno `effect`, non cambia nulla.
      if (idx[k] && conEffetto(db[idx[k]]) && !conEffetto(voce)) continue;
      idx[k] = chiave;
    }
  }
  _INDICI_NOMI.set(db, idx);
  return idx;
}

// La chiave corrispondente a quel che l'utente ha scritto, o la stringa stessa.
function risolviChiave(db, nome) {
  if (!nome) return '';
  return indiceNomi(db)[String(nome).trim().toLowerCase()] || nome;
}

function normalizeName(name){
  if(CHAMPIONS_BST[name]) return name;
  if(ALIAS[name]) return ALIAS[name];
  const lo = name.toLowerCase();
  for(const k of Object.keys(CHAMPIONS_BST)) if(k.toLowerCase()===lo) return k;
  for(const [a,c] of Object.entries(ALIAS)) if(a.toLowerCase()===lo) return c;
  return name;
}

// Indice del catalogo, equivalente JS di _INDICE in api_pokemon.py: chiavi top-level
// + campo `name` + le forme annidate in `forms`. Senza le forme, Mega e regionali
// sono irraggiungibili (il catalogo ne annida 84 dentro 72 Pokémon).
let _CATALOG_INDEX = null;
function catalogIndex(){
  if(_CATALOG_INDEX) return _CATALOG_INDEX;
  const idx = {};
  const add = (k, v) => { const kk = String(k).toLowerCase(); if(!(kk in idx)) idx[kk] = v; };
  for(const [key, e] of Object.entries(CHAMPIONS_BST)){
    add(key, e);
    if(e.name) add(e.name, e);
    if(e.forms) for(const [fname, fentry] of Object.entries(e.forms)) add(fname, fentry);
  }
  _CATALOG_INDEX = idx;
  return idx;
}

// Ritorna la voce di catalogo di un nome (forme incluse), o null.
function catalogEntry(name){
  const idx = catalogIndex();
  return idx[String(name).toLowerCase()] || idx[String(normalizeName(name)).toLowerCase()] || null;
}

// Marca una voce come Mega e ne calcola il BST. Prima queste due informazioni
// arrivavano da MEGA_DATA, la terza copia delle stat: le Mega ora escono dal
// catalogo come tutti gli altri, quindi il BST è la somma delle base.
// "Meganium" non ha lo spazio dopo "Mega" e non entra qui.
function marcaMega(nome, d){
  if(!nome.startsWith('Mega ')) return d;
  d.isMega = true;
  d.megaName = d.name || nome;
  d.megaBST = Object.values(d.stats || {}).reduce((s, v) => s + (parseInt(v, 10) || 0), 0);
  return d;
}

async function fetchPkmn(name){
  if(pkCache[name]) return pkCache[name];

  // ── Fetch normale ── (Mega comprese: /api/pokemon risolve anche le forme
  // annidate in `forms`, quindi il catalogo è l'unica fonte delle stat)
  try {
    // `?reg=` serve alle mosse legali: l'elenco di Champions non e' quello dei
    // giochi principali (Incineroar in M-A non ha Knock Off). Le stat non cambiano.
    const r = await fetch('/api/pokemon/' + encodeURIComponent(name) + '?reg=' + encodeURIComponent(REG_ID));
    const d = await r.json();
    if (d.ok) {
      marcaMega(name, d);
      pkCache[name] = d;
      return d;
    }
  } catch(e) {}

  // Fallback senza parentesi
  const baseName = name.replace(/\s*\(.*?\)/g, '').trim();
  if (baseName !== name) {
    try {
      const r2 = await fetch('/api/pokemon/' + encodeURIComponent(baseName) + '?reg=' + encodeURIComponent(REG_ID));
      const d2 = await r2.json();
      if (d2.ok) {
        marcaMega(name, d2);
        pkCache[name] = d2;
        return d2;
      }
    } catch(e) {}
  }

  return null;
}

window.switchTab = function(id, btn){
  document.querySelectorAll('.calc-panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.calc-tab').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab_'+id).classList.add('active');btn.classList.add('active');
  if (id === 'speed' && SPEED_META.length === 0) loadRegSpeed();
  // Le tabelle di riferimento sono generate da JS al primo accesso al tab.
  if (id === 'ref') preparaTabelleRiferimento();
}

function enforceEVLimit(inputs, displayId) {
  inputs.forEach(inp => {
    let v = parseInt(inp.value, 10);
    if (isNaN(v) || v < 0) v = 0;
    if (v > EV_FIELD_MAX) { v = EV_FIELD_MAX; inp.value = v; }
  });
  let total = inputs.reduce((s, e) => s + (parseInt(e.value, 10)||0), 0);
  if (total > EV_TOTAL_MAX) {
    const excess = total - EV_TOTAL_MAX;
    for (let i = inputs.length - 1; i >= 0; i--) {
      const v = parseInt(inputs[i].value, 10)||0;
      if (v > 0) { inputs[i].value = Math.max(0, v - excess); break; }
    }
    total = EV_TOTAL_MAX;
  }
  if (displayId) {
    const el = document.getElementById(displayId);
    if (el) {
      el.textContent = `EVs: ${total}/66`;
      el.style.color = total >= EV_TOTAL_MAX ? 'var(--error,#c33)' : 'var(--text-muted)';
      el.style.fontWeight = total >= EV_TOTAL_MAX ? '700' : '';
    }
  }
}

function getEVInputs(prefix) {
  return ['hp','atk','def','spa','spd','spe'].map(s => document.getElementById(prefix + s)).filter(Boolean);
}
