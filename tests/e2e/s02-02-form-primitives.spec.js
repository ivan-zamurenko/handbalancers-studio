import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));

function renderFixture() {
  const source = String.raw`
from jinja2 import Environment, FileSystemLoader

environment = Environment(loader=FileSystemLoader("server/templates"), autoescape=True)
template = environment.from_string("""<!doctype html>
{% from "shared/forms.html" import error_summary, form_field, button, pending_form, dialog %}
<html lang="en"><body>
  {{ error_summary([{"field_id": "email", "message": "Email is invalid"}], title="Check your email") }}
  {% call pending_form("/submit") %}
    {{ form_field("email", "Email", id="email", type="email", error="Email is invalid", hint="Used only for account access.") }}
    {{ button("Save", type="submit", kind="primary", pending_label="Submitting") }}
  {% endcall %}
  <button id="dialog-trigger" type="button" data-dialog-open="confirm-dialog">Open dialog</button>
  {% call dialog("confirm-dialog", "Confirm action") %}
    <button type="button" data-dialog-close>Cancel</button>
    <button type="button" id="last-dialog-button">Continue</button>
  {% endcall %}
  <button id="outside-dialog">Outside</button>
</body></html>""")
print(template.render())
`;

  return execFileSync(
    'uv',
    ['run', '--locked', 'python', '-c', source],
    { cwd: root, encoding: 'utf8' },
  );
}

test.beforeEach(async ({ page }) => {
  await page.goto('/health/live');
  await page.setContent(renderFixture());
  // Use the same external assets as product pages under the real strict CSP.
  for (const name of ['tokens.css', 'base.css', 'components.css']) {
    await page.addStyleTag({ url: `/static/css/${name}` });
  }
  for (const name of ['forms.js', 'dialog.js']) {
    await page.addScriptTag({ url: `/static/js/components/${name}`, type: 'module' });
  }
});

test('label_focus associates the label and validation error with the field', async ({ page }) => {
  const email = page.getByRole('textbox', { name: 'Email' });
  await page.locator('label[for="email"]').click();
  await expect(email).toBeFocused();
  await expect(email).toHaveAttribute('aria-describedby', 'email-hint email-error');
  await expect(page.locator('#email-hint')).toHaveText('Used only for account access.');
  await expect(page.locator('#email-error')).toHaveText('Email is invalid');
  await expect(page.locator('.error-summary')).toHaveAttribute('role', 'alert');
  await expect(page.locator('.error-summary a')).toHaveAttribute('href', '#email');
});

test('dialog_keyboard traps focus, closes on Escape, and restores the trigger', async ({ page }) => {
  const trigger = page.getByRole('button', { name: 'Open dialog' });
  const dialog = page.getByRole('dialog', { name: 'Confirm action' });
  const close = dialog.getByRole('button', { name: 'Close' });
  const last = page.getByRole('button', { name: 'Continue' });

  await trigger.click();
  await expect(dialog).toBeVisible();
  await last.focus();
  await page.keyboard.press('Tab');
  await expect(close).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(last).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test('submit_pending blocks repeats while pending and clears pending after failure', async ({ page }) => {
  let requestCount = 0;
  let releaseFirstRequest;
  const firstRequest = new Promise(resolveRequest => {
    releaseFirstRequest = resolveRequest;
  });

  await page.route('**/submit', async route => {
    requestCount += 1;
    if (requestCount === 1) await firstRequest;
    await route.fulfill({ status: 503, body: 'temporarily unavailable' });
  });

  const form = page.locator('form');
  const submit = form.locator('button[type="submit"]');
  await submit.click();
  await expect(submit).toBeDisabled();
  await expect(submit).toHaveText('Submitting');
  await form.evaluate(element => element.requestSubmit());
  expect(requestCount).toBe(1);

  releaseFirstRequest();
  await expect(submit).toBeEnabled();
  await expect(submit).toHaveText('Save');
  await expect(form).not.toHaveAttribute('aria-busy');
  await expect(form.locator('[data-form-feedback]')).toHaveText('Could not submit. Please try again.');

  await submit.click();
  await expect.poll(() => requestCount).toBe(2);
  await expect(submit).toBeEnabled();
});

test('primitives remain within narrow and wide viewports in both themes', async ({ page }) => {
  for (const width of [390, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ['light', 'dark']) {
      await page.locator('html').evaluate((element, value) => element.dataset.theme = value, theme);
      await expect(page.getByRole('textbox', { name: 'Email' })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth))
        .toBeLessThanOrEqual(width);
    }
  }
});
