"""Exercise the shipped facade script without IRIS, network, models or browser credentials."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest


class Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cases = []
        self.targets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "data-judge-case" in attrs:
            self.cases.append(attrs["data-judge-case"])
        if tag == "button" and "data-proof-target" in attrs:
            self.targets.append(attrs["data-proof-target"])


@unittest.skipUnless(shutil.which("node"), "Node is needed for the shipped UI script contract")
class ProofDeskTests(unittest.TestCase):
    def test_navigation_all_outcomes_and_missing_cases_never_request_a_decision(self):
        panel = Path(__file__).with_name("live_panel.html").read_text()
        controls = Controls()
        controls.feed(panel)
        script, = re.findall(r"<script>(.*?)</script>", panel, re.S)
        harness = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
class Element {
  constructor(dataset={}) { this.dataset=dataset; this.handlers={}; this.hidden=false; this.textContent=''; this.attrs={}; this.scrolled=0; this.options=[]; }
  addEventListener(name, handler) { this.handlers[name]=handler; }
  setAttribute(name, value) { this.attrs[name]=value; }
  removeAttribute(name) { delete this.attrs[name]; }
  scrollIntoView() { this.scrolled++; }
  before() {}
  replaceChildren() { this.options=[]; }
  append(option) { this.options.push(option); }
}
const elements = new Map();
const get = id => { if(!elements.has(id)) elements.set(id,new Element()); return elements.get(id); };
const caseButtons=input.cases.map(judgeCase=>new Element({judgeCase}));
const navButtons=input.targets.map(proofTarget=>new Element({proofTarget}));
const flowSteps=Array.from({length:5},()=>new Element());
get('pbp-judge-guide').querySelectorAll=()=>caseButtons;
const classes=new Set(), views=[], opened=[], requests=[], saved=new Map(input.savedTheme?[['pbp49-proof-theme',input.savedTheme]]:[]);
const targets=Object.fromEntries(['.app','.queue','#detail','#replay','.tl','.seal','.decision','.decision + .card','#pbp-evaluation'].map(s=>[s,new Element()]));
const context={
 document:{hidden:false,body:{classList:{add:c=>classes.add(c),contains:c=>classes.has(c),toggle:(c,force)=>{if(force!==undefined){if(force)classes.add(c);else classes.delete(c);return force;}if(classes.has(c)){classes.delete(c);return false;}classes.add(c);return true;}}},
   getElementById:get,querySelector:s=>targets[s]||null,querySelectorAll:s=>s==='[data-proof-target]'?navButtons:s==='.flow .step'?flowSteps:[],createElement:()=>new Element()},
 state:{current:null,cases:[...new Set(input.cases)].map(case_id=>({case_id}))},
 setView:v=>views.push(v), refresh:async()=>{}, openCase:async(id,explicit)=>{opened.push({id,explicit});context.state.current=id;},
 fetch:async(path,options={})=>{requests.push({path,method:options.method||'GET'});return {ok:true,json:async()=>({ok:true,available:false,reason:'live_disabled_or_expired',scenarios:[]})};},
 crypto:{randomUUID:()=>{throw Error('A retained action must not allocate a LIVE request');}},
 sessionStorage:{getItem:()=>null},localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v)},matchMedia:()=>({matches:input.systemDark}),setInterval:()=>0,setTimeout:()=>{throw Error('No worker polling expected');},console
};
async function main(){
 vm.runInNewContext(input.script,context);
 await Promise.resolve(); await Promise.resolve();
 assert(classes.has('pbp-proof-desk'));
 const initialInk=input.savedTheme==='ink'||(!input.savedTheme&&input.systemDark);
 assert.equal(classes.has('pbp-ink'),initialInk);
 assert(navButtons.filter(b=>!['queue','evaluation'].includes(b.dataset.proofTarget)).every(b=>b.disabled));
 get('pbp-desk-theme').handlers.click();
 assert.equal(classes.has('pbp-ink'),!initialInk); assert.equal(get('pbp-desk-theme').attrs['aria-pressed'],String(!initialInk));
 get('pbp-desk-theme').handlers.click(); assert.equal(classes.has('pbp-ink'),initialInk);
 assert.equal(saved.get('pbp49-proof-theme'),initialInk?'ink':'paper');
 // An empty selection must not pretend an evidence panel exists.
 await navButtons.find(b=>b.dataset.proofTarget==='evidence').handlers.click();
 assert.match(get('pbp-desk-status').textContent,/Open a retained case first/); assert.equal(views.length,0);
 // Exercise every rendered case button, including both catalogue-only outcomes.
 for(const button of caseButtons){
   await button.handlers.click();
   assert.equal(opened.at(-1).id,button.dataset.judgeCase);
   assert.equal(opened.at(-1).explicit,true);
   assert.equal(get('pbp-desk-status').textContent,'');
   assert.equal(get('pbp-desk-current').textContent,'Case: '+button.dataset.judgeCase);
   assert.equal(navButtons.find(b=>b.dataset.proofTarget==='dossier').attrs['aria-current'],'location');
 }
 assert.equal(new Set(opened.map(c=>c.id)).size,4);
 for(const button of navButtons){ await button.handlers.click(); }
 assert(views.includes('queue')); assert(views.includes('case'));
 assert.equal(targets['#pbp-evaluation'].open,true);
 assert(navButtons.every(b=>!b.disabled));
 for(const step of flowSteps){assert.equal(step.attrs.role,'button');await step.handlers.click();let prevented=false;await step.handlers.keydown({key:'Enter',preventDefault:()=>{prevented=true;}});assert(prevented);}
 for(const selector of ['.queue','#detail','#replay','.tl','.seal']) assert(targets[selector].scrolled>0,selector);
 // An unavailable historical ID must not open another record or create a replacement run.
 context.state.cases=[]; const count=opened.length;
 await caseButtons.at(-1).handlers.click();
 assert.equal(opened.length,count); assert.match(get('pbp-judge-status').textContent,/no new decision was requested/);
 // Missing DOM sections must fail visibly, including after a view changes.
 delete targets['.seal']; await navButtons.find(b=>b.dataset.proofTarget==='seals').handlers.click();
 assert.equal(get('pbp-desk-status').hidden,false);
 assert(requests.length>0); assert(requests.every(r=>r.path==='/pbp/api/live'&&r.method==='GET'));
 assert.equal(get('pbp-live-run').disabled,true); assert.equal(get('pbp-live-scenario').disabled,true);
 console.log(JSON.stringify({ok:true,retained_outcomes:4,scenario_submissions:0,financial_actions:0,theme_roundtrip:true,missing_case_fails_closed:true}));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
"""
        for saved_theme, system_dark in [("paper", True), ("ink", False), (None, True), (None, False)]:
            with self.subTest(saved_theme=saved_theme, system_dark=system_dark):
                result = subprocess.run(
                    [shutil.which("node"), "-e", harness],
                    input=json.dumps({"script": script, "cases": controls.cases, "targets": controls.targets,
                                      "savedTheme": saved_theme, "systemDark": system_dark}),
                    text=True, capture_output=True, timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["retained_outcomes"], 4)
                self.assertEqual(json.loads(result.stdout)["scenario_submissions"], 0)


if __name__ == "__main__":
    unittest.main()
