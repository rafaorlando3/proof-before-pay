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
The lab is disposable; restart retains its writable layer, recreation reloads source.

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
