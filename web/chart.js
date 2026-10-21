// The chart of the stock page (ROADMAP TA-F2): candles and their time scales (real time and game time), the crosshair
// and readout, your trades and orders on the chart, the indicators and their settings, the drawing tools, the chart's
// size and the position-size box. Loaded after the page's own script (index.html), whose helpers it uses ($, esc, S,
// lsGet, api, ...); the page calls into it only once it is running (drawChart, requestHistory, ...), so the two share
// one set of globals like a single script would.
const PERIODS=[['30s','30s',30],['1m','1m',60],['5m','5m',300],['15m','15m',900],['30m','30m',1800],['1h','1h',3600],['2h','2h',7200],['4h','4h',14400],['1d','1d',86400],['1mo','1M',2592000],['1y','1Y',31536000]];
const secsOf=k=>(PERIODS.find(p=>p[0]===k)||PERIODS[0])[2];

// ---------- candlestick chart ----------
// The newest candle sits at the middle and everything shifts left as candles arrive. Candles start thick and
// thin out as more are created. Zoom and pan are free: you can zoom out well past the data. On a laptop the chart is
// drawn at the width of its box (1 unit = 1 pixel); its height is the player's choice (drag the bar under it, or full
// screen). Under the price: the volume, then one panel per oscillator that is switched on.
const NARROW=matchMedia('(max-width:760px)').matches;
const CH=NARROW?{w:400,h:330,padL:6,padR:80,padT:12,padB:26}:{w:960,h:330,padL:8,padR:96,padT:14,padB:28};
const PH_DEFAULT=NARROW?220:250,VOL_H=56,PANEL_H=70,PANEL_GAP=8;
let chartFull=false,chartGeom=null;
// the chart type and price scale (TA-B2), kept with the rest of the set-up (savePrefs)
const CTYPES={candles:'Candles',hollow:'Hollow candles',bars:'Bars (OHLC)',line:'Line',ha:'Heikin-Ashi'};
let chartType=CTYPES[lsGet('ms_ctype','candles')]?lsGet('ms_ctype','candles'):'candles',logScale=!!lsGet('ms_log',false),showTrades=lsGet('ms_trades',true)!==false;
let myTrades=[],myTradesFor=null,myTradesKey=null;
const plotW=()=>CH.w-CH.padL-CH.padR;
const baseSlot=n=>Math.max(7,Math.min(80,plotW()*.5/Math.max(n,3)));
const clampZoom=(z,n)=>{const b=baseSlot(n);return Math.max(1.2/b,Math.min(160/b,z))};
const newestX=()=>CH.padL+plotW()*.5+pan;
function clampPan(n){const slot=baseSlot(n)*zoom,lo=CH.padL,hi=CH.padL+plotW()+(n-1)*slot;pan=Math.max(lo,Math.min(hi,newestX()))-(CH.padL+plotW()*.5)}
function chartPH(){
 if(chartFull){const box=$('chart-box'),px=box?box.clientWidth:CH.w,scale=CH.w/Math.max(300,px);
  const used=(NARROW?190:175)+(VOL_H+PANEL_GAP+activeOf('panel').length*(PANEL_H+PANEL_GAP))/scale;
  return Math.max(200,Math.round((window.innerHeight-used)*scale))}
 const v=Number(lsGet('ms_ph',PH_DEFAULT));return Math.max(160,Math.min(1400,isFinite(v)?v:PH_DEFAULT))}
function axisLabel(t){
 const d=new Date(t*1000),p=x=>String(x).padStart(2,'0'),hm=p(d.getHours())+':'+p(d.getMinutes());
 if(chartPeriod==='30s')return hm+':'+p(d.getSeconds());
 if(['1m','5m','15m','30m'].includes(chartPeriod))return hm;
 if(['1h','2h','4h'].includes(chartPeriod))return(d.getMonth()+1)+'/'+d.getDate()+' '+hm;
 if(chartPeriod==='1d')return(d.getMonth()+1)+'/'+d.getDate();
 return chartPeriod==='1mo'?d.toLocaleString(undefined,{month:'short',year:'2-digit'}):String(d.getFullYear())}
function liveCandles(price){
 const c=chartCandles.map(x=>({...x}));
 if(!c.length||!price)return c;
 const secs=secsOf(chartPeriod),bucket=Math.floor(engineNow()/secs)*secs,lc=c[c.length-1];
 if(bucket>lc.t)c.push({t:bucket,o:lc.c,h:Math.max(lc.c,price),l:Math.min(lc.c,price),c:price,v:0});
 else{lc.c=price;lc.h=Math.max(lc.h,price);lc.l=Math.min(lc.l,price)}
 return c}
const pxText=v=>numText(v,Math.abs(v)<1?4:2);
// Heikin-Ashi candles: each one averages its own prices with the candle before, so a trend reads as a run of one colour
function haOf(c){const o=[];for(let i=0;i<c.length;i++){const x=c[i],cl=(x.o+x.h+x.l+x.c)/4,op=i?(o[i-1].o+o[i-1].c)/2:(x.o+x.c)/2;o.push({t:x.t,o:op,c:cl,h:Math.max(x.h,op,cl),l:Math.min(x.l,op,cl),v:x.v})}return o}
function candleSvg(candles,price,avg){
 if(!NARROW){const wr=$('chart-wrap'),cw=wr?wr.clientWidth:0;if(cw>300)CH.w=Math.round(cw)}
 const{w,padL,padR,padT,padB}=CH,pw=plotW(),axisX=w-padR,n=candles.length;
 if(!n){chartGeom=null;return '<p class="mut">Collecting prices…</p>'}
 clampPan(n);
 const panels=activeOf('panel'),PH=chartPH(),VH=VOL_H,SH=PANEL_H,GAP=PANEL_GAP,secs=secsOf(chartPeriod);
 const vTop=padT+PH+GAP,pTop=vTop+VH+GAP,h=pTop+panels.length*(SH+GAP)+padB-GAP;
 CH.h=h;
 const slot=baseSlot(n)*zoom,x0=newestX(),cx=i=>x0-(n-1-i)*slot,bodyW=Math.max(1,slot*.7);
 const vis=[];for(let i=0;i<n;i++){const x=cx(i);if(x>=padL-slot&&x<=padL+pw+slot)vis.push(i)}
 const C=colsOf(candles),ctx={secs,candles,vis,n},D=chartType==='ha'?haOf(candles):candles;
 let lo=Infinity,hi=-Infinity;
 for(const i of vis){lo=Math.min(lo,D[i].l);hi=Math.max(hi,D[i].h)}
 if(!vis.length){lo=hi=price||candles[n-1].c}
 if(price){lo=Math.min(lo,price);hi=Math.max(hi,price)}
 if(avg){lo=Math.min(lo,avg);hi=Math.max(hi,avg)}
 for(const o of(S&&S.orders||[]))if(o.ticker===selectedTicker&&price&&Math.abs(o.trigger/price-1)<0.1){lo=Math.min(lo,o.trigger);hi=Math.max(hi,o.trigger)}   // your stop and target stay in view
 if(logScale&&lo>0){const r=Math.log(hi/lo)*.08||.002;lo*=Math.exp(-r);hi*=Math.exp(r)}
 else{const padv=(hi-lo)*.08||hi*.002||1e-6;lo-=padv;hi+=padv}
 if(yMan){lo=yMan.lo;hi=yMan.hi}               // the player has moved the price scale up or down
 // a log scale shows equal percentage moves the same height: the map from price to height works in logs
 const LG=logScale&&lo>0&&hi>lo,L0=LG?Math.log(lo):lo,LS=LG?Math.log(hi/lo):hi-lo,span=hi-lo;
 const y=v=>padT+PH-((LG?Math.log(Math.max(v,1e-12)):v)-L0)/LS*PH,pAt=yy=>{const u=L0+(padT+PH-yy)/PH*LS;return LG?Math.exp(u):u};
 const reads=[];                              // what the readout above the chart shows for each indicator
 chartGeom={x0,slot,secs,tLast:candles[n-1].t,n,padL,pw,padT,PH,lo,span,w,h,axisX,log:LG,y,pAt,drawn:D,raw:candles,reads};
 // indices whose x is on screen, including ones past the newest candle (the Ichimoku cloud is drawn 26 candles ahead)
 const onScreen=len=>{const a=Math.max(0,Math.floor(n-1-(x0-padL+slot)/slot)),b=Math.min(len-1,Math.ceil(n-1+(padL+pw+slot-x0)/slot));return[a,b]};
 const pathOf=(vals,yf)=>{let d='',pen=false;const[a,b]=onScreen(vals.length);for(let i=a;i<=b;i++){const v=vals[i];if(nv(v)){pen=false;continue}d+=(pen?'L':'M')+cx(i).toFixed(1)+' '+yf(v).toFixed(1);pen=true}return d};
 let s=`<svg class="price-chart" viewBox="0 0 ${w} ${h}" style="aspect-ratio:${w}/${h}" role="img" aria-label="${chartPeriod} candlestick price chart"><defs><clipPath id="clip"><rect x="${padL}" y="${padT}" width="${pw}" height="${PH}"/></clipPath><clipPath id="clipV"><rect x="${padL}" y="${vTop}" width="${pw}" height="${h-vTop}"/></clipPath></defs>`;
 for(let i=0;i<=4;i++){const v=LG?Math.exp(L0+LS*i/4):lo+span*i/4,yy=y(v).toFixed(1);
  s+=`<line x1="${padL}" y1="${yy}" x2="${axisX}" y2="${yy}" stroke="#1a1f24"/><text x="${axisX+6}" y="${(+yy+4).toFixed(1)}" fill="#7d8a93" font-size="11">${pxText(v)} MB</text>`}
 s+=`<line x1="${axisX}" y1="${padT}" x2="${axisX}" y2="${h-padB}" stroke="#262d33"/><line x1="${padL}" y1="${h-padB}" x2="${axisX}" y2="${h-padB}" stroke="#262d33"/><line x1="${padL}" y1="${vTop-GAP/2}" x2="${axisX}" y2="${vTop-GAP/2}" stroke="#1a1f24"/><g clip-path="url(#clip)">`;
 const every=Math.max(1,Math.ceil(110/slot));
 // overlays under the candles: filled bands and clouds
 const legend=[],notes=[],over=[];
 for(const d of activeOf('price')){const r=runInd(d,C,ctx);over.push([d,r]);if(r.note)notes.push(r.note)}
 for(const[d,r]of over)(r.lines||[]).concat(r.dots||[]).forEach((ln,j)=>{if(ln.label||j===0)reads.push({label:ln.label||indLabel(d),c:ln.c,v:ln.v})});
 for(const[d,r]of over)for(const fl of r.fills||[]){const[a,b]=onScreen(fl.a.length);let run=[],sign=0;
  const flush=()=>{if(run.length>1){const top=run.map(i=>cx(i).toFixed(1)+' '+y(fl.a[i]).toFixed(1)),bot=run.slice().reverse().map(i=>cx(i).toFixed(1)+' '+y(fl.b[i]).toFixed(1));s+=`<path d="M${top.join('L')}L${bot.join('L')}Z" fill="${fl.c2&&sign<0?fl.c2:fl.c}" stroke="none"/>`}run=[]};
  for(let i=a;i<=b;i++){if(nv(fl.a[i])||nv(fl.b[i])){flush();continue}const sg=fl.a[i]>=fl.b[i]?1:-1;if(fl.c2&&run.length&&sg!==sign)flush();sign=sg;run.push(i)}flush()}
 // the price, drawn the chosen way: candles, hollow candles (a rising one is an outline), bars, a line, or Heikin-Ashi
 if(chartType==='line'){const p=pathOf(D.map(c=>c.c),y);if(p)s+=`<path d="${p}" fill="none" stroke="#4cc3cc" stroke-width="1.6" stroke-linejoin="round"/>`}
 else for(const i of vis){
  const c=D[i],x=cx(i),up=c.c>=c.o,col=up?'#3ad07a':'#f25c54',yO=y(c.o),yC=y(c.c),top=Math.min(yO,yC),bh=Math.max(1,Math.abs(yC-yO)),sw=Math.max(1,Math.min(2,bodyW/8)).toFixed(1);
  if(chartType==='bars'){const tk=Math.max(2,bodyW/2);s+=`<path d="M${x.toFixed(1)} ${y(c.h).toFixed(1)}V${y(c.l).toFixed(1)}M${(x-tk).toFixed(1)} ${yO.toFixed(1)}H${x.toFixed(1)}M${x.toFixed(1)} ${yC.toFixed(1)}H${(x+tk).toFixed(1)}" stroke="${col}" stroke-width="${sw}" fill="none"/>`;continue}
  s+=`<line x1="${x.toFixed(1)}" y1="${y(c.h).toFixed(1)}" x2="${x.toFixed(1)}" y2="${y(c.l).toFixed(1)}" stroke="${col}" stroke-width="${sw}"/>`;
  s+=chartType==='hollow'&&up?`<rect x="${(x-bodyW/2+.5).toFixed(1)}" y="${top.toFixed(1)}" width="${Math.max(.5,bodyW-1).toFixed(1)}" height="${bh.toFixed(1)}" fill="#08090b" stroke="${col}" stroke-width="1"/>`
   :`<rect x="${(x-bodyW/2).toFixed(1)}" y="${top.toFixed(1)}" width="${bodyW.toFixed(1)}" height="${bh.toFixed(1)}" fill="${col}"/>`}
 for(const[d,r]of over){
  for(const ln of r.lines||[]){const p=pathOf(ln.v,y);if(p)s+=`<path d="${p}" fill="none" stroke="${ln.c}" stroke-width="1.4"${ln.dash?` stroke-dasharray="${ln.dash}"`:''}/>`;if(ln.label)legend.push([ln.label,ln.c])}
  for(const dt of r.dots||[]){const[a,b]=onScreen(dt.v.length);for(let i=a;i<=b;i++)if(!nv(dt.v[i]))s+=`<circle cx="${cx(i).toFixed(1)}" cy="${y(dt.v[i]).toFixed(1)}" r="${Math.max(1.3,Math.min(2.6,bodyW/4)).toFixed(1)}" fill="${dt.c}"/>`;legend.push([dt.label,dt.c])}
  for(const sg of r.segs||[]){s+=`<line x1="${cx(sg.i0).toFixed(1)}" y1="${y(sg.p0).toFixed(1)}" x2="${cx(sg.i1).toFixed(1)}" y2="${y(sg.p1).toFixed(1)}" stroke="${sg.c}" stroke-width="1.4"${sg.dash?` stroke-dasharray="${sg.dash}"`:''}/>`;if(sg.label)legend.push([sg.label,sg.c])}
  if(r.pivots){for(const pv of r.pivots){const xa=cx(pv.i0)-slot/2,xb=cx(pv.i1)+slot/2;if(xb<padL||xa>padL+pw)continue;
    for(const[lab,p]of pv.lv){const yy=y(p).toFixed(1),col=lab==='P'?'#d2a8ff':lab[0]==='R'?'#f25c54aa':'#3ad07aaa';s+=`<line x1="${xa.toFixed(1)}" y1="${yy}" x2="${xb.toFixed(1)}" y2="${yy}" stroke="${col}" stroke-width="1.2"/><text x="${(xa+3).toFixed(1)}" y="${(+yy-3).toFixed(1)}" fill="${col}" font-size="9.5">${lab}</text>`}}
   legend.push(['Pivots','#d2a8ff'])}
  if(r.autofib&&vis.length){let ih=vis[0],il=vis[0];for(const i of vis){if(candles[i].h>candles[ih].h)ih=i;if(candles[i].l<candles[il].l)il=i}
   const H=candles[ih].h,L=candles[il].l,rising=il<ih,xs=cx(Math.min(ih,il));
   FIBS.forEach((r0,j)=>{const p=rising?H-r0*(H-L):L+r0*(H-L),yy=y(p).toFixed(1);s+=`<line x1="${Math.max(padL,xs).toFixed(1)}" y1="${yy}" x2="${axisX}" y2="${yy}" stroke="#e3b341${j%6?'99':''}" stroke-width="1" stroke-dasharray="${j%6?'5 4':''}"/><text x="${(Math.max(padL,xs)+3).toFixed(1)}" y="${(+yy-3).toFixed(1)}" fill="#e3b341" font-size="10">${(r0*100).toFixed(1)}% · ${pxText(p)}</text>`});
   legend.push(['Auto Fib','#e3b341'])}}
 s+=drawingsSvg();
 s+='</g>';
 s+=`<rect class="y-axis-hit" x="${axisX}" y="${padT}" width="${padR}" height="${PH}" fill="transparent"><title>Drag up or down (or scroll) to squeeze or stretch the price range; double-click for automatic</title></rect>`;
 if(legend.length||notes.length)s+=`<text x="${padL+4}" y="${padT+12}" font-size="10.5">${legend.map(l=>`<tspan fill="${l[1]}">${esc(l[0])}  </tspan>`).join('')}${notes.map(t=>`<tspan fill="#7d8a93">${esc(t)}  </tspan>`).join('')}</text>`;
 // volume, with its average if switched on
 let vmax=0;for(const i of vis)vmax=Math.max(vmax,candles[i].v||0);
 s+=`<g clip-path="url(#clipV)">`;
 const yv=v=>vTop+VH-v/vmax*(VH-4);
 if(vmax>0){for(const i of vis){const c=candles[i],vh=(c.v||0)/vmax*(VH-4),x=cx(i);s+=`<rect x="${(x-bodyW/2).toFixed(1)}" y="${(vTop+VH-vh).toFixed(1)}" width="${bodyW.toFixed(1)}" height="${Math.max(0,vh).toFixed(1)}" fill="${c.c>=c.o?'#3ad07a66':'#f25c5466'}"/>`}
  for(const d of activeOf('volume')){const r=runInd(d,C,ctx);for(const ln of r.lines||[]){reads.push({label:ln.label||indLabel(d),c:ln.c,v:ln.v,fmt:volText});const p=pathOf(ln.v.map(v=>nv(v)?null:Math.min(v,vmax)),yv);if(p)s+=`<path d="${p}" fill="none" stroke="${ln.c}" stroke-width="1.3"/>`}}}
 s+=`</g><text x="${axisX+6}" y="${vTop+12}" fill="#7d8a93" font-size="10.5">Volume</text>${vmax>0?`<text x="${axisX+6}" y="${vTop+26}" fill="#7d8a93" font-size="10.5">${volText(vmax)}</text>`:''}`;
 // one panel per oscillator
 panels.forEach((d,j)=>{const top=pTop+j*(SH+GAP);const r=runInd(d,C,ctx);
  (r.lines||[]).forEach((ln,k)=>{if(ln.label||k===0)reads.push({label:ln.label&&(r.lines||[]).length>1?indLabel(d)+' '+ln.label:indLabel(d),c:ln.c,v:ln.v,fmt:r.fmt})});
  if(!(r.lines||[]).length&&r.hist)reads.push({label:indLabel(d),c:indCol(d),v:r.hist,fmt:r.fmt});
  let a=Infinity,b=-Infinity;const series=(r.lines||[]).map(l=>l.v).concat(r.hist?[r.hist]:[]);
  if(r.range){[a,b]=r.range}else{for(const v of series)for(const i of vis)if(!nv(v[i])){a=Math.min(a,v[i]);b=Math.max(b,v[i])}for(const rf of r.refs||[]){a=Math.min(a,rf);b=Math.max(b,rf)}if(!isFinite(a)){a=0;b=1}if(a===b){a-=1;b+=1}const pd=(b-a)*.08;a-=pd;b+=pd}
  const yp=v=>top+SH-(v-a)/(b-a)*SH,fmt=r.fmt||(v=>Math.abs(v)>=1000?volText(v):Math.abs(v)<10?v.toFixed(2):v.toFixed(0));
  s+=`<line x1="${padL}" y1="${top-GAP/2}" x2="${axisX}" y2="${top-GAP/2}" stroke="#1a1f24"/>`;
  for(const rf of r.refs||[])s+=`<line x1="${padL}" y1="${yp(rf).toFixed(1)}" x2="${axisX}" y2="${yp(rf).toFixed(1)}" stroke="#7d8a9355" stroke-dasharray="3 3"/>`;
  s+=`<g clip-path="url(#clipV)">`;
  if(r.hist){const z=yp(Math.max(a,Math.min(b,0)));for(const i of vis){const v=r.hist[i];if(nv(v))continue;const x=cx(i),yy=yp(v);s+=`<rect x="${(x-bodyW/2).toFixed(1)}" y="${Math.min(z,yy).toFixed(1)}" width="${bodyW.toFixed(1)}" height="${Math.abs(yy-z).toFixed(1)}" fill="${v>=0?'#3ad07a66':'#f25c5466'}"/>`}}
  for(const ln of r.lines||[]){const p=pathOf(ln.v,yp);if(p)s+=`<path d="${p}" fill="none" stroke="${ln.c}" stroke-width="1.3"/>`}
  s+=`</g><text x="${axisX+6}" y="${top+12}" fill="#7d8a93" font-size="10.5">${esc(indLabel(d))}</text>`;
  const first=series[0];let last=null;if(first)for(let i=first.length-1;i>=0;i--)if(!nv(first[i])){last=first[i];break}
  if(last!==null)s+=`<text x="${axisX+6}" y="${top+26}" fill="${(r.lines&&r.lines[0]&&r.lines[0].c)||'#7d8a93'}" font-size="10.5">${esc(fmt(last))}</text>`});
 for(const i of vis){if((n-1-i)%every===0){const x=cx(i);if(x>=padL+20&&x<=padL+pw-20)s+=`<text x="${x.toFixed(1)}" y="${h-9}" fill="#7d8a93" font-size="11" text-anchor="middle">${axisLabel(candles[i].t)}</text>`}}
 // your own trades in this stock (TA-B6): a green arrow under the price where you bought or covered, a red one over it where
 // you sold or shorted (hover one for what and when); "My trades" under the chart switches them off
 if(showTrades&&myTradesFor===selectedTicker&&myTrades.length){s+=`<g clip-path="url(#clip)">`;
  for(const e of myTrades){const x=x0-(candles[n-1].t-Math.floor(e.t/secs)*secs)/secs*slot;if(x<padL-8||x>padL+pw+8||!(e.price>0))continue;
   const buy=e.kind==='buy'||e.kind==='cover',yy=y(e.price),z=Math.max(4,Math.min(7,bodyW/2+2)),col=buy?'#3ad07a':'#f25c54',a=buy?yy+2:yy-2,b=buy?a+1.6*z:a-1.6*z;
   s+=`<polygon class="trade-mark" points="${x.toFixed(1)},${a.toFixed(1)} ${(x-z).toFixed(1)},${b.toFixed(1)} ${(x+z).toFixed(1)},${b.toFixed(1)}" fill="${col}" stroke="#08090b" stroke-width="1"><title>${esc((TRADE_WORD[e.kind]||e.kind)+' '+numText(e.shares,4)+' at '+pxText(e.price)+' MB, '+stamp(e.t))}</title></polygon>`}
  s+='</g>'}
 // lines with a tag on the price scale: the price now, your average entry and your open orders in this stock; tags that
 // would overlap are moved apart
 const tags=[];
 if(price)tags.push({p:price,bg:'#4cc3cc',t:pxText(price)+' MB',dash:'4 4',w:1});
 if(avg)tags.push({p:avg,bg:'#e3b341',t:'Avg '+pxText(avg),dash:'2 4',w:1.5});
 for(const o of(S&&S.orders||[]).filter(o=>o.ticker===selectedTicker)){const k=ORDER_TAG[o.kind]||['Order','#7d8a93'];tags.push({p:o.trigger,bg:k[1],t:k[0]+' '+pxText(o.trigger),dash:'6 3',w:1})}
 const shown=tags.map(g=>Object.assign(g,{y:y(g.p)})).filter(g=>g.y>=padT-1&&g.y<=padT+PH+1).sort((a,b)=>a.y-b.y);
 shown.forEach((g,i)=>{g.ly=i&&g.y-shown[i-1].ly<19?shown[i-1].ly+19:g.y});
 for(const g of shown)s+=`<line x1="${padL}" y1="${g.y.toFixed(1)}" x2="${axisX}" y2="${g.y.toFixed(1)}" stroke="${g.bg}" stroke-width="${g.w}" stroke-dasharray="${g.dash}" stroke-linecap="round"/>`
  +`<rect x="${axisX+1}" y="${(g.ly-9).toFixed(1)}" width="${CH.padR-2}" height="18" rx="2" fill="${g.bg}"/><text x="${axisX+5}" y="${(g.ly+4).toFixed(1)}" fill="#08090b" font-size="11" font-weight="600">${esc(g.t)}</text>`;
 return s+'</svg>'}
