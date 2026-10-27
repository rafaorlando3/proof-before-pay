# Proof Before Pay

**An InterSystems IRIS Interoperability workflow where an AI Hub agent decides payment exceptions, and every
decision is sealed before anything moves.** What the agent saw, what it did *not* see, what it was not allowed
to do and what it decided are committed to a salted hash before a human approves, before a permit exists and
before the test ledger acts. Change anything afterwards and the seal turns red.

Built for the InterSystems Programming Contest "AI Agents in Interoperability Workflows" (build 154, AI Hub EAP).
Maintainer: Rafael Orlando Mendes (Developer Community profile in the repository README). Code written with AI
assistants under Rafael's direction and review. MIT.

## What it does, in one run

1. A Pix payment exception arrives (`pbp.Service.Intake`): duplicate payment, amount mismatch, late payment,
   refund request, MED dispute, failed withdrawal. Synthetic cases only; the intake guard refuses personal data and
   malformed JSON before anything is stored.
2. `pbp.Process.Decide` (Business Process) applies deterministic rules. Simple cases close there.
3. Hard cases go to the **AI Hub agent** (`pbp.Agent`, native `%AI.Agent`; `EnsLib.AI.Agent.OutboundAdapter`),
   which reads the case through five read-only tools (order, payments, payer history, evidence, store policy),
   restricted by a native authorization policy to the case of the current run, and returns a typed decision.
4. The process enforces the policy server-side (allowed and forbidden actions, autonomous limit, unknown refund
   destination), then **seals** the decision (`pbp.seal/1`, RFC 8785 canonical JSON, salted SHA-256) through
   `ProofBeforePay.Witness`. Decisions that would move money are staged in `ProofBeforePay.Ledger`, the single
   authority for the TEST effect.
5. A reviewer sees the sealed decision in the console or the native Workflow inbox, approves in their own IRIS
   session (the ledger records the login), the approval is sealed and chained to the decision, a single-use permit
   bound to the exact commitment is issued, and the test ledger executes **once**: ten identical requests, one
   effect, nine replays of the same receipt. Lost replies are reconciled, never re-executed.
6. The review console (`/pbp/ui`) shows the chain of seals with four states (intact, tampered, sealed after the
   money moved, unverifiable), a **Try to tamper** editor that verifies an edited copy against the stored
   commitment, and a **time machine** that replays exactly what the agent saw and did not see. Every message
   in the Interoperability trace carries the commitment.

## Honest scope

- **Recorded mode is not live inference.** Without a provider key the agent operation is disabled and
  `pbp.Operation.Replay` returns recorded decisions, labelled `mode: recorded, provider: replay` in every sealed
  record and in the console. Live mode needs your own key and an explicit model (see below); nothing in this
  repository claims a live call succeeded unless the record says `mode: live`.
- **The ledger is a test ledger.** No bank, no settlement, no external network. Recipients are `test:` accounts.
- **Seals are local.** A commitment is a salted hash kept with the record inside IRIS; verification proves that a
  shown record is (or is not) the one that was sealed. No external anchoring is claimed. (A Solana Memo anchor
  exists in the reference library and is not used by the application.)
- **Synthetic inputs only.** The guard detects common CPF, CNPJ, e-mail, phone and Pix-key formats; it is not a universal detector of personal information. Pseudonymize inputs before using this laboratory.

## Run it

Prerequisites: Docker with Compose v2 and the AI Hub Community build 154 image loaded locally from the EAP portal
(see the repository README for the exact archive, load and retag steps; the image is not redistributed).

```sh
docker compose up --build --detach --wait
python3 scripts/test_iris.py
python3 scripts/test_ledger.py
python3 scripts/test_workflow.py
```

For the private console, follow the network and authentication instructions in the repository README. Then open `/pbp/ui/` with an IRIS login that has the `PBPReview:U` resource
(the installer grants role `PBPReviewer` to the users in `PBP_REVIEWERS`). The Workflow inbox in the Management
Portal shows the same tasks.

### Live mode (your key)

| Variable | Meaning |
|---|---|
| `PBP_LLM_PROVIDER` | `gemini`, `openai` or `anthropic` (AI Hub providers supported on build 154) |
| `PBP_LLM_MODEL` | required for live mode; the model id as your provider names it |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | your key, read from the environment, never stored |
| `PBP_LLM_MODE` | `recorded` forces replay even when a key exists |
| the Agent operation setting `PriceTableJSON` | optional USD per million tokens per model; when a model or usage is unknown the console says *cost unknown* |

Keys are never committed, never logged and never sent to the model as data.

## Read the code

`cls/pbp/Process/Decide.cls` is the workflow. `cls/pbp/Operation/Witness.cls` seals. `cls/ProofBeforePay/Ledger.cls`
is the effect boundary. `cls/pbp/Data/Permit.cls` re-verifies seal, policy and approval before any permit exists.
`python/pbp_s0_core/record.py` is the `pbp.seal/1` validator (24 vectors shared with the TypeScript twin).
Tests: `%UnitTest` suites under `cls/pbp/Test`, the ledger's 39 native checks, Python and TypeScript vector suites,
and `tests/iris/production_smoke.py`.

## Reuse it in your own production

Any Business Process can seal a decision with `pbp.Msg.SealRequest` to `pbp.Operation.Witness`, or call
`ProofBeforePay.Witness.Seal(recordJSON)` directly with a `pbp.seal/1` record. The record format is documented in
`python/pbp_s0_core/record.py`. (The ergonomics of this integration are still being measured; do not expect a
one-liner yet.)

