// calcolatori-data.js — dati e stato globale del calcolatore VGC.
// PRIMO file da caricare: tutti gli altri leggono le costanti dichiarate qui.
//
// I dati che vengono da Flask non possono stare in un file statico: arrivano nel
// blocco <script type="application/json" id="calc-bootstrap"> del template, con
// lo stesso schema che items_editor.html usa per `items-data`.
const CALC_BOOTSTRAP = JSON.parse(document.getElementById('calc-bootstrap').textContent);

let MOVES_DB            = CALC_BOOTSTRAP.moves;       // moves_data.moves
const ABILITIES_DATA    = CALC_BOOTSTRAP.abilities;   // data/abilities.json, 408 voci
const REG_ID            = CALC_BOOTSTRAP.reg_id;      // current_reg.id
const CHAMPIONS_BST     = CALC_BOOTSTRAP.champions;   // pokemon_catalog.json, 174 voci
const NATURES           = CALC_BOOTSTRAP.natures;     // NATURES di data.py, 25 in ordine

const TYPE_EN_TO_IT = {
  "normal":"Normale","fire":"Fuoco","water":"Acqua","electric":"Elettro",
  "grass":"Erba","ice":"Ghiaccio","fighting":"Lotta","poison":"Veleno",
  "ground":"Terra","flying":"Volante","psychic":"Psico","bug":"Coleottero",
  "rock":"Roccia","ghost":"Spettro","dragon":"Drago","dark":"Buio",
  "steel":"Acciaio","fairy":"Folletto"
};
const NM={
  "Lonely":{atk:1.1,def:0.9},"Brave":{atk:1.1,spe:0.9},"Adamant":{atk:1.1,spa:0.9},"Naughty":{atk:1.1,spd:0.9},
  "Bold":{def:1.1,atk:0.9},"Relaxed":{def:1.1,spe:0.9},"Impish":{def:1.1,spa:0.9},"Lax":{def:1.1,spd:0.9},
  "Timid":{spe:1.1,atk:0.9},"Hasty":{spe:1.1,def:0.9},"Jolly":{spe:1.1,spa:0.9},"Naive":{spe:1.1,spd:0.9},
  "Modest":{spa:1.1,atk:0.9},"Mild":{spa:1.1,def:0.9},"Quiet":{spa:1.1,spe:0.9},"Rash":{spa:1.1,spd:0.9},
  "Calm":{spd:1.1,atk:0.9},"Gentle":{spd:1.1,def:0.9},"Sassy":{spd:1.1,spe:0.9},"Careful":{spd:1.1,spa:0.9},
};
// I 18 tipi nell'ordine canonico. Le tabelle di riferimento usano `nome.slice(0,4)`
// come abbreviazione, quindi l'ordine qui e' anche l'ordine di righe e colonne.
const TIPI_IT = ['Normale','Fuoco','Acqua','Elettro','Erba','Ghiaccio','Lotta','Veleno',
  'Terra','Volante','Psico','Coleottero','Roccia','Spettro','Drago','Buio','Acciaio','Folletto'];

// Palette della tabella di riferimento, con i nomi in italiano. NON e' TYPE_CLR:
// quella e' indicizzata sui nomi inglesi e usa tinte diverse (serve ai badge mossa).
const TYPE_CLR_IT = {
  Normale:"#9099A1", Fuoco:"#FF9741", Acqua:"#3692DC", Elettro:"#FBD100",
  Erba:"#38BF4B", Ghiaccio:"#70CBD4", Lotta:"#E0306A", Veleno:"#B567CE",
  Terra:"#E87236", Volante:"#89AAE3", Psico:"#FF6675", Coleottero:"#83C300",
  Roccia:"#C8B686", Spettro:"#4C6AB2", Drago:"#006FC9", Buio:"#5B5465",
  Acciaio:"#5A8EA2", Folletto:"#FB89EB"
};

// Reflect e Light Screen in doppie. In singole taglierebbero a metà, ma il VGC si
// gioca solo in doppie e i giochi usano 2732/4096. Se un giorno servisse il
// calcolo in singole, questo è l'unico punto da cambiare.
const SCHERMO_DOPPIE = 2732 / 4096;

