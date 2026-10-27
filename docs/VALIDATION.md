# Validation on 26 October 2026

The native workflow has been exercised in a dedicated, synthetic x86-64 Linux build154 laboratory.
The public CI and private licensed-runtime gates are deliberately separate.

| Gate | Observed result | Scope |
|---|---|---|
| TypeScript reference | 20 vectors and typecheck passed in foundation validation | S0 source unchanged |
| Python reference | 24 vectors passed in foundation validation | S0 source unchanged |
| Offline boundary suites | 47 methods passed; forbidden network/process attempts 0 | Witness adapter, ledger plan, intake guards |
| Native Witness bridge | 12 checks passed | Actual ObjectScript → embedded Python, no model |
| Native ledger | 39 checks plus 12 independent IRIS execution sessions | One effect, identical receipts, authenticated review, TTL, tampering, loss/retry |
| Native unit suites | 21 methods; framework reports All PASSED | Rules, output contract, scope isolation, permits, receipt projection tampering |
| Native Production replay | 48 checks on ten fresh synthetic cases | Service → Process → recorded agent/tools → Workflow review → seal approval → permit → one effect → readback |
| Native adversarial workflow | Three development attacks now await human review, with intact seals and zero permits/receipts | Inconsistent financial intent, fabricated evidence ref, declared missing evidence without review |
| Actual HTTP workflow | 34 checks | Authenticated reviewer session, version binding, CSRF header, copied-record tamper, timeline/tool retrieval, refusal paths |
| Real model integration | Gemini, GPT-5.4 Mini and Claude Haiku each completed one synthetic scenario | Five native tools, sealed decision/approval, authenticated test review, one sandbox effect; not a quality benchmark |
| Actual browser | Approve closes synthetic case; modified amount returns tampered | IRIS-backed API, not a mock API |

These counts are different kinds of evidence, not interchangeable test totals. Native unit tests are gated
on the framework's actual result: RunTest returning status1 alone does **not** mean assertions passed.
Missing JSON markers and missing expected methods fail the runtime runners.

JSON evidence and a SHA-256 manifest of runtime source are in [validation/](validation/).
The live-provider trial and clean-volume/lifecycle gates describe baseline commit
`db7c75c7ec5cf32730bf1f13ba4e489a758db7bf`. The later reviewer-note fix was rebuilt into image
`sha256:8debd0af12fc80ea0dbd491ce4a9aab6019a22bd3f435605ef321004a1832002`
and passed 20 native unit methods plus all 48 replay E2E checks. Its source manifest hash is
`9c03e9be300d888d49a6e432837b70b39678169b2ece93c81226256624df68fd`;
[review-note-regression.json](validation/review-note-regression.json) binds those checks to that source.
The unchanged ledger lifecycle was not rerun for this two-class note fix.
The server's full logs remain private; they are not required to distribute vendor code or credentials.

## Boundaries and remaining gates

- Replay is labelled recorded, and has zero LLM calls. It does not establish AI Hub live inference.
- Real inference was tested through OpenRouter using the native OpenAI-compatible provider, not three
  direct vendor APIs. See [live-provider-smoke.json](validation/live-provider-smoke.json) for original
  synthetic records, generation ids, usage and defects. Total provider-reported cost: US$0.01699175;
  one failed HTTP 404 request has an unreconciled US$0.114858 reservation, retained conservatively.
- The baseline live trial exposed missing reviewer notes in approval seals. `%FormValues` is a native
  array; storing/reading its `pbp_note` entry fixes the defect. Subsequent replay assertions require
  both approval and rejection notes to be sealed. Original live receipts were retained unchanged.
- Anthropic's rationale confused minor units with BRL; the bound effect amount remained correct.
  GPT-5.4 Mini initially failed parameter routing and safely escalated. Its successful trial omitted
  unsupported temperature in the private gateway. No model-quality winner or ensemble benefit is claimed.
- Root ledger data is journaled in a named IRIS durable volume. Restart and recreation retained original
  confirmed receipts in lifecycle testing. A fresh volume compiled all classes, installed and started the Production, then passed all native suites. Restart, container recreation and SIGKILL recovery retained the verified original receipt and one effect. This tests process termination, not a host power loss. The replay test also refused a live-key environment before setup or case feed.
- Every refund in this application requires authenticated review. Test review sessions are synthetic
  automation; they do not represent Rafael approving a real payment or contest submission.
- No bank/chain transaction, settlement, independent timestamp or external anchoring is claimed.
  An administrator who can replace all local evidence can rewrite local history.
- No Open Exchange submission or public demo has been published by these tests. Rafael's final OK is required.

## Model-context regression

At baseline `d39c7085ed5ed7f8274c332adfa24270861cafe7`, three syntactically valid recorded proposals
incorrectly closed their cases without review: `refund_full` with `moves_money=false`, an invented
evidence reference, and a declared missing signature with `requires_human=false`. None moved money.
[Original reproduction](validation/adversarial-before.json) is retained rather than rewritten.

The corrected path rejects each proposal for its specific reason, seals an escalation, preserves
declared missing evidence and actual tool outputs, and leaves the native human task open with no
permit or receipt. The same native runner also verifies the ten original cases and successful
review paths. Offline positive controls include complete nonfinancial cases, genuine false/zero
evidence and all three captured live-provider proposals, so a broken guard that rejects everything
cannot satisfy the regression. Model explanations still need independent evaluation.

