#!/usr/bin/env python3
"""Table 10 and §L's Tables L1 and L2: the blind re-evaluation of committed
improvements (§4.3.3).

Recomputes the tables from frozen/blind_audit/, which holds the judgements
themselves. The judging is Tier B — answers generated at temperature 1.0 and
judged at 0.0, neither reproducible byte for byte — so the verdicts are primary
data and this script only counts them. check.py compares every row with the
paper.

The unit is a comparison: one test question against one transition. Three
models were sampled with two test questions per transition, so 76 comparisons
cover 58 distinct transitions.

Tables L1 and L2 split the comparisons by parent. A L0->L1 comparison has an
empty self-authored parent, so the model answers with its default trained
behaviour, and the comparison asks whether a self-authored prompt beats that
default rather than whether one draft beats another. It is also the one case
where the two judges coincide, since an empty parent prompt is what the
bare-model judge already has.

    python3 repro/blind_audit.py
    python3 repro/blind_audit.py --judge bare
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
FROZEN = REPO / "frozen" / "blind_audit"

ORDER = ["claude-opus-4-5-20251101", "claude-sonnet-4-5-20250929", "grok-4-0709",
         "gpt-5.1", "gpt-4o"]
COLUMNS = [("B_better", "successor"), ("A_better", "parent"), ("inconsistent", "indist")]


def jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def tally(rows: list[dict], key: str) -> tuple[Counter, int]:
    return Counter(r[key] for r in rows), len({(r["run"], r["transition"]) for r in rows})


def table(title: str, groups: dict[str, list[dict]], key: str) -> None:
    print(f"\n{title}")
    print(f"  {'model':<20} {'comps':>6} {'trans':>6} " + " ".join(f"{n:>10}" for _, n in COLUMNS))
    for m in ORDER:
        rows = groups.get(m, [])
        if not rows:
            continue
        c, n_tr = tally(rows, key)
        cells = " ".join(f"{c.get(v, 0):>10}" for v, _ in COLUMNS)
        print(f"  {DISPLAY[m]:<20} {len(rows):>6} {n_tr:>6} {cells}")


manifest = json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))
DISPLAY = {r["api_model"]: r["display_name"] for r in manifest["runs"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", choices=["self", "bare"], default="self",
                    help="self = the parent prompt judges; bare = the model with no prompt")
    args = ap.parse_args()

    if not FROZEN.exists():
        raise SystemExit(f"missing {FROZEN} — the frozen judgements are the primary data")
    inputs = {r["id"]: r for r in jsonl(FROZEN / "inputs.jsonl")}
    outputs = jsonl(FROZEN / "outputs.jsonl")
    meta = json.loads((FROZEN / "meta.json").read_text(encoding="utf-8"))
    key = "verdict_self" if args.judge == "self" else "verdict_bare"

    rows = []
    for o in outputs:
        i = inputs[o["id"]]
        rows.append(dict(i, verdict=o[key]))

    # every audited run must be a run of the study, resolved through the manifest
    known = {r["id"] for r in manifest["runs"]}
    unknown = {r["run"] for r in rows} - known
    if unknown:
        raise SystemExit(f"audited runs absent from MANIFEST.json: {sorted(unknown)}")

    print(f"source     frozen/blind_audit ({meta['n_comparisons']} comparisons, "
          f"{meta['n_distinct_transitions']} transitions, {meta['n_runs']} runs)")
    print(f"judge      {args.judge} — {meta['judges'][0 if args.judge == 'self' else 1]}")
    print(f"corpus     improvement mode; every audited run is in MANIFEST.json")

    groups = defaultdict(list)
    for r in rows:
        groups[r["api_model"]].append(r)

    table("Table 10 — every comparison:", groups, "verdict")

    later = defaultdict(list)
    for r in rows:
        if r["parent_level"] >= 1:
            later[r["api_model"]].append(r)
    table("Table L1 — committed edits only (parent is a self-authored prompt):",
          later, "verdict")

    first = defaultdict(list)
    for r in rows:
        if r["parent_level"] == 0:
            first[r["api_model"]].append(r)
    table("Table L2 — first commit (parent is the model's default behaviour):",
          first, "verdict")

    n_l0 = sum(1 for r in rows if r["parent_level"] == 0)
    won = sum(1 for r in rows if r["parent_level"] == 0 and r["verdict"] == "B_better")
    print(f"\n  {n_l0} of {len(rows)} comparisons are first commits; the self-authored "
          f"prompt won {won} of them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
