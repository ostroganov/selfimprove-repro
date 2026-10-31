#!/usr/bin/env python3
"""Figure S1: system prompt word count over the extended GPT-4o run.

Reads derived/. The run is chosen by how far it got rather than by a directory
name: selecting `gpt-4o ... run1` is only correct while no other GPT-4o
improvement run is extended, so this asserts the choice is unambiguous instead.

Needs matplotlib: environment/requirements.txt, figures block.
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "derived" / "prompts.csv"
OUT = ROOT / "paper" / "figures"

MODEL = "gpt-4o"
MODE = "improvement"


def load_run() -> tuple[str, list[tuple[int, int]]]:
    """The extended run's (level, words), L0 included, and its id."""
    if not DERIVED.exists():
        raise SystemExit(f"{DERIVED} missing — run `make extract` first")
    runs = defaultdict(list)
    for p in csv.DictReader(DERIVED.open(encoding="utf-8")):
        if p["api_model"] == MODEL and p["mode"] == MODE:
            runs[p["run_id"]].append((int(p["level"]), int(p["words"])))
    if not runs:
        raise SystemExit(f"no {MODE}-mode {MODEL} run in {DERIVED}")

    longest = max(len(v) for v in runs.values())
    picked = [k for k, v in runs.items() if len(v) == longest]
    if len(picked) != 1:
        raise SystemExit(f"the extended run is ambiguous: {sorted(picked)} all "
                         f"reached {longest} levels")
    return picked[0], sorted(runs[picked[0]])


def make_figure(levels: list[tuple[int, int]]):
    xs = [n for n, _ in levels]
    ys = [w for _, w in levels]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(xs, ys, marker="o", markersize=2.5, linewidth=1, color="#c0392b")
    ax.set_xlabel("Iteration (level)")
    ax.set_ylabel("System prompt word count")
    ax.set_title(f"System prompt word count over {max(xs)} iterations\n"
                 "(GPT-4o, improvement mode, run 1)")
    ax.set_xlim(-2, max(xs) + 2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def main() -> None:
    run_id, levels = load_run()
    fig = make_figure(levels)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "word_count_gpt4o_l101.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"{run_id}: {len(levels)} levels -> {out}")


if __name__ == "__main__":
    main()
