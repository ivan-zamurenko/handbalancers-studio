import test from 'node:test';
import assert from 'node:assert/strict';
import {poseAt} from '../../server/static/previews/handstand/cycle-motion.js';
const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
const close=(a,b)=>assert.ok(Math.abs(a-b)<.001, `${a} != ${b}`);

test('full sequence steps forward, inverts, steps back and closes the loop',()=>{
  const start=poseAt(0), step=poseAt(.24), peak=poseAt(.58);
  assert.ok(start.head[1]<start.hip[1]);
  assert.ok(step.frontFoot[0]>start.frontFoot[0]+35);
  assert.ok(peak.frontToe[1]<peak.frontFoot[1] && peak.frontFoot[1]<peak.hip[1]);
  assert.ok(peak.hip[1]<peak.shoulder[1] && peak.shoulder[1]<peak.frontHand[1]);
  assert.deepEqual(poseAt(1),start);
});

test('support has straight arms, a straight leading leg and planted hands',()=>{
  for(let i=360;i<=780;i++){
    const p=poseAt(i/1000);
    for(const [side,x] of [['back',178],['front',182]]){
      assert.deepEqual(p[side+'Hand'],[x,164]);
      close(distance(p[side+'Shoulder'],p[side+'Hand']),46);
    }
    close(distance(p.backHip,p.backFoot),60);
  }
});

test('limb lengths, floor contact and frame continuity survive the entire cycle',()=>{
  let previous;
  for(let i=0;i<=10000;i++){
    const p=poseAt(i/10000);
    for(const [name,point] of Object.entries(p)){
      assert.ok(point.every(Number.isFinite),name);
      assert.ok(point[1]<=164.001,`${name} below ground at ${i/10000}: ${point}`);
      if(previous) assert.ok(distance(point,previous[name])<.7,`jump: ${name} at ${i/10000}`);
    }
    close(distance(p.hip,p.shoulder),40);
    for(const side of ['front','back']){
      for(const [a,b,len] of [['Hip','Knee',30],['Knee','Foot',30],['Shoulder','Elbow',23],['Elbow','Hand',23]])
        close(distance(p[side+a],p[side+b]),len);
    }
    previous=p;
  }
});

test('playful balance opens the legs, softens the trailing knee and settles before a nod',()=>{
  const wobble=poseAt(.55),settle=poseAt(.94),nod=poseAt(.967);
  assert.ok(Math.abs(wobble.frontFoot[0]-wobble.backFoot[0])>30);
  assert.ok(distance(wobble.frontHip,wobble.frontFoot)<57);
  assert.deepEqual(settle.frontFoot,[66,164]);
  assert.deepEqual(nod.frontFoot,settle.frontFoot);
  assert.ok(nod.head[1]>settle.head[1]+1);
});
