(() => {
  "use strict";

  const W = 791, H = 1050, COLS = 113, ROWS = 105, CW = 7, CH = 10;
  const TAU = Math.PI * 2, LOOP = 20;
  const T_GROW = [0.5, 3], T_BUDS = [2.5, 3.6], T_PAPER = [2.9, 4.1];
  const T_RIBBON = 4.25, T_BLOSSOM = [4.4, 5.1], GROWN = 5.1;
  const T_OPEN = 5, STAGGER = 0.38, OPEN = 2.6, T_GLEAM = [14.6, 15.8];
  const T_FALL = 15.2, T_MSG = 13, FLASH = 0.6, STEPS = 50;
  const POOLS = ["1il!;:", "rtfjcvxz=+", "aeoun0{}[]<>", "08B$#&%Q"];
  const TAG = { STEM:0, LEAF:1, SEPAL:2, PETAL:3, EDGE:4, GLINT:5, PAPER:6, PAPER_IN:7,
    RIBBON:8, DUST:9, GOLD:10, FOLIAGE:11, BLOSSOM:12, STAR_PINK:13, STAR_BLUE:14 };
  const COLORS = [
    [70,200,96],[52,196,84],[80,206,100],[255,34,64],[255,120,146],[255,255,255],
    [212,220,236],[128,136,156],[255,190,80],[220,228,245],[255,214,150],
    [34,130,62],[255,244,248],[255,150,190],[170,205,255]
  ];
  const SHADES = [
    [[255,22,52],[255,90,112]], [[255,70,140],[255,150,190]],
    [[255,34,64],[255,110,130]], [[255,120,176],[255,186,214]],
    [[255,50,76],[255,126,144]]
  ];
  const ROSE_COLOURS = [SHADES[0], SHADES[1], SHADES[2], SHADES[1], SHADES[2], SHADES[1],
    SHADES[2], SHADES[3], SHADES[4], SHADES[0], SHADES[3], SHADES[4], SHADES[0],
    SHADES[3], SHADES[4], SHADES[0], SHADES[3], SHADES[4], SHADES[0]];
  const canvas = document.getElementById("bouquet");
  const ctx = canvas.getContext("2d", { alpha: false });
  const music = document.getElementById("music");
  const soundButton = document.getElementById("sound");
  const artCanvas = document.createElement("canvas");
  artCanvas.width = W; artCanvas.height = H;
  const art = artCanvas.getContext("2d");
  const trailCanvas = document.createElement("canvas");
  trailCanvas.width = W; trailCanvas.height = H;
  const trail = trailCanvas.getContext("2d");
  const glyphs = new Array(COLS * ROWS).fill("");
  const rgb = new Uint8ClampedArray(COLS * ROWS * 3);
  const steady = new Uint8Array(COLS * ROWS);
  let running = true, elapsed = 0, lastTime = 0, musicOn = false, audioStarting = false;

  const clamp = (x, a=0, b=1) => Math.max(a, Math.min(b, x));
  const smooth = x => { x = clamp(x); return x*x*(3-2*x); };
  const vadd = (a,b) => [a[0]+b[0],a[1]+b[1],a[2]+b[2]];
  const vsub = (a,b) => [a[0]-b[0],a[1]-b[1],a[2]-b[2]];
  const vmul = (a,k) => [a[0]*k,a[1]*k,a[2]*k];
  const dot = (a,b) => a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const norm = a => Math.hypot(a[0],a[1],a[2]);
  const unit = a => { const n=norm(a)||1; return [a[0]/n,a[1]/n,a[2]/n]; };
  function rng(seed) {
    let a = seed >>> 0;
    return () => { a += 0x6D2B79F5; let t=a; t=Math.imul(t^(t>>>15),t|1); t^=t+Math.imul(t^(t>>>7),t|61); return ((t^(t>>>14))>>>0)/4294967296; };
  }
  function matMul(a,b) {
    const r = new Array(9);
    for(let i=0;i<3;i++) for(let j=0;j<3;j++) r[3*i+j]=a[3*i]*b[j]+a[3*i+1]*b[3+j]+a[3*i+2]*b[6+j];
    return r;
  }
  function matVec(m,v) { return [m[0]*v[0]+m[1]*v[1]+m[2]*v[2],m[3]*v[0]+m[4]*v[1]+m[5]*v[2],m[6]*v[0]+m[7]*v[1]+m[8]*v[2]]; }
  function spinY(a) { const c=Math.cos(a),s=Math.sin(a); return [c,0,s,0,1,0,-s,0,c]; }
  function turnTo(d) {
    d=unit(d); const y=[0,1,0], v=cross(y,d), c=dot(y,d), n=norm(v);
    if(n<1e-9) return [1,0,0,0,1,0,0,0,1];
    const x=v[0], yy=v[1], z=v[2];
    const k=[0,-z,yy,z,0,-x,-yy,x,0];
    const k2=matMul(k,k), out=[];
    for(let i=0;i<9;i++) out[i]=(i%4===0?1:0)+k[i]+k2[i]/(1+c);
    return out;
  }
  function spinPoint(p,a) { const c=Math.cos(a),s=Math.sin(a); return [c*p[0]+s*p[2],p[1],-s*p[0]+c*p[2]]; }
  function dome(tilt,around) { return [Math.sin(tilt)*Math.sin(around),Math.cos(tilt),Math.sin(tilt)*Math.cos(around)]; }

  const DOME=[0,-0.38,0], DOME_R=0.64, WAIST=[0,-0.62,0], BOTTOM_Y=-1.10;
  const ROSE_SIZE=0.30, RING_TILT=0.47;
  const dirs=[dome(0,0)];
  for(let k=0;k<6;k++) dirs.push(dome(RING_TILT,TAU*k/6+TAU/12));
  for(let k=0;k<12;k++) dirs.push(dome(2*RING_TILT,TAU*k/12));
  const rosePos=dirs.map(d=>vadd(DOME,vmul(d,DOME_R)));
  const turnRng=rng(5), roseTurn=dirs.map(d=>matMul(turnTo(d),spinY(turnRng()*TAU)));
  const order=[0,1,4,2,5,3,6,...Array.from({length:12},(_,j)=>7+(5*j)%12)];
  const roseStart=new Array(19);
  order.forEach((k,i)=>roseStart[k]=T_OPEN+STAGGER*i);
  const stemTop=Math.max(...rosePos.map(p=>p[1]));
  const growTime=y=>T_GROW[0]+(T_GROW[1]-T_GROW[0])*clamp((y-BOTTOM_Y)/(stemTop-BOTTOM_Y));
  const budRng=rng(23), buds=rosePos.map(p=>T_BUDS[0]+(T_BUDS[1]-T_BUDS[0]-0.35)*(p[1]+0.01)/(stemTop+0.01)+0.35*budRng());
  const BLOSSOM_N=110, blossomRng=rng(41);
  const blossomSeeds=Array.from({length:BLOSSOM_N},()=>[blossomRng(),blossomRng(),blossomRng()]);
  const blossomPos=blossomSeeds.map(q=>vadd(DOME,vmul([Math.sin(2*RING_TILT+0.12+0.30*q[0])*Math.sin(q[1]*TAU),
    Math.cos(2*RING_TILT+0.12+0.30*q[0]),Math.sin(2*RING_TILT+0.12+0.30*q[0])*Math.cos(q[1]*TAU)],DOME_R+0.10)));
  const blossomAppear=blossomSeeds.map(q=>T_BLOSSOM[0]+(T_BLOSSOM[1]-T_BLOSSOM[0])*q[2]);
  const fallRng=rng(17), falls=Array.from({length:18},()=>Array.from({length:8},fallRng));
  const fallFrom=dirs.map((d,k)=>({d,k})).filter(x=>x.d[2]>-0.3).map(x=>x.k);
  const popRng=rng(13), pops=Array.from({length:19},()=>Array.from({length:14},()=>Array.from({length:4},popRng)));
  const starRng=rng(21), stars=Array.from({length:460},()=>Array.from({length:6},starRng));
  const dewRng=rng(31), dewOff=Array.from({length:14},()=>dewRng()*10), dewEvery=Array.from({length:14},()=>2+dewRng()*2);
  const viewEye=[0,1.75,4], target=[0,-0.28,0], forward=unit(vsub(target,viewEye));
  const right=unit(cross(forward,[0,1,0])), up=cross(right,forward), view=vmul(forward,-1);
  const geometryCache=new Map(), sepalCache=new Map(), roseCache=new Array(19);
  const base=[];

  function gridMesh(rows,cols,fn,outwardFn) {
    const p=new Array(rows*cols);
    for(let r=0;r<rows;r++) for(let c=0;c<cols;c++) p[r*cols+c]=fn(r,c);
    const n=new Array(p.length);
    for(let r=0;r<rows;r++) for(let c=0;c<cols;c++) {
      const a=p[r*cols+Math.min(cols-1,c+1)], b=p[r*cols+Math.max(0,c-1)];
      const d=p[Math.min(rows-1,r+1)*cols+c], e=p[Math.max(0,r-1)*cols+c];
      let normal=unit(cross(vsub(a,b),vsub(d,e)));
      const out=outwardFn(r,c,p[r*cols+c]);
      if(dot(normal,out)<0) normal=vmul(normal,-1);
      n[r*cols+c]=normal;
    }
    return {p,n};
  }
  function addMesh(mesh,tag,part,appear,pop=false,center=[0,0,0],opts={}) {
    for(let i=0;i<mesh.p.length;i++) base.push({
      p:mesh.p[i],n:mesh.n[i],tag,part:typeof part==="function"?part(i):part,
      appear:typeof appear==="function"?appear(i,mesh.p[i]):appear,pop,
      center:typeof center==="function"?center(i,mesh.p[i]):center,
      rim:opts.rim?opts.rim(i):false,gain:opts.gain||1,gloss:tag===TAG.RIBBON?0.9:0.3
    });
  }
  function tube(curve,radius,around) {
    const p=[],n=[];
    for(let i=0;i<curve.length;i++) {
      const d=unit(vsub(curve[Math.min(curve.length-1,i+1)],curve[Math.max(0,i-1)]));
      let side=unit(cross(d,[0,0,1])); if(norm(side)<1e-8) side=[1,0,0];
      const upv=cross(side,d);
      for(let j=0;j<around;j++) {
        const a=TAU*j/around, normal=vadd(vmul(side,Math.cos(a)),vmul(upv,Math.sin(a)));
        p.push(vadd(curve[i],vmul(normal,radius))); n.push(normal);
      }
    }
    return {p,n};
  }
  function buildBase() {
    for(let k=0;k<9;k++) {
      const spot=[0.026*Math.sin(1.7*k)*(k>0),0,0.026*Math.cos(1.7*k)*(k>0)];
      const top=vadd(vadd(WAIST,spot),[0,0.10,0]);
      const end=vadd(vadd(WAIST,vmul(spot,2.4)),[0,BOTTOM_Y-WAIST[1],0]);
      const curve=Array.from({length:40},(_,i)=>vadd(top,vmul(vsub(end,top),i/39)));
      addMesh(tube(curve,0.013,6),TAG.STEM,1,(_,p)=>growTime(p[1]));
    }
    for(let k=0;k<19;k++) {
      const b=vsub(rosePos[k],vmul(dirs[k],0.02));
      const start=vadd(vadd(WAIST,[0,0.10,0]),[0.026*Math.sin(1.7*k),0,0.026*Math.cos(1.7*k)]);
      const bend=[0.35*b[0],0.5*(start[1]+b[1]),0.35*b[2]];
      const curve=Array.from({length:30},(_,i)=>{const u=i/29,v=1-u;return vadd(vadd(vmul(start,v*v),vmul(bend,2*v*u)),vmul(b,u*u));});
      addMesh(tube(curve,0.011,5),TAG.STEM,1,(_,p)=>growTime(p[1]));
    }
    const foliage=gridMesh(90,20,(r,c)=>{
      const tilt=1.25*c/19,a=TAU*r/90,rad=0.60+0.012*Math.sin(7*a+14*tilt);
      return vadd(DOME,vmul([Math.sin(tilt)*Math.sin(a),Math.cos(tilt),Math.sin(tilt)*Math.cos(a)],rad));
    },()=>[0,1,0]);
    addMesh(foliage,TAG.FOLIAGE,50,(i)=>{const tilt=1.25*(i%20)/19,start=growTime(0);return start+(T_GROW[1]-start)*tilt/1.25;},false,[0,0,0],{gain:0.55});
    for(let j=1;j<7;j++) {
      const a=TAU*j/8+TAU/16, b=[0.60*Math.sin(a),-0.17,0.60*Math.cos(a)], d=unit([Math.sin(a),0.05,Math.cos(a)]), wide=unit(cross(d,[0,1,0])), upv=cross(wide,d), len=0.30+0.03*Math.sin(5*a);
      const leaf=gridMesh(11,34,(r,c)=>{
        const s=c/33,w=-1+2*r/10,half=0.30*len*Math.sqrt(s)*Math.pow(1-s,0.8)*1.9*(1+0.06*Math.sin(s*40));
        const crease=0.10*len*w*w,curl=-0.28*len*Math.pow(s,1.8);
        return vadd(vadd(vadd(b,vmul(d,s*len)),vmul(wide,w*half)),vmul(upv,crease+curl));
      },()=>upv);
      const app=growTime(b[1])+0.12*j;
      addMesh(leaf,TAG.LEAF,20+j,(i)=>app+0.5*((i%34)/33));
    }
    const paper=gridMesh(28,150,(r,c)=>{
      const a=TAU*c/150,v=r/27,top=-0.15+0.60*(1-Math.cos(a))/2+0.03*Math.cos(9*a);
      const rad=(0.075+(0.645+0.20*(1-Math.cos(a))/2)*Math.pow(v,0.75))*(1+0.07*v*Math.sin(9*a));
      const y=WAIST[1]+v*(top-WAIST[1]); return [rad*Math.sin(a),y,rad*Math.cos(a)];
    },(r,c)=>[Math.sin(TAU*c/150),0,Math.cos(TAU*c/150)]);
    addMesh(paper,TAG.PAPER,60,(i)=>{const c=i%150,r=Math.floor(i/150),a=TAU*c/150,v=r/27,wrap=(1+Math.cos(a))/2;return T_PAPER[0]+(T_PAPER[1]-T_PAPER[0])*(0.6*wrap+0.4*v);},false,[0,0,0],{rim:i=>Math.floor(i/150)/27>0.965});
    buildRibbon();
  }
  function buildRibbon() {
    const knot=vadd(WAIST,[0,0,0.10]);
    const band=gridMesh(6,120,(r,c)=>[0.09*Math.sin(TAU*c/120),WAIST[1]+0.022*(-1+2*r/5),0.09*Math.cos(TAU*c/120)],(r,c)=>[Math.sin(TAU*c/120),0,Math.cos(TAU*c/120)]);
    addMesh(band,TAG.RIBBON,70,T_RIBBON,true,WAIST);
    for(const [side,part] of [[-1,71],[1,72]]) {
      const loop=gridMesh(9,80,(r,c)=>{const u=TAU*c/79,q=r/8,rx=0.03+0.055*q,ry=0.010+0.036*q,tip=side*0.30;
        let x=side*(0.02+rx+rx*Math.cos(u+Math.PI)),y=ry*Math.sin(u);
        const xx=x*Math.cos(tip)-y*Math.sin(tip),yy=x*Math.sin(tip)+y*Math.cos(tip),z=0.03*Math.sin(u/2)**2+0.015*q;
        return vadd(knot,[xx,yy,z]);},()=>[0,0.3,1]);
      addMesh(loop,TAG.RIBBON,part,T_RIBBON,true,knot);
    }
    for(const [side,part] of [[-1,73],[1,74]]) {
      const tail=gridMesh(7,40,(r,c)=>{const s=c/39,w=-1+2*r/6;
        const center=[side*(0.03+0.08*s),-0.02-0.22*s,0.03+0.03*Math.sin(3*s)];
        const across=[0.030*Math.cos(0.4*side),0.030*Math.sin(0.4*side),0];
        return vadd(knot,vadd(center,vmul(across,w)));},()=>[0,0,1]);
      for(let i=0;i<tail.p.length;i++) if((i%40)/39 < 1-0.10*(1-Math.abs(-1+2*Math.floor(i/40)/6)))
        base.push({p:tail.p[i],n:tail.n[i],tag:TAG.RIBBON,part,appear:T_RIBBON,pop:true,center:knot,rim:false,gain:1,gloss:0.9});
    }
    const knotMesh=gridMesh(6,40,(r,c)=>{const u=TAU*c/40,q=r/5;return vadd(knot,[0.032*q*Math.cos(u),0.028*q*Math.sin(u),0.035-0.02*q*q]);},()=>[0,0,1]);
    addMesh(knotMesh,TAG.RIBBON,75,T_RIBBON,true,knot);
  }
  buildBase();

  const ANGLE_MIN=2.2*Math.PI, ANGLE_MAX=20*Math.PI;
  function roseMesh(open) {
    const key=Math.round(open*STEPS)/STEPS;
    if(geometryCache.has(key)) return geometryCache.get(key);
    const spread=1.4+4.2*key, wrap=smooth(key/0.7);
    const mesh=gridMesh(10,300,(r,c)=>{
      const a=ANGLE_MIN+(ANGLE_MAX-ANGLE_MIN)*c/299,l=r/9,lean=Math.PI/2*Math.exp(-a/(spread*Math.PI));
      const mod=((3.6*a)%TAU+TAU)%TAU;
      const width=1-0.5*Math.pow(1.25*Math.pow(1-mod/Math.PI,2)-0.25,2);
      const cup=1.95653*l*l*Math.pow(1.27689*l-1,2)*Math.sin(lean);
      const rad=width*(l*Math.sin(lean)+cup*Math.cos(lean));
      let x=rad*Math.sin(a)*0.8,z=rad*Math.cos(a)*0.8,y=(width*(l*Math.cos(lean)-cup*Math.sin(lean)))*0.8;
      const scale=0.72+0.28*wrap; x*=scale;z*=scale;y*=0.66+0.34*wrap;
      return [x,y,z];
    },(r,c)=>{const a=ANGLE_MIN+(ANGLE_MAX-ANGLE_MIN)*c/299;return [Math.sin(a),0.3,Math.cos(a)];});
    const petalId=mesh.p.map((_,i)=>Math.floor(3.6*(ANGLE_MIN+(ANGLE_MAX-ANGLE_MIN)*(i%300)/299)/TAU)-Math.floor(3.6*ANGLE_MIN/TAU));
    const rim=mesh.p.map((_,i)=>Math.floor(i/300)/9>0.92);
    const result={...mesh,petalId,rim,outer:mesh.p.map((_,i)=>1-(ANGLE_MIN+(ANGLE_MAX-ANGLE_MIN)*(i%300)/299-ANGLE_MIN)/(ANGLE_MAX-ANGLE_MIN))};
    geometryCache.set(key,result); return result;
  }
  function sepalMesh(open) {
    const key=Math.round(open*10)/10;
    if(sepalCache.has(key)) return sepalCache.get(key);
    const allP=[],allN=[];
    for(let i=0;i<5;i++) {
      const a=TAU*i/5+0.6,out=[Math.sin(a),0,Math.cos(a)],side=[Math.cos(a),0,-Math.sin(a)];
      const b0=vadd([0,0.03,0],vmul(out,0.03)),b1=vadd(vmul(out,0.16),[0,0.10-0.10*key,0]);
      const reach=0.24+0.06*key,droop=0.10+0.14*key,b2=vsub(vmul(out,reach),[0,droop,0]);
      const m=gridMesh(3,10,(r,c)=>{const u=c/9,w=-1+r;const p=vadd(vadd(vmul(b0,(1-u)**2),vmul(b1,2*(1-u)*u)),vmul(b2,u*u));
        const half=0.05*Math.sin(Math.PI*Math.min(u*1.5,1)/2)*(1-u)**0.7;
        return vadd(vadd(p,vmul(side,w*half)),[0,0.05*w*w*(1-u)-0.28*0.05*u**1.8,0]);},()=>[0,1,0]);
      allP.push(...m.p);allN.push(...m.n);
    }
    const result={p:allP,n:allN};sepalCache.set(key,result);return result;
  }
  const roseOpenNow=new Array(19).fill(-1);
  function getRose(k,open,flash) {
    const openKey=Math.round(open*STEPS)/STEPS, flashKey=Math.round(flash*10)/10;
    const cache=roseCache[k];
    if(cache&&cache.open===openKey&&cache.flash===flashKey)return cache;
    const petal=roseMesh(openKey),sep=sepalMesh(openKey),R=roseTurn[k],size=ROSE_SIZE*(1+0.12*flashKey),pos=rosePos[k],shade=ROSE_COLOURS[k];
    const vertices=[];
    for(let i=0;i<petal.p.length+sep.p.length;i++) {
      const isPetal=i<petal.p.length,j=isPetal?i:i-petal.p.length;
      const local=isPetal?petal.p[j]:sep.p[j], normal=isPetal?petal.n[j]:sep.n[j];
      const p=vadd(pos,matVec(R,vmul(local,size))), n=matVec(R,normal);
      const tag=isPetal?(petal.rim[j]?TAG.EDGE:TAG.PETAL):TAG.SEPAL;
      const part=isPetal?1000+100*k+petal.petalId[j]:40+k;
      const tone=isPetal?(petal.rim[j]?shade[1]:shade[0]):COLORS[TAG.SEPAL];
      const gain=isPetal?0.66+0.34*Math.pow(petal.outer[j],0.8):1;
      vertices.push({p,n,tag,part,appear:buds[k],pop:true,center:pos,rim:false,gain,gloss:0.3,tone,flash:tag===TAG.SEPAL?0:0.75*flashKey,petalIndex:isPetal?j:-1});
    }
    roseCache[k]={open:openKey,flash:flashKey,vertices,petal}; return roseCache[k];
  }

  const FWD=unit(vsub(target,viewEye)), CAM_RIGHT=unit(cross(FWD,[0,1,0])), CAM_UP=cross(CAM_RIGHT,FWD);
  function camera(p) { const rel=vsub(p,viewEye); return [dot(rel,CAM_RIGHT),dot(rel,CAM_UP),dot(rel,FWD)]; }
  const ASPECT=W/H, FOCAL=3.3, MIDDLE=0.5, FOLD=0.12;
  function project(p) {
    const [x,y,z]=camera(p), zz=Math.max(z,0.2);
    return [Math.floor((0.5+x/zz*FOCAL*0.5/ASPECT)*COLS),Math.floor((MIDDLE-y/zz*FOCAL*0.5)*ROWS),z];
  }
  const count=COLS*ROWS, depth=new Float32Array(count), partGrid=new Int32Array(count), lum=new Float32Array(count);
  const tagGrid=new Int8Array(count), toneGrid=new Uint8Array(count*3), glossGrid=new Float32Array(count);
  const vertexColor=new Uint8Array(count*3), gx=new Int8Array(count), gy=new Int8Array(count), edge=new Uint8Array(count);
  const bodyGrid=new Uint8Array(count), keyLight=unit([0.45,0.80,0.55]), halfKey=unit(vadd(keyLight,view));
  let halfSheen;
  function resetGrid(){depth.fill(99);partGrid.fill(-1);lum.fill(0);tagGrid.fill(0);toneGrid.fill(0);glossGrid.fill(0);gx.fill(0);gy.fill(0);edge.fill(0);}
  function lightVertex(v,p,n,yaw,t) {
    const nr=n, back=dot(nr,view)<0, side=back?-1:1;
    const diff=Math.max(0,side*dot(nr,keyLight));
    const a2=Math.max(0,side*dot(nr,halfKey))**2,b2=Math.max(0,side*dot(nr,halfSheen))**2;
    let shade=(0.62+0.60*diff+v.gloss*(a2**12+0.7*b2**9))*v.gain;
    let tag=v.tag,tone=v.tone||COLORS[tag];
    if(tag===TAG.PAPER) {
      shade=0.40+0.45*diff+1.1*(a2**3+b2**3);
      if(back&&!v.rim){tag=TAG.PAPER_IN;tone=COLORS[TAG.PAPER_IN];}
    }
    if(tag===TAG.RIBBON&&t>T_GLEAM[0]&&t<T_GLEAM[1]+0.3) {
      const x=camera(p)[0],at=-0.35+0.70*(t-T_GLEAM[0])/(T_GLEAM[1]-T_GLEAM[0]),g=Math.exp(-(((x-at)/0.05)**2));
      shade+=1.45*g;tone=tone.map(c=>c+(255-c)*0.7*g);
    }
    if(v.flash>0){const f=v.flash;tone=tone.map(c=>c+(255-c)*f);shade+=0.8*f;}
    return {shade,tag,tone};
  }
  function plotVertex(v,t,yaw,growing) {
    const age=t-v.appear;if(growing&&age<0)return;
    let p=v.p;
    if(growing&&v.pop&&age<FLASH) {
      const g=smooth(age/0.2)*(1+0.35*clamp(1-age/FLASH));
      p=vadd(v.center,vmul(vsub(p,v.center),g));
    }
    p=spinPoint(p,yaw);
    const n=spinPoint(v.n,yaw);
    const [cx,cy,z]=project(p);
    if(z<=0.2||cx<0||cx>=COLS||cy<0||cy>=ROWS)return;
    const idx=cy*COLS+cx;
    if(z>=depth[idx])return;
    let {shade,tag,tone}=lightVertex(v,p,n,yaw,t);
    if(growing&&age>=0&&age<0.14&&!v.pop){tag=TAG.GLINT;tone=COLORS[TAG.GLINT];shade=1.2;}
    depth[idx]=z;partGrid[idx]=v.part;lum[idx]=shade;tagGrid[idx]=tag;glossGrid[idx]=v.gloss;
    toneGrid[idx*3]=tone[0];toneGrid[idx*3+1]=tone[1];toneGrid[idx*3+2]=tone[2];
  }
  function opening(t){return roseStart.map(s=>{const e=smooth((t-s)/OPEN);return e*(1.35-0.35*e);});}
  function sway(t){return 0.38*Math.sin(TAU*t/LOOP)*smooth(t/1.5);}
  const starKind=g=>g[2]%0.25<0.045?TAG.STAR_PINK:g[2]%0.25<0.08?TAG.STAR_BLUE:g[2]%0.25<0.105?TAG.GOLD:TAG.GLINT;
  function starData(t) {
    return stars.map(g=>{
      const x=2.5*g[0]-1.25+0.04*Math.sin(t*0.5+g[5]*TAU), y=-1.75+3.1*((g[1]+t*0.006*(0.5+g[3]))%1), z=-1.3+2.2*g[2];
      const beat=2.5+4.5*g[3],peak=clamp(1-Math.abs((t/beat+g[4])%1-0.5)*beat/0.24);
      return {p:[x,y,z],s:0.30+0.35*g[5]+peak**1.5,tag:starKind(g)};
    });
  }
  function blossomData(t) {
    return blossomPos.map((p,i)=>{
      const seed=blossomSeeds[i],phase=seed[2];
      const lit=clamp(1-(t-blossomAppear[i])/FLASH)**2*(t>=blossomAppear[i]?1:0);
      const s=(0.55+0.35*Math.max(0,Math.sin(t*1.3+phase*40))**4+0.9*lit)*(t>=blossomAppear[i]?1:0);
      return {p,s,tag:TAG.BLOSSOM};
    });
  }
  function fallingData(t) {
    const out=[];
    for(let k=0;k<falls.length;k++){
      const [a,b,c,d,e,f,g,h]=falls[k],since=t-T_FALL-k*5/18;
      if(since<0)continue;
      const age=since%5,rose=Math.floor(a*fallFrom.length),rk=fallFrom[Math.min(fallFrom.length-1,rose)];
      const start=vadd(rosePos[rk],matVec(roseTurn[rk],vmul([Math.cos(b*TAU),0.10,Math.sin(b*TAU)],ROSE_SIZE*0.35)));
      const drift=[0.20*(c-0.5)*age+0.06*Math.sin(age*(2+2*d)+e*TAU),-0.30*age,0.25*age*f+0.05*Math.cos(age*(2+g)+h*TAU)];
      const pose=[0,1,2,3,4,3,2,1][Math.floor(age*(3+3*d)+e*8)%8];
      out.push({p:vadd(start,drift),rose:rk,pose,fade:smooth(age/0.3)*smooth((5-age)/0.6)});
    }
    return out;
  }
  function ray(cx,cy,reach,color,strength=1,over=1) {
    const arms=[[0,1,"-"],[0,-1,"-"],[1,0,"|"],[-1,0,"|"]];
    for(let d=1;d<=reach;d++){
      const fade=(1-d/(reach+1))*strength, choices=d<=Math.floor(reach/2)?arms.concat([[1,1,"\\"],[-1,-1,"\\"],[1,-1,"/"],[-1,1,"/"]]):arms;
      for(const [dy,dx,ch] of choices){
        const y=cy+dy*d,x=cx+dx*d*(dy===0?2:1),i=y*COLS+x,k=fade*(dx&&dy?0.7:1);
        if(y>=0&&y<ROWS&&x>=0&&x<COLS&&Math.max(rgb[i*3],rgb[i*3+1],rgb[i*3+2])<k*over)addGlyph(i,ch,color.map(c=>c*k));
      }
    }
    if(cx>=0&&cx<COLS&&cy>=0&&cy<ROWS)addGlyph(cy*COLS+cx,"*",color.map(c=>c*1.3*strength));
  }
  function renderFrame(t) {
    resetGrid();glyphs.fill("");steady.fill(0);
    const sheen=unit([0.9*Math.sin(t*0.5),0.35,0.6]);
    halfSheen=unit(vadd(sheen,view));
    const yaw=sway(t),op=opening(t),growing=t<GROWN+FLASH;
    for(const v of base) plotVertex(v,t,yaw,growing);
    const heads=[];
    for(let k=0;k<19;k++){
      if(t<buds[k]||(dot(spinPoint(dirs[k],yaw),view)<-0.3))continue;
      const flash=t>=roseStart[k]?clamp(1-(t-roseStart[k])/FLASH)**2:0;
      const r=getRose(k,op[k],flash);
      for(const v of r.vertices)plotVertex(v,t,yaw,growing);
      heads.push({p:spinPoint(vadd(rosePos[k],vmul(dirs[k],0.10*(0.5+op[k]))),yaw),f:flash});
      if(op[k]>0.85){
        for(let j=0;j<14;j++){
          const idx=(j*197+k*37)%r.petal.p.length,beat=clamp(1-Math.abs((t+dewOff[j]+0.7*k)%dewEvery[j]-0.25)/0.25);
          if(beat>0.3){const p=spinPoint(vadd(rosePos[k],matVec(roseTurn[k],vmul(r.petal.p[idx],ROSE_SIZE))),yaw),q=project(p);if(q[2]>0.2&&q[0]>=0&&q[0]<COLS&&q[1]>=0&&q[1]<ROWS)addGlyph(q[1]*COLS+q[0],"*",[255,255,255]);}
        }
      }
    }
    const part=partGrid,body=bodyGrid;
    body.fill(0);
    for(let i=0;i<count;i++)body[i]=part[i]>=0?1:0;
    const dep=(x,y)=>x<0||x>=COLS||y<0||y>=ROWS?99:depth[y*COLS+x];
    const par=(x,y)=>x<0||x>=COLS||y<0||y>=ROWS?-1:part[y*COLS+x];
    for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){
      const i=y*COLS+x;if(!body[i])continue;
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
        if(!dx&&!dy)continue;
        const nb=par(x+dx,y+dy),nz=dep(x+dx,y+dy),other=(Math.floor(nb/100)!==Math.floor(part[i]/100)&&nb>=1000&&part[i]>=1000&&nz>=depth[i]);
        const out=nb<0||(nb!==part[i]&&nz>depth[i]+FOLD)||other;
        if(out){gx[i]+=dx;gy[i]+=dy;if(!dx||!dy)edge[i]=1;}
      }
    }
    for(let y=0;y<ROWS;y++)for(let x=0;x<COLS;x++){
      const i=y*COLS+x;if(!body[i])continue;
      const h=(y*7919+x*104729)%9973,lev=clamp(Math.floor(lum[i]*3.2),0,3),pool=POOLS[lev],ch=pool[((h+Math.trunc(t*4+h%11))%12)%pool.length];
      let c=Array.from(toneGrid.slice(i*3,i*3+3));
      const light=edge[i]?Math.max(0.85,lum[i]):clamp(0.45+0.55*lum[i]/0.9,0.45,1.25);
      if(tagGrid[i]===TAG.PAPER)c=c.map(v=>v*light*0.66);else if(tagGrid[i]===TAG.PAPER_IN)c=c.map(v=>v*light*0.40);else c=c.map(v=>v*light);
      const letter=tagGrid[i]===TAG.GLINT?"*":edge[i]?outline(gx[i],gy[i]):ch;
      addGlyph(i,letter,c,true);
    }
    overlayEffects(t,yaw,op,body,heads);
    drawCanvas(t);
  }
  function outline(x,y) {
    const ax=Math.abs(x),ay=Math.abs(y);
    if(ax+ay===0)return "+";
    if(ax>2*ay)return "|";
    if(ay>2*ax)return y>0?"_":"-";
    return x*y>0?"/":"\\";
  }
  const fallPoses=[["(",")"],["/",""],["-",""],["\\",""],["{","}"],["<",">"]];
  const fallTurn=[0,1,2,3,4,3,2,1];
  const white=[255,255,255];
  function overlayEffects(t,yaw,op,body,heads) {
    const extras=[];
    for(let i=0;i<BLOSSOM_N;i++) {
      const lit=clamp(1-(t-blossomAppear[i])/FLASH)**2*(t>=blossomAppear[i]?1:0);
      const phase=blossomSeeds[i][2],s=(0.55+0.35*Math.max(0,Math.sin(t*1.3+phase*40))**4+0.9*lit)*(t>=blossomAppear[i]?1:0);
      extras.push({p:spinPoint(blossomPos[i],yaw),s,tag:TAG.BLOSSOM,blossom:true});
    }
    for(let k=0;k<19;k++) {
      const age=t-(roseStart[k]+0.85*OPEN);
      if(!(age>0&&age<1.4))continue;
      for(const q of pops[k]) {
        const a=q[0]*TAU,upv=0.4+0.8*q[1],speed=0.45+0.5*q[2];
        const vel=[Math.cos(a)*speed,upv,Math.sin(a)*speed],head=vadd(rosePos[k],vmul(dirs[k],0.12));
        const p=vadd(vadd(head,vmul(vel,age)),[0,-0.9*age*age,0]);
        const s=(1-age/1.4)**1.2*(0.8+0.5*q[3]);
        extras.push({p:spinPoint(p,yaw),s,tag:q[3]>0.5?TAG.GLINT:TAG.GOLD,blossom:false});
      }
    }
    for(const s of starData(t))extras.push({...s,blossom:false});
    const hot=[];
    for(const item of extras) {
      const [x,y,z]=project(item.p);
      if(x<0||x>=COLS||y<0||y>=ROWS||z<=0.2||item.s<=0.04)continue;
      const i=y*COLS+x;
      if(item.blossom&&body[i]&&z>depth[i]+0.01)continue;
      if(body[i]&&!(z<depth[i]-0.05&&(item.blossom||item.s>0.6)))continue;
      const c=COLORS[item.tag],scale=clamp(item.blossom?item.s:0.25+item.s,0,1.3);
      addGlyph(i,item.blossom?(item.s>0.8?"*":"o"):item.s>0.7?"*":item.s>0.35?"+":".",c.map(v=>v*scale),item.blossom);
      if(!item.blossom&&item.s>0.8)hot.push({x,y,s:item.s,tag:item.tag});
    }
    hot.sort((a,b)=>b.s-a.s);
    for(const s of hot.slice(0,6))ray(s.x,s.y,Math.floor(1+4*Math.min(s.s,1.3)**2/1.3),COLORS[s.tag],0.75*Math.min(s.s,1.2));

    for(const f of fallingData(t)) {
      const [x,y,z]=project(spinPoint(f.p,yaw)),letters=fallPoses[f.pose],color=ROSE_COLOURS[f.rose][0].map(v=>v*1.15*f.fade);
      for(let j=0;j<letters.length;j++) {
        const xx=x+j,i=y*COLS+xx;
        if(letters[j]&&y>=0&&y<ROWS&&xx>=0&&xx<COLS&&(!body[i]||z<depth[i]))addGlyph(i,letters[j],color);
      }
    }
    for(const h of heads)if(h.f>0.15){const [x,y]=project(h.p);ray(x,y,Math.floor(3+5*h.f),white,0.6+0.6*h.f);}
    const sparkles=[];
    for(let i=0;i<count;i++)if(tagGrid[i]===TAG.GLINT&&body[i])sparkles.push({i,score:lum[i]+((Math.floor(i/COLS)*7919+(i%COLS)*104729)%9973%7)*0.01});
    sparkles.sort((a,b)=>b.score-a.score);
    for(let n=0;n<Math.min(4,sparkles.length);n++) {
      const s=sparkles[n];if(s.score<=0)break;
      const i=s.i,x=i%COLS,y=Math.floor(i/COLS);
      ray(x,y,Math.floor(3+5*(0.5+0.5*Math.sin(t*6+n*1.9))),white,1,2.2);
    }
    if(t>=T_RIBBON&&t<T_RIBBON+FLASH) {
      const p=spinPoint(spinPoint(vadd(WAIST,[0,0,0.13]),sway(t)),0),[x,y]=project(p),g=(1-(t-T_RIBBON)/FLASH)**2;
      ray(x,y,Math.floor(2+6*g),white,0.6+0.6*g);
    }
    if(t>T_GLEAM[1]-0.2&&t<T_GLEAM[1]+0.6) {
      const p=spinPoint(vadd(WAIST,[0,0,0.13]),sway(t)),[x,y]=project(p),g=Math.exp(-(((t-T_GLEAM[1]-0.15)/0.2)**2));
      ray(x,y,Math.floor(2+5*g),COLORS[TAG.GOLD],0.5+0.7*g);
    }
  }
  function addGlyph(i,ch,color,isSteady=false) {
    if(i<0||i>=count)return;
    glyphs[i]=ch;
    rgb[i*3]=clamp(color[0],0,255);rgb[i*3+1]=clamp(color[1],0,255);rgb[i*3+2]=clamp(color[2],0,255);
    steady[i]=isSteady?1:0;
  }
  function drawCanvas(t) {
    art.clearRect(0,0,W,H);art.font="11px Consolas, Menlo, monospace";art.textBaseline="top";
    for(let i=0;i<count;i++) {
      const ch=glyphs[i];if(!ch)continue;
      art.fillStyle=`rgb(${rgb[i*3]},${rgb[i*3+1]},${rgb[i*3+2]})`;
      art.fillText(ch,(i%COLS)*CW,Math.floor(i/COLS)*CH-1);
    }
    drawMessage(t,art);
    trail.globalCompositeOperation="destination-in";trail.fillStyle="rgba(0,0,0,0.45)";trail.fillRect(0,0,W,H);
    trail.globalCompositeOperation="source-over";trail.font=art.font;trail.textBaseline="top";
    for(let i=0;i<count;i++)if(glyphs[i]&&!steady[i]) {
      trail.fillStyle=`rgb(${rgb[i*3]},${rgb[i*3+1]},${rgb[i*3+2]})`;
      trail.fillText(glyphs[i],(i%COLS)*CW,Math.floor(i/COLS)*CH-1);
    }
    ctx.fillStyle="#000";ctx.fillRect(0,0,W,H);ctx.globalCompositeOperation="lighter";
    ctx.globalAlpha=0.52;ctx.filter="blur(5px)";ctx.drawImage(artCanvas,0,0);
    ctx.globalAlpha=0.26;ctx.filter="blur(13px)";ctx.drawImage(artCanvas,0,0);
    ctx.filter="none";ctx.globalAlpha=1;ctx.drawImage(trailCanvas,0,0);ctx.globalCompositeOperation="source-over";
    ctx.drawImage(artCanvas,0,0);
    drawHud(t);
  }
  function drawMessage(t,target) {
    if(t<=T_MSG)return;
    const text="F O R   Y O U   <3";
    const [_,y,z]=camera([0,BOTTOM_Y-0.28,0]),row=Math.floor((MIDDLE-y/z*FOCAL*0.5)*ROWS);
    const size=Math.max(8,Math.round(15*W/792)),advance=0.6*size,x0=(W-advance*text.length)/2;
    const reach=Math.ceil(0.75*size/CH),x0Cell=Math.max(0,Math.floor(x0/CW)-2);
    const x1Cell=Math.min(COLS,Math.floor((x0+advance*text.length)/CW)+3);
    const y0=Math.max(0,row-reach)*CH,y1=Math.min(ROWS,row+reach+1)*CH;
    target.clearRect(x0Cell*CW,y0,(x1Cell-x0Cell)*CW,y1-y0);
    const shown=Math.min(text.length,Math.floor((t-T_MSG)*10)),love=text.indexOf("<3");
    const ph=(t-T_MSG-love/10+0.6)%1.1,beat=Math.exp(-((ph/0.06)**2))+0.55*Math.exp(-(((ph-0.24)/0.06)**2));
    target.save();
    target.textAlign="center";target.textBaseline="middle";target.font=`${size}px Consolas, Menlo, monospace`;
    for(let i=0;i<shown;i++) {
      const ch=text[i];if(ch===" ")continue;
      const newest=clamp(1-((t-T_MSG)*10-i)/3);
      let color;
      if(i>=love)color=[255,41,77].map(v=>clamp((v+(255-v)*newest)*(1+0.5*beat),0,255));
      else {const shimmer=Math.max(0,Math.sin(t*2.6-i*0.55))**6,a=Math.max(newest,0.8*shimmer);color=[255,189,219].map(v=>v+(255-v)*a);}
      target.shadowColor=`rgb(${color[0]},${color[1]},${color[2]})`;target.shadowBlur=9;
      target.fillStyle=`rgb(${color[0]},${color[1]},${color[2]})`;target.fillText(ch,x0+advance*(i+0.5),row*CH+CH/2);
    }
    target.restore();
  }
  function drawHud(t) {
    const open=opening(t).filter(x=>x>0.98).length,falling=fallingData(t).length;
    const first=t<GROWN?`growing ${String((clamp((t-T_GROW[0])/(GROWN-T_GROW[0]))*100).toFixed(1)).padStart(5)}%`:`roses open ${String(open).padStart(2)}/19      petals falling ${String(falling).padStart(2)}`;
    const letters=glyphs.reduce((n,ch)=>n+(ch?1:0),0);
    ctx.font="15px Consolas, Menlo, monospace";ctx.textBaseline="alphabetic";ctx.fillStyle="rgba(185,175,195,.82)";
    ctx.fillText(first,24,H-60);ctx.fillText(`letters ${letters.toLocaleString("en-US")}`,24,H-39);
    ctx.fillText("Space pause · R restart · S screenshot · Esc quit",24,H-18);
    ctx.fillStyle="rgba(176,168,196,.9)";ctx.fillText("@tamphung.ascii",24,H-86);
    ctx.fillStyle="#ff7ab6";ctx.textAlign="right";ctx.fillText(`${Math.floor(t*2)%2===0?"●":" "} t ${t.toFixed(2).padStart(5,"0")}s`,W-24,36);
    ctx.textAlign="start";
  }
  function updateAudioButton() {
    const playing=!music.paused;
    soundButton.textContent=playing?"Tắt nhạc":"Bật nhạc";
    soundButton.setAttribute("aria-pressed",String(playing));
  }
  function startAudio() {
    if(audioStarting||!music.paused){updateAudioButton();return;}
    audioStarting=true;
    music.play().then(()=>{musicOn=true;updateAudioButton();}).catch(error=>{
      musicOn=false;
      updateAudioButton();
      console.warn("Audio autoplay was blocked; use the music button or tap the animation.",error);
    }).finally(()=>{audioStarting=false;});
  }
  function toggleAudio() {
    if(music.paused)startAudio();
    else music.pause();
  }
  soundButton.addEventListener("click",toggleAudio);
  canvas.addEventListener("pointerdown",()=>{if(!musicOn)startAudio();},{passive:true});
  music.addEventListener("play",()=>{musicOn=true;updateAudioButton();});
  music.addEventListener("pause",()=>{musicOn=false;updateAudioButton();});
  document.addEventListener("keydown",e=>{
    if(e.code==="Space"){e.preventDefault();running=!running;}
    else if(e.key.toLowerCase()==="r"){elapsed=0;trail.clearRect(0,0,W,H);}
    else if(e.key.toLowerCase()==="m")toggleAudio();
    else if(e.key.toLowerCase()==="s"){const a=document.createElement("a");a.download="rose-bouquet.png";a.href=canvas.toDataURL("image/png");a.click();}
    else if(e.key.toLowerCase()==="f"){if(document.fullscreenElement)document.exitFullscreen();else canvas.requestFullscreen?.();}
    else if(e.key==="Escape")running=false;
  });
  updateAudioButton();
  startAudio();
  function tick(now) {
    if(!lastTime)lastTime=now;
    const dt=Math.min((now-lastTime)/1000,1/15);lastTime=now;
    if(running){elapsed=(elapsed+dt)%LOOP;renderFrame(elapsed);}
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})();
