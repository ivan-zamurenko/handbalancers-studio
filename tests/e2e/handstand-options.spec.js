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
  // SVG joint animation changes paths; the other studies use CSS animation clocks.
  const snapshots=()=>page.locator('[data-option]').evaluateAll(cards=>cards.map(card=>JSON.stringify({
    svg:card.querySelector('svg').outerHTML, clocks:card.getAnimations({subtree:true}).map(a=>a.currentTime),
  })));
  const before=await snapshots();
  await page.waitForTimeout(800);
  const after=await snapshots();
  expect(after.every((value,index)=>value!==before[index])).toBe(true);
  await page.getByRole('button',{name:'Пауза'}).click();
  expect(await page.evaluate(()=>document.getAnimations().every(animation=>animation.playState==='paused'))).toBe(true);
  const still=await page.locator('[data-handstand-cycle]').innerHTML();
  await page.waitForTimeout(120);
  expect(await page.locator('[data-handstand-cycle]').innerHTML()).toBe(still);
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
  const cycle=page.locator('[data-handstand-cycle]');
  const still=await cycle.innerHTML();
  await page.waitForTimeout(800);
  expect(await cycle.innerHTML()).toBe(still);
  await page.getByRole('button',{name:'На весь екран — Перша спроба'}).click();
  const clone=page.getByRole('dialog').locator('[data-handstand-cycle]');
  const cloneStill=await clone.innerHTML();
  await page.waitForTimeout(800);
  expect(await clone.innerHTML()).toBe(cloneStill);
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'На весь екран — Пружинка'}).click();
  expect(await page.getByRole('dialog').evaluate(el=>el.getAnimations({subtree:true}).every(animation=>animation.playState==='paused'))).toBe(true);
  expect(api).toEqual([]);
});

test('dedicated cycle moves from standing feet to a handstand and pauses', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/static/previews/handstand/cycle.html');
  const figure=page.locator('[data-handstand-cycle]');
  expect(Number(await figure.locator('[data-head]').getAttribute('cy'))).toBeLessThan(60);
  await expect.poll(async()=>{
    const path=await figure.locator('[data-bone="front-foot"]').getAttribute('d');
    return Number(path.match(/-?\d+(?:\.\d+)?/g)[1]);
  },{timeout:6500}).toBeLessThan(25);
  await page.getByRole('button',{name:'Пауза'}).click();
  const still=await figure.innerHTML();
  await page.waitForTimeout(120);
  expect(await figure.innerHTML()).toBe(still);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('button',{name:'На весь екран — Повний цикл'}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'На весь екран — Повний цикл'})).toBeFocused();
});

test('studio composition uses product tokens and fits both themes on mobile and desktop', async ({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/static/previews/handstand/cycle.html');
  for(const width of [390,1440]){
    await page.setViewportSize({width,height:1000});
    for(const theme of ['light','dark']){
      await page.getByRole('button',{name:'Змінити тему'}).click();
      await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
      const styles=await page.locator('.single-stage').evaluate(el=>{
        const root=getComputedStyle(document.documentElement),card=getComputedStyle(el);
        return {radius:card.borderRadius,token:root.getPropertyValue('--radius-panel').trim(),fits:document.documentElement.scrollWidth<=innerWidth};
      });
      expect(styles.radius).toBe(styles.token);
      expect(styles.fits).toBe(true);
      await expect(page.locator('[data-contact-shadow]')).toHaveCount(1);
    }
  }
  await page.getByRole('button',{name:'На весь екран — Повний цикл'}).click();
  const dialog=page.getByRole('dialog');
  await expect(dialog.locator('[data-stage] svg')).toBeVisible();
  expect(await dialog.locator('.loading-stage').evaluate(el=>el.getBoundingClientRect().width)).toBeLessThan(300);
  await page.keyboard.press('Escape');
});
