import React,{useState,useEffect,useReducer,useRef} from 'react';
import {ArrowRight,ArrowUpRight,Check,HelpCircle,BookOpen,Pause,MoreHorizontal,CircleCheck,Bookmark,Download,RotateCcw,AlertCircle,Printer,ChevronRight,ChevronLeft,Layers,Wifi,BatteryFull,Signal} from 'lucide-react';
import {steps,stepById,phases} from './data/project.js';
import {freshState,restoreState,reducer,STORAGE_KEY,projectRecord} from './state.js';
import {ProductScene} from './components/ProductScene.jsx';
import {Dialog} from './components/Dialog.jsx';
import {ProjectSheets,SourceLinks} from './components/ProjectSheets.jsx';
import './mobile.css';

function loadProject(){try{return restoreState(localStorage.getItem(STORAGE_KEY));}catch{return freshState();}}
function downloadRecord(state){const blob=new Blob([projectRecord(state)],{type:'text/plain;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='benchmate-project-record.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
const titles={intro:'A little cat.\nA lot of character.',personalize:'A little more\nyou.',studio:'Start with\na good setup.',plate:'A clean\nbeginning.',filament:'One spool.\nAll you need.',start:'Over to\nBambu Studio.',firstLayer:'The first layer\nsets the tone.',printing:'Let it\ntake shape.',cooling:'A little patience.\nThen, your cat.',quality:'Ready for\nits new home.'};
const recoveryTitles={question:'Let’s take\na closer look.',stop:'End this attempt.\nStart fresh.',clean:'A fresh surface.\nA fresh start.',restart:'Back to\nthe beginning.',support:'A little\nexpert help.'};
const recoveryActions={question:'Yes, it’s lifting or loose',stop:'I’ve reviewed ending the attempt',clean:'Cleaning steps reviewed',restart:'Return to setup checkpoint',support:'Prepare support handoff'};

export default function MobileApp(){
  const [state,dispatch]=useReducer(reducer,undefined,loadProject);
  const [modal,setModal]=useState(null),[question,setQuestion]=useState(null),[saved,setSaved]=useState(true),[toast,setToast]=useState('');
  const heading=useRef(),scrollArea=useRef(),opener=useRef(),lastStep=useRef('');
  const step=stepById[state.step],isEntry=state.step==='intro',isFinish=state.step==='complete';
  const restartCheckpoint=state.issue?.stage==='restart'&&state.step==='studio';
  const recovering=!!state.issue&&!restartCheckpoint;
  const sceneType=recovering?(state.issue.stage==='clean'?'clean':'layer'):step.art;
  useEffect(()=>{try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state));setSaved(true);}catch{setSaved(false);}},[state]);
  useEffect(()=>{const key=state.step+(state.issue?.stage||'')+state.paused;if(lastStep.current!==key){scrollArea.current?.scrollTo({top:0,behavior:'instant'});if(lastStep.current)heading.current?.focus({preventScroll:true});lastStep.current=key;}setQuestion(null);},[state.step,state.issue?.stage,state.paused]);
  useEffect(()=>{if(!toast)return;const id=setTimeout(()=>setToast(''),3500);return()=>clearTimeout(id);},[toast]);
  function openModal(name){opener.current=document.activeElement;setModal(name);setQuestion(null);}
  function closeModal(){setModal(null);setTimeout(()=>opener.current?.focus(),0);}
  function advance(){if(restartCheckpoint)dispatch({type:'REVIEWED_RESTART'});dispatch({type:'NEXT'});}
  const phasesDone=phases.map((_,i)=>steps.filter(s=>s.phase===i&&!['intro','complete'].includes(s.id)).every(s=>state.completed.includes(s.id)));
  const title=state.paused?'Right where\nyou left off.':recovering?recoveryTitles[state.issue.stage]:isFinish?`Meet ${state.name.trim()||'Little cat'}.`:titles[state.step];
  const disabled=!state.paused&&!recovering&&((state.step==='quality'&&(!state.quality.object||!state.quality.workspace))||(state.step==='firstLayer'&&state.scenario==='lifting'));
  function primaryAction(){
    if(state.paused){dispatch({type:'RESUME'});return;}
    if(recovering){const stage=state.issue.stage;if(stage==='question')dispatch({type:'OBSERVE',value:'loose'});else if(stage==='restart')dispatch({type:'RESTART'});else if(stage==='support')openModal('support');else dispatch({type:'RECOVERY_NEXT'});return;}
    if(isFinish){downloadRecord(state);setToast('Record prepared. Check your downloads.');}else advance();
  }
  const action=state.paused?'Resume my project':recovering?recoveryActions[state.issue.stage]:step.action;
  return <div className="preview-shell">
    <aside className="preview-caption"><span className="preview-index">BENCHMATE / 002</span><h2>Made for<br/>the making.</h2><p>A companion for the small things<br/>you make your own.</p><div className="preview-rule"/><span>iPHONE APP CONCEPT</span><small>Interactive browser mockup</small></aside>
    <section className={`device ${recovering?'recovery-mode':''}`} aria-label="Benchmate mobile app">
      <div className="device-status" aria-hidden="true"><strong>9:41</strong><span className="device-island"/><div><Signal size={14}/><Wifi size={14}/><BatteryFull size={20}/></div></div>
      <a className="skip-link" href="#main-content">Skip to project</a>
      <header className="app-bar">
        {!isEntry&&!recovering&&!state.paused?<button className="icon-button back-button" aria-label="Back" onClick={()=>dispatch({type:'BACK'})}><ChevronLeft size={23}/></button>:<span className="brand-mark" aria-hidden="true"><i/><i/></span>}
        <a className="wordmark" href="#main-content">benchmate<span>✳</span></a>
        <button className="demo-button" onClick={()=>openModal('demo')} aria-label="Demo menu"><span className="demo-dot"/>Demo<MoreHorizontal size={18}/></button>
      </header>
      <main id="main-content" ref={scrollArea} className={`app-scroll ${isEntry?'entry':''} ${isFinish?'finished':''}`} tabIndex={-1}>
        {!saved&&<div className="notice" role="alert">Saving unavailable. Download a record from the saved-place menu before closing.</div>}
        <div className="title-block">
          <div className="task-kicker"><span>{state.paused?'YOUR PLACE, KEPT':recovering?'RECOVERY / FIRST LAYER':isEntry?'PROJECT 001 / THE LITTLE CAT':isFinish?'A LITTLE THING, MADE BY YOU':step.label.toUpperCase()}</span><button className="icon-button save-button" aria-label={saved?'Saved on this browser':'Saving unavailable'} onClick={()=>openModal('save')}><Bookmark size={17}/></button></div>
          <h1 ref={heading} tabIndex={-1}>{title}</h1>
          {isEntry&&<p className="intro-copy">From a spool of possibility<br/>to something with personality.</p>}
          {isFinish&&<p className="intro-copy">{state.purpose==='gift'?'A little gift. Made with care.':'A new companion for your desk.'}</p>}
        </div>
        <ProductScene type={state.paused?'cat':sceneType} lifting={recovering||state.scenario==='lifting'} compact={!isEntry&&!isFinish}/>
        <div className="task-content">
          {state.paused?<><p className="task-description"><strong>{state.name||'Little cat'}</strong> · {step.label}{state.issue&&' · Issue still open'}</p><div className="notice"><Pause size={18}/><span>Only the guide is paused. Your printer has not been paused or stopped.</span></div><p className="fineprint">Saved on this browser. No cross-device sync.</p></>:recovering?<RecoveryContent state={state}/>:<>
            {isEntry?<button className="equipment-row" onClick={()=>openModal('setup')}><span className="equipment-icon"><Printer size={22}/></span><span><strong>Bambu Lab X1 Carbon</strong><small>PLA Basic · Gold Textured PEI</small></span><ArrowUpRight size={18}/></button>:!isFinish&&<p className="task-description">{step.body}</p>}
            {state.step==='personalize'&&<div className="personalize"><fieldset className="purpose"><legend>This one is…</legend>{[['desk','For my desk'],['gift','As a gift']].map(([value,label])=><label key={value} className={state.purpose===value?'selected':''}><input type="radio" name="purpose" checked={state.purpose===value} onChange={()=>dispatch({type:'UPDATE',patch:{purpose:value}})}/>{label}{state.purpose===value&&<Check size={16}/>}</label>)}</fieldset><label className="input-label" htmlFor="project-name">Give it a name <span>optional</span></label><input id="project-name" value={state.name} maxLength={48} placeholder="Little cat" onChange={e=>dispatch({type:'UPDATE',patch:{name:e.target.value}})}/></div>}
            {state.step==='studio'&&<>{restartCheckpoint&&<div className="notice"><RotateCcw size={18}/><span>New attempt. Review the plate preset and slice again; do not resume the failed job.</span></div>}<dl className="setup-list"><div><dt>Printer</dt><dd>X1 Carbon · 0.4 mm</dd></div><div><dt>Plate</dt><dd>Textured PEI · X1 size</dd></div><div><dt>Material</dt><dd>Bambu PLA Basic</dd></div></dl><p className="fineprint">Visualization only. No printable file is supplied.</p></>}
            {state.step==='plate'&&<details><summary>A ready plate looks like…<ChevronRight size={17}/></summary><p>No scraps or fingerprints; clean, dry and flat on the magnetic platform. If cleaning is needed, use water, a sponge and dish detergent without oils or moisturizers. Rinse and dry.</p><SourceLinks ids={['clean','plate']}/></details>}
            {state.step==='filament'&&<div className="inset"><Layers size={19}/><p>Keep the loaded spool if it matches. For PLA on this plate, Bambu specifies the upper glass cover off.</p></div>}
            {state.step==='start'&&<div className="handoff"><span>BENCHMATE</span><ArrowRight size={18}/><strong>Bambu Studio</strong><p>Printing starts in the official controls.<br/>This button opens the demo.</p></div>}
            {state.step==='firstLayer'&&<div className={`observation ${state.scenario==='lifting'?'warning':''}`}><span className="status-dot"/><span><strong>{state.scenario==='lifting'?'Demo example · lifting edge':'Demo example · connected lines'}</strong><small>Your observation is the checkpoint.</small></span></div>}
            {state.step==='printing'&&<div className="inset"><Bookmark size={18}/><p>Your place is saved. Pausing this guide never pauses the printer.</p></div>}
            {state.step==='cooling'&&<div className="notice"><AlertCircle size={18}/><span>Check the actual hardware. Benchmate has no temperature reading and cannot confirm it is safe to touch.</span></div>}
            {state.step==='quality'&&<div className="checks">{[['object','I’ve checked the object'],['workspace','I’ve restored the workspace']].map(([key,label])=><label key={key}><input type="checkbox" checked={state.quality[key]} onChange={e=>dispatch({type:'UPDATE',patch:{quality:{...state.quality,[key]:e.target.checked}}})}/><span>{label}</span></label>)}</div>}
            {isFinish&&<><div className="finish-record"><CircleCheck size={24}/><div><strong>{state.name.trim()||'Little cat'}</strong><span>{state.purpose==='gift'?'A gift':'For my desk'} · Demo journey complete</span></div><button className="icon-button" aria-label="View my project story" onClick={()=>openModal('progress')}><ArrowUpRight size={18}/></button></div><div className="mini-history"><span>4 phases explored</span><span>{state.restartCount?`${state.restartCount} restart worked through`:'A smooth demo journey'}</span></div><label className="input-label" htmlFor="project-note">One thing to remember <span>optional</span></label><textarea id="project-note" rows={2} maxLength={500} placeholder="A note for next time…" value={state.note} onChange={e=>dispatch({type:'UPDATE',patch:{note:e.target.value}})}/></>}
          </>}
          {!isEntry&&<div className="content-tools"><button onClick={()=>openModal('sources')}><BookOpen size={15}/>Sources</button>{!isFinish&&!state.paused&&<button onClick={()=>dispatch({type:'PAUSE'})}><Pause size={15}/>Save & pause guide</button>}</div>}
        </div>
      </main>
      <footer className="action-dock">
        <div className="glass-ribs" aria-hidden="true"/>
        <div className="dock-meta"><span><span className={`status-dot ${state.issue?'amber':''}`}/>{state.issue?'Issue saved with your project':isEntry?'A guided demo. No printer needed.':isFinish?'Your project, remembered.':state.paused?'Only the guide is paused.':'One step at your pace.'}</span><button className="help-button" onClick={()=>openModal('help')}><HelpCircle size={16}/>Help</button></div>
        <button className="primary" disabled={disabled} onClick={primaryAction}><span>{action}</span><span className="action-arrow">{isFinish&&!state.paused?<Download size={19}/>:<ArrowRight size={22}/>}</span></button>
        {!state.paused&&(state.step==='firstLayer'&&!recovering?<button className="issue-button" onClick={()=>dispatch({type:'REPORT'})}><AlertCircle size={15}/>Something looks wrong</button>:recovering&&state.issue.stage==='question'?<button className="issue-button" onClick={()=>dispatch({type:'OBSERVE',value:'unknown'})}>I’m not sure / something else</button>:recovering&&state.issue.stage==='support'?<button className="issue-button" onClick={()=>dispatch({type:'CORRECT_REPORT'})}>I reported this by mistake</button>:state.step==='quality'&&disabled?<p className="dock-note">Check both items above to finish.</p>:null)}
        <nav className="phase-nav" aria-label="Project phases">{phases.map((name,i)=><div key={name} aria-current={step.phase===i?'step':undefined} className={`phase ${step.phase===i?'active':''} ${phasesDone[i]?'done':''}`}><span className="phase-track"/><span>{i===1?'At printer':name}</span></div>)}<button className="icon-button" aria-label="View checkpoint details" onClick={()=>openModal('progress')}><MoreHorizontal size={19}/></button></nav>
        <div className="home-indicator" aria-hidden="true"/>
      </footer>
      {toast&&<div className="toast" role="status"><Check size={17}/>{toast}</div>}
      {modal&&<Dialog title={{help:'A little help',sources:'Behind this step',setup:'Our setup',progress:'Your project story',save:'Your place, kept',demo:'Demo controls',reset:'A fresh start?',support:'Bring the context'}[modal]} onClose={closeModal}><ProjectSheets {...{modal,state,step,recovering,question,setQuestion,setModal,saved,closeModal,dispatch,downloadRecord}}/>{modal==='setup'&&<p className="fineprint">3D materials are a visual study, not actual material properties. Independent prototype; no Bambu Lab affiliation.</p>}</Dialog>}
    </section>
    <aside className="preview-detail"><span className="detail-line"/><span>01 / MATERIAL STUDY</span><p>Satin celadon.<br/>Soft light.<br/>A little character.</p><div className="material-swatch" aria-hidden="true"/><small>Designed for the moments<br/>between starting and finishing.</small></aside>
  </div>;
}

