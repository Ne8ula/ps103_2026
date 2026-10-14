import React,{useState} from 'react';
import {ArrowRight,Check,ChevronDown,Home,Grid2X2,Users,UserRound,ChevronRight} from 'lucide-react';
import {phaseStatus} from '../state.js';
import {phases} from '../data/project.js';
import {sources} from '../data/equipment.js';
export const titleCase=value=>String(value).replace(/\./g,'').replace(/\b\p{L}/gu,c=>c.toUpperCase());
export function Glass({children,className='',...props}){return <div className={`glass ${className}`} {...props}>{children}</div>;}
export function Primary({children,onClick,disabled,icon:Icon=ArrowRight}){return <button className="primary" disabled={disabled} onClick={onClick}><span>{children}</span><span className="action-arrow"><Icon size={21}/></span></button>;}
export function Row({icon:Icon,children,sub,onClick,trailing}){return <button className="row glass" onClick={onClick}>{Icon&&<span className="row-icon"><Icon size={21}/></span>}<span><strong>{children}</strong>{sub&&<small>{sub}</small>}</span>{trailing||<ChevronRight size={19}/>}</button>;}
export function Sources({ids=[]}){return <div className="source-links">{ids.map(id=><a key={id} href={sources[id].url} target="_blank" rel="noreferrer"><span>{titleCase(sources[id].title)}</span><span aria-hidden="true">↗</span></a>)}</div>;}
export function Disclosure({title='More Detail',children,ids=[]}){const [expanded,setExpanded]=useState(false);return <details className="glass disclosure" onToggle={e=>setExpanded(e.currentTarget.open)}><summary><span>{title==='More Detail'&&expanded?'Less Detail':title}</span><ChevronDown size={18}/></summary><div className="disclosure-body">{children}<Sources ids={ids}/></div></details>;}
export function PhaseRail({state,recovery=false,neutral=false}){
 const labels=recovery?['End Job','Cool','Clean','Review']:phases;
 const data=recovery?labels.map((_,i)=>({done:i===0?state.issue.ended:i===1?state.issue.cooled:i===2?state.issue.stage==='restart':false,current:i===(state.issue.stage==='stop'?(state.issue.ended?1:0):state.issue.stage==='clean'?2:3)})):phaseStatus(state);
 return <ol className="phase-rail" aria-label={recovery?'Recovery Progress':'Project Phases'}>{labels.map((label,i)=><li key={label} className={!neutral&&data[i].done?'done':!neutral&&data[i].current?'current':''} aria-current={!neutral&&data[i].current?'step':undefined}><span className="phase-node">{!neutral&&data[i].done?<Check size={12}/>:null}</span><span>{label}</span><span className="sr-only">{neutral?'Not Started':data[i].done?'Completed':data[i].current?'Current':'Not Completed'}</span></li>)}</ol>;
}
export function Tabs({route,onNavigate}){return <nav className="tab-dock glass" aria-label="Main Navigation">{[['home','Home',Home],['collection','Collection',Grid2X2],['community','Community',Users],['profile','Profile',UserRound]].map(([id,label,Icon])=><button key={id} aria-current={route===id?'page':undefined} onClick={()=>onNavigate(id)}><Icon size={23} strokeWidth={1.7}/><span>{label}</span></button>)}</nav>;}
export function Segments({values,value,onChange,label}){return <div className="segments" role="group" aria-label={label}>{values.map(([id,name])=><button key={id} aria-pressed={value===id} onClick={()=>onChange(id)}>{name}</button>)}</div>;}
export function CheckRow({label,sub,checked,onChange}){return <label className="check-row glass"><input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)}/><span><strong>{label}</strong>{sub&&<small>{sub}</small>}</span></label>;}

