/* Handbalancer's Studio: local-time appearance, no account/network access.
 * Include before the main stylesheet. Integrate account sync separately.
 * Schedule is a product default: Light 07:00 <= t < 20:00, otherwise Dark.
 */
(function (root, factory) {
  const api=factory();
  if(typeof module==='object' && module.exports) module.exports=api;
  else root.StudioTheme=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const MODES=['auto','light','dark'];
  const normalize=value=>MODES.includes(value)?value:'auto';
  function resolve(value,date=new Date(),fallback='light'){
    const mode=normalize(value);
    if(mode!=='auto') return mode;
    if(!date || !Number.isFinite(date.getTime())) return fallback==='dark'?'dark':'light';
    const hour=date.getHours();
    return hour>=7 && hour<20?'light':'dark';
  }
  function read(storage,key){try{return normalize(storage.getItem(key));}catch(_){return 'auto';}}
  function write(storage,key,value){try{storage.setItem(key,normalize(value));return true;}catch(_){return false;}}
  function mount(options={}){
    const doc=options.document||document;
    const win=doc.defaultView;
    const node=doc.documentElement;
    const key=options.key||'studio.demo.appearance.v2';
    let storage=options.storage;
    if(!storage){try{storage=win.localStorage;}catch(_){storage=null;}}
    let preference=normalize(options.preference||read(storage,key));
    let locked=false, current=null, pending=null;
    const now=options.now||(()=>new Date());
    function fallback(){return win.matchMedia && win.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
    function syncControls(){
      doc.querySelectorAll('[data-appearance]').forEach(el=>{el.value=preference;});
    }
    function apply(force=false){
      const next=resolve(preference,now(),fallback());
      if(locked && preference==='auto' && current && next!==current && !force){
        pending=next; return current;
      }
      current=next;pending=null;
      node.dataset.theme=current;
      node.dataset.themePreference=preference;
      node.style.colorScheme=current;
      syncControls();
      doc.dispatchEvent(new win.CustomEvent('studio:appearance',{detail:{preference,appearance:current}}));
      return current;
    }
    function setPreference(value,persist=true){
      preference=normalize(value);
      const persisted=persist?write(storage,key,preference):null;
      apply(true);
      return {preference,appearance:current,persisted};
    }
    function setLocked(value){locked=Boolean(value);if(!locked)apply();}
    function onChange(e){if(e.target.matches('[data-appearance]'))setPreference(e.target.value);}
    function onStorage(e){if(e.key===key){preference=normalize(e.newValue);apply(true);}}
    const refresh=()=>apply();
    doc.addEventListener('change',onChange);
    doc.addEventListener('visibilitychange',refresh);
    doc.addEventListener('DOMContentLoaded',syncControls);
    win.addEventListener('pageshow',refresh);
    win.addEventListener('focus',refresh);
    win.addEventListener('storage',onStorage);
    const timer=win.setInterval(refresh,30000);
    apply(true);
    return {setPreference,setLocked,refresh,syncControls,
      state:()=>({preference,appearance:current,locked,pending}),
      destroy(){win.clearInterval(timer);doc.removeEventListener('change',onChange);doc.removeEventListener('visibilitychange',refresh);doc.removeEventListener('DOMContentLoaded',syncControls);win.removeEventListener('pageshow',refresh);win.removeEventListener('focus',refresh);win.removeEventListener('storage',onStorage);}
    };
  }
  return {normalize,resolve,read,write,mount};
});
