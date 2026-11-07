import {test, expect} from '@playwright/test';

for (const width of [390,1440]) for (const theme of ['light','dark']) {
  test(`logout clears account drafts and cache ${width} ${theme}`, async ({page}) => {
    await page.setViewportSize({width,height:1000});
    let authenticated = true;
    await page.route('**/api/session',route => route.fulfill({json: authenticated
      ? {authenticated:true,csrf_token:'synthetic-csrf',user:{id:'member-a',role:'member'}}
      : {authenticated:false}}));
    await page.route('**/api/auth/logout', async route => {
      expect(route.request().headers()['x-csrf-token']).toBe('synthetic-csrf');
      authenticated = false;
      await route.fulfill({status:204});
    });
    await page.goto('/login');
    await page.evaluate(preference => {
      localStorage.setItem('studio:theme:guest', preference);
      for (const storage of [localStorage,sessionStorage]) {
        storage.setItem('studio:account:member-a:draft', 'private-draft');
        storage.setItem('studio:account:member-a:cache', 'private-cache');
        storage.setItem('studio:account:member-b:draft', 'other-account');
      }
    },theme);
    await page.reload();
    await expect(page.locator('[data-logout]')).toBeVisible();
    await page.locator('[data-logout]').click();
    await expect(page.locator('[data-login-link]')).toBeVisible();
    await expect(page.locator('[data-logout]')).toBeHidden();
    expect(await page.evaluate(() => [localStorage,sessionStorage].map(storage => [
      storage.getItem('studio:account:member-a:draft'),
      storage.getItem('studio:account:member-a:cache'),
      storage.getItem('studio:account:member-b:draft'),
    ]))).toEqual([[null,null,'other-account'],[null,null,'other-account']]);
    expect(await page.evaluate(() => localStorage.getItem('studio:theme:guest'))).toBe(theme);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });
}

test('lost logout response clears cache after session confirms guest', async ({page}) => {
  let authenticated = true;
  await page.route('**/api/session',route => route.fulfill({json: authenticated
    ? {authenticated:true,csrf_token:'synthetic-csrf',user:{id:'member-a'}}
    : {authenticated:false}}));
  await page.route('**/api/auth/logout',route => { authenticated=false; return route.abort(); });
  await page.goto('/login');
  await expect(page.locator('[data-logout]')).toBeVisible();
  await page.evaluate(() => localStorage.setItem('studio:account:member-a:draft','private'));
  await page.locator('[data-logout]').click();
  await expect(page.locator('[data-login-link]')).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('studio:account:member-a:draft'))).toBeNull();
});

test('failed logout does not pretend success or discard drafts', async ({page}) => {
  await page.route('**/api/session',route => route.fulfill({json:
    {authenticated:true,csrf_token:'synthetic-csrf',user:{id:'member-a'}}}));
  await page.route('**/api/auth/logout',route => route.fulfill({status:503}));
  await page.goto('/login');
  await expect(page.locator('[data-logout]')).toBeVisible();
  await page.evaluate(() => localStorage.setItem('studio:account:member-a:draft','private'));
  await page.locator('[data-logout]').click();
  await expect(page.locator('[data-logout]')).toBeEnabled();
  await expect(page.locator('[data-login-link]')).toBeHidden();
  expect(await page.evaluate(() => localStorage.getItem('studio:account:member-a:draft'))).toBe('private');
});

test('pending session snapshot cannot enable logout twice', async ({page}) => {
  let releaseSnapshot, releaseLogout;
  let snapshots = 0;
  await page.route('**/api/session', async route => {
    snapshots++;
    if (snapshots === 2) await new Promise(resolve => { releaseSnapshot=resolve; });
    await route.fulfill({json:{authenticated:true,csrf_token:'synthetic-csrf',user:{id:'member-a'}}});
  });
  await page.route('**/api/auth/logout', async route => {
    await new Promise(resolve => { releaseLogout=resolve; });
    await route.fulfill({status:503});
  });
  await page.goto('/login');
  await expect(page.locator('[data-logout]')).toBeVisible();
  await page.evaluate(() => window.dispatchEvent(new Event('pageshow')));
  await expect.poll(() => !!releaseSnapshot).toBe(true);
  await page.locator('[data-logout]').click();
  await expect.poll(() => !!releaseLogout).toBe(true);
  const snapshotResponse=page.waitForResponse('**/api/session');
  releaseSnapshot();
  await snapshotResponse;
  await expect(page.locator('[data-logout]')).toBeDisabled();
  releaseLogout();
  await expect(page.locator('[data-logout]')).toBeEnabled();
});

test('blocked browser storage does not prevent logout', async ({page}) => {
  let authenticated = true;
  await page.route('**/api/session',route => route.fulfill({json: authenticated
    ? {authenticated:true,csrf_token:'synthetic-csrf',user:{id:'member-a'}}
    : {authenticated:false}}));
  await page.route('**/api/auth/logout',route => {authenticated=false; return route.fulfill({status:204});});
  await page.goto('/login');
  await expect(page.locator('[data-logout]')).toBeVisible();
  await page.evaluate(() => {
    Object.defineProperty(window,'localStorage',{get() { throw new DOMException('Blocked','SecurityError'); }});
  });
  await page.locator('[data-logout]').click();
  await expect(page.locator('[data-login-link]')).toBeVisible();
});
