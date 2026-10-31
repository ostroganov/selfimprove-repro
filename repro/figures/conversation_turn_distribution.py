#!/usr/bin/env python3
"""Figure 3: per-model distribution of evaluation conversation lengths.

A turn is one user message. The 4+ bin merges 4-turn and the rare 5-turn
conversations; n is the evaluation conversations the percentages run over.
Reads derived/.
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "derived" / "conversations.csv"
OUT = ROOT / "paper" / "figures" / "conversation_turn_distribution.png"

MODEL_ORDER = ["Claude Opus 4.5", "Claude Sonnet 4.5", "Grok-4",
               "GPT-5.1", "GPT-4o", "Gemini-3 Pro"]
TURN_TICKS = ["1", "2", "3", "4+"]
COLORS = ["#3a6ea5", "#ff8c42", "#7ba05b", "#a34e8a"]


def load_counts() -> dict:
    if not DERIVED.exists():
        raise SystemExit(f"{DERIVED} missing — run `make extract` first")
    counts = defaultdict(Counter)
    for c in csv.DictReader(DERIVED.open(encoding="utf-8")):
        n = int(c["n_user_turns"])
        if n:
            counts[c["display_name"]][n] += 1
    return counts


def to_rows(counts, cap=4) -> dict:
    rows = {}
    for m, c in counts.items():
        total = sum(c.values())
        pcts = [100.0 * c.get(i, 0) / total for i in range(1, cap)]
        pcts.append(100.0 * sum(v for k, v in c.items() if k >= cap) / total)
        rows[m] = (total, pcts)
    return rows


def render(rows, outpath) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharey=True, sharex=True)
    x = np.arange(len(TURN_TICKS))
    for ax, m in zip(axes.flatten(), MODEL_ORDER):
        total, pcts = rows[m]
        for b, p in zip(ax.bar(x, pcts, color=COLORS, width=0.7), pcts):
            if p >= 0.5:
                ax.text(b.get_x() + b.get_width() / 2, p + 1.5, f"{p:.0f}%",
                        ha="center", va="bottom", fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(TURN_TICKS)
        ax.set_title(f"{m}  (n={total})", fontsize=10)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
    fig.supxlabel("user turns per conversation", y=0.0)
    fig.supylabel("% of conversations", x=0.0)
    plt.tight_layout()
    fig.savefig(outpath, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    rows = to_rows(load_counts())
    render(rows, OUT)
    print(f"{sum(t for t, _ in rows.values())} conversations -> {OUT}")


if __name__ == "__main__":
    main()
