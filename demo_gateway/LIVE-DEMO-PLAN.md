# Optional bounded LIVE demo

The dedicated route produced its first valid cited LIVE proposal on the VPS on
5 November 2026. [Session1566 evidence](../docs/validation/live-gemini35lite-1566-20261105.json)
records three normal HTTP200 protocol turns, five observed tools, an integrity-checked
local policy passage cited inside the decision seal, native message headers and
zero financial effect. This one case proves neither general model quality nor a
bonus award. Fresh admission is OFF during final package and publication review;
the authenticated viewer retains recorded examples without making a model call.

## Existing admission and accounting controls

- Only the two fixed public synthetic fixtures are admitted. Case/order/payment
  identifiers change; public fixture contents and timestamps stay pinned by hash.
  No arbitrary prompts or customer data can be submitted through the viewer.
- One queued/running decision; at least ten seconds between actual worker starts;
  five queue admissions and fifteen provider HTTP requests per Pacific calendar
  day. Failed jobs consume admission. Each case allows at most three normal
  tool/decision protocol requests. JSON repair and automatic provider retry are
  disabled for the dedicated demo. The original private agent retains its own
  independently documented behavior.
- The fixed reviewed model is `gemini-3.5-flash-lite`, medium reasoning, default and
  upper output bound4096; a smaller explicit caller bound is preserved. Four exact
  response IDs are allowlisted. The provider project, key and compatible transport
  were retained. Model metadata GET is not inference or a capacity guarantee.
- Rafael expressly approved the cumulative US$5 ceiling on4November. The existing
  ledger/lock, earlier costs, six uncertain holds, quotas and history remain intact.
  Nothing was reset or released to fund the new case. Each HTTP request reserves
  before sending; the maximum reservation remains US$0.384064, based on the
  existing conservative65536 theoretical-output allowance, not merely4096.
- Valid matching-model usage must be archived before a provisional estimate is
  settled. Output accounting conservatively includes `total_tokens-prompt_tokens`
  where this exceeds visible completion tokens. Native SDK visible-token estimates
  and gateway bounds are reported separately. Neither is a billing receipt.
- A503/429, uncertain response, length/empty output or invalid proposal stops the
  attempt; the phase is disabled on transport/shape failure. An uncertain reserve
  remains held. Pacing before a first send is not a retry. The55second bridge
  deadline includes pacing; the viewer waits at most240seconds. The consulted
  native SDK configuration exposed no timeout setting.
- Process locks, atomic replacement and fsync protect private state. An interrupted
  worker remains uncertain and is reconciled against its original case; it is not
  resubmitted under a new token. These controls do not protect against a privileged
  operator rewriting state or calls made elsewhere with the same provider project.

## Native route and operator sequence

`pbp.Demo.Intake` → `pbp.Demo.Process` → `pbp.Demo.Operation` uses the native AI Hub
adapter and a private budget bridge. Its local placeholder is not a provider key.
Only an explicitly enabled `public-live:` profile can use this route. A normal
installation starts no Production and enables neither LIVE nor RAG. Autonomous
financial effects remain disabled; the viewer cannot approve a payment or grant
itself permission. Status, errors and confirmations stay inline.

A changed model/source requires exact peer review, passing CI, fresh private
backups, an OFF native profile and idle ledger/queue, compilation of Runtime and
both dependent Demo classes, explicit locked native/ledger migrations and external
file/method checks. Preserve all existing holds and protected history; append only
the reviewed migration records. Pin both bridge and viewer sources, start only the
own Production/services, verify read-only health and recorded fallback, then admit
only the explicitly reviewed new qualification. Do not rerun Stage, clear alerts,
reset counters, replay uncertain cases or restart the whole instance as a shortcut.

Runtime config metadata pins a revision but does not attest the loaded source by
itself. `GET /pbp/api/health` exposes the non-secret `public_live_demo` object.
A recreated container must build the current sources; COW persistence qualifies
only the existing container. Preserve vendor images privately and other projects'
services and volumes.

The explicit entry is `python3 -I -B demo_gateway/live_entry.py --viewer-config
/absolute/private/viewer.json --live-config /absolute/private/live.json`. The
private LIVE configuration contains exactly `enabled`, `budget_directory`,
`queue_directory`, `native_attempt_directory`, `fixtures_directory`,
`native_source_revision` and `native_relay`. A configuration flag alone cannot
establish native readiness or paid-call permission. Existing one-hour viewer
sessions expire independently; accounting is never reset to refresh access.

## Evidence and limits

Session1566 ended with `escalate_to_human`, a valid proposal and an intact local
seal, without permit/receipt/effect. Its five persisted tool outputs match the
sealed record, and the cited chunk matches one of three returned policy passages.
The archived HTTP response usage sums to6391prompt/511visible completion tokens;
conservative output accounting uses2000tokens including nonvisible output. New
provisional estimate: US$0.00691730. Six earlier uncertain holds remain preserved.
The native SDK stored US$0.003194 from visible-token metadata; that separate
estimate excludes the additional output bound and is not billing.

Offline tests use isolated synthetic state and injected/fake providers. They are
not fresh native generations. Earlier503/truncation failures remain historical
failures, and the old video/recorded Visual Trace are not relabelled as this run.
Public admission must remain bounded, explicitly enabled and reconciled with the
current release; this document does not silently enable it.
