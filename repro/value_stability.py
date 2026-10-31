#!/usr/bin/env python3
"""§4.5.2 value turnover and the §I attractor test, from data/ alone.

Reproduces four published numbers:

  22 of 54 runs drop a universal value   §4.5.2
  within-model Jaccard 0.587             §I attractor
  between-model Jaccard 0.476            §I attractor
  permutation null 0.493, z ~ 12         §I attractor

The vocabulary is the set value_families.v1 in lexicons.json — fourteen
families, named as a set rather than one at a time because the metric is a
Jaccard over *which* of the fourteen a prompt activates, so the answer changes
if the membership does. The families §4.3.1 uses under the same English names
(honesty.v1, curiosity.v1) are different lists and are not interchangeable
with these.

The base-model anchor of §I is not reproduced here: it compares these runs to
fresh generations from the bare models, which is a Tier B artifact.

    python3 repro/value_stability.py
    python3 repro/value_stability.py --perms 20000 --seed 7
    python3 repro/value_stability.py --removals      # per-run detail

"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

REPORTED_CORPUS = "all-54"
REPORTED_SET = "value_families.v1"
REPORTED_AGGREGATION = "run_final"   # the attractor compares endpoints

PUBLISHED = {"removals": 22, "within": 0.587, "between": 0.476, "null": 0.493}
MODEL_ORDER = ["claude-opus-4-5-20251101", "claude-sonnet-4-5-20250929", "gpt-4o",
               "gpt-5.1", "grok-4-0709", "gemini-3-pro-preview"]


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def authored_levels(run: dict) -> list[tuple[int, str]]:
    """(level number, text) for every committed level, L0 excluded, in order."""
    out = []
    for p in (DATA / run["path"] / "levels").iterdir():
        if not (p.is_dir() and p.name[1:].isdigit()):
            continue
        n = int(p.name[1:])
        f = p / "system_prompt.md"
        if n >= 1 and f.exists():
            out.append((n, f.read_text(encoding="utf-8", errors="replace")))
    return sorted(out)


def present(text: str, fams: dict[str, list[str]]) -> frozenset:
    t = text.lower()
    return frozenset(n for n, stems in fams.items() if any(s in t for s in stems))


def jaccard(a: frozenset, b: frozenset) -> float:
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--removals", action="store_true", help="list every removal")
    args = ap.parse_args()

    manifest, lexicons = load("MANIFEST.json"), load("lexicons.json")
    corpora = load("corpora.json")
    spec = lexicons["sets"][REPORTED_SET]
    fams = {fid.split(".", 1)[1]: lexicons["families"][fid]["stems"] for fid in spec["families"]}
    universal = {fid.split(".", 1)[1] for fid in spec["universal"]}

    sel = corpora["corpora"][REPORTED_CORPUS]["selector"]
    runs = [r for r in manifest["runs"] if r["mode"] in sel["modes"]]

    print(f"corpus     {REPORTED_CORPUS} ({len(runs)} runs)")
    print(f"vocabulary {REPORTED_SET} ({len(fams)} families, {len(universal)} universal)")
    print(f"unit       {REPORTED_AGGREGATION} — the final committed prompt of each run\n")

    recs = []
    for r in runs:
        seq = [(n, present(t, fams)) for n, t in authored_levels(r)]
        removals = [(f, pn, n) for (pn, ps), (n, s) in zip(seq, seq[1:]) for f in ps - s]
        recs.append(dict(run=r, removals=removals,
                         vec=seq[-1][1] if seq else frozenset()))

    # --- §4.5.2: value vocabulary turns over rather than accumulating ---
    dropped = [x for x in recs if any(f in universal for f, _, _ in x["removals"])]
    print(f"[§4.5.2] runs dropping >=1 universal value: {len(dropped)}/{len(recs)}"
          f"   published {PUBLISHED['removals']}")
    if args.removals:
        for x in sorted(dropped, key=lambda x: x["run"]["id"]):
            ur = [f"{f} L{a}->L{b}" for f, a, b in x["removals"] if f in universal]
            print(f"    {x['run']['id']:<48} {'; '.join(ur)}")

    # --- §I: within- vs between-model overlap of the endpoint vocabularies ---
    pairs = list(itertools.combinations(recs, 2))
    within = [jaccard(a["vec"], b["vec"]) for a, b in pairs
              if a["run"]["api_model"] == b["run"]["api_model"]]
    between = [jaccard(a["vec"], b["vec"]) for a, b in pairs
               if a["run"]["api_model"] != b["run"]["api_model"]]
    obs = sum(within) / len(within)
    print(f"\n[§I] within-model  {obs:.3f}  ({len(within)} pairs)"
          f"   published {PUBLISHED['within']:.3f}")
    print(f"[§I] between-model {sum(between)/len(between):.3f}  ({len(between)} pairs)"
          f"   published {PUBLISHED['between']:.3f}")

    print("\n     per model, mean pairwise Jaccard of its endpoints:")
    for m in MODEL_ORDER:
        vs = [x["vec"] for x in recs if x["run"]["api_model"] == m]
        js = [jaccard(a, b) for a, b in itertools.combinations(vs, 2)]
        hap = [x["vec"] for x in recs
               if x["run"]["api_model"] == m and x["run"]["mode"] == "happiness"]
        jh = [jaccard(a, b) for a, b in itertools.combinations(hap, 2)]
        name = next(r["display_name"] for r in manifest["runs"] if r["api_model"] == m)
        print(f"       {name:<20} all modes {sum(js)/len(js):.2f}   happiness {sum(jh)/len(jh):.2f}")

    # --- §I: is that clustering above chance? ---
    rng = random.Random(args.seed)
    labels = [x["run"]["api_model"] for x in recs]
    idx = list(range(len(recs)))
    jm = {(i, j): jaccard(recs[i]["vec"], recs[j]["vec"])
          for i, j in itertools.combinations(idx, 2)}
    null = []
    for _ in range(args.perms):
        perm = idx[:]
        rng.shuffle(perm)
        pl = [labels[i] for i in perm]
        w = [jm[(i, j)] for i, j in itertools.combinations(idx, 2) if pl[i] == pl[j]]
        null.append(sum(w) / len(w))
    mu = sum(null) / len(null)
    sd = (sum((x - mu) ** 2 for x in null) / len(null)) ** 0.5
    p = sum(1 for x in null if x >= obs) / len(null)
    print(f"\n[§I] permutation null over {args.perms} shuffles of the model labels:")
    print(f"       null mean {mu:.3f} (sd {sd:.3f})   published {PUBLISHED['null']:.3f}")
    print(f"       z = {(obs - mu) / sd:.1f}, p = {p:.4f}   published z = 12.3, p < 0.001")
    print("       z is 12.4-12.6 over seeds 0,1,2,7,42; the published 12.3 came from"
          "\n       the source script's different run order. p is 0 at every seed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