// Type chart Gen 9 — unica copia. La legge sia calcDamage() per l'efficacia, sia
// renderTypeChart() per disegnare la tabella di riferimento: prima la tabella era
// 46 KB di HTML incollato a mano, indipendente da questa, e duplicato due volte.
const TYPE_CHART = {
  Normale:    {Roccia:0.5,Acciaio:0.5,Spettro:0},
  Fuoco:      {Fuoco:0.5,Acqua:0.5,Roccia:0.5,Drago:0.5,Erba:2,Ghiaccio:2,Coleottero:2,Acciaio:2},
  Acqua:      {Acqua:0.5,Erba:0.5,Drago:0.5,Fuoco:2,Terra:2,Roccia:2},
  Elettro:    {Elettro:0.5,Erba:0.5,Drago:0.5,Terra:0,Acqua:2,Volante:2},
  Erba:       {Fuoco:0.5,Erba:0.5,Veleno:0.5,Volante:0.5,Coleottero:0.5,Drago:0.5,Acciaio:0.5,Acqua:2,Terra:2,Roccia:2},
  Ghiaccio:   {Acqua:0.5,Erba:2,Terra:2,Volante:2,Drago:2,Acciaio:0.5,Ghiaccio:0.5},
  Lotta:      {Normale:2,Ghiaccio:2,Roccia:2,Buio:2,Acciaio:2,Veleno:0.5,Coleottero:0.5,Psico:0.5,Volante:0.5,Spettro:0,Folletto:0.5},
  Veleno:     {Erba:2,Folletto:2,Veleno:0.5,Terra:0.5,Roccia:0.5,Spettro:0.5,Acciaio:0},
  Terra:      {Fuoco:2,Elettro:2,Veleno:2,Roccia:2,Acciaio:2,Erba:0.5,Coleottero:0.5,Volante:0},
  Volante:    {Erba:2,Lotta:2,Coleottero:2,Elettro:0.5,Roccia:0.5,Acciaio:0.5},
  Psico:      {Lotta:2,Veleno:2,Psico:0.5,Acciaio:0.5,Buio:0},
  Coleottero: {Erba:2,Psico:2,Buio:2,Fuoco:0.5,Lotta:0.5,Volante:0.5,Spettro:0.5,Acciaio:0.5,Folletto:0.5},
  Roccia:     {Fuoco:2,Ghiaccio:2,Volante:2,Coleottero:2,Lotta:0.5,Terra:0.5,Acciaio:0.5},
  Spettro:    {Spettro:2,Psico:2,Normale:0,Buio:0.5},
  Drago:      {Drago:2,Acciaio:0.5,Folletto:0},
  Buio:       {Spettro:2,Psico:2,Lotta:0.5,Buio:0.5,Folletto:0.5},
  Acciaio:    {Ghiaccio:2,Roccia:2,Folletto:2,Fuoco:0.5,Acqua:0.5,Elettro:0.5,Acciaio:0.5},
  Folletto:   {Lotta:2,Drago:2,Buio:2,Fuoco:0.5,Veleno:0.5,Acciaio:0.5}
};

const TYPE_CLR={fire:"#E8622C",water:"#6390F0",grass:"#7AC74C",electric:"#F7D02C",ice:"#96D9D6",
  fighting:"#C22E28",poison:"#A33EA1",ground:"#E2BF65",flying:"#A98FF3",psychic:"#F95587",
  bug:"#A6B91A",rock:"#B6A136",ghost:"#735797",dragon:"#6F35FC",dark:"#705746",
  steel:"#B7B7CE",fairy:"#D685AD",normal:"#A8A77A"};
const SC={hp:"#FF5959",atk:"#F5AC78",def:"#FAE078",spa:"#9DB7F5",spd:"#A7DB8D",spe:"#FA92B2"};
const SM={hp:255,atk:165,def:230,spa:175,spd:230,spe:180};
const STAT_KEYS=['hp','atk','def','spa','spd','spe'];
const STAT_LBLS=['HP','ATK','DEF','SpA','SpD','SPE'];
const pkCache={};
let BS={atk:{},def:{},stat:{}};
let mySpeed=0;
let TEAM_DATA=[];
let SPEED_META=[];

