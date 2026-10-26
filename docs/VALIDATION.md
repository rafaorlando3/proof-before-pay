# Validation on 26 October 2026

Executed in isolated lab containers on x86-64 Linux:

- TypeScript S0: 20 tests passed; typecheck passed.
- Python S0: 24 tests passed, with no live Solana calls.
- Bounded Witness adapter: 16 tests passed; attempted forbidden network/process I/O: 0.
- Actual IRIS build154: Witness compiled; 12 bridge checks passed.

The bridge checks cover seal creation, random salt, local pending state, absence of
payment authority, local verification, no salt in verification response, tampering,
PII-key redaction, the human boundary, duplicate JSON fields, input size and the
actual ObjectScript Catch path when Python raises an exception.

Runtime tests compile the ObjectScript class and call its methods through IRIS.
They do not merely retest the Python implementation. A failed compile or missing
result marker fails `scripts/test_iris.py`, even if the terminal process exits zero.

The public workflow does not possess or redistribute the separately licensed EAP
image; its result and private-image IRIS runtime evidence are separate gates.
No AI Hub agent decision, Interoperability workflow completion, paid inference,
new chain transaction or final contest submission is established by these tests.
