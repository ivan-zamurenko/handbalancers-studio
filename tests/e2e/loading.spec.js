import {test, expect} from '@playwright/test';

async function ready(page, language = 'uk') {
  await page.route('**/api/session', route => route.fulfill({json:{authenticated:false}}));
  await page.goto(`/login?lang=${language}`);
  await expect(page.locator('[data-loading-indicator]')).toBeAttached();
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
}

for (const width of [390, 1440]) for (const theme of ['light', 'dark']) {
  test(`handstand loading is compact and accessible ${width} ${theme}`, async ({page}) => {
    await page.setViewportSize({width, height:800});
    await page.addInitScript(value => localStorage.setItem('studio:theme:guest', value), theme);
    await ready(page);
    let release;
    const held = new Promise(resolve => {release = resolve;});
    await page.route('**/api/loading-example', async route => {await held; await route.fulfill({json:{ok:true}});});
    await page.evaluate(() => {window.work = import('/static/js/api/client.js').then(({requestApi})=>requestApi('/api/loading-example'));});
    const indicator = page.locator('[data-loading-indicator]');
    await expect(indicator).toBeVisible();
    await expect(indicator).toHaveAttribute('role','status');
    await expect(indicator).toContainText('Завантажуємо');
    await expect(indicator.locator('svg')).toHaveAttribute('aria-hidden','true');
    expect(await indicator.evaluate(el=>getComputedStyle(el).pointerEvents)).toBe('none');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const box = await indicator.boundingBox();
    expect(box.width).toBeLessThan(260); expect(box.height).toBeLessThan(110);
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
    window.first = requestApi('/api/held/success');
    window.second = requestApi('/api/held/failure').catch(()=>null);
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
    await requestApi('/api/fast');
  });
  await page.waitForTimeout(250);
  expect(await page.evaluate(()=>window.shown)).toBe(false);
  await page.route('**/api/hang', route=>route.abort('timedout'));
  await page.evaluate(async () => {
    const {requestApi} = await import('/static/js/api/client.js');
    const controller = new AbortController(); controller.abort();
    await requestApi('/api/hang',{signal:controller.signal}).catch(()=>{});
    const {beginLoading} = await import('/static/js/components/loading.js');
    window.finish = beginLoading();
  });
  await expect(page.locator('[data-loading-indicator]')).toBeVisible();
  await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await page.evaluate(()=>{window.finish(); window.finish();});
});

test('reduced motion uses a still handstand; real page navigation shows loading', async ({page}) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  await ready(page);
  let release;
  const held = new Promise(resolve=>{release=resolve;});
  await page.route('**/recovery?lang=uk', async route=>{await held; await route.continue();});
  // Observe before navigation: Playwright DOM queries wait for its commit.
  let snapshot;
  await page.exposeFunction('reportLoading',value=>{snapshot=value;});
  await page.evaluate(()=>{
    const element=document.querySelector('[data-loading-indicator]');
    new MutationObserver(()=>window.reportLoading({visible:!element.hidden,
      animations:element.getAnimations({subtree:true}).length})).observe(element,{attributes:true});
  });
  await page.getByRole('link',{name:'Забули пароль?'}).click({noWaitAfter:true});
  const indicator = page.locator('[data-loading-indicator]');
  await expect.poll(()=>snapshot?.visible).toBe(true);
  expect(snapshot.animations).toBe(0);
  release();
  await expect(page).toHaveURL(/\/recovery\?lang=uk$/);
  await expect(indicator).toBeHidden();
});

test('initial page assets show loading until the load event', async ({page}) => {
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
  await expect(page.locator('[data-loading-indicator]')).toBeVisible();
  release();
  await page.waitForLoadState('load');
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
});

test('body parsing and HTTP errors finish correctly', async ({page}) => {
  await ready(page);
  await page.evaluate(async () => {
    const {requestApi} = await import('/static/js/api/client.js');
    window.bodyWork = requestApi('/test', {fetchImpl:async()=>({
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
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
  await page.evaluate(()=>document.addEventListener('click',event=>event.preventDefault(),{once:true}));
  await page.getByRole('link',{name:'Забули пароль?'}).click();
  await page.waitForTimeout(250);
  await expect(page.locator('[data-loading-indicator]')).toBeHidden();
});
