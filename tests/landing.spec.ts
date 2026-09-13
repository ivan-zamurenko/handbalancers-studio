import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { catalogue } from '../src/content/catalog';
import { copy } from '../src/content/copy';
import type { Locale, OfferId } from '../src/content/types';

const locales = ['uk', 'en'] as const;
const sectionIds = ['programmes', 'method', 'coaching', 'equipment', 'future', 'faq'] as const;
const languageNames = { uk: 'Українська', en: 'English' } as const;

// A fresh English-language browser must still respect the agreed Ukrainian default.
test.use({ locale: 'en-US' });

function offerTrigger(page: Page, locale: Locale, id: OfferId) {
  return page.getByRole('button', {
    name: `${copy[locale].common.details}: ${copy[locale].offers[id].title}`,
    exact: true,
  });
}

async function selectLanguage(page: Page, locale: Locale) {
  await page.getByRole('button', { name: languageNames[locale], exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', locale);
}

async function expectOffer(page: Page, locale: Locale, id: OfferId) {
  const offer = copy[locale].offers[id];
  const dialog = page.getByRole('dialog', { name: offer.title, exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('heading', { name: offer.title, exact: true })).toBeVisible();
  await expect(dialog.getByText(offer.description, { exact: true })).toBeVisible();
  for (const item of offer.includes) {
    await expect(dialog.getByText(item, { exact: true })).toBeVisible();
  }
  return dialog;
}

async function expectAccessible(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze();
  expect(result.violations).toEqual([]);
}

test('a fresh browser opens the complete Ukrainian landing', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('html')).toHaveAttribute('lang', 'uk');
  await expect(page.getByRole('heading', { level: 1 })).toContainText(copy.uk.hero.line1);
  await expect(page.getByRole('heading', { level: 1 })).toContainText(copy.uk.hero.line2);
  await expect(page.getByRole('button', { name: 'English', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Українська', exact: true })).toBeVisible();
  await expect(
    page.getByRole('contentinfo').getByRole('link').filter({ hasText: 'Handbalancer’s Studio' }),
  ).toHaveAccessibleName(/Handbalancer’s Studio/);

  for (const id of sectionIds) {
    await expect(page.locator(`#${id}`).getByRole('heading', { level: 2 })).toHaveText(
      copy.uk[id].title,
    );
  }
});

test('every offer opens its own details and Escape restores trigger focus', async ({ page }) => {
  await page.goto('/');

  for (const { id } of catalogue) {
    await test.step(id, async () => {
      const trigger = offerTrigger(page, 'uk', id);
      await trigger.click();
      const dialog = await expectOffer(page, 'uk', id);
      await expect(
        dialog.getByRole('button', { name: copy.uk.common.close, exact: true }),
      ).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(dialog).toBeHidden();
      await expect(trigger).toBeFocused();
    });
  }
});

test('English translates the landing and preserves the opened FAQ', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/');

  const [ukFaq] = copy.uk.faq.items;
  const [enFaq] = copy.en.faq.items;
  if (!ukFaq || !enFaq) throw new Error('The landing must contain a translated FAQ.');
  const ukDetails = page.locator('#faq details').filter({
    has: page.getByText(ukFaq.question, { exact: true }),
  });
  await ukDetails.locator('summary').click();
  await expect(ukDetails).toHaveJSProperty('open', true);
  await expect(ukDetails.getByText(ukFaq.answer, { exact: true })).toBeVisible();

  await selectLanguage(page, 'en');
  const enDetails = page.locator('#faq details').filter({
    has: page.getByText(enFaq.question, { exact: true }),
  });
  await expect(enDetails).toHaveJSProperty('open', true);
  await expect(enDetails.getByText(enFaq.answer, { exact: true })).toBeVisible();
  await expect(
    page.getByRole('contentinfo').getByRole('link').filter({ hasText: 'Handbalancer’s Studio' }),
  ).toHaveAccessibleName(/Handbalancer’s Studio/);

  const navigation = page.getByRole('navigation', { name: copy.en.navigation.label, exact: true });
  await expect(navigation).toBeVisible();
  for (const id of ['programmes', 'method', 'coaching', 'equipment'] as const) {
    await expect(
      navigation.getByRole('link', { name: copy.en.navigation[id], exact: true }),
    ).toHaveAttribute('href', `#${id}`);
  }
  for (const id of sectionIds) {
    await expect(page.locator(`#${id}`).getByRole('heading', { level: 2 })).toHaveText(
      copy.en[id].title,
    );
  }
  for (const { id } of catalogue) {
    const trigger = offerTrigger(page, 'en', id);
    await trigger.click();
    const dialog = await expectOffer(page, 'en', id);
    await dialog.getByRole('button', { name: copy.en.common.close, exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
  }

  await selectLanguage(page, 'uk');
  await expect(page.getByRole('heading', { level: 1 })).toContainText(copy.uk.hero.line1);
  await expect(ukDetails).toHaveJSProperty('open', true);
  await expect(ukDetails.getByText(ukFaq.answer, { exact: true })).toBeVisible();
});

test('mobile navigation supports keyboard dismissal and closes after a link', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  const openMenu = page.getByRole('button', { name: copy.uk.navigation.openMenu, exact: true });
  const navigation = page.getByRole('navigation', { name: copy.uk.navigation.label, exact: true });
  const firstLink = navigation.getByRole('link').first();
  await expect(openMenu).toHaveAttribute('aria-expanded', 'false');
  await expect(navigation).toBeHidden();
  await openMenu.focus();
  await page.keyboard.press('Enter');
  await expect(navigation).toBeVisible();
  await expect(firstLink).toBeFocused();
  await expect(
    page.getByRole('button', { name: copy.uk.navigation.closeMenu, exact: true }),
  ).toHaveAttribute('aria-expanded', 'true');
  await page.keyboard.press('Escape');
  await expect(navigation).toBeHidden();
  await expect(openMenu).toBeFocused();

  await page.keyboard.press('Enter');
  await expect(firstLink).toBeFocused();
  await expect(firstLink).toHaveAccessibleName(copy.uk.navigation.programmes);
  await page.keyboard.press('Enter');
  await expect(navigation).toBeHidden();
  await expect(openMenu).toHaveAttribute('aria-expanded', 'false');
  await expect(page).toHaveURL(/#programmes$/);
  await expect(page.locator('#programmes').getByRole('heading', { level: 2 })).toBeInViewport();
});

test('reduced motion preserves content and interactions without prolonged animation', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior)).toBe(
    'auto',
  );
  await page.getByRole('button', { name: copy.uk.navigation.openMenu, exact: true }).click();
  await expect(
    page.getByRole('navigation', { name: copy.uk.navigation.label, exact: true }),
  ).toBeVisible();
  await page.keyboard.press('Escape');
  await offerTrigger(page, 'uk', 'handstand').click();
  await expectOffer(page, 'uk', 'handstand');

  // Inspect real running animations; screenshot options alone would hide a defect.
  const longAnimations = await page.evaluate(
    () =>
      document.getAnimations().filter((animation) => {
        if (animation.playState !== 'running') return false;
        const duration = animation.effect?.getComputedTiming().activeDuration;
        return typeof duration === 'number' && duration > 1;
      }).length,
  );
  expect(longAnimations).toBe(0);

  await page.keyboard.press('Escape');
  await expect(offerTrigger(page, 'uk', 'handstand')).toBeFocused();
});

test('both languages fit mobile, tablet and desktop widths', async ({ page }) => {
  await page.goto('/');

  for (const locale of locales) {
    await selectLanguage(page, locale);
    for (const width of [360, 390, 768, 1440]) {
      await test.step(`${locale} at ${width}px`, async () => {
        await page.setViewportSize({ width, height: 1000 });
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
        for (const id of sectionIds) {
          await expect(page.locator(`#${id}`).getByRole('heading', { level: 2 })).toBeVisible();
        }
        await expect
          .poll(() =>
            page.evaluate(
              () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
            ),
          )
          .toBeLessThanOrEqual(1);

        await offerTrigger(page, locale, 'coach').click();
        const dialog = await expectOffer(page, locale, 'coach');
        await expect(
          dialog.getByRole('button', { name: copy[locale].common.close, exact: true }),
        ).toBeInViewport();
        await page.keyboard.press('Escape');
      });
    }
  }
});

test('desktop content passes automated accessibility checks in both languages', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/');
  await expectAccessible(page);
  await selectLanguage(page, 'en');
  await expectAccessible(page);
});

test('mobile navigation and an open offer pass automated accessibility checks', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: copy.uk.navigation.openMenu, exact: true }).click();
  await expectAccessible(page);
  await page.keyboard.press('Escape');

  const backgroundButton = page.getByRole('button', {
    name: 'English',
    exact: true,
    includeHidden: true,
  });
  await backgroundButton.focus();
  await expect(backgroundButton).toBeFocused();

  await offerTrigger(page, 'uk', 'coach').click();
  const dialog = await expectOffer(page, 'uk', 'coach');
  await expectAccessible(page);

  // Native dialogs may yield focus to browser controls, never to the background page.
  // HTML's sequential focus navigation permits this; BODY alone cannot identify a leak.
  for (const key of ['Tab', 'Tab', 'Tab', 'Tab', 'Shift+Tab', 'Shift+Tab']) {
    await page.keyboard.press(key);
    const focusIsSafe = await dialog.evaluate(
      (element) =>
        element.contains(document.activeElement) ||
        (!document.hasFocus() && document.activeElement === document.body),
    );
    expect(focusIsSafe).toBe(true);
  }

  const closeButton = dialog.getByRole('button', { name: copy.uk.common.close, exact: true });
  await closeButton.focus();
  await backgroundButton.focus();
  await expect(backgroundButton).not.toBeFocused();
  await expect(closeButton).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(offerTrigger(page, 'uk', 'coach')).toBeFocused();
});

