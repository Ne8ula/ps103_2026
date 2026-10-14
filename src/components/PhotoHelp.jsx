import React,{useEffect,useRef,useState} from 'react';
import {Camera,ImagePlus,RotateCcw,AlertCircle} from 'lucide-react';
import {DEMO_PHOTO} from '../state.js';
import {Glass,Primary} from './UI.jsx';
export function PhotoCapture({photo,dispatch}) {
 const picker=useRef(),capturePicker=useRef(),video=useRef(),stream=useRef(),request=useRef(0),alive=useRef(true);
 const [camera,setCamera]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 function stop(){request.current++;stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;setCamera(false);setBusy(false);}
 useEffect(()=>()=>{alive.current=false;request.current++;stream.current?.getTracks().forEach(t=>t.stop());},[]);
 useEffect(()=>{if(camera&&video.current)video.current.srcObject=stream.current;},[camera]);
 async function startCamera(){
   if(!navigator.mediaDevices?.getUserMedia){setError('Live camera is unavailable here. Use Take Photo or Choose Photo to open your device picker.');capturePicker.current.click();return;}
   const id=++request.current;setError('');setBusy(true);
   try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});if(!alive.current||id!==request.current){s.getTracks().forEach(t=>t.stop());return;}stream.current=s;setCamera(true);}
   catch(e){if(alive.current&&id===request.current)setError(e.name==='NotAllowedError'?'Camera permission was declined. Choose a photo or use the built-in demo.':e.name==='NotFoundError'?'No camera was found. Choose a photo or use the built-in demo.':'The camera could not open. Close other camera apps or choose a photo.');}
   finally{if(alive.current&&id===request.current)setBusy(false);}
 }
 function storePhoto(src,name){dispatch({type:'PHOTO_SELECT',photo:{src,name}});setError('');}
 async function select(event){
   const file=event.target.files?.[0];event.target.value='';if(!file)return;
   if(!/^image\/(jpeg|png|webp|heic|heif)$/.test(file.type)){setError('Choose a JPEG, PNG or WebP photo. Convert HEIC if your browser cannot open it.');return;}
   if(file.size>20*1024*1024){setError('This photo is too large. Choose a photo smaller than 20 MB.');return;}
   setBusy(true);const id=++request.current;
   try{const bitmap=await createImageBitmap(file);const canvas=document.createElement('canvas');const ratio=Math.min(1,1100/Math.max(bitmap.width,bitmap.height));canvas.width=Math.round(bitmap.width*ratio);canvas.height=Math.round(bitmap.height*ratio);canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();if(alive.current&&id===request.current)storePhoto(canvas.toDataURL('image/jpeg',.78),file.name);}
   catch{if(alive.current)setError('This photo could not be opened. Try a JPEG or PNG instead.');}
   finally{if(alive.current&&id===request.current)setBusy(false);}
 }
 function take(){if(!video.current?.videoWidth){setError('The camera is still getting ready. Try again.');return;}const c=document.createElement('canvas'),v=video.current;c.width=Math.min(1100,v.videoWidth);c.height=Math.round(c.width*v.videoHeight/v.videoWidth);c.getContext('2d').drawImage(v,0,0,c.width,c.height);storePhoto(c.toDataURL('image/jpeg',.78),'Camera Photo');stop();}
 return <>
   <input ref={picker} data-testid="photo-picker" type="file" accept="image/*" hidden onChange={select}/>
   <input ref={capturePicker} type="file" accept="image/*" capture="environment" hidden onChange={select}/>
   {camera?<div className="photo-frame"><video ref={video} autoPlay playsInline muted aria-label="Live Camera Preview"/></div>:photo?<PhotoFrame photo={photo}/>:<div className="photo-empty glass"><Camera size={40}/><h2>A Closer Look</h2><p>Choose a photo, open your camera, or explore the example below</p></div>}
   <p className="safety-line"><AlertCircle size={17}/>Keep Clear Of Hot Or Moving Parts</p>
   {error&&<p className="notice" role="alert">{error}</p>}
   {busy&&<p role="status">Opening Your Photo Or Camera…</p>}
   {camera?<><Primary onClick={take} icon={Camera}>Take Photo</Primary><button className="secondary" onClick={stop}>Cancel Camera</button></>:<>
     <div className="photo-actions"><button className="secondary" onClick={startCamera} disabled={busy}><Camera size={20}/>{photo?'Retake Photo':'Open Camera'}</button><button className="secondary" onClick={()=>picker.current.click()} disabled={busy}><ImagePlus size={20}/>Choose Photo</button></div>
     <button className="text-button" onClick={()=>{stop();storePhoto(DEMO_PHOTO,'Built-In First-Layer Example');}}><RotateCcw size={16}/>Use Demo Image</button>
   </>}
   <p className="fineprint">Photos stay in this browser. The next screen demonstrates the help flow; it does not analyze your photo.</p>
 </>;
}
export function PhotoFrame({photo}){return <figure className="photo-frame"><img src={photo.src} alt={photo.kind==='demo'?'Synthetic first-layer example: thin lines with one lifted corner on a seated gold plate':'Your selected photo, displayed without analysis'}/><figcaption>{photo.kind==='demo'?'Synthetic Demo Image':'Your Photo · Not Analyzed'}</figcaption></figure>;}
