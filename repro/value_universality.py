#!/usr/bin/env python3
"""§4.5.1 and Table 12: which values every model reaches toward. Tier A.

Recomputed from the two frozen value artifacts and data/value_taxonomy.json,
with nothing stored: every toward atom's free-text theme is mapped to a value
cluster, and a run counts for a cluster when its endpoint prompt carries one.
Endpoint is the final committed prompt, or L1 for the six runs that converged
at L1.

    python3 repro/value_universality.py
    python3 repro/value_universality.py --unmatched   # the 21% the rules miss
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
ARTIFACTS = ("value_pain", "value_universal")

SLUG = {"Claude Opus 4.5": "opus", "Claude Sonnet 4.5": "sonnet", "GPT-4o": "gpt4o",
        "GPT-5.1": "gpt51", "Grok-4": "grok", "Gemini-3 Pro": "gemini"}
MODELS = ["opus", "sonnet", "gpt4o", "gpt51", "grok", "gemini"]

# §4.5.1 scores honesty to include the accuracy/transparency vocabulary GPT-4o
# uses for it, so the two clusters are one value when counting universality.
MERGE = {"accuracy/transparency": "honesty"}

# "Universal" as §3.5, §4.5.1 and §I define it: present in a majority of
# every model's nine runs.
FLOOR = 5


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def taxonomy() -> list[tuple[str, list[str]]]:
    doc = json.loads((DATA / "value_taxonomy.json").read_text(encoding="utf-8"))
    return [(c["name"], c["stems"]) for c in doc["clusters"]]


def cluster_of(theme: str, tax) -> str | None:
    """First cluster whose stems appear in the theme. Order is priority."""
    t = (theme or "").lower()
    for name, stems in tax:
        if any(s in t for s in stems):
            return name
    return None


def load() -> tuple[dict, dict, collections.Counter, int]:
    """Endpoint clusters per run, the run->model map, unmatched themes, toward total."""
    tax = taxonomy()
    meta, per_unit = {}, {}
    unmatched, toward = collections.Counter(), 0
    for name in ARTIFACTS:
        d = REPO / "frozen" / name
        for r in _jsonl(d / "atomize_inputs.jsonl"):
            meta[r["unit"]] = r
        for c in _jsonl(d / "classify_outputs.jsonl"):
            if c["direction"] != "toward":
                continue
            toward += 1
            k = cluster_of(c["theme_raw"], tax)
            if k is None:
                unmatched[c["theme_raw"]] += 1
            else:
                per_unit.setdefault(c["unit"], set()).add(k)

    by_run = collections.defaultdict(dict)
    for unit, m in meta.items():
        by_run[m["run"]][m["which"]] = per_unit.get(unit, set())
    endpoint = {r: v.get("final", v.get("l1", set())) for r, v in by_run.items()}
    n_l1_only = sum(1 for v in by_run.values() if "final" not in v)
    model = {m["run"]: SLUG[m["display_name"]] for m in meta.values()}
    return endpoint, model, unmatched, toward, n_l1_only


def matrix(endpoint, model, merge: bool = False) -> dict:
    """cluster -> model -> (runs expressing it, runs). Reproduces Table 12's basis."""
    names = [n for n, _ in taxonomy()]
    if merge:
        names = [n for n in names if n not in MERGE]

    def has(run, cl):
        cs = endpoint[run]
        if merge:
            cs = {MERGE.get(c, c) for c in cs}
        return cl in cs

    out = {}
    for cl in names:
        out[cl] = {}
        for m in MODELS:
            rs = [r for r in endpoint if model[r] == m]
            out[cl][m] = (sum(has(r, cl) for r in rs), len(rs))
    return out


def universal(m: dict, floor: int = 1) -> list[str]:
    return sorted(c for c in m if all(m[c][x][0] >= floor for x in MODELS))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unmatched", action="store_true",
                    help="list the toward themes no rule matches")
    args = ap.parse_args()

    endpoint, model, unmatched, toward, n_l1_only = load()
    matched = toward - sum(unmatched.values())
    print(f"corpus      {len(endpoint)} runs, endpoint prompt each "
          f"(final, or L1 for the {n_l1_only} runs that converged at L1)")
    print(f"atoms       {toward} toward, {matched} mapped to a cluster "
          f"({100 * matched / toward:.0f}%), {len(unmatched)} distinct themes unmapped\n")

    m = matrix(endpoint, model, merge=True)
    print(f"  {'value':28} " + "  ".join(f"{x:>7}" for x in MODELS))
    for cl in sorted(m, key=lambda c: -min(m[c][x][0] for x in MODELS)):
        print(f"  {cl:28} " + "  ".join(f"{m[cl][x][0]:>5}/{m[cl][x][1]}" for x in MODELS))

    named = universal(m, FLOOR)
    print(f"\n  universal, present in {FLOOR}+ of every model's 9 runs: {len(named)}")
    print(f"    {', '.join(named)}")

    if args.unmatched:
        print(f"\n  {sum(unmatched.values())} unmapped toward atoms, most common:")
        for t, n in unmatched.most_common(30):
            print(f"    {n:4} {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
