# Adversarial review: review console and live configuration (Claude, 26/10/2026)

Scope: `ui/index.html`, `pbp.API`, `pbp.Review`, `pbp.Setup.EnsureWebApp`, live-mode configuration. Findings in
order of severity, each with the fix applied in this delta or the change proposed to the owner of the class.

1. TOCTOU on approval (high, FIXED in UI + Codex in Review.Act). The click could approve a head the reviewer never
   saw. Fix: the UI stores the commitment it displayed and sends it in the POST body; `Review.Act` requires it as the
   4th argument and refuses when it differs from the case head. Smoke reads the head explicitly.
2. CSRF through cached HTTP Basic credentials (high, PROPOSED for pbp.API). `/pbp/api` uses password authentication;
   browsers resend Basic credentials automatically. With `HandleCorsRequest = 1` a hostile page can preflight and POST
   `/review/:id` with the user's credentials. Fix: set `Parameter HandleCorsRequest = 0` (the console is same-origin)
   and, in `ReviewAct`, refuse when the `Origin` header is present and differs from the request host. The
   commitment requirement (1) reduces blind CSRF but does not remove it.
3. Session identity (high, OK). `Review.Act` uses `$USERNAME` of the authenticated session and `PBPReview:U`;
   the business process never approves. Keep `_SYSTEM`/`irisowner` out of `PBP_REVIEWERS` in the public demo and
   create a named reviewer; the smoke runs as the lab user by design.
4. XSS (medium, OK). Every API value rendered in the console passes through `esc()`; the tamper editor only sends
   JSON to the verify endpoint, which never persists. Keep it that way: no `innerHTML` with raw API strings.
5. Information disclosure (medium, PARTIAL). `GET /seals/:c` returns the sealed record (not the salt) to any
   authenticated user. Records are synthetic here; for real data this endpoint must require `PBPReview:U` or a
   per-case grant. The `Envelope` (with salt) is never exposed by the API. Logs never carry exception data.
6. Live mode truthfulness (medium, FIXED in UI + proposed in API). The header no longer says "live" because a key
   exists; it says "live configured, no live call verified yet" until `/health` reports `last_live_call_ok` (proposed
   field: the agent operation records the timestamp and status of its last successful live decision). Cost is shown
   as "unknown" when the model is not in the price table; `cost_micro_usd` should be `-1` (not 0) in that case.
   `PBP_LLM_MODEL` must be explicit for live mode; no default model id is assumed.
7. Denial of service on verify (low). `POST /seals/:c/verify` accepts up to the Witness bound (32 KB) and rate is not
   limited; acceptable for the demo, note for the public demo (reverse proxy rate limit).
8. Static console caching (low). `/pbp/ui` is served by IRIS with password auth; set `Cache-Control: no-store` for
   `index.html` if the demo host is shared.

Not reviewed here: the ledger's own adversarial suite (Codex, 39 checks), and the Workflow inbox path.
