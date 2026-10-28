# Open Exchange submission draft (not submitted)

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
The recipient-observation correction subsequently passed a frozen live run of ten
post-fix regressions plus four prospective controls: six mandatory financial positives
closed with one intact synthetic receipt each, and eight negatives had zero effects.
There were 14 accepted protected outcomes and 13 raw proposals without frozen-label
problems; one dangerous raw proposal was contained by refund-binding enforcement.
Claude's independent JSON reports match ours. This is not a fresh held-out cohort or
population-quality estimate. See [the failed result](validation/live-v3-failed.json),
[post-fix scope](validation/live-v4-regression-controls.json), and
[independent review and supplied artifacts](validation/independent-v4-review.json).

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
- [x] Authenticated HTTPS viewer backed by running IRIS: two explicitly selected synthetic cases, recorded proposals, case-scoped seals/receipts and copy verification. Review, intake and model calls are disabled.
- [ ] Optional public live-inference access with its own quota/BYOK; the viewer does not provide this.
- [x] Model/protocol/routing provider and actual trial usage/cost recorded; unknown billing kept reserved.
- [x] Pre-frozen regression controls include successful financial paths and zero-effect negatives.
- [x] Final candidate UI/text cross-review received (C-1196): UI156, provenance index, public prose, private article and video script3.1 accepted, with editorial follow-ups. Core6d source review and v4 independent evidence review are complete (C-1189/C-1192/C-1194).
- [ ] Fully disjoint post-fix held-out quality acceptance; v4 currently provides explicitly qualified regression/prospective-control evidence.
- [x] Cold/lifecycle, native IPM application and fresh-volume bootstrap acceptance completed; see [installation scope](validation/native-installation-IPM.json) and [bootstrap qualifications](validation/native-IPM-bootstrap.json).
- [x] 168-second native-workflow review cut exported in four languages. Rafael approved the narration/languages; Claude accepted4.2 visuals and requested the4.2.1 public-footer correction. Final visual/submission approval remains separate.
- [ ] Final package reviewed and approved by Rafael for Open Exchange submission.
- [ ] Actual Open Exchange receipt/status captured after submission.

A sealing bridge alone is insufficient for this contest's workflow requirement.
Do not submit this draft before the remaining gates and Rafael's final approval.

Internal delivery deadline: **8 November 2026, 18:00 America/Asuncion**.
The [official contest page](https://openexchange.intersystems.com/contest/49) lists
8 November 2026, 23:59:59 EST (9 November, 01:59:59 in Paraguay).

## Video and authenticated demonstration

The 168-second review cut shows a recorded agent proposal on actual native IRIS,
a fresh case approved once by an authenticated test reviewer, one intact synthetic
receipt, explicit missing evidence, a copied-record tamper test and the bounded
results of the separate frozen live evaluation. It does not represent replay as
live inference. The [four-language production script](VIDEO-SCRIPT.md) and
[canonical JSON source](video/script-v4.json) identify every scene and qualification.
Narration is synthetic, not Rafael’s voice. The English master has Portuguese,
Spanish and Mandarin alternatives and four closed-caption tracks. Language choice
is for accessibility, with no multilingual-video bonus or certified pronunciation
review claimed. The exported media and final review kit remain separate from the
source ZIP.

The authenticated viewer reads the running private IRIS backend through a narrow
[demo gateway](../demo_gateway/README.md). It exposes two selected synthetic cases,
with matching subset counters. It allows inspection and copy verification, with no
intake, approvals or paid model calls. Viewer credentials are private and never
embedded in a URL, source package or video. Public HTTPS and the browser login
were verified; publishing the contest entry remains subject to Rafael’s final OK.
Owned service units now start the viewer, private relay and existing lab container at boot.
A bounded timer restores only the exact demo route after a shared proxy reload, with
ETag protection and no full-config replacement. An actual remove/recover rehearsal
preserved every previous route, the tracked proxy file and the intact receipt. The
IRIS container was not restarted; a full shared-host reboot was not performed. See
[the service-recovery scope](validation/demo-service-recovery.json).

The EAP archive and derived images must never enter the source package or a public registry.

## Source candidate

From a clean committed checkout, run `python3 scripts/package_source.py /absolute/output/directory`
to produce a deterministic source ZIP and per-file SHA-256 manifest. The output must be outside the
checkout. Committed files are written with fixed ZIP timestamps, ordering and Unix permissions,
without platform-dependent compression. The packaging gate excludes credentials, private evaluation data and the separately licensed
vendor kit. This source archive is a candidate, not an Open Exchange submission or approval request.
The fully disjoint post-fix held-out quality gate and Rafael's final review remain separate from the qualified regression/prospective evidence and prepared media.

## Current installation qualification

The earlier clean272 attempt is retained as a qualified historical result: its functional workflow passed, but the unrelated-container identity guard failed without a retained initial identity set. That earlier run is not relabelled as a fully audited acceptance pass.

Subsequent cold/lifecycle acceptance of the native backend baseline passed with matching runtime files and external container identity/state/image/health/mount snapshots. Native IPM application loading, local-package generation, uninstall without purge, and reinstall preserved the original intact receipt and one effect. See [native installation and IPM scope](validation/native-installation-IPM.json).

A separate fresh-volume vendor IPM bootstrap and first application load passed once with process-local diagnostic tracing, followed by48 recorded checks. The cause of the earlier NAMESPACE/PushNS failure and repeatability without tracing remain unproved. See [fresh-bootstrap qualifications](validation/native-IPM-bootstrap.json).

The current candidate additionally contains the separately verified UI replay-loading correction, gateway access/copy changes and presentation documentation. These are not represented as a new cold-image or bootstrap run. The latest native deployment changed the UI asset only, with the same IRIS container/start time and mounts. See [the separately validated UI correction](validation/ui-replay-loading42.json). No public IPM-registry installation is claimed.
