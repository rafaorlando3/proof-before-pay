"""Replay is a presentation of retained facts, not an inference or effect runner."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node exercises the actual shipped presentation functions')
class CaseCinemaTests(unittest.TestCase):
    def run_js(self, assertions):
        panel = Path(__file__).with_name('live_panel.html').read_text()
        script, = re.findall(r'<script>(.*?)</script>', panel, re.S)
        pure = script.split('\n(()=>{\n', 1)[0]
        harness = """
const assert=require('node:assert/strict'),vm=require('node:vm');
const ctx={};vm.runInNewContext(JSON.parse(require('node:fs').readFileSync(0,'utf8')),ctx);
const d={ok:true,case:{case_id:'case1',status:'awaiting_human',session_id:1566},decision:{source:'model',commitment:'seal1',proposal:{action:'escalate_to_human'},requires_human:true,model:{mode:'live'}},seals:[],events:[]};
const record={case:{id:'case1'},saw:{inputs:{currency:'BRL'}},decision:{action:'escalate_to_human',evidence_refs:['policy.chunk:cited']},missing:{signature:null},model:{mode:'live'}};
const r={ok:true,steps:[{kind:'decision',commitment:'seal1',verification:{state:'intact'},record}],tool_calls:[{seq:1,name:'GetStorePolicy',duration_ms:0,output:{retrieval:{available:true,passages:[{chunk_id:'cited'},{chunk_id:'not-cited'}]}}}]};
""" + assertions
        result = subprocess.run([shutil.which('node'), '-e', harness], input=json.dumps(pure),
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_verified_case_binding_and_real_tool_citation_counts(self):
        self.run_js("""
const before=JSON.stringify([d,r]);const frames=ctx.proofDeskReplayFrames(d,r);
assert.equal(frames.length,6);assert.equal(frames[1].title,'GetStorePolicy');assert.match(frames[1].text,/2 local policy passages returned; 1 cited/);
assert.equal(frames[1].raw.duration_ms,0);assert.equal(frames.at(-2).title,'Awaiting human review');assert.equal(frames.at(-1).title,'No permit or receipt');assert.equal(frames.at(-1).tone,'stop');
assert.equal(JSON.stringify([d,r]),before);
r.steps[0].verification.state='tampered';assert.equal(ctx.proofDeskReplayFrames(d,r).length,0);
r.steps[0].verification.state='intact';record.case.id='case2';assert.equal(ctx.proofDeskReplayFrames(d,r).length,0);
record.case.id='case1';r.ok=false;assert.equal(ctx.proofDeskReplayFrames(d,r).length,0);
r.ok=true;d.ok=false;assert.equal(ctx.proofDeskReplayFrames(d,r).length,0);
""")

    def test_actual_refusal_rejection_and_receipt_states_are_not_payment_success(self):
        self.run_js("""
d.case.status='closed_no_effect';d.events=[{kind:'human_approved'}];d.seals=[{kind:'decision',commitment:'seal1',ledger_state:'blocked:test_recipient_required'}];
let frames=ctx.proofDeskReplayFrames(d,r);assert.equal(frames.at(-2).title,'Acknowledged; no payment authority');assert.match(frames.at(-1).title,/Ledger refused/);assert.equal(frames.at(-1).tone,'stop');
d.case.status='rejected';assert.equal(ctx.proofDeskReplayFrames(d,r).at(-2).title,'Rejected by reviewer');
d.receipt={receipt_id:'test:1',verification:'intact',status:'pending'};assert.equal(ctx.proofDeskReplayFrames(d,r).at(-1).tone,'stop');
d.receipt.status='effected';frames=ctx.proofDeskReplayFrames(d,r);assert.equal(frames.at(-1).tone,'effect');assert.match(frames.at(-1).text,/historical synthetic effect/);
d.receipt.verification='tampered';assert.equal(ctx.proofDeskReplayFrames(d,r).at(-1).tone,'stop');
""")

    def test_rules_and_absent_tools_are_not_animated_as_model_calls(self):
        self.run_js("""
r.tool_calls=[];d.decision.source='rules';d.decision.action='hold_for_evidence';delete d.decision.proposal;
let frames=ctx.proofDeskReplayFrames(d,r);assert.equal(frames[1].title,'No tool calls in this trace');assert.match(frames[1].text,/no model call is represented/);assert.match(frames[2].label,/RULES/);assert.match(frames[2].text,/not a model response/);
d.decision.source='model';assert.match(ctx.proofDeskReplayFrames(d,r)[1].text,/absence is not evidence/);
""")

    def test_clock_cancels_stale_callbacks_when_paused_disposed_hidden_or_switched(self):
        self.run_js("""
const tasks=[],cancelled=[],seen=[],states=[];let allowed=true;
const make=()=>ctx.proofDeskReplayClock({length:3,onFrame:i=>seen.push(i),onState:s=>states.push(s),schedule:(fn,delay)=>{tasks.push({fn,delay});return tasks.length;},cancel:id=>cancelled.push(id),canPlay:()=>allowed});
let clock=make();clock.play();assert.equal(tasks[0].delay,1800);clock.pause();tasks[0].fn();assert.equal(seen.length,0);assert(cancelled.includes(1));
clock.play();const old=tasks.at(-1);clock.seek(2);old.fn();assert.equal(seen.join(','),'2');assert.equal(states.at(-1).playing,false);
clock.play();assert.equal(seen.at(-1),0);const before=tasks.at(-1);clock.setSpeed(2);assert.equal(tasks.at(-1).delay,900);before.fn();assert.equal(seen.at(-1),0);
allowed=false;tasks.at(-1).fn();assert.equal(states.at(-1).playing,false);assert.equal(seen.at(-1),0);
allowed=true;clock.play();const stale=tasks.at(-1);clock.dispose();stale.fn();assert.equal(seen.at(-1),0);const count=tasks.length;clock.play();clock.seek(1);assert.equal(tasks.length,count);assert.equal(seen.at(-1),0);
clock=make();clock.play();tasks.at(-1).fn();assert.equal(seen.at(-1),1);tasks.at(-1).fn();assert.equal(seen.at(-1),2);assert.equal(states.at(-1).ended,true);assert.equal(states.at(-1).playing,false);
""")


if __name__ == '__main__':
    unittest.main()
