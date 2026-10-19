import { test, expect } from '@playwright/test';
for (const width of [390,1440]) for (const theme of ['light','dark']) {
  test(`login form ${width} ${theme}`, async ({page}) => {
    await page.setViewportSize({width,height:900});
    await page.goto('/?lang=uk');
    await page.getByLabel('Тема').selectOption(theme);
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

for (const width of [390, 1440]) test(`login actions align ${width}`, async ({page}) => {
  await page.setViewportSize({width, height: 900});
  await page.goto('/login');
  const show = await page.getByRole('button', {name: 'Показати пароль', exact: true}).boundingBox();
  const recovery = await page.getByRole('button', {name: 'Забули пароль?', exact: true}).boundingBox();
  expect(Math.abs((show.y + show.height / 2) - (recovery.y + recovery.height / 2))).toBeLessThan(2);
  const alignment = await page.locator('.login-submit').evaluate(button => {
    const text = [...button.childNodes].find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
    const range = document.createRange(); range.selectNodeContents(text);
    const label = range.getBoundingClientRect(), box = button.getBoundingClientRect();
    return Math.abs(label.x + label.width / 2 - box.x - box.width / 2);
  });
  expect(alignment).toBeLessThan(2);
});
