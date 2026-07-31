# GPT-5.6 Luna voice-agent migration

Date: 2026-08-01

## Result

The Epictetus voice worker now builds its OpenAI language model with
`gpt-5.6-luna` and `reasoning_effort="none"`. The explicit reasoning value is
required for the existing Chat Completions function-tool path.

## Why GPT-4.1 was present

The active voice model was set once in `agent/main.py`. The README described the
choice as useful for staying in character while using tools. No comparative
benchmark between GPT-4.1 and another voice model was present in the repository.

Historical GPT-4.1 references in the evaluation generator and generated question
set remain unchanged because they describe which model produced that saved data.

## Verification

- Red test: `tests/test_worker_wiring.py` failed because the built model was
  `gpt-4.1`, not `gpt-5.6-luna`.
- Focused green run: 9 tests passed.
- Full Python run: 46 tests passed.
- Ruff: `agent/main.py` and `tests/test_worker_wiring.py` are clean. A whole-repo
  run still reports eight existing E402 import-order warnings in the two
  standalone scripts under `eval/tools/`; this migration did not add them.
- Paid OpenAI smoke test: 3/3 cases behaved as expected. The modern-world prompt
  called `look_up_modern_thing`, the reflection prompt called
  `write_to_session_log`, and the greeting called no tool.
- LiveKit deployment: agent `CA_oCa7eq9DyLT4`, production version
  `fEHe7zJqJHSA`, deployed at 2026-07-31 21:42:28 UTC.
- Worker startup: two warm processes initialized, each loaded 539 chunks, and
  the `epictetus` worker registered in US East.
- Paid deployed simulation: stricter run `SR_7Hc9sCZYkV2v`, scenario
  `SRJ_GxZTrNLcMeM4`, passed 1/1 with `write_to_session_log` as an explicit pass
  condition. Its transcript recorded two successful calls: the caller's initial
  reflection and later commitment. The production worker log recorded
  `model=gpt-5.6-luna reasoning=none` for the same deployed version.
- Public token route: HTTP 200 with a non-empty server URL, non-empty room token,
  and an `epictetus-` room name. Secret values were not printed.
- Notion read-back: the screen-share page names GPT-5.6 Luna in the overview and
  names reasoning `none` in the code walkthrough.

The LiveKit simulation runs in text mode, so it exercised the deployed language
model, session-log tool, persona, and conversation logic. It did not exercise Deepgram or
ElevenLabs. The earlier paid model smoke test also used text. A microphone-based
voice call remains the final rehearsal step for the recording.

## Reproduce

```bash
python -m pytest tests/test_worker_wiring.py -q
python -m pytest -q
ruff check agent/main.py tests/test_worker_wiring.py
python eval/tools/tool_check.py
lk agent list
lk agent simulate --scenarios eval/tools/luna_live_smoke.yaml --agent-name epictetus
```

The commands requiring live services expect credentials from the local `.env`;
do not print or commit that file.
