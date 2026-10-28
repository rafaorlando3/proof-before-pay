# Authenticated demo gateway

This optional gateway presents a small, explicitly selected set of synthetic cases
from a running private IRIS instance. It is separate from the native application
image and its IPM module. It is not a static simulation or a live-model API.

It binds only to `127.0.0.1:18879`. Put a HTTPS reverse proxy in front of it before
remote access. The login page is public. Case data and all API routes require dedicated random demo credentials. Browser login sets an opaque, one-hour Secure/HttpOnly/SameSite=Strict cookie; sessions remain in memory. HTTP Basic remains available to API clients. Login is same-origin, bounded and rate limited.
The JSON config file must have mode0600 and stays outside Git:

```
{
  "username": "viewer",
  "password": "GENERATE_A_NEW_RANDOM_SECRET_AT_LEAST_32_CHARACTERS",
  "case_ids": ["YOUR_EXPLICIT_PUBLIC_SYNTHETIC_CASE_ID"],
  "origin": "https://YOUR_DEMO_HOST",
  "backend": "http://127.0.0.1:18878"
}
```

Generate the password with a cryptographic random generator; do not use the example
as a password. The upstream must be a private, authenticated loopback relay to IRIS.
Do not expose the vendor image, provider keys or reviewer credentials through public routes.
This service does not provision that private relay or distribute the EAP image.

```
python3 demo_gateway/server.py /absolute/private/demo-config.json
python3 -m unittest discover -s demo_gateway -p 'test_*.py'
```

The viewer can inspect the selected cases, their seals, receipts and actual tool
outputs. Counters cover only that subset. Case identity, sandbox environment and
recorded model mode are checked against IRIS responses. Other cases and commitments
are refused. Intake and review routes are blocked, regardless of frontend controls.
After login, the only allowed application POST is verification of an edited copy of an allowlisted seal;
it requires the configured HTTPS origin, the same-origin header and bounded JSON.
The native verifier does not change the stored record or issue an effect.

The page identifies this limited viewer mode and does not claim reviewer privileges.
The public TLS proxy, private config and service lifecycle are operator responsibilities.
Bounded request concurrency and service resource limits should protect the lab.
Do not call a staged loopback service a published demo or an awarded contest bonus.

## Scoped route recovery

`restore_route.py /absolute/path/to/route.json` supports a shared Caddy server whose
private admin API listens at localhost:2019 and whose HTTPS server is named `srv0`.
An operator supplies exactly one `pbp49-*` route id, one explicit host and the
loopback viewer upstream `127.0.0.1:18879`. The worker refuses a conflicting id or
host and broader handlers. It reads first, appends only when absent using the
returned ETag, and verifies that all previous routes remain equal. An uncertain
POST is recovered with GET; it is never blindly resent. It does not replace full
configuration or edit the shared proxy's tracked Caddyfile.

Example route (replace the host):

```json
{"@id":"pbp49-demo","match":[{"host":["demo.example.com"]}],"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"127.0.0.1:18879"}]}],"terminal":true}
```

An operator may supervise the viewer/private relay and start the owned IRIS
container with separate systemd units, then run the recovery worker from a bounded
oneshot timer. In the current lab the timer checks every30seconds; it makes no
mutation while the exact route exists. Stop/disable that own timer before retiring
or intentionally removing the demo route. Credentials remain in private0600
config and opaque browser sessions stay in memory.

The lab verified owned service starts and an actual remove/recover of only its
route, with the receipt intact and no IRIS restart. It did not reboot the shared
host or replace shared proxy/boot configuration. These are operational evidence
limits, not a claim of tested whole-host disaster recovery.
