// Real hosted Checkout. No request interception or mocked API responses.
// Only Stripe's published test card numbers are entered on checkout.stripe.com.
import {chromium,expect} from '@playwright/test';
import fs from 'node:fs/promises';
process.umask(0o077);
function localFixture(config,label){
 if(config.origin!=='http://127.0.0.1:8787'||!['pro','plus'].includes(label))throw new Error('Local test only');
 const account=config.accounts?.[label];
 if(!account?.email?.endsWith('@example.test')||!account.cookies?.length||account.cookies.some(c=>c.domain!=='127.0.0.1'))throw new Error('Synthetic local identity required');
}
function sameRun(config,result){if(!/^[a-f0-9]{32}$/.test(config.run_id||'')||config.run_id!==result.run_id)throw new Error('Different gate run');}
function testCheckout(value){const u=new URL(value);if(u.protocol!=='https:'||u.hostname!=='checkout.stripe.com'||!/^\/[cg]\/pay\/cs_test_/.test(u.pathname)||u.username||u.password)throw new Error('Test Checkout required');}
if(process.argv.includes('--self-check')){
 const valid={run_id:'a'.repeat(32),origin:'http://127.0.0.1:8787',accounts:{pro:{email:'synthetic@example.test',cookies:[{domain:'127.0.0.1'}]}}};
 localFixture(valid,'pro');testCheckout('https://checkout.stripe.com/c/pay/cs_test_synthetic');
 const denied=[()=>sameRun(valid,{run_id:'b'.repeat(32)}),()=>localFixture({...valid,origin:'https://production.example'},'pro'),()=>localFixture({...valid,accounts:{pro:{...valid.accounts.pro,cookies:[{domain:'production.example'}]}}},'pro'),()=>testCheckout('https://checkout.stripe.com/c/pay/cs_live_synthetic'),()=>testCheckout('https://evil.example/c/pay/cs_test_synthetic')];
 for(const call of denied){let rejected=false;try{call();}catch{rejected=true;}if(!rejected)throw new Error('Unsafe fixture accepted');}
 console.log('5 unsafe fixtures rejected; no browser/network started');process.exit(0);
}
const root='private-evidence/stripe-testmode';
const config=JSON.parse(await fs.readFile(`${root}/browser.json`,'utf8'));
const label=process.argv[2]||'pro';
localFixture(config,label);
sameRun(config,JSON.parse(await fs.readFile(`${root}/result.json`,'utf8')));
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
await context.addCookies(config.accounts[label].cookies);
const page=await context.newPage();
page.setDefaultTimeout(15000);
let step='open_subscription';
try{
 await page.goto(`${config.origin}/subscription?lang=en`);
 await expect(page.locator('[data-subscription-state]')).not.toHaveAttribute('data-state','loading');
 if(process.argv.includes('--portal-only')){
  await page.locator('[data-billing-portal]').click();
  await page.waitForURL('https://billing.stripe.com/**',{timeout:30000});
  await expect(page.locator('body')).toContainText(/Current subscription|Payment method/i,{timeout:30000});
  await page.screenshot({path:`${root}/${label}-portal.png`,fullPage:true});
  const saved=JSON.parse(await fs.readFile(`${root}/browser-${label}.json`,'utf8'));
  sameRun(config,saved);sameRun(config,JSON.parse(await fs.readFile(`${root}/result.json`,'utf8')));
  saved.real_portal_browser_loaded=true;
  await fs.writeFile(`${root}/browser-${label}.json`,JSON.stringify(saved),{mode:0o600});
  console.log(JSON.stringify({portal_loaded:true,plan:label}));
  await browser.close();process.exit(0);
 }
 const resume=page.locator('[data-active-link]');
 if(await resume.isVisible()){
  await resume.click();await page.locator('[data-resume-checkout]').click();
 }else{
  await page.locator(`[name=plan_code][value="${label}"]`).check();
  await page.locator('[data-billing-consent]').check();
  await page.locator('[data-buy-package]').click();
 }
 await page.waitForURL('https://checkout.stripe.com/**',{timeout:30000});
 testCheckout(page.url());
 step='hosted_form';
 let form;
 await expect.poll(async()=>{
  for(const frame of page.frames())if(new URL(frame.url()||'about:blank').hostname==='js.stripe.com'&&await frame.locator('#payment-numberInput').count()){form=frame;return true;}
  return false;
 },{timeout:45000}).toBe(true);
 await page.screenshot({path:`${root}/${label}-hosted.png`,fullPage:true});
 if(process.argv.includes('--inspect'))console.log(JSON.stringify({hosted_test_form:true,plan:label}));
 else{
  const email=form.locator('#linkAuthentication-emailInput');
  if(await email.isEditable())await email.fill(config.accounts[label].email);
  else await expect(email).toHaveValue(config.accounts[label].email);
  await form.locator('#payment-numberInput').fill(label==='pro'?'4000000000000002':'4242424242424242');
  await form.locator('#payment-expiryInput').fill('1234');
  await form.locator('#payment-cvcInput').fill('123');
  await form.locator('#payment-nameInput').fill('Studio Test Member');
  if(await form.locator('#payment-postalCodeInput').isVisible())await form.locator('#payment-postalCodeInput').fill('D02 X285');
  step='submit_test_card';
  testCheckout(page.url());
  await form.getByRole('button',{name:/Pay and subscribe|Start trial|Subscribe/i}).click();
  if(label==='pro'){
   await expect.poll(async()=>{for(const frame of page.frames())if(await frame.getByText(/Your card was declined|card has been declined/i).first().isVisible().catch(()=>false)){form=frame;return true;}return false;},{timeout:30000}).toBe(true);
   const summary=await context.request.get(`${config.origin}/api/me/subscription`);
   if((await summary.json()).subscription!==null)throw new Error('Declined payment must not grant access');
   await page.screenshot({path:`${root}/pro-declined.png`,fullPage:true});
   console.log(JSON.stringify({decline_denied_access:true}));
   await form.locator('#payment-numberInput').fill('4242424242424242');
   testCheckout(page.url());
   await form.getByRole('button',{name:/Pay and subscribe|Start trial|Subscribe/i}).click();
  }
  step='return_and_confirmation';
  await page.waitForURL(`${config.origin}/billing/checkout/**`,{timeout:60000});
  await expect(page.locator('[data-payment-state]')).toHaveAttribute('data-state','active',{timeout:60000});
  await page.screenshot({path:`${root}/${label}-confirmed.png`,fullPage:true});
  await page.goto(`${config.origin}/subscription?lang=en`);
  await expect(page.locator('[data-subscription-state]')).toHaveText(label==='plus'?'Trial':'Active');
  await page.screenshot({path:`${root}/${label}-subscription.png`,fullPage:true});
  step='portal';
  await page.locator('[data-billing-portal]').click();
  await page.waitForURL('https://billing.stripe.com/**',{timeout:30000});
  await expect(page.locator('body')).toContainText(/Current subscription|Payment method/i,{timeout:30000});
  await page.screenshot({path:`${root}/${label}-portal.png`,fullPage:true});
  sameRun(config,JSON.parse(await fs.readFile(`${root}/result.json`,'utf8')));
  const result={run_id:config.run_id,real_browser_purchase:true,plan:label,real_portal_browser:true,real_portal_browser_loaded:true,decline_denied_access:label==='pro'};
  await fs.writeFile(`${root}/browser-${label}.json`,JSON.stringify(result),{mode:0o600});
  console.log(JSON.stringify(result));
 }
}catch(error){
 await page.screenshot({path:`${root}/${label}-failure.png`,fullPage:true}).catch(()=>{});
 console.log(JSON.stringify({failed_step:step,error_type:error.constructor.name,fields:await page.locator('input,select').evaluateAll(nodes=>nodes.map(n=>({id:n.id,name:n.name,type:n.type}))).catch(()=>[])}));
 process.exitCode=1;
}finally{await browser.close();}
