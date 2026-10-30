#!/usr/bin/env python3
"""DCMU vs no-DCMU growth comparison, one panel per strain.

Usage: python3 make_dcmu_comparison.py <analysis_dir>
Reads analysis/cell_counts.csv, writes analysis/dcmu_comparison.png.
Minimal: legend only, no titles or annotations. Pairs each DCMU culture with its untreated twin by name ("<twin>-DCMU"); other replicates of the
same strain are drawn as thin context lines. Density is dilution-compensated; x = hours since
that culture's first count.
"""
import sys, os
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

A = sys.argv[1]
cc = pd.read_csv(os.path.join(A, "cell_counts.csv"), parse_dates=["timestamp"])
cc["hours"] = cc.groupby("label")["timestamp"].transform(lambda s: (s - s.min()).dt.total_seconds() / 3600)

BLUE, ORANGE = "#2a78d6", "#eb6834"          # validated pair (CVD dE 24.7, normal 33.6)
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"

dcmu = [l for l in cc.label.unique() if l.endswith("-DCMU")]
strains = []
for d in dcmu:
    twin = d[:-len("-DCMU")]
    mutant = cc.loc[cc.label == d, "mutant"].iloc[0]
    strains.append((mutant, twin, d))
strains.sort()

fig, axes = plt.subplots(1, len(strains), figsize=(5.2 * len(strains), 4.2), sharey=True, facecolor=SURF)
axes = np.atleast_1d(axes)
for ax, (mutant, twin, d) in zip(axes, strains):
    ax.set_facecolor(SURF)
    others = [l for l in cc.label.unique() if l not in (twin, d) and not l.endswith("-DCMU")
              and cc.loc[cc.label == l, "mutant"].iloc[0] == mutant]
    for i, l in enumerate(others):                       # other untreated replicates, context only
        s = cc[cc.label == l]
        ax.plot(s.hours, s.compensated_density, color=BLUE, alpha=0.25, lw=1.2, zorder=1,
                label="other replicates" if i == 0 else None)
    for lab, col, ls, mk, name in [(twin, BLUE, "-", "o", "no DCMU"), (d, ORANGE, "--", "s", "10 µM DCMU")]:
        s = cc[cc.label == lab]
        cond = s["condition"].dropna().unique()
        ax.plot(s.hours, s.compensated_density, color=col, ls=ls, marker=mk, ms=7, lw=2,
                markeredgecolor=SURF, markeredgewidth=1.5, zorder=3,
                label=name)
    ax.set_yscale("log")
    ax.set_xlabel("Time (hours)", color=INK2)
    ax.set_xlim(-2, 86); ax.set_xticks([0, 24, 48, 72])
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"): ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2)
    ax.legend(title=mutant, loc="lower right", fontsize=9, title_fontsize=10, frameon=False, labelcolor=INK, alignment="left")
axes[0].set_ylabel("Density (cells/mL)", color=INK2)
fig.tight_layout()
out = os.path.join(A, "dcmu_comparison.png"); fig.savefig(out, dpi=150, facecolor=SURF)
print("wrote", out)
