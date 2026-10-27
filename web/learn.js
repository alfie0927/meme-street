// ---------- the Learn page (learning.py, drills.py): tracks of lessons with quizzes, and chart tests on real game charts ----------
// /learn lists the tracks and the chart tests, /learn?l=<id> is a lesson, /learn?test=<kind> a run of chart tests.
// Each view is drawn once when it opens (never redrawn under the reader); visitors can read, answer and test too.
let lrnData=null,lrnLesson=null,lrnView=null;
const LRN_TONE={level:'#4cc3cc',stop:'#f25c54',target:'#3ad07a',entry:'#e8b84a',trigger:'#d2a8ff'};
const lrnPx=v=>numText(v,v<1?4:2);
// a lesson's text: escaped, then **bold**, *italics* and [text](/a/path on this site)
const lrnText=s=>esc(s).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/\*([^*\s][^*]*?)\*/g,'<i>$1</i>').replace(/\[([^\]]+)\]\((\/[^)\s]*)\)/g,'<a href="$2">$1</a>');
async function loadLearn(){
 const q=new URLSearchParams(location.search),l=q.get('l'),t=q.get('test'),key=l?'l:'+l:t?'t:'+t:'list';
 if(lrnView===key)return;lrnView=key;
 if(l){let d=null;try{d=await (await fetch('/api/learn/lesson/'+encodeURIComponent(l))).json()}catch(e){}
  if(!d||d.error){setHtml($('learn-body'),'<p>There is no such lesson. <a href="/learn">All lessons</a></p>');return}
  lrnLesson=d;drawLesson();return}
 if(t){drawTestPage(t);return}
 const d=await api('/api/learn');if(!d||d.slow||d.error||!d.tracks){lrnView=null;return}
 lrnData=d;drawLearn()}

// ---- the list: progress, the chart tests, every track
function drawLearn(){
 const d=lrnData;$('learn-card').classList.remove('reading');
 const tr=d.tests.reduce((a,t)=>[a[0]+t.right,a[1]+t.n],[0,0]);
 setHtml($('learn-body'),`<div class="lrn-top"><div><h3 style="margin:0 0 6px">Learn to trade</h3>
  <p class="about" style="margin:0">Everything a trader needs, from what a share is to options, macro and building a trading bot, in ${d.total} short lessons. Each ends with a few questions, and the chart tests use real charts from this market: answer, then see what happened next. Nothing here costs or pays MB.</p></div>
  <div class="lrn-prog"><b>${d.passed}</b> of ${d.total} lessons passed${pbar(d.passed,d.total||1)}<span class="mut">${tr[1]?`Chart tests: ${tr[0]} of ${tr[1]} right`:'No chart tests yet'}</span></div></div>
  ${token?'':'<p class="hint">You are not signed in: you can read everything and answer every question, but your progress is not kept. <a href="/#join">Create an account</a> to keep it.</p>'}
  <h3 class="sp">Chart tests</h3><p class="hint" style="margin-top:0">A real chart from the game, stopped at a moment worth asking about. Pick your answer, then the chart shows what came next.</p>
  <div class="lrn-tests">${d.tests.map(t=>`<a class="lrn-test" href="/learn?test=${t.kind}"><b>${esc(t.title)}</b><small>${esc(t.about)}</small><span class="mut">${t.n?`${t.right} of ${t.n} right`:'Not tried yet'}</span></a>`).join('')}<a class="lrn-test" href="/learn?test=any"><b>Mixed</b><small>Any of the above, at random.</small><span class="mut">&nbsp;</span></a></div>
  <h3 class="sp">The course</h3><div class="lrn-tracks">${d.tracks.map((t,k)=>{const done=t.lessons.filter(x=>x.passed).length;
   return `<section class="lrn-track"><div class="lrn-th"><span class="lrn-n">${k||'S'}</span><div><b>${esc(t.title)}</b><small>${done} of ${t.lessons.length} passed</small></div></div><p class="mut">${lrnText(t.blurb)}</p>${pbar(done,t.lessons.length||1)}
    <ol class="lrn-ls">${t.lessons.map(x=>`<li class="${x.passed?'done':''}"><a href="/learn?l=${encodeURIComponent(x.id)}" title="${esc(x.summary)}">${esc(x.title)}</a><small>${x.passed?'Passed':x.minutes+' min'}</small></li>`).join('')}</ol></section>`}).join('')}</div>`)}

