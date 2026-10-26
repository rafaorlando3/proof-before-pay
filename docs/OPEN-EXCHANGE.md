# Open Exchange submission draft — not submitted

Application name: **Proof Before Pay**

Repository: https://github.com/rafaorlando3/proof-before-pay

License: MIT (application code only).

Maintainer profile: https://community.intersystems.com/user/rafaelorlando-mendes

Target short description:
Seal an AI agent's decision evidence before action, surface missing information,
and let a reviewer detect changed evidence and decisions.

Current implementation description:
The foundation supplies a reproducible isolated IRIS AI Hub EAP build154 lab, an
ObjectScript Witness class with real embedded-Python tests, and matching Python /
TypeScript canonical sealing vectors. It detects changes to a sealed decision and
keeps local-only evidence in the pending state. Inputs and fixtures are synthetic.
No payment, wallet, model credential or on-chain verification is enabled by default.
The native AI Hub / Interoperability application workflow is still to be integrated.

## Acceptance gates before requesting Rafael's final OK

- [x] Separate MIT repository without PixSettle Git history or secrets.
- [x] Build154 startup defect reproduced and corrected.
- [x] Dockerfile / Compose and English install instructions.
- [x] Witness compiled and both methods tested in actual build154 IRIS.
- [x] TypeScript/Python test workflow prepared.
- [ ] GitHub workflow confirmed green for the published commit.
- [ ] Claude review received for the corrected bridge and intended workflow.
- [ ] Native AI Hub agent participates in a working Interoperability production.
- [ ] Current app demo, reviewer UI and end-to-end workflow evidence.
- [ ] Model/provider and any inference cost explicitly resolved before a live call.
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

This is a recording plan. No video or native workflow result is claimed yet.
The EAP archive and derived images must never enter the source package or a public registry.
