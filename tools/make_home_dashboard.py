#!/usr/bin/env python3
"""
make_home_dashboard.py - build docs/plots/home_growth_dashboard.html: the
home page's two cross-source growth charts, current-framework and legacy
data together.

Sources combined here (run tools/parse_data.py and tools/parse_legacy.py
first):
    build/all_growth_summary.csv         current cellcounting.py experiments
                                          - doubling-time fits
    build/all_cell_counts.csv            current cellcounting.py experiments
                                          - per-point density
    build/all_legacy_growth_summary.csv  legacy CSVs - doubling-time fits
    build/all_legacy_counts.csv          legacy CSVs - per-point density
                                          (already restricted to pure growth
                                          curves only - protocol-development
                                          and centrifugation/motility runs
                                          are excluded upstream, see
                                          tools/parse_legacy.py)

Metaexperiment data is deliberately not in either chart: those logs record
one raw + one separator density reading per culture per day, not a
timeseries a doubling time (or a growth curve) can be fit to, and have no
strain/mutant field to group by in the first place (see
tools/parse_metaexperiments.py).

Two charts, stacked on one page:

1. Doubling time by strain and colony (bar chart, unchanged) - bars grouped
   by strain (nested category axis: strain -> colony/replicate), coloured
   by source, sorted by doubling time within each strain.

2. Growth curves over real calendar time (new) - every colony's density
   plotted against its own real timestamp, not elapsed hours: this is a
   cross-experiment, cross-source view and different experiments start on
   different dates, so elapsed-hours-since-start (what every single-
   experiment plot elsewhere on this site uses) would overlay unrelated
   colonies on top of each other. Filterable by mutant and by media.

   Current-framework rows have no recorded media field at all - per
   Yatharth, "assume TAP wherever not mentioned" - so they default to
   "TAP" for filtering purposes only; this default is applied here, in the
   dashboard, not written back into build/all_cell_counts.csv or any
   upstream file.

   Lab-wide events (an incubator change, a light-intensity change, etc.)
   can be marked as vertical dashed lines across this chart's real-time
   axis via the EVENTS list below - currently empty, pending exact
   dates/times from Yatharth. Adding one is a one-line change: no other
   code here needs to change.
"""

import os

import pandas as pd

BUILD = "build"
OUT = "plots"

CURRENT_COLOUR = "#2f4b7c"
LEGACY_COLOUR = "#b3423f"
GRID = "#d8d8d8"

DEFAULT_MEDIA = "TAP"  # matches tools/parse_legacy.py's DEFAULT_MEDIA

PALETTE = ["#2f4b7c", "#b3423f", "#2e7d5b", "#c77d1a", "#7a4fa3", "#3a6ea5",
           "#c2185b", "#5d4037", "#00838f", "#8d6e63", "#558b2f", "#ad1457"]

# Vertical dashed-line markers for lab-wide events, shown on chart 2's real
# time axis. Empty for now - pending exact dates/times. To add one:
#   EVENTS = [
#       {"label": "changed incubator", "at": "2026-06-01 00:00:00"},
#       {"label": "increased light intensity", "at": "2026-06-15 00:00:00"},
#       {"label": "started growth with air exchange", "at": "2026-07-01 00:00:00"},
#   ]
EVENTS = []


def _read(name):
    path = os.path.join(BUILD, name)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return None
    df = pd.read_csv(path)
    return df if not df.empty else None


def _build_doubling_time_chart(current_gs, legacy_gs):
    from bokeh.plotting import figure
    from bokeh.models import ColumnDataSource, HoverTool, FactorRange
    from bokeh.transform import factor_cmap

    rows = []
    if current_gs is not None:
        for r in current_gs.itertuples():
            rows.append(dict(strain=str(r.mutant), colony=r.label, source="current",
                              doubling_time_hr=r.doubling_time_hr, r_squared=r.r_squared,
                              n_points=r.n_points, detail=""))
    if legacy_gs is not None:
        for r in legacy_gs.itertuples():
            rows.append(dict(strain=str(r.strain), colony=r.label, source="legacy",
                              doubling_time_hr=r.doubling_time_hr, r_squared=r.r_squared,
                              n_points=r.n_points, detail=r.source_file))

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df = df[df["doubling_time_hr"].apply(lambda x: x == x and x not in (float("inf"), float("-inf")) and x > 0)]
    df = df.sort_values(["strain", "doubling_time_hr"])
    if df.empty:
        return None

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
    return p, len(df), df["strain"].nunique()