const SPEED_META_STATIC=[{"name": "Regieleki", "base": 200}, {"name": "Deoxys-Speed", "base": 180}, {"name": "Ninjask", "base": 160}, {"name": "Pheromosa", "base": 151}, {"name": "Electrode", "base": 150}, {"name": "Calyrex-Shadow", "base": 150}, {"name": "Zacian", "base": 148}, {"name": "Accelgor", "base": 145}, {"name": "Dragapult", "base": 142}, {"name": "Barraskewda", "base": 136}, {"name": "Iron Bundle", "base": 136}, {"name": "Miraidon", "base": 135}, {"name": "Flutter Mane", "base": 135}, {"name": "Chien-Pao", "base": 135}, {"name": "Koraidon", "base": 135}, {"name": "Jolteon", "base": 130}, {"name": "Crobat", "base": 130}, {"name": "Spectrier", "base": 130}, {"name": "Mewtwo", "base": 130}, {"name": "Shaymin-Sky", "base": 127}, {"name": "Talonflame", "base": 126}, {"name": "Weavile", "base": 125}, {"name": "Darkrai", "base": 125}, {"name": "Ribombee", "base": 124}, {"name": "Meowscarada", "base": 123}, {"name": "Noivern", "base": 123}, {"name": "Greninja", "base": 122}, {"name": "Tornadus-Therian", "base": 121}, {"name": "Inteleon", "base": 120}, {"name": "Arceus", "base": 120}, {"name": "Roaring Moon", "base": 119}, {"name": "Cinderace", "base": 119}, {"name": "Hawlucha", "base": 118}, {"name": "Iron Valiant", "base": 116}, {"name": "Sandy Shocks", "base": 116}, {"name": "Iron Treads", "base": 116}, {"name": "Whimsicott", "base": 116}, {"name": "Raikou", "base": 115}, {"name": "Tornadus", "base": 111}, {"name": "Thundurus", "base": 111}, {"name": "Scream Tail", "base": 111}, {"name": "Fezandipiti", "base": 111}, {"name": "Enamorus", "base": 110}, {"name": "Latios", "base": 110}, {"name": "Latias", "base": 110}, {"name": "Iron Moth", "base": 110}, {"name": "Lycanroc", "base": 110}, {"name": "Zoroark-Hisui", "base": 110}, {"name": "Espeon", "base": 110}, {"name": "Ogerpon", "base": 110}, {"name": "Ogerpon-Hearthflame", "base": 110}, {"name": "Ogerpon-Cornerstone", "base": 110}, {"name": "Ogerpon-Wellspring", "base": 110}, {"name": "Lugia", "base": 110}, {"name": "Enamorus-Therian", "base": 110}, {"name": "Walking Wake", "base": 109}, {"name": "Iron Jugulis", "base": 108}, {"name": "Keldeo", "base": 108}, {"name": "Zoroark", "base": 105}, {"name": "Gouging Fire", "base": 105}, {"name": "Garchomp", "base": 102}, {"name": "Landorus", "base": 101}, {"name": "Thundurus-Therian", "base": 101}, {"name": "Chi-Yu", "base": 100}, {"name": "Palafin", "base": 100}, {"name": "Charizard", "base": 100}, {"name": "Ninetales", "base": 100}, {"name": "Salamence", "base": 100}, {"name": "Volcarona", "base": 100}, {"name": "Flygon", "base": 100}, {"name": "Mew", "base": 100}, {"name": "Entei", "base": 100}, {"name": "Zapdos", "base": 100}, {"name": "Palkia", "base": 100}, {"name": "Shaymin", "base": 100}, {"name": "Terapagos", "base": 99}, {"name": "Genesect", "base": 99}, {"name": "Iron Crown", "base": 98}, {"name": "Urshifu", "base": 97}, {"name": "Urshifu-Rapid", "base": 97}, {"name": "Mimikyu", "base": 96}, {"name": "Arcanine", "base": 95}, {"name": "Leafeon", "base": 95}, {"name": "Gliscor", "base": 95}, {"name": "Rayquaza", "base": 95}, {"name": "Kyurem", "base": 95}, {"name": "Landorus-Therian", "base": 91}, {"name": "Archaludon", "base": 90}, {"name": "Moltres", "base": 90}, {"name": "Giratina", "base": 90}, {"name": "Giratina-Origin", "base": 90}, {"name": "Kyogre", "base": 90}, {"name": "Groudon", "base": 90}, {"name": "Ho-Oh", "base": 90}, {"name": "Dialga", "base": 90}, {"name": "Reshiram", "base": 90}, {"name": "Zekrom", "base": 90}, {"name": "Meloetta", "base": 90}, {"name": "Excadrill", "base": 88}, {"name": "Pecharunt", "base": 88}, {"name": "Baxcalibur", "base": 87}, {"name": "Great Tusk", "base": 87}, {"name": "Rotom-Wash", "base": 86}, {"name": "Rotom-Heat", "base": 86}, {"name": "Rotom-Frost", "base": 86}, {"name": "Rotom-Fan", "base": 86}, {"name": "Rotom-Mow", "base": 86}, {"name": "Glimmora", "base": 86}, {"name": "Rillaboom", "base": 85}, {"name": "Kommo-o", "base": 85}, {"name": "Suicune", "base": 85}, {"name": "Articuno", "base": 85}, {"name": "Iron Boulder", "base": 84}, {"name": "Goodra-Hisui", "base": 81}, {"name": "Dragonite", "base": 80}, {"name": "Goodra", "base": 80}, {"name": "Gardevoir", "base": 80}, {"name": "Gallade", "base": 80}, {"name": "Skeledirge", "base": 75}, {"name": "Raging Bolt", "base": 75}, {"name": "Butterfree", "base": 70}, {"name": "Decidueye", "base": 70}, {"name": "Decidueye-Hisui", "base": 70}, {"name": "Umbreon", "base": 65}, {"name": "Flareon", "base": 65}, {"name": "Vaporeon", "base": 65}, {"name": "Glaceon", "base": 65}, {"name": "Sinistcha", "base": 61}, {"name": "Grimmsnarl", "base": 60}, {"name": "Sylveon", "base": 60}, {"name": "Primarina", "base": 60}, {"name": "Incineroar", "base": 60}, {"name": "Abomasnow", "base": 60}, {"name": "Brute Bonnet", "base": 60}, {"name": "Farigiraf", "base": 52}, {"name": "Beartic", "base": 50}, {"name": "Calyrex-Ice", "base": 50}, {"name": "Iron Hands", "base": 50}, {"name": "Kingambit", "base": 50}, {"name": "Okidogi", "base": 50}, {"name": "Munkidori", "base": 50}, {"name": "Hippowdon", "base": 47}, {"name": "Conkeldurr", "base": 45}, {"name": "Ting-Lu", "base": 45}, {"name": "Wo-Chien", "base": 45}, {"name": "Hydrapple", "base": 43}, {"name": "Orthworm", "base": 40}, {"name": "Cetitan", "base": 36}, {"name": "Toxapex", "base": 35}, {"name": "Garganacl", "base": 35}, {"name": "Mudsdale", "base": 35}, {"name": "Dondozo", "base": 35}, {"name": "Bronzong", "base": 33}, {"name": "Glastrier", "base": 30}, {"name": "Amoonguss", "base": 30}, {"name": "Hatterene", "base": 29}, {"name": "Torkoal", "base": 20}, {"name": "Clodsire", "base": 20}];

