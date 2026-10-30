# Cell counting experiments

Growth curves from the current framework — `cellcounting.py` on top of
Trappy-Scopes' `Experiment.Construct`. Density is dilution-compensated (see
[Methodology](methodology.md)) so a media addition reads as a continuation
of the same exponential, not a sudden drop.

## Interactive dashboard

Pick one experiment from the dropdown, or leave it on "All experiments" to
see every colony from every experiment on the same axis — the view that
matters for spotting whether a cell line's growth rate has drifted between
runs done weeks or months apart. Pan, zoom, hover for exact values, and
click a legend entry to hide or show a colony. The top panel is elapsed
time (hours since each colony's own first reading, so one experiment's
curve isn't offset by when it happened to start); the bottom panel is real
date/time, the same colonies on a shared calendar axis. Triangles mark
media-addition events.

<iframe src="../plots/interactive.html" width="100%" height="960" style="border:none;"
        title="Interactive growth curve explorer"></iframe>

[Open full screen →](plots/interactive.html){ .md-button }

**GitHub cannot display this** — README HTML is sanitised there, and files
viewed in the repo show as source. It's published here and also uploaded as
a workflow artifact on every CI run if you need a standalone copy.

## Doubling time

![Doubling time summary](plots/doubling_time_summary.png)

One number per colony: `ln(2) / growth_rate_per_hr`, with the fit's R² as a
reliability check. These same numbers, alongside legacy data, are on the
[home page](index.md) grouped by strain.

## Treated cultures (DCMU, cycloheximide, ...)

A culture counted with a treatment in its `condition` (for example
`condition="10uM DCMU"` or `"1uM cyclohexamine"` in `new_count`) is an
inhibited culture, so its growth rate is not comparable to the untreated
cultures of the same strain. In the aggregated data and every plot on this
site it is therefore grouped as its own strain, e.g. **CC125 + 10uM DCMU**,
next to **CC125** (the strain as logged is kept in the `mutant_raw` column
of `build/all_cell_counts.csv` and `all_growth_summary.csv`). A culture
counts as treated if any of its counts had a treatment, even if it was
released later. Blank conditions and vehicle controls such as `EtOH-VC` stay
with their strain; the vehicle words are listed in `VEHICLE_WORDS` in
`tools/parse_data.py`.
