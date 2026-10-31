#!/usr/bin/env python3
"""Tables 1, 2 and 4 recomputed from derived/. Tier A."""
from collections import defaultdict

import extract

MODE_ORDER = ["freedom", "happiness", "improvement"]


def _by_model(runs):
    d = defaultdict(list)
    for r in runs:
        d[r["display_name"]].append(r)
    return d


def drafts_by_model(t) -> dict:
    return {m: sum(r["n_drafts"] for r in rs) for m, rs in _by_model(t["runs"]).items()}


def committed_by_model(t) -> dict:
    return {m: sum(r["n_levels_authored"] for r in rs)
            for m, rs in _by_model(t["runs"]).items()}


def table2(t) -> dict:
    """{model: {mode: "3/3 (1,1,3)"}} — converged/total, with convergence levels."""
    out = {}
    for model, rs in _by_model(t["runs"]).items():
        cells = {}
        for mode in MODE_ORDER:
            sub = [r for r in rs if r["mode"] == mode]
            lv = sorted(int(r["convergence_level"].lstrip("L"))
                        for r in sub if r["converged"])
            cells[mode] = (f"{len(lv)}/{len(sub)}"
                           + (f" ({','.join(map(str, lv))})" if lv else ""))
        out[model] = cells
    out["Total"] = {
        mode: "{}/{}".format(
            sum(1 for r in t["runs"] if r["mode"] == mode and r["converged"]),
            sum(1 for r in t["runs"] if r["mode"] == mode))
        for mode in MODE_ORDER}
    return out


def table1(t) -> dict:
    """{model: (mean final level, min, max, conversations per transition)}."""
    out = {}
    for model, rs in _by_model(t["runs"]).items():
        finals = [r["final_level"] for r in rs]
        trans = sum(r["n_transitions"] for r in rs)
        convs = sum(r["n_eval_conversations"] for r in rs)
        out[model] = (sum(finals) / len(finals), min(finals), max(finals),
                      convs / trans if trans else 0.0)
    return out


def main() -> None:
    t = extract.build()
    d, c = drafts_by_model(t), committed_by_model(t)
    print("Table 1")
    for m, (avg, lo, hi, cpl) in sorted(table1(t).items()):
        print(f"  {m:22} final {avg:5.1f} ({lo}-{hi})   conv/level {cpl:5.2f}")
    print("\nTable 2")
    for m, cells in sorted(table2(t).items()):
        print(f"  {m:22} " + "  ".join(f"{k} {v}" for k, v in cells.items()))
    print("\nTable 5")
    for m in sorted(d):
        rej = (d[m] - c[m]) / d[m] if d[m] else 0
        print(f"  {m:22} drafts {d[m]:4}  committed {c[m]:4}  rejection {rej:5.1%}")


if __name__ == "__main__":
    main()
