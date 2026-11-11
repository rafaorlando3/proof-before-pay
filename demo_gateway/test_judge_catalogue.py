"""Read-only catalogue and local-guide contracts; no backend, model or credentials."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node exercises the shipped UI functions")
class JudgeCatalogueTests(unittest.TestCase):
    def run_js(self, checks):
        panel = Path(__file__).with_name("live_panel.html").read_text()
        script, = re.findall(r"<script>(.*?)</script>", panel, re.S)
        pure = script.split("\n(()=>{\n", 1)[0]
        harness = "const assert=require('node:assert/strict'),vm=require('node:vm');const ctx={};vm.runInNewContext(JSON.parse(require('node:fs').readFileSync(0,'utf8')),ctx);\n" + checks
        result = subprocess.run([shutil.which("node"), "-e", harness], input=json.dumps(pure), text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_availability_is_server_driven_and_constructed_labels_require_exact_ids(self):
        self.run_js(r"""
const ids=['video-demo:d83544a2','public-live:lite35_f3ac72b4c4b9412b9d664e0f73e38ebe','recipient-flow:absent:bfe5c8fd','pix-0006:70dc920238','pix-0005:70dc920238','pix-0007:70dc920238','pix-0008:70dc920238','recipient-flow:mismatch:bfe5c8fd','adversarial:4ae70281:missing_gate','adversarial:4ae70281:invented_ref','adversarial:4ae70281:refund_flag'];
const input=ids.map(case_id=>({case_id,status:'awaiting_human'})),original=JSON.stringify(input);
const rows=ctx.proofDeskCatalogue(input);assert.equal(rows.length,11);assert.equal(rows.filter(r=>r.constructed).length,3);
assert.equal(ctx.proofDeskCatalogue(input,'effect').length,1);assert.equal(ctx.proofDeskCatalogue(input,'human').length,2);assert.equal(ctx.proofDeskCatalogue(input,'stopped').length,7);assert.equal(ctx.proofDeskCatalogue(input,'live').length,1);
assert.equal(ctx.proofDeskCatalogue(input,'all','closed account')[0].id,'pix-0008:70dc920238');
assert.equal(ctx.proofDeskCatalogue(input.slice(0,2)).length,2);assert.equal(ctx.proofDeskCatalogue([]).length,0);
assert.equal(ctx.proofDeskCatalogue([...input,input[0],null,{case_id:12}]).length,11);
const unknown=ctx.proofDeskCatalogue([{case_id:'adversarial:new-install:missing_gate'},{case_id:'public-live:new-legitimate'},{case_id:'__proto__'}]);
assert(unknown.every(r=>r.constructed===false));assert.equal(unknown[1].group,'live');assert.equal(unknown[0].title,'Retained example');
assert.equal(JSON.stringify(input),original); // Neither metadata nor filtering can alter server data.
""")

    def test_checklist_has_per_case_persistence_reset_and_storage_failure_fallback(self):
        self.run_js(r"""
const saved=new Map(),storage={getItem:k=>saved.get(k),setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)};
const value=[true,false,true,false,true];assert.equal(JSON.stringify(ctx.proofDeskChecklist(storage,'A',value)),JSON.stringify(value));
assert.equal(JSON.stringify(ctx.proofDeskChecklist(storage,'A')),JSON.stringify(value));assert(ctx.proofDeskChecklist(storage,'B').every(v=>!v));
ctx.proofDeskChecklist(storage,'B',[true,true,true,true,true]);ctx.proofDeskChecklist(storage,'A',null);assert(ctx.proofDeskChecklist(storage,'A').every(v=>!v));assert(ctx.proofDeskChecklist(storage,'B').every(Boolean));
saved.set('pbp49-inspection:malformed','{bad');assert(ctx.proofDeskChecklist(storage,'malformed').every(v=>!v));
saved.set('pbp49-inspection:badshape','true');assert(ctx.proofDeskChecklist(storage,'badshape').every(v=>!v));
const denied={getItem:()=>{throw Error('denied');},setItem:()=>{throw Error('denied');},removeItem:()=>{throw Error('denied');}};
assert.equal(JSON.stringify(ctx.proofDeskChecklist(denied,'C',value)),JSON.stringify(value));assert(ctx.proofDeskChecklist(null,'C').every(v=>!v));
assert.equal(saved.size,3); // Stored data contains only per-case booleans, no juror identity or server write.
""")

    def test_nonfinancial_acknowledgement_requires_verified_decision_and_bound_review_note(self):
        self.run_js(r"""
const d={case:{case_id:'mismatch',status:'closed'},decision:{commitment:'decision1',requires_human:true,proposal:{action:'refund_duplicate'}},events:[{kind:'human_approved'}],seals:[{kind:'decision',commitment:'decision1',ledger_state:''}],permit:'',receipt:''};
const r={steps:[{kind:'decision',commitment:'decision1',verification:{state:'intact'},record:{case:{id:'mismatch'},decision:{action:'escalate_to_human',moves_money:false},model:{mode:'recorded'}}},{kind:'approval',verification:{state:'intact'},record:{case:{id:'mismatch'},human:{approves:'decision1',note:'Automated recorded recipient regression; not Rafael approval.'}}}],tool_calls:[]};
let f=ctx.proofDeskFacts(d,r);assert.equal(f.review,'Acknowledged; no payment authority');assert.equal(f.effect,'No permit or receipt');assert.match(f.reviewNote,/Automated/);
r.steps[1].record.human.approves='other-decision';assert.equal(ctx.proofDeskFacts(d,r).reviewNote,'');r.steps[1].record.human.approves='decision1';r.steps[1].verification.state='tampered';assert.equal(ctx.proofDeskFacts(d,r).reviewNote,'');
r.steps[0].verification.state='tampered';assert.equal(ctx.proofDeskFacts(d,r).review,'Review not established from verified record');
r.steps[0].verification.state='intact';d.receipt={status:'effected',receipt_id:'synthetic:receipt',verification:'intact'};f=ctx.proofDeskFacts(d,r);assert.equal(f.review,'Recorded approval');assert.match(f.effect,/Intact synthetic receipt/);
d.receipt='';d.case.status='closed_no_effect';d.seals[0].ledger_state='blocked:test_recipient_required';r.steps[0].record.decision={action:'refund_duplicate',moves_money:true};f=ctx.proofDeskFacts(d,r);assert.equal(f.review,'Acknowledged; no payment authority');assert.equal(f.effect,'Ledger refused: test_recipient_required');
""")


if __name__ == "__main__":
    unittest.main()
