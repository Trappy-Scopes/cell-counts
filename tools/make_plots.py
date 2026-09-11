#!/usr/bin/env python3
"""
make_plots.py - build the site figures from build/all_*.csv.

Run tools/parse_data.py first.

Outputs into plots/:
    growth_curves_overview.png   every colony, every experiment: log density
                                  vs elapsed hours, dilution-compensated
    doubling_time_summary.png    doubling time per colony, perturbed vs not
    interactive.html             Bokeh: pan / zoom / hover / click-to-hide,
                                  one tab per experiment

GitHub cannot render interactive.html - README HTML is sanitised and files
viewed in the repo are shown as source. It is published as part of the
site (docs/growth-curves.md) and as a workflow artifact; it is not
committed (~ a few hundred KB to a few MB, and stale the moment a new
experiment is added).
"""

import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BUILD = "build"
OUT = "plots"

INK = "#1a1a1a"
GRID = "#d8d8d8"
PERTURBED_C = "#b3423f"
UNPERTURBED_C = "#2f6f4f"
PALETTE = ["#2f4b7c", "#b3423f", "#2e7d5b", "#c77d1a", "#7a4fa3", "#3a6ea5",
           "#c2185b", "#5d4037"]


def style(ax):
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK, labelsize=9)


def _read(name):
    path = os.path.join(BUILD, name)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    return df


