// Layer 3: user project state. Navigation never means completion.
import { steps, stepById } from './data/project.js';
export const STORAGE_KEY = 'benchmate.project.v1';
export function freshState() { return { version: 1, step: 'intro', name: 'Little cat', purpose: 'desk', completed: [], issue: null, history: [], note: '', quality: { object: false, workspace: false }, paused: false, scenario: 'expected', restartCount: 0, updatedAt: null }; }
export function restoreState(raw) {
  try {
    const p = JSON.parse(raw);
    if (!p || p.version !== 1 || !stepById[p.step] || !Array.isArray(p.completed)) return freshState();
    const validIssue = p.issue && ['question', 'stop', 'clean', 'support', 'restart'].includes(p.issue.stage);
    return { ...freshState(), step: p.step, name: typeof p.name === 'string' ? p.name.slice(0,48) : 'Little cat', purpose: p.purpose === 'gift' ? 'gift' : 'desk', completed: [...new Set(p.completed.filter(id=>stepById[id] && id !== 'intro' && id !== 'complete'))], issue: validIssue ? { stage: p.issue.stage, observation: String(p.issue.observation || '').slice(0,200), returnStep: stepById[p.issue.returnStep] ? p.issue.returnStep : 'firstLayer' } : null, history: Array.isArray(p.history) ? p.history.filter(h=>typeof h === 'string').slice(-40) : [], note: typeof p.note === 'string' ? p.note.slice(0,500) : '', quality: { object: p.quality?.object === true, workspace: p.quality?.workspace === true }, paused: p.paused === true, scenario: p.scenario === 'lifting' ? 'lifting' : 'expected', restartCount: Number.isInteger(p.restartCount) && p.restartCount >= 0 ? p.restartCount : 0, updatedAt: p.updatedAt || null };
  } catch { return freshState(); }
}
export function reducer(state, event) {
  let next = state;
  switch(event.type) {
    case 'UPDATE': next = {...state, ...event.patch}; break;
    case 'NEXT': {
      if (state.issue || state.paused || (state.step === 'quality' && (!state.quality.object || !state.quality.workspace)) || (state.step === 'firstLayer' && state.scenario === 'lifting')) return state;
      const index = steps.findIndex(s=>s.id===state.step);
      if(index === steps.length - 1) return state;
      next = {...state, step: steps[index+1].id, completed: state.step === 'intro' ? state.completed : [...new Set([...state.completed, state.step])], history: state.history.includes(state.step) ? state.history : [...state.history,state.step]}; break;
    }
    case 'BACK': { if(state.issue || state.paused) return state; const index=steps.findIndex(s=>s.id===state.step); next={...state, step: steps[Math.max(0,index-1)].id}; break; }
    case 'PAUSE': next = {...state, paused: true}; break;
    case 'RESUME': next = {...state, paused: false}; break;
    case 'REPORT': next = {...state, issue: { stage: 'question', observation: '', returnStep: state.step }}; break;
    case 'OBSERVE': next = {...state, issue: {...state.issue, stage: event.value === 'loose' ? 'stop' : 'support', observation: event.value === 'loose' ? 'First layer lifting or moving on the plate' : 'Issue is unclear or does not match the example'}}; break;
    case 'RECOVERY_NEXT': if (!state.issue) return state; next = {...state, issue: {...state.issue, stage: state.issue.stage === 'stop' ? 'clean' : 'restart'}}; break;
    case 'RESTART': if(state.issue?.stage !== 'restart') return state; next = {...state, step: 'studio', issue: {...state.issue, stage: 'restart'}, completed: state.completed.filter(id=>id==='personalize'), quality: { object: false, workspace: false }, restartCount: state.restartCount + 1, history: [...state.history, 'Failed first layer: ended attempt; reviewed cleaning; returned to Studio'], scenario:'expected'}; break;
    case 'REVIEWED_RESTART': if (state.issue?.stage !== 'restart' || state.step !== 'studio') return state; next = {...state, issue: null}; break;
    case 'CORRECT_REPORT': next = {...state, step: state.issue?.returnStep || state.step, issue:null, history:[...state.history,'Issue report withdrawn by user']}; break;
    case 'DEMO_SCENARIO': next = {...state, scenario: event.value === 'lifting' ? 'lifting' : 'expected'}; break;
    case 'RESET': return freshState();
    default: return state;
  }
  return {...next, updatedAt:new Date().toISOString()};
}
export function projectRecord(state) {
  return `BENCHMATE · PROJECT RECORD\n${state.name.trim() || 'Little cat'} · ${state.purpose === 'gift' ? 'A gift' : 'For my desk'}\nIndependent demo, not evidence of a physical print.\n\nEquipment: Bambu Lab X1 Carbon / 0.4 mm / Bambu PLA Basic / X1 Textured PEI / external spool\nCheckpoint: ${stepById[state.step].label}\nCompleted checkpoints: ${state.completed.join(', ') || 'None'}\nUnresolved issue: ${state.issue ? state.issue.observation || 'Observation pending' : 'None'}\nRecovery stage: ${state.issue?.stage || 'None'}\nDemo restarts: ${state.restartCount}\n\nHistory:\n${state.history.join('\n')}\n\nNote: ${state.note || 'No note added.'}\n\nSaved locally; no printer data or sensor readings.\n`;
}
