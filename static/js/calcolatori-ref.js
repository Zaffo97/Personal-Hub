// calcolatori-ref.js — tabelle di riferimento (efficacia tipi e nature) e loro
// due contenitori: il tab "📚 Reference" e l'overlay a schermo.
// Serve calcolatori-data.js caricato prima (TYPE_CHART, TIPI_IT, TYPE_CLR_IT, NM, NATURES).
//
// Prima dell'08/08/2026 queste due tabelle erano HTML incollato a mano nel template,
// duplicato byte per byte nei due contenitori: 4 righe per 112 KB. Peggio, erano
// indipendenti dalla type chart del motore danno, quindi potevano divergere in
// silenzio. Ora entrambe le versioni escono da qui, dagli stessi dati del calcolo.

// Aspetto delle celle di efficacia, per moltiplicatore.
const EFF_CELLA = {
  2:   { sfondo: '#2a8a3a',     testo: '#fff',                simbolo: '2×' },
  0.5: { sfondo: '#c33322',     testo: '#fff',                simbolo: '½' },
  0:   { sfondo: '#555',        testo: '#fff',                simbolo: '0' },
  1:   { sfondo: 'transparent', testo: 'var(--text-muted)',   simbolo: '·' }
};

// Abbreviazione usata da righe e colonne: le prime 4 lettere del nome **mostrato**,
// quindi tradotto. Verificato che non nasca nessuna collisione: in inglese Grass/
// Ground danno Gras/Grou e Dragon/Dark danno Drag/Dark, tutte distinte fra loro.
function abbrTipo(tipo) { return tipoVis(tipo).slice(0, 4); }

// Tabella 18x18 dell'efficacia, generata da TYPE_CHART.
function htmlTabellaTipi() {
  let h = '<div style="overflow-x:auto"><table style="border-collapse:collapse;width:100%">';

  h += '<tr><th style="font-size:.55rem;padding:.2rem;background:var(--surface-off)">ATK↓ DEF→</th>';
  for (const t of TIPI_IT) {
    const c = TYPE_CLR_IT[t];
    h += '<th style="padding:.15rem .1rem;background:' + c + '22;min-width:28px">'
       + '<span style="writing-mode:vertical-rl;font-size:.55rem;font-weight:700;color:' + c + '">'
       + abbrTipo(t) + '</span></th>';
  }
  h += '</tr>';

  for (const atk of TIPI_IT) {
    const c = TYPE_CLR_IT[atk];
    h += '<tr><td style="padding:.15rem .3rem;background:' + c + '22">'
       + '<span style="font-size:.6rem;font-weight:700;color:' + c + '">' + abbrTipo(atk) + '</span></td>';
    for (const dif of TIPI_IT) {
      const eff = EFF_CELLA[(TYPE_CHART[atk] || {})[dif] ?? 1];
      h += '<td style="text-align:center;padding:.1rem;background:' + eff.sfondo
         + ';font-size:.65rem;font-weight:700;color:' + eff.testo + '">' + eff.simbolo + '</td>';
    }
    h += '</tr>';
  }
  return h + '</table></div>';
}

// Tabella delle 25 nature, generata da NATURES (ordine) e NM (moltiplicatori).
// Le 5 neutre non stanno in NM: restano senza + e senza −.
function htmlTabellaNature() {
  const ETICHETTA = { atk:'Atk', def:'Def', spa:'SpA', spd:'SpD', spe:'Spe' };
  const TD = 'padding:.35rem .6rem;text-align:center;font-size:.75rem';
  const cella = (testo, colore) => '<td style="' + TD + '"><span style="'
    + (colore ? 'color:' + colore + ';font-weight:700' : 'color:var(--text-muted)')
    + '">' + testo + '</span></td>';

  let h = '<table style="border-collapse:collapse;width:100%">'
    + '<tr style="background:var(--surface-off)">'
    + '<th style="padding:.4rem .6rem;text-align:left;font-size:.75rem">' + t('Natura') + '</th>'
    + '<th style="padding:.4rem .6rem;font-size:.75rem">+10%</th>'
    + '<th style="padding:.4rem .6rem;font-size:.75rem">-10%</th></tr>';

  for (const nome of NATURES) {
    const mod = NM[nome] || {};
    const su  = Object.keys(mod).find(k => mod[k] > 1);
    const giu = Object.keys(mod).find(k => mod[k] < 1);
    h += '<tr style="border-top:1px solid var(--border)">'
       + '<td style="padding:.35rem .6rem;font-size:.75rem;font-weight:600">' + nome + '</td>'
       + (su  ? cella('+' + ETICHETTA[su],  '#2a8a3a') : cella('–', null))
       + (giu ? cella('-' + ETICHETTA[giu], '#c33322') : cella('–', null))
       + '</tr>';
  }
  return h + '</table>';
}

// Riempie un contenitore una sola volta: 324 celle per tabella, inutile rifarle.
function riempiUnaVolta(id, generatore) {
  const el = document.getElementById(id);
  if (el && !el.dataset.riempito) {
    el.innerHTML = generatore();
    el.dataset.riempito = '1';
  }
}

// I quattro contenitori: due nel tab Reference, due nell'overlay.
function preparaTabelleRiferimento() {
  riempiUnaVolta('tab_tipi_box',     htmlTabellaTipi);
  riempiUnaVolta('tab_nature_box',   htmlTabellaNature);
  riempiUnaVolta('ovl_tipi_box',     htmlTabellaTipi);
  riempiUnaVolta('ovl_nature_box',   htmlTabellaNature);
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function openRef(section){
  preparaTabelleRiferimento();
  document.getElementById('ref_overlay').style.display='block';
  showRef(section||'types');
}
function closeRef(){
  document.getElementById('ref_overlay').style.display='none';
}
function showRef(section){
  preparaTabelleRiferimento();
  document.getElementById('ref_types').style.display   = section==='types'   ? 'block':'none';
  document.getElementById('ref_natures').style.display = section==='natures' ? 'block':'none';
  document.getElementById('ref_title').textContent     = section==='types' ? t('Tabella Tipi (Gen 9)') : t('Tabella Nature');
  document.getElementById('ref_btn_types').className   = 'btn btn-sm ' + (section==='types'   ? 'btn-primary':'btn-secondary');
  document.getElementById('ref_btn_natures').className = 'btn btn-sm ' + (section==='natures' ? 'btn-primary':'btn-secondary');
}
document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeRef(); });

// ── Tab Reference ─────────────────────────────────────────────────────────────
function showRefSection(sec, btn){
  preparaTabelleRiferimento();
  document.getElementById('refsec_types').style.display   = sec==='types'   ? 'block':'none';
  document.getElementById('refsec_natures').style.display = sec==='natures' ? 'block':'none';
  document.getElementById('refsec_btn_types').className   = 'btn btn-sm '+(sec==='types'  ?'btn-primary':'btn-secondary');
  document.getElementById('refsec_btn_natures').className = 'btn btn-sm '+(sec==='natures'?'btn-primary':'btn-secondary');
}