// ---- a lesson
function lrnBlock(b){
 if(b.h)return `<h4>${lrnText(b.h)}</h4>`;
 if(b.list)return `<ul>${b.list.map(x=>`<li>${lrnText(x)}</li>`).join('')}</ul>`;
 if(b.tip)return `<div class="tip">${lrnText(b.tip)}</div>`;
 if(b.here)return `<div class="lrn-here"><b>On Meme Street</b>${lrnText(b.here)}</div>`;
 if(b.warn)return `<div class="lrn-warn">${lrnText(b.warn)}</div>`;
 if(b.table)return `<div class="lrn-tw"><table class="lrn-t"><thead><tr>${b.table[0].map(c=>`<th>${lrnText(c)}</th>`).join('')}</tr></thead><tbody>${b.table.slice(1).map(r=>`<tr>${r.map(c=>`<td>${lrnText(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
 if(b.chart)return `<div class="lrn-box" data-lrn-ex="${esc(b.chart)}"><p class="mut">Finding a real chart…</p></div>`;
 if(b.test)return `<div class="lrn-box" data-lrn-test="${esc(b.test)}"><p class="mut">Finding a real chart…</p></div>`;
 if(b.try)return `<div class="lrn-try"><span><b>Try it</b>${lrnText(b.try)}</span><a class="btn" href="${esc(b.href)}">Open</a></div>`;
 return `<p>${lrnText(b.p||'')}</p>`}
function drawLesson(){
 const L=lrnLesson;$('learn-card').classList.add('reading');
 const quiz=L.quiz.length?`<h3 class="sp">Check what you learnt</h3><div id="quiz">${L.quiz.map((q,i)=>`<div class="quiz-q" data-q="${i}"><b>${i+1}. ${lrnText(q.q)}</b>${q.options.map((o,j)=>`<label><input type="radio" name="q${i}" value="${j}">${lrnText(o)}</label>`).join('')}<div class="why"></div></div>`).join('')}</div>
  <div class="bar"><button class="buy" id="quiz-go">Check my answers</button><span id="quiz-out" class="hint"></span></div>${token?'':'<p class="hint">Not signed in: your answers are marked, but your progress is not kept.</p>'}`:'';
 const nav=`<div class="lrn-nav">${L.prev?`<a href="/learn?l=${encodeURIComponent(L.prev.id)}">← ${esc(L.prev.title)}</a>`:'<span></span>'}${L.next?`<a href="/learn?l=${encodeURIComponent(L.next.id)}">${esc(L.next.title)} →</a>`:''}</div>`;
 setHtml($('learn-body'),`<div class="lrn-crumb"><a href="/learn">Learn</a> › ${esc(L.track_title)}</div><h3 style="margin:8px 0 2px">${esc(L.title)}</h3><p class="mut" style="margin:0">${L.minutes} minutes</p>
  <div class="lesson-body">${L.body.map(lrnBlock).join('')}</div>${quiz}${nav}`);
 document.querySelectorAll('#learn-body [data-lrn-ex]').forEach(el=>lrnExample(el,el.dataset.lrnEx));
 document.querySelectorAll('#learn-body [data-lrn-test]').forEach(el=>lrnTest(el,el.dataset.lrnTest))}
async function lrnQuiz(){
 const L=lrnLesson,answers=L.quiz.map((_,i)=>{const c=document.querySelector(`input[name=q${i}]:checked`);return c?Number(c.value):-1});
 if(answers.includes(-1)){setText($('quiz-out'),'Answer every question first');return}
 const r=await postJson('/api/learn/quiz',{lesson:L.id,answers},{'X-Token':token||''});
 if(!r.ok){setText($('quiz-out'),r.error||'Error');return}
 r.marks.forEach((m,i)=>{const box=document.querySelector(`.quiz-q[data-q="${i}"]`);box.classList.toggle('right',m.right);box.classList.toggle('wrong',!m.right);
  box.querySelector('.why').innerHTML=(m.right?'<span class="up">Right.</span> ':'<span class="dn">Not quite.</span> ')+lrnText(m.why)});
 setText($('quiz-out'),r.passed?(r.first?`Passed: all ${r.of} right.`:`All ${r.of} right.`)+(L.next?' On to the next lesson.':''):`${r.score} of ${r.of} right. Read the notes and try again.`)}

// ---- a page of chart tests
function drawTestPage(kind){
 $('learn-card').classList.add('reading');
 setHtml($('learn-body'),`<div class="lrn-crumb"><a href="/learn">Learn</a> › Chart tests</div><h3 style="margin:8px 0 4px">Chart tests</h3>
  <p class="about" style="margin:0">A real chart from the game, stopped at a moment worth asking about. Pick an answer, then the chart shows what came next and why. Over many charts your score says more than any one answer.</p>
  <div class="lrn-box big" data-lrn-test="${esc(kind)}"><p class="mut">Finding a real chart…</p></div><p class="hint"><a href="/learn">All chart tests and lessons</a></p>`);
 lrnTest(document.querySelector('[data-lrn-test]'),kind)}

// ---- the chart widget: a test (question, then the answer) and a lesson's example
const lrnWhere=w=>w.ticker?`This was <a href="/stock/${encodeURIComponent(w.ticker)}">${esc(w.ticker)}</a> (${esc(w.name)}), ${esc(w.tf)} candles${w.end?`, up to ${new Date(w.end*1000).toLocaleString(undefined,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}`:''}.`:esc(w.name)+'.';
async function lrnTest(el,kind){
 el._kind=kind;el._q=null;el._done=false;el.innerHTML='<p class="mut">Finding a real chart…</p>';
 const q=await api('/api/learn/test?kind='+encodeURIComponent(kind));
 if(!q||q.error||q.slow||!q.candles){el.innerHTML=`<p class="mut">${esc(q&&q.error||'Could not load a chart test.')}</p><button data-lrn-again>Try again</button>`;return}
 el._q=q;
 el.innerHTML=`<div class="lrn-qh"><b>${esc(q.title)}</b><span class="mut">${q.tf==='short'?'a chart from the price model':esc(q.tf)+' candles from the game'}</span></div>
  <div class="lrn-chart">${lrnSvg(q,q.candles.length+25)}</div><p class="lrn-q">${lrnText(q.q)}</p>
  <div class="lrn-opts">${q.options.map((o,i)=>`<button data-lrn-pick="${i}">${esc(o)}</button>`).join('')}</div><div class="lrn-out"></div>`}
async function lrnPick(el,i){
 const q=el._q;if(!q||el._done)return;el._done=true;
 el.querySelectorAll('[data-lrn-pick]').forEach(b=>b.disabled=true);
 const a=await postJson('/api/learn/test',{id:q.id,choice:i},{'X-Token':token||''});
 if(a.expired){lrnTest(el,el._kind);return}
 if(a.error||!a.candles){el._done=false;el.querySelectorAll('[data-lrn-pick]').forEach(b=>b.disabled=false);toast(a.error||'Could not mark it',false);return}
 el.querySelector('.lrn-chart').innerHTML=lrnSvg({candles:q.candles.concat(a.candles),upto:q.candles.length-1,lines:a.lines,marks:a.marks,overlay:q.overlay,panel:q.panel},q.candles.length+25);
 el.querySelectorAll('[data-lrn-pick]').forEach(b=>{const k=+b.dataset.lrnPick;if(k===a.answer)b.classList.add('right');else if(k===i)b.classList.add('wrong')});
 el.querySelector('.lrn-out').innerHTML=`<p><b class="${a.right?'up':'dn'}">${a.right?'Right.':'Not this time.'}</b> ${lrnText(a.result)}</p><p class="mut">${lrnText(a.explain)}</p>
  <p class="hint">${lrnWhere(a.where)}${a.score?` Your score at this test: ${a.score[0]} of ${a.score[1]}.`:''}</p><button class="buy" data-lrn-again>Another chart</button>`}
async function lrnExample(el,kind){
 const d=await api('/api/learn/test?example=1&kind='+encodeURIComponent(kind));
 if(!d||d.error||d.slow||!d.candles){el.innerHTML='<p class="mut">No example chart right now.</p>';return}
 const before=Object.assign({},d,{candles:d.candles.slice(0,d.upto+1),lines:d.lines.filter(x=>!x.after),marks:d.marks.filter(x=>!x.after)});
 el._ex=d;
 el.innerHTML=`<div class="lrn-qh"><b>On a real chart: ${esc(d.title)}</b><span class="mut">${d.tf==='short'?'a chart from the price model':esc(d.tf)+' candles from the game'}</span></div>
  <div class="lrn-chart">${lrnSvg(before,d.candles.length)}</div><p class="lrn-q">${lrnText(d.q)}</p><div class="lrn-out"><button data-lrn-show>Show the answer and what happened next</button></div>`}
function lrnShow(el){
 const d=el._ex;if(!d)return;
 el.querySelector('.lrn-chart').innerHTML=lrnSvg(d,d.candles.length);
 el.querySelector('.lrn-out').innerHTML=`<p><b>${esc(d.options[d.answer])}.</b> ${lrnText(d.result)}</p><p class="mut">${lrnText(d.explain)}</p><p class="hint">${lrnWhere(d.where)} This example changes every quarter of an hour.</p>`}

// the chart: candles and volume, the levels and marks of the test, moving averages, an RSI panel, and once answered
// a line at the moment of the question with the candles after it. `slots` leaves room on the right for what comes next,
// so the candles stay where they are when the answer arrives.
function lrnSvg(o,slots){
 const cs=o.candles,n=Math.max(slots||cs.length,cs.length),W=PHONE?380:860,R=PHONE?50:60,top=12,ph=PHONE?190:250,volH=ph*0.16,rsiH=o.panel==='rsi'?(PHONE?60:74):0,H=ph+volH+8+(rsiH?rsiH+10:0)+14;
 const lines=o.lines||[],marks=o.marks||[];
 const lo=Math.min(...cs.map(c=>c[2]),...lines.map(l=>l.price)),hi=Math.max(...cs.map(c=>c[1]),...lines.map(l=>l.price)),pad=(hi-lo||hi*0.01)*0.07;
 const a=lo-pad,b=hi+pad,y=v=>top+(b-v)/(b-a)*ph,sw=(W-R)/n,bw=Math.max(1,sw*0.66),X=i=>i*sw+sw/2,vx=Math.max(...cs.map(c=>c[4]),1),vy=top+ph+volH;
 const tags=lines.map(l=>({l,y:y(l.price)})).sort((p,q)=>p.y-q.y);
 tags.forEach((t,k)=>{t.ty=k?Math.max(t.y,tags[k-1].ty+17):t.y});      // (close lines' tags are moved apart)
 let h='';
 for(let k=0;k<5;k++){const v=a+(b-a)*(k+0.5)/5,yy=y(v).toFixed(1);h+=`<line x1="0" x2="${W-R}" y1="${yy}" y2="${yy}" stroke="#ffffff0a"/>`+(tags.some(t=>Math.abs(t.ty-yy)<13)?'':`<text x="${W-R+4}" y="${(+yy+4).toFixed(0)}" fill="var(--mut)" font-size="10.5">${lrnPx(v)}</text>`)}
 if(o.upto!=null&&o.upto<cs.length-1){const x=X(o.upto)+sw/2;h+=`<rect x="${x.toFixed(1)}" y="0" width="${(W-R-x).toFixed(1)}" height="${H}" fill="#ffffff06"/><line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="0" y2="${H}" stroke="#ffffff40" stroke-dasharray="3 4"/><text x="${(x+4).toFixed(1)}" y="10" fill="var(--mut)" font-size="10">what came next</text>`}
 cs.forEach((c,i)=>{const x=X(i),col=c[3]>=c[0]?'var(--up)':'var(--dn)';
  h+=`<line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${y(c[1]).toFixed(1)}" y2="${y(c[2]).toFixed(1)}" stroke="${col}"/><rect x="${(x-bw/2).toFixed(1)}" y="${y(Math.max(c[0],c[3])).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1,Math.abs(y(c[0])-y(c[3]))).toFixed(1)}" fill="${col}"/>`
   +`<rect x="${(x-bw/2).toFixed(1)}" y="${(vy-c[4]/vx*volH).toFixed(1)}" width="${bw.toFixed(1)}" height="${(c[4]/vx*volH).toFixed(1)}" fill="${col}" opacity="0.3"/>`});
 const path=vals=>vals.map((v,i)=>v==null?'':`${i&&vals[i-1]!=null?'L':'M'}${X(i).toFixed(1)} ${y(v).toFixed(1)}`).join('');
 const closes=cs.map(c=>c[3]),OV={sma20:['#e8b84a',20],sma50:['#79c0ff',50]};
 (o.overlay||[]).forEach(k=>{const v=OV[k];if(v)h+=`<path d="${path(smaOf(closes,v[1]))}" fill="none" stroke="${v[0]}" stroke-width="1.5"/>`});
 tags.forEach(({l,y:yy,ty})=>{const col=LRN_TONE[l.tone]||'#8b949e',x0=Math.max(0,X(l.from||0)-sw/2);
  h+=`<line x1="${x0.toFixed(1)}" x2="${W-R}" y1="${yy.toFixed(1)}" y2="${yy.toFixed(1)}" stroke="${col}" stroke-dasharray="6 4" stroke-width="1.3"/><text x="${W-R-4}" y="${(ty-4).toFixed(1)}" fill="${col}" font-size="10.5" text-anchor="end" paint-order="stroke" stroke="#12161a" stroke-width="3">${esc(l.label)}</text>`
   +`<rect x="${W-R+1}" y="${(ty-8).toFixed(1)}" width="${R-2}" height="16" fill="${col}"/><text x="${W-R+4}" y="${(ty+4).toFixed(1)}" fill="#021012" font-size="10.5" font-weight="700">${lrnPx(l.price)}</text>`});
 marks.forEach(m=>{const x=X(m.i),c=cs[m.i],above=!c||m.price>=(c[1]+c[2])/2,yy=y(m.price);
  h+=m.label==='This one'?`<path d="M${x.toFixed(1)} ${(yy-6).toFixed(1)} l-5 -9 h10 z" fill="var(--acc)"/>`
   :`<circle cx="${x.toFixed(1)}" cy="${yy.toFixed(1)}" r="3.6" fill="var(--acc)"/>${m.label?`<text x="${x.toFixed(1)}" y="${(above?yy-8:yy+16).toFixed(1)}" fill="var(--acc)" font-size="10.5" text-anchor="middle">${esc(m.label)}</text>`:''}`});
 if(rsiH){const r=rsiOf(closes,14),t0=vy+10,ry=v=>t0+(100-v)/100*rsiH;
  h+=`<rect x="0" y="${t0}" width="${W-R}" height="${rsiH}" fill="#ffffff05"/>`+[70,50,30].map(v=>`<line x1="0" x2="${W-R}" y1="${ry(v).toFixed(1)}" y2="${ry(v).toFixed(1)}" stroke="${v===50?'#ffffff12':'#ffffff30'}" stroke-dasharray="${v===50?'':'4 4'}"/><text x="${W-R+4}" y="${(ry(v)+4).toFixed(1)}" fill="var(--mut)" font-size="10">${v}</text>`).join('')
   +`<path d="${r.map((v,i)=>v==null?'':`${i&&r[i-1]!=null?'L':'M'}${X(i).toFixed(1)} ${ry(v).toFixed(1)}`).join('')}" fill="none" stroke="#d2a8ff" stroke-width="1.4"/><text x="4" y="${t0+11}" fill="#d2a8ff" font-size="10">RSI 14</text>`}
 return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="A chart from the game">${h}</svg>`}

$('learn-card').addEventListener('click',e=>{
 const t=e.target;
 if(t.id==='quiz-go'){lrnQuiz();return}
 const box=t.closest('[data-lrn-test],[data-lrn-ex]');if(!box)return;
 if(t.dataset.lrnPick!==undefined)lrnPick(box,+t.dataset.lrnPick);
 else if(t.dataset.lrnAgain!==undefined)lrnTest(box,box._kind);
 else if(t.dataset.lrnShow!==undefined)lrnShow(box)});
