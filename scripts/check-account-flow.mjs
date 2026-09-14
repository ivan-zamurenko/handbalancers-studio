// Local-only integration: verification mail stays on disk; Stripe entitlement is a test fixture.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { chromium, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

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
try {
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
  assert.equal(await page.locator('.trial-caption').filter({ hasText: '7 днів' }).count(), 2);
  await page.locator('[data-plan="plus"]').click();
  await page.locator('[data-plan-continue]').click();
  await page.waitForURL('**/register');
  await page.locator('#first-name').fill('Олена');
  await page.locator('#last-name').fill('Тест');
  await page.locator('#account-email').fill(email);
  await page.locator('#account-password').fill(password);
  await page.locator('#email-register-form button[type=submit]').click();
  await expect(page.locator('#email-code')).toBeVisible();
  assert.equal((await session()).user, null, 'No account until email is verified');
  const code = execFileSync(
    '.local-tools/python/bin/python',
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
    '.local-tools/python/bin/python',
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
  await expect(page.locator('.header-account')).toHaveText('Логін');
  console.log(
    'Verified registration, plan ordering, login, inline profile edit, inactive gate, real session minutes, next planned session and responsive accessible dashboard passed. Stripe entitlement was a local test fixture.',
  );
} finally {
  await browser.close();
}
