(() => {
  const slide=document.getElementById('slide-logo');
  const sources=JSON.parse(document.getElementById('construction-vector-data').textContent);
  const ns='http://www.w3.org/2000/svg',blue='#3155D9';
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const scrub=document.getElementById('construction-scrub'),play=document.getElementById('construction-play'),icon=document.getElementById('construction-play-icon');
  const clamp=v=>Math.max(0,Math.min(1,v));
  const ramp=(t,start,end)=>clamp((t-start)/(end-start));
  const matrix=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]];
  function element(tag,attrs={},parent){const e=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(parent)parent.append(e);return e;}
  function line(parent,x1,y1,x2,y2,attrs={}){return element('path',{d:`M${x1} ${y1}L${x2} ${y2}`,...attrs},parent);}
  function cross(parent,x,y,r=4){return element('path',{d:`M${x-r} ${y}H${x+r}M${x} ${y-r}V${y+r}`},parent);}
  function sourceMatrix(path,svg){let transform=new DOMMatrix(),node=path;while(node!==svg){const local=node.transform?.baseVal?.consolidate()?.matrix;if(local)transform=new DOMMatrix([local.a,local.b,local.c,local.d,local.e,local.f]).multiply(transform);node=node.parentNode;}return transform;}
  function setup(kind,source){
    const master=new DOMParser().parseFromString(source,'image/svg+xml').documentElement;
    const isLogo=kind==='symbol',width=isLogo?256:1440,height=isLogo?256:240;
    const svg=element('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':isLogo?'BenchMate Soft Joint Logo Construction':'BenchMate Wordmark Construction'});
    document.getElementById(`${kind}-construction`).append(svg);
    const defs=element('defs',{},svg),id=`${kind}-ink`;
    for(let level=0;level<=16;level++){
      const cell=isLogo?1.5:3,tile=cell*4;
      const pattern=element('pattern',{id:`${id}-${level}`,width:tile,height:tile,patternUnits:'userSpaceOnUse'},defs);
      if(level===16)element('rect',{width:tile,height:tile,fill:'white'},pattern);
      else for(let y=0;y<4;y++)for(let x=0;x<4;x++)if(matrix[y][x]<level)element('rect',{x:x*cell,y:y*cell,width:cell,height:cell,fill:'white'},pattern);
    }
    const mask=element('mask',{id,maskUnits:'userSpaceOnUse',x:0,y:0,width,height},defs);
    const bands=Array.from({length:32},(_,i)=>element('rect',{x:i*width/32,y:0,width:width/32+.1,height,fill:`url(#${id}-0)`},mask));
    const blueprint=element('g',{fill:'none',stroke:blue,'stroke-width':'.65','data-layer':'blueprint'},svg);
    const construction=element('g',{fill:'none',stroke:blue,'stroke-width':'.85','data-layer':'wireframe'},svg);
    const detail=element('g',{fill:'none',stroke:blue,'stroke-width':'.65','data-layer':'details'},svg);
    const fill=element('g',{mask:`url(#${id})`,'data-layer':'colors'},svg);
    const sourceGroup=master.querySelector(':scope > g');
    fill.append(sourceGroup.cloneNode(true));
    const outline=sourceGroup.cloneNode(true);construction.append(outline);
    // Presentation changes only: source paths and transforms remain exact.
    for(const node of [outline,...outline.querySelectorAll('*')]){node.removeAttribute('id');node.setAttribute('fill','none');node.setAttribute('stroke',blue);}
    const wirePaths=[...outline.querySelectorAll('path')];
    for(const path of wirePaths){const length=path.getTotalLength(),m=sourceMatrix(path,svg);path.setAttribute('stroke-width',(isLogo?.8:1.4)/Math.sqrt(Math.abs(m.a*m.d-m.b*m.c)));path.dataset.length=length;path.style.strokeDasharray=`${length} ${length}`;path.style.strokeDashoffset=length;}
    if(isLogo){
      for(let x=16;x<=240;x+=8)line(blueprint,x,16,x,240,{'stroke-opacity':x%32===0?.3:.13});
      for(let y=16;y<=240;y+=8)line(blueprint,16,y,240,y,{'stroke-opacity':y%32===0?.3:.13});
      element('rect',{x:48,y:48,width:160,height:160,'stroke-opacity':'.7'},blueprint);
      element('rect',{x:16,y:16,width:224,height:224,'stroke-dasharray':'3 3','stroke-opacity':'.35'},blueprint);
      line(blueprint,128,4,128,252,{'stroke-dasharray':'2 3','stroke-opacity':'.5'});
      line(blueprint,4,128,252,128,{'stroke-dasharray':'2 3','stroke-opacity':'.5'});
      const radii=[[64,64,16],[136,56,8],[96,96,8],[96,104,8],[104,144,8]];
      const anchors=[[64,48],[136,48],[144,56],[144,88],[96,88],[88,96],[88,104],[96,112],[112,112],[112,144],[104,152],[48,152],[48,64]];
      for(let rotation=0;rotation<2;rotation++){
        const g=element('g',{transform:rotation?'rotate(180 128 128)':''},detail);
        radii.forEach(([x,y,r])=>{element('circle',{cx:x,cy:y,r,'stroke-dasharray':'1.2 1.2','stroke-opacity':'.65'},g);cross(g,x,y,2);});
        anchors.forEach(([x,y])=>element('rect',{x:x-1,y:y-1,width:2,height:2,fill:'#D6E879'},g));
      }
      cross(detail,128,128,5);
    }else{
      for(let x=10;x<=1430;x+=20)line(blueprint,x,0,x,240,{'stroke-opacity':x%100===10?.2:.08});
      for(let y=0;y<=240;y+=20)line(blueprint,0,y,1440,y,{'stroke-opacity':'.12'});
      [20,70,220].forEach(y=>line(blueprint,0,y,1440,y,{'stroke-opacity':'.7','stroke-dasharray':'4 5'}));
      const divisions=[10,154,167,317,330,470,488,625,645,795,807,997,1148,1160,1267,1278,1420];
      divisions.forEach(x=>{line(blueprint,x,8,x,232,{'stroke-opacity':'.38'});cross(blueprint,x,220,4);});
      // Tangent inspection points stay attached to the original vector contours.
      for(const path of wirePaths){
        const length=path.getTotalLength(),transform=sourceMatrix(path,svg);
        const count=Math.max(4,Math.min(12,Math.ceil(length/65)));
        for(let i=0;i<count;i++){
          const p=path.getPointAtLength(i/count*length),a=path.getPointAtLength(Math.max(0,i/count*length-.3)),b=path.getPointAtLength(Math.min(length,i/count*length+.3));
          const point=new DOMPoint(p.x,p.y).matrixTransform(transform),before=new DOMPoint(a.x,a.y).matrixTransform(transform),after=new DOMPoint(b.x,b.y).matrixTransform(transform);
          const dx=after.x-before.x,dy=after.y-before.y,n=Math.hypot(dx,dy)||1;
          line(detail,point.x-dx/n*8,point.y-dy/n*8,point.x+dx/n*8,point.y+dy/n*8,{'stroke-opacity':'.55'});
          element('rect',{x:point.x-1.8,y:point.y-1.8,width:3.6,height:3.6,fill:'#D6E879','vector-effect':'non-scaling-stroke'},detail);
        }
      }
    }
    for(const p of blueprint.querySelectorAll('path,rect')){const length=p.getTotalLength();p.dataset.length=length;p.style.strokeDasharray=p.getAttribute('stroke-dasharray')||`${length} ${length}`;}
    return {svg,blueprint,construction,detail,fill,bands,wirePaths,id};
  }
  const marks=[setup('wordmark',sources.wordmark),setup('symbol',sources.logo)];
  let position=reduced.matches?1:0,playing=!reduced.matches,elapsed=position*10,raf=0,last=0,renderCount=0;
  function render(value){
    position=clamp(value);renderCount++;
    const t=position*10;
    const guideIn=ramp(t,.1,1.35),wire=ramp(t,1.6,3.6),details=ramp(t,3.8,4.5),color=ramp(t,5.5,7.8),guideOut=1-ramp(t,6.3,7.8);
    const stage=t<1.6?'Blueprint':t<3.8?'Wireframe':t<5.5?'Details':t<7.8?'Colors':'Complete';
    for(const mark of marks){
      mark.blueprint.setAttribute('opacity',guideIn*guideOut);
      for(const [i,p]of [...mark.blueprint.querySelectorAll('path,rect')].entries())if(!p.getAttribute('stroke-dasharray'))p.style.strokeDashoffset=Number(p.dataset.length)*(1-clamp(guideIn*1.4-i*.004));
      mark.construction.setAttribute('opacity',wire===0?0:1-ramp(t,7.6,7.8));
      mark.wirePaths.forEach((p,i)=>{p.style.strokeDashoffset=Number(p.dataset.length)*(1-clamp(wire*1.25-i/mark.wirePaths.length*.25));});
      mark.detail.setAttribute('opacity',details*guideOut);
      [...mark.detail.children].forEach((p,i)=>p.setAttribute('opacity',clamp(details*1.5-i/mark.detail.children.length*.5)));
      mark.bands.forEach((band,i)=>{const density=Math.round(clamp(color*1.6-i/31*.6)*16);band.setAttribute('fill',`url(#${mark.id}-${density})`);});
      if(color===1)mark.fill.removeAttribute('mask');else mark.fill.setAttribute('mask',`url(#${mark.id})`);
      mark.svg.dataset.stage=stage;mark.svg.dataset.position=position.toFixed(4);
    }
    scrub.value=String(Math.round(position*1000));scrub.setAttribute('aria-valuetext',stage);
  }
  function updateControls(){play.setAttribute('aria-label',playing?'Pause Construction Animation':'Play Construction Animation');icon.setAttribute('d',playing?'M8 6V18M16 6V18':'M8 5L18 12L8 19Z');}
  function eligible(){return playing&&!slide.hidden&&!document.hidden;}
  function tick(now){raf=0;if(!eligible()){last=0;return;}if(last)elapsed+=Math.min((now-last)/1000,.05);last=now;render((elapsed%10.5)/10);raf=requestAnimationFrame(tick);}
  function sync(){if(!eligible()){if(raf)cancelAnimationFrame(raf);raf=0;last=0;}else if(!raf)raf=requestAnimationFrame(tick);updateControls();}
  function seek(value){playing=false;elapsed=clamp(value)*10;render(value);sync();}
  play.addEventListener('click',()=>{playing=!playing;sync();});
  document.getElementById('construction-replay').addEventListener('click',()=>{elapsed=0;render(0);playing=true;sync();});
  scrub.addEventListener('input',()=>seek(Number(scrub.value)/1000));
  new MutationObserver(sync).observe(slide,{attributes:true,attributeFilter:['hidden']});
  document.addEventListener('visibilitychange',sync);
  reduced.addEventListener('change',()=>{if(reduced.matches)seek(1);});
  window.addEventListener('beforeprint',()=>{if(raf)cancelAnimationFrame(raf);raf=0;last=0;});window.addEventListener('afterprint',sync);
  window.benchmateConstruction={seek,render,getState:()=>({position,playing,active:Boolean(raf),renderCount,reducedMotion:reduced.matches,stage:marks[0].svg.dataset.stage})};
  render(position);sync();
})();
