# Optional live demo, staged admission layer

`live_queue.py` is an admission component, disabled by default. It is not connected
to `server.py`, has no provider key, performs no HTTP calls and cannot approve a
refund. The published viewer still shows recorded decisions from the real IRIS
backend. This component does not establish a live-demo bonus.

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

1. A private worker must construct fresh synthetic inputs from reviewed public
   fixtures, submit once to native Interoperability and read the resulting seal.
   It must never call the reviewer/approval endpoint. The sealed case and trace,
   rather than a successful admission response, establish completion.
2. A separate provider bridge must enforce the existing cumulative US$1 ledger
   before **every** HTTP request, preserving all prior costs and uncertain holds.
   The planned free-tier bridge permits at most three HTTP requests per decision,
   admits only the configured Gemini model/local tools, records usage estimates
   as estimates and preserves uncertain reservations. Five admissions alone do
   not enforce provider RPM/RPD or spending. Quotas must be checked at deployment.
3. Configure the native agent through a private, reviewed runtime recipe without
   keys in source, command arguments, UI, logs or public Docker metadata. Check
   host capacity before any deployment; do not remove historical volumes or
   change services belonging to another project.
4. Extend the authenticated viewer with same-origin admission/status endpoints,
   visible LIVE/recorded-fallback labels and scoped access to the newly sealed
   case. The account remains unable to approve, intake arbitrary data or access
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
