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

Each culture (`label`) gets a raw-density point (before separation) and,
when a separation step was run that day, a separator-density point (after
separation), joined by a thin line so the drop from raw to separator
density reads at a glance.

This now covers the real Metaexperiment archive (dozens of folders, tens of
distinct culture labels) rather than the two hand-picked examples the
interim version plotted. Most labels appear on exactly one day; a Bokeh
legend with 60+ entries is unreadable, so there is no default legend at
all - instead a search-as-you-type MultiChoice box lets you isolate one or
more cultures by label, and hover always shows which label/day/folder a
point belongs to regardless of the filter.
"""

import os

import pandas as pd

BUILD = "build"
OUT = "plots"

PALETTE = ["#2f4b7c", "#b3423f", "#2e7d5b", "#c77d1a", "#7a4fa3", "#3a6ea5",
           "#c2185b", "#5d4037", "#00838f", "#8d6e63", "#558b2f", "#ad1457"]
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
        from bokeh.models import ColumnDataSource, HoverTool, MultiChoice, CustomJS, Div
        from bokeh.layouts import column
    except ImportError:
        print("bokeh not installed - skipping metaexperiments.html")
        return

    labels = sorted(df["label"].unique())
    colour_of = {lb: PALETTE[i % len(PALETTE)] for i, lb in enumerate(labels)}

    p = figure(
        x_axis_type="datetime", y_axis_type="log", height=560, width=980,
        tools="pan,box_zoom,wheel_zoom,reset,save",
        title="Metaexperiment cultures — raw density (before separation, circle) vs. "
              "separator density (after separation, square), by real date",
        x_axis_label="date / time", y_axis_label="density (cells/mL)",
    )

    # One CustomJS-driven filter box replaces a per-label legend (60+ entries
    # is unreadable and click-to-hide doesn't scale); it toggles renderer
    # visibility directly rather than restyling glyphs.
    all_renderers = []          # every renderer, for "selection cleared -> show all"
    renderer_label = []          # parallel list: which label each renderer belongs to

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
                       line_dash="dotted")

        src_raw = ColumnDataSource(dict(
            x=raw["dt"], y=raw["density"], label=[label] * len(raw),
            df=raw["df"], ts=raw["dt"].astype(str), source_folder=raw["source_folder"],
        ))
        r_raw = p.scatter("x", "y", source=src_raw, size=9, color=colour,
                           marker="circle")

        src_sep = ColumnDataSource(dict(
            x=sep["dt"], y=sep["density"], label=[label] * len(sep),
            df=sep["df"], ts=sep["dt"].astype(str), source_folder=sep["source_folder"],
        ))
        r_sep = p.scatter("x", "y", source=src_sep, size=9, color=colour,
                           marker="square", fill_alpha=0.3)

        p.add_tools(HoverTool(renderers=[r_raw], tooltips=[
            ("culture", "@label"), ("day", "@ts"), ("raw density", "@y{%.2e}"),
            ("count dilution (df)", "@df"), ("folder", "@source_folder"),
        ], formatters={"@y": "printf"}))
        p.add_tools(HoverTool(renderers=[r_sep], tooltips=[
            ("culture", "@label"), ("day", "@ts"), ("separator density", "@y{%.2e}"),
            ("count dilution (df)", "@df"), ("folder", "@source_folder"),
        ], formatters={"@y": "printf"}))

        for r in (line, r_raw, r_sep):
            all_renderers.append(r)
            renderer_label.append(label)

    p.xgrid.grid_line_color = GRID
    p.ygrid.grid_line_color = GRID
    p.toolbar.logo = None

    picker = MultiChoice(
        title="Filter by culture label (empty = show all)",
        options=labels, value=[], width=980,
        placeholder="start typing a culture label…",
    )
    note = Div(text=(
        f"<i>{len(labels)} culture label(s) across {df['source_folder'].nunique()} "
        "Metaexperiment day(s). Most labels appear on a single day (one raw + "
        "one separator point); a few span more than one day.</i>"
    ))

    callback = CustomJS(args=dict(renderers=all_renderers, owner=renderer_label), code="""
        const chosen = cb_obj.value;
        for (let i = 0; i < renderers.length; i++) {
            renderers[i].visible = (chosen.length === 0) || chosen.includes(owner[i]);
        }
    """)
    picker.js_on_change("value", callback)

    output_file(out_path, title="cell-counts — Metaexperiment cultures", mode="inline")
    save(column(picker, note, p, sizing_mode="stretch_width"))
    print(f"wrote {out_path} ({len(df)} rows, {len(labels)} culture(s))")


if __name__ == "__main__":
    main()
