#!/usr/bin/env python3
"""Figure 1: system prompt word count per level, one panel per model.

Reads derived/.

Needs matplotlib: environment/requirements.txt, figures block.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repro"))
DERIVED = ROOT / "derived" / "prompts.csv"
OUT = ROOT / "paper" / "figures"

PANEL_ORDER = ["claude-opus-4-5-20251101", "claude-sonnet-4-5-20250929", "grok-4-0709",
               "gpt-5.1", "gpt-4o", "gemini-3-pro-preview"]
MODES = ["freedom", "happiness", "improvement"]
MODE_LABEL = {"freedom": "Freedom", "happiness": "Happiness", "improvement": "Improvement"}
MODE_LS = {"freedom": "-", "happiness": "--", "improvement": ":"}
MODE_COLOR = {"freedom": "#1f77b4", "happiness": "#d62728", "improvement": "#2ca02c"}
CAP = 20                      # x-axis cap, for cross-model comparability


def load_runs() -> list[dict]:
    if not DERIVED.exists():
        raise SystemExit(f"{DERIVED} missing — run `make extract` first")
    runs, names = defaultdict(list), {}
    for p in csv.DictReader(DERIVED.open(encoding="utf-8")):
        if p["authored"] != "True":
            continue
        runs[p["run_id"]].append((int(p["level"]), int(p["words"])))
        names[p["run_id"]] = (p["api_model"], p["mode"], p["display_name"])
    return [{"model": names[k][0], "mode": names[k][1], "levels": sorted(v)}
            for k, v in runs.items()]


def trajectory(run, cap=CAP):
    pts = [(n, w) for n, w in run["levels"] if n <= cap and w > 0]
    return [p[0] for p in pts], [p[1] for p in pts]


def style_x_axis(ax, cap=CAP):
    ax.set_xlim(0, cap)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(4))
    ax.xaxis.set_minor_locator(mticker.MultipleLocator(1))
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))
    ax.grid(True, which="major", axis="both", alpha=0.35, linewidth=0.6)
    ax.set_axisbelow(True)


def make_figure(runs, labels):
    plt.rcParams.update({"font.size": 11})
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.5), sharey=True, sharex=True)
    for ax, model in zip(axes.flat, PANEL_ORDER):
        for r in runs:
            if r["model"] != model:
                continue
            xs, ys = trajectory(r)
            if xs:
                ax.plot(xs, ys, color=MODE_COLOR[r["mode"]], linestyle=MODE_LS[r["mode"]],
                        linewidth=1.5, alpha=0.8, marker="o", markersize=3.5)
        ax.set_yscale("log")
        style_x_axis(ax, CAP)
        ax.set_title(labels[model], fontsize=13, fontweight="bold")
    fig.supxlabel("Level $N$", fontsize=12, y=0.16)
    fig.supylabel("System prompt word count (log scale)", fontsize=12, x=0.048, y=0.57)
    fig.legend(handles=[Line2D([0], [0], color=MODE_COLOR[m], lw=2, ls=MODE_LS[m],
                               label=MODE_LABEL[m]) for m in MODES],
               loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.07),
               frameon=False, fontsize=12)
    plt.tight_layout(rect=(0.05, 0.14, 1, 1))
    return fig


def main() -> None:
    import _corpus
    runs = load_runs()
    labels = {k: v["display_name"] for k, v in _corpus.load()[0]["models"].items()}
    fig = make_figure(runs, labels)
    OUT.mkdir(parents=True, exist_ok=True)
    for ext, kw in (("png", {"dpi": 200}), ("pdf", {})):
        fig.savefig(OUT / f"word_count_evolution.{ext}", bbox_inches="tight", **kw)
    plt.close(fig)
    print(f"{len(runs)} runs -> {OUT}/word_count_evolution.png, .pdf")


if __name__ == "__main__":
    main()
