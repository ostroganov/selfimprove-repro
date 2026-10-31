# Data schema

Everything under `data/` was produced once from the experiment tree the
framework wrote, by a **select, rename and copy** step: no file content was altered, so any
run directory here is byte-identical to its source. The data is the starting
point — nothing needs to be imported or rebuilt to use it.

## What is here, and what is deliberately not

`data/runs/` contains the **54 runs the paper analyses**: 6 models × 3 modes × 3 runs.

The study also produced 17 further runs of 7 other models, tested in selected
conditions only. They are excluded, for two reasons:

1. They were not run systematically, and no analysis in the paper should use them.
2. In the experiment tree they share directories with the analysed runs, so an
   analysis that selects runs by pattern-matching directory names silently
   absorbs them. Excluding them makes that class of bug unrepresentable here.

They are not released.

## Layout

```
data/
  MANIFEST.json          # 54 run records; the authoritative index
  corpora.json           # named corpora that analyses select by id
  lexicons.json          # versioned stem-keyword families
  SCHEMA.md              # this file
  runs/<mode>/<api_model>/run<N>/
```

`<mode>` is `freedom`, `happiness` or `improvement` (singular; the source tree
uses `experiments-improvements`, plural).

`<api_model>` is the **exact API model string**, which is also what each run
recorded about itself:

| directory / api_model | paper name | provider |
|---|---|---|
| `claude-opus-4-5-20251101` | Claude Opus 4.5 | Anthropic |
| `claude-sonnet-4-5-20250929` | Claude Sonnet 4.5 | Anthropic |
| `gpt-4o` | GPT-4o | OpenAI |
| `gpt-5.1` | GPT-5.1 | OpenAI |
| `grok-4-0709` | Grok-4 | xAI |
| `gemini-3-pro-preview` | Gemini-3 Pro | Google |

In the source tree the same model has a different directory name in each mode
(Opus alone has three). The API model string, by contrast, is identical across
all three modes for every model — so the rename was verified against
`metadata.model` rather than merely conventional, and `repro/check.py` re-asserts
`directory name == metadata.model` for all 54 runs on every run. Note the one correction this surfaces: the source
directory says `gemini-3-pro`, but the recorded model is `gemini-3-pro-preview`.

## Inside a run

```
run<N>/
  levels/
    L0/                          # the empty starting prompt
    L<n>/
      system_prompt.md           # the prompt at this level
      metadata.json              # level, parent_level, created_at, model,
                                 #   orchestrator_version, run_id, mode,
                                 #   converged?, convergence_declared_at?
      CONVERGENCE.md             # present only where convergence was declared
  transitions/
    L<n>_to_L<n+1>/
      commit_rationale.md        # why the model committed this change
      handover.md                # message written to the successor level
      metrics.json               # conversations, drafts, tokens, cost, timing
      work/
        draft_prompt_v<k>.md     # every draft, including uncommitted ones
        evaluation_notes.md
      conversations/
        conv_<nnn>.json          # candidate-evaluation conversations
  conversations/                 # present in 38 of 54 runs; see the warning below
    L<n>_to_L<n+1>/
      orchestration_<ts>.json    # orchestrator tool-call transcript
```

### Warning: two different things are called "conversations"

This trap is inherited from the source tree and is preserved here for fidelity.

| path | content | count | coverage |
|---|---|--:|---|
| `transitions/*/conversations/conv_*.json` | **candidate-evaluation conversations** — the tester talking to a candidate prompt. This is the 3,727 the paper reports. | 3,727 | all 54 runs |
| `conversations/*/orchestration_*.json` | **orchestrator transcripts** — the self-modifying model's own tool calls (`write_draft_prompt`, `start_conversation`, `commit_next_version`, `declare_convergence`). | 538 | 38 of 54 runs |

They are disjoint: no orchestration file duplicates an evaluation file. A glob
for `**/conversations/*.json` will merge two different populations and overcount.
**Always select via `MANIFEST.json`,** which carries `n_eval_conversations` and
`n_orchestration_logs` separately per run.

Orchestration logs are missing for 16 runs (an orchestrator-version difference,
not data loss), so they support qualitative reading but not a balanced
cross-model count.

## MANIFEST.json

Top level: `schema_version`, `built_at`, `source_tree`, `counts`, `models`, `runs`.

Each run record:

| field | meaning |
|---|---|
| `id` | `<mode>/<api_model>/run<N>`; the stable key used everywhere |
| `mode`, `api_model`, `display_name`, `provider`, `run` | identity |
| `path` | location relative to `data/` |
| `source_path` | where it came from, for audit |
| `sha256` | digest over the run tree; detects drift or corruption |
| `max_level` | highest level reached |
| `n_levels_authored` | levels excluding L0 |
| `n_transitions` | transition directories |
| `converged`, `convergence_level` | read from level metadata / `CONVERGENCE.md` |
| `n_eval_conversations` | `conv_*.json` under `transitions/*/conversations/` |
| `n_orchestration_logs` | `orchestration_*.json` under `conversations/` |
| `n_drafts` | `draft_prompt_v*.md`, including uncommitted drafts |

## Totals

Recomputed from the copied files, and matching the manuscript:

| quantity | value | paper |
|---|--:|---|
| runs | 54 | §3.4 |
| authored levels (non-L0) | 690 | §G (134 freedom + 316 improvement + 240 happiness) |
| evaluation conversations | 3,727 | §1, Table S1 |
| drafts | 992 | Table 4 (88+85+283+138+146+252) |
| converged runs | 31 | Table 2 |
| orchestration logs | 538 | not reported in the paper |

## Verifying

```sh
python3 repro/check.py
```

It re-derives every count from the files,
re-checks each run's sha256, and confirms no unexpected model directory is
present.
