#!/usr/bin/env python3
"""
make_home_dashboard.py - build docs/plots/home_growth_dashboard.html: one
interactive doubling-time chart across every strain and colony/replicate we
have a fit for, current-framework and legacy data together.

Sources combined here (run tools/parse_data.py and tools/parse_legacy.py
first):
    build/all_growth_summary.csv         current cellcounting.py experiments
    build/all_legacy_growth_summary.csv  legacy CSVs (motility-assay and
                                          minute-scale files already excluded
                                          by tools/parse_legacy.py)

Metaexperiment data is deliberately not in this dashboard: those logs record
one raw + one separator density reading per culture per day, not a
timeseries a doubling time can be fit to, and have no strain/mutant field to
group by in the first place (see tools/parse_metaexperiments.py).

Bars are grouped by strain (nested category axis: strain -> colony/
replicate), coloured by source, sorted by doubling time within each strain -
this is the "growth rate per mutant, current vs legacy" view asked for on
the home page.
"""

import os

import pandas as pd

BUILD = "build"
OUT = "plots"

CURRENT_COLOUR = "#2f4b7c"
LEGACY_COLOUR = "#b3423f"
GRID = "#d8d8d8"


def _read(name):
    path = os.path.join(BUILD, name)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return None
    df = pd.read_csv(path)
    return df if not df.empty else None


def main():
    os.makedirs(OUT, exist_ok=True)
    out_path = os.path.join(OUT, "home_growth_dashboard.html")

    current = _read("all_growth_summary.csv")
    legacy = _read("all_legacy_growth_summary.csv")

    rows = []
    if current is not None:
        for r in current.itertuples():
            rows.append(dict(strain=str(r.mutant), colony=r.label, source="current",
                              doubling_time_hr=r.doubling_time_hr, r_squared=r.r_squared,
                              n_points=r.n_points, detail=""))
    if legacy is not None:
        for r in legacy.itertuples():
            rows.append(dict(strain=str(r.strain), colony=r.label, source="legacy",
                              doubling_time_hr=r.doubling_time_hr, r_squared=r.r_squared,
                              n_points=r.n_points, detail=r.source_file))

    if not rows:
        open(out_path, "w").close()
        print(f"wrote {out_path} (no growth-rate fits available yet)")
        return

    df = pd.DataFrame(rows)
    df = df[df["doubling_time_hr"].apply(lambda x: x == x and x not in (float("inf"), float("-inf")) and x > 0)]
    df = df.sort_values(["strain", "doubling_time_hr"])

    try:
        from bokeh.plotting import figure, output_file, save
        from bokeh.models import ColumnDataSource, HoverTool, FactorRange
        from bokeh.transform import factor_cmap
        from bokeh.layouts import column
    except ImportError:
        print("bokeh not installed - skipping home_growth_dashboard.html")
        return

    factors = [(row.strain, f"{row.colony} ({row.source})") for row in df.itertuples()]
    src = ColumnDataSource(dict(
        x=factors, doubling_time_hr=df["doubling_time_hr"], strain=df["strain"],
        colony=df["colony"], source=df["source"], r_squared=df["r_squared"],
        n_points=df["n_points"], detail=df["detail"],
    ))

    p = figure(
        x_range=FactorRange(*factors), height=max(420, 26 * len(factors)),
        width=980, tools="pan,wheel_zoom,reset,save",
        title="Doubling time by strain and colony — current growth-curve experiments vs. legacy data",
        y_axis_label="doubling time (hours)",
    )
    p.vbar(x="x", top="doubling_time_hr", width=0.8, source=src,
           fill_color=factor_cmap("source", [CURRENT_COLOUR, LEGACY_COLOUR], ["current", "legacy"]),
           line_color="white")
    p.add_tools(HoverTool(tooltips=[
        ("strain", "@strain"), ("colony/replicate", "@colony"), ("source", "@source"),
        ("doubling time", "@doubling_time_hr{0.0} h"), ("R²", "@r_squared{0.00}"),
        ("n points", "@n_points"), ("file (legacy only)", "@detail"),
    ]))
    p.xaxis.major_label_orientation = 1.0
    p.xaxis.group_label_orientation = 0.9
    p.xaxis.subgroup_label_orientation = 1.0
    p.y_range.start = 0
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = GRID
    p.toolbar.logo = None

    output_file(out_path, title="cell-counts — doubling time, all strains", mode="inline")
    save(column(p, sizing_mode="stretch_width"))
    print(f"wrote {out_path} ({len(df)} colony/replicate fit(s), {df['strain'].nunique()} strain(s))")


if __name__ == "__main__":
    main()
