import {test, expect} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const registrationPlans = JSON.parse(execFileSync('.venv/bin/python', ['tests/fixtures/render_public_pages.py'], {encoding:'utf8'}))['/plans?lang=uk'];

const guest = {goal_codes:['handstand'], self_reported_level:2, session_minutes:90,
  weekdays:[1,3,5], time_of_day:'evening'};
const existing = {...guest, goal_codes:['mobility'], session_minutes:30, revision:7,
  birth_year:1992, height_cm:178, weight_kg:74};

async function questionnaire(page) {
  await page.goto('/onboarding?lang=uk');
  await page.locator('[name=goal_codes][value=handstand]').check();
  await page.locator('[name=self_reported_level][value="2"]').check();
  await page.locator('[data-guest-next]').click();
  for (const day of guest.weekdays) await page.locator(`[name=weekdays][value="${day}"]`).check();
  await page.locator('[name=time_of_day][value=evening]').check();
  await page.locator('[name=session_minutes][value="90"]').check();
}

async function account(page, onboarding = null, {saveStatus = 200, id = 'member-a'} = {}) {
  const writes=[];
  await page.route('**/dashboard?*',r=>r.fulfill({contentType:'text/html',body:'<h1>Today</h1>'}));
  await page.route('**/api/session', r => r.fulfill({json:{authenticated:true, csrf_token:'a'.repeat(64),
    setup_required:!onboarding, user:{id,role:'member'}}}));
  await page.route('**/api/me/profile', r => r.fulfill({json:{first_name:'Іван',last_name:'Тест',locale:'uk'}}));
  await page.route('**/api/me/preferences', r => r.fulfill({json:{theme_preference:'auto',revision:0}}));
  await page.route('**/api/me/onboarding', r => {
    if(r.request().method()==='GET') return r.fulfill({json:onboarding});
    writes.push(r.request().postDataJSON());
    if(saveStatus===200) onboarding={...writes.at(-1),revision:(onboarding?.revision??0)+1};
    return r.fulfill({status:saveStatus,json:saveStatus===200?onboarding:{error:{code:'internal_error'}}});
  });
  return writes;
}

test('fresh_days_empty', async ({page}) => {
  await page.goto('/onboarding?lang=uk');
  await expect(page.locator('[data-guest-form]')).toBeVisible();
  await expect(page.locator('[name=weekdays]:checked')).toHaveCount(0);
  await page.locator('[data-guest-next]').click();
  await expect(page.locator('[name=goal_codes]').first()).toBeFocused();
});

test('selected_dom_value: 90 survives plans/auth navigation and explicit profile save', async ({page}) => {
  // This journey requires registration enabled; draft presence does not enable it.
  await page.route('**/plans?lang=uk', r=>r.fulfill({contentType:'text/html',body:registrationPlans}));
  await questionnaire(page);
  await page.locator('[name=session_minutes][value="30"]').check();
  // Browser restoration/programmatic selection need not fire a change event.
  await page.locator('[name=session_minutes][value="90"]').evaluate(n=>{n.checked=true;});
  await page.locator('[data-guest-submit]').click();
  await expect(page).toHaveURL(/\/plans\?lang=uk$/);
  await page.getByRole('radio',{name:'Essential',exact:true}).check();
  await page.locator('[data-continue-plan]').click();
  await expect(page).toHaveURL(/\/register\?lang=uk$/);
  await page.unroute('**/plans?lang=uk');
  // Synthetic authenticated boundary, real public/profile pages and draft endpoint.
  const writes=await account(page);
  await page.goto('/plans?lang=uk');
  await expect(page).toHaveURL(/\/profile\?lang=uk$/);
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
  expect(writes).toEqual([]);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('[data-profile-form] [type=submit]').click();
  await expect.poll(()=>writes.length).toBe(1);
  expect(writes[0]).toMatchObject({...guest,expected_revision:0});
  await expect(page.locator('[data-save-feedback]')).toBeHidden({timeout:8000});
  await expect(page).toHaveURL(/\/dashboard\?lang=uk$/);
  await page.goto('/profile?lang=uk');
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
  expect(await page.evaluate(()=>Object.keys(sessionStorage).filter(k=>k.endsWith(':onboarding-draft')))).toEqual([]);
});

test('existing_account_no_silent_overwrite: explicit apply preserves body and revision', async ({page}) => {
  await questionnaire(page);
  await page.locator('[data-guest-submit]').click();
  await expect(page).toHaveURL(/\/plans/);
  const writes=await account(page,existing);
  await page.goto('/plans?lang=uk');
  // Completed users are no longer forced back through onboarding by a guest draft.
  await expect(page).toHaveURL(/\/plans/);
  await page.goto('/profile?lang=uk');
  await expect(page.locator('[name=session_minutes][value="30"]')).toBeChecked();
  await expect(page.locator('[data-draft-apply]')).toBeVisible();
  expect(writes).toEqual([]);
  await page.locator('[data-draft-apply]').click();
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
  await expect(page.locator('[name=birth_year]')).toHaveValue('1992');
  expect(writes).toEqual([]);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('[data-profile-form] [type=submit]').click();
  await expect.poll(()=>writes.length).toBe(1);
  expect(writes[0]).toMatchObject({...guest,birth_year:1992,expected_revision:7});
});

