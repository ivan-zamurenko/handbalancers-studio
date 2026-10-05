import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { resolve, extname, sep } from 'node:path';
import { chromium, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { freshData, STORAGE_KEY } from './data.js';

const root = fileURLToPath(new URL('.', import.meta.url));
const args = process.argv.slice(2);
const variantArg = args.includes('--variant') ? args[args.indexOf('--variant') + 1] : null;
const ids = variantArg
  ? [variantArg]
  : Array.from({ length: 10 }, (_, index) => String(index + 1).padStart(2, '0'));
const matrix = args.includes('--matrix');
const types = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.webp': 'image/webp',
  '.png': 'image/png',
  '.json': 'application/json',
};
const server = createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
  const target = resolve(root, `.${pathname === '/' ? '/index.html' : pathname}`);
  if (!target.startsWith(root.endsWith(sep) ? root : root + sep)) {
    response.writeHead(403).end();
    return;
  }
  try {
    response
      .writeHead(200, { 'Content-Type': types[extname(target)] || 'application/octet-stream' })
      .end(await readFile(target));
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise((done) => server.listen(0, '127.0.0.1', done));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const report = {
  scope: 'Synthetic coach-admin preview only; no production API, auth or database',
  startedAt: new Date().toISOString(),
  layouts: [],
  accessibility: [],
  behaviors: [],
  errors: [],
  requests: [],
  failedResponses: [],
  artifacts: {},
  controls: [],
};
await mkdir(new URL('screenshots/', import.meta.url), { recursive: true });

async function newPage(width, locale = 'uk', theme = 'dark') {
  const context = await browser.newContext({
    viewport: { width, height: width >= 768 ? 1000 : 844 },
    reducedMotion: 'reduce',
  });
  await context.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === base && !url.pathname.startsWith('/api/')) return route.continue();
    report.requests.push(url.pathname);
    return route.abort();
  });
  await context.addInitScript(
    ({ key, data, locale, theme }) => {
      if (!localStorage.getItem(key))
        localStorage.setItem(key, JSON.stringify({ schema: 1, data, locale, theme, drafts: {} }));
    },
    { key: STORAGE_KEY, data: freshData(), locale, theme },
  );
  const page = await context.newPage();
  page.on('pageerror', (error) => report.errors.push(error.message));
  page.on('response', (response) => {
    if (response.status() >= 400)
      report.failedResponses.push({
        path: new URL(response.url()).pathname,
        status: response.status(),
      });
  });
  return { context, page };
}

async function geometry(page, label) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map((image) => image.decode().catch(() => {})));
  });
  const result = await page.evaluate(() => ({
    pageOverflow: document.documentElement.scrollWidth > innerWidth + 1,
    brokenImages: [...document.images]
      .filter((image) => !image.complete || !image.naturalWidth)
      .map((image) => image.getAttribute('src')),
    outsideControls: [...document.querySelectorAll('button,input,select,textarea')]
      .filter((element) => {
        if (element.closest('.table-scroll')) return false;
        const rect = element.getBoundingClientRect();
        return rect.width && rect.height && (rect.left < -1 || rect.right > innerWidth + 1);
      })
      .map((element) => element.id || element.dataset.action || element.name),
  }));
  assert.deepEqual(result, { pageOverflow: false, brokenImages: [], outsideControls: [] }, label);
}

async function accessibility(page, label) {
  const audit = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  assert.deepEqual(
    audit.violations.map((issue) => ({
      id: issue.id,
      targets: issue.nodes.map((node) => node.target),
    })),
    [],
    label,
  );
  report.accessibility.push({ label, result: 'pass' });
}

async function prepareCapture(page) {
  await page.evaluate(() => {
    document.activeElement?.blur();
    window.scrollTo(0, 0);
  });
  await expect(page.locator('.skip-link')).not.toBeFocused();
  await expect(page.locator('#toast')).not.toBeVisible();
}

