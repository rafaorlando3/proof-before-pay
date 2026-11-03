# Proof Before Pay, Open Exchange release description

Proof Before Pay seals what an AI Hub agent observed, what evidence was missing and what it proposed before a synthetic payment effect.

The application runs inside an InterSystems IRIS Interoperability production on AI Hub EAP build 154. Simple cases use deterministic rules. When no rule matches, the native agent reads five scoped tools: order, payments, payer history, evidence and store policy. The server checks the proposal, preserves the evidence and missing fields, and requires authenticated Workflow approval before an eligible duplicate refund can receive a single-use test permit and an intact synthetic receipt. The review console replays the sealed observations and lets a juror edit a copy to see intact versus tampered verification.

Audited paired result, 1 November

In a final informed 12-case test frozen before any output (cases and rubric by one reviewer, a deterministic baseline frozen beforehand by another, one admitted run after two infrastructure aborts with no case output), the native agent's raw proposals were correct in 11 of 12 cases, against 7 for rules with safe abstention and 8 for the deterministic baseline, with no unsafe agent decision. The pre-registered criterion (at least two more correct decisions than both baselines, zero unsafe, all controls) was met. The baseline made one unsafe decision (a synthetic double refund). One correct agent refund was safely blocked because the test ledger does not accept that exception label, and the agent missed one required missing-evidence declaration. Descriptive evidence on these cases only: not blind, not a population estimate, not general superiority. Estimated cost US$0.026, not an invoice.

The secondary effective-decision reading was 10/12 for the agent, 7/12 for rules and 8/12 for the deterministic baseline. The r4 eligible-effect label in the committed gold was an authoring error; it was kept unchanged and still counts against the agent in the effective reading. The test ledger executes duplicate refunds only for duplicate_payment or duplicate_charge, never because model prose requests a broader action.

Judge journey

The basic authenticated judge journey was checked through automated browser navigation with Rafael signing in manually, including the evidence/approval/permit/receipt chain, a missing-recipient case without effect, and a tampered/restored record copy at 303, 390, 980 and 1100 pixels. This is not an independent human study. Logout and recovery-code consumption were not run, to preserve access. The online viewer and video show earlier recorded examples, not the v7 run; replay makes no model call.

Installation and scope

Follow the English README in the source repository. Obtain the licensed build-154 AI Hub Community image from the InterSystems EAP portal, load it locally, and use the supplied Dockerfile/Compose recipe. The vendor image and derived images are not distributed. Source-only IPM loading, packaging and non-purge uninstall/reinstall were qualified on the owner's already loaded licensed image under amd64 emulation on Apple Silicon; this was not a fresh portal download, a public IPM-registry installation or an independent human install.

All effects are synthetic. Local salted commitments detect changes against a retained trusted commitment; they do not provide external notarization or resist an administrator who can rewrite the database and its commitments. No real payment or blockchain transaction is performed. No general model superiority or production payment readiness is claimed.

Source: https://github.com/rafaorlando3/proof-before-pay
