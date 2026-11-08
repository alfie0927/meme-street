// ---------- the Learn page (learning.py, drills.py): the path of lessons with their exercises, and chart tests ----------
// /learn is the path (units in order, the next lesson, XP, streak and the daily goal; since 2026-11-07, ROADMAP LP1-LP3),
// /learn?l=<id> is a lesson that ends with its exercises (questions answered in place, chart tests that count, tasks
// checked on the live market), /learn?test=<kind> a run of chart tests. Each view is drawn once when it opens (never
// redrawn under the reader); visitors can read, answer and test too, but only a player's progress is kept.
let lrnData=null,lrnLesson=null,lrnView=null;
const LRN_LEVELS=['Trainee','Apprentice','Trader','Analyst','Strategist','Master'];
const LRN_TONE={level:'#4cc3cc',stop:'#f25c54',target:'#3ad07a',entry:'#e8b84a',trigger:'#d2a8ff'};
const lrnPx=v=>numText(v,v<1?4:2);
// a lesson's text: escaped, then **bold**, *italics* and [text](/a/path on this site)
const lrnText=s=>esc(s).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/\*([^*\s][^*]*?)\*/g,'<i>$1</i>').replace(/\[([^\]]+)\]\((\/[^)\s]*)\)/g,'<a href="$2">$1</a>');
async function loadLearn(){
 const q=new URLSearchParams(location.search),l=q.get('l'),t=q.get('test'),pl=q.get('place'),rv=q.get('review'),key=l?'l:'+l:t?'t:'+t:pl?'place':rv?'review':'list';
 if(lrnView===key)return;lrnView=key;
 if(pl){drawPlacement();return}
 if(rv){drawReview();return}
 if(l){let d=null;try{d=await (await fetch('/api/learn/lesson/'+encodeURIComponent(l),{headers:{'X-Token':token||''}})).json()}catch(e){}
  if(!d||d.error){setHtml($('learn-body'),'<p>There is no such lesson. <a href="/learn">All lessons</a></p>');return}
  lrnLesson=d;drawLesson();return}
 if(t){drawTestPage(t);return}
 const d=await api('/api/learn');if(!d||d.slow||d.error||!d.tracks){lrnView=null;return}
 lrnData=d;drawLearn()}

