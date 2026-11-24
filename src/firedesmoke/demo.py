"""Loopback-only single-model Gradio application."""
import json
import hashlib
import logging
import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from PIL import Image
from .images import read_image,prepare_demo,as_rgb_array

log=logging.getLogger(__name__)

class RequestStore:
    def __init__(self,root,ttl=3600):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.ttl=ttl;self.active=set();self.lock=threading.Lock()
        self.cleanup()
    def new(self):
        with self.lock:
            p=self.root/uuid.uuid4().hex;p.mkdir();self.active.add(p.name);return p
    def finish(self,path):
        with self.lock:
            os.utime(path,None);self.active.discard(path.name)
    def cleanup(self):
        with self.lock:
            for p in self.root.iterdir():
                if p.is_dir() and not p.is_symlink() and p.name not in self.active and time.time()-p.stat().st_mtime>self.ttl:
                    shutil.rmtree(p)

def clean_expired_cache(root, ttl=3600, protected=()):
    root=Path(root)
    if not root.exists():return
    protected=[Path(p).resolve() for p in protected]
    for item in root.iterdir():
        try:
            if item.is_symlink() or any(p.is_relative_to(item.resolve()) for p in protected):continue
            entries=[item]+list(item.rglob('*')) if item.is_dir() else [item]
            latest=max(p.stat().st_mtime for p in entries)
            if time.time()-latest>ttl:
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        except FileNotFoundError:
            continue

def clean_demo_cache(root, app, active_uploads=()):
    # Initial component assets stay referenced by /config for the app's lifetime.
    # Respect the same keep set as Gradio's own cache cleanup.
    protected=set(active_uploads)
    for component in app.blocks.values():
        protected.update(component.keep_in_cache)
    clean_expired_cache(root,protected=protected)