async function controlContrast(control) {
  return control.evaluate((element) => {
    const parse = (color) => color.match(/[\d.]+/g).map(Number);
    const layers = [];
    for (let parent = element; parent; parent = parent.parentElement)
      layers.unshift(parse(getComputedStyle(parent).backgroundColor));
    let background = [255, 255, 255];
    for (const layer of layers) {
      const alpha = layer[3] ?? 1;
      background = background.map((value, index) => layer[index] * alpha + value * (1 - alpha));
    }
    const luminance = (channels) =>
      channels.slice(0, 3).reduce((total, value, index) => {
        const channel = value / 255;
        const linear = channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
        return total + linear * [0.2126, 0.7152, 0.0722][index];
      }, 0);
    const style = getComputedStyle(element);
    const values = [luminance(parse(style.color)), luminance(background)].sort(
      (first, second) => second - first,
    );
    return { ratio: (values[0] + 0.05) / (values[1] + 0.05), color: style.color, background };
  });
}

async function controlStates() {
  const selectors = [
    '.button.primary:enabled',
    '.button.quiet',
    '.save-note',
    '.heading-tools .icon-button',
    '.nav-item.active',
    '.nav-item:not(.active)',
    '.person-row.selected',
    '.person-row:not(.selected)',
    '.segmented button[aria-pressed=true]',
    '.segmented button[aria-pressed=false]',
    '.tabs button[aria-selected=true]',
    '.tabs button[aria-selected=false]',
    '.video-link',
    '.range-control select',
    '#coach-note',
    '#client-search',
  ];
  for (const theme of ['dark', 'light']) {
    for (const locale of ['uk', 'en']) {
      for (const width of [1440, 390]) {
        const { context, page } = await newPage(width, locale, theme);
        await page.goto(`${base}/?variant=02`);
        for (const selector of selectors) {
          const control = page.locator(selector).first();
          for (const interaction of ['default', 'hover', 'active', 'focus']) {
            await page.mouse.move(0, 0);
            await control.evaluate((element) => element.blur());
            if (interaction === 'hover' || interaction === 'active') await control.hover();
            if (interaction === 'active') await page.mouse.down();
            if (interaction === 'focus') {
              await page.keyboard.press('Tab');
              await control.focus();
              await expect(control).toBeFocused();
              await expect(control).toHaveCSS('outline-style', 'solid');
            }
            const contrast = await controlContrast(control);
            if (interaction === 'active') {
              await page.mouse.move(0, 0);
              await page.mouse.up();
              await page.keyboard.press('Escape');
            }
            assert.ok(
              contrast.ratio >= 4.5,
              JSON.stringify({ selector, interaction, theme, locale, width, ...contrast }),
            );
            report.controls.push({
              selector,
              interaction,
              theme,
              locale,
              width,
              ratio: contrast.ratio,
            });
          }
          if (width === 390 && !selector.startsWith('.nav-item')) {
            const box = await control.boundingBox();
            assert.ok(
              box.width >= 44 && box.height >= 44,
              `${selector}: touch target ${JSON.stringify(box)}`,
            );
          }
        }
        for (const action of ['theme', 'language']) {
          const control = page.locator(`[data-action=${action}]`).first();
          await control.focus();
          await page.keyboard.press('Enter');
          await expect(control).toBeFocused();
          await page.keyboard.press('Enter');
        }
        await page.locator('[data-action=visibility][data-id=private]').click();
        await expect(page.locator('[data-action=visibility][data-id=private]')).toBeFocused();
        const iconButtons = page.locator('.heading-tools .icon-button');
        for (const control of await iconButtons.all()) {
          const label = await control.getAttribute('aria-label');
          assert.ok(label);
          assert.equal(await control.getAttribute('title'), label);
        }
        await page.locator('.chart-data summary').click();
        await geometry(page, `chart-table/${theme}/${locale}/${width}`);
        await page.locator('[data-action=complete-review]').click();
        const completed = page.locator('[data-action=complete-review]');
        await expect(completed).toBeDisabled();
        const before = await controlContrast(completed);
        await completed.hover();
        assert.deepEqual(await controlContrast(completed), before);
        await accessibility(page, `controls/${theme}/${locale}/${width}`);
        await context.close();
      }
    }
  }
}

