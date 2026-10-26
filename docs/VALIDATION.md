# Validation on 26 October 2026

The native workflow has been exercised in a dedicated, synthetic x86-64 Linux build154 laboratory.
The public CI and private licensed-runtime gates are deliberately separate.

| Gate | Observed result | Scope |
|---|---|---|
| TypeScript reference | 20 vectors and typecheck passed in foundation validation | S0 source unchanged |
| Python reference | 24 vectors passed in foundation validation | S0 source unchanged |
| Offline boundary suites | 31 methods passed; forbidden network/process attempts 0 | Witness adapter, ledger plan, intake guards |
| Native Witness bridge | 12 checks passed | Actual ObjectScript → embedded Python, no model |
| Native ledger | 39 checks plus 12 independent IRIS execution sessions | One effect, identical receipts, authenticated review, TTL, tampering, loss/retry |
| Native unit suites | 20 methods; framework reports All PASSED | Rules, output contract, scope isolation, permits, receipt projection tampering |
| Native Production replay | 46 checks on ten fresh synthetic cases | Service → Process → recorded agent/tools → Workflow review → seal approval → permit → one effect → readback |
| Actual HTTP workflow | 34 checks | Authenticated reviewer session, version binding, CSRF header, copied-record tamper, timeline/tool retrieval, refusal paths |
| Actual browser | Approve closes synthetic case; modified amount returns tampered | IRIS-backed API, not a mock API |

These counts are different kinds of evidence, not interchangeable test totals. Native unit tests are gated
on the framework's actual result: RunTest returning status1 alone does **not** mean assertions passed.
Missing JSON markers and missing expected methods fail the runtime runners.

JSON evidence and a SHA-256 manifest of runtime source are in [validation/](validation/).
The server's full logs remain private; they are not required to distribute vendor code or credentials.

## Boundaries and remaining gates

- Replay is labelled recorded, and has zero LLM calls. It does not establish AI Hub live inference.
- The three provider constructors and native agent initialization were probed with dummy credentials
  without network calls. Real account access, live tool execution, model quality and measured billing
  remain unverified until private credentials and a bounded comparison run are available.
- Root ledger data is journaled in a named IRIS durable volume. Restart and recreation retained original
  confirmed receipts in lifecycle testing. A fresh volume compiled all classes, installed and started the Production, then passed all native suites. Restart, container recreation and SIGKILL recovery retained the verified original receipt and one effect. This tests process termination, not a host power loss. The replay test also refused a live-key environment before setup or case feed.
- Every refund in this application requires authenticated review. Test review sessions are synthetic
  automation; they do not represent Rafael approving a real payment or contest submission.
- No bank/chain transaction, settlement, independent timestamp or external anchoring is claimed.
  An administrator who can replace all local evidence can rewrite local history.
- No Open Exchange submission or public demo has been published by these tests. Rafael's final OK is required.
