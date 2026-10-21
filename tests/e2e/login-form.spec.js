import { test, expect } from '@playwright/test';
for (const width of [390,1440]) for (const theme of ['light','dark']) {
  test(`login form ${width} ${theme}`, async ({page}) => {
    await page.setViewportSize({width,height:900});
    await page.goto('/?lang=uk');
    await page.evaluate(preference => localStorage.setItem('studio:theme:guest', preference), theme);
    await page.reload();
    await page.getByRole('link',{name:'Логін',exact:true}).click();
    await expect(page).toHaveURL(/\/login\?lang=uk$/);
    await expect(page.getByRole('heading',{level:1})).toHaveText('Раді бачити вас знову.');
    await expect(page.getByLabel('Email', {exact:true})).toHaveAttribute('autocomplete','username');
    const password=page.getByLabel('Пароль',{exact:true});
    await page.getByLabel('Email', {exact:true}).fill('preview@example.test');
    await password.fill('synthetic-password-only');
    await expect(password).toHaveAttribute('type','password');
    await page.getByRole('button',{name:'Показати пароль',exact:true}).click();
    await expect(password).toHaveAttribute('type','text');
    await page.getByRole('button',{name:'Приховати пароль',exact:true}).click();
    await expect(password).toHaveAttribute('type','password');
    await expect(page.getByRole('button',{name:'Увійти',exact:true})).toBeDisabled();
    await expect(page.locator('#login-status')).toContainText('Вхід через email ще не підключено');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    const requests=[];page.on('request', r=>requests.push(r.url()+' '+(r.postData()||'')));
    await password.press('Enter');
    await expect(page).toHaveURL(/\/login\?lang=uk$/);
    expect(requests.some(r=>r.includes('synthetic-password-only'))).toBe(false);
    expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain('synthetic-password-only');
    await page.getByRole('link',{name:'EN',exact:true}).click();
    await expect(page.getByRole('heading',{level:1})).toHaveText('Good to see you again.');
    await expect(page.getByLabel('Password',{exact:true})).toHaveValue('');
    await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
  });
}
test('login safe without JavaScript and unavailable recovery is explicit',async({browser,page})=>{
  await page.goto('/login');
  await page.getByRole('button',{name:'Забули пароль?',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'Відновлення доступу'})).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'Забули пароль?',exact:true})).toBeFocused();
  const context=await browser.newContext({javaScriptEnabled:false});
  const bare=await context.newPage();
  await bare.goto('http://127.0.0.1:8765/login');
  await expect(bare.getByRole('button',{name:'Увійти',exact:true})).toBeDisabled();
  await bare.getByLabel('Email',{exact:true}).fill('preview@example.test');
  await bare.getByLabel('Пароль',{exact:true}).fill('synthetic');
  await bare.getByLabel('Пароль',{exact:true}).press('Enter');
  await expect(bare).toHaveURL('http://127.0.0.1:8765/login');
  await context.close();
});

test('leaving the preview clears password and resets visibility state',async({page})=>{
  await page.goto('/login');
  await page.getByLabel('Пароль',{exact:true}).fill('synthetic-only');
  await page.getByRole('button',{name:'Показати пароль',exact:true}).click();
  await page.evaluate(()=>window.dispatchEvent(new PageTransitionEvent('pagehide')));
  await expect(page.getByLabel('Пароль',{exact:true})).toHaveValue('');
  await expect(page.getByLabel('Пароль',{exact:true})).toHaveAttribute('type','password');
  await expect(page.getByRole('button',{name:'Показати пароль',exact:true})).toHaveAttribute('aria-pressed','false');
});

for (const width of [390, 1440]) for (const theme of ['light', 'dark']) test(`inline animated password eye ${width} ${theme}`, async ({page}) => {
  await page.setViewportSize({width, height: 900});
  await page.goto('/login');
  await page.evaluate(preference => localStorage.setItem('studio:theme:guest', preference), theme);
  await page.reload();
  const toggle = page.locator('[data-password-toggle]');
  await expect(toggle).toHaveAccessibleName('Показати пароль');
  const input = page.getByLabel('Пароль', {exact: true});
  const box = await input.boundingBox(), eye = await toggle.boundingBox();
  expect(eye.x).toBeGreaterThan(box.x + box.width / 2);
  expect(eye.x + eye.width).toBeLessThanOrEqual(box.x + box.width);
  expect(eye.y).toBeGreaterThanOrEqual(box.y);
  expect(eye.y + eye.height).toBeLessThanOrEqual(box.y + box.height);
  expect(eye.width).toBeGreaterThanOrEqual(44);
  await expect(toggle.locator('svg')).toHaveCount(1);
  await input.fill('synthetic-password');
  const animations = await toggle.evaluate(button => {
    getComputedStyle(button.querySelector('.eye-open')).transform;
    button.click();
    return button.getAnimations({subtree:true}).length;
  });
  expect(animations).toBeGreaterThan(0);
  await expect(input).toHaveAttribute('type','text');
  await expect(toggle).toHaveAttribute('aria-pressed','true');
  await expect(toggle).toHaveAccessibleName('Приховати пароль');
  await toggle.focus();
  await page.keyboard.press('Space');
  await expect(input).toHaveAttribute('type','password');
  await expect(toggle).toHaveAttribute('aria-pressed','false');
  await expect(input).toHaveValue('synthetic-password');
  const alignment = await page.locator('.login-submit').evaluate(button => {
    const text = [...button.childNodes].find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
    const range = document.createRange(); range.selectNodeContents(text);
    const label = range.getBoundingClientRect(), box = button.getBoundingClientRect();
    return Math.abs(label.x + label.width / 2 - box.x - box.width / 2);
  });
  expect(alignment).toBeLessThan(2);
});

test('password eye respects reduced motion and English labels', async ({page}) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/login?lang=en');
  const toggle=page.locator('[data-password-toggle]');
  await expect(toggle).toHaveAccessibleName('Show password');
  await toggle.click();
  await expect(page.getByRole('button',{name:'Hide password',exact:true})).toHaveAttribute('aria-pressed','true');
  expect(await toggle.evaluate(button => button.getAnimations({subtree:true}).length)).toBe(0);
  await expect(page.getByLabel('Password',{exact:true})).toHaveAttribute('type','text');
});
