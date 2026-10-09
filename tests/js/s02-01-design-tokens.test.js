import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import test from 'node:test';
import { chromium } from '@playwright/test';

const read = (path) => existsSync(path) ? readFileSync(path, 'utf8') : '';
const reference = JSON.parse(read('references/design/preview/assets/design-tokens.json'));
const tokens = read('server/static/css/tokens.css');
const base = read('server/static/css/base.css');
const shell = read('server/templates/shared/base.html');
const rgb = (hex) => `rgb(${hex.slice(1).match(/../g).map((v) => parseInt(v, 16)).join(', ')})`;

test('semantic_tokens_present: approved colors in both themes', () => {
  for (const theme of ['light', 'dark']) {
    const rule = tokens.match(new RegExp(`html\\[data-theme=["']?${theme}["']?\\]\\s*\\{([^}]+)\\}`));
    assert.ok(rule, `missing ${theme} palette`);
    for (const [name, value] of Object.entries(reference.colors[theme])) {
      assert.match(rule[1], new RegExp(`--${name}:\\s*${value}\\s*;`));
    }
  }
  assert.match(tokens, /--accent:\s*var\(--green\)/);
});

test('no_font_files: system stack without font downloads', () => {
  assert.ok(tokens.includes(reference.font.family), 'approved system font stack absent');
  const paths = readdirSync('server', { recursive: true });
  assert.equal(paths.some((p) => /\.(woff2?|ttf|otf|eot)$/i.test(p)), false);
  assert.doesNotMatch(tokens + base + shell, /@font-face|@import|https?:\/\//i);
});

test('shared shell loads tokens before base, without demo runtime', () => {
  assert.ok(shell.indexOf('/static/css/tokens.css') >= 0);
  assert.ok(shell.indexOf('/static/css/base.css') > shell.indexOf('/static/css/tokens.css'));
  assert.match(shell, /name="viewport"/);
  assert.match(shell, /{% block content %}/);
  assert.doesNotMatch(shell, /selected-preview|fake|data-tier|data-role/);
});

for (const theme of ['light', 'dark']) {
  for (const width of [390, 1440]) {
    test(`monochrome_primary_action and typography: ${theme} ${width}`, async () => {
      const browser = await chromium.launch();
      try {
        const page = await browser.newPage({ viewport: { width, height: 900 } });
        // CSS fixture only; page routes/Jinja rendering belong to later shell cards.
        await page.setContent(`<html data-theme="${theme}"><head><style>${tokens}\n${base}</style></head><body><main><section class="panel"><h1>Тренування / Training</h1><p class="muted">Збережіть зміни перед продовженням тренування. Save changes before continuing your training.</p><p class="accent">Збережено / Saved</p><button class="primary">Зберегти та продовжити / Save and continue</button></section></main></body></html>`);
        const result = await page.evaluate(() => {
          const style = (selector) => getComputedStyle(document.querySelector(selector));
          const button = document.querySelector('button');
          return {
            bg: style('body').backgroundColor, text: style('body').color,
            surface: style('.panel').backgroundColor, muted: style('.muted').color,
            accent: style('.accent').color, line: style('.panel').borderTopColor,
            button: style('button').backgroundColor, buttonText: style('button').color,
            font: style('body').fontFamily, height: button.getBoundingClientRect().height,
            overflow: document.documentElement.scrollWidth > innerWidth,
          };
        });
        const expected = reference.colors[theme];
        for (const key of ['bg', 'text', 'surface', 'muted', 'line', 'button']) assert.equal(result[key], rgb(expected[key]), key);
        assert.equal(result.accent, rgb(expected.green));
        assert.equal(result.buttonText, rgb(expected['button-text']));
        assert.match(result.font, /-apple-system/);
        assert.ok(result.height >= 44);
        assert.equal(result.overflow, false);
        await page.keyboard.press('Tab');
        assert.equal(await page.locator('button').evaluate((el) => document.activeElement === el), true);
        assert.equal(await page.locator('button').evaluate((el) => getComputedStyle(el).outlineStyle), 'solid');
      } finally { await browser.close(); }
    });
  }
}
