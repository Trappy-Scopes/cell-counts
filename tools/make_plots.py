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
    """Bokeh: a single combined dashboard across every cellcounting.py
    experiment, not one tab per experiment - so growth-rate drift between
    experiments (run at different calendar times) is visible on one axis.

    Two stacked figures share every renderer and the same colony colours:
    elapsed time (hours since that colony's own first reading - the natural
    axis for a single growth curve) on top, real calendar date/time on the
    bottom (the natural axis for spotting drift between experiments run
    weeks or months apart). A Select box above both - "All experiments" plus
    one entry per experiment - shows/hides renderers in both figures at
    once via a CustomJS filter (this page has no Python server, so the
    filter has to run client-side); "All experiments" is the combined
    dashboard the growth-rate-drift question actually needs.

    Dilution/media-addition events are drawn as inverted triangles on the
    colony's own line, on both axes.
    """
    try:
        from bokeh.plotting import figure, output_file, save
        from bokeh.models import ColumnDataSource, HoverTool, Select, CustomJS
        from bokeh.layouts import column
    except ImportError:
        print("bokeh not installed - skipping interactive.html")
        return
    if cc is None:
        return

    tools = "pan,box_zoom,wheel_zoom,reset,save"
    experiments = sorted(cc["experiment_name"].unique())
    labels = sorted(cc["label"].unique())
    colour_of_label = {lb: PALETTE[i % len(PALETTE)] for i, lb in enumerate(labels)}

    fig_elapsed = figure(
        y_axis_type="log", height=440, width=980, tools=tools,
        title="Elapsed time per colony — drag to pan, scroll to zoom, "
              "click a legend entry to hide/show it",
        x_axis_label="elapsed time (hours, since that colony's own first reading)",
        y_axis_label="density (cells/mL, dilution-compensated)",
    )
    fig_datetime = figure(
        x_axis_type="datetime", y_axis_type="log", height=440, width=980, tools=tools,
        title="Real date/time, every experiment on one axis — for spotting growth-rate drift over calendar time",
        x_axis_label="date / time",
        y_axis_label="density (cells/mL, dilution-compensated)",
    )

    js_renderers = []  # every renderer that should respond to the Select box

    for (exp_name, label), g in cc.groupby(["experiment_name", "label"]):
        g = g.sort_values("elapsed_hours")
        mutant = g["mutant"].iloc[0] if "mutant" in g else None
        colour = colour_of_label[label]
        legend = f"{label} ({mutant}) — {exp_name}" if len(experiments) > 1 else f"{label} ({mutant})"
        src = ColumnDataSource(dict(
            x_elapsed=g["elapsed_hours"], x_datetime=g["timestamp"],
            y=g["compensated_density"], raw=g["density"],
            label=[label] * len(g), mutant=[str(mutant)] * len(g),
            experiment=[exp_name] * len(g),
            perturbed=[str(bool(p)) for p in g.get("perturbed", [False] * len(g))],
            ts=g["timestamp"].astype(str),
        ))
        hover_tooltips = [("colony", "@label"), ("mutant", "@mutant"),
                          ("experiment", "@experiment"), ("time", "@ts"),
                          ("density (compensated)", "@y{%.2e}"),
                          ("raw density", "@raw{%.2e}"), ("perturbed", "@perturbed")]
        for fig, xcol in ((fig_elapsed, "x_elapsed"), (fig_datetime, "x_datetime")):
            r_line = fig.line(xcol, "y", source=src, line_width=1.6, color=colour,
                               legend_label=legend)
            r_line.tags = [exp_name]
            r_pts = fig.scatter(xcol, "y", source=src, size=5, color=colour,
                                 marker="circle", legend_label=legend)
            r_pts.tags = [exp_name]
            fig.add_tools(HoverTool(renderers=[r_pts], tooltips=hover_tooltips,
                                     formatters={"@y": "printf", "@raw": "printf"}, mode="mouse"))
            js_renderers += [r_line, r_pts]

        if ma is not None:
            events = ma[(ma["experiment_name"] == exp_name) & (ma["label"] == label)]
            if not events.empty:
                xs_e, xs_d, ys, details = [], [], [], []
                for row in events.itertuples():
                    idx = (g["timestamp"] - row.timestamp).abs().idxmin()
                    xs_e.append(g.loc[idx, "elapsed_hours"])
                    xs_d.append(g.loc[idx, "timestamp"])
                    ys.append(g.loc[idx, "compensated_density"])
                    details.append(
                        f"{row.media_added_ml} mL into {row.volume_before_ml} mL "
                        f"(dilution {row.dilution_fraction:.2f})"
                    )
                esrc = ColumnDataSource(dict(x_elapsed=xs_e, x_datetime=xs_d, y=ys, detail=details))
                for fig, xcol in ((fig_elapsed, "x_elapsed"), (fig_datetime, "x_datetime")):
                    tri = fig.scatter(xcol, "y", source=esrc, size=11, color=colour,
                                       marker="inverted_triangle", line_color="white",
                                       line_width=0.5)
                    tri.tags = [exp_name]
                    fig.add_tools(HoverTool(renderers=[tri], tooltips=[("media added", "@detail")]))
                    js_renderers.append(tri)

    for fig in (fig_elapsed, fig_datetime):
        fig.toolbar.logo = None
        fig.legend.click_policy = "hide"
        fig.legend.label_text_font_size = "8pt"
        fig.legend.location = "top_left"
        fig.xgrid.grid_line_color = GRID
        fig.ygrid.grid_line_color = GRID

    select = Select(title="Experiment", value="All experiments",
                     options=["All experiments"] + experiments)
    select.js_on_change("value", CustomJS(args=dict(renderers=js_renderers), code="""
        const chosen = cb_obj.value;
        for (const r of renderers) {
            const tag = r.tags.length ? r.tags[0] : null;
            r.visible = (chosen === "All experiments") || (tag === chosen);
        }
    """))

    output_file(f"{OUT}/interactive.html",
                title="cell-counts — growth curve explorer", mode="inline")
    save(column(select, fig_elapsed, fig_datetime, sizing_mode="stretch_width"))


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
