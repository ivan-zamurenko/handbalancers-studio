import assert from 'node:assert/strict';
import {beforeEach, test} from 'node:test';
import {claimGuestDraft, cleanChoices, clearAccountDraft, readAccountDraft, readGuestDraft, saveGuestDraft}
  from '../../server/static/js/features/onboarding/draft.js';
import {clearAccountState} from '../../server/static/js/state/session.js';

const valid={goal_codes:['handstand'],self_reported_level:2,session_minutes:90,weekdays:[1,3,5],time_of_day:null};
const key='studio:guest:onboarding-draft';
function storage(){
  const data=new Map();
  return {getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k),
    get length(){return data.size;},key:i=>[...data.keys()][i]};
}
beforeEach(()=>{globalThis.sessionStorage=storage();globalThis.localStorage=storage();});

test('draft cannot smuggle identity, tier, body measurements or duplicate days',()=>{
  for(const extra of [{user_id:'b'},{tier:'pro'},{expected_revision:99},{birth_year:1990},
    {weekdays:[1,1]},{session_minutes:'90'},{self_reported_level:true}]){
    assert.equal(cleanChoices({...valid,...extra}),null);
  }
});

test('expired, future, malformed and oversized drafts are discarded',()=>{
  for(const raw of ['{','x'.repeat(3000),JSON.stringify({version:2,data:valid,expiresAt:Date.now()+60000}),
    JSON.stringify({version:1,data:valid,expiresAt:Date.now()-1}),
    JSON.stringify({version:1,data:valid,expiresAt:Date.now()+48*3600000})]){
    sessionStorage.setItem(key,raw);
    assert.equal(readGuestDraft(),null);
    assert.equal(sessionStorage.getItem(key),null);
  }
});

test('claim is account-scoped, cannot be inherited by a second user, logout clears it',()=>{
  saveGuestDraft(valid);
  assert.deepEqual(claimGuestDraft('a').data,valid);
  assert.equal(readGuestDraft(),null);
  assert.equal(claimGuestDraft('b'),null);
  assert.deepEqual(readAccountDraft('a').data,valid);
  clearAccountState('a');
  assert.equal(readAccountDraft('a'),null);
});

test('explicit discard clears only this account draft',()=>{
  saveGuestDraft(valid);claimGuestDraft('a');
  sessionStorage.setItem('studio:account:a:other','keep');
  clearAccountDraft('a');
  assert.equal(readAccountDraft('a'),null);
  assert.equal(sessionStorage.getItem('studio:account:a:other'),'keep');
});

test('storage error is not reported as a successful guest save',()=>{
  sessionStorage.setItem=()=>{throw new Error('blocked');};
  assert.throws(()=>saveGuestDraft(valid));
  assert.equal(readGuestDraft(),null);
});
