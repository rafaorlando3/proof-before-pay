# Open Exchange submission draft — not submitted

Application name: **Proof Before Pay**

Repository: https://github.com/rafaorlando3/proof-before-pay

License: MIT (application code only).

Maintainer profile: https://community.intersystems.com/user/rafaelorlando-mendes

Target short description:
Seal an AI agent's decision evidence before action, surface missing information,
and let a reviewer detect changed evidence and decisions.

Current implementation description:
The application provides a native Interoperability Production: intake, deterministic policy, a scoped
AI Hub agent interface with recorded fallback, authenticated Workflow review, a sealed approval,
a single-use permit, one journaled sandbox effect and independently checked readback. The authenticated
console exposes the sealed chain, missing evidence, forensic tool outputs and a copied-record tamper test.
Model proposals also pass an I/O-free context check against observed tool outputs; inconsistent action
flags, fabricated references and missing evidence without review become sealed human escalations.
The full path has run with explicitly recorded decisions and in a private one-scenario integration
trial with real Gemini, OpenAI and Anthropic models through OpenRouter. This proves native tool and
workflow integration, not model quality or ensemble benefit. The live trial exposed a reviewer-note
bug and an amount-unit error in one model rationale; both are recorded in validation, and the note fix
has regression coverage. Inputs are synthetic; no real payment or external anchor is claimed.

## Acceptance gates before requesting Rafael's final OK

- [x] Separate MIT repository without PixSettle Git history or secrets.
- [x] Build154 startup defect reproduced and corrected.
- [x] Dockerfile / Compose and English install instructions.
- [x] Witness compiled and both methods tested in actual build154 IRIS.
- [x] TypeScript/Python test workflow prepared.
- [x] GitHub workflow confirmed green for the published commit (see validation and repository Actions).
- [ ] Claude review received for the corrected bridge and intended workflow.
- [x] Native AI Hub agent participates in a working Interoperability production, with actual native tool calls.
- [x] Private IRIS-backed reviewer UI and recorded end-to-end evidence.
- [ ] Public authenticated demo with qualified model inference.
- [x] Model/protocol/routing provider and actual trial usage/cost recorded; unknown billing kept reserved.
- [ ] Three-minute video demonstrating the final app and required links.
- [ ] Final package reviewed and approved by Rafael for Open Exchange submission.
- [ ] Actual Open Exchange receipt/status captured after submission.

A sealing bridge alone is insufficient for this contest's workflow requirement.
Do not submit this draft as a completed AI Hub application.

Internal delivery deadline: **8 November 2026, 18:00 America/Asuncion**.
The [official contest page](https://openexchange.intersystems.com/contest/49) lists
8 November 2026, 23:59:59 EST (9 November, 01:59:59 in Paraguay).

## Planned three-minute demonstration

0:00–0:25: a synthetic duplicate-payment exception enters the native production.
0:25–1:05: show the AI Hub agent's inputs, tool outputs and explicit missing evidence.
1:05–1:35: seal the decision before the guarded simulated action or human approval.
1:35–2:15: edit a copy of the decision; verification turns tampered without resealing.
2:15–2:45: demonstrate missing/unknown evidence and the human boundary.
2:45–3:00: show reproducible startup, repository, validation and cost/observability facts.

This is a recording plan. No video has been produced; native workflow results are in validation.
The EAP archive and derived images must never enter the source package or a public registry.