async function layoutChecks() {
  for (const id of ids) {
    for (const locale of matrix ? ['uk', 'en'] : ['uk']) {
      for (const theme of matrix ? ['dark', 'light'] : ['dark']) {
        for (const width of variantArg && !matrix ? [1440, 390] : [1440, 390, 768, 320]) {
          const { context, page } = await newPage(width, locale, theme);
          const label = `${id}/${locale}/${theme}/${width}`;
          await page.goto(`${base}/?variant=${id}`);
          await expect(page.locator('main')).toHaveCount(1);
          await expect(
            page.getByRole('heading', { name: 'Emma Wilson', exact: true }),
          ).toBeVisible();
          await geometry(page, label);
          if (width === 1440 || width === 390) await accessibility(page, label);
          if (locale === 'uk' && theme === 'dark' && [1440, 390].includes(width)) {
            const suffix = width === 1440 ? 'desktop' : 'mobile';
            await prepareCapture(page);
            await page.screenshot({
              path: new URL(`screenshots/${id}-${suffix}.png`, import.meta.url).pathname,
              animations: 'disabled',
            });
            await page.screenshot({
              path: new URL(`screenshots/${id}-${suffix}-full.png`, import.meta.url).pathname,
              fullPage: true,
              animations: 'disabled',
            });
          }
          report.layouts.push({ id, locale, theme, width, result: 'pass' });
          if (width === 1440 && locale === 'uk' && theme === 'dark') {
            await page.locator('[data-action=client-details]').first().click();
            await expect(page.locator('.history-entry')).toHaveCount(8);
          }
          await context.close();
        }
      }
    }
    console.log(`Layout ${id}: passed`);
  }
}

async function coreBehavior(width) {
  const { context, page } = await newPage(width);
  await page.goto(`${base}/?variant=02`);
  await page.keyboard.press('Tab');
  await expect(page.locator('.skip-link')).toBeFocused();
  await expect(page.locator('.skip-link')).toHaveCSS('clip-path', 'none');
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
  await page.locator('.video-preview').click();
  await expect(page.locator('dialog')).toBeVisible();
  await expect(page.locator('dialog')).toContainText('не підключене');
  await page.keyboard.press('Escape');
  await expect(page.locator('.video-preview')).toBeFocused();
  await page.locator('#coach-note').fill('Focus on the final set.');
  await page.locator('#note-form button[type=submit]').click();
  await expect(page.locator('[data-action=complete-review]')).toBeEnabled();
  await page.locator('[data-action=visibility][data-id=private]').click();
  await page.locator('#coach-note').fill('Private observation');
  await page.locator('#note-form button[type=submit]').click();
  await page.locator('[data-action=client-view]').first().click();
  await expect(page.locator('[data-client-note]')).toHaveText('Від тренераFocus on the final set.');
  assert.ok(!(await page.locator('main').innerText()).includes('Private observation'));
  await page.locator('.preview-client-bar [data-action=workspace]').click();
  await page.locator('[data-action=complete-review]').click();
  await expect(page.locator('[data-action=complete-review]')).toBeDisabled();
  await page.locator('[data-action=select-client][data-id=liam]').click();
  await expect(page.locator('#coach-note')).toHaveValue('');
  await page.locator('#coach-note').fill('Liam draft');
  await page.locator('[data-action=select-client][data-id=emma]').click();
  await expect(page.locator('#coach-note')).toHaveValue('Focus on the final set.');
  await page.locator('[data-action=select-client][data-id=liam]').click();
  await expect(page.locator('#coach-note')).toHaveValue('Liam draft');
  await page.locator('#tab-overview').focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('#tab-program')).toHaveAttribute('aria-selected', 'true');
  await page.locator('[data-action=tab][data-id=history]').click();
  await expect(page.locator('.history-entry')).toHaveCount(8);
  await page.locator('#client-search').fill('zzzz');
  await expect(page.locator('.empty-search')).toBeVisible();
  await page.locator('#client-search').fill('');
  await page.locator('[data-action=select-client][data-id=oliver]').click();
  await expect(page.locator('main')).toContainText('Історія поки порожня');
  report.behaviors.push({
    width,
    name: 'Video, notes, privacy, separate review, drafts, keyboard tabs, history and search',
    result: 'pass',
  });
  await context.close();
}