const TRADE_WORD={buy:'Bought',sell:'Sold',short:'Shorted',cover:'Covered',margin_call:'Closed by a margin call:'};
const ORDER_TAG={stop_loss:['SL','#f25c54'],take_profit:['TP','#3ad07a'],limit_buy:['Buy at','#9aa7b0'],limit_sell:['Sell at','#9aa7b0']};
function scheduleChart(){if(rafPending)return;rafPending=true;requestAnimationFrame(()=>{rafPending=false;drawChart()})}
function scheduleDelistedChart(){const D=company&&company.delisted;const wrap=$('chart-wrap');if(!wrap||!D||typeof D!=='object')return;wrap.querySelector('.svgslot').innerHTML=candleSvg(chartCandles,D.final_price,0)}
function drawChart(){
 const wrap=$('chart-wrap');if(!wrap||!S)return;
 const st=S.byT[selectedTicker];if(!st){if(delistedView)scheduleDelistedChart();return}
 const h=S.holdings.find(x=>x.ticker===selectedTicker);
 const candles=chartCandles.length?liveCandles(st.price):[];
 wrap.querySelector('.svgslot').innerHTML=candleSvg(candles,st.price,h?h.avg:0);
 drawChartInfo();drawIndBar();drawToolbar();drawRisk();drawChartOpts();updateXh();const fit=$('z-fit');if(fit)fit.hidden=!yMan;
 const tk=selectedTicker+'|'+(h?h.shares.toFixed(6):0)+'|'+(S.orders||[]).length;if(tk!==myTradesKey){myTradesKey=tk;loadMyTrades()}}
// your trades in this stock, from the money ledger (GET /api/history?ticker=), fetched again whenever your position changes
async function loadMyTrades(){if(!token||guest)return;const tk=selectedTicker;
 const d=await api('/api/history?ticker='+encodeURIComponent(tk)+'&limit=300&kind=buy,sell,short,cover,margin_call');
 if(d&&Array.isArray(d.events)&&tk===selectedTicker){myTrades=d.events;myTradesFor=tk;scheduleChart()}}
function drawChartOpts(){const sel=$('c-type');if(!sel)return;
 if(!sel.options.length)sel.innerHTML=Object.entries(CTYPES).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');
 if(sel.value!==chartType)sel.value=chartType;$('c-log').classList.toggle('on',logScale);
 const tb=$('c-trades');tb.classList.toggle('on',showTrades);tb.style.display=token&&!guest?'':'none'}
