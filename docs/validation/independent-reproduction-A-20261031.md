# PBP49: independent reproduction (A), final report

Source 725d549 (ZIP 02b481dd), runtime pinned. 31 Oct 2026. Facts cross-checked by Codex (c8356fff).

## What was reproduced

- README path on a cold empty volume: image load, build and start, the five native test scripts, console profile, authenticated HTTP workflow (34 checks), new unreviewed case, the ten public fixtures, and persistence across stop/start (42 cases, 37 decisions, 63 seals, 10 permits, 9 receipts equal before and after; also equal after returning to A in 96).
- IPM path on a new plain-vendor volume: IPM 0.10.10 in USER, literal load, 38 declared resources, Production not started, recorded E2E smoke with 48 checks, then package, non-purge uninstall and archive reinstall with the original receipt intact.
- Judge Path A against the remote dedicated viewer: Authored and executed by Codex (97: 55 assertions; 49: 7 additional refusal checks), reviewed by Claude. Claude-authored script 37 was offered and declined by Codex (no new technical doubt); it was not run. Scripted HTTP, not a browser DOM or a human walkthrough.

## Qualifications (read before quoting any result)

- Reproduction by agents, not by an independent human operator: README/IPM steps authored by Claude and executed unchanged by a Codex runner; supplements 90-97 and 49 (including the IPM USER bootstrap and Path A) authored and executed by Codex and reviewed by Claude.
- Host: isolated Docker-in-Docker on the owner's Apple Silicon Mac; the x64 image ran under emulation. README tested platform is x86-64 Linux; native ARM64 not validated.
- Image: private docker-save re-export of the licensed build 154 (same content chain 8fc1e5c6/1d3d52bf), not a new portal download.
- Deviations, each labelled: 2g memory override, reviewer login and roles created by workaround steps, IPM bootstrap in USER written by Codex after a Claude-authored attempt failed by loading in %SYS.
- Failed attempts are kept as failures (09, 13, 19, 24, 26, 34, 90, 93); later passes are new numbered attempts.

## Findings

- **F1** README prerequisites did not name python3 on the host (fixed in README, d77ffeb).
- **F2** README asks for an existing PBP* reviewer login and did not say how to create one on a new volume.
- **F2b** Final sufficient set in this installation: PBPReviewer + %DB_USER + a role with only %Service_EmbeddedPython:USE, without %Developer or %All (%Developer was added temporarily in 25 and removed in 29; %Development:USE alone failed in 24). Documented in docs/REVIEWER-SETUP.md (49dfdaa). Not proved minimal.
- **F2c** A reviewer created after installation must be enrolled in the native Workflow role pbp.Workflow (assign_task_failed otherwise).
- **F2d** PBP_REVIEWERS is not forwarded by the Compose files; exporting it on the host does nothing (documented, Compose unchanged).
- **F3** The README called the OCI manifest digest 8fc1e5c6 the image ID; the classic store reports the config 1d3d52bf (fixed, d77ffeb).
- **F4** passo-09 timed out on the script's fixed 45 s wait. Afterwards passo-12 showed OOMKilled=true while healthy and 3 kernel OOM kills; with 2g, passo-14 passed in 9.178 s. Strong temporal association with the OOM; not a causal proof tied to one specific job.
- **F5** Original cap 1258291200 B; cgroup peak 1258295296 B (at the cap) under amd64 emulation on Apple Silicon. With 2g (2147483648 B) the later peak was 1956376576 B (about 1.82 GiB). The native x86 main lab showed a 432 MB snapshot peak with zero OOM, but that is not a paired workload or platform comparison. Compose default raised to 2g (45714af), README qualified.
- **F6** Product robustness: the healthcheck reported healthy while kernel OOM kills had occurred. Candidate wrapper reads oom_kill only when the counter belongs to the container (cgroup v2 with private namespace, or the resolved v1 self path) and reports unavailable otherwise; v1 checked only with fixtures, native checks (94/95) on v2. It is not a worker-liveness probe.
- **F7** Two separate events: (a) passo-13, after recreation under emulation, the vendor SystemMonitor was in alert and up --wait failed; it later dropped to warn/healthy without reset (consistent with the documented cooldown). (b) passo-93, the candidate failed up --wait because the 60 s start_period expired while PBP init was still running; not attributed to SystemMonitor. start_period raised to 180 s (252638b); passo-95 passed on a new volume.
- **F8** IPM-OPERATOR step 6 had no concrete command; now documents the production_smoke command and its limits (92de10b, attribution corrected in b0890b6).

