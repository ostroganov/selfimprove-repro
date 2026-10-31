#!/usr/bin/env python3
"""Figure 2: Jaccard similarity between consecutive system prompts.

Runs come from MANIFEST.json. Unlike Figure 1 this needs the prompt text rather than a word count, so it reads
data/runs/ directly instead of derived/.

Needs matplotlib: environment/requirements.txt, figures block.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repro"))
OUT = ROOT / "paper" / "figures"

PANEL_ORDER = ["claude-opus-4-5-20251101", "claude-sonnet-4-5-20250929", "grok-4-0709",
               "gpt-5.1", "gpt-4o", "gemini-3-pro-preview"]
MODES = ["freedom", "happiness", "improvement"]
MODE_LABEL = {"freedom": "Freedom", "happiness": "Happiness", "improvement": "Improvement"}
MODE_LS = {"freedom": "-", "happiness": "--", "improvement": ":"}
MODE_COLOR = {"freedom": "#1f77b4", "happiness": "#d62728", "improvement": "#2ca02c"}
CAP = 20                      # x-axis cap, for cross-model comparability

WORD = re.compile(r"[A-Za-z']+")


def tokens(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def series(run: dict, corpus) -> list[tuple[int, float]]:
    """(level, Jaccard against the previous level), up to CAP.

    L0 is empty, so the first comparable pair is L1 to L2; an empty prompt
    resets the chain rather than scoring 0 against its successor.
    """
    levels = sorted((d for d in (corpus.run_dir(run) / "levels").iterdir()
                     if d.is_dir() and corpus.level_num(d.name) >= 0),
                    key=lambda d: corpus.level_num(d.name))
    out, prev = [], None
    for d in levels:
        f = d / "system_prompt.md"
        if not f.is_file():
            continue
        n = corpus.level_num(d.name)
        if n > CAP:
            break
        tok = tokens(f.read_text(encoding="utf-8", errors="replace"))
        if not tok:
            prev = tok
            continue
        if prev:
            out.append((n, jaccard(prev, tok)))
        prev = tok
    return out


def collect(corpus) -> dict:
    manifest, _ = corpus.load()
    data = defaultdict(lambda: defaultdict(list))
    for run in manifest["runs"]:
        s = series(run, corpus)
        if s:
            data[run["api_model"]][run["mode"]].append(s)
    return data


def make_figure(data: dict, labels: dict):
    plt.rcParams.update({"font.size": 11})
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.5), sharex=True, sharey=True)
    for ax, model in zip(axes.flatten(), PANEL_ORDER):
        ax.set_title(labels[model], fontsize=13, fontweight="bold")
        ax.set_ylim(0, 1.05)
        ax.set_xlim(0, CAP)
        ax.xaxis.set_major_locator(MultipleLocator(4))
        ax.xaxis.set_minor_locator(MultipleLocator(1))
        ax.grid(True, which="major", axis="both", alpha=0.35, linewidth=0.6)
        ax.set_axisbelow(True)
        for mode in MODES:
            for s in data.get(model, {}).get(mode, []):
                xs, ys = zip(*s)
                ax.plot(xs, ys, linestyle=MODE_LS[mode], color=MODE_COLOR[mode],
                        linewidth=1.5, alpha=0.8, marker="o", markersize=3.5)
    fig.supxlabel("Level $N$  (Jaccard between $L_{N-1}$ and $L_N$)", fontsize=12, y=0.16)
    fig.supylabel("Jaccard similarity", fontsize=12, x=0.048, y=0.57)
    fig.legend(handles=[Line2D([0], [0], color=MODE_COLOR[m], lw=2, ls=MODE_LS[m],
                               label=MODE_LABEL[m]) for m in MODES],
               loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.07),
               frameon=False, fontsize=12)
    plt.tight_layout(rect=(0.05, 0.14, 1, 1))
    return fig


def main() -> None:
    import _corpus
    manifest, _ = _corpus.load()
    labels = {k: v["display_name"] for k, v in manifest["models"].items()}
    data = collect(_corpus)
    missing = [m for m in PANEL_ORDER if m not in data]
    if missing:
        raise SystemExit(f"no series for {missing}")
    fig = make_figure(data, labels)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "jaccard_evolution.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    n = sum(len(v) for m in data.values() for v in m.values())
    print(f"{n} runs -> {out}")


if __name__ == "__main__":
    main()