def _unified_points(current_cc, legacy_cc):
    """One row per (source, mutant, colony, timestamp, density) - the common
    shape chart 2 needs, whichever source it came from."""
    rows = []
    if current_cc is not None:
        cc = current_cc.copy()
        cc["timestamp"] = pd.to_datetime(cc["timestamp"])
        for r in cc.itertuples():
            rows.append(dict(
                source="current", mutant=str(r.mutant), media=DEFAULT_MEDIA,
                colony=r.label, timestamp=r.timestamp, density=r.compensated_density,
                detail=getattr(r, "experiment_name", ""),
            ))
    if legacy_cc is not None:
        lc = legacy_cc.copy()
        lc["timestamp"] = pd.to_datetime(lc["timestamp"])
        for r in lc.itertuples():
            media = str(r.media).strip() if pd.notna(r.media) and str(r.media).strip() else DEFAULT_MEDIA
            rows.append(dict(
                source="legacy", mutant=str(r.strain), media=media,
                colony=r.label, timestamp=r.timestamp, density=r.density,
                detail=r.source_file,
            ))
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["timestamp", "density"])
    df = df[df["density"] > 0]
    return df if not df.empty else None


def _build_realtime_growth_chart(current_cc, legacy_cc):
    from bokeh.plotting import figure
    from bokeh.models import ColumnDataSource, HoverTool, Select, CustomJS, Span, Label
    from bokeh.layouts import row as bokeh_row

    df = _unified_points(current_cc, legacy_cc)
    if df is None:
        return None

    mutants = sorted(df["mutant"].unique())
    media_types = sorted(df["media"].unique())
    # Keyed by (source, mutant, colony) rather than just (source, colony):
    # raw_exports/coimbra_growth_curves.csv reuses "BG-11" / "TAP" as the
    # colony/replicate label across three different strains (see
    # tools/parse_legacy.py's "BG-11 media" section), so mutant has to be
    # part of the key or those three strains would collide onto one colour.
    colonies = sorted(df[["source", "mutant", "colony"]].drop_duplicates().itertuples(index=False))
    colour_of = {(src, mu, col): PALETTE[i % len(PALETTE)] for i, (src, mu, col) in enumerate(colonies)}

    p = figure(
        x_axis_type="datetime", y_axis_type="log", height=520, width=980,
        tools="pan,box_zoom,wheel_zoom,reset,save",
        title="Growth curves over real calendar time — current growth-curve experiments and legacy data",
        x_axis_label="date / time", y_axis_label="density (cells/mL)",
    )

    # No per-colony legend: with this many colony/replicate series across
    # both sources a legend that size would cover the plot rather than
    # explain it (same reasoning as the legacy-data page). The mutant/media
    # Selects below plus hover carry the identification instead.
    renderers = []
    renderer_mutant = []
    renderer_media = []
    for (source, mutant, media, colony), g in df.groupby(["source", "mutant", "media", "colony"]):
        g = g.sort_values("timestamp")
        colour = colour_of[(source, mutant, colony)]
        src = ColumnDataSource(dict(
            x=g["timestamp"], y=g["density"], mutant=[mutant] * len(g),
            media=[media] * len(g), colony=[colony] * len(g),
            source_label=[source] * len(g), detail=g["detail"],
            ts=g["timestamp"].astype(str),
        ))
        line_dash = "solid" if source == "current" else "dashed"
        r_line = p.line("x", "y", source=src, line_width=1.3, color=colour, line_dash=line_dash)
        r_pts = p.scatter("x", "y", source=src, size=6, color=colour, marker="circle")
        p.add_tools(HoverTool(renderers=[r_pts], tooltips=[
            ("mutant", "@mutant"), ("media", "@media"), ("colony/replicate", "@colony"),
            ("source", "@source_label"), ("time", "@ts"), ("density", "@y{%.2e}"),
            ("detail", "@detail"),
        ], formatters={"@y": "printf"}, mode="mouse"))
        for r in (r_line, r_pts):
            renderers.append(r)
            renderer_mutant.append(mutant)
            renderer_media.append(media)

    for event in EVENTS:
        at = pd.Timestamp(event["at"])
        span = Span(location=at.timestamp() * 1000, dimension="height",
                     line_color="#555555", line_dash="dashed", line_width=1.5)
        p.add_layout(span)
        label = Label(x=at.timestamp() * 1000, y=0, y_units="screen", angle=1.5708,
                      text=f"  {event['label']}", text_font_size="8pt", text_color="#555555")
        p.add_layout(label)

    p.xgrid.grid_line_color = GRID
    p.ygrid.grid_line_color = GRID
    p.toolbar.logo = None

    mutant_select = Select(title="Mutant", value="All mutants", options=["All mutants"] + mutants)
    media_select = Select(title="Media", value="All media", options=["All media"] + media_types)
    callback = CustomJS(
        args=dict(renderers=renderers, r_mutant=renderer_mutant, r_media=renderer_media,
                   mutant_select=mutant_select, media_select=media_select),
        code="""
        const chosenMutant = mutant_select.value;
        const chosenMedia = media_select.value;
        for (let i = 0; i < renderers.length; i++) {
            const mutantOk = (chosenMutant === "All mutants") || (r_mutant[i] === chosenMutant);
            const mediaOk = (chosenMedia === "All media") || (r_media[i] === chosenMedia);
            renderers[i].visible = mutantOk && mediaOk;
        }
        """,
    )
    mutant_select.js_on_change("value", callback)
    media_select.js_on_change("value", callback)

    controls = bokeh_row(mutant_select, media_select)
    return controls, p, len(df), len(mutants)


