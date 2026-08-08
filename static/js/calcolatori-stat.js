// calcolatori-stat.js — tab Stat Preview e forme alternative.
// Serve calcolatori-data.js e calcolatori-core.js caricati prima.

// ── TAB STAT PREVIEW ──────────────────────────────────────────────────────────
let curBS=null;
let curBS_b=null;


async function loadStatPkmn(side){
  side = side || 'a';
  const sfx = side==='b' ? '_b' : '';
  const name=document.getElementById('stat_name'+sfx).value.trim();
  if(name.length<2)return;
  const timerKey='stat'+side;
  clearTimeout(loadTimers[timerKey]);
  loadTimers[timerKey]=setTimeout(async()=>{
    const d=await fetchPkmn(name);if(!d)return;
    if (side === 'b') {
      curBS_b = {
        ...d.stats,
        abilities: d.abilities || [],
        types: d.types || []
      };
    } else {
      curBS = {
        ...d.stats,
        abilities: d.abilities || [],
        types: d.types || []
      };
    }
    const sp=document.getElementById('stat_spr'+sfx);
    if(sp){const url=d.sprite_hd||d.sprite;sp.innerHTML=url?'<img src="'+url+'" style="width:78px;height:78px;object-fit:contain" loading="lazy">':'<span style="font-size:2.5rem">?</span>';}
    // Tipi e abilità (usa quelli della mega se attiva)
    const types = d.types || [];
    const abils = d.abilities || [];
    document.getElementById('stat_types'+sfx).innerHTML=types.map(t=>'<span style="background:'+(TYPE_CLR[t]||TYPE_CLR[t.toLowerCase()]||'#888')+';color:#fff;padding:.15rem .5rem;border-radius:20px;font-size:.65rem;font-weight:700">'+t+'</span>').join('');
    let abilHtml = '<strong>Abilita:</strong> '+abils.join(' / ');
    if(d.isMega) abilHtml += ' <span style="background:var(--primary);color:#fff;font-size:.6rem;padding:.1rem .4rem;border-radius:10px;font-weight:700">MEGA</span>';
    if(d.megaBST) abilHtml += ' <span style="color:var(--text-muted);font-size:.65rem">BST '+d.megaBST+'</span>';
    document.getElementById('stat_abils'+sfx).innerHTML=abilHtml;
    updateStatPreview();
  },300);
}

function clearStatB(){
  curBS_b=null;
  document.getElementById('stat_name_b').value='';
  document.getElementById('stat_spr_b').innerHTML='<span style="font-size:2rem;opacity:.25">❔</span>';
  document.getElementById('stat_types_b').innerHTML='';
  document.getElementById('stat_abils_b').innerHTML='';
  ['hp','atk','def','spa','spd','spe'].forEach(function(s){
    const ev=document.getElementById('st_ev_b_'+s);if(ev)ev.value=0;
  });
  document.getElementById('st_ev_tot_b').textContent='EVs: 0/66';
  updateStatPreview();
}

