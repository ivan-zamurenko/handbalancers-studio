// Знімає еталонні скриншоти всіх публічних екранів на чотирьох ширинах.
// Призначення: довести, що рефакторинг стилів не змінив жодного пікселя.
// Запуск: node scripts/capture-baseline.mjs <тека>
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

const outDir = process.argv[2] || '.local-tools/visual/baseline';
const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8000';
const widths = [320, 390, 768, 1440];
const routes = ['/', '/plans', '/onboarding', '/privacy', '/terms'];

mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome', headless: true });
let taken = 0;

for (const width of widths) {
  const context = await browser.newContext({
    viewport: { width, height: 900 },
    deviceScaleFactor: 1,
    reducedMotion: 'reduce',
  });
  const page = await context.newPage();
  for (const route of routes) {
    await page.goto(baseUrl + route, { waitUntil: 'networkidle' });
    // Анімації входу встигають завершитися, інакше знімок ловить проміжний кадр.
    await page.waitForTimeout(1200);
    const name = route === '/' ? 'home' : route.slice(1).replace(/\//g, '-');
    await page.screenshot({
      path: path.join(outDir, `${name}-${width}.png`),
      fullPage: true,
      animations: 'disabled',
    });
    taken += 1;
  }
  await context.close();
}

await browser.close();
console.log(`Знято ${taken} знімків у ${outDir}`);
