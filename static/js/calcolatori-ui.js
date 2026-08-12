// calcolatori-ui.js — quick-load del team, overlay riferimenti, init della pagina.
// ULTIMO file da caricare: qui stanno le chiamate che avviano la pagina.

// ── Team quick-load ───────────────────────────────────────────────────────────
async function loadTeamFromURL(){
  const tid=new URLSearchParams(location.search).get('team');
  if(!tid)return;
  try{
    const r=await fetch('/api/team/'+tid);const d=await r.json();
    if(!d.ok)return;
    TEAM_DATA=d.members.filter(m=>m&&m.pokemon);
    const wrap=document.getElementById('team_quickload');
    const btnWrap=document.getElementById('team_pk_buttons');
    if(!TEAM_DATA.length)return;
    wrap.style.display='block';
    btnWrap.innerHTML=TEAM_DATA.map((m,i)=>`
      <button class="team-pk-btn" id="tpk_${i}"
        onclick="loadTeamPkmn(${i},'atk',event)"
        title="Click=ATK · Shift+Click=DEF">
        ${m.pokemon}
      </button>`).join('');
  }catch(e){console.warn('Team non caricato:',e);}
}
async function loadTeamPkmn(idx,side,ev){
  const actualSide=ev&&ev.shiftKey?'def':'atk';
  const m=TEAM_DATA[idx];if(!m)return;
  // Evidenzia pulsante
  document.querySelectorAll('.team-pk-btn').forEach(b=>{b.classList.remove('active-atk','active-def');});
  document.getElementById('tpk_'+idx).classList.add('active-'+actualSide);
  // Carica il Pokémon nel lato corretto
  const effName = m.mega_stone ? 'Mega '+m.pokemon : m.pokemon;
  document.getElementById(actualSide+'_name').value=effName;
  const d=await fetchPkmn(effName);
  if(!d)return;
  BS[actualSide]=d.stats;
  const sp=document.getElementById(actualSide+'_spr');
  if(sp&&d.sprite)sp.innerHTML='<img src="'+d.sprite+'" style="height:66px;image-rendering:pixelated">';
  checkFormToggle(actualSide, effName);
  // Precompila EVs/IVs/natura dal team salvato
  const evMap={hp:'ev_hp',atk:'ev_atk',def:'ev_def',spa:'ev_spatk',spd:'ev_spdef',spe:'ev_spe'};
  const ivMap={hp:'iv_hp',atk:'iv_atk',def:'iv_def',spa:'iv_spatk',spd:'iv_spdef',spe:'iv_spe'};
  STAT_KEYS.forEach(s=>{
    const evEl=document.getElementById(actualSide+'_ev_'+s);
    const ivEl=document.getElementById(actualSide+'_iv_'+s);
    if(evEl) evEl.value=m[evMap[s]]||0;
    if(ivEl) ivEl.value=m[ivMap[s]]!==undefined?m[ivMap[s]]:31;
  });
  if(m.nature){
    const natSel=document.getElementById(actualSide+'_nat');
    if(natSel){[...natSel.options].forEach(o=>{if(o.value===m.nature)o.selected=true;});}
  }
  recalcSide(actualSide);
}

// Sposta overlay al body per evitare problemi con overflow-x:hidden
// Al caricamento le select abilità mostrano l'elenco completo, marcando le attive:
// nessun Pokémon è ancora scelto, quindi non c'è niente su cui stringerle. Si
// restringono da sole quando un Pokémon viene caricato (loadSide / loadStatPkmn).
document.addEventListener('DOMContentLoaded', function(){
  popolaSelectAbilita(document.getElementById('atk_ability'));
  popolaSelectAbilita(document.getElementById('def_ability'));
  popolaSelectAbilita(document.getElementById('spe_abil'), 'velocita');
  popolaSelectAbilita(document.getElementById('stat_abil'), 'stat');
  popolaSelectAbilita(document.getElementById('stat_abil_b'), 'stat');
});

document.addEventListener('DOMContentLoaded', function(){
  const ov = document.getElementById('ref_overlay');
  if (ov && ov.parentNode !== document.body) {
    document.body.appendChild(ov);
  }
  loadRegSpeed();

  const weatherEl = document.getElementById('f_weather');
  if (weatherEl) {
    weatherEl.addEventListener('change', function () {
      // Weather Ball e i Solar cambiano BP/tipo col meteo: aggiornali subito.
      applicaMeteoAllaMossa();
      aggiornaNotaMeteo();
      updateSpeed();
      updateStatPreview();
      // Solo se c'e' un attaccante caricato: calcDamage() altrimenti apre un alert.
      if (BS.atk && (BS.atk.hp || BS.atk.atk)) calcDamage();
    });
  }
  aggiornaNotaMeteo();
});

// openRef / closeRef / showRef / showRefSection stanno in calcolatori-ref.js,
// insieme ai generatori delle due tabelle che riempiono.

document.addEventListener('DOMContentLoaded', function(){
  loadMovesDB();
});
// ────────────────────────────────────────────────────────────────────────────
// Init
//loadMovesDB();
loadTeamFromURL();
