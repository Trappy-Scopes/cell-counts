# cell-counts

One place for every cell-density measurement in the lab — cultures logged by
nutrient, date and mutant line, across however the count was actually taken:
a dedicated growth-curve experiment, a day's Metaexperiment log, or an old
hand-kept CSV. Four pages, one per source, plus this dashboard tying them
together.

## Doubling time, every strain we have a fit for

<iframe src="plots/home_growth_dashboard.html" width="100%" height="560" style="border:none;"
        title="Doubling time by strain and colony"></iframe>

Current growth-curve experiments (blue) and legacy data (red), grouped by
strain — this is the view to watch for growth-rate drift in a cell line
over time. Metaexperiment logs aren't in it: those record one raw and one
separator density reading per culture per day, not a timeseries a doubling
time can be fit to, and carry no strain/mutant field to group by (see the
[Metaexperiments](metaexperiments.md) page). Motility/swimming assays and
minute-timescale protocol tests (centrifugation, resuspension) are excluded
from every doubling-time number here for the same reason a stopwatch
reading isn't a growth rate — see [Methodology](methodology.md) and
[Legacy data](legacy-data.md) for what's excluded and why.

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