A local administrator able to replace the stored record, salt and commitment can rewrite local history. No independent timestamp, external anchor or protection from a malicious IRIS administrator is claimed.

## Context validation after model output

Valid JSON is only the first check. The live and recorded operations call the same local,
I/O-free context guard after collecting tool outputs. The guard accepts only the v1 action
semantics: `refund_duplicate` must request money and human review; other executable proposals
must not move money. Full/partial refunds and withdrawal retries are outside v1 execution and
become a human escalation. The ledger remains the sole authority for any sandbox financial effect.
A duplicate-refund proposal also requires exactly two observed payment entries with distinct,
nonempty payment references. Repeated observations of one reference cannot establish a second
payment. The ledger separately checks the explicit refund target, amount, payer and currency.

Every cited reference must identify a non-null output actually returned by the scoped tools.
A tool's absence/error wrapper does not count as evidence. Null evidence observed by tools is
merged into `missing`, even if the model returned an empty object; any declared or observed
missing evidence requires review on the model path. Trusted deterministic rules keep their own
business criteria and continue to seal their observed missing fields.

A rejected proposal produces a sealed escalation with a stable reason, actual tool outputs and
the declared missing fields. It does not create a permit or effect. This guard does not establish
that a model's natural-language explanation is correct; the recorded Haiku unit error remains an
explicit limitation. Development tests are not an independent held-out model benchmark.

New permit/effect events explicitly label raw amounts as **minor units**. Older diagnostic events
are preserved; the main decision, permit and receipt cards format BRL amounts as reais.

## Review and proposal provenance

The console distinguishes refund approval, acknowledgement of a ledger refusal and acknowledgement
of a nonfinancial escalation. Only a permitted duplicate-refund plan can produce a sandbox effect.
A structurally valid model proposal is retained before context enforcement in `ProposalJSON` for
inspection and evaluation. The API labels this projection `unsealed_diagnostic` and not authoritative;
changing it cannot authorize an effect or change the sealed decision. Invalid/PII-bearing output is
not persisted as a proposal. The original sealed inputs and frozen S0 schema remain unchanged.

V1 deliberately requires review for any missing evidence on the model path. This conservative rule
does not apply to trusted deterministic rules' business criteria. Complete model observations can
still pass the nonfinancial positive control. This tradeoff is fixed before the private benchmark.

`model.temperature=-1` means the transport sampling temperature was not established. It is a metadata
sentinel, not a requested negative temperature. When a gateway omits the native client's requested zero,
set `PBP_LLM_TEMPERATURE_SENT=0`; old seals remain unchanged and retain their documented limitation.

### Dashboard usage provenance

`GET /pbp/api/stats` additionally exposes `model_decisions_by_mode` buckets (`live`, `recorded`,
`unknown`). Each contains decision counts, stored token metadata, known cost subtotal, unknown-cost
decision count and total cost (`-1` if any cost is unknown). Recorded values are fixture/replay metadata,
not paid inference. A live bucket counts decisions/attempts, not successful generations.
`billing_verified` remains false and `usage_cost_basis` is `stored_decision_metadata_not_billing`.
Legacy source totals remain for compatibility; a dashboard must not label those mixed values as a bill.


## Financial review read model

`GET /cases/:id` includes a read-only `review` view derived from the verified decision
seal's `saw.inputs`, bound by `review.source_commitment`. It does not use the mutable
case input projection. The view includes order/payment amounts, payment references,
destination and `delta_minor` (sum of sealed payments minus sealed order amount).
That delta is an observation comparison, never an authorized refund amount.
`decision_amount_minor` is the sealed decision's amount; approval is still a separate step.
Unknown or conflicting amounts/currencies keep the delta null. Integer arithmetic
preserves minor units without floating-point rounding. `verified` describes the local
seal check, not factual correctness, external settlement or protection from an administrator.

`review.stage_remaining_seconds` is calculated on the server using the ledger's clock,
with `stage_ttl_seconds=600`. Null means unavailable/not staged; zero means a known
window has expired. `permit.remaining_seconds` is separate from that stage window
and from `permit.expires_at`. Clients must also respect consumed/rejected/closed status.
The browser never interprets the ledger's internal Horolog epoch as Unix time.

`decision.denied_tool_calls` is a sanitized, bounded application-log excerpt before the
decision's creation time. It includes tool name, reason code and timestamp, with an
explicit availability flag. It is unsealed and non-authoritative, does not claim complete
coverage, and is never mixed with the tool outputs the agent actually observed. No raw
diagnostic message or extra permission grant is exposed by this view.


## Refund payment binding on the agent path

A model refund proposal never chooses its target through prose. The server validates exactly
two distinct payment references, matching order/payment minor units, payer, recipient when known
and BRL currency. It preserves an explicitly observed input target. When no target was supplied,
it derives the strictly later payment using timezone-aware timestamps; missing, invalid or tied
times remain unknown and produce a sealed human escalation. A missing recipient stays missing.
The ledger independently validates the resulting sealed binding and requires authenticated approval.

The sealed input snapshot is normalized context, including server policy/refund bindings. It is
not a verbatim copy of the intake or of an LLM prompt. Sealed tool outputs remain the actual outputs
returned during the decision. The console labels these sources separately and uses only verified
sealed financial facts, exact integer minor units, and server-derived stage/permit expiry windows.
Consumed permits and completed reviews are displayed as completed, rather than as active windows.

Native recorded regression evidence: [derived target and authenticated UI review](validation/derived-target-ui.json).
That test supplied no refund target, verified the derived binding in the seal, observed zero effects
before browser approval, and then verified one effect and an intact receipt. It is a development
regression, not an independent live-model benchmark.
