import { steps, stepById, phases } from './data/project.js';
// Keep R2's key and migrate in place; the app first keeps a v1 backup.
export const STORAGE_KEY = 'benchmate.project.v1';
export const DEMO_PHOTO = '/demo-first-layer.svg';
const routes = ['home','catalog','detail','guide','collection','community','profile','share','preview','record'];
const issueStages = ['question','capture','processing','finding','stop','clean','support','restart'];
const text = (v,n,f='') => typeof v === 'string' ? v.slice(0,n) : f;
export function freshState() { return { version:2, route:'home', step:'intro', name:'Miso', purpose:'desk', completed:[], issue:null, history:[], note:'', quality:{object:false,workspace:false}, paused:false, scenario:'expected', restartCount:0, updatedAt:null, startedAt:null, savedIdeas:[], records:[], selectedRecord:null, collectionTab:'saved', profile:{name:'',bio:'',reducedMotion:false}, appreciated:false, comments:[], draft:{caption:'',recordId:null} }; }
function validPhoto(p) {
  if(!p || typeof p.src!=='string' || p.src.length>1600000)return null;
  if(p.src!==DEMO_PHOTO && !/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(p.src))return null;
  return {src:p.src,kind:p.src===DEMO_PHOTO?'demo':'selected',name:text(p.name,100,'Selected Photo')};
}
function projectFields(p) {
  const issue = p.issue && issueStages.includes(p.issue.stage) ? {stage:p.issue.stage,observation:text(p.issue.observation,200),returnStep:stepById[p.issue.returnStep]?p.issue.returnStep:'firstLayer',ended:p.issue.ended===true,cooled:p.issue.cooled===true,photo:validPhoto(p.issue.photo)} : null;
  return {step:stepById[p.step]?p.step:'intro',name:text(p.name,48,'Miso'),purpose:p.purpose==='gift'?'gift':'desk',completed:[...new Set((Array.isArray(p.completed)?p.completed:[]).filter(id=>stepById[id]&&!['intro','complete'].includes(id)))],issue,history:Array.isArray(p.history)?p.history.filter(h=>typeof h==='string').map(h=>h.slice(0,300)).slice(-40):[],note:text(p.note,500),quality:{object:p.quality?.object===true,workspace:p.quality?.workspace===true},paused:p.paused===true,scenario:p.scenario==='lifting'?'lifting':'expected',restartCount:Number.isInteger(p.restartCount)&&p.restartCount>=0?p.restartCount:0,updatedAt:text(p.updatedAt,40)||null,startedAt:text(p.startedAt,40)||null};
}
function snapshot(state,id=state.startedAt||'legacy'){return {...projectFields(state),id,issue:null,paused:false};}
export function restoreState(raw) {
  try {
    const p=JSON.parse(raw);
    if(!p || ![1,2].includes(p.version) || !stepById[p.step] || !Array.isArray(p.completed))return freshState();
    const s={...freshState(),...projectFields(p)};
    if(p.version===1){s.route=p.step==='intro'?'home':'guide';if(p.step==='complete'&&p.completed.includes('quality'))s.records=[snapshot(s,'legacy')];return s;}
    s.route=routes.includes(p.route)?p.route:'home';
    s.savedIdeas=Array.isArray(p.savedIdeas)?[...new Set(p.savedIdeas.filter(id=>['cat','tray','pebble'].includes(id)))]:[];
    s.records=Array.isArray(p.records)?p.records.filter(r=>r&&typeof r.id==='string'&&r.step==='complete'&&Array.isArray(r.completed)&&r.completed.includes('quality')).slice(-50).map(r=>({...projectFields(r),id:r.id.slice(0,60),issue:null,paused:false})):[];
    s.selectedRecord=s.records.some(r=>r.id===p.selectedRecord)?p.selectedRecord:null;
    s.collectionTab=p.collectionTab==='made'?'made':'saved';
    s.profile={name:text(p.profile?.name,48),bio:text(p.profile?.bio,180),reducedMotion:p.profile?.reducedMotion===true};
    s.appreciated=p.appreciated===true;
    s.comments=Array.isArray(p.comments)?p.comments.filter(c=>typeof c==='string').map(c=>c.slice(0,500)).slice(-20):[];
    s.draft={caption:text(p.draft?.caption,500),recordId:typeof p.draft?.recordId==='string'?p.draft.recordId:null};
    return s;
  } catch { return freshState(); }
}
export function phaseStatus(state){return phases.map((_,i)=>({current:stepById[state.step].phase===i,done:steps.filter(s=>s.phase===i&&!['intro','complete'].includes(s.id)).every(s=>state.completed.includes(s.id))}));}
export function loadStoredProject(storage){
  let raw;
  try{raw=storage.getItem(STORAGE_KEY);}catch{return {state:freshState(),notice:'Browser storage is unavailable. Download your record before closing.',writeAllowed:false};}
  if(!raw)return {state:freshState(),notice:'',writeAllowed:true};
  let p;try{p=JSON.parse(raw);}catch{}
  const supported=p&&[1,2].includes(p.version)&&Object.hasOwn(stepById,p.step)&&Array.isArray(p.completed);
  if(!supported){
    try{storage.setItem('benchmate.project.recovery.'+Date.now(),raw);}catch{return {state:freshState(),notice:'Your saved data could not be opened. The original is untouched; this session cannot overwrite it.',writeAllowed:false};}
    return {state:freshState(),notice:'Your saved data could not be opened. A recovery copy was kept in this browser; a fresh guide is ready.',writeAllowed:true};
  }
  if(p.version===1){try{if(!storage.getItem('benchmate.project.v1.backup'))storage.setItem('benchmate.project.v1.backup',raw);}catch{return {state:restoreState(raw),notice:'Your previous project was opened, but its backup could not be saved. Download a record before closing.',writeAllowed:false};}}
  return {state:restoreState(raw),notice:'',writeAllowed:true};
}
export function reducer(state,event) {
  let next=state;
  if(state.paused && ['NEXT','BACK','REPORT','OBSERVE','PHOTO_SELECT','PHOTO_PROCESS','PHOTO_DONE','ISSUE_STAGE','RECOVERY_CHECK','RECOVERY_NEXT','RESTART','REVIEWED_RESTART','CORRECT_REPORT'].includes(event.type))return state;
  switch(event.type) {
    case 'NAV':if(!routes.includes(event.route))return state;next={...state,route:event.route};break;
    case 'UPDATE':{const patch={};for(const key of ['name','purpose','note','quality'])if(key in event.patch)patch[key]=event.patch[key];next={...state,...patch};if(state.step==='complete')next.records=state.records.map(r=>r.id===(state.startedAt||'legacy')?snapshot(next,r.id):r);break;}
    case 'START_PROJECT':if(state.step!=='intro'&&state.step!=='complete')return {...state,route:'guide'};next={...freshState(),profile:state.profile,records:state.records,savedIdeas:state.savedIdeas,comments:state.comments,appreciated:state.appreciated,draft:state.draft,step:'personalize',route:'guide',startedAt:new Date().toISOString()};break;
    case 'NEXT':{
      if(state.issue||(state.step==='quality'&&(!state.quality.object||!state.quality.workspace))||(state.step==='firstLayer'&&state.scenario==='lifting'))return state;
      const i=steps.findIndex(s=>s.id===state.step);if(i===steps.length-1)return state;
      next={...state,route:'guide',step:steps[i+1].id,startedAt:state.startedAt||new Date().toISOString(),completed:state.step==='intro'?state.completed:[...new Set([...state.completed,state.step])],history:state.history.includes(state.step)?state.history:[...state.history,state.step]};
      if(next.step==='complete')next.records=[...state.records.filter(r=>r.id!==next.startedAt),snapshot(next)].slice(-50);
      break;
    }
    case 'BACK':{if(state.issue)return state;const i=steps.findIndex(s=>s.id===state.step);next={...state,step:steps[Math.max(0,i-1)].id,route:i<=1?'detail':'guide'};break;}
    case 'PAUSE':next={...state,paused:true,route:'guide'};break;
    case 'RESUME':next={...state,paused:false,route:'guide'};break;
    case 'REPORT':if(state.step!=='firstLayer'||state.issue)return state;next={...state,issue:{stage:'capture',observation:'First-layer concern',returnStep:state.step,ended:false,cooled:false,photo:null}};break;
    case 'PHOTO_SELECT':if(!state.issue||!validPhoto(event.photo))return state;next={...state,issue:{...state.issue,stage:'capture',photo:validPhoto(event.photo)}};break;
    case 'PHOTO_PROCESS':if(!state.issue?.photo||state.issue.stage!=='capture')return state;next={...state,issue:{...state.issue,stage:'processing'}};break;
    case 'PHOTO_DONE':if(state.issue?.stage!=='processing')return state;next={...state,issue:{...state.issue,stage:'finding',observation:state.issue.photo.kind==='demo'?'Demo example: an edge may be lifting; cause unconfirmed':'User-selected photo; not analyzed; cause unconfirmed'}};break;
    case 'ISSUE_BACK':if(!state.issue||state.paused)return state;next={...state,issue:{...state.issue,stage:({processing:'capture',finding:'capture',stop:'finding',clean:'stop',restart:'clean',support:state.issue.photo?'finding':'capture'})[state.issue.stage]||'capture'}};if(next.issue.stage==='finding'&&!next.issue.photo)next.issue.stage='capture';break;
    case 'ISSUE_STAGE':if(!state.issue||!['capture','support','stop'].includes(event.stage))return state;next={...state,issue:{...state.issue,stage:event.stage}};break;
    case 'OBSERVE':if(!state.issue)return state;next={...state,issue:{...state.issue,stage:event.value==='loose'?'stop':'support',observation:event.value==='loose'?'First layer lifting or moving on the plate':'Issue is unclear or does not match the example'}};break;
    case 'RECOVERY_CHECK':if(state.issue?.stage!=='stop'||!['ended','cooled'].includes(event.key))return state;next={...state,issue:{...state.issue,[event.key]:event.value===true}};break;
    case 'RECOVERY_NEXT':if(state.issue?.stage==='stop'){if(!state.issue.ended||!state.issue.cooled)return state;next={...state,issue:{...state.issue,stage:'clean'}};}else if(state.issue?.stage==='clean')next={...state,issue:{...state.issue,stage:'restart'}};else return state;break;
    case 'RESTART':if(state.issue?.stage!=='restart'||state.step==='studio')return state;next={...state,step:'studio',completed:state.completed.filter(id=>id==='personalize'),quality:{object:false,workspace:false},restartCount:state.restartCount+1,history:[...state.history,'Failed first layer: ended attempt; reviewed cleaning; returned to Studio'],scenario:'expected'};break;
    case 'REVIEWED_RESTART':if(state.issue?.stage!=='restart'||state.step!=='studio')return state;next={...state,issue:null};break;
    case 'CORRECT_REPORT':if(!state.issue)return state;next={...state,step:state.issue.returnStep,issue:null,history:[...state.history,'Issue report withdrawn by user']};break;
    case 'SAVE_IDEA':if(!['cat','tray','pebble'].includes(event.id))return state;next={...state,savedIdeas:state.savedIdeas.includes(event.id)?state.savedIdeas.filter(id=>id!==event.id):[...state.savedIdeas,event.id]};break;
    case 'COLLECTION_TAB':next={...state,collectionTab:event.value==='made'?'made':'saved'};break;
    case 'OPEN_RECORD':if(!state.records.some(r=>r.id===event.id))return state;next={...state,selectedRecord:event.id,route:'record'};break;
    case 'PROFILE':next={...state,profile:{...state.profile,...event.patch}};break;
    case 'APPRECIATE':next={...state,appreciated:!state.appreciated};break;
    case 'COMMENT':if(!event.text.trim())return state;next={...state,comments:[...state.comments,event.text.trim().slice(0,500)].slice(-20)};break;
    case 'SHARE':next={...state,route:'share',draft:{recordId:event.id||null,caption:event.id===state.draft.recordId?state.draft.caption:`Meet ${state.records.find(r=>r.id===event.id)?.name||state.name}`}};break;
    case 'DRAFT':next={...state,draft:{...state.draft,caption:event.value.slice(0,500)}};break;
    case 'DEMO_SCENARIO':next={...state,scenario:event.value==='lifting'?'lifting':'expected'};break;
    case 'RESET':return {...freshState(),profile:state.profile,records:state.records,savedIdeas:state.savedIdeas,comments:state.comments,appreciated:state.appreciated,draft:state.draft};
    default:return state;
  }
  return {...next,updatedAt:new Date().toISOString()};
}
export function projectRecord(s){return `BENCHMATE · PROJECT RECORD\n${s.name.trim()||'Little Cat'} · ${s.purpose==='gift'?'A Gift':'For My Desk'}\nIndependent guided demo, not evidence of a physical print.\n\nEquipment: Bambu Lab X1 Carbon / assumed 0.4 mm / Bambu PLA Basic / X1 Textured PEI / external spool\nCheckpoint: ${stepById[s.step]?.label||'Unknown'}\nCompleted checkpoints: ${s.completed.join(', ')||'None'}\nUnresolved issue: ${s.issue?s.issue.observation||'Observation pending':'None'}\nRecovery stage: ${s.issue?.stage||'None'}\nPhoto: ${s.issue?.photo?`${s.issue.photo.name} (not analyzed; image not included in text export)`:'None'}\nDemo restarts: ${s.restartCount}\n\nHistory:\n${s.history.join('\n')}\n\nNote: ${s.note||'No note added.'}\n\nSaved locally; no printer data or sensor readings.\n`;}
