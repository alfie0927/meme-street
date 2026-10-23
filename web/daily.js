// The Daily Chart (game/daily.py): one stock with no name, two minutes, the same chart for everyone today. The page asks
// the server for the candles shown so far once a second; the ones still to come never reach the browser. When the two
// minutes are up a summary pops up: the return, the place, everyone's returns as a distribution. Loaded by index.html
// after its own script, so it shares its globals (S, page, api, postJson, refreshers...).
let dly=null,dlyG=null,dlyT=null,dlyBusy=false,dlyWasRunning=false;
async function loadDaily(){
 if(guest){setHtml($('daily-body'),'<p class="mut">Sign in to play.</p>');return}
 const d=await api('/api/daily');if(!d||d.error||d.slow)return;
 dly=d;dlyG=d.game?Object.assign({},d.game):null;drawDaily();
 if(d.status==='running'){dlyWasRunning=true;dlyRun()}
 else if(d.status==='done'&&dlyG&&dlyG.done&&(dlyWasRunning||lsGet('ms_daily_seen',null)!==d.day)){dlyWasRunning=false;dlySummary()}}
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
const DLY_WORD={buy:'Bought',sell:'Sold',short:'Shorted',cover:'Covered'};
function dlySvg(g){
 const cs=g.candles,total=g.history+g.live,W=PHONE?380:900,H=PHONE?280:360,R=PHONE?52:64,top=8,volH=H*0.16,ph=H-volH-14;
 const lo=Math.min(...cs.map(c=>c[2]),...g.trades.map(t=>t[2])),hi=Math.max(...cs.map(c=>c[1]),...g.trades.map(t=>t[2])),pad=(hi-lo||hi*0.01)*0.08;
 const a=lo-pad,b=hi+pad,y=v=>top+(b-v)/(b-a)*ph,sw=(W-R)/total,bw=Math.max(1,sw*0.68),vx=Math.max(...cs.map(c=>c[4]),1),lastY=y(cs[cs.length-1][3]);
 let h='';
 for(let k=0;k<4;k++){const v=a+(b-a)*(k+0.5)/4;h+=`<line x1="0" x2="${W-R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="#ffffff0c"/>`+(Math.abs(y(v)-lastY)<14?'':`<text x="${W-R+4}" y="${(y(v)+4).toFixed(0)}" fill="var(--mut)" font-size="11">${dlyPx(v)}</text>`)}
 cs.forEach((c,i)=>{const x=i*sw+sw/2,col=c[3]>=c[0]?'var(--up)':'var(--dn)';
  h+=`<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${y(c[1]).toFixed(1)}" y2="${y(c[2]).toFixed(1)}" stroke="${col}"/>`
   +`<rect x="${(x-bw/2).toFixed(1)}" y="${y(Math.max(c[0],c[3])).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1,Math.abs(y(c[0])-y(c[3]))).toFixed(1)}" fill="${col}"/>`
   +`<rect x="${(x-bw/2).toFixed(1)}" y="${(H-6-c[4]/vx*volH).toFixed(1)}" width="${bw.toFixed(1)}" height="${(c[4]/vx*volH).toFixed(1)}" fill="${col}" opacity="0.35"/>`});
 for(const t of g.trades){const x=t[0]*sw+sw/2,up=t[1]==='buy'||t[1]==='cover',c=cs[t[0]]||[0,t[2],t[2]],yy=up?y(c[2])+12:y(c[1])-12;
  h+=`<path d="M${x.toFixed(1)} ${(up?yy-7:yy+7).toFixed(1)} l-5 ${up?9:-9} h10 z" fill="${up?'var(--up)':'var(--dn)'}"><title>${DLY_WORD[t[1]]||t[1]} at ${dlyPx(t[2])}</title></path>`}
 h+=`<line x1="0" x2="${W-R}" y1="${lastY.toFixed(1)}" y2="${lastY.toFixed(1)}" stroke="var(--acc)" stroke-dasharray="2 3"/><rect x="${W-R+1}" y="${(lastY-9).toFixed(0)}" width="${R-2}" height="18" fill="var(--acc)"/><text x="${W-R+4}" y="${(lastY+4).toFixed(0)}" fill="#021012" font-size="11" font-weight="700">${dlyPx(cs[cs.length-1][3])}</text>`;
 if(!g.done)h+=`<text x="10" y="${PHONE?30:38}" fill="var(--acc)" font-size="${PHONE?24:30}" font-weight="700">${dlyClock(g.left)}</text>`;
 return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="Today's chart">${h}</svg>`}
function dlyBoard(d){
 const me=S&&S.name;
 return `<h3 class="sp">Today's board <span class="mut">(${numText(d.players,0)} finished)</span></h3>`
  +(d.board.length?`<table class="dly-board"><thead><tr><th>#</th><th>Player</th><th>Return</th><th>Trades</th></tr></thead><tbody>${d.board.map((x,i)=>`<tr class="${x.name===me?'me':''}"><td>${i+1}</td><td><a href="/player/${encodeURIComponent(x.name)}">${esc(x.name)}</a></td><td class="${clsP(x.ret)}">${pc(x.ret)}</td><td>${x.trades}</td></tr>`).join('')}</tbody></table>`:'<p class="mut">Nobody has finished today\'s chart yet.</p>')
  +(d.past.length?`<h3 class="sp">The last days</h3><table class="dly-board"><thead><tr><th>Day</th><th>Winner</th><th>Return</th><th>Players</th></tr></thead><tbody>${d.past.map(p=>`<tr><td>${new Date(p.day*86400000).toLocaleDateString(undefined,{day:'numeric',month:'short',timeZone:'UTC'})}</td><td>${p.top[0]?esc(p.top[0].name):'-'}</td><td class="${p.top[0]?clsP(p.top[0].ret):''}">${p.top[0]?pc(p.top[0].ret):'-'}</td><td>${p.players}</td></tr>`).join('')}</tbody></table>`:'')}
