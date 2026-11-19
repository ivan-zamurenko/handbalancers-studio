import {readGuestDraft, saveGuestDraft} from './draft.js';

const form = document.querySelector('[data-guest-form]');
const steps = [...form.querySelectorAll('fieldset')];
const error = document.querySelector('[data-guest-error]');
const next = document.querySelector('[data-guest-next]');
const back = document.querySelector('[data-guest-back]');
const submit = document.querySelector('[data-guest-submit]');
const count = document.querySelector('[data-guest-count]');
let step = 0;
let busy = false;
const values = name => [...form.querySelectorAll(`input[name="${name}"]:checked`)].map(n=>n.value);

function show(index, focus = true) {
  step = index;
  steps.forEach((node,i)=>{node.hidden=i!==step;});
  back.hidden = step === 0;
  next.hidden = step === 1;
  submit.hidden = step !== 1;
  count.textContent = count.dataset.label.replace('{n}',step+1);
  document.querySelector('[data-guest-bar]').style.width = `${(step+1)*50}%`;
  error.hidden = true;
  if (focus) steps[step].querySelector('legend').focus();
}

function validate() {
  let first;
  for (const group of steps[step].querySelectorAll('[data-group]')) {
    const size = values(group.dataset.group).length;
    const bad = size < Number(group.dataset.min||0) || size > Number(group.dataset.max||99);
    group.setAttribute('aria-invalid',String(bad));
    if (bad && !first) first = group.querySelector('input');
  }
  if (first) { error.textContent=error.dataset.required; error.hidden=false; first.focus(); }
  return !first;
}

function syncLimits() {
  for (const group of form.querySelectorAll('[data-max]')) {
    const full=values(group.dataset.group).length>=Number(group.dataset.max);
    for(const input of group.querySelectorAll('input')) input.disabled=full&&!input.checked;
  }
}

form.addEventListener('change',syncLimits);
next.addEventListener('click',()=>{if(!busy&&validate())show(1);});
back.addEventListener('click',()=>{if(!busy)show(0);});
form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(busy||!validate())return;
  if(step===0){show(1);return;}
  busy=true;submit.disabled=true;back.disabled=true;form.setAttribute('aria-busy','true');
  // Snapshot actual controls, including selections restored without a change event.
  const data={goal_codes:values('goal_codes'), self_reported_level:Number(values('self_reported_level')[0]),
    session_minutes:Number(values('session_minutes')[0]), weekdays:values('weekdays').map(Number).sort((a,b)=>a-b),
    time_of_day:values('time_of_day')[0]??null};
  for (const input of form.querySelectorAll('input')) input.disabled = true;
  try {
    const response=await fetch('/api/onboarding/draft',{method:'POST',credentials:'same-origin',cache:'no-store',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal:AbortSignal.timeout(8000)});
    if(!response.ok)throw new Error('Request failed');
    const accepted=await response.json();
    try {saveGuestDraft(accepted);} catch {
      error.textContent=error.dataset.storage;error.hidden=false;return;
    }
    location.assign(`/plans?lang=${document.documentElement.lang==='en'?'en':'uk'}`);
  } catch {error.textContent=error.dataset.network;error.hidden=false;}
  finally {
    busy=false;submit.disabled=false;back.disabled=false;form.removeAttribute('aria-busy');
    for (const input of form.querySelectorAll('input')) input.disabled = false;
    syncLimits();
  }
});

const draft=readGuestDraft();
if(draft)for(const input of form.querySelectorAll('input')){
  const value=draft.data[input.name];
  input.checked=(Array.isArray(value)?value:[value]).map(String).includes(input.value);
}
for(const legend of form.querySelectorAll('legend'))legend.tabIndex=-1;
syncLimits();show(0,false);next.disabled=false;
