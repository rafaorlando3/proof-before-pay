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

Later validation included 33 live Gemini workflows. Their original evaluation failed on a dangerous
decision involving repeated payment references; the Ledger prevented the effect. That result remains
recorded. After generic reference checks and deterministic refund-target binding were corrected,
eight pre-frozen regression workflows passed: two financial positives each produced one intact
synthetic receipt after test review, and six negatives produced no financial effect. One dangerous
raw model proposal was still intercepted by the guard. These eight cases establish regression and
positive-path evidence, not independent held-out model quality. See [validation](VALIDATION.md)
and [the aggregate result](validation/live-regression-v2.json).

The later ten-case live challenge failed all four mandatory financial positives because
the agent's tools omitted an existing refund destination. That failed result is retained.
The recipient-observation correction has passed native and recorded workflow regressions;
its live acceptance remains pending. A scorer accepting ten actions does not establish
that the four required refunds happened. See [the failed result](validation/live-v3-failed.json)
and [the correction's scope](validation/recipient-observability-fix.json).

## Acceptance gates before requesting Rafael's final OK

- [x] Separate MIT repository without PixSettle Git history or secrets.
- [x] Build154 startup defect reproduced and corrected.
- [x] Dockerfile / Compose and English install instructions.
- [x] Witness compiled and both methods tested in actual build154 IRIS.
- [x] TypeScript/Python test workflow prepared.
- [x] GitHub workflow confirmed green for the published commit (see validation and repository Actions).
- [x] Initial Claude code review received (C-1163); source/freeze review in C-1182 and independent v2 result review in C-1183, with artifact limits recorded in validation.
- [x] Native AI Hub agent participates in a working Interoperability production, with actual native tool calls.
- [x] Private IRIS-backed reviewer UI and recorded end-to-end evidence.
- [ ] Public authenticated demo with qualified model inference.
- [x] Model/protocol/routing provider and actual trial usage/cost recorded; unknown billing kept reserved.
- [x] Pre-frozen regression controls include successful financial paths and zero-effect negatives.
- [ ] Independent review of the final candidate source and its current evidence (eight-case export sent to Claude).
- [ ] Disjoint held-out acceptance completed, separating raw model quality from the guarded effective decision.
- [ ] Final operator installation/lifecycle acceptance with complete before/after audit evidence.
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

## Source candidate

From a clean committed checkout, run `python3 scripts/package_source.py /absolute/output/directory`
to produce a deterministic source ZIP and per-file SHA-256 manifest. The output must be outside the
checkout. Committed files are written with fixed ZIP timestamps, ordering and Unix permissions,
without platform-dependent compression. The packaging gate excludes credentials, private evaluation data and the separately licensed
vendor kit. This source archive is a candidate, not an Open Exchange submission or approval request.
The private held-out model benchmark, final demo/video and Rafael's final review remain separate gates.

## Current installation qualification

The build154 lab compiled and tested the current executable source on a fresh volume, including
Witness, Ledger, Workflow and receipt preservation across restart, recreation and SIGKILL. The
overall job nevertheless returned false on its unrelated-container ID guard and did not retain the
initial ID set. It is a qualified functional result, not a completed release-acceptance gate.
Preserving the IRIS hostname was separately tested during recreation, with matching external
container ID snapshots and the original receipt intact. That narrower check does not retroactively
repair the clean-install audit. See [the qualified result](validation/clean-current272-qualified.json)
and [the hostname diagnosis](IRIS-154.md). No new installation, inference, publication or submission
is implied by assembling a source candidate.
