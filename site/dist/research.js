'use strict';
(() => {
  const $ = selector => document.querySelector(selector);
  let research, gallery, curated;
  const request = {field: 0, gallery: 0, haze: 0};
  const state = {group: 'Fireground', level: 'all', active: 'M1'};
  const context = {
    Fireground: 'Curated examples from held-out burns, spanning light to dense smoke.',
    SmokeBench: 'SmokeBench test scenes. FireDesmoke* is trained only on the SmokeBench training split.',
    RealX3D: 'One fixed checkpoint, with no RealX3D adaptation.',
    'Burn chamber': 'The complete FireDesmoke checkpoint, without chamber adaptation. Most evaluated images are clear.'
  };
  function status(message) {
    $('#status').textContent = message;
    $('#status').hidden = !message;
  }
  function option(label, value) {
    const el = document.createElement('option'); el.textContent = label; el.value = value; return el;
  }
  function load(src) {
    return new Promise((resolve, reject) => {
      const image = new Image(); image.onload = () => resolve(image);
      image.onerror = () => reject(new Error('Image unavailable')); image.src = src;
    });
  }
  async function atomic(entries, valid) {
    const present = entries.filter(([id]) => $(id));
    const images = await Promise.all(present.map(([, src]) => load(src)));
    if (!valid()) return false;
    present.forEach(([id], i) => { $(id).src = images[i].src; });
    return true;
  }
  function bindWipe(wipeId, sliderId) {
    const wipe = $(wipeId), slider = $(sliderId);
    if (!wipe || !slider) return;
    function split() {
      wipe.style.setProperty('--split', slider.value + '%');
      slider.setAttribute('aria-valuetext', slider.value + ' percent input, ' + (100 - slider.value) + ' percent FireDesmoke');
    }
    slider.oninput = split; split();
    let dragging = false;
    function move(e) {
      const rect = wipe.getBoundingClientRect();
      slider.value = Math.round(Math.max(0, Math.min(100, (e.clientX - rect.left) / rect.width * 100)));
      split();
    }
    wipe.onpointerdown = e => {
      if (e.button !== 0) return;
      dragging = true; wipe.setPointerCapture(e.pointerId); move(e);
    };
    wipe.onpointermove = e => { if (dragging) move(e); };
    wipe.onpointerup = wipe.onpointercancel = () => { dragging = false; };
    wipe.querySelectorAll('img').forEach(image => { image.draggable = false; });
  }
  async function hero() {
    if (!$('#hero-stage')) return;
    const h = curated.cases.find(c => c.id === curated.default);
    try {
      await atomic([['#hero-before', h.input], ['#hero-after', h.output]], () => true);
      for (const [kind, x, y] of [['dense', 80, 100], ['clear', 340, 280]]) {
        for (const [key, source] of [['in', '#hero-before'], ['out', '#hero-after']]) {
          const canvas = $('#' + kind + '-' + key);
          canvas.getContext('2d').drawImage($(source), x, y, 200, 200, 0, 0, 200, 200);
        }
      }
    } catch (e) { status('The fireground example could not be loaded. Please reload the page.'); }
    finally { $('#hero-stage').setAttribute('aria-busy', 'false'); }
  }
  function allCases() {
    return state.group === 'Fireground' ? curated.cases : gallery.cases.filter(c => c.group === state.group);
  }
  function visibleCases() {
    return allCases().filter(c => state.group !== 'Fireground' || state.level === 'all' || c.level === state.level);
  }
  function thumbnails() {
    const rail = $('#gallery-thumbnails');
    if (!rail) return;
    rail.replaceChildren(...visibleCases().map((c, index) => {
      const button = document.createElement('button'); button.className = 'case-thumbnail';
      button.dataset.case = c.id;
      button.setAttribute('aria-pressed', String(c.id === state.active));
      button.setAttribute('aria-label', 'View ' + c.label + ' example ' + (index + 1));
      const image = document.createElement('img'); image.src = c.input; image.alt = ''; image.loading = 'lazy';
      const text = document.createElement('span'); text.textContent = c.label;
      button.append(image, text); button.onclick = () => showCase(c.id);
      button.onkeydown = e => {
        const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
        if (!keys.includes(e.key)) return;
        e.preventDefault();
        const buttons = [...rail.children], current = buttons.indexOf(button);
        const next = e.key === 'Home' ? 0 : e.key === 'End' ? buttons.length - 1 :
          (current + (e.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
        buttons[next].focus(); buttons[next].click();
      };
      return button;
    }));
  }
  async function showCase(id) {
    const c = allCases().find(c => c.id === id);
    if (!c) return;
    const ticket = ++request.gallery;
    $('#gallery-view').setAttribute('aria-busy', 'true');
    try {
      const [input, output, reference] = await Promise.all([load(c.input), load(c.output), c.reference ? load(c.reference) : null]);
      if (ticket !== request.gallery) return;
      if (input.naturalWidth !== output.naturalWidth || input.naturalHeight !== output.naturalHeight) {
        throw new Error('Input and output dimensions differ');
      }
      $('#gallery-before').src = input.src; $('#gallery-after').src = output.src;
      $('#gallery-wipe').style.aspectRatio = input.naturalWidth + ' / ' + input.naturalHeight;
      $('#gallery-before').alt = c.group + ' input: ' + c.label;
      const modelLabel = c.group === 'SmokeBench' ? 'FireDesmoke*' : 'FireDesmoke';
      $('#gallery-after').alt = modelLabel + ': ' + c.label;
      $('#gallery-wipe [data-visual-role=output]').textContent = modelLabel;
      state.active = c.id;
      document.querySelectorAll('[data-case]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.case === c.id)));
      $('#gallery-caption').textContent = c.group + ' · ' + c.label + (c.group === 'Fireground' ? ' — ' + c.note : '');
      $('#gallery-context').textContent = context[c.group];
      const panel = $('#gallery-reference-panel'); panel.hidden = !reference; panel.open = false;
      if (reference) $('#gallery-reference').src = reference.src;
      else $('#gallery-reference').removeAttribute('src');
      status('');
    } catch (e) { status('The selected example could not be loaded. The last complete comparison is retained.'); }
    finally { if (ticket === request.gallery) $('#gallery-view').setAttribute('aria-busy', 'false'); }
  }
  function group(name) {
    state.group = name; state.level = 'all';
    $('#smoke-filters').hidden = name !== 'Fireground';
    document.querySelectorAll('[data-gallery-group]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.galleryGroup === name)));
    document.querySelectorAll('[data-level]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.level === 'all')));
    const cases = allCases();
    const preferred = name === 'Fireground' ? curated.default : name === 'SmokeBench' ? 'SB2' : name === 'RealX3D' ? 'Akikaze' : 'light smoke';
    const initial = cases.find(c => c.id === preferred || c.label === preferred) || cases[0];
    thumbnails(); showCase(initial.id);
  }
  function level(name) {
    state.level = name;
    document.querySelectorAll('[data-level]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.level === name)));
    thumbnails();
    const cases = visibleCases();
    if (!cases.some(c => c.id === state.active)) showCase(cases[0].id);
  }
  async function field() {
    const ticket = ++request.field;
    $('#transfer-view').setAttribute('aria-busy', 'true');
    try {
      const f = research.fields[+$('#field-select').value], b = +$('#background-select').value, v = f.variants[b];
      const entries = [['#source-field', f.source], ['#clean-field', v.target], ['#render-field', v.measured],
        ['#transmission-field', f.T], ['#airlight-field', f.A], ['#measured-render', v.measured],
        ['#procedural-render', v.procedural], ...['procedural', 'layout', 'airlight', 'measured'].map(k => ['#ablation-' + k, v[k]])];
      if (await atomic(entries, () => ticket === request.field)) {
        if ($('#histogram')) histogram(f.histogram);
        $('#gain').textContent = 'Fixed RGB exposure gain: ' + f.gain.map(x => x.toFixed(3)).join(' / ') + '. Source: ' + f.id + ', frame ' + f.frame + '.';
        status('');
      }
    } catch (e) { status('The selected rendering could not be loaded. The last complete set is retained.'); }
    finally { if (ticket === request.field) $('#transfer-view').setAttribute('aria-busy', 'false'); }
  }
  function histogram(values) {
    const svg = $('#histogram'), peak = Math.max(...values); svg.replaceChildren();
    values.forEach((n, i) => {
      const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      for (const [key, value] of Object.entries({x: i * 18 + 1, width: 16, y: 96 - 92 * n / peak, height: 92 * n / peak, fill: '#146b73'})) r.setAttribute(key, value);
      svg.append(r);
    });
  }
  function tokens(stratum) {
    const values = stratum === 'dense' ? [[.600, .744], [.698, .799], [.679, .771], [.538, .643]] : [[.994, .990], [.993, .992], [.987, .984], [.983, .979]];
    $('#token-chart').replaceChildren(...values.map((v, i) => {
      const row = document.createElement('div'); row.className = 'token-row';
      const title = document.createElement('span'); title.textContent = 'Block ' + [6, 12, 18, 24][i];
      const bars = document.createElement('div'); bars.className = 'bars';
      v.forEach((x, k) => {
        const bar = document.createElement('div'); bar.className = k ? 'after' : 'before'; bar.style.width = x * 100 + '%';
        bar.setAttribute('aria-label', (k ? 'Rectified' : 'Input') + ' tokens: ' + x.toFixed(3));
        const n = document.createElement('span'); n.textContent = x.toFixed(3); bar.append(n); bars.append(bar);
      });
      row.append(title, bars); return row;
    }));
    document.querySelectorAll('[data-stratum]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.stratum === stratum)));
    $('#token-note').textContent = stratum === 'dense' ? 'Dense-smoke tokens move closer to the clean view at all four blocks. The scale is 0–1; rectification is partial.' : 'Clear tokens are already close to the clean view. Rectification slightly lowers their similarity (at most 0.004), rather than improving every token.';
  }
  async function haze() {
    const ticket = ++request.haze;
    try {
      const h = research.haze[+$('#haze-select').value];
      await atomic([['#haze-input', h.input], ['#haze-output', h.output], ['#haze-reference', h.reference]], () => ticket === request.haze);
    } catch (e) { status('The haze example could not be loaded. The last complete comparison is retained.'); }
  }
  function dialog() {
    const element = $('#image-dialog'); let previousFocus = null;
    function openImage(src, title) {
      previousFocus = document.activeElement; $('#full-image').src = src;
      $('#full-image').alt = title; $('#image-title').textContent = title; element.showModal();
    }
    $('#close-image').onclick = () => element.close();
    element.addEventListener('close', () => previousFocus?.focus());
    element.onclick = e => { if (e.target === element) element.close(); };
    document.querySelectorAll('.transfer-story img,.field-inner img,.pair-render img,.ablation-grid img,.scene-grid img,.failure-pair img,.pipeline,#gallery-reference').forEach(image => {
      image.tabIndex = 0; image.setAttribute('role', 'button'); image.setAttribute('aria-label', 'Inspect image: ' + image.alt);
      image.title = 'Open larger view'; image.onclick = () => { if (image.getAttribute('src')) openImage(image.src, image.alt); };
      image.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); image.click(); } };
    });
    document.querySelectorAll('.hero-details canvas').forEach(canvas => {
      canvas.tabIndex = 0; canvas.setAttribute('role', 'button'); canvas.setAttribute('aria-label', 'Inspect ' + canvas.id.replaceAll('-', ' ') + ' detail');
      canvas.onclick = () => openImage(canvas.toDataURL(), 'Same-scale detail');
      canvas.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); canvas.click(); } };
    });
  }
  async function init() {
    try {
      [research, gallery, curated] = await Promise.all(['research.json', 'showcase-data.json', 'homepage-cases.json'].map(async path => {
        const response = await fetch(path); if (!response.ok) throw new Error('Data unavailable'); return response.json();
      }));
      dialog(); bindWipe('#hero-wipe', '#hero-slider'); bindWipe('#gallery-wipe', '#gallery-slider');
      const pending = [hero()];
      if ($('#gallery-thumbnails')) {
        document.querySelectorAll('[data-gallery-group]').forEach(b => { b.onclick = () => group(b.dataset.galleryGroup); });
        document.querySelectorAll('[data-level]').forEach(b => { b.onclick = () => level(b.dataset.level); });
        thumbnails(); pending.push(showCase(curated.default));
      }
      if ($('#field-select')) {
        $('#field-select').replaceChildren(...research.fields.map((f, i) => option(f.label, i))); $('#field-select').value = '2';
        $('#field-select').onchange = field; $('#background-select').onchange = field;
        $('#render-note').textContent = research.render_note;
        $('#render-info').onclick = () => {
          $('#render-note').hidden = !$('#render-note').hidden;
          $('#render-info').setAttribute('aria-expanded', String(!$('#render-note').hidden));
        };
        pending.push(field());
      }
      if ($('#token-chart')) {
        document.querySelectorAll('[data-stratum]').forEach(b => { b.onclick = () => tokens(b.dataset.stratum); }); tokens('dense');
      }
      if ($('#haze-select')) {
        $('#haze-select').replaceChildren(...research.haze.map((h, i) => option(h.label, i))); $('#haze-select').onchange = haze; pending.push(haze());
      }
      if ($('#limit-input')) {
        const c = gallery.cases.find(c => c.group === 'RealX3D' && c.label === 'Tsubaki');
        pending.push(atomic([['#limit-input', c.input], ['#limit-output', c.output], ['#limit-reference', c.reference]], () => true));
      }
      await Promise.all(pending);
    } catch (e) { status('The research collection could not be loaded. Please reload the page.'); }
  }
  init();
})();