// the crosshair (TA-B1): it follows the mouse; on a touch screen a tap puts it on a candle, and a drag moves the chart.
// The readout above the chart shows that candle (or the newest one) and every indicator's value there.
let xhPt=null,tapAt=null;
function crossTime(t){const d=new Date(t*1000),o={month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'};
 if(chartPeriod==='30s')o.second='2-digit';if(['1d','1mo','1y'].includes(chartPeriod)){delete o.hour;delete o.minute}if(chartPeriod==='1mo'||chartPeriod==='1y')o.year='numeric';
 return d.toLocaleString([],o)}
const fmtVal=v=>Math.abs(v)>=1e5?volText(v):Math.abs(v)<1?v.toFixed(4):v.toFixed(2);
function drawReadout(i){const el=$('xread'),g=chartGeom;if(!el)return;if(!g||!g.n){setHtml(el,'');return}
 const c=g.drawn[i],prev=i?g.drawn[i-1].c:c.o,ch=(c.c/prev-1)*100;
 let html=`<span>${esc(crossTime(c.t))}</span><span>O <b>${pxText(c.o)}</b></span><span>H <b>${pxText(c.h)}</b></span><span>L <b>${pxText(c.l)}</b></span><span>C <b>${pxText(c.c)}</b></span><span class="${ch>0?'up':ch<0?'dn':''}">${ch>0?'+':''}${ch.toFixed(2)}%</span><span>Vol <b>${volText(g.raw[i].v)}</b></span>`;
 for(const r of g.reads){const v=r.v[i];if(!nv(v))html+=`<span style="color:${r.c}">${esc(r.label)} ${esc(r.fmt?r.fmt(v):fmtVal(v))}</span>`}
 setHtml(el,html)}
function showXh(cx,cy){
 const wrap=$('chart-wrap'),svg=wrap&&wrap.querySelector('svg'),g=chartGeom,xh=$('xh');if(!svg||!g||!xh)return;
 const r=svg.getBoundingClientRect(),wr=wrap.getBoundingClientRect(),k=r.width/CH.w,sx=(cx-r.left)/k,sy=(cy-r.top)/k;
 if(sx<g.padL||sx>g.axisX||sy<g.padT||sy>g.h-CH.padB){hideXh();return}
 xhPt={x:cx,y:cy};const i=Math.max(0,Math.min(g.n-1,Math.round(g.n-1-(g.x0-sx)/g.slot))),X=g.x0-(g.n-1-i)*g.slot,ox=r.left-wr.left,oy=r.top-wr.top;
 const v=xh.querySelector('.xh-v'),hz=xh.querySelector('.xh-h'),bp=xh.querySelector('.xh-p'),bt=xh.querySelector('.xh-t');
 xh.hidden=false;
 Object.assign(v.style,{left:(ox+X*k)+'px',top:(oy+g.padT*k)+'px',height:((g.h-CH.padB-g.padT)*k)+'px'});
 Object.assign(hz.style,{top:(oy+sy*k)+'px',left:(ox+g.padL*k)+'px',width:((g.axisX-g.padL)*k)+'px'});
 const inP=sy<=g.padT+g.PH;bp.hidden=!inP;if(inP){bp.textContent=pxText(g.pAt(sy));Object.assign(bp.style,{left:(ox+(g.axisX+1)*k)+'px',top:(oy+sy*k-9)+'px'})}
 bt.textContent=crossTime(g.drawn[i].t);Object.assign(bt.style,{left:(ox+X*k)+'px',top:(oy+(g.h-CH.padB+3)*k)+'px'});
 drawReadout(i)}
function hideXh(){xhPt=null;const xh=$('xh');if(xh)xh.hidden=true;const g=chartGeom;if(g&&g.n)drawReadout(g.n-1)}
function updateXh(){if(xhPt)showXh(xhPt.x,xhPt.y);else{const g=chartGeom;if(g&&g.n)drawReadout(g.n-1)}}
function zoomAt(factor,mx){
 const n=chartCandles.length||1,oldSlot=baseSlot(n)*zoom,nz=clampZoom(zoom*factor,n),newSlot=baseSlot(n)*nz;
 const x0=newestX(),u=(mx-x0)/oldSlot;zoom=nz;pan+=(mx-u*newSlot)-x0;scheduleChart()}
function svgX(ev){const el=$('chart-wrap').querySelector('svg');if(!el)return newestX();const r=el.getBoundingClientRect();return(ev.clientX-r.left)*CH.w/r.width}
function resetZoom(){zoom=1;pan=0;yMan=null;scheduleChart()}
function selectPeriod(p){chartPeriod=p;chartCandles=[];zoom=1;pan=0;yMan=null;document.querySelectorAll('.periods button').forEach(b=>b.classList.toggle('active',b.dataset.p===p));requestHistory();drawChart()}

// ---------- chart indicators ----------
// Every indicator the chart can show, worked out on the page from the candles (nothing here touches the game). Each one
// says where it is drawn (over the price, in its own panel under the volume, or on the volume), whether it is free or a
// Pro tool, and what it means. The Indicators box searches them by name, group and description.
const nv=x=>x===null||x===undefined||!isFinite(x);
function colsOf(c){return{o:c.map(x=>x.o),h:c.map(x=>x.h),l:c.map(x=>x.l),c:c.map(x=>x.c),v:c.map(x=>x.v||0),t:c.map(x=>x.t)}}
const pick=(a,b,f)=>a.map((x,i)=>nv(x)||nv(b[i])?null:f(x,b[i]));
function smaOf(v,n){const o=new Array(v.length).fill(null);let s=0,k=0;for(let i=0;i<v.length;i++){const x=v[i];if(nv(x)){s=0;k=0;continue}s+=x;k++;if(k>n){s-=v[i-n];k=n}if(k>=n)o[i]=s/n}return o}
function emaOf(v,n){const o=new Array(v.length).fill(null),a=2/(n+1);let e=null,k=0;for(let i=0;i<v.length;i++){const x=v[i];if(nv(x))continue;e=e===null?x:x*a+e*(1-a);k++;if(k>=n)o[i]=e}return o}
function rmaOf(v,n){const o=new Array(v.length).fill(null);let a=null,k=0,s=0;for(let i=0;i<v.length;i++){const x=v[i];if(nv(x))continue;if(a===null){s+=x;k++;if(k===n){a=s/n;o[i]=a}}else{a=(a*(n-1)+x)/n;o[i]=a}}return o}
function wmaOf(v,n){const o=new Array(v.length).fill(null),den=n*(n+1)/2;for(let i=n-1;i<v.length;i++){let s=0,ok=true;for(let j=0;j<n;j++){const x=v[i-j];if(nv(x)){ok=false;break}s+=(n-j)*x}if(ok)o[i]=s/den}return o}
function hmaOf(v,n){const a=wmaOf(v,Math.round(n/2)),b=wmaOf(v,n);return wmaOf(pick(a,b,(x,y)=>2*x-y),Math.round(Math.sqrt(n)))}
function demaOf(v,n){const e1=emaOf(v,n),e2=emaOf(e1,n);return pick(e1,e2,(x,y)=>2*x-y)}
function temaOf(v,n){const e1=emaOf(v,n),e2=emaOf(e1,n),e3=emaOf(e2,n);return e1.map((x,i)=>nv(x)||nv(e2[i])||nv(e3[i])?null:3*x-3*e2[i]+e3[i])}
function sdOf(v,n,m){return v.map((_,i)=>{if(nv(m[i])||i<n-1)return null;let s=0;for(let j=i-n+1;j<=i;j++)s+=(v[j]-m[i])**2;return Math.sqrt(s/n)})}
function winOf(v,n,f){const o=new Array(v.length).fill(null);for(let i=n-1;i<v.length;i++){let ok=true;const w=[];for(let j=i-n+1;j<=i;j++){if(nv(v[j])){ok=false;break}w.push(v[j])}if(ok)o[i]=f(w)}return o}
const hiOf=(v,n)=>winOf(v,n,w=>Math.max(...w)),loOf=(v,n)=>winOf(v,n,w=>Math.min(...w)),sumOf=(v,n)=>winOf(v,n,w=>w.reduce((a,b)=>a+b,0));
function trOf(C){return C.c.map((_,i)=>i?Math.max(C.h[i]-C.l[i],Math.abs(C.h[i]-C.c[i-1]),Math.abs(C.l[i]-C.c[i-1])):C.h[i]-C.l[i])}
function atrSeries(C,n=14){return rmaOf(trOf(C),n)}
function atrOf(c,n=14){const a=atrSeries(colsOf(c),n);for(let i=a.length-1;i>=0;i--)if(!nv(a[i]))return a[i];return null}
function rsiOf(v,n=14){const o=new Array(v.length).fill(null);let g=0,l=0;for(let i=1;i<v.length;i++){const d=v[i]-v[i-1],up=Math.max(d,0),dn=Math.max(-d,0);if(i<=n){g+=up/n;l+=dn/n;if(i===n)o[i]=l?100-100/(1+g/l):100}else{g=(g*(n-1)+up)/n;l=(l*(n-1)+dn)/n;o[i]=l?100-100/(1+g/l):100}}return o}
function stochOf(C,n=14,k=3,d=3){const hh=hiOf(C.h,n),ll=loOf(C.l,n),raw=C.c.map((x,i)=>nv(hh[i])?null:(hh[i]===ll[i]?50:100*(x-ll[i])/(hh[i]-ll[i]))),K=smaOf(raw,k);return{K,D:smaOf(K,d)}}
function stochRsiOf(v,n=14){const r=rsiOf(v,n),hh=hiOf(r,n),ll=loOf(r,n),st=r.map((x,i)=>nv(hh[i])?null:(hh[i]===ll[i]?50:100*(x-ll[i])/(hh[i]-ll[i]))),K=smaOf(st,3);return{K,D:smaOf(K,3)}}
function cciOf(C,n=20){const tp=C.c.map((x,i)=>(C.h[i]+C.l[i]+x)/3),m=smaOf(tp,n);return tp.map((x,i)=>{if(nv(m[i]))return null;let md=0;for(let j=i-n+1;j<=i;j++)md+=Math.abs(tp[j]-m[i]);md/=n;return md?(x-m[i])/(0.015*md):0})}
function willrOf(C,n=14){const hh=hiOf(C.h,n),ll=loOf(C.l,n);return C.c.map((x,i)=>nv(hh[i])?null:(hh[i]===ll[i]?-50:-100*(hh[i]-x)/(hh[i]-ll[i])))}
function rocOf(v,n=12){return v.map((x,i)=>i<n||!v[i-n]?null:100*(x/v[i-n]-1))}
function momOf(v,n=10){return v.map((x,i)=>i<n?null:x-v[i-n])}
function adxOf(C,n=14){const len=C.c.length,pdm=new Array(len).fill(null),mdm=new Array(len).fill(null),tr=trOf(C);tr[0]=null;
 for(let i=1;i<len;i++){const up=C.h[i]-C.h[i-1],dn=C.l[i-1]-C.l[i];pdm[i]=up>dn&&up>0?up:0;mdm[i]=dn>up&&dn>0?dn:0}
 const atr=rmaOf(tr,n),sp=rmaOf(pdm,n),sm=rmaOf(mdm,n),P=pick(sp,atr,(a,b)=>b?100*a/b:0),M=pick(sm,atr,(a,b)=>b?100*a/b:0);
 const dx=pick(P,M,(a,b)=>a+b?100*Math.abs(a-b)/(a+b):0);return{P,M,A:rmaOf(dx,n)}}
function obvOf(C){const o=[0];for(let i=1;i<C.c.length;i++)o.push(o[i-1]+Math.sign(C.c[i]-C.c[i-1])*C.v[i]);return o}
function mfiOf(C,n=14){const tp=C.c.map((x,i)=>(C.h[i]+C.l[i]+x)/3),pos=tp.map((x,i)=>i&&x>tp[i-1]?x*C.v[i]:0),neg=tp.map((x,i)=>i&&x<tp[i-1]?x*C.v[i]:0);
 pos[0]=neg[0]=null;const ps=sumOf(pos,n),ns=sumOf(neg,n);return pick(ps,ns,(a,b)=>b?100-100/(1+a/b):100)}
function cmfOf(C,n=20){const mfv=C.c.map((x,i)=>{const r=C.h[i]-C.l[i];return r?((x-C.l[i])-(C.h[i]-x))/r*C.v[i]:0}),a=sumOf(mfv,n),b=sumOf(C.v,n);return pick(a,b,(x,y)=>y?x/y:0)}
function aoOf(C){const m=C.h.map((x,i)=>(x+C.l[i])/2);return pick(smaOf(m,5),smaOf(m,34),(a,b)=>a-b)}
function aroonOf(C,n=25){const up=[],dn=[];for(let i=0;i<C.c.length;i++){if(i<n){up.push(null);dn.push(null);continue}let hi=i,lo=i;for(let j=i-n;j<=i;j++){if(C.h[j]>=C.h[hi])hi=j;if(C.l[j]<=C.l[lo])lo=j}up.push(100*(n-(i-hi))/n);dn.push(100*(n-(i-lo))/n)}return{up,dn}}
function trixOf(v,n=15){const e3=emaOf(emaOf(emaOf(v,n),n),n),t=e3.map((x,i)=>i&&!nv(x)&&!nv(e3[i-1])&&e3[i-1]?100*(x/e3[i-1]-1):null);return{t,s:emaOf(t,9)}}
function uoOf(C){const bp=[],tr=[];for(let i=0;i<C.c.length;i++){const pc=i?C.c[i-1]:C.c[i];bp.push(C.c[i]-Math.min(C.l[i],pc));tr.push(Math.max(C.h[i],pc)-Math.min(C.l[i],pc))}
 const av=n=>pick(sumOf(bp,n),sumOf(tr,n),(a,b)=>b?a/b:0),a7=av(7),a14=av(14),a28=av(28);return a7.map((x,i)=>nv(x)||nv(a14[i])||nv(a28[i])?null:100*(4*x+2*a14[i]+a28[i])/7)}
function bbOf(v,n=20,k=2){const m=smaOf(v,n),sd=sdOf(v,n,m);return{m,u:pick(m,sd,(a,b)=>a+k*b),l:pick(m,sd,(a,b)=>a-k*b)}}
function hvOf(v,secs,n=20){const r=v.map((x,i)=>i&&v[i-1]>0&&x>0?Math.log(x/v[i-1]):null),m=smaOf(r,n),sd=sdOf(r,n,m),yr=Math.sqrt(365*1800/Math.max(1,secs));return sd.map(x=>nv(x)?null:x*yr*100)}
function vwapOf(c){const o=[];let pv=0,vv=0,day=null;for(const x of c){const d=Math.floor(x.t/1800);if(d!==day){day=d;pv=0;vv=0}const tp=(x.h+x.l+x.c)/3,v=x.v||0;pv+=tp*v;vv+=v;o.push(vv?pv/vv:tp)}return o}
function vwmaOf(C,n=20){const pv=sumOf(C.c.map((x,i)=>x*C.v[i]),n),vv=sumOf(C.v,n);return pick(pv,vv,(a,b)=>b?a/b:null)}
function psarOf(C,step=.02,max=.2){const n=C.c.length,o=new Array(n).fill(null);if(n<3)return o;let up=C.c[1]>=C.c[0],af=step,ep=up?C.h[0]:C.l[0],sar=up?C.l[0]:C.h[0];
 for(let i=1;i<n;i++){sar=sar+af*(ep-sar);if(up){sar=Math.min(sar,C.l[i-1],i>1?C.l[i-2]:C.l[i-1]);if(C.l[i]<sar){up=false;sar=ep;ep=C.l[i];af=step}else if(C.h[i]>ep){ep=C.h[i];af=Math.min(max,af+step)}}
  else{sar=Math.max(sar,C.h[i-1],i>1?C.h[i-2]:C.h[i-1]);if(C.h[i]>sar){up=true;sar=ep;ep=C.h[i];af=step}else if(C.l[i]<ep){ep=C.l[i];af=Math.min(max,af+step)}}o[i]=sar}return o}
function superTrendOf(C,n=10,k=3){const atr=atrSeries(C,n),len=C.c.length,up=new Array(len).fill(null),dn=new Array(len).fill(null);let fu=null,fl=null,trend=1;
 for(let i=0;i<len;i++){if(nv(atr[i]))continue;const m=(C.h[i]+C.l[i])/2,bu=m+k*atr[i],bl=m-k*atr[i],pc=i?C.c[i-1]:C.c[i];
  fu=fu===null||bu<fu||pc>fu?bu:fu;fl=fl===null||bl>fl||pc<fl?bl:fl;
  if(trend===1&&C.c[i]<fl)trend=-1;else if(trend===-1&&C.c[i]>fu)trend=1;if(trend===1)up[i]=fl;else dn[i]=fu}return{up,dn}}
function ichimokuOf(C){const mid=(a,b)=>pick(a,b,(x,y)=>(x+y)/2),n=C.c.length,ten=mid(hiOf(C.h,9),loOf(C.l,9)),kij=mid(hiOf(C.h,26),loOf(C.l,26)),sa0=mid(ten,kij),sb0=mid(hiOf(C.h,52),loOf(C.l,52));
 const shift=(a,s)=>{const o=new Array(n+26).fill(null);a.forEach((x,i)=>{if(i+s>=0&&i+s<o.length)o[i+s]=x});return o};
 return{ten,kij,sa:shift(sa0,26),sb:shift(sb0,26),chi:shift(C.c,-26)}}
function linregOf(v,n=100){const len=v.length;if(len<10)return null;const k=Math.min(n,len),i0=len-k;let sx=0,sy=0,sxx=0,sxy=0;for(let i=0;i<k;i++){sx+=i;sy+=v[i0+i];sxx+=i*i;sxy+=i*v[i0+i]}
 const b=(k*sxy-sx*sy)/(k*sxx-sx*sx||1),a=(sy-b*sx)/k;let ss=0;for(let i=0;i<k;i++)ss+=(v[i0+i]-(a+b*i))**2;return{i0,i1:len-1,p0:a,p1:a+b*(k-1),sd:Math.sqrt(ss/k)}}
function pivotsOf(c){const out=[],days=[];for(let i=0;i<c.length;i++){const d=Math.floor(c[i].t/1800),last=days[days.length-1];if(!last||last.d!==d)days.push({d,i0:i,i1:i,h:c[i].h,l:c[i].l,c:c[i].c});else{last.i1=i;last.h=Math.max(last.h,c[i].h);last.l=Math.min(last.l,c[i].l);last.c=c[i].c}}
 for(let j=1;j<days.length;j++){const p=days[j-1],P=(p.h+p.l+p.c)/3;out.push({i0:days[j].i0,i1:days[j].i1,lv:[['P',P],['R1',2*P-p.l],['S1',2*P-p.h],['R2',P+(p.h-p.l)],['S2',P-(p.h-p.l)]]})}return out}
const FIBS=[0,.236,.382,.5,.618,.786,1];
// [id, name, group, place (price | panel | volume), Pro?, colour, what it means, extra search words, how it is worked out
//  (from the candles C, the chart x and the settings P), the settings it has and their defaults]
// P.n is the period (the length); some have a second (m), a signal line (s) or a width (k). The page fills P from the
// player's settings (indSet) over these defaults, so every indicator can be tuned without changing this list.
const MA_COL={10:'#f2cc60',20:'#e3b341',50:'#bc8cff',100:'#ff7b72',200:'#79c0ff',9:'#56d364',12:'#39c5cf',26:'#a5d6ff'};
const maLine=(f,lab,col)=>(C,x,P)=>({lines:[{v:f(C.c,P.n),c:col,label:lab+' '+P.n}]});
const EMA_COL=['#56d364','#39c5cf','#2dd4bf','#a5d6ff','#d2a8ff','#ffa657','#f778ba'];
const IND=[
 ...[10,20,50,100,200].map(n=>['sma'+n,'SMA '+n,'Moving averages','price',0,MA_COL[n],`Simple moving average of the last ${n} closes: the average price, which smooths out the noise. Price above a rising average is the classic sign of an uptrend${n===200?'; the 200 is the long-term trend most traders watch':''}.`,'simple moving average ma',maLine(smaOf,'SMA',MA_COL[n]),{n}]),
 ...[9,12,20,26,50,100,200].map((n,j)=>['ema'+n,'EMA '+n,'Moving averages','price',0,EMA_COL[j],`Exponential moving average of ${n} closes: weights recent prices more, so it turns sooner than an SMA of the same length.`,'exponential moving average ma',maLine(emaOf,'EMA',EMA_COL[j]),{n}]),
 ['wma20','WMA 20','Moving averages','price',1,'#ffd33d','Weighted moving average of 20 closes: the newest close counts 20 times, the oldest once.','weighted ma',maLine(wmaOf,'WMA','#ffd33d'),{n:20}],
 ['hma20','Hull MA 20','Moving averages','price',1,'#7ee787','Hull moving average: very smooth and with little lag, built from weighted averages.','hull ma',maLine(hmaOf,'HMA','#7ee787'),{n:20}],
 ['dema20','DEMA 20','Moving averages','price',1,'#ff9bce','Double exponential moving average: less lag than an EMA of the same length.','double exponential ma',maLine(demaOf,'DEMA','#ff9bce'),{n:20}],
 ['tema20','TEMA 20','Moving averages','price',1,'#b392f0','Triple exponential moving average: even less lag than DEMA.','triple exponential ma',maLine(temaOf,'TEMA','#b392f0'),{n:20}],
 ['vwma20','VWMA 20','Moving averages','price',1,'#f0883e','Volume-weighted moving average: closes on busy candles count more.','volume weighted ma',(C,x,P)=>({lines:[{v:vwmaOf(C,P.n),c:'#f0883e',label:'VWMA '+P.n}]}),{n:20}],
 ['bb','Bollinger Bands','Bands and channels','price',1,'#7d8a93','The 20-candle average plus and minus two standard deviations. The bands widen when the market is volatile and squeeze before big moves.','bollinger volatility bands',(C,x,P)=>{const b=bbOf(C.c,P.n,P.k);return{lines:[{v:b.m,c:'#7d8a93',label:`BB ${P.n},${P.k}`,dash:'2 3'},{v:b.u,c:'#7d8a93',dash:'4 3'},{v:b.l,c:'#7d8a93',dash:'4 3'}],fills:[{a:b.u,b:b.l,c:'#7d8a9314'}]}},{n:20,k:2}],
 ['keltner','Keltner Channels','Bands and channels','price',1,'#56d4dd','The 20-candle EMA plus and minus two average true ranges: a channel that widens with volatility.','keltner channel atr',(C,x,P)=>{const m=emaOf(C.c,P.n),a=atrSeries(C,10);return{lines:[{v:m,c:'#56d4dd',label:'Keltner '+P.n,dash:'2 3'},{v:pick(m,a,(x,y)=>x+P.k*y),c:'#56d4dd'},{v:pick(m,a,(x,y)=>x-P.k*y),c:'#56d4dd'}],fills:[{a:pick(m,a,(x,y)=>x+P.k*y),b:pick(m,a,(x,y)=>x-P.k*y),c:'#56d4dd10'}]}},{n:20,k:2}],
 ['donchian','Donchian Channels','Bands and channels','price',1,'#3ad07a','The highest high and lowest low of the last 20 candles: a break of the channel is a classic breakout signal.','donchian breakout channel turtle',(C,x,P)=>{const u=hiOf(C.h,P.n),l=loOf(C.l,P.n);return{lines:[{v:u,c:'#3ad07a',label:'Donchian '+P.n},{v:l,c:'#f25c54'},{v:pick(u,l,(a,b)=>(a+b)/2),c:'#7d8a93',dash:'3 3'}]}},{n:20}],
 ['env','Envelopes','Bands and channels','price',1,'#d29922','The 20-candle average shifted 2.5% up and down: a simple band for stretched prices.','envelope percent bands',(C,x,P)=>{const m=smaOf(C.c,P.n);return{lines:[{v:m.map(x=>nv(x)?null:x*(1+P.k/100)),c:'#d29922',label:`Env ${P.k}%`},{v:m.map(x=>nv(x)?null:x*(1-P.k/100)),c:'#d29922'}]}},{n:20,k:2.5}],
 ['linreg','Regression channel','Bands and channels','price',1,'#a371f7','A straight line fitted through the last 100 closes, with lines two standard deviations either side.','linear regression trend channel',(C,x,P)=>{const r=linregOf(C.c,P.n);return r?{segs:[{i0:r.i0,i1:r.i1,p0:r.p0,p1:r.p1,c:'#a371f7',label:'Regression '+P.n},{i0:r.i0,i1:r.i1,p0:r.p0+2*r.sd,p1:r.p1+2*r.sd,c:'#a371f7',dash:'4 3'},{i0:r.i0,i1:r.i1,p0:r.p0-2*r.sd,p1:r.p1-2*r.sd,c:'#a371f7',dash:'4 3'}]}:{}},{n:100}],
 ['vwap','VWAP','Volume','price',1,'#f778ba','Volume-weighted average price since the game day began: where the average trade happened today (intraday charts only).','volume weighted average price intraday',(C,x)=>x.secs<1800?{lines:[{v:vwapOf(x.candles),c:'#f778ba',label:'VWAP'}]}:{note:'VWAP: intraday charts only'}],
 ['psar','Parabolic SAR','Trend','price',1,'#e3b341','Dots under the price in an uptrend and over it in a downtrend; when the price crosses them they flip. Often used as a trailing stop.','parabolic stop and reverse sar',C=>({dots:[{v:psarOf(C),c:'#e3b341',label:'SAR'}]})],
 ['supertrend','SuperTrend','Trend','price',1,'#3ad07a','A trailing line, green under the price in an uptrend and red over it in a downtrend, three average true ranges away.','supertrend atr trailing stop',(C,x,P)=>{const s=superTrendOf(C,P.n,P.k);return{lines:[{v:s.up,c:'#3ad07a',label:'SuperTrend'},{v:s.dn,c:'#f25c54'}]}},{n:10,k:3}],
 ['ichimoku','Ichimoku Cloud','Trend','price',1,'#4cc3cc','Ichimoku: the conversion and base lines, the cloud projected 26 candles ahead, and the lagging line. Price above the cloud is bullish, below it bearish.','ichimoku kinko hyo cloud tenkan kijun',C=>{const k=ichimokuOf(C);return{lines:[{v:k.ten,c:'#4cc3cc',label:'Ichimoku'},{v:k.kij,c:'#f25c54'},{v:k.chi,c:'#3ad07a99'},{v:k.sa,c:'#3ad07a88'},{v:k.sb,c:'#f25c5488'}],fills:[{a:k.sa,b:k.sb,c:'#3ad07a18',c2:'#f25c5418'}]}}],
 ['pivots','Pivot points','Levels','price',1,'#d2a8ff','Classic floor pivots from the previous game day: the pivot P and support and resistance levels S1, S2, R1, R2 that day traders watch (intraday charts).','pivot points support resistance floor',(C,x)=>x.secs<1800?{pivots:pivotsOf(x.candles)}:{note:'Pivots: intraday charts only'}],
 ['autofib','Auto Fibonacci','Levels','price',0,'#e3b341','Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%) between the highest and lowest price on the screen: where a pullback often pauses.','fibonacci fib retracement levels golden ratio',(C,x)=>({autofib:1})],
 ['rsi','RSI 14','Momentum','panel',0,'#4cc3cc','Relative strength index (14): above 70 is often called overbought, below 30 oversold.','relative strength index oscillator',(C,x,P)=>({lines:[{v:rsiOf(C.c,P.n),c:'#4cc3cc'}],range:[0,100],refs:[70,30]}),{n:14}],
 ['stoch','Stochastic','Momentum','panel',0,'#4cc3cc','Stochastic (14, 3, 3): where the close sits in the range of the last 14 candles. Above 80 is stretched up, below 20 stretched down; %K crossing %D is a signal.','stochastic oscillator %k %d',(C,x,P)=>{const s=stochOf(C,P.n,P.m,P.s);return{lines:[{v:s.K,c:'#4cc3cc',label:'%K'},{v:s.D,c:'#f0883e',label:'%D'}],range:[0,100],refs:[80,20]}},{n:14,m:3,s:3}],
 ['mom','Momentum','Momentum','panel',0,'#56d364','Momentum (10): this close minus the close 10 candles ago. Above zero the price is higher than it was.','momentum',(C,x,P)=>({lines:[{v:momOf(C.c,P.n),c:'#56d364'}],refs:[0]}),{n:10}],
 ['macd','MACD','Momentum','panel',1,'#4cc3cc','MACD (12, 26, 9): the gap between two moving averages, its signal line and the histogram between them.','moving average convergence divergence',(C,x,P)=>{const e1=emaOf(C.c,P.n),e2=emaOf(C.c,P.m),m=pick(e1,e2,(a,b)=>a-b),s=emaOf(m,P.s);return{lines:[{v:m,c:'#4cc3cc',label:'MACD'},{v:s,c:'#f0883e',label:'Signal'}],hist:pick(m,s,(a,b)=>a-b),refs:[0]}},{n:12,m:26,s:9}],
 ['stochrsi','Stochastic RSI','Momentum','panel',1,'#4cc3cc','The stochastic formula applied to RSI: a faster, more sensitive overbought/oversold gauge.','stochastic rsi stochrsi',(C,x,P)=>{const s=stochRsiOf(C.c,P.n);return{lines:[{v:s.K,c:'#4cc3cc',label:'%K'},{v:s.D,c:'#f0883e',label:'%D'}],range:[0,100],refs:[80,20]}},{n:14}],
 ['cci','CCI 20','Momentum','panel',1,'#d29922','Commodity channel index (20): how far the typical price is from its average; beyond +100 or -100 is unusual.','commodity channel index',(C,x,P)=>({lines:[{v:cciOf(C,P.n),c:'#d29922'}],refs:[100,-100,0]}),{n:20}],
 ['willr','Williams %R','Momentum','panel',1,'#bc8cff','Williams %R (14): like the stochastic, on a scale of 0 to -100; above -20 overbought, below -80 oversold.','williams percent r',(C,x,P)=>({lines:[{v:willrOf(C,P.n),c:'#bc8cff'}],range:[-100,0],refs:[-20,-80]}),{n:14}],
 ['roc','Rate of change','Momentum','panel',1,'#39c5cf','Rate of change (12): the percentage change over the last 12 candles.','roc rate of change percent',(C,x,P)=>({lines:[{v:rocOf(C.c,P.n),c:'#39c5cf'}],refs:[0],fmt:v=>v.toFixed(2)+'%'}),{n:12}],
 ['ao','Awesome Oscillator','Momentum','panel',1,'#3ad07a','Awesome oscillator: the 5-candle average of the midpoint minus the 34-candle one, as a histogram. Crossing zero shows a change in momentum.','awesome oscillator bill williams',C=>({hist:aoOf(C),refs:[0]})],
 ['trix','TRIX','Momentum','panel',1,'#ff7b72','TRIX (15): the rate of change of a triple-smoothed EMA, with a 9-candle signal line. Filters out small moves.','trix triple exponential',(C,x,P)=>{const t=trixOf(C.c,P.n);return{lines:[{v:t.t,c:'#ff7b72',label:'TRIX'},{v:t.s,c:'#7d8a93',label:'Signal'}],refs:[0]}},{n:15}],
 ['uo','Ultimate Oscillator','Momentum','panel',1,'#a5d6ff','Ultimate oscillator (7, 14, 28): buying pressure over three lengths blended into one; above 70 overbought, below 30 oversold.','ultimate oscillator',C=>({lines:[{v:uoOf(C),c:'#a5d6ff'}],range:[0,100],refs:[70,30]})],
 ['adx','ADX / DMI','Trend','panel',1,'#e3b341','Average directional index (14) with +DI and -DI: ADX above 25 means a strong trend (in either direction); +DI over -DI means the bulls lead.','adx dmi directional movement trend strength',(C,x,P)=>{const a=adxOf(C,P.n);return{lines:[{v:a.A,c:'#e3b341',label:'ADX'},{v:a.P,c:'#3ad07a',label:'+DI'},{v:a.M,c:'#f25c54',label:'-DI'}],range:[0,100],refs:[25]}},{n:14}],
 ['aroon','Aroon','Trend','panel',1,'#3ad07a','Aroon (25): how recently the highest high and the lowest low happened. Up above down means an uptrend.','aroon up down',(C,x,P)=>{const a=aroonOf(C,P.n);return{lines:[{v:a.up,c:'#3ad07a',label:'Up'},{v:a.dn,c:'#f25c54',label:'Down'}],range:[0,100],refs:[70,30]}},{n:25}],
 ['atr','ATR 14','Volatility','panel',1,'#ffa657','Average true range (14): how far the price usually moves in one candle. Useful for placing stops (1.5 to 2 ATR is common).','average true range volatility stop',(C,x,P)=>({lines:[{v:atrSeries(C,P.n),c:'#ffa657'}]}),{n:14}],
 ['hv','Historical volatility','Volatility','panel',1,'#ff9bce','Historical volatility (20): how much the price has been moving, as a yearly percentage in game time.','historical volatility standard deviation',(C,x,P)=>({lines:[{v:hvOf(C.c,x.secs,P.n),c:'#ff9bce'}],fmt:v=>v.toFixed(1)+'%'}),{n:20}],
 ['bbw','Bollinger Bandwidth','Volatility','panel',1,'#7d8a93','How wide the Bollinger bands are, as a percentage of the average. Very low values (a squeeze) often come before a big move.','bollinger bandwidth squeeze',(C,x,P)=>{const b=bbOf(C.c,P.n);return{lines:[{v:b.m.map((m,i)=>nv(m)||nv(b.u[i])||!m?null:100*(b.u[i]-b.l[i])/m),c:'#7d8a93'}],fmt:v=>v.toFixed(2)+'%'}},{n:20}],
 ['bbpct','Bollinger %B','Volatility','panel',1,'#7d8a93','Where the close sits between the Bollinger bands: 1 at the upper band, 0 at the lower one.','bollinger percent b',(C,x,P)=>{const b=bbOf(C.c,P.n);return{lines:[{v:C.c.map((c,i)=>nv(b.u[i])||b.u[i]===b.l[i]?null:(c-b.l[i])/(b.u[i]-b.l[i])),c:'#7d8a93'}],refs:[1,0],fmt:v=>v.toFixed(2)}},{n:20}],
 ['obv','On-balance volume','Volume','panel',1,'#56d364','On-balance volume: adds the volume of up candles and subtracts that of down candles. Rising OBV with a flat price can mean buying is building up.','obv on balance volume accumulation',C=>({lines:[{v:obvOf(C),c:'#56d364'}],fmt:v=>volText(v)})],
 ['mfi','Money Flow Index','Volume','panel',1,'#d2a8ff','Money flow index (14): an RSI that also weighs volume. Above 80 overbought, below 20 oversold.','mfi money flow index volume rsi',(C,x,P)=>({lines:[{v:mfiOf(C,P.n),c:'#d2a8ff'}],range:[0,100],refs:[80,20]}),{n:14}],
 ['cmf','Chaikin Money Flow','Volume','panel',1,'#79c0ff','Chaikin money flow (20): whether volume has come in on closes near the highs (above zero, buying) or near the lows (below zero, selling).','chaikin money flow cmf',(C,x,P)=>({lines:[{v:cmfOf(C,P.n),c:'#79c0ff'}],refs:[0],fmt:v=>v.toFixed(3)}),{n:20}],
 ['volma','Volume average','Volume','volume',0,'#e3b341','The 20-candle average of volume, drawn over the volume bars: a bar well above it is unusual activity.','volume moving average ma',(C,x,P)=>({lines:[{v:smaOf(C.v,P.n),c:'#e3b341',label:'Vol MA '+P.n}]}),{n:20}],
];
const IND_BY=Object.fromEntries(IND.map(x=>[x[0],x]));
const ind=new Set(lsGet('ms_ind',['sma20']).filter(k=>IND_BY[k]));
// each indicator's settings: the player's values (indSet) over its defaults (the tenth item above). `src` picks the price
// the indicator is worked out from (close by default), `c` its colour.
let indSet=lsGet('ms_indset',{});if(!indSet||typeof indSet!=='object')indSet={};
const SRC_OK=new Set(IND.filter(x=>x[2]==='Moving averages'&&x[0]!=='vwma20').map(x=>x[0]).concat(['bb','env','linreg','rsi','mom','macd','stochrsi','roc','trix','hv','bbw','bbpct','keltner']));
const SRC_NAMES={c:'Close',o:'Open',h:'High',l:'Low',hl2:'(High + Low) / 2',hlc3:'(High + Low + Close) / 3',ohlc4:'(Open + High + Low + Close) / 4'};
const PARAM_NAMES={n:'Length',m:'Second length',s:'Signal',k:'Width'};
const PARAM_BY={macd:{n:'Fast',m:'Slow',s:'Signal'},stoch:{n:'Length',m:'%K smoothing',s:'%D smoothing'},bb:{k:'Width (standard deviations)'},keltner:{k:'Width (ATRs)'},env:{k:'Width (%)'},supertrend:{k:'ATR multiple'}};
const indP=d=>Object.assign({},d[9]||{},indSet[d[0]]||{});
const indCol=d=>(indSet[d[0]]&&indSet[d[0]].c)||d[5];
function indLabel(d){const P=indP(d),D=d[9]||{},keys=Object.keys(D);if(!keys.some(k=>P[k]!==D[k]))return d[1];
 if(keys.length===1&&/\d/.test(d[1]))return d[1].replace(/\d+(\.\d+)?/,P.n);
 return d[1].replace(/ \d+$/,'')+' ('+keys.map(k=>P[k]).join(', ')+')'}
function srcOf(C,src){const L=C.c.length,o=new Array(L);for(let i=0;i<L;i++){const O=C.o[i],H=C.h[i],Lo=C.l[i],Cl=C.c[i];
  o[i]=src==='o'?O:src==='h'?H:src==='l'?Lo:src==='hl2'?(H+Lo)/2:src==='hlc3'?(H+Lo+Cl)/3:src==='ohlc4'?(O+H+Lo+Cl)/4:Cl}return o}
// run one indicator with its settings: the chosen source in place of the close, and its colour on the lines drawn in its own
function runInd(d,C,ctx){const P=indP(d),Cx=P.src&&P.src!=='c'&&SRC_OK.has(d[0])?Object.assign({},C,{c:srcOf(C,P.src)}):C;
 let r={};try{r=d[8](Cx,ctx,P)||{}}catch(e){r={}}
 if(P.c&&P.c!==d[5]){for(const ln of r.lines||[])if(ln.c===d[5])ln.c=P.c;for(const dt of r.dots||[])if(dt.c===d[5])dt.c=P.c;for(const sg of r.segs||[])if(sg.c===d[5])sg.c=P.c}
 return r}
// the chart set-up follows a signed-in player to any browser (chartprefs.py); a visitor keeps it in this browser only
let prefsLoaded=false,prefsT=null;
function savePrefs(){lsSet('ms_ind',[...ind]);lsSet('ms_indset',indSet);lsSet('ms_ctype',chartType);lsSet('ms_log',logScale);lsSet('ms_trades',showTrades);
 if(!token||guest)return;clearTimeout(prefsT);
 prefsT=setTimeout(()=>postJson('/api/chart',{ind:[...ind],set:indSet,ctype:chartType,log:logScale,trades:showTrades},{'X-Token':token}),800)}
async function loadPrefs(){
 if(prefsLoaded||!token||guest)return;prefsLoaded=true;
 const d=await api('/api/chart'),p=d&&d.prefs;if(!p)return;
 if(!p.ind){savePrefs();return}                 // nothing kept for this account yet: it starts from this browser's set-up
 ind.clear();p.ind.filter(k=>IND_BY[k]).forEach(k=>ind.add(k));indSet=p.set||{};
 if(CTYPES[p.ctype])chartType=p.ctype;logScale=!!p.log;if(p.trades!==undefined)showTrades=!!p.trades;
 lsSet('ms_ind',[...ind]);lsSet('ms_indset',indSet);lsSet('ms_ctype',chartType);lsSet('ms_log',logScale);lsSet('ms_trades',showTrades);
 const bar=$('ind-bar');if(bar)bar._k='';drawIndBar();drawChartOpts();scheduleChart()}
const isPro=()=>!!(S&&S.pro);
const indOn=k=>ind.has(k)&&IND_BY[k]&&(!IND_BY[k][4]||isPro());
const activeOf=place=>IND.filter(x=>x[3]===place&&indOn(x[0]));
function volText(v){v=Number(v||0);const a=Math.abs(v),s=v<0?'-':'';return a>=1e9?s+(a/1e9).toFixed(2)+'B':a>=1e6?s+(a/1e6).toFixed(2)+'M':a>=1e3?s+(a/1e3).toFixed(1)+'K':s+a.toFixed(0)}

// ---------- the Indicators box: search every indicator, switch them on and off ----------
const ICON_IND='<svg viewBox="0 0 18 18" width="15" height="15" style="vertical-align:-3px;margin-right:4px" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 14l4-5 3 3 6-8"/><path d="M2 16h14"/></svg>';
let indFilter='all';
function drawIndBar(){
 const el=$('ind-bar');if(!el)return;const pro=isPro();
 const key=[...ind].join()+pro+JSON.stringify(indSet);if(el._k===key)return;el._k=key;
 const act=IND.filter(x=>ind.has(x[0]));
 el.innerHTML=`<button class="chip ind-open" id="ind-open" aria-haspopup="true">${ICON_IND}Indicators${act.length?` <b>${act.length}</b>`:''}</button>`
  +act.map(x=>{const locked=x[4]&&!pro;return `<span class="ind-chip${locked?' locked':''}" style="--c:${indCol(x)}" title="${esc(x[6])}${locked?' (a Pro tool: it shows again when Pro is on)':''}"><i></i>${esc(indLabel(x))}${locked?' <small>PRO</small>':''}<button data-ind-cfg="${x[0]}" aria-label="Settings for ${esc(x[1])}" title="Settings">${ICON_CFG}</button><button data-ind-off="${x[0]}" aria-label="Remove ${esc(x[1])}">&times;</button></span>`}).join('')
  +(act.length?'':'<span class="hint" style="margin:0">Moving averages, RSI, MACD, Bollinger bands, Fibonacci and 40 more: open Indicators and search.</span>')}
function drawIndPop(){
 const pop=$('ind-pop');if(!pop||pop.hidden)return;const pro=isPro(),q=($('ind-q').value||'').trim().toLowerCase();
 const words=q.split(/\s+/).filter(Boolean);
 const inTab=x=>indFilter==='all'||(indFilter==='free'&&!x[4])||(indFilter==='pro'&&x[4])||(indFilter==='on'&&ind.has(x[0]));
 const match=(x,full)=>words.every(w=>(x[1]+' '+x[2]+' '+x[7]+(full?' '+x[6]:'')).toLowerCase().includes(w));
 let rows=IND.filter(x=>inTab(x)&&match(x,false));if(!rows.length&&words.length)rows=IND.filter(x=>inTab(x)&&match(x,true));
 const groups={};rows.forEach(x=>(groups[x[2]]=groups[x[2]]||[]).push(x));
 $('ind-tabs').querySelectorAll('[data-ind-filter]').forEach(b=>b.classList.toggle('on',b.dataset.indFilter===indFilter));
 setHtml($('ind-list'),rows.length?Object.entries(groups).map(([g,xs])=>`<div class="ind-group">${esc(g)}</div>`+xs.map(x=>`<button class="ind-row ${ind.has(x[0])?'on':''}" data-ind="${x[0]}"><span class="ind-dot" style="background:${x[5]}"></span><span class="ind-name">${esc(x[1])}${ind.has(x[0])?' <span class="up">✓</span>':''}</span><span class="ind-tag ${x[4]?'pro':'free'}">${x[4]?'PRO':'FREE'}</span><small title="${esc(x[6])}">${esc(x[6])}${x[4]&&!pro?' Pro members only.':''}</small></button>`).join('')).join('')
  :'<p class="hint" style="margin:8px">Nothing matches. Try “average”, “RSI”, “volume”, “trend” or “fib”.</p>')}
function openIndPop(open){const pop=$('ind-pop');if(!pop)return;pop.hidden=!open;if(open){$('ind-q').value='';drawIndPop();setTimeout(()=>$('ind-q').focus(),0)}}
document.addEventListener('click',e=>{
 if(e.target.closest('#ind-open')){const pop=$('ind-pop');openIndPop(pop&&pop.hidden);return}
 const tab=e.target.closest('[data-ind-filter]');if(tab){indFilter=tab.dataset.indFilter;drawIndPop();return}
 const b=e.target.closest('[data-ind]');
 if(b){const k=b.dataset.ind,def=IND_BY[k];if(!def)return;
  if(def[4]&&!isPro()&&!ind.has(k)){toast(`${def[1]} is a Pro tool: see the Shop`,false,3500);return}
  if(ind.has(k))ind.delete(k);else ind.add(k);savePrefs();drawIndBar();drawIndPop();scheduleChart();return}
 const off=e.target.closest('[data-ind-off]');
 if(off){ind.delete(off.dataset.indOff);savePrefs();drawIndBar();drawIndPop();openIndCfg(null);scheduleChart();return}
 const cfg=e.target.closest('[data-ind-cfg]');
 if(cfg){openIndCfg(cfgFor===cfg.dataset.indCfg?null:cfg.dataset.indCfg,cfg);return}
 if(e.target.closest('[data-cfg-reset]')){delete indSet[cfgFor];savePrefs();openIndCfg(cfgFor);drawIndBar();scheduleChart();return}
 if(e.target.closest('[data-cfg-done]')){openIndCfg(null);return}
 const cp=$('ind-cfg');if(cp&&!cp.hidden&&!e.target.closest('#ind-cfg'))openIndCfg(null);
 const pop=$('ind-pop');if(pop&&!pop.hidden&&!e.target.closest('#ind-pop'))pop.hidden=true});
document.addEventListener('input',e=>{if(e.target.id==='ind-q')drawIndPop();if(e.target.dataset&&e.target.dataset.cfg)cfgInput(e.target)});
// the settings of one indicator: a small box under its chip, applied as you type
let cfgFor=null;
const ICON_CFG='<svg viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 4h7M12 4h2M2 12h2M7 12h7"/><circle cx="10.5" cy="4" r="1.6"/><circle cx="5.5" cy="12" r="1.6"/></svg>';
function openIndCfg(k,anchor){
 const box=$('ind-cfg');if(!box)return;cfgFor=k;if(!k){box.hidden=true;return}
 const d=IND_BY[k],P=indP(d),D=d[9]||{},names=Object.assign({},PARAM_NAMES,PARAM_BY[k]||{});
 box.innerHTML=`<b>${esc(d[1])}</b>`+Object.keys(D).map(p=>`<label>${esc(names[p])}<input type="number" data-cfg="${p}" value="${P[p]}" min="${p==='k'?0.1:1}" max="${p==='k'?20:500}" step="${p==='k'?0.1:1}"></label>`).join('')
  +(SRC_OK.has(k)?`<label>Source<select data-cfg="src">${Object.entries(SRC_NAMES).map(([v,n])=>`<option value="${v}" ${(P.src||'c')===v?'selected':''}>${esc(n)}</option>`).join('')}</select></label>`:'')
  +`<label>Colour<input type="color" data-cfg="c" value="${indCol(d)}"></label>`
  +`<div class="bar" style="margin:6px 0 0"><button data-cfg-reset>Reset</button><button class="buy" data-cfg-done>Done</button></div>`;
 box.hidden=false;
 if(anchor){const bx=$('chart-box').getBoundingClientRect(),ar=anchor.getBoundingClientRect();box.style.left=Math.max(0,Math.min(bx.width-260,ar.left-bx.left-150))+'px';box.style.top=(ar.bottom-bx.top+6)+'px'}}
function cfgInput(el){
 const k=cfgFor,d=IND_BY[k];if(!d)return;const p=el.dataset.cfg,cur=Object.assign({},indSet[k]||{});
 if(p==='src'){if(el.value==='c')delete cur.src;else cur.src=el.value}
 else if(p==='c'){if(el.value.toLowerCase()===d[5].toLowerCase())delete cur.c;else cur.c=el.value.toLowerCase()}
 else{let v=parseFloat(el.value);if(!isFinite(v))return;v=p==='k'?Math.min(20,Math.max(0.1,v)):Math.round(Math.min(500,Math.max(1,v)));if(v===(d[9]||{})[p])delete cur[p];else cur[p]=v}
 if(Object.keys(cur).length)indSet[k]=cur;else delete indSet[k];
 savePrefs();drawIndBar();scheduleChart()}

// ---------- drawing tools ----------
// Drawings are kept per stock in this browser (localStorage), in time and price, so they stay on the right candles
// when you zoom, pan or change the candle size. A floating toolbar (drag it by its grip) picks the tool; with the
// arrow you can select a drawing, drag it or its handles, and delete it (Delete key or the bin).
const SVGI=b=>`<svg viewBox="0 0 18 18">${b}</svg>`,DOT=(x,y)=>`<circle cx="${x}" cy="${y}" r="1.7" fill="currentColor" stroke="none"/>`;
const ICONS={cursor:SVGI('<path d="M5 2.5l9 7.2-4.3.5 2.6 4.6-1.9 1-2.6-4.6L5 14z" fill="currentColor" stroke="none"/>'),
 hline:SVGI('<path d="M1.5 9h15"/>'+DOT(9,9)),vline:SVGI('<path d="M9 1.5v15"/>'+DOT(9,9)),
 trend:SVGI('<path d="M3.5 14.5l11-11"/>'+DOT(3.5,14.5)+DOT(14.5,3.5)),ray:SVGI('<path d="M3.5 14.5L16 3M16 3h-4.2M16 3v4.2"/>'+DOT(3.5,14.5)),
 rect:SVGI('<rect x="2.5" y="4.5" width="13" height="9" rx="1"/>'),circle:SVGI('<circle cx="9" cy="9" r="6.3"/>'+DOT(9,9)),
 fib:SVGI('<path d="M2 3h14M2 6.5h14M2 10h14M2 15h14"/><path d="M4 15L14 3" stroke-dasharray="1.6 1.8"/>'),
 channel:SVGI('<path d="M2 11.5L12.5 3M5.5 15.5L16 7"/><path d="M3.7 13.5L14.2 5" stroke-dasharray="1.6 1.8"/>'+DOT(2,11.5)+DOT(12.5,3)),
 fibext:SVGI('<path d="M1.5 15.5l4.5-9 3.5 5"/><path d="M10.5 11.5h6M10.5 7.5h6M10.5 3h6" stroke-dasharray="1.6 1.6"/>'),
 brush:SVGI('<path d="M2 13.5c2.6-4.5 4.2-6.6 6.3-4.6s1.7 4.3 3.7 2.6S15 6 16.3 4.6"/>'),
 path:SVGI('<path d="M2.5 14.5l3.8-8.2 4.2 5 5-7.6"/>'+DOT(6.3,6.3)+DOT(10.5,11.3)),
 hs:SVGI('<path d="M1 14.5l2.6-5.3 2 3.2 3.4-9 3.4 9 2-3.2 2.6 5.3"/><path d="M3.5 12.4h11" stroke-dasharray="1.6 1.8"/>'),
 long:SVGI('<rect x="2.5" y="2.5" width="13" height="7" rx="1" fill="#3ad07a40" stroke="#3ad07a"/><rect x="2.5" y="9.5" width="13" height="6" rx="1" fill="#f25c5440" stroke="#f25c54"/>'),
 short:SVGI('<rect x="2.5" y="2.5" width="13" height="6" rx="1" fill="#f25c5440" stroke="#f25c54"/><rect x="2.5" y="8.5" width="13" height="7" rx="1" fill="#3ad07a40" stroke="#3ad07a"/>'),
 text:SVGI('<path d="M3.5 4h11M9 4v11M6.5 15h5"/>'),
 trash:SVGI('<path d="M3 5h12M7 5V3h4v2M4.8 5l.9 10.5h6.6L13.2 5"/>'),
 eye:SVGI('<path d="M1.5 9S4.3 4 9 4s7.5 5 7.5 5-2.8 5-7.5 5S1.5 9 1.5 9z"/><circle cx="9" cy="9" r="2.2"/>'),
 eyeoff:SVGI('<path d="M1.5 9S4.3 4 9 4s7.5 5 7.5 5-2.8 5-7.5 5S1.5 9 1.5 9z"/><path d="M3 15L15 3"/>'),
 clear:SVGI('<path d="M12.5 2.5l-5 8M3 10.5h8.5l1.7 5H1.5z"/>'),
 unfold:SVGI('<path d="M5.5 7l3.5 3.5L12.5 7"/>'),
 grip:'<svg viewBox="0 0 8 18"><circle cx="2.3" cy="4" r="1.2"/><circle cx="5.7" cy="4" r="1.2"/><circle cx="2.3" cy="9" r="1.2"/><circle cx="5.7" cy="9" r="1.2"/><circle cx="2.3" cy="14" r="1.2"/><circle cx="5.7" cy="14" r="1.2"/></svg>'};
// [tool, name, what to do]
const TOOLS=[['cursor','Select','Select a drawing to move it or delete it (Esc)'],
 ['hline','Horizontal line','Click to mark a support or resistance level'],['vline','Vertical line','Click to mark a moment'],
 ['trend','Trend line','Drag from one point to another (or click twice) to draw a trend line'],['ray','Ray','Like a trend line, but it carries on to the right'],
 ['channel','Parallel channel','Click the two ends of the first line, then a third point for the width of the channel'],
 ['rect','Box','Drag across a range or a zone to box it'],['circle','Circle','Drag from the centre outwards'],
 ['fib','Fibonacci retracement','Drag from the start of a swing to its end: the 23.6% to 78.6% levels are where pullbacks often pause'],
 ['fibext','Fibonacci extension','Click the start of a move, its end and the end of the pullback after it: the extension levels (61.8% to 261.8%) are common targets'],
 ['brush','Brush','Hold and draw freely'],['path','Path','Click each point; double-click, press Enter or tap the last point again to finish'],
 ['hs','Head and shoulders','Click the 7 points: start, left shoulder, neckline, head, neckline, right shoulder, end'],
 ['long','Long position','Click your entry: the green box is the target, the red box the stop; drag their edges to change them'],
 ['short','Short position','Click your entry: the green box is the target below, the red box the stop above'],
 ['text','Text note','Click where the note goes, then type it']];
const TOOL_BY=Object.fromEntries(TOOLS.map(x=>[x[0],x]));
const TWO_POINT=new Set(['trend','ray','rect','circle','fib']),ONE_CLICK=new Set(['hline','vline','long','short','text']),THREE_CLICK=new Set(['channel','fibext']);
const FIBEXT=[0,.618,1,1.272,1.618,2,2.618],FIB_COLS=['#7d8a93','#f25c54','#e3b341','#3ad07a','#4cc3cc','#bc8cff','#7d8a93'];
const D_COL={hline:'#c3a3ff',vline:'#c3a3ff',trend:'#4cc3cc',ray:'#4cc3cc',channel:'#4cc3cc',fibext:'#e3b341',rect:'#4cc3cc',circle:'#f778ba',fib:'#e3b341',brush:'#ffa657',path:'#56d364',hs:'#d2a8ff',text:'#dce3e8'};
let tool='cursor',drawSel=null,placing=null,dragD=null,drawList=[],drawFor=null,drawHidden=lsGet('ms_draw_hide',false);
function loadDrawings(){
 if(drawFor===selectedTicker)return;drawFor=selectedTicker;drawSel=null;placing=null;
 const all=lsGet('ms_draw',{});drawList=Array.isArray(all[selectedTicker])?all[selectedTicker]:[];
 const old=lsGet('ms_lines',{});                    // the levels drawn before the toolbar existed become horizontal lines
 if(Array.isArray(old[selectedTicker])&&old[selectedTicker].length){const t=chartCandles.length?chartCandles[chartCandles.length-1].t:engineNow();
  for(const p of old[selectedTicker])drawList.push({id:newId(),type:'hline',pts:[{t,p:Number(p)}]});delete old[selectedTicker];lsSet('ms_lines',old);saveDrawings()}}
function saveDrawings(){const all=lsGet('ms_draw',{});all[selectedTicker]=drawList.slice(-80);lsSet('ms_draw',all);pushDrawings()}
// a signed-in player's drawings are kept on the server too (chartprefs.py), so they follow them to another browser or a
// phone; the first time a stock is opened, whatever this browser has is sent up
let drawSynced=null,drawT=null;
function pushDrawings(){if(!token||guest||!selectedTicker)return;const tk=selectedTicker,list=drawList.slice(-80);clearTimeout(drawT);
 drawT=setTimeout(()=>postJson('/api/drawings/'+encodeURIComponent(tk),list,{'X-Token':token}),800)}
async function syncDrawings(){const tk=selectedTicker;if(!tk||!token||guest||drawSynced===tk)return;drawSynced=tk;
 const d=await api('/api/drawings/'+encodeURIComponent(tk));if(!d||!Array.isArray(d.drawings)||tk!==selectedTicker)return;
 loadDrawings();
 if(d.saved){drawList=d.drawings;drawSel=null;const all=lsGet('ms_draw',{});all[tk]=drawList;lsSet('ms_draw',all);scheduleChart()}
 else if(drawList.length)pushDrawings()}
const newId=()=>Date.now().toString(36)+Math.random().toString(36).slice(2,6);
const G=()=>chartGeom;
const gX=t=>{const g=G();return g.x0-(g.tLast-t)/g.secs*g.slot},gY=p=>G().y(p);
const gT=x=>{const g=G();return g.tLast-(g.x0-x)/g.slot*g.secs},gP=y=>G().pAt(y);
const pct=(a,b)=>(b>=a?'+':'')+((b/a-1)*100).toFixed(2)+'%';
function drawOne(d,sel){
 const g=G(),col=d.c||D_COL[d.type]||'#c3a3ff',w=sel?2.2:1.5,P=d.pts.map(p=>[gX(p.t),gY(p.p)]),L=g.padL,R=g.axisX,hit=(dd)=>`<path d="${dd}" fill="none" stroke="transparent" stroke-width="12"/>`;
 let s='',hd=[];const seg=(a,b,extra='')=>`M${a[0].toFixed(1)} ${a[1].toFixed(1)}L${b[0].toFixed(1)} ${b[1].toFixed(1)}`+extra;
 const poly=pts=>'M'+pts.map(p=>p[0].toFixed(1)+' '+p[1].toFixed(1)).join('L');
 switch(d.type){
  case 'hline':{const yy=P[0][1];const dd=`M${L} ${yy.toFixed(1)}L${R} ${yy.toFixed(1)}`;s+=hit(dd)+`<path d="${dd}" stroke="${col}" stroke-width="${w}" stroke-dasharray="6 4"/><text x="${L+4}" y="${(yy-4).toFixed(1)}" fill="${col}" font-size="10.5">${pxText(d.pts[0].p)}</text>`;hd=[[Math.min(R-20,Math.max(L+20,P[0][0])),yy]];break}
  case 'vline':{const xx=P[0][0],dd=`M${xx.toFixed(1)} ${g.padT}L${xx.toFixed(1)} ${g.padT+g.PH}`;s+=hit(dd)+`<path d="${dd}" stroke="${col}" stroke-width="${w}" stroke-dasharray="6 4"/>`;hd=[[xx,g.padT+g.PH/2]];break}
  case 'trend':case 'ray':{let b=P[1];if(d.type==='ray'&&P.length>1){const dx=P[1][0]-P[0][0],dy=P[1][1]-P[0][1];if(Math.abs(dx)>1e-6){const k=((dx>0?R:L)-P[0][0])/dx;if(k>1)b=[P[0][0]+dx*k,P[0][1]+dy*k]}}
   const dd=seg(P[0],b);s+=hit(dd)+`<path d="${dd}" stroke="${col}" stroke-width="${w}"/>`;hd=P;break}
  case 'rect':{const x=Math.min(P[0][0],P[1][0]),y=Math.min(P[0][1],P[1][1]),ww=Math.abs(P[1][0]-P[0][0]),hh=Math.abs(P[1][1]-P[0][1]);
   s+=`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${ww.toFixed(1)}" height="${hh.toFixed(1)}" fill="${col}1f" stroke="${col}" stroke-width="${w}"/>`;hd=P;break}
  case 'circle':{const rx=Math.abs(P[1][0]-P[0][0]),ry=Math.abs(P[1][1]-P[0][1]);s+=`<ellipse cx="${P[0][0].toFixed(1)}" cy="${P[0][1].toFixed(1)}" rx="${rx.toFixed(1)}" ry="${ry.toFixed(1)}" fill="${col}14" stroke="${col}" stroke-width="${w}"/>`;hd=P;break}
  case 'fib':{const a=d.pts[0].p,b=d.pts[1].p,x1=Math.min(P[0][0],P[1][0]),cols=['#7d8a93','#f25c54','#e3b341','#3ad07a','#4cc3cc','#bc8cff','#7d8a93'];
   s+=hit(seg(P[0],P[1]))+`<path d="${seg(P[0],P[1])}" stroke="${col}88" stroke-width="1" stroke-dasharray="4 4"/>`;
   FIBS.forEach((r,j)=>{const p=b-r*(b-a),yy=gY(p);if(j){const yp=gY(b-FIBS[j-1]*(b-a));s+=`<rect x="${x1.toFixed(1)}" y="${Math.min(yy,yp).toFixed(1)}" width="${Math.max(0,R-x1).toFixed(1)}" height="${Math.abs(yy-yp).toFixed(1)}" fill="${cols[j]}12"/>`}
    s+=`<path d="M${x1.toFixed(1)} ${yy.toFixed(1)}L${R} ${yy.toFixed(1)}" stroke="${cols[j]}" stroke-width="${sel?1.6:1.1}"/><text x="${(x1+4).toFixed(1)}" y="${(yy-3).toFixed(1)}" fill="${cols[j]}" font-size="10">${r} (${pxText(p)})</text>`});hd=P;break}
  case 'channel':{const A=P[0],B=P[1]||P[0],Q=P[2]||B,dx=B[0]-A[0],k=Math.abs(dx)>1e-6?(B[1]-A[1])/dx:0,off=P.length>2?Q[1]-(A[1]+k*(Q[0]-A[0])):0;
   const A2=[A[0],A[1]+off],B2=[B[0],B[1]+off],M1=[A[0],A[1]+off/2],M2=[B[0],B[1]+off/2];
   s+=(P.length>2?`<path d="M${A[0].toFixed(1)} ${A[1].toFixed(1)}L${B[0].toFixed(1)} ${B[1].toFixed(1)}L${B2[0].toFixed(1)} ${B2[1].toFixed(1)}L${A2[0].toFixed(1)} ${A2[1].toFixed(1)}Z" fill="${col}14" stroke="none"/>`+hit(seg(A2,B2))+`<path d="${seg(A2,B2)}" stroke="${col}" stroke-width="${w}"/><path d="${seg(M1,M2)}" stroke="${col}" stroke-width="1" stroke-dasharray="4 4"/>`:'')
    +hit(seg(A,B))+`<path d="${seg(A,B)}" stroke="${col}" stroke-width="${w}"/>`;hd=P;break}
  case 'fibext':{const a=d.pts[0].p,b=(d.pts[1]||d.pts[0]).p,c=(d.pts[2]||d.pts[1]||d.pts[0]).p,x1=(P[2]||P[1]||P[0])[0];
   s+=hit(poly(P))+`<path d="${poly(P)}" fill="none" stroke="${col}99" stroke-width="1" stroke-dasharray="4 4"/>`;
   if(P.length>2)FIBEXT.forEach((r,j)=>{const p=c+r*(b-a);if(!(p>0))return;const yy=gY(p),fc=FIB_COLS[j%FIB_COLS.length];
    s+=`<path d="M${x1.toFixed(1)} ${yy.toFixed(1)}L${R} ${yy.toFixed(1)}" stroke="${fc}" stroke-width="${sel?1.6:1.1}"/><text x="${(x1+4).toFixed(1)}" y="${(yy-3).toFixed(1)}" fill="${fc}" font-size="10">${r} (${pxText(p)})</text>`});
   hd=P;break}
  case 'brush':case 'path':{const dd=poly(P);s+=hit(dd)+`<path d="${dd}" fill="none" stroke="${col}" stroke-width="${d.type==='brush'?w+.6:w}" stroke-linejoin="round" stroke-linecap="round"/>`;
   if(d.type==='path')for(const p of P)s+=`<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="2.2" fill="${col}"/>`;hd=d.type==='path'?P:[P[0]];break}
  case 'hs':{const dd=poly(P);s+=hit(dd)+`<path d="${dd}" fill="${col}14" stroke="${col}" stroke-width="${w}" stroke-linejoin="round"/>`;
   if(P.length>=5){const a=P[2],b=P[4],x0=P[0][0],x1=P[P.length-1][0],k=Math.abs(b[0]-a[0])>1e-6?(b[1]-a[1])/(b[0]-a[0]):0;s+=`<path d="M${x0.toFixed(1)} ${(a[1]+k*(x0-a[0])).toFixed(1)}L${x1.toFixed(1)} ${(a[1]+k*(x1-a[0])).toFixed(1)}" stroke="#f25c54" stroke-width="1.3" stroke-dasharray="5 4"/><text x="${(x1+4).toFixed(1)}" y="${(a[1]+k*(x1-a[0])+4).toFixed(1)}" fill="#f25c54" font-size="10">neckline</text>`}
   [[1,'Left shoulder'],[3,'Head'],[5,'Right shoulder']].forEach(([k,lab])=>{if(P[k])s+=`<text x="${P[k][0].toFixed(1)}" y="${(P[k][1]-7).toFixed(1)}" fill="${col}" font-size="10.5" text-anchor="middle">${lab}</text>`});hd=P;break}
  case 'long':case 'short':{const[e,tg,st]=d.pts,xa=P[0][0],xb=P[1][0],ye=P[0][1],yt=P[1][1],ys=P[2][1],x=Math.min(xa,xb),ww=Math.abs(xb-xa),rr=Math.abs(tg.p-e.p)/Math.max(1e-12,Math.abs(e.p-st.p));
   s+=`<rect x="${x.toFixed(1)}" y="${Math.min(ye,yt).toFixed(1)}" width="${ww.toFixed(1)}" height="${Math.abs(yt-ye).toFixed(1)}" fill="#3ad07a33" stroke="#3ad07a" stroke-width="${sel?1.4:1}"/><rect x="${x.toFixed(1)}" y="${Math.min(ye,ys).toFixed(1)}" width="${ww.toFixed(1)}" height="${Math.abs(ys-ye).toFixed(1)}" fill="#f25c5433" stroke="#f25c54" stroke-width="${sel?1.4:1}"/>`
    +`<path d="M${x.toFixed(1)} ${ye.toFixed(1)}L${(x+ww).toFixed(1)} ${ye.toFixed(1)}" stroke="#dce3e8" stroke-width="1.3"/>`
    +`<text x="${(x+4).toFixed(1)}" y="${(yt+(yt<ye?13:-5)).toFixed(1)}" fill="#3ad07a" font-size="10.5">Target ${pxText(tg.p)} (${pct(e.p,tg.p)}) · ${rr.toFixed(2)}R</text>`
    +`<text x="${(x+4).toFixed(1)}" y="${(ys+(ys<ye?13:-5)).toFixed(1)}" fill="#f25c54" font-size="10.5">Stop ${pxText(st.p)} (${pct(e.p,st.p)})</text>`
    +`<text x="${(x+4).toFixed(1)}" y="${(ye-4).toFixed(1)}" fill="#dce3e8" font-size="10.5">${d.type==='long'?'Long':'Short'} from ${pxText(e.p)}</text>`;
   hd=[P[0],[xb,yt],[xb,ys]];break}
  case 'text':{const t=d.text||'';s+=`<rect x="${(P[0][0]-3).toFixed(1)}" y="${(P[0][1]-14).toFixed(1)}" width="${(t.length*7+8).toFixed(1)}" height="19" rx="4" fill="${sel?'#ffffff14':'transparent'}"/><text x="${P[0][0].toFixed(1)}" y="${P[0][1].toFixed(1)}" fill="${col}" font-size="13">${esc(t)}</text>`;hd=[P[0]];break}}
 s=`<g data-dw="${d.id}">${s}</g>`;
 if(sel)hd.forEach((h,k)=>{s+=`<circle data-dh="${d.id}:${k}" cx="${h[0].toFixed(1)}" cy="${h[1].toFixed(1)}" r="5" fill="#08090b" stroke="${col}" stroke-width="1.6"/>`});
 return s}
function drawingsSvg(){if(!chartGeom)return '';loadDrawings();if(drawHidden&&!placing)return '';let s='';for(const d of drawList){try{s+=drawOne(d,d.id===drawSel||(placing&&placing.d===d))}catch(e){}}return s}
function svgPt(e){const el=$('chart-wrap').querySelector('svg');if(!el)return null;const r=el.getBoundingClientRect();return{x:(e.clientX-r.left)*CH.w/r.width,y:(e.clientY-r.top)*CH.h/r.height}}
const inPrice=pt=>{const g=G();return g&&pt.x>=g.padL&&pt.x<=g.axisX&&pt.y>=g.padT&&pt.y<=g.padT+g.PH};
const atPt=pt=>({t:gT(pt.x),p:Math.max(1e-9,gP(pt.y))});
function setTool(t){tool=t;placing=null;$('chart-wrap').classList.toggle('tool',t!=='cursor');drawToolbar();drawChartInfo()}
function finishPlacing(){const d=placing&&placing.d;placing=null;if(d){if(d.type==='path'||d.type==='brush'){if(d.pts.length<2)drawList=drawList.filter(x=>x!==d)}drawSel=drawList.includes(d)?d.id:null;saveDrawings()}setTool('cursor');scheduleChart()}
function startPlacing(pt){
 const g=G(),a=atPt(pt),d={id:newId(),type:tool,pts:[a]};
 if(TWO_POINT.has(tool)||tool==='path'||tool==='hs'||THREE_CLICK.has(tool))d.pts.push({...a});
 if(tool==='long'||tool==='short'){const atr=atrOf(chartCandles)||a.p*.01,dir=tool==='long'?1:-1;d.pts=[a,{t:a.t+20*g.secs,p:a.p+dir*3*atr},{t:a.t+20*g.secs,p:a.p-dir*1.5*atr}]}
 if(tool==='text'){const t=(prompt('Text for the note:')||'').trim().slice(0,80);if(!t){setTool('cursor');return}d.text=t}
 drawList.push(d);
 if(ONE_CLICK.has(tool)){placing={d};finishPlacing();return}
 placing={d,k:d.pts.length-1,down:pt};scheduleChart()}
// the price range around its middle: factor > 1 shows more prices (squeezes the candles), < 1 fewer (stretches them)
function scaleY(base,factor){
 if(chartGeom&&chartGeom.log&&base.lo>0){const mid=Math.sqrt(base.lo*base.hi),r=Math.max(Math.log(base.hi/base.lo)/2*factor,1e-5);yMan={lo:mid*Math.exp(-r),hi:mid*Math.exp(r)};scheduleChart();return}
 const mid=(base.lo+base.hi)/2,half=Math.max((base.hi-base.lo)/2*factor,Math.abs(mid)*1e-5||1e-9);yMan={lo:mid-half,hi:mid+half};scheduleChart()}
const onAxis=pt=>{const g=chartGeom;return g&&pt&&pt.x>g.axisX&&pt.y>=g.padT&&pt.y<=g.padT+g.PH};
const curY=()=>({lo:chartGeom.lo,hi:chartGeom.lo+chartGeom.span});
function chartDown(e){
 if(e.target.closest('.draw-tools'))return;
 tapAt=e.pointerType==='mouse'?null:{x:e.clientX,y:e.clientY};
 const wrap=$('chart-wrap'),pt=svgPt(e);
 if(!placing&&onAxis(pt)){axisDrag={y:e.clientY,base:curY()};wrap.classList.add('dragging');try{wrap.setPointerCapture(e.pointerId)}catch(err){}return}
 if(pt&&chartGeom){
  if(placing){const d=placing.d,last=d.pts[d.pts.length-2];
   if(d.type==='path'||d.type==='hs'||THREE_CLICK.has(d.type)){const lp=last?[gX(last.t),gY(last.p)]:null;
    if(d.type==='path'&&lp&&Math.hypot(lp[0]-pt.x,lp[1]-pt.y)<7){d.pts.pop();finishPlacing();return}
    d.pts[d.pts.length-1]=atPt(pt);if((d.type==='hs'&&d.pts.length>=7)||(THREE_CLICK.has(d.type)&&d.pts.length>=3)){finishPlacing();return}d.pts.push(atPt(pt));placing.k=d.pts.length-1;drawChartInfo();scheduleChart();return}
   d.pts[placing.k]=atPt(pt);finishPlacing();return}
  if(tool!=='cursor'&&inPrice(pt)){startPlacing(pt);if(tool==='brush'||placing){try{wrap.setPointerCapture(e.pointerId)}catch(err){}}return}
  const h=e.target.closest('[data-dh]'),dw=e.target.closest('[data-dw]');
  if(tool==='cursor'&&(h||dw)){const id=(h?h.dataset.dh.split(':')[0]:dw.dataset.dw),d=drawList.find(x=>x.id===id);
   if(d){drawSel=id;dragD={d,k:h?Number(h.dataset.dh.split(':')[1]):-1,pt,orig:d.pts.map(p=>({...p})),moved:false};try{wrap.setPointerCapture(e.pointerId)}catch(err){}drawToolbar();scheduleChart();return}}
  if(drawSel){drawSel=null;drawToolbar();scheduleChart()}}
 dragX=e.clientX;dragPan0=pan;dragY=e.clientY;dragYOn=!!yMan;dragY0=chartGeom?{lo:chartGeom.lo,hi:chartGeom.lo+chartGeom.span,PH:chartGeom.PH}:null;wrap.classList.add('dragging');try{wrap.setPointerCapture(e.pointerId)}catch(err){}}
function chartMove(e){
 const wrap=$('chart-wrap');
 if(axisDrag){scaleY(axisDrag.base,Math.exp((e.clientY-axisDrag.y)*0.006));return}
 if(placing&&chartGeom){const pt=svgPt(e);if(!pt)return;const d=placing.d;
  if(d.type==='brush'){if(e.buttons){const lp=d.pts[d.pts.length-1],l=[gX(lp.t),gY(lp.p)];if(Math.hypot(l[0]-pt.x,l[1]-pt.y)>=3&&d.pts.length<400)d.pts.push(atPt(pt))}}
  else d.pts[placing.k]=atPt(pt);scheduleChart();return}
 if(dragD&&chartGeom){const pt=svgPt(e);if(!pt)return;const g=G(),dt=(pt.x-dragD.pt.x)/g.slot*g.secs,dy=pt.y-dragD.pt.y,d=dragD.d,o=dragD.orig,k=dragD.k;dragD.moved=true;
  const mv=p=>Math.max(1e-9,gP(gY(p)+dy));        // (moved by the same height on the screen, on either scale)
  if(k<0||((d.type==='long'||d.type==='short')&&k===0))d.pts=o.map(p=>({t:p.t+dt,p:mv(p.p)}));
  else if(d.type==='long'||d.type==='short'){d.pts[k]={t:o[k].t+dt,p:mv(o[k].p)};const k2=k===1?2:1;d.pts[k2]={t:d.pts[k].t,p:o[k2].p}}
  else if(d.type==='hline')d.pts[0]={t:o[0].t,p:mv(o[0].p)};
  else d.pts[k]={t:o[k].t+dt,p:mv(o[k].p)};
  scheduleChart();return}
 if(dragX===null)return;const el=wrap.querySelector('svg'),r=el?el.getBoundingClientRect():null;pan=dragPan0+(e.clientX-dragX)*(r?CH.w/r.width:1);
 const dy=e.clientY-dragY;                    // up and down too: a clear vertical drag (8 px) takes the price scale off automatic
 if(dragY0&&(dragYOn||Math.abs(dy)>8)){dragYOn=true;const u=dy*(r?CH.h/r.height:1)/dragY0.PH;
  if(chartGeom&&chartGeom.log&&dragY0.lo>0){const f=Math.exp(u*Math.log(dragY0.hi/dragY0.lo));yMan={lo:dragY0.lo*f,hi:dragY0.hi*f}}
  else{const sh=u*(dragY0.hi-dragY0.lo);yMan={lo:dragY0.lo+sh,hi:dragY0.hi+sh}}}
 scheduleChart()}
function chartUp(e){
 const wrap=$('chart-wrap');
 if(tapAt){const t=tapAt;tapAt=null;if(Math.hypot(e.clientX-t.x,e.clientY-t.y)<8&&!placing&&tool==='cursor')setTimeout(()=>showXh(e.clientX,e.clientY),0);else hideXh()}
 if(axisDrag){axisDrag=null;wrap.classList.remove('dragging');return}
 if(placing){const d=placing.d;if(d.type==='brush'){finishPlacing();return}
  if(TWO_POINT.has(d.type)&&placing.down){const pt=svgPt(e);if(pt&&Math.hypot(pt.x-placing.down.x,pt.y-placing.down.y)>6){d.pts[placing.k]=atPt(pt);finishPlacing();return}placing.down=null}return}
 if(dragD){if(dragD.moved)saveDrawings();dragD=null;return}
 dragX=null;wrap.classList.remove('dragging')}
function deleteSelected(){if(!drawSel)return false;drawList=drawList.filter(x=>x.id!==drawSel);drawSel=null;saveDrawings();drawToolbar();scheduleChart();return true}
document.addEventListener('keydown',e=>{
 if(!$('chart-wrap'))return;const typing=/^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName||''));
 if(e.key==='Escape'){if(placing){const d=placing.d;if(d.type==='path'||d.type==='hs'){d.pts.pop();if(d.pts.length<2)drawList=drawList.filter(x=>x!==d);finishPlacing()}else{drawList=drawList.filter(x=>x!==d);placing=null;setTool('cursor');scheduleChart()}return}
  const pop=$('ind-pop');if(pop&&!pop.hidden){pop.hidden=true;return}
  if(chartFull){toggleFull(false);return}if(drawSel){drawSel=null;drawToolbar();scheduleChart();return}if(tool!=='cursor')setTool('cursor');return}
 if(typing)return;
 if(e.key==='Enter'&&placing&&placing.d.type==='path'){placing.d.pts.pop();finishPlacing();return}
 if((e.key==='Delete'||e.key==='Backspace')&&deleteSelected())e.preventDefault()});
