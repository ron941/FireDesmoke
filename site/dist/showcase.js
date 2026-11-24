'use strict';
(() => {
  const $ = s => document.querySelector(s);
  const names = {gendeg:'GenDeg (NAFNet)',hazeflow:'HazeFlow','moce-ir':'MoCE-IR',histoformer:'Histoformer'};
  let data, current, selectedMethod = '', request = 0;
  function load(src) {
    return new Promise((resolve,reject) => {
      const image = new Image(); image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('Image unavailable')); image.src = src;
    });
  }
  async function choose(c, preferred = selectedMethod) {
    const ticket = ++request;
    const keys = Object.keys(c.methods);
    const method = keys.includes(preferred) ? preferred : keys[0];
    $('#explorer').setAttribute('aria-busy','true');
    $('#compare-method').disabled = true;
    try {
      const images = await Promise.all([c.input,c.output,c.methods[method],...(c.reference ? [c.reference] : [])].map(load));
      if (ticket !== request) return;
      if (images.some(i => i.naturalWidth !== images[0].naturalWidth || i.naturalHeight !== images[0].naturalHeight)) throw new Error('Image dimensions differ');
      current = c; selectedMethod = method;
      ['input-image','output-image','method-image'].forEach((id,i) => { $('#'+id).src = images[i].src; });
      $('#method-label').textContent = names[method] || method;
      const modelLabel = c.group === 'SmokeBench' ? 'FireDesmoke*' : 'FireDesmoke';
      $('[data-visual-role=output]').textContent = modelLabel;
      $('#output-image').alt = modelLabel + ' restoration';
      $('#method-image').alt = (names[method] || method) + ' restoration';
      $('#compare-method').replaceChildren(...keys.map(k => {
        const o = document.createElement('option'); o.value = k; o.textContent = names[k] || k; return o;
      }));
      $('#compare-method').value = method;
      $('#case-note').textContent = c.label + ' — ' + c.note;
      $('#reference').hidden = !c.reference;
      if (c.reference) $('#ref-image').src = images[3].src;
      else $('#ref-image').removeAttribute('src');
      document.querySelectorAll('[data-case]').forEach(b => b.setAttribute('aria-pressed',String(b.dataset.case === c.id)));
      $('#loading').hidden = true;
    } catch (e) {
      if (ticket !== request) return;
      $('#loading').textContent = 'This comparison could not be loaded. Please select another scene or method.';
      $('#loading').hidden = false;
      if (current) $('#compare-method').value = selectedMethod;
    } finally {
      if (ticket === request) { $('#explorer').setAttribute('aria-busy','false'); $('#compare-method').disabled = false; }
    }
  }
  function group(name) {
    const cases = data.cases.filter(c => c.group === name && Object.keys(c.methods).length);
    document.querySelectorAll('[data-group]').forEach(b => b.setAttribute('aria-pressed',String(b.dataset.group === name)));
    $('#cases').replaceChildren(...cases.map(c => {
      const b = document.createElement('button'); b.type = 'button'; b.dataset.case = c.id; b.setAttribute('aria-pressed','false');
      const image = document.createElement('img'); image.src = c.input; image.alt = '';
      const label = document.createElement('span'); label.textContent = c.label;
      b.append(image,label); b.onclick = () => choose(c); return b;
    }));
    choose(cases[0]);
  }
  $('#compare-method').onchange = e => { if (current) choose(current,e.target.value); };
  (async () => {
    try {
      const response = await fetch('showcase-data.json'); if (!response.ok) throw new Error(); data = await response.json();
      $('#explorer').hidden = false;
      $('#groups').replaceChildren(...['Fireground','SmokeBench','RealX3D','Burn chamber'].map(g => {
        const b = document.createElement('button'); b.type = 'button'; b.dataset.group = g; b.textContent = g; b.onclick = () => group(g); return b;
      }));
      group('Fireground');
    } catch (e) { $('#loading').textContent = 'Comparisons are unavailable. Please reload this page.'; }
  })();
})();
