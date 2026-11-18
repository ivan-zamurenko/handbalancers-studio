import { test, expect } from '@playwright/test';

test.use({ reducedMotion: 'reduce' });

const pages = ['/', '/plans', '/login', '/register', '/verify-email', '/recovery'];
const phones = [[320, 'uk', 'light'], [360, 'en', 'dark'], [390, 'uk', 'dark'], [430, 'en', 'light'], [768, 'uk', 'light']];

async function themed(page, width, theme) {
  await page.setViewportSize({ width, height: 800 });
  await page.addInitScript(value => localStorage.setItem('studio:theme:guest', value), theme);
}

for (const [width, language, theme] of phones) {
  test(`phone header is one compact bar with a menu button: ${width} ${language} ${theme}`, async ({ page }) => {
    await themed(page, width, theme);
    for (const path of pages) {
      await page.goto(`${path}?lang=${language}`);
      const bar = await page.locator('.site-header').boundingBox();
      expect(bar.height, `${path}: single-row bar`).toBeLessThanOrEqual(68);
      const toggle = page.locator('[data-menu-toggle]');
      await expect(toggle).toBeVisible();
      await expect(toggle).toHaveAttribute('aria-expanded', 'false');
      const box = await toggle.boundingBox();
      expect(box.width).toBeGreaterThanOrEqual(44);
      expect(box.height).toBeGreaterThanOrEqual(44);
      // Secondary items live in the menu, not in the bar.
      await expect(page.locator('.primary-nav')).toBeHidden();
      await expect(page.locator('.locale-nav')).toBeHidden();
      await expect(page.locator('[data-login-cta]')).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${path}: no overflow`).toBe(true);
    }
  });

  test(`phone menu is a full-height panel with large targets: ${width} ${language} ${theme}`, async ({ page }) => {
    await themed(page, width, theme);
    await page.goto(`/?lang=${language}`);
    const toggle = page.locator('[data-menu-toggle]');
    await toggle.click();
    const menu = page.locator('#site-menu');
    await expect(menu).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const panel = await menu.boundingBox();
    expect(panel.height).toBeGreaterThanOrEqual(790);
    const targets = menu.locator('.primary-nav a, .locale-nav a, .theme-toggle, [data-login-link], [data-menu-close]');
    for (const target of await targets.all()) {
      const b = await target.boundingBox();
      expect(b.height).toBeGreaterThanOrEqual(44);
      expect(b.x).toBeGreaterThanOrEqual(0);
      expect(b.x + b.width).toBeLessThanOrEqual(width);
    }
    const first = await menu.locator('.primary-nav a').first().boundingBox();
    expect(first.height, 'main links are large').toBeGreaterThanOrEqual(52);
    await expect(page.locator('main')).toHaveAttribute('inert', '');
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).overflow)).toBe('hidden');
  });
}

test('desktop keeps links, language and theme in one row', async ({ page }) => {
  await themed(page, 1440, 'dark');
  for (const path of pages) {
    await page.goto(`${path}?lang=en`);
    await expect(page.locator('[data-menu-toggle]')).toBeHidden();
    const boxes = await page.locator('.primary-nav a, .locale-nav a, .theme-toggle').evaluateAll(elements => elements.map(element => {
      const { x, y, width, height } = element.getBoundingClientRect();
      return { x, y, width, height };
    }));
    expect(boxes).toHaveLength(6);
    const centers = boxes.map(box => box.y + box.height / 2);
    expect(Math.max(...centers) - Math.min(...centers)).toBeLessThan(2);
    for (let i = 1; i < boxes.length; i++) expect(boxes[i].x).toBeGreaterThanOrEqual(boxes[i - 1].x + boxes[i - 1].width);
  }
});

test('phone menu: keyboard, Esc, backdrop and link all close it and restore focus', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto('/?lang=en');
  const toggle = page.locator('[data-menu-toggle]');
  const menu = page.locator('#site-menu');
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(menu.locator('.primary-nav a').first()).toBeFocused();
  // Focus stays inside the open menu.
  for (let i = 0; i < 20; i++) await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.querySelector('#site-menu').contains(document.activeElement))).toBe(true);
  expect(await page.locator('.wordmark').evaluate(el => el.inert)).toBe(true);
  await menu.locator('[data-menu-close]').focus();
  await page.keyboard.press('Space');
  await expect(menu).toBeHidden();
  await expect(toggle).toBeFocused();
  await toggle.click();
  await page.keyboard.press('Escape');
  await expect(menu).toBeHidden();
  await expect(toggle).toBeFocused();
  await toggle.click();
  await page.mouse.click(10, 400); // backdrop, left of the panel
  await expect(menu).toBeHidden();
  await toggle.click();
  await menu.getByRole('link', { name: 'Method', exact: true }).click();
  await expect(page).toHaveURL(/#method$/);
  await expect(menu).toBeHidden();
  const header = await page.locator('.site-header').boundingBox();
  await expect.poll(async () => page.locator('#method').evaluate(element => element.getBoundingClientRect().top)).toBeGreaterThanOrEqual(header.height - 1);
});

test('phone menu: language, theme and login work', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto('/?lang=uk');
  await page.locator('[data-menu-toggle]').click();
  await page.locator('#site-menu').getByRole('link', { name: 'EN', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await page.locator('[data-menu-toggle]').click();
  const before = await page.locator('html').getAttribute('data-theme');
  await page.locator('#site-menu').getByRole('button', { name: 'Theme' }).click();
  await expect(page.locator('html')).not.toHaveAttribute('data-theme', before);
  await page.keyboard.press('Escape');
  await page.locator('[data-login-cta]').click();
  await expect(page).toHaveURL(/\/login\?lang=en$/);
});

test('signed-in phone bar shows profile in the menu, not login', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.route('**/api/session', route => route.fulfill({ json: { authenticated: true, csrf_token: 'a'.repeat(64), user: { id: 'member-a' } } }));
  await page.goto('/?lang=uk');
  await expect(page.locator('[data-login-cta]')).toBeHidden();
  await page.locator('[data-menu-toggle]').click();
  const menu = page.locator('#site-menu');
  await expect(menu.getByRole('link', { name: 'Профіль' })).toBeVisible();
  await expect(menu.getByRole('button', { name: 'Вийти' })).toBeVisible();
});

test('mobile account help has comfortable touch targets', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto('/login?lang=uk');
  for (const link of await page.locator('.login-help a').all()) {
    const box = await link.boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(44);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('phone bar and menu reflow when text is enlarged', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto('/?lang=uk');
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('[data-menu-toggle]').click();
  await expect(page.locator('#site-menu .primary-nav a').first()).toHaveCSS('font-size', '44px');
  for (const link of await page.locator('#site-menu .primary-nav a').all()) {
    const box = await link.boundingBox();
    expect(box.x + box.width).toBeLessThanOrEqual(320);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

for (const staleCookie of [false, true]) {
  test(`mobile login is reachable without JavaScript, stale cookie: ${staleCookie}`, async ({ browser, baseURL }) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 740 } });
    if (staleCookie) await context.addCookies([{ name: 'studio_local_session', value: 'synthetic-expired-cookie', url: baseURL }]);
    const page = await context.newPage();
    await page.goto(`${baseURL}/?lang=en`);
    const login = page.locator('.site-header').getByRole('link', { name: 'Log in', exact: true });
    await expect(login).toBeVisible();
    await expect(login).toHaveCount(1);
    await page.locator('[data-menu-toggle]').click();
    await expect(page.locator('#site-menu').getByRole('link', { name: 'Plans', exact: true })).toBeVisible();
    await page.goto(`${baseURL}/?lang=en`);
    await login.click();
    await expect(page).toHaveURL(/\/login\?lang=en$/);
    await context.close();
  });
}
