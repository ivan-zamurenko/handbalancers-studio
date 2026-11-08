import test from 'node:test';
import assert from 'node:assert/strict';
import {poseAt} from '../../server/static/previews/handstand/cycle-motion.js';

test('standing, forward step, planted hands, handstand and return form a complete loop', () => {
  const start=poseAt(0), step=poseAt(.22), plant=poseAt(.34), peak=poseAt(.6);
  assert.ok(start.head[1]<start.hip[1] && start.hip[1]<start.frontFoot[1]);
  assert.equal(start.frontFoot[1],164);
  assert.ok(step.frontFoot[0]>start.frontFoot[0]+30);
  assert.equal(plant.frontHand[1],164);
  assert.ok(peak.frontFoot[1]<peak.hip[1] && peak.hip[1]<peak.shoulder[1]);
  assert.ok(peak.shoulder[1]<peak.frontHand[1]);
  assert.deepEqual(poseAt(1),start);
  assert.deepEqual(poseAt(0.98),start);
});

test('hands stay planted throughout the kick and exit; joints stay above the floor', () => {
  for (let i=0;i<=1000;i++) {
    const t=i/1000, pose=poseAt(t);
    for (const point of Object.values(pose)) {
      assert.ok(point.every(Number.isFinite));
      assert.ok(point[1]<=164.001,`below ground at ${t}`);
    }
    if(t>=.34 && t<=.80) {
      assert.deepEqual(pose.frontHand,[176,164]);
      assert.deepEqual(pose.backHand,[166,164]);
    }
    assert.ok(Math.abs(Math.hypot(pose.shoulder[0]-pose.hip[0],pose.shoulder[1]-pose.hip[1])-40)<.001);
    for(const side of ['back','front']) {
      for(const [from,to,length] of [['hip',`${side}Knee`,30],[`${side}Knee`,`${side}Foot`,30],
        ['shoulder',`${side}Elbow`,25],[`${side}Elbow`,`${side}Hand`,25]]) {
        assert.ok(Math.abs(Math.hypot(pose[from][0]-pose[to][0],pose[from][1]-pose[to][1])-length)<.001);
      }
    }
  }
});
