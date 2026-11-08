import { test, expect } from '@playwright/test';

test.use({ reducedMotion: 'reduce' });

const pages = ['/', '/plans', '/login', '/register', '/verify-email', '/recovery'];
const layouts = [
  [320, 'uk', 'light'], [360, 'en', 'dark'], [390, 'uk', 'dark'],
  [430, 'en', 'light'], [768, 'uk', 'light'], [1440, 'en', 'dark'],
];

for (const [width, language, theme] of layouts) {
  test(`navigation stays usable on every page: ${width} ${language} ${theme}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(value => localStorage.setItem('studio:theme:guest', value), theme);
    for (const path of pages) {
      await page.goto(`${path}?lang=${language}`);
      await page.evaluate(() => document.fonts.ready);
      await expect(page.locator('[data-theme-control]')).toBeEnabled();
      const targets = page.locator('.primary-nav a, .locale-nav a, .theme-toggle');
      const boxes = await targets.evaluateAll(elements => elements.map(element => {
        const { x, y, width, height } = element.getBoundingClientRect();
        return { x, y, width, height, label: element.textContent.trim() || 'theme' };
      }));
      expect(boxes).toHaveLength(6);
      const centers = boxes.map(box => box.y + box.height / 2);
      expect(Math.max(...centers) - Math.min(...centers), `${path}: links, language and theme share one row`).toBeLessThan(2);
      for (const box of boxes) {
        expect(box.width, `${path}: ${box.label} target width`).toBeGreaterThanOrEqual(24);
        expect(box.height, `${path}: ${box.label} target height`).toBeGreaterThanOrEqual(44);
        expect(box.x).toBeGreaterThanOrEqual(0);
        expect(box.x + box.width).toBeLessThanOrEqual(width);
      }
      for (let i = 1; i < boxes.length; i++) {
        expect(boxes[i].x, `${path}: adjacent controls do not overlap`).toBeGreaterThanOrEqual(boxes[i - 1].x + boxes[i - 1].width);
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${path}: no page overflow`).toBe(true);
      await expect(page.locator('[data-login-link]')).toBeVisible();
    }
  });
}

test('mobile language, theme, navigation and login remain functional', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto('/?lang=uk');
  await page.getByRole('link', { name: 'EN', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  const theme = page.getByRole('button', { name: 'Theme', exact: true });
  const before = await page.locator('html').getAttribute('data-theme');
  await theme.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('html')).not.toHaveAttribute('data-theme', before);
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Method', exact: true }).click();
  await expect(page).toHaveURL(/#method$/);
  const header = await page.locator('.site-header').boundingBox();
  await expect.poll(async () => page.locator('#method').evaluate(element => element.getBoundingClientRect().top)).toBeGreaterThanOrEqual(header.height);
  await page.getByRole('link', { name: 'Log in', exact: true }).click();
  await expect(page).toHaveURL(/\/login\?lang=en$/);
  await expect(page.locator('h1')).toBeVisible();
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

test('mobile navigation reflows when text is enlarged', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto('/?lang=uk');
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  await expect(page.locator('html')).toHaveCSS('font-size', '32px');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const nav = await page.locator('.primary-nav').boundingBox();
  const locale = await page.locator('.locale-nav').boundingBox();
  for (const link of await page.locator('.primary-nav a').all()) {
    const box = await link.boundingBox();
    expect(box.x + box.width).toBeLessThanOrEqual(locale.x);
    expect(box.y + box.height).toBeLessThanOrEqual(nav.y + nav.height);
  }
  await page.locator('.primary-nav a[href$="#method"]').click();
  const header = await page.locator('.site-header').boundingBox();
  await expect.poll(async () => page.locator('#method').evaluate(element => element.getBoundingClientRect().top)).toBeGreaterThanOrEqual(header.height);
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
    await login.click();
    await expect(page).toHaveURL(/\/login\?lang=en$/);
    await context.close();
  });
}