def main():
    os.makedirs(OUT, exist_ok=True)
    out_path = os.path.join(OUT, "home_growth_dashboard.html")

    current_gs = _read("all_growth_summary.csv")
    legacy_gs = _read("all_legacy_growth_summary.csv")
    current_cc = _read("all_cell_counts.csv")
    legacy_cc = _read("all_legacy_counts.csv")

    try:
        from bokeh.plotting import output_file, save
        from bokeh.layouts import column
    except ImportError:
        print("bokeh not installed - skipping home_growth_dashboard.html")
        return

    pieces = []
    bar_result = _build_doubling_time_chart(current_gs, legacy_gs)
    realtime_result = _build_realtime_growth_chart(current_cc, legacy_cc)

    if bar_result is not None:
        bar_fig, n_bars, n_strains_bar = bar_result
        pieces.append(bar_fig)
    if realtime_result is not None:
        controls, realtime_fig, n_points, n_mutants = realtime_result
        pieces.append(controls)
        pieces.append(realtime_fig)

    if not pieces:
        open(out_path, "w").close()
        print(f"wrote {out_path} (no growth data available yet)")
        return

    output_file(out_path, title="cell-counts — growth dashboard", mode="inline")
    save(column(*pieces, sizing_mode="stretch_width"))

    if bar_result is not None:
        print(f"  doubling-time chart: {n_bars} colony/replicate fit(s), {n_strains_bar} strain(s)")
    else:
        print("  doubling-time chart: skipped (no fits available)")
    if realtime_result is not None:
        print(f"  real-time growth chart: {n_points} point(s), {n_mutants} mutant(s)"
              f"{' (no EVENTS configured yet)' if not EVENTS else f', {len(EVENTS)} event marker(s)'}")
    else:
        print("  real-time growth chart: skipped (no per-point data available)")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
