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

// Latest owner request replaces the exaggerated split/nod with a natural hold.
test('natural handstand joins straight legs and returns to a grounded stance',()=>{
  for(const t of [.53,.57,.61]){
    const p=poseAt(t);
    assert.ok(Math.abs(p.frontFoot[0]-p.backFoot[0])<8);
    close(distance(p.frontHip,p.frontFoot),60);
    close(distance(p.backHip,p.backFoot),60);
  }
  assert.deepEqual(poseAt(.96).frontFoot,[66,164]);
  assert.deepEqual(poseAt(.96).backFoot,[62,164]);
});

test('weight transfer keeps moving through the hand contact transition',()=>{
  const dt=.0001;
  const before=poseAt(.36-dt),contact=poseAt(.36),after=poseAt(.36+dt);
  const speedBefore=distance(before.hip,contact.hip)/dt;
  const speedAfter=distance(after.hip,contact.hip)/dt;
  assert.ok(speedBefore>40 && speedAfter>40,'hips must not stop at hand contact');
  assert.ok(Math.abs(speedBefore-speedAfter)<10,'contact must not abruptly change hip speed');
});

test('hand contact and release preserve joint velocities; push-off starts from rest',()=>{
  const dt=.00001;
  const velocity=(a,b)=>a.map((v,i)=>(b[i]-v)/dt);
  for(const t of [.36,.78]){
    for(const key of ['hip','backKnee','backFoot','frontHand']){
      const a=poseAt(t-dt)[key],p=poseAt(t)[key],b=poseAt(t+dt)[key];
      assert.ok(distance(velocity(a,p),velocity(p,b))<1, `velocity jump: ${key} at ${t}`);
    }
  }
  // Locate the instant the previously planted foot begins lifting.
  let low=.36,high=.41;
  for(let i=0;i<40;i++){
    const mid=(low+high)/2;
    if(poseAt(mid).frontFoot[1]>=164-1e-9)low=mid;else high=mid;
  }
  const foot=poseAt(low).frontFoot,next=poseAt(low+dt).frontFoot;
  assert.ok(distance(foot,next)/dt<1,'push-off must accelerate from rest');
});
