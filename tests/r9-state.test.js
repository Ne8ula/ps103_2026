import test from 'node:test';
import assert from 'node:assert/strict';
import {freshState,reducer,restoreState,phaseStatus,DEMO_PHOTO} from '../src/state.js';
const act=(s,type,rest={})=>reducer(s,{type,...rest});
const until=(s,id)=>{for(let i=0;s.step!==id&&i<15;i++)s=act(s,'NEXT');return s;};
test('migrates v1 paused recovery and completed records without discarding choices',()=>{
 const old={...freshState(),version:1,step:'firstLayer',name:'Original Cat',note:'Keep me',paused:true,issue:{stage:'clean',observation:'Loose lines',returnStep:'firstLayer'},completed:['personalize','studio','plate','filament','start']};
 const s=restoreState(JSON.stringify(old));assert.equal(s.version,2);assert.equal(s.route,'guide');assert.equal(s.note,'Keep me');assert.equal(s.issue.stage,'clean');assert.equal(s.paused,true);
 const completed=restoreState(JSON.stringify({...old,step:'complete',issue:null,completed:[...old.completed,'firstLayer','printing','cooling','quality']}));assert.equal(completed.records[0].name,'Original Cat');
});
test('all phase markers use actual completion, including backward navigation',()=>{
 let s=until(freshState(),'plate');assert.deepEqual(phaseStatus(s).map(p=>p.done),[true,false,false,false]);s=act(s,'BACK');assert.equal(s.completed.includes('plate'),false);assert.equal(phaseStatus(s)[1].done,false);
 s=until(s,'printing');assert.equal(phaseStatus(s)[2].done,false);assert.equal(phaseStatus(s)[2].current,true);
});
test('photo cancel, processing, pause and reload preserve exactly the chosen image',()=>{
 let s=act(until(freshState(),'firstLayer'),'REPORT');assert.equal(act(s,'PHOTO_PROCESS'),s);
 s=act(s,'PHOTO_SELECT',{photo:{src:DEMO_PHOTO,name:'Demo'}});s=act(s,'PHOTO_PROCESS');s=act(s,'PAUSE');s=restoreState(JSON.stringify(s));assert.equal(act(s,'PHOTO_DONE'),s);assert.equal(s.issue.photo.src,DEMO_PHOTO);
 s=act(s,'RESUME');s=act(s,'ISSUE_STAGE',{stage:'capture'});assert.equal(s.issue.photo.src,DEMO_PHOTO);assert.equal(act(s,'PHOTO_DONE').issue.stage,'capture');s=act(s,'PHOTO_PROCESS');s=act(s,'PHOTO_DONE');assert.equal(s.issue.stage,'finding');assert.equal(s.issue.photo.src,DEMO_PHOTO);
});
test('uploaded images never inherit the demonstration finding',()=>{
 let s=act(until(freshState(),'firstLayer'),'REPORT');s=act(s,'PHOTO_SELECT',{photo:{src:'data:image/png;base64,YQ==',name:'Photo.png',kind:'demo'}});s=act(s,'PHOTO_PROCESS');s=act(s,'PHOTO_DONE');assert.equal(s.issue.photo.kind,'selected');assert.match(s.issue.observation,/not analyzed/);
 const malicious=act(s,'PHOTO_SELECT',{photo:{src:'https://example.com/tracker.jpg'}});assert.equal(malicious,s);
});
test('records persist independently of the next guide and note edits update the right record',()=>{
 let s=until(freshState(),'quality');s=act(s,'UPDATE',{patch:{quality:{object:true,workspace:true}}});s=act(s,'NEXT');const id=s.records[0].id;s=act(s,'UPDATE',{patch:{note:'A gift'}});assert.equal(s.records[0].note,'A gift');
 s=act(s,'START_PROJECT');assert.equal(s.records[0].id,id);assert.equal(s.note,'');s=restoreState(JSON.stringify(s));s=act(s,'OPEN_RECORD',{id});assert.equal(s.route,'record');assert.equal(s.step,'personalize');
});
test('saved ideas, profile, community interactions and draft survive reload and guide reset',()=>{
 let s=act(freshState(),'SAVE_IDEA',{id:'tray'});s=act(s,'PROFILE',{patch:{name:'Alex',reducedMotion:true}});s=act(s,'APPRECIATE');s=act(s,'COMMENT',{text:'My private draft'});s=act(s,'SHARE');s=act(s,'DRAFT',{value:'My caption'});s=act(s,'RESET');s=restoreState(JSON.stringify(s));assert.deepEqual(s.savedIdeas,['tray']);assert.equal(s.profile.name,'Alex');assert.equal(s.profile.reducedMotion,true);assert.equal(s.comments[0],'My private draft');assert.equal(s.draft.caption,'My caption');assert.equal(s.appreciated,true);
});
test('pause freezes recovery confirmations and prevents clearing unresolved issue',()=>{
 let s=act(until(freshState(),'firstLayer'),'REPORT');s=act(s,'OBSERVE',{value:'loose'});s=act(s,'PAUSE');for(const type of ['RECOVERY_NEXT','CORRECT_REPORT','RESTART','ISSUE_BACK'])assert.equal(act(s,type),s);assert.equal(act(s,'RECOVERY_CHECK',{key:'ended',value:true}),s);
});
test('restart is counted once and keeps the issue until reviewed setup',()=>{
 let s=act(until(freshState(),'firstLayer'),'REPORT');s=act(s,'OBSERVE',{value:'loose'});for(const key of ['ended','cooled'])s=act(s,'RECOVERY_CHECK',{key,value:true});s=act(s,'RECOVERY_NEXT');s=act(s,'RECOVERY_NEXT');s=act(s,'RESTART');assert.equal(act(s,'RESTART').restartCount,1);assert.equal(act(s,'NEXT').step,'studio');
});
import {loadStoredProject,STORAGE_KEY} from '../src/state.js';
test('storage migration keeps the original and corrupt data gets a visible recovery copy',()=>{
 const values=new Map(),storage={getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v)};
 const old=JSON.stringify({...freshState(),version:1,step:'firstLayer',name:'Keep This'});values.set(STORAGE_KEY,old);let boot=loadStoredProject(storage);assert.equal(boot.state.name,'Keep This');assert.equal(values.get('benchmate.project.v1.backup'),old);
 values.set(STORAGE_KEY,'broken json');boot=loadStoredProject(storage);assert.match(boot.notice,/recovery copy/);assert.equal([...values.entries()].find(([k])=>k.startsWith('benchmate.project.recovery.'))[1],'broken json');
});
test('failed backup never silently overwrites an old or unreadable project',()=>{
 const old=JSON.stringify({...freshState(),version:1,step:'plate',name:'My Original'});const storage={getItem:k=>k===STORAGE_KEY?old:null,setItem:()=>{throw Error('Full');}};let boot=loadStoredProject(storage);assert.equal(boot.state.name,'My Original');assert.equal(boot.writeAllowed,false);
 boot=loadStoredProject({getItem:()=>'{bad',setItem:()=>{throw Error('Full');}});assert.equal(boot.writeAllowed,false);assert.match(boot.notice,/untouched/);
});