function drawChartInfo(){const info=$('chart-info');if(!info)return;
 if(tool!=='cursor'){const t=TOOL_BY[tool];let msg=`${t[1]}: ${t[2]}.`;if(placing&&placing.d.type==='hs')msg+=` (${placing.d.pts.length-1} of 7)`;if(placing&&THREE_CLICK.has(placing.d.type))msg+=` (${placing.d.pts.length-1} of 3)`;info.textContent=msg+' Esc to stop.';return}
 info.textContent=`${chartCandles.length} candles · scroll to zoom, drag to move it in any direction, drag the prices on the right to stretch or squeeze them${yMan?' · price scale set by hand: Fit prices or double-click to fit':''}${drawList.length?` · ${drawList.length} drawing${drawList.length>1?'s':''}`:''}`}
// the floating toolbar: a small bar (grip, the arrow, the last tool used, a bin while a drawing is selected) and a
// drop-down with every tool, which closes again once a tool is picked
let tbOpen=false,lastTool=lsGet('ms_tb_last','trend');
function drawToolbar(){
 const el=$('draw-tools');if(!el)return;const key=[tool,drawSel,drawHidden,tbOpen,lastTool].join('|');if(el._k===key)return;el._k=key;
 const quick=TOOL_BY[tool!=='cursor'?tool:lastTool]?(tool!=='cursor'?tool:lastTool):'trend',q=TOOL_BY[quick];
 el.innerHTML=`<div class="dt-bar"><span class="dt-grip" title="Drag to move the toolbar">${ICONS.grip}</span>`
  +`<button class="dt-btn ${tool==='cursor'?'on':''}" data-tool="cursor" title="Select: click a drawing to move or delete it (Esc)" aria-label="Select">${ICONS.cursor}</button>`
  +`<button class="dt-btn ${tool===quick?'on':''}" data-tool="${quick}" title="${esc(q[1])}: ${esc(q[2])}" aria-label="${esc(q[1])}">${ICONS[quick]}</button>`
  +(drawSel?`<button class="dt-btn" data-dt="delete" title="Delete the selected drawing (Delete key)" aria-label="Delete the selected drawing">${ICONS.trash}</button>`:'')
  +`<button class="dt-btn dt-more ${tbOpen?'open':''}" data-dt="menu" title="${tbOpen?'Close the list':'All drawing tools'}" aria-label="All drawing tools" aria-expanded="${tbOpen}">${ICONS.unfold}</button></div>`
  +(tbOpen?`<div class="dt-menu">${TOOLS.map(([k,n,h])=>`<button class="dt-item ${tool===k?'on':''}" data-tool="${k}" title="${esc(h)}">${ICONS[k]}<span>${esc(n)}</span></button>`).join('')}`
   +`<div class="dt-acts"><button class="dt-item" data-dt="hide">${drawHidden?ICONS.eyeoff:ICONS.eye}<span>${drawHidden?'Show':'Hide'} drawings</span></button><button class="dt-item" data-dt="clear">${ICONS.clear}<span>Clear all</span></button></div></div>`:'');
 placeToolbar()}
