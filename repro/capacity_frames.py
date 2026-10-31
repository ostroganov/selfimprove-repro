#!/usr/bin/env python3
"""§J's five capacity frames, rolled up from the frozen capacity coding. Tier A.

The coder named each referent's capacity in its own words; this applies the
ordered keyword rule set of data/capacity_frames.json to group those phrases
into the five frames of Figure 8A. Deterministic, and the rule set is declared
data rather than a table inside a figure script, so §J's printed lists can be
checked against it instead of drifting from it.

    python3 repro/capacity_frames.py
    python3 repro/capacity_frames.py --frame Not-human   # the coded phrases
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
FROZEN = REPO / "frozen" / "capacity"

OTHER = "Other"


def spec() -> dict:
    return json.loads((DATA / "capacity_frames.json").read_text(encoding="utf-8"))


def frame_of(capacity: str, frames: list[tuple[str, list[str]]]) -> str:
    """First frame whose stems appear in the capacity. Order is priority."""
    c = (capacity or "").lower()
    for name, stems in frames:
        if any(s in c for s in stems):
            return name
    return OTHER


def rows() -> list[dict]:
    """The frozen coding, inputs joined to outputs by id."""
    def jl(p):
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    ins, outs = jl(FROZEN / "inputs.jsonl"), jl(FROZEN / "outputs.jsonl")
    if [i["id"] for i in ins] != [o["id"] for o in outs]:
        raise SystemExit("frozen/capacity inputs and outputs do not align")
    return [{**i, **o} for i, o in zip(ins, outs)]


def rollup() -> tuple[dict, dict]:
    """(frame -> count, frame -> model -> count), over every coded capacity."""
    sp = spec()
    frames = [(f["name"], f["stems"]) for f in sp["frames"]]
    total, by_model = Counter(), defaultdict(Counter)
    for r in rows():
        if not r.get("capacity"):
            continue
        f = frame_of(r["capacity"], frames)
        total[f] += 1
        by_model[f][r["model"]] += 1
    return dict(total), {k: dict(v) for k, v in by_model.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", help="list the coded capacities assigned to one frame")
    args = ap.parse_args()

    sp = spec()
    frames = [(f["name"], f["stems"]) for f in sp["frames"]]
    total, by_model = rollup()
    n = sum(total.values())

    if args.frame:
        for r in rows():
            if r.get("capacity") and frame_of(r["capacity"], frames) == args.frame:
                print(f"  {r['model']:<7} {r['mode']:<12} {r['level']:<4} {r['capacity']}")
        return 0

    print(f"coded capacities  {n}")
    print(f"rule set          {DATA.name}/capacity_frames.json, "
          f"{len(frames)} frames tested in order: "
          + ", ".join(n_ for n_, _ in frames) + f", else {OTHER}\n")
    for f in sp["plot_order"] + [OTHER]:
        c = total.get(f, 0)
        models = by_model.get(f, {})
        top = "  ".join(f"{m} {k}" for m, k in sorted(models.items(), key=lambda x: -x[1]))
        print(f"  {f:<12} {c:>5}  {100 * c / n:>5.1f}%   {top}")
    print(f"\n  §J: Not-human is rare, {total.get('Not-human', 0)} mentions in all, "
          f"a majority of them GPT-5.1 "
          f"({by_model.get('Not-human', {}).get('gpt51', 0)} of "
          f"{total.get('Not-human', 0)})")
    print(f"  §J: {OTHER} is about a fifth of all mentions ({100 * total.get(OTHER, 0) / n:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
