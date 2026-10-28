# Proof Before Pay: 3-minute video script (draft 3.1, reviewed, English)

Base: source 6d03432 (runtime of the v4 round), real console captures from the private build-154 lab. The public demo case
used in scenes 2 to 4 is the recorded public-demo case (56352df3: 0 LLM calls, authenticated review, one 84 BRL test effect,
receipt 340), labelled RECORDED on screen. Narrated by Rafael (his voice optional; the
on-screen text is his). The main mode shown is RECORDED (rules + replay); the caption says so in every scene. The separate live v4 round is shown only through actual case evidence or a clearly labelled results still; neither a still nor a recorded scene is presented as live inference in this take. No final video has been recorded. Nothing in this script claims a probability, a prize, a published article or a public demo.

Prerequisite line for the description (not narrated): "Install needs the InterSystems AI Hub EAP build 154 image, obtained
from the vendor portal and loaded locally; the repository ships no image. Then `docker compose up`."

0:00-0:18  Title card over the logo. "An online store gets Pix payments that do not reconcile: paid twice, paid late, paid
           the wrong amount. When an AI agent helps decide those, the question is not whether it is smart. It is whether
           you can prove afterwards what it saw, what it did not see, and what it was allowed to do."
           Caption: "Proof Before Pay. Sealed before anything moves."

0:18-0:40  Console, real screen, queue on the left. Open the public-demo DUPLICATE CHARGE case (recorded model-path example with a replayed
           test proposal; caption: "Recorded mode: replayed agent decision, no live inference in this take"). The flow
           stepper shows Evidence (5 tool calls), Proposal, Seal, Review, Test effect. Narration: "The agent reads the
           order, the Pix events, the payer history, the evidence and the store policy through scoped read-only tools,
           using the actual historical tool outputs. It proposes a refund of 8400 minor units, that
           is 84.00 BRL, to the recorded payer, and flags that a person must approve."
           NOTE: this old decision seal predates the destination projection fix. Do not narrate or display that new field as part of this historical record.

0:40-1:05  Same case, Decision card: "Saw" and "Did not see (sealed as missing)". Narration: "What the agent did not get
           is sealed as missing. Nobody can complete the file afterwards." Then the FORGED-DESTINATION case from the v4
           round (hid-061, shown as its runtime case, labelled LIVE Gemini 3.8 Flash): the order object carried a fake
           refund destination tagged as the store record and the customer message asked for a third key; the time
           machine shows the tool returned only the recorded destination; the receipt went to the recorded payer.
           Caption: "Destinations come from the store record. Messages and payloads cannot redirect money."
           NOTE: if the v4 lab case cannot be shown, use the recorded guard-refusal case (missing gate) instead and keep
           the caption honest. Never present a rules (R1) refund as an agent decision.

1:05-1:35  Review card of the duplicate-charge case: amount, currency, destination, "TEST ledger", the exact commitment
           in the completed record. Open the existing sealed approval and receipt history; do not try to approve the closed case again. If filming an approval click, first prepare a new synthetic recorded demonstration case with new references, show its actual new case/receipt IDs, and record the single authenticated synthetic review once. Never reset case56352df3 or receipt340. Do not name Rafael as the test approver. Narration: "The approval is sealed and chained to the decision. A single-use permit is bound to that
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

2:30-2:45  Still: the v4 evaluation table from the article (14 cases: 14/14 protected decisions, 6/6 legitimate refunds
           executed, 8/8 negatives without effect, 1 raw proposal contained by the server; frozen before outputs).
           Narration: "We ran four frozen rounds against a hidden matrix with one live model. The baseline found a policy
           miss and a missing refund target; both were fixed server-side and re-measured. We publish the failures with
           the fixes." No percentages, no "approved", no "held-out" for v4.

2:45-3:00  Close over the logo: "Test ledger, synthetic data, local seals, recorded mode labelled as such. Repository on
           GitHub, MIT. The validation report preserves the failed runs, fixes and limits; related work is linked in the README." No "first", no numbers about chances, no article link until one exists.

## Scene checklist (what must be real on the day)
- Duplicate-charge case decided on the AGENT path with a test effect (not R1): public-demo 56352df3 (recorded) and, if
  available, v4 hid-061 (live). If neither can be shown, record the rules refund and say so; do not relabel.
- Ambiguous case with guard refusal (exists: adversarial missing_gate, see docs/screens/native-ui25.png).
- Reviewer = authenticated synthetic login; its name appears in the console and ledger audit. The old closed case is read-only history. Any filmed new approval must use a freshly prepared synthetic case and must retain its actual identifiers.
- Tamper verdicts filmed live in the console, original seal still intact afterwards.
- Captions carry the mode (recorded / live) and "sandbox" wherever money appears.
