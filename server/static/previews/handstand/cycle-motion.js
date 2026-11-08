// Side-view rig. The support chain is solved from the wrists, not interpolated
// between bent poses: wrist → shoulder → hip stays straight throughout the kick.
const rad = Math.PI/180;
const clamp = t => Math.max(0,Math.min(1,t));
const mix = (a,b,t) => a+(b-a)*t;
const smooth = t => {t=clamp(t);return t*t*(3-2*t);};
const polar = (p,length,angle) => [p[0]+length*Math.cos(angle*rad),p[1]+length*Math.sin(angle*rad)];
const blend = (a,b,t) => a.map((v,i)=>mix(v,b[i],t));

// Shape-preserving cubic interpolation: passing poses retain velocity, while
// anticipation, the apex and the finish can settle without overshooting.
function track(t,keys,startVelocity=0,endVelocity=0) {
  if(t<=keys[0][0]) return keys[0][1];
  if(t>=keys.at(-1)[0]) return keys.at(-1)[1];
  const i=keys.findIndex(k=>k[0]>t)-1;
  const slope=j=>(keys[j+1][1]-keys[j][1])/(keys[j+1][0]-keys[j][0]);
  const tangent=j=>{
    if(j===0) return startVelocity;
    if(j===keys.length-1) return endVelocity;
    const a=slope(j-1),b=slope(j);
    return a*b<=0?0:2*a*b/(a+b);
  };
  const h=keys[i+1][0]-keys[i][0], u=(t-keys[i][0])/h;
  return (2*u**3-3*u*u+1)*keys[i][1]+(u**3-2*u*u+u)*h*tangent(i)
    +(-2*u**3+3*u*u)*keys[i+1][1]+(u**3-u*u)*h*tangent(i+1);
}

// Hermite endpoints carry velocity across the floor-contact boundary.
function hermite(a,b,va,vb,u,duration) {
  return (2*u**3-3*u*u+1)*a+(u**3-2*u*u+u)*duration*va
    +(-2*u**3+3*u*u)*b+(u**3-u*u)*duration*vb;
}
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1];

function joint(a,b,length,bend=-1) {
  const dx=b[0]-a[0],dy=b[1]-a[1],d=Math.max(.00001,Math.hypot(dx,dy));
  const height=Math.sqrt(Math.max(0,length*length-d*d/4));
  return [(a[0]+b[0])/2-bend*dy/d*height,(a[1]+b[1])/2+bend*dx/d*height];
}

const plantHip=polar([180,164],-86,30);
const lungeHip=[98,118.64];
const rearStartAngle=Math.atan2(164-lungeHip[1],62-(lungeHip[0]-2))/rad;
const rearStartLength=Math.hypot(62-(lungeHip[0]-2),164-lungeHip[1]);
const releaseAngle=35; // Push off before the knee locks, then extend in flight.
const releaseHip=polar([182,164],-86,releaseAngle);
const releaseLength=Math.hypot(118-releaseHip[0],164-releaseHip[1]);
const releaseLegAngle=Math.atan2(164-releaseHip[1],118-releaseHip[0])/rad;

const contactSpeed=180;
const contactVelocity=[86*Math.sin(30*rad)*contactSpeed*rad,
  -86*Math.cos(30*rad)*contactSpeed*rad];
const releaseDirection=polar([0,0],1,releaseLegAngle);
const releaseHipVelocity=[86*Math.sin(releaseAngle*rad),-86*Math.cos(releaseAngle*rad)];
const releaseLengthVelocity=-dot(releaseHipVelocity,releaseDirection)*rad;
const releaseLegVelocity=-dot(releaseHipVelocity,[-releaseDirection[1],releaseDirection[0]])/releaseLength;
const releaseFlex=Math.acos(releaseLength/60)/rad;
const releaseFlexVelocity=-releaseLengthVelocity/(60*Math.sin(releaseFlex*rad))/rad;

