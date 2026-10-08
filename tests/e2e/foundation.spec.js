import { test, expect } from '@playwright/test';

test('health smoke: real browser sees liveness JSON', async ({ page }) => {
  const response = await page.goto('/health/live');
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual({ status: 'ok' });
  await expect(page.locator('pre')).toContainText('"status":"ok"');
});

test.describe('context isolation', () => {
  test.describe.configure({ mode: 'serial' });
  test('first test seeds and verifies its own state', async ({ page, context, baseURL }) => {
    await page.goto('/health/live');
    await context.addCookies([{ name: 'isolation_probe', value: 'synthetic', url: baseURL }]);
    await page.evaluate(() => {
      localStorage.setItem('isolation_probe', 'synthetic');
      sessionStorage.setItem('isolation_probe', 'synthetic');
    });
    expect((await context.cookies()).find(cookie => cookie.name === 'isolation_probe').value)
      .toBe('synthetic');
    expect(await page.evaluate(() => localStorage.getItem('isolation_probe'))).toBe('synthetic');
    expect(await page.evaluate(() => sessionStorage.getItem('isolation_probe'))).toBe('synthetic');
  });
  test('next test starts with fresh cookies and storage', async ({ page, context }) => {
    await page.goto('/health/live');
    expect(await context.cookies()).toEqual([]);
    expect(await page.evaluate(() => localStorage.length)).toBe(0);
    expect(await page.evaluate(() => sessionStorage.length)).toBe(0);
  });
});