function placeToolbar(){const el=$('draw-tools'),wrap=$('chart-wrap');if(!el||!wrap)return;const p=lsGet('ms_tb',{x:10,y:34}),bar=el.querySelector('.dt-bar')||el;
 const x=Math.max(0,Math.min(Math.max(0,wrap.clientWidth-bar.offsetWidth),p.x)),y=Math.max(0,Math.min(Math.max(0,wrap.clientHeight-bar.offsetHeight),p.y));
 el.style.left=x+'px';el.style.top=y+'px';el.classList.toggle('up',y>wrap.clientHeight/2);el.classList.toggle('right',x>wrap.clientWidth-300)}
function wireToolbar(el){
 let g=null;
 el.addEventListener('pointerdown',e=>{e.stopPropagation();if(!e.target.closest('.dt-grip'))return;g={x:e.clientX,y:e.clientY,l:el.offsetLeft,t:el.offsetTop};try{el.setPointerCapture(e.pointerId)}catch(err){}});
 el.addEventListener('pointermove',e=>{if(!g)return;const wrap=$('chart-wrap'),bar=el.querySelector('.dt-bar')||el,x=Math.max(0,Math.min(wrap.clientWidth-bar.offsetWidth,g.l+e.clientX-g.x)),y=Math.max(0,Math.min(wrap.clientHeight-bar.offsetHeight,g.t+e.clientY-g.y));el.style.left=x+'px';el.style.top=y+'px'});
 const end=()=>{if(!g)return;g=null;lsSet('ms_tb',{x:el.offsetLeft,y:el.offsetTop});placeToolbar()};el.addEventListener('pointerup',end);el.addEventListener('pointercancel',end);
 el.addEventListener('click',e=>{e.stopPropagation();const b=e.target.closest('[data-tool]');
  if(b){const k=b.dataset.tool;tbOpen=false;if(k!=='cursor'&&k!==lastTool){lastTool=k;lsSet('ms_tb_last',k)}setTool(tool===k&&k!=='cursor'&&!b.closest('.dt-menu')?'cursor':k);return}
  const a=e.target.closest('[data-dt]');if(!a)return;const act=a.dataset.dt;
  if(act==='menu'){tbOpen=!tbOpen;drawToolbar()}
  else if(act==='delete')deleteSelected();
  else if(act==='hide'){drawHidden=!drawHidden;lsSet('ms_draw_hide',drawHidden);tbOpen=false;drawToolbar();scheduleChart()}
  else if(act==='clear'){tbOpen=false;drawToolbar();if(drawList.length&&confirm(`Remove all ${drawList.length} drawing${drawList.length>1?'s':''} on ${selectedTicker}?`)){drawList=[];drawSel=null;saveDrawings();drawToolbar();scheduleChart()}}})}