// ── Champions BST & forme ─────────────────────────────────────────────────────
const ALIAS = {"Aegislash": "Aegislash (Shield Forme)", "Arcanine-Hisui": "Hisuian Arcanine", "Avalugg-Hisui": "Hisuian Avalugg", "Basculegion": "Basculegion (Male)", "Basculegion-F": "Basculegion (Female)", "Basculegion-M": "Basculegion (Male)", "Decidueye-Hisui": "Hisuian Decidueye", "Goodra-Hisui": "Hisuian Goodra", "Gourgeist": "Gourgeist (Average)", "Lycanroc-Dusk": "Lycanroc (Dusk Form)", "Lycanroc-Midday": "Lycanroc", "Lycanroc-Midnight": "Lycanroc (Midnight Form)", "Meowstic": "Meowstic (Male)", "Meowstic-F": "Meowstic (Female)", "Meowstic-M": "Meowstic (Male)", "Morpeko": "Morpeko (Full Belly Mode)", "Mr. Rime": "Mr. Rime", "Ninetales-Alola": "Alolan Ninetales", "Palafin": "Palafin (Zero Form)", "Raichu-Alola": "Alolan Raichu", "Rotom-Fan": "Fan Rotom", "Rotom-Frost": "Frost Rotom", "Rotom-Heat": "Heat Rotom", "Rotom-Mow": "Mow Rotom", "Rotom-Wash": "Wash Rotom", "Samurott-Hisui": "Hisuian Samurott", "Slowbro-Galar": "Galarian Slowbro", "Slowking-Galar": "Galarian Slowking", "Stunfisk-Galar": "Galarian Stunfisk", "Tauros-Paldea-Aqua": "Paldean Tauros (Aqua Breed)", "Tauros-Paldea-Blaze": "Paldean Tauros (Blaze Breed)", "Tauros-Paldea-Combat": "Paldean Tauros (Combat Breed)", "Typhlosion-Hisui": "Hisuian Typhlosion", "Zoroark-Hisui": "Hisuian Zoroark"};
const FORM_VARIANTS = {"Palafin": ["Palafin (Zero Form)", "Palafin (Hero Form)"], "Meowstic": ["Meowstic (Male)", "Meowstic (Female)"], "Aegislash": ["Aegislash (Shield Forme)", "Aegislash (Blade Forme)"], "Basculegion": ["Basculegion (Male)", "Basculegion (Female)"], "Gourgeist": ["Gourgeist (Average)", "Gourgeist (Small)", "Gourgeist (Large)", "Gourgeist (Super)"]};
const FORM_BASE = {"Palafin (Zero Form)": "Palafin", "Palafin (Hero Form)": "Palafin", "Meowstic (Male)": "Meowstic", "Meowstic (Female)": "Meowstic", "Aegislash (Shield Forme)": "Aegislash", "Aegislash (Blade Forme)": "Aegislash", "Basculegion (Male)": "Basculegion", "Basculegion (Female)": "Basculegion", "Gourgeist (Average)": "Gourgeist", "Gourgeist (Small)": "Gourgeist", "Gourgeist (Large)": "Gourgeist", "Gourgeist (Super)": "Gourgeist"};

