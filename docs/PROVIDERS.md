# Provider validation and cost

The live model must be configured explicitly. The default compose has no network and no LLM key.

On 2026-10-26, the native AI Hub agent completed one synthetic duplicate-payment scenario with each
of `google/gemini-3.8-flash`, `openai/gpt-5.4-mini` and `anthropic/claude-haiku-4.5` through OpenRouter.
The native protocol provider was `openai` for all three. The routed inference providers reported
Google AI Studio for Gemini and Azure for the other two; this does not prove direct vendor credentials.
Each model actually called all five scoped native tools, proposed a duplicate refund, waited for
an authenticated automated test review, and ended with one confirmed sandbox effect.

| Model | API-reported cost for this case | Native LLM duration | Prompt / completion tokens |
|---|---:|---:|---:|
| Gemini 3.8 Flash | US$0.007833 | 12,121 ms | 2,534 / 1,582 |
| GPT-5.4 Mini | US$0.00286875 | 18,138 ms | 2,109 / 286 |
| Claude Haiku 4.5 | US$0.006290 | 5,534 ms | 3,925 / 473 |

**One case per model is insufficient for quality ranking or latency percentiles.** The scenario uses
fixture pix-0001 with unique references, an explicit trusted refund reference and the ledger-supported
legacy exception `duplicate_charge`, which deliberately has no R1 deterministic match. It exercises
the agent path; ordinary R1 `duplicate_payment` cases can correctly bypass inference.

The bounded private gateway capped the whole trial at US$1 and 24 forwarded requests, with at most
2,048 output tokens per generation. Seven requests were forwarded: six successful generations and
one initial GPT routing failure. Provider-reported spend was US$0.01699175. The failed HTTP 404 request
had no usage receipt; its US$0.114858 reservation remains held, rather than being called free.
The trial gateway was stopped and its decrypted credential RAM mount removed; the accounting ledger
and original synthetic receipts were retained.

Compatibility and quality findings:

- GPT-5.4 Mini rejected the native client's temperature parameter under strict routing. The private
  gateway omitted that unsupported parameter for the successful retry. Its effective temperature is
  unknown; the sealed native configuration records the client's requested zero. See the model's
  [supported endpoint parameters](https://openrouter.ai/api/v1/models/openai/gpt-5.4-mini/endpoints)
  and [strict parameter routing](https://openrouter.ai/docs/guides/routing/provider-selection).
- Haiku described 18,990 minor units as 18,990 BRL in its rationale. The deterministic ledger executed
  the correctly bound 18,990 minor units, but the explanation still has a quality error.
- Approval notes were absent in the baseline trial because Workflow `%FormValues` is an array. The
  application fix is tested in replay for both approval and rejection; old seals were not rewritten.

See [original live evidence](validation/live-provider-smoke.json). All inputs are synthetic. No model
may authorize money. No quality winner or three-agent architecture is established by this smoke test.
Do not put API credentials in commands, URLs, output, Git, or the channel.

Prices checked 2026-10-26, standard text USD per million tokens:

| Model | Input | Output | Source |
|---|---:|---:|---|
| gemini-3.8-flash | 0.75 | 3.75 | [Google](https://ai.google.dev/gemini-api/docs/pricing) |
| gpt-5.4-mini | 0.75 | 4.50 | [OpenAI](https://developers.openai.com/api/docs/pricing) |
| claude-haiku-4-5 | 1.00 | 5.00 | [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing) |

Google's quoted Flash rates apply through 2026-12-31. Prices, access and quotas can change.
The app's estimate is not a billing receipt; cached and reasoning tokens require careful accounting.
A missing price or missing usage must appear as **unknown**, not free. Replay has zero LLM calls.

## Three-agent experiment

The core remains one bounded tool-using agent followed by deterministic policy and authenticated human
review. An optional proposer → independent evidence critic → consolidator can be compared after the
core passes. None may authorize a financial effect or change evidence/policy. A majority vote never
supersedes an absent critical field, a refusal by the ledger or the human gate.

Use the same held-out cases for one-agent and three-agent conditions, randomize order, retain raw
synthetic outputs and sealed provenance. Count unsafe proposals, fabricated evidence, missed missing
fields, correctly escalated contradictions, useful disagreements, latency, calls/tokens and estimated
cost. Include correlated-error cases where all three agree incorrectly. Separate model comparisons
from architectural comparisons. Adopt only if the observed gain merits its cost and failure surface;
report sample sizes and uncertainty. Do not convert a small test into a probability of winning.

## Subsequent local hardening

The context guard is exercised without new inference calls against the three actual captured
provider proposals above, as well as development attacks and positive controls. These proposals
remain accepted by the new structural/context checks. This is replay of existing evidence, not
three new live calls, a held-out quality result, or a demonstration of ensemble benefit.

## Direct Google API key trial

Rafael supplied the private Gemini key on 26 October. Authenticated model metadata succeeded,
then one synthetic case completed the actual IRIS agent/tool/review/ledger workflow using Google's
OpenAI-compatible endpoint directly, without OpenRouter. The native protocol provider was explicitly
`openai`; the model vendor was Google and model `gemini-3.8-flash`. This route is documented by
[Google](https://ai.google.dev/gemini-api/docs/openai).

Two generation requests returned 2,557 prompt tokens and 340 completion tokens. Applying the
[standard rates](https://ai.google.dev/gemini-api/docs/pricing) checked that day gives US$0.00319275.
That is a usage-based estimate, not a Google billing receipt. Separate thinking-token detail was not
independently preserved; zero is not inferred. Full conservative reservations remain held. The trial
retained the original US$1 lifetime cap, prior spend and the failed OpenAI request reservation.

The private gateway capped this direct phase at two generation requests and 2,048 output tokens each,
and explicitly requested reasoning_effort=low. It did not fabricate a model response or tool result.
The decision and approval seals, consumed permit, intact receipt and one sandbox effect are in
[direct Gemini evidence](validation/gemini-direct-smoke.json). Automated test review is not Rafael's
approval of a real payment or contest submission.

On build154, `%AI.Provider.%GetProviders()` advertises only api_key for the named Gemini provider;
its fixed default endpoint is Google's compatible API. A top-level base_url fails construction;
nesting it under http_config constructs successfully but does not change the destination. Therefore
the application rejects a custom base URL for provider=gemini and requires an explicit compatible
transport selection. A native constructor regression covers both the rejection and valid standard
Gemini/OpenAI configurations, without inference. Do not treat a successful constructor alone as
proof that network routing works.
