// Local-only integration: verification mail stays on disk; Stripe entitlement is a test fixture.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { chromium, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// The isolated interpreter exists only on the development machine, so CI runners
// fall back to the platform python instead of failing on a missing path.
const isolatedPython = '.local-tools/python/bin/python';
const python = process.env.PYTHON_BIN || (existsSync(isolatedPython) ? isolatedPython : 'python3');

const email = `browser-flow-${randomBytes(8).toString('hex')}@example.invalid`;
const password = randomBytes(24).toString('base64url');
const browser = await chromium.launch({ channel: 'chrome' });
const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
const page = await context.newPage();
const base = 'http://127.0.0.1:8000';
const submit = () => page.locator('#onboarding-form button[type=submit]').click();
async function session() {
  return page.evaluate(() => fetch('/api/session').then((r) => r.json()));
}
async function auditAuth(name, verify = false) {
  const screenshots = '.local-tools/visual/login-current';
  await mkdir(screenshots, { recursive: true });
  for (const language of ['uk', 'en']) {
    await page.locator(`#footer [data-language="${language}"]`).click();
    await expect(page.locator('main')).toHaveAttribute('aria-busy', 'false');
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      const card = await page.locator('.login-card').boundingBox();
      const brand = await page.locator('.login-brand .brand').boundingBox();
      const section = await page.locator('.login-section').boundingBox();
      await expect(page.locator('.login-section')).toHaveCSS(
        'padding-top',
        width <= 480 ? '48px' : '80px',
      );
      await expect(page.locator('.site-header, .local-bar')).toHaveCount(0);
      await expect(page.locator('#footer .footer-inner')).toHaveCount(1);
      await expect(page.locator('main .language-switch')).toHaveCount(0);
      await expect(page.locator(`#footer [data-language="${language}"]`)).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      await expect(page.locator('.provider-logo')).toHaveCount(verify ? 0 : 2);
      assert.doesNotMatch(
        await page.locator('body').innerText(),
        /після його підключення|once connected/,
      );
      assert.ok(card.width <= 400, 'Login is no wider than 400px');
      for (const box of [card, brand]) {
        assert.ok(Math.abs(box.x + box.width / 2 - width / 2) <= 1, 'Centered login and logo');
      }
      if (name === 'login') {
        assert.ok(Math.abs(card.y + card.height / 2 - section.y - section.height / 2) <= 1);
      } else {
        const terms = await page.locator('.auth-legal-links a[href="/terms"]').boundingBox();
        const privacy = await page.locator('.auth-legal-links a[href="/privacy"]').boundingBox();
        assert.ok(Math.abs(terms.y - privacy.y) <= 1, 'Legal links share one line');
        assert.ok(terms.x >= 0 && privacy.x + privacy.width <= width, 'Legal links fit on screen');
        const completed = page.locator('.stepper .complete .step-indicator');
        await expect(completed).toHaveCount(2);
        for (const circle of await completed.all()) {
          await expect(circle).toHaveText('✓');
          await expect(circle).toHaveCSS('background-color', 'rgb(114, 201, 145)');
          await expect(circle).toHaveCSS('border-radius', '50%');
        }
        await expect(page.locator('.stepper li').nth(2)).toHaveAttribute('aria-current', 'step');
        await expect(page.locator('.stepper')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
        await expect(page.locator('.stepper')).toHaveCSS('border-top-width', '0px');
        await expect(page.locator('.stepper li:not(.complete) a')).toHaveCount(0);
        assert.doesNotMatch(
          await page.locator('main').innerText(),
          /Локальна перевірка|Local testing|приватній тестовій скриньці|private test inbox/,
        );
      }
      if (!verify) {
        const providers = await page.locator('.login-provider').all();
        assert.equal(providers.length, 3);
        const boxes = await Promise.all(providers.map((button) => button.boundingBox()));
        assert.ok(boxes.every((box) => Math.abs(box.y - boxes[0].y) <= 1));
        assert.ok(boxes.every((box) => box.width >= 44 && box.height >= 44));
        await expect(page.locator('.login-provider-pending')).toBeDisabled();
        await expect(page.locator('#account-email')).toHaveAttribute('type', 'email');
        await expect(page.locator('#account-password')).toHaveAttribute(
          'autocomplete',
          name === 'login' ? 'current-password' : 'new-password',
        );
      }
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),
        false,
      );
      const audit = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze();
      assert.deepEqual(
        audit.violations.map((item) => item.id),
        [],
      );
      await page.evaluate(() => {
        if (document.activeElement?.matches('.skip-link')) document.activeElement.blur();
      });
      await page.screenshot({
        path: `${screenshots}/${name}-${language}-${width}.png`,
        fullPage: true,
        animations: 'disabled',
      });
    }
  }
  await page.locator('#footer [data-language="uk"]').click();
  await expect(page.locator('main')).toHaveAttribute('aria-busy', 'false');
  await page.setViewportSize({ width: 1440, height: 1100 });
}
try {
  await page.goto(`${base}/login`);
  await auditAuth('login');
  const anonymousSession = await session();
  await page.route('**/api/session', (route) =>
    route.fulfill({
      json: { ...anonymousSession, providers: { google: true, apple: true } },
    }),
  );
  await page.goto(`${base}/login?auth_error=unavailable`);
  await expect(page.locator('.login-section [role="alert"]')).toBeVisible();
  for (const provider of ['google', 'apple']) {
    await expect(page.locator(`.login-providers a[href="/auth/${provider}/login"]`)).toBeVisible();
  }
  await expect(page.locator('.login-provider-pending')).toBeDisabled();
  await page.unroute('**/api/session');
  await page.goto(`${base}/login`);
  for (const provider of ['google', 'apple']) {
    if (!anonymousSession.providers[provider]) {
      const label = provider === 'google' ? 'Google' : 'Apple';
      await expect(page.locator(`.login-providers button[aria-label*="${label}"]`)).toBeDisabled();
    }
  }
  await page.locator('#footer [data-language="uk"]').click();
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.route('**/api/auth/login', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Login test rejection' } }),
  );
  await page.locator('#account-email').fill(email);
  await page.locator('#account-password').fill(password);
  const loginRequest = page.waitForRequest('**/api/auth/login');
  await page.locator('#login-form button[type=submit]').click();
  const request = await loginRequest;
  assert.equal(request.method(), 'POST');
  assert.ok(request.postDataJSON().email === email);
  assert.ok(request.postDataJSON().password === password);
  await expect(page.locator('.login-section [role="alert"]')).toBeVisible();
  await expect(page.locator('#login-form button[type=submit]')).toBeEnabled();
  await page.unroute('**/api/auth/login');
  if (process.argv.includes('--login-only')) {
    await browser.close();
    console.log(
      'Login: centered layout at four widths in UA/EN, eight axe audits, provider states and OAuth errors passed.',
    );
    process.exit(0);
  }
  await page.goto(`${base}/onboarding`);
  await page.locator('label:has(#goal-mobility)').click();
  await submit();
  await page.locator('label:has(#experience-beginner)').click();
  await submit();
  await page.locator('label:has(#minutes-60)').click();
  await submit();
  for (const i of [0, 2, 4]) await page.locator(`label:has(#day-${i})`).click();
  await submit();
  await page.waitForURL('**/plans');
  await expect(page.locator('.stepper li').nth(1)).toHaveAttribute('aria-current', 'step');
  await expect(page.locator('.plans-page > .section-heading .chips')).toHaveCount(0);
  await expect(page.locator('.stepper')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  const editGoals = page.locator('.stepper a[href="/onboarding"]');
  await editGoals.focus();
  await editGoals.press('Enter');
  await page.waitForURL('**/onboarding');
  await expect(page.locator('#goal-mobility')).toBeChecked();
  await page.locator('label:has(#goal-handstand)').click();
  await submit();
  await expect(page.locator('#experience-beginner')).toBeChecked();
  await submit();
  await expect(page.locator('#minutes-60')).toBeChecked();
  await submit();
  for (const i of [0, 2, 4]) await expect(page.locator(`#day-${i}`)).toBeChecked();
  await submit();
  await page.waitForURL('**/plans');
  assert.deepEqual(new Set((await session()).onboarding.goals), new Set(['mobility', 'handstand']));
  assert.equal(await page.locator('.trial-caption').filter({ hasText: '7 днів' }).count(), 2);
  await page.locator('[data-plan="plus"]').click();
  await page.locator('[data-plan-continue]').click();
  await page.waitForURL('**/register');
  await auditAuth('register');
  await page.locator('#first-name').fill('Олена');
  await page.locator('#last-name').fill('Тест');
  await page.locator('#account-email').fill(email);
  await page.locator('#account-password').fill(password);
  await page.locator('#email-register-form button[type=submit]').click();
  await expect(page.locator('#email-code')).toBeVisible();
  await auditAuth('verify', true);
  await page.locator('.stepper a[href="/plans"]').click();
  await page.waitForURL('**/plans');
  await page.locator('[data-plan="essential"]').click();
  await page.locator('[data-plan-continue]').click();
  await page.waitForURL('**/register');
  await expect(page.locator('#email-code')).toBeVisible();
  assert.equal((await session()).selected_plan, 'essential');
  await page.locator('.stepper a[href="/plans"]').click();
  await page.locator('[data-plan="plus"]').click();
  await page.locator('[data-plan-continue]').click();
  await page.waitForURL('**/register');
  await expect(page.locator('#email-code')).toBeVisible();
  assert.equal((await session()).user, null, 'No account until email is verified');
  const code = execFileSync(
    python,
    [
      '-c',
      `
from pathlib import Path
from email import policy
from email.parser import BytesParser
import re,sys
for p in Path('.local-tools/mail-inbox').glob('*.eml'):
 m=BytesParser(policy=policy.default).parsebytes(p.read_bytes())
 if m['To']==sys.argv[1]:
  print(re.search(r'\\b[0-9]{6}\\b',m.get_body(preferencelist=('plain',)).get_content()).group())
  break
else: raise SystemExit(1)
`,
      email,
    ],
    { encoding: 'utf8' },
  ).trim();
  await page.locator('#email-code').fill(code);
  await page.locator('#verify-form button[type=submit]').click();
  await page.waitForURL('**/checkout');
  await expect(page.locator('.trial-terms')).toContainText('автоматично');
  await page.locator('.stepper a[href="/register?edit=profile"]').click();
  await page.waitForURL('**/register?edit=profile');
  await page.reload();
  await expect(page.locator('#first-name')).toHaveValue('Олена');
  await expect(page.locator('#last-name')).toHaveValue('Тест');
  await page.locator('#first-name').fill('Олена Марія');
  await page.locator('#profile-form button[type=submit]').click();
  await page.waitForURL('**/checkout');
  assert.equal((await session()).user.first_name, 'Олена Марія');
  assert.equal((await session()).selected_plan, 'plus');
  if (process.argv.includes('--auth-only')) {
    await expect(page.locator('.site-header')).toBeVisible();
    const registeredUser = (await session()).user.id;
    await page.locator('.header-account[data-logout]').click();
    await page.goto(`${base}/login`);
    await page.locator('#account-email').fill(email);
    await page.locator('#account-password').fill(password);
    await page.locator('#login-form button[type=submit]').click();
    await expect(page.locator('.header-account[data-logout]')).toBeVisible();
    assert.equal((await session()).user.id, registeredUser);
    await browser.close();
    console.log(
      'Auth: 24 responsive UA/EN axe audits, provider icons, completed steps, email verification and real password login passed.',
    );
    process.exit(0);
  }
  await page.locator('.checkout-links a[href="/dashboard"]').click();
  await page.waitForURL('**/dashboard');
  await expect(page.locator('.subscription-dot')).toHaveClass(/status-inactive/);
  await page.locator('.profile-editor summary').click();
  await page.locator('#first-name').fill('Олена Марія');
  await page.locator('#profile-form button[type=submit]').click();
  await expect(page.locator('.greeting')).toContainText('Олена Марія');
  const owner = (await session()).user.id;
  const blocked = await page.evaluate(async () => {
    const s = await fetch('/api/session').then((r) => r.json());
    return (
      await fetch('/api/training-sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': s.csrf_token },
        body: JSON.stringify({ minutes: 60, goal: 'mobility' }),
      })
    ).status;
  });
  assert.equal(blocked, 402);
  // Create a clearly simulated entitlement only for this randomly named local test account.
  execFileSync(
    python,
    [
      '-c',
      `
import sys,uuid
from datetime import timedelta
sys.path.insert(0,'server')
from studio.settings import Settings
from studio.db import make_engine,make_session_factory
from studio.models import User,Subscription,TrainingSession,utcnow
settings=Settings()
assert settings.preview_enabled
with make_session_factory(make_engine(settings))() as db:
 u=db.get(User,uuid.UUID(sys.argv[1])); assert u.email==sys.argv[2] and u.email.startswith('browser-flow-') and u.email.endswith('@example.invalid')
 db.add(Subscription(user_id=u.id,plan_id='plus',status='trialing',is_demo=True,current_period_end=utcnow()+timedelta(days=7)))
 db.add(TrainingSession(user_id=u.id,title='Розтяжка',goal='mobility',status='planned',scheduled_at=utcnow()+timedelta(days=1)))
 db.commit()
`,
      owner,
      email,
    ],
    { stdio: 'pipe' },
  );
  await page.reload();
  await expect(page.locator('.subscription-dot')).toHaveClass(/status-active/);
  await page.locator('.training-editor summary').click();
  await page.locator('#training-minutes').fill('60');
  await page.locator('#training-form button[type=submit]').click();
  await expect(page.locator('.weekly-completed')).toContainText('60 / 180');
  await expect(page.locator('.progress-ring strong')).toHaveText('33.3%');
  await expect(page.locator('.next-session')).toContainText('Розтяжка');
  await expect(page.locator('.dashboard-days .scheduled').first()).toHaveCSS(
    'background-color',
    'rgb(25, 37, 28)',
  );
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1100 });
    assert.equal(
      await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),
      false,
    );
    const audit = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    assert.equal(
      audit.violations.length,
      0,
      JSON.stringify(
        audit.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })),
      ),
    );
    await page.evaluate(() => document.activeElement?.blur());
    await page.screenshot({
      path: `.local-tools/verification/site/member-dashboard-${width}.png`,
      fullPage: true,
    });
  }
  await page.locator('#menu-toggle').click();
  await expect(page.locator('.mobile-account[data-logout]')).toHaveText('Вийти');
  await expect(page.locator('main [data-logout]')).toHaveCount(0);
  await page.locator('.mobile-account[data-logout]').click();
  await page.waitForURL((url) => url.pathname === '/');
  assert.equal((await session()).user, null);
  await page.goto(`${base}/dashboard`);
  await page.waitForURL('**/login');
  await expect(page.locator('#login-form')).toBeVisible();
  await page.goto(`${base}/login`);
  await page.locator('#account-email').fill(email);
  await page.locator('#account-password').fill(password);
  await page.locator('#login-form button[type=submit]').click();
  await page.waitForURL('**/dashboard');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect(page.locator('.header-account[data-logout]')).toHaveText('Вийти');
  await expect(page.locator('main [data-logout]')).toHaveCount(0);
  await page.locator('.goals-card a').click();
  await expect(page.locator('#goal-mobility')).toBeChecked();
  await page.clock.install();
  await page.goto(`${base}/dashboard`);
  await expect(page.locator('.header-account[data-logout]')).toBeVisible();
  await context.clearCookies();
  await page.clock.runFor(60000);
  await page.waitForURL('**/login');
  await expect(page.locator('#login-form')).toBeVisible();
  await expect(page.locator('.site-header')).toHaveCount(0);
  console.log(
    'Verified registration, plan ordering, login, inline profile edit, inactive gate, real session minutes, next planned session and responsive accessible dashboard passed. Stripe entitlement was a local test fixture.',
  );
} finally {
  await browser.close();
}
