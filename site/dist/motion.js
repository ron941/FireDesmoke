'use strict';
(() => {
  const $ = s => document.querySelector(s), reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const cache = new Map(); let data;
  function image(src) {
    if (cache.has(src)) { const item = cache.get(src); cache.delete(src); cache.set(src, item); return item; }
    const item = new Promise((resolve, reject) => {
      const im = new Image(); im.onload = () => resolve(im);
      im.onerror = () => { cache.delete(src); reject(new Error('Image unavailable')); }; im.src = src;
    });
    cache.set(src, item); if (cache.size > 40) cache.delete(cache.keys().next().value); return item;
  }
  function prefetch(paths) { paths.forEach(src => image(src).catch(() => {})); }
  function message(id, text) { $(id).textContent = text; $(id).hidden = !text; }
  const motion = {sequence:0,index:5,ticket:0,busy:false,playing:false,visible:false,manualPaused:false,userStarted:false,timer:null,images:null,pinned:true,inspect:true,x:154/640,y:164/480};
  let motionWanted = {sequence:0,index:5};
  const lab = {field:0,background:'1',mode:'measured',index:7,ticket:0,busy:false,playing:false,visible:false,manualPaused:false,userStarted:false,timer:null,map:false};
  let labWanted = {field:0,background:'1',mode:'measured',index:7};
  function motionPlay(on, manual=true) {
    clearTimeout(motion.timer); motion.playing = on;
    if (manual) { motion.manualPaused = !on; motion.userStarted = on; if (!on) { motion.ticket++; motion.busy=false; $('#motion-stage').setAttribute('aria-busy','false'); if (motionWanted.sequence===motion.sequence) motionWanted.index=motion.index; } }
    $('#motion-play').innerHTML = on ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M7 5h4v14H7zm6 0h4v14h-4z"/></svg>' : '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="m9 5 11 7-11 7Z"/></svg>'; $('#motion-play').setAttribute('aria-label',on?'Pause sampled sequence':'Play sampled sequence'); $('#motion-play').setAttribute('aria-pressed',String(on));
    if (on && motion.visible && !document.hidden) motion.timer = setTimeout(async () => {
      if (!motion.busy) await renderMotion({sequence:motion.sequence,index:(motion.index+1)%data.sequences[motion.sequence].frames.length});
      if (motion.playing) motionPlay(true,false);
    },450);
  }
  function labPlay(on, manual=true) {
    clearTimeout(lab.timer); lab.playing = on;
    if (manual) { lab.manualPaused = !on; lab.userStarted = on; if (!on) { lab.ticket++; lab.busy=false; $('#lab-stage').setAttribute('aria-busy','false'); if (labWanted.field===lab.field) labWanted.index=lab.index; } }
    $('#lab-play').innerHTML = on ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M7 5h4v14H7zm6 0h4v14h-4z"/></svg>' : '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="m9 5 11 7-11 7Z"/></svg>'; $('#lab-play').setAttribute('aria-label',on?'Pause smoke':'Play smoke'); $('#lab-play').setAttribute('aria-pressed',String(on));
    if (on && lab.visible && !document.hidden) lab.timer = setTimeout(async () => {
      if (!lab.busy) await renderLab({field:lab.field,background:lab.background,mode:lab.mode,index:(lab.index+1)%data.fields[lab.field].frames.length});
      if (lab.playing) labPlay(true,false);
    },450);
  }
  function visibility() {
    motionPlay(motion.visible && !document.hidden && !motion.manualPaused && (!reduced.matches || motion.userStarted),false);
    labPlay(lab.visible && !document.hidden && !lab.manualPaused && (!reduced.matches || lab.userStarted),false);
  }
  async function selectMotion(changes) {
    motionPlay(false,false);
    motion.manualPaused=false;
    await renderMotion(changes);
    visibility();
  }
  async function selectLab(changes) {
    labPlay(false,false);
    lab.manualPaused=false;
    await renderLab(changes);
    visibility();
  }
  function inspect(on) {
    motion.inspect = on && !!motion.images && $('#motion-stage').dataset.mode === 'pair';
    $('#motion-inspect').setAttribute('aria-pressed',String(motion.pinned));
    ['input','output'].forEach(key => {
      $('#motion-'+key+'-crop').hidden = !motion.inspect;
      $('#motion-'+key+'-inset').hidden = !motion.inspect;
    });
    if (!motion.inspect) return;
    const width=motion.images[0].naturalWidth, height=motion.images[0].naturalHeight, size=128;
    const x=Math.round(Math.max(0,Math.min(width-size,motion.x*width-size/2)));
    const y=Math.round(Math.max(0,Math.min(height-size,motion.y*height-size/2)));
    $('#motion-stage').dataset.crop=[x,y,size,size].join(',');
    ['input','output'].forEach((key,i) => {
      const canvas=$('#motion-'+key+'-detail');
      canvas.getContext('2d').drawImage(motion.images[i],x,y,size,size,0,0,size,size);
      const marker=$('#motion-'+key+'-crop');
      Object.assign(marker.style,{left:x/width*100+'%',top:y/height*100+'%',width:size/width*100+'%',height:size/height*100+'%'});
    });
  }
  function mode(name) {
    $('#motion-stage').dataset.mode=name;
    document.querySelectorAll('[data-motion-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.motionMode===name)));
    inspect(name==='pair' && motion.pinned);
    $('#motion-hint').textContent=name==='pair'?'Move over either image to inspect the same detail.':'Drag across the image to compare input and restoration.';
  }
  function railKeys(rail) {
    rail.addEventListener('keydown',e=>{
      if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
      const buttons=[...rail.querySelectorAll('button')], current=buttons.indexOf(e.target);
      if(current<0)return; e.preventDefault();
      const next=e.key==='Home'?0:e.key==='End'?buttons.length-1:Math.max(0,Math.min(buttons.length-1,current+(e.key==='ArrowLeft'?-1:1)));
      buttons[next].focus({preventScroll:true});buttons[next].click();
      buttons[next].scrollIntoView({block:'nearest',inline:'nearest',behavior:reduced.matches?'instant':'smooth'});
    });
  }
  function frameRail(seq) {
    $('#motion-filmstrip').replaceChildren(...seq.frames.map((frame,i)=>{
      const b=document.createElement('button');b.type='button';b.dataset.sample=i;
      b.setAttribute('aria-label','Show sample '+(i+1)+' of '+seq.frames.length);
      const im=new Image();im.src=frame.input;im.alt='';im.draggable=false;
      const n=document.createElement('span');n.textContent=String(i+1).padStart(2,'0');b.append(im,n);
      b.onclick=()=>{motionPlay(false);renderMotion({index:i});};return b;
    }));
  }
  async function renderMotion(changes={}) {
    Object.assign(motionWanted,changes);const wanted={...motionWanted},seq=data.sequences[wanted.sequence],frame=seq.frames[wanted.index];
    const ticket=++motion.ticket;motion.busy=true;$('#motion-stage').setAttribute('aria-busy','true');
    try {
      const images=await Promise.all([image(frame.input),image(frame.output)]);
      if(ticket!==motion.ticket)return;
      if(images.some(im=>im.naturalWidth!==images[0].naturalWidth||im.naturalHeight!==images[0].naturalHeight))throw new Error('Mismatched dimensions');
      const changedSequence=motion.sequence!==wanted.sequence||!motion.images;
      Object.assign(motion,wanted,{images});
      $('#motion-input').src=images[0].src;$('#motion-output').src=images[1].src;
      $('#motion-stage').dataset.sourceFrame=String(frame.source_frame);$('#motion-stage').dataset.sequence=seq.id;
      $('#motion-case-note').textContent=seq.note;
      $('#motion-frame').max=seq.frames.length-1;$('#motion-frame').value=String(wanted.index);
      $('#motion-frame').setAttribute('aria-valuetext','Sample '+(wanted.index+1)+' of '+seq.frames.length);
      $('#motion-count').textContent=String(wanted.index+1).padStart(2,'0')+' / '+String(seq.frames.length).padStart(2,'0');
      document.querySelectorAll('[data-motion-sequence]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.motionSequence===wanted.sequence)));
      if(changedSequence)frameRail(seq);
      document.querySelectorAll('[data-sample]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.sample===wanted.index)));
      const rail=$('#motion-filmstrip'), selected=rail.querySelector('[aria-pressed=true]');
      if(selected) {
        const item=selected.getBoundingClientRect(), bounds=rail.getBoundingClientRect();
        if(item.left<bounds.left+6||item.right>bounds.right-6)rail.scrollTo({left:rail.scrollLeft+item.left-bounds.left-(bounds.width-item.width)/2,behavior:reduced.matches?'instant':'smooth'});
      }
      if(motion.pinned)inspect(true);
      const next=[1,2].flatMap(d=>{const f=seq.frames[(wanted.index+d)%seq.frames.length];return[f.input,f.output];});prefetch(next);
      message('#motion-status','');
    } catch(e) {
      if(ticket!==motion.ticket)return;
      motionPlay(false);motionWanted={sequence:motion.sequence,index:motion.index};$('#motion-frame').value=String(motion.index);
      message('#motion-status','This sample could not be loaded. The last complete pair is retained; choose a sample to retry.');
    } finally {if(ticket===motion.ticket){motion.busy=false;$('#motion-stage').setAttribute('aria-busy','false');}}
  }
  function labFrameRail(field,wanted){
    $('#lab-filmstrip').replaceChildren(...field.frames.map((frame,i)=>{
      const button=document.createElement('button');button.type='button';button.dataset.labSample=i;
      button.setAttribute('aria-label','Show smoke sample '+(i+1)+' of '+field.frames.length);
      const im=new Image();im.src=frame.backgrounds[wanted.background][wanted.mode];im.alt='';im.draggable=false;
      const n=document.createElement('span');n.textContent=String(i+1).padStart(2,'0');button.append(im,n);
      button.onclick=()=>{labPlay(false);renderLab({index:i});};return button;
    }));
  }
  async function renderLab(changes={}) {
    Object.assign(labWanted,changes);const wanted={...labWanted};const field=data.fields[wanted.field],frame=field.frames[wanted.index],v=frame.backgrounds[wanted.background];
    const ticket=++lab.ticket;lab.busy=true;$('#lab-stage').setAttribute('aria-busy','true');
    try {
      const images=await Promise.all([image(frame.source),image(frame.T),image(v.target),image(v[wanted.mode])]);
      if(ticket!==lab.ticket)return;
      const changedRail=!lab.images||lab.field!==wanted.field||lab.background!==wanted.background||lab.mode!==wanted.mode;
      Object.assign(lab,wanted);lab.images=images;
      if(changedRail)labFrameRail(field,wanted);
      $('#lab-source').src=images[lab.map?1:0].src;$('#lab-clean').src=images[2].src;$('#lab-render').src=images[3].src;
      $('#lab-render-label').textContent=lab.mode==='measured'?'MEASURED SMOKE':'PROCEDURAL SMOKE';
      $('#lab-source-caption').textContent=lab.map?'Transmission T · dark is opaque':'Recorded smoke';
      $('#lab-stage').dataset.sourceFrame=String(frame.source_frame);$('#lab-stage').dataset.field=String(wanted.field);$('#lab-stage').dataset.background=wanted.background;$('#lab-stage').dataset.renderMode=wanted.mode;
      $('#lab-frame').max=field.frames.length-1;$('#lab-frame').value=String(wanted.index);$('#lab-frame').setAttribute('aria-valuetext','Measured smoke sample '+(wanted.index+1)+' of '+field.frames.length);
      $('#lab-count').textContent=String(wanted.index+1).padStart(2,'0')+' / '+String(field.frames.length).padStart(2,'0');
      const rail=$('#lab-filmstrip');rail.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.labSample===wanted.index)));
      const selected=rail.querySelector('[aria-pressed=true]');
      if(selected){const item=selected.getBoundingClientRect(),bounds=rail.getBoundingClientRect();if(item.left<bounds.left+6||item.right>bounds.right-6)rail.scrollTo({left:rail.scrollLeft+item.left-bounds.left-(bounds.width-item.width)/2,behavior:reduced.matches?'instant':'smooth'});}
      $('#lab-caption').textContent=field.label+' · '+data.backgrounds.find(b=>b.id===wanted.background).label+' · '+(wanted.mode==='measured'?'Measured layout and spatial airlight':'Matched procedural layout and mean airlight');
      document.querySelectorAll('[data-lab-field]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.labField===wanted.field)));
      document.querySelectorAll('[data-lab-background]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.labBackground===wanted.background)));
      document.querySelectorAll('[data-lab-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.labMode===wanted.mode)));
      const next=field.frames[(wanted.index+1)%field.frames.length],nv=next.backgrounds[wanted.background];prefetch([next.source,next.T,nv.target,nv[wanted.mode]]);
      message('#lab-status','');
    }catch(e){
      if(ticket!==lab.ticket)return;
      labPlay(false);labWanted={field:lab.field,background:lab.background,mode:lab.mode,index:lab.index};$('#lab-frame').value=String(lab.index);
      message('#lab-status','This field sample could not be loaded. The last complete rendering is retained; select a sample to retry.');
    }finally{if(ticket===lab.ticket){lab.busy=false;$('#lab-stage').setAttribute('aria-busy','false');}}
  }
  function bindInput() {
    $('#motion-sequences').replaceChildren(...data.sequences.map((s,i)=>{
      const b=document.createElement('button');b.type='button';b.dataset.motionSequence=i;
      b.setAttribute('aria-pressed',String(i===0));b.setAttribute('aria-label','View smoke sequence '+(i+1));
      const im=new Image();im.src=s.frames[s.initial].input;im.alt='';im.draggable=false;
      const caption=document.createElement('span');caption.textContent='Sequence '+String(i+1).padStart(2,'0');b.append(im,caption);
      b.onclick=()=>{selectMotion({sequence:i,index:s.initial});};return b;
    }));
    railKeys($('#motion-sequences'));railKeys($('#motion-filmstrip'));railKeys($('#lab-filmstrip'));
    $('#motion-play').onclick=()=>motionPlay(!motion.playing);
    $('#motion-frame').oninput=()=>{motionPlay(false);renderMotion({index:+$('#motion-frame').value});};
    document.querySelectorAll('[data-motion-mode]').forEach(b=>b.onclick=()=>mode(b.dataset.motionMode));
    $('#motion-inspect').onclick=()=>{if($('#motion-stage').dataset.mode!=='pair'){mode('pair');motion.pinned=true;}else motion.pinned=!motion.pinned;inspect(motion.pinned);};
    $('#motion-player').addEventListener('keydown',e=>{if(e.key==='Escape'){motion.pinned=false;inspect(false);}});
    for(const key of ['input','output']) {
      const pane=$('#motion-'+key+'-pane');
      function point(e){if($('#motion-stage').dataset.mode!=='pair'||!motion.pinned)return;const r=pane.getBoundingClientRect();motion.x=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width));motion.y=Math.max(0,Math.min(1,(e.clientY-r.top)/r.height));inspect(true);}
      pane.onpointermove=e=>{if(e.pointerType==='mouse'||e.buttons)point(e);};
      pane.onpointerdown=e=>{if(e.button!==0)return;point(e);};
      pane.onkeydown=e=>{
        if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;
        e.preventDefault();
        if($('#motion-stage').dataset.mode==='split') {const value=parseFloat($('#motion-stage').style.getPropertyValue('--motion-split'))||50;$('#motion-stage').style.setProperty('--motion-split',Math.max(0,Math.min(100,value+(e.key==='ArrowLeft'||e.key==='ArrowUp'?-5:5)))+'%');return;}
        motion.pinned=true;if(e.key==='ArrowLeft')motion.x-=.025;if(e.key==='ArrowRight')motion.x+=.025;if(e.key==='ArrowUp')motion.y-=.025;if(e.key==='ArrowDown')motion.y+=.025;
        motion.x=Math.max(0,Math.min(1,motion.x));motion.y=Math.max(0,Math.min(1,motion.y));inspect(true);
      };
    }
    let dragging=false;const stage=$('#motion-stage');
    function split(e){const r=stage.getBoundingClientRect();stage.style.setProperty('--motion-split',Math.max(0,Math.min(100,100*(e.clientX-r.left)/r.width))+'%');}
    stage.addEventListener('pointerdown',e=>{if(stage.dataset.mode!=='split'||e.button!==0)return;dragging=true;stage.setPointerCapture(e.pointerId);split(e);});
    stage.addEventListener('pointermove',e=>{if(dragging)split(e);});stage.addEventListener('pointerup',()=>{dragging=false;});stage.addEventListener('pointercancel',()=>{dragging=false;});stage.querySelectorAll('img').forEach(im=>im.draggable=false);
    $('#lab-fields').replaceChildren(...data.fields.map((f,i)=>{
      const b=document.createElement('button');b.dataset.labField=i;b.setAttribute('aria-pressed',String(i===0));b.setAttribute('aria-label',f.label);
      const im=new Image();im.src=f.frames[f.initial].source;im.alt='';const span=document.createElement('span');span.textContent='Smoke '+(i+1);b.append(im,span);b.onclick=()=>{selectLab({field:i,index:f.initial});};return b;
    }));
    $('#lab-backgrounds').replaceChildren(...data.backgrounds.map(background=>{
      const b=document.createElement('button');b.dataset.labBackground=background.id;b.setAttribute('aria-pressed',String(background.id==='1'));const im=new Image();im.src=background.image;im.alt='';const span=document.createElement('span');span.textContent=background.label;b.append(im,span);b.onclick=()=>{selectLab({background:background.id});};return b;
    }));
    document.querySelectorAll('[data-lab-mode]').forEach(b=>b.onclick=()=>{selectLab({mode:b.dataset.labMode});});
    $('#lab-play').onclick=()=>labPlay(!lab.playing);$('#lab-frame').oninput=()=>{labPlay(false);renderLab({index:+$('#lab-frame').value});};
    $('#lab-map').onclick=()=>{lab.map=!lab.map;$('#lab-map').setAttribute('aria-pressed',String(lab.map));$('#lab-map').textContent=lab.map?'Show smoke':'Show T';if(lab.images){$('#lab-source').src=lab.images[lab.map?1:0].src;$('#lab-source-caption').textContent=lab.map?'Transmission T · dark is opaque':'Recorded smoke';}};
    const wipe=$('#lab-wipe'),range=$('#lab-split');function reveal(){wipe.style.setProperty('--split',range.value+'%');range.setAttribute('aria-valuetext',range.value+' percent clean target');}range.oninput=reveal;reveal();let labDragging=false;
    function labSplit(e){const r=wipe.getBoundingClientRect();range.value=Math.max(0,Math.min(100,100*(e.clientX-r.left)/r.width));reveal();}
    wipe.onpointerdown=e=>{if(e.button!==0)return;labDragging=true;wipe.setPointerCapture(e.pointerId);labSplit(e);};wipe.onpointermove=e=>{if(labDragging)labSplit(e);};wipe.onpointerup=wipe.onpointercancel=()=>{labDragging=false;};wipe.querySelectorAll('img').forEach(im=>im.draggable=false);
  }
  async function init(){
    try{
      const response=await fetch('motion.json');if(!response.ok)throw new Error('Missing motion data');data=await response.json();motion.index=data.sequences[0].initial;motionWanted.index=motion.index;bindInput();await Promise.all([renderMotion(),renderLab()]);
      const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.target.id==='motion-player')motion.visible=entry.isIntersecting;else lab.visible=entry.isIntersecting;});visibility();},{threshold:.2});observer.observe($('#motion-player'));observer.observe($('#smoke-lab'));
      document.addEventListener('visibilitychange',visibility);reduced.addEventListener('change',visibility);window.addEventListener('pagehide',()=>{motionPlay(false,false);labPlay(false,false);});
    }catch(e){message('#motion-status','The interactive samples could not be loaded. Please reload to retry.');message('#lab-status','The field samples could not be loaded. Please reload to retry.');$('#motion-stage').setAttribute('aria-busy','false');$('#lab-stage').setAttribute('aria-busy','false');}
  }
  init();
})();