// ── Motore meteo ──────────────────────────────────────────────────────────────
// Tipo di Palla Clima per meteo. E' il meteo in campo a decidere, non l'abilita':
// il campo `weather_ball_type` di abilities.json fa da override data-driven quando
// il meteo lo impone un'abilita' (finora quel campo esisteva su 7 abilita' ma
// nessuno lo leggeva).
const WEATHER_BALL_TYPE = {
  sun: 'Fuoco', harshsun: 'Fuoco',
  rain: 'Acqua', heavyrain: 'Acqua',
  sand: 'Roccia',
  snow: 'Ghiaccio', hail: 'Ghiaccio'
};

const METEO_LABEL = {
  '': 'nessuno', sun: 'Sole', harshsun: 'Sole forte', rain: 'Pioggia',
  heavyrain: 'Pioggia forte', sand: 'Sabbia', snow: 'Neve', hail: 'Grandine', fog: 'Nebbia'
};

// Mosse la cui potenza o il cui tipo dipendono dal meteo.
const MOSSE_METEO = {
  'Weather Ball': { bpBase: 50,  bpConMeteo: 100, tipoDalMeteo: true },
  'Solar Beam':   { bpBase: 120, dimezzaCon: ['rain','heavyrain','sand','snow','hail'] },
  'Solar Blade':  { bpBase: 125, dimezzaCon: ['rain','heavyrain','sand','snow','hail'] }
};

// MEGA_DATA è stato eliminato l'11/08/2026: era la terza copia delle stat, e le
// Mega sono ora nel catalogo come ogni altra forma (data/catalog/pokemon.json).
// fetchPkmn() le prende da /api/pokemon, quindi tabella Danno e Speed Tier
// leggono le stesse base — prima il Danno usava MEGA_DATA e lo Speed Tier il
// catalogo, e sulle Mega la formula Lv.50 finiva applicata due volte.


// ── EV LIMIT HELPERS (max 66 totali, max 32 per campo) ──────────────────────
const EV_TOTAL_MAX = 66;
const EV_FIELD_MAX = 32;