test('reduced_motion_no_click_loss: rapid submit sends one request with current values', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:'reduce'});
  await questionnaire(page);
  const requests=[];
  page.on('request',r=>{if(r.url().endsWith('/api/onboarding/draft'))requests.push(r.postDataJSON());});
  await page.locator('[data-guest-submit]').evaluate(n=>{n.click();n.click();});
  await expect(page).toHaveURL(/\/plans/);
  expect(requests).toEqual([guest]);
  await page.goto('/onboarding?lang=en');
  await page.locator('[data-guest-next]').click();
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
});

test('storage disabled prevents silent loss and keeps editable answers', async ({page}) => {
  await page.addInitScript(()=>{Storage.prototype.setItem=()=>{throw new Error('storage disabled');};});
  await questionnaire(page);
  await page.locator('[data-guest-submit]').click();
  await expect(page.locator('[data-guest-error]')).toBeVisible();
  await expect(page).toHaveURL(/\/onboarding/);
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
  await expect(page.locator('[data-guest-submit]')).toBeEnabled();
});

test('pending submission locks choices and unlocks them after a failed response', async ({page}) => {
  await questionnaire(page);
  let release;
  await page.route('**/api/onboarding/draft',async route=>{
    await new Promise(resolve=>{release=resolve;});
    await route.fulfill({status:503,json:{error:{code:'unavailable'}}});
  });
  await page.locator('[data-guest-submit]').click();
  await expect.poll(()=>!!release).toBe(true);
  await expect(page.locator('[name=session_minutes][value="30"]')).toBeDisabled();
  await expect(page.locator('[name=weekdays][value="1"]')).toBeDisabled();
  release();
  await expect(page.locator('[data-guest-error]')).toBeVisible();
  await expect(page.locator('[name=session_minutes][value="30"]')).toBeEnabled();
  await expect(page.locator('[name=weekdays][value="1"]')).toBeEnabled();
  await expect(page.locator('[name=weekdays][value="2"]')).toBeDisabled();
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
});

test('server failure keeps draft for retry without writing on page load', async ({page}) => {
  await questionnaire(page);
  await page.locator('[data-guest-submit]').click();
  await expect(page).toHaveURL(/\/plans/);
  const writes=await account(page,null,{saveStatus:500});
  await page.goto('/profile?lang=uk');
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
  expect(writes).toEqual([]);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('[data-profile-form] [type=submit]').click();
  await expect(page.locator('[data-profile-status]')).toContainText('помилка',{timeout:8000});
  await page.reload();
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
});

test('discard keeps existing answers and does not create a write', async ({page}) => {
  await questionnaire(page);
  await page.locator('[data-guest-submit]').click();
  await expect(page).toHaveURL(/\/plans/);
  const writes=await account(page,existing);
  await page.goto('/profile?lang=uk');
  await page.locator('[data-draft-discard]').click();
  await expect(page.locator('[data-draft-notice]')).toBeHidden();
  await expect(page.locator('[name=session_minutes][value="30"]')).toBeChecked();
  await page.reload();
  await expect(page.locator('[data-draft-notice]')).toBeHidden();
  expect(writes).toEqual([]);
});

test('409 shows latest server answers without a blind overwrite retry', async ({page}) => {
  await questionnaire(page);
  await page.locator('[data-guest-submit]').click();
  await expect(page).toHaveURL(/\/plans/);
  await account(page);
  let writes=0;
  await page.route('**/api/me/onboarding',r=>{
    if(r.request().method()==='GET')return r.fulfill({json:null});
    writes++;
    return r.fulfill({status:409,json:{current:existing}});
  });
  await page.goto('/profile?lang=uk');
  await expect(page.locator('[name=session_minutes][value="90"]')).toBeChecked();
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('[data-profile-form] [type=submit]').click();
  await expect(page.locator('[data-profile-status]')).toContainText('іншому пристрої',{timeout:8000});
  await expect(page.locator('[name=session_minutes][value="30"]')).toBeChecked();
  expect(writes).toBe(1);
});

for(const width of [390,1440])for(const theme of ['light','dark']){
  test(`guest layout ${width} ${theme}: both steps, keyboard, no overflow`,async({page})=>{
    await page.setViewportSize({width,height:900});
    await page.emulateMedia({colorScheme:theme});
    await page.addInitScript(theme=>localStorage.setItem('studio:theme:guest',theme),theme);
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('/onboarding?lang=en');
    await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
    await page.locator('[name=goal_codes][value=handstand]').check();
    await page.locator('[name=self_reported_level][value="2"]').check();
    const folder='private-evidence/onboarding-s05-02';
    await mkdir(folder,{recursive:true});
    await page.screenshot({path:`${folder}/${width}-${theme}-goals.png`,fullPage:true});
    await page.locator('[data-guest-next]').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-step=schedule] legend')).toBeFocused();
    await expect(page.locator('[data-step=goals]')).toBeHidden();
    await page.screenshot({path:`${folder}/${width}-${theme}-schedule.png`,fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.locator('[data-guest-back]').click();
    await expect(page.locator('[name=goal_codes][value=handstand]')).toBeChecked();
    expect(errors).toEqual([]);
  });
}
