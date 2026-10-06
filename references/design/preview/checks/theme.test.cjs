const {test}=require('node:test');
const assert=require('node:assert/strict');
const theme=require('../assets/theme-controller.js');
const at=(h,m=0)=>new Date(2026,9,5,h,m);
test('Auto uses local wall clock and explicit boundaries',()=>{
 for(const [h,m,result] of [[0,0,'dark'],[6,59,'dark'],[7,0,'light'],[12,0,'light'],[19,59,'light'],[20,0,'dark'],[23,59,'dark']]){
  assert.equal(theme.resolve('auto',at(h,m)),result);
 }
});
test('Explicit choices override the clock',()=>{
 assert.equal(theme.resolve('dark',at(12)),'dark');
 assert.equal(theme.resolve('light',at(23)),'light');
});
test('Unknown preference is Auto; invalid clock has safe fallback',()=>{
 assert.equal(theme.normalize('broken'),'auto');
 assert.equal(theme.resolve('auto',new Date(NaN),'light'),'light');
 assert.equal(theme.resolve('auto',new Date(NaN),'dark'),'dark');
});
test('Blocked storage is nonfatal',()=>{
 const blocked={getItem(){throw new Error('blocked')},setItem(){throw new Error('blocked')}};
 assert.equal(theme.read(blocked,'key'),'auto');
 assert.equal(theme.write(blocked,'key','dark'),false);
});
test('Persistence stores the preference, not the current appearance',()=>{
 const values=new Map();const store={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};
 assert.equal(theme.write(store,'key','auto'),true);
 assert.equal(theme.read(store,'key'),'auto');
 assert.equal(values.get('key'),'auto');
});
