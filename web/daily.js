// The Daily Chart (game/daily.py): one stock with no name, two minutes, the same chart for everyone today. The page asks
// the server for the candles shown so far once a second; the ones still to come never reach the browser. Loaded by
// index.html after its own script, so it shares its globals (S, page, api, postJson, refreshers...).
let dly=null,dlyG=null,dlyT=null,dlyBusy=false;
async function loadDaily(){
 if(guest){setHtml($('daily-body'),'<p class="mut">Sign in to play.</p>');return}
 const d=await api('/api/daily');if(!d||d.error||d.slow)return;
 dly=d;dlyG=d.game?Object.assign({},d.game):null;drawDaily();if(d.status==='running')dlyRun()}
refreshers.daily=()=>{if(!dly||dly.status!=='running')loadDaily()};
function dlyRun(){if(!dlyT)dlyT=setInterval(dlyPoll,1000)}
function dlyStop(){clearInterval(dlyT);dlyT=null}
async function dlyPoll(){
 if(!dlyG){dlyStop();return}if(dlyBusy)return;dlyBusy=true;               // (a hidden tab keeps polling: the game must reach its end)
 const r=await api('/api/daily/state?since='+dlyG.shown);dlyBusy=false;if(!r||r.error||r.slow)return;
 dlyMerge(r);if(r.done){dlyStop();loadDaily()}else drawDaily()}