function RecoveryContent({state}){
  const stage=state.issue.stage;
  if(stage==='question')return <><p className="task-description">Is the first layer lifting or moving away from the plate?</p><p className="fineprint">One observation, not an automatic diagnosis.</p></>;
  if(stage==='stop')return <><p className="task-description">End the failed job using Bambu Studio or the printer’s controls. Let the plate and toolhead cool before handling anything.</p><div className="notice"><AlertCircle size={18}/><span>Do not clean a plate while a job is active. A detached first layer needs a new attempt, not a resumed job.</span></div></>;
  if(stage==='clean')return <><p className="task-description">With the job ended and the plate cool, remove oils that can weaken adhesion.</p><ol className="recovery-list"><li>Wash with water, a sponge and dish detergent without oils or moisturizers.</li><li>Rinse and dry fully. Hold the edges. No acetone.</li><li>Reseat the plate flat against its alignment stops.</li></ol><details><summary>Why this check?<ChevronRight size={17}/></summary><p>Bambu’s guide explains that oils and debris reduce adhesion. Alcohol can spread oils over the textured surface. Cleaning is a possible fix, not a confirmed diagnosis.</p></details></>;
  if(stage==='restart')return <><p className="task-description">Return to Bambu Studio. Match the Textured PEI preset, review a new slice and keep bed leveling on.</p><div className="inset"><RotateCcw size={19}/><p>We’ll revisit setup. The failed job is not resumed, and Benchmate sends nothing to your printer.</p></div></>;
  return <><p className="task-description">This doesn’t match the issue covered here. Keep it open and bring your project context to official support.</p><div className="notice"><Bookmark size={18}/><span>Your issue and checkpoint stay saved together.</span></div></>;
}
