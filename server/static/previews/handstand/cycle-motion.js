// One small, side-view skeleton. Hands stay at fixed floor anchors during support.
// Frames: time, hip, torso angle, rear/front feet, rear/front hands.
const stand = [[68,105],-90,[62,164],[74,164],[57,108],[82,108]];
const step = [[88,111],-78,[62,164],[112,164],[125,42],[133,47]];
const stride = [[75,108],-86,[62,164],[90,149],[98,105],[108,93]];
const lunge = [[100,116],-42,[64,164],[118,164],[153,124],[161,123]];
const plant = [[108,106],41,[62,133],[118,164],[166,164],[176,164]];
const split = [[161,76],81,[174,18],[113,109],[166,164],[176,164]];
const balance = [[171,75],90,[176,16],[166,16],[166,164],[176,164]];
const frames = [
  [0,...stand],[.06,...stand],[.14,...stride],[.22,...step],[.28,...lunge],
  [.34,...plant],
  [.43,[130,88],51,[90,45],[117,145],[166,164],[176,164]],
  [.50,...split],[.56,...balance],[.66,...balance],
  [.72,...split],[.80,...plant],[.87,...lunge],[.92,...step],
  [.96,...stride],[.98,...stand],[1,...stand],
];
const lerp = (a,b,t) => a+(b-a)*t;
const point = (a,b,t) => [lerp(a[0],b[0],t),lerp(a[1],b[1],t)];

function joint(start,end,length,bend) {
  const dx=end[0]-start[0], dy=end[1]-start[1];
  const distance=Math.max(.001,Math.hypot(dx,dy));
  const offset=Math.sqrt(Math.max(0,length*length-distance*distance/4));
  return [(start[0]+end[0])/2-bend*dy/distance*offset,
    (start[1]+end[1])/2+bend*dx/distance*offset];
}

export function poseAt(progress) {
  const t=Math.min(1,Math.max(0,progress));
  const index=Math.max(1,frames.findIndex(frame=>frame[0]>=t));
  const a=frames[index-1], b=frames[index];
  const fraction=(t-a[0])/(b[0]-a[0]);
  const ease=fraction*fraction*(3-2*fraction);
  const hip=point(a[1],b[1],ease);
  const angle=lerp(a[2],b[2],ease)*Math.PI/180;
  const shoulder=[hip[0]+40*Math.cos(angle),hip[1]+40*Math.sin(angle)];
  const head=[shoulder[0]+14*Math.cos(angle),shoulder[1]+14*Math.sin(angle)];
  const backFoot=point(a[3],b[3],ease), frontFoot=point(a[4],b[4],ease);
  const backHand=point(a[5],b[5],ease), frontHand=point(a[6],b[6],ease);
  return {hip,shoulder,head,backFoot,frontFoot,backHand,frontHand,
    backKnee:joint(hip,backFoot,30,-1),frontKnee:joint(hip,frontFoot,30,-1),
    backElbow:joint(shoulder,backHand,25,-1),frontElbow:joint(shoulder,frontHand,25,-1)};
}

export function drawPose(svg,progress) {
  const pose=poseAt(progress);
  const coordinates = p => p.map(value=>value.toFixed(2)).join(' ');
  const path = (name,points) => svg.querySelector(`[data-bone="${name}"]`)
    .setAttribute('d',points.map((p,i)=>(i?'L':'M')+coordinates(p)).join(' '));
  path('torso',[pose.hip,pose.shoulder]);
  for (const side of ['back','front']) {
    path(`${side}-leg`,[pose.hip,pose[`${side}Knee`],pose[`${side}Foot`]]);
    path(`${side}-arm`,[pose.shoulder,pose[`${side}Elbow`],pose[`${side}Hand`]]);
    const foot=pose[`${side}Foot`], hand=pose[`${side}Hand`];
    path(`${side}-foot`,[foot,[foot[0]+6,foot[1]]]);
    path(`${side}-hand`,[hand,[hand[0]+5,hand[1]]]);
  }
  svg.querySelector('[data-head]').setAttribute('cx',pose.head[0].toFixed(2));
  svg.querySelector('[data-head]').setAttribute('cy',pose.head[1].toFixed(2));
}

export function mountHandstandCycle(svg) {
  let elapsed=0, previous=null, frame=null, disposed=false;
  const root=document.documentElement;
  function tick(now) {
    if (disposed) return;
    if (!svg.isConnected) {dispose();return;}
    if (previous!==null) elapsed+=now-previous;
    previous=now;
    drawPose(svg,(elapsed%8200)/8200);
    frame=requestAnimationFrame(tick);
  }
  function sync() {
    cancelAnimationFrame(frame); previous=null;
    if (!document.hidden && root.dataset.paused!=='true') frame=requestAnimationFrame(tick);
  }
  const observer=new MutationObserver(sync);
  observer.observe(root,{attributes:true,attributeFilter:['data-paused']});
  document.addEventListener('visibilitychange',sync);
  function dispose() {
    disposed=true; cancelAnimationFrame(frame); observer.disconnect();
    document.removeEventListener('visibilitychange',sync);
  }
  drawPose(svg,0); sync();
  return dispose;
}
