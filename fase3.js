"use strict";
const DATA={base:"data/fase3/punten_tot_fase2.csv",predictions:"data/fase3/voorspellingen_fase3.csv",results:"data/fase3/uitslagen_fase3.csv"};
const ROUND_INFO={r16:{label:"Achtste finales",result:4,exact:6},qf:{label:"Kwartfinales",result:5,exact:8,reducedResult:2,reducedExact:4},sf:{label:"Halve finales",result:6,exact:10,reducedResult:3,reducedExact:5},f:{label:"Finale",result:8,exact:12}};
const state={participants:[],predictions:[],results:new Map(),resultRows:[],next:null,selected:null,tab:"r16"};
const $=s=>document.querySelector(s);
const el={status:$("#load-status"),error:$("#error-panel"),count:$("#participant-count"),completed:$("#completed-matches"),available:$("#available-points"),next:$("#next-open-match"),nextRound:$("#next-open-round"),updated:$("#last-updated"),body:$("#ranking-body"),search:$("#search-input"),empty:$("#empty-search"),section:$("#participant-section"),title:$("#participant-title"),summary:$("#participant-summary"),route:$("#route-summary"),tabs:$("#round-tabs"),content:$("#round-content"),close:$("#close-details")};
function norm(v){return String(v??"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}
function esc(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;")}
function num(v){const n=Number(v);return Number.isFinite(n)?n:0}
function csv(text){const rows=[];let r=[],f="",q=false;for(let i=0;i<text.replace(/^\uFEFF/,"").length;i++){const s=text.replace(/^\uFEFF/,""),c=s[i],n=s[i+1];if(q){if(c=='"'&&n=='"'){f+='"';i++}else if(c=='"')q=false;else f+=c}else if(c=='"')q=true;else if(c==","){r.push(f);f=""}else if(c=="\n"){r.push(f.replace(/\r$/,""));if(r.some(Boolean))rows.push(r);r=[];f=""}else f+=c}if(f||r.length){r.push(f);rows.push(r)}if(!rows.length)return[];const h=rows[0].map(x=>x.trim());return rows.slice(1).map(v=>Object.fromEntries(h.map((x,i)=>[x,(v[i]??"").trim()])))}
async function load(p){const r=await fetch(`${p}?v=${Date.now()}`,{cache:"no-store"});if(!r.ok)throw Error(`${p} kon niet worden geladen (${r.status}).`);return csv(await r.text())}
function key(r){return `${r.ronde}|${r.wedstrijd}`}
function outcome(h,a){return h>a?"home":a>h?"away":"draw"}
function sameTeams(p,a){return new Set([norm(p.thuis),norm(p.uit)]).size===2&&new Set([norm(p.thuis),norm(p.uit)]).size===new Set([norm(a.thuis),norm(a.uit)]).size&&[norm(p.thuis),norm(p.uit)].every(x=>[norm(a.thuis),norm(a.uit)].includes(x))}
function score(p,a){if(!a||a.werkelijk_thuis===""||a.werkelijk_uit===""||p.voorspeld_thuis===""||p.voorspeld_uit==="")return{points:0,processed:!!a,exact:false,teams:false};const ph=num(p.voorspeld_thuis),pa=num(p.voorspeld_uit),ah=num(a.werkelijk_thuis),aa=num(a.werkelijk_uit);const exact=ph===ah&&pa===aa,correct=outcome(ph,pa)===outcome(ah,aa),teams=sameTeams(p,a),info=ROUND_INFO[p.ronde];if(p.ronde==="f"&&!teams)return{points:0,processed:true,exact:false,teams};if(p.ronde==="qf"||p.ronde==="sf"){return{points:exact?(teams?info.exact:info.reducedExact):correct?(teams?info.result:info.reducedResult):0,processed:true,exact,teams}}return{points:exact?info.exact:correct?info.result:0,processed:true,exact,teams}}
function winner(p){if(!p)return"";if(p.voorspeld_thuis===""||p.voorspeld_uit==="")return p.winnaar||"";const h=num(p.voorspeld_thuis),a=num(p.voorspeld_uit);return h>a?p.thuis:a>h?p.uit:p.winnaar||"Gelijk"}
function build(base,preds,results){state.predictions=preds;state.resultRows=results;state.results=new Map(results.map(r=>[key(r),r]));state.next=results.find(r=>r.werkelijk_thuis===""||r.werkelijk_uit==="")??null;const by=new Map();for(const p of preds){const k=norm(p.naam);if(!by.has(k))by.set(k,[]);by.get(k).push(p)}state.participants=base.map(b=>{const ps=by.get(norm(b.naam))??[];let p3=0;for(const p of ps)p3+=score(p,state.results.get(key(p))).points;return{name:b.naam,base:num(b.punten_tot_fase2),p3,total:num(b.punten_tot_fase2)+p3,preds:ps}}).sort((a,b)=>b.total-a.total||b.p3-a.p3||a.name.localeCompare(b.name,"nl"))}
function nextPick(x){if(!state.next)return"Alles verwerkt";const p=x.preds.find(y=>key(y)===key(state.next));return p?`${esc(p.thuis)} ${p.voorspeld_thuis}–${p.voorspeld_uit} ${esc(p.uit)}`:"Geen formulier"}
function renderRanking(filter=""){const q=norm(filter);const rows=state.participants.filter(x=>norm(x.name).includes(q));el.empty.hidden=rows.length>0;el.body.innerHTML=rows.map((x,i)=>`<tr><td><span class="rank-badge${i<3?` rank-badge--${i+1}`:""}">${i+1}</span></td><td><button class="name-button" data-name="${esc(x.name)}">${esc(x.name)}</button></td><td>${x.base}</td><td>${x.p3}</td><td><span class="next-pick"><strong>${nextPick(x)}</strong></span></td><td><strong>${x.total}</strong></td><td><button class="detail-button" data-name="${esc(x.name)}">›</button></td></tr>`).join("");el.body.querySelectorAll("[data-name]").forEach(b=>b.onclick=()=>openParticipant(b.dataset.name))}
const BRACKET={
  "qf|1":[["r16","B"],["r16","A"]],
  "qf|2":[["r16","E"],["r16","F"]],
  "qf|3":[["r16","C"],["r16","D"]],
  "qf|4":[["r16","G"],["r16","H"]],
  "sf|X":[["qf","1"],["qf","2"]],
  "sf|Y":[["qf","3"],["qf","4"]],
  "f|F":[["sf","X"],["sf","Y"]],
};

function predictedWinner(match){
  if(!match)return "";
  const home=String(match.thuis??"").trim();
  const away=String(match.uit??"").trim();
  const homeText=String(match.voorspeld_thuis??"").trim();
  const awayText=String(match.voorspeld_uit??"").trim();

  if(homeText!==""&&awayText!==""){
    const homeScore=Number(homeText);
    const awayScore=Number(awayText);
    if(homeScore>awayScore)return home;
    if(awayScore>homeScore)return away;
  }

  const winner=String(match.winnaar??"").trim();
  if(winner&&!norm(winner).startsWith("winnaar "))return winner;
  return "";
}

function resolvedPredictions(participant){
  const byKey=new Map(
    participant.preds.map(match=>[
      `${match.ronde}|${match.wedstrijd}`,
      {...match},
    ])
  );

  for(const round of ["qf","sf","f"]){
    for(const match of [...byKey.values()].filter(item=>item.ronde===round)){
      const sources=BRACKET[`${match.ronde}|${match.wedstrijd}`];
      if(!sources)continue;

      const sourceHome=byKey.get(`${sources[0][0]}|${sources[0][1]}`);
      const sourceAway=byKey.get(`${sources[1][0]}|${sources[1][1]}`);

      const homeWinner=predictedWinner(sourceHome);
      const awayWinner=predictedWinner(sourceAway);

      if(
        !String(match.thuis??"").trim()||
        norm(match.thuis).startsWith("winnaar ")
      ){
        match.thuis=homeWinner||match.thuis;
      }

      if(
        !String(match.uit??"").trim()||
        norm(match.uit).startsWith("winnaar ")
      ){
        match.uit=awayWinner||match.uit;
      }

      byKey.set(`${match.ronde}|${match.wedstrijd}`,match);
    }
  }

  return [...byKey.values()];
}

function routeCards(p){
  const resolved=resolvedPredictions(p);

  const qf=resolved
    .filter(x=>x.ronde==="qf")
    .flatMap(x=>[x.thuis,x.uit])
    .filter(x=>x&&!norm(x).startsWith("winnaar "));

  const sf=resolved
    .filter(x=>x.ronde==="sf")
    .flatMap(x=>[x.thuis,x.uit])
    .filter(x=>x&&!norm(x).startsWith("winnaar "));

  const finalMatch=resolved.find(x=>x.ronde==="f");

  return[
    {
      label:"Voorspelde kwartfinalisten",
      value:[...new Set(qf)].join(", ")||"–",
    },
    {
      label:"Voorspelde halvefinalisten",
      value:[...new Set(sf)].join(", ")||"–",
    },
    {
      label:"Voorspelde finale",
      value:finalMatch
        ?`${finalMatch.thuis||"–"} – ${finalMatch.uit||"–"}`
        :"–",
    },
  ];
}
function renderParticipant(){const p=state.selected;if(!p)return;el.route.innerHTML=routeCards(p).map(x=>`<article class="route-card"><span>${x.label}</span><strong>${esc(x.value)}</strong></article>`).join("");el.tabs.innerHTML=Object.entries(ROUND_INFO).map(([id,x])=>`<button class="round-tab${state.tab===id?" is-active":""}" data-round="${id}">${x.label}</button>`).join("");el.tabs.querySelectorAll("[data-round]").forEach(b=>b.onclick=()=>{state.tab=b.dataset.round;renderParticipant()});const rows=resolvedPredictions(p).filter(x=>x.ronde===state.tab);el.content.innerHTML=`<div class="round-grid">${rows.map(x=>{const a=state.results.get(key(x));const s=score(x,a);const isNext=state.next&&key(x)===key(state.next);return`<article class="round-match${isNext?" is-next":""}"><div class="round-match__head"><strong>${ROUND_INFO[x.ronde].label} ${esc(x.wedstrijd)}</strong><span>${s.processed?`${s.points} punten`:"Nog open"}</span></div><div class="round-match__body"><div class="round-team"><span>${esc(x.thuis)}</span><span class="prediction">${esc(x.voorspeld_thuis)}</span><span class="actual">${a?.werkelijk_thuis??"–"}</span></div><div class="round-team"><span>${esc(x.uit)}</span><span class="prediction">${esc(x.voorspeld_uit)}</span><span class="actual">${a?.werkelijk_uit??"–"}</span></div><span class="team-status${s.teams?" is-correct":""}">${s.teams?"Juiste landen":"Voorspelde landen"}</span></div></article>`}).join("")}</div>`}
function openParticipant(name){state.selected=state.participants.find(x=>x.name===name);if(!state.selected)return;el.title.textContent=state.selected.name;el.summary.textContent=`${state.selected.base} punten tot fase 2 · ${state.selected.p3} punten in fase 3 · ${state.selected.total} totaal`;state.tab="r16";renderParticipant();el.section.hidden=false;el.section.scrollIntoView({behavior:"smooth"})}
async function commitDate(){try{const r=await fetch(`https://api.github.com/repos/RSlanjouw/wk_2026/commits/main?t=${Date.now()}`,{cache:"no-store"});if(!r.ok)throw Error();const c=await r.json();el.updated.textContent=new Date(c.commit.committer.date).toLocaleString("nl-NL",{dateStyle:"medium",timeStyle:"short"})}catch{el.updated.textContent="Niet beschikbaar"}}
async function init(){try{const [b,p,r]=await Promise.all([load(DATA.base),load(DATA.predictions),load(DATA.results)]);build(b,p,r);el.count.textContent=state.participants.length;el.completed.textContent=r.filter(x=>x.werkelijk_thuis!==""&&x.werkelijk_uit!=="").length;el.available.textContent=r.reduce((sum,x)=>sum+(x.werkelijk_thuis!==""&&x.werkelijk_uit!==""?(ROUND_INFO[x.ronde].exact):0),0);el.next.textContent=state.next?`${state.next.thuis||"Nog te bepalen"} – ${state.next.uit||"Nog te bepalen"}`:"Alles verwerkt";el.nextRound.textContent=state.next?`${ROUND_INFO[state.next.ronde].label} ${state.next.wedstrijd}`:"";renderRanking();await commitDate();el.status.textContent="Stand is actueel"}catch(e){console.error(e);el.error.hidden=false;el.error.textContent=`De stand kon niet worden geladen. ${e.message}`;el.status.textContent="Laden mislukt"}}
el.search.oninput=e=>renderRanking(e.target.value);el.close.onclick=()=>el.section.hidden=true;init();
