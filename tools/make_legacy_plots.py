#!/usr/bin/env python3
"""
make_legacy_plots.py - build docs/plots/legacy.html from
build/all_legacy_counts.csv (run tools/parse_legacy.py first).

One combined interactive plot, real date/time on the x-axis (legacy data
predates the current framework's elapsed-hours convention and, unlike
Metaexperiment logs, spans months rather than days, so calendar time is the
only axis that makes every file comparable). A Select box - "All strains"
plus one entry per strain - filters which colonies are shown, the same
selector pattern as the growth-curves and Metaexperiment pages.

Density here is already dilution-corrected (see tools/parse_legacy.py's
module docstring for the formula and why it differs from what
legacy/script/analysis.py originally computed).
"""

import os

import pandas as pd

BUILD = "build"
OUT = "plots"

PALETTE = ["#2f4b7c", "#b3423f", "#2e7d5b", "#c77d1a", "#7a4fa3", "#3a6ea5",
           "#c2185b", "#5d4037", "#8d6e63", "#00796b", "#5e35b1", "#d81b60",
           "#455a64", "#f57f17", "#00838f", "#6d4c41", "#9e9d24"]
GRID = "#d8d8d8"


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(BUILD, "all_legacy_counts.csv")
    out_path = os.path.join(OUT, "legacy.html")

    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        open(out_path, "w").close()
        print(f"wrote {out_path} (no legacy data - run tools/parse_legacy.py first)")
        return

    df = pd.read_csv(path, parse_dates=["timestamp"])
    if df.empty:
        open(out_path, "w").close()
        print(f"wrote {out_path} (0 rows)")
        return

    try:
        from bokeh.plotting import figure, output_file, save
        from bokeh.models import ColumnDataSource, HoverTool, Select, CustomJS
        from bokeh.layouts import column
    except ImportError:
        print("bokeh not installed - skipping legacy.html")
        return

    strains = sorted(df["strain"].unique())
    # Keyed by (source_file, strain, label) rather than just (source_file,
    # label): TheEight.csv's replicate ids happen to be unique across its
    # own strains, but raw_exports/coimbra_growth_curves.csv reuses "BG-11"
    # / "TAP" as the label for three different strains (see
    # tools/parse_legacy.py), so strain has to be part of the key or those
    # three strains would collide onto the same colour.
    colonies = sorted(df[["source_file", "strain", "label"]].drop_duplicates().itertuples(index=False))
    colour_of = {(sf, st, lb): PALETTE[i % len(PALETTE)] for i, (sf, st, lb) in enumerate(colonies)}

    p = figure(
        x_axis_type="datetime", y_axis_type="log", height=560, width=980,
        tools="pan,box_zoom,wheel_zoom,reset,save",
        title="Legacy density data, normalised to one schema — drag to pan, scroll to zoom, "
              "click a legend entry to hide/show it",
        x_axis_label="date / time", y_axis_label="density (cells/mL, dilution-corrected)",
    )

    # No per-colony legend: with 30+ colony/replicate series across the
    # legacy files a Bokeh legend that size would cover the plot rather than
    # explain it. The strain Select below plus hover tooltips carry the
    # same identification without the clutter.
    js_renderers = []
    for (source_file, strain, label), g in df.groupby(["source_file", "strain", "label"]):
        g = g.sort_values("timestamp")
        colour = colour_of[(source_file, strain, label)]
        src = ColumnDataSource(dict(
            x=g["timestamp"], y=g["density"], label=[label] * len(g),
            strain=[strain] * len(g), source_file=[source_file] * len(g),
            ts=g["timestamp"].astype(str),
        ))
        r_line = p.line("x", "y", source=src, line_width=1.4, color=colour)
        r_line.tags = [strain]
        r_pts = p.scatter("x", "y", source=src, size=6, color=colour, marker="circle")
        r_pts.tags = [strain]
        p.add_tools(HoverTool(renderers=[r_pts], tooltips=[
            ("colony/replicate", "@label"), ("strain", "@strain"),
            ("source file", "@source_file"), ("time", "@ts"),
            ("density", "@y{%.2e}"),
        ], formatters={"@y": "printf"}, mode="mouse"))
        js_renderers += [r_line, r_pts]

    p.toolbar.logo = None
    p.xgrid.grid_line_color = GRID
    p.ygrid.grid_line_color = GRID

    select = Select(title="Strain", value="All strains", options=["All strains"] + strains)
    select.js_on_change("value", CustomJS(args=dict(renderers=js_renderers), code="""
        const chosen = cb_obj.value;
        for (const r of renderers) {
            const tag = r.tags.length ? r.tags[0] : null;
            r.visible = (chosen === "All strains") || (tag === chosen);
        }
    """))

    output_file(out_path, title="cell-counts — legacy data explorer", mode="inline")
    save(column(select, p, sizing_mode="stretch_width"))
    print(f"wrote {out_path} ({len(df)} rows, {len(strains)} strain(s), {len(colonies)} colony/replicate series)")


if __name__ == "__main__":
    main()