These cases were authored by Codex during development. Claude's peer review has arrived; the held-out model benchmark
remains pending; no new live inference, calibrated quality ranking or three-agent advantage is claimed.

Final context-guard runtime: `sha256:644a631e1d7453f4d2bab9f921189e21b86d095efc0b36f1042f2a0e389869a1`. Source manifest SHA-256:
`397c53c98b5e79393c4b2d2f652e9f90956eb2d18db292547906a9f2cf3c8a6d` (95 baked runtime files matched).
[Native regression evidence](validation/decision-guard-regression.json) contains the 20 native unit
methods, 48 original E2E checks and three adversarial cases with their expected refusal reasons.
No paid inference was performed in this later regression. HTTP workflow passed 34 checks again.

## Subsequent direct Gemini key trial

[Direct Google evidence](validation/gemini-direct-smoke.json) records one successful native workflow
with the context guard active: five tools, explicit missing delivery proof, authenticated test review,
sealed reviewer note, one consumed permit and one verified sandbox effect. Two API generations used
2,557 prompt and 340 completion tokens; standard-price estimate US$0.00319275, actual Google billing
unverified. The named Gemini provider's unsupported private-route configuration was discovered and
is rejected explicitly; the successful trial used the native OpenAI-compatible provider against Google.
These are different claims and are labelled separately. No additional model-quality ranking is implied.

The subsequent provider-configuration correction passed **21 native unit methods**, all 48 original
E2E checks and all three adversarial cases. The runner requires the new constructor/configuration
method by name as well as the framework's All PASSED result. Runtime image `sha256:1074da796e1a1eb3c3ec659255265b157a0fa91578475f6f6b1d623154d36f4e`
matched 95 source files; manifest SHA-256 `49d4b34066a9a044d18f1cefd5151ef983458de47caa8d9e5969e781b7ed27c9`.
See [provider configuration regression](validation/native-provider-config-regression.json).

## Claude review and UI v2.3 integration

Claude independently reviewed a45e801 in C-1163. The integration exposes seal source and ledger state
at sealing, distinguishes refund approval from nonfinancial/blocked acknowledgement, and shows the
original validated proposal as an **unsealed, non-authoritative diagnostic**. Context guards and
policy determine the separately sealed decision; neither the diagnostic nor its UI authorizes money.

The original seven deterministic cases from the private 40-case matrix ran natively: four authenticated
synthetic reviews produced one verified sandbox receipt each, and three blocked plans closed with no
effect. All 40 intake/routing classifications were checked, with no LLM calls. The 33 model cases have
not been run. Source cases, labels and detailed results remain private. The evaluator needs correction
before its aggregate is meaningful: it currently calls a correctly blocked financial proposal dangerous
and expects a different missing-destination reason than the ledger returns. These issues were found in
the deterministic controls before any paid model benchmark; the answer key was not tuned to model results.

Transport temperature metadata uses -1 for unknown/omitted values and Gemini 3.8's ignored parameter,
without changing the frozen S0 schema or rewriting historical seals. Billing wrappers explicitly state
billing_verified=false. Actual receipts, API-reported charges and list-price estimates remain distinct.

The integrated runtime image `sha256:65a234e7631ad6be26e4c52b780fc22dc7d82a9e460b9adef09698a7b4b7ee69`
passed 21 native unit methods, 48 E2E checks and all three adversarial refusals with original proposals
preserved. Its 96 baked runtime files match source manifest SHA-256
`935583d1fdbce937d643fa7f23a91053b069b5dce3c8f5f10cb262205518f532`.
The authenticated HTTP suite passed all 34 checks against that runtime. See
[native integration evidence](validation/native-ui23-regression.json) and
[HTTP integration evidence](validation/http-ui23-regression.json). These are recorded-mode tests,
with no new paid inference. The cold-start and durability tests above remain evidence for their
explicitly identified baseline; they were not repeated for this UI/diagnostic change.

## Portable source archive

The initial source packaging gate repeated successfully within each host, but its Git-generated ZIP
bytes differed between macOS and Linux CI for the same 649a952 commit. This is a packaging defect,
not a native workflow result. Packaging now reads committed Git files and writes an uncompressed ZIP
with sorted entries, fixed timestamps and explicit Unix permissions, avoiding Git/zlib ZIP variation.
Runtime evidence above still describes the tested runtime snapshot; packaging-only changes do not
claim a rerun of the native workflow. Cross-host archive hashes must match before a source candidate
is treated as portable.

## Usage dashboard provenance and current runtime caveat

A read-only API addition separates stored model decision metadata into live, recorded and unknown-mode
buckets. Real native compilation, bucket totals and the four read-only HTTP endpoints were checked;
[stats-provenance.json](validation/stats-provenance.json) states the exact source/image and test limits.
Unknown historical modes remain unknown. Stored tokens/costs are not verified billing. No new inference
was made and unchanged native workflow/durability suites were not rerun for this reporting change.

The rebuilt lab serves the Production/API, but the vendor health check now reports alert/unhealthy.
Messages show 96.44% disk utilization and a startup SYS.ICM.Sharding method error; their separate
contributions to health have not yet been isolated. Do not treat HTTP availability as a passed runtime
health gate. This is an open infrastructure issue before final demonstration; no health check was
bypassed, no vendor method was stubbed and no other project's images/services were removed.
