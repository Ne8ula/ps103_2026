(() => {
  const slide=document.getElementById('slide-logo');
  const canvas=document.getElementById('logo-motion-canvas');
  const context=canvas.getContext('2d');
  const glyphs=JSON.parse(document.getElementById('motion-glyph-data').textContent);
  const scrub=document.getElementById('motion-scrub'),output=document.getElementById('motion-position');
  const play=document.getElementById('motion-play'),caption=document.getElementById('motion-caption');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const W=1538,H=510,ratio=Math.min(devicePixelRatio||1,2);
  canvas.width=W*ratio;canvas.height=H*ratio;context.scale(ratio,ratio);
  const blue='#3155D9',lime='#D6E879';
  const origin=[[0,0,144,200],[157,48,150,155],[320,50,140,150],[478,50,137,150],[635,0,150,200],[797,0,190,200],[986,50,152,150],[1150,9,107,194],[1268,49,142,154]];
  const clamp=n=>Math.max(0,Math.min(1,n)),lerp=(a,b,t)=>a+(b-a)*t;
  const smooth=t=>t*t*t*(t*(t*6-15)+10);
  const matrix=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]];
  const patterns=Array.from({length:16},(_,level)=>{
    const tile=document.createElement('canvas');tile.width=16;tile.height=16;
    const c=tile.getContext('2d');c.fillStyle='#000';
    for(let y=0;y<4;y++)for(let x=0;x<4;x++)if(matrix[y][x]<level)c.fillRect(x*4,y*4,3,3);
    return context.createPattern(tile,'repeat');
  });
  let position=0,playing=!reduced.matches,phase=0,raf=0,last=0,initialized=false,renderCount=0;
  function render(value){
    position=clamp(value);renderCount++;
    context.clearRect(0,0,W,H);
    const bounds=[];
    glyphs.forEach((glyph,index)=>{
      const p=smooth(clamp((position-index*.018)/.856));
      const flow=Math.sin(Math.PI*p);
      const [ox,oy,ow,oh]=origin[index];
      const horizontal={x:64+ox, y:151+oy, w:ow, h:oh};
      const square=index<5?{x:514+index*104,y:38,w:96,h:210}:{x:514+(index-5)*130,y:262,w:122,h:210};
      const x=lerp(horizontal.x,square.x,p)+flow*Math.sin(index*.8)*44;
      const y=lerp(horizontal.y,square.y,p)+flow*Math.sin(index*.72-1.4)*68;
      const width=lerp(horizontal.w,square.w,p)*(1+flow*.36*Math.sin(index*.83+p*4));
      const height=lerp(horizontal.h,square.h,p)*(1-flow*.12*Math.sin(index*.83+p*4));
      const path=new Path2D();let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
      glyph.from.forEach((contour,j)=>{
        contour.forEach((pt,k)=>{
          const target=glyph.to[j][k];
          const u=lerp(pt[0],target[0],p),v=lerp(pt[1],target[1],p);
          // The outline bends as well as changing its proportions and position.
          const bend=flow*(Math.sin(v*Math.PI*1.5+p*3+index*.42)*24+(v-.5)*25*Math.sin(index));
          const px=x+u*width+bend,py=y+v*height+flow*Math.sin(u*Math.PI)*12;
          minX=Math.min(minX,px);maxX=Math.max(maxX,px);minY=Math.min(minY,py);maxY=Math.max(maxY,py);
          if(k===0)path.moveTo(px,py);else path.lineTo(px,py);
        });path.closePath();
      });
      bounds.push({minX,maxX,minY,maxY});
      // A small ordered-dither wake follows the outside contour during flow.
      if(flow>.02){
        context.fillStyle=index===6?lime:blue;
        glyph.from[0].forEach((pt,k)=>{
          if(k%3)return;
          const target=glyph.to[0][k],u=lerp(pt[0],target[0],p),v=lerp(pt[1],target[1],p);
          for(let n=1;n<5;n++){
            if((k+n)%4===0)continue;
            const px=x+u*width-flow*n*8,py=y+v*height+Math.sin(k*.8)*flow*n*4;
            context.globalAlpha=flow*(.35-n*.06);context.fillRect(Math.round(px/4)*4,Math.round(py/4)*4,3,3);
          }
        });context.globalAlpha=1;
      }
      context.fillStyle=blue;context.fill(path,'evenodd');
      context.save();context.clip(path,'evenodd');context.globalCompositeOperation='destination-out';
      // Density is applied to the actual letterforms, not a decorative backdrop.
      for(let band=0;band<8;band++){
        const signature=(index===1||index===6)?2:0;
        const density=Math.min(13,Math.round(signature+flow*7*(band/7)+((band>5)?(band-5)*1.2:0)));
        if(density){context.fillStyle=patterns[density];context.fillRect(minX+(maxX-minX)*band/8-1,minY-1,(maxX-minX)/8+2,maxY-minY+2);}
      }
      context.restore();
    });
    scrub.value=String(Math.round(position*1000));
    output.value=`${Math.round(position*100)}%`;
    scrub.setAttribute('aria-valuetext',position<.01?'Horizontal Wordmark':position>.99?'Square Wordmark':`${Math.round(position*100)} Percent Toward Square`);
    const state=position<.01?'Horizontal':position>.99?'Square':'In Flow';
    caption.textContent=state;
    canvas.setAttribute('aria-label',`BenchMate Wordmark — ${state}`);
    canvas.dataset.position=position.toFixed(4);
    canvas.dataset.bounds=JSON.stringify(bounds);
  }
  function updatePlay(){play.textContent=playing?'Pause':'Play';play.setAttribute('aria-label',playing?'Pause Logo Animation':'Play Logo Animation');}
  function valueAt(t){
    const s=t%10;
    if(s<1.5)return 0;
    if(s<4.2)return (s-1.5)/2.7;
    if(s<5.8)return 1;
    if(s<8.7)return 1-(s-5.8)/2.9;
    return 0;
  }
  function eligible(){return initialized&&playing&&!slide.hidden&&!document.hidden;}
  function tick(now){
    raf=0;if(!eligible()){last=0;return;}
    if(last)phase+=Math.min((now-last)/1000,.05);
    last=now;render(valueAt(phase));raf=requestAnimationFrame(tick);
  }
  function sync(){
    if(!eligible()){if(raf)cancelAnimationFrame(raf);raf=0;last=0;}
    else if(!raf)raf=requestAnimationFrame(tick);
    updatePlay();
  }
  function seek(value){playing=false;render(value);phase=1.5+position*2.7;sync();}
  play.addEventListener('click',()=>{playing=!playing;sync();});
  scrub.addEventListener('input',()=>seek(Number(scrub.value)/1000));
  document.getElementById('motion-horizontal').addEventListener('click',()=>seek(0));
  document.getElementById('motion-square').addEventListener('click',()=>seek(1));
  new MutationObserver(sync).observe(slide,{attributes:true,attributeFilter:['hidden']});
  document.addEventListener('visibilitychange',sync);
  reduced.addEventListener('change',()=>{if(reduced.matches)seek(0);});
  window.addEventListener('beforeprint',()=>{if(raf)cancelAnimationFrame(raf);raf=0;last=0;});
  window.addEventListener('afterprint',sync);
  // A small deterministic interface supports frame inspection and export.
  window.benchmateLogoMotion={seek,getState:()=>({position,playing,active:Boolean(raf),renderCount,reducedMotion:reduced.matches}),render};
  render(0);initialized=true;sync();
})();
