import React,{useEffect,useRef,useState} from 'react';
import {Box,Check} from 'lucide-react';
import {Cat,FocusArt} from './Illustrations.jsx';

export function ProductScene({type='cat',lifting=false,compact=false,controls=true}) {
  const host=useRef(null),controller=useRef(null);
  const [view,setView]=useState(0),[status,setStatus]=useState('loading');
  const sceneType=type;
  useEffect(()=>{
    let active=true;setStatus('loading');setView(0);
    import('../scene/createScene.js').then(({mountProductScene})=>{if(!active)return;controller.current=mountProductScene(host.current,{type:sceneType,lifting,onReady:()=>active&&setStatus('ready'),onError:()=>active&&setStatus('fallback')});}).catch(()=>active&&setStatus('fallback'));
    return()=>{active=false;controller.current?.dispose();controller.current=null;};
  },[sceneType,lifting]);
  const label=sceneType==='cat'?'Cloud blue cat with closed eyes, rounded body, pointed ears, paws and curled tail':sceneType==='clean'?'Gold textured plate with detergent bottle and sponge':sceneType==='spool'?'Schematic PLA spool on a holder':sceneType==='workshop'?'Schematic X1-style printer, cloud blue cat and external spool':sceneType==='printer'?'Schematic enclosed printer with the upper cover removed':sceneType==='tray'?'Preview of a sculptural ripple tray':sceneType==='pebble'?'Preview of a rounded cable pebble':sceneType==='layer'?(lifting?'Illustrated first-layer lines lifting from a gold plate':'Illustrated joined first-layer lines on a gold plate'):'Gold textured build plate seated on its dark platform with rear alignment stops';
  return <div className={`product-scene ${compact?'compact':''}`}>
    <div className="scene-atmosphere" aria-hidden="true"/><div className="glass-facet" aria-hidden="true"/><div className="scene-crosshair left" aria-hidden="true"/><div className="scene-crosshair right" aria-hidden="true"/>{type!=='layer'&&<div className="scene-matrix" aria-hidden="true"/>}
    <div ref={host} className="scene-canvas" role="img" aria-label={status==='ready'?`3D view: ${label}`:`Illustration: ${label}`} data-renderer={status}/>
    {status==='loading'&&<div className="scene-loading" aria-hidden="true"><Box size={24}/><span>Preparing The View</span></div>}
    {status==='fallback'&&<div className="scene-fallback">{type==='cat'?<Cat small/>:['tray','pebble'].includes(type)?<svg viewBox="0 0 200 160" role="img" aria-label={type==='tray'?'Ripple Tray Preview':'Cable Pebble Preview'}><ellipse cx="100" cy="112" rx="70" ry="20" fill="#191820" opacity=".2"/>{type==='tray'?<path d="M30 65Q38 49 48 60Q58 42 70 55Q85 40 97 53Q113 39 125 55Q143 44 151 60Q173 51 175 70L162 110Q100 145 45 110Z" fill="#a8b8f3" stroke="#fcfcfe" strokeWidth="3"/>:<><ellipse cx="100" cy="85" rx="68" ry="42" fill="#a8b8f3"/><ellipse cx="100" cy="77" rx="30" ry="18" fill="#514d63"/><path d="M10 113Q55 94 100 77L180 58" stroke="#292733" strokeWidth="7" fill="none"/></>}</svg>:<FocusArt type={['workshop','printing'].includes(type)?'printer':type==='studio'?'release':type} lifting={lifting}/>}</div>}
    <div className="scene-caption"><span><Box size={12}/>{status==='ready'?'3D Study':status==='loading'?'Loading 3D':'Illustration'}</span><span>{sceneType==='cat'?'Cloud / Blue':'Schematic · Not To Scale'}</span></div>
    {status==='ready'&&controls&&<div className="view-controls" role="group" aria-label="3D camera views">{['Perspective','Front','Detail'].map((name,i)=><button key={name} aria-pressed={view===i} onClick={()=>{setView(i);controller.current?.setView(i);}}>{view===i&&<Check size={12}/>}<span>{name}</span></button>)}</div>}
    {status==='fallback'&&<span className="fallback-message" role="status">3D unavailable. The guide still works.</span>}
  </div>;
}
