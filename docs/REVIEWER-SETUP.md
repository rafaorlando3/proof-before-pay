# Private reviewer setup

Use this only in your dedicated, loopback-only recorded lab after the application has
started. It creates one private IRIS login and grants access to the synthetic application
database and native review tasks. Do not expose this lab publicly.

The independent run passed 34 authenticated HTTP checks with `PBPReviewer`, `%DB_USER`,
a dedicated role containing only `%Service_EmbeddedPython:U`, and membership in the
native Workflow role `pbp.Workflow` with ranking 3. That is a tested sufficient set on
build154, not a proof of absolute minimum permissions or a diagnosis of vendor internals.
The narrower `%Development:U` resource alone did not make the HTTP guard work in that run.
Do not grant `%All`, `%Developer` or `%Development` to this reviewer.

## Create a new login after installation

Choose a new login name beginning with `PBP`; the example below uses `PBPReviewer1`.
Existing logins are preserved. The terminal is an installer/admin session; the new
reviewer does not receive the installer's privileges.

On the host, prompt privately for a new password, then pass it by inherited environment
to the IRIS terminal. The password is not placed in the command text or arguments:

```sh
export PBP_REVIEWER_PASSWORD="$(python3 -c 'import getpass; print(getpass.getpass("New private reviewer password: "))')"
docker compose -f compose.yml -f compose.ui.yml exec -e PBP_REVIEWER_PASSWORD iris iris session IRIS -U %SYS
unset PBP_REVIEWER_PASSWORD
```

In that IRIS terminal, use the following commands. Stop on an error; do not reset an
existing login or broaden its privileges to make a failed command pass.

```objectscript
set u="PBPReviewer1",pw=$SYSTEM.Util.GetEnviron("PBP_REVIEWER_PASSWORD")
if $length(pw)<16 { write "Use a private password of at least 16 characters",! halt }
if ##class(Security.Users).Exists(u) { kill pw write "Existing login preserved; choose a new name",! halt }
if '##class(Security.Roles).Exists("PBPEmbeddedPython") { set sc=##class(Security.Roles).Create("PBPEmbeddedPython","Embedded Python for private PBP review","%Service_EmbeddedPython:U") if $SYSTEM.Status.IsError(sc) { kill pw write "Role creation failed",! halt } }
set sc=##class(Security.Roles).Get("PBPEmbeddedPython",.role)
if $SYSTEM.Status.IsError(sc) { kill pw write "Role lookup failed",! halt }
if $get(role("Resources"))'="%Service_EmbeddedPython:U" { kill pw write "Existing role has different resources; preserved",! halt }
set sc=##class(Security.Users).Create(u,"PBPReviewer,%DB_USER,PBPEmbeddedPython",pw,"Private PBP reviewer","","","",0,1)
kill pw
if $SYSTEM.Status.IsError(sc) { write "Reviewer creation failed",! halt }
zn "USER"
if '##class(EnsLib.Workflow.UserDefinition).%ExistsId(u) { set sc=##class(EnsLib.Workflow.UserDefinition).CreateUser(u,u) if $SYSTEM.Status.IsError(sc) { write "Workflow user creation failed; reconcile the existing login",! halt } }
set sc=##class(EnsLib.Workflow.RoleDefinition).AddUserToRole("pbp.Workflow",u,3,"")
write "Workflow membership success=",$SYSTEM.Status.IsOK(sc),!
halt
```

These API calls follow the successful independent steps 18, 29 and 30. The original
test credential is private and is not part of this repository or installation recipe.
If creation succeeds but a later step fails, keep that login for diagnosis instead of
recreating it with another password. In particular, `assign_task_failed` means the
reviewer could not claim the native task; check Workflow membership before retrying.
`guard_unavailable` is a fail-closed guard error, not permission to skip the guard.

`PBP_REVIEWERS` is an alternative for logins that already exist before `pbp.Setup.Install`:
the installer grants `PBPReviewer` and Workflow membership to those names. It does not
create their passwords or grant Embedded Python access. This variable must be present
inside the IRIS container; setting it only in the host shell does not forward it through
the supplied Compose files. The post-install recipe above works for a fresh application
volume without requiring a custom bootstrap image or reinstalling the application.

## Run the authenticated check

Use the same private password and the login just created:

```sh
export PBP_TEST_BASE_URL=http://127.0.0.1:52773
export PBP_TEST_USER=PBPReviewer1
export PBP_TEST_PASSWORD="$(python3 -c 'import getpass; print(getpass.getpass("Private reviewer password: "))')"
python3 tests/http_workflow.py
unset PBP_TEST_PASSWORD
```

Require `"ok": true` and the reported checks. The command creates uniquely named
synthetic cases and one test-ledger effect, including negative and idempotence checks.
It makes no paid inference or blockchain transaction. A failed attempt remains a failed
attempt; preserve its case and diagnostic before starting any new test.