function dlyMerge(r){dlyG=Object.assign(dlyG||{},r,{candles:(dlyG&&dlyG.candles||[]).slice(0,r.from).concat(r.candles)})}
const dlyClock=s=>{s=Math.ceil(Math.max(0,s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
const dlyPx=v=>numText(v,v<1?4:2);
const dlyPlace=n=>n+(n%100>=11&&n%100<=13?'th':['th','st','nd','rd'][n%10]||'th');
function dlySvg(g){
 const cs=g.candles,total=g.history+g.live,W=PHONE?380:900,H=PHONE?280:360,R=PHONE?52:64,top=8,volH=H*0.16,ph=H-volH-26;
 const lo=Math.min(...cs.map(c=>c[2]),...g.trades.map(t=>t[2])),hi=Math.max(...cs.map(c=>c[1]),...g.trades.map(t=>t[2])),pad=(hi-lo||hi*0.01)*0.08;
 const a=lo-pad,b=hi+pad,y=v=>top+(b-v)/(b-a)*ph,sw=(W-R)/total,bw=Math.max(1,sw*0.68),vx=Math.max(...cs.map(c=>c[4]),1);
 let h=`<rect x="0" y="0" width="${(g.history*sw).toFixed(1)}" height="${H}" fill="#ffffff06"/>`
  +`<line x1="${(g.history*sw).toFixed(1)}" x2="${(g.history*sw).toFixed(1)}" y1="0" y2="${H-18}" stroke="var(--line)" stroke-dasharray="3 3"/>`
  +`<text x="4" y="${H-6}" fill="var(--mut)" font-size="11">lead-in</text><text x="${(g.history*sw+4).toFixed(0)}" y="${H-6}" fill="var(--mut)" font-size="11">your two minutes</text>`;
 const lastY=y(cs[cs.length-1][3]);
 for(let k=0;k<4;k++){const v=a+(b-a)*(k+0.5)/4;h+=`<line x1="0" x2="${W-R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="#ffffff0c"/>`+(Math.abs(y(v)-lastY)<14?'':`<text x="${W-R+4}" y="${(y(v)+4).toFixed(0)}" fill="var(--mut)" font-size="11">${dlyPx(v)}</text>`)}
 cs.forEach((c,i)=>{const x=i*sw+sw/2,up=c[3]>=c[0],col=up?'var(--up)':'var(--dn)',o=i<g.history?' opacity="0.55"':'';
  h+=`<g${o}><line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${y(c[1]).toFixed(1)}" y2="${y(c[2]).toFixed(1)}" stroke="${col}"/>`
   +`<rect x="${(x-bw/2).toFixed(1)}" y="${y(Math.max(c[0],c[3])).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1,Math.abs(y(c[0])-y(c[3]))).toFixed(1)}" fill="${col}"/>`
   +`<rect x="${(x-bw/2).toFixed(1)}" y="${(H-20-c[4]/vx*volH).toFixed(1)}" width="${bw.toFixed(1)}" height="${(c[4]/vx*volH).toFixed(1)}" fill="${col}" opacity="0.35"/></g>`});
 for(const t of g.trades){const x=t[0]*sw+sw/2,buy=t[1]==='buy',c=cs[t[0]]||[0,t[2],t[2]],yy=buy?y(c[2])+12:y(c[1])-12;
  h+=`<path d="M${x.toFixed(1)} ${(buy?yy-7:yy+7).toFixed(1)} l-5 ${buy?9:-9} h10 z" fill="${buy?'var(--up)':'var(--dn)'}"><title>${buy?'Bought':'Sold'} at ${dlyPx(t[2])}</title></path>`}
 const last=cs[cs.length-1][3];
 h+=`<line x1="0" x2="${W-R}" y1="${y(last).toFixed(1)}" y2="${y(last).toFixed(1)}" stroke="var(--acc)" stroke-dasharray="2 3"/><rect x="${W-R+1}" y="${(y(last)-9).toFixed(0)}" width="${R-2}" height="18" fill="var(--acc)"/><text x="${W-R+4}" y="${(y(last)+4).toFixed(0)}" fill="#021012" font-size="11" font-weight="700">${dlyPx(last)}</text>`;
 return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="Today's chart">${h}</svg>`}
function dlyBoard(d){
 const me=S&&S.name;
 return `<h3 class="sp">Today's board <span class="mut">(${numText(d.players,0)} finished)</span></h3>`
  +(d.board.length?`<table class="dly-board"><thead><tr><th>#</th><th>Player</th><th>Return</th><th>Trades</th></tr></thead><tbody>${d.board.map((x,i)=>`<tr class="${x.name===me?'me':''}"><td>${i+1}</td><td><a href="/player/${encodeURIComponent(x.name)}">${esc(x.name)}</a></td><td class="${clsP(x.ret)}">${pc(x.ret)}</td><td>${x.trades}</td></tr>`).join('')}</tbody></table>`:'<p class="mut">Nobody has finished today\'s chart yet.</p>')
  +(d.past.length?`<h3 class="sp">The last days</h3><table class="dly-board"><thead><tr><th>Day</th><th>Winner</th><th>Return</th><th>Players</th></tr></thead><tbody>${d.past.map(p=>`<tr><td>${new Date(p.day*86400000).toLocaleDateString(undefined,{day:'numeric',month:'short',timeZone:'UTC'})}</td><td>${p.top[0]?esc(p.top[0].name):'-'}</td><td class="${p.top[0]?clsP(p.top[0].ret):''}">${p.top[0]?pc(p.top[0].ret):'-'}</td><td>${p.players}</td></tr>`).join('')}</tbody></table>`:'')}
function drawDaily(){
 const el=$('daily-body'),d=dly;if(!el||!d)return;
 const st=d.status==='running'&&dlyG&&dlyG.done?'done':d.status;
 if(el._st!==st){el._st=st;
  if(st==='new')setHtml(el,`<p>One stock with no name, two minutes, and the same chart for everyone today. You get <b>1,000 MB</b> of practice money (not your real MB). Press <b>Start</b>: a minute of the chart's past appears, then a new one-second candle every second for two minutes. Buy with 25, 50, 75 or 100% of your cash, sell 25, 50, 75 or 100% of your shares, at the latest price, with no fees. Whatever you hold at the end is valued at the last price. Read the levels in the lead-in: the stock respects support and resistance like the real market does. <b>One go a day</b>; the best returns top the board.</p>
   <p><button class="buy dly-start" id="dly-start">Start</button></p><div id="dly-board"></div>`);
  else if(st==='running')setHtml(el,`<div id="dly-stats" class="dly-stats"></div><div id="dly-chart" class="dly-chart"></div>
   <div class="dly-acts"><div class="bar"><span class="lab">Buy</span>${[25,50,75,100].map(p=>`<button class="buy" data-dly="buy" data-p="${p/100}">${p}%</button>`).join('')}</div>
   <div class="bar"><span class="lab">Sell</span>${[25,50,75,100].map(p=>`<button class="sell" data-dly="sell" data-p="${p/100}">${p}%</button>`).join('')}</div></div><div id="dly-board"></div>`);
  else setHtml(el,`<div id="dly-result" class="dly-result"></div><div id="dly-chart" class="dly-chart"></div><p class="hint" id="dly-next"></p><div id="dly-board"></div>`)}
 const g=dlyG;
 if(st!=='new'&&g&&g.candles&&g.candles.length){
  setHtml($('dly-chart'),dlySvg(g));
  const eq=g.equity,ret=eq/d.cash-1;
  if(st==='running')setHtml($('dly-stats'),[['Time left',`<b class="dly-clock">${dlyClock(g.left)}</b>`],['Price',dlyPx(g.price)],['Cash',numText(g.cash)+' MB'],['Shares',numText(g.shares,g.shares<10?4:2)+` <span class="mut">(${numText(g.shares*g.price)} MB)</span>`],['Total',numText(eq)+' MB'],['Return',`<span class="${clsP(ret)}">${pc(ret)}</span>`]].map(([l,v])=>`<div><small>${l}</small><strong>${v}</strong></div>`).join(''));
  else{setHtml($('dly-result'),`<div><small>Your result</small><strong class="${clsP(g.ret)}">${pc(g.ret)}</strong></div><div><small>You finished with</small><strong>${numText(d.cash*(1+g.ret))} MB</strong></div><div><small>Your place</small><strong>${g.rank?dlyPlace(g.rank)+' of '+numText(g.of,0):'-'}</strong></div><div><small>Trades</small><strong>${g.trades.length}</strong></div>`);
   const left=Math.max(0,d.next-engineNow()),hrs=Math.floor(left/3600),mins=Math.floor(left%3600/60);
   setHtml($('dly-next'),`A new chart in ${hrs?hrs+' h ':''}${mins} min (at midnight UTC). The whole chart is shown now, with your buys (green) and sells (red).`)}}
 setHtml($('dly-board'),dlyBoard(d))}
document.addEventListener('click',async e=>{
 if(e.target.id==='dly-start'){e.target.disabled=true;const r=await postJson('/api/daily/start',{},{'X-Token':token||''});e.target.disabled=false;
  if(r.error){toast(r.error,false,4000);loadDaily();return}dly.status='running';dlyG=r;drawDaily();dlyRun();return}
 const b=e.target.closest('[data-dly]');if(!b||!dlyG)return;
 const r=await postJson('/api/daily/trade',{side:b.dataset.dly,pct:Number(b.dataset.p)},{'X-Token':token||''});
 if(r.candles)dlyMerge(r);if(r.error)toast(r.error,false,2500);else{const t=r.trades[r.trades.length-1];toast(`${t[1]==='buy'?'Bought':'Sold'} at ${dlyPx(t[2])}`,true,1500)}
 if(r.done){dlyStop();loadDaily()}else drawDaily()});
