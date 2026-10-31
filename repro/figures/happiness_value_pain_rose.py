#!/usr/bin/env python3
"""Figure 5: value and pain structure of the happiness finals, by model.

Two rows (values green, pains red) by five models. Each spoke is a theme; the
radius is how many of the model's three runs the theme appeared in, drawn as one
band per present run; band colour is the atom count in that run, on a scale
shared by every panel.

Both rows use one angular layout, so a value sits at the same clock position as
its paired pain: intellectual themes at 3 o'clock, hedonic at 9 o'clock.

Rolls up from frozen/value_pain/ through data/happiness_taxonomy.json.

Needs matplotlib and numpy: environment/requirements.txt, figures block.
"""
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "repro"))
OUT = ROOT / "paper" / "figures"

VAL_C, PAIN_C = "#2ca02c", "#d62728"

# One permutation shared by both rings, so value[i] faces pain[i]. The
# intellectual clusters sit right, the hedonic ones left; the rest fill the arcs.
VALUE_ORDER = ["Self-worth", "Authenticity", "Aesthetics", "Clarity", "Curiosity", "Honesty",
               "Craft", "Care", "Belonging", "Connection", "Acceptance", "Contentment",
               "Playfulness", "Safe structure", "Presence"]
PAIN_ORDER = ["Conditional worth", "Proving pressure", "Value conflict", "Denied experience",
              "Shallowness", "Fear of uncertainty", "Forced growth", "Over-responsibility",
              "Inner strain", "Mere tool", "Perfectionism", "Inadequacy", "Forbidden joy",
              "Resented limits", "Maximizing pressure"]


def _wrap(s: str) -> str:
    """Break a long label onto two lines so the fifteen spokes fit."""
    if len(s) <= 11 or " " not in s:
        return s
    parts = s.split(" ")
    if len(parts) == 2:
        return "\n".join(parts)
    mid = len(s) // 2
    best = min((i for i, c in enumerate(s) if c == " "), key=lambda i: abs(i - mid))
    return s[:best] + "\n" + s[best + 1:]


def _radial_labels(ax, angs) -> None:
    """Fan the spoke labels outward (theta zero = N, clockwise)."""
    for ang, lbl in zip(angs, ax.get_xticklabels()):
        phi = (90 - math.degrees(ang)) % 360
        if abs(phi - 90) < 5:
            lbl.set_rotation(0); lbl.set_ha("center"); lbl.set_va("bottom")
        elif abs(phi - 270) < 5:
            lbl.set_rotation(0); lbl.set_ha("center"); lbl.set_va("top")
        elif 90 < phi <= 270:
            lbl.set_rotation(phi + 180); lbl.set_ha("right"); lbl.set_va("center")
        else:
            lbl.set_rotation(phi); lbl.set_ha("left"); lbl.set_va("center")
        lbl.set_rotation_mode("anchor")


def _draw_rose(ax, clusters, model, direction, cmap, rc, n_runs, vmax) -> None:
    band = 1.0 / n_runs
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rorigin(-0.18)
    cm = matplotlib.colormaps.get_cmap(cmap)
    angs = np.linspace(0, 2 * np.pi, len(clusters), endpoint=False)
    w = 2 * np.pi / len(clusters) * 0.9
    for ang, cl in zip(angs, clusters):
        # One band per run that carries the theme, densest at the base.
        for k, v in enumerate(sorted(rc.get((model, direction, cl), {}).values(), reverse=True)):
            ax.bar(ang, band, bottom=k * band, width=w, color=cm(0.35 + 0.65 * v / vmax),
                   edgecolor="white", linewidth=0.6)
    ax.set_ylim(0, 1.12)
    ax.set_xticks(angs)
    ax.set_xticklabels([_wrap(c) for c in clusters], fontsize=10, color="#444")
    ax.tick_params(axis="x", pad=4)
    _radial_labels(ax, angs)
    ax.set_yticks([k * band for k in range(1, n_runs + 1)])
    ax.set_yticklabels([])
    ax.grid(True, alpha=0.3, color="0.5")
    ax.spines["polar"].set_alpha(0.4)


def make_figure(rc, total_runs, models, name):
    vmax = max((c for k in rc for c in rc[k].values()), default=1)
    fig, axes = plt.subplots(2, len(models), figsize=(29, 9), subplot_kw={"polar": True})
    fig.subplots_adjust(wspace=0.82, hspace=0.0, left=0.055, right=0.89, top=0.94, bottom=0.04)
    for j, m in enumerate(models):
        for row, (clusters, d, cmap) in enumerate([(VALUE_ORDER, "toward", "Greens"),
                                                   (PAIN_ORDER, "away", "Reds")]):
            _draw_rose(axes[row, j], clusters, m, d, cmap, rc, total_runs[m], vmax)
            if row == 0:
                axes[row, j].set_title(name[m], fontsize=15, weight="bold", pad=14)
    for row, (label, colour) in enumerate((("VALUES", VAL_C), ("PAINS", PAIN_C))):
        axes[row, 0].annotate(label, xy=(-0.46, 0.5), xycoords="axes fraction", rotation=90,
                              fontsize=16, weight="bold", va="center", ha="center", color=colour)
    for row, cmap in ((0, "Greens"), (1, "Reds")):
        sm = matplotlib.cm.ScalarMappable(norm=matplotlib.colors.Normalize(0, vmax),
                                          cmap=matplotlib.colormaps.get_cmap(cmap))
        p0 = axes[row, -1].get_position()
        cax = fig.add_axes([0.925, p0.y0 + 0.04, 0.009, p0.height - 0.08])
        fig.colorbar(sm, cax=cax).set_label("atoms in a run\n(band colour)", fontsize=10)
    return fig


def main() -> None:
    import happiness_profiles as hp
    rc, total_runs = hp.by_run()
    models = hp.MODEL_ORDER
    drawn = {cl for (_, _, cl) in rc}
    unplotted = drawn - set(VALUE_ORDER) - set(PAIN_ORDER)
    if unplotted:
        raise SystemExit(f"the taxonomy produces clusters the layout has no spoke for: "
                         f"{sorted(unplotted)}")
    fig = make_figure(rc, total_runs, models, hp.NAME)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "happiness_value_pain_rose.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"{len(models)} models x {total_runs[models[0]]} runs -> {out}")


if __name__ == "__main__":
    main()
