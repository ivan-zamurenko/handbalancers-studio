import { test, expect } from '@playwright/test';

async function headerItem(page, locator) {
  // Phones keep language/theme/account inside the menu panel.
  if (await page.locator('[data-menu-toggle]').isVisible()) {
    if (await page.locator('[data-menu-toggle]').getAttribute('aria-expanded') !== 'true') await page.locator('[data-menu-toggle]').click();
  }
  return locator;
}
for (const width of [390, 1440]) for (const theme of ['light', 'dark']) {
  test(`clear progress and equipment ${width} ${theme}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await page.evaluate(preference => localStorage.setItem('studio:theme:guest', preference), theme);
    await page.reload();
    const steps = page.locator('.practice-path');
    await expect(steps).toContainText('Початок');
    await expect(steps).toContainText('Практика');
    await expect(steps).toContainText('Впевненість');
    await expect(page.locator('.progress-line')).toHaveCount(0);
    const equipment = page.locator('.equipment-list');
    await expect(equipment.locator('svg')).toHaveCount(3);
    for (const label of ['Килимок', 'Паралетси', 'Блоки для йоги']) await expect(equipment).toContainText(label);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await (await headerItem(page, page.getByRole('link', { name: 'EN', exact: true }))).click();
    await expect(page.locator('.practice-path')).toContainText('Confidence');
  });
}