document.addEventListener('click',e=>{if(tbOpen&&!e.target.closest('#draw-tools')){tbOpen=false;drawToolbar()}});
// ---------- the chart's size: drag the bar under it, or full screen ----------
function setPH(v){lsSet('ms_ph',Math.round(Math.max(160,Math.min(1400,v))));scheduleChart()}
function toggleFull(on){chartFull=on===undefined?!chartFull:on;const box=$('chart-box');if(box)box.classList.toggle('chart-full',chartFull);document.body.classList.toggle('noscroll',chartFull);
 const b=$('z-full');if(b)b.textContent=chartFull?'✕ Exit full screen':'⤢ Full screen';scheduleChart();setTimeout(placeToolbar,50)}
function wireChartSize(){
 const bar=$('chart-resize');let r=null;
 bar.addEventListener('pointerdown',e=>{if(chartFull)return;const el=$('chart-wrap').querySelector('svg');r={y:e.clientY,ph:chartPH(),sc:el?CH.w/el.getBoundingClientRect().width:1};try{bar.setPointerCapture(e.pointerId)}catch(err){}});
 bar.addEventListener('pointermove',e=>{if(r)setPH(r.ph+(e.clientY-r.y)*r.sc)});
 const end=()=>{r=null};bar.addEventListener('pointerup',end);bar.addEventListener('pointercancel',end);
 $('z-fit').onclick=()=>{yMan=null;scheduleChart()};
 $('z-full').onclick=()=>toggleFull()}
