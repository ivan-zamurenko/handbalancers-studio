import {test, expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';

async function ready(page, language = 'uk') {
  await page.route('**/api/session', route => route.fulfill({json:{authenticated:false}}));
  await page.goto(`/login?lang=${language}`);
  await expect(page.locator('[data-loading-indicator]')).toBeAttached();
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
}

for (const width of [390, 1440]) for (const theme of ['light', 'dark']) {
  test(`explicit screen loading uses centered handstand after 500ms ${width} ${theme}`, async ({page}) => {
    await page.setViewportSize({width, height:800});
    await page.addInitScript(value => localStorage.setItem('studio:theme:guest', value), theme);
    await ready(page);
    let release;
    const held = new Promise(resolve => {release = resolve;});
    await page.route('**/api/loading-example', async route => {await held; await route.fulfill({json:{ok:true}});});
    await page.evaluate(() => {window.work = import('/static/js/api/client.js').then(({requestApi})=>requestApi('/api/loading-example',{loading:'screen'}));});
    const indicator = page.locator('[data-loading-indicator]');
    await expect(indicator).toBeVisible();
    await expect(indicator).toHaveAttribute('role','status');
    await expect(indicator).toContainText('Завантажуємо');
    await expect(indicator.locator('svg')).toHaveAttribute('aria-hidden','true');
    expect(await indicator.evaluate(el=>getComputedStyle(el).pointerEvents)).toBe('none');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const box = await indicator.locator('.loading-card').boundingBox();
    expect(box.width).toBeLessThan(260); expect(box.height).toBeLessThan(240);
    expect(Math.abs(box.x+box.width/2-width/2)).toBeLessThan(2);
    expect(Math.abs(box.y+box.height/2-400)).toBeLessThan(2);
    expect(await indicator.evaluate(el=>getComputedStyle(el).backgroundColor)).not.toBe('rgba(0, 0, 0, 0)');
    await expect(indicator.locator('[data-handstand-cycle]')).toHaveCount(1);
    await page.screenshot({path:test.info().outputPath('handstand.png')});
    release(); await page.evaluate(()=>window.work);
    await expect(indicator).toBeHidden();
  });
}

test('concurrent API work stays visible until all settle, including network failure', async ({page}) => {
  await ready(page,'en');
  const releases = {};
  await page.route('**/api/held/*', async route => {
    const id = route.request().url().split('/').pop();
    await new Promise(resolve => {releases[id] = resolve;});
    if (id === 'failure') await route.abort(); else await route.fulfill({json:{ok:true}});
  });
  await page.evaluate(async () => {
    const {requestApi} = await import('/static/js/api/client.js');
    window.first = requestApi('/api/held/success',{loading:'screen'});
    window.second = requestApi('/api/held/failure',{loading:'screen'}).catch(()=>null);
  });
  await expect.poll(()=>Object.keys(releases).length).toBe(2);
  const indicator = page.locator('[data-loading-indicator]');
  await expect(indicator).toBeVisible();
  await expect(indicator).toContainText('Loading');
  releases.success(); await page.evaluate(()=>window.first);
  await expect(indicator).toBeVisible();
  releases.failure(); await page.evaluate(()=>window.second);
  await expect(indicator).toBeHidden();
});

test('fast work does not flash; abort and history restore clear loading', async ({page}) => {
  await ready(page);
  await page.route('**/api/fast', route=>route.fulfill({json:{ok:true}}));
  await page.evaluate(async () => {
    window.shown = false;
    const el = document.querySelector('[data-loading-indicator]');
    new MutationObserver(records=>{if(records.some(r=>r.attributeName==='hidden') && !el.hidden) window.shown = true;}).observe(el,{attributes:true});
    const {requestApi} = await import('/static/js/api/client.js');
    await requestApi('/api/fast',{loading:'screen'});
  });
  await page.waitForTimeout(650);
  expect(await page.evaluate(()=>window.shown)).toBe(false);
  await page.route('**/api/hang', route=>route.abort('timedout'));
  await page.evaluate(async () => {
    const {requestApi} = await import('/static/js/api/client.js');
    const controller = new AbortController(); controller.abort();
    await requestApi('/api/hang',{signal:controller.signal}).catch(()=>{});
    const {beginLoading} = await import('/static/js/components/loading.js');
    window.finish = beginLoading({mode:'screen'});
  });
  await expect(page.locator('[data-loading-indicator]')).toBeVisible();
  await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await page.evaluate(()=>{window.finish(); window.finish();});
});

test('navigation uses only the top bar and respects reduced motion', async ({page}) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  await ready(page);
  let release;
  const held = new Promise(resolve=>{release=resolve;});
  await page.route('**/recovery?lang=uk', async route=>{await held; await route.continue();});
  // Observe before navigation: Playwright DOM queries wait for its commit.
  let snapshot;
  await page.exposeFunction('reportLoading',value=>{snapshot=value;});
  await page.evaluate(()=>{
    const element=document.querySelector('[data-loading-navigation]');
    new MutationObserver(()=>window.reportLoading({visible:!element.hidden,
      screenVisible:!document.querySelector('[data-loading-indicator]').hidden,
      animations:element.getAnimations({subtree:true}).length})).observe(element,{attributes:true});
  });
  await page.getByRole('link',{name:'Забули пароль?'}).click({noWaitAfter:true});
  const indicator = page.locator('[data-loading-indicator]');
  await expect.poll(()=>snapshot?.visible).toBe(true);
  expect(snapshot.animations).toBe(0);
  expect(snapshot.screenVisible).toBe(false);
  release();
  await expect(page).toHaveURL(/\/recovery\?lang=uk$/);
  await expect(indicator).toBeHidden();
});

