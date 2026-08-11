// calcolatori-speed.js — tab Speed Tier.
// Serve calcolatori-data.js e calcolatori-core.js caricati prima.

// ── Mosse DB ──────────────────────────────────────────────────────────────────
async function loadRegSpeed() {
  const header = document.getElementById('speed_tier_header');
  if (header) header.textContent = '⏳ Caricamento…';
  try {
    const r = await fetch('/api/regulation/' + REG_ID + '/data');
    const d = await r.json();
    if (d.ok && d.roster) {
      // La velocità sta in base_stats.spe: leggerla da bst.spe dava null su tutti
      // e 174 Pokémon su 174 finivano scartati, con caduta muta sulla lista statica.
      const mancanti = [];
      SPEED_META = d.roster
        .map(name => {
          const base = catalogEntry(name)?.base_stats?.spe ?? null;
          if (base==null) { mancanti.push(name); return null; }
          return {name,base};
        })
        .filter(Boolean).sort((a,b) => b.base - a.base);
      if (mancanti.length) console.warn('Speed Tier — ' + mancanti.length + ' nomi del roster assenti dal catalogo:', mancanti);
      if (header) header.textContent = '📊 Speed Tier — ' + SPEED_META.length + ' Pokémon (' + REG_ID.toUpperCase() + ')';
    } else { SPEED_META = SPEED_META_STATIC; if (header) header.textContent = '📊 Speed Tier — ' + SPEED_META.length + ' Pokémon'; }
    // Se il roster non risolve nulla, meglio la lista statica di una tabella vuota.
    if (!SPEED_META.length) { SPEED_META = SPEED_META_STATIC; if (header) header.textContent = '📊 Speed Tier — ' + SPEED_META.length + ' Pokémon'; }
  } catch(e) { SPEED_META = SPEED_META_STATIC; if (header) header.textContent = '📊 Speed Tier — ' + SPEED_META.length + ' Pokémon'; }
  renderSpeed();
}
// ── TAB SPEED ─────────────────────────────────────────────────────────────────
async function loadSpePkmn(){
  const name=document.getElementById('spe_name').value.trim();
  if(name.length<2)return;
  clearTimeout(loadTimers.spe);
  loadTimers.spe=setTimeout(async()=>{
    const d=await fetchPkmn(name);
    if(!d)return;
    const sp=document.getElementById('spe_spr');
    if(sp){
      const url=d.sprite_hd||d.sprite;
      if(url) sp.innerHTML='<img src="'+url+'" style="height:58px;object-fit:contain" loading="lazy">';
      else sp.innerHTML='<span style="font-size:1.8rem;opacity:.3">🧬</span>';
    }
    document.getElementById('spe_base').value=d.stats?.spe||0;
    // Popola select abilità Speed
    const speAbilSel = document.getElementById('spe_abil');
    if (speAbilSel && d.abilities && d.abilities.length) {
      speAbilSel.innerHTML = '<option value="">— Nessuna —</option>';
    // Il catalogo Pokémon cita le abilità col nome inglese: qui si risale alla
    // chiave e si mostra il nome nella lingua attiva, come nelle altre tendine.
    // Il `value` resta il nome di partenza — `abilityEffect` lo risolve comunque.
    d.abilities.forEach(ab => {
      const opt = document.createElement('option');
      opt.value = ab;
      const chiave = risolviChiave(ABILITIES_DATA, ab);
      const voce = ABILITIES_DATA[chiave];
      const incide = ['speed_weather', 'speed_status'].includes(abilityEffect(ab).type);
      opt.textContent = (incide ? '● ' : '') + nomeVis(voce, chiave);
      if (incide) opt.style.fontWeight = '600';
      if (voce && voce.desc) opt.title = voce.desc;
      speAbilSel.appendChild(opt);
    });
}
    // Riempire spe_base non bastava: senza questa chiamata la propria Velocità
    // restava a "—" finché non si toccava un altro campo, e la tabella restava
    // confrontata con la velocità precedente.
    updateSpeed();
  },500);
}