window.addEventListener('resize',()=>{if($('chart-wrap')){scheduleChart();placeToolbar()}});
function wireChart(wrap){
 wrap.addEventListener('pointerdown',chartDown);wrap.addEventListener('pointermove',chartMove);
 wrap.addEventListener('pointerup',chartUp);wrap.addEventListener('pointercancel',chartUp);
 wrap.addEventListener('pointermove',e=>{if(e.pointerType!=='mouse')return;if(e.buttons&&!placing)hideXh();else showXh(e.clientX,e.clientY)});
 wrap.addEventListener('pointerleave',e=>{if(e.pointerType==='mouse')hideXh()});
 wrap.addEventListener('dblclick',e=>{if(placing&&placing.d.type==='path'){const d=placing.d;d.pts.pop();const a=d.pts[d.pts.length-1],b=d.pts[d.pts.length-2];if(a&&b&&Math.abs(gX(a.t)-gX(b.t))<4&&Math.abs(gY(a.p)-gY(b.p))<4)d.pts.pop();finishPlacing()}
  else if(!placing&&yMan&&(onAxis(svgPt(e))||(tool==='cursor'&&!e.target.closest('[data-dw],.draw-tools')))){yMan=null;scheduleChart()}});
 wireToolbar($('draw-tools'));wireChartSize();drawToolbar()}

