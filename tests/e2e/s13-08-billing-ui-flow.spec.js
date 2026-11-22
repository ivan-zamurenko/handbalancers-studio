import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdir} from 'node:fs/promises';
const id='00000000-0000-4000-8000-000000000001';
const checkout=`/billing/checkout/${id}`;
const future=days=>new Date(Date.now()+days*86400000).toISOString();
const baseSummary=()=>({subscription:null,active_attempt:null,trial_available:true,portal_available:false});
const attempt=(state='pending')=>({id,plan_code:'plus',state,trial_enabled:true,expires_at:future(1),checkout_url:state==='open'?'https://checkout.stripe.com/c/pay/cs_test_synthetic':null});
const cache=new Map();
async function setup(page,path='/subscription',summary=baseSummary(),getAttempt=()=>attempt(),lang='uk'){
 const key=path+lang;
 if(!cache.has(key))cache.set(key,execFileSync('.venv/bin/python',['tests/fixtures/render_member_page.py',path,lang,'billing'],{encoding:'utf8'}));
 await page.route(`**${path}?*`,r=>r.fulfill({contentType:'text/html',body:cache.get(key)}));
 await page.route('**/api/session',r=>r.fulfill({json:{authenticated:true,csrf_token:'a'.repeat(64),setup_required:false,user:{id:'billing-member'}}}));
 await page.route('**/api/me/preferences',r=>r.fulfill({json:{theme_preference:'auto',revision:0}}));
 await page.route('**/api/me/subscription',r=>r.fulfill({json:summary}));
 await page.route(`**/api/me/checkout-attempts/${id}`,r=>r.fulfill({json:getAttempt()}));
 await page.goto(`${path}?lang=${lang}${path===checkout?'&cancelled=1':''}`);
}

test('pending_until_webhook and reload never create a second Checkout',async({page})=>{
 let posts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/checkout'))posts++;});
 await setup(page,checkout);
 await expect(page.locator('[data-payment-state]')).toHaveAttribute('data-state','pending');
 await expect(page.locator('[data-payment-message]')).toContainText('Очікуємо підтвердження');
 await page.reload();
 await expect(page.locator('[data-payment-state]')).toHaveAttribute('data-state','pending');
 expect(posts).toBe(0);
});

test('cancel_recoverable restores original plan and hosted session',async({page})=>{
 await setup(page,checkout,baseSummary(),()=>attempt('open'));
 await expect(page.locator('[data-payment-plan]')).toHaveText('Plus');
 await expect(page.locator('[data-resume-checkout]')).toHaveAttribute('href',attempt('open').checkout_url);
 await expect(page.locator('[data-payment-state]')).not.toHaveAttribute('data-state','active');
});

for(const [status,days,semantic] of [['active',10,'active'],['trialing',3,'expiring'],['active',-1,'inactive'],['past_due',10,'inactive']])test(`status uses server projection ${status} ${days}`,async({page})=>{
 const summary={...baseSummary(),portal_available:true,subscription:{plan_code:'pro',status,current_period_end:future(days)}};
 await page.addInitScript(()=>localStorage.setItem('studio:subscription','active'));
 await setup(page,'/subscription',summary);
 await expect(page.locator('[data-subscription-state]')).toHaveAttribute('data-state',semantic);
 await expect(page.locator('[data-subscription-plan]')).toHaveText('Pro');
});

test('Checkout timeout keeps idempotency key, selected plan and consent for retry',async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('studio:public:plan','pro'));
 const sent=[];
 await page.route('**/api/checkout',async r=>{sent.push({key:r.request().headers()['idempotency-key'],body:r.request().postDataJSON(),csrf:r.request().headers()['x-csrf-token']});await r.fulfill({status:503,json:{error:{code:'service_unavailable'}}});});
 await setup(page);
 await expect(page.locator('[name=plan_code][value=pro]')).toBeChecked();
 await page.locator('[data-billing-consent]').check();
 await page.locator('[data-buy-package]').click();
 await expect(page.locator('[data-billing-error]')).toBeVisible();
 await page.locator('.locale-nav a[lang=en]').click();
 await expect(page.locator('[data-billing-error]')).toContainText('We could not check your payment');
 await expect(page.locator('[name=plan_code][value=pro]')).toBeChecked();
 await page.locator('[data-buy-package]').click();
 await expect.poll(()=>sent.length).toBe(2);
 expect(sent[0]).toEqual(sent[1]);
 expect(sent[0].body).toEqual({plan_code:'pro',terms_version:'test-v1'});
 expect(sent[0].csrf).toBe('a'.repeat(64));
 await expect(page.locator('[data-billing-consent]')).toBeChecked();
});

