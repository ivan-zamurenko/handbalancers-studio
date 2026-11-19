import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdir} from 'node:fs/promises';
const html=new Map();
async function member(page,path,lang='uk'){
 const key=path+lang;
 if(!html.has(key))html.set(key,execFileSync('.venv/bin/python',['tests/fixtures/render_member_page.py',path,lang],{encoding:'utf8'}));
 await page.route(`**${path}?lang=${lang}`,r=>r.fulfill({contentType:'text/html',body:html.get(key)}));
 await page.route('**/api/session',r=>r.fulfill({json:{authenticated:true,setup_required:false,user:{id:'test-member'},csrf_token:'a'.repeat(64)}}));
 await page.route('**/api/me/preferences',r=>r.fulfill({json:{theme_preference:'auto',revision:0}}));
 await page.goto(`${path}?lang=${lang}`);
 await expect.poll(()=>page.evaluate(()=>localStorage.getItem('studio:account:test-member:theme'))).not.toBeNull();
}
for(const width of [390,1440])for(const theme of ['light','dark'])test(`cabinet navigation and honest overview ${width} ${theme}`,async({page})=>{
 await page.setViewportSize({width,height:1000});
 await member(page,'/dashboard');
 await page.evaluate(theme=>document.dispatchEvent(new CustomEvent('studio:theme-select',{detail:theme})),theme);
 await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
 await expect(page.locator('[data-member-shell]')).toBeVisible();
 if(width>780){
  const brand=await page.locator('.side-brand').boundingBox();
  const name=await page.locator('.side-brand small').boundingBox();
  expect(Math.abs(brand.y+brand.height/2-name.y-name.height/2)).toBeLessThan(2);
 }

 await expect(page.locator('.site-header')).toHaveCSS('border-bottom-width','1px');
 await expect(page.locator('[data-member-nav]')).not.toContainText(/Напрями|Методика|Тарифи|Сьогодні/);
 await expect(page.locator('[data-member-nav] a[aria-current=page]')).toHaveAttribute('href','/dashboard?lang=uk');
 await expect(page.locator('[data-today-empty]')).toBeVisible();
 await expect(page.locator('[data-empty-metric]')).toHaveCount(4);
 for(const metric of await page.locator('[data-empty-metric]').all())await expect(metric).toHaveText('—');
 await expect(page.locator('[data-heatmap-empty]')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 if(width<780){
  await page.locator('[data-menu-toggle]').click();
  await expect(page.locator('#site-menu')).toHaveAttribute('aria-modal','true');
  await expect(page.locator('main')).toHaveAttribute('inert','');
  await expect(page.locator('[data-member-nav] a').first()).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-menu-toggle]')).toBeFocused();
  await expect(page.locator('main')).not.toHaveAttribute('inert','');
 }
 await mkdir('private-evidence/member-cabinet-2026-11-19',{recursive:true});
 await page.locator('.cabinet-page-head h1').click();
 await page.screenshot({path:`private-evidence/member-cabinet-2026-11-19/dashboard-${width}-${theme}.png`,fullPage:true});
});

// Owner replaced the empty metrics/tabs with one dedicated first-session state.
for(const width of [320,390,1440])for(const theme of ['light','dark'])test(`empty progress ${width} ${theme}`,async({page})=>{
 await page.setViewportSize({width,height:1000});
 await member(page,'/progress');
 await page.evaluate(theme=>document.dispatchEvent(new CustomEvent('studio:theme-select',{detail:theme})),theme);
 await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
 await expect(page.locator('[data-progress-empty]')).toBeVisible();
 await expect(page.locator('[data-empty-metric], [data-heatmap-empty], [role=tab]')).toHaveCount(0);
 const art=page.locator('[data-empty-art]');
 await expect(art).toHaveAttribute('aria-hidden','true');
 const motion=await art.evaluate(el=>el.getAnimations({subtree:true}).map(a=>a.effect.getTiming()));
 expect(motion.length).toBeGreaterThan(0);
 for(const timing of motion){expect(timing.iterations).toBe(1);expect(timing.duration+timing.delay).toBeLessThanOrEqual(5000);}
 await page.evaluate(()=>{window.emptyDocument=document.documentElement;});
 if(width<780)await page.locator('[data-menu-toggle]').click();
 await page.locator('.locale-nav a[lang=en]').click();
 await expect(page.locator('[data-progress-empty]')).toContainText('Your first session is a starting point.');
 expect(await page.evaluate(()=>window.emptyDocument===document.documentElement)).toBe(true);
 await expect(page.locator('[data-empty-action]')).toHaveAttribute('href','/dashboard?lang=en');
 await art.evaluate(el=>Promise.all(el.getAnimations({subtree:true}).map(a=>a.finished)));
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`private-evidence/member-cabinet-2026-11-19/empty-progress-${width}-${theme}.png`,fullPage:true});
 await page.route('**/dashboard?lang=en',r=>r.fulfill({contentType:'text/html',body:'<h1>Overview</h1>'}));
 await page.locator('[data-empty-action]').click();
 await expect(page).toHaveURL(/\/dashboard\?lang=en$/);
});

test('empty progress respects reduced motion',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});
 await member(page,'/progress');
 const art=page.locator('[data-empty-art]');
 await expect(art).toBeVisible();
 expect(await art.evaluate(el=>el.getAnimations({subtree:true}).length)).toBe(0);
 await expect(art.locator('.first-step-dot')).toHaveCSS('opacity','1');
 await expect(page.locator('[data-empty-action]')).toBeVisible();
});
