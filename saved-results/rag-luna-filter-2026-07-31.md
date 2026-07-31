# Luna retrieval filter result

**Date:** 2026-07-31  
**Purpose:** make RAG eager enough to cover the substantive turns in the supplied call without attaching Epictetus passages to its closing acknowledgment.

## Decision

```text
cosine < 0.2315        -> no retrieval
0.2315 <= cosine < .36 -> GPT-5.6 Luna dialogue-intent check
cosine >= 0.36         -> retrieval without Luna
```

Luna receives only the previous Epictetus reply and current user turn. It returns one structured boolean with reasoning disabled, a 16-token output ceiling, a three-second timeout, response storage disabled, and automatic retries disabled.

If Luna fails in the deployed `start` process, the worker logs the exception and proceeds with retrieval. In `dev`, `console`, and tests, the same failure is raised so it cannot pass unnoticed. A Luna rejection publishes the existing empty source payload; the Vercel interface does not need a new state.

## Test-first evidence

Before implementation, the focused run reported eight behavioral failures plus the missing Luna module. The failures showed the old `0.36` constant, missing filter arguments, and missing previous-reply context.

After implementation:

```text
59 passed in 2.57s
```

The project virtual environment did not contain Ruff, but the machine Ruff binary completed both `ruff check agent tests` and `ruff format --check agent tests` successfully. The two existing evaluation helper scripts retain eight pre-existing import-position warnings caused by deliberately inserting the repository path before local imports.

The unchanged web app also passed 55 tests, TypeScript checking, and a production Next.js build.

## Real GPT-5.6 Luna check

The first 1.5-second request timed out. With a longer measurement ceiling, the cold request completed in 2.386 seconds and rejected Turn 7. A seven-turn sequential run then produced:

| Turn | Luna retrieve | Seconds |
|---:|:---:|---:|
| 1 | yes | 1.993 |
| 2 | yes | 1.158 |
| 3 | yes | 0.966 |
| 4 | no | 0.921 |
| 5 | yes | 0.820 |
| 6 | yes | 0.819 |
| 7 | no | 0.920 |

The three known false matches were also rejected: connection check in 1.999 seconds, calendar request in 1.569 seconds, and journal request in 1.357 seconds. These measurements led to the three-second hard ceiling and zero retries.

## Real index and API pipeline

The final pre-deployment check used the committed 539-chunk index, real OpenAI embeddings, real hybrid search, the new threshold, real Luna decisions, prompt construction, and source-payload publication.

| Case | Best cosine | Prompt passages | Visible sources |
|---|---:|:---:|---:|
| Turn 1 | 0.2843 | yes | 4 |
| Turn 2 | 0.3376 | yes | 4 |
| Turn 3 | 0.2315 | yes | 4 |
| Turn 4 | 0.2695 | no | 0 |
| Turn 5 | 0.3213 | yes | 4 |
| Turn 6 | 0.3172 | yes | 4 |
| Turn 7 | 0.2473 | no | 0 |
| connection check | 0.2944 | no | 0 |
| calendar request | 0.3536 | no | 0 |
| journal request | 0.3044 | no | 0 |

The integrated run normalized punctuation in the fragmented Turn 7 transcript,
which changed its cosine from the exact replay's 0.2451 to 0.2473. Both values
are within the Luna-only range and Luna rejected both wordings.

Turn 3 displayed four passages led by Book 4, Chapter 1, **About Freedom**. This is the exact low-scoring but logically strong match the old gate discarded.

The existing ranking benchmark was rerun without changing its ranking settings:

| Question set | Questions | Hit@4 | MRR | Median retrieval latency |
|---|---:|---:|---:|---:|
| chapter-derived | 53 | 96.2% | 0.912 | 252 ms |
| spoken | 12 | 75.0% | 0.528 | 269 ms |

Those values match the recorded ranking quality. Its raw-score check correctly notes that small talk reaches the new floor; Luna's real-pipeline rejections above are the final-decision evidence.

## Sources and reproduction

- Transcript: `/Users/aadivyar/.codex/attachments/57a1f2d6-e8c4-49ed-ab3b-b8f4fed7223d/pasted-text.txt`
- Diagnosis and exact chunk scores: `saved-results/rag-live-debug-2026-07-31.md` in the original checkout
- Official model page: `https://developers.openai.com/api/docs/models/gpt-5.6-luna`
- Focused checks: `pytest tests/test_agent_behaviour.py tests/test_turn_hook_grounds.py tests/test_worker_wiring.py tests/grounding/test_luna_turn_filter.py`
- Full local suite: `pytest`

Production deployment and browser-driven evidence will be appended after release verification.