export function poseAt(progress) {
  const time=clamp(progress);
  // Leave a short beat after landing for the character's pleased little nod.
  const t=time<=.78?time:mix(.78,1,clamp((time-.78)/.16));
  // Return is deliberately slower than the kick, with a different step rhythm.
  let phase=t;
  if(t>.78) phase=track(t,[[.78,.36],[.88,.24],[.96,.10],[1,0]],-1/1.375);
  let hip,angle,armAngle,armLength=46,backFoot,frontFoot;
  if(t>=.36 && t<=.78) {
    angle=track(t,[[.36,30],[.405,51],[.46,83],[.51,90.7],
      [.56,89.8],[.61,90],[.64,90],[.69,77],[.75,45],[.78,30]],contactSpeed,-contactSpeed);
    hip=polar([180,164],-86,angle);
    armAngle=angle;
    backFoot=polar([hip[0]-2,hip[1]],60,angle+180);
    if(angle<=releaseAngle) frontFoot=[118,164];
    else {
      const q=clamp((angle-releaseAngle)/(90-releaseAngle));
      // The trailing leg follows a long, clean arc; it joins after the first.
      const legAngle=hermite(releaseLegAngle,270,releaseLegVelocity,1,q,90-releaseAngle);
      // Animate knee flexion, not endpoint distance: locking the knee then has
      // continuous velocity, rather than a square-root snap from inverse IK.
      const extension=clamp((angle-releaseAngle)/25);
      const flex=hermite(releaseFlex,0,releaseFlexVelocity,0,extension,25);
      const length=60*Math.cos(flex*rad);
      frontFoot=polar([hip[0]+2,hip[1]],length,legAngle+(angle>90?angle-90:0));
    }
  } else if(phase>=.24) {
    const q=(phase-.24)/.12;
    hip=lungeHip.map((v,i)=>hermite(v,plantHip[i],0,contactVelocity[i],q,.12));
    angle=hermite(-60,30,0,contactSpeed,q,.12);
    armAngle=angle;
    const rearAngle=hermite(rearStartAngle,210,0,contactSpeed,q,.12);
    const rearFlex=Math.acos(rearStartLength/60)*(1-smooth(q));
    backFoot=polar([hip[0]-2,hip[1]],60*Math.cos(rearFlex),rearAngle);
    frontFoot=[118,164];
  } else {
    hip=[track(phase,[[0,64],[.06,64],[.12,67],[.24,98]]),
      track(phase,[[0,104],[.06,104],[.12,105],[.24,118.64]])];
    angle=track(phase,[[0,-90],[.08,-90],[.14,-86],[.24,-60]]);
    armAngle=track(phase,[[0,78],[.035,78],[.13,-94],[.20,-78],[.24,-60]]);
    armLength=track(phase,[[0,44],[.08,42],[.18,46],[.24,46]]);
    const stride=smooth((phase-.10)/.14);
    backFoot=[62,164];
    frontFoot=[mix(66,118,stride),164-16*Math.sin(Math.PI*stride)];
  }
  if(t>.88) {
    armAngle=track(t,[[.88,-60],[.95,65],[1,78]]);
    armLength=track(t,[[.88,46],[.96,44],[1,44]]);
  }
  const shoulder=polar(hip,40,angle);
  // Keep the head outside the supporting arm silhouette; a small preparatory
  // nod and a relaxed settling pose provide character without extra effects.
  const head=polar(shoulder,14,angle);
  head[0]+=-Math.sin(angle*rad)*4;
  head[1]+=Math.cos(angle*rad)*4;
  const nod=track(time,[[0,0],[.035,1],[.075,0],[.94,0],[.967,1],[1,0]]);
  head[0]+=.5*nod;
  head[1]+=.4*nod;
  const pose={hip,shoulder,head};
  for(const [side,offset,foot] of [['back',-2,backFoot],['front',2,frontFoot]]) {
    const origin=[hip[0]+offset,hip[1]], top=[shoulder[0]+offset,shoulder[1]];
    const hand=t>=.36 && t<=.78?[180+offset,164]:polar(top,armLength,armAngle);
    const knee=joint(origin,foot,30);
    const elbow=joint(top,hand,23,1);
    const air=smooth((164-foot[1])/12);
    const pointed=polar(foot,6,Math.atan2(foot[1]-knee[1],foot[0]-knee[0])/rad);
    const toe=blend([foot[0]+6,foot[1]],pointed,air);
    Object.assign(pose,{[side+'Hip']:origin,[side+'Shoulder']:top,[side+'Foot']:foot,
      [side+'Knee']:knee,[side+'Hand']:hand,[side+'Elbow']:elbow,[side+'Toe']:toe});
  }
  return pose;
}

export function drawPose(svg,progress) {
  const pose=poseAt(progress);
  const coordinates=p=>p.map(value=>value.toFixed(2)).join(' ');
  const path=(name,points)=>svg.querySelector('[data-bone="'+name+'"]')
    .setAttribute('d',points.map((p,i)=>(i?'L':'M')+coordinates(p)).join(' '));
  path('torso',[pose.hip,pose.shoulder]);
  path('neck',[pose.shoulder,pose.head]);
  for(const side of ['back','front']) {
    path(side+'-leg',[pose[side+'Hip'],pose[side+'Knee'],pose[side+'Foot']]);
    path(side+'-arm',[pose[side+'Shoulder'],pose[side+'Elbow'],pose[side+'Hand']]);
    path(side+'-foot',[pose[side+'Foot'],pose[side+'Toe']]);
    const hand=pose[side+'Hand'];
    path(side+'-hand',[hand,[hand[0]+4,hand[1]]]);
  }
  const shadow=svg.querySelector('[data-contact-shadow]');
  shadow.setAttribute('cx',pose.hip[0].toFixed(2));
  shadow.setAttribute('rx',(16+18*Math.abs(pose.shoulder[0]-pose.hip[0])/40).toFixed(2));
  const head=svg.querySelector('[data-head]');
  head.setAttribute('cx',pose.head[0].toFixed(2));
  head.setAttribute('cy',pose.head[1].toFixed(2));
  // Two tiny eyes follow the floor during support, then soften on landing.
  const t=clamp(progress), lookingDown=smooth((t-.25)/.1)*(1-smooth((t-.80)/.1));
  const blink=track(t,[[0,0],[.04,0],[.047,1],[.058,0],[.95,0],[.968,1],[.985,0],[1,0]]);
  const eyeY=pose.head[1]-1+4*lookingDown;
  for(const [side,offset] of [['left',2],['right',5.5]]) {
    const x=pose.head[0]+offset;
    path('eye-'+side,[[x-.7*blink,eyeY],[x+.2+.7*blink,eyeY+.4*(1-blink)]]);
  }
}

export function mountHandstandCycle(svg) {
  let elapsed=0, previous=null, frame=null, disposed=false;
  const root=document.documentElement;
  function tick(now) {
    if (disposed) return;
    if (!svg.isConnected) {dispose();return;}
    if (previous!==null) elapsed+=now-previous;
    previous=now;
    drawPose(svg,(elapsed%6600)/6600);
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
