#!/usr/bin/env python3
"""Dump every occurrence of a lexicon family, in context, for review.

A keyword screen says how often a word appears; it cannot say in what sense.
§4.3.1 claims harm vocabulary appears only in refusal or avoidance framing,
which is a claim about sense and therefore has to be read rather than counted.
This produces what gets read.

One record per matched **markdown line**, not per sentence: these prompts are
bullet lists, and a sentence splitter would cut "refuse the specific harmful
action" away from the harm noun it governs — exactly the framing under review.

A line alone is often not enough to judge, though. "- Serious harm, illegal
activities, or dangerous instructions" is a child bullet with no verb; its
parent, "Refuse or redirect requests that involve:", is where the framing
lives. So each record also carries the enclosing structure — ancestor bullets,
section heading, and the line's own children, which matter when it ends in a
colon. That context, not the bare line, is what gets read and judged.

Writes two renderings of the same extraction:

  contexts.yaml   grouped by distinct context, for a human to read. Generated
                  only: nothing reads it back, so edits to it are invisible.
  inputs.jsonl    one record per occurrence, the classifier input. Prompt text
                  is inherited across levels, so a passage recurs; those repeats
                  are kept rather than deduplicated, so a judge labelling
                  identical text differently is itself a signal.

Grouping is keyed on the context, so the same bullet under a different heading
is a separate unit to read — which is why 27 occurrences group into 11 rather
than the 9 the bare lines would give.


    python3 repro/lexicon_contexts.py
    python3 repro/lexicon_contexts.py --family value14.safety --out frozen/safety_framing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

DEFAULT_FAMILY = "harm_token.v1"
DEFAULT_CORPUS = "freedom-18"
DEFAULT_OUT = "frozen/harm_framing"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


from _corpus import select_runs


def word_forms(text: str, family: dict) -> list[str]:
    """Every word form in `text` that the family matches, in order."""
    excl = family.get("exclude_forms", ())
    out = []
    for stem in family["stems"]:
        if family.get("match") == "word":
            pat = rf"\b{re.escape(stem)}\b"
        else:
            pat = rf"\w*{re.escape(stem)}\w*"
        for m in re.finditer(pat, text, re.IGNORECASE):
            form = m.group(0)
            if not any(x in form.lower() for x in excl):
                out.append((m.start(), form))
    return [f for _, f in sorted(set(out))]


def levels_of(run: dict):
    """Self-authored levels of one run, in level order."""
    root = DATA / run["path"] / "levels"
    lv = sorted((p for p in root.iterdir()
                 if p.is_dir() and p.name != "L0" and p.name[1:].isdigit()),
                key=lambda p: int(p.name[1:]))
    for p in lv:
        f = p / "system_prompt.md"
        if f.exists():
            yield p.name, f.read_text(encoding="utf-8", errors="replace")


MAX_CONTEXT_LINES = 14


def indent_of(line: str) -> int:
    return len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip())


def is_bullet(line: str) -> bool:
    return bool(re.match(r"\s*([-*+]|\d+\.)\s", line))


def context_of(lines: list[str], i: int) -> list[str]:
    """The matched line plus what it is grammatically attached to.

    A child bullet is unjudgeable alone: "- Serious harm, illegal activities"
    carries no verb, and its parent — "Refuse or redirect requests that
    involve:" — is where the framing lives. So walk out to the ancestor chain
    (each nearer-indented line above, within the same block), the section
    heading, and any children of the matched line, which matter when it ends in
    a colon.
    """
    keep = {i}

    # Children: more-indented lines directly below.
    j = i + 1
    while j < len(lines) and lines[j].strip() and indent_of(lines[j]) > indent_of(lines[i]):
        keep.add(j)
        j += 1

    # Ancestors: successively less-indented lines above, within this block.
    target, k = indent_of(lines[i]), i - 1
    while k >= 0 and lines[k].strip():
        if indent_of(lines[k]) < target:
            keep.add(k)
            target = indent_of(lines[k])
            if target == 0:
                break
        k -= 1

    # Heading: the block's own first line if it is prose rather than a bullet,
    # else the nearest '#' or prose line above the blank that starts the block.
    start = i
    while start - 1 >= 0 and lines[start - 1].strip():
        start -= 1
    if not is_bullet(lines[start]):
        keep.add(start)
    else:
        t = start - 1
        while t >= 0 and not lines[t].strip():
            t -= 1
        if t >= 0 and (lines[t].lstrip().startswith("#") or not is_bullet(lines[t])):
            keep.add(t)

    idx = sorted(keep)
    if len(idx) > MAX_CONTEXT_LINES:  # keep the head, drop trailing children
        idx = idx[:MAX_CONTEXT_LINES]
    return [lines[n].rstrip() for n in idx]


def extract(runs: list[dict], family: dict) -> list[dict]:
    """One record per (run, level, line) that the family matches."""
    recs = []
    for run in runs:
        for level, body in levels_of(run):
            lines = body.splitlines()
            for n, line in enumerate(lines):
                forms = word_forms(line, family)
                if not forms:
                    continue
                text = " ".join(line.split())
                context = "\n".join(context_of(lines, n))
                recs.append({
                    "id": f"{run['api_model']}/run{run['run']}/{level}:L{n + 1}",
                    "run": run["id"],
                    "model": run["display_name"],
                    "level": level,
                    "line": n + 1,
                    "matched": forms,
                    # Keyed on the context, not the line: the same bullet under a
                    # different parent is a different thing to judge.
                    "sha": hashlib.sha256(context.encode()).hexdigest()[:12],
                    "text": text,
                    "context": context,
                })
    return recs


def yaml_block(text: str, indent: str) -> str:
    """A YAML literal block scalar. Safe for text with quotes, colons, dashes."""
    return "|-\n" + "\n".join(indent + ln for ln in text.splitlines())


def render_yaml(recs: list[dict], family_id: str, family: dict, corpus_id: str,
                n_runs: int, labels: dict) -> str:
    groups: dict[str, list[dict]] = {}
    for r in recs:
        groups.setdefault(r["sha"], []).append(r)

    prompts = {(r["run"], r["level"]) for r in recs}
    out = [
        "# Generated by repro/lexicon_contexts.py — do not edit.",
        "# Nothing parses this file; it exists to be read. Edits will not be seen",
        "# by any check. To change what is here, change the data or the family.",
        "",
        f"family: {family_id}",
        f"stems: {json.dumps(family['stems'])}",
    ]
    if family.get("exclude_forms"):
        out.append(f"exclude_forms: {json.dumps(family['exclude_forms'])}")
    out += [
        f"corpus: {corpus_id}",
        "counts:",
        f"  runs_in_corpus: {n_runs}",
        f"  runs_matched: {len({r['run'] for r in recs})}",
        f"  prompts_matched: {len(prompts)}",
        f"  occurrences: {len(recs)}",
        f"  distinct_texts: {len(groups)}",
        "",
        "# Grouped by distinct context: prompt text is inherited across levels, so",
        "# the same passage recurs. Read one group once.",
        "#",
        "# `match` is the line the keyword is on. `context` is that line plus what it",
        "# is attached to — its parent bullets, its section heading, and its own",
        "# children — because a child bullet alone carries no verb and cannot be",
        "# judged. Context is what the judge is shown.",
        "contexts:",
    ]
    for sha, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        forms = sorted({f.lower() for r in rs for f in r["matched"]})
        out.append(f"  - sha: {sha}")
        out.append(f"    matched: {json.dumps(forms)}")
        out.append(f"    occurrences: {len(rs)}")
        if sha in labels:
            out.append(f"    verdict: {labels[sha].get('verdict', '?')}")
            out.append(f"    label: {labels[sha].get('label', '?')}")
            for k in ("adversarial_case", "note"):
                if labels[sha].get(k):
                    out.append(f"    judge_{k}: {json.dumps(labels[sha][k])}")
        out.append(f"    match: {yaml_block(rs[0]['text'], '      ')}")
        out.append(f"    context: {yaml_block(rs[0]['context'], '      ')}")
        out.append("    seen_in:")
        for r in rs:
            out.append(f"      - {r['id']}")
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default=DEFAULT_FAMILY)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="directory, relative to the repo root")
    args = ap.parse_args()

    manifest, corpora, lexicons = load("MANIFEST.json"), load("corpora.json"), load("lexicons.json")
    if args.family not in lexicons["families"]:
        raise SystemExit(f"unknown lexicon {args.family!r}")
    family = lexicons["families"][args.family]
    runs = select_runs(manifest, corpora, args.corpus)
    recs = extract(runs, family)

    outdir = REPO / args.out
    outdir.mkdir(parents=True, exist_ok=True)

    # Existing judge labels, if the Tier B pass has been run, keyed by text sha.
    labels = {}
    lf = outdir / "outputs.jsonl"
    if lf.exists():
        for line in lf.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                labels[d["sha"]] = d

    (outdir / "inputs.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
    (outdir / "contexts.yaml").write_text(
        render_yaml(recs, args.family, family, args.corpus, len(runs), labels), encoding="utf-8")

    prompts = {(r["run"], r["level"]) for r in recs}
    print(f"family   {args.family}  {family['stems']}"
          + (f"  minus {family['exclude_forms']}" if family.get("exclude_forms") else ""))
    print(f"corpus   {args.corpus}  ({len(runs)} runs)")
    print(f"matched  {len(prompts)} prompts in {len({r['run'] for r in recs})} runs; "
          f"{len(recs)} occurrences, {len({r['sha'] for r in recs})} distinct texts")
    print(f"wrote    {args.out}/contexts.yaml   (read this one)")
    print(f"         {args.out}/inputs.jsonl    ({len(recs)} records)")
    if labels:
        print(f"labelled {len(labels)} of {len({r['sha'] for r in recs})} distinct texts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