async function editorBehavior(width) {
  const { context, page } = await newPage(width);
  await page.goto(`${base}/?variant=02`);
  const originalHistory = await page.evaluate(
    (key) => JSON.parse(localStorage.getItem(key)).data.clients,
    STORAGE_KEY,
  );
  await page.locator('nav [data-action=exercises]').click();
  await page.locator('[data-action=new-exercise]').click();
  await accessibility(page, `exercise-form/${width}`);
  const form = page.locator('#exercise-form');
  await form.locator('[name=name-uk]').fill('Контрольований підхід');
  await form.locator('[name=name-en]').fill('Controlled set');
  await form.locator('[name=unit]').selectOption('reps');
  await form.locator('[name=tutorial]').fill('https://example.com/video');
  await form.locator('button[type=submit]').click();
  await expect(form.locator('.form-error')).toContainText('YouTube');
  await form.locator('[name=tutorial]').fill('');
  await form.locator('button[type=submit]').click();
  await expect(page.locator('dialog')).not.toBeVisible();
  await expect(page.locator('.catalog-table')).toContainText('Контрольований підхід');
  await page.locator('nav [data-action=programs]').click();
  await page.locator('[data-action=new-program]').click();
  await page.locator('[name=program-uk]').fill('Мій цикл');
  await page.locator('[name=program-en]').fill('My cycle');
  await page.locator('#program-editor button[type=submit]').click();
  await expect(page.locator('#program-error')).toContainText('щонайменше одну вправу');
  await page.locator('#add-exercise-select').selectOption({ label: 'Контрольований підхід' });
  await page.locator('[data-action=add-row]').click();
  await page.locator('#add-exercise-select').selectOption('handstand');
  await page.locator('[data-action=add-row]').click();
  await page.locator('[data-action=move-row-up][data-index="1"]').click();
  await expect(page.locator('.builder-row h3').first()).toHaveText('Стійка біля стіни');
  await page.locator('[data-action=add-set][data-index="0"]').click();
  await expect(page.locator('.builder-row').first().locator('[data-target]')).toHaveCount(4);
  await page.locator('[data-action=remove-set][data-index="0"]').click();
  await page.locator('[data-action=add-week]').click();
  await expect(page.locator('.editor-week-button')).toHaveCount(2);
  await page.locator('[data-action=add-session]').click();
  await expect(page.locator('.editor-session-button')).toHaveCount(2);
  await page.locator('nav [data-action=clients]').click();
  await expect(page.locator('dialog')).toContainText('незбережені');
  await page.keyboard.press('Escape');
  await page.locator('#program-editor button[type=submit]').click();
  await expect(page.locator('[data-editor-status]')).toHaveText('Чернетку збережено');
  await geometry(page, `program-editor/${width}`);
  await accessibility(page, `program-editor/${width}`);
  await prepareCapture(page);
  await page.screenshot({
    path: new URL(`screenshots/program-editor-${width}.png`, import.meta.url).pathname,
    fullPage: true,
  });
  await page.locator('[data-action=preview-program]').click();
  await expect(page.locator('dialog')).toContainText('Контрольований підхід');
  await page.keyboard.press('Escape');
  await page.locator('[data-action=publish-program]').click();
  await page.locator('[data-action=confirm-publish]').click();
  await expect(page.locator('.editor-versions')).toContainText('v1');
  await page.locator('.editor-save-bar [data-action=assign]').click();
  await page.locator('#assignment-form [name=client]').selectOption('anna');
  await page.locator('#assignment-form button[type=submit]').click();
  await expect(page.locator('#assignment-form .form-error')).toContainText(
    'Немає активного доступу',
  );
  await page.locator('#assignment-form [name=client]').selectOption('emma');
  await page.locator('#assignment-form button[type=submit]').click();
  await expect(page.locator('dialog')).not.toBeVisible();
  const after = await page.evaluate(
    (key) => JSON.parse(localStorage.getItem(key)).data,
    STORAGE_KEY,
  );
  assert.deepEqual(after.clients, originalHistory);
  assert.equal(after.assignments.length, 1);
  assert.equal(after.assignments[0].version.number, 1);
  await page.locator('nav [data-action=workspace]').click();
  await page.locator('[data-action=client-view]').first().click();
  await expect(page.locator('[data-future-assignment]')).toContainText('Мій цикл');
  await page.locator('[data-future-assignment] summary').first().click();
  await expect(page.locator('[data-future-assignment]')).toContainText('Контрольований підхід');
  await page.locator('nav [data-action=exercises]').click();
  const row = page.locator('.catalog-table tr').filter({ hasText: 'Контрольований підхід' });
  await row.locator('[data-action=archive-exercise]').click();
  await expect(row).toHaveCount(0);
  await page.locator('#show-archived').check();
  await expect(row).toHaveCount(1);
  await expect(row).toContainText('В архіві');
  report.behaviors.push({
    width,
    name: 'Validation, builder, reorder, unsaved guard, preview, publish, assignment, history, archive',
    result: 'pass',
  });
  await context.close();
}

