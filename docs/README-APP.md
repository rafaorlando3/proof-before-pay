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