test('public page assets use only the top bar until the load event', async ({page}) => {
  let release;
  const held = new Promise(resolve=>{release=resolve;});
  await page.route('**/api/session', route=>route.fulfill({json:{authenticated:false}}));
  await page.route('**/held-image.svg', async route=>{
    await held;
    await route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'});
  });
  await page.route('**/login', async route=>{
    const response = await route.fetch();
    await route.fulfill({response,body:(await response.text()).replace('</body>','<img src="/held-image.svg" alt=""></body>')});
  });
  await page.goto('/login',{waitUntil:'domcontentloaded'});
  await expect(page.locator('[data-loading-navigation]')).toBeVisible();
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  release();
  await page.waitForLoadState('load');
  await expect(page.locator('[data-loading-navigation]')).toBeHidden();
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
});

test('body parsing and HTTP errors finish correctly', async ({page}) => {
  await ready(page);
  await page.evaluate(async () => {
    const {requestApi} = await import('/static/js/api/client.js');
    window.bodyWork = requestApi('/test', {loading:'screen',fetchImpl:async()=>({
      ok:true, status:200, headers:new Headers({'Content-Type':'application/json'}),
      json:()=>new Promise(resolve=>{window.releaseBody=resolve;}),
    })});
  });
  await expect(page.locator('[data-loading-indicator]')).toBeVisible();
  await page.evaluate(async()=>{window.releaseBody({ok:true}); await window.bodyWork;});
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await page.route('**/api/rejected', route=>route.fulfill({status:503,json:{}}));
  expect(await page.evaluate(async()=>{
    const {requestApi} = await import('/static/js/api/client.js');
    try {await requestApi('/api/rejected');} catch (error) {return error.status;}
  })).toBe(503);
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
});

test('anchors, downloads, other tabs and cancelled navigation do not start loading', async ({page}) => {
  await ready(page);
  await page.evaluate(()=>{
    const examples = [
      {href:'#'}, {href:'/login#login-form'},
      {href:'/recovery',target:'_blank'}, {href:'/recovery',download:'file'},
      {href:'https://example.test/'}, {href:'/recovery'},
    ];
    for (const attrs of examples) {
      const link=document.createElement('a'); Object.assign(link,attrs); document.body.append(link);
      // Window cancellation runs after the document's loading listener.
      window.addEventListener('click',event=>event.preventDefault(),{once:true});
      link.click(); link.remove();
    }
  });
  await page.waitForTimeout(250);
  await expect(page.locator('[data-loading-navigation]')).toBeHidden();
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await page.evaluate(()=>document.addEventListener('click',event=>event.preventDefault(),{once:true}));
  await page.getByRole('link',{name:'Забули пароль?'}).click();
  await page.waitForTimeout(250);
  await expect(page.locator('[data-loading-navigation]')).toBeHidden();
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
});


test('production motion animates only while visible and responds to reduced motion',async({page})=>{
  await ready(page);
  await page.evaluate(async()=>{window.finish=(await import('/static/js/components/loading.js')).beginLoading({mode:'screen'});});
  const indicator=page.locator('[data-loading-indicator]');
  const figure=indicator.locator('[data-handstand-cycle]');
  await expect(indicator).toBeVisible();
  const first=await figure.innerHTML();
  await page.waitForTimeout(300);
  expect(await figure.innerHTML()).not.toBe(first);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.waitForTimeout(60);
  const still=await figure.innerHTML();
  await page.waitForTimeout(300);
  expect(await figure.innerHTML()).toBe(still);
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.waitForTimeout(200);
  expect(await figure.innerHTML()).not.toBe(still);
  await page.evaluate(()=>window.finish());
  await expect(indicator).toBeHidden();
  const hidden=await figure.innerHTML();
  await page.waitForTimeout(300);
  expect(await figure.innerHTML()).toBe(hidden);
});

