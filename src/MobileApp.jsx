import React,{useEffect,useReducer,useRef,useState} from 'react';
import {ChevronLeft,HelpCircle,Bookmark,ArrowDownToLine,BookOpen,Signal,Wifi,BatteryFull,Check,Pause} from 'lucide-react';
import {freshState,loadStoredProject,reducer,STORAGE_KEY,projectRecord} from './state.js';
import {screens} from './data/presentation.js';
import {Dialog} from './components/Dialog.jsx';
import {Browse} from './components/Browse.jsx';
import {GuideContent} from './components/GuideContent.jsx';
import {Sheets} from './components/Sheets.jsx';
import {Primary,PhaseRail,Tabs,titleCase} from './components/UI.jsx';
import './mobile.css';
function bootProject(){try{return loadStoredProject(localStorage);}catch{return {state:freshState(),notice:'Browser storage is unavailable. Download a record before closing.',writeAllowed:false};}}
const modalTitles={help:'A Little Help',setup:'What You Need',identity:'Your Local Profile',preferences:'Preferences',notifications:'Notifications',privacy:'Privacy',discussion:'Local Discussion',support:'Project Summary',withdraw:'Withdraw Issue Report',reset:'Reset Current Guide',tray:'Ripple Tray',pebble:'Cable Pebble'};
export default function MobileApp(){
 const [boot]=useState(bootProject);
 const [state,dispatch]=useReducer(reducer,boot.state),[modal,setModal]=useState(null),[saved,setSaved]=useState(boot.writeAllowed),[toast,setToast]=useState('');
 const scroll=useRef(),heading=useRef(),opener=useRef(),lastScreen=useRef('');
 const guide=state.route==='guide',restart=state.issue?.stage==='restart'&&state.step==='studio';
 const screen=guide?(state.paused?'paused':restart?'studio':state.issue?.stage||state.step):state.route;
 let [title,subtitle,action]=screens[screen]||screens.home;
 if(screen==='complete')title=`Meet ${titleCase(state.name.trim()||'Little Cat')}`;
 if(screen==='finding'&&state.issue.photo.kind!=='demo'){title='Review Your Photo';subtitle='Your Photo Has Not Been Analyzed';}
 useEffect(()=>{if(!boot.writeAllowed)return;try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state));setSaved(true);}catch{setSaved(false);}},[state,boot.writeAllowed]);
 useEffect(()=>{const key=state.route+screen;if(lastScreen.current!==key){setToast('');scroll.current?.scrollTo({top:0});if(lastScreen.current)heading.current?.focus({preventScroll:true});lastScreen.current=key;}},[state.route,screen]);
 useEffect(()=>{if(state.issue?.stage!=='processing'||state.paused||!guide)return;const timer=setTimeout(()=>dispatch({type:'PHOTO_DONE'}),1800);return()=>clearTimeout(timer);},[state.issue?.stage,state.paused,guide]);
 useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(''),3500);return()=>clearTimeout(timer);},[toast]);
 function open(name){if(!modal)opener.current=document.activeElement;setModal(name);}
 function close(){setModal(null);requestAnimationFrame(()=>opener.current?.isConnected&&opener.current.focus());}
 function download(record){const url=URL.createObjectURL(new Blob([projectRecord(record)],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=record.issue?'benchmate-support-summary.txt':'benchmate-project-record.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setToast('Record Prepared · Check Your Downloads');}
 function back(){if(guide){if(state.paused)dispatch({type:'NAV',route:'home'});else if(state.issue){if(['capture','question'].includes(state.issue.stage))open('withdraw');else dispatch({type:'ISSUE_BACK'});}else dispatch({type:'BACK'});}else dispatch({type:'NAV',route:state.route==='detail'?'catalog':['record','share','preview'].includes(state.route)?'collection':'home'});}
 function primary(){
  if(state.paused){dispatch({type:'RESUME'});return;}
  if(restart){dispatch({type:'REVIEWED_RESTART'});dispatch({type:'NEXT'});return;}
  if(state.issue){switch(state.issue.stage){case 'capture':case 'question':dispatch({type:'PHOTO_PROCESS'});break;case 'finding':dispatch({type:'ISSUE_STAGE',stage:'stop'});break;case 'stop':case 'clean':dispatch({type:'RECOVERY_NEXT'});break;case 'restart':dispatch({type:'RESTART'});break;case 'support':download(state);break;}return;}
  if(state.step==='complete')download(state);else dispatch({type:'NEXT'});
 }
 const disabled=!state.paused&&((['capture','question'].includes(screen)&&!state.issue?.photo)||(screen==='stop'&&(!state.issue.ended||!state.issue.cooled))||(screen==='quality'&&(!state.quality.object||!state.quality.workspace))||(screen==='firstLayer'&&state.scenario==='lifting'));
 const activeTab=['catalog','detail'].includes(state.route)?'home':['share','preview','record'].includes(state.route)?'collection':state.route;
 const phaseVisible=guide&&!['capture','question','processing','finding','support','paused'].includes(screen);
 return <div className={`preview-shell ${state.profile.reducedMotion?'reduce-motion':''}`}>
  <aside className="preview-caption"><span className="edition">BENCHMATE / R9</span><h2>A Little<br/>Guidance<br/>Goes A Long Way</h2><p>From a small idea to<br/>something of your own</p><div className="matrix-divider"/><small>Interactive iPhone Mockup<br/>React · Three.js · On This Device</small></aside>
  <section className="device" aria-label="Benchmate App">
   <div className="device-status" aria-hidden="true"><strong>9:41</strong><span className="device-island"/><div><Signal size={14}/><Wifi size={14}/><BatteryFull size={20}/></div></div>
   <a className="skip-link" href="#main-content">Skip To Content</a>
   <header className="app-bar">{guide||['catalog','detail','share','preview','record'].includes(state.route)?<button className="back-button" onClick={back}><ChevronLeft size={22}/><span>{guide?'Back':state.route==='detail'?'Bambu Projects':['share','record','preview'].includes(state.route)?'Collection':'Home'}</span></button>:<span className="wordmark">Benchmate<span className="brand-dots" aria-hidden="true"/></span>}{guide?<span className="badge guided-badge">Guided Demo</span>:null}{guide||['share','preview','detail'].includes(state.route)?<button className="icon-button" aria-label="Help" onClick={()=>open(guide?'help':'setup')}><HelpCircle size={22}/></button>:<button className="icon-button" aria-label="About This Demo" onClick={()=>open('setup')}><BookOpen size={20}/></button>}</header>
   <main id="main-content" className="app-scroll" ref={scroll} tabIndex={-1}>
    {boot.notice&&<div className="notice" role="alert">{boot.notice}</div>}
    {!saved&&!boot.notice&&<div className="notice" role="alert">Local saving is unavailable or full. Keep this tab open and download a project record before closing.</div>}
    {phaseVisible&&<PhaseRail state={state} recovery={['stop','clean','restart'].includes(screen)}/>}
    <div className="title-block">{state.issue&&guide&&!['capture','question','processing','finding'].includes(screen)&&<span className="eyebrow">{titleCase(state.name)} / Issue Open</span>}<h1 ref={heading} tabIndex={-1}>{title}</h1><p className="subtitle">{subtitle}</p></div>
    <div className="screen-content" data-screen={screen} key={`${state.route}-${screen}`}>
     {guide?<GuideContent {...{state,dispatch,open,download}}/>:<Browse {...{state,dispatch,open,download}}/>}
    </div>
   </main>
   {guide?<footer className="action-dock glass">{action&&<Primary disabled={disabled} onClick={primary} icon={screen==='complete'||screen==='support'?ArrowDownToLine:undefined}>{action}</Primary>}{screen==='firstLayer'&&<button className="text-button" onClick={()=>dispatch({type:'REPORT'})}><HelpCircle size={17}/>Something Looks Wrong</button>}{!state.paused&&screen!=='complete'&&<button className="pause-button" onClick={()=>dispatch({type:'PAUSE'})}><Pause size={13}/>Save And Pause</button>}<div className="home-indicator" aria-hidden="true"/></footer>:<><Tabs route={activeTab} onNavigate={route=>dispatch({type:'NAV',route})}/><div className="home-indicator" aria-hidden="true"/></>}
   {toast&&<div className="toast" role="status"><Check size={17}/>{toast}</div>}
   {modal&&<Dialog title={modalTitles[modal]} onClose={close}><Sheets key={modal} {...{modal,state,dispatch,close,open,download}}/></Dialog>}
  </section>
  <aside className="preview-detail"><span className="material-orb"/><span className="edition">PEARL / ORCHID / CITRON</span><p>Small Makes<br/>Thoughtfully Guided</p><small>One project<br/>One step at a time</small></aside>
 </div>;
}
