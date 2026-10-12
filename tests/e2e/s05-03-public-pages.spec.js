import { expect, test } from '@playwright/test';

const prices = { essential: 1999, plus: 4999, pro: 17999, 'pro-plus': 29999 };

test('prices_unchanged and trial_terms_visible', async ({ page }) => {
  const response = await page.goto('/');
  expect(response.status()).toBe(200);
  for (const [id, price] of Object.entries(prices)) {
    const card = page.locator(`[data-plan="${id}"]`);
    await expect(card).toHaveAttribute('data-price-minor', String(price));
    await expect(card).toContainText('€');
    await expect(card).toContainText('/ місяць');
    await expect(card).toContainText(id === 'essential' || id === 'plus' ? '7 днів' : 'Без пробного періоду');
  }
  await expect(page.locator('#trial-terms')).toContainText('картка');
  await expect(page.locator('#trial-terms')).toContainText('автоматично');
  await expect(page.locator('#trial-terms')).toContainText('один раз');
});

test('selection_survives_reload and travels between public pages', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('radio', { name: 'Plus', exact: true })).toBeChecked();
  await page.getByRole('radio', { name: 'Essential', exact: true }).check();
  await page.reload();
  await expect(page.getByRole('radio', { name: 'Essential', exact: true })).toBeChecked();
  await page.goto('/plans?lang=en');
  await expect(page.getByRole('radio', { name: 'Essential', exact: true })).toBeChecked();
  await page.getByRole('button', { name: 'Continue with Essential' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('Registration and payments are not open yet');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Continue with Essential' })).toBeFocused();
});

test('no_fake_claims or broken public navigation', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.locator('[data-availability]')).toContainText('AI-аналіз ще недоступний');
  await expect(page.getByText('Порівняти можливості', { exact: true })).toHaveCount(0);
  await page.locator('header').getByRole('link', { name: 'Напрями', exact: true }).click();
  await expect(page).toHaveURL(/#directions$/);
  await expect(page.locator('#directions h2')).toBeInViewport();
  await page.locator('header').getByRole('link', { name: 'Методика', exact: true }).click();
  await expect(page.locator('#method h2')).toBeInViewport();
  await page.locator('header').getByRole('link', { name: 'Тарифи', exact: true }).click();
  await expect(page.locator('#plans h2')).toBeInViewport();
  await expect(page.locator('body')).not.toContainText('1000 клієнтів');
  expect(errors).toEqual([]);
});

for (const width of [390, 1440]) for (const theme of ['light', 'dark']) {
  test(`public page ${width} ${theme}, language and theme persist`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await page.getByLabel('Тема').selectOption(theme);
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Рухатися вільніше.');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole('link', { name: 'EN', exact: true }).click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Move more freely.');
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.getByRole('radio', { name: 'Pro+', exact: true }).check();
    await expect(page.getByRole('button', { name: 'Continue with Pro+' })).toBeVisible();
  });
}

test('blocked storage remains usable', async ({ page }) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new Error('disabled'); };
    Storage.prototype.setItem = () => { throw new Error('disabled'); };
  });
  await page.goto('/plans');
  await page.getByRole('radio', { name: 'Pro', exact: true }).check();
  await expect(page.getByRole('button', { name: 'Продовжити з Pro', exact: true })).toBeEnabled();
  await expect(page.locator('[data-storage-status]')).toContainText('збереження вимкнене');
});

test('public copy and prices work without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:8765/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Рухатися вільніше.');
  await expect(page.locator('[data-plan="plus"]')).toContainText('49,99');
  await expect(page.locator('noscript p')).toContainText('JavaScript');
  await context.close();
});

test('plans heading and keyboard selection; unknown saved choice falls back safely', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('studio:public:plan', '__proto__'));
  await page.goto('/plans?lang=en');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Your goals. My attention.');
  const plus = page.getByRole('radio', { name: 'Plus', exact: true });
  await expect(plus).toBeChecked();
  await plus.focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('radio', { name: 'Pro', exact: true })).toBeChecked();
  await expect(page.getByRole('button', { name: 'Continue with Pro', exact: true })).toBeEnabled();
});
