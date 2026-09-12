# cell-counts

One place for every cell-density measurement in the lab — cultures logged by
nutrient, date and mutant line, across however the count was actually taken:
a dedicated growth-curve experiment, a day's Metaexperiment log, or an old
hand-kept CSV. Four pages, one per source, plus this dashboard tying them
together.

## Growth, every strain we have data for

<iframe src="plots/home_growth_dashboard.html" width="100%" height="1160" style="border:none;"
        title="Doubling time and growth curves, by strain"></iframe>

Two charts. **Doubling time by strain and colony** — current growth-curve
experiments (blue) and legacy data (red), grouped by strain — is the view
to watch for growth-rate drift in a cell line over time. **Growth curves
over real calendar time** plots every colony's own density readings
against real date/time (not elapsed hours — different experiments start on
different dates, so this view only makes sense on a shared calendar axis),
filterable by **mutant** and by **media**. Current-framework data has no
recorded media field yet, so it's shown as `TAP` by default (per the "TAP
unless stated otherwise" convention — see [Legacy data](legacy-data.md)).
Lab-wide events (an incubator change, a light-intensity change, and so on)
will show up on this chart as vertical dashed lines once their dates are
recorded — none are configured yet.

Metaexperiment logs aren't in either chart: those record one raw and one
separator density reading per culture per day, not a timeseries a doubling
time (or a growth curve) can be fit to, and carry no strain/mutant field to
group by (see the [Metaexperiments](metaexperiments.md) page). Motility/
swimming assays, minute-timescale protocol tests (centrifugation,
resuspension), and counting-protocol development runs are excluded from
both charts entirely — see [Legacy data](legacy-data.md) for the full list
and why.

## The three sources

| | |
|---|---|
| [Cell counting experiments](growth-curves.md) | The current framework: `cellcounting.py` logs counts and media additions through Trappy-Scopes' `Experiment.Construct`, and this site fits dilution-compensated growth curves from them automatically on every push. |
| [Metaexperiments](metaexperiments.md) | Day-level logs shared across microscopes: a culture's raw density and, when the day includes a separation step, its density after separating. Real calendar dates from day one. |
| [Legacy data](legacy-data.md) | Hand-kept CSVs from before this framework existed, normalised here into one schema so they plot the same way as everything else. |

See [Methodology](methodology.md) for what "dilution-compensated", "growth
rate" and "doubling time" actually mean, and [The data](data.md) for a short
note on where each source's numbers come from.

---

*`cellcounting.py`, the analysis it runs, and this site were built by
Claude, reviewed by Yatharth Bhasin.*
