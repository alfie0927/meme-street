// The Daily Chart (game/daily.py), made like the daily word games: a numbered chart a day, the same for everyone, two
// minutes, one go; streaks and stats; a grid of squares to share. The page asks the server for the candles shown so far
// once a second; the ones still to come never reach the browser. Loaded by index.html after its own script, so it shares
// its globals (S, page, api, postJson, refreshers...).
let dly=null,dlyG=null,dlyT=null,dlyBusy=false,dlyWasRunning=false,dlySize=Number(lsGet('ms_daily_size',1))||1,dlyCd=null;
async function loadDaily(){
 if(guest){dly=null;drawDailyGuest();return}
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
const dlyHMS=s=>{s=Math.max(0,Math.floor(s));return [Math.floor(s/3600),Math.floor(s%3600/60),s%60].map(x=>String(x).padStart(2,'0')).join(':')};
const dlyPx=v=>numText(v,v<1?4:2);
const dlyPlace=n=>n+(n%100>=11&&n%100<=13?'th':['th','st','nd','rd'][n%10]||'th');
const dlyDate=d=>new Date(d.day*86400000).toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'});
const DLY_WORD={buy:'Bought',sell:'Sold',short:'Shorted',cover:'Covered'};
// the chart: the lead-in and the candles so far, your trades as arrows, the last price
function dlySvg(g){
 const cs=g.candles,total=g.history+g.live,W=PHONE?380:900,H=PHONE?260:340,R=PHONE?52:64,top=8,volH=H*0.14,ph=H-volH-14;
 const lo=Math.min(...cs.map(c=>c[2]),...g.trades.map(t=>t[2])),hi=Math.max(...cs.map(c=>c[1]),...g.trades.map(t=>t[2])),pad=(hi-lo||hi*0.01)*0.08;
 const a=lo-pad,b=hi+pad,y=v=>top+(b-v)/(b-a)*ph,sw=(W-R)/total,bw=Math.max(1,sw*0.68),vx=Math.max(...cs.map(c=>c[4]),1),lastY=y(cs[cs.length-1][3]);
 const startX=(g.history-0.5)*sw;
 let h=`<rect x="0" y="0" width="${startX.toFixed(1)}" height="${H}" fill="#ffffff05"/><line x1="${startX.toFixed(1)}" x2="${startX.toFixed(1)}" y1="0" y2="${H}" stroke="#ffffff1a" stroke-dasharray="3 4"/>`;
 for(let k=0;k<4;k++){const v=a+(b-a)*(k+0.5)/4;h+=`<line x1="0" x2="${W-R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="#ffffff0a"/>`+(Math.abs(y(v)-lastY)<14?'':`<text x="${W-R+4}" y="${(y(v)+4).toFixed(0)}" fill="var(--mut)" font-size="11">${dlyPx(v)}</text>`)}
 cs.forEach((c,i)=>{const x=i*sw+sw/2,col=c[3]>=c[0]?'var(--up)':'var(--dn)';
  h+=`<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${y(c[1]).toFixed(1)}" y2="${y(c[2]).toFixed(1)}" stroke="${col}"/>`
   +`<rect x="${(x-bw/2).toFixed(1)}" y="${y(Math.max(c[0],c[3])).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1,Math.abs(y(c[0])-y(c[3]))).toFixed(1)}" fill="${col}"/>`
   +`<rect x="${(x-bw/2).toFixed(1)}" y="${(H-6-c[4]/vx*volH).toFixed(1)}" width="${bw.toFixed(1)}" height="${(c[4]/vx*volH).toFixed(1)}" fill="${col}" opacity="0.3"/>`});
 for(const t of g.trades){const x=t[0]*sw+sw/2,up=t[1]==='buy'||t[1]==='cover',c=cs[t[0]]||[0,t[2],t[2]],yy=up?y(c[2])+12:y(c[1])-12;
  h+=`<path d="M${x.toFixed(1)} ${(up?yy-7:yy+7).toFixed(1)} l-5 ${up?9:-9} h10 z" fill="${up?'var(--up)':'var(--dn)'}"><title>${DLY_WORD[t[1]]||t[1]} at ${dlyPx(t[2])}</title></path>`}
 h+=`<line x1="0" x2="${W-R}" y1="${lastY.toFixed(1)}" y2="${lastY.toFixed(1)}" stroke="var(--acc)" stroke-dasharray="2 3"/><rect x="${W-R+1}" y="${(lastY-9).toFixed(0)}" width="${R-2}" height="18" fill="var(--acc)"/><text x="${W-R+4}" y="${(lastY+4).toFixed(0)}" fill="#021012" font-size="11" font-weight="700">${dlyPx(cs[cs.length-1][3])}</text>`;
 return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="Today's chart">${h}</svg>`}
// the distribution of today's returns (bars of players), with where the player landed
function dlyHist(dist,mine){
 const W=PHONE?320:520,H=150,lo=Math.min(...dist,mine,-0.05),hi=Math.max(...dist,mine,0.05),n=Math.min(16,Math.max(8,Math.round(Math.sqrt(dist.length))+6)),bw=(hi-lo)/n;
 const bins=new Array(n).fill(0);for(const r of dist)bins[Math.max(0,Math.min(n-1,Math.floor((r-lo)/bw)))]++;
 const most=Math.max(...bins,1),x=v=>(v-lo)/(hi-lo)*W,ph=H-46,T=22;
 let h='';bins.forEach((c,i)=>{const bh=c/most*ph,mid=lo+(i+0.5)*bw;if(c)h+=`<rect x="${(x(lo+i*bw)+1).toFixed(1)}" y="${(ph-bh+10).toFixed(1)}" width="${Math.max(1,W/n-2).toFixed(1)}" height="${bh.toFixed(1)}" rx="2" fill="${mid>=0?'var(--up)':'var(--dn)'}" opacity="0.5" transform="translate(0 ${T-10})"><title>${c} player${c===1?'':'s'}: ${pc(lo+i*bw)} to ${pc(lo+(i+1)*bw)}</title></rect>`});
 const z=x(0),m=x(mine),base=ph+T,you='you '+pc(mine),yw=you.length*7.4,yx=Math.min(W-yw,Math.max(0,m-yw/2));
 h+=`<line x1="0" x2="${W}" y1="${base}" y2="${base}" stroke="var(--line)"/><line x1="${z.toFixed(1)}" x2="${z.toFixed(1)}" y1="${T}" y2="${base}" stroke="var(--mut)" stroke-dasharray="3 3"/>`
  +`<line x1="${m.toFixed(1)}" x2="${m.toFixed(1)}" y1="${T-4}" y2="${base}" stroke="var(--acc)" stroke-width="2.5"/>`
  +`<text x="${yx.toFixed(0)}" y="13" fill="var(--acc)" font-size="12" font-weight="700">${you}</text>`
  +`<text x="2" y="${H-4}" fill="var(--mut)" font-size="11">${pc(lo)}</text><text x="${W-2}" y="${H-4}" fill="var(--mut)" font-size="11" text-anchor="end">${pc(hi)}</text>`
  +(z>44&&z<W-44?`<text x="${z.toFixed(1)}" y="${H-4}" fill="var(--mut)" font-size="11" text-anchor="middle">0%</text>`:'');
 return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="Everyone's returns today, and yours">${h}</svg>`}
function dlyBoard(d){
 const me=S&&S.name,medal=['dly-gold','dly-silver','dly-bronze'];
 return `<h3 class="dly-h">Today's best <span class="mut">${numText(d.players,0)} played</span></h3>`
  +(d.board.length?`<table class="dly-board"><tbody>${d.board.map((x,i)=>`<tr class="${x.name===me?'me':''}"><td class="dly-rk ${medal[i]||''}">${i+1}</td><td><a href="/player/${encodeURIComponent(x.name)}">${esc(x.name)}</a></td><td class="mut">${x.trades} trade${x.trades===1?'':'s'}</td><td class="${clsP(x.ret)} dly-r">${pc(x.ret)}</td></tr>`).join('')}</tbody></table>`:'<p class="mut">Nobody has finished today\'s chart yet. Be the first.</p>')
  +(d.past.length?`<h3 class="dly-h">Winners of the last days</h3><table class="dly-board"><tbody>${d.past.map(p=>`<tr><td class="mut">${new Date(p.day*86400000).toLocaleDateString(undefined,{day:'numeric',month:'short',timeZone:'UTC'})}</td><td>${p.top[0]?esc(p.top[0].name):'-'}</td><td class="mut">${p.players} played</td><td class="${p.top[0]?clsP(p.top[0].ret):''} dly-r">${p.top[0]?pc(p.top[0].ret):'-'}</td></tr>`).join('')}</tbody></table>`:'')}
const dlyHead=d=>`<div class="dly-head"><div><div class="dly-title">Daily Chart <span>#${d.number}</span></div><div class="dly-sub">${dlyDate(d)} · ${numText(d.players,0)} played today</div></div>
 <div class="dly-icons"><button class="dly-ic" data-dly-help aria-label="How to play">?</button><button class="dly-ic" data-dly-stats>Stats</button></div></div>`;
const dlySquares=(grid,anim)=>`<div class="dly-grid${anim?' anim':''}">${grid.map((v,i)=>`<i class="${v>0?'u':v<0?'d':'f'}" style="animation-delay:${i*0.09}s"></i>`).join('')}</div>`;
function dlyStatRow(st){
 return `<div class="dly-stat">${[['Played',numText(st.played,0)],['Average',st.avg===null?'-':`<span class="${clsP(st.avg)}">${pc(st.avg)}</span>`],['Beat the stock',st.played?Math.round(st.beat/st.played*100)+'%':'-'],['Streak',st.streak],['Best streak',st.max_streak]]
  .map(([l,v])=>`<div><strong>${v}</strong><small>${l}</small></div>`).join('')}</div>`}
// the result: what Wordle's end screen is to Wordle
function dlyCard(g,d,anim){
 const others=(g.of||1)-1,better=others>0&&g.rank?(g.of-g.rank)/others:null;
 return `<div class="dly-res"><div class="dly-kicker">Daily Chart #${d.number} · ${dlyDate(d)}</div>
  <div class="dly-big ${clsP(g.ret)}">${pc(g.ret)}</div>
  <div class="dly-place">${g.rank?`<b>${dlyPlace(g.rank)}</b> of ${numText(g.of,0)}`:''}${better===null?(g.rank?' · the first to finish today':''):better>0?` · better than ${Math.round(better*100)}% of players`:''}</div>
  ${dlySquares(g.grid||[],anim)}
  <div class="dly-vs">The stock did <b class="${clsP(g.hold)}">${pc(g.hold)}</b>: ${!g.trades.length?'you sat it out.':g.ret>g.hold+1e-9?'you beat it.':'it beat you.'}</div>
  ${dlyStatRow(d.stats)}
  <div class="dly-share"><button class="dly-go" data-dly-share>Share</button><button class="dly-alt" data-dly-pic>Story picture</button></div>
  <div class="dly-next">Next chart in <b class="dly-cd">${dlyHMS(d.next-engineNow())}</b></div></div>`}
function dlyPop(html,label){
 let box=$('dly-pop');if(!box){box=document.createElement('div');box.id='dly-pop';document.body.appendChild(box)}
 setHtml(box,`<div class="dly-pop-in dly-modal" role="dialog" aria-label="${label}"><button class="dly-x" data-dly-close aria-label="Close">&times;</button>${html}</div>`);
 box.style.display='flex';dlyCountdown()}
function dlySummary(){
 const g=dlyG,d=dly;if(!g||!g.done||!d||!g.dist)return;lsSet('ms_daily_seen',d.day);
 dlyPop(dlyCard(g,d,true)+`<h3 class="dly-h">Everyone's returns today</h3>${dlyHist(g.dist,g.ret)}`,'Your result')}
function dlyHelp(){
 dlyPop(`<h3 class="dly-mt">How to play</h3><ul class="dly-rules">
  <li><b>One chart a day</b>, the same for everyone, with no name. A new one at midnight UTC.</li>
  <li>Press <b>Play</b>: the last minute of the chart appears, then <b>two minutes</b> of live one-second candles.</li>
  <li>Pick a size, then <b>Buy</b> or <b>Sell</b> at the latest price, as often as you like. No fees.</li>
  <li><b>Sell with nothing held and you short</b>: you win if it falls. Buy covers the short.</li>
  <li>At the end everything is valued at the last price. Your <b>return</b> is your score.</li>
  <li><b>One go a day.</b> Keep your streak going, beat the stock, and top the board.</li></ul>
  <p class="mut" style="margin:10px 0 0">Practice money (1,000 MB just for this game), not your account's MB. On a keyboard: <b>B</b> buy, <b>S</b> sell, <b>1</b>-<b>4</b> the size.</p>`,'How to play')}
function dlyStatsPop(){const d=dly;if(!d)return;dlyPop(`<h3 class="dly-mt">Your Daily Chart</h3>${dlyStatRow(d.stats)}<p class="mut" style="margin:8px 0 0">Best return: ${d.stats.best===null?'-':pc(d.stats.best)}. A streak counts days in a row; miss a day and it starts again.</p><div class="dly-next">Next chart in <b class="dly-cd">${dlyHMS(d.next-engineNow())}</b></div>`,'Your stats')}
// the countdown to the next chart, on the page and in a box, once a second while either shows it
function dlyCountdown(){if(dlyCd)return;dlyCd=setInterval(()=>{const els=document.querySelectorAll('.dly-cd');const pop=$('dly-pop');if(!dly||!els.length||(page!=='daily'&&!(pop&&pop.style.display==='flex'))){clearInterval(dlyCd);dlyCd=null;return}
 const left=dly.next-engineNow();els.forEach(e=>e.textContent=dlyHMS(left));if(left<=0){clearInterval(dlyCd);dlyCd=null;loadDaily()}},1000)}
function drawDailyGuest(){
 const el=$('daily-body');if(!el)return;el._st='guest';
 setHtml(el,`<div class="dly-wrap"><div class="dly-head"><div><div class="dly-title">Daily Chart</div><div class="dly-sub">A new chart every day</div></div><div class="dly-icons"><button class="dly-ic" data-dly-help aria-label="How to play">?</button></div></div>
  <div class="dly-hero"><p class="dly-tag">Two minutes. One chart.<br>The same one for everyone.</p><button class="dly-go" data-dly-join>Create an account to play</button><p class="dly-small">Free · one go a day · practice money</p></div></div>`)}
function drawDaily(){
 const el=$('daily-body'),d=dly;if(!el||!d)return;
 const st=d.status==='running'&&dlyG&&dlyG.done?'done':d.status;
 if(el._st!==st){el._st=st;
  if(st==='new')setHtml(el,`<div class="dly-wrap">${dlyHead(d)}<div class="dly-hero"><p class="dly-tag">Two minutes. One chart.<br>The same one for everyone.</p>
   ${d.stats.streak?`<p class="dly-streak">Streak <b>${d.stats.streak}</b> day${d.stats.streak===1?'':'s'}: keep it going</p>`:''}<button class="dly-go" id="dly-start">Play</button>
   <p class="dly-small">One go a day · 1,000 MB of practice money · <a href="#" data-dly-help>how to play</a></p></div><div id="dly-board"></div></div>`);
  else if(st==='running')setHtml(el,`<div class="dly-wrap">${dlyHead(d)}<div class="dly-top"><div class="dly-timer" id="dly-timer"></div><div class="dly-pnl"><div class="dly-ret" id="dly-ret"></div><div class="dly-eq" id="dly-eq"></div></div></div>
   <div id="dly-chart" class="dly-chart"></div><div class="dly-pos" id="dly-pos"></div>
   <div class="dly-sizes" role="group" aria-label="Size">${[0.25,0.5,0.75,1].map((p,i)=>`<button data-dly-size="${p}" title="Key ${i+1}">${p*100}%</button>`).join('')}</div>
   <div class="dly-btns"><button class="dly-buy" data-dly="buy"><span id="dly-lb">Buy</span><small>B</small></button><button class="dly-sell" data-dly="sell"><span id="dly-ls">Sell</span><small>S</small></button></div></div>`);
  else setHtml(el,`<div class="dly-wrap">${dlyHead(d)}<div id="dly-card"></div><div id="dly-chart" class="dly-chart"></div><div id="dly-dist"></div><div id="dly-board"></div></div>`)}
 const g=dlyG;
 if(st==='running'&&g&&g.candles&&g.candles.length){
  setHtml($('dly-chart'),dlySvg(g));
  const eq=g.equity,ret=eq/d.cash-1,sh=g.shares;
  $('dly-timer').textContent=dlyClock(g.left);$('dly-timer').classList.toggle('low',g.left<=15);
  setHtml($('dly-ret'),`<span class="${clsP(ret)}">${pc(ret)}</span>`);$('dly-eq').textContent=numText(eq)+' MB';
  setHtml($('dly-pos'),sh>0?`<b class="up">Long</b> ${numText(sh,sh<10?4:2)} shares · ${numText(sh*g.price)} MB`:sh<0?`<b class="dn">Short</b> ${numText(-sh,-sh<10?4:2)} shares · ${numText(-sh*g.price)} MB`:'<b>In cash</b> · pick a size, then Buy or Sell');
  $('dly-lb').textContent=sh<0?'Cover':'Buy';$('dly-ls').textContent=sh>0?'Sell':'Short';
  document.querySelectorAll('[data-dly-size]').forEach(b=>b.classList.toggle('on',Number(b.dataset.dlySize)===dlySize))}
 else if(st==='done'&&g&&g.done){
  if(g.candles&&g.candles.length)setHtml($('dly-chart'),dlySvg(g));
  if(!$('dly-card').firstChild)setHtml($('dly-card'),dlyCard(g,d,false));
  if(g.dist&&!$('dly-dist').firstChild)setHtml($('dly-dist'),`<h3 class="dly-h">Everyone's returns today</h3>${dlyHist(g.dist,g.ret)}`);
  dlyCountdown()}
 else if(st==='new')dlyCountdown();
 const bd=$('dly-board');if(bd)setHtml(bd,dlyBoard(d))}
// sharing: the result as text (the squares, like Wordle's) and as a picture for an Instagram story (1080 x 1920). A phone
// gets its share sheet; elsewhere the text is copied (and the picture saved, from its own button)
function dlyShareText(g,d){
 return `Meme Street Daily Chart #${d.number}\n${pc(g.ret)}${g.rank?' · '+dlyPlace(g.rank)+' of '+numText(g.of,0):''}\n${(g.grid||[]).map(v=>v>0?'\u{1F7E9}':v<0?'\u{1F7E5}':'⬜').join('')}\n${d.stats.streak>1?'Streak '+d.stats.streak+'\n':''}https://memestreet.net/daily?ref=daily_share`}
async function dlyPicture(g,d){
 const c=document.createElement('canvas');c.width=1080;c.height=1920;const x=c.getContext('2d'),F='ui-monospace,Consolas,Menlo,monospace',L=96;
 const up=g.ret>=0,col=up?'#3ad07a':'#f25c54';
 x.fillStyle='#08090b';x.fillRect(0,0,1080,1920);
 x.fillStyle='#4cc3cc';x.font=`700 52px ${F}`;x.fillText('MEME STREET',L,210);
 x.fillStyle='#dce3e8';x.font=`700 64px ${F}`;x.fillText('Daily Chart #'+d.number,L,300);
 x.fillStyle='#7d8a93';x.font=`40px ${F}`;x.fillText(dlyDate(d),L,360);
 x.fillStyle=col;x.font=`700 200px ${F}`;x.fillText(pc(g.ret),L,620);
 x.fillStyle='#dce3e8';x.font=`48px ${F}`;if(g.rank)x.fillText(`${dlyPlace(g.rank)} of ${numText(g.of,0)} today`,L,710);
 const grid=g.grid||[],sz=96,gap=14;grid.forEach((v,i)=>{x.fillStyle=v>0?'#3ad07a':v<0?'#f25c54':'#2a3138';x.fillRect(L+i*(sz+gap),790,sz,sz)});
 const cs=g.candles.slice(g.history-1).map(k=>k[3]),lo=Math.min(...cs),hi=Math.max(...cs),X=i=>L+i*((1080-2*L)/(cs.length-1||1)),Y=v=>1500-(hi>lo?(v-lo)/(hi-lo):0.5)*460;
 x.strokeStyle='#4cc3cc';x.lineWidth=6;x.lineJoin='round';x.beginPath();cs.forEach((v,i)=>i?x.lineTo(X(i),Y(v)):x.moveTo(X(i),Y(v)));x.stroke();
 x.fillStyle='#7d8a93';x.font=`36px ${F}`;x.fillText(`The stock: ${pc(g.hold)}`,L,1580);
 x.fillStyle='#dce3e8';x.font=`700 60px ${F}`;x.fillText('Can you beat it?',L,1720);
 x.fillStyle='#4cc3cc';x.font=`48px ${F}`;x.fillText('memestreet.net/daily',L,1800);
 const blob=await new Promise(r=>c.toBlob(r,'image/png'));return blob&&new File([blob],`meme-street-daily-${d.number}.png`,{type:'image/png'})}
async function dlyShare(){
 const g=dlyG,d=dly;if(!g||!g.done||!d)return;const text=dlyShareText(g,d);
 if(PHONE&&navigator.share){try{const f=await dlyPicture(g,d);await navigator.share(f&&navigator.canShare&&navigator.canShare({files:[f]})?{files:[f],text}:{text});return}catch(e){if(e.name==='AbortError')return}}
 try{await navigator.clipboard.writeText(text);toast('Result copied: paste it anywhere',true,3500)}catch(e){toast('Could not copy the result',false,3000)}}
async function dlySavePicture(){
 const g=dlyG,d=dly;if(!g||!g.done||!d)return;const f=await dlyPicture(g,d);if(!f)return;
 if(PHONE&&navigator.canShare&&navigator.canShare({files:[f]})){try{await navigator.share({files:[f]});return}catch(e){if(e.name==='AbortError')return}}
 const a=document.createElement('a');a.href=URL.createObjectURL(f);a.download=f.name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),5000);
 toast('Picture saved: post it to your story',true,3500)}
