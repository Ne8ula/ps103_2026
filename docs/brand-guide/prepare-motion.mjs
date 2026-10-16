import fs from 'node:fs';
import {chromium} from '@playwright/test';

// Bake matched contours once. Runtime animation needs no font/parser/library.
const source=fs.readFileSync('docs/brand-guide/assets/benchmate-wordmark.svg','utf8');
const targets=[
  'M0 0H76Q100 0 100 25Q100 43 84 50Q100 57 100 75Q100 100 76 100H0Z M30 20V40H65Q75 40 75 30Q75 20 65 20Z M30 60V80H65Q75 80 75 70Q75 60 65 60Z',
  'M100 56H30V68Q30 78 48 78H60Q70 78 74 70H100Q93 100 52 100Q0 100 0 50Q0 0 52 0Q100 0 100 48Z M30 38H72Q71 20 52 20Q33 20 30 38Z',
  'M0 0H28V14Q42 0 62 0Q100 0 100 36V100H70V36Q70 24 53 24Q30 24 30 45V100H0Z',
  'M100 0H25L0 25V75L25 100H100V70H40L30 60V40L40 30H100Z',
  'M0 0H30V35Q42 24 65 24Q100 24 100 60V100H70V62Q70 50 55 50Q30 50 30 65V100H0Z',
  'M0 100V0H28L50 46L72 0H100V100H70V50L50 86L30 50V100Z',
  'M0 0H75Q100 0 100 25V100H0V45H70V28H0Z M30 68V82H70V68Z',
  'M27 0H63V26H100V55H63V73Q63 83 78 83H100V100H62Q27 100 27 72V55H0V26H27Z',
  'M100 0H0V100H100V72H32V60H100Z M32 23V37H70V23Z',
];
const browser=await chromium.launch({channel:'msedge'});
const page=await browser.newPage();
await page.setContent(source);
const glyphs=await page.evaluate(({targets})=>{
  const svg=document.querySelector('svg');
  const originals=[...svg.querySelector(':scope > g').children];
  const N=160, ns='http://www.w3.org/2000/svg';
  function sample(d,matrix){
    return d.match(/M[^M]*/gi).map(contour=>{
      const path=document.createElementNS(ns,'path');path.setAttribute('d',contour);svg.append(path);
      const length=path.getTotalLength();
      const points=Array.from({length:N},(_,i)=>{
        const pt=path.getPointAtLength(i/N*length);
        const p=matrix?new DOMPoint(pt.x,pt.y).matrixTransform(matrix):pt;
        return [p.x,p.y];
      });path.remove();return points;
    });
  }
  function normalize(contours){
    const points=contours.flat(),xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
    const x=Math.min(...xs),y=Math.min(...ys),w=Math.max(...xs)-x,h=Math.max(...ys)-y;
    return contours.map(c=>c.map(p=>[(p[0]-x)/w,(p[1]-y)/h]));
  }
  const area=c=>c.reduce((s,p,i)=>{const q=c[(i+1)%N];return s+p[0]*q[1]-q[0]*p[1]},0);
  function align(a,b){
    if(area(a)*area(b)<0)b=b.slice().reverse();
    let best=0,score=Infinity;
    for(let offset=0;offset<N;offset++){
      let cost=0;for(let i=0;i<N;i++){const q=b[(i+offset)%N];cost+=(a[i][0]-q[0])**2+(a[i][1]-q[1])**2;}
      if(cost<score){score=cost;best=offset;}
    }
    return a.map((_,i)=>b[(i+best)%N]);
  }
  return originals.map((element,i)=>{
    let contours;
    if(i===0)contours=sample('M0 0H126V18H144V82H126V118H144V182H126V200H0Z M40 32V68H102V32Z M40 132V168H102V132Z');
    else contours=[...(element.tagName==='path'?[element]:element.querySelectorAll('path'))].flatMap(p=>sample(p.getAttribute('d'),p.getCTM()));
    const from=normalize(contours),to=normalize(sample(targets[i]));
    if(from.length!==to.length)throw Error('Mismatched counters '+i);
    return {from,to:to.map((c,j)=>align(from[j],c))};
  });
},{targets});
await browser.close();
const round=(_,v)=>typeof v==='number'?Math.round(v*100000)/100000:v;
fs.writeFileSync('docs/brand-guide/assets/motion-glyphs.json',JSON.stringify(glyphs,round));
console.log('Prepared 9 continuously morphing glyphs with matched contours');
