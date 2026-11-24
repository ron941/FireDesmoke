"""Browser regression check for homepage playback, scene selection and split controls.
Requires Playwright and Chromium; run against the local preview server.
Optional: SITE_URL, CHROMIUM_EXECUTABLE, AUDIT_OUTPUT.
"""
import asyncio,os,tempfile
from pathlib import Path
from playwright.async_api import async_playwright,expect
BASE=os.environ.get('SITE_URL','http://127.0.0.1:8080').rstrip('/')
OUT=Path(os.environ.get('AUDIT_OUTPUT',tempfile.mkdtemp(prefix='firedesmoke-interactions-')));OUT.mkdir(exist_ok=True)
async def advances(page,prefix):
    await expect(page.locator('#'+prefix+'-play')).to_have_attribute('aria-pressed','true')
    before=await page.locator('#'+prefix+'-count').inner_text()
    await page.wait_for_function('(x)=>document.querySelector("#"+x[0]+"-count").textContent!==x[1]',arg=[prefix,before],timeout=6000)
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
  for width in [1440,390]:
   page=await browser.new_page(viewport={'width':width,'height':1000},reduced_motion='no-preference');errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   await page.goto(BASE+'/',wait_until='domcontentloaded')
   await expect(page.locator('#motion-stage')).to_have_attribute('aria-busy','false')
   await page.locator('#motion-stage').scroll_into_view_if_needed();await advances(page,'motion')
   for prefix,selector in [('motion','[data-motion-sequence]'),('lab','[data-lab-background]'),('lab','[data-lab-field]'),('lab','[data-lab-mode]')]:
    for button in await page.locator(selector).all():
     await page.locator('#'+prefix+'-stage').scroll_into_view_if_needed()
     await advances(page,prefix)
     # Scene selection must restart even after manually pausing.
     await page.locator('#'+prefix+'-play').click()
     await expect(page.locator('#'+prefix+'-play')).to_have_attribute('aria-pressed','false')
     await button.click();await page.locator('#'+prefix+'-stage').scroll_into_view_if_needed()
     await advances(page,prefix)
   await page.locator('#motion-stage').scroll_into_view_if_needed()
   await page.locator('[data-motion-mode="split"]').click()
   for ident,var in [('motion-stage','--motion-split'),('gallery-wipe','--split'),('lab-wipe','--split')]:
    stage=page.locator('#'+ident);await stage.scroll_into_view_if_needed()
    box=await stage.bounding_box()
    for fraction in [0,.5,1]:
     await page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
     await page.mouse.down();await page.mouse.move(box['x']+box['width']*fraction,box['y']+box['height']/2);await page.mouse.up()
     val=await stage.evaluate('(el,v)=>parseFloat(el.style.getPropertyValue(v))',var)
     assert abs(val-fraction*100)<1,(ident,fraction,val)
     await stage.screenshot(path=str(OUT/f'{width}-{ident}-{fraction}.png'))
    if ident!='motion-stage':
     handle=stage.locator('[role=slider]');await handle.focus();await page.keyboard.press('Home');await expect(handle).to_have_attribute('aria-valuenow','0')
     await page.keyboard.press('End');await expect(handle).to_have_attribute('aria-valuenow','100')
     assert await stage.locator('.comparison-label-layer').count()==2
   await page.locator('#motion-stage').scroll_into_view_if_needed();await page.locator('[data-motion-mode="pair"]').click()
   await page.locator('#motion-filmstrip button').first.click()
   await expect(page.locator('#motion-play')).to_have_attribute('aria-pressed','false')
   await expect(page.locator('#motion-stage')).to_have_attribute('aria-busy','false')
   before=await page.locator('#motion-count').inner_text();await page.wait_for_timeout(900);assert before==await page.locator('#motion-count').inner_text()
   assert await page.locator('#gallery-wipe canvas,#lab-wipe canvas').count()==0
   assert not await page.evaluate('document.documentElement.scrollWidth>innerWidth')
   assert not errors,errors
   print('PASS autoplay, scene switches, split drag/keyboard, sample pause, layout:',width,flush=True)
   await page.close()
  page=await browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
  await page.goto(BASE+'/');await page.locator('#motion-stage').scroll_into_view_if_needed();await page.wait_for_timeout(800)
  await expect(page.locator('#motion-play')).to_have_attribute('aria-pressed','false')
  await page.locator('#motion-play').click();await advances(page,'motion')
  print('PASS reduced-motion preference and explicit playback',flush=True)
  await browser.close()
asyncio.run(main())