test('Google sign-in shows a button spinner without covering the page',async({page})=>{
  // The isolated test server intentionally has no configured OAuth provider.
  // Reuse the real Jinja fixture with synthetic availability, as oauth-ui does.
  const html=execFileSync('uv',['run','--locked','python','tests/fixtures/render_oauth_login.py'],{encoding:'utf8'});
  await page.route('**/login?lang=uk',route=>route.fulfill({contentType:'text/html',body:html}));
  await ready(page);
  let release;
  const held=new Promise(resolve=>{release=resolve;});
  await page.route('**/api/auth/oauth/google/start',async route=>{
    await held;await route.fulfill({status:503,json:{}});
  });
  const google=page.locator('[data-oauth-provider="google"]');
  await google.click();
  await expect(google.locator('.button-spinner')).toBeVisible();
  await expect(google).toHaveAttribute('aria-busy','true');
  await page.waitForTimeout(550);
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await expect(page.locator('[data-loading-navigation]')).toBeHidden();
  release();
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await expect(google).toBeEnabled();
  await expect(google.locator('.button-spinner')).toHaveCount(0);
  await expect(google).not.toHaveAttribute('aria-busy','true');
  await expect(page.locator('#oauth-message')).not.toBeEmpty();
});


test('background API work is silent and does not keep a screen indicator alive',async({page})=>{
  await ready(page);
  let release;const held=new Promise(resolve=>release=resolve);
  await page.route('**/api/background',async route=>{await held;await route.fulfill({json:{ok:true}});});
  await page.evaluate(()=>{window.background=import('/static/js/api/client.js').then(({requestApi})=>requestApi('/api/background'));});
  await page.waitForTimeout(650);
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await expect(page.locator('[data-loading-navigation]')).toBeHidden();
  await page.evaluate(async()=>{window.finish=(await import('/static/js/components/loading.js')).beginLoading({mode:'screen'});});
  await expect(page.locator('[data-loading-indicator]')).toBeVisible();
  await page.evaluate(()=>window.finish());
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  release();await page.evaluate(()=>window.background);
});

test('whole-screen delay is 500ms and a finished task does not play out the cycle',async({page})=>{
  await ready(page);
  await page.clock.install();
  await page.evaluate(async()=>{window.finish=(await import('/static/js/components/loading.js')).beginLoading({mode:'screen'});});
  await page.clock.runFor(499);
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await page.clock.runFor(1);
  await expect(page.locator('[data-loading-indicator]')).toBeVisible();
  await page.evaluate(()=>window.finish());
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
});

test('recovery uses a local busy button and restores it after the response',async({page})=>{
  let release;const held=new Promise(resolve=>release=resolve);
  await page.route('**/api/session',route=>route.fulfill({json:{authenticated:false}}));
  await page.route('**/api/auth/recovery/request',async route=>{await held;await route.fulfill({status:503,json:{}});});
  await page.goto('/recovery?lang=uk');
  await page.getByLabel('Email',{exact:true}).fill('synthetic@example.test');
  const submit=page.getByRole('button',{name:'Надіслати код'});
  await submit.click();
  await expect(page.getByRole('button',{name:'Надсилаємо…'})).toBeDisabled();
  await expect(page.locator('[data-request-code] .button-spinner')).toBeVisible();
  await page.waitForTimeout(550);
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await expect(page.locator('[data-loading-navigation]')).toBeHidden();
  release();
  await expect(page.getByRole('button',{name:'Надіслати код'})).toBeEnabled();
  await expect(page.locator('[data-request-code] .button-spinner')).toHaveCount(0);
});


test('session refresh stays quiet while pending',async({page})=>{
  let release;const held=new Promise(resolve=>release=resolve);
  await page.route('**/api/session',async route=>{await held;await route.fulfill({json:{authenticated:false}});});
  await page.goto('/login');
  await page.waitForTimeout(650);
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await expect(page.locator('[data-loading-navigation]')).toBeHidden();
  release();
});

test('button feedback restores original nodes and ignores stale completion after history restore',async({page})=>{
  await ready(page);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.evaluate(async()=>{
    const button=document.createElement('button');button.id='loading-fixture';
    const icon=document.createElement('span');icon.textContent='Save';
    button.append(icon);document.body.append(button);window.originalIcon=icon;
    const {beginLoading}=await import('/static/js/components/loading.js');
    window.oldFinish=beginLoading({mode:'button',target:button,label:'Saving…'});
  });
  const button=page.locator('#loading-fixture');
  await expect(button).toHaveText('Saving…');
  expect(await button.evaluate(el=>el.getAnimations({subtree:true}).length)).toBe(0);
  await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));
  await expect(button).toHaveText('Save');
  expect(await button.evaluate(el=>el.firstChild===window.originalIcon)).toBe(true);
  await page.evaluate(async()=>{
    const {beginLoading}=await import('/static/js/components/loading.js');
    window.newFinish=beginLoading({mode:'button',target:document.querySelector('#loading-fixture'),label:'Saving again…'});
    window.oldFinish();
  });
  await expect(button).toHaveText('Saving again…');
  await expect(button).toHaveAttribute('aria-busy','true');
  await page.evaluate(()=>{window.newFinish();window.newFinish();});
  await expect(button).toHaveText('Save');
  await expect(button).not.toHaveAttribute('aria-busy','true');
  expect(await button.evaluate(el=>el.firstChild===window.originalIcon)).toBe(true);
});
