import {test, expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';

const html = new Map();
async function configured(page, language='uk') {
  // Only the destination is synthetic here; real server gate has DB tests.
  await page.route('**/dashboard?*',r=>r.fulfill({contentType:'text/html',body:'<h1>Today</h1>'}));
  for (const path of ['/register','/verify-email','/login']) {
    const url=`${path}?lang=${language}`;
    if (!html.has(url)) html.set(url,execFileSync('.venv/bin/python',['tests/fixtures/render_auth_page.py',url],{encoding:'utf8'}));
    await page.route(`**${url}`,route=>route.fulfill({contentType:'text/html',body:html.get(url)}));
  }
  await page.route('**/api/session',route=>route.fulfill({json:{authenticated:false}}));
}
async function registerFields(page) {
  await page.getByLabel('Ім’я',{exact:true}).fill('Іван');
  await page.getByLabel('Прізвище',{exact:true}).fill('Коваль');
  await page.getByLabel('Email',{exact:true}).fill('member@example.test');
  await page.getByLabel('Пароль',{exact:true}).fill('synthetic-password-123');
}

test('full_signup_keyboard',async({page})=>{
  await configured(page);
  const calls=[];
  await page.route('**/api/auth/register',route=>{calls.push(route.request().postDataJSON());return route.fulfill({status:202,json:{state:'verification_pending'}});});
  await page.route('**/api/auth/verify-email',route=>{calls.push(route.request().postDataJSON());return route.fulfill({json:{state:'authenticated',profile_complete:true}});});
  await page.goto('/register?lang=uk');
  await expect(page.locator('#availability-dialog')).not.toContainText('Реєстрація й оплата ще не відкриті');
  await page.getByLabel('Ім’я',{exact:true}).focus();
  await page.keyboard.type('Ivan');await page.keyboard.press('Tab');
  await page.keyboard.type('Koval');await page.keyboard.press('Tab');
  await page.keyboard.type('member@example.test');await page.keyboard.press('Tab');
  await page.keyboard.type('synthetic-password-123');await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/verify-email\?lang=uk$/);
  await expect(page.getByLabel('Email',{exact:true})).toHaveValue('member@example.test');
  await page.getByLabel('Код із листа',{exact:true}).focus();
  await page.keyboard.type('012345');await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/dashboard\?lang=uk$/);
  expect(calls).toEqual([{first_name:'Ivan',last_name:'Koval',email:'member@example.test',password:'synthetic-password-123'},{email:'member@example.test',token:'012345'}]);
  expect(await page.evaluate(()=>sessionStorage.getItem('studio:auth-draft'))).toBeNull();
});

test('no_double_submit and Google share one pending gate',async({page})=>{
  await configured(page);await page.goto('/login?lang=uk');
  let release;const held=new Promise(r=>release=r);let count=0,google=0;
  await page.route('**/api/auth/login',async route=>{count++;await held;await route.fulfill({status:401,json:{}});});
  await page.route('**/api/auth/oauth/google/start',route=>{google++;return route.fulfill({status:503,json:{}});});
  await page.getByLabel('Email',{exact:true}).fill('member@example.test');
  await page.getByLabel('Пароль',{exact:true}).fill(' x ');
  await page.locator('#login-form').evaluate(form=>{form.requestSubmit();form.requestSubmit();});
  await expect(page.locator('[data-oauth-provider]')).toBeDisabled();
  await page.locator('[data-oauth-provider]').evaluate(button=>button.click());
  await expect.poll(()=>count).toBe(1);expect(google).toBe(0);
  release();await expect(page.locator('[data-auth-status]')).toBeFocused();
  await expect(page.getByLabel('Пароль',{exact:true})).toHaveValue(' x ');
});

test('reload_no_password and theme_preserves_form',async({page})=>{
  await configured(page);await page.goto('/register?lang=uk');await registerFields(page);
  await page.getByRole('button',{name:'Тема',exact:true}).click();
  await expect(page.getByLabel('Ім’я',{exact:true})).toHaveValue('Іван');
  await expect(page.getByLabel('Email',{exact:true})).toHaveValue('member@example.test');
  expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain('synthetic-password-123');
  await page.reload();
  await expect(page.getByLabel('Пароль',{exact:true})).toHaveValue('');
  await expect(page.getByLabel('Прізвище',{exact:true})).toHaveValue('Коваль');
});

test('error_focus without scrolling or rendering upstream text',async({page})=>{
  await page.setViewportSize({width:390,height:600});
  await configured(page);await page.goto('/register?lang=uk');await registerFields(page);
  let release;const held=new Promise(r=>release=r);
  await page.route('**/api/auth/register',async route=>{await held;await route.fulfill({status:503,json:{error:{message_key:'<script>unsafe</script>'}}});});
  await page.getByRole('button',{name:'Створити акаунт',exact:true}).click();
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  const scrollBefore=await page.evaluate(()=>window.scrollY);
  release();
  await expect(page.locator('[data-auth-status]')).toBeFocused();
  expect(await page.evaluate(()=>window.scrollY)).toBe(scrollBefore);
  await expect(page.locator('[data-auth-status]')).toHaveAttribute('aria-live','polite');
  await expect(page.locator('[data-auth-status]')).toContainText('Спробуйте');
  await expect(page.locator('[data-auth-status]')).not.toContainText('<script>');
});

