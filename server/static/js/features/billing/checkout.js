// Only presentation state is browser-owned. Subscription/owner/price come from the server.
const $=selector=>document.querySelector(selector);
const names={essential:'Essential',plus:'Plus',pro:'Pro','pro-plus':'Pro+'};
const prices={essential:'19.99',plus:'49.99',pro:'179.99','pro-plus':'299.99'};
const english=()=>document.documentElement.lang==='en';
const text=(uk,en)=>english()?en:uk;
const page=$('[data-billing-page]');
const statusPage=$('[data-payment-state]');
let session=null, summary=null, payment=null, selected='plus', pending=null;
let busy=false, timer=null, polls=0, generation=0;
const storageKey=()=>`studio:account:${session.user.id}:checkout`;
const validId=value=>typeof value==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
const paymentId=location.pathname.split('/').pop();
function stripeURL(value,host){try{const u=new URL(value);return u.protocol==='https:'&&u.hostname===host&&!u.username&&!u.password?u.href:null;}catch{return null;}}
function showError(){const el=$('[data-billing-error]');el.hidden=false;el.textContent=text('Не вдалося перевірити оплату. Ваш вибір збережено — спробуйте ще раз.','We could not check your payment. Your selection is saved — please try again.');}
async function request(path,options={}){
 const response=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(12000),...options});
 if(response.status===401){location.assign('/login');throw new Error('Unauthorized');}
 if(!response.ok)throw new Error('Unavailable');
 return response.json();
}
function active(sub){return sub&&['active','trialing'].includes(sub.status)&&Date.parse(sub.current_period_end)>Date.now();}
function render(){
 if(!$('[data-billing-error]').hidden)showError();
 if(page&&summary){
  const sub=summary.subscription, hasAccess=active(sub);
  $('[data-subscription-plan]').textContent=sub?names[sub.plan_code]||'—':text('Пакет ще не обрано','No plan yet');
  const badge=$('[data-subscription-state]');
  badge.dataset.state=!hasAccess?'inactive':Date.parse(sub.current_period_end)-Date.now()<=5*86400000?'expiring':'active';
  badge.textContent=hasAccess?(sub.status==='trialing'?text('Пробний період','Trial'):text('Активна','Active')):text('Неактивна','Inactive');
  $('[data-subscription-date]').textContent=sub?`${hasAccess?text('Діє до','Valid until'):text('Кінець періоду','Period ended')} ${new Intl.DateTimeFormat(english()?'en-GB':'uk-UA',{dateStyle:'medium'}).format(new Date(sub.current_period_end))}`:'';
  $('[data-billing-portal]').hidden=!summary.portal_available;
  const attempt=summary.active_attempt;
  $('[data-active-attempt]').hidden=!attempt;
  if(attempt&&validId(attempt.id))$('[data-active-link]').href=`/billing/checkout/${attempt.id}?lang=${english()?'en':'uk'}`;
  $('[data-billing-form]').hidden=!!attempt||hasAccess;
  for(const radio of document.querySelectorAll('[name=plan_code]')){radio.checked=radio.value===selected;radio.disabled=busy||!!pending;}
  const trial=summary.trial_available&&['essential','plus'].includes(selected);
  $('[data-trial-terms]').textContent=trial?text(`7 днів безкоштовно з карткою, потім €${prices[selected]} щомісяця. Один пробний період на акаунт.`,`7 days free with a card, then €${prices[selected]} monthly. One trial per account.`):text(`€${prices[selected]} щомісяця. Без пробного періоду.`,`€${prices[selected]} monthly. No trial period.`);
  $('[data-buy-package]').disabled=busy;
  $('[data-buy-package]').textContent=busy?text('Переходимо…','Opening…'):text('Продовжити у Stripe','Continue to Stripe');
 }
 if(statusPage&&payment){
  $('[data-payment-plan]').textContent=names[payment.plan_code]||'—';
  const confirmed=payment.state==='completed'&&active(summary?.subscription);
  const ended=['expired','failed'].includes(payment.state);
  statusPage.dataset.state=confirmed?'active':ended?'inactive':'pending';
  $('[data-payment-message]').textContent=confirmed?text('Підписку підтверджено. Дякуємо!','Your subscription is confirmed. Thank you!'):ended?text('Спроба оплати завершилася без покупки. Можна повернутися до вибору пакета.','This payment attempt ended without a purchase. You can return to the plan selection.'):payment.state==='open'?text('Оплату ще не завершено. Продовжіть на сторінці Stripe.','Payment is not complete yet. Continue on Stripe.'):payment.state==='completed'?text('Цю покупку підтверджено раніше. Поточний стан підписки дивіться в кабінеті.','This purchase was confirmed earlier. Check your current subscription in your studio.'):text('Очікуємо підтвердження Stripe. Це може зайняти трохи часу.','Waiting for Stripe confirmation. This may take a little time.');
  const resume=$('[data-resume-checkout]');
  const url=payment.state==='open'&&Date.parse(payment.expires_at)>Date.now()?stripeURL(payment.checkout_url,'checkout.stripe.com'):null;
  resume.hidden=!url;if(url)resume.href=url;else resume.removeAttribute('href');
  $('[data-payment-dashboard]').hidden=payment.state!=='completed';
  $('[data-retry-checkout]').hidden=payment.state!=='creating'||Date.parse(payment.expires_at)<Date.now()+30*60000;
  $('[data-retry-checkout]').disabled=busy;
  if(['completed','expired','failed'].includes(payment.state)){try{sessionStorage.removeItem(storageKey());}catch{/* optional storage */}}
 }
}
async function refresh(){
 if(busy||!session)return;
 const revision=generation;
 busy=true;clearTimeout(timer);
 try{
  // A completed attempt and its projection commit atomically. Read the attempt
  // first so its subsequent projection cannot be an older pre-confirmation snapshot.
  const attempt=statusPage?await request(`/api/me/checkout-attempts/${paymentId}`):null;
  const next=await request('/api/me/subscription');
  if(revision!==generation)return;
  summary=next;payment=attempt;$('[data-billing-error]').hidden=true;
  if(pending&&next.last_attempt?.idempotency_key===pending.key&&['completed','expired','failed'].includes(next.last_attempt.state)){
   pending=null;try{sessionStorage.removeItem(storageKey());}catch{/* optional storage */}
  }
  if(statusPage&&['creating','open','pending','needs_reconcile'].includes(payment.state)&&polls++<12&&!document.hidden)timer=setTimeout(refresh,5000);
 }catch{if(revision===generation)showError();}
 finally{busy=false;if(revision===generation)render();}
}
async function beginCheckout(intent){
 if(busy||!session)return;
 busy=true;pending=intent;
 try{sessionStorage.setItem(storageKey(),JSON.stringify(pending));}catch{/* same key stays in memory */}
 render();$('[data-billing-error]').hidden=true;
 const revision=generation;
 try{
  const result=await request('/api/checkout',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token,'Idempotency-Key':pending.key},body:JSON.stringify({plan_code:pending.plan,terms_version:'test-v1'})});
  if(revision!==generation)return;
  if(!validId(result.id))throw new Error('Invalid attempt');
  const url=stripeURL(result.checkout_url,'checkout.stripe.com');
  if(result.state==='open'&&!url)throw new Error('Invalid URL');
  location.assign(url||`/billing/checkout/${result.id}?lang=${english()?'en':'uk'}`);
 }catch{if(revision===generation)showError();}
 finally{busy=false;if(revision===generation)render();}
}
$('[data-billing-form]')?.addEventListener('submit',event=>{
 event.preventDefault();if(!summary||!$('[data-billing-consent]').checked)return;
 beginCheckout(pending??{key:crypto.randomUUID(),plan:selected});
});
$('[data-retry-checkout]')?.addEventListener('click',()=>{
 if(payment?.state==='creating'&&typeof payment.idempotency_key==='string')beginCheckout({key:payment.idempotency_key,plan:payment.plan_code});
});
$('[data-billing-portal]')?.addEventListener('click',async()=>{
 if(busy||!session)return;busy=true;render();
 const revision=generation;
 try{
  const result=await request('/api/billing-portal',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},body:'{}'});
  const url=stripeURL(result.url,'billing.stripe.com');if(!url)throw new Error('Invalid URL');
  if(revision===generation)location.assign(url);
 }catch{if(revision===generation)showError();}
 finally{busy=false;if(revision===generation)render();}
});
for(const radio of document.querySelectorAll('[name=plan_code]'))radio.addEventListener('change',()=>{if(!pending&&Object.hasOwn(names,radio.value)){selected=radio.value;render();}});
$('[data-refresh-billing]')?.addEventListener('click',()=>{polls=0;refresh();});
document.addEventListener('studio:language-changed',render);
document.addEventListener('studio:account',event=>{
 if(session&&event.detail.id!==session.user.id){++generation;clearTimeout(timer);session=null;summary=null;payment=null;location.replace('/login');}
});
window.addEventListener('pagehide',()=>{++generation;clearTimeout(timer);});
window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
async function start(){
 try{
  if(page?.dataset.enabled==='false')throw new Error('Billing unavailable');
  session=await request('/api/session');
  if(!session.authenticated||!session.user?.id||!session.csrf_token){location.replace('/login');return;}
  if(session.setup_required){location.replace('/profile');return;}
  try{
   const saved=localStorage.getItem('studio:public:plan');if(Object.hasOwn(names,saved))selected=saved;
   const draft=JSON.parse(sessionStorage.getItem(storageKey()));
   if(draft&&validId(draft.key)&&Object.hasOwn(names,draft.plan)){pending=draft;selected=draft.plan;}
  }catch{/* browser storage is optional */}
  await refresh();
 }catch{showError();}
}
start();
