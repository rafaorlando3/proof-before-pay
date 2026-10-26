# Proof Before Pay

Seal what an AI agent saw, what was missing and what it decided **before** an action.
The current foundation runs on InterSystems IRIS AI Hub EAP build 154, with a native
ObjectScript `ProofBeforePay.Witness` bridge to a bounded Python sealing adapter.
The TypeScript reference checks the same `pbp.seal/1` canonicalization vectors.

**Status:** the isolated IRIS runtime, compiler and sealing bridge are implemented.
The contest application still needs its AI Hub agent / Interoperability workflow,
end-to-end evidence, UI/demo and final review. This repository is not yet a completed
contest submission. Local verification returns `pending`, never an on-chain claim
or permission to pay. All included records are synthetic; no wallet or API key is needed.

Maintainer: [Rafael Orlando Mendes](https://community.intersystems.com/user/rafaelorlando-mendes).
Code developed with AI assistants under Rafael's direction. License: [MIT](LICENSE).
The vendor EAP image is separately licensed and is not distributed here.

## Start the isolated IRIS lab

Prerequisites: Docker Engine with Compose v2; x86-64 Linux (tested); enough capacity
for the approximately 3.4 GB vendor image, build overhead and 1.2 GiB of container RAM.
The tested lab had at least 2.5 GB free **after** the base image had already been loaded.

1. Obtain the **AI Hub Community build 154** archive from the
   [official EAP portal](https://evaluation.intersystems.com/EAP/), completing the
   vendor's access and license steps yourself. Use the x64 archive
   `iris-community-2026.3.0AI.154.0-docker.tar.gz`. The
   [contest instructions](https://community.intersystems.com/post/intersystems-programming-contest-ai-agents-interoperability-workflows)
   specify build 154. The downloaded image and any derived image must stay private.
2. Load the archive locally and tag the loaded image:

   ```sh
   docker load --input /path/to/iris-community-2026.3.0AI.154.0-docker.tar.gz
   docker tag docker.iscinternal.com/docker-intersystems/intersystems/iris-community:2026.3.0AI.154.0 proof-before-pay/iris-eap:2026.3.0AI.154.0
   ```

   The validated x64 image ID is
   `sha256:8fc1e5c64ed790aa263af05089d003a49bba272fb9c714e4823dd868aebff2a6`.
   The archive's SHA-256 was
   `8b0daa63f279ef9f11fd2377ab9fcf5d5cc953e8141d000539d7eecceee39170`.
   Check your archive/image against those values for the same x64 kit.
3. From this repository:

   ```sh
   docker compose up --build --detach --wait
   python3 scripts/test_iris.py
   ```

   Startup imports and compiles `Witness.cls`. The test then calls both ObjectScript
   methods through the actual embedded Python bridge, including failure and tamper cases.
   It exits nonzero if compilation fails, a result marker is missing, or an assertion fails.
4. Stop the lab with `docker compose stop`. `docker compose down` removes the lab
   container and its disposable state. Recreating it imports the source again.

The service has no network, published port, wallet, model credential or paid inference.
Its working directory and IRIS databases must be writable. It uses the vendor's
normal startup capabilities, dropping NET_RAW and MKNOD. It does not change default
accounts or authentication. Keep this isolated configuration until a separately
reviewed authenticated application is ready. Do not publish this lab's ports.

Apple Silicon is not validated. An ARM64 EAP kit is available from the vendor;
using it requires the matching local image and `IRIS_PLATFORM=linux/arm64`.
Do not compare that image with the x64 hash above.

## Test the language components

```sh
cd seal
npm ci
npm test
npm run typecheck
cd ..
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m pip install -r requirements-test.txt
python -I -B tests/offline_runner.py
python -m pytest -q python/tests
python scripts/check_source.py
```

GitHub Actions runs the TypeScript vectors/typecheck and Python suites. The vendor
EAP image is not available on public CI runners, so actual IRIS compile/bridge tests
run with `scripts/test_iris.py` in the local private-image lab. A green public workflow
alone does not establish an IRIS integration pass.

## What is sealed

The salted SHA-256 commitment covers canonical JSON: inputs, tool outputs, explicit
missing evidence, policy, forbidden actions, decision and autonomy limits. An edited
decision or a dossier completed after sealing changes the commitment. The adapter
rejects personal data and bounded-input errors without returning offending values.
`Witness.Seal` creates a local commitment; `Witness.VerifyLocal` detects edits.
An intact local envelope stays `pending` until independent anchoring is verified.

The original `pbp_seal` reference also contains chain and Solana helpers. Those are
not invoked by the runtime or tests, which do not sign or broadcast transactions.
The historical S0 fixture is public synthetic test evidence, not a new S1 anchor.

See [provenance](docs/PROVENANCE.json), [runtime diagnosis](docs/IRIS-154.md),
[validation](docs/VALIDATION.md), and the [submission draft](docs/OPEN-EXCHANGE.md).
