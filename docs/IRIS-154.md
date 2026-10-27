# Build 154 startup diagnosis

The old exit 139 was reproduced on the exact x64 EAP image with a read-only root,
UID/GID 51773, no network, a 128 MiB memory limit and all capabilities dropped.
Only `iris-main --help` was invoked. A 2×2 experiment separated directory identity
from write permission:

| Working directory | Writable tmpfs at that directory | Exit |
|---|---|---:|
| `/home/irisowner` | no | 139 |
| `/tmp` | no | 139 |
| `/home/irisowner` | yes | 0 |
| `/tmp` | yes | 0 |

Both failing cases reported `Unable to find/open file iris-main.log in current directory`
followed by their actual directory. Both passing cases printed the full help text.
Neither failure was OOM. Existing running container IDs were preserved.

The cause reproduced here is failure to open the entrypoint log in an unwritable
working directory, followed by an entrypoint failure with exit 139. Changing only
the directory name does not fix it. The prior claim that `/tmp` alone fixed it was
therefore incomplete. Source-level analysis of the vendor binary was not performed.

The server also needs writable databases and instance files. This lab follows the
vendor image's normal writable filesystem and `/home/irisowner` working directory;
adding a 4 MiB writable directory alone is not a complete server configuration.

An initial custom CPF failed for a separate reason: `SystemMode` exceeds its length
limit above 32 characters. It is now `Proof Before Pay EAP`. The final configuration
successfully starts a fresh container, compiles Witness and passes bridge tests.
The application now persists instance/security/case/receipt data in a named durable volume; recreation reloads source and retains that volume. Removing the volume deliberately erases laboratory data.

On 27 October, recreating a container with its existing durable volume but a new
Docker-generated hostname produced `System appears to have failed over from node`
in the IRIS alert log. The vendor health check subsequently failed even though the
Production/API were available. A restart on the same node restored vendor health;
the original receipt remained intact with one effect. No alert was cleared and no
health check was overridden.

A subsequent [native recreation check](validation/stable-container-identity.json)
preserved the observed hostname and the original named volume. After 46 seconds,
vendor health passed, the apparent-failover alert was absent and the same original
receipt still verified with one effect. Complete before/after unrelated-container
ID sets were saved privately and matched for this check. This narrower result does
not repair the missing audit snapshot of the earlier clean-install job.

Compose now sets a stable hostname, `pbp-iris`. When migrating an existing durable
instance, preserve its current hostname instead of adopting the default:

```sh
docker inspect --format '{{.Config.Hostname}}' <existing-container>
PBP_IRIS_HOSTNAME=<observed-hostname> docker compose up -d
```

Keep that override in subsequent invocations. Do not mount the same durable volume
in two running instances. Check vendor health after the monitor has had time to
run, inspect actual alerts, and verify an existing receipt after migration. HTTP200
alone does not establish runtime health. This hostname finding does not establish
the cause of every historical health alert or resolve the separate EAP Sharding
message below.

An EAP startup log also contains `<METHOD DOES NOT EXIST>Sharding+2^STU *Sharding,SYS.ICM`.
IRIS health, compilation and tested bridge calls still pass. This message is retained
as a vendor EAP observation; its wider impact has not been established.

The second defect was in the ObjectScript bridge. Python names containing `_` must
be quoted in ObjectScript calls: `adapter."seal_json"(...)` and
`adapter."verify_local_json"(...)`. Without quoting, the class compiles but catches
a runtime parsing/lookup error and returns `bridge_unavailable`. Runtime tests
caught this defect; offline Python tests could not.

Sources: [vendor container documentation](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ADOCK)
and the actual build154 runtime experiments on 26 October 2026. Generic vendor
documentation is not an EAP certification. No image or derived image is published.
