'use strict';
(() => {
  for(const [stageId,rangeId,label] of [['gallery-wipe','gallery-slider','Input and FireDesmoke comparison'],['lab-wipe','lab-split','Clean target and smoke comparison']]){
    const stage=document.getElementById(stageId),range=document.getElementById(rangeId);if(!stage||!range)continue;
    // Labels belong to the same clipped image region as their pixels.
    for (const side of ['left','right']) {
      const tag=stage.querySelector('.image-tag.'+side);
      if (!tag) continue;
      const layer=document.createElement('div');
      layer.className='comparison-label-layer comparison-label-'+side;
      tag.before(layer);layer.append(tag);
    }
    range.tabIndex=-1;
    const handle=stage.querySelector('.comparison-divider');handle.removeAttribute('aria-hidden');handle.tabIndex=0;handle.setAttribute('role','slider');handle.setAttribute('aria-label',label);handle.setAttribute('aria-valuemin','0');handle.setAttribute('aria-valuemax','100');
    const sync=()=>handle.setAttribute('aria-valuenow',range.value);sync();
    new MutationObserver(sync).observe(stage,{attributes:true,attributeFilter:['style']});
    handle.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(e.key))return;e.preventDefault();range.value=e.key==='Home'?0:e.key==='End'?100:Math.max(0,Math.min(100,+range.value+(['ArrowLeft','ArrowDown'].includes(e.key)?-5:5)));range.dispatchEvent(new Event('input',{bubbles:true}));sync();});
  }
  // Dynamically built thumbnail rails share keyboard behavior as well as appearance.
  for(const id of ['lab-fields','lab-backgrounds'])document.getElementById(id)?.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;const buttons=[...e.currentTarget.querySelectorAll('button')],index=buttons.indexOf(e.target);if(index<0)return;e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?buttons.length-1:(index+(e.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length;buttons[next].focus();buttons[next].click();});
})();
