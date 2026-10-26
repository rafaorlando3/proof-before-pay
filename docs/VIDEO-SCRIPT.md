# Proof Before Pay: 3-minute video script (draft, English, honest)

Narrated by Rafael (his voice is optional; the on-screen text is his). Recorded against the real IRIS 154 lab in
RECORDED mode unless a live key is available on the day; the caption says which.

0:00-0:20  Title card. "Agents are starting to touch money. Afterwards, nobody can prove what the agent saw.
           Proof Before Pay seals the decision before anything moves. Change it afterwards and the seal turns red."
0:20-0:45  Management Portal: the production. Point at Intake, Decide, Agent (disabled: no key, recorded replay
           enabled), Witness, TestLedger, Workflow. Caption: "Native Interoperability: every step is a message."
0:45-1:20  Console: feed a duplicate Pix payment. Rules propose refund_duplicate (18990 BRL), requires human. The
           seal card appears: intact, commitment, prev none. Open "what it did not see": delivery_proof missing.
           Caption: "Sealed ignorance: what was missing is part of the proof."
1:20-1:45  Approve as the reviewer. Show the sealed approval chained to the decision, the single-use permit bound to
           the commitment, the test ledger receipt (sealed_seq < authorized_seq < executed_seq). Caption: "One permit,
           one effect. Ten identical requests give one receipt."
1:45-2:15  Try to tamper: change the amount in the copy, verify: red. Change a missing field: red. Restore: green.
           Then the "sealed after the money moved" state on the failure-lab case. Caption: "The verifier does not
           trust the database."
2:15-2:40  Time machine: the tool outputs the agent saw, model/mode label (recorded), tokens and cost column
           (unknown when no price). Message trace in the Portal with the commitment in each message.
2:40-3:00  Honest close: "Test ledger, synthetic data, local seals. Live mode runs with your own key; recorded mode
           is labelled as such. Repository, install in one compose, article on the AI Hub experience." No claims about
           novelty beyond "we found no public precedent inside an interoperability engine"; related work (AP2) in the README.
