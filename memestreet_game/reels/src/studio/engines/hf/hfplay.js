// Lets the studio's frame grabber drive a HyperFrames composition exactly as HyperFrames' own renderer does: at a time t every
// registered GSAP timeline is seeked, each .clip is shown only inside its own data-start / data-duration, and "hf-seek" is fired
// for canvas and three.js layers. The composition stays a plain HyperFrames project (its CLI can lint, check and render it).
// The grabber's contract: window.ready (a promise), window.render(t), window.__R (the reel's data), window.__coverOn (the cover frame).
(function () {
  'use strict';
  window.__timelines = window.__timelines || {};
  window.render = function (t) {
    for (const id in window.__timelines) { const tl = window.__timelines[id]; tl.pause(); tl.seek(Math.min(t, tl.duration()), false); }
    document.querySelectorAll('.clip').forEach(el => { const s = +el.dataset.start || 0, d = parseFloat(el.dataset.duration); el.style.visibility = t >= s && (isNaN(d) || t < s + d) ? 'visible' : 'hidden'; });
    window.dispatchEvent(new CustomEvent('hf-seek', {detail: {time: t, cover: !!window.__coverOn}}));
  };
  window.ready = (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(() => new Promise(ok => {
    const go = () => { if (window.__build) window.__build(window.__R || {}); window.render(0); ok(); };      // (a composition builds itself from the reel's data in window.__build)
    document.readyState === 'complete' ? go() : window.addEventListener('load', go);
  }));
})();