test('verify resend cooldown and editing email clears old code',async({page})=>{
  await configured(page);await page.goto('/verify-email?lang=uk');await page.clock.install();
  await page.getByLabel('Email',{exact:true}).fill('member@example.test');
  await page.getByLabel('Код із листа',{exact:true}).fill('012345');
  let calls=0;
  await page.route('**/api/auth/resend-verification',route=>{calls++;return route.fulfill({status:202,json:{state:'verification_pending'}});});
  await page.locator('[data-auth-resend]').click();
  await expect(page.locator('[data-auth-resend]')).toBeDisabled();
  await page.locator('[data-auth-resend]').evaluate(button=>button.click());expect(calls).toBe(1);
  await page.clock.runFor(61000);
  await expect(page.locator('[data-auth-resend]')).toBeEnabled();
  await page.getByLabel('Email',{exact:true}).fill('other@example.test');
  await expect(page.getByLabel('Код із листа',{exact:true})).toHaveValue('');
});

test('history restore discards stale success and keeps a new submission pending',async({page})=>{
  await configured(page);await page.goto('/login?lang=uk');
  await page.evaluate(()=>{
    const original=window.fetch;window.replies=[];
    window.fetch=(input,options)=>String(input).includes('/api/auth/login') ? new Promise(resolve=>window.replies.push(resolve)) : original(input,options);
  });
  await page.getByLabel('Email',{exact:true}).fill('member@example.test');
  await page.getByLabel('Пароль',{exact:true}).fill('first-password');
  await page.locator('#login-form').evaluate(form=>form.requestSubmit());
  await expect.poll(()=>page.evaluate(()=>window.replies.length)).toBe(1);
  await page.evaluate(()=>{window.dispatchEvent(new PageTransitionEvent('pagehide'));window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}));});
  await expect(page.getByLabel('Пароль',{exact:true})).toHaveValue('');
  await page.getByLabel('Пароль',{exact:true}).fill('second-password');
  await page.locator('#login-form').evaluate(form=>form.requestSubmit());
  await expect.poll(()=>page.evaluate(()=>window.replies.length)).toBe(2);
  await page.evaluate(()=>window.replies[0](new Response(JSON.stringify({state:'authenticated'}),{headers:{'Content-Type':'application/json'}})));
  await expect(page).toHaveURL(/\/login\?lang=uk$/);
  await expect(page.locator('[data-auth-submit]')).toBeDisabled();
  await page.evaluate(()=>window.replies[1](new Response('{}',{status:401,headers:{'Content-Type':'application/json'}})));
  await expect(page.locator('[data-auth-submit]')).toBeEnabled();
  await expect(page.locator('[data-auth-status]')).toBeFocused();
});

test('429 cooldown prevents retries; rejected OTP never becomes a session',async({page})=>{
  await configured(page);await page.goto('/verify-email?lang=uk');await page.clock.install();
  await page.getByLabel('Email',{exact:true}).fill('member@example.test');
  await page.getByLabel('Код із листа',{exact:true}).fill('000001');
  let requests=0;
  await page.route('**/api/auth/verify-email',route=>{requests++;return route.fulfill({status:requests===1?429:422,json:{}});});
  await page.locator('[data-auth-submit]').click();
  await expect(page.locator('[data-auth-status]')).toContainText('Забагато спроб');
  await page.locator('#verify-form').evaluate(form=>form.requestSubmit());expect(requests).toBe(1);
  await page.clock.runFor(61000);
  await page.locator('[data-auth-submit]').click();
  await expect(page.locator('[data-auth-status]')).toContainText('прострочений');
  await expect(page).toHaveURL(/\/verify-email\?lang=uk$/);
  expect(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))).not.toContain('000001');
  await page.reload();await expect(page.getByLabel('Код із листа',{exact:true})).toHaveValue('');
});

test('forms still work with storage denied and English copy',async({page})=>{
  await configured(page,'en');
  await page.addInitScript(()=>{Storage.prototype.setItem=()=>{throw new Error('Storage unavailable');};Storage.prototype.getItem=()=>{throw new Error('Storage unavailable');};});
  await page.route('**/api/auth/login',route=>route.fulfill({json:{state:'authenticated',profile_complete:false}}));
  await page.goto('/login?lang=en');
  await page.getByLabel('Email',{exact:true}).fill('member@example.test');
  await page.getByLabel('Password',{exact:true}).fill('synthetic');
  await page.getByRole('button',{name:'Log in',exact:true}).click();
  await expect(page).toHaveURL(/\/dashboard\?lang=en$/);
});

for(const width of [390,1440]) for(const theme of ['dark','light']) test(`auth layout ${width} ${theme}`,async({page})=>{
  await configured(page);await page.setViewportSize({width,height:1000});
  await page.addInitScript(theme=>localStorage.setItem('studio:theme:guest',theme),theme);
  for(const path of ['/register','/verify-email','/login']) {
    await page.goto(`${path}?lang=uk`);
    await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
    await expect(page.getByRole('heading',{level:1})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await expect(page.locator('[data-auth-submit]')).toBeEnabled();
    await expect(page.getByRole('button',{name:/Apple/})).toHaveCount(0);
    await page.screenshot({path:test.info().outputPath(`${path.slice(1)}.png`)});
  }
});


test('language switch keeps login values and uses the selected language after login',async({page})=>{
  await configured(page);
  await page.goto('/login?lang=uk');
  await page.getByLabel('Email',{exact:true}).fill('member@example.test');
  await page.getByLabel('Пароль',{exact:true}).fill('synthetic-password-123');
  let sent;
  await page.route('**/api/auth/login',r=>{sent=r.request().postDataJSON();return r.fulfill({json:{state:'authenticated'}});});
  await page.locator('.locale-nav a[lang=en]').click();
  await expect(page.getByLabel('Password',{exact:true})).toHaveValue('synthetic-password-123');
  await page.getByRole('button',{name:'Log in',exact:true}).click();
  await expect(page).toHaveURL(/\/dashboard\?lang=en$/);
  expect(sent).toEqual({email:'member@example.test',password:'synthetic-password-123'});
});
