# Provider validation and cost

The live model must be configured explicitly. The default compose has no network and no LLM key.
Gemini, OpenAI and Anthropic provider constructors and native agent session initialization have been
exercised on build154 with dummy credentials and **no inference**. This does not prove account access,
API compatibility during generation, model quality or live tool execution.

Initial comparison candidates: gemini-3.8-flash, gpt-5.4-mini, claude-haiku-4-5.
These are candidates, not a quality ranking. A real-call result is required before choosing the demo model.
Use only synthetic fixtures. Do not put API credentials in commands, URLs, output, Git, or the channel.

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
