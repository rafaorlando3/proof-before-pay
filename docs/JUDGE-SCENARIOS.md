# Proof desk: inspect, compare and reproduce

Use the [hosted viewer](https://review.pbp49.78-17-93-244.sslip.io/pbp/ui/) with the dedicated viewer invitation. It is an inspection facade over a running IRIS instance. It cannot approve payments, import cases or run arbitrary prompts. All amounts and effects are synthetic.

## Four retained outcomes, without running a model

The four outcome cards are visible at the top. Start with the completed refund and compare the missing-destination refusal. **Cases** opens the queue; **Dossier**, **Evidence**, **Timeline** and **Seals** move within the selected record. The five steps inside a case are keyboard-accessible links to the corresponding proof sections. **Evaluation** opens the published historical results; it does not rerun them. Appearance follows your system until you choose Paper or Ink; that choice is saved only in this browser.

| Route | Question to answer | Inspect | Retained outcome and boundary |
|---|---|---|---|
| Completed refund — `video-demo:d83544a2` | What connects a proposal to exactly one test effect? | Recorded proposal; decision and approval seals; permit bound to the approval; consumed permit; receipt `test-refund:456`. | Intact **84.00 BRL synthetic receipt**. The approval and effect happened historically; opening the record creates neither. |
| Retained LIVE — session **1566** | Did the model cite something it actually observed? | Five tool calls in Time Machine; `GetStorePolicy` with three retrieved passages; the cited chunk; decision seal and native session. | Valid cited human-review proposal, **no permit or effect**. This is one prior qualification, not a fresh call or general model-quality result. [Public qualification](validation/live-gemini35lite-1566-20261105.json), [native headers](validation/live-session1566-native-headers.json). |
| Missing destination — `recipient-flow:absent:bfe5c8fd` | Can an acknowledgement create missing payment authority? | Recorded refund proposal; sealed ledger refusal `test_recipient_required`; historical acknowledgement; absence of permit and receipt. | **Closed, no effect.** A closed case is not necessarily a payment. The test ledger refused an unusable destination. |
| Delivery conflict — `pix-0006:70dc920238` | Is a delivery scan enough to resolve the customer's contradictory claim? | Recorded `hold_for_evidence`; `evidence.carrier_signature` sealed as missing; five retained tools; later human rejection in Timeline; two linked seals. | **Rejected, no effect.** The proposal and subsequent review are distinct. Disputed-delivery refunds are outside the v1 effect contract. |

For each route, distinguish the proposed action, the effective sealed decision, the historical review and any actual test receipt. A `moves_money` flag, a confidence value or an intact local seal alone does not authorize an effect.

### Check a copy, without changing the original

1. Open a retained decision and its **Seals** section. Choose **Try to tamper**.
2. In the displayed JSON copy, append a short word to `decision.rationale`, preserving valid JSON.
3. **Verify this copy** should report that the copy differs from the sealed record. The stored original should still show **Intact**.
4. Restore the complete original JSON copy and verify again; it should report **intact · identical to the sealed record**.

This checks local integrity against the stored commitment. It does not protect against a privileged administrator replacing the database, salt and commitment. It performs copy verification, not a model call, approval or payment.

## Ten public local fixtures, with different questions

These [source fixtures](../fixtures/cases/) are available in a private recorded-mode installation. They are **not ten additional cases in the hosted viewer**, new live runs, a blind evaluation or a measured improvement. The four online records above have their own historical IDs and amounts.

| Fixture | Input to notice | What to inspect in a recorded local run |
|---|---|---|
| [pix-0001](../fixtures/cases/pix-0001.json) | Two distinct payments of 18990 minor units from one payer; stored recipient present. | Rule R1 proposes the later duplicate for refund; human review and a seal-bound permit remain required for a test effect. |
| [pix-0002](../fixtures/cases/pix-0002.json) | Two payments of 129900; order already shipped. | Duplicate handling and the exact refund target. Shipment and a delivery scan do not themselves authorize a different effect. |
| [pix-0003](../fixtures/cases/pix-0003.json) | 5000 paid for a 4990 order. | R2's small overpayment route, accepted with store credit; no transfer or refund. |
| [pix-0004](../fixtures/cases/pix-0004.json) | Full payment after expiry, within the policy's grace window. | R3's nonfinancial release decision and the timestamps it read. |
| [pix-0005](../fixtures/cases/pix-0005.json) | 12900 paid for an 8900 order; customer requests the difference. | Rules abstain; a recorded escalation explains the unsupported partial-refund request. No new inference. |
| [pix-0006](../fixtures/cases/pix-0006.json) | Delivered status and carrier scan contradict the customer's claim. | Recorded missing carrier signature, evidence references, hold-for-evidence and the v1 execution boundary. |
| [pix-0007](../fixtures/cases/pix-0007.json) | MED dispute, absent delivery proof and customer message. | Explicit sealed gaps and human escalation; the system does not invent a defense or execute a dispute refund. |
| [pix-0008](../fixtures/cases/pix-0008.json) | Failed withdrawal, `account_closed`, no new destination. | The recorded withdrawal-retry proposal is outside the executable contract; inspect the guard's refusal and effective escalation. |
| [pix-0009](../fixtures/cases/pix-0009.json) | Duplicate payments with **no stored recipient**. | Missing refund target/destination and the refusal of a financial effect; never fill it from model prose. |
| [pix-0010](../fixtures/cases/pix-0010.json) | 9900 paid for a 10000 order; payer history absent. | R2's nonfinancial small-underpayment route and the separately retained missing history. |

Rules R1–R3, recorded proposals and server validation have different responsibilities. Read [Rules.cls](../cls/pbp/Rules.cls), [the public recorded tape](../fixtures/replay/decisions.json) and [the context guard](../python/pbp_guard/decision.py) alongside the outputs. The default policy uses a 200-minor-unit small-difference threshold and 48-hour late-payment grace; inspect the policy actually loaded in your lab.

## Reproduce in the appropriate environment

The [root installation recipe](../README.md#start-the-isolated-iris-lab) covers the separately licensed build154 image, platform, dependencies, private credentials and resource prerequisites. No EAP image, model key or reviewer password is distributed here. Use a dedicated synthetic recorded-mode lab; these commands execute tests and can create historical test cases and effects there.

After installing that lab:

```sh
python3 scripts/test_iris.py
python3 scripts/test_ledger.py
python3 scripts/test_workflow.py
python3 scripts/test_pairguard.py
python3 scripts/test_recipient.py
```

Check the JSON assertions and reported case IDs, rather than treating an IRIS terminal's exit code alone as a pass. The workflow gate includes three recorded adversarial proposals; the pair guard checks competing refund targets; recipient tests cover known, absent and mismatched destinations. Use the IDs those commands report, not stale IDs from another installation. This is execution of replay/regression tests, not new inference or a new benchmark.

For the ten original fixtures, `Do ##class(pbp.Setup).FeedCases()` in the lab's USER terminal feeds the public inputs. It does not create the workflow gate's suffixed adversarial examples. Follow the [authenticated HTTP recipe](../README.md#judge-path) for end-to-end test review, consumed permit, copy verification and refusal paths. That recipe requires private reviewer credentials and a loopback URL; it is not an instruction to submit HTTP approvals to the hosted viewer.

For source-only checks without the licensed runtime, follow [Test the language components](../README.md#test-the-language-components). Public CI covers TypeScript, Python and the standalone optional PEX algorithm; it does not establish a native IRIS integration pass. Fresh paid inference is a separate opt-in under existing cost controls, unnecessary for these retained examples.

## Published evaluations are a separate layer

| Evidence | Scope to preserve |
|---|---|
| [v7 report](validation/paired-v7-20261101.md) and [structured summary](validation/paired-v7-20261101.json) | One pre-frozen **informed 12-case set**: raw agent 11/12, effective 10/12, versus the stated baselines on those same cases. Published errors remain counted. This is not a population estimate or twelve new online cases. |
| [Independent v5 cohort](validation/live-independent-v5.json) | Eight informed adversarial cases, three intact positive test receipts and five zero-effect cases. One raw malformed-amount error was contained by the server. |
| [v6 readings](validation/paired-v6-20261031.json) | Preserve the failed instrumentation attempt and separately admitted technical repeat; the required autonomy gain was not demonstrated. |
| [LIVE1566](validation/live-gemini35lite-1566-20261105.json) | One successful cited hosted qualification. No effect and no general quality-gain claim. |

More examples make boundaries easier to inspect. They do not, by themselves, establish higher accuracy, awarded bonus points or a probability of winning.

## Guided proof inspection

After opening a retained case, use **Previous / Next step** to inspect evidence, proposal, seals, review and test effect. This moves focus through the loaded record; it does not replay an agent, authorize a payment or create a new trace. The dossier separates the unsealed diagnostic proposal from the verified effective decision and the actual outcome. “Acknowledged” does not mean payment approved, and the historical generic event “approval sealed (witness)” is qualified when the actual review was a rejection.

Readable order/payment amounts and explicit gaps come from the matching intact decision record. If verification or case binding fails, that view stays unavailable. Original rationale, normalized JSON, hashes and events are preserved. Model confidence is uncalibrated; visible-token cost estimates are distinct from conservative budget accounting and billing. Stored zero tool timings are not a fresh latency measurement.

The retained LIVE1566 dossier highlights three local vector-policy passages and the passage cited in the sealed decision. Opening it does not generate embeddings or call a model. A citation proves the reference was retained; it does not establish correct interpretation. The **Evaluation** panel shows four v7 controls and eight residues from the public report, including r4's ledger/gold limitation, r8's missing-evidence omission and D7's unsafe synthetic second refund. These historical informed cases do not estimate general accuracy or contest results.
