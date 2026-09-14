// Local browser checks; session fixtures never create accounts or subscriptions.
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const base = 'http://127.0.0.1:8000';
const output = '.local-tools/visual/footer';
const browser = await chromium.launch({ channel: 'chrome' });
const context = await browser.newContext({ reducedMotion: 'reduce' });
const page = await context.newPage();
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const routes = [
  '/',
  '/onboarding',
  '/plans',
  '/login',
  '/register',
  '/checkout',
  '/privacy',
  '/terms',
];

try {
  await mkdir(output, { recursive: true });
  await page.goto(base);
  const session = await page.evaluate(() =>
    fetch('/api/session').then((response) => response.json()),
  );
  assert.equal(session.local_preview, true, 'Only run on the local preview');
  let currentRoute = '/';
  await page.route('**/api/session', (route) =>
    route.fulfill({
      json: {
        ...session,
        selected_plan: 'plus',
        onboarding: {
          schema_version: 2,
          goals: ['mobility'],
          experience: 'beginner',
          minutes: 60,
          minutes_plus: false,
          days: [0, 2, 4],
          timezone: 'Europe/Kyiv',
          locale: 'uk',
        },
        user:
          currentRoute === '/checkout'
            ? {
                id: 'footer-preview',
                first_name: 'Preview',
                last_name: 'Test',
                name: 'Preview Test',
                is_demo: true,
              }
            : null,
        subscription: null,
      },
    }),
  );
  for (const route of routes) {
    const heights = new Map();
    const headerless = ['/login', '/register'].includes(route);
    const languageRegion = headerless ? '#footer' : '#shell';
    currentRoute = route;
    await page.goto(base + route);
    await expect(page.locator('#footer .footer-inner')).toBeVisible();
    assert.equal(new URL(page.url()).pathname, route);
    for (const language of ['uk', 'en']) {
      await page.locator(`${languageRegion} [data-language="${language}"]`).click();
      await expect(page.locator('main')).toHaveAttribute('aria-busy', 'false');
      await expect(page.locator(`${languageRegion} [data-language="${language}"]`)).toBeFocused();
      for (const width of [320, 390, 768, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        const footer = page.locator('#footer');
        await expect(footer.locator('.footer-brand .brand-mark')).toHaveText('h.');
        await expect(footer.locator('.footer-copyright')).toHaveText(
          `© ${new Date().getFullYear()} Handbalancer’s Studio`,
        );
        await expect(footer.locator('.footer-legal a')).toHaveCount(2);
        for (const path of ['/privacy', '/terms']) {
          await expect(footer.locator(`a[href="${path}"]`)).toBeVisible();
        }
        await expect(footer.locator('button:disabled')).toHaveCount(1);
        await expect(footer.getByRole('button', { name: 'X', exact: true })).toBeDisabled();
        await expect(footer.locator('.footer-socials a')).toHaveCount(2);
        for (const [name, href] of [
          ['Instagram - @ivan.zamurenko', 'https://www.instagram.com/ivan.zamurenko/'],
          ['YouTube - Handbalancer’s Notes', 'https://www.youtube.com/@HandbalancersNotes'],
        ]) {
          const link = footer.getByRole('link', { name, exact: true });
          await expect(link).toHaveAttribute('href', href);
          await expect(link).toHaveAttribute('target', '_blank');
          await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
        }
        await expect(footer.getByRole('button', { name: 'Facebook' })).toHaveCount(0);
        await expect(footer.locator('.footer-social svg')).toHaveCount(3);
        const bounds = await footer.boundingBox();
        if (language === 'uk') heights.set(width, bounds.height);
        else
          assert.ok(
            Math.abs(bounds.height - heights.get(width)) <= 1,
            `Stable UA/EN footer height at ${width}px`,
          );
        assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= width);
        assert.equal(await footer.evaluate((node) => node.scrollWidth > node.clientWidth), false);
        const brand = await footer.locator('.footer-brand').boundingBox();
        const info = await footer.locator('.footer-info').boundingBox();
        const socials = await footer.locator('.footer-socials').boundingBox();
        await expect(page.locator('.language-switch')).toHaveCount(1);
        await expect(footer.locator('.language-switch')).toHaveCount(headerless ? 1 : 0);
        if (headerless) {
          const languages = await footer.locator('.language-switch').boundingBox();
          assert.ok(languages.y + languages.height < socials.y, 'Languages above social icons');
          assert.ok(
            Math.abs(languages.x + languages.width / 2 - socials.x - socials.width / 2) <= 1,
            'Language switch centered above socials',
          );
        }
        await expect(footer.locator('.footer-social-youtube')).toHaveCSS(
          'background-color',
          'rgb(255, 0, 0)',
        );
        assert.match(
          await footer
            .locator('.footer-social-instagram')
            .evaluate((node) => getComputedStyle(node).backgroundImage),
          /gradient/,
        );
        if (width === 1440) {
          assert.ok(brand.x + brand.width < info.x);
          assert.ok(info.x + info.width < socials.x);
        }
        if (route === '/login') {
          const audit = await new AxeBuilder({ page })
            .include('#footer')
            .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
            .analyze();
          assert.deepEqual(
            audit.violations.map((item) => item.id),
            [],
          );
          await footer.screenshot({
            path: `${output}/${language}-${width}.png`,
            animations: 'disabled',
          });
        }
      }
    }
  }
  await page.locator('#footer a[href="/privacy"]').click();
  await expect(page).toHaveURL(`${base}/privacy`);
  await page.locator('#footer a[href="/terms"]').click();
  await expect(page).toHaveURL(`${base}/terms`);
  await page.locator('#footer .footer-brand').click();
  await expect(page).toHaveURL(`${base}/`);
  await expect(page.locator('.final-cta .cta-mark')).toHaveCount(0);
  await expect(page.locator('.final-cta h2')).toBeVisible();
  await expect(page.locator('.final-cta .intro')).toBeVisible();
  await page.locator('.final-cta a[href="/onboarding"]').click();
  await expect(page).toHaveURL(`${base}/onboarding`);
  await expect(page.locator('#onboarding-form')).toBeVisible();
  assert.deepEqual(errors, []);
  console.log(
    'Footer passed: 8 routes × 2 languages × 4 widths, 8 axe audits and working internal links.',
  );
} finally {
  await browser.close();
}
