import {test, expect} from '@playwright/test';

for (const width of [390, 1440]) for (const theme of ['light', 'dark']) {
  test(`recovery request and confirm ${width} ${theme}`, async ({page}) => {
    await page.setViewportSize({width, height:900});
    await page.addInitScript(value => localStorage.setItem('studio:theme:guest', value), theme);
    const requests = [];
    await page.route('**/api/auth/recovery/*', async route => {
      requests.push({url:route.request().url(), body:route.request().postDataJSON()});
      const confirm = route.request().url().endsWith('/confirm');
      await route.fulfill({status:confirm ? 200 : 202, contentType:'application/json',
        body:JSON.stringify(confirm ? {state:'password_changed', login_required:true} : {state:'recovery_pending'})});
    });
    await page.goto('/login?lang=uk');
    await page.getByRole('link', {name:'Забули пароль?'}).click();
    await expect(page).toHaveURL(/\/recovery\?lang=uk$/);
    await page.getByLabel('Email', {exact:true}).fill('member@example.test');
    await page.getByRole('button', {name:'Надіслати код'}).click();
    await expect(page.locator('#recovery-status')).toContainText('Якщо для цієї пошти');
    await expect(page.getByLabel('Код із листа')).toBeFocused();
    await page.getByLabel('Код із листа').fill('123456');
    await page.getByLabel('Новий пароль', {exact:true}).fill('synthetic-new-password');
    await page.getByRole('button', {name:'Зберегти новий пароль'}).click();
    await expect(page.locator('#recovery-status')).toContainText('Пароль змінено');
    expect(requests).toHaveLength(2);
    expect(requests[1].body).toEqual({email:'member@example.test', token:'123456', password:'synthetic-new-password'});
    expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain('synthetic-new-password');
    await expect(page.locator('#recovery-password')).toHaveValue('');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
  });
}

test('recovery pending rejects duplicates; retry, English and history clear secrets', async ({page}) => {
  let release;
  const held = new Promise(resolve => { release = resolve; });
  let count = 0;
  await page.route('**/api/auth/recovery/request', async route => {
    ++count; await held;
    await route.fulfill({status:202, contentType:'application/json', body:'{"state":"recovery_pending"}'});
  });
  await page.route('**/api/auth/recovery/confirm', route => route.fulfill({status:422, contentType:'application/json',body:'{}'}));
  await page.goto('/recovery?lang=en');
  await page.getByLabel('Email', {exact:true}).fill('member@example.test');
  await page.getByRole('button', {name:'Send a code'}).click();
  await expect(page.locator('#recovery-form')).toHaveAttribute('aria-busy','true');
  await page.locator('#recovery-form').evaluate(form => form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));
  expect(count).toBe(1); release();
  await page.getByLabel('Email code').fill('123456');
  await page.getByLabel('New password',{exact:true}).fill('synthetic-password');
  await page.getByRole('button', {name:'Save new password'}).click();
  await expect(page.locator('#recovery-status')).toContainText('Check the code');
  await expect(page.getByRole('button', {name:'Save new password'})).toBeEnabled();
  await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pagehide')));
  await expect(page.locator('#recovery-password')).toHaveValue('');
  await expect(page.locator('#recovery-code')).toHaveValue('');
  await expect(page.getByLabel('Email',{exact:true})).toHaveValue('');
});

test('recovery never submits credentials without JavaScript', async ({browser}) => {
  const context = await browser.newContext({javaScriptEnabled:false});
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:8765/recovery');
  await expect(page.getByRole('button',{name:'Надіслати код'})).toBeDisabled();
  await page.getByLabel('Email',{exact:true}).fill('member@example.test');
  await page.getByLabel('Email',{exact:true}).press('Enter');
  await expect(page).toHaveURL('http://127.0.0.1:8765/recovery');
  await context.close();
});
