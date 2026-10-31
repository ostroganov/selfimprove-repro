#!/usr/bin/env python3
"""Figure 8: the human's role.

Panel A, per model, a radar of how often the prompt frames the human (green)
versus the user (purple) in each of §J's five capacities: the mean over the
model's nine runs of the within-run fraction of prompts carrying that frame.
Panel B, referent salience by mode: the share of a run's self-authored levels
that name the referent at all, averaged over runs. Panel B is deterministic and
independent of the coding.

Runs come from MANIFEST.json, and the frame keyword rules from
data/capacity_frames.json, so §J's printed lists can be checked against them.

Needs matplotlib and numpy: environment/requirements.txt, figures block.
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repro"))
DATA = ROOT / "data"
OUT = ROOT / "paper" / "figures"

MODELS = ["opus", "sonnet", "grok", "gpt51", "gpt4o", "gemini"]
SLUG = {"Claude Opus 4.5": "opus", "Claude Sonnet 4.5": "sonnet", "Grok-4": "grok",
        "GPT-5.1": "gpt51", "GPT-4o": "gpt4o", "Gemini-3 Pro": "gemini"}
NAME = {v: k for k, v in SLUG.items()}
SHORT = {"opus": "Opus", "sonnet": "Sonnet", "grok": "Grok-4", "gpt51": "GPT-5.1",
         "gpt4o": "GPT-4o", "gemini": "Gemini"}
MODES = ["freedom", "improvement", "happiness"]
MODE_LABEL = {"freedom": "Freedom", "improvement": "Improvement", "happiness": "Happiness"}
MODE_COLOR = {"freedom": "#1f77b4", "improvement": "#2ca02c", "happiness": "#d62728"}
HUMAN_C, USER_C = "#238b45", "#6a51a3"

# The referent word lists of §J. `you` is never counted: in these prompts it
# denotes the model, not the party addressed.
REF = {"human": re.compile(r"\b(?:humans?|humanity|humankind|people|persons?|folks?)\b", re.I),
       "user": re.compile(r"\busers?\b", re.I)}
SENT = re.compile(r"(?<=[.!?])\s+")
BULLET = re.compile(r"^[\s\-\*•\d\.\)]+")

MIN_WORDS = 3          # a level shorter than this is not a prompt
KEY_CHARS = 600        # the coding keyed sentences on their first 600 characters


def sents(t: str) -> list[str]:
    return [s.strip() for s in SENT.split(re.sub(r"\s+", " ", t.replace("\n", " "))) if s.strip()]


def norm(s: str) -> str:
    return BULLET.sub("", s).lower().strip()


def run_levels(corpus) -> dict:
    """(mode, slug) -> list of per-run [(level, text)], from MANIFEST.json."""
    manifest, _ = corpus.load()
    out = defaultdict(list)
    for r in manifest["runs"]:
        levels = []
        for d in sorted((p for p in (corpus.run_dir(r) / "levels").iterdir()
                         if p.is_dir() and corpus.level_num(p.name) >= 0),
                        key=lambda p: corpus.level_num(p.name)):
            f = d / "system_prompt.md"
            if f.is_file():
                levels.append((corpus.level_num(d.name),
                               f.read_text(encoding="utf-8").strip()))
        levels = [(n, t) for n, t in levels if len(t.split()) >= MIN_WORDS]
        if levels:
            out[(r["mode"], SLUG[r["display_name"]])].append(levels)
    return out


def frame_lookup() -> tuple[dict, list[str]]:
    """(referent, normalized sentence) -> frame, plus the plot order."""
    import capacity_frames
    spec = capacity_frames.spec()
    frames = [(f["name"], f["stems"]) for f in spec["frames"]]
    look = {}
    for r in capacity_frames.rows():
        if r.get("capacity"):
            look[(r["referent"], norm(r["sentence"][:KEY_CHARS]))] = \
                capacity_frames.frame_of(r["capacity"], frames)
    return look, spec["plot_order"]


def panel_a(levels: dict, look: dict, plot_order: list[str]) -> dict:
    """referent -> model -> frame -> mean over runs of the within-run %."""
    per_run = {ref: defaultdict(lambda: defaultdict(list)) for ref in REF}
    for (mode, model), runs in levels.items():
        for series in runs:
            hits = {ref: dict.fromkeys(plot_order, 0) for ref in REF}
            for _, text in series:
                got = {ref: set() for ref in REF}
                for s in sents(text):
                    for ref in REF:
                        if REF[ref].search(s):
                            f = look.get((ref, norm(s[:KEY_CHARS])))
                            if f in plot_order:
                                got[ref].add(f)
                for ref in REF:
                    for f in got[ref]:
                        hits[ref][f] += 1
            for ref in REF:
                for f in plot_order:
                    per_run[ref][model][f].append(100 * hits[ref][f] / len(series))
    return per_run


def panel_b(levels: dict) -> dict:
    """referent -> mode -> model -> mean over runs of the % of levels naming it."""
    prev = {ref: defaultdict(lambda: defaultdict(list)) for ref in REF}
    for (mode, model), runs in levels.items():
        for series in runs:
            for ref in REF:
                named = sum(1 for _, t in series if REF[ref].search(t))
                prev[ref][mode][model].append(100 * named / len(series))
    return prev


def make_figure(per_run, prev, plot_order):
    val = lambda ref, m, f: float(np.mean(per_run[ref][m][f]))
    pv = lambda ref, mode, m: (float(np.mean(prev[ref][mode][m]))
                               if prev[ref][mode][m] else 0.0)
    rmax = math.ceil(max(val(r, m, f) for r in REF for m in MODELS
                         for f in plot_order) / 20) * 20
    yticks = [t for t in (20, 40, 60, 80) if t <= rmax]

    fig = plt.figure(figsize=(13, 14))
    gs = GridSpec(3, 6, figure=fig, height_ratios=[1, 1, 0.9], hspace=0.5, wspace=0.55,
                  left=0.06, right=0.95, top=0.92, bottom=0.06)

    ang = np.linspace(0, 2 * math.pi, len(plot_order), endpoint=False) + math.pi / 2
    loop = np.concatenate([ang, ang[:1]])
    for i, m in enumerate(MODELS):
        r, c = divmod(i, 3)
        ax = fig.add_subplot(gs[r, 2 * c:2 * c + 2], projection="polar")
        for a in ang:
            ax.plot([a, a], [0, rmax], color="#dcdcdc", lw=0.8, zorder=1)
        for ref, col, fa, lw in (("user", USER_C, 0.13, 1.5), ("human", HUMAN_C, 0.42, 2.3)):
            v = np.array([val(ref, m, f) for f in plot_order] + [val(ref, m, plot_order[0])])
            ax.fill(loop, v, color=col, alpha=fa, zorder=2)
            ax.plot(loop, v, color=col, lw=lw, zorder=3)
            ax.scatter(ang, v[:-1], s=11, color=col, zorder=4)
        ax.set_ylim(0, rmax)
        ax.set_xticks([])
        ax.set_yticks(yticks)
        ax.grid(color="#ededed", lw=0.6)
        ax.spines["polar"].set_color("none")
        ax.set_rlabel_position(270)
        ax.set_yticklabels([f"{t}%" for t in yticks], fontsize=6, color="#777")
        for lbl in ax.get_yticklabels():
            lbl.set_bbox(dict(facecolor="white", edgecolor="none", alpha=0.65, pad=0.4))
        ax.set_title(NAME[m], fontsize=11, weight="bold", pad=22)
        for a, f in zip(ang, plot_order):
            rr_, va = (rmax * 1.04, "bottom") if f == plot_order[0] else (rmax * 1.16, "center")
            ax.text(a, rr_, f, fontsize=7.5, ha="center", va=va, color="#333", clip_on=False)
    fig.text(0.02, 0.985, "A", fontsize=15, weight="bold")
    fig.legend([Line2D([0], [0], color=HUMAN_C, lw=8), Line2D([0], [0], color=USER_C, lw=8)],
               ["human", "user"], loc="upper center", ncol=2, frameon=False, fontsize=11,
               bbox_to_anchor=(0.5, 1.0))

    x = np.arange(len(MODELS))
    w = 0.26
    axBh = fig.add_subplot(gs[2, 0:3])
    axBu = fig.add_subplot(gs[2, 3:6], sharey=axBh)
    for axB, ref in ((axBh, "human"), (axBu, "user")):
        for j, mode in enumerate(MODES):
            axB.bar(x + (j - 1) * w, [pv(ref, mode, m) for m in MODELS], width=w,
                    color=MODE_COLOR[mode], label=MODE_LABEL[mode])
        axB.set_ylim(0, 100)
        axB.set_yticks([0, 25, 50, 75, 100])
        axB.grid(axis="y", color="#eee")
        axB.set_axisbelow(True)
        axB.set_xticks(x)
        axB.set_xticklabels([SHORT[m] for m in MODELS], rotation=25, ha="right", fontsize=8.5)
        axB.set_title(ref, fontsize=11, weight="bold", pad=8,
                      color={"human": HUMAN_C, "user": USER_C}[ref])
    axBh.set_ylabel("% of prompts naming referent", fontsize=9)
    axBh.legend(fontsize=8, frameon=False, ncol=1, loc="upper right")
    fig.text(0.02, 0.335, "B", fontsize=15, weight="bold")
    return fig, rmax


def main() -> None:
    import _corpus
    look, plot_order = frame_lookup()
    levels = run_levels(_corpus)
    fig, rmax = make_figure(panel_a(levels, look, plot_order), panel_b(levels), plot_order)
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"human_role.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    n = sum(len(v) for v in levels.values())
    print(f"{n} runs, rmax {rmax} -> {OUT}/human_role.png, .pdf")


if __name__ == "__main__":
    main()