async function stateBehavior() {
  const { context, page } = await newPage(390);
  await page.goto(`${base}/?variant=02`);
  for (const id of ['loading', 'error', 'unavailable', 'denied']) {
    await page.locator('nav [data-action=settings]').click();
    await page.locator(`[data-action=demo-state][data-id=${id}]`).click();
    await expect(page.locator('dialog')).toBeVisible();
    await accessibility(page, `state-${id}`);
    await page.keyboard.press('Escape');
  }
  await page.locator('[data-action=demo-state][data-id=conflict]').click();
  await page.locator('[data-action=close-modal]').last().click();
  await page.locator('[name=program-uk]').fill('Stale draft');
  await page.locator('#program-editor button[type=submit]').click();
  await expect(page.locator('#program-error')).toContainText('Версію змінено');
  await page.locator('[data-action=duplicate-program]').click();
  await page.locator('[data-action=discard-editor]').click();
  await expect(page.locator('[name=program-uk]')).toHaveValue('Stale draft (копія)');
  await page.locator('#program-editor button[type=submit]').click();
  await expect(page.locator('[data-editor-status]')).toHaveText('Чернетку збережено');
  report.behaviors.push({
    name: 'Loading, error, unavailable video, access denied, revision conflict and recovery',
    result: 'pass',
  });
  await context.close();
}

async function captureGallery() {
  const { context, page } = await newPage(1440);
  await page.goto(base);
  await expect(page.locator('.concept-card')).toHaveCount(10);
  await page.locator('.gallery-footer').scrollIntoViewIfNeeded();
  await geometry(page, 'gallery');
  await accessibility(page, 'gallery');
  await prepareCapture(page);
  await page.screenshot({
    path: new URL('screenshots/gallery.png', import.meta.url).pathname,
    fullPage: true,
  });
  await page.addStyleTag({
    content:
      '.gallery-grid{gap:18px;padding:0}.concept-caption p{display:none}.concept-caption{padding:12px 16px}.concept-image{aspect-ratio:1440/1000}.gallery{max-width:none;padding:18px}',
  });
  await page
    .locator('.gallery-grid')
    .screenshot({ path: new URL('overview.png', import.meta.url).pathname });
  await page.setViewportSize({ width: 390, height: 844 });
  await geometry(page, 'gallery-mobile');
  await context.close();
}