def build_app(engine,workdir):
    import gradio as gr
    import torch
    store=RequestStore(Path(workdir)/'requests')
    cache=Path(workdir)/'gradio-cache'
    active_uploads=set();cache_lock=threading.Lock()
    clean_expired_cache(cache)
    def clean_loop():
        while True:
            time.sleep(60);store.cleanup()
            with cache_lock:clean_demo_cache(cache,app,active_uploads)
    def preview(path):
        if not path:return None,'Upload a PNG or JPEG to begin.',None,None,'Your result will appear here.'
        try:
            im,meta=prepare_demo(read_image(path,demo=True))
            a,b=meta['original_size'],meta['inference_size']
            return im,f'{a[0]} × {a[1]} → {b[0]} × {b[1]} px',None,None,'Ready to restore this image.'
        except ValueError as e:return None,str(e),None,None,'Please choose a supported image.'
    def restore(path):
        if not path:raise gr.Error('Please choose an image first.')
        request=store.new()
        with cache_lock:active_uploads.add(str(Path(path).resolve()))
        try:
            im,meta=prepare_demo(read_image(path,demo=True))
            result=engine.predict_array(as_rgb_array(im),pad=True)
            out=Image.fromarray(result);output=request/'restored.png';out.save(output,format='PNG')
            (request/'_run.json').write_text(json.dumps({**engine.provenance,**meta,'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2))
            return (im,out),str(output),'Done. Drag the divider to compare input (left) and restored output (right).'
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache();log.warning('Inference failed: CUDA out of memory')
            return None,None,'GPU memory is currently insufficient. Please try again after other work finishes.'
        except ValueError as e:return None,None,str(e)
        except Exception:
            log.exception('Inference failed')
            return None,None,'Restoration failed. Please retry or contact the local maintainer.'
        finally:
            store.finish(request)
            with cache_lock:active_uploads.discard(str(Path(path).resolve()))
    def execute(path):
        if not path:return None,None,'Please choose an image first.',gr.update(interactive=True),gr.update(interactive=True)
        return (*restore(path),gr.update(interactive=True),gr.update(interactive=True))
    css = """
    .gradio-container {width:100%!important;max-width:1440px!important;box-sizing:border-box;margin-left:auto!important;margin-right:auto!important;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif!important;padding:clamp(16px,3vw,36px) clamp(14px,3vw,32px)!important;color:#253436;}
    .gradio-container main.app {padding:0!important;}
    .gradio-container main.app,.gradio-container main.app > .wrap,.gradio-container main.app > .wrap > .contain {width:100%!important;max-width:none!important;}
    #demo-workspace {display:grid!important;grid-template-columns:minmax(260px,0.30fr) minmax(0,0.70fr);width:100%!important;gap:20px;}
    #upload-panel,#output-panel {min-width:0!important;width:100%!important;box-sizing:border-box;}
    #comparison {width:100%!important;height:clamp(360px,40vw,580px)!important;}
    @media(max-width:800px){#demo-workspace{grid-template-columns:minmax(0,1fr)!important;}}
    #demo-heading {text-align:center;margin:0 auto 26px;max-width:760px;}
    #demo-heading h1 {font-size:44px;letter-spacing:-2px;font-weight:750;color:#203b3e;margin-bottom:8px;}
    #demo-heading p {color:#6a7c7e;font-size:17px;}
    #upload-panel,#output-panel {border:1px solid #dfe8e7;border-radius:18px;padding:20px;background:white;box-shadow:0 6px 24px #203b3e05;}
    #upload-panel,#output-panel {justify-content:flex-start;gap:16px;}
    #upload-panel > *,#output-panel > * {flex-grow:0!important;margin-top:0!important;margin-bottom:0!important;}
    #upload-panel #run-btn {margin-top:auto!important;}
    #upload-panel h3,#output-panel h3 {font-size:19px;letter-spacing:-.4px;margin:0 0 8px;}
    #run-btn {background:#146b73;border-color:#146b73;color:white;border-radius:28px;font-weight:600;min-height:48px;}
    #run-btn:hover {background:#10545b;}
    #download-btn {border-radius:28px;border-color:#bfd6d6;background:#f3f9f8;color:#146b73;}
    #result-status,#image-info {font-size:13px;color:#6a7c7e;min-height:20px;}
    #input-preview .image-container {align-items:flex-start!important;}
    #input-preview img {object-position:top center!important;}
    #choose-image {min-height:46px;border-radius:24px;background:#f3f9f8;color:#146b73;border:1px solid #bfd6d6;white-space:normal;}
    #comparison .image-container {height:100%!important;display:flex!important;align-items:center;justify-content:center;}
    #comparison .slider-wrap,#comparison .slider-wrap > .wrap,#comparison .slider-wrap .content {height:100%!important;width:100%!important;position:relative;}
    #comparison .slider-wrap .content img {position:absolute!important;inset:0!important;margin:0!important;width:100%!important;height:100%!important;max-height:100%!important;object-fit:contain!important;object-position:center!important;transform:none!important;}
    #examples {border:none;background:transparent;height:auto!important;overflow:visible!important;}
    #examples .grid-wrap {height:auto!important;max-height:none!important;overflow:visible!important;}
    #examples .gallery-item {min-height:0!important;height:140px!important;}
    #examples .grid-container {grid-template-columns:repeat(4,minmax(0,1fr))!important;grid-template-rows:none!important;grid-auto-rows:140px!important;height:auto!important;}
    #examples .thumbnail-item {border-radius:12px!important;transition:transform .18s,box-shadow .18s;}
    #examples .caption-label {white-space:normal!important;text-overflow:clip!important;max-width:calc(100% - 12px)!important;line-height:1.3;font-size:12px;text-align:left;}
    #examples .thumbnail-item:hover {transform:translateY(-3px);box-shadow:0 5px 14px #146b7320;}
    #demo-footnote {text-align:center;margin-top:12px;font-size:12px;color:#748587;}
    footer {display:none!important;}
    @media(max-width:640px){#examples .gallery-item{height:115px!important;}#examples .grid-container{grid-template-columns:repeat(2,minmax(0,1fr))!important;grid-auto-rows:115px!important;}#input-preview{height:220px!important;}#comparison{height:260px!important;}.gradio-container{padding:20px 14px!important;}#demo-heading h1{font-size:34px;}#upload-panel,#output-panel{padding:14px;}}
    """
    theme=gr.themes.Soft(primary_hue='teal',neutral_hue='slate',
                         font=['system-ui','sans-serif'],font_mono=['monospace']).set(
                             body_background_fill='#fafcfb',body_background_fill_dark='#fafcfb',
                             body_text_color='#253436',body_text_color_dark='#253436')
    # Keep every component in the same light palette, including OS dark mode.
    tokens=theme.to_dict()['theme']
    theme=theme.set(**{key:tokens[key[:-5]] for key in tokens
                       if key.endswith('_dark') and key[:-5] in tokens})
    example_manifest=Path(workdir)/'examples.json'
    examples=[]
    if example_manifest.is_file():
        examples=json.loads(example_manifest.read_text())
    else:
        bundled=Path(__file__).resolve().parents[2]/'demo'/'examples'
        manifest=bundled/'manifest.json'
        if manifest.is_file():
            examples=[{**row,'path':str(bundled/row['file'])} for row in json.loads(manifest.read_text())]
    files=[str(Path(row['path']).resolve()) for row in examples]
    if any(not Path(f).is_file() for f in files):raise FileNotFoundError('A configured demo example is missing.')
    # The divider must use the rendered image rectangle, excluding contain-mode gutters.
    head = """<script>
    (() => {
      let pending = false, observed = null;
      const resize = new ResizeObserver(schedule);
      function schedule() {
        if (pending) return;
        pending = true;
        requestAnimationFrame(() => { pending = false; fit(); });
      }
      function fit() {
        const root = document.querySelector('#comparison');
        if (!root) return;
        if (root !== observed) { resize.disconnect(); resize.observe(root); observed = root; }
        const wrap = root.querySelector('.slider-wrap');
        const img = root.querySelector('.content img');
        if (!wrap || !img || !img.naturalWidth || !root.clientHeight) return;
        const ratio = img.naturalWidth / img.naturalHeight;
        const width = Math.min(root.clientWidth, root.clientHeight * ratio);
        wrap.style.setProperty('width', width + 'px', 'important');
        wrap.style.setProperty('height', (width / ratio) + 'px', 'important');
        wrap.style.setProperty('flex', '0 0 auto');
        let control = wrap.querySelector('.comir-divider-control');
        if (!control) {
          control = document.createElement('div');
          control.className = 'comir-divider-control';
          control.tabIndex = 0;
          control.setAttribute('role', 'slider');
          control.setAttribute('aria-label', 'Input and FireDesmoke comparison');
          control.setAttribute('aria-valuemin', '0');
          control.setAttribute('aria-valuemax', '100');
          control.style.cssText = 'position:absolute;inset:0;z-index:20;cursor:ew-resize;touch-action:none;background:transparent;';
          wrap.appendChild(control);
          control.fraction = 0.5;
          control.paint = () => {
            const x = control.fraction * wrap.getBoundingClientRect().width;
            const result = wrap.querySelector('.content img.fixed');
            const handle = wrap.querySelector('.outer');
            if (result) result.style.setProperty('clip-path', 'inset(0 0 0 ' + (control.fraction * 100) + '%)', 'important');
            if (handle) handle.style.setProperty('transform', 'translateX(' + x + 'px)', 'important');
            control.setAttribute('aria-valuenow', String(Math.round(control.fraction * 100)));
          };
          const move = event => {
            const rect = wrap.getBoundingClientRect();
            control.fraction = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
            control.paint();
          };
          control.addEventListener('pointerdown', event => {
            event.preventDefault(); event.stopPropagation();
            control.focus({preventScroll:true}); control.setPointerCapture(event.pointerId); move(event);
          });
          control.addEventListener('pointermove', event => {
            event.stopPropagation(); if (control.hasPointerCapture(event.pointerId)) move(event);
          });
          control.addEventListener('pointerup', event => {
            event.stopPropagation(); move(event);
            if (control.hasPointerCapture(event.pointerId)) control.releasePointerCapture(event.pointerId);
          });
          for (const name of ['mousedown', 'mousemove', 'mouseup', 'touchstart', 'touchmove', 'touchend', 'click'])
            control.addEventListener(name, event => event.stopPropagation());
          control.addEventListener('keydown', event => {
            const keys = {ArrowLeft:-0.02, ArrowDown:-0.02, ArrowRight:0.02, ArrowUp:0.02};
            if (!(event.key in keys) && event.key !== 'Home' && event.key !== 'End') return;
            event.preventDefault(); event.stopPropagation();
            control.fraction = event.key === 'Home' ? 0 : event.key === 'End' ? 1 : Math.max(0, Math.min(1, control.fraction + keys[event.key]));
            control.paint();
          });
        }
        control.paint();
      }
      new MutationObserver(schedule).observe(document.documentElement,
        {subtree:true, childList:true, attributes:true, attributeFilter:['src']});
      document.addEventListener('load', schedule, true);
      window.addEventListener('resize', schedule);
      schedule();
    })();
    </script>"""
    with gr.Blocks(title='FireDesmoke · Image Restoration',theme=theme,css=css,head=head,delete_cache=(60,3600),analytics_enabled=False) as app:
        gr.Markdown('# FireDesmoke\nRestore your own image.',elem_id='demo-heading')
        with gr.Row(equal_height=True,elem_id="demo-workspace"):
            with gr.Column(scale=3,min_width=270,elem_id='upload-panel'):
                gr.Markdown('### Your image')
                prepared=gr.Image(show_label=False,interactive=False,format='png',height=300,show_download_button=False,elem_id='input-preview')
                upload=gr.File(file_types=['.png','.jpg','.jpeg'],type='filepath',visible=False)
                chooser=gr.UploadButton('Upload / replace image',file_types=['.png','.jpg','.jpeg'],type='filepath',elem_id='choose-image')
                info=gr.Markdown('Choose an image or try an example below.',elem_id='image-info')
                run=gr.Button('Restore image →',variant='primary',elem_id='run-btn')
            with gr.Column(scale=7,min_width=300,elem_id='output-panel'):
                gr.Markdown('### Input → FireDesmoke')
                comparison=gr.ImageSlider(show_label=False,interactive=False,format='png',height=440,elem_id='comparison')
                status=gr.Markdown('Your restoration will appear here.',elem_id='result-status')
                download=gr.DownloadButton('Download PNG',elem_id='download-btn')
        busy=gr.State(False)
        gallery=None
        if files:
            gr.Markdown('### Try an example')
            gallery=gr.Gallery(value=[(f,row.get('label','Example')) for f,row in zip(files,examples)],
                               columns=4,rows=2,height=300,object_fit='cover',show_label=False,
                               allow_preview=False,interactive=False,elem_id='examples')
            def select_example(is_busy,evt:gr.SelectData):
                return gr.skip() if is_busy else files[int(evt.index)]
            gallery.select(select_example,busy,upload,queue=False,api_name=False)
        with gr.Accordion('About this demo',open=False):
            gr.Markdown('PNG or JPEG · up to 20 MB. Images larger than 640 pixels on their longest side are resized without changing their aspect ratio. The dimensions shown before restoration are also the download dimensions. Examples run through the same model as uploads. The complete AdaIR + DINOv3 FireDesmoke model uses 384-pixel overlapping windows and horizontal-flip averaging, including for SmokeBench examples; no ground-truth quality score is estimated. Dense smoke can conceal details the model cannot recover. Uploaded images and results expire after one hour.')
        chooser.upload(lambda path:path,chooser,upload,queue=False,api_name=False)
        upload.change(preview,upload,[prepared,info,comparison,download,status],queue=False,api_name='preview')
        submission=run.click(lambda:('Restoring…',gr.update(interactive=False),gr.update(interactive=False)),None,[status,upload,run],queue=False)
        submission=submission.then(lambda:gr.update(interactive=False),None,chooser,queue=False)
        if gallery is not None:
            submission=submission.then(lambda:True,None,busy,queue=False)
        completion=submission.then(execute,upload,[comparison,download,status,upload,run],concurrency_limit=1,concurrency_id='firedesmoke-model',api_name='restore')
        completion.then(lambda:gr.update(interactive=True),None,chooser,queue=False)
        if gallery is not None:
            completion.then(lambda:False,None,busy,queue=False)
    app.queue(max_size=8,default_concurrency_limit=1)
    threading.Thread(target=clean_loop,daemon=True).start()
    return app

def launch(args):
    workdir=Path(args.workdir).resolve();workdir.mkdir(parents=True,exist_ok=True)
    cache=workdir/'gradio-cache'
    clean_expired_cache(cache)
    os.environ['GRADIO_TEMP_DIR']=str(cache)
    os.environ['GRADIO_ANALYTICS_ENABLED']='False'
    from .runtime import RestorationEngine
    engine=RestorationEngine(args.model,args.registry,args.assets,args.device)
    app=build_app(engine,workdir)
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    class LocalOnlyHeaders(BaseHTTPMiddleware):
        async def dispatch(self,request,call_next):
            response=await call_next(request)
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self' blob:; worker-src 'self' blob:; frame-ancestors 'self'"
            response.headers['Referrer-Policy']='no-referrer'
            response.headers['X-Robots-Tag']='noindex, nofollow, noarchive'
            return response
    app.launch(server_name='127.0.0.1',server_port=args.port,share=False,inbrowser=False,
               app_kwargs={'middleware':[Middleware(LocalOnlyHeaders)]},max_file_size='20mb',allowed_paths=[str(workdir/'requests')],show_error=False)