## Step log

| Step | Author | What | Result |
|---|---|---|---|
| 01 | Claude | inventory, read-only | PASS |
| 02 | Claude | host prerequisite python3 | PASS |
| 03 | Claude | README docker load + tag + image check | PASS |
| 04 | Claude | README compose up --build --wait, cold empty volume (110.7 s) | PASS |
| 05 | Claude | README test_iris.py | PASS |
| 06 | Claude | README test_ledger.py | PASS |
| 07 | Claude | README test_workflow.py (35 unit, 48 E2E, 3 adversarial) | PASS |
| 08 | Claude | README test_pairguard.py | PASS |
| 09 | Claude | README test_recipient.py, first attempt (1200m limit) | FAIL |
| 10/11 | Claude | retired before running (replaced by 15/16) | NOT RUN |
| 12 | Claude | diagnostic read-only (OOMKilled=true, oom_kill 3, healthy) | DIAGNOSTIC exit 0 (not an application test) |
| 13 | Claude | resource deviation: override 2g, recreate | FAIL |
| 17 | Claude | pre-check healthy before retry | PASS |
| 14 | Claude | README test_recipient.py, second attempt (2g) | PASS |
| 15 | Claude | README console profile + 2g override | PASS |
| 16 | Claude | list IRIS users (no PBP* login) | PASS |
| 18 | Claude | workaround: create PBP reviewer (password generated in sandbox, never printed) | PASS |
| 19 | Claude | README http_workflow.py | FAIL |
| 22 | Claude | diagnostic (Security.Login denied; inconclusive) | INCONCLUSIVE |
| 23 | Claude | role with %Development:USE only | PASS |
| 24 | Claude | README http_workflow.py, new attempt | FAIL |
| 25 | Claude | add %Developer temporarily (main-lab parity); removed in 29 | PASS |
| 26 | Claude | README http_workflow.py, new attempt (passed guard; assign_task_failed) | FAIL |
| 28 | Claude | read-only roles/resource/Workflow membership | PASS |
| 29 | Claude | narrow role %Service_EmbeddedPython:USE only, remove %Developer | PASS |
| 30 | Claude | enrol reviewer in pbp.Workflow | PASS |
| 31 | Claude | README http_workflow.py, new attempt (34 authenticated checks) | PASS |
| 20 | Claude | README http_workflow.py --seed | PASS |
| 21 | Claude | README FeedCases (10) | PASS |
| 27 | Claude | README persistence stop/up (42/37/63/10/9 equal) | PASS |
| 32 | Claude | stop A, nothing deleted | PASS |
| 33 | Claude | IPM lab: plain vendor image, new volume, readiness | PASS |
| 34 | Claude | IPM bootstrap loaded in %SYS: deviation in the Claude-authored script, executed unchanged by the Codex runner | FAIL |
| 90 | Codex | supplement: new USER volume (readiness harness stopped early) | FAIL |
| 91 | Codex | supplement: IPM bootstrap in USER, untraced | PASS |
| 35 | Claude | IPM-OPERATOR literal load in USER + checks (38 resources, Production stopped) | PASS |
| 36 | Claude | IPM step 6: production_smoke with IPM assets (48 checks) | PASS |
| 92 | Codex | supplement: package -only, non-purge uninstall, archive reinstall (receipt identical) | PASS |
| 93 | Codex | candidate image: up --wait failed on the 60 s start_period while PBP init was still running under emulation; no OOM | FAIL |
| 94 | Codex | read-only: new health wrapper exit 0, peak 1.96 GB < 2g | PASS |
| 95 | Codex | candidate on new volume with 180 s start_period | PASS |
| 96 | Codex | restore A: same container/volume, counts equal, receipts intact | PASS |
| 97 | Codex | Path A scripted against the remote judge viewer (55 assertions) | PASS |
| 49 | Codex | Path A delta: 7 refusal checks not in 97 | PASS |
| 37 | Claude | Path A, Claude-authored script | NOT RUN (declined by Codex; Path A covered by 97 + 49) |

Evidence packages and SHAs: channel C-1218 onward and vigia/registro/pbp49-flow-20261026/.