def plot_growth_curves_overview(cc):
    """One line per colony, every experiment on the same axes, colored by
    mutant so the same strain reads the same colour across experiments."""
    if cc is None:
        return
    mutants = sorted(cc["mutant"].dropna().unique()) if "mutant" in cc else []
    colour_of = {m: PALETTE[i % len(PALETTE)] for i, m in enumerate(mutants)}

    fig, ax = plt.subplots(figsize=(10, 5.5))
    groups = cc.groupby(["experiment_name", "label"])
    for (exp, label), g in groups:
        g = g.sort_values("elapsed_hours")
        mutant = g["mutant"].iloc[0] if "mutant" in g else None
        colour = colour_of.get(mutant, INK)
        perturbed = bool(g["perturbed"].iloc[0]) if "perturbed" in g else False
        ax.plot(g["elapsed_hours"], g["compensated_density"], marker="o",
                markersize=3, linewidth=1, color=colour, alpha=0.9,
                linestyle="-" if perturbed else "--")

    ax.set_yscale("log")
    ax.set_xlabel("elapsed time (hours, per colony)", color=INK, fontsize=10)
    ax.set_ylabel("density (cells/mL, dilution-compensated)", color=INK,
                  fontsize=10)
    ax.set_title(
        f"Growth curves — {cc['label'].nunique()} colonies across "
        f"{cc['experiment_name'].nunique()} experiment(s)  "
        "(solid = media added at some point, dashed = none)",
        color=INK, fontsize=11, loc="left", pad=12,
    )
    if mutants:
        handles = [plt.Line2D([0], [0], color=colour_of[m], lw=2, label=m)
                   for m in mutants]
        ax.legend(handles=handles, fontsize=8, frameon=False, title="mutant",
                  title_fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/growth_curves_overview.png", dpi=150)
    plt.close(fig)


def plot_doubling_time_summary(gs):
    if gs is None:
        return
    gs = gs.sort_values("doubling_time_hr")
    colours = [PERTURBED_C if p else UNPERTURBED_C for p in gs["perturbed"]]

    fig, ax = plt.subplots(figsize=(9, max(2.5, 0.35 * len(gs) + 1)))
    y = np.arange(len(gs))
    ax.barh(y, gs["doubling_time_hr"], color=colours, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(
        [f"{r.label} ({r.mutant})" if pd.notna(r.mutant) else r.label
         for r in gs.itertuples()],
        fontsize=8,
    )
    for yi, (t, r2) in enumerate(zip(gs["doubling_time_hr"], gs["r_squared"])):
        ax.text(t + 0.1, yi, f"{t:.1f} h  (R²={r2:.2f})",
                va="center", fontsize=7.5, color=INK)
    ax.set_xlabel("doubling time (hours)", color=INK, fontsize=10)
    ax.set_title(
        "Doubling time by colony — red = media added at some point, "
        "green = none",
        color=INK, fontsize=11, loc="left", pad=12,
    )
    style(ax)
    ax.spines["left"].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{OUT}/doubling_time_summary.png", dpi=150)
    plt.close(fig)


def plot_interactive(cc, ma):
    """Bokeh: one tab per experiment, one renderer per colony, hover for
    exact values, click a legend entry to hide/show that colony, triangles
    mark media-addition events."""
    try:
        from bokeh.plotting import figure, output_file, save
        from bokeh.models import ColumnDataSource, HoverTool, TabPanel, Tabs
    except ImportError:
        print("bokeh not installed - skipping interactive.html")
        return
    if cc is None:
        return

    tools = "pan,box_zoom,wheel_zoom,reset,save"

    tabs = []
    for exp_name, exp_cc in cc.groupby("experiment_name"):
        p = figure(
            y_axis_type="log", height=480, width=980, tools=tools,
            title=f"{exp_name} — drag to pan, scroll to zoom, "
                  "click a legend entry to hide/show it",
            x_axis_label="elapsed time (hours, per colony)",
            y_axis_label="density (cells/mL, dilution-compensated)",
        )

        labels = sorted(exp_cc["label"].unique())
        colour_of_label = {lb: PALETTE[i % len(PALETTE)] for i, lb in enumerate(labels)}

        for label, g in exp_cc.groupby("label"):
            g = g.sort_values("elapsed_hours")
            mutant = g["mutant"].iloc[0] if "mutant" in g else None
            colour = colour_of_label[label]
            src = ColumnDataSource(dict(
                x=g["elapsed_hours"], y=g["compensated_density"],
                raw=g["density"], label=[label] * len(g),
                mutant=[str(mutant)] * len(g),
                perturbed=[str(bool(p)) for p in g.get("perturbed", [False] * len(g))],
                ts=g["timestamp"].astype(str),
            ))
            renderer = p.line("x", "y", source=src, line_width=1.6,
                               color=colour, legend_label=f"{label} ({mutant})")
            p.scatter("x", "y", source=src, size=5, color=colour,
                       marker="circle", legend_label=f"{label} ({mutant})")
            p.add_tools(HoverTool(
                renderers=[renderer],
                tooltips=[("colony", "@label"), ("mutant", "@mutant"),
                          ("time", "@ts"), ("density (compensated)", "@y{%.2e}"),
                          ("raw density", "@raw{%.2e}"),
                          ("perturbed", "@perturbed")],
                formatters={"@y": "printf", "@raw": "printf"},
                mode="mouse",
            ))

            if ma is not None:
                events = ma[(ma["experiment_name"] == exp_name) & (ma["label"] == label)]
                if not events.empty:
                    # match each event to the nearest reading on this colony's
                    # own curve so the marker sits on the line, not floating
                    xs, ys, details = [], [], []
                    for row in events.itertuples():
                        idx = (g["timestamp"] - row.timestamp).abs().idxmin()
                        xs.append(g.loc[idx, "elapsed_hours"])
                        ys.append(g.loc[idx, "compensated_density"])
                        details.append(
                            f"{row.media_added_ml} mL into {row.volume_before_ml} mL "
                            f"(dilution {row.dilution_fraction:.2f})"
                        )
                    esrc = ColumnDataSource(dict(x=xs, y=ys, detail=details))
                    tri = p.scatter("x", "y", source=esrc, size=11, color=colour,
                                     marker="inverted_triangle",
                                     line_color="white", line_width=0.5)
                    p.add_tools(HoverTool(renderers=[tri],
                                           tooltips=[("media added", "@detail")]))

        p.toolbar.logo = None
        p.legend.click_policy = "hide"
        p.legend.label_text_font_size = "8pt"
        p.legend.location = "top_left"
        p.xgrid.grid_line_color = GRID
        p.ygrid.grid_line_color = GRID
        tabs.append(TabPanel(child=p, title=exp_name))

    output_file(f"{OUT}/interactive.html",
                title="cell-counts — growth curve explorer", mode="inline")
    save(Tabs(tabs=tabs))


def main():
    os.makedirs(OUT, exist_ok=True)
    cc = _read("all_cell_counts.csv")
    ma = _read("all_media_additions.csv")
    gs = _read("all_growth_summary.csv")

    if cc is not None:
        cc["timestamp"] = pd.to_datetime(cc["timestamp"])
    if ma is not None:
        ma["timestamp"] = pd.to_datetime(ma["timestamp"])

    plot_growth_curves_overview(cc)
    plot_doubling_time_summary(gs)
    plot_interactive(cc, ma)

    print(f"wrote {len(os.listdir(OUT))} file(s) to {OUT}/")


if __name__ == "__main__":
    main()