test('purchase and Portal navigate only to Stripe hosted URLs',async({page})=>{
 await page.route('https://checkout.stripe.com/**',r=>r.fulfill({body:'<h1>Synthetic hosted Checkout</h1>',contentType:'text/html'}));
 await page.route('**/api/checkout',r=>r.fulfill({json:attempt('open')}));
 await setup(page);
 await page.locator('[data-billing-consent]').check();
 await page.locator('[data-buy-package]').click();
 await expect(page).toHaveURL(/^https:\/\/checkout\.stripe\.com\//);
 await page.route('**/api/billing-portal',r=>r.fulfill({json:{url:'https://evil.test/steal'}}));
 await setup(page,'/subscription',{...baseSummary(),portal_available:true});
 await page.locator('[data-billing-portal]').click();
 await expect(page.locator('[data-billing-error]')).toBeVisible();
 await expect(page).toHaveURL(/\/subscription/);
});

for(const width of [320,390,1440])for(const theme of ['light','dark'])test(`billing visual ${width} ${theme}`,async({page})=>{
 await page.setViewportSize({width,height:950});
 await setup(page);
 await expect(page.locator('[data-buy-package]')).toBeEnabled();
 await page.evaluate(t=>document.dispatchEvent(new CustomEvent('studio:theme-select',{detail:t})),theme);
 await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
 const toggle=page.locator('[data-menu-toggle]');
 if(width<780)await toggle.click();
 await page.locator('.locale-nav a[lang=en]').click();
 if(width<780)await page.keyboard.press('Escape');
 await expect(page.locator('[data-buy-package]')).toHaveText('Continue to Stripe');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await mkdir('private-evidence/stripe-ui',{recursive:true});
 await page.screenshot({path:`private-evidence/stripe-ui/subscription-${width}-${theme}.png`,fullPage:true});
 await setup(page,checkout,baseSummary(),()=>attempt('open'),'en');
 await page.evaluate(t=>document.dispatchEvent(new CustomEvent('studio:theme-select',{detail:t})),theme);
 await expect(page.locator('[data-resume-checkout]')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`private-evidence/stripe-ui/checkout-${width}-${theme}.png`,fullPage:true});
});

test('verified terminal attempt permits a fresh purchase; ambiguity retains original key',async({page})=>{
 const oldKey='00000000-0000-4000-8000-000000000055';
 await page.addInitScript(key=>sessionStorage.setItem('studio:account:billing-member:checkout',JSON.stringify({key,plan:'plus'})),oldKey);
 await setup(page,'/subscription',{...baseSummary(),last_attempt:{...attempt('expired'),idempotency_key:oldKey}});
 await expect(page.locator('[name=plan_code][value=pro]')).toBeEnabled();
 await page.locator('[name=plan_code][value=pro]').check();
});

test('creating attempt retries original server key without duplicating a purchase',async({page})=>{
 let sent;
 await page.route('**/api/checkout',r=>{sent=r.request().headers()['idempotency-key'];return r.fulfill({status:503,json:{error:{code:'service_unavailable'}}});});
 await setup(page,checkout,baseSummary(),()=>({...attempt('creating'),idempotency_key:'original-server-key'}));
 await page.locator('[data-retry-checkout]').click();
 await expect(page.locator('[data-billing-error]')).toBeVisible();
 expect(sent).toBe('original-server-key');
});

test('confirmation needs completed attempt AND active server subscription',async({page})=>{
 const summary={...baseSummary(),subscription:null};
 await setup(page,checkout,summary,()=>attempt('completed'));
 await expect(page.locator('[data-payment-state]')).not.toHaveAttribute('data-state','active');
 summary.subscription={plan_code:'plus',status:'trialing',current_period_end:future(7)};
 await page.locator('[data-refresh-billing]').click();
 await expect(page.locator('[data-payment-state]')).toHaveAttribute('data-state','active');
});

