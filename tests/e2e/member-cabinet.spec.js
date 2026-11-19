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

for(const width of [320,1440])test(`progress tabs and language work without synthetic results ${width}`,async({page})=>{
 await page.setViewportSize({width,height:1000});
 await member(page,'/progress');
 await expect(page.locator('[data-member-nav] a[aria-current=page]')).toHaveAttribute('href','/progress?lang=uk');
 await expect(page.getByRole('tabpanel')).toHaveCount(1);
 await page.getByRole('tab',{name:'Стійка',exact:true}).click();
 await expect(page.locator('#progress-hold')).toBeVisible();
 await page.keyboard.press('ArrowRight');
 await expect(page.locator('#progress-exercises')).toBeVisible();
 if(width<780)await page.locator('[data-menu-toggle]').click();
 await page.locator('.locale-nav a[lang=en]').click();
 await expect(page.getByRole('tab',{name:'Exercises',exact:true})).toHaveAttribute('aria-selected','true');
 await expect(page.locator('#progress-exercises')).toContainText('No results yet');
 const tabBox=await page.getByRole('tab',{name:'Exercises',exact:true}).boundingBox();
 const listBox=await page.getByRole('tablist').boundingBox();
 expect(tabBox.x+tabBox.width).toBeLessThanOrEqual(listBox.x+listBox.width+1);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:`private-evidence/member-cabinet-2026-11-19/progress-${width}.png`,fullPage:true});
});