test('browsing offers makes only local read requests', async ({ page, context, baseURL }) => {
  const localOrigin = new URL(baseURL ?? 'http://127.0.0.1:4173').origin;
  const unexpectedRequests: string[] = [];
  await context.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const isNetworkRequest = url.protocol === 'http:' || url.protocol === 'https:';
    if (
      isNetworkRequest &&
      (url.origin !== localOrigin || !['GET', 'HEAD'].includes(request.method()))
    ) {
      // Record origins and methods only; future query strings could contain private data.
      unexpectedRequests.push(`${request.method()} ${url.origin}`);
      await route.abort('blockedbyclient');
      return;
    }
    await route.continue();
  });

  await page.goto('/');
  for (const locale of locales) {
    await selectLanguage(page, locale);
    for (const { id } of catalogue) {
      await offerTrigger(page, locale, id).click();
      await expectOffer(page, locale, id);
      await page.keyboard.press('Escape');
    }
  }
  expect(unexpectedRequests).toEqual([]);
});

test('repeated language, menu and dialog actions leave no browser errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');

  for (const locale of ['en', 'uk', 'en', 'uk'] as const) {
    await selectLanguage(page, locale);
    await page.getByRole('button', { name: copy[locale].navigation.openMenu, exact: true }).click();
    await page.keyboard.press('Escape');
    const trigger = offerTrigger(page, locale, 'consultation');
    await trigger.click();
    const dialog = await expectOffer(page, locale, 'consultation');
    await dialog.getByRole('button', { name: copy[locale].common.close, exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
  }
  expect(errors).toEqual([]);
});
