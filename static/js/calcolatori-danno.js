// calcolatori-danno.js — tab Danno: DB mosse, caricamento lati, formula Gen 9.
// Serve calcolatori-data.js e calcolatori-core.js caricati prima.

// MOVES_DB arriva già dal blocco calc-bootstrap, filtrato sulla regulation attiva.
// Prima questa funzione rifaceva fetch su /api/moves, che legge moves_ma.json
// hardcoded: su qualunque regulation diversa da MA le mosse corrette venivano
// sovrascritte con quelle di MA (su Pokedex: 921 -> 461).
// Mosse che l'attaccante puo' imparare nella regulation attiva, da /api/pokemon.
// `null` non vuol dire "nessuna": vuol dire **non lo sappiamo** — le forme inventate
// non stanno su PokeAPI, e chi non e' in Champions non ha l'elenco su M-A/M-B. In quel
// caso si mostrano tutte le mosse con un avviso, perche' mostrarne zero renderebbe
// inutilizzabili proprio le forme inventate.
let MOSSE_LEGALI = null;

function loadMovesDB(){
  const dl = document.getElementById('mv_dl');
  if (!dl) return 0;
  // Intersezione dei due filtri: le mosse della regulation (MOVES_DB, gia' filtrato
  // dal bootstrap) e quelle che il Pokemon puo' imparare.
  const legali = MOSSE_LEGALI ? new Set(MOSSE_LEGALI) : null;
  const chiavi = Object.keys(MOVES_DB).filter(m => !legali || legali.has(m));
  // Nel datalist si mostra il nome nella lingua attiva; risolviChiave() lo riporta
  // alla chiave quando l'utente lo sceglie.
  dl.innerHTML = chiavi
    .map(m => nomeVis(MOVES_DB[m], m))
    .sort((a, b) => a.localeCompare(b, LANG))
    .map(m => '<option value="' + m.replace(/"/g, '&quot;') + '">').join('');
  return chiavi.length;
}

// Chiamata quando cambia l'attaccante. `d` e' la risposta di /api/pokemon.
function applicaMosseLegali(d){
  MOSSE_LEGALI = (d && Array.isArray(d.moves)) ? d.moves : null;
  const quante = loadMovesDB();
  const nota = document.getElementById('mv_legali');
  if (!nota) return;
  const nome = (d && (d.nome || d.name)) || '';
  if (MOSSE_LEGALI) {
    nota.style.display = 'block';
    nota.style.color = 'var(--text-muted, #888)';
    nota.textContent = `${quante} mosse di ${nome} in ${REG_ID}`;
  } else if (nome) {
    nota.style.display = 'block';
    nota.style.color = 'var(--warning, #d90)';
    nota.textContent = `⚠️ Nessun elenco mosse per ${nome} in ${REG_ID}: sono mostrate tutte`;
  } else {
    nota.style.display = 'none';
  }
  // La mossa gia' scritta puo' essere diventata illegale col nuovo attaccante: si
  // lascia scritta ma si dice che non e' nell'elenco, invece di cancellarla sotto le
  // dita di chi sta digitando.
  const scritta = document.getElementById('mv_name').value.trim();
  if (scritta && MOSSE_LEGALI) {
    const chiave = risolviChiave(MOVES_DB, scritta);
    if (chiave && !MOSSE_LEGALI.includes(chiave)) {
      nota.style.color = 'var(--danger, #c33)';
      nota.textContent = `⚠️ ${nomeVis(MOVES_DB[chiave], chiave)} non è fra le mosse di ${nome} in ${REG_ID}`;
    }
  }
}
function onMoveSelect(){
  const mv=risolviChiave(MOVES_DB, document.getElementById('mv_name').value);
  const data=MOVES_DB[mv];
  const badge=document.getElementById('mv_autofill');
  if(!data){if(badge)badge.style.display='none';return;}
  document.getElementById('mv_bp').value=data.bp||0;
  if(data.category!=='status') document.getElementById('mv_cat').value=data.category;
  // Mappa tipo EN->IT e setta mv_type
  const mvTypeSel=document.getElementById('mv_type');
  if(mvTypeSel&&data.type){
    const itType=tipoIT(data.type);
    [...mvTypeSel.options].forEach(function(o){if(o.value===itType)o.selected=true;});
  }
  // Flag "contatto" — viene dal campo flags del JSON mosse (164 mosse su 461 ce l'hanno).
  // Serve a Tough Claws (x1.3) e Fluffy (x0.5).
  const _ct=document.getElementById('f_contact');
  if(_ct){
    _ct.checked=(data.flags||[]).includes('contact');
    const _lbl=document.getElementById('f_contact_auto');
    if(_lbl) _lbl.textContent=_ct.checked?'(auto: sì)':'(auto: no)';
  }
  // Label stage ATK/SP ATK e DEF/SP DEF
  const _isPhys=data.category==='physical';
  const _al=document.getElementById('atk_stage_lbl');
  const _dl=document.getElementById('def_stage_lbl');
  if(_al) _al.textContent=_isPhys?'ATK':'SP ATK';
  if(_dl) _dl.textContent=_isPhys?'DEF':'SP DEF';
  if(badge){
    const catIcon={physical:'Fis.',special:'Sp.',status:'Status'};
    badge.style.display='flex';
    badge.innerHTML=`<span class="mv-tag" style="background:${TYPE_CLR[data.type]||'#888'};color:#fff">${data.type}</span>`+
      `<span class="mv-tag">${catIcon[data.category]||''} ${data.category}</span>`+
      (data.bp?`<span class="mv-tag">BP ${data.bp}</span>`:'<span class="mv-tag">Status</span>');
  }
  // Weather Ball, Solar Beam e Solar Blade: BP e tipo dipendono dal meteo, quindi
  // vanno riscritti dopo l'autofill da MOVES_DB.
  applicaMeteoAllaMossa();
}

// ── TAB DANNO ─────────────────────────────────────────────────────────────────
let loadTimers={};

function loadSide(side){
  const name=document.getElementById(side+'_name').value.trim();
  if(name.length<2)return;
  clearTimeout(loadTimers[side]);
  loadTimers[side]=setTimeout(async()=>{
    const d=await fetchPkmn(name);if(!d)return;
    //BS[side]=d.stats;
    BS[side] = {
      ...d.stats,
      abilities: d.abilities || [],
      types: d.types || []
    };
    const sp=document.getElementById(side+'_spr');
    if(sp){
      const url=d.sprite_hd||d.sprite;
      if(url) sp.innerHTML='<img src="'+url+'" style="height:66px;object-fit:contain" loading="lazy">';
      else sp.innerHTML='<span style="font-size:2.5rem;opacity:.25">🧬</span>';
    }
    recalcSide(side);
    checkFormToggle(side, name);
    // Le mosse sono quelle di chi attacca: il difensore non le cambia.
    if (side === 'atk') applicaMosseLegali(d);
    // Autofill tipi difensore — reset esplicito, gestisce mono-tipo correttamente
    // Autofill tipi difensore — IDs corretti: def_type1 / def_type2
if (side === 'def' && d.types && d.types.length) {
  const tIT = d.types.map(tipoIT);
  const t1 = document.getElementById('def_type1');
  const t2 = document.getElementById('def_type2');

  if (t1) t1.value = tIT[0] || '';
  if (t2) t2.value = tIT[1] || '';
}

if (side === 'atk' && d.types && d.types.length) {
  BS.atk.types = d.types.map(tipoIT);
}

// Le tendine abilità sono gia' popolate al load: l'elenco non dipende dal Pokémon.

  },500);
}

function recalcSide(side){
  enforceEVLimit(getEVInputs(`${side}_ev_`), null);
  const bs=BS[side];if(!bs)return;
  const nat=document.getElementById(side+'_nat').value;
  const lvl=document.getElementById(side+'_lvl').value;
  STAT_KEYS.forEach(s=>{
    const ev=document.getElementById(side+'_ev_'+s)?.value||0;
    const iv=document.getElementById(side+'_iv_'+s)?.value||31;
    const val=calcSt(bs[s]||0,ev,iv,lvl,getNM(nat,s),s==='hp');
    const el=document.getElementById(side+'_cs_'+s);if(el)el.textContent=val;
  });
}

function calcDamage(){
  // Prima di leggere gli input: BP e tipo di Weather Ball / Solar Beam / Solar Blade
  // dipendono dal meteo effettivo, che a sua volta dipende dalle abilita' scelte.
  applicaMeteoAllaMossa();
  aggiornaNotaMeteo();

  // ── Leggi inputs ────────────────────────────────────────────────────────────
  const cat      = document.getElementById('mv_cat').value;
  const bp       = parseInt(document.getElementById('mv_bp').value)||100;
  const mvTypeRaw = document.getElementById('mv_type')?.value || '';
  let mvType = mvTypeRaw.trim(); // già italiano, nessuna traduzione necessaria
  const spread   = parseFloat(document.getElementById('mv_spread').value);
  const crit     = document.getElementById('f_crit').checked;
  const hh       = document.getElementById('f_hh').checked;
  const reflect  = document.getElementById('f_reflect')?.checked||false;
  const lscreen  = document.getElementById('f_lscreen')?.checked||false;
  // Meteo effettivo, non quello grezzo della tendina: le abilita' weather_override
  // lo impongono e le weather_setter lo evocano se non e' stato scelto nulla.
  const { weather, fonte: meteoFonte } = meteoEffettivo();
  const terrain  = document.getElementById('f_terrain').value;
  const aN       = document.getElementById('atk_nat').value;
  const dN       = document.getElementById('def_nat').value;
  const aLvl     = document.getElementById('atk_lvl').value;
  const dLvl     = document.getElementById('def_lvl').value;
  const atkStage  = parseInt(document.getElementById('atk_stage')?.value||0);
  const defStage  = parseInt(document.getElementById('def_stage')?.value||0);
  const trickroom = document.getElementById('f_trickroom')?.checked||false;
  const atkItem  = parseFloat(document.getElementById('atk_item')?.value||1);
  const defItem  = document.getElementById('def_item')?.value||'1';
  const atkStatus= document.getElementById('atk_status')?.value||'';
  const atkTera  = document.getElementById('atk_tera')?.value||'';
  const defTera  = document.getElementById('def_tera')?.value||'';
  const defType1 = document.getElementById('def_type1')?.value||'';
  const defType2 = document.getElementById('def_type2')?.value||'';
  const contact   = document.getElementById('f_contact')?.checked||false;
  const atkPinch  = document.getElementById('f_atk_pinch')?.checked||false;
  const atkAbilityName = document.getElementById('atk_ability')?.value || '';
  const defAbilityName = document.getElementById('def_ability')?.value || '';

  if(!BS.atk?.hp&&!BS.atk?.atk){alert('Carica almeno l\'attaccante!');return;}

  const aFx = abilityEffect(atkAbilityName);
  const dFx = abilityEffect(defAbilityName);

  // ── Abilità "-ate": cambiano il tipo della mossa e la potenziano ×1.2 ────────
  // Va applicato PRIMA di STAB e tabella tipi, altrimenti entrambi sbagliano.
  let ateBoost = 1.0;
  if (aFx.type === 'ate' && mvType) {
    if (aFx.any_source) {              // Normalità: converte qualsiasi tipo
      if (mvType !== aFx.move_type) { mvType = aFx.move_type; ateBoost = aFx.value || 1.2; }
    } else if (mvType === 'Normale') { // le altre: solo dalle mosse Normale
      mvType = aFx.move_type; ateBoost = aFx.value || 1.2;
    }
  }

  // ── Tipi effettivi (Tera sovrascrive) ────────────────────────────────────────
  const atkTypes = BS.atk?.types||[];
  const effectiveAtkTypes = atkTera ? [atkTera] : atkTypes;
  const effectiveDefTypes = defTera ? [defTera] : [defType1, defType2].filter(Boolean);

  // ── Type chart Gen 9 ─────────────────────────────────────────────────────────
  // Unica copia in calcolatori-data.js come TYPE_CHART: la stessa che disegna la
  // tabella di riferimento, così le due non possono più divergere.
  const TC = TYPE_CHART;

// Efficacia tipo — prodotto sui tipi del difensore (0x, 0.25x, 0.5x, 1x, 2x, 4x)
      let typeEff = 1.0;
        if (mvType && mvType !== 'Sconosciuto' && effectiveDefTypes.length > 0) { // 3B
          for (const dt of effectiveDefTypes)
          typeEff *= TC[mvType]?.[dt] ?? 1.0;
      }
      // Wonder Guard: subisce danno SOLO dalle mosse super efficaci.
      // Lo tratto come immunità (typeEff 0) cosi' riusa il ramo di output gia' esistente.
      let wonderGuardBlock = false;
      if (dFx.type === 'wonder_guard' && typeEff <= 1) {
        wonderGuardBlock = true;
        typeEff = 0;
      }
      // Immunità/assorbimento per tipo (Levitazione, Assorbiacqua, ...)
      if ((dFx.type === 'immunity' || dFx.type === 'absorb') && dFx.move_type === mvType) {
        typeEff = 0;
      }

      if (typeEff === 0) {
        const res = document.getElementById('dmg_result');
        if (res) res.style.display = 'block';
        const el = (id) => document.getElementById(id);
        if (el('dmg_line'))  el('dmg_line').textContent  = wonderGuardBlock
          ? `${mvType} → Wonder Guard: bloccata (solo le super efficaci passano)`
          : `${mvType} → Immune (0×) su ${effectiveDefTypes.join('/')}`;
        if (el('dmg_pct'))   el('dmg_pct').textContent   = '0%';
        if (el('dmg_bar'))   el('dmg_bar').style.width   = '0%';
        if (el('dmg_min'))   el('dmg_min').textContent   = '0';
        if (el('dmg_max'))   el('dmg_max').textContent   = '0';
        if (el('dmg_ohko'))  el('dmg_ohko').textContent  = '0 / 16';
        if (el('dmg_2hko'))  el('dmg_2hko').textContent  = '0 / 16';
        if (el('dmg_rolls')) el('dmg_rolls').textContent = '';
        return;
      }

      // STAB — 1.5× se tipo mossa == tipo attaccante
      // STAB
      let stab = 1.0;
      if (mvType) {
        const hasStab = effectiveAtkTypes.includes(mvType);
        stab = hasStab ? 1.5 : 1.0;
      }
  // ── Stage moltiplicatori ─────────────────────────────────────────────────────
  function stageMult(stage){
    const tbl={'-6':0.25,'-5':0.286,'-4':0.333,'-3':0.4,'-2':0.5,'-1':0.667,
               '0':1,'1':1.5,'2':2,'3':2.5,'4':3,'5':3.5,'6':4};
    return tbl[String(stage)]??1;
  }

  // ── Stat effettive ────────────────────────────────────────────────────────────
  const aStat = cat==='physical'?'atk':'spa';
  const dStat = cat==='physical'?'def':'spd';
  let A = calcSt(BS.atk[aStat]||0, document.getElementById('atk_ev_'+aStat)?.value||0,
                  31, aLvl, getNM(aN,aStat), false);
  let D = calcSt(BS.def[dStat]||0, document.getElementById('def_ev_'+dStat)?.value||0,
                  31, dLvl, getNM(dN,dStat), false);
  const HP = calcSt(BS.def.hp||0, document.getElementById('def_ev_hp')?.value||0,
                    31, dLvl, 1.0, true);

  // Stage — un critico ignora gli stage che sfavoriscono chi attacca: quelli
  // negativi dell'attaccante e quelli positivi del difensore. Prima li applicava
  // comunque, quindi un critico contro Difesa a +2 dava 52 invece di 102.
  const atkStageEff = (crit && atkStage < 0) ? 0 : atkStage;
  const defStageEff = (crit && defStage > 0) ? 0 : defStage;
  A = Math.floor(A * stageMult(atkStageEff));
  D = Math.floor(D * stageMult(defStageEff));

  // ── Modificatori su A (stat attacco) ────────────────────────────────────────
  // Guts (Combattività) trasforma la scottatura da malus in bonus
  if (cat === 'physical' && atkStatus === 'burn') {
    A = aFx.type === 'guts' ? Math.floor(A * 1.5) : Math.floor(A * 0.5);
  }
  // stat_mult: {stat:'atk'|'spa'|'spe', value:N} — es. Forzapura, Vigorilla, Agitazione
  if (aFx.type === 'stat_mult' && aFx.stat === aStat)
    A = Math.floor(A * (aFx.value || 1.0));

  // ── Modificatori su D (stat difesa) ─────────────────────────────────────────
  if (dFx.type === 'fur_coat' && cat === 'physical')
    D = Math.floor(D * 2.0);
  if (dFx.type === 'marvel_scale' && cat === 'physical')
    D = Math.floor(D * 1.5);
  if (dFx.type === 'stat_mult' && dFx.stat === dStat)
    D = Math.floor(D * (dFx.value || 1.0));
  // Meteo difensivo (Manto Neve -> Difesa, Tempra -> Difesa Speciale)
  if (dFx.type === 'weather_def_boost'    && cat === 'physical' && weather === dFx.weather)
    D = Math.floor(D * (dFx.value || 1.0));
  if (dFx.type === 'weather_spdef_boost'  && cat === 'special'  && weather === dFx.weather)
    D = Math.floor(D * (dFx.value || 1.0));
  // Fluffy NON e' un boost di Difesa: dimezza il danno da contatto e lo raddoppia
  // se la mossa e' di tipo Fuoco. I due effetti sono indipendenti e si cumulano
  // (mossa Fuoco da contatto -> x0.5 * x2 = x1). Applicato piu' sotto su `dmg`.

  // ── Moltiplicatori finali sul danno (non sulle stat) ────────────────────────
  let abilityDmgMult = ateBoost;   // le "-ate" portano gia' il loro ×1.2

  // ATTACCANTE
  if (aFx.type === 'tough_claws' && contact)                 abilityDmgMult *= (aFx.value || 1.3);
  if (aFx.type === 'technician'  && bp <= 60)                abilityDmgMult *= 1.5;
  if (aFx.type === 'sheer_force')                            abilityDmgMult *= 1.3;
  if (aFx.type === 'tinted_lens' && typeEff < 1)             abilityDmgMult *= 2.0;
  if (aFx.type === 'spread_boost' && spread < 1)             abilityDmgMult *= (aFx.value || 1.3);
  if (aFx.type === 'type_boost_weather' && mvType === aFx.move_type && weather === aFx.weather)
    abilityDmgMult *= (aFx.value || 1.5);
  // Overgrow & co.: ×1.5 solo sotto 1/3 PS e solo sul tipo giusto
  if (aFx.type === 'overgrow' && atkPinch && mvType === aFx.move_type) abilityDmgMult *= 1.5;

  // DIFENSORE
  // Fluffy NON e' un boost di Difesa: dimezza il danno da contatto e lo raddoppia
  // se la mossa e' Fuoco. Effetti indipendenti: Fuoco da contatto -> ×0.5 × ×2 = ×1.
  if (dFx.type === 'fluffy') {
    if (contact)             abilityDmgMult *= 0.5;
    if (mvType === 'Fuoco')  abilityDmgMult *= 2.0;
  }
  if (dFx.type === 'multiscale')                             abilityDmgMult *= 0.5;
  if (dFx.type === 'filter' && typeEff > 1.0)                abilityDmgMult *= (dFx.value || 0.75);
  if (dFx.type === 'thick_fat' && (mvType === 'Fuoco' || mvType === 'Ghiaccio')) abilityDmgMult *= 0.5;
  if (dFx.type === 'purifying_salt' && mvType === 'Spettro') abilityDmgMult *= 0.5;

  // ── STAB (Adattabilità lo porta da 1.5 a 2.0) ───────────────────────────────
  if (mvType && effectiveAtkTypes.includes(mvType))
    stab = (aFx.type === 'stab_multiplier') ? (aFx.value || 2.0) : 1.5;

  // ── Item ATK ─────────────────────────────────────────────────────────────────
  A = Math.floor(A * atkItem);

  // ── Item DEF ─────────────────────────────────────────────────────────────────
  if (defItem === 'av' && cat === 'special') D = Math.floor(D * 1.5);

  // ── Pioggia forte: le mosse Fuoco falliscono ────────────────────────────────
  // Il campo `fire_blocked` sta su Pioggia Perpetua in abilities.json; vale anche
  // quando la pioggia forte viene scelta a mano dalla tendina.
  const fuocoBloccato = weather === 'heavyrain' ||
    (meteoFonte ? (ABILITIES_DATA[meteoFonte] || {}).fire_blocked === true : false);

  // ── Formula danno base Gen 9 ──────────────────────────────────────────────────
  const base = Math.floor(Math.floor(Math.floor(2 * parseInt(aLvl) / 5 + 2) * bp * A / D) / 50) + 2;

  const rolls = Array.from({length: 16}, (_, i) => {
    let dmg = base;

    // Meteo
    if (weather === 'sun' || weather === 'harshsun') {
      if (mvType === 'Fuoco') dmg = Math.floor(dmg * 1.5);
      if (mvType === 'Acqua') dmg = Math.floor(dmg * 0.5);
    }
    if (weather === 'rain' || weather === 'heavyrain') {
      if (mvType === 'Acqua') dmg = Math.floor(dmg * 1.5);
      if (mvType === 'Fuoco') dmg = fuocoBloccato ? 0 : Math.floor(dmg * 0.5);
    }

    // Terrain — il boost dipende SOLO dal tipo della mossa, non dalla categoria.
    // Prima ogni terreno era legato a una categoria (elettrico e psichico alle
    // speciali, erboso alle fisiche): Wild Charge in terreno elettrico, Energy Ball
    // in quello erboso e Psychic Fangs in quello psichico non prendevano nulla.
    if (terrain === 'electric' && mvType === 'Elettro') dmg = Math.floor(dmg * 1.3);
    if (terrain === 'grassy'   && mvType === 'Erba')    dmg = Math.floor(dmg * 1.3);
    if (terrain === 'psychic'  && mvType === 'Psico')   dmg = Math.floor(dmg * 1.3);
    if (terrain === 'misty'    && mvType === 'Drago')   dmg = Math.floor(dmg * 0.5);

    // Critico
    if (crit) dmg = Math.floor(dmg * 1.5);

    // Schermi: il critico li ignora. Valore da doppie (2732/4096), non ×0.5:
    // il VGC si gioca solo in doppie, dove gli schermi tagliano meno.
    if (reflect && cat === 'physical' && !crit) dmg = Math.floor(dmg * SCHERMO_DOPPIE);
    if (lscreen && cat === 'special'  && !crit) dmg = Math.floor(dmg * SCHERMO_DOPPIE);

    // Abilità ATK + DEF: tutti i moltiplicatori vengono da abilityDmgMult, che e'
    // calcolato una volta sola fuori dal ciclo leggendo gli `effect` di abilities.json.
    if (abilityDmgMult !== 1.0) dmg = Math.floor(dmg * abilityDmgMult);

    // Helping Hand
    if (hh) dmg = Math.floor(dmg * 1.5);

    // Spread
    dmg = Math.floor(dmg * spread);

    // Roll + STAB + TypeEff
    dmg = Math.floor(dmg * (85 + i) / 100);
    dmg = Math.floor(dmg * stab * typeEff);

    return dmg;
  });

  // ── Output ───────────────────────────────────────────────────────────────────
  const minD = rolls[0], maxD = rolls[15];
  const minP = (minD / HP * 100).toFixed(1);
  const maxP = (maxD / HP * 100).toFixed(1);
  const ohko   = rolls.filter(r => r >= HP).length;
  const twohko = rolls.filter(r => r * 2 >= HP).length;
  const avgP   = (parseFloat(minP) + parseFloat(maxP)) / 2;

  const aN2 = document.getElementById('atk_name').value || 'Atk';
  const dN2 = document.getElementById('def_name').value || 'Def';
  const mv  = document.getElementById('mv_name').value  || 'Mossa';
  const teraTag  = atkTera ? ` [Tera ${atkTera}]` : '';
  const abilTag  = atkAbilityName ? ` (${atkAbilityName})` : '';
  const stabLabel = stab > 1 ? ` +STAB(${stab}×)` : '';
  let effLabel = '';
  if      (typeEff >= 4)    effLabel = ' ✕4 (super)';
  else if (typeEff >= 2)    effLabel = ' ✕2 (super)';
  else if (typeEff <= 0.25) effLabel = ' ✕0.25 (poco)';
  else if (typeEff <= 0.5)  effLabel = ' ✕0.5 (poco)';

  document.getElementById('dmg_line').textContent = `${aN2}${teraTag}${abilTag} → ${mv} → ${dN2} HP ${HP}`;
  document.getElementById('dmg_pct').textContent  = `${minP} ~ ${maxP}${effLabel}${stabLabel}`;
  document.getElementById('dmg_bar').style.width  = Math.min(avgP, 100) + '%';
  document.getElementById('dmg_min').textContent  = `${minD} (${minP}%)`;
  document.getElementById('dmg_max').textContent  = `${maxD} (${maxP}%)`;
  document.getElementById('dmg_ohko').innerHTML   = ohko > 0
    ? `<span style="color:var(--error,#c33)">${(ohko/16*100).toFixed(0)}%</span>` : '0%';
  document.getElementById('dmg_2hko').innerHTML   = twohko > 0
    ? `<span style="color:var(--warning,#b96)">${(twohko/16*100).toFixed(0)}%</span>` : '0%';
  document.getElementById('dmg_rolls').textContent = 'Rolls: ' + rolls.join(', ');
  document.getElementById('dmg_result').style.display = 'block';
  const _trNote = document.getElementById('trick_room_note');
  if (_trNote) _trNote.style.display = trickroom ? 'block' : 'none';
}
