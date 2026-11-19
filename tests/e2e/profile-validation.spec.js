import {test, expect} from '@playwright/test';

async function profile(page, {setup=false, missing=false}={}) {
  const writes=[];
  await page.route('**/api/session', r=>r.fulfill({json:{authenticated:true,setup_required:setup,csrf_token:'synthetic',user:{id:'member-a',role:'member'}}}));
  await page.route('**/api/me/preferences', r=>r.fulfill({json:{theme_preference:'light',revision:0}}));
  await page.route('**/api/me/profile', r=>r.fulfill({json:{first_name:missing?'':'Іван',last_name:missing?'':'Тест',locale:'uk'}}));
  await page.route('**/api/me/onboarding', r=>{
    if(r.request().method()!=='GET') writes.push(r.request().postDataJSON());
    return r.fulfill({json:setup?null:{goal_codes:missing?[]:['handstand'],self_reported_level:null,weekdays:missing?[]:[1],time_of_day:null,session_minutes:missing?null:45,revision:1}});
  });
  await page.goto('/profile?lang=uk');
  await expect(page.locator('[data-profile-form]')).toBeVisible();
  return writes;
}

for(const width of [390,1440]) test(`required level has inline feedback and clears after selection ${width}`, async({page})=>{
  await page.setViewportSize({width,height:900});
  const writes=await profile(page);
  const group=page.locator('[data-group=self_reported_level]');
  await expect(page.locator('.profile-field-error:visible')).toHaveCount(0);
  await page.locator('[type=submit]').click();
  await expect(group).toHaveAttribute('aria-invalid','true');
  const error=page.locator('#profile-error-self_reported_level');
  await expect(error).toBeVisible();
  await expect(error).toHaveText('Оберіть ваш рівень.');
  if(width===390) {
    const hint=await error.boundingBox();
    const actions=await page.locator('[data-actions]').boundingBox();
    expect(hint.y+hint.height).toBeLessThanOrEqual(actions.y);
    expect(hint.y).toBeGreaterThanOrEqual(64);
  }
  await expect(group.locator('input').first()).toBeFocused();
  await expect(group.locator('input').first()).toHaveAttribute('aria-describedby',/profile-error-self_reported_level/);
  expect(writes).toEqual([]);
  if(width===390) await page.locator('[data-menu-toggle]').click();
  await page.locator('.locale-nav a[lang=en]').click();
  if(width===390 && await page.locator('[data-menu-toggle]').getAttribute('aria-expanded')==='true') await page.locator('[data-menu-close]').click();
  await expect(error).toHaveText('Choose your level.');
  await group.locator('input[value="2"]').check();
  await expect(error).toBeHidden();
  await expect(group).toHaveAttribute('aria-invalid','false');
  await expect(group.locator('input').first()).not.toHaveAccessibleDescription(/Choose your level/);
  await expect(page.locator('[data-profile-error]')).toBeHidden();
  await expect(page.locator('#profile-first-name')).toHaveValue('Іван');
});

test('required fields show specific messages; optional empty fields are not errors', async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  const writes=await profile(page,{missing:true});
  await page.locator('[type=submit]').click();
  for(const [name,text] of Object.entries({first_name:'Вкажіть ім’я.',last_name:'Вкажіть прізвище.',goal_codes:'Оберіть хоча б одну ціль.',self_reported_level:'Оберіть ваш рівень.',weekdays:'Оберіть хоча б один день.',session_minutes:'Оберіть тривалість заняття.'})) {
    await expect(page.locator(`#profile-error-${name}`)).toHaveText(text);
  }
  await expect(page.locator('.profile-field-error:visible')).toHaveCount(6);
  for(const name of ['birth_year','height_cm','weight_kg']) await expect(page.locator(`[name=${name}]`)).toHaveAttribute('aria-invalid','false');
  await page.locator('#profile-first-name').fill('Іван');
  await expect(page.locator('#profile-error-first_name')).toBeHidden();
  expect(writes).toEqual([]);
});

test('mobile wizard validates only the current step and keeps choices',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  const writes=await profile(page,{setup:true});
  await page.locator('[data-wizard-next]').click();
  await page.locator('[name=goal_codes][value=handstand]').check();
  await page.locator('[data-wizard-next]').click();
  await expect(page.locator('#profile-error-self_reported_level')).toBeVisible();
  await expect(page.locator('.profile-field-error:visible')).toHaveCount(1);
  await expect(page.locator('[data-wizard-count]')).toHaveText('Крок 2 з 4');
  await page.locator('[name=self_reported_level][value="1"]').check();
  await page.locator('[data-wizard-next]').click();
  await expect(page.locator('[data-wizard-count]')).toHaveText('Крок 3 з 4');
  await page.locator('[data-wizard-back]').click();
  await expect(page.locator('[name=goal_codes][value=handstand]')).toBeChecked();
  expect(writes).toEqual([]);
});

test('desktop category labels have breathing room',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await profile(page);
  for(const id of ['level-label','time-label','minutes-label']) {
    const gaps=await page.locator('#'+id).evaluate(el=>({above:el.getBoundingClientRect().top-el.previousElementSibling.getBoundingClientRect().bottom,below:el.nextElementSibling.getBoundingClientRect().top-el.getBoundingClientRect().bottom}));
    expect(gaps.above).toBeGreaterThanOrEqual(24);
    expect(gaps.below).toBeGreaterThanOrEqual(10);
  }
});


test('corrected group removes error description and restores it on another invalid submit',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await profile(page);
  const input=page.locator('[name=goal_codes][value=handstand]');
  await input.uncheck();
  await page.locator('[type=submit]').click();
  await expect(input).toHaveAccessibleDescription('Оберіть хоча б одну ціль.');
  await input.check();
  await expect(input).not.toHaveAccessibleDescription(/Оберіть/);
  await input.uncheck();
  await page.locator('[type=submit]').click();
  await expect(input).toHaveAccessibleDescription('Оберіть хоча б одну ціль.');
});
