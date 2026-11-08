# Optional Java PEX export inspection

This optional production checks the **exact UTF-8 transport bytes** of a synthetic
evidence export against a SHA-256 digest retained separately. It helps detect a
changed download before an auditor compares the underlying evidence. It does not
canonicalize JSON: changing whitespace intentionally changes this transport digest.

`MATCH` is **not** a verified Witness seal, an authentic source, an approval,
a permit or a payment. Replacing both the export and its expected digest is outside
this check. Continue using the main console's seal and receipt verification.

The Java class extends the vendor's `com.intersystems.enslib.pex.BusinessOperation`.
The dedicated `pbp.PEX.Production` routes a typed request from an adapterless
service to that PEX operation and records the typed response in native message
history. The operator entry requires `%Admin_Operate:U`. There is no HTTP/MCP
route, provider call, ledger call, file access or external network call in the
operation. Its payload is bounded to 65,536 UTF-8 bytes. Invalid expected digests,
malformed UTF-16 input and oversized payloads are rejected.

## Reproduce in a dedicated build154 instance

Use the vendor-licensed IRIS AI Hub build154 image and its bundled JDK/PEX/JDBC
libraries. The repository supplies only our MIT source. Do not publish the vendor
image, vendor JARs or a derived image. Use a dedicated instance with no provider
credentials or mounted live data. No model, wallet or internet connection is needed.

1. Copy this checkout's `pex/` and `pex/cls/pbp/PEX/` directories into the dedicated
   container, for example as `/tmp/pbp-pex/` and `/tmp/pbp-pex-cls/`.
2. Build inside that container:

   ```sh
   sh /tmp/pbp-pex/build.sh /tmp/pbp-pex /tmp/pbp-pex-build
   ```

   It compiles with the bundled vendor libraries, runs the algorithm checks and
   creates an own-code JAR. It does not copy the vendor libraries into that JAR.
3. In a `USER` terminal in the **dedicated** instance, load the five ObjectScript
   classes, register the remote Java operation and start this separate production:

   ```objectscript
   set sc=$SYSTEM.OBJ.LoadDir("/tmp/pbp-pex-cls/","ck",,1)
   do $SYSTEM.Status.DisplayError(sc)
   set cp="/tmp/pbp-pex-build/pbp-export-digest.jar:/usr/irissys/dev/java/lib/1.8/intersystems-pex-1.0.0-shaded.jar"
   set sc=##class(EnsLib.PEX.Utils).RegisterComponent("pbp.pex.ExportDigestOperation","%Java Server",cp,0,"pbp.PEX.ExportDigestOperation",0)
   do $SYSTEM.Status.DisplayError(sc)
   set sc=##class(Ens.Director).StartProduction("pbp.PEX.Production")
   do $SYSTEM.Status.DisplayError(sc)
   ```

   Check every status before proceeding. The Java server is internal to the
   isolated container; do not publish its port. The classpath separator shown is
   for the qualified Linux build154 environment. Registration generates a native
   PEX proxy; a standalone Java invocation alone is not Production integration.
4. Send a known exact-byte check through the actual service and operation:

   ```objectscript
   set expected="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
   set sc=##class(pbp.PEX.Inspection).Inspect("abc",expected,.response)
   write $SYSTEM.Status.IsOK(sc)," ",response.Status," ",response.ByteCount,!
   set sc=##class(pbp.PEX.Inspection).Inspect("abd",expected,.changed)
   write $SYSTEM.Status.IsOK(sc)," ",changed.Status,!
   ```

   Expect `1 MATCH 3` then `1 MISMATCH`. Follow the two native sessions in
   Interoperability message history. For your own **synthetic public export**, use
   the exact file bytes and a separately recorded digest. Do not send private salts
   or credentials to this example.
5. Stop **this dedicated production** after inspection:

   ```objectscript
   set sc=##class(Ens.Director).StopProduction()
   do $SYSTEM.Status.DisplayError(sc)
   ```

Never run these setup/stop commands in the hosted payment-demo namespace. This
optional source-checkout component is separate from the immutable public IPM
beta.4 artifact and is not enabled in the hosted viewer.

The [native qualification](../docs/validation/pex-export-inspection-20261108.json) separates algorithm, build, native registration and Production checks.
C1270 reviewed the source without blockers. Its oversized-payload status correction
passed all 12 algorithm checks separately; the retained native/JAR qualification
is from the preceding `941e929` source. No final-source native rerun or public CI
result is claimed. No bonus award is inferred from this implementation.
