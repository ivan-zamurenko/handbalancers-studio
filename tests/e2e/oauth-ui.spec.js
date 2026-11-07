import {test, expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
const html = execFileSync('uv', ['run','--locked','python','tests/fixtures/render_oauth_login.py'], {encoding:'utf8'});
for (const width of [390,1440]) for (const theme of ['light','dark']) {
  test(`OAuth buttons and recoverable failure ${width} ${theme}`, async ({page}) => {
    await page.setViewportSize({width,height:1000});
    await page.route('**/login', route=>route.fulfill({contentType:'text/html',body:html}));
    let starts=0;
    await page.route('**/api/auth/oauth/google/start', async route=> {
      starts++;
      await new Promise(resolve=>setTimeout(resolve,200));
      await route.fulfill({status:503,contentType:'application/json',body:'{}'});
    });
    await page.goto('/login');
    await page.evaluate(preference => localStorage.setItem('studio:theme:guest', preference), theme);
    await page.reload();
    const google=page.getByRole('button',{name:'Продовжити з Google'});
    await expect(page.getByRole('button',{name:/Apple/})).toHaveCount(0);
    await expect(google).toBeEnabled();
    await google.click();
    await expect(google).toBeDisabled();
    await expect(page.getByRole('status')).toContainText('Не вдалося почати вхід');
    await expect(google).toBeEnabled();
    expect(starts).toBe(1);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });
}

test('guest does not see logout and signed-in visitor can log out', async ({page}) => {
  await page.goto('/login');
  await expect(page.locator('[data-logout]')).toBeHidden();
  await page.route('**/api/session', route=>route.fulfill({json:{authenticated:true,csrf_token:'synthetic-csrf',user:{role:'member'}}}));
  let csrf;
  await page.route('**/api/auth/logout',route=>{
    csrf=route.request().headers()['x-csrf-token'];
    return route.fulfill({status:204});
  });
  await page.reload();
  await expect(page.locator('[data-logout]')).toBeVisible();
  await expect(page.locator('[data-login-link]')).toBeHidden();
  await page.locator('[data-logout]').click();
  await expect(page).toHaveURL(/\/login$/);
  expect(csrf).toBe('synthetic-csrf');
});
