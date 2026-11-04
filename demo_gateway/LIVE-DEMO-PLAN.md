# Optional live demo, staged admission layer

The optional queue, budget, native worker and viewer integration is staged,
disabled by default and not yet deployed as an end-to-end LIVE demo. The published
viewer still shows recorded decisions from the real IRIS backend. Passing the
local tests and compiling the native hooks does not establish a live-demo bonus.

The admission layer allows one queued/running decision, at least ten seconds
between actual worker starts, and at most five admitted decisions per Pacific
calendar day. Failed jobs consume admission. Request identifiers are idempotent
and select only operator-configured scenario names, never user prompts. The
worker result must identify that request's `public-live:<request_id>` case and a
decision commitment plus native session id. Arbitrary response fields are not
stored or exposed by the queue projection.
Request identifiers contain 16 to 48 ASCII letters, digits, underscores or
hyphens, keeping the prefixed case within the native 64-character CaseId limit.
Product errors, status and confirmations must remain in the page; do not add
native JavaScript alert/confirm/prompt calls or an HTTP authentication challenge.

State lives in a private operator directory outside Git. A process-shared lock,
atomic replacement and file/directory fsync protect admission across concurrent
requests and restarts. Invalid or unreadable state fails closed without resetting
counts. A worker interrupted while running remains in flight and is not replayed
automatically; an operator must reconcile its native case and cost reservations.
These controls do not protect against a privileged operator rewriting state.

## Remaining integration gates

1. `live_native.py` pins public fixtures0005/0006 by content hash, changes only
   case/order/payment identifiers and retains their original synthetic data and
   timestamps. An exclusive durable intent precedes its single native intake.
   The worker never calls a reviewer/approval endpoint. It requires a matching
   LIVE model decision, intact decision seal, actual native session, and no
   money flag, permit or receipt. The service also requires a settled observed
   provider request; a fabricated or recorded result cannot establish completion.
2. `live_budget.py` and `live_provider.py` now implement the separate per-HTTP
   admission and private transport. The integration is deployed but **paused after the first real provider timeout**, with its reservation retained. The subsequent US$2 cap authorization does not itself enable admission. They
   require an explicitly approved public phase in the existing `budget.json`,
   use its existing `budget.lock`, use the explicitly approved US$2 cumulative cap
   (Rafael, 3 November 2026; recorded approval reference required), and preserve
   prior costs, holds and historical phases. There is no new/reset budget.
   Admission reserves before sending, allows three HTTP requests per case and
   fifteen per Pacific day, and enforces fifteen seconds between starts. The
   only upstream is Google's compatible Gemini endpoint; redirects, alternate
   models, remote tools and unbounded input/output are refused. A successful
   response needs an archived matching-model usage report before provisional
   estimate settlement. Uncertain responses retain the reservation and disable
   the public phase; there is no provider retry. A pre-admission pacing wait is
   separate from a retry. Five queue admissions alone are not a cost control.
   The free-tier project and its quota were checked on 3 November; preserve that binding when resuming.
   These are limits on this bridge, not a guarantee about calls made elsewhere
   using the same provider project. The real key is read from an operator-only
   credential file; it is absent from native IRIS, requests, logs and public code.
3. `pbp.Demo.*` defines a separate native intake/process/operation and a provider
   with a non-secret local placeholder. Only enabled `public-live:` cases use
   this route; the original process selection remains unchanged. Staging and
   enabling require the existing operator permission; neither happens during
   installation. The operator's existing build154 instance compiled the seven
   changed/new classes; the profile remained absent/OFF and the retained recorded
   case's receipt remained intact. This was not a fresh install or a LIVE run.
   The profile contains no provider key and exposes only non-secret readiness
   metadata. Check capacity before deployment; preserve all historical volumes
   and services belonging to another project.
4. `live_service.py`, `live_entry.py` and the optional `live_panel.html` connect
   authenticated, same-origin fixed-scenario admission/status to the worker.
   Run buttons and confirmations are in-page; fallback explicitly says recorded.
   A completed case is admitted to the viewer only with its matching live mode
   and commitment; the account cannot approve, intake arbitrary data or access
   unrelated cases. Existing one-hour viewer sessions expire independently;
   retained evidence and cost accounting are never reset to refresh a demo.
5. Test admission through the actual browser, worker, provider bridge and native
   production, including exhausted quota and unavailable upstream. Publish a
   concrete deployed version and evidence before describing the demo as LIVE.

## Local verification

`python3 -m unittest discover -s demo_gateway -p test_live_queue.py -v`

Thirteen tests cover the native case identifier boundary, concurrent threads and processes, one worker claim, restart
and idempotency, the Pacific day boundary, delayed worker starts, failed jobs,
in-flight crash preservation, state corruption, symlinks, unsafe configuration,
wrong-case replies and exclusion of arbitrary runner fields. An optimized-Python
run also checks that validation does not depend on removable `assert` statements.
No provider request or native workflow is performed by these tests.

The per-HTTP budget/transport tests use a temporary synthetic ledger and an
injected provider, including an actual local HTTP server. They cover shared
process admission, archived estimates, preservation of unrelated history and
old uncertain holds, crash/restart, quota/day boundaries, denied redirects,
secret echoes, wrong-model/missing-usage responses, scoped peers/routes and
disabled or corrupt state. They never open the operator's real ledger or call
Google. Passing these tests does not establish the native end-to-end LIVE path.

The explicit entry is `python3 -I -B demo_gateway/live_entry.py --viewer-config
/absolute/private/viewer.json --live-config /absolute/private/live.json`. The
operator-only live configuration must contain exactly `enabled` (Boolean),
`budget_directory`, `queue_directory`, `native_attempt_directory`,
`fixtures_directory`, `native_source_revision` (verified40-character SHA) and
`native_relay` (the existing loopback HTTP relay). Enabling requires the existing
budget phase and real native readiness, not merely a configuration flag.

`GET /pbp/api/health.public_live_demo` is metadata, not an HTTP path: the health
JSON's `public_live_demo` object must identify the pinned native source revision,
Gemini model, `public-live:` prefix, `private_budget_bridge` transport and disabled
autonomous effects. No provider key or private bridge URL is returned there.