// ---- the path: XP, streak and the daily goal, the next lesson, every unit, then the chart tests
function drawLearn(){
 const d=lrnData;$('learn-card').classList.remove('reading');
 const tr=d.tests.reduce((a,t)=>[a[0]+t.right,a[1]+t.n],[0,0]);
 const next=d.tracks.flatMap(t=>t.lessons).find(x=>x.id===d.next);
 setHtml($('learn-body'),`<div class="lrn-top"><div><h3 style="margin:0 0 6px">Learn to trade</h3>
  <p class="about" style="margin:0">A path of ${d.total} short lessons, from what a share is to options, macro and trading bots. Every lesson has a few exercises: questions, and in many lessons a chart test on a real chart from this market or something to do on the live market. It never costs MB.</p>
  ${next?`<div class="lrn-next"><div><small>${d.passed?'Next on your path':'Start here'}</small><b>${esc(next.title)}</b><span class="mut">${next.minutes} min · ${next.ex_total} exercise${next.ex_total===1?'':'s'}${next.ex_done?` · ${next.ex_done} done`:''}</span></div><a class="buy" href="/learn?l=${encodeURIComponent(next.id)}">${next.ex_done?'Continue':d.passed?'Next lesson':'Start'}</a></div>`:'<div class="lrn-next"><b>You have passed every lesson.</b></div>'}</div>
  <div class="lrn-prog"><div class="lrn-xp"><div><strong>${numText(d.xp,0)}</strong><small>XP · ${esc(d.level?d.level.name:'')}</small></div><div title="Days in a row with any XP (calendar days, UTC), not the game's 30-minute day"><strong>${d.streak?'🔥 ':''}${d.streak}</strong><small>day streak</small></div><div><strong>${d.total?Math.round(d.passed/d.total*100):0}%</strong><small>of the course</small></div></div>
   ${d.level&&d.level.next?`<span class="mut">${numText(d.level.next-d.xp,0)} XP to ${esc(LRN_LEVELS[d.level.n]||'the next level')}</span>${pbar(d.xp-d.level.floor,(d.level.next-d.level.floor)||1)}`:''}
   <span class="mut">Today: <b>${d.today}</b> of ${token?`<select id="lrn-goal" aria-label="Daily goal">${(d.goals||[20,50,100]).map(g=>`<option value="${g}" ${g===d.goal?'selected':''}>${g}</option>`).join('')}</select>`:d.goal} XP${d.today>=d.goal?' · goal reached':''}</span>${pbar(d.today,d.goal||1)}<span class="mut">${tr[1]?`Chart tests: ${tr[0]} of ${tr[1]} right`:'No chart tests yet'}</span>
   <span class="mut">${d.xp_rules?`XP: ${d.xp_rules.right} for a right answer, ${d.xp_rules.wrong} for a wrong one, ${d.xp_rules.pass} for each lesson passed, ${d.xp_rules.task} for each market task. The streak counts calendar days (UTC) with any XP.`:''}</span>
   ${token?`<span class="up">${d.today>=d.goal?`Goal reached. Come back tomorrow: any XP ${d.streak>=1?`keeps your ${d.streak}-day streak going`:'starts a streak'}.`:d.streak?`Any XP today keeps your ${d.streak}-day streak; ${d.goal-d.today} more reaches the goal.`:'Any XP today starts a streak; come back tomorrow to keep it.'}</span>`:''}
   ${d.league?`<div class="lrn-league"><b>This week's learners</b>${d.league.rows.length?`<ol>${d.league.rows.slice(0,10).map(r=>`<li><a href="/player/${encodeURIComponent(r.name)}">${esc(r.name)}</a><span>${numText(r.xp,0)} XP</span></li>`).join('')}</ol>`:'<span class="mut">Nobody has earned XP yet this week: be the first.</span>'}${d.league.rank?`<span class="mut">You are #${d.league.rank} of ${d.league.learners} with ${numText(d.league.xp,0)} XP this week.</span>`:token&&d.league.rows.length?'<span class="mut">Earn XP this week to be on it.</span>':''}</div>`:''}</div></div>
  ${token?'':'<p class="hint">You are not signed in: you can read everything, answer every question and take every test, but your progress, XP and streak are not kept. <a href="/#join">Create an account</a> to keep them.</p>'}
  ${token&&!d.passed&&!d.placed?`<div class="lrn-place"><div><b>Already know some of this?</b><span class="mut">Twelve quick questions, one from each of the first twelve units, find where your path should start. Units you know are marked passed.</span></div><a class="btn" href="/learn?place=1">Take the placement test</a></div>`:''}
  ${token?lrnMineHtml(d.mine,false):''}
  ${token?lrnHabitsHtml(d.challenges):''}
  ${d.weak&&d.weak.length?`<div class="lrn-place lrn-weak"><div><b>Your weak spots</b><span class="mut">${d.weak.map(w=>`${esc(w.name)} (${w.right} of ${w.n} right)`).join(' · ')}. A review asks you again, with other questions from those units.</span></div><a class="btn" href="/learn?review=1">Review</a></div>`:''}
  <h3 class="sp">The path</h3><div class="lrn-tracks">${d.tracks.map((t,k)=>{const done=t.lessons.filter(x=>x.passed).length;
   const steps=t.lessons.filter(x=>x.ex_total>0),refs=t.lessons.filter(x=>!x.ex_total);   // a lesson without exercises (the glossary) is reference, not a step (loop 11)
   const fin=steps.length&&done===steps.length;
   return `<section class="lrn-track${fin?' done collapsed':''}" data-unit="${esc(t.id)}"><div class="lrn-th" ${fin?'data-lrn-unfold title="Finished: click to open"':''}><span class="lrn-n">${fin?'✓':k||'S'}</span><div><b>${esc(t.title)}</b><small>${fin?'Finished':`${done} of ${steps.length} passed`}</small></div></div><p class="mut">${lrnText(t.blurb)}</p>${pbar(done,steps.length||1)}
    <ol class="lrn-ls">${steps.map(x=>`<li class="${x.passed?'done':x.next?'next':''}"><a href="/learn?l=${encodeURIComponent(x.id)}" title="${esc(x.summary)}">${esc(x.title)}</a><small>${x.passed?'Passed':x.ex_done?`${x.ex_done} of ${x.ex_total}`:x.next?'Next':x.minutes+' min'}</small></li>`).join('')}</ol>${refs.length?`<p class="mut" style="margin:4px 0 0">Reference, not a step: ${refs.map(x=>`<a href="/learn?l=${encodeURIComponent(x.id)}">${esc(x.title)}</a>`).join(', ')}</p>`:''}</section>`}).join('')}</div>
  <h3 class="sp">Chart tests</h3><p class="hint" style="margin-top:0">Practice on its own: a real chart from the game, stopped at a moment worth asking about. Pick your answer, then the chart shows what came next.</p>
  <div class="lrn-tests">${d.tests.map(t=>`<a class="lrn-test" href="/learn?test=${t.kind}"><b>${esc(t.title)}</b><small>${esc(t.about)}</small><span class="mut">${t.n?`${t.right} of ${t.n} right`:'Not tried yet'}</span></a>`).join('')}<a class="lrn-test" href="/learn?test=any"><b>Mixed</b><small>Any of the above, at random.</small><span class="mut">The all-round test</span></a></div>`)}

// ---- the placement test (LP6): twelve questions, one per unit, graded together; the path starts at the first unit missed
let lrnPlace=null;
async function drawPlacement(){
 $('learn-card').classList.add('reading');
 setHtml($('learn-body'),'<div class="lrn-crumb"><a href="/learn">Learn</a> › Placement test</div><p class="mut">Loading the questions…</p>');
 const d=await api('/api/learn/placement');if(!d||d.error||!d.questions){setHtml($('learn-body'),'<p>Could not load the test. <a href="/learn">Back to the path</a></p>');return}
 lrnPlace={qs:d.questions,picks:{}};
 setHtml($('learn-body'),`<div class="lrn-crumb"><a href="/learn">Learn</a> › Placement test</div><h3 style="margin:8px 0 2px">Where should your path start?</h3>
  <p class="about" style="margin:0 0 8px">One question from each of the first twelve units, in the order of the course. Answer them all, then <b>See where to start</b>. The units you get right in a row from the first are marked passed and your path begins at the first one you miss. ${token?'':'<b>Sign in first</b> to have the result kept.'}</p>
  <div class="lesson-body">${d.questions.map((x,n)=>`<div class="lrn-box lrn-qbox" data-place-q="${n}"><div class="lrn-qh"><b>${n+1}. ${esc(x.title)}</b><span class="mut lrn-qs"></span></div><p class="lrn-q">${lrnText(x.q)}</p><div class="lrn-opts">${x.options.map((o,i)=>`<button data-place-pick="${i}">${esc(o)}</button>`).join('')}</div><div class="lrn-out"></div></div>`).join('')}</div>
  <div class="bar" style="margin-top:12px"><button class="buy" id="place-go" disabled>See where to start</button><span class="hint" id="place-note">Answer all ${d.questions.length} first.</span></div><div id="place-result"></div>`)}
function lrnPlacePick(box,i){
 if(!lrnPlace||lrnPlace.graded)return;const n=+box.dataset.placeQ;lrnPlace.picks[n]=i;
 box.querySelectorAll('[data-place-pick]').forEach(b=>b.classList.toggle('on',+b.dataset.placePick===i));
 const left=lrnPlace.qs.length-Object.keys(lrnPlace.picks).length;$('place-go').disabled=left>0;$('place-note').textContent=left?`${left} to go.`:'Ready.'}
async function lrnPlaceGrade(){
 const P=lrnPlace;if(!P||P.graded)return;P.graded=true;$('place-go').disabled=true;
 const r=await postJson('/api/learn/placement',{answers:P.qs.map((x,n)=>({lesson:x.lesson,i:x.i,choice:P.picks[n]}))},{'X-Token':token||''});
 if(r.error||!r.results){P.graded=false;$('place-go').disabled=false;toast(r.error||'Could not grade it',false);return}
 r.results.forEach((res,n)=>{const box=document.querySelector(`[data-place-q="${n}"]`);if(!box)return;
  box.querySelectorAll('[data-place-pick]').forEach(b=>{b.disabled=true;const k=+b.dataset.placePick;if(k===res.answer)b.classList.add('right');else if(k===P.picks[n])b.classList.add('wrong')});
  box.querySelector('.lrn-qs').textContent=res.right?'Right':'Missed';box.querySelector('.lrn-out').innerHTML=`<p class="mut">${lrnText(res.why)}</p>`});
 const st=r.start,known=r.known||[];lrnView=null;
 setHtml($('place-result'),`<div class="lrn-next" style="margin-top:14px"><div><small>Your level</small><b>${known.length?`You know ${known.length===1?known[0]:known.slice(0,-1).join(', ')+' and '+known[known.length-1]}.`:'Start from the beginning.'}</b><span class="mut">${st&&st.lesson?`Your path starts at <b>${esc(st.track||'Start here')}</b>, with “${esc(st.lesson.title)}”.`:'You know every unit asked: carry on from the advanced units.'}${r.passed!==undefined?` ${r.passed} lesson${r.passed===1?'':'s'} marked passed.`:token?'':' Sign in and take it again to keep this.'}</span></div>${st&&st.lesson?`<a class="buy" href="/learn?l=${encodeURIComponent(st.lesson.id)}">Start there</a>`:'<a class="buy" href="/learn">The path</a>'}</div>`);
 $('place-result').scrollIntoView({behavior:'smooth',block:'center'})}

// ---- the review (LP5): fresh questions on the units missed most and a chart test of each kind missed most
async function drawReview(){
 $('learn-card').classList.add('reading');
 setHtml($('learn-body'),'<div class="lrn-crumb"><a href="/learn">Learn</a> › Review</div><p class="mut">Building your review…</p>');
 const d=await api('/api/learn/review');
 if(!d||d.error||!d.items){setHtml($('learn-body'),`<div class="lrn-crumb"><a href="/learn">Learn</a> › Review</div><p>${esc(d&&d.error||'Could not build a review.')} <a href="/learn">Back to the path</a></p>`);return}
 lrnLesson=null;
 setHtml($('learn-body'),`<div class="lrn-crumb"><a href="/learn">Learn</a> › Review</div><h3 style="margin:8px 0 2px">Review your weak spots</h3>
  <p class="about" style="margin:0 0 8px">${d.weak.map(w=>`<b>${esc(w.name)}</b> (${w.right} of ${w.n} right)`).join(', ')}. Answer these; a right answer earns ${d.xp_review||5} XP (once a day for each question). Nothing here passes a lesson: go back to the lesson for that.</p>
  <div class="lesson-body">${d.items.map((x,n)=>x.test?`<p class="mut" style="margin:14px 0 0">${esc(x.name)}</p><div class="lrn-box" data-lrn-test="${esc(x.test)}" data-lrn-review><p class="mut">Finding a real chart…</p></div>`
   :`<div class="lrn-box lrn-qbox" data-lrn-q="${x.i}" data-lrn-lesson="${esc(x.lesson)}" data-lrn-review><div class="lrn-qh"><b>${esc(x.name)}</b><span class="mut lrn-qs"></span></div><p class="lrn-q">${lrnText(x.q)}</p><div class="lrn-opts">${x.options.map((o,i)=>`<button data-lrn-choice="${i}">${esc(o)}</button>`).join('')}</div><div class="lrn-out"></div></div>`).join('')}</div>
  <div class="lrn-nav"><a href="/learn">← The path</a><a href="/learn?review=1" onclick="lrnView=null">Another review →</a></div>`);
 document.querySelectorAll('#learn-body [data-lrn-test]').forEach(el=>lrnTest(el,el.dataset.lrnTest))}

// ---- the player's own trading (LP10): on the path and inside the risk lessons as a [mine] block
function lrnMineHtml(m,inLesson){
 if(!token)return `<div class="lrn-box lrn-mine"><div class="lrn-qh"><b>Your trading</b></div><p class="mut">Sign in and trade a little: this box shows your own numbers (stops used, wins and losses, R, fees) against what the lesson says.</p></div>`;
 if(!m)return '';
 if(!m.closes&&!m.all_closes)return `<div class="lrn-box lrn-mine"><div class="lrn-qh"><b>Your trading</b></div><p class="mut">Nothing closed yet. Trade a little, with a stop, and this box fills with your own numbers: stops used, wins and losses, R, fees.</p></div>`;
 const pct=v=>v===null||v===undefined?'-':(v*100).toFixed(0)+'%',r=v=>v===null||v===undefined?'-':(v>=0?'+':'')+v.toFixed(2)+'R',mb=v=>v===null||v===undefined?'-':numText(v)+' MB';
 const ex=m.exits||{},exits=(ex.stop+ex.target+ex.trail)?`${ex.stop} by stop · ${ex.target} by target${ex.trail?` · ${ex.trail} by trailing stop`:''}`:'none by an order yet';
 return `<div class="lrn-box lrn-mine"><div class="lrn-qh"><b>Your trading</b><span class="mut">${m.closes} close${m.closes===1?'':'s'} in the last 7 days</span></div>
  <div class="finance-grid"><div><small>Win rate, 7 days</small><strong>${pct(m.win_rate)}</strong></div><div><small>Average win, 7 days</small><strong class="up">${mb(m.avg_win)}</strong></div><div><small>Average loss, 7 days</small><strong class="dn">${mb(m.avg_loss)}</strong></div><div><small>Profit factor, 7 days</small><strong>${m.profit_factor===null?'-':m.profit_factor.toFixed(2)}</strong></div><div><small>Fees, 7 days</small><strong>${pct(m.fee_share)} of turnover</strong></div><div><small>Worst fall today</small><strong>${pct(m.maxdd)}</strong></div><div><small>Closes with a stop, all time</small><strong>${m.with_stop} of ${m.all_closes}</strong></div><div><small>Average R, all time</small><strong class="${m.avg_r>0?'up':m.avg_r<0?'dn':''}">${r(m.avg_r)}${m.r_n?` <span class="mut">(${m.r_n})</span>`:''}</strong></div></div>
  <p class="mut" style="margin:6px 0 0">Positions ended by an order, all time: ${exits}.</p>
  ${m.tips&&m.tips.length?`<ul class="lrn-tips">${m.tips.map(t=>`<li>${esc(t.text)} <a href="/learn?l=${encodeURIComponent(t.lesson)}">${esc(t.title)}</a></li>`).join('')}</ul>`:'<p class="up" style="margin:6px 0 0">Nothing stands out this week. Keep the stops on.</p>'}</div>`}
function lrnHabitsHtml(cs){
 if(!cs||!cs.length)return '';
 return `<div class="lrn-box lrn-habits"><div class="lrn-qh"><b>This week's habits</b><span class="mut">XP, reset every Monday (UTC)</span></div>${cs.map(c=>`<div class="lrn-habit ${c.done?'done':''}"><div><b>${esc(c.title)}</b> <small class="mut">${esc(c.how)}</small></div><span>${c.done?`Done · +${c.xp} XP`:`${c.n} of ${c.target}`}</span>${pbar(c.n,c.target)}</div>`).join('')}</div>`}

// ---- a lesson
function lrnBlock(b){
 if(b.h)return `<h4>${lrnText(b.h)}</h4>`;
 if(b.list)return `<ul>${b.list.map(x=>`<li>${lrnText(x)}</li>`).join('')}</ul>`;
 if(b.tip)return `<div class="tip">${lrnText(b.tip)}</div>`;
 if(b.here)return `<div class="lrn-here"><b>On Meme Street</b>${lrnText(b.here)}</div>`;
 if(b.warn)return `<div class="lrn-warn">${lrnText(b.warn)}</div>`;
 if(b.table)return `<div class="lrn-tw"><table class="lrn-t"><thead><tr>${b.table[0].map(c=>`<th>${lrnText(c)}</th>`).join('')}</tr></thead><tbody>${b.table.slice(1).map(r=>`<tr>${r.map(c=>`<td>${lrnText(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
 if(b.chart)return `<div class="lrn-box" data-lrn-ex="${esc(b.chart)}"><p class="mut">Finding a real chart…</p></div>`;
 if(b.test)return `<div class="lrn-box" data-lrn-test="${esc(b.test)}" ${b.opt?`data-lrn-opt="${esc(b.opt)}"`:''} data-lrn-i="${b.i}"><p class="mut">Finding a real chart…</p></div>`;
 if(b.q&&b.num){const done=lrnDone(b.i),a=done&&lrnLesson.answers&&lrnLesson.answers[String(b.i)];
  return `<div class="lrn-box lrn-qbox" data-lrn-q="${b.i}" data-lrn-num><div class="lrn-qh"><b>Work it out</b><span class="mut lrn-qs">${done?'Answered':''}</span></div><p class="lrn-q">${lrnText(b.q)}</p><div class="bar" style="margin:0">${done?'':`<input class="amt-input" type="number" step="any" placeholder="your answer${b.unit?' in '+esc(b.unit):''}" aria-label="Your answer"><button class="buy" data-lrn-numgo>Check</button>`}</div><div class="lrn-out">${a?`<p><b>The answer:</b> ${a.answer}${b.unit?' '+esc(b.unit):''}. <span class="mut">${lrnText(a.why)}</span></p>`:done?'<p class="mut">You have answered this one.</p>':''}</div></div>`};
 if(b.q){const done=lrnDone(b.i),a=done&&lrnLesson.answers&&lrnLesson.answers[String(b.i)];
  return `<div class="lrn-box lrn-qbox" data-lrn-q="${b.i}"><div class="lrn-qh"><b>Check yourself</b><span class="mut lrn-qs">${done?'Answered':''}</span></div><p class="lrn-q">${lrnText(b.q)}</p><div class="lrn-opts">${b.options.map((o,i)=>`<button data-lrn-choice="${i}" ${done?'disabled':''} class="${a&&a.answer===i?'right':''}">${esc(o)}</button>`).join('')}</div><div class="lrn-out">${a?`<p><b>The answer:</b> ${esc(b.options[a.answer])}. <span class="mut">${lrnText(a.why)}</span></p>`:done?'<p class="mut">You have answered this one.</p>':''}</div></div>`};
 if(b.mine)return lrnMineHtml(lrnLesson&&lrnLesson.mine,true);
 if(b.task){const done=lrnDone(b.i);return `<div class="lrn-box lrn-task ${done?'done':''}" data-lrn-task="${b.i}"><div class="lrn-qh"><b>Do it on the market</b><span class="${done?'up':'mut'}">${done?'Done':'Not yet'}</span></div><p class="lrn-q">${lrnText(b.text)}</p>${done?'':`<div class="bar" style="margin:0"><a class="btn" href="${b.task==='short'||b.task==='trade'?'/stock/NVXA':'/holdings'}">${b.task==='trade'||b.task==='short'?"Open a stock's page":'Open your holdings'}</a><button data-lrn-recheck>I have done it: check</button></div><p class="hint" style="margin:6px 0 0">${token?'The game notices it the moment you do it, on any stock.':'Sign in first: tasks are checked on your own account.'}</p>`}</div>`};
 if(b.try)return `<div class="lrn-try"><span><b>Try it</b>${lrnText(b.try)}</span><a class="btn" href="${esc(b.href)}">Open</a></div>`;
 return `<p>${lrnText(b.p||'')}</p>`}
const lrnDone=i=>!!(lrnLesson&&lrnLesson.done&&lrnLesson.done.includes(i));
function lrnHead(){
 const L=lrnLesson,n=(L.done||[]).length,t=L.total||0;
 return t?`<span class="lrn-exs ${L.passed?'up':''}">${L.passed?'Passed ✓':`${n} of ${t} exercise${t===1?'':'s'} done`}</span>`:''}
function drawLesson(){
 const L=lrnLesson;$('learn-card').classList.add('reading');
 const nav=`<div class="lrn-nav">${L.prev?`<a href="/learn?l=${encodeURIComponent(L.prev.id)}">← ${esc(L.prev.title)}</a>`:'<span></span>'}${L.next?`<a href="/learn?l=${encodeURIComponent(L.next.id)}" class="${L.passed?'lrn-go':''}">${esc(L.next.title)} →</a>`:''}</div>`;
 const first=L.body.findIndex(b=>b.q||b.task||b.test);
 let seen=0,hideFrom=false,html='';                       // exercises come one at a time: the ones after the first unanswered question or test wait (LP14d)
 L.body.forEach((b,k)=>{const isEx=!!(b.q||b.test||b.task);
  if(k===first)html+=`<p class="mut lrn-exh" style="margin:0 0 6px">Check yourself as you read: the lesson is passed when every exercise is done. ${token?'Right answers earn more XP, but a wrong one still counts and is explained.':'Sign in to keep your XP and passes.'}</p>`;
  let h=lrnBlock(b);
  if(isEx&&!b.task){if(hideFrom)h=h.replace(/^<div class="lrn-box/,'<div hidden data-lrn-later class="lrn-box');else if(!lrnDone(b.i))hideFrom=true}
  html+=h});
 setHtml($('learn-body'),`<div class="lrn-crumb"><a href="/learn">Learn</a> › ${esc(L.track_title)}</div><h3 style="margin:8px 0 2px">${esc(L.title)}</h3><p class="mut" style="margin:0">${L.minutes} minutes · <span id="lrn-head">${lrnHead()}</span></p>
  <div class="lesson-body">${html}</div>${nav}`);
 document.querySelectorAll('#learn-body [data-lrn-ex]').forEach(el=>lrnExample(el,el.dataset.lrnEx));
 document.querySelectorAll('#learn-body [data-lrn-test]:not([hidden])').forEach(el=>lrnTest(el,el.dataset.lrnTest))}
function lrnReveal(){
 const nx=document.querySelector('#learn-body [data-lrn-later]');if(!nx)return;
 nx.hidden=false;nx.removeAttribute('data-lrn-later');if(nx.dataset.lrnTest!==undefined)lrnTest(nx,nx.dataset.lrnTest);
 nx.scrollIntoView({behavior:'smooth',block:'nearest'})}
// a question answered in place: right or wrong, the right answer and why (learning.learn_answer)
async function lrnAnswer(box,choice){
 if(box._busy)return;box._busy=true;const i=+box.dataset.lrnQ,review=box.dataset.lrnReview!==undefined,lesson=box.dataset.lrnLesson||(lrnLesson&&lrnLesson.id),num=box.dataset.lrnNum!==undefined;
 box.querySelectorAll('[data-lrn-choice],[data-lrn-numgo]').forEach(b=>b.disabled=true);
 const a=await postJson('/api/learn/answer',{lesson,i,choice,review},{'X-Token':token||''});box._busy=false;
 if(a.error||a.answer===undefined){box.querySelectorAll('[data-lrn-choice],[data-lrn-numgo]').forEach(b=>b.disabled=false);toast(a.error||'Could not mark it',false);return}
 if(num){const inp=box.querySelector('input');if(inp)inp.disabled=true;box.querySelector('.lrn-out').innerHTML=`<p><b class="${a.right?'up':'dn'}">${a.right?'Right.':`Not quite: the answer is ${a.answer}.`}</b> ${lrnText(a.why)}</p>`}
 else{box.querySelectorAll('[data-lrn-choice]').forEach(b=>{const k=+b.dataset.lrnChoice;if(k===a.answer)b.classList.add('right');else if(k===choice)b.classList.add('wrong')});
 box.querySelector('.lrn-out').innerHTML=`<p><b class="${a.right?'up':'dn'}">${a.right?'Right.':'Not this one.'}</b> ${lrnText(a.why)}</p>`}
 box.querySelector('.lrn-qs').textContent=a.right?'Right':'Answered';
 if(review){if(a.xp)toast(`+${a.xp} XP`,true,2000);return}
 lrnProgress(a)}
// progress that came back with an answer (a question, a chart test or a task check): the header, XP, a pass
function lrnProgress(a){
 const L=lrnLesson;if(!L||!a||a.done===undefined)return;
 const was=L.passed;L.done=a.done;L.passed=a.passed;
 const h=$('lrn-head');if(h)h.innerHTML=lrnHead();
 lrnReveal();
 if(a.xp)toast(`+${a.xp} XP${a.passed&&!was?' with the pass':''}${a.today!==undefined?` · ${a.today} of ${a.goal} today`:''}`,true,2500);
 if(a.passed&&!was){const go=document.querySelector('.lrn-nav a:last-child');if(go)go.classList.add('lrn-go')}}   // (the server's own notice says "Lesson passed")
async function lrnRecheck(box){
 const d=await api('/api/learn/lesson/'+encodeURIComponent(lrnLesson.id));if(!d||d.error)return;
 const i=+box.dataset.lrnTask,done=(d.done||[]).includes(i);
 if(!done){toast(token?'Not done yet: the game has not seen it on your account.':'Sign in first: tasks are checked on your account.',false,3500);return}
 lrnLesson.done=d.done;lrnLesson.passed=d.passed;
 box.outerHTML=lrnBlock(lrnLesson.body.find(b=>b.i===i));lrnProgress(Object.assign({xp:0},d))}

// ---- a page of chart tests
function drawTestPage(kind){
 $('learn-card').classList.add('reading');
 setHtml($('learn-body'),`<div class="lrn-crumb"><a href="/learn">Learn</a> › Chart tests</div><h3 style="margin:8px 0 4px">Chart tests</h3>
  <p class="about" style="margin:0">A real chart from the game, stopped at a moment worth asking about. Pick an answer, then the chart shows what came next and why. Over many charts your score says more than any one answer. The tests with two outcomes (hold or break, real or fake, up or down) are evenly split by design, so always answering the same way scores 50%.</p>
  <div class="lrn-box big" data-lrn-test="${esc(kind)}"><p class="mut">Finding a real chart…</p></div><p class="hint"><a href="/learn">All chart tests and lessons</a></p>`);
 lrnTest(document.querySelector('[data-lrn-test]'),kind)}

// ---- the chart widget: a test (question, then the answer) and a lesson's example
const lrnWhere=w=>w.ticker?`This was <a href="/stock/${encodeURIComponent(w.ticker)}">${esc(w.ticker)}</a> (${esc(w.name)}), ${esc(w.tf)} candles${w.end?`, up to ${new Date(w.end*1000).toLocaleString(undefined,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}`:''}.`:esc(w.name)+'.';
async function lrnTest(el,kind){
 el._kind=kind;el._q=null;el._done=false;el.innerHTML='<p class="mut">Finding a real chart…</p>';
 const q=await api('/api/learn/test?kind='+encodeURIComponent(kind)+(el.dataset.lrnOpt?'&opt='+encodeURIComponent(el.dataset.lrnOpt):''));
 if(!q||q.error||q.slow||!q.candles){el.innerHTML=`<p class="mut">${esc(q&&q.error||'Could not load a chart test.')}</p><button data-lrn-again>Try again</button>`;return}
 el._q=q;
 el.innerHTML=`<div class="lrn-qh"><b>${esc(q.title)}</b><span class="mut">${q.tf==='short'?'a chart from the price model':esc(q.tf)+' candles from the game'}</span></div>
  <div class="lrn-chart">${lrnSvg(q,q.candles.length+25)}</div><p class="lrn-q">${lrnText(q.q)}</p>
  <div class="lrn-opts">${q.options.map((o,i)=>`<button data-lrn-pick="${i}">${esc(o)}</button>`).join('')}</div><div class="lrn-out"></div>`}
async function lrnPick(el,i){
 const q=el._q;if(!q||el._done)return;el._done=true;
 el.querySelectorAll('[data-lrn-pick]').forEach(b=>b.disabled=true);
 const a=await postJson('/api/learn/test',Object.assign({id:q.id,choice:i},el.dataset.lrnI!==undefined&&lrnLesson?{lesson:lrnLesson.id,i:+el.dataset.lrnI}:{},el.dataset.lrnReview!==undefined?{review:true}:{}),{'X-Token':token||''});
 if(a.expired){lrnTest(el,el._kind);return}
 if(a.error||!a.candles){el._done=false;el.querySelectorAll('[data-lrn-pick]').forEach(b=>b.disabled=false);toast(a.error||'Could not mark it',false);return}
 el.querySelector('.lrn-chart').innerHTML=lrnSvg({candles:q.candles.concat(a.candles),upto:q.candles.length-1,lines:a.lines,marks:a.marks,overlay:q.overlay,panel:q.panel},q.candles.length+25);
 el.querySelectorAll('[data-lrn-pick]').forEach(b=>{const k=+b.dataset.lrnPick;if(k===a.answer)b.classList.add('right');else if(k===i)b.classList.add('wrong')});
 el.querySelector('.lrn-out').innerHTML=`<p><b class="${a.right?'up':'dn'}">${a.right?'Right.':'Not this time.'}</b> ${lrnText(a.result)}</p><p class="mut">${lrnText(a.explain)}</p>
  <p class="hint">${lrnWhere(a.where)}${a.score?` Your score at this test: ${a.score[0]} of ${a.score[1]}.`:''}</p><button class="buy" data-lrn-again>Another chart</button>`;
 if(el.dataset.lrnReview!==undefined&&a.xp)toast(`+${a.xp} XP`,true,2000);
 if(a.done!==undefined)lrnProgress(a)}
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
 const qb=t.closest('[data-lrn-q]');if(qb&&t.dataset.lrnChoice!==undefined){lrnAnswer(qb,+t.dataset.lrnChoice);return}
 if(qb&&t.dataset.lrnNumgo!==undefined){const v=parseFloat(qb.querySelector('input').value);if(!isFinite(v)){toast('Type a number first',false);return}lrnAnswer(qb,v);return}
 const pb=t.closest('[data-place-q]');if(pb&&t.dataset.placePick!==undefined){lrnPlacePick(pb,+t.dataset.placePick);return}
 const uf=t.closest('[data-lrn-unfold]');if(uf){uf.closest('.lrn-track').classList.toggle('collapsed');return}
 if(t.id==='place-go'){lrnPlaceGrade();return}
 const tb=t.closest('[data-lrn-task]');if(tb&&t.dataset.lrnRecheck!==undefined){lrnRecheck(tb);return}
 const box=t.closest('[data-lrn-test],[data-lrn-ex]');if(!box)return;
 if(t.dataset.lrnPick!==undefined)lrnPick(box,+t.dataset.lrnPick);
 else if(t.dataset.lrnAgain!==undefined)lrnTest(box,box._kind);
 else if(t.dataset.lrnShow!==undefined)lrnShow(box)});
$('learn-card').addEventListener('change',async e=>{if(e.target.id!=='lrn-goal')return;
 const r=await postJson('/api/learn/goal',{goal:+e.target.value},{'X-Token':token||''});toast(r.msg||r.error||'Error',!!r.ok);lrnView=null;loadLearn()});
// back from the market after a task: a page restored from the back/forward cache is drawn again, so a task box that said
// "Not yet" shows the task done (loop 8)
window.addEventListener('pageshow',e=>{if(e.persisted&&page==='learn'){lrnView=null;loadLearn()}});
