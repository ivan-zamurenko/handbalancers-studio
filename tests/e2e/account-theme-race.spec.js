import {test, expect} from '@playwright/test';

async function delayedPreferences(page) {
  const patches = [];
  let pending, authenticated = true;
  await page.addInitScript(() => {
    localStorage.setItem('studio:theme:guest', 'light');
    window.accountAnnouncements = [];
    document.addEventListener('studio:account', e => window.accountAnnouncements.push(e.detail));
  });
  await page.route('**/api/session', r => r.fulfill({json: authenticated
    ? {authenticated:true,setup_required:false,csrf_token:'synthetic-csrf',user:{id:'member-a'}}
    : {authenticated:false}}));
  await page.route('**/api/me/preferences', async r => {
    if (r.request().method() === 'GET') { pending = r; return; }
    patches.push(r.request().postDataJSON());
    await r.fulfill({json:{theme_preference:patches.at(-1).theme_preference,revision:8}});
  });
  await page.goto('/login');
  await expect.poll(() => Boolean(pending)).toBe(true);
  return {
    patches,
    release: (status=200, theme='light') => pending.fulfill({status,json:status===200
      ? {theme_preference:theme,revision:7} : {error:{code:'unavailable'}}}),
    signOut: async () => {
      authenticated = false;
      await page.evaluate(() => window.dispatchEvent(new Event('studio:session-changed')));
      await expect(page.locator('[data-logout]')).toBeHidden();
    },
  };
}

for (const clicks of [1,3]) test(`latest of ${clicks} early theme choices survives preferences load`, async ({page}) => {
  const state = await delayedPreferences(page);
  for (let i=0;i<clicks;i++) await page.locator('[data-theme-control]').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await state.release();
  await expect.poll(() => state.patches).toEqual([{theme_preference:'dark',expected_revision:7}]);
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  expect(await page.evaluate(() => localStorage.getItem('studio:account:member-a:theme'))).toBe('dark');
});

test('without an early choice use server preference without PATCH', async ({page}) => {
  const state = await delayedPreferences(page);
  await state.release(200, 'dark');
  await expect.poll(() => page.evaluate(() => window.accountAnnouncements.length)).toBe(1);
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  expect(state.patches).toEqual([]);
});

test('late preferences after sign-out cannot reattach account or save queued choice', async ({page}) => {
  const state = await delayedPreferences(page);
  await page.locator('[data-theme-control]').click();
  await state.signOut();
  await state.release();
  // Drain fetch/JSON tasks before inspecting the absence of account-side effects.
  await page.evaluate(() => new Promise(r => setTimeout(r,100)));
  expect(state.patches).toEqual([]);
  expect(await page.evaluate(() => window.accountAnnouncements)).toEqual([{id:null}]);
  expect(await page.evaluate(() => localStorage.getItem('studio:account:member-a:theme'))).toBeNull();
});

test('unavailable preferences retain local choice without guessing a revision', async ({page}) => {
  const state = await delayedPreferences(page);
  await page.locator('[data-theme-control]').click();
  await state.release(503);
  await expect.poll(() => page.evaluate(() => window.accountAnnouncements.length)).toBe(1);
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  expect(state.patches).toEqual([]);
});
