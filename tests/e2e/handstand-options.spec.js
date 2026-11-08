import {test, expect} from '@playwright/test';

const preview = '/static/previews/handstand/index.html';

test('five animated options, both themes, mobile layout and pause', async ({page}) => {
  await page.goto(preview);
  await expect(page.locator('[data-option]')).toHaveCount(5);
  for (const width of [390, 1440]) {
    await page.setViewportSize({width,height:1000});
    for (const theme of ['light','dark']) {
      await page.getByRole('button',{name:'Змінити тему'}).click();
      await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    }
  }
  expect(await page.locator('[data-option]').evaluateAll(cards=>cards.every(card=>card.getAnimations({subtree:true}).length>0))).toBe(true);
  await page.getByRole('button',{name:'Пауза'}).click();
  expect(await page.evaluate(()=>document.getAnimations().every(animation=>animation.playState==='paused'))).toBe(true);
});

test('each option opens a small central animation with dimming; corner and Escape restore focus', async ({page}) => {
  await page.goto(preview);
  const buttons=page.getByRole('button',{name:/На весь екран/});
  for (let index=0;index<5;index++) {
    await buttons.nth(index).click();
    const dialog=page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.locator('[data-stage] svg')).toHaveCount(1);
    await expect(dialog).toHaveAttribute('data-placement','center');
    const backdrop=await dialog.evaluate(el=>getComputedStyle(el,'::backdrop').backgroundColor);
    expect(backdrop).not.toBe('rgba(0, 0, 0, 0)');
    await page.getByRole('button',{name:'У кутку',exact:true}).click();
    await expect(dialog).toHaveAttribute('data-placement','corner');
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    await expect(buttons.nth(index)).toBeFocused();
  }
});

test('reduced motion defaults to still poses; preview makes no API calls', async ({page}) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  const api=[];
  page.on('request',request=>{if(new URL(request.url()).pathname.startsWith('/api/'))api.push(request.url());});
  await page.goto(preview);
  await expect(page.locator('[data-option]')).toHaveCount(5);
  expect(await page.evaluate(()=>document.getAnimations().every(animation=>animation.playState==='paused'))).toBe(true);
  await page.getByRole('button',{name:'На весь екран — Пружинка'}).click();
  expect(await page.getByRole('dialog').evaluate(el=>el.getAnimations({subtree:true}).every(animation=>animation.playState==='paused'))).toBe(true);
  expect(api).toEqual([]);
});
