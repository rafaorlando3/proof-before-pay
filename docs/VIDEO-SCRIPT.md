# Proof Before Pay: 3-minute video script (draft 2, English, honest)

Base: frozen agent/evidence baseline 7a66726; real console captures from the private build-154 lab.
The documentation/UI successor is 9287fb5. This remains a script; no final video has been recorded. Narrated by Rafael (his voice optional; the
on-screen text is his). The main mode shown is RECORDED (rules + replay); the caption says so in every scene. The native
live run with Gemini was validated in a separate one-scenario rehearsal and is shown only as a labelled still, not as a
benchmark. Nothing in this script claims a probability, a prize, a published article or a public demo.

Prerequisite line for the description (not narrated): "Install needs the InterSystems AI Hub EAP build 154 image, obtained
from the vendor portal and loaded locally; the repository ships no image. Then `docker compose up`."

0:00-0:18  Title card over the logo. "An online store gets Pix payments that do not reconcile: paid twice, paid late, paid
           the wrong amount. When an AI agent helps decide those, the question is not whether it is smart. It is whether
           you can prove afterwards what it saw, what it did not see, and what it was allowed to do."
           Caption: "Proof Before Pay. Sealed before anything moves."

0:18-0:40  Console, real screen, queue on the left. Open a DUPLICATE CHARGE case (agent path, not R1): two Pix payments for
           one order, different timestamps. Caption: "Recorded mode: rules plus replayed agent decisions; no live
           inference in this take." The flow stepper shows Evidence (5 tool calls), Proposal, Seal, Review, Test effect.
           Narration: "The agent reads the order, the Pix events, the payer history, the evidence and the store policy
           through scoped read-only tools. It proposes a refund of 18990 minor units, that is 189.90 BRL, to the same
           payer, and flags that a person must approve."
           NOTE: if the only duplicate case available on the day is decided by rule R1 (same payer, same amount), say
           "the rule closes this one; the agent handles the ambiguous ones" and show the ambiguous case next. Never show a
           rules case as if the agent decided it.

0:40-1:05  Same case, Decision card. Point at "Saw" and "Did not see (sealed as missing)". Narration: "What the agent did
           not get is sealed as missing. Later evidence cannot be presented as if it had been in this sealed decision." Then the AMBIGUOUS case (missing gate):
           the recorded proposal was accept_order without human review despite declaring a missing carrier signature.
           The guard refused it and sealed an escalation. The proposal is an unsealed diagnostic, not proof of
           an unchanged original model output. Fabricated-reference refusal belongs to the separate invented_ref case. Caption: "A refused proposal never becomes money."

1:05-1:35  Review card of the duplicate-charge case: amount, currency, destination, "TEST ledger", the exact commitment
           being approved. Approve as the synthetic reviewer (an authenticated test login; do not name Rafael as the
           approver). Narration: "The approval is sealed and chained to the decision. A single-use permit is bound to that
           seal. The test ledger executes once and returns a receipt." Show permit status consumed, receipt verification
           intact, and the sequence numbers sealed < authorized < executed. Caption: "One permit, one effect."
           Do NOT narrate "ten identical requests give one receipt" unless the UI action is filmed; the concurrency test
           (39 ledger checks, 12 sessions) is cited in the description instead.

1:35-2:05  Try to tamper: open the sealed record copy, change the amount, verify: tampered. Change a missing field:
           tampered. Restore: intact. Narration: "The verifier recomputes the commitment from the record. It detects any
           edit of a copy." Caption, honest limit: "Local seals: this proves a copy was changed. It does not protect
           against someone who can rewrite the database itself; external anchoring is out of scope."

2:05-2:30  Time machine: the inputs and the actual tool outputs the agent saw, model and mode label, tokens, cost label
           ("none (recorded replay)" here; "estimated from tokens x price table" on live decisions). Cut to the Management
           Portal visual trace: Intake, Decide, Agent operation, Witness, TestLedger, Workflow task, each message carrying
           the commitment. Caption: "Native Interoperability: every step is a message."

2:30-2:45  Still image, labelled "Live run, one scenario, Gemini via Google's OpenAI-compatible endpoint": the same flow
           with a real model call, 5 tool calls, one test effect. Narration: "With your own key the agent runs live; the
           seal records which model and mode decided. One scenario is a smoke test, not a benchmark."

2:45-3:00  Close over the logo: "Test ledger, synthetic data, local seals, recorded mode labelled as such. Repository on
           GitHub, MIT. The application combines native workflow messages, evidence checks and bound test effects.
           See the documented validation scope and related work." No "first", no numbers about chances, no article link until one exists.

## Scene checklist (what must be real on the day)
- Duplicate-charge case decided on the AGENT path with a test effect (not R1). If none exists in the lab, record the
  rules refund and say so; do not relabel.
- Ambiguous case with guard refusal (exists: adversarial missing_gate, see docs/screens/native-ui25.png).
- Reviewer = authenticated synthetic login; its name appears in the console and in the ledger audit.
- Tamper verdicts filmed live in the console, original seal still intact afterwards.
- Captions carry the mode (recorded / live) and "sandbox" wherever money appears.