function updateSpeed() {
  const base = parseInt(document.getElementById('spe_base').value) || 0;
  const ev   = parseInt(document.getElementById('spe_ev').value) || 0;
  const nat  = parseFloat(document.getElementById('spe_nat').value) || 1.0;
  const abil = document.getElementById('spe_abil')?.value || '';
  const weather = document.getElementById('spe_weather')?.value || '';

  const tailwind  = document.getElementById('spe_tailwind')?.checked;
  const scarf     = document.getElementById('spe_scarf')?.checked;
  const para      = document.getElementById('spe_para')?.checked;
  const icywind   = document.getElementById('spe_icywind')?.checked;
  const trickroom = document.getElementById('spe_trickroom')?.checked;

  // Stat base Lv.50
  let spd = Math.floor((2 * base + 31 + ev * 2) * 50 / 100 + 5);
  spd = Math.floor(spd * nat);

  // Moltiplicatori abilità — letti da abilities.json come nel calcolatore danno
  const fx = abilityEffect(abil);
  let abilMult = 1.0;
  if (fx.type === 'speed_weather' && weather === fx.weather) abilMult = fx.value || 2.0;
  if (fx.type === 'speed_status'  && para)                   abilMult = fx.value || 1.5;
  spd = Math.floor(spd * abilMult);
  const quickFeet = (fx.type === 'speed_status');

  // Item
  if (scarf) spd = Math.floor(spd * 1.5);

  // Condizioni campo
  if (tailwind) spd = Math.floor(spd * 2.0);
  if (para && !quickFeet) spd = Math.floor(spd * 0.5);
  if (icywind) spd = Math.floor(spd * 0.5);

  mySpeed = trickroom ? -spd : spd; // negativo = Trick Room per ordinamento invertito

  const el = document.getElementById('spe_val');
  if (el) {
    el.textContent = spd;
    el.style.color = trickroom ? 'var(--error)' : 'var(--primary)';
  }
  renderSpeed();
}

function renderSpeed(){
  const filt=document.getElementById('spe_filter').value;
  const search=document.getElementById('spe_search').value.toLowerCase();
  let rows=SPEED_META.filter(p=>{
    if(search&&!p.name.toLowerCase().includes(search))return false;
    const spd=calcSt(p.base,0,31,50,1.0,false);
    if(filt==='faster')return spd>mySpeed;
    if(filt==='slower')return spd<mySpeed;
    if(filt==='creep')return Math.abs(spd-mySpeed)<=10;
    return true;
  }).map(p=>({...p,speed:calcSt(p.base,0,31,50,1.0,false)}))
    .sort((a,b)=>b.speed-a.speed);
  const list=document.getElementById('speed_list');
  if(!rows.length){list.innerHTML='<div style="text-align:center;padding:1rem;color:var(--text-muted);font-size:.8rem">Nessun Pokémon trovato</div>';return;}
  list.innerHTML=rows.map(p=>{
    const cls=p.speed===mySpeed?'highlight':p.speed<mySpeed?'slower':'';
    const ico=p.speed>mySpeed?'▲':p.speed<mySpeed?'▼':'●';
    const scarfSpd=Math.floor(calcSt(p.base,0,31,50,1.0,false)*1.5);
    const twSpd=calcSt(p.base,0,31,50,1.0,false)*2;
    return `<div class="speed-row ${cls}">
      <span style="width:20px;font-size:.75rem">${ico}</span>
      <span style="font-weight:600;min-width:160px;font-size:.8rem">${p.name}</span>
      <span style="font-size:.7rem;color:var(--text-muted);min-width:55px" title="Stat base Speed">Base ${p.base}</span>
      <span style="font-weight:700;color:var(--primary);min-width:38px" title="Speed a Lv.50, 0 EV, nat. neutrale">${p.speed}</span>
      <span style="font-size:.65rem;color:var(--text-faint)" title="Con Choice Scarf / Con Tailwind">Scarf ${scarfSpd} · TW ${twSpd}</span>
    </div>`;
  }).join('');
}
