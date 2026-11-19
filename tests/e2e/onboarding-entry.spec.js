import {test, expect} from '@playwright/test';

async function locale(page, lang) {
  const toggle=page.locator('[data-menu-toggle]');
  if(await toggle.isVisible() && await toggle.getAttribute('aria-expanded') !== 'true') await toggle.click();
  await page.locator(`.locale-nav a[lang=${lang}]`).click();
  if(await toggle.isVisible() && await toggle.getAttribute('aria-expanded') === 'true') await page.locator('[data-menu-close]').click();
}

for(const width of [390,1440]) test(`language and theme preserve step, DOM and answers at ${width}`,async({page})=>{
  await page.setViewportSize({width,height:900});
  await page.goto('/onboarding?lang=uk');
  await page.locator('[name=goal_codes][value=handstand]').check();
  await page.locator('[name=self_reported_level][value="2"]').check();
  await page.locator('[data-guest-next]').click();
  await page.locator('[name=weekdays][value="3"]').check();
  await page.locator('[name=session_minutes][value="90"]').check();
  await page.evaluate(()=>{window.originalForm=document.querySelector('[data-guest-form]');});
  await locale(page,'en');
  await expect(page.locator('html')).toHaveAttribute('lang','en');
  expect(await page.evaluate(()=>window.originalForm===document.querySelector('[data-guest-form]'))).toBe(true);
  await expect(page.locator('[data-guest-count]')).toHaveText('Step 2 of 2');
  await expect(page.locator('[data-guest-submit]')).toHaveText('View plans');
  await expect(page.getByRole('radio',{name:'90 min',exact:true})).toBeChecked();
  await expect(page).toHaveTitle('Your starting point — Handbalancer’s Studio');
  await expect(page.locator('[name=weekdays][value="3"]')).toBeChecked();
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
  const toggle=page.locator('[data-menu-toggle]');
  if(await toggle.isVisible()) await toggle.click();
  const before=await page.locator('html').getAttribute('data-theme');
  await page.locator('[data-theme-control]').click();
  await expect(page.locator('html')).not.toHaveAttribute('data-theme',before);
  if(await toggle.isVisible()) await page.locator('[data-menu-close]').click();
  await locale(page,'uk');
  await expect(page.locator('[data-guest-count]')).toHaveText('Крок 2 з 2');
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
  expect(await page.evaluate(()=>window.originalForm===document.querySelector('[data-guest-form]'))).toBe(true);
  await page.locator('[data-guest-submit]').click();
  await expect(page).toHaveURL(/\/plans\?lang=uk$/);
  await page.getByRole('radio',{name:'Pro',exact:true}).check();
  await locale(page,'en');
  await expect(page.getByRole('radio',{name:'Pro',exact:true})).toBeChecked();
  await expect(page.locator('[data-continue-plan]')).toHaveText('Continue with Pro');
  await expect(page.locator('[data-plan=pro]')).toContainText('Personal weekly review');
});

test('profile language preserves unsaved names, answers, revision and active step',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.route('**/api/session',r=>r.fulfill({json:{authenticated:true,csrf_token:'a'.repeat(64),setup_required:true,user:{id:'member-a'}}}));
  await page.route('**/api/me/profile',r=>r.fulfill({json:{first_name:'',last_name:'',locale:'uk'}}));
  await page.route('**/api/me/onboarding',r=>r.fulfill({json:null}));
  await page.route('**/api/me/preferences',r=>r.fulfill({json:{theme_preference:'dark',revision:0}}));
  await page.goto('/profile?lang=uk');
  await page.locator('[name=first_name]').fill('Ivan');
  await page.locator('[name=last_name]').fill('Koval');
  await page.locator('[data-wizard-next]').click();
  await page.locator('[name=goal_codes][value=handstand]').check();
  await page.evaluate(()=>{window.originalForm=document.querySelector('[data-profile-form]');});
  await locale(page,'en');
  await expect(page.locator('[data-wizard-count]')).toHaveText('Step 2 of 4');
  await expect(page.locator('[name=first_name]')).toHaveValue('Ivan');
  await expect(page.locator('[name=goal_codes][value=handstand]')).toBeChecked();
  expect(await page.evaluate(()=>window.originalForm===document.querySelector('[data-profile-form]'))).toBe(true);
});