function updateStatPreview(){
  const nat_a = document.getElementById('stat_nat').value;
  const nat_b = document.getElementById('stat_nat_b') ? document.getElementById('stat_nat_b').value : '';
  const lvl_a = parseInt(document.getElementById('stat_lvl').value) || 50;
  const lvl_b = parseInt(document.getElementById('stat_lvl_b') ? document.getElementById('stat_lvl_b').value : 50) || 50;
  const nm_a = NM[nat_a] || {};
  const nm_b = NM[nat_b] || {};
  const bars = document.getElementById('stat_bars');

  if (!curBS && !curBS_b){
    bars.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-muted);font-size:.85rem">Seleziona almeno un Pokemon</div>';
    return;
  }

  const comparing = curBS && curBS_b;
  const CLR_A = comparing ? 'var(--primary)' : null;
  const CLR_B = '#e07b39';

  let html = '';
  let bst_a = 0;
  let bst_b = 0;

  for (const [i, s] of STAT_KEYS.entries()) {
    const base_a = curBS ? curBS[s] || 0 : null;
    const base_b = curBS_b ? curBS_b[s] || 0 : null;
    const ev_a = parseInt(document.getElementById('st_ev_' + s)?.value ?? 0, 10) || 0;
    const ev_b = parseInt(document.getElementById('st_ev_b_' + s)?.value ?? 0, 10) || 0;
    const mod_a = s === 'hp' ? 1.0 : (nm_a[s] ?? 1.0);
    const mod_b = s === 'hp' ? 1.0 : (nm_b[s] ?? 1.0);
    const weather = document.getElementById('f_weather')?.value || '';
    // Abilità scelte dall'utente nelle tendine, stesso motore degli altri due tab
    const aFx = abilityEffect(document.getElementById('stat_abil')?.value || '');
    const bFx = abilityEffect(document.getElementById('stat_abil_b')?.value || '');
    let val_a = base_a != null ? calcSt(base_a, ev_a, 31, lvl_a, mod_a, s === 'hp') : null;
    let val_b = base_b != null ? calcSt(base_b, ev_b, 31, lvl_b, mod_b, s === 'hp') : null;

    if (val_a != null) val_a = Math.floor(val_a * moltiplicatoreStat(aFx, s, weather));
    if (val_b != null) val_b = Math.floor(val_b * moltiplicatoreStat(bFx, s, weather));

    if (val_a !== null) bst_a += val_a;
    if (val_b !== null) bst_b += val_b;

    const maxVal = SM[s];
    const pct_a = val_a !== null ? Math.min(val_a / maxVal * 100, 100) : 0;
    const pct_b = val_b !== null ? Math.min(val_b / maxVal * 100, 100) : 0;
    const ind_a = mod_a > 1 ? '↑' : mod_a < 1 ? '↓' : '';
    const ind_b = mod_b > 1 ? '↑' : mod_b < 1 ? '↓' : '';
    const clr_ind_a = mod_a > 1 ? 'var(--success,#3a7)' : mod_a < 1 ? 'var(--error,#c33)' : 'transparent';
    const clr_ind_b = mod_b > 1 ? 'var(--success,#3a7)' : mod_b < 1 ? 'var(--error,#c33)' : 'transparent';
    const barClrA = CLR_A || SC[s];

    var cmp = '';
    if (comparing && val_a !== null && val_b !== null) {
      if (val_a > val_b) cmp = `<span style="color:var(--primary);font-weight:800;font-size:.7rem">A</span>`;
      else if (val_b > val_a) cmp = `<span style="color:#e07b39;font-weight:800;font-size:.7rem">B</span>`;
      else cmp = `<span style="color:var(--text-muted);font-size:.7rem">=</span>`;
    }

    var rowA = '';
    if (val_a !== null) rowA = `
      <div style="display:flex;align-items:center;gap:.35rem;margin-bottom:.15rem">
        <div style="font-size:.68rem;font-weight:700;width:28px;color:${SC[s]}">${STAT_LBLS[i]}</div>
        <div style="flex:1;height:8px;background:var(--surface-off);border-radius:4px;overflow:hidden">
          <div style="height:100%;width:${pct_a}%;background:${barClrA};border-radius:4px;opacity:.85"></div>
        </div>
        <div style="font-size:.72rem;font-weight:700;width:36px;text-align:right;color:${barClrA}">${val_a}<span style="font-size:.55rem;color:${clr_ind_a}">${ind_a}</span></div>
        ${comparing ? `<div style="width:14px;text-align:center">${cmp}</div>` : ''}
      </div>`;

    var rowB = '';
    if (val_b !== null) rowB = `
      <div style="display:flex;align-items:center;gap:.35rem;margin-bottom:.35rem">
        <div style="font-size:.68rem;font-weight:700;width:28px;color:${SC[s]}"></div>
        <div style="flex:1;height:8px;background:var(--surface-off);border-radius:4px;overflow:hidden">
          <div style="height:100%;width:${pct_b}%;background:${CLR_B};border-radius:4px;opacity:.85"></div>
        </div>
        <div style="font-size:.72rem;font-weight:700;width:36px;text-align:right;color:${CLR_B}">${val_b}<span style="font-size:.55rem;color:${clr_ind_b}">${ind_b}</span></div>
        <div style="width:14px"></div>
      </div>`;

    html += rowA + rowB;
  }

  html += `
    <div style="margin-top:.6rem;padding:.45rem .65rem;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--surface-off);font-size:.78rem;font-weight:700;">
      BST totale A: <span style="color:var(--primary)">${bst_a}</span>
      ${curBS_b ? ` | BST totale B: <span style="color:#e07b39">${bst_b}</span>` : ''}
    </div>
  `;

  bars.innerHTML = html;

  updStEV();
  if(curBS_b) updStEV('b');
}


function updStEV(){
  enforceEVLimit(getEVInputs('st_ev_'), 'st_ev_tot');
}
function resetStEVs(){
  STAT_KEYS.forEach(s=>{const el=document.getElementById('st_ev_'+s);if(el)el.value=0;});
  updateStatPreview();
}

// ── Forme alternative ─────────────────────────────────────────────────────────
function checkFormToggle(side, loadedName) {
  const baseName = FORM_BASE[loadedName] || loadedName;
  const variants = FORM_VARIANTS[baseName];
  const wrap = document.getElementById(side + '_form_wrap');
  if (!wrap) return;
  const sel = document.getElementById(side + '_form_sel');
  if (variants) {
    sel.innerHTML = variants.map(f =>
      '<option value="' + f + '"' + (f === loadedName ? ' selected' : '') + '>' + f + '</option>'
    ).join('');
    wrap.style.display = '';
  } else {
    wrap.style.display = 'none';
  }
}

async function onFormChange(side) {
  const val = document.getElementById(side + '_form_sel').value;
  if (!val) return;
  const d = await fetchPkmn(val);
  if (!d) return;
  BS[side] = d.stats;
  if (d.types && d.types.length) {
  BS[side].types = d.types.map(tipoIT);
}
  document.getElementById(side + '_name').value = val;
  const sp = document.getElementById(side + '_spr');
  if (sp && d.sprite) sp.innerHTML = '<img src="' + d.sprite + '" style="height:66px;image-rendering:pixelated">';
  else if (sp) sp.innerHTML = '<span style="font-size:2.5rem;opacity:.25">🧬</span>';
  recalcSide(side);
}