for(const path of ['/dashboard','/progress','/profile'])for(const width of [320,390,1440])for(const theme of ['light','dark'])test(`shared cabinet with billing ${path} ${width} ${theme}`,async({page})=>{
 await page.setViewportSize({width,height:950});
 await page.route('**/api/me/profile',r=>r.fulfill({json:{first_name:'Тест',last_name:'Студія',locale:'uk'}}));
 await page.route('**/api/me/onboarding',r=>r.fulfill({json:{goal_codes:['handstand'],self_reported_level:2,session_minutes:45,weekdays:[1,3,5],time_of_day:'evening',birth_year:null,height_cm:null,weight_kg:null,revision:1}}));
 await setup(page,path);
 if(path==='/profile')await expect(page.locator('[data-profile-form]')).toBeVisible();
 await page.evaluate(t=>document.dispatchEvent(new CustomEvent('studio:theme-select',{detail:t})),theme);
 await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
 await mkdir('private-evidence/stripe-ui',{recursive:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`private-evidence/stripe-ui/${path.slice(1)}-${width}-${theme}-uk.png`,fullPage:true});
 if(width<780)await page.locator('[data-menu-toggle]').click();
 await expect(page.locator('[data-member-nav] a[href^="/subscription"]')).toBeVisible();
 if(width<780){
  await expect(page.locator('#site-menu')).toHaveAttribute('aria-modal','true');
  await page.screenshot({path:`private-evidence/stripe-ui/${path.slice(1)}-${width}-${theme}-menu-open.png`,fullPage:true});
 }
 await page.locator('.locale-nav a[lang=en]').click();
 if(width<780){
  await page.screenshot({path:`private-evidence/stripe-ui/${path.slice(1)}-${width}-${theme}-menu.png`,fullPage:true});
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-menu-toggle]')).toBeFocused();
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`private-evidence/stripe-ui/${path.slice(1)}-${width}-${theme}-en.png`,fullPage:true});
});

for(const width of [390,1440])for(const theme of ['light','dark'])test(`payment success and error visuals ${width} ${theme}`,async({page})=>{
 await page.setViewportSize({width,height:950});
 const summary={...baseSummary(),portal_available:true,subscription:{plan_code:'plus',status:'trialing',current_period_end:future(3)}};
 await setup(page,'/subscription',summary);
 await expect(page.locator('[data-subscription-state]')).toHaveAttribute('data-state','expiring');
 await page.evaluate(t=>document.dispatchEvent(new CustomEvent('studio:theme-select',{detail:t})),theme);
 await page.screenshot({path:`private-evidence/stripe-ui/active-${width}-${theme}.png`,fullPage:true});
 await setup(page,checkout,summary,()=>attempt('completed'));
 await expect(page.locator('[data-payment-state]')).toHaveAttribute('data-state','active');
 await page.evaluate(t=>document.dispatchEvent(new CustomEvent('studio:theme-select',{detail:t})),theme);
 await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
 await page.screenshot({path:`private-evidence/stripe-ui/success-${width}-${theme}.png`,fullPage:true});
 await setup(page);
 await page.route('**/api/checkout',r=>r.fulfill({status:503,json:{error:{code:'service_unavailable'}}}));
 await page.locator('[data-billing-consent]').check();await page.locator('[data-buy-package]').click();
 await expect(page.locator('[data-billing-error]')).toBeVisible();
 await page.evaluate(t=>document.dispatchEvent(new CustomEvent('studio:theme-select',{detail:t})),theme);
 await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
 await page.screenshot({path:`private-evidence/stripe-ui/error-${width}-${theme}.png`,fullPage:true});
});

test('webhook commit between status reads confirms automatically',async({page})=>{
 const summary={...baseSummary(),subscription:null};
 await setup(page,checkout,summary,()=>{
  // Provider confirmation and projection commit together while the page is loading.
  summary.subscription={plan_code:'plus',status:'trialing',current_period_end:future(7)};
  return attempt('completed');
 });
 await expect(page.locator('[data-payment-state]')).toHaveAttribute('data-state','active');
});
