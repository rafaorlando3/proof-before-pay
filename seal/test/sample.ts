// Read-only example using the existing public cross-language test vectors.
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { canonical, commitment, memoFor, verifyAgainst } from '../src/seal.js'

const vectorUrl = new URL('./vectors.json', import.meta.url)
const vectorSha256 = '4db680b42b8a133867fc90e5a91cee74f959fa23e78852cdb581a9a2d5d5583f'
const digest = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')
const before = readFileSync(vectorUrl)
assert.equal(digest(before), vectorSha256, 'Public vector file differs from the pinned sample')

type Vector = {
  name: string
  record: Record<string, unknown> & { missing: Record<string, null> }
  salt: string
  canonical: string
  commitment: string
}
const vectors = JSON.parse(before.toString('utf8')) as { valid: Vector[] }
for (const vector of vectors.valid) {
  assert.equal(canonical(vector.record), vector.canonical, `${vector.name}: canonical bytes differ`)
  assert.equal(commitment(vector.record, vector.salt), vector.commitment, `${vector.name}: commitment differs`)
}
const original = vectors.valid.find(vector => vector.name === 'decision_duplicate')
assert(original, 'Public decision_duplicate vector is missing')
assert.equal(original.record.missing.payer_message, null, 'Expected an explicitly missing payer message')
const snapshot = JSON.stringify(original.record)
const edited = structuredClone(original.record)
delete edited.missing.payer_message
assert.equal(edited.missing.delivery_photo, null, 'The other declared gap must remain')
const editedCommitment = commitment(edited, original.salt)
assert.notEqual(editedCommitment, original.commitment, 'Editing a declared gap must change the commitment')

// These references are supplied locally. No RPC or chain lookup happens.
const simulatedReference = { memo: memoFor(original.commitment), blockTime: null }
const matching = verifyAgainst(original.record, original.salt, simulatedReference)
const changed = verifyAgainst(edited, original.salt, simulatedReference)
const absent = verifyAgainst(original.record, original.salt, null)
const unreadable = verifyAgainst(original.record, original.salt, { memo: 'not-a-pbp-memo', blockTime: null })
assert.deepEqual(matching, { state: 'sealed', reason: 'ok' })
assert.deepEqual(changed, { state: 'tampered', reason: 'commitment_mismatch' })
assert.deepEqual(absent, { state: 'pending', reason: 'not_anchored' })
assert.deepEqual(unreadable, { state: 'unverifiable', reason: 'anchor_memo_not_pbp' })
assert.equal(JSON.stringify(original.record), snapshot, 'Original in-memory record changed')
assert.equal(commitment(original.record, original.salt), original.commitment, 'Original commitment changed')
const after = readFileSync(vectorUrl)
assert(before.equals(after), 'Public vector file changed during the sample')
assert.equal(digest(after), vectorSha256, 'Public vector file no longer matches the pinned sample')

console.log(JSON.stringify({
  schema: 'pbp.seal.offline-sample/1',
  scope: 'Public synthetic test vectors; local commitment recomputation and comparison only.',
  provenance: {
    path: 'seal/test/vectors.json',
    published_commit: 'a36a922d9e8f292aef0a034af541f7fe06d14d5e',
    file_sha256: vectorSha256,
    salt: 'Long-public synthetic fixed test salt; not a private export.'
  },
  vectors_checked: vectors.valid.length,
  selected_vector: original.name,
  expected_commitment: original.commitment,
  edited_copy_commitment: editedCommitment,
  edit: 'Removed missing.payer_message from a copy; missing.delivery_photo stays null.',
  checks: {
    original_commitment_matches: true,
    edited_copy_matches: false,
    original_record_unchanged: true,
    vector_file_unchanged: true
  },
  simulated_reference_results: {
    warning: 'All memo references below are supplied locally, not read from a chain.',
    original_with_matching_memo: matching,
    edited_copy_with_original_memo: changed,
    original_without_reference: absent,
    original_with_unreadable_memo: unreadable
  },
  limits: [
    'Not a native IRIS execution, human approval, permit or payment receipt.',
    'No model, IRIS, RPC, payment or other network call is made by this sample.',
    'No blockchain anchor, signer identity or event time is independently established.',
    'A matching commitment does not establish that a decision is correct.'
  ]
}, null, 2))
