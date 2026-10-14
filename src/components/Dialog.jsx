import React, {useEffect, useRef} from 'react';
import {X} from 'lucide-react';
export function Dialog({title, children, onClose, wide=false}) {
  const ref=useRef();
  useEffect(()=>{
    const el=ref.current,device=el.closest('.device');
    const place=()=>{if(!device)return;const r=device.getBoundingClientRect();el.style.left=`${r.left+device.clientLeft}px`;el.style.width=`${device.clientWidth}px`;el.style.bottom=`${Math.max(0,window.innerHeight-r.bottom+device.clientTop)}px`;el.style.maxHeight=`${Math.max(200,device.clientHeight-65)}px`;el.style.margin='0';el.style.right='auto';};
    place();el.showModal();const observer=new ResizeObserver(place);if(device)observer.observe(device);window.addEventListener('resize',place);
    const cancel=e=>{e.preventDefault();onClose();};el.addEventListener('cancel',cancel);
    return()=>{observer.disconnect();window.removeEventListener('resize',place);el.removeEventListener('cancel',cancel);el.close();};
  },[]);
  return <dialog ref={ref} className={wide?'wide':''} aria-labelledby="dialog-title" onClick={e=>{if(e.target===ref.current)onClose();}}><div className="dialog-head"><h2 id="dialog-title">{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={22}/></button></div><div className="dialog-content">{children}</div></dialog>;
}
