import React,{useEffect,useRef,useState} from 'react';
import {Box,Check} from 'lucide-react';
import {Cat,FocusArt} from './Illustrations.jsx';

export function ProductScene({type='cat',lifting=false,compact=false}) {
  const host=useRef(null),controller=useRef(null);
  const [view,setView]=useState(0),[status,setStatus]=useState('loading');
  const sceneType=type;
  useEffect(()=>{
    let active=true;setStatus('loading');setView(0);
    import('../scene/createScene.js').then(({mountProductScene})=>{if(!active)return;controller.current=mountProductScene(host.current,{type:sceneType,lifting,onReady:()=>active&&setStatus('ready'),onError:()=>active&&setStatus('fallback')});}).catch(()=>active&&setStatus('fallback'));
    return()=>{active=false;controller.current?.dispose();controller.current=null;};
  },[sceneType,lifting]);
  const label=sceneType==='cat'?'Satin celadon cat with rounded body, pointed ears, paws and curled tail':sceneType==='clean'?'Gold textured plate with detergent bottle and sponge':sceneType==='spool'?'Schematic PLA spool on a holder':sceneType==='printer'?'Schematic enclosed printer with the upper cover removed':sceneType==='layer'?(lifting?'Illustrated first-layer lines lifting from a gold plate':'Illustrated joined first-layer lines on a gold plate'):'Gold textured build plate and project visualization';
  return <div className={`product-scene ${compact?'compact':''}`}>
    <div className="scene-atmosphere" aria-hidden="true"/><div className="glass-facet" aria-hidden="true"/><div className="scene-crosshair left" aria-hidden="true"/><div className="scene-crosshair right" aria-hidden="true"/>
    <div ref={host} className="scene-canvas" role="img" aria-label={status==='ready'?`3D view: ${label}`:`Illustration: ${label}`} data-renderer={status}/>
    {status==='loading'&&<div className="scene-loading" aria-hidden="true"><Box size={24}/><span>Preparing the material study</span></div>}
    {status==='fallback'&&<div className="scene-fallback">{type==='cat'?<Cat/>:<FocusArt type={type==='studio'?'release':type} lifting={lifting}/>}</div>}
    <div className="scene-caption"><span><Box size={12}/>{status==='ready'?'3D STUDY':status==='loading'?'LOADING 3D':'ILLUSTRATION'}</span><span>{sceneType==='cat'?'01 — SATIN CELADON':'SCHEMATIC · NOT TO SCALE'}</span></div>
    {status==='ready'&&<div className="view-controls" role="group" aria-label="3D camera views">{['Perspective','Front','Detail'].map((name,i)=><button key={name} aria-pressed={view===i} onClick={()=>{setView(i);controller.current?.setView(i);}}>{view===i&&<Check size={12}/>}<span>{name}</span></button>)}</div>}
    {status==='fallback'&&<span className="fallback-message" role="status">3D unavailable. The guide still works.</span>}
  </div>;
}