async function sharedEditorMatrix() {
  for (const locale of ['uk', 'en']) {
    for (const theme of ['dark', 'light']) {
      for (const width of [1440, 390]) {
        const { context, page } = await newPage(width, locale, theme);
        const label = `${locale}/${theme}/${width}`;
        await page.goto(`${base}/?variant=02`);
        await page.locator('nav [data-action=programs]').click();
        await page
          .locator('[name=program-uk]')
          .fill('Персональна програма балансу, сили й рухливості плечей');
        await page
          .locator('[name=program-en]')
          .fill('Personal balance, strength and shoulder mobility program');
        await page.locator('#program-editor button[type=submit]').click();
        await geometry(page, `builder/${label}`);
        await accessibility(page, `builder/${label}`);
        report.layouts.push({ view: 'builder', locale, theme, width, result: 'pass' });
        if (locale === 'en' && theme === 'light' && width === 1440) {
          await prepareCapture(page);
          await page.screenshot({
            path: new URL('screenshots/editor-en-light.png', import.meta.url).pathname,
            fullPage: true,
          });
        }
        await page.locator('nav [data-action=exercises]').click();
        await geometry(page, `catalog/${label}`);
        await accessibility(page, `catalog/${label}`);
        report.layouts.push({ view: 'catalog', locale, theme, width, result: 'pass' });
        await page.locator('[data-action=new-exercise]').click();
        await page
          .locator('[name=name-uk]')
          .fill('Контрольована вправа з довгою назвою для перевірки компонування');
        await page
          .locator('[name=name-en]')
          .fill('A controlled exercise with a long name for the layout check');
        await geometry(page, `exercise-dialog/${label}`);
        await accessibility(page, `exercise-dialog/${label}`);
        report.layouts.push({ view: 'exercise-dialog', locale, theme, width, result: 'pass' });
        await context.close();
      }
    }
  }
}

try {
  if (args.includes('--controls-only')) {
    await controlStates();
  } else if (args.includes('--editors-only')) {
    await sharedEditorMatrix();
  } else {
    await layoutChecks();
    for (const width of [1440, 390]) {
      await coreBehavior(width);
      await editorBehavior(width);
    }
    await stateBehavior();
    if (!variantArg) await captureGallery();
  }
  assert.deepEqual(report.errors, []);
  assert.deepEqual(report.requests, []);
  assert.deepEqual(report.failedResponses, []);
  report.sourceFiles = {};
  for (const file of [
    'index.html',
    'styles.css',
    'app.js',
    'data.js',
    'components.js',
    'editors.js',
    'ui.js',
    'variants.js',
    'assets/studio-ui.js',
  ]) {
    report.sourceFiles[file] = createHash('sha256')
      .update(await readFile(new URL(file, import.meta.url)))
      .digest('hex');
  }
  for (const id of ids) {
    for (const suffix of ['desktop', 'mobile']) {
      const path = `screenshots/${id}-${suffix}.png`;
      const content = await readFile(new URL(path, import.meta.url));
      report.artifacts[path] = {
        bytes: content.length,
        sha256: createHash('sha256').update(content).digest('hex'),
      };
    }
  }
  report.passed = true;
} catch (error) {
  report.passed = false;
  report.failure = error.stack;
  process.exitCode = 1;
} finally {
  report.finishedAt = new Date().toISOString();
  await writeFile(
    new URL(
      args.includes('--controls-only')
        ? 'verification-controls.json'
        : args.includes('--editors-only')
          ? 'verification-editors.json'
          : variantArg
            ? `verification-${variantArg}.json`
            : 'verification.json',
      import.meta.url,
    ),
    JSON.stringify(report, null, 2) + '\n',
  );
  await browser.close();
  await new Promise((done) => server.close(done));
}
console.log(
  JSON.stringify(
    {
      passed: report.passed,
      layouts: report.layouts.length,
      accessibility: report.accessibility.length,
      controls: report.controls.length,
      behaviors: report.behaviors,
      errors: report.errors,
      requests: report.requests,
      failedResponses: report.failedResponses,
      failure: report.failure,
    },
    null,
    2,
  ),
);