// the distribution of today's returns (bars of players), with where the player landed
function dlyHist(dist,mine){
 const W=PHONE?320:520,H=170,lo=Math.min(...dist,mine,-0.05),hi=Math.max(...dist,mine,0.05),n=Math.min(16,Math.max(8,Math.round(Math.sqrt(dist.length))+6)),bw=(hi-lo)/n;
 const bins=new Array(n).fill(0);for(const r of dist)bins[Math.max(0,Math.min(n-1,Math.floor((r-lo)/bw)))]++;
 const most=Math.max(...bins,1),x=v=>(v-lo)/(hi-lo)*W,ph=H-46,T=22;
 let h='';bins.forEach((c,i)=>{const bh=c/most*ph,mid=lo+(i+0.5)*bw;if(c)h+=`<rect x="${(x(lo+i*bw)+1).toFixed(1)}" y="${(ph-bh+10).toFixed(1)}" width="${Math.max(1,W/n-2).toFixed(1)}" height="${bh.toFixed(1)}" fill="${mid>=0?'var(--up)':'var(--dn)'}" opacity="0.55" transform="translate(0 ${T-10})"><title>${c} player${c===1?'':'s'}: ${pc(lo+i*bw)} to ${pc(lo+(i+1)*bw)}</title></rect>`});
 const z=x(0),m=x(mine);
 const base=ph+T,you='you '+pc(mine),yw=you.length*7.4,yx=Math.min(W-yw,Math.max(0,m-yw/2));
 h+=`<line x1="0" x2="${W}" y1="${base}" y2="${base}" stroke="var(--line)"/><line x1="${z.toFixed(1)}" x2="${z.toFixed(1)}" y1="${T}" y2="${base}" stroke="var(--mut)" stroke-dasharray="3 3"/>`
  +`<line x1="${m.toFixed(1)}" x2="${m.toFixed(1)}" y1="${T-4}" y2="${base}" stroke="var(--acc)" stroke-width="2.5"/>`
  +`<text x="${yx.toFixed(0)}" y="13" fill="var(--acc)" font-size="12" font-weight="700">${you}</text>`
  +`<text x="2" y="${H-4}" fill="var(--mut)" font-size="11">${pc(lo)}</text><text x="${W-2}" y="${H-4}" fill="var(--mut)" font-size="11" text-anchor="end">${pc(hi)}</text>`
  +(z>44&&z<W-44?`<text x="${z.toFixed(1)}" y="${H-4}" fill="var(--mut)" font-size="11" text-anchor="middle">0%</text>`:'');
 return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="Everyone's returns today, and yours">${h}</svg>`}
function dlySummary(){
 const g=dlyG,d=dly;if(!g||!g.done||!d||!g.dist)return;lsSet('ms_daily_seen',d.day);
 const others=(g.of||1)-1,better=others>0&&g.rank?(g.of-g.rank)/others:null;          // (from the place, so the two agree)
 let box=$('dly-pop');if(!box){box=document.createElement('div');box.id='dly-pop';document.body.appendChild(box)}
 setHtml(box,`<div class="dly-pop-in" role="dialog" aria-label="Your result"><div class="bar" style="justify-content:space-between;margin:0"><b>Today's Daily Chart</b><button data-dly-close aria-label="Close">&times;</button></div>
  <div class="dly-big ${clsP(g.ret)}">${pc(g.ret)}</div>
  <p style="margin:2px 0 10px">You finished with <b>${numText(g.equity)} MB</b> from 1,000.00 MB: <b>${g.rank?dlyPlace(g.rank)+' of '+numText(g.of,0):'-'}</b> today${better===null?'. You are the first to finish: the board fills in as others play.':`, better than <b>${Math.round(better*100)}%</b> of the others.`}</p>
  <h3 class="sp" style="margin-top:4px">Everyone's returns today</h3>${dlyHist(g.dist,g.ret)}
  <div class="dly-result" style="margin-top:12px"><div><small>The stock itself</small><strong class="${clsP(g.hold)}">${pc(g.hold)}</strong></div><div><small>Your trades</small><strong>${g.trades.length}</strong></div><div><small>Its high</small><strong>${dlyPx(g.hi)}</strong></div><div><small>Its low</small><strong>${dlyPx(g.lo)}</strong></div></div>
  <p class="hint" style="margin:6px 0 0">${!g.trades.length?'You sat it out.':g.ret>g.hold+1e-9?'You beat just holding the stock.':'Just holding the stock would have done better.'} A new chart comes at midnight UTC.</p>
  <div class="bar" style="margin:12px 0 0"><button class="buy" data-dly-close>Close</button></div></div>`);
 box.style.display='flex'}
function drawDaily(){
 const el=$('daily-body'),d=dly;if(!el||!d)return;
 const st=d.status==='running'&&dlyG&&dlyG.done?'done':d.status;
 if(el._st!==st){el._st=st;
  if(st==='new')setHtml(el,`<p>One stock with no name, two minutes, and the same chart for everyone today. You get <b>1,000 MB</b> of practice money (not your real MB). Press <b>Start</b>: a minute of the chart's past appears, then a new one-second candle every second for two minutes. <b>Buy</b> with 25, 50, 75 or 100% of your cash and <b>sell</b> 25, 50, 75 or 100% of your shares, at the latest price, with no fees. <b>Sell with no shares and you short</b> the stock (you win if it falls); buying then covers the short. Whatever you hold at the end is valued at the last price. Read the levels in the minute before you start: the stock respects support and resistance like the real market does. <b>One go a day</b>; the best returns top the board.</p>
   <p><button class="buy dly-start" id="dly-start">Start</button></p><div id="dly-board"></div>`);
  else if(st==='running')setHtml(el,`<div id="dly-stats" class="dly-stats"></div><div id="dly-chart" class="dly-chart"></div>
   <div class="dly-acts"><div class="bar"><span class="lab" id="dly-lb"></span>${[25,50,75,100].map(p=>`<button class="buy" data-dly="buy" data-p="${p/100}">${p}%</button>`).join('')}</div>
   <div class="bar"><span class="lab" id="dly-ls"></span>${[25,50,75,100].map(p=>`<button class="sell" data-dly="sell" data-p="${p/100}">${p}%</button>`).join('')}</div></div><div id="dly-board"></div>`);
  else setHtml(el,`<div id="dly-result" class="dly-result"></div><div id="dly-chart" class="dly-chart"></div><div class="bar"><button id="dly-again">See the summary</button><span class="hint" id="dly-next"></span></div><div id="dly-board"></div>`)}
 const g=dlyG;
 if(st!=='new'&&g&&g.candles&&g.candles.length){
  setHtml($('dly-chart'),dlySvg(g));
  const eq=g.equity,ret=eq/d.cash-1,sh=g.shares;
  if(st==='running'){
   setHtml($('dly-stats'),[['Price',dlyPx(g.price)],['Cash',numText(g.cash)+' MB'],[sh<0?'Short':'Shares',sh?numText(Math.abs(sh),Math.abs(sh)<10?4:2)+` <span class="mut">(${numText(Math.abs(sh)*g.price)} MB)</span>`:'-'],['Total',numText(eq)+' MB'],['Return',`<span class="${clsP(ret)}">${pc(ret)}</span>`]].map(([l,v])=>`<div><small>${l}</small><strong>${v}</strong></div>`).join(''));
   $('dly-lb').textContent=sh<0?'Cover':'Buy';$('dly-ls').textContent=sh>0?'Sell':'Short'}
  else{setHtml($('dly-result'),`<div><small>Your result</small><strong class="${clsP(g.ret)}">${pc(g.ret)}</strong></div><div><small>You finished with</small><strong>${numText(g.equity)} MB</strong></div><div><small>Your place</small><strong>${g.rank?dlyPlace(g.rank)+' of '+numText(g.of,0):'-'}</strong></div><div><small>Trades</small><strong>${g.trades.length}</strong></div>`);
   const left=Math.max(0,d.next-engineNow()),hrs=Math.floor(left/3600),mins=Math.floor(left%3600/60);
   setHtml($('dly-next'),`A new chart in ${hrs?hrs+' h ':''}${mins} min (at midnight UTC). Green arrows are your buys and covers, red ones your sells and shorts.`)}}
 setHtml($('dly-board'),dlyBoard(d))}
document.addEventListener('click',async e=>{
 if(e.target.closest('[data-dly-close]')||e.target.id==='dly-pop'){const b=$('dly-pop');if(b)b.style.display='none';return}
 if(e.target.id==='dly-again'){dlySummary();return}
 if(e.target.id==='dly-start'){e.target.disabled=true;const r=await postJson('/api/daily/start',{},{'X-Token':token||''});e.target.disabled=false;
  if(r.error){toast(r.error,false,4000);loadDaily();return}dly.status='running';dlyG=r;dlyWasRunning=true;drawDaily();dlyRun();return}
 const b=e.target.closest('[data-dly]');if(!b||!dlyG)return;
 const r=await postJson('/api/daily/trade',{side:b.dataset.dly,pct:Number(b.dataset.p)},{'X-Token':token||''});
 if(r.candles)dlyMerge(r);if(r.error)toast(r.error,false,2500);else{const t=r.trades[r.trades.length-1];toast(`${DLY_WORD[t[1]]||t[1]} at ${dlyPx(t[2])}`,true,1500)}
 if(r.done){dlyStop();loadDaily()}else drawDaily()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){const b=$('dly-pop');if(b)b.style.display='none'}});
