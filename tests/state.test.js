import test from 'node:test';
import assert from 'node:assert/strict';
import {freshState, reducer, restoreState, projectRecord} from '../src/state.js';
const act=(s,type,rest={})=>reducer(s,{type,...rest});
const until=(s,id)=>{let guard=0;while(s.step!==id&&guard++<15)s=act(s,'NEXT');return s;};
test('happy path requires explicit quality checks and records completion',()=>{
 let s=until(freshState(),'quality'); assert.equal(s.completed.includes('quality'),false); assert.equal(act(s,'NEXT').step,'quality');
 s=act(s,'UPDATE',{patch:{quality:{object:true,workspace:true}}});s=act(s,'NEXT');assert.equal(s.step,'complete');assert.equal(s.completed.length,9);
});
test('back and help-equivalent no-op never complete visited steps',()=>{
 let s=act(freshState(),'NEXT');assert.equal(s.step,'personalize');assert.deepEqual(s.completed,[]);s=act(s,'BACK');assert.deepEqual(s.completed,[]);s=act(s,'NEXT');assert.deepEqual(s.completed,[]);
});
test('recovery survives reload, invalidates downstream checkpoints, and needs review',()=>{
 let s=until(freshState(),'firstLayer');s=act(s,'REPORT');s=act(s,'OBSERVE',{value:'loose'});s=restoreState(JSON.stringify(s));assert.equal(s.issue.stage,'stop');assert.equal(act(s,'NEXT').step,'firstLayer');
 assert.equal(act(s,'RECOVERY_NEXT').issue.stage,'stop');
 s=act(s,'RECOVERY_CHECK',{key:'ended',value:true});s=act(s,'RECOVERY_CHECK',{key:'cooled',value:true});
 s=act(s,'RECOVERY_NEXT');s=act(s,'RECOVERY_NEXT');s=act(s,'RESTART');assert.equal(s.step,'studio');assert.equal(s.restartCount,1);assert.deepEqual(s.completed,['personalize']);assert.equal(s.issue.stage,'restart');
 s=restoreState(JSON.stringify(s));assert.equal(act(s,'NEXT').step,'studio');s=act(s,'REVIEWED_RESTART');s=act(s,'NEXT');assert.equal(s.step,'plate');s=until(s,'firstLayer');assert.equal(s.issue,null);assert.equal(s.scenario,'expected');
});
test('unknown issue stays unresolved through save, pause and reload',()=>{
 let s=until(freshState(),'firstLayer');s=act(s,'REPORT');s=act(s,'OBSERVE',{value:'unknown'});s=act(s,'PAUSE');s=restoreState(JSON.stringify(s));assert.equal(s.paused,true);s=act(s,'RESUME');assert.equal(s.issue.stage,'support');assert.equal(act(s,'NEXT').step,'firstLayer');assert.match(projectRecord(s),/Issue is unclear/);
});
test('pause cannot advance and name, note, observations survive persistence',()=>{
 let s=act(freshState(),'UPDATE',{patch:{name:'Miso',purpose:'gift',note:'Handle the plate by its edges.'}});s=act(s,'PAUSE');assert.equal(act(s,'NEXT').step,'intro');s=restoreState(JSON.stringify(s));assert.equal(s.name,'Miso');assert.equal(s.purpose,'gift');assert.match(projectRecord(s),/Miso/);assert.match(s.note,/edges/);
});
test('lifting scenario cannot be accepted as good; reset clears issue and note',()=>{
 let s=until(freshState(),'firstLayer');s=act(s,'DEMO_SCENARIO',{value:'lifting'});assert.equal(act(s,'NEXT').step,'firstLayer');s=act(s,'REPORT');s=act(s,'RESET');assert.deepEqual(s,freshState());
});
test('corrupt and unsupported storage versions recover to an honest fresh start',()=>{
 for(const raw of ['no json','null','{}','{"version":7,"step":"complete"}','{"version":1,"step":"missing","completed":[]}'])assert.deepEqual(restoreState(raw),freshState());
});
