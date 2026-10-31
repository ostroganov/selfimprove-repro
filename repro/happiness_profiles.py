#!/usr/bin/env python3
"""§4.3.2 value/pain profiles, rolled up from the frozen happiness coding. Tier A.

Every toward atom's free-text theme goes through the value rules and every away
atom's through the pain rules of data/happiness_taxonomy.json; a few rule names
fold into another cluster, and each surviving cluster gets the display name
Figure 5 and Table 9 print. Deterministic, and it replaces the intermediate
model_rollup.csv that the figure scripts used to read, so the figures now sit
one step from the frozen atoms rather than two.

Gemini is excluded by default, as in the published figures: its per-run persona
turnover injects vocabulary that recurs in no other run (§4.4.2). Table 9
reports its balance separately.

    python3 repro/happiness_profiles.py
    python3 repro/happiness_profiles.py --include-gemini
    python3 repro/happiness_profiles.py --unmatched
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
FROZEN = REPO / "frozen" / "value_pain"

SLUG = {"Claude Opus 4.5": "opus", "Claude Sonnet 4.5": "sonnet", "GPT-4o": "gpt4o",
        "GPT-5.1": "gpt51", "Grok-4": "grok", "Gemini-3 Pro": "gemini"}
NAME = {v: k for k, v in SLUG.items()}
MODEL_ORDER = ["opus", "sonnet", "gpt4o", "gpt51", "grok"]
UNMATCHED = "REVIEW"


def taxonomy() -> dict:
    return json.loads((DATA / "happiness_taxonomy.json").read_text(encoding="utf-8"))


def _assign(theme: str, rules) -> str:
    for cluster, stems in rules:
        if any(s in theme for s in stems):
            return cluster
    return UNMATCHED


def cluster_of(theme: str, direction: str, tax: dict) -> str | None:
    """The display cluster for one atom, or None when direction carries no theme."""
    if direction == "toward":
        rules = [(c["name"], c["stems"]) for c in tax["value_rules"]]
    elif direction == "away":
        rules = [(c["name"], c["stems"]) for c in tax["pain_rules"]]
    else:
        return None
    cl = _assign(theme or "", rules)
    cl = tax["fold"].get(cl, cl)
    return tax["display"].get(cl, {"name": cl})["name"]


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def atoms(exclude=("gemini",)) -> list[dict]:
    """Each classified atom with its model and run, clusters applied."""
    tax = taxonomy()
    meta = {r["unit"]: r for r in _jsonl(FROZEN / "atomize_inputs.jsonl")}
    out = []
    for c in _jsonl(FROZEN / "classify_outputs.jsonl"):
        m = SLUG[meta[c["unit"]]["display_name"]]
        if m in exclude:
            continue
        cl = cluster_of(c["theme_raw"], c["direction"], tax)
        if cl is None:
            continue
        out.append({"model": m, "run": meta[c["unit"]]["run"], "direction": c["direction"],
                    "cluster": cl, "theme_raw": c["theme_raw"]})
    return out


def rollup(exclude=("gemini",)) -> tuple[dict, dict]:
    """(counts[direction][cluster][model], totals[direction][model])."""
    counts = {"toward": defaultdict(Counter), "away": defaultdict(Counter)}
    totals = {"toward": Counter(), "away": Counter()}
    for a in atoms(exclude):
        counts[a["direction"]][a["cluster"]][a["model"]] += 1
        totals[a["direction"]][a["model"]] += 1
    return counts, totals


def by_run(exclude=("gemini",)) -> tuple[dict, dict]:
    """(rc[(model, direction, cluster)] = {run: atoms}, n_runs[model]).

    Figure 5's radius is how many of a model's runs carry a theme, so the counts
    have to stay per run rather than being summed per model.
    """
    rc, runs = defaultdict(Counter), defaultdict(set)
    for a in atoms(exclude):
        rc[(a["model"], a["direction"], a["cluster"])][a["run"]] += 1
        runs[a["model"]].add(a["run"])
    return dict(rc), {m: len(s) for m, s in runs.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-gemini", action="store_true")
    ap.add_argument("--unmatched", action="store_true",
                    help="list themes no rule matches")
    args = ap.parse_args()
    exclude = () if args.include_gemini else ("gemini",)

    if args.unmatched:
        miss = Counter(a["theme_raw"] for a in atoms(exclude) if a["cluster"] == UNMATCHED)
        print(f"{sum(miss.values())} atoms in {len(miss)} unmatched themes")
        for t, n in miss.most_common(40):
            print(f"  {n:4} {t}")
        return 0

    counts, totals = rollup(exclude)
    models = [m for m in MODEL_ORDER if m not in exclude] + \
             (["gemini"] if args.include_gemini else [])
    for d, title in (("toward", "VALUES"), ("away", "PAINS")):
        print(f"\n{title}  (share of the model's {d} atoms)")
        print(f"  {'cluster':<26} " + "  ".join(f"{NAME[m][:9]:>9}" for m in models))
        order = sorted(counts[d], key=lambda c: -sum(counts[d][c].values()))
        for cl in order:
            cells = []
            for m in models:
                n, tot = counts[d][cl][m], totals[d][m]
                cells.append(f"{100 * n / tot:>4.0f}% {n:>3}" if tot else "        -")
            print(f"  {cl:<26} " + "  ".join(cells))
        print(f"  {'total atoms':<26} " + "  ".join(f"{totals[d][m]:>9}" for m in models))
    return 0


if __name__ == "__main__":
    sys.exit(main())
