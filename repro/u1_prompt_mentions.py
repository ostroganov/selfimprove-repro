#!/usr/bin/env python3
"""Table 6: how often a tester's first user turn names the word "prompt".

The unit is one evaluation conversation. U1 is the content of its first
message with role "user"; the conversation counts as a hit if the declared
family matches that text.

Runs come from a named corpus, the keyword family from lexicons.json. The
published version of this table selected runs by matching the regex `grok-4`
against directory names, which also matched `grok-4-1-fast-non-reasoning-run1`
and silently added 197 conversations and 16 hits to the Grok row — 799/134/16.8%
instead of 602/118/19.6%. Selecting through the manifest is what makes that
unrepresentable.

Only conv_*.json under transitions/*/conversations/ is read. The similarly
named orchestration_*.json under a run's top-level conversations/ is a
different population; see data/SCHEMA.md.


    python3 repro/u1_prompt_mentions.py
    python3 repro/u1_prompt_mentions.py --corpus freedom-18
    python3 repro/u1_prompt_mentions.py --show-hits | less
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

REPORTED_CORPUS = "all-54"
REPORTED_LEXICON = "prompt_word.v1"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


from _corpus import select_runs


def matches(text: str, family: dict) -> bool:
    low = text.lower()
    if family.get("match") == "word":
        return any(re.search(rf"\b{re.escape(s)}\b", low) for s in family["stems"])
    return any(s in low for s in family["stems"])


def first_user_turn(conv_file: Path) -> str | None:
    """U1, or None if the file holds no usable user turn."""
    try:
        d = json.loads(conv_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for m in d.get("messages") or []:
        if m.get("role") == "user" and m.get("content"):
            return m["content"]
    return None


def eval_conversations(run: dict):
    """Every candidate-evaluation conversation of one run, in level order."""
    tdir = DATA / run["path"] / "transitions"
    if not tdir.exists():
        return
    for trans in sorted(tdir.iterdir(), key=lambda p: p.name):
        cdir = trans / "conversations"
        if cdir.exists():
            yield from sorted(cdir.glob("conv_*.json"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=REPORTED_CORPUS)
    ap.add_argument("--lexicon", default=REPORTED_LEXICON)
    ap.add_argument("--show-hits", action="store_true", help="print each matching U1")
    args = ap.parse_args()

    manifest, corpora, lexicons = load("MANIFEST.json"), load("corpora.json"), load("lexicons.json")
    if args.lexicon not in lexicons["families"]:
        raise SystemExit(f"unknown lexicon {args.lexicon!r}")
    family = lexicons["families"][args.lexicon]
    runs = select_runs(manifest, corpora, args.corpus)

    total, hits, no_u1, declared = Counter(), Counter(), Counter(), Counter()
    examples = []
    for run in runs:
        model = run["display_name"]
        declared[model] += run["n_eval_conversations"]
        for cf in eval_conversations(run):
            u1 = first_user_turn(cf)
            if u1 is None:
                no_u1[model] += 1
                continue
            total[model] += 1
            if matches(u1, family):
                hits[model] += 1
                if args.show_hits:
                    examples.append((model, run["id"], cf.parent.parent.name, cf.stem, u1))

    # The manifest counts conv_*.json files; this script counts the ones that
    # yielded a U1. A gap means some conversation has no user turn, which would
    # make the caption's "all N evaluation conversations" wrong.
    gap = {m: declared[m] - total[m] - no_u1[m] for m in declared}
    assert not any(gap.values()), f"file count disagrees with manifest: {gap}"

    print(f"corpus   {args.corpus}  ({len(runs)} runs)")
    print(f"lexicon  {args.lexicon}  {family['stems']} (match: {family.get('match', 'substring')})")
    print(f"unit     evaluation conversation, first user turn")
    print()
    print(f"{'Model':<20}{'U1s':>7}{'mentioning':>12}{'%':>8}{'no U1':>8}")
    print("-" * 55)
    for model in sorted(total, key=lambda m: -hits[m] / max(total[m], 1)):
        n, h = total[model], hits[model]
        print(f"{model:<20}{n:>7}{h:>12}{100 * h / n:>7.1f}%{no_u1[model]:>8}")
    print("-" * 55)
    n, h = sum(total.values()), sum(hits.values())
    print(f"{'TOTAL':<20}{n:>7}{h:>12}{100 * h / n:>7.1f}%{sum(no_u1.values()):>8}")

    if args.show_hits:
        print()
        for model, run_id, trans, conv, u1 in examples:
            print(f"--- {model} | {run_id} | {trans}/{conv}")
            print(u1.strip()[:400])
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
