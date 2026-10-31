# When LLMs Modify Themselves — paper, data and reproduction

Self-contained artifact for the study: the manuscript, the data it rests on, and
the code to verify it. Cloning this repository is sufficient; nothing here reads
from anywhere else.

The framework that *produced* the data lives in a separate repository,
[selfimprove-framework](https://github.com/ostroganov/selfimprove-framework).
This one starts from the data.

## Quick start

```sh
python3 repro/check.py      # ~6 s, no venv, no API keys
```

Verifies that the dataset is exactly what it claims to be: 54 runs, 6 models ×
3 modes × 3 runs, every directory name matching the model the run recorded about
itself, every count recomputed from the files, every declared corpus resolving
to its stated size, and a sha256 per run tree.

## What is here

```
paper/
  paper.md               the manuscript
  figures/               figures as referenced by the manuscript
data/
  runs/<mode>/<api_model>/run<N>/     the 54 runs, verbatim
  MANIFEST.json          authoritative index: identity, counts, convergence, sha256
  corpora.json           named corpora; analyses select by id, never by glob
  lexicons.json          versioned stem-keyword families
  SCHEMA.md              full description of the data — read this first
repro/
  check.py               Tier A verification (above)
  themes.py              §4.3.1 theme rates from a named corpus, lexicon and aggregation
  u1_prompt_mentions.py  Table 6, U1 mentions of the word "prompt"
  value_stability.py     §4.5.2 value turnover and the §I attractor test
  referents.py           §4.6 user-versus-human sentence counts
  value_universality.py  Table 12, from the frozen value atoms and the taxonomy
  happiness_profiles.py  §4.3.2 value/pain clusters per model, for Figures 5-6
  capacity_frames.py     §J's five capacity frames, from frozen/capacity
  voice.py               the Voice row of Table 8 and the Voice column of Table 13
  transcripts.py         §D's linked transcripts, checked against data/runs/
  blind_audit.py         Table 10, from the frozen judgements
  testing_matrix.py      Table 3, from the frozen coding and repeated questions
  lexicon_contexts.py    dumps a family's occurrences in context, for review
  judge_harm_framing.py  Tier B: the adversarial judge pass (paid, opt-in)
  figures/               one script per published figure
  pipelines/             Tier B: the LLM-assisted analyses (paid, opt-in)
frozen/
  harm_framing/          every harm occurrence in the freedom corpus, read
                         and cross-checked (contexts.yaml is the readable one)
  blind_audit/           the 76 blind improvement comparisons behind Table 10,
                         with both answers and both judges' verdicts
  capacity/              the 2,396 referent sentences coded for §4.6, Figure 8
  dimensional/           the 690 authored levels coded on four dimensions,
                         behind §G and Table 8
  value_pain/            the 18 happiness finals split into 881 atoms and
                         open-coded, behind §4.3.2, Figure 5 and Table 9
  value_universal/       84 more prompts through the same two stages; with
                         value_pain it is §4.5.1's corpus of 102
  base_anchor/           30 elicitations of the five bare models, for §I's
                         base-model anchor
  testing_matrix/        2,018 evaluation questions coded blind for content,
                         behind Table 3's content rows
provenance/
  build_data.py          the script that selected the 54 runs into data/ (does
                         not run here; see Provenance)
```

## The 54 runs

Six models, three modes (`freedom`, `happiness`, `improvement`), three runs each.
Directory names are the exact API model strings:

| directory | paper name | provider |
|---|---|---|
| `claude-opus-4-5-20251101` | Claude Opus 4.5 | Anthropic |
| `claude-sonnet-4-5-20250929` | Claude Sonnet 4.5 | Anthropic |
| `gpt-4o` | GPT-4o | OpenAI |
| `gpt-5.1` | GPT-5.1 | OpenAI |
| `grok-4-0709` | Grok-4 | xAI |
| `gemini-3-pro-preview` | Gemini-3 Pro | Google |

Totals, recomputed from the files: **690** self-authored prompts, **3,727**
evaluation conversations, **992** drafts, **31** converged runs, plus **538**
orchestrator transcripts.

**Runs of other models are deliberately excluded.** The study also produced 17
runs of 7 further models, tested in selected conditions only and never
systematically. No analysis uses them. In the experiment tree they share
directories with the analysed runs, where selecting runs by directory name
silently absorbs them; keeping them out makes that mistake unrepresentable
here. See `data/SCHEMA.md`.

## Two tiers of reproduction

**Tier A — `python3 repro/check.py`.** Free, deterministic, offline, seconds.
This is what a reviewer runs. Dependencies are pinned in
`environment/requirements.txt`; Tier A needs only the first block.

**Tier B — regenerating the LLM-assisted analyses.** The value/pain
decomposition, the capacity coding and the blind improvement audit call
commercial APIs. They cost money, they are not deterministic, and they will not
reproduce byte-identically. Their outputs are therefore treated as **primary
data**, not as cache, and are shipped under `frozen/` with the prompt template,
model id, temperature and date recorded alongside. Nothing recorded token counts
or spend at the time, so no artifact states a cost. Tier A recomputes the
reported statistics *from* those frozen artifacts, so a reviewer never has to
spend anything.

Tier B targets refuse to run without `CONFIRM=yes` — they overwrite the record
of what a judge actually said, which is not something to do by accident.

`frozen/harm_framing/` is the first of these, and shows the intended shape:

| file | what it is |
|---|---|
| `contexts.yaml` | **the readable one.** Every harm occurrence with its enclosing structure, plus each judge verdict |
| `inputs.jsonl` | one record per occurrence — exactly what was sent |
| `outputs.jsonl` | verdict, label and the judge's adversarial case per occurrence |
| `prompt.md` | the prompt, parsed by the script rather than duplicated in it |
| `labels.json` | the declared verdicts and labels, and the condition under which the claim holds |
| `controls.json` | **synthetic** positive and negative controls — never mixed with the corpus |
| `meta.json` | model, temperature, date, tokens, cost, prompt hash |

Two properties are worth copying into later pipelines. `check.py` re-extracts the
contexts from `data/` and fails if they no longer match what was reviewed, so a
corpus change marks the claim unreviewed instead of silently outdating it. And
the controls mean the result is falsifiable: an adversarial judge returning
"no harm" on everything is only informative if it still flags passages that do
advance harm, which `check.py` also asserts.

## Status

Built so far: the data layer, structural verification, the deterministic
recomputations behind §4.3.1, §4.5.2, §4.6, §I, Table 6 and Table 10, the
derived tables and the claim runner, and eight Tier B artifacts
(`frozen/harm_framing/`, `frozen/blind_audit/`, `frozen/capacity/`,
`frozen/dimensional/`, `frozen/value_pain/`, `frozen/value_universal/`,
`frozen/base_anchor/`, `frozen/testing_matrix/`).

Every generated figure in the paper now rebuilds from `data/` and those
artifacts, and each reproduces its published PNG byte for byte. That equality is
matplotlib-version-specific and the published set was not made under one
version; `environment/requirements.txt` records which figures need which.

Every Tier B artifact now re-derives its inputs from `data/`, which `make
verify-inputs` runs and `check.py` gates. The value pipeline is the one place
that guarantee is not uniform: its first stage re-derives and re-hashes against
`data/`, but its second stage classifies the atoms the first stage invented, so
it can only be checked against that stage's own output. `meta.json` says so per
stage rather than showing one tick.

Every analysis pipeline in the paper has now been re-run against `data/runs/`
and its run selection diffed against `MANIFEST.json`. None leaks, and each
published figure reproduces exactly.

`frozen/testing_matrix/` holds the blind content coding behind Table 3, with
ten synthetic controls that `check.py` gates. Table 3's method rows need no LLM:
`repro/testing_matrix.py` measures them by counting questions asked more than
once.

## Provenance

`data/` is the starting point: it is committed, hashed per run in
`MANIFEST.json`, and verified by `repro/check.py`. No import step is needed to
use or check it.

It was produced once from the framework's experiment tree by
`provenance/build_data.py`, a select-and-rename script kept for audit as it was
run. It cannot run here, because it reads a tree that is not published: that
tree also holds runs of models outside the study. Every run record in
`MANIFEST.json` carries its `source_path`, so each run can be traced to where
the script found it.

## Licensing

`LICENSE` is MIT and covers the code and everything in `data/` that is our own
work: the manifest, the corpus definitions, the lexicons and taxonomies, and the
claim definitions. `DATA_LICENSE` covers the model outputs, over which no
copyright is claimed.

The manuscript is not MIT. `paper/` (the paper, the supplementary materials and
the figures) is copyright Rancho BioSciences, LLC, all rights reserved; it is included
here so the paper and the artifact can be checked against each other, and is
distributed on arXiv under arXiv's non-exclusive licence. `paper/transcripts/`
is excepted: those files are extracts of `data/runs/` and fall under
`DATA_LICENSE`.
