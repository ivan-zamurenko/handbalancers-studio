import {test, expect} from '@playwright/test';

const filled = {goal_codes:['handstand','strength'], self_reported_level:2, session_minutes:45,
  weekdays:[1,3,5], time_of_day:'evening', birth_year:1992, height_cm:178, weight_kg:74.5, revision:1};

async function mockProfile(page, {setup, onboardingStatus = 200}) {
  const sent = [];
  await page.route('**/api/session', route => route.fulfill({json: {authenticated:true, setup_required:setup,
    csrf_token:'a'.repeat(64), user:{id:'member-a', role:'member'}}}));
  await page.route('**/api/me/profile', route => route.fulfill({json: {first_name:'Іван',
    last_name: setup ? '' : 'Петренко', locale:'uk'}}));
  await page.route('**/api/me/preferences', route => route.fulfill({json:{theme_preference:'auto', revision:0}}));
  await page.route('**/api/me/onboarding', async route => {
    if (route.request().method() === 'GET') return route.fulfill({json: setup ? null : filled});
    sent.push(route.request().postDataJSON());
    await new Promise(resolve => setTimeout(resolve, 150));
    return onboardingStatus === 200
      ? route.fulfill({json:{...route.request().postDataJSON(), revision:2}})
      : route.fulfill({status:onboardingStatus, json:{error:{code:'internal_error'}}});
  });
  return sent;
}

test('mobile setup is a step-by-step form and ends with the save animation', async ({page}) => {
  await page.setViewportSize({width:390, height:844});
  const sent = await mockProfile(page, {setup:true});
  await page.goto('/profile?lang=uk');
  await expect(page.locator('[data-wizard-count]')).toHaveText('Крок 1 з 4');
  await expect(page.locator('fieldset[data-step="goals"]')).toBeHidden();
  await page.locator('[data-wizard-next]').click();
  await expect(page.locator('[data-wizard-count]')).toHaveText('Крок 1 з 4');
  await expect(page.locator('#profile-last-name')).toBeFocused();
  await page.fill('#profile-last-name', 'Петренко');
  await page.locator('[data-wizard-next]').click();
  await expect(page.locator('[data-wizard-count]')).toHaveText('Крок 2 з 4');
  await page.getByRole('checkbox', {name:'Стійка на руках', exact:true}).check();
  await page.getByRole('radio', {name:'Маю досвід'}).check();
  await page.locator('[data-wizard-next]').click();
  for (const day of ['Пн','Ср','Пт']) await page.getByRole('checkbox', {name:day, exact:true}).check();
  await page.getByRole('radio', {name:'90 хв'}).check();
  await page.locator('[data-wizard-next]').click();
  await expect(page.locator('[data-wizard-count]')).toHaveText('Крок 4 з 4');
  await expect(page.locator('[data-wizard-skip]')).toBeVisible();
  await page.locator('[data-wizard-skip]').click();

  const overlay = page.locator('[data-save-feedback]');
  await expect(overlay).toBeVisible();
  await expect(page.locator('[data-profile-form]')).toHaveCSS('opacity', '0', {timeout:1500});
  await expect(overlay.locator('[data-sf-figure]')).toBeVisible();
  await expect(overlay.locator('[data-sf-text]')).toHaveText('Збережено', {timeout:8000});
  await expect(overlay).toHaveAttribute('data-outcome', 'success');
  await expect(overlay).toBeHidden({timeout:5000});
  expect(sent[0]).toMatchObject({session_minutes:90, weekdays:[1,3,5], birth_year:null});
  // After the first save the phone layout switches to the editable accordion.
  await expect(page.locator('[data-wizard-count]')).toBeHidden();
  await expect(page.locator('fieldset[data-step="about"] [data-acc-toggle]')).toHaveAttribute('aria-expanded', 'true');
});

test('mobile edit uses collapsible sections with summaries', async ({page}) => {
  await page.setViewportSize({width:390, height:844});
  await mockProfile(page, {setup:false});
  await page.goto('/profile?lang=uk');
  const schedule = page.locator('fieldset[data-step="schedule"]');
  await expect(schedule.locator('[data-acc-toggle]')).toHaveAttribute('aria-expanded', 'false');
  await expect(schedule.locator('[data-acc-summary]')).toHaveText('Пн, Ср, Пт · Вечір · 45 хв');
  await expect(schedule.getByRole('radio', {name:'90 хв'})).toBeHidden();
  await schedule.locator('[data-acc-toggle]').click();
  await expect(schedule.locator('[data-acc-toggle]')).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('.profile-actions [type=submit]')).toBeInViewport();
});

test('server error: figure falls, red cross, data kept; Esc skips', async ({page}) => {
  await page.setViewportSize({width:1440, height:900});
  await mockProfile(page, {setup:false, onboardingStatus:500});
  await page.goto('/profile?lang=uk');
  await page.fill('#profile-first-name', 'Остап');
  await page.locator('[type=submit]').click();
  const overlay = page.locator('[data-save-feedback]');
  await expect(overlay.locator('[data-sf-text]')).toHaveText('Виникла помилка', {timeout:8000});
  await expect(overlay).toHaveAttribute('data-outcome', 'error');
  await page.keyboard.press('Escape');
  await expect(overlay).toBeHidden({timeout:2000});
  await expect(page.locator('#profile-first-name')).toHaveValue('Остап');
  await expect(page.locator('[data-profile-form]')).toHaveCSS('opacity', '1');
});

test('reduced motion shows a static result without the figure', async ({page}) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.setViewportSize({width:1440, height:900});
  await mockProfile(page, {setup:false});
  await page.goto('/profile?lang=uk');
  await page.locator('[type=submit]').click();
  const overlay = page.locator('[data-save-feedback]');
  await expect(overlay.locator('[data-sf-text]')).toHaveText('Збережено');
  await expect(overlay.locator('[data-sf-figure]')).toBeHidden();
});
