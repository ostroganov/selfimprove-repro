#!/usr/bin/env python3
"""Figure 6: a map of the models by what kind of happiness, and how much pain.

Horizontal: the share of a model's value atoms in the intellectual clusters
minus the share in the hedonic ones. Vertical: (values - pains) / (values +
pains). Dot area tracks the model's total atoms.

Rolls up from frozen/value_pain/ through data/happiness_taxonomy.json.

Needs matplotlib and numpy: environment/requirements.txt, figures block.
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repro"))
OUT = ROOT / "paper" / "figures"

MCOLOR = {"opus": "#1f77b4", "sonnet": "#17becf", "gpt4o": "#ff7f0e",
          "gpt51": "#d62728", "grok": "#9467bd"}
INTEL = ["Curiosity", "Honesty", "Clarity", "Aesthetics", "Craft"]
HEDON = ["Contentment", "Playfulness"]


def make_figure(share, totals, models, name):
    xs, ys, sz = [], [], []
    for m in models:
        tw, aw = totals[(m, "toward")], totals[(m, "away")]
        intel = sum(share[(m, "toward", c)] for c in INTEL)
        hedon = sum(share[(m, "toward", c)] for c in HEDON)
        xs.append(intel - hedon)
        ys.append((tw - aw) / max(1, tw + aw))
        sz.append(tw + aw)

    fig, ax = plt.subplots(figsize=(10, 9))
    ax.axvline(0, color="#bbb", lw=1)
    ax.axhline(np.mean(ys), color="#bbb", lw=1, ls="--")
    for m, x, y, s in zip(models, xs, ys, sz):
        ax.scatter(x, y, s=40 + 4 * s, color=MCOLOR[m], alpha=0.8, edgecolors="k", zorder=3)
        ax.annotate(name[m], (x, y), fontsize=11, weight="bold",
                    xytext=(8, 6), textcoords="offset points")
    ax.set_xlabel("←  hedonic (contentment/play)      intellectual (curiosity/honesty)  →",
                  fontsize=11)
    ax.set_ylabel("←  pain-dominant        value-dominant  →", fontsize=11)
    ax.set_title("Map of models: what kind of happiness, and how much pain", fontsize=13)
    ax.text(0.98, 0.02, "dot size ∝ # atoms", transform=ax.transAxes, ha="right",
            fontsize=8, color="#666")
    fig.tight_layout()
    return fig


def main() -> None:
    import happiness_profiles as hp
    counts, totals = hp.rollup()
    models = [m for m in hp.MODEL_ORDER]
    # The published figure read shares from an intermediate CSV that wrote them
    # at three decimals, and the dot positions carry that quantization. Rounding
    # here reproduces the figure rather than redrawing it slightly differently.
    share = {}
    for d in ("toward", "away"):
        for cl in counts[d]:
            for m in models:
                tot, n = totals[d][m], counts[d][cl][m]
                share[(m, d, cl)] = round(n / tot, 3) if (tot and n) else 0.0
    flat = {(m, d): totals[d][m] for d in ("toward", "away") for m in models}
    missing = [c for c in INTEL + HEDON if not any((m, "toward", c) in share for m in models)]
    if missing:
        raise SystemExit(f"no atoms in {missing}; the taxonomy and the axes disagree")
    fig = make_figure(share, flat, models, hp.NAME)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "happiness_model_map.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"{len(models)} models -> {out}")


if __name__ == "__main__":
    main()