async function dlyTrade(side){
 if(!dlyG||dlyG.done)return;
 const r=await postJson('/api/daily/trade',{side,pct:dlySize},{'X-Token':token||''});
 if(r.candles)dlyMerge(r);if(r.error)toast(r.error,false,2500);else{const t=r.trades[r.trades.length-1];toast(`${DLY_WORD[t[1]]||t[1]} at ${dlyPx(t[2])}`,true,1200)}
 if(r.done){dlyStop();loadDaily()}else drawDaily()}
document.addEventListener('click',async e=>{
 const t=e.target;
 if(t.closest('[data-dly-close]')||t.id==='dly-pop'){const b=$('dly-pop');if(b)b.style.display='none';return}
 if(t.closest('[data-dly-help]')){e.preventDefault();dlyHelp();return}
 if(t.closest('[data-dly-stats]')){dlyStatsPop();return}
 if(t.closest('[data-dly-share]')){dlyShare();return}
 if(t.closest('[data-dly-pic]')){dlySavePicture();return}
 if(t.closest('[data-dly-join]')){const j=$('g-join');if(j)j.click();return}
 const sz=t.closest('[data-dly-size]');if(sz){dlySize=Number(sz.dataset.dlySize);lsSet('ms_daily_size',dlySize);drawDaily();return}
 if(t.id==='dly-start'){t.disabled=true;const r=await postJson('/api/daily/start',{},{'X-Token':token||''});t.disabled=false;
  if(r.error){toast(r.error,false,4000);loadDaily();return}dly.status='running';dlyG=r;dlyWasRunning=true;dlyRun();drawDaily();return}
 const b=t.closest('[data-dly]');if(b)dlyTrade(b.dataset.dly)});
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'){const b=$('dly-pop');if(b)b.style.display='none';return}
 if(page!=='daily'||!dlyG||dlyG.done||!dly||dly.status!=='running'||e.ctrlKey||e.metaKey||e.altKey||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;
 const k=e.key.toLowerCase();
 if(k==='b'){e.preventDefault();dlyTrade('buy')}else if(k==='s'){e.preventDefault();dlyTrade('sell')}
 else if('1234'.includes(k)&&k){dlySize=[0.25,0.5,0.75,1][Number(k)-1];lsSet('ms_daily_size',dlySize);drawDaily()}});
