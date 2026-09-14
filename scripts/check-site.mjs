// Runs against the isolated local preview; never point this at a public service.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const base = 'http://127.0.0.1:8000';
const output = new URL('../.local-tools/verification/site/', import.meta.url);
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const errors = [];
page.on('pageerror', (error) => errors.push(error.message));
const report = { checks: [], accessibility: [] };
const check = (message) => report.checks.push(message);
async function audit(label) {
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  report.accessibility.push({
    page: label,
    violations: result.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => n.target),
    })),
  });
}
async function screenshot(name) {
  await page.evaluate(async () => {
    if (document.activeElement?.matches('.skip-link')) document.activeElement.blur();
    await Promise.all(
      [...document.images].map(async (image) => {
        image.loading = 'eager';
        await image.decode().catch(() => {});
      }),
    );
  });
  await page.screenshot({ path: new URL(`${name}.png`, output).pathname, fullPage: true });
}
async function choose(id) {
  const input = page.locator(id);
  await expect(input).toBeEnabled();
  if (!(await input.isChecked())) {
    await input.focus();
    await input.press('Space');
  }
  assert.equal(await page.locator(id).isChecked(), true);
}
async function cardStyles() {
  return page.locator('.plan-card').evaluateAll((cards) =>
    cards.map((card) => {
      const style = getComputedStyle(card);
      const transformScale = new DOMMatrixReadOnly(style.transform).a;
      return {
        background: style.backgroundColor,
        border: style.borderColor,
        shadow: style.boxShadow,
        scale: transformScale * (style.scale === 'none' ? 1 : Number.parseFloat(style.scale)),
      };
    }),
  );
}
async function next() {
  await page.locator('#onboarding-form button[type="submit"]').click();
}
try {
  await page.goto(base);
  await page.locator('.hero').waitFor();
  assert.equal(await page.locator('html').getAttribute('lang'), 'uk');
  const session = await page.evaluate(async () => (await fetch('/api/session')).json());
  assert.equal(session.local_preview, true, 'Refuse to test outside local preview');
  assert.equal(session.user, null);
  check('Ukrainian default; isolated anonymous session');
  const heroType = await page.locator('.hero h1 > span').evaluateAll((nodes) =>
    nodes.map((node) => {
      const style = getComputedStyle(node);
      return [style.fontFamily, style.fontSize, style.fontWeight];
    }),
  );
  assert.ok(heroType.length > 1);
  assert.ok(
    heroType.every((style) => JSON.stringify(style) === JSON.stringify(heroType[0])),
    'Hero lines use identical typography',
  );
  assert.equal(
    await page.locator('.hero-small, .hero-scroll, #coaching, .direction-top .index').count(),
    0,
  );
  assert.equal(await page.locator('.change-card').count(), 3);
  assert.equal(await page.locator('.change-before .change-list li').count(), 5);
  assert.equal(await page.locator('.change-actions > li').count(), 3);
  assert.equal(await page.locator('.change-after .change-list li').count(), 5);
  await page.locator('.change-after').scrollIntoViewIfNeeded();
  await expect(page.locator('.change-after')).toHaveClass(/is-visible/);
  await expect(page.locator('#needs-heading')).toHaveText('Від «немає сил» до «я це зробив!»');
  check(
    'Three stages show problems, product support and desired outcomes; arrow animates on entry',
  );

  const direction = page.locator('.direction-card').first();
  await direction.hover();
  await expect
    .poll(() =>
      direction.evaluate((node) => new DOMMatrixReadOnly(getComputedStyle(node).transform).a),
    )
    .toBeGreaterThan(1);
  await page.mouse.move(0, 0);
  await expect
    .poll(() =>
      direction.evaluate((node) => new DOMMatrixReadOnly(getComputedStyle(node).transform).a),
    )
    .toBe(1);
  check(
    'Consistent hero type; simple problem/solution section; direction hover; duplicated blocks removed',
  );

  await audit('landing-uk');
  const alignment = await page.locator('#directions .section-heading').evaluate((element) => {
    const center = (node) => {
      const box = node.getBoundingClientRect();
      return box.x + box.width / 2;
    };
    return Math.abs(center(element.querySelector('h2')) - center(element.querySelector('.intro')));
  });
  assert.ok(alignment < 2, 'Direction heading and description share a center axis');
  check('Section heading and description aligned on one axis');
  await screenshot('landing-desktop');
  await page
    .locator('#philosophy')
    .screenshot({ path: new URL('transformation-desktop.png', output).pathname });
  await page
    .locator('#directions')
    .screenshot({ path: new URL('directions-desktop.png', output).pathname });
  const tariffsLink = page.locator('#main-navigation a[href="/#plans"]');
  await expect(page.locator('.header-account')).toHaveText('Логін');
  assert.equal(await page.locator('.comparison, .plan-note').count(), 0);
  await tariffsLink.hover();
  await expect
    .poll(() =>
      tariffsLink.evaluate(
        (node) => new DOMMatrixReadOnly(getComputedStyle(node, '::after').transform).a,
      ),
    )
    .toBe(1);
  const underlineOrigin = await tariffsLink.evaluate((node) => {
    const style = getComputedStyle(node, '::after');
    return Math.abs(parseFloat(style.transformOrigin) - parseFloat(style.width) / 2);
  });
  assert.ok(underlineOrigin < 1, 'Navigation underline expands from its center');
  check('Login label, clean pricing and center-out navigation underline');
  await tariffsLink.click();
  await page.waitForURL((url) => url.pathname === '/' && url.hash === '#plans');
  await expect
    .poll(() =>
      page.locator('#plans').evaluate((element) => {
        const bounds = element.getBoundingClientRect();
        return bounds.top >= 0 && bounds.top < innerHeight / 2;
      }),
    )
    .toBe(true);
  check('Header tariffs link scrolls to landing pricing section');
  const neutralCards = await cardStyles();
  assert.equal(neutralCards.length, 4);
  assert.ok(neutralCards[1].scale > 1, 'Recommended Plus is initially selected');
  await expect(page.locator('[data-plan="plus"]')).toHaveAttribute('aria-pressed', 'true');
  for (const index of [0, 2, 3]) {
    assert.equal(neutralCards[index].scale, 1);
    assert.deepEqual(neutralCards[index], neutralCards[0], 'Other tariffs remain neutral');
  }
  assert.equal(
    await page
      .locator('body')
      .innerText()
      .then((text) => /[—–]/.test(text)),
    false,
  );
  check('Recommended Plus selected by default; ordinary hyphens in visible copy');
  await page.locator('[data-plan="essential"]').click();
  await page.mouse.move(0, 0);
  await expect.poll(async () => (await cardStyles())[0].scale).toBeGreaterThan(1);
  assert.equal(new URL(page.url()).pathname, '/');
  await page.reload();
  await expect(page.locator('[data-plan="essential"]')).toHaveAttribute('aria-pressed', 'true');
  check('Explicit plan selection survives reload instead of reverting to Plus');
  await page.locator('[data-plan="plus"]').click();
  await page.mouse.move(0, 0);
  await expect.poll(async () => (await cardStyles())[0].scale).toBe(1);
  await expect.poll(async () => (await cardStyles())[1].scale).toBeGreaterThan(1);
  const selectedCards = await cardStyles();
  assert.equal(selectedCards[2].scale, 1);
  assert.equal(selectedCards[3].scale, 1);
  check('Only selected tariff zooms; selection is separate from continuing');
  await page.goto(`${base}/dashboard`);
  await page.waitForURL('**/login');
  await expect(page.locator('#login-form')).toBeVisible();
  await expect(page.locator('.dashboard')).toHaveCount(0);
  await page.goto(`${base}/onboarding`);
  await next();
  await page.getByRole('alert').waitFor();
  check('Protected route and empty questionnaire validation');
  await choose('#goal-handstand');
  await choose('#goal-mobility');
  assert.equal(await page.locator('#primary-goal').count(), 0, 'Goals have equal priority');
  await page.reload();
  await page.locator('#goal-mobility').waitFor();
  assert.equal(await page.locator('#goal-mobility').isChecked(), true);
  check('Multiple goals and draft survive reload');
  await audit('onboarding-goals-uk');
  await screenshot('onboarding-desktop');
  await next();
  await choose('#experience-beginner');
  await next();
  await page.locator('#minutes-30').waitFor();
  assert.deepEqual(
    await page
      .locator('input[name=minutes]')
      .evaluateAll((inputs) => inputs.map((input) => input.value)),
    ['30', '45', '60', '90'],
  );
  await choose('#minutes-90');
  await screenshot('onboarding-time');
  await audit('onboarding-time-uk');
  await next();
  await choose('#day-0');
  await choose('#day-3');
  await choose('#day-5');
  await expect(page.locator('#day-1')).toBeDisabled();
  assert.equal(await page.locator('input[name=days]:checked').count(), 3);
  await page.locator('#day-5').focus();
  await page.locator('#day-5').press('Space');
  await expect(page.locator('#day-1')).toBeEnabled();
  await choose('#day-5');
  check('Four duration choices; 90 minutes; at most three days with deselection available');
  await screenshot('onboarding-days');
  await audit('onboarding-days-uk');
  await next();
  await page.waitForURL('**/plans');
  await audit('plans-uk');
  await screenshot('plans-desktop');
  await page.locator('[data-plan="plus"]').click();
  await page.locator('[data-plan-continue]').click();
  await page.waitForURL('**/register');
  await expect(page.locator('#email-register-form')).toBeVisible();
  await audit('register-uk');
  // Local-only billing fixture; the public registration UI requires email verification.
  await page.evaluate(async () => {
    const state = await fetch('/api/session').then((r) => r.json());
    const response = await fetch('/api/preview/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf_token },
      body: JSON.stringify({ name: 'Studio Browser Test' }),
    });
    if (!response.ok) throw Error('Local billing fixture failed');
  });
  await page.reload();
  await page.waitForURL((url) => url.pathname === '/checkout');
  await audit('checkout-uk');
  await page.locator('[data-demo-pay]').click();
  await page.waitForURL('**/dashboard');
  await page.locator('.member-plan').waitFor();
  await page.reload();
  await page.locator('.member-plan').waitFor();
  const saved = await page.evaluate(async () => (await fetch('/api/session')).json());
  assert.deepEqual(saved.onboarding.goals, ['handstand', 'mobility']);
  assert.deepEqual(saved.onboarding.days, [0, 3, 5]);
  assert.equal(saved.onboarding.minutes, 90);
  assert.equal(saved.onboarding.minutes_plus, false);
  assert.equal(saved.onboarding.primary_goal, undefined);
  assert.equal(saved.onboarding.equipment, undefined);
  assert.equal(saved.subscription.plan_id, 'plus');
  assert.equal(saved.subscription.is_demo, true);
  assert.equal(saved.subscription.status, 'active');
  check('Onboarding → plan selection → local billing fixture → persisted dashboard');
  await audit('dashboard-uk');
  await screenshot('dashboard-desktop');
  await page.locator('[data-language="en"]').click();
  assert.equal(await page.locator('html').getAttribute('lang'), 'en');
  await audit('dashboard-en');
  check('English switch');
  await page.locator('.header-account[data-logout]').click();
  await page.waitForURL((url) => url.pathname === '/');
  const loggedOut = await page.evaluate(async () => (await fetch('/api/session')).json());
  assert.equal(loggedOut.user, null);
  assert.equal(loggedOut.onboarding, null);
  check('Logout clears browser access to profile');
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of ['/', '/plans', '/onboarding', '/privacy', '/terms']) {
      await page.goto(base + route);
      await page.locator('h1').waitFor();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      );
      assert.equal(overflow, false, `Horizontal overflow at ${width}px on ${route}`);
    }
  }
  check('No page overflow: 320 / 390 / 768 / 1440 px, five routes');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base);
  await page.locator('.hero').waitFor();
  await screenshot('landing-mobile');
  await page
    .locator('#philosophy')
    .screenshot({ path: new URL('transformation-mobile.png', output).pathname });
  await audit('landing-en-mobile');
  assert.equal(await page.locator('.change-card').count(), 3);
  await expect(page.locator('#needs-heading')).toHaveText('From “no energy” to “I did it!”');
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1),
    false,
  );
  await page.goto(`${base}/plans`);
  await page.locator('.plan-card').first().waitFor();
  await screenshot('plans-mobile');
  await audit('plans-en-mobile');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`${base}/onboarding`);
  await page.locator('#onboarding-form').waitFor();
  const movingElements = await page
    .locator('#onboarding-form, .onboarding-slide, .plan-card')
    .evaluateAll((elements) =>
      elements.map((element) => {
        const style = getComputedStyle(element);
        const seconds = (value) =>
          Math.max(
            ...value
              .split(',')
              .map((item) => Number.parseFloat(item) * (item.trim().endsWith('ms') ? 0.001 : 1)),
          );
        return {
          animation: seconds(style.animationDuration),
          transition: seconds(style.transitionDuration),
        };
      }),
    );
  assert.ok(
    movingElements.every((item) => item.animation <= 0.01 && item.transition <= 0.01),
    'Reduced motion avoids carousel animation',
  );
  await choose('#goal-handstand');
  await next();
  await page.locator('#experience-beginner').waitFor();
  assert.equal(
    await page.evaluate(() =>
      document.getAnimations().some((animation) => animation.playState === 'running'),
    ),
    false,
    'No running swipe/fade with reduced motion',
  );
  check('Reduced-motion preference respected, including carousel transitions');
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await choose('#experience-beginner');
  await next();
  await choose('#minutes-45');
  await expect
    .poll(() =>
      page.locator('.onboarding-slide h1').evaluate((node) => node.getBoundingClientRect().top),
    )
    .toBeGreaterThanOrEqual(0);
  await screenshot('onboarding-time-mobile');
  await next();
  await choose('#day-1');
  await choose('#day-3');
  await choose('#day-5');
  await screenshot('onboarding-days-mobile');
  await audit('onboarding-days-en-mobile');
  const calendarOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > innerWidth + 1,
  );
  assert.equal(calendarOverflow, false);
  check('Mobile carousel keeps new question visible; calendar fits at 390 px');
  // Restored radio state must win over an old 60+ draft at submission time.
  for (const restoreWithoutChange of [false, true]) {
    const recovery = await browser.newPage();
    try {
      await recovery.addInitScript(() => {
        localStorage.setItem(
          'hbs:onboarding:v1',
          JSON.stringify({
            document: {
              goals: ['handstand'],
              experience: 'beginner',
              minutes: 60,
              minutes_plus: true,
              days: [],
              locale: 'uk',
              timezone: 'Europe/Dublin',
            },
            dirty: true,
            owner: null,
          }),
        );
      });
      await recovery.goto(`${base}/onboarding`);
      await recovery.locator('button[type=submit]').click();
      await expect(recovery.locator('#experience-beginner')).toBeEnabled();
      await recovery.locator('button[type=submit]').click();
      await expect(recovery.locator('#minutes-90')).toBeEnabled();
      if (restoreWithoutChange) {
        await recovery.locator('#minutes-90').evaluate((input) => {
          input.checked = true;
        });
      } else {
        await recovery.locator('label:has(#minutes-90)').click();
      }
      await recovery.locator('button[type=submit]').click();
      await expect(recovery.locator('#day-0')).toBeEnabled();
      await recovery.locator('label:has(#day-0)').click();
      await recovery.locator('button[type=submit]').click();
      await recovery.waitForURL('**/plans');
      const recovered = await recovery.evaluate(() => fetch('/api/session').then((r) => r.json()));
      assert.equal(recovered.onboarding.minutes, 90);
      assert.equal(recovered.onboarding.minutes_plus, false);
    } finally {
      await recovery.close();
    }
  }
  check('90-minute selection survives legacy drafts and radio restoration without change events');
  assert.deepEqual(errors, [], 'No unhandled browser errors');
  check('No unhandled browser JavaScript errors');
  assert.equal(
    report.accessibility.flatMap((r) => r.violations).length,
    0,
    'Accessibility violations: see report',
  );
} catch (error) {
  report.failure = { message: error.message, url: page.url() };
  await screenshot('failure').catch(() => {});
  throw error;
} finally {
  await writeFile(new URL('browser-report.json', output), JSON.stringify(report, null, 2));
  await browser.close();
}
console.log(JSON.stringify(report, null, 2));
