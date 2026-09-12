#!/usr/bin/env python3
"""
make_metaexperiment_plots.py - build docs/plots/metaexperiments.html from
build/all_metaexperiment_counts.csv (run tools/parse_metaexperiments.py first).

Metaexperiment logs carry genuine calendar dates from day one - unlike a
cellcounting.py experiment, there's no "elapsed hours since the first
reading" framing here, only real date/time, which is also the more useful
axis for this data: it's meant to show what cultures were in use and how
dense/how well-separated they were on a given day, not a growth curve fit
to two points.

Each culture (`label`) gets a raw-density point (before separation) and a
separator-density point (after separation) per day it was logged, joined by
a thin line so the drop from raw to separator density reads at a glance.
"""

import os

import pandas as pd

BUILD = "build"
OUT = "plots"

PALETTE = ["#2f4b7c", "#b3423f", "#2e7d5b", "#c77d1a", "#7a4fa3", "#3a6ea5",
           "#c2185b", "#5d4037"]
GRID = "#d8d8d8"


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(BUILD, "all_metaexperiment_counts.csv")
    out_path = os.path.join(OUT, "metaexperiments.html")

    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        open(out_path, "w").close()
        print(f"wrote {out_path} (no Metaexperiment data - run tools/parse_metaexperiments.py first)")
        return

    df = pd.read_csv(path, parse_dates=["dt"])
    if df.empty:
        open(out_path, "w").close()
        print(f"wrote {out_path} (0 rows)")
        return

    try:
        from bokeh.plotting import figure, output_file, save
        from bokeh.models import ColumnDataSource, HoverTool
        from bokeh.layouts import column
    except ImportError:
        print("bokeh not installed - skipping metaexperiments.html")
        return

    labels = sorted(df["label"].unique())
    colour_of = {lb: PALETTE[i % len(PALETTE)] for i, lb in enumerate(labels)}

    p = figure(
        x_axis_type="datetime", y_axis_type="log", height=520, width=980,
        tools="pan,box_zoom,wheel_zoom,reset,save",
        title="Metaexperiment cultures — raw density (before separation, circle) vs. "
              "separator density (after separation, square), by real date",
        x_axis_label="date / time", y_axis_label="density (cells/mL)",
    )

    for label, g in df.groupby("label"):
        g = g.sort_values("dt")
        colour = colour_of[label]
        raw = g[~g["sep"]]
        sep = g[g["sep"]]

        src_all = ColumnDataSource(dict(
            x=g["dt"], y=g["density"], label=[label] * len(g),
            kind=["separator" if s else "raw" for s in g["sep"]],
            df=g["df"], ts=g["dt"].astype(str), source_folder=g["source_folder"],
        ))
        line = p.line("x", "y", source=src_all, color=colour, line_width=1.2,
                       line_dash="dotted", legend_label=label)

        src_raw = ColumnDataSource(dict(
            x=raw["dt"], y=raw["density"], label=[label] * len(raw),
            df=raw["df"], ts=raw["dt"].astype(str), source_folder=raw["source_folder"],
        ))
        r_raw = p.scatter("x", "y", source=src_raw, size=9, color=colour,
                           marker="circle", legend_label=label)

        src_sep = ColumnDataSource(dict(
            x=sep["dt"], y=sep["density"], label=[label] * len(sep),
            df=sep["df"], ts=sep["dt"].astype(str), source_folder=sep["source_folder"],
        ))
        r_sep = p.scatter("x", "y", source=src_sep, size=9, color=colour,
                           marker="square", fill_alpha=0.3, legend_label=label)

        p.add_tools(HoverTool(renderers=[r_raw], tooltips=[
            ("culture", "@label"), ("day", "@ts"), ("raw density", "@y{%.2e}"),
            ("count dilution (df)", "@df"), ("folder", "@source_folder"),
        ], formatters={"@y": "printf"}))
        p.add_tools(HoverTool(renderers=[r_sep], tooltips=[
            ("culture", "@label"), ("day", "@ts"), ("separator density", "@y{%.2e}"),
            ("count dilution (df)", "@df"), ("folder", "@source_folder"),
        ], formatters={"@y": "printf"}))

    p.toolbar.logo = None
    p.legend.click_policy = "hide"
    p.legend.label_text_font_size = "8pt"
    p.legend.location = "top_left"
    p.xgrid.grid_line_color = GRID
    p.ygrid.grid_line_color = GRID

    output_file(out_path, title="cell-counts — Metaexperiment cultures", mode="inline")
    save(column(p, sizing_mode="stretch_width"))
    print(f"wrote {out_path} ({len(df)} rows, {len(labels)} culture(s))")


if __name__ == "__main__":
    main()
