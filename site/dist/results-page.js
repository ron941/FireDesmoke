'use strict';
const datasets = {
  fire: {name:'Fireground',title:'Held-out fireground recordings',description:'1,500 test frames. The complete FireDesmoke model is evaluated on fire recordings held out from training.',headers:['Dense PSNR ↑','Dense SSIM ↑','Medium PSNR ↑','Clear PSNR ↑','Overall PSNR ↑','Overall SSIM ↑','Object PSNR ↑'],selected:['Input','AutoDIR','Histoformer','DiffUIR','FireDesmoke','FireDesmoke*'],note:'Table S2. PSNR in dB. Training groups are shown separately; FireDesmoke* uses only SmokeBench training pairs.'},
  smokebench: {name:'SmokeBench',title:'Public smoke · SmokeBench',description:'100 image pairs. FireDesmoke* is the model trained only on the SmokeBench training split.',headers:['Y-PSNR ↑','Y-SSIM ↑','LPIPS ↓'],selected:['Input','FireDesmoke*','PGDR* (SmokeBench)','DVANet* (SmokeBench)','Uformer-B* (SmokeBench)','MB-TaylorFormer†'],note:'Table S7. Official SmokeBench evaluation: Y-channel PSNR/SSIM, 4-pixel border crop and AlexNet LPIPS. * trained by us on SmokeBench; † authors’ released outputs; ◇ trained or adapted by us on other data.'},
  realx3d: {name:'RealX3D',title:'Public smoke · RealX3D',description:'The complete FireDesmoke model is evaluated without RealX3D adaptation.',headers:['PSNR ↑','SSIM ↑','Scene-mean PSNR ↑'],selected:['Input','FireDesmoke','GenDeg (NAFNet)'],note:'Table S8. RGB evaluation. Frame-average PSNR and scene-average PSNR are listed separately. Training groups remain separate.'},
  haze: {name:'Public haze',title:'Public dehazing benchmarks',description:'Five public haze datasets, evaluated with the complete FireDesmoke model.',headers:['O-HAZE ↑','I-HAZE ↑','NH-HAZE ↑','Dense-Haze ↑','RESIDE-6K ↑','Mean ↑'],selected:['FireDesmoke','ConvIR-B (O-HAZE)','ConvIR-B (I-HAZE)','HistoFusionNet (NH-HAZE)'],note:'Table S9. RGB PSNR in dB. # marks a checkpoint trained on that dataset. Models trained or adapted on the test images are listed separately and are not ranked.'}
};
const tabs = [...document.querySelectorAll('[role=tab]')];
let resultData = null;
let activeDataset = 'fire';
let allRows = false;
function renderResults() {
  const data=datasets[activeDataset];
  document.querySelector('#dataset-title').textContent=data.title;
  document.querySelector('#dataset-description').textContent=data.description;
  document.querySelector('#results-caption').textContent=`${data.name} · ${allRows?'All manuscript rows':'Selected comparisons'} · PSNR in dB`;
  document.querySelector('#training-note').textContent=data.note;
  if (!resultData) return;
  const head=document.querySelector('#results-head'); head.replaceChildren();
  const tr=document.createElement('tr');
  ['Method / checkpoint',...data.headers].forEach(label=>{const th=document.createElement('th');th.scope='col';th.textContent=label;tr.append(th);});head.append(tr);
  const body=document.querySelector('#results-body');body.replaceChildren();
  const rows=resultData.datasets[activeDataset].filter(row=>allRows||data.selected.includes(row.method));
  let group=null;
  rows.forEach(row=>{
    const label=row.method==='Input'?'Reference input':row.group;
    if(group!==label){const heading=document.createElement('tr');heading.className='group-row';const cell=document.createElement('th');cell.colSpan=data.headers.length+1;cell.scope='colgroup';cell.textContent=label;heading.append(cell);body.append(heading);group=label;}
    const line=document.createElement('tr');if(row.method.startsWith('FireDesmoke'))line.className='ours';
    const method=document.createElement('th');method.scope='row';method.textContent=row.method;line.append(method);
    row.values.forEach(value=>{const cell=document.createElement('td');cell.textContent=value==='--'?'—':value;line.append(cell);});body.append(line);
  });
  document.querySelector('#result-count').textContent=`${rows.length} of ${resultData.datasets[activeDataset].length} rows shown`;
  const button=document.querySelector('#show-all');button.textContent=allRows?'Show selected comparisons':'Show all manuscript rows';button.setAttribute('aria-expanded',String(allRows));
}
function selectDataset(button,focus=false){activeDataset=button.dataset.dataset;allRows=false;tabs.forEach(tab=>{const active=tab===button;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;});document.querySelector('#result-panel').setAttribute('aria-labelledby',button.id);renderResults();if(focus)button.focus();}
tabs.forEach((tab,index)=>{tab.addEventListener('click',()=>selectDataset(tab));tab.addEventListener('keydown',event=>{let next;if(event.key==='ArrowRight')next=(index+1)%tabs.length;if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;if(event.key==='Home')next=0;if(event.key==='End')next=tabs.length-1;if(next!==undefined){event.preventDefault();selectDataset(tabs[next],true);}});});
document.querySelector('#show-all').addEventListener('click',()=>{allRows=!allRows;renderResults();});
fetch('results.json').then(response=>{if(!response.ok)throw new Error('Results unavailable');return response.json();}).then(data=>{resultData=data;renderResults();}).catch(()=>{document.querySelector('.result-loading').hidden=false;document.querySelector('#show-all').disabled=true;});