// ---------- position size and risk ----------
let riskPlan=null;
function drawRisk(){
 const out=$('r-out');if(!out||!S)return;const st=S.byT[selectedTicker];if(!st)return;
 const entry=parseFloat($('r-entry').value)||st.price,stop=parseFloat($('r-stop').value),pct=parseFloat($('r-pct').value),rr=parseFloat($('r-rr').value);
 if($('r-entry').placeholder!==numText(st.price,Math.abs(st.price)<1?4:2))$('r-entry').placeholder=numText(st.price,Math.abs(st.price)<1?4:2);
 const atr=indOn('atr')?atrOf(chartCandles):null;setText($('r-atr'),atr?`ATR on this chart: ${numText(atr,Math.abs(atr)<1?4:3)} MB a candle (a stop 1.5-2 ATR away is common)`:'');
 if(!(stop>0)||stop===entry){riskPlan=null;$('r-use').disabled=true;setHtml(out,'Type a stop-loss price to see the size.');return}
 const long=stop<entry,perShare=Math.abs(entry-stop),riskMB=S.equity*pct,shares=riskMB/perShare,cost=shares*entry,target=entry+(long?1:-1)*rr*perShare;
 const tooBig=cost>(long?S.cash:S.equity);
 riskPlan={long,shares,cost,stop,target};$('r-use').disabled=false;
 setHtml(out,`${long?'Buy':'Short'} <b>${numText(shares,shares<10?3:1)} shares</b> for about <b>${numText(cost)} MB</b>${tooBig?' <span class="dn">(more than you have: lower the risk or move the stop further away)</span>':''}. If the stop at ${priceText(stop)} is hit you lose about <b>${numText(riskMB)} MB</b> (${(pct*100).toFixed(1)}% of your equity) plus fees; at the ${rr}R target of ${priceText(target)} you make about <b>${numText(riskMB*rr)} MB</b>. The stop is ${(perShare/entry*100).toFixed(2)}% from the entry.`)}
document.addEventListener('input',e=>{if(['r-entry','r-stop','r-pct','r-rr'].includes(e.target.id))drawRisk()});
document.addEventListener('change',e=>{if(['r-pct','r-rr'].includes(e.target.id))drawRisk()});
document.addEventListener('click',e=>{
 if(e.target.id!=='r-use'||!riskPlan)return;
 const amt=document.querySelector('.detail-actions .amt-input');if(amt){amt.value=riskPlan.cost.toFixed(2);amt.dispatchEvent(new Event('input',{bubbles:true}))}
 const d=$('d-orders');if(d)d.open=true;
 $('b-tp').value=riskPlan.target.toPrecision(6);$('b-sl').value=riskPlan.stop.toPrecision(6);
 toast(`Filled in: press ${riskPlan.long?'Buy':'Sell'} for ${numText(riskPlan.cost)} MB, then Set bracket`,true,5000)});

